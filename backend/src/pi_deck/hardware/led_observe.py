"""Digital observation of conditioned KEY_LED."""

from __future__ import annotations

from collections.abc import Callable

from pi_deck.hardware.protoboard_pins import ProtoboardPins


def _rpi_gpio():
    import RPi.GPIO as GPIO  # noqa: N814

    return GPIO


class KeyLedObserve:
    """KEY_LED via RPi.GPIO: level read for snapshots; optional BOTH-edge detect for telemetry."""

    def __init__(self, pins: ProtoboardPins | None = None, *, pull_up: bool | None = None) -> None:
        self._pins = pins or ProtoboardPins()
        self._bcm = self._pins.key_led_digital
        self._edge_cb: Callable[[], None] | None = None
        GPIO = _rpi_gpio()
        GPIO.setmode(GPIO.BCM)
        pud = GPIO.PUD_UP if (pull_up if pull_up is not None else True) else GPIO.PUD_DOWN
        GPIO.setup(self._bcm, GPIO.IN, pull_up_down=pud)

    @property
    def is_active(self) -> bool:
        GPIO = _rpi_gpio()
        return GPIO.input(self._bcm) == GPIO.LOW

    def enable_edge_detect(self, on_edge: Callable[[], None], *, bouncetime_ms: int = 25) -> None:
        """Register BOTH-edge detection; ``on_edge`` runs on RPi.GPIO's helper thread — keep it tiny."""
        import sys

        if sys.platform != "linux":
            return
        self.disable_edge_detect()
        self._edge_cb = on_edge
        GPIO = _rpi_gpio()

        def _wrapped(_ch: int) -> None:
            if self._edge_cb is not None:
                self._edge_cb()

        GPIO.add_event_detect(self._bcm, GPIO.BOTH, callback=_wrapped, bouncetime=bouncetime_ms)

    def disable_edge_detect(self) -> None:
        import sys

        if sys.platform != "linux":
            return
        self._edge_cb = None
        try:
            GPIO = _rpi_gpio()
            GPIO.remove_event_detect(self._bcm)
        except Exception:
            pass

    def close(self) -> None:
        self.disable_edge_detect()
