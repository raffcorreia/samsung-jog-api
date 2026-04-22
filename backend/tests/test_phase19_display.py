"""Phase 19: display brightness / power and system shutdown API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pi_deck.api.app import create_app
from pi_deck.hardware.display_power import BRIGHTNESS_RAW_MAX


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as c:
        yield c


# ── brightness ────────────────────────────────────────────────────────────────

def test_get_brightness_shape(client: TestClient) -> None:
    r = client.get("/api/v1/display/brightness")
    assert r.status_code == 200
    body = r.json()
    assert "brightness_pct" in body
    assert "brightness_raw" in body
    assert body["max_raw"] == BRIGHTNESS_RAW_MAX


def test_get_brightness_pct_range(client: TestClient) -> None:
    r = client.get("/api/v1/display/brightness")
    body = r.json()
    assert 0 <= body["brightness_pct"] <= 100


def test_set_brightness_pct(client: TestClient) -> None:
    r = client.put("/api/v1/display/brightness", json={"brightness_pct": 50})
    assert r.status_code == 200
    body = r.json()
    assert body["brightness_pct"] == 50


def test_set_brightness_zero(client: TestClient) -> None:
    r = client.put("/api/v1/display/brightness", json={"brightness_pct": 0})
    assert r.status_code == 200
    assert r.json()["brightness_pct"] == 0


def test_set_brightness_100(client: TestClient) -> None:
    r = client.put("/api/v1/display/brightness", json={"brightness_pct": 100})
    assert r.status_code == 200
    body = r.json()
    assert body["brightness_pct"] == 100
    # Raw must not exceed the Phase 18 safe ceiling.
    assert body["brightness_raw"] <= BRIGHTNESS_RAW_MAX


def test_set_brightness_invalid_above_100(client: TestClient) -> None:
    r = client.put("/api/v1/display/brightness", json={"brightness_pct": 101})
    assert r.status_code == 422


def test_set_brightness_invalid_negative(client: TestClient) -> None:
    r = client.put("/api/v1/display/brightness", json={"brightness_pct": -1})
    assert r.status_code == 422


# ── power ─────────────────────────────────────────────────────────────────────

def test_get_power_shape(client: TestClient) -> None:
    r = client.get("/api/v1/display/power")
    assert r.status_code == 200
    body = r.json()
    assert "on" in body
    assert "brightness_pct" in body


def test_power_off(client: TestClient) -> None:
    r = client.post("/api/v1/display/power", json={"on": False})
    assert r.status_code == 200
    body = r.json()
    assert body["on"] is False
    # API returns the saved (pre-power-off) brightness, not 0.
    assert 0 <= body["brightness_pct"] <= 100


def test_power_on_after_off(client: TestClient) -> None:
    client.post("/api/v1/display/power", json={"on": False})
    r = client.post("/api/v1/display/power", json={"on": True})
    assert r.status_code == 200
    body = r.json()
    assert body["on"] is True


# ── shutdown ──────────────────────────────────────────────────────────────────

def test_shutdown_returns_ok(client: TestClient) -> None:
    # Mock mode — no actual shutdown.
    r = client.post("/api/v1/system/shutdown")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "message" in body


# ── display service unit tests ────────────────────────────────────────────────

def test_display_service_pct_roundtrip() -> None:
    from pi_deck.hardware.display_power import MockDisplayPower
    from pi_deck.services.display_service import DisplayService

    hw = MockDisplayPower(initial_raw=0)
    svc = DisplayService(hw)
    for pct in (0, 10, 30, 50, 75, 100):
        svc.set_brightness_pct(pct)
        got = svc.get_brightness_pct()
        # Allow ±1 % rounding error from integer math.
        assert abs(got - pct) <= 1, f"pct={pct} → roundtrip={got}"


def test_display_service_raw_cap() -> None:
    from pi_deck.hardware.display_power import MockDisplayPower
    from pi_deck.services.display_service import DisplayService

    hw = MockDisplayPower(initial_raw=0)
    svc = DisplayService(hw)
    svc.set_brightness_pct(100)
    assert hw.read_brightness_raw() == BRIGHTNESS_RAW_MAX


def test_display_service_power_saves_restores_brightness() -> None:
    from pi_deck.hardware.display_power import MockDisplayPower
    from pi_deck.services.display_service import DisplayService

    hw = MockDisplayPower(initial_raw=51)
    svc = DisplayService(hw)

    assert svc.is_on is True
    svc.power_off()
    # Compositor off + backlight zeroed.
    assert hw.read_power_on() is False
    assert hw.read_brightness_raw() == 0  # backlight killed
    # But get_brightness_pct returns the saved pre-off value.
    assert svc.get_brightness_pct() == round(51 * 100 / 170)

    svc.power_on()
    assert hw.read_power_on() is True
    assert hw.read_brightness_raw() == 51  # restored to pre-off level
