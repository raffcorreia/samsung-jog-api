from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pi_deck.api.app import create_app
from pi_deck.services.led_communication import (
    RawLedEdge,
    crc8,
    decode_state_frames,
)


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


def _edges_for_frame(raw: bytes, *, half_ns: int = 10_000_000, leading_garbage: bool = False):
    bits = [(raw[index // 8] >> (7 - index % 8)) & 1 for index in range(len(raw) * 8)]
    slots: list[int] = []
    for slot in range(len(bits) * 2):
        if slot % 2 == 0 or bits[slot // 2]:
            slots.append(slot)
    slots.append(len(bits) * 2)
    timestamp = 1_000_000_000
    level = 0
    result: list[RawLedEdge] = []
    if leading_garbage:
        result.extend(
            [
                RawLedEdge(0, timestamp - 75_000_000, 1, None),
                RawLedEdge(1, timestamp - 43_000_000, 0, 32_000_000),
            ]
        )
    offset = len(result)
    previous = result[-1].monotonic_ns if result else None
    for index, slot in enumerate(slots):
        edge_ts = timestamp + slot * half_ns
        level ^= 1
        result.append(
            RawLedEdge(
                offset + index,
                edge_ts,
                level,
                None if previous is None else edge_ts - previous,
            )
        )
        previous = edge_ts
    return result


def test_crc_matches_1007_7_golden_vector() -> None:
    assert crc8(bytes.fromhex("11002320")) == 0x00
    assert crc8(bytes.fromhex("11011130")) == 0xC8


def test_decodes_1007_7_state_frame_after_garbage() -> None:
    edges = _edges_for_frame(bytes.fromhex("ffff2dd41100232000"), leading_garbage=True)
    frames = decode_state_frames(edges)
    assert len(frames) == 1
    frame = frames[0]
    assert frame.sequence == 0
    assert frame.layout == "pbp"
    assert frame.input1 == "tb"
    assert frame.input2 == "dp"


def test_decoder_is_polarity_independent() -> None:
    edges = _edges_for_frame(bytes.fromhex("ffff2dd411011130c8"))
    inverted = [RawLedEdge(e.seq, e.monotonic_ns, 1 - e.level, e.interval_ns) for e in edges]
    assert decode_state_frames(edges)[0].raw_hex == "ffff2dd411011130c8"
    assert decode_state_frames(inverted)[0].raw_hex == "ffff2dd411011130c8"


def test_rejects_corrupt_crc_and_truncated_frame() -> None:
    corrupt = _edges_for_frame(bytes.fromhex("ffff2dd41100232001"))
    valid = _edges_for_frame(bytes.fromhex("ffff2dd41100232000"))
    assert decode_state_frames(corrupt) == []
    assert decode_state_frames(valid[:-5]) == []


def test_led_communication_rest_api(client) -> None:
    initial = client.get("/api/v1/led-communication/status")
    assert initial.status_code == 200
    assert initial.json()["capturing"] is True

    stopped = client.post("/api/v1/led-communication/stop")
    assert stopped.status_code == 200
    assert stopped.json()["capturing"] is False

    started = client.post("/api/v1/led-communication/start")
    assert started.json()["capturing"] is True

    exported = client.get("/api/v1/led-communication/export")
    assert exported.status_code == 200
    assert exported.json()["format"] == "pi-deck-key-led-edges"

    bad_replay = client.post("/api/v1/led-communication/replay", json={"edges": "bad"})
    assert bad_replay.status_code == 400
