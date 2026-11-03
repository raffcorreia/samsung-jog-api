from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from pi_deck.api.app import create_app
from pi_deck.hardware.protoboard_pins import JogAction, ProtoboardPins
from pi_deck.services.deck_control import DeckControlService
from pi_deck.services.hardware_facade import MockDeckHardware
from pi_deck.services.led_communication import (
    DecodedLedFrame,
    LedCommunicationService,
    LedSemanticClassifier,
    RawLedEdge,
    command_bits,
    command_frame,
    crc8,
    decode_led_frames,
    decode_state_frames,
)
from pi_deck.services.live_log import LiveLogService
from pi_deck.services.ws_hub import WsHub


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


def test_crc_matches_1007_8_golden_vector() -> None:
    assert crc8(bytes.fromhex("11002320")) == 0x00
    assert crc8(bytes.fromhex("11011130")) == 0xC8


def test_decodes_1007_8_state_frame_after_garbage() -> None:
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


def test_decodes_1007_9_level_and_shared_sequence_frames() -> None:
    level_edges = _edges_for_frame(bytes.fromhex("ffff2dd4120102309a"))
    level = decode_led_frames(level_edges)[0]
    assert level.message_type == "level"
    assert level.sequence == 1
    assert level.level == 2
    assert level.raw_value == 0x30

    state_edges = _edges_for_frame(bytes.fromhex("ffff2dd4110502009b"))
    state = decode_led_frames(state_edges)[0]
    assert state.message_type == "state"
    assert state.sequence == 5
    assert state.layout == "single"
    assert state.input1 == "dp"


def test_decodes_1008_0_ack_hold_and_rate_frames() -> None:
    ack = decode_led_frames(_edges_for_frame(bytes.fromhex("ffff2dd41610003126")))[0]
    assert ack.message_type == "ack"
    assert ack.ack_result == 0
    assert ack.ack_code == 0
    assert ack.measured_bit_ticks == 0x31

    hold_payload = bytes.fromhex("13205456")
    hold_raw = bytes.fromhex("ffff2dd4") + hold_payload + bytes([crc8(hold_payload)])
    hold = decode_led_frames(_edges_for_frame(hold_raw))[0]
    assert (hold.message_type, hold.min_raw, hold.max_raw) == ("hold", 0x54, 0x56)

    rate_payload = bytes.fromhex("14210308")
    rate_raw = bytes.fromhex("ffff2dd4") + rate_payload + bytes([crc8(rate_payload)])
    rate = decode_led_frames(_edges_for_frame(rate_raw))[0]
    assert (rate.message_type, rate.shortest_gap_ticks, rate.longest_gap_ticks) == (
        "rate",
        3,
        8,
    )


def test_1008_0_commands_use_frozen_codeword_table_msb_first() -> None:
    assert command_frame(0) == bytes.fromhex("a55a")
    assert command_frame(7) == bytes.fromhex("a522")
    assert command_bits(0) == (1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0)
    with pytest.raises(ValueError):
        command_frame(16)


def test_command_transmission_waits_for_matching_ack() -> None:
    async def scenario() -> None:
        service = LedCommunicationService(ws_hub=WsHub())

        async def sender(bits: tuple[int, ...], bit_time_s: float) -> list[tuple[int, int]]:
            assert bits == command_bits(7)
            assert bit_time_s == 0.05
            await service._publish_frame(  # noqa: SLF001 - exercise ACK correlation boundary
                DecodedLedFrame(
                    edge_seq=100,
                    monotonic_ns=1_000_000_000,
                    raw_hex="ffff2dd41611073126",
                    sequence=0x11,
                    crc=0x26,
                    message_type="ack",
                    type_code=0x16,
                    ack_result=0,
                    ack_code=7,
                    measured_bit_ticks=0x31,
                )
            )
            return [(1_000_000_000, 1), (1_050_000_000, 0)]

        service.configure_command_sender(sender)
        result = await service.send_command(7)
        assert result["status"] == "ack"
        assert result["frame_hex"] == "a522"
        assert result["ack"]["ack_code"] == 7
        assert service.status()["tx_history"][0]["samples"][0]["level"] == 1

        with pytest.raises(ValueError, match="1 and 50"):
            await service.send_command(0, bit_time_ms=51)

    asyncio.run(scenario())


def test_command_tx_uses_dedicated_gpio_not_native_center_branch() -> None:
    class TrackingHardware(MockDeckHardware):
        def __init__(self) -> None:
            super().__init__()
            self.jog_calls: list[tuple[JogAction, bool]] = []
            self.communication_calls: list[bool] = []

        def set_jog_line(self, action: JogAction, active: bool) -> None:
            self.jog_calls.append((action, active))
            super().set_jog_line(action, active)

        def set_communication_line(self, active: bool) -> None:
            self.communication_calls.append(active)
            super().set_communication_line(active)

    async def scenario() -> None:
        hardware = TrackingHardware()
        hub = WsHub()
        deck = DeckControlService(hardware, hub, LiveLogService(hub), "test")
        await deck.send_monitor_command_bits(command_bits(0), 0.001)
        assert hardware.jog_calls == []
        assert hardware.communication_calls[0] is False
        assert True in hardware.communication_calls
        assert hardware.communication_calls[-1] is False

    pins = ProtoboardPins()
    assert pins.drive_center == 5
    assert pins.communication_tx == 12
    asyncio.run(scenario())


def test_keeps_crc_valid_unknown_type_for_forward_compatibility() -> None:
    payload = bytes.fromhex("18060000")
    raw = bytes.fromhex("ffff2dd4") + payload + bytes([crc8(payload)])
    frame = decode_led_frames(_edges_for_frame(raw))[0]
    assert frame.message_type == "unknown"
    assert frame.type_code == 0x18
    assert frame.sequence == 6


def test_recovers_frame_after_first_preamble_bit_is_distorted() -> None:
    edges = _edges_for_frame(bytes.fromhex("ffff2dd4120102309a"))
    # The live conditioned input can distort the first two transitions into 16 ms + 4 ms.
    # Acquisition resumes at the following bit boundary, one known preamble bit late.
    recovered = decode_led_frames(edges[2:])
    assert len(recovered) == 1
    assert recovered[0].raw_hex == "ffff2dd4120102309a"
    assert recovered[0].acquisition_recovered is True


def test_accepts_asymmetric_short_phase_pair_with_valid_crc() -> None:
    edges = _edges_for_frame(bytes.fromhex("ffff2dd4110502009b"))
    distorted = list(edges)
    pivot = distorted[12]
    distorted[12] = RawLedEdge(
        pivot.seq,
        pivot.monotonic_ns + 4_000_000,
        pivot.level,
        pivot.interval_ns,
    )
    frames = decode_led_frames(distorted)
    assert frames[0].raw_hex == "ffff2dd4110502009b"


def test_recovers_repeated_16ms_4ms_half_bit_pairs() -> None:
    edges = _edges_for_frame(bytes.fromhex("ffff2dd4120102309a"))
    distorted = list(edges)
    for index in (1, 7, 13):
        edge = distorted[index]
        distorted[index] = RawLedEdge(
            edge.seq,
            edge.monotonic_ns + 6_000_000,
            edge.level,
            edge.interval_ns,
        )
    frames = decode_led_frames(distorted)
    assert frames[0].raw_hex == "ffff2dd4120102309a"
    assert frames[0].acquisition_recovered is True


def test_rejects_corrupt_crc_and_truncated_frame() -> None:
    corrupt = _edges_for_frame(bytes.fromhex("ffff2dd41100232001"))
    valid = _edges_for_frame(bytes.fromhex("ffff2dd41100232000"))
    assert decode_state_frames(corrupt) == []
    assert decode_state_frames(valid[:-5]) == []


def test_semantic_led_waits_for_stable_level_and_ignores_fast_burst() -> None:
    classifier = LedSemanticClassifier()
    classifier.initialize(active=False)

    classifier.observe(0, 1_000_000_000)
    assert classifier.poll(1_029_000_000) is None
    assert classifier.poll(1_030_000_000) is True

    classifier.observe(1, 2_000_000_000)
    assert classifier.poll(2_010_000_000) is None
    classifier.observe(0, 2_010_000_000)
    assert classifier.poll(2_020_000_000) is None
    classifier.observe(1, 2_020_000_000)
    assert classifier.poll(2_040_000_000) is None


def test_led_communication_rest_api(client) -> None:
    initial = client.get("/api/v1/led-communication/status")
    assert initial.status_code == 200
    assert initial.json()["capturing"] is True

    stopped = client.post("/api/v1/led-communication/stop")
    assert stopped.status_code == 200
    assert stopped.json()["capturing"] is False

    paused_command = client.post(
        "/api/v1/led-communication/command",
        json={"command_code": 0, "bit_time_ms": 50},
    )
    assert paused_command.status_code == 409

    started = client.post("/api/v1/led-communication/start")
    assert started.json()["capturing"] is True

    invalid_command = client.post(
        "/api/v1/led-communication/command",
        json={"command_code": 16, "bit_time_ms": 50},
    )
    assert invalid_command.status_code == 400

    exported = client.get("/api/v1/led-communication/export")
    assert exported.status_code == 200
    assert exported.json()["format"] == "pi-deck-key-led-edges"

    bad_replay = client.post("/api/v1/led-communication/replay", json={"edges": "bad"})
    assert bad_replay.status_code == 400
