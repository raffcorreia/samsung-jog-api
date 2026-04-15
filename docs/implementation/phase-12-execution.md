# Phase 12 Execution Record

**Status:** complete

**Date:** 2026-04-15

## Summary

Phase 12 delivers the canonical deploy mechanism and a persistent version counter that is visible in the UI on every deployment.

Phase 12 was validated through repeated deploys during Phase 13 UI work. The final observed runtime status was `0.1.0+r20` on the live deck host, with the version badge visible in the kiosk UI and the host health gate passing.

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
| Deploy script pushes latest code, reloads kiosk, and increments version visible in UI | Done — script tested end-to-end on deck host; final Phase 13 deploy reported `"version":"0.1.0+r20"` and the badge was visible in the kiosk UI. |
| Host health gate | Done — snapshot below |

## Host health snapshot

Output of `python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py` on the deck host:

```text
pi-deck host health  |  2026-04-15T16:51:54.078515+00:00
hostname: pi-deck

[python]
  executable: /usr/bin/python3
  version:    3.13.5
  platform:   Linux-6.18.18-v7+-armv7l-with-glibc2.41
  pi_deck:    importable=True  package_version=0.1.0

[cpu]
  model: ARMv7 Processor rev 5 (v7l)
  logical cpus: 4
  load average (1 / 5 / 15 min): 0.08  0.13  0.26

[memory]
  RAM:  total 0.90 GiB  available 0.55 GiB  (MemTotal/MemAvailable KiB: 942120 / 578008)
  swap: total 0.90 GiB  free 0.90 GiB  (KiB: 942076 / 941668)

[disk]  mount /
  size 56.49 GiB  used 4.98 GiB  avail 49.17 GiB  (8.82% used)

[thermal]  sysfs zones
  thermal_zone0  cpu-thermal  45.5 °C

[raspberry_pi]  vcgencmd (SoC voltage / throttling)
  temperature: temp=46.0'C
  voltage core: volt=1.3125V
  voltage sdram_c: volt=1.2000V
  voltage sdram_i: volt=1.2000V
  voltage sdram_p: volt=1.2250V
  get_throttled: throttled=0x0
  flags set: (none)

[systemd]
  pi-deck.service: active
  lightdm.service: active

[pi-deck HTTP]
  GET http://127.0.0.1:8756/health
  ok: True  body: '{"status":"ok","version":"0.1.0"}'
```
