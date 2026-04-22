"""Phase 16: recording capture, library management, and websocket sync."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from pi_deck.api.app import create_app


def _build_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PI_DECK_RECORDINGS_DIR", str(tmp_path))
    return TestClient(create_app())


def _wait_for(condition, timeout_s: float = 1.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if condition():
            return
        time.sleep(0.02)
    raise AssertionError("timed out waiting for condition")


def test_start_stop_recording_saves_observation_sequence(tmp_path: Path, monkeypatch) -> None:
    with _build_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/recordings/start").status_code == 200
        assert client.post("/api/v1/jog/hold", json={"action": "up"}).status_code == 200
        assert client.post("/api/v1/jog/release", json={"action": "up"}).status_code == 200

        def has_event() -> bool:
            body = client.get("/api/v1/recordings/state").json()
            return int(body["event_count"]) >= 1

        _wait_for(has_event)

        stop = client.post("/api/v1/recordings/stop")
        assert stop.status_code == 200
        item = stop.json()["item"]
        assert item["event_count"] >= 1
        assert item["filename"].endswith(".json")

        library = client.get("/api/v1/recordings").json()
        assert len(library["items"]) == 1

        path = tmp_path / item["filename"]
        saved = json.loads(path.read_text())
        assert saved["source"] == "observation"
        assert saved["version"] == "V1"
        assert "start_state" not in saved
        assert "end_state" not in saved
        assert saved["events"][0]["type"] == "hold"
        assert saved["events"][1]["type"] == "release"
        assert "duration_ms" not in saved


def test_led_changes_are_recorded_as_non_blocking_led_events(tmp_path: Path, monkeypatch) -> None:
    with _build_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/recordings/start").status_code == 200
        asyncio.run(
            client.app.state.recordings.observe_event(
                {
                    "category": "bus",
                    "type": "led_changed",
                    "ts": "2026-04-16T12:00:00Z",
                    "data": {"key_led_active": True},
                }
            )
        )
        item = client.post("/api/v1/recordings/stop").json()["item"]
        body = json.loads((tmp_path / item["filename"]).read_text())
        led_events = [event for event in body["events"] if event["type"] == "led"]
        assert led_events == [{"type": "led", "active": True, "blocking": False, "poll_interval_ms": None, "timeout_ms": None}]


def test_recordings_can_be_renamed_and_deleted(tmp_path: Path, monkeypatch) -> None:
    with _build_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/recordings/start").status_code == 200
        assert client.post("/api/v1/jog/hold", json={"action": "center"}).status_code == 200
        assert client.post("/api/v1/jog/release", json={"action": "center"}).status_code == 200
        _wait_for(lambda: client.get("/api/v1/recordings/state").json()["event_count"] >= 1)
        item = client.post("/api/v1/recordings/stop").json()["item"]

        renamed = client.patch(
            f"/api/v1/recordings/{item['id']}",
            json={"name": "Desk Macro"},
        )
        assert renamed.status_code == 200
        renamed_item = renamed.json()["item"]
        assert renamed_item["name"] == "Desk Macro"
        assert renamed_item["filename"].startswith("Desk-Macro")

        deleted = client.delete(f"/api/v1/recordings/{renamed_item['id']}")
        assert deleted.status_code == 200
        assert client.get("/api/v1/recordings").json() == {"items": []}


def test_recording_websocket_sync_sends_state_and_library(tmp_path: Path, monkeypatch) -> None:
    with _build_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/recordings/start").status_code == 200
        assert client.post("/api/v1/jog/hold", json={"action": "left"}).status_code == 200
        assert client.post("/api/v1/jog/release", json={"action": "left"}).status_code == 200
        _wait_for(lambda: client.get("/api/v1/recordings/state").json()["event_count"] >= 1)
        assert client.post("/api/v1/recordings/stop").status_code == 200

        with client.websocket_connect("/ws/events") as ws:
            received = [json.loads(ws.receive_text()) for _ in range(8)]

        seen_types = {(msg["category"], msg["type"]) for msg in received}
        assert ("control", "connected") in seen_types
        assert ("recording", "state") in seen_types
        assert ("recording", "library") in seen_types


def test_recording_ignores_preheld_state_at_start(tmp_path: Path, monkeypatch) -> None:
    with _build_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/jog/hold", json={"action": "center"}).status_code == 200
        assert client.post("/api/v1/recordings/start").status_code == 200
        assert client.post("/api/v1/jog/release", json={"action": "center"}).status_code == 200
        time.sleep(0.1)
        item = client.post("/api/v1/recordings/stop").json()["item"]
        body = json.loads((tmp_path / item["filename"]).read_text())
        assert body["events"] == []


def test_recording_does_not_persist_initial_setup_delay(tmp_path: Path, monkeypatch) -> None:
    with _build_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/recordings/start").status_code == 200
        time.sleep(0.12)
        assert client.post("/api/v1/jog/hold", json={"action": "left"}).status_code == 200
        assert client.post("/api/v1/jog/release", json={"action": "left"}).status_code == 200
        _wait_for(lambda: client.get("/api/v1/recordings/state").json()["event_count"] >= 2)
        item = client.post("/api/v1/recordings/stop").json()["item"]
        body = json.loads((tmp_path / item["filename"]).read_text())
        assert body["events"][0]["type"] == "hold"
        assert body["events"][1]["type"] == "release"
        assert all(event["type"] != "delay" for event in body["events"][:2])
        assert item["duration_ms"] == 0
        assert "duration_ms" not in body


def test_upload_and_download_recording_file(tmp_path: Path, monkeypatch) -> None:
    payload = {
        "name": "Imported",
        "version": "V1",
        "source": "observation",
        "created_at": "2026-04-16T12:00:00Z",
        "updated_at": "2026-04-16T12:00:00Z",
        "duration_ms": 1250,
        "events": [
            {"type": "hold", "action": "up"},
            {"type": "delay", "duration_ms": 80},
            {"type": "release", "action": "up"},
        ],
    }
    with _build_client(tmp_path, monkeypatch) as client:
        uploaded = client.post(
            "/api/v1/recordings/upload",
            files={"file": ("imported.json", json.dumps(payload), "application/json")},
        )
        assert uploaded.status_code == 200
        item = uploaded.json()["item"]

        download = client.get(f"/api/v1/recordings/{item['id']}/download")
        assert download.status_code == 200
        body = json.loads(download.text)
        assert body["name"] == "Imported"
        assert item["duration_ms"] == 80
        assert "duration_ms" not in body


def test_recording_content_can_be_loaded_and_replaced(tmp_path: Path, monkeypatch) -> None:
    payload = {
        "name": "Editable",
        "version": "V1",
        "source": "observation",
        "created_at": "2026-04-16T12:00:00Z",
        "updated_at": "2026-04-16T12:00:00Z",
        "duration_ms": 1250,
        "events": [
            {"type": "hold", "action": "up"},
            {"type": "delay", "duration_ms": 80},
            {"type": "release", "action": "up"},
        ],
    }
    with _build_client(tmp_path, monkeypatch) as client:
        uploaded = client.post(
            "/api/v1/recordings/upload",
            files={"file": ("editable.json", json.dumps(payload), "application/json")},
        )
        item = uploaded.json()["item"]

        content = client.get(f"/api/v1/recordings/{item['id']}/content")
        assert content.status_code == 200
        assert '"name": "Editable"' in content.text

        updated = {**payload, "name": "Edited Raw"}
        replace = client.put(
            f"/api/v1/recordings/{item['id']}/content",
            content=json.dumps(updated),
            headers={"Content-Type": "application/json"},
        )
        assert replace.status_code == 200
        replaced_item = replace.json()["item"]
        assert replaced_item["name"] == "Edited Raw"
        assert replaced_item["filename"] == item["filename"]
        assert replaced_item["duration_ms"] == 80


def test_empty_recording_playback_returns_idle_immediately(tmp_path: Path, monkeypatch) -> None:
    payload = {
        "name": "Empty",
        "version": "V1",
        "source": "observation",
        "created_at": "2026-04-16T12:00:00Z",
        "updated_at": "2026-04-16T12:00:00Z",
        "duration_ms": 0,
        "events": [],
    }
    with _build_client(tmp_path, monkeypatch) as client:
        uploaded = client.post(
            "/api/v1/recordings/upload",
            files={"file": ("empty.json", json.dumps(payload), "application/json")},
        )
        item = uploaded.json()["item"]

        play = client.post(f"/api/v1/recordings/{item['id']}/play")
        assert play.status_code == 200
        assert play.json()["mode"] == "idle"

        state = client.get("/api/v1/recordings/state")
        assert state.status_code == 200
        assert state.json()["mode"] == "idle"
        library = client.get("/api/v1/recordings").json()
        assert library["items"][0]["duration_ms"] == 0


def test_stop_playback_interrupts_long_delay_recording(tmp_path: Path, monkeypatch) -> None:
    payload = {
        "name": "Long Delay",
        "version": "V1",
        "source": "observation",
        "created_at": "2026-04-16T12:00:00Z",
        "updated_at": "2026-04-16T12:00:00Z",
        "duration_ms": 5000,
        "events": [
            {"type": "delay", "duration_ms": 5000},
        ],
    }
    with _build_client(tmp_path, monkeypatch) as client:
        uploaded = client.post(
            "/api/v1/recordings/upload",
            files={"file": ("long-delay.json", json.dumps(payload), "application/json")},
        )
        item = uploaded.json()["item"]

        play = client.post(f"/api/v1/recordings/{item['id']}/play")
        assert play.status_code == 200
        assert play.json()["mode"] == "replaying"

        stop = client.post("/api/v1/recordings/stop-playback")
        assert stop.status_code == 200
        assert stop.json()["mode"] == "idle"


def test_uploaded_stale_duration_is_ignored_in_favor_of_event_timing(tmp_path: Path, monkeypatch) -> None:
    payload = {
        "name": "Stale Duration",
        "version": "V1",
        "source": "observation",
        "created_at": "2026-04-16T12:00:00Z",
        "updated_at": "2026-04-16T12:00:00Z",
        "duration_ms": 9999,
        "events": [
            {"type": "hold", "action": "left"},
            {"type": "delay", "duration_ms": 120},
            {"type": "release", "action": "left"},
        ],
    }
    with _build_client(tmp_path, monkeypatch) as client:
        uploaded = client.post(
            "/api/v1/recordings/upload",
            files={"file": ("stale-duration.json", json.dumps(payload), "application/json")},
        )
        assert uploaded.status_code == 200
        item = uploaded.json()["item"]
        assert item["duration_ms"] == 120

        content = client.get(f"/api/v1/recordings/{item['id']}/content")
        assert content.status_code == 200
        saved = json.loads(content.text)
        assert "duration_ms" not in saved


def test_concurrent_operations_are_rejected_while_busy(tmp_path: Path, monkeypatch) -> None:
    payload = {
        "name": "Long",
        "version": "V1",
        "source": "observation",
        "created_at": "2026-04-16T12:00:00Z",
        "updated_at": "2026-04-16T12:00:00Z",
        "duration_ms": 5000,
        "events": [{"type": "delay", "duration_ms": 5000}],
    }
    with _build_client(tmp_path, monkeypatch) as client:
        # start recording → second start is rejected
        assert client.post("/api/v1/recordings/start").status_code == 200
        busy = client.post("/api/v1/recordings/start")
        assert busy.status_code == 409
        assert busy.json()["reason"] == "busy"

        # playback while recording is also rejected
        uploaded = client.post(
            "/api/v1/recordings/upload",
            files={"file": ("long.json", json.dumps(payload), "application/json")},
        )
        item = uploaded.json()["item"]
        assert client.post(f"/api/v1/recordings/{item['id']}/play").status_code == 409

        # stop recording
        client.post("/api/v1/recordings/stop")

        # start playback → second start is rejected
        assert client.post(f"/api/v1/recordings/{item['id']}/play").status_code == 200
        busy = client.post(f"/api/v1/recordings/{item['id']}/play")
        assert busy.status_code == 409
        assert busy.json()["reason"] == "busy"

        # recording while replaying is also rejected
        assert client.post("/api/v1/recordings/start").status_code == 409

        client.post("/api/v1/recordings/stop-playback")


def test_delete_recording_while_replaying_succeeds_and_playback_continues(tmp_path: Path, monkeypatch) -> None:
    payload = {
        "name": "Delete During Replay",
        "version": "V1",
        "source": "observation",
        "created_at": "2026-04-16T12:00:00Z",
        "updated_at": "2026-04-16T12:00:00Z",
        "duration_ms": 5000,
        "events": [{"type": "delay", "duration_ms": 5000}],
    }
    with _build_client(tmp_path, monkeypatch) as client:
        item = client.post(
            "/api/v1/recordings/upload",
            files={"file": ("replay-delete.json", json.dumps(payload), "application/json")},
        ).json()["item"]

        assert client.post(f"/api/v1/recordings/{item['id']}/play").status_code == 200
        assert client.get("/api/v1/recordings/state").json()["mode"] == "replaying"

        # delete while replaying: the file is removed but playback continues from in-memory copy
        deleted = client.delete(f"/api/v1/recordings/{item['id']}")
        assert deleted.status_code == 200
        assert client.get("/api/v1/recordings/state").json()["mode"] == "replaying"
        assert client.get("/api/v1/recordings").json() == {"items": []}

        client.post("/api/v1/recordings/stop-playback")
        assert client.get("/api/v1/recordings/state").json()["mode"] == "idle"


def test_recording_with_interleaved_led_and_hold_release_events(tmp_path: Path, monkeypatch) -> None:
    with _build_client(tmp_path, monkeypatch) as client:
        assert client.post("/api/v1/recordings/start").status_code == 200

        assert client.post("/api/v1/jog/hold", json={"action": "up"}).status_code == 200
        _wait_for(lambda: client.get("/api/v1/recordings/state").json()["event_count"] >= 1)

        led_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        asyncio.run(
            client.app.state.recordings.observe_event(
                {
                    "category": "bus",
                    "type": "led_changed",
                    "ts": led_ts,
                    "data": {"key_led_active": True},
                }
            )
        )
        _wait_for(lambda: client.get("/api/v1/recordings/state").json()["event_count"] >= 2)

        assert client.post("/api/v1/jog/release", json={"action": "up"}).status_code == 200
        _wait_for(lambda: client.get("/api/v1/recordings/state").json()["event_count"] >= 3)

        item = client.post("/api/v1/recordings/stop").json()["item"]
        body = json.loads((tmp_path / item["filename"]).read_text())

        types = [e["type"] for e in body["events"]]
        assert "hold" in types
        assert "led" in types
        assert "release" in types
        # hold must come before the led event, led before release
        assert types.index("hold") < types.index("led")
        assert types.index("led") < types.index("release")


def test_upload_rejects_unsupported_recording_version(tmp_path: Path, monkeypatch) -> None:
    payload = {
        "name": "Unsupported Version",
        "version": "V2",
        "source": "observation",
        "created_at": "2026-04-16T12:00:00Z",
        "updated_at": "2026-04-16T12:00:00Z",
        "duration_ms": 0,
        "events": [],
    }
    with _build_client(tmp_path, monkeypatch) as client:
        uploaded = client.post(
            "/api/v1/recordings/upload",
            files={"file": ("unsupported.json", json.dumps(payload), "application/json")},
        )
        assert uploaded.status_code == 400
        body = uploaded.json()
        assert body["error"] == "recording_rejected"
        assert body["reason"] == "invalid_recording"
