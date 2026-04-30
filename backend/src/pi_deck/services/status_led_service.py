"""Status LED — WS2812B via SPI (GPIO10 / SPI0 MOSI).

Pi 5 (RP1 chip) does not expose the GPU DMA mailbox that rpi_ws281x uses,
so we drive the LED with the SPI bus instead.  SPI generates the precise
800 kHz NRZ waveform in hardware without needing root or DMA access.

Encoding (4 SPI bits per WS2812B bit at 3.2 MHz → 312.5 ns per SPI bit):
  WS2812B '1' → SPI nibble 0xE  (1110) : 937.5 ns high / 312.5 ns low  ✓
  WS2812B '0' → SPI nibble 0x8  (1000) : 312.5 ns high / 937.5 ns low  ✓

Hardware: GPIO10 (SPI0 MOSI, physical pin 19) → SN74AHCT125 level shifter
3.3 V → 5 V → WS2812B DIN.

Color / state matrix:
  monitor LED active   → off (0%) — inverted: status LED is dark while monitor LED blinks
  monitor LED inactive → restore _BRIGHTNESS with current color:
    button held        → amber
    panel on           → green
    panel off          → red

Threading model:
  All SPI writes happen on a dedicated daemon thread (_run).  Callers (asyncio
  loop, gpiozero callbacks) only update state variables under a lock and signal
  a threading.Event — they never block on SPI.  Rapid state changes coalesce:
  the thread always reads the latest state, so no intermediate state is lost.
"""

from __future__ import annotations

import glob
import logging
import threading

logger = logging.getLogger(__name__)

_SPI_SPEED_HZ = 3_200_000

_BRIGHTNESS = 0.01   # 1 % — normal operating brightness (adjust here to change all states)

_RESET = bytes(20)

# Full-scale RGB before brightness scaling
_GREEN = (0, 255, 0)
_RED   = (255, 0, 0)
_AMBER = (255, 165, 0)


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


class StatusLedService:
    """Single WS2812B status LED with a state-driven colour model.

    State inputs (each triggers an immediate LED update):
      set_panel_on(bool)     — panel on → green base; off → red base
      set_button_held(bool)  — held → amber override until released
      set_monitor_led(bool)  — monitor LED active → fully off (0 %)

    All SPI I/O runs on a private daemon thread; callers never block.
    """

    def __init__(self, hw_mode: str) -> None:
        self._live = hw_mode == "live"
        self._spi = None
        self._panel_on = True
        self._button_held = False
        self._monitor_led_on = False
        self._lock = threading.Lock()
        self._signal = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        if self._live:
            self._init_spi()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, name="status-led", daemon=True
        )
        self._thread.start()
        self._signal.set()  # trigger initial paint
        logger.info("status-led: started")

    def stop(self) -> None:
        self._stop.set()
        self._signal.set()  # wake thread so it can exit
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._send(0, 0, 0)
        if self._spi is not None:
            try:
                self._spi.close()
            except Exception:
                pass

    # ── state setters — called from any thread ────────────────────────────────

    def set_panel_on(self, on: bool) -> None:
        with self._lock:
            self._panel_on = on
        self._signal.set()

    def set_button_held(self, held: bool) -> None:
        with self._lock:
            self._button_held = held
        self._signal.set()

    def set_monitor_led(self, active: bool) -> None:
        with self._lock:
            self._monitor_led_on = active
        self._signal.set()

    # ── LED thread ────────────────────────────────────────────────────────────

    def _run(self) -> None:
        while not self._stop.is_set():
            self._signal.wait()
            self._signal.clear()
            if self._stop.is_set():
                break
            with self._lock:
                monitor_on = self._monitor_led_on
                button_held = self._button_held
                panel_on = self._panel_on
            if monitor_on:
                self._send(0, 0, 0)
            else:
                r, g, b = _AMBER if button_held else (_GREEN if panel_on else _RED)
                self._send(
                    int(r * _BRIGHTNESS),
                    int(g * _BRIGHTNESS),
                    int(b * _BRIGHTNESS),
                )

    # ── SPI helpers ───────────────────────────────────────────────────────────

    def _send(self, r: int, g: int, b: int) -> None:
        if self._spi is not None:
            try:
                self._spi.xfer2(list(_encode_pixel(r, g, b) + _RESET))
            except Exception as exc:
                logger.debug("status-led: SPI write error: %s", exc)
        else:
            logger.debug("status-led: mock rgb(%d,%d,%d)", r, g, b)

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
