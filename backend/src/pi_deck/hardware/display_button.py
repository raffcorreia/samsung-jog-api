"""Physical display toggle button — SW1, GPIO4, active-low.

Wiring: +3V3 ── R25 (10 kΩ) ── GPIO4 ── SW1 ── GND
                                   │
                              C5 (100 nF) ── GND

Behaviour:
  on_press        — fires immediately on button-down
  on_hold         — fires at exactly 3 s while still held
  on_short_press  — fires on release when held < 3 s
  on_release_any  — fires on release regardless (after on_short_press when applicable)
"""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable

from pi_deck.hardware.protoboard_pins import ProtoboardPins

logger = logging.getLogger(__name__)

_HOLD_SECONDS = 3.0


class DisplayButton:
    """SW1 momentary button on GPIO4 (active-low; R25 hardware pull-up, C5 debounce cap)."""

    def __init__(self, pins: ProtoboardPins | None = None) -> None:
        self._bcm = (pins or ProtoboardPins()).display_btn
        self._dev = None
        self._hold_timer: threading.Timer | None = None
        self._hold_fired = False
        if sys.platform != "linux":
            logger.info("display-btn: not on Linux — button disabled (mock)")
            return
        try:
            from gpiozero import DigitalInputDevice  # noqa: PLC0415
            self._dev = DigitalInputDevice(
                self._bcm,
                pull_up=True,
                active_state=None,
                bounce_time=0.05,
            )
            logger.info("display-btn: SW1 ready on BCM %d (GPIO4)", self._bcm)
        except Exception as exc:
            logger.warning("display-btn: GPIO init failed (%s) — button disabled", exc)

    def set_callback(
        self,
        on_short_press: Callable[[], None],
        on_hold: Callable[[], None],
        *,
        on_press: Callable[[], None] | None = None,
        on_release_any: Callable[[], None] | None = None,
    ) -> None:
        """Register callbacks (all run in the gpiozero helper thread).

        on_press        — button went down
        on_hold         — button held for 3 s (before release)
        on_short_press  — button released before 3 s
        on_release_any  — button released (fires after on_short_press when applicable)
        """
        if self._dev is None:
            return

        def _hold_tick() -> None:
            self._hold_fired = True
            self._hold_timer = None
            try:
                on_hold()
            except Exception:
                logger.exception("display-btn: on_hold raised")

        def _pressed() -> None:
            logger.debug("display-btn: pressed")
            try:
                if on_press:
                    on_press()
            except Exception:
                logger.exception("display-btn: on_press raised")
            self._hold_fired = False
            timer = threading.Timer(_HOLD_SECONDS, _hold_tick)
            self._hold_timer = timer
            timer.start()

        def _released() -> None:
            logger.debug("display-btn: released")
            timer = self._hold_timer
            if timer is not None:
                timer.cancel()
                self._hold_timer = None
            try:
                if not self._hold_fired:
                    on_short_press()
            except Exception:
                logger.exception("display-btn: on_short_press raised")
            finally:
                try:
                    if on_release_any:
                        on_release_any()
                except Exception:
                    logger.exception("display-btn: on_release_any raised")

        self._dev.when_activated = _pressed
        self._dev.when_deactivated = _released

    def close(self) -> None:
        timer = self._hold_timer
        if timer is not None:
            timer.cancel()
            self._hold_timer = None
        if self._dev is not None:
            self._dev.when_activated = None
            self._dev.when_deactivated = None
            self._dev.close()
            self._dev = None
