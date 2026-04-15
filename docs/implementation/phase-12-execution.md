# Phase 12 Execution Record

**Status:** in progress — deploy script verified on deck host; pending visual confirmation of version badge in kiosk UI and host health snapshot.

**Date:** 2026-04-15

## Summary

Phase 12 delivers the canonical deploy mechanism and a persistent version counter that is visible in the UI on every deployment.

**Done in repo:**

- **`scripts/deploy.sh`** — single deploy script that is the authoritative way to push code to the deck Pi. It:
  - Builds the frontend (`npm run build`)
  - `rsync`s `backend/src/pi_deck/` (including `static/`), `backend/pyproject.toml`, `scripts/kiosk/`, and `scripts/host/` to the Pi
  - Increments a persistent counter at `~/.pi-deck-deploy` on the Pi
  - Reinstalls the Python package in the Pi virtualenv
  - Ensures `PI_DECK_HARDWARE=live` in the systemd unit and restarts `pi-deck`
  - Waits for `/health`, then prints `/api/v1/status` to confirm version
  - Reloads Chromium via `xdotool F5` (X11) or kills and relaunches the kiosk process if `xdotool` is absent
- **`backend/src/pi_deck/api/app.py`** — reads `~/.pi-deck-deploy` at startup via `_read_deploy_counter()` / `_build_version()` and formats `status.version` as `"{__version__}+r{N}"` when the counter is present (bare `__version__` when absent or zero)
- **`frontend/src/components/VersionBadge.tsx`** — floating badge fixed to the top-left corner, sourced from `status.version`; rendered in `App.tsx` once `status` is available
- **Tests:**
  - `backend/tests/test_deploy_version.py` — 6 tests: counter absent, valid, corrupt; version string without and with counter; REST endpoint reflects counter
  - `frontend/src/components/VersionBadge.test.tsx` — 2 tests: renders deploy version string, renders bare version

## Operational entry points

| Item | Role |
|------|------|
| `scripts/deploy.sh` | **Canonical deploy** — run from dev machine; safe to repeat |
| `~/.pi-deck-deploy` (on Pi) | Persistent integer counter; written by deploy script |
| `GET /api/v1/status` → `version` | Reports `"0.1.0+r{N}"` after first deploy |
| `VersionBadge` (top-left UI) | Shows `status.version` as a floating overlay |

## Agent authorization

`scripts/deploy.sh` is the authorized deploy mechanism. It can be invoked by the agent without per-run confirmation from the repo root:

```bash
PI_TARGET=user@pi-hostname ./scripts/deploy.sh
```

## Exit criteria (from plan)

| Criterion | Evidence |
|-----------|----------|
| Deploy script pushes latest code, reloads kiosk, and increments version visible in UI | Script tested end-to-end on deck host: rsync, counter incremented across multiple runs, `GET /api/v1/status` returns expected `"version":"0.1.0+r{N}"`, Chromium restarted. Visual badge confirmation pending from kiosk display. |
| Host health gate | Pending — paste snapshot below after confirming kiosk |

## Host health snapshot

*(Paste output of `python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py` on the deck host after first deploy.)*
