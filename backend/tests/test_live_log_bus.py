"""Live log records bus snapshots for replay (same text as UI mirrors from ``bus/snapshot``)."""

from __future__ import annotations

from pi_deck.services.live_log import LiveLogService
from pi_deck.services.ws_hub import WsHub


def test_record_event_stores_bus_snapshot_message() -> None:
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
    row = svc.record_event(ev)
    assert row is not None
    assert row.data["source"] == "bus"
    assert (
        row.data["message"]
        == "key_adc1_active=false key_adc2_direction=up key_led_active=true"
    )
