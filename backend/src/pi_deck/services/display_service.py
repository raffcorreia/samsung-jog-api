"""Display brightness and power management.

Brightness and power are independent hardware knobs that must both be touched:

  brightness  /sys/class/backlight/10-0045/brightness  (0–170 raw, sysfs)
              Controls the physical backlight LED.  Must be 0 to actually cut
              light when powering off; restored on power-on.

  power       wlr-randr --output DSI-1 --off / --on
              Routes through the labwc Wayland compositor. This blanks the
              panel image (compositor stops sending frames), but does NOT touch
              the backlight hardware — hence we also zero brightness on off.

Power-off sequence: save brightness → write 0 → wlr-randr --off
Power-on  sequence: wlr-randr --on → restore saved brightness
"""

from __future__ import annotations

import logging

from pi_deck.hardware.display_power import BRIGHTNESS_RAW_MAX, DisplayPowerControl

logger = logging.getLogger(__name__)


def _raw_to_pct(raw: int) -> int:
    return round(raw * 100 / BRIGHTNESS_RAW_MAX)


def _pct_to_raw(pct: int) -> int:
    return round(pct * BRIGHTNESS_RAW_MAX / 100)


_DEFAULT_RAW = round(BRIGHTNESS_RAW_MAX * 0.30)  # 30 % — safe default for restore


class DisplayService:
    """UI-facing display brightness and power API (pct units, capped at 170/255 raw)."""

    def __init__(self, display_hw: DisplayPowerControl) -> None:
        self._hw = display_hw
        self._saved_raw: int | None = None  # brightness saved before power-off

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
        # Keep save in sync so power-on restores the most recently set level.
        if not self._hw.read_power_on():
            self._saved_raw = raw

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
