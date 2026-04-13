"""ADS1115 ALERT/RDY line (BCM pin from ProtoboardPins)."""

from __future__ import annotations

from gpiozero import DigitalInputDevice

from pi_deck.hardware.protoboard_pins import ProtoboardPins


class AdsAlertObserve:
    """Conversion-ready output from ADS1115 (polarity depends on wiring)."""

    def __init__(self, pins: ProtoboardPins | None = None, *, pull_up: bool | None = None) -> None:
        self._pins = pins or ProtoboardPins()
        self._inp = DigitalInputDevice(
            self._pins.ads_alert,
            pull_up=pull_up if pull_up is not None else True,
        )

    @property
    def is_active(self) -> bool:
        return bool(self._inp.is_active)

    def close(self) -> None:
        self._inp.close()
