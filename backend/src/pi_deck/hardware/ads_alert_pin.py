"""ADS1115 ALERT/RDY as a gpiozero digital input (IRQ-style edges via lgpio / rpigpio factory)."""

from __future__ import annotations

import logging
from collections.abc import Callable

from gpiozero import DigitalInputDevice

logger = logging.getLogger(__name__)


class AdsAlertPin:
    """Open-drain ALERT/RDY (active low with pull-up). Edges schedule observation via gpiozero."""

    def __init__(self, bcm: int) -> None:
        self._bcm = bcm
        self._edge_cb: Callable[[], None] | None = None
        self._dev = DigitalInputDevice(
            bcm,
            pull_up=True,
            active_state=None,
            bounce_time=0.001,
        )

    def enable_edge_detect(self, on_edge: Callable[[], None]) -> bool:
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
                "ADS ALERT BCM %s: gpiozero edge hooks failed (%s); KEY_ADC2 path uses asyncio poll only",
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
