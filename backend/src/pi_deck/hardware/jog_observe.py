"""Digital observation of conditioned KEY_ADC1 (gpiozero — same pin factory as JogDrive)."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable

from gpiozero import DigitalInputDevice

from pi_deck.hardware.protoboard_pins import ProtoboardPins

logger = logging.getLogger(__name__)


class KeyAdc1Observe:
    """KEY_ADC1: gpiozero ``DigitalInputDevice`` for levels + optional edge callbacks.

    The conditioned protoboard path is **idle-high / pressed-low** at the Pi pin:
    idle reads ~3.3 V, center assert reads ~0 V.
    """

    def __init__(self, pins: ProtoboardPins | None = None, *, pull_up: bool | None = None) -> None:
        self._pins = pins or ProtoboardPins()
        self._bcm = self._pins.key_adc1_digital
        self._pull_up = pull_up if pull_up is not None else True
        self._edge_cb: Callable[[], None] | None = None
        # Keep gpiozero in raw input mode here; the wrapper inverts the idle-high/pressed-low
        # conditioned signal into the project-level "pressed == active" meaning.
        self._dev = DigitalInputDevice(
            self._bcm,
            pull_up=self._pull_up,
            active_state=None,
            bounce_time=0.025,
        )

    @property
    def is_active(self) -> bool:
        return not bool(self._dev.value)

    def enable_edge_detect(self, on_edge: Callable[[], None], *, _bouncetime_ms: int = 25) -> bool:
        """Fire ``on_edge`` on both edges (gpiozero helper thread → keep callback tiny)."""
        if sys.platform != "linux":
            return False
        self.disable_edge_detect()
        self._edge_cb = on_edge

        def _fire() -> None:
            if self._edge_cb is not None:
                self._edge_cb()

        try:
            self._dev.when_activated = _fire
            self._dev.when_deactivated = _fire
        except Exception as e:
            self._edge_cb = None
            logger.warning(
                "KEY_ADC1 BCM %s: gpiozero edge hooks failed (%s); telemetry uses asyncio poll only",
                self._bcm,
                e,
            )
            return False
        return True

    def disable_edge_detect(self) -> None:
        self._edge_cb = None
        self._dev.when_activated = None
        self._dev.when_deactivated = None

    def close(self) -> None:
        self.disable_edge_detect()
        self._dev.close()
