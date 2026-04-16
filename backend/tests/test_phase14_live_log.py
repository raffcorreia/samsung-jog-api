"""Phase 14: backend-owned live log buffer and websocket replay."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from pi_deck.api.app import create_app


def test_websocket_replays_backend_log_history_on_connect() -> None:
    with TestClient(create_app()) as client:
        assert client.post(
            "/api/v1/log",
            json={"level": "info", "source": "test", "message": "history before connect"},
        ).status_code == 200

        with client.websocket_connect("/ws/events") as ws:
            hello = json.loads(ws.receive_text())
            assert hello["category"] == "control"
            replay = json.loads(ws.receive_text())
            assert replay["category"] == "log"
            assert replay["type"] == "entry"
            assert replay["data"]["message"] == "history before connect"


def test_command_rejection_emits_log_entries_to_connected_clients() -> None:
    """Successful jog commands do not stream ``command/*``; rejections still do."""
    with TestClient(create_app()) as client:
        with client.websocket_connect("/ws/events") as ws:
            ws.receive_text()  # control/connected
            ws.receive_text()  # log/entry for the connection

            assert client.post("/api/v1/jog/hold", json={"action": "up"}).status_code == 200
            r = client.post("/api/v1/jog/press", json={"action": "left", "duration_ms": 10})
            assert r.status_code == 409

            saw_log = False
            for _ in range(15):
                msg = json.loads(ws.receive_text())
                if msg["category"] == "log" and msg["type"] == "entry":
                    if "command rejected" in msg["data"].get("message", ""):
                        saw_log = True
                        break

            assert saw_log


def test_two_websocket_clients_receive_same_log_entry() -> None:
    with TestClient(create_app()) as client:
        with client.websocket_connect("/ws/events") as ws1:
            ws1.receive_text()  # control/connected
            ws1.receive_text()  # log/entry for ws1 connection
            with client.websocket_connect("/ws/events") as ws2:
                ws2.receive_text()  # control/connected
                ws2.receive_text()  # replayed ws1 connection log
                ws2.receive_text()  # log/entry for ws2 connection
                ws1.receive_text()  # log/entry for ws2 connection

                assert client.post(
                    "/api/v1/log",
                    json={"level": "info", "source": "test", "message": "shared event"},
                ).status_code == 200

                msg1 = json.loads(ws1.receive_text())
                msg2 = json.loads(ws2.receive_text())

                assert msg1["category"] == "log"
                assert msg2["category"] == "log"
                assert msg1["data"]["message"] == "shared event"
                assert msg2["data"]["message"] == "shared event"


def test_delete_log_clears_buffer_and_not_replayed() -> None:
    with TestClient(create_app()) as client:
        assert (
            client.post(
                "/api/v1/log",
                json={"level": "info", "source": "test", "message": "before clear"},
            ).status_code
            == 200
        )
        assert client.delete("/api/v1/log").status_code == 200

        with client.websocket_connect("/ws/events") as ws:
            assert json.loads(ws.receive_text())["category"] == "control"
            nxt = json.loads(ws.receive_text())
            assert nxt["category"] == "log"
            assert "before clear" not in json.dumps(nxt)
