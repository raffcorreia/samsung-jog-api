"""Hardware access for the deck control service: live GPIO path vs test mock."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from pi_deck.hardware.jog_drive import JogDrive
from pi_deck.hardware.jog_observe import KeyAdc1Observe
from pi_deck.hardware.led_observe import KeyLedObserve
from pi_deck.hardware.protoboard_pins import JogAction, ProtoboardPins

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

    def read_signals(self) -> tuple[bool, bool]:
        """Return ``(key_adc1_active, key_led_active)`` for status and websocket snapshots."""

    def close(self) -> None:
        """Release host resources (GPIO, etc.)."""


class LiveDeckHardware:
    """Protoboard GPIO stack (Phase 6 map)."""

    def __init__(self, pins: ProtoboardPins | None = None) -> None:
        self._pins = pins or ProtoboardPins()
        self._drive = JogDrive(self._pins)
        self._adc1 = KeyAdc1Observe(self._pins)
        self._led = KeyLedObserve(self._pins)

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
    def kind(self) -> str:
        return "live"

    def pulse(self, action: JogAction, duration_s: float) -> None:
        self._drive.pulse(action, duration_s)

    def set_jog_line(self, action: JogAction, active: bool) -> None:
        self._drive.set_line(action, active)

    def read_signals(self) -> tuple[bool, bool]:
        return (self._adc1.is_active, self._led.is_active)

    def close(self) -> None:
        self._drive.close()
        self._adc1.close()
        self._led.close()


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

    def set_jog_line(self, action: JogAction, active: bool) -> None:
        if active:
            self._lines_on.add(action)
        else:
            self._lines_on.discard(action)
        logger.debug("mock set_jog_line %s %s", action.value, active)
        self._notify_change()

    def read_signals(self) -> tuple[bool, bool]:
        return (JogAction.CENTER in self._lines_on, self._led_active)

    def close(self) -> None:
        pass


def _gpiozero_pin_factory_for_live() -> None:
    """Use RPi.GPIO for gpiozero outputs (JogDrive). Native sysfs often fails export on older Pis.

    KEY_ADC1 / KEY_LED observation uses direct ``RPi.GPIO`` polling (no edge IRQs). Override with
    ``GPIOZERO_PIN_FACTORY`` if needed (e.g. ``lgpio`` on Pi 4+ Bookworm).
    """
    import os

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
