"""Command arbitration and jog orchestration (API and websocket notifications)."""

from __future__ import annotations

import asyncio
import logging
import platform
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, cast

from pi_deck.hardware.protoboard_pins import JogAction
from pi_deck.models.schemas import (
    CommandRejectedReason,
    ControlState,
    OperatingMode,
    StatusOut,
    ws_command_rejected,
)
from pi_deck.services.hardware_facade import DeckHardwareFacade
from pi_deck.services.live_log import LiveLogService
from pi_deck.services.ws_hub import WsHub

logger = logging.getLogger(__name__)

_ACTION_MAP: dict[str, JogAction] = {
    "center": JogAction.CENTER,
    "up": JogAction.UP,
    "down": JogAction.DOWN,
    "left": JogAction.LEFT,
    "right": JogAction.RIGHT,
}
_STR_FOR_ACTION: dict[JogAction, str] = {v: k for k, v in _ACTION_MAP.items()}

_MAX_HOLD_S = 20.0
_COMMUNICATION_MEASUREMENT_S = 3.0
_MAX_COMMUNICATION_BIT_TIME_S = 1.0


@dataclass
class HoldRecord:
    start_monotonic: float
    watchdog: asyncio.Task[None] | None = None


@dataclass
class DeckControlService:
    """Jog orchestration with one authoritative hold per direction."""

    hardware: DeckHardwareFacade
    ws_hub: WsHub
    live_log: LiveLogService
    version: str
    _operating_mode: OperatingMode = OperatingMode.JOG
    _control_state: ControlState = ControlState.IDLE
    _hold: dict[JogAction, HoldRecord] = field(default_factory=dict)
    _pulse_in_progress: bool = field(default=False, repr=False)
    _custom_command_in_progress: bool = field(default=False, repr=False)
    _communication_sample_listener: Callable[[int, int], None] | None = field(
        default=None, repr=False
    )

    def configure_communication_sample_listener(
        self, listener: Callable[[int, int], None]
    ) -> None:
        self._communication_sample_listener = listener

    def status(self) -> StatusOut:
        return StatusOut(
            version=self.version,
            hardware=cast(Literal["live", "mock"], self.hardware.kind),
            operating_mode=self._operating_mode,
            control_state=self._control_state,
            signals=self.hardware.read_bus_snapshot(),
            os_version=platform.platform(terse=True),
            python_version=sys.version.split()[0],
        )

    def set_operating_mode(self, mode: OperatingMode) -> None:
        self._operating_mode = mode

    def _any_holds(self) -> bool:
        return len(self._hold) > 0

    def _cancel_watchdog(self, rec: HoldRecord) -> None:
        if rec.watchdog is not None:
            rec.watchdog.cancel()
            rec.watchdog = None

    def _schedule_watchdog(self, jog: JogAction) -> None:
        deck = self
        action_str = _STR_FOR_ACTION[jog]

        async def _run() -> None:
            try:
                await asyncio.sleep(_MAX_HOLD_S)
                err, _ms = await deck.jog_release(action_str)
                if err is not None:
                    logger.warning("watchdog release %s: %s", action_str, err)
            except asyncio.CancelledError:
                pass

        rec = self._hold.get(jog)
        if rec is None:
            return
        self._cancel_watchdog(rec)
        rec.watchdog = asyncio.create_task(_run())

    async def jog_hold(self, action: str) -> CommandRejectedReason | None:
        """Assert ``action``; same-direction replacement avoids a GPIO glitch."""
        if self._custom_command_in_progress:
            return CommandRejectedReason.CONCURRENT_COMMAND
        jog = _ACTION_MAP.get(action)
        if jog is None:
            return CommandRejectedReason.HARDWARE_ERROR

        # Replace same direction: no GPIO toggle (no extra drive edge).
        if jog in self._hold:
            prev = self._hold[jog]
            self._cancel_watchdog(prev)
            now = time.monotonic()
            self._hold[jog] = HoldRecord(start_monotonic=now)
            self._schedule_watchdog(jog)
            return None

        try:
            await asyncio.to_thread(self.hardware.set_jog_line, jog, True)
        except Exception:
            logger.exception("set_jog_line failed")
            msg = "Hardware failure while asserting jog line"
            await self._emit(
                ws_command_rejected(reason=CommandRejectedReason.HARDWARE_ERROR, message=msg),
            )
            return CommandRejectedReason.HARDWARE_ERROR

        self._hold[jog] = HoldRecord(start_monotonic=time.monotonic())
        self._schedule_watchdog(jog)
        self._control_state = ControlState.COMMANDING if self._any_holds() else ControlState.IDLE
        return None

    async def jog_release(self, action: str) -> tuple[CommandRejectedReason | None, int]:
        """Release ``action``; idempotent when already idle for that direction (duration_ms 0)."""
        jog = _ACTION_MAP.get(action)
        if jog is None:
            return CommandRejectedReason.HARDWARE_ERROR, 0

        rec = self._hold.pop(jog, None)
        if rec is None:
            return None, 0

        self._cancel_watchdog(rec)
        duration_ms = int((time.monotonic() - rec.start_monotonic) * 1000)
        duration_ms = max(0, min(duration_ms, 60_000))

        try:
            await asyncio.to_thread(self.hardware.set_jog_line, jog, False)
        except Exception:
            logger.exception("set_jog_line off failed")
            want = ControlState.COMMANDING if self._any_holds() else ControlState.IDLE
            self._control_state = want
            return CommandRejectedReason.HARDWARE_ERROR, 0

        self._control_state = (
            ControlState.COMMANDING if self._any_holds() else ControlState.IDLE
        )
        return None, duration_ms

    async def jog_press(self, action: str, duration_ms: int) -> None | CommandRejectedReason:
        """Legacy timed pulse — not allowed while directional holds are active."""
        if self._any_holds():
            await self._emit(
                ws_command_rejected(
                    reason=CommandRejectedReason.ACTIVE_HOLDS,
                    message="Release active jog holds before using timed pulse",
                ),
            )
            return CommandRejectedReason.ACTIVE_HOLDS

        if self._pulse_in_progress or self._custom_command_in_progress:
            await self._emit(
                ws_command_rejected(
                    reason=CommandRejectedReason.CONCURRENT_COMMAND,
                    message="Another timed pulse is in progress",
                ),
            )
            return CommandRejectedReason.CONCURRENT_COMMAND

        jog = _ACTION_MAP.get(action)
        if jog is None:
            return CommandRejectedReason.HARDWARE_ERROR

        duration_s = duration_ms / 1000.0
        if duration_s <= 0:
            return CommandRejectedReason.INVALID_DURATION

        self._pulse_in_progress = True
        try:
            self._control_state = ControlState.COMMANDING
            try:
                try:
                    await asyncio.to_thread(self.hardware.pulse, jog, duration_s)
                except Exception:
                    logger.exception("jog pulse failed")
                    msg = "Hardware failure during jog pulse"
                    await self._emit(
                        ws_command_rejected(
                            reason=CommandRejectedReason.HARDWARE_ERROR,
                            message=msg,
                        ),
                    )
                    return CommandRejectedReason.HARDWARE_ERROR

                return None
            finally:
                self._control_state = ControlState.IDLE
        finally:
            self._pulse_in_progress = False

    async def send_monitor_command_bits(
        self,
        bits: tuple[int, ...],
        bit_time_s: float,
    ) -> list[tuple[int, int]]:
        """Drive NRZ through the dedicated 10 kΩ KEY_ADC1 branch with deadline timing."""
        if len(bits) != 16 or any(bit not in (0, 1) for bit in bits):
            raise ValueError("monitor command must contain exactly 16 binary bits")
        if not 0.001 <= bit_time_s <= _MAX_COMMUNICATION_BIT_TIME_S:
            raise ValueError("monitor command bit time must be 1-1000 ms")
        if self._any_holds() or self._pulse_in_progress or self._custom_command_in_progress:
            raise RuntimeError("jog control is busy")

        self._custom_command_in_progress = True
        self._control_state = ControlState.COMMANDING

        def _transmit() -> list[tuple[int, int]]:
            samples: list[tuple[int, int]] = []
            # The protocol requires at least 100 ms released before the first high bit.
            self.hardware.set_communication_line(False)
            time.sleep(0.100)
            deadline = time.monotonic()
            try:
                for bit in bits:
                    self.hardware.set_communication_line(bool(bit))
                    timestamp = time.monotonic_ns()
                    samples.append((timestamp, bit))
                    if self._communication_sample_listener is not None:
                        self._communication_sample_listener(timestamp, bit)
                    deadline += bit_time_s
                    remaining = deadline - time.monotonic()
                    if remaining > 0:
                        time.sleep(remaining)
            finally:
                self.hardware.set_communication_line(False)
                timestamp = time.monotonic_ns()
                samples.append((timestamp, 0))
                if self._communication_sample_listener is not None:
                    self._communication_sample_listener(timestamp, 0)
            return samples

        try:
            return await asyncio.to_thread(_transmit)
        finally:
            self._custom_command_in_progress = False
            self._control_state = ControlState.IDLE

    async def hold_communication_high_for_measurement(self) -> list[tuple[int, int]]:
        """Assert only the custom ``KEY_ADC1`` transmitter for three seconds, then release it."""
        if self._any_holds() or self._pulse_in_progress or self._custom_command_in_progress:
            raise RuntimeError("jog control is busy")

        self._custom_command_in_progress = True
        self._control_state = ControlState.COMMANDING

        def _hold_high() -> list[tuple[int, int]]:
            samples: list[tuple[int, int]] = []
            self.hardware.set_communication_line(False)
            try:
                self.hardware.set_communication_line(True)
                samples.append((time.monotonic_ns(), 1))
                time.sleep(_COMMUNICATION_MEASUREMENT_S)
            finally:
                self.hardware.set_communication_line(False)
                samples.append((time.monotonic_ns(), 0))
            return samples

        try:
            return await asyncio.to_thread(_hold_high)
        finally:
            self._custom_command_in_progress = False
            self._control_state = ControlState.IDLE

    async def _emit(self, event: object) -> None:
        payload = (
            event.model_dump(mode="json") if hasattr(event, "model_dump") else event  # type: ignore[assignment]
        )
        if not isinstance(payload, dict):
            return
        log_event = self.live_log.record_event(payload)
        if self.ws_hub.client_count == 0:
            return
        await self.ws_hub.broadcast_json(payload)
        if log_event is not None:
            await self.ws_hub.broadcast_json(log_event.model_dump(mode="json"))
