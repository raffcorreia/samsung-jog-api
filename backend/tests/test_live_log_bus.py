"""Live log: ``bus/snapshot`` does not append a dump row; semantic lines use ``bus_delta_log_messages``."""

from __future__ import annotations

from pi_deck.models.schemas import SignalSnapshot
from pi_deck.services.live_log import LiveLogService, bus_delta_log_messages
from pi_deck.services.ws_hub import WsHub


def test_record_event_skips_bus_snapshot() -> None:
    svc = LiveLogService(WsHub())
    ev = {
        "v": 1,
        "category": "bus",
        "type": "snapshot",
        "ts": "2026-01-01T00:00:00Z",
        "data": {
            "key_adc1_active": False,
            "key_led_active": True,
            "key_adc2_direction": "up",
        },
    }
    assert svc.record_event(ev) is None


def test_bus_delta_log_messages() -> None:
    idle = SignalSnapshot(
        key_adc1_active=False,
        key_led_active=False,
        key_adc2_direction=None,
    )
    left = SignalSnapshot(
        key_adc1_active=False,
        key_led_active=False,
        key_adc2_direction="left",
    )
    assert bus_delta_log_messages(None, left) == ["key_adc2 -> left"]
    assert bus_delta_log_messages(idle, left) == ["key_adc2 -> left"]
    assert bus_delta_log_messages(left, idle) == ["key_adc2 -> idle"]
    pressed = SignalSnapshot(
        key_adc1_active=True,
        key_led_active=False,
        key_adc2_direction=None,
    )
    assert bus_delta_log_messages(idle, pressed) == ["key_adc1 -> on"]
