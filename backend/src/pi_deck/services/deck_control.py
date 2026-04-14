"""Command arbitration and jog orchestration (API and websocket notifications)."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import Counter
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
    ws_command_accepted,
    ws_command_hold_started,
    ws_command_rejected,
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

_MAX_HOLD_S = 60.0
_MAX_CONCURRENT_HOLDS = 32


@dataclass
class HoldRecord:
    action: JogAction
    start_monotonic: float
    watchdog: asyncio.Task[None] | None = None


@dataclass
class DeckControlService:
    """Jog orchestration: multitouch / multicommand via refcounted GPIO lines + hold tokens."""

    hardware: DeckHardwareFacade
    ws_hub: WsHub
    version: str
    _operating_mode: OperatingMode = OperatingMode.JOG
    _control_state: ControlState = ControlState.IDLE
    _holds: dict[str, HoldRecord] = field(default_factory=dict)
    _refcount: Counter[JogAction] = field(default_factory=Counter)
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
        return len(self._holds) > 0

    def _cancel_watchdog(self, rec: HoldRecord) -> None:
        if rec.watchdog is not None:
            rec.watchdog.cancel()
            rec.watchdog = None

    def _schedule_watchdog(self, token: str) -> None:
        deck = self

        async def _run() -> None:
            try:
                await asyncio.sleep(_MAX_HOLD_S)
                err, _ms = await deck.jog_up(token)
                if err is not None:
                    logger.warning("watchdog jog_up token=%s: %s", token, err)
            except asyncio.CancelledError:
                pass

        rec = self._holds.get(token)
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

    async def jog_down(self, action: str) -> tuple[CommandRejectedReason | None, str | None]:
        """Begin one hold; returns ``(error, hold_token)``."""
        if len(self._holds) >= _MAX_CONCURRENT_HOLDS:
            await self._emit(
                ws_command_rejected(
                    reason=CommandRejectedReason.HOLD_LIMIT,
                    message="Too many simultaneous jog holds",
                ),
            )
            return CommandRejectedReason.HOLD_LIMIT, None

        jog = _ACTION_MAP.get(action)
        if jog is None:
            return CommandRejectedReason.HARDWARE_ERROR, None

        prev = self._refcount[jog]
        if jog is JogAction.CENTER and prev == 0:
            if not await asyncio.to_thread(self.hardware.adc1_physical_idle):
                msg = "KEY_ADC1 observation reports activity; refusing center command"
                await self._emit(
                    ws_command_rejected(reason=CommandRejectedReason.BUS_BUSY, message=msg),
                )
                return CommandRejectedReason.BUS_BUSY, None

        token = str(uuid.uuid4())
        self._refcount[jog] += 1
        if prev == 0:
            try:
                await asyncio.to_thread(self.hardware.set_jog_line, jog, True)
            except Exception:
                logger.exception("set_jog_line on failed")
                self._refcount[jog] -= 1
                if self._refcount[jog] <= 0:
                    del self._refcount[jog]
                msg = "Hardware failure while asserting jog line"
                await self._emit(
                    ws_command_rejected(
                        reason=CommandRejectedReason.HARDWARE_ERROR,
                        message=msg,
                    ),
                )
                return CommandRejectedReason.HARDWARE_ERROR, None

        now = time.monotonic()
        self._holds[token] = HoldRecord(action=jog, start_monotonic=now)
        await self._emit(ws_command_hold_started(action=action, hold_token=token))
        await self._emit_control_if_needed()
        adc1, led = self.hardware.read_signals()
        await self._emit(ws_bus_snapshot(signals=SignalSnapshot(key_adc1_active=adc1, key_led_active=led)))
        self._schedule_watchdog(token)
        return None, token

    async def jog_up(self, hold_token: str) -> tuple[CommandRejectedReason | None, int]:
        """Release one hold by token. Returns ``(error, duration_ms)``."""
        rec = self._holds.pop(hold_token, None)
        if rec is None:
            await self._emit(
                ws_command_rejected(
                    reason=CommandRejectedReason.UNKNOWN_HOLD_TOKEN,
                    message="Unknown or expired hold_token",
                ),
            )
            return CommandRejectedReason.UNKNOWN_HOLD_TOKEN, 0

        self._cancel_watchdog(rec)
        jog = rec.action
        duration_ms = int((time.monotonic() - rec.start_monotonic) * 1000)
        duration_ms = max(0, min(duration_ms, 60_000))

        self._refcount[jog] -= 1
        if self._refcount[jog] <= 0:
            del self._refcount[jog]
            try:
                await asyncio.to_thread(self.hardware.set_jog_line, jog, False)
            except Exception:
                logger.exception("set_jog_line off failed")
                await self._emit_control_if_needed()
                return CommandRejectedReason.HARDWARE_ERROR, 0

        action_str = next(k for k, v in _ACTION_MAP.items() if v == jog)
        await self._emit(
            ws_command_accepted(action=action_str, duration_ms=duration_ms, hold_token=hold_token),
        )
        adc1, led = self.hardware.read_signals()
        await self._emit(ws_bus_snapshot(signals=SignalSnapshot(key_adc1_active=adc1, key_led_active=led)))
        await self._emit_control_if_needed()
        return None, duration_ms

    async def jog_press(self, action: str, duration_ms: int) -> None | CommandRejectedReason:
        """Legacy timed pulse — not allowed while multitouch holds are active."""
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
                if jog is JogAction.CENTER:
                    if not await asyncio.to_thread(self.hardware.adc1_physical_idle):
                        msg = "KEY_ADC1 observation reports activity; refusing center command"
                        await self._emit(
                            ws_command_rejected(reason=CommandRejectedReason.BUS_BUSY, message=msg),
                        )
                        return CommandRejectedReason.BUS_BUSY

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

                await self._emit(
                    ws_command_accepted(action=action, duration_ms=duration_ms, hold_token="pulse"),
                )
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
