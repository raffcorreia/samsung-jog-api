"""Status LED — WS2812B via SPI (GPIO10 / SPI0 MOSI).

Pi 5 (RP1 chip) does not expose the GPU DMA mailbox that rpi_ws281x uses,
so we drive the LED with the SPI bus instead.  SPI generates the precise
800 kHz NRZ waveform in hardware without needing root or DMA access.

Encoding (8 SPI bits per WS2812B bit at 6.4 MHz → 156.25 ns per SPI bit):
  WS2812B '1' → 0xF8 (11111000) : 781.25 ns high / 468.75 ns low  ✓
  WS2812B '0' → 0xC0 (11000000) : 312.5 ns high  / 937.5 ns low   ✓

This matches the Adafruit NeoPixel SPI encoding and gives well-centred
timing margins vs the WS2812B spec (±150 ns tolerance).

Hardware: GPIO10 (SPI0 MOSI, physical pin 19) → WS2812B DIN (direct, no level shifter).
The SN74AHCT125 level shifter was removed after testing showed it caused random frame
corruption and missed updates. WS2812B tolerates 3.3 V logic reliably at this distance.

Color / state — priority reassert (button > monitor > panel):
  button held                        → AMBER
  monitor active,  panel on          → BLUE
  monitor active,  panel off         → OFF
  default,         panel on          → GREEN
  default,         panel off         → RED

Threading:
  State is read inside _spi_lock so the last writer always uses the true
  final state — prevents a race where two rapid events queue and the
  earlier write overwrites the later one.
  SPI frames for all states are pre-computed at import time.
"""

from __future__ import annotations

import glob
import logging
import threading

logger = logging.getLogger(__name__)

_SPI_SPEED_HZ = 6_400_000
_BRIGHTNESS = 0.01   # 1 % — adjust here to change all states
_RESET = bytes(40)   # 40 bytes × 8 bits / 6.4 MHz = 50 µs reset pulse

_GREEN = (0, 255, 0)
_RED   = (255, 0, 0)
_AMBER = (255, 165, 0)
_BLUE  = (0, 0, 255)


def _find_spi() -> tuple[int, int] | None:
    devices = sorted(glob.glob("/dev/spidev*.0"))
    if not devices:
        return None
    path = devices[0]
    parts = path.replace("/dev/spidev", "").split(".")
    return int(parts[0]), int(parts[1])


def _encode_pixel(r: int, g: int, b: int) -> bytes:
    """Encode one pixel as 24 SPI bytes (RGB order, 8 SPI bits per WS2812B bit)."""
    buf = bytearray(24)
    for ch_idx, byte_val in enumerate((r, g, b)):
        for bit in range(8):
            buf[ch_idx * 8 + bit] = 0xF8 if (byte_val >> (7 - bit)) & 1 else 0xC0
    return bytes(buf)


def _make_frame(r: int, g: int, b: int) -> list[int]:
    return list(_RESET + _encode_pixel(r, g, b) + _RESET)


# Pre-computed SPI frames — avoids encoding + list conversion on every write.
_FRAME_OFF   = _make_frame(0, 0, 0)
_FRAME_GREEN = _make_frame(int(_GREEN[0] * _BRIGHTNESS), int(_GREEN[1] * _BRIGHTNESS), int(_GREEN[2] * _BRIGHTNESS))
_FRAME_RED   = _make_frame(int(_RED[0]   * _BRIGHTNESS), int(_RED[1]   * _BRIGHTNESS), int(_RED[2]   * _BRIGHTNESS))
_FRAME_AMBER = _make_frame(int(_AMBER[0] * _BRIGHTNESS), int(_AMBER[1] * _BRIGHTNESS), int(_AMBER[2] * _BRIGHTNESS))
_FRAME_BLUE  = _make_frame(int(_BLUE[0]  * _BRIGHTNESS), int(_BLUE[1]  * _BRIGHTNESS), int(_BLUE[2]  * _BRIGHTNESS))


class StatusLedService:
    """Single WS2812B status LED driven by tracked state with priority reassert.

    Setters call SPI directly from the caller thread — no polling, no queue.
    A correction daemon re-asserts the full current state every 5 s to self-heal
    missed events without clobbering non-panel states (e.g. blue during monitor active).

    Priority (for reassert and terminal fallbacks):
      button held  →  AMBER
      monitor active  →  BLUE (panel on) / OFF (panel off)
      default  →  GREEN (panel on) / RED (panel off)
    """

    def __init__(self, hw_mode: str) -> None:
        self._live = hw_mode == "live"
        self._spi = None
        self._panel_on = True
        self._monitor_active = False
        self._button_held = False
        self._state_lock = threading.Lock()
        self._spi_lock = threading.Lock()
        if self._live:
            self._init_spi()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._reassert()
        logger.info("status-led: started")

    def stop(self) -> None:
        if self._spi is not None:
            with self._spi_lock:
                try:
                    self._spi.writebytes2(_FRAME_OFF)
                    self._spi.close()
                except Exception:
                    pass

    # ── state setters — called from any thread ────────────────────────────────

    def set_panel_on(self, on: bool) -> None:
        with self._state_lock:
            self._panel_on = on
        logger.info("status-led: panel_on → %s", on)
        self._reassert()

    def set_button_held(self, held: bool) -> None:
        with self._state_lock:
            self._button_held = held
        logger.info("status-led: button_held → %s", held)
        self._reassert()

    def set_monitor_led(self, active: bool) -> None:
        with self._state_lock:
            self._monitor_active = active
        logger.info("status-led: monitor_led → %s", active)
        self._reassert()

    # ── internals ─────────────────────────────────────────────────────────────

    def _reassert(self) -> None:
        """Write the correct frame for the current state, re-reading state inside the SPI lock.

        Acquiring spi_lock before reading state guarantees the last writer always
        reflects the true final state — prevents a race where two rapid events
        queue up and the earlier one overwrites the later one's SPI write.
        """
        if self._spi is None:
            return
        with self._spi_lock:
            with self._state_lock:
                button_held = self._button_held
                monitor_active = self._monitor_active
                panel_on = self._panel_on
            if button_held:
                label, color, frame = "AMBER", _AMBER, _FRAME_AMBER
            elif monitor_active:
                if panel_on:
                    label, color, frame = "BLUE", _BLUE, _FRAME_BLUE
                else:
                    label, color, frame = "OFF", (0, 0, 0), _FRAME_OFF
            else:
                if panel_on:
                    label, color, frame = "GREEN", _GREEN, _FRAME_GREEN
                else:
                    label, color, frame = "RED", _RED, _FRAME_RED
            r = int(color[0] * _BRIGHTNESS)
            g = int(color[1] * _BRIGHTNESS)
            b = int(color[2] * _BRIGHTNESS)
            logger.info(
                "status-led: %s (%d,%d,%d)  [button=%s monitor=%s panel=%s]",
                label, r, g, b, button_held, monitor_active, panel_on,
            )
            try:
                self._spi.writebytes2(frame)
            except Exception as exc:
                logger.error("status-led: SPI write error: %s", exc)

    def _init_spi(self) -> None:
        bus_dev = _find_spi()
        if bus_dev is None:
            logger.warning("status-led: no SPI device found — LED disabled (mock mode)")
            self._live = False
            return
        bus, dev = bus_dev
        try:
            import spidev  # type: ignore[import]
            spi = spidev.SpiDev()
            spi.open(bus, dev)
            spi.max_speed_hz = _SPI_SPEED_HZ
            spi.mode = 0
            self._spi = spi
            logger.info(
                "status-led: SPI opened spidev%d.%d @ %d Hz (GPIO10 / WS2812B)",
                bus, dev, _SPI_SPEED_HZ,
            )
        except Exception as exc:
            logger.warning("status-led: SPI init failed (%s) — LED disabled", exc)
            self._live = False
