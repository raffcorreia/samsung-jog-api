"""Command arbitration and jog orchestration (API and websocket notifications)."""

from __future__ import annotations

import asyncio
import logging
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


@dataclass
class DeckControlService:
    """Serialized jog commands with best-effort physical bus checks."""

    hardware: DeckHardwareFacade
    ws_hub: WsHub
    version: str
    _idle: asyncio.Event = field(default_factory=asyncio.Event)
    _operating_mode: OperatingMode = OperatingMode.JOG
    _control_state: ControlState = ControlState.IDLE

    def __post_init__(self) -> None:
        self._idle.set()

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

    async def jog_press(self, action: str, duration_ms: int) -> None | CommandRejectedReason:
        """Execute one timed jog assertion. Returns ``None`` on success or a rejection reason."""
        if not self._idle.is_set():
            await self._emit(
                ws_command_rejected(
                    reason=CommandRejectedReason.CONCURRENT_COMMAND,
                    message="Another jog command is in progress",
                )
            )
            return CommandRejectedReason.CONCURRENT_COMMAND

        jog = _ACTION_MAP.get(action)
        if jog is None:
            return CommandRejectedReason.HARDWARE_ERROR

        duration_s = duration_ms / 1000.0
        if duration_s <= 0:
            return CommandRejectedReason.INVALID_DURATION

        self._idle.clear()
        self._control_state = ControlState.COMMANDING
        await self._emit(
            ws_control_state(control_state=self._control_state, operating_mode=self._operating_mode)
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
                    )
                )
                return CommandRejectedReason.HARDWARE_ERROR

            await self._emit(ws_command_accepted(action=action, duration_ms=duration_ms))
            adc1, led = self.hardware.read_signals()
            snap = SignalSnapshot(key_adc1_active=adc1, key_led_active=led)
            await self._emit(ws_bus_snapshot(signals=snap))
            return None
        finally:
            self._control_state = ControlState.IDLE
            self._idle.set()
            await self._emit(
                ws_control_state(
                    control_state=self._control_state,
                    operating_mode=self._operating_mode,
                ),
            )

    async def _emit(self, event: object) -> None:
        if self.ws_hub.client_count == 0:
            return
        payload = (
            event.model_dump(mode="json") if hasattr(event, "model_dump") else event  # type: ignore[assignment]
        )
        if not isinstance(payload, dict):
            return
        await self.ws_hub.broadcast_json(payload)
