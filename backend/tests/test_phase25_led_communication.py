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
    _incomplete_prefix,
    _state_frame_is_unambiguous,
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


def test_state_semantics_reject_unknown_or_reserved_payloads() -> None:
    valid = decode_led_frames(
        _edges_for_frame(bytes.fromhex("ffff2dd41120232651"))
    )[0]
    assert _state_frame_is_unambiguous(valid) is True
    assert _state_frame_is_unambiguous(
        DecodedLedFrame(
            edge_seq=1,
            monotonic_ns=1,
            raw_hex="ffff2dd41100000000",
            sequence=1,
            crc=0,
            message_type="state",
            type_code=0x11,
            layout="unknown",
            input1="tb",
            input2="dp",
            connection_mask=6,
        )
    ) is False


def test_corrupt_state_triggers_one_event_driven_query() -> None:
    async def scenario() -> None:
        service = LedCommunicationService(ws_hub=WsHub())
        commands: list[tuple[int, ...]] = []

        async def sender(bits: tuple[int, ...], _bit_time_s: float) -> list[tuple[int, int]]:
            commands.append(bits)

            async def answer() -> None:
                await asyncio.sleep(0)
                await service._publish_frame(  # noqa: SLF001 - recovery correlation
                    DecodedLedFrame(
                        edge_seq=100,
                        monotonic_ns=2_000_000_000,
                        raw_hex="ffff2dd41120232651",
                        sequence=32,
                        crc=0x51,
                        message_type="state",
                        type_code=0x11,
                        layout="pbp",
                        input1="tb",
                        input2="dp",
                        connection_mask=6,
                    )
                )

            asyncio.create_task(answer())
            return [(1_900_000_000, 0)]

        service.configure_command_sender(sender)
        service.start()
        await service._publish_frame(  # noqa: SLF001 - corrupt input regression
            DecodedLedFrame(
                edge_seq=99,
                monotonic_ns=1_000_000_000,
                raw_hex="ffff2dd41130020600",
                sequence=48,
                crc=0,
                message_type="bad_crc",
                type_code=0x11,
                crc_valid=False,
                expected_crc=0xA8,
            )
        )
        await asyncio.sleep(0.2)

        assert commands == [command_bits(0)]
        assert service.status()["state_valid"] is True
        await service.stop()

    asyncio.run(scenario())


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


def test_decodes_real_1008_4_state_and_diag_vectors() -> None:
    state = decode_led_frames(_edges_for_frame(bytes.fromhex("ffff2dd411040300e5")))[0]
    assert (state.message_type, state.layout, state.input1, state.input2) == (
        "state",
        "single",
        "tb",
        "none",
    )

    diagnostic = decode_led_frames(
        _edges_for_frame(bytes.fromhex("ffff2dd415025500b2"))
    )[0]
    assert diagnostic.message_type == "diag"
    assert diagnostic.diagnostic_reads == 85
    assert diagnostic.diagnostic_errors == 0
    assert diagnostic.diagnostic_conversions_stopped is False
    assert diagnostic.diagnostic_timeouts == 0
    assert diagnostic.diagnostic_rejected_frames == 0

    presence_payload = bytes.fromhex("18030712")
    presence_raw = bytes.fromhex("ffff2dd4") + presence_payload + bytes(
        [crc8(presence_payload)]
    )
    presence = decode_led_frames(_edges_for_frame(presence_raw))[0]
    assert presence.message_type == "presence"
    assert presence.presence_mask == 0x07
    assert presence.presence_window0_state == 1
    assert presence.presence_window1_state == 2


@pytest.mark.parametrize(
    ("raw_hex", "sequence", "layout", "input1", "input2", "connection_mask"),
    [
        # Real Logic 2 captures from firmware 1008.5/a, 2026-11-05.
        ("ffff2dd41120232651", 32, "pbp", "tb", "dp", 0x06),
        ("ffff2dd4111f2326f7", 31, "pbp", "tb", "dp", 0x06),
        ("ffff2dd411112236be", 17, "pbp", "dp", "tb", 0x06),
        ("ffff2dd41112232666", 18, "pbp", "tb", "dp", 0x06),
        ("ffff2dd411042326b9", 4, "pbp", "tb", "dp", 0x06),
        ("ffff2dd411050106b6", 5, "single", "hdmi", "none", 0x06),
        ("ffff2dd41106020634", 6, "single", "dp", "none", 0x06),
        ("ffff2dd4110703064a", 7, "single", "tb", "none", 0x06),
        ("ffff2dd41108212669", 8, "pbp", "hdmi", "dp", 0x06),
        ("ffff2dd41109213672", 9, "pbp", "hdmi", "tb", 0x06),
        ("ffff2dd4110a221610", 10, "pbp", "dp", "hdmi", 0x06),
        ("ffff2dd4110b22369b", 11, "pbp", "dp", "tb", 0x06),
        ("ffff2dd4110c231678", 12, "pbp", "tb", "hdmi", 0x06),
        ("ffff2dd4110d232683", 13, "pbp", "tb", "dp", 0x06),
    ],
)
def test_decodes_real_1008_5_state_vectors(
    raw_hex: str,
    sequence: int,
    layout: str,
    input1: str,
    input2: str,
    connection_mask: int,
) -> None:
    frame = decode_led_frames(_edges_for_frame(bytes.fromhex(raw_hex)))[0]

    assert frame.message_type == "state"
    assert (
        frame.sequence,
        frame.layout,
        frame.input1,
        frame.input2,
        frame.connection_mask,
    ) == (sequence, layout, input1, input2, connection_mask)


def test_1008_0_commands_use_frozen_codeword_table_msb_first() -> None:
    assert command_frame(0) == bytes.fromhex("a55a")
    assert command_frame(7) == bytes.fromhex("a522")
    assert command_frame(0xB) == bytes.fromhex("a5ee")
    assert command_bits(0) == (1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0)
    with pytest.raises(ValueError):
        command_frame(16)


def test_command_transmission_accepts_state_while_sender_is_still_finishing() -> None:
    async def scenario() -> None:
        service = LedCommunicationService(ws_hub=WsHub())

        async def sender(bits: tuple[int, ...], bit_time_s: float) -> list[tuple[int, int]]:
            assert bits == command_bits(7)
            assert bit_time_s == 1.0
            await service._publish_frame(  # noqa: SLF001 - exercise early RX boundary
                DecodedLedFrame(
                    edge_seq=100,
                    monotonic_ns=1_067_000_000,
                    raw_hex="ffff2dd411040300e5",
                    sequence=4,
                    crc=0xE5,
                    message_type="state",
                    type_code=0x11,
                    layout="single",
                    input1="tb",
                    input2="none",
                )
            )
            return [(1_000_000_000, 1), (1_050_000_000, 0)]

        service.configure_command_sender(sender)
        result = await service.send_command(7, bit_time_ms=1000)
        assert result["status"] == "waiting_response"
        assert result["frame_hex"] == "a522"
        assert result["state"] is None
        assert result["diagnostic"] is None
        assert service.status()["tx_history"][0]["samples"][0]["level"] == 1
        await asyncio.sleep(0)
        completed = service.status()["last_command"]
        assert completed["status"] == "response"
        assert completed["state"]["raw_hex"] == "ffff2dd411040300e5"

        with pytest.raises(ValueError, match="1 and 1000"):
            await service.send_command(0, bit_time_ms=1001)

    asyncio.run(scenario())


def test_recovered_response_starting_before_final_release_is_correlated() -> None:
    async def scenario() -> None:
        service = LedCommunicationService(ws_hub=WsHub())

        async def sender(_bits: tuple[int, ...], _bit_time_s: float) -> list[tuple[int, int]]:
            return [(1_000_000_000, 1), (1_400_000_000, 0)]

        service.configure_command_sender(sender)
        result = await service.send_command(0)
        assert result["status"] == "waiting_response"
        await service._publish_frame(  # noqa: SLF001 - correlation boundary regression
            DecodedLedFrame(
                edge_seq=100,
                # Reconstructed frame start is before the final TX release, but after TX start.
                monotonic_ns=1_385_000_000,
                raw_hex="ffff2dd411382326a2",
                sequence=56,
                crc=0xA2,
                message_type="state",
                type_code=0x11,
                acquisition_recovered=True,
                layout="pbp",
                input1="tb",
                input2="dp",
                connection_mask=6,
            )
        )
        await asyncio.sleep(0)
        assert service.status()["last_command"]["status"] == "response"

    asyncio.run(scenario())


def test_tb_refresh_command_completes_on_refresh_frame() -> None:
    async def scenario() -> None:
        service = LedCommunicationService(ws_hub=WsHub())

        async def sender(bits: tuple[int, ...], bit_time_s: float) -> list[tuple[int, int]]:
            assert bits == command_bits(0xB)
            assert bit_time_s == 0.025
            await service._publish_frame(  # noqa: SLF001 - response correlation
                DecodedLedFrame(
                    edge_seq=200,
                    monotonic_ns=2_000_000_000,
                    raw_hex="ffff2dd41b200003a7",
                    sequence=0x20,
                    crc=0xA7,
                    message_type="refresh",
                    type_code=0x1B,
                    refresh_result=0x00,
                    refresh_flags=0x03,
                )
            )
            return [(1_000_000_000, 1), (1_400_000_000, 0)]

        service.configure_command_sender(sender)
        result = await service.send_command(0xB)
        assert result["frame_hex"] == "a5ee"
        assert result["command_name"] == "tb_refresh"
        await asyncio.sleep(0)
        completed = service.status()["last_command"]
        assert completed["status"] == "response"
        assert completed["refresh"]["refresh_result"] == 0x00
        assert completed["refresh"]["refresh_flags"] == 0x03

    asyncio.run(scenario())


def test_1008_5_query_completes_on_state_and_ignores_other_types() -> None:
    async def scenario() -> None:
        service = LedCommunicationService(ws_hub=WsHub())

        async def sender(bits: tuple[int, ...], bit_time_s: float) -> list[tuple[int, int]]:
            assert bits == command_bits(0)
            assert bit_time_s == 0.025
            await service._publish_frame(  # noqa: SLF001 - exercise Query correlation
                DecodedLedFrame(
                    edge_seq=100,
                    monotonic_ns=1_000_000_000,
                    raw_hex="ffff2dd411040300e5",
                    sequence=4,
                    crc=0xE5,
                    message_type="state",
                    type_code=0x11,
                    layout="single",
                    input1="tb",
                    input2="none",
                )
            )
            await service._publish_frame(  # noqa: SLF001 - exercise Query correlation
                DecodedLedFrame(
                    edge_seq=150,
                    monotonic_ns=1_500_000_000,
                    raw_hex="ffff2dd41806000000",
                    sequence=6,
                    crc=0,
                    message_type="unknown",
                    type_code=0x18,
                )
            )
            await service._publish_frame(  # noqa: SLF001 - exercise Query correlation
                DecodedLedFrame(
                    edge_seq=200,
                    monotonic_ns=2_000_000_000,
                    raw_hex="ffff2dd415025500b2",
                    sequence=2,
                    crc=0xB2,
                    message_type="diag",
                    type_code=0x15,
                    diagnostic_reads=85,
                    diagnostic_errors=0,
                )
            )
            return [(900_000_000, 1), (2_100_000_000, 0)]

        service.configure_command_sender(sender)
        result = await service.send_command(0)

        assert result["status"] == "waiting_response"
        await asyncio.sleep(0)
        completed = service.status()["last_command"]
        assert completed["status"] == "response"
        assert completed["state"]["sequence"] == 4
        assert completed["diagnostic"] is None
        assert service.status()["tx_history"][0]["status"] == "response"

    asyncio.run(scenario())


def test_diagnostic_command_reports_diag_without_presence_as_partial_response() -> None:
    async def scenario() -> None:
        service = LedCommunicationService(ws_hub=WsHub())

        async def sender(_bits: tuple[int, ...], _bit_time_s: float) -> list[tuple[int, int]]:
            await service._publish_frame(  # noqa: SLF001 - exercise diagnostic correlation
                DecodedLedFrame(
                    edge_seq=100,
                    monotonic_ns=1_000_000_000,
                    raw_hex="ffff2dd415025500b2",
                    sequence=2,
                    crc=0xB2,
                    message_type="diag",
                    type_code=0x15,
                    diagnostic_reads=85,
                    diagnostic_errors=0,
                )
            )
            return [(900_000_000, 1), (1_100_000_000, 0)]

        service.configure_command_sender(sender)
        result = await service.send_command(0xA, response_timeout_s=0.001)

        assert result["status"] == "waiting_response"
        assert service.status()["tx_history"][0]["diagnostic"]["sequence"] == 2
        await asyncio.sleep(0.01)
        completed = service.status()["last_command"]
        assert completed["status"] == "partial_response"
        assert completed["state"] is None
        assert completed["diagnostic"]["sequence"] == 2
        assert completed["presence"] is None

    asyncio.run(scenario())


def test_diagnostic_command_collects_diag_presence_then_scan() -> None:
    async def scenario() -> None:
        service = LedCommunicationService(ws_hub=WsHub())

        async def sender(_bits: tuple[int, ...], _bit_time_s: float) -> list[tuple[int, int]]:
            await service._publish_frame(  # noqa: SLF001
                DecodedLedFrame(
                    edge_seq=100,
                    monotonic_ns=1_000_000_000,
                    raw_hex="ffff2dd415025500b2",
                    sequence=2,
                    crc=0xB2,
                    message_type="diag",
                    type_code=0x15,
                    diagnostic_reads=85,
                    diagnostic_errors=0,
                )
            )
            await service._publish_frame(  # noqa: SLF001
                DecodedLedFrame(
                    edge_seq=200,
                    monotonic_ns=2_700_000_000,
                    raw_hex="ffff2dd41803071200",
                    sequence=3,
                    crc=0,
                    message_type="presence",
                    type_code=0x18,
                    presence_mask=7,
                    presence_window0_state=1,
                    presence_window1_state=2,
                )
            )
            await service._publish_frame(  # noqa: SLF001
                DecodedLedFrame(
                    edge_seq=300,
                    monotonic_ns=4_400_000_000,
                    raw_hex="ffff2dd41a04784800",
                    sequence=4,
                    crc=0,
                    message_type="scan",
                    type_code=0x1A,
                    scan_longest_gap_ms=120,
                    scan_last_ms=72,
                )
            )
            return [(900_000_000, 1), (950_000_000, 0)]

        service.configure_command_sender(sender)
        result = await service.send_command(0xA)
        assert result["status"] == "waiting_response"
        await asyncio.sleep(0)
        completed = service.status()["last_command"]
        assert completed["status"] == "response"
        assert completed["diagnostic"]["diagnostic_reads"] == 85
        assert completed["presence"]["presence_mask"] == 7
        assert completed["scan"]["scan_longest_gap_ms"] == 120

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
        live_samples: list[tuple[int, int]] = []
        deck.configure_communication_sample_listener(
            lambda monotonic_ns, level: live_samples.append((monotonic_ns, level))
        )
        samples = await deck.send_monitor_command_bits(command_bits(0), 0.001)
        assert hardware.jog_calls == []
        assert hardware.communication_calls[0] is False
        assert True in hardware.communication_calls
        assert hardware.communication_calls[-1] is False
        assert live_samples == samples

    pins = ProtoboardPins()
    assert pins.drive_center == 5
    assert pins.communication_tx == 12
    asyncio.run(scenario())


def test_command_tx_accepts_1000ms_bit_time(monkeypatch) -> None:
    sleep_calls: list[float] = []
    monkeypatch.setattr(
        "pi_deck.services.deck_control.time.sleep",
        lambda seconds: sleep_calls.append(seconds),
    )
    hub = WsHub()
    deck = DeckControlService(MockDeckHardware(), hub, LiveLogService(hub), "test")

    samples = asyncio.run(deck.send_monitor_command_bits(command_bits(0), 1.0))

    assert len(samples) == 17
    assert sleep_calls[0] == 0.100
    assert len(sleep_calls[1:]) == 16


def test_three_second_measurement_uses_only_communication_gpio(monkeypatch) -> None:
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

    sleep_calls: list[float] = []
    monkeypatch.setattr(
        "pi_deck.services.deck_control.time.sleep",
        lambda seconds: sleep_calls.append(seconds),
    )
    hardware = TrackingHardware()
    hub = WsHub()
    deck = DeckControlService(hardware, hub, LiveLogService(hub), "test")
    samples = asyncio.run(deck.hold_communication_high_for_measurement())

    assert hardware.jog_calls == []
    assert hardware.communication_calls == [False, True, False]
    assert sleep_calls == [3.0]
    assert [level for _, level in samples] == [1, 0]


def test_three_second_measurement_api(client, monkeypatch) -> None:
    async def fake_hold() -> list[tuple[int, int]]:
        return [(1_000_000_000, 1), (4_000_000_000, 0)]

    monkeypatch.setattr(
        client.app.state.deck,
        "hold_communication_high_for_measurement",
        fake_hold,
    )
    response = client.post("/api/v1/led-communication/test-high")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "duration_ms": 3000,
        "started_monotonic_ns": 1_000_000_000,
        "ended_monotonic_ns": 4_000_000_000,
    }


def test_communication_note_is_kept_in_session(client) -> None:
    response = client.post(
        "/api/v1/led-communication/note",
        json={"text": "unplugged DP"},
    )

    assert response.status_code == 200
    note = response.json()["session_history"][-1]
    assert note["direction"] == "NOTE"
    assert note["kind"] == "NOTE"
    assert note["note"] == "unplugged DP"
    assert note["timestamp"].endswith("Z")


def test_decodes_1008_7_refresh_frame() -> None:
    frame = decode_led_frames(
        _edges_for_frame(bytes.fromhex("ffff2dd41b200003a7"))
    )[0]
    assert frame.message_type == "refresh"
    assert frame.type_code == 0x1B
    assert frame.sequence == 0x20
    assert frame.refresh_result == 0x00
    assert frame.refresh_flags == 0x03


def test_decodes_1008_6_scan_and_watch_frames() -> None:
    scan = decode_led_frames(
        _edges_for_frame(bytes.fromhex("ffff2dd41a2078484d"))
    )[0]
    assert scan.message_type == "scan"
    assert scan.scan_longest_gap_ms == 120
    assert scan.scan_last_ms == 72

    saturated = decode_led_frames(
        _edges_for_frame(bytes.fromhex("ffff2dd41a24ff15af"))
    )[0]
    assert saturated.scan_longest_gap_ms == 0xFF
    assert saturated.scan_last_ms == 21

    watch = decode_led_frames(
        _edges_for_frame(bytes.fromhex("ffff2dd4194102051d"))
    )[0]
    assert watch.message_type == "watch"
    assert watch.watch_index == 2
    assert watch.watch_value == 5


def test_reports_complete_bad_crc_candidate_without_accepting_it_as_valid() -> None:
    bad = decode_led_frames(
        _edges_for_frame(bytes.fromhex("ffff2dd41130020600")),
        include_bad_crc=True,
    )[0]
    assert bad.message_type == "bad_crc"
    assert bad.crc_valid is False
    assert bad.raw_hex == "ffff2dd41130020600"
    assert bad.expected_crc == 0xA8


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


def test_recovers_real_world_17_8ms_2_2ms_half_bit_pair() -> None:
    edges = _edges_for_frame(bytes.fromhex("ffff2dd4115e01067e"))
    distorted = list(edges)
    pivot = distorted[1]
    distorted[1] = RawLedEdge(
        pivot.seq,
        pivot.monotonic_ns + 7_800_000,
        pivot.level,
        pivot.interval_ns,
    )

    frames = decode_led_frames(distorted)

    assert frames[0].raw_hex == "ffff2dd4115e01067e"
    assert frames[0].acquisition_recovered is True


def test_reports_sync_constrained_prefix_for_incomplete_frame() -> None:
    edges = _edges_for_frame(bytes.fromhex("ffff2dd4116003008b"))

    raw_prefix, bit_count = _incomplete_prefix(edges[:-35], 10_000_000)

    assert 32 <= bit_count < 72
    assert raw_prefix.startswith("ffff2dd4")


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
