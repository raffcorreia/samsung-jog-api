"""Digital observation of conditioned KEY_LED (gpiozero — same pin factory as JogDrive)."""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Callable

from gpiozero import DigitalInputDevice

from pi_deck.hardware.protoboard_pins import ProtoboardPins

logger = logging.getLogger(__name__)

class KeyLedObserve:
    """KEY_LED gpiozero input; active-low at the pin matches the Phase 6 wiring."""

    def __init__(self, pins: ProtoboardPins | None = None, *, pull_up: bool | None = None) -> None:
        self._pins = pins or ProtoboardPins()
        self._bcm = self._pins.key_led_digital
        self._pull_up = pull_up if pull_up is not None else True
        self._edge_cb: Callable[[], None] | None = None
        self._state_cb: Callable[[bool], None] | None = None
        self._raw_edge_cb: Callable[[int, int], None] | None = None
        self._last_level: int | None = None
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

    def set_raw_edge_callback(self, fn: Callable[[int, int], None] | None) -> None:
        """Register physical-level edge capture as ``(level, monotonic_ns)``.

        The current conditioned input is active-low, so gpiozero activation is physical level 0
        and deactivation is physical level 1.  This path deliberately does not rewrite levels as
        semantic LED on/off state.
        """
        self._raw_edge_cb = fn
        self._install_hooks()

    def disable_edge_detect(self) -> None:
        self._edge_cb = None
        self._install_hooks()

    def close(self) -> None:
        self._edge_cb = None
        self._state_cb = None
        self._raw_edge_cb = None
        self._dev.when_activated = None
        self._dev.when_deactivated = None
        self._dev.close()

    # ── internals ─────────────────────────────────────────────────────────────

    def _install_hooks(self) -> None:
        """Rebuild when_activated / when_deactivated to chain both callbacks."""
        edge_cb = self._edge_cb
        state_cb = self._state_cb
        raw_edge_cb = self._raw_edge_cb

        if edge_cb is None and state_cb is None and raw_edge_cb is None:
            self._dev.when_activated = None
            self._dev.when_deactivated = None
            return

        def _on_active() -> None:
            self._dispatch_level(0, time.monotonic_ns())

        def _on_inactive() -> None:
            self._dispatch_level(1, time.monotonic_ns())

        self._dev.when_activated = _on_active
        self._dev.when_deactivated = _on_inactive

    def _dispatch_level(self, level: int, timestamp_ns: int) -> None:
        """Fan out one physical transition without letting one consumer block the others."""
        if level == self._last_level:
            return
        self._last_level = level
        edge_cb = self._edge_cb
        state_cb = self._state_cb
        raw_edge_cb = self._raw_edge_cb

        # Preserve the pre-Phase-25 semantic consumers first. Raw communication capture is an
        # additional observer and must never prevent ordinary LED status from being delivered.
        if edge_cb is not None:
            try:
                edge_cb()
            except Exception:
                logger.exception("KEY_LED generic edge callback failed")
        if state_cb is not None:
            try:
                state_cb(level == 0)
            except Exception:
                logger.exception("KEY_LED state callback failed")
        if raw_edge_cb is not None:
            try:
                raw_edge_cb(level, timestamp_ns)
            except Exception:
                logger.exception("KEY_LED raw capture callback failed")
