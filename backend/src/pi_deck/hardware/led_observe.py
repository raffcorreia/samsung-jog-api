"""Digital observation of conditioned KEY_LED."""

from __future__ import annotations

from pi_deck.hardware.protoboard_pins import ProtoboardPins


def _rpi_gpio():
    import RPi.GPIO as GPIO  # noqa: N814

    return GPIO


class KeyLedObserve:
    """Poll KEY_LED via RPi.GPIO (no edge interrupts)."""

    def __init__(self, pins: ProtoboardPins | None = None, *, pull_up: bool | None = None) -> None:
        self._pins = pins or ProtoboardPins()
        self._bcm = self._pins.key_led_digital
        GPIO = _rpi_gpio()
        GPIO.setmode(GPIO.BCM)
        pud = GPIO.PUD_UP if (pull_up if pull_up is not None else True) else GPIO.PUD_DOWN
        GPIO.setup(self._bcm, GPIO.IN, pull_up_down=pud)

    @property
    def is_active(self) -> bool:
        GPIO = _rpi_gpio()
        return GPIO.input(self._bcm) == GPIO.LOW

    def close(self) -> None:
        pass
