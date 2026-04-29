"""Display backlight power and brightness control.

Three independent mechanisms are used:

  brightness  /sys/class/backlight/<bus>-0045/brightness   (group video, writable)
              0–255 raw; Phase 20 Pi 5 validated full 255/255 range.
              Bus number differs by host: 10 on Pi 2, 11 on Pi 5 — auto-discovered.

  power       wlr-randr --output <DSI-N> --off / --on
              Routes through the labwc Wayland compositor, which stops/starts
              sending frames.  bl_power sysfs accepts writes but does not
              physically power the panel.
              DSI output name differs by host: DSI-1 on Pi 2, DSI-2 on Pi 5 — auto-discovered.

  rail        GPIO24 → Phase 21 S8550 PNP high-side switch
              Cuts the display's 5V supply rail.  Must be asserted BEFORE the
              compositor sends frames (power-on) and de-asserted AFTER the
              compositor stops (power-off) to avoid panel transients.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# Phase 18 cap was 170/255 (Pi 2 power-path limit). Phase 20 Pi 5 validation
# confirmed full 255/255 is stable — cap lifted to hardware maximum.
BRIGHTNESS_RAW_MAX = 255
BRIGHTNESS_RAW_MIN = 0

_BACKLIGHT_DIR = Path("/sys/class/backlight")


def _find_backlight_path() -> Path:
    # Waveshare panel backlight controller is always at I2C address 0x45;
    # the bus number varies by host (10 on Pi 2, 11 on Pi 5).
    for candidate in sorted(_BACKLIGHT_DIR.iterdir()):
        if candidate.name.endswith("-0045"):
            return candidate / "brightness"
    return _BACKLIGHT_DIR / "10-0045" / "brightness"  # legacy fallback


def _find_dsi_output() -> str:
    # DSI output name varies by host: DSI-1 on Pi 2, DSI-2 on Pi 5.
    try:
        result = subprocess.run(
            ["wlr-randr"], capture_output=True, timeout=3, env=_WAYLAND_ENV
        )
        for line in result.stdout.decode(errors="replace").splitlines():
            if line.startswith("DSI-"):
                return line.split()[0]
    except Exception:
        pass
    return "DSI-1"  # legacy fallback

# Wayland compositor env — hardcoded because the API server may start without
# a graphical session (e.g. via systemd user service or SSH).
_WAYLAND_ENV = {
    **os.environ,
    "WAYLAND_DISPLAY": "wayland-0",
    "XDG_RUNTIME_DIR": "/run/user/1000",
}



@runtime_checkable
class DisplayPowerControl(Protocol):
    """Abstraction for display backlight read/write."""

    @property
    def kind(self) -> str:
        """``live`` or ``mock``."""

    def read_brightness_raw(self) -> int:
        """Return current sysfs brightness value (0–255)."""

    def write_brightness_raw(self, value: int) -> None:
        """Write sysfs brightness; value is clamped to [0, BRIGHTNESS_RAW_MAX]."""

    def read_power_on(self) -> bool:
        """Return True when the display output is enabled."""

    def write_power_on(self, on: bool) -> None:
        """Enable or disable the display output."""

    def write_rail_on(self, on: bool) -> None:
        """Assert or de-assert the display 5V supply rail via GPIO24."""


class LiveDisplayPower:
    """Backlight driver for the Waveshare DSI panel.

    brightness writes go directly via sysfs file (group video, no sudo needed).
    power on/off goes via wlr-randr through the labwc Wayland compositor.
    rail on/off drives GPIO24 → Phase 21 S8550 high-side switch.
    """

    def __init__(self, display_rail_pin: int) -> None:
        from gpiozero import OutputDevice  # noqa: PLC0415 — lazy: not available on non-Pi hosts
        self._rail = OutputDevice(display_rail_pin, active_high=True, initial_value=False)

    @property
    def kind(self) -> str:
        return "live"

    def read_brightness_raw(self) -> int:
        try:
            return int(_find_backlight_path().read_text().strip())
        except Exception:
            logger.exception("display_power: read brightness failed")
            return 0

    def write_brightness_raw(self, value: int) -> None:
        clamped = max(BRIGHTNESS_RAW_MIN, min(BRIGHTNESS_RAW_MAX, value))
        if clamped != value:
            logger.debug(
                "display_power: clamped requested %d → %d (ceiling %d)",
                value,
                clamped,
                BRIGHTNESS_RAW_MAX,
            )
        try:
            _find_backlight_path().write_text(str(clamped))
        except Exception:
            logger.exception("display_power: write brightness %d failed", clamped)

    def read_power_on(self) -> bool:
        try:
            result = subprocess.run(
                ["wlr-randr"],
                capture_output=True,
                timeout=3,
                env=_WAYLAND_ENV,
            )
            output = result.stdout.decode(errors="replace")
            # Find the DSI-1 block and check "Enabled: yes"
            in_dsi = False
            dsi_name = _find_dsi_output()
            for line in output.splitlines():
                if line.startswith(dsi_name):
                    in_dsi = True
                elif in_dsi and not line.startswith(" "):
                    break
                elif in_dsi and "Enabled:" in line:
                    return "yes" in line
            return True  # assume on if unreadable
        except Exception:
            logger.exception("display_power: read power state failed")
            return True

    def write_power_on(self, on: bool) -> None:
        flag = "--on" if on else "--off"
        try:
            result = subprocess.run(
                ["wlr-randr", "--output", _find_dsi_output(), flag],
                capture_output=True,
                timeout=5,
                env=_WAYLAND_ENV,
            )
            if result.returncode != 0:
                logger.error(
                    "display_power: wlr-randr %s failed (rc=%d): %s",
                    flag,
                    result.returncode,
                    result.stderr.decode(errors="replace").strip(),
                )
        except Exception:
            logger.exception("display_power: write power %s failed", "on" if on else "off")

    def write_rail_on(self, on: bool) -> None:
        try:
            if on:
                self._rail.on()
            else:
                self._rail.off()
        except Exception:
            logger.exception("display_power: write rail %s failed", "on" if on else "off")


class MockDisplayPower:
    """In-memory backlight mock for dev hosts and tests."""

    def __init__(self, initial_raw: int = 51) -> None:
        self._raw = max(BRIGHTNESS_RAW_MIN, min(BRIGHTNESS_RAW_MAX, initial_raw))
        self._power_on = True
        self._rail_on = False

    @property
    def kind(self) -> str:
        return "mock"

    def read_brightness_raw(self) -> int:
        return self._raw

    def write_brightness_raw(self, value: int) -> None:
        self._raw = max(BRIGHTNESS_RAW_MIN, min(BRIGHTNESS_RAW_MAX, value))

    def read_power_on(self) -> bool:
        return self._power_on

    def write_power_on(self, on: bool) -> None:
        self._power_on = on

    def write_rail_on(self, on: bool) -> None:
        self._rail_on = on


def build_display_power(hw_mode: str, pins: "ProtoboardPins | None" = None) -> DisplayPowerControl:
    """Return a live or mock display power controller matching hw_mode."""
    if hw_mode == "live":
        from pi_deck.hardware.protoboard_pins import ProtoboardPins  # noqa: PLC0415
        p = pins or ProtoboardPins()
        return LiveDisplayPower(display_rail_pin=p.display_power_en)
    return MockDisplayPower()
