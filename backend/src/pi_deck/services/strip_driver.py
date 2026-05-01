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

Lock model (per LED index):
  send(index, color)                         — normal; ignored if LED is locked
                                               always updates saved state
  send(index, color, lock=LockMode.LOCK)     — lock LED to color immediately
  send(index, color, lock=LockMode.UNLOCK)   — unlock and display color; color=None
                                               reverts to last saved state

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
from enum import Enum

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


class LockMode(Enum):
    LOCK   = "lock"
    UNLOCK = "unlock"


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
class _LedState:
    saved:  tuple[int, int, int]        # last non-locked color
    locked: tuple[int, int, int] | None # None = not locked


@dataclass
class _Cmd:
    index: int
    color: tuple[int, int, int] | None
    lock:  LockMode | None


class StripDriver:
    """Addressable RGB LED strip with per-LED lock arbitration.

    send(index, color)                       — normal update, ignored if locked
    send(index, color, lock=LockMode.LOCK)   — lock LED to color
    send(index, color, lock=LockMode.UNLOCK) — unlock; color overrides saved if given
    """

    def __init__(self, num_leds: int, hw_mode: str) -> None:
        self._num_leds = num_leds
        self._live = hw_mode == "live"
        self._spi = None
        self._queue: queue.SimpleQueue[_Cmd | None] = queue.SimpleQueue()
        self._worker: threading.Thread | None = None
        # Worker-owned state — only touched from the worker thread.
        self._state: list[_LedState] = [_LedState(saved=OFF, locked=None) for _ in range(num_leds)]
        if self._live:
            self._init_spi()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._worker = threading.Thread(target=self._drain, daemon=True, name="strip-driver")
        self._worker.start()
        self._queue.put(_Cmd(index=-1, color=None, lock=None))  # initial assert
        logger.info("strip-driver: started (%d LED(s))", self._num_leds)

    def stop(self) -> None:
        self._queue.put(None)  # sentinel
        if self._worker is not None:
            self._worker.join(timeout=2)

    # ── public API ────────────────────────────────────────────────────────────

    def send(
        self,
        index: int,
        color: tuple[int, int, int] | None,
        lock: LockMode | None = None,
    ) -> None:
        """Enqueue a command for LED at index. Non-blocking."""
        if not 0 <= index < self._num_leds:
            raise IndexError(f"LED index {index} out of range (0..{self._num_leds - 1})")
        self._queue.put(_Cmd(index=index, color=color, lock=lock))

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
            self._write_strip()
            return

        s = self._state[cmd.index]

        if cmd.lock is LockMode.LOCK:
            s.locked = cmd.color
            logger.info("strip-driver: LED[%d] locked %s", cmd.index, cmd.color)

        elif cmd.lock is LockMode.UNLOCK:
            if cmd.color is not None:
                s.saved = cmd.color
            s.locked = None
            logger.info("strip-driver: LED[%d] unlocked → %s", cmd.index, s.saved)

        else:
            # Normal command — always update saved; apply only if not locked.
            if cmd.color is not None:
                s.saved = cmd.color
            if s.locked is None:
                logger.info("strip-driver: LED[%d] %s", cmd.index, s.saved)
            else:
                logger.info(
                    "strip-driver: LED[%d] saved %s (locked, not applied)",
                    cmd.index, s.saved,
                )

        self._write_strip()

    def _current(self, s: _LedState) -> tuple[int, int, int]:
        return s.locked if s.locked is not None else s.saved

    def _write_strip(self) -> None:
        if self._spi is None:
            return
        frame = bytearray(_RESET)
        for s in self._state:
            r, g, b = self._current(s)
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
