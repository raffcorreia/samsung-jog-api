"""Addressable RGB LED strip driver — WS2812B via SPI (GPIO10 / SPI0 MOSI).

Pi 5 (RP1 chip) does not expose the GPU DMA mailbox that rpi_ws281x uses,
so we drive the strip with the SPI bus instead.  SPI generates the precise
800 kHz NRZ waveform in hardware without needing root or DMA access.

Encoding (8 SPI bits per WS2812B bit at 6.4 MHz → 156.25 ns per SPI bit):
  WS2812B '1' → 0xF8 (11111000) : 781.25 ns high / 468.75 ns low  ✓
  WS2812B '0' → 0xC0 (11000000) : 312.5 ns high  / 937.5 ns low   ✓

This matches the Adafruit NeoPixel SPI encoding and gives well-centred
timing margins vs the WS2812B spec (±150 ns tolerance).

Hardware: GPIO10 (SPI0 MOSI, physical pin 19) → WS2812B DIN (direct, no level shifter).
The SN74AHCT125 level shifter was removed after testing showed it caused random frame
corruption and missed updates. WS2812B tolerates 3.3 V logic reliably at this distance.

Color order: the installed LED responds to RGB byte order (Red, Green, Blue), not the
GRB order specified by the standard WS2812B datasheet. This is common in clone/variant
units. If a replacement LED shows red and green swapped, change _encode_pixel to send
(g, r, b) instead of (r, g, b).

Priority model (per LED index):
  Non-priority command  — updates the saved state; applied immediately unless that LED
                          is currently under a priority override.
  Priority command      — applied immediately regardless; non-priority commands received
                          while active still update the saved state but do not change
                          the displayed color.
  Priority cancel       — send(index, priority=True, color=None); reverts to the last
                          saved non-priority color for that LED.

Threading:
  send() is non-blocking — it enqueues a command and returns immediately.
  A single worker thread drains the queue, mutates per-LED state, and writes
  the full strip frame to SPI.  All state is owned by the worker thread so
  no additional locks are needed.
"""

from __future__ import annotations

import glob
import logging
import queue
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_SPI_SPEED_HZ = 6_400_000
_BRIGHTNESS = 0.01   # 1 % — adjust here to change all states
_RESET = bytes(80)   # 80 bytes × 8 bits / 6.4 MHz = 100 µs reset pulse

# Named color constants — also accept any (r, g, b) tuple directly.
OFF   = (0,   0,   0)
GREEN = (0,   255, 0)
RED   = (255, 0,   0)
AMBER = (255, 165, 0)
BLUE  = (0,   0,   255)


def _find_spi() -> tuple[int, int] | None:
    devices = sorted(glob.glob("/dev/spidev*.0"))
    if not devices:
        return None
    path = devices[0]
    parts = path.replace("/dev/spidev", "").split(".")
    return int(parts[0]), int(parts[1])


def _encode_pixel(r: int, g: int, b: int) -> bytes:
    buf = bytearray(24)
    for ch_idx, byte_val in enumerate((r, g, b)):
        for bit in range(8):
            buf[ch_idx * 8 + bit] = 0xF8 if (byte_val >> (7 - bit)) & 1 else 0xC0
    return bytes(buf)


@dataclass
class _Cmd:
    index: int
    priority: bool
    color: tuple[int, int, int] | None  # None = cancel priority


class StripDriver:
    """Addressable RGB LED strip with per-LED priority arbitration.

    Priority:
      send(index, priority=True, color=RGB)  — override that LED immediately
      send(index, priority=True, color=None) — cancel override, revert to saved state
      send(index, priority=False, color=RGB) — update saved state; applied only when
                                               no priority override is active for that LED
    """

    def __init__(self, num_leds: int, hw_mode: str) -> None:
        self._num_leds = num_leds
        self._live = hw_mode == "live"
        self._spi = None
        self._queue: queue.SimpleQueue[_Cmd | None] = queue.SimpleQueue()
        self._worker: threading.Thread | None = None
        # Worker-owned state — only touched from the worker thread.
        self._saved: list[tuple[int, int, int]] = [OFF] * num_leds
        self._current: list[tuple[int, int, int]] = [OFF] * num_leds
        self._priority_active: list[bool] = [False] * num_leds
        if self._live:
            self._init_spi()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._worker = threading.Thread(target=self._drain, daemon=True, name="strip-driver")
        self._worker.start()
        self._queue.put(_Cmd(index=-1, priority=False, color=None))  # initial assert
        logger.info("strip-driver: started (%d LED(s))", self._num_leds)

    def stop(self) -> None:
        self._queue.put(None)  # sentinel
        if self._worker is not None:
            self._worker.join(timeout=2)

    # ── public API ────────────────────────────────────────────────────────────

    def send(
        self,
        index: int,
        *,
        priority: bool,
        color: tuple[int, int, int] | None,
    ) -> None:
        """Enqueue a command for LED at index. Non-blocking."""
        if not 0 <= index < self._num_leds:
            raise IndexError(f"LED index {index} out of range (0..{self._num_leds - 1})")
        self._queue.put(_Cmd(index=index, priority=priority, color=color))

    # ── worker ────────────────────────────────────────────────────────────────

    def _drain(self) -> None:
        while True:
            cmd = self._queue.get()
            if cmd is None:
                self._write_all_off()
                break
            self._process(cmd)

    def _process(self, cmd: _Cmd) -> None:
        if cmd.index == -1:
            # Initial assert — write current state without changing it.
            self._write_strip()
            return

        idx = cmd.index
        if cmd.priority:
            if cmd.color is None:
                # Cancel priority — revert to saved state.
                self._priority_active[idx] = False
                self._current[idx] = self._saved[idx]
                logger.info(
                    "strip-driver: LED[%d] priority cleared → %s", idx, self._current[idx]
                )
            else:
                # Activate priority override.
                self._priority_active[idx] = True
                self._current[idx] = cmd.color
                logger.info(
                    "strip-driver: LED[%d] priority %s", idx, cmd.color
                )
        else:
            # Non-priority: always update saved state.
            self._saved[idx] = cmd.color  # type: ignore[assignment]
            if not self._priority_active[idx]:
                self._current[idx] = cmd.color  # type: ignore[assignment]
                logger.info("strip-driver: LED[%d] %s", idx, cmd.color)
            else:
                logger.info(
                    "strip-driver: LED[%d] saved %s (priority active, not applied)",
                    idx, cmd.color,
                )
        self._write_strip()

    def _write_strip(self) -> None:
        if self._spi is None:
            return
        frame = bytearray(_RESET)
        for idx, (r, g, b) in enumerate(self._current):
            frame += _encode_pixel(
                int(r * _BRIGHTNESS),
                int(g * _BRIGHTNESS),
                int(b * _BRIGHTNESS),
            )
        frame += _RESET
        try:
            self._spi.writebytes2(bytes(frame))
        except Exception as exc:
            logger.error("strip-driver: SPI write error: %s", exc)

    def _write_all_off(self) -> None:
        if self._spi is None:
            return
        frame = _RESET + _encode_pixel(0, 0, 0) * self._num_leds + _RESET
        try:
            self._spi.writebytes2(frame)
            self._spi.close()
        except Exception:
            pass
        finally:
            self._spi = None

    def _init_spi(self) -> None:
        bus_dev = _find_spi()
        if bus_dev is None:
            logger.warning("strip-driver: no SPI device found — LED disabled (mock mode)")
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
                "strip-driver: SPI opened spidev%d.%d @ %d Hz (GPIO10 / WS2812B)",
                bus, dev, _SPI_SPEED_HZ,
            )
        except Exception as exc:
            logger.warning("strip-driver: SPI init failed (%s) — LED disabled", exc)
            self._live = False
