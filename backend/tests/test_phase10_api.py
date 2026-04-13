"""Phase 10: REST validation, websocket envelope, command rejection responses."""

from __future__ import annotations

import asyncio
import json

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


def test_build_hardware_auto_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from pi_deck.services import hardware_facade as hf

    def boom() -> None:
        raise RuntimeError("simulated gpio failure")

    monkeypatch.setattr(hf, "LiveDeckHardware", lambda *a, **k: boom())
    monkeypatch.setenv("PI_DECK_HARDWARE", "auto")
    hw = hf.build_hardware()
    assert hw.kind == "mock"


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
