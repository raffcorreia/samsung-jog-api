"""Phase 10: REST validation, websocket envelope, command rejection responses."""

from __future__ import annotations

import asyncio
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from pi_deck.api.app import create_app
from pi_deck.models.schemas import CommandRejectedReason
from pi_deck.services.deck_control import DeckControlService
from pi_deck.services.hardware_facade import MockDeckHardware
from pi_deck.services.ws_hub import WsHub


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as c:
        yield c


def test_health_includes_version(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_status_mock(client: TestClient) -> None:
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    body = r.json()
    assert body["hardware"] == "mock"
    assert body["operating_mode"] == "jog"
    assert body["control_state"] == "idle"
    assert "signals" in body


def test_set_operating_mode(client: TestClient) -> None:
    r = client.post("/api/v1/mode", json={"mode": "ddc"})
    assert r.status_code == 200
    assert r.json()["operating_mode"] == "ddc"


def test_jog_press_validation(client: TestClient) -> None:
    r = client.post("/api/v1/jog/press", json={"action": "up", "duration_ms": 0})
    assert r.status_code == 422


def test_jog_press_ok(client: TestClient) -> None:
    r = client.post("/api/v1/jog/press", json={"action": "up", "duration_ms": 5})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_websocket_connected_envelope(client: TestClient) -> None:
    with client.websocket_connect("/ws/events") as ws:
        raw = ws.receive_text()
        msg = json.loads(raw)
        assert msg["v"] == 1
        assert msg["category"] == "control"
        assert msg["type"] == "connected"
        assert "status" in msg["data"]


def test_websocket_receives_command_accept_after_jog(client: TestClient) -> None:
    """Integrated: REST jog while WS client connected must stream command/accepted."""
    with client.websocket_connect("/ws/events") as ws:
        ws.receive_text()
        r = client.post("/api/v1/jog/press", json={"action": "up", "duration_ms": 8})
        assert r.status_code == 200
        accepted = False
        for _ in range(12):
            msg = json.loads(ws.receive_text())
            if msg.get("category") == "command" and msg.get("type") == "accepted":
                assert msg["data"].get("action") == "up"
                accepted = True
                break
        assert accepted, "expected command/accepted on websocket"


def test_concurrent_jog_rejects_second_command() -> None:
    """While a slow pulse runs, a second jog_press must return CONCURRENT_COMMAND."""

    class SlowMock(MockDeckHardware):
        def pulse(self, action, duration_s: float) -> None:
            import time

            time.sleep(0.2)

    deck = DeckControlService(SlowMock(), WsHub(), "test")

    async def body() -> None:
        t = asyncio.create_task(deck.jog_press("up", 200))
        await asyncio.sleep(0)
        r2 = await deck.jog_press("left", 10)
        assert r2 == CommandRejectedReason.CONCURRENT_COMMAND
        await t
        assert await deck.jog_press("left", 10) is None

    asyncio.run(body())


def test_jog_down_up_roundtrip(client: TestClient) -> None:
    r = client.post("/api/v1/jog/down", json={"action": "right"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "hold_token" in body
    token = body["hold_token"]
    r2 = client.post("/api/v1/jog/up", json={"hold_token": token})
    assert r2.status_code == 200
    up_body = r2.json()
    assert up_body["ok"] is True
    assert "duration_ms" in up_body
    assert up_body["duration_ms"] >= 0


def test_jog_up_duplicate_token_returns_unknown(client: TestClient) -> None:
    """Second jog/up with the same token after a successful release is rejected."""
    r = client.post("/api/v1/jog/down", json={"action": "up"})
    assert r.status_code == 200
    token = r.json()["hold_token"]
    assert client.post("/api/v1/jog/up", json={"hold_token": token}).status_code == 200
    r2 = client.post("/api/v1/jog/up", json={"hold_token": token})
    assert r2.status_code == 409
    assert r2.json()["reason"] == "unknown_hold_token"


def test_jog_up_without_prior_hold_returns_unknown(client: TestClient) -> None:
    fake = str(uuid.uuid4())
    r = client.post("/api/v1/jog/up", json={"hold_token": fake})
    assert r.status_code == 409
    assert r.json()["reason"] == "unknown_hold_token"


def test_two_simultaneous_holds_same_deck(client: TestClient) -> None:
    """Multitouch: two directions can be held at once with independent tokens."""
    a = client.post("/api/v1/jog/down", json={"action": "up"})
    b = client.post("/api/v1/jog/down", json={"action": "left"})
    assert a.status_code == 200
    assert b.status_code == 200
    ta = a.json()["hold_token"]
    tb = b.json()["hold_token"]
    assert ta != tb
    assert client.post("/api/v1/jog/up", json={"hold_token": ta}).status_code == 200
    assert client.post("/api/v1/jog/up", json={"hold_token": tb}).status_code == 200


def test_concurrent_hold_allows_second_down() -> None:
    deck = DeckControlService(MockDeckHardware(), WsHub(), "test")

    async def body() -> None:
        err1, t1 = await deck.jog_down("up")
        err2, t2 = await deck.jog_down("left")
        assert err1 is None and t1 is not None
        assert err2 is None and t2 is not None
        assert t1 != t2
        e1, _ms1 = await deck.jog_up(t1)
        e2, _ms2 = await deck.jog_up(t2)
        assert e1 is None and e2 is None

    asyncio.run(body())


def test_build_hardware_live_propagates_gpio_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from pi_deck.services import hardware_facade as hf

    def boom() -> None:
        raise RuntimeError("simulated gpio failure")

    monkeypatch.setattr(hf, "LiveDeckHardware", lambda *a, **k: boom())
    monkeypatch.setenv("PI_DECK_HARDWARE", "live")
    with pytest.raises(RuntimeError, match="simulated gpio failure"):
        hf.build_hardware()


def test_bus_busy_409_shape(client: TestClient) -> None:
    class BusyAdc1(MockDeckHardware):
        def adc1_physical_idle(self) -> bool:
            return False

    deck: DeckControlService = client.app.state.deck
    prev = deck.hardware
    deck.hardware = BusyAdc1()
    try:
        r = client.post("/api/v1/jog/press", json={"action": "center", "duration_ms": 10})
        assert r.status_code == 409
        body = r.json()
        assert body["error"] == "command_rejected"
        assert body["reason"] == "bus_busy"
        assert "message" in body
    finally:
        deck.hardware = prev
