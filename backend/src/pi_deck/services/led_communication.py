"""Raw KEY_LED capture plus the bidirectional custom monitor protocol.

The GPIO callback only timestamps and appends to bounded in-memory queues.  Decoding and
websocket fan-out run on the asyncio loop, away from gpiozero's helper thread.
"""

from __future__ import annotations

import asyncio
import statistics
import threading
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from typing import Any

from fastapi import WebSocket

from pi_deck.models.schemas import utc_iso
from pi_deck.services.live_log import LiveLogService
from pi_deck.services.ws_hub import WsHub

EDGE_LOG_VERSION = 1
DEFAULT_HALF_BIT_NS = 10_000_000
DEFAULT_TOLERANCE = 0.45
DEFAULT_GLITCH_NS = 1_000_000
DEFAULT_BUFFER_SIZE = 4096
SEMANTIC_SETTLE_NS = 30_000_000
BURST_GAP_NS = 30_000_000
MIN_BURST_EDGES = 4
FRAME_BITS = 72
FRAME_BYTES = 9
PREAMBLE_SYNC = bytes.fromhex("ffff2dd4")
PREAMBLE_SYNC_BITS = tuple(
    (PREAMBLE_SYNC[index // 8] >> (7 - index % 8)) & 1
    for index in range(len(PREAMBLE_SYNC) * 8)
)
MAX_RECOVERY_STATES = 256

COMMAND_CODEWORDS: dict[int, int] = {
    0x0: 0x5A,
    0x1: 0x44,
    0x2: 0x77,
    0x3: 0x69,
    0x4: 0x11,
    0x5: 0x0F,
    0x6: 0x3C,
    0x7: 0x22,
    0x8: 0xDD,
    0x9: 0xC3,
    0xA: 0xF0,
    0xB: 0xEE,
    0xC: 0x96,
    0xD: 0x88,
    0xE: 0xBB,
    0xF: 0xA5,
}
COMMAND_NAMES: dict[int, str] = {
    0x0: "query",
    0x1: "single_hdmi",
    0x2: "single_dp",
    0x3: "single_tb",
    0x4: "pbp_hdmi_dp",
    0x5: "pbp_hdmi_tb",
    0x6: "pbp_dp_hdmi",
    0x7: "pbp_dp_tb",
    0x8: "pbp_tb_hdmi",
    0x9: "pbp_tb_dp",
}


@dataclass(frozen=True)
class RawLedEdge:
    seq: int
    monotonic_ns: int
    level: int
    interval_ns: int | None


@dataclass(frozen=True)
class DecodedLedFrame:
    edge_seq: int
    monotonic_ns: int
    raw_hex: str
    sequence: int
    crc: int
    message_type: str
    type_code: int
    acquisition_recovered: bool = False
    layout: str | None = None
    input1: str | None = None
    input2: str | None = None
    level: int | None = None
    raw_value: int | None = None
    min_raw: int | None = None
    max_raw: int | None = None
    shortest_gap_ticks: int | None = None
    longest_gap_ticks: int | None = None
    ack_result: int | None = None
    ack_code: int | None = None
    measured_bit_ticks: int | None = None


def command_frame(command_code: int) -> bytes:
    """Return the frozen page-0 wire bytes; callers never synthesize a codeword."""
    if command_code not in COMMAND_CODEWORDS:
        raise ValueError("command code must be between 0 and 15")
    return bytes((0xA5, COMMAND_CODEWORDS[command_code]))


def command_bits(command_code: int) -> tuple[int, ...]:
    raw = command_frame(command_code)
    return tuple((raw[index // 8] >> (7 - index % 8)) & 1 for index in range(16))


@dataclass
class LedSemanticClassifier:
    """Turn physical edges into active-low LED state only after a stable dwell."""

    settle_ns: int = SEMANTIC_SETTLE_NS
    stable_level: int | None = None
    candidate_level: int | None = None
    candidate_since_ns: int | None = None

    def initialize(self, *, active: bool) -> None:
        level = 0 if active else 1
        self.stable_level = level
        self.candidate_level = level
        self.candidate_since_ns = None

    def observe(self, level: int, timestamp_ns: int) -> None:
        level = int(bool(level))
        if level == self.candidate_level:
            return
        self.candidate_level = level
        self.candidate_since_ns = timestamp_ns

    def poll(self, now_ns: int) -> bool | None:
        if (
            self.candidate_level is None
            or self.candidate_since_ns is None
            or self.candidate_level == self.stable_level
            or now_ns - self.candidate_since_ns < self.settle_ns
        ):
            return None
        self.stable_level = self.candidate_level
        self.candidate_since_ns = None
        return self.stable_level == 0


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
    edges: list[RawLedEdge],
    start: int,
    half_ns: int,
    tolerance: float,
    prefix_bits: tuple[int, ...] = (),
) -> tuple[bytes, int] | None:
    """Treat ``edges[start]`` as a bit-boundary edge and decode one fixed frame."""
    bits = list(prefix_bits)
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


def _decode_bits_resilient(
    edges: list[RawLedEdge],
    start: int,
    half_ns: int,
    prefix_bits: tuple[int, ...] = (),
) -> list[tuple[bytes, int]]:
    """Bounded recovery for duty-distorted edges, still gated by sync and CRC later.

    The conditioned input sometimes reports two real half-bit phases as roughly 16+4 ms.
    Search both interpretations in the overlapping timing region, prefer pairs whose combined
    duration is one full bit, and prune against the fixed preamble/sync as bits are produced.
    """
    value = 0
    for bit in prefix_bits:
        value = (value << 1) | bit
    states: list[tuple[int, int, int]] = [(0, start, value)]  # score, edge position, bits

    for bit_index in range(len(prefix_bits), FRAME_BITS):
        expected = PREAMBLE_SYNC_BITS[bit_index] if bit_index < len(PREAMBLE_SYNC_BITS) else None
        next_states: dict[tuple[int, int], int] = {}
        for score, pos, bits in states:
            if pos + 1 >= len(edges):
                continue
            delta = edges[pos + 1].monotonic_ns - edges[pos].monotonic_ns

            if expected in (None, 0) and half_ns * 1.45 <= delta <= half_ns * 2.75:
                key = (pos + 1, bits << 1)
                candidate_score = score + abs(delta - half_ns * 2)
                next_states[key] = min(next_states.get(key, candidate_score), candidate_score)

            if expected in (None, 1) and pos + 2 < len(edges):
                delta2 = edges[pos + 2].monotonic_ns - edges[pos + 1].monotonic_ns
                if (
                    half_ns * 0.30 <= delta <= half_ns * 1.75
                    and half_ns * 0.30 <= delta2 <= half_ns * 1.75
                ):
                    key = (pos + 2, (bits << 1) | 1)
                    # The pair sum is much more stable than either phase on the real input.
                    candidate_score = score + abs(delta + delta2 - half_ns * 2)
                    next_states[key] = min(
                        next_states.get(key, candidate_score), candidate_score
                    )

        states = sorted(
            (score, pos, bits) for (pos, bits), score in next_states.items()
        )[:MAX_RECOVERY_STATES]
        if not states:
            return []

    return [(bits.to_bytes(FRAME_BYTES, "big"), pos) for _, pos, bits in states]


def decode_led_frames(
    edges: list[RawLedEdge],
    *,
    half_bit_ns: int = DEFAULT_HALF_BIT_NS,
    tolerance: float = DEFAULT_TOLERANCE,
    allow_recovery: bool = True,
) -> list[DecodedLedFrame]:
    """Decode CRC-valid STATE/LEVEL and 1008.0 diagnostic/ACK frames."""
    frames: list[DecodedLedFrame] = []
    seen_frames: set[tuple[bytes, int]] = set()
    for start in range(max(0, len(edges) - 512), len(edges)):
        # Hardware captures show that the first preamble bit can be swallowed by the
        # receiver's turn-on transient (about 16 ms + 4 ms instead of 10 ms + 10 ms).
        # The second attempt recovers only that known leading preamble bit; sync and CRC still
        # have to validate the complete 72-bit frame.
        candidates: list[tuple[bytes, int, bool]] = []
        direct = _decode_bits_from(
            edges,
            start,
            half_bit_ns,
            tolerance,
        )
        if direct is not None:
            candidates.append((*direct, False))
        prefixed = _decode_bits_from(
            edges,
            start,
            half_bit_ns,
            tolerance,
            (1,),
        )
        if prefixed is not None:
            candidates.append((*prefixed, True))
        if allow_recovery and not candidates:
            candidates.extend(
                (*decoded, True)
                for decoded in _decode_bits_resilient(
                    edges,
                    start,
                    half_bit_ns,
                )
            )
            candidates.extend(
                (*decoded, True)
                for decoded in _decode_bits_resilient(
                    edges,
                    start,
                    half_bit_ns,
                    (1,),
                )
            )

        for raw, end, recovered in candidates:
            if raw[:4] != PREAMBLE_SYNC or crc8(raw[4:8]) != raw[8]:
                continue
            marker = (raw, edges[end].seq)
            if marker in seen_frames:
                continue
            seen_frames.add(marker)
            start_ns = edges[start].monotonic_ns - (half_bit_ns * 2 if recovered else 0)
            common = {
                "edge_seq": edges[end].seq,
                "monotonic_ns": start_ns,
                "raw_hex": raw.hex(),
                "sequence": raw[5],
                "crc": raw[8],
                "type_code": raw[4],
                "acquisition_recovered": recovered,
            }
            if raw[4] == 0x11:
                state = raw[6]
                layout_code = state >> 4
                input1_code = state & 0x0F
                input2_code = raw[7] >> 4
                inputs = {0: "none", 1: "hdmi", 2: "dp", 3: "tb"}
                frames.append(
                    DecodedLedFrame(
                        **common,
                        message_type="state",
                        layout={0: "single", 1: "pip", 2: "pbp"}.get(
                            layout_code, "unknown"
                        ),
                        input1=inputs.get(input1_code, "unknown"),
                        input2=inputs.get(input2_code, "unknown"),
                    )
                )
            elif raw[4] == 0x12:
                frames.append(
                    DecodedLedFrame(
                        **common,
                        message_type="level",
                        level=raw[6],
                        raw_value=raw[7],
                    )
                )
            elif raw[4] == 0x13:
                frames.append(
                    DecodedLedFrame(
                        **common,
                        message_type="hold",
                        min_raw=raw[6],
                        max_raw=raw[7],
                    )
                )
            elif raw[4] == 0x14:
                frames.append(
                    DecodedLedFrame(
                        **common,
                        message_type="rate",
                        shortest_gap_ticks=raw[6],
                        longest_gap_ticks=raw[7],
                    )
                )
            elif raw[4] == 0x16:
                frames.append(
                    DecodedLedFrame(
                        **common,
                        message_type="ack",
                        ack_result=raw[6] >> 4,
                        ack_code=raw[6] & 0x0F,
                        measured_bit_ticks=raw[7],
                    )
                )
            else:
                frames.append(DecodedLedFrame(**common, message_type="unknown"))
    return frames


def decode_state_frames(
    edges: list[RawLedEdge],
    *,
    half_bit_ns: int = DEFAULT_HALF_BIT_NS,
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[DecodedLedFrame]:
    """Backward-compatible STATE-only view over the multi-type decoder."""
    return [
        frame
        for frame in decode_led_frames(
            edges,
            half_bit_ns=half_bit_ns,
            tolerance=tolerance,
        )
        if frame.message_type == "state"
    ]


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
        live_log: LiveLogService | None = None,
    ) -> None:
        self._hub = ws_hub
        self._live_log = live_log
        self._buffer_size = max(256, buffer_size)
        self._glitch_ns = max(0, glitch_ns)
        self._half_bit_ns = half_bit_ns
        self._tolerance = tolerance
        self._lock = threading.Lock()
        self._edges: deque[RawLedEdge] = deque(maxlen=self._buffer_size)
        self._pending: deque[RawLedEdge] = deque(maxlen=self._buffer_size)
        self._frames: deque[DecodedLedFrame] = deque(maxlen=64)
        self._latest_state: DecodedLedFrame | None = None
        self._latest_level: DecodedLedFrame | None = None
        self._latest_ack: DecodedLedFrame | None = None
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
        self._semantic = LedSemanticClassifier()
        self._semantic_callback: Callable[[bool], Awaitable[None]] | None = None
        self._burst_start_ns: int | None = None
        self._burst_last_ns: int | None = None
        self._burst_edge_count = 0
        self._burst_valid = False
        self._ended_rejected_bursts: deque[tuple[int, int]] = deque()
        self._drain_task: asyncio.Task[None] | None = None
        self._command_sender: (
            Callable[[tuple[int, ...], float], Awaitable[list[tuple[int, int]]]] | None
        ) = None
        self._command_lock = asyncio.Lock()
        self._ack_waiter: tuple[int, asyncio.Future[DecodedLedFrame]] | None = None
        self._last_command: dict[str, Any] | None = None
        self._tx_history: deque[dict[str, Any]] = deque(maxlen=64)

    def configure_command_sender(
        self,
        sender: Callable[[tuple[int, ...], float], Awaitable[list[tuple[int, int]]]],
    ) -> None:
        self._command_sender = sender

    async def send_command(
        self,
        command_code: int,
        *,
        bit_time_ms: int = 50,
        ack_timeout_s: float = 3.0,
    ) -> dict[str, Any]:
        """Transmit one page-0 command and wait for the matching LED ACK."""
        if command_code not in COMMAND_CODEWORDS:
            raise ValueError("command code must be between 0 and 15")
        if not 1 <= bit_time_ms <= 50:
            raise ValueError("bit_time_ms must be between 1 and 50")
        if self._command_sender is None:
            raise RuntimeError("monitor command transmitter is unavailable")
        with self._lock:
            if not self._capturing:
                raise RuntimeError("resume LED capture before sending a monitor command")

        async with self._command_lock:
            loop = asyncio.get_running_loop()
            waiter: asyncio.Future[DecodedLedFrame] = loop.create_future()
            self._ack_waiter = (command_code, waiter)
            sent = {
                "command_code": command_code,
                "command_name": COMMAND_NAMES.get(command_code, "reserved"),
                "frame_hex": command_frame(command_code).hex(),
                "bit_time_ms": bit_time_ms,
                "status": "waiting_ack",
            }
            self._last_command = sent
            try:
                samples = await self._command_sender(
                    command_bits(command_code), bit_time_ms / 1000
                )
                transmission = {
                    **sent,
                    "monotonic_ns": samples[0][0] if samples else time.monotonic_ns(),
                    "samples": [
                        {"monotonic_ns": timestamp, "level": level}
                        for timestamp, level in samples
                    ],
                }
                with self._lock:
                    self._tx_history.append(transmission)
                if self._hub.client_count:
                    await self._hub.broadcast_json(
                        self._event(
                            "tx",
                            {"transmission": transmission, "status": self.status()},
                        )
                    )
                ack = await asyncio.wait_for(waiter, timeout=ack_timeout_s)
                result = {**sent, "status": "ack", "ack": asdict(ack)}
            except TimeoutError:
                result = {**sent, "status": "timeout", "ack": None}
            finally:
                if self._ack_waiter is not None and self._ack_waiter[1] is waiter:
                    self._ack_waiter = None
            self._last_command = result
            if "transmission" in locals():
                with self._lock:
                    transmission["status"] = result["status"]
                    transmission["ack"] = result["ack"]
                if self._hub.client_count:
                    await self._hub.broadcast_json(
                        self._event(
                            "command_result",
                            {"transmission": transmission, "status": self.status()},
                        )
                    )
            return result

    def configure_semantic_led(
        self,
        *,
        initial_active: bool,
        callback: Callable[[bool], Awaitable[None]],
    ) -> None:
        with self._lock:
            self._semantic.initialize(active=initial_active)
            self._semantic_callback = callback

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
        physical_level = int(bool(level))
        with self._lock:
            self._last_level = physical_level
            self._semantic.observe(physical_level, timestamp)
            if not self._capturing:
                return
            interval = (
                None if self._last_accepted_ns is None else timestamp - self._last_accepted_ns
            )
            if interval is not None and interval < self._glitch_ns:
                self._rejected_glitches += 1
                return
            if len(self._edges) == self._buffer_size or len(self._pending) == self._buffer_size:
                self._overruns += 1
            previous_ns = self._last_accepted_ns
            edge = RawLedEdge(self._next_seq, timestamp, physical_level, interval)
            self._next_seq += 1
            self._accepted += 1
            self._last_accepted_ns = timestamp
            self._edges.append(edge)
            self._pending.append(edge)
            if interval is not None and interval <= BURST_GAP_NS:
                if self._burst_start_ns is None:
                    self._burst_start_ns = previous_ns
                    self._burst_edge_count = 2
                else:
                    self._burst_edge_count += 1
                self._burst_last_ns = timestamp
            else:
                self._finish_burst_locked()

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
            self._latest_state = None
            self._latest_level = None
            self._latest_ack = None
            self._tx_history.clear()
            self._last_command = None
            self._last_accepted_ns = None
            self._accepted = 0
            self._rejected_glitches = 0
            self._overruns = 0
            self._decoder_rejections = 0
            self._last_decoded_start_ns = None
            self._valid_frames = 0
            self._missing_frames = 0
            self._last_frame_sequence = None
            self._burst_start_ns = None
            self._burst_last_ns = None
            self._burst_edge_count = 0
            self._burst_valid = False
            self._ended_rejected_bursts.clear()
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
        latest_message = asdict(self._frames[-1]) if self._frames else None
        latest_state = asdict(self._latest_state) if self._latest_state is not None else None
        latest_level = asdict(self._latest_level) if self._latest_level is not None else None
        latest_ack = asdict(self._latest_ack) if self._latest_ack is not None else None
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
            "latest_message": latest_message,
            "latest_state": latest_state,
            "latest_level": latest_level,
            "latest_ack": latest_ack,
            "last_command": self._last_command,
            "frame_history": [asdict(frame) for frame in self._frames],
            "tx_history": list(self._tx_history),
            # Kept for clients deployed before 1007.9; it always means latest STATE.
            "latest_frame": latest_state,
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
        ui_pending: list[RawLedEdge] = []
        ui_frames: list[DecodedLedFrame] = []
        last_ui_send_ns = time.monotonic_ns()
        while True:
            await asyncio.sleep(0.01)
            now_ns = time.monotonic_ns()
            with self._lock:
                pending = list(self._pending)
                self._pending.clear()
                edges = list(self._edges)
                semantic_active = self._semantic.poll(now_ns)
                burst_ended = bool(
                    self._burst_last_ns is not None
                    and now_ns - self._burst_last_ns >= BURST_GAP_NS
                )
            if semantic_active is not None and self._semantic_callback is not None:
                await self._semantic_callback(semantic_active)

            ui_pending.extend(pending)
            new_frames: list[DecodedLedFrame] = []
            if pending or burst_ended:
                frames = decode_led_frames(
                    edges,
                    half_bit_ns=self._half_bit_ns,
                    tolerance=self._tolerance,
                    allow_recovery=burst_ended,
                )
                with self._lock:
                    for frame in frames:
                        if (
                            self._last_decoded_start_ns is None
                            or frame.monotonic_ns > self._last_decoded_start_ns
                        ):
                            self._frames.append(frame)
                            if frame.message_type == "state":
                                self._latest_state = frame
                            elif frame.message_type == "level":
                                self._latest_level = frame
                            elif frame.message_type == "ack":
                                self._latest_ack = frame
                            self._last_decoded_start_ns = frame.monotonic_ns
                            if self._last_frame_sequence is not None:
                                advance = (frame.sequence - self._last_frame_sequence) & 0xFF
                                if advance:
                                    self._missing_frames += advance - 1
                            self._last_frame_sequence = frame.sequence
                            self._valid_frames += 1
                            self._burst_valid = True
                            new_frames.append(frame)

            if burst_ended:
                with self._lock:
                    self._finish_burst_locked()

            for frame in new_frames:
                await self._publish_frame(frame)
            ui_frames.extend(new_frames)

            with self._lock:
                rejected_bursts = list(self._ended_rejected_bursts)
                self._ended_rejected_bursts.clear()
            if self._live_log is not None:
                for edge_count, duration_ns in rejected_bursts:
                    await self._live_log.publish(
                        level="warning",
                        source="led_comm",
                        message=(
                            f"rejected LED burst - {edge_count} edges, "
                            f"{duration_ns / 1_000_000:.1f}ms, no valid frame"
                        ),
                    )

            if now_ns - last_ui_send_ns >= 100_000_000 and (ui_pending or ui_frames):
                with self._lock:
                    status = self._status_locked(list(self._edges))
                if self._hub.client_count:
                    await self._hub.broadcast_json(
                        self._event(
                            "edge_batch",
                            {
                                "edges": [asdict(edge) for edge in ui_pending[-240:]],
                                "status": status,
                                "frames": [asdict(frame) for frame in ui_frames],
                            },
                        )
                    )
                ui_pending.clear()
                ui_frames.clear()
                last_ui_send_ns = now_ns

    def _finish_burst_locked(self) -> None:
        if (
            self._burst_start_ns is not None
            and self._burst_last_ns is not None
            and self._burst_edge_count >= MIN_BURST_EDGES
            and not self._burst_valid
        ):
            self._decoder_rejections += 1
            self._ended_rejected_bursts.append(
                (self._burst_edge_count, self._burst_last_ns - self._burst_start_ns)
            )
        self._burst_start_ns = None
        self._burst_last_ns = None
        self._burst_edge_count = 0
        self._burst_valid = False

    async def _publish_frame(self, frame: DecodedLedFrame) -> None:
        if frame.message_type == "ack" and self._ack_waiter is not None:
            expected_code, waiter = self._ack_waiter
            # RESULT 8/9 frames report CODE 0 because no valid codeword survived; since
            # commands are strictly serialized, they still belong to the sole pending send.
            if (
                frame.ack_code == expected_code or frame.ack_result in (8, 9)
            ) and not waiter.done():
                waiter.set_result(frame)
        if self._hub.client_count:
            await self._hub.broadcast_json(self._event("frame", asdict(frame)))
        if self._live_log is not None:
            acquisition = " acquisition=recovered" if frame.acquisition_recovered else ""
            if frame.message_type == "state":
                message = (
                    f"STATE frame - seq={frame.sequence} layout={frame.layout} "
                    f"input1={frame.input1} input2={frame.input2} CRC=valid{acquisition}"
                )
            elif frame.message_type == "level":
                message = (
                    f"LEVEL frame - seq={frame.sequence} level={frame.level} "
                    f"raw=0x{frame.raw_value:02X} CRC=valid{acquisition}"
                )
            elif frame.message_type == "hold":
                message = (
                    f"HOLD frame - seq={frame.sequence} min_raw=0x{frame.min_raw:02X} "
                    f"max_raw=0x{frame.max_raw:02X} CRC=valid{acquisition}"
                )
            elif frame.message_type == "rate":
                message = (
                    f"RATE frame - seq={frame.sequence} shortest={frame.shortest_gap_ticks} "
                    f"longest={frame.longest_gap_ticks} ticks CRC=valid{acquisition}"
                )
            elif frame.message_type == "ack":
                message = (
                    f"ACK frame - seq={frame.sequence} result={frame.ack_result} "
                    f"code={frame.ack_code} measured={frame.measured_bit_ticks} ticks "
                    f"CRC=valid{acquisition}"
                )
            else:
                message = (
                    f"unknown LED frame - seq={frame.sequence} "
                    f"type=0x{frame.type_code:02X} CRC=valid{acquisition}"
                )
            await self._live_log.publish(level="info", source="led_comm", message=message)
