"""ADS1115 ALERT/RDY using raw ``RPi.GPIO.add_event_detect`` (RISING, pull-down).

Use when you want the classic interrupt pattern::

    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(pin, GPIO.RISING, callback=...)

``ObservationBusService`` wires ``callback`` → ``run_coroutine_threadsafe`` like gpiozero mode.

Enable with ``PI_DECK_ADS_ALERT_BACKEND=rpi`` (see ``hardware_facade``). That forces
``GPIOZERO_PIN_FACTORY=rpigpio`` so JogDrive / KEY lines share the same RPi.GPIO stack as this pin.
Do **not** mix with ``lgpio`` for gpiozero on the same process — pick one stack.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


def _rpi_gpio():
    import RPi.GPIO as GPIO  # noqa: N814

    return GPIO


class AdsAlertPinRpi:
    """BCM input + RISING edge via RPi.GPIO (matches common bare-metal ALERT demos)."""

    def __init__(self, bcm: int) -> None:
        self._bcm = bcm
        self._edge_cb: Callable[[], None] | None = None

    def enable_edge_detect(self, on_edge: Callable[[], None], *, bouncetime_ms: int = 20) -> bool:
        self.disable_edge_detect()
        self._edge_cb = on_edge
        GPIO = _rpi_gpio()
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._bcm, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

            def _cb(channel: int) -> None:
                if self._edge_cb is not None:
                    self._edge_cb()

            GPIO.add_event_detect(
                self._bcm,
                GPIO.RISING,
                callback=_cb,
                bouncetime=bouncetime_ms,
            )
        except Exception as e:
            self._edge_cb = None
            logger.warning(
                "ADS ALERT BCM %s: RPi.GPIO add_event_detect failed (%s)",
                self._bcm,
                e,
            )
            return False
        return True

    def disable_edge_detect(self) -> None:
        self._edge_cb = None
        try:
            GPIO = _rpi_gpio()
            GPIO.remove_event_detect(self._bcm)
        except Exception:
            pass

    def close(self) -> None:
        self.disable_edge_detect()
