"""Display backlight power and brightness control.

Two independent mechanisms are used:

  brightness  /sys/class/backlight/10-0045/brightness   (group video, writable)
              0–255 raw; Phase 18 validated ceiling is 170.

  power       wlr-randr --output DSI-1 --off / --on
              Routes through the labwc Wayland compositor, which is the only
              mechanism that actually cuts panel power on this Pi/Waveshare setup.
              bl_power sysfs accepts writes but does not physically power the panel.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# Phase 18 validated safe brightness ceiling — do not raise without new testing.
BRIGHTNESS_RAW_MAX = 170
BRIGHTNESS_RAW_MIN = 0

_SYSFS_BRIGHTNESS = Path("/sys/class/backlight/10-0045/brightness")

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


class LiveDisplayPower:
    """Backlight driver for the Waveshare DSI panel.

    brightness writes go directly via sysfs file (group video, no sudo needed).
    power on/off goes via wlr-randr through the labwc Wayland compositor.
    """

    @property
    def kind(self) -> str:
        return "live"

    def read_brightness_raw(self) -> int:
        try:
            return int(_SYSFS_BRIGHTNESS.read_text().strip())
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
            _SYSFS_BRIGHTNESS.write_text(str(clamped))
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
            for line in output.splitlines():
                if line.startswith("DSI-1"):
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
                ["wlr-randr", "--output", "DSI-1", flag],
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


class MockDisplayPower:
    """In-memory backlight mock for dev hosts and tests."""

    def __init__(self, initial_raw: int = 51) -> None:
        self._raw = max(BRIGHTNESS_RAW_MIN, min(BRIGHTNESS_RAW_MAX, initial_raw))
        self._power_on = True

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


def build_display_power(hw_mode: str) -> DisplayPowerControl:
    """Return a live or mock display power controller matching hw_mode."""
    if hw_mode == "live":
        return LiveDisplayPower()
    return MockDisplayPower()
