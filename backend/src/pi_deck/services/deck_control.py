"""Command arbitration and jog orchestration (API and websocket notifications)."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Literal, cast

from pi_deck.hardware.protoboard_pins import JogAction
from pi_deck.models.schemas import (
    CommandRejectedReason,
    ControlState,
    OperatingMode,
    SignalSnapshot,
    StatusOut,
    ws_bus_snapshot,
    ws_command_held,
    ws_command_pulse,
    ws_command_rejected,
    ws_command_released,
    ws_control_state,
)
from pi_deck.services.hardware_facade import DeckHardwareFacade
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


@dataclass
class HoldRecord:
    start_monotonic: float
    watchdog: asyncio.Task[None] | None = None


@dataclass
class DeckControlService:
    """Jog orchestration: one authoritative hold per direction; new hold replaces prior on same line."""

    hardware: DeckHardwareFacade
    ws_hub: WsHub
    version: str
    _operating_mode: OperatingMode = OperatingMode.JOG
    _control_state: ControlState = ControlState.IDLE
    _hold: dict[JogAction, HoldRecord] = field(default_factory=dict)
    _pulse_in_progress: bool = field(default=False, repr=False)

    def status(self) -> StatusOut:
        adc1, led = self.hardware.read_signals()
        return StatusOut(
            version=self.version,
            hardware=cast(Literal["live", "mock"], self.hardware.kind),
            operating_mode=self._operating_mode,
            control_state=self._control_state,
            signals=SignalSnapshot(key_adc1_active=adc1, key_led_active=led),
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

    async def _emit_control_if_needed(self) -> None:
        want = ControlState.COMMANDING if self._any_holds() else ControlState.IDLE
        if want != self._control_state:
            self._control_state = want
            await self._emit(
                ws_control_state(control_state=self._control_state, operating_mode=self._operating_mode),
            )

    async def jog_hold(self, action: str) -> CommandRejectedReason | None:
        """Assert ``action``; replaces any existing hold on the same direction (GPIO unchanged if already held)."""
        jog = _ACTION_MAP.get(action)
        if jog is None:
            return CommandRejectedReason.HARDWARE_ERROR

        # Replace same direction: end previous logically; keep line high (no GPIO glitch).
        if jog in self._hold:
            prev = self._hold[jog]
            self._cancel_watchdog(prev)
            duration_ms = int((time.monotonic() - prev.start_monotonic) * 1000)
            duration_ms = max(0, min(duration_ms, 60_000))
            await self._emit(ws_command_released(action=action, duration_ms=duration_ms))
            now = time.monotonic()
            self._hold[jog] = HoldRecord(start_monotonic=now)
            self._schedule_watchdog(jog)
            await self._emit(ws_command_held(action=action))
            adc1, led = self.hardware.read_signals()
            await self._emit(ws_bus_snapshot(signals=SignalSnapshot(key_adc1_active=adc1, key_led_active=led)))
            await self._emit_control_if_needed()
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
        await self._emit(ws_command_held(action=action))
        self._schedule_watchdog(jog)
        await self._emit_control_if_needed()
        adc1, led = self.hardware.read_signals()
        await self._emit(ws_bus_snapshot(signals=SignalSnapshot(key_adc1_active=adc1, key_led_active=led)))
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
            await self._emit_control_if_needed()
            return CommandRejectedReason.HARDWARE_ERROR, 0

        await self._emit(ws_command_released(action=action, duration_ms=duration_ms))
        adc1, led = self.hardware.read_signals()
        await self._emit(ws_bus_snapshot(signals=SignalSnapshot(key_adc1_active=adc1, key_led_active=led)))
        await self._emit_control_if_needed()
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

        if self._pulse_in_progress:
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
            await self._emit(
                ws_control_state(control_state=self._control_state, operating_mode=self._operating_mode),
            )
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

                await self._emit(ws_command_pulse(action=action, duration_ms=duration_ms))
                adc1, led = self.hardware.read_signals()
                snap = SignalSnapshot(key_adc1_active=adc1, key_led_active=led)
                await self._emit(ws_bus_snapshot(signals=snap))
                return None
            finally:
                self._control_state = ControlState.IDLE
                await self._emit(
                    ws_control_state(
                        control_state=self._control_state,
                        operating_mode=self._operating_mode,
                    ),
                )
        finally:
            self._pulse_in_progress = False

    async def _emit(self, event: object) -> None:
        if self.ws_hub.client_count == 0:
            return
        payload = (
            event.model_dump(mode="json") if hasattr(event, "model_dump") else event  # type: ignore[assignment]
        )
        if not isinstance(payload, dict):
            return
        await self.ws_hub.broadcast_json(payload)
