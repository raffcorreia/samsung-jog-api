"""Raw KEY_LED capture and 1007.7 STATE-frame decoding.

The GPIO callback only timestamps and appends to bounded in-memory queues.  Decoding and
websocket fan-out run on the asyncio loop, away from gpiozero's helper thread.
"""

from __future__ import annotations

import asyncio
import statistics
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any

from fastapi import WebSocket

from pi_deck.models.schemas import utc_iso
from pi_deck.services.ws_hub import WsHub

EDGE_LOG_VERSION = 1
DEFAULT_HALF_BIT_NS = 10_000_000
DEFAULT_TOLERANCE = 0.35
DEFAULT_GLITCH_NS = 250_000
DEFAULT_BUFFER_SIZE = 4096
FRAME_BITS = 72
FRAME_BYTES = 9
PREAMBLE_SYNC = bytes.fromhex("ffff2dd4")


@dataclass(frozen=True)
class RawLedEdge:
    seq: int
    monotonic_ns: int
    level: int
    interval_ns: int | None


@dataclass(frozen=True)
class DecodedStateFrame:
    edge_seq: int
    monotonic_ns: int
    raw_hex: str
    sequence: int
    layout: str
    input1: str
    input2: str
    crc: int


def crc8(data: bytes) -> int:
    """CRC-8 poly 0x07, init 0, MSB first, no reflection/final XOR."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def _near(value: int, target: int, tolerance: float) -> bool:
    return target * (1 - tolerance) <= value <= target * (1 + tolerance)


def _decode_bits_from(
    edges: list[RawLedEdge], start: int, half_ns: int, tolerance: float
) -> tuple[bytes, int] | None:
    """Treat ``edges[start]`` as a bit-boundary edge and decode one fixed 1007.7 frame."""
    bits: list[int] = []
    pos = start
    while len(bits) < FRAME_BITS:
        if pos + 1 >= len(edges):
            return None
        delta = edges[pos + 1].monotonic_ns - edges[pos].monotonic_ns
        # Classify around the midpoint first so wide tolerance windows cannot overlap.
        if delta >= half_ns * 1.5 and _near(delta, half_ns * 2, tolerance):
            bits.append(0)
            pos += 1
            continue
        if delta < half_ns * 1.5 and _near(delta, half_ns, tolerance):
            if pos + 2 >= len(edges):
                return None
            delta2 = edges[pos + 2].monotonic_ns - edges[pos + 1].monotonic_ns
            if not _near(delta2, half_ns, tolerance):
                return None
            bits.append(1)
            pos += 2
            continue
        return None

    raw = bytearray(FRAME_BYTES)
    for index, bit in enumerate(bits):
        raw[index // 8] |= bit << (7 - index % 8)
    return bytes(raw), pos


def decode_state_frames(
    edges: list[RawLedEdge],
    *,
    half_bit_ns: int = DEFAULT_HALF_BIT_NS,
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[DecodedStateFrame]:
    """Sliding, polarity-independent decoder for the draft 1007.7 STATE frame."""
    frames: list[DecodedStateFrame] = []
    seen_starts: set[int] = set()
    for start in range(max(0, len(edges) - 512), len(edges)):
        decoded = _decode_bits_from(edges, start, half_bit_ns, tolerance)
        if decoded is None:
            continue
        raw, end = decoded
        if raw[:4] != PREAMBLE_SYNC or raw[4] != 0x11:
            continue
        if crc8(raw[4:8]) != raw[8]:
            continue
        start_ns = edges[start].monotonic_ns
        if start_ns in seen_starts:
            continue
        seen_starts.add(start_ns)
        state = raw[6]
        layout_code = state >> 4
        input1_code = state & 0x0F
        input2_code = raw[7] >> 4
        layout = {0: "single", 1: "pip", 2: "pbp"}.get(layout_code, "unknown")
        inputs = {0: "none", 1: "hdmi", 2: "dp", 3: "tb"}
        frames.append(
            DecodedStateFrame(
                edge_seq=edges[end].seq,
                monotonic_ns=start_ns,
                raw_hex=raw.hex(),
                sequence=raw[5],
                layout=layout,
                input1=inputs.get(input1_code, "unknown"),
                input2=inputs.get(input2_code, "unknown"),
                crc=raw[8],
            )
        )
    return frames


class LedCommunicationService:
    """Bounded raw capture, decoder, REST snapshots and batched websocket updates."""

    def __init__(
        self,
        *,
        ws_hub: WsHub,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        glitch_ns: int = DEFAULT_GLITCH_NS,
        half_bit_ns: int = DEFAULT_HALF_BIT_NS,
        tolerance: float = DEFAULT_TOLERANCE,
    ) -> None:
        self._hub = ws_hub
        self._buffer_size = max(256, buffer_size)
        self._glitch_ns = max(0, glitch_ns)
        self._half_bit_ns = half_bit_ns
        self._tolerance = tolerance
        self._lock = threading.Lock()
        self._edges: deque[RawLedEdge] = deque(maxlen=self._buffer_size)
        self._pending: deque[RawLedEdge] = deque(maxlen=self._buffer_size)
        self._frames: deque[DecodedStateFrame] = deque(maxlen=64)
        self._capturing = True
        self._next_seq = 0
        self._last_accepted_ns: int | None = None
        self._last_level: int | None = None
        self._accepted = 0
        self._rejected_glitches = 0
        self._overruns = 0
        self._decoder_rejections = 0
        self._last_decoded_start_ns: int | None = None
        self._valid_frames = 0
        self._missing_frames = 0
        self._last_frame_sequence: int | None = None
        self._drain_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._drain_task = asyncio.create_task(self._drain_loop(), name="led-communication")

    async def stop(self) -> None:
        if self._drain_task is None:
            return
        self._drain_task.cancel()
        try:
            await self._drain_task
        except asyncio.CancelledError:
            pass
        self._drain_task = None

    def on_raw_edge(self, level: int, monotonic_ns: int | None = None) -> None:
        """GPIO-thread entry point. ``level`` is the physical sampled 0/1 level."""
        timestamp = time.monotonic_ns() if monotonic_ns is None else monotonic_ns
        with self._lock:
            if not self._capturing:
                self._last_level = int(bool(level))
                return
            interval = (
                None if self._last_accepted_ns is None else timestamp - self._last_accepted_ns
            )
            if interval is not None and interval < self._glitch_ns:
                self._rejected_glitches += 1
                return
            if len(self._edges) == self._buffer_size or len(self._pending) == self._buffer_size:
                self._overruns += 1
            edge = RawLedEdge(self._next_seq, timestamp, int(bool(level)), interval)
            self._next_seq += 1
            self._accepted += 1
            self._last_accepted_ns = timestamp
            self._last_level = edge.level
            self._edges.append(edge)
            self._pending.append(edge)

    def start_capture(self) -> dict[str, Any]:
        with self._lock:
            self._capturing = True
            self._last_accepted_ns = None
        return self.status()

    def stop_capture(self) -> dict[str, Any]:
        with self._lock:
            self._capturing = False
        return self.status()

    def clear(self) -> dict[str, Any]:
        with self._lock:
            self._edges.clear()
            self._pending.clear()
            self._frames.clear()
            self._last_accepted_ns = None
            self._accepted = 0
            self._rejected_glitches = 0
            self._overruns = 0
            self._decoder_rejections = 0
            self._last_decoded_start_ns = None
            self._valid_frames = 0
            self._missing_frames = 0
            self._last_frame_sequence = None
        return self.status()

    def replay(self, document: dict[str, Any]) -> dict[str, Any]:
        raw_edges = document.get("edges")
        if not isinstance(raw_edges, list):
            raise ValueError("edge log must contain an edges array")
        self.clear()
        previous: int | None = None
        for item in raw_edges:
            if not isinstance(item, dict):
                raise ValueError("each edge must be an object")
            timestamp = int(item["monotonic_ns"])
            level = int(item["level"])
            if previous is not None and timestamp <= previous:
                raise ValueError("edge timestamps must increase")
            self.on_raw_edge(level, timestamp)
            previous = timestamp
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            edges = list(self._edges)
            data = self._status_locked(edges)
        return data

    def export(self) -> dict[str, Any]:
        with self._lock:
            edges = list(self._edges)
            status = self._status_locked(edges)
        return {
            "format": "pi-deck-key-led-edges",
            "version": EDGE_LOG_VERSION,
            "clock": "time.monotonic_ns",
            "clock_resolution_ns": int(time.get_clock_info("monotonic").resolution * 1_000_000_000),
            "settings": {
                "buffer_size": self._buffer_size,
                "glitch_ns": self._glitch_ns,
                "half_bit_ns": self._half_bit_ns,
                "tolerance": self._tolerance,
            },
            "status": status,
            "edges": [asdict(edge) for edge in edges],
        }

    def _status_locked(self, edges: list[RawLedEdge]) -> dict[str, Any]:
        intervals = [edge.interval_ns for edge in edges if edge.interval_ns is not None]
        stats: dict[str, int | float | None] = {
            "min_ns": min(intervals) if intervals else None,
            "median_ns": statistics.median(intervals) if intervals else None,
            "max_ns": max(intervals) if intervals else None,
        }
        latest_frame = asdict(self._frames[-1]) if self._frames else None
        return {
            "capturing": self._capturing,
            "level": self._last_level,
            "accepted_edges": self._accepted,
            "rejected_glitches": self._rejected_glitches,
            "overruns": self._overruns,
            "buffered_edges": len(edges),
            "buffer_size": self._buffer_size,
            "glitch_ns": self._glitch_ns,
            "half_bit_ns": self._half_bit_ns,
            "tolerance": self._tolerance,
            "intervals": stats,
            "valid_frames": self._valid_frames,
            "missing_frames": self._missing_frames,
            "decoder_rejections": self._decoder_rejections,
            "latest_frame": latest_frame,
        }

    async def websocket_sync(self, ws: WebSocket) -> None:
        await ws.send_json(
            self._event("sync", {"status": self.status(), "edges": self._recent_edges()})
        )

    def _recent_edges(self, limit: int = DEFAULT_BUFFER_SIZE) -> list[dict[str, Any]]:
        with self._lock:
            return [asdict(edge) for edge in list(self._edges)[-limit:]]

    def _event(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        return {"v": 1, "category": "led_comm", "type": event_type, "ts": utc_iso(), "data": data}

    async def _drain_loop(self) -> None:
        while True:
            await asyncio.sleep(0.1)
            with self._lock:
                pending = list(self._pending)
                self._pending.clear()
                edges = list(self._edges)
            if not pending:
                continue
            frames = decode_state_frames(
                edges,
                half_bit_ns=self._half_bit_ns,
                tolerance=self._tolerance,
            )
            new_frames: list[DecodedStateFrame] = []
            with self._lock:
                for frame in frames:
                    if (
                        self._last_decoded_start_ns is None
                        or frame.monotonic_ns > self._last_decoded_start_ns
                    ):
                        self._frames.append(frame)
                        self._last_decoded_start_ns = frame.monotonic_ns
                        if self._last_frame_sequence is not None:
                            advance = (frame.sequence - self._last_frame_sequence) & 0xFF
                            if advance:
                                self._missing_frames += advance - 1
                        self._last_frame_sequence = frame.sequence
                        self._valid_frames += 1
                        new_frames.append(frame)
                status = self._status_locked(list(self._edges))
            if self._hub.client_count:
                await self._hub.broadcast_json(
                    self._event(
                        "edge_batch",
                        {
                            "edges": [asdict(edge) for edge in pending[-240:]],
                            "status": status,
                            "frames": [asdict(frame) for frame in new_frames],
                        },
                    )
                )
