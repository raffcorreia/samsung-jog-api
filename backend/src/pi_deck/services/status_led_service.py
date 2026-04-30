"""Status LED — WS2812B via SPI (GPIO10 / SPI0 MOSI).

Pi 5 (RP1 chip) does not expose the GPU DMA mailbox that rpi_ws281x uses,
so we drive the LED with the SPI bus instead.  SPI generates the precise
800 kHz NRZ waveform in hardware without needing root or DMA access.

Encoding (4 SPI bits per WS2812B bit at 3.2 MHz → 312.5 ns per SPI bit):
  WS2812B '1' → SPI nibble 0xE  (1110) : 937.5 ns high / 312.5 ns low  ✓
  WS2812B '0' → SPI nibble 0x8  (1000) : 312.5 ns high / 937.5 ns low  ✓

Hardware: GPIO10 (SPI0 MOSI, physical pin 19) → SN74AHCT125 level shifter
3.3 V → 5 V → WS2812B DIN.

Color / state — last event wins, all terminal events fall to panel colour:
  set_button_held(True)              → AMBER
  set_button_held(False)             → panel colour
  set_monitor_led(True),  panel on   → BLUE
  set_monitor_led(True),  panel off  → OFF
  set_monitor_led(False)             → panel colour
  set_panel_on(True)                 → GREEN
  set_panel_on(False)                → RED
  correction thread (every 5 s)     → panel colour  (self-heals missed events)

Threading:
  Each setter calls _send_frame() directly from the caller thread.
  _spi_lock serialises concurrent SPI writes (~80 µs each at 3.2 MHz).
  A correction daemon thread re-asserts panel colour every 5 s.
  SPI frames for all states are pre-computed at import time.
"""

from __future__ import annotations

import glob
import logging
import threading

logger = logging.getLogger(__name__)

_SPI_SPEED_HZ = 3_200_000
_BRIGHTNESS = 0.01   # 1 % — adjust here to change all states
_RESET = bytes(20)

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
    """Encode one WS2811 pixel as 12 SPI bytes (RGB order, 4 SPI bits per bit)."""
    buf = bytearray(12)
    for ch_idx, byte_val in enumerate((r, g, b)):
        for pair in range(4):
            hi = (byte_val >> (7 - pair * 2)) & 1
            lo = (byte_val >> (6 - pair * 2)) & 1
            buf[ch_idx * 4 + pair] = (0xE0 if hi else 0x80) | (0x0E if lo else 0x08)
    return bytes(buf)


def _make_frame(r: int, g: int, b: int) -> list[int]:
    return list(_encode_pixel(r, g, b) + _RESET)


# Pre-computed SPI frames — avoids encoding + list conversion on every write.
_FRAME_OFF   = _make_frame(0, 0, 0)
_FRAME_GREEN = _make_frame(int(_GREEN[0] * _BRIGHTNESS), int(_GREEN[1] * _BRIGHTNESS), int(_GREEN[2] * _BRIGHTNESS))
_FRAME_RED   = _make_frame(int(_RED[0]   * _BRIGHTNESS), int(_RED[1]   * _BRIGHTNESS), int(_RED[2]   * _BRIGHTNESS))
_FRAME_AMBER = _make_frame(int(_AMBER[0] * _BRIGHTNESS), int(_AMBER[1] * _BRIGHTNESS), int(_AMBER[2] * _BRIGHTNESS))
_FRAME_BLUE  = _make_frame(int(_BLUE[0]  * _BRIGHTNESS), int(_BLUE[1]  * _BRIGHTNESS), int(_BLUE[2]  * _BRIGHTNESS))


class StatusLedService:
    """Single WS2812B status LED driven by last-event-wins state model.

    Setters call SPI directly from the caller thread — no polling, no queue.
    A correction daemon re-asserts panel colour every 5 s to self-heal missed events.
    """

    def __init__(self, hw_mode: str) -> None:
        self._live = hw_mode == "live"
        self._spi = None
        self._panel_on = True
        self._state_lock = threading.Lock()   # guards _panel_on reads/writes
        self._spi_lock = threading.Lock()     # serialises concurrent SPI writes
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        if self._live:
            self._init_spi()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._correction_loop, name="status-led", daemon=True
        )
        self._thread.start()
        self._send_panel_color()
        logger.info("status-led: started")

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=6)
        self._send_frame(_FRAME_OFF)
        if self._spi is not None:
            try:
                self._spi.close()
            except Exception:
                pass

    # ── state setters — called from any thread ────────────────────────────────

    def set_panel_on(self, on: bool) -> None:
        with self._state_lock:
            self._panel_on = on
        self._send_frame(_FRAME_GREEN if on else _FRAME_RED)

    def set_button_held(self, held: bool) -> None:
        if held:
            self._send_frame(_FRAME_AMBER)
        else:
            self._send_panel_color()

    def set_monitor_led(self, active: bool) -> None:
        if active:
            with self._state_lock:
                panel_on = self._panel_on
            self._send_frame(_FRAME_BLUE if panel_on else _FRAME_OFF)
        else:
            self._send_panel_color()

    # ── correction thread ─────────────────────────────────────────────────────

    def _correction_loop(self) -> None:
        while not self._stop.wait(timeout=5.0):
            self._send_panel_color()

    # ── internals ─────────────────────────────────────────────────────────────

    def _send_panel_color(self) -> None:
        with self._state_lock:
            panel_on = self._panel_on
        self._send_frame(_FRAME_GREEN if panel_on else _FRAME_RED)

    def _send_frame(self, frame: list[int]) -> None:
        if self._spi is not None:
            with self._spi_lock:
                try:
                    self._spi.writebytes2(frame)
                except Exception as exc:
                    logger.debug("status-led: SPI write error: %s", exc)
        else:
            logger.debug("status-led: mock frame len=%d", len(frame))

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
