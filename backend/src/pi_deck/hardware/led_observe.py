"""Digital observation of conditioned KEY_LED (gpiozero — same pin factory as JogDrive)."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable

from gpiozero import DigitalInputDevice

from pi_deck.hardware.protoboard_pins import ProtoboardPins

logger = logging.getLogger(__name__)


class KeyLedObserve:
    """KEY_LED: gpiozero ``DigitalInputDevice``; **active-low** at the pin matches Phase 6 wiring."""

    def __init__(self, pins: ProtoboardPins | None = None, *, pull_up: bool | None = None) -> None:
        self._pins = pins or ProtoboardPins()
        self._bcm = self._pins.key_led_digital
        self._pull_up = pull_up if pull_up is not None else True
        self._edge_cb: Callable[[], None] | None = None
        self._state_cb: Callable[[bool], None] | None = None
        self._dev = DigitalInputDevice(
            self._bcm,
            pull_up=self._pull_up,
            active_state=None,
            bounce_time=None,  # electronic signal — no mechanical bounce
        )

    @property
    def is_active(self) -> bool:
        return self._dev.is_active

    def enable_edge_detect(self, on_edge: Callable[[], None]) -> bool:
        """Register a generic edge callback (called on both activate and deactivate).

        Safe to call while a state callback is already installed — both are chained.
        """
        if sys.platform != "linux":
            return False
        self._edge_cb = on_edge
        self._install_hooks()
        return True

    def set_state_callback(self, fn: Callable[[bool], None] | None) -> None:
        """Register a direct state callback: True on activate, False on deactivate.

        Called from the gpiozero background thread — no asyncio, no CoalesceGate.
        Pass None to unregister.
        """
        self._state_cb = fn
        self._install_hooks()

    def disable_edge_detect(self) -> None:
        self._edge_cb = None
        self._install_hooks()

    def close(self) -> None:
        self._edge_cb = None
        self._state_cb = None
        self._dev.when_activated = None
        self._dev.when_deactivated = None
        self._dev.close()

    # ── internals ─────────────────────────────────────────────────────────────

    def _install_hooks(self) -> None:
        """Rebuild when_activated / when_deactivated to chain both callbacks."""
        edge_cb = self._edge_cb
        state_cb = self._state_cb

        if edge_cb is None and state_cb is None:
            self._dev.when_activated = None
            self._dev.when_deactivated = None
            return

        def _on_active() -> None:
            if edge_cb is not None:
                edge_cb()
            if state_cb is not None:
                state_cb(True)

        def _on_inactive() -> None:
            if edge_cb is not None:
                edge_cb()
            if state_cb is not None:
                state_cb(False)

        self._dev.when_activated = _on_active
        self._dev.when_deactivated = _on_inactive
