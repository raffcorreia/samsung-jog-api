"""Phase 10: REST validation, websocket envelope, command rejection responses."""

from __future__ import annotations

import asyncio
import json
import re

import pytest
from fastapi.testclient import TestClient

from pi_deck.api.app import create_app
from pi_deck.models.schemas import CommandRejectedReason
from pi_deck.services.deck_control import DeckControlService
from pi_deck.services.hardware_facade import MockDeckHardware
from pi_deck.services.live_log import LiveLogService
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


def test_websocket_receives_held_after_jog_hold_mock(client: TestClient) -> None:
    """REST hold must stream ``command/held`` on the websocket (deck_control is the source)."""
    with client.websocket_connect("/ws/events") as ws:
        ws.receive_text()
        r = client.post("/api/v1/jog/hold", json={"action": "down"})
        assert r.status_code == 200
        saw_held = False
        for _ in range(40):
            msg = json.loads(ws.receive_text())
            if msg.get("category") == "command" and msg.get("type") == "held":
                assert msg["data"].get("action") == "down"
                saw_held = True
                break
        assert saw_held, "expected command/held from deck_control on websocket"
        client.post("/api/v1/jog/release", json={"action": "down"})


def test_websocket_receives_pulse_after_jog_press(client: TestClient) -> None:
    """Integrated: REST jog press while WS client connected streams pulse event."""
    with client.websocket_connect("/ws/events") as ws:
        ws.receive_text()
        r = client.post("/api/v1/jog/press", json={"action": "up", "duration_ms": 8})
        assert r.status_code == 200
        saw_pulse = False
        for _ in range(20):
            msg = json.loads(ws.receive_text())
            if msg.get("category") == "command" and msg.get("type") == "pulse":
                assert msg["data"].get("action") == "up"
                saw_pulse = True
                break
        assert saw_pulse, "expected command/pulse on websocket"


def test_concurrent_jog_rejects_second_command() -> None:
    """While a slow pulse runs, a second jog_press must return CONCURRENT_COMMAND."""

    class SlowMock(MockDeckHardware):
        def pulse(self, action, duration_s: float) -> None:
            import time

            time.sleep(0.2)

    hub = WsHub()
    deck = DeckControlService(SlowMock(), hub, LiveLogService(hub), "test")

    async def body() -> None:
        t = asyncio.create_task(deck.jog_press("up", 200))
        await asyncio.sleep(0)
        r2 = await deck.jog_press("left", 10)
        assert r2 == CommandRejectedReason.CONCURRENT_COMMAND
        await t
        assert await deck.jog_press("left", 10) is None

    asyncio.run(body())


def test_jog_hold_release_roundtrip(client: TestClient) -> None:
    r = client.post("/api/v1/jog/hold", json={"action": "right"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    r2 = client.post("/api/v1/jog/release", json={"action": "right"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["ok"] is True
    assert "duration_ms" in body
    assert body["duration_ms"] >= 0


def test_jog_release_idempotent_when_idle(client: TestClient) -> None:
    r = client.post("/api/v1/jog/release", json={"action": "up"})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "duration_ms": 0}


def test_two_directions_coexist(client: TestClient) -> None:
    assert client.post("/api/v1/jog/hold", json={"action": "up"}).status_code == 200
    assert client.post("/api/v1/jog/hold", json={"action": "left"}).status_code == 200
    assert client.post("/api/v1/jog/release", json={"action": "up"}).status_code == 200
    assert client.post("/api/v1/jog/release", json={"action": "left"}).status_code == 200


def test_second_hold_same_direction_replaces_first(client: TestClient) -> None:
    """New hold on same action ends the previous hold (authoritative per direction)."""
    assert client.post("/api/v1/jog/hold", json={"action": "left"}).status_code == 200
    assert client.post("/api/v1/jog/hold", json={"action": "left"}).status_code == 200
    assert client.post("/api/v1/jog/release", json={"action": "left"}).status_code == 200


def test_service_hold_release_two_directions() -> None:
    hub = WsHub()
    deck = DeckControlService(MockDeckHardware(), hub, LiveLogService(hub), "test")

    async def body() -> None:
        assert await deck.jog_hold("up") is None
        assert await deck.jog_hold("left") is None
        e1, _ = await deck.jog_release("up")
        e2, _ = await deck.jog_release("left")
        assert e1 is None and e2 is None

    asyncio.run(body())


def test_watchdog_auto_releases_hold_after_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unreleased hold must be auto-released by the watchdog after _MAX_HOLD_S seconds."""
    import pi_deck.services.deck_control as dc_module

    monkeypatch.setattr(dc_module, "_MAX_HOLD_S", 0.05)
    hub = WsHub()
    deck = DeckControlService(MockDeckHardware(), hub, LiveLogService(hub), "test")

    async def body() -> None:
        err = await deck.jog_hold("up")
        assert err is None
        assert len(deck._hold) == 1
        await asyncio.sleep(0.15)  # outlast the 50 ms watchdog
        assert len(deck._hold) == 0

    asyncio.run(body())


def test_build_hardware_live_propagates_gpio_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from pi_deck.services import hardware_facade as hf

    def boom() -> None:
        raise RuntimeError("simulated gpio failure")

    monkeypatch.setattr(hf, "LiveDeckHardware", lambda *a, **k: boom())
    monkeypatch.setenv("PI_DECK_HARDWARE", "live")
    with pytest.raises(RuntimeError, match="simulated gpio failure"):
        hf.build_hardware()


def test_index_html_sent_with_no_store_cache(client: TestClient) -> None:
    """Kiosk / remote browsers must not keep a stale shell that references deleted hashed bundles."""
    r = client.get("/")
    assert r.status_code == 200
    cc = r.headers.get("cache-control") or ""
    assert "no-store" in cc
    assert r.headers.get("pragma") == "no-cache"


def test_hashed_assets_sent_with_long_cache(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    m = re.search(r'src="(/assets/[^"]+)"', r.text)
    assert m is not None
    r2 = client.get(m.group(1))
    assert r2.status_code == 200
    cc = r2.headers.get("cache-control") or ""
    assert "immutable" in cc
    assert "max-age=" in cc
