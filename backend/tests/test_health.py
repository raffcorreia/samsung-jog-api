from fastapi.testclient import TestClient

from pi_deck.api.app import create_app


def test_health() -> None:
    with TestClient(create_app()) as client:
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data
