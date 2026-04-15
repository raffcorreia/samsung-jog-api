"""Phase 12: deploy counter reader and version string construction."""

from __future__ import annotations

from pi_deck.api.app import _build_version, _read_deploy_counter


def test_read_deploy_counter_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("pi_deck.api.app._DEPLOY_COUNTER_FILE", tmp_path / "no-such-file")
    assert _read_deploy_counter() == 0


def test_read_deploy_counter_valid(tmp_path, monkeypatch) -> None:
    f = tmp_path / ".pi-deck-deploy"
    f.write_text("42\n")
    monkeypatch.setattr("pi_deck.api.app._DEPLOY_COUNTER_FILE", f)
    assert _read_deploy_counter() == 42


def test_read_deploy_counter_corrupt(tmp_path, monkeypatch) -> None:
    f = tmp_path / ".pi-deck-deploy"
    f.write_text("not-a-number")
    monkeypatch.setattr("pi_deck.api.app._DEPLOY_COUNTER_FILE", f)
    assert _read_deploy_counter() == 0


def test_build_version_no_counter(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("pi_deck.api.app._DEPLOY_COUNTER_FILE", tmp_path / "absent")
    # No counter file: version is bare __version__ (no +r suffix)
    v = _build_version()
    assert "+" not in v
    assert len(v) > 0


def test_build_version_with_counter(tmp_path, monkeypatch) -> None:
    f = tmp_path / ".pi-deck-deploy"
    f.write_text("7")
    monkeypatch.setattr("pi_deck.api.app._DEPLOY_COUNTER_FILE", f)
    v = _build_version()
    assert v.endswith("+r7")


def test_status_version_reflects_deploy_counter(tmp_path, monkeypatch) -> None:
    """status.version from the REST endpoint includes the deploy counter."""
    from fastapi.testclient import TestClient

    from pi_deck.api.app import create_app

    f = tmp_path / ".pi-deck-deploy"
    f.write_text("3")
    monkeypatch.setattr("pi_deck.api.app._DEPLOY_COUNTER_FILE", f)

    with TestClient(create_app()) as client:
        r = client.get("/api/v1/status")
        assert r.status_code == 200
        assert r.json()["version"].endswith("+r3")
