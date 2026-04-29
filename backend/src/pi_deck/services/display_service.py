"""Display brightness and power management.

Brightness and power are independent hardware knobs that must both be touched:

  brightness  /sys/class/backlight/<bus>-0045/brightness  (0–170 raw, sysfs)
              Controls the physical backlight LED.  Must be 0 to actually cut
              light when powering off; restored on power-on.

  power       wlr-randr --output <DSI-N> --off / --on
              Routes through the labwc Wayland compositor. This blanks the
              panel image (compositor stops sending frames), but does NOT touch
              the backlight hardware — hence we also zero brightness on off.

Power-off sequence: save brightness → write 0 → wlr-randr --off
Power-on  sequence: wlr-randr --on → restore saved brightness

Brightness is persisted to ~/.pi-deck-brightness (raw int) so it survives reboots.
The labwc autostart re-applies it after the DRM driver resets the backlight on takeover.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from pi_deck.hardware.display_power import BRIGHTNESS_RAW_MAX, DisplayPowerControl

logger = logging.getLogger(__name__)

_BRIGHTNESS_FILE = Path.home() / ".pi-deck-brightness"


def _raw_to_pct(raw: int) -> int:
    # Clamp to 100 — raw values above BRIGHTNESS_RAW_MAX are valid on hardware
    # (e.g. set externally or persisted from before the ceiling was enforced).
    return min(100, round(raw * 100 / BRIGHTNESS_RAW_MAX))


def _pct_to_raw(pct: int) -> int:
    return round(pct * BRIGHTNESS_RAW_MAX / 100)


_DEFAULT_RAW = round(BRIGHTNESS_RAW_MAX * 0.30)  # 30 % — safe default for restore


def _load_saved_raw() -> int | None:
    try:
        return int(_BRIGHTNESS_FILE.read_text().strip())
    except Exception:
        return None


def _persist_raw(raw: int) -> None:
    try:
        tmp = _BRIGHTNESS_FILE.with_suffix(".tmp")
        tmp.write_text(str(raw))
        # fsync before rename so a hard power cut doesn't leave a corrupt or missing file.
        with tmp.open() as f:
            os.fsync(f.fileno())
        tmp.replace(_BRIGHTNESS_FILE)
    except Exception:
        logger.warning("display: could not persist brightness to %s", _BRIGHTNESS_FILE)


class DisplayService:
    """UI-facing display brightness and power API (pct units, full 0–255 raw range)."""

    def __init__(self, display_hw: DisplayPowerControl) -> None:
        self._hw = display_hw
        self._saved_raw: int | None = _load_saved_raw()  # persisted across reboots

    # ── brightness ────────────────────────────────────────────────────────────

    def get_brightness_pct(self) -> int:
        """Return current brightness as 0–100 % (derived from live sysfs value).

        Returns the saved (pre-power-off) brightness when the display is off so
        callers see the intended level rather than the physical 0.
        """
        if not self._hw.read_power_on() and self._saved_raw is not None:
            return _raw_to_pct(self._saved_raw)
        return _raw_to_pct(self._hw.read_brightness_raw())

    def set_brightness_pct(self, pct: int) -> None:
        """Set brightness to ``pct`` percent (clamped 0–100; hardware caps at 170 raw)."""
        pct = max(0, min(100, pct))
        raw = _pct_to_raw(pct)
        logger.info("display: set brightness %d%% (raw %d)", pct, raw)
        self._hw.write_brightness_raw(raw)
        self._saved_raw = raw
        _persist_raw(raw)

    def get_brightness_raw(self) -> int:
        """Return raw sysfs brightness (0–255 as reported by the driver)."""
        return self._hw.read_brightness_raw()

    # ── power ─────────────────────────────────────────────────────────────────

    @property
    def is_on(self) -> bool:
        """True when the DSI output is enabled via wlr-randr."""
        return self._hw.read_power_on()

    def power_off(self) -> None:
        """Power off the display.

        Saves the current backlight level, zeros the backlight LED, then signals
        the compositor to disable the DSI-1 output.
        """
        self._saved_raw = self._hw.read_brightness_raw()
        _persist_raw(self._saved_raw)
        self._hw.write_brightness_raw(0)
        self._hw.write_power_on(False)
        logger.info("display: power off (brightness saved=%d raw, backlight=0, wlr-randr --off)",
                    self._saved_raw)

    def power_on(self) -> None:
        """Power on the display.

        Signals the compositor to re-enable the DSI-1 output, then restores the
        backlight to the level that was active before the last power_off().
        """
        self._hw.write_power_on(True)
        restore = self._saved_raw if self._saved_raw is not None else _DEFAULT_RAW
        self._hw.write_brightness_raw(restore)
        logger.info("display: power on (brightness restored=%d raw, wlr-randr --on)", restore)
        self._saved_raw = None
