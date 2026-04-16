"""Hardware access for the deck control service: live GPIO path vs test mock."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from pi_deck.hardware.ads1115 import Ads1115
from pi_deck.hardware.ads_alert_pin import AdsAlertPin
from pi_deck.hardware.jog_drive import JogDrive
from pi_deck.hardware.jog_observe import KeyAdc1Observe
from pi_deck.hardware.key_adc2_decode import decode_key_adc2_direction
from pi_deck.hardware.led_observe import KeyLedObserve
from pi_deck.hardware.protoboard_pins import JogAction, ProtoboardPins
from pi_deck.models.schemas import SignalSnapshot

logger = logging.getLogger(__name__)


@runtime_checkable
class DeckHardwareFacade(Protocol):
    """Abstracts jog drive and observation for arbitration and status."""

    @property
    def kind(self) -> str:
        """``live`` or ``mock``."""

    def pulse(self, action: JogAction, duration_s: float) -> None:
        """Assert ``action`` for ``duration_s`` seconds, then release all lines (exclusive)."""

    def set_jog_line(self, action: JogAction, active: bool) -> None:
        """Drive one jog line high/low without clearing other lines (multicommand)."""

    def read_bus_snapshot(self) -> SignalSnapshot:
        """Observed KEY_ADC1, KEY_ADC2 (decoded), KEY_LED — single source for telemetry and REST."""

    def close(self) -> None:
        """Release host resources (GPIO, etc.)."""


class LiveDeckHardware:
    """Protoboard GPIO stack (Phase 6 map)."""

    def __init__(self, pins: ProtoboardPins | None = None) -> None:
        self._pins = pins or ProtoboardPins()
        self._drive = JogDrive(self._pins)
        self._adc1 = KeyAdc1Observe(self._pins)
        self._led = KeyLedObserve(self._pins)
        self._ads_alert = AdsAlertPin(self._pins.ads_alert)
        self._ads: Ads1115 | None = None
        try:
            ads = Ads1115()
            ads.start_continuous_ain0_rdy()
            self._ads = ads
        except Exception:
            logger.exception("live hardware: ADS1115 init failed; KEY_ADC2 decode unavailable")

    @property
    def pins(self) -> ProtoboardPins:
        return self._pins

    @property
    def adc1_observer(self) -> KeyAdc1Observe:
        return self._adc1

    @property
    def led_observer(self) -> KeyLedObserve:
        return self._led

    @property
    def ads_alert_pin(self) -> AdsAlertPin:
        return self._ads_alert

    @property
    def kind(self) -> str:
        return "live"

    def pulse(self, action: JogAction, duration_s: float) -> None:
        self._drive.pulse(action, duration_s)

    def set_jog_line(self, action: JogAction, active: bool) -> None:
        self._drive.set_line(action, active)

    def read_bus_snapshot(self) -> SignalSnapshot:
        adc1 = self._adc1.is_active
        led = self._led.is_active
        d2 = None
        if self._ads is not None:
            try:
                mv = self._ads.read_conversion_mv()
                d2 = decode_key_adc2_direction(mv)
            except Exception:
                logger.exception("read_bus_snapshot: ADS read/decode failed")
        return SignalSnapshot(key_adc1_active=adc1, key_led_active=led, key_adc2_direction=d2)

    def close(self) -> None:
        self._drive.close()
        self._adc1.close()
        self._led.close()
        self._ads_alert.close()
        if self._ads is not None:
            try:
                self._ads.close()
            except Exception:
                logger.debug("live hardware: ads close failed", exc_info=True)
            self._ads = None


class MockDeckHardware:
    """No GPIO; used for pytest and dev hosts without the protoboard."""

    def __init__(self) -> None:
        self._led_active = False
        self._lines_on: set[JogAction] = set()
        self._change_notifier: Callable[[], None] | None = None

    @property
    def kind(self) -> str:
        return "mock"

    @property
    def active_drive_lines(self) -> set[JogAction]:
        return set(self._lines_on)

    def set_change_notifier(self, fn: Callable[[], None] | None) -> None:
        self._change_notifier = fn

    def _notify_change(self) -> None:
        if self._change_notifier is not None:
            self._change_notifier()

    def pulse(self, action: JogAction, duration_s: float) -> None:
        logger.debug("mock pulse %s %.4fs", action.value, duration_s)
        self.set_jog_line(action, True)
        time.sleep(duration_s)
        self.set_jog_line(action, False)

    def set_jog_line(self, action: JogAction, active: bool) -> None:
        if active:
            self._lines_on.add(action)
        else:
            self._lines_on.discard(action)
        logger.debug("mock set_jog_line %s %s", action.value, active)
        self._notify_change()

    def read_bus_snapshot(self) -> SignalSnapshot:
        adc1 = JogAction.CENTER in self._lines_on
        led = self._led_active
        d2 = None
        for ja in (JogAction.UP, JogAction.DOWN, JogAction.LEFT, JogAction.RIGHT):
            if ja in self._lines_on:
                d2 = ja.value
                break
        return SignalSnapshot(key_adc1_active=adc1, key_led_active=led, key_adc2_direction=d2)

    def close(self) -> None:
        pass


def _gpiozero_pin_factory_for_live() -> None:
    """Select gpiozero pin factory before any ``OutputDevice`` / ``DigitalInputDevice``.

    Prefer **lgpio** (Pi 5 / Bookworm) so edge IRQs work for inputs + outputs; fall back to **rpigpio**
    (RPi.GPIO) on older images. Override with ``GPIOZERO_PIN_FACTORY`` if needed.
    """
    import os

    if os.environ.get("GPIOZERO_PIN_FACTORY"):
        return
    try:
        import lgpio  # noqa: F401

        os.environ["GPIOZERO_PIN_FACTORY"] = "lgpio"
    except ImportError:
        os.environ.setdefault("GPIOZERO_PIN_FACTORY", "rpigpio")


def build_hardware() -> DeckHardwareFacade:
    """Select hardware from ``PI_DECK_HARDWARE``: ``mock`` | ``live``.

    Default when unset is ``mock`` (safe for dev machines without GPIO). Production systemd units
    should set ``PI_DECK_HARDWARE=live`` for real GPIO.
    """
    import os

    mode = (os.environ.get("PI_DECK_HARDWARE") or "mock").strip().lower()
    if mode == "mock":
        return MockDeckHardware()
    if mode == "live":
        _gpiozero_pin_factory_for_live()
        return LiveDeckHardware()
    raise ValueError(f"PI_DECK_HARDWARE must be 'mock' or 'live', got {mode!r}")
