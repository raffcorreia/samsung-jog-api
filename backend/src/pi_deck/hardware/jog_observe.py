"""Digital observation of conditioned KEY_ADC1."""

from __future__ import annotations

from pi_deck.hardware.protoboard_pins import ProtoboardPins


def _rpi_gpio():
    import RPi.GPIO as GPIO  # noqa: N814 — conventional name

    return GPIO


class KeyAdc1Observe:
    """Poll KEY_ADC1 with RPi.GPIO (no edge IRQs; stable on Pi 2 / older stacks)."""

    def __init__(self, pins: ProtoboardPins | None = None, *, pull_up: bool | None = None) -> None:
        self._pins = pins or ProtoboardPins()
        self._bcm = self._pins.key_adc1_digital
        GPIO = _rpi_gpio()
        GPIO.setmode(GPIO.BCM)
        pud = GPIO.PUD_UP if (pull_up if pull_up is not None else True) else GPIO.PUD_DOWN
        GPIO.setup(self._bcm, GPIO.IN, pull_up_down=pud)

    @property
    def is_active(self) -> bool:
        GPIO = _rpi_gpio()
        return GPIO.input(self._bcm) == GPIO.LOW

    def close(self) -> None:
        # JogDrive (gpiozero) still owns other BCM lines; do not GPIO.cleanup() the whole chip here.
        pass
