# Phase 10 Execution Record

**Status:** complete (repository; verified on deck host `pi-deck`).

**Date:** 2026-04-13

## Summary

Phase 10 defines and implements the **local backend API** used by all UI and control flows, per [Implementation Plan — Phase 10](plan.md#phase-10-local-api) and [Solution Overview — WebSocket event model](../design/solution-overview.md):

- **REST (prefix `/api/v1`):**
  - `GET /api/v1/status` — version, `hardware` (`live` | `mock`), `operating_mode` (`jog` | `ddc` | `blind`), `control_state` (`idle` | `commanding`), and GPIO-derived `signals` (`key_adc1_active`, `key_led_active`) when live hardware is active.
  - `POST /api/v1/mode` — set operating mode (in-memory; persisted settings come later).
  - `POST /api/v1/jog/press` — body `{ "action": "up"|"down"|"left"|"right"|"center", "duration_ms": <1..60000> }`; success `{ "ok": true }`, conflict **`409`** with `{ "error": "command_rejected", "reason": "<enum>", "message": "..." }`.
- **`GET /health`** — `{ "status": "ok", "version": "<semver>" }` (host health script and kiosk wait logic remain compatible).
- **WebSocket `/ws/events`** — first message is a versioned envelope (`v`, `category`, `type`, `ts`, `data`) with `category: control`, `type: connected`, and full status under `data.status`. Further events include command accepted/rejected, control state, and bus snapshots (see `pi_deck.models.schemas`).
- **Hardware selection** — `PI_DECK_HARDWARE` = `mock` | `live` | **`auto`** (default). **`auto`** tries real GPIO (`LiveDeckHardware`) and falls back to **`mock`** if GPIO cannot be opened, with an **ERROR** log so the service still listens (useful when the protoboard is disconnected or pin export fails). Use **`live`** to fail fast when GPIO must be mandatory.
- **Orchestration** — `DeckControlService` in `pi_deck.services.deck_control` serializes jog commands; **center** refuses when KEY_ADC1 observation reports activity (`bus_busy`). Directional actions rely on app-level serialization until a dedicated KEY_ADC2 observe path exists.
- **Tests** — `backend/tests/test_phase10_api.py` (validation, websocket envelope, concurrent rejection, `409` bodies, `auto` fallback).

## Operational entry points

| Item | Role |
|------|------|
| `pi_deck.api.app:create_app` | FastAPI app, lifespan, routes, static UI |
| `config/systemd/pi-deck.service` | Optional `Environment=PI_DECK_HARDWARE=auto` (template) |
| `backend/tests/conftest.py` | Defaults `PI_DECK_HARDWARE=mock` for pytest |

## Exit criteria (from plan)

| Criterion | Evidence |
|-----------|----------|
| Frontend can drive low-level control and receive live state | REST + WebSocket contract implemented; Phase 11 UI will consume the same endpoints. |
| Host health gate | Snapshot below (deck host). |

## Host health snapshot

Recorded on the deck host **`pi-deck`** (`10.0.0.11`):

```bash
python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py
```

**Captured output (2026-04-13):**

```
pi-deck host health  |  2026-04-13T17:29:22.270834+00:00
hostname: pi-deck

[python]
  executable: /usr/bin/python3
  version:    3.13.5
  platform:   Linux-6.18.18-v7+-armv7l-with-glibc2.41
  pi_deck:    importable=True  package_version=0.1.0

[cpu]
  model: ARMv7 Processor rev 5 (v7l)
  logical cpus: 4
  load average (1 / 5 / 15 min): 0.34  0.16  0.05

[memory]
  RAM:  total 0.90 GiB  available 0.57 GiB  (MemTotal/MemAvailable KiB: 942120 / 601948)
  swap: total 0.90 GiB  free 0.90 GiB  (KiB: 942076 / 942076)

[disk]  mount /
  size 56.49 GiB  used 4.97 GiB  avail 49.18 GiB  (8.79% used)

[thermal]  sysfs zones
  thermal_zone0  cpu-thermal  47.6 °C

[raspberry_pi]  vcgencmd (SoC voltage / throttling)
  temperature: temp=47.6'C
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

**Review:** `get_throttled` is **`0x0`**. Root filesystem use is **~8.8%**. The `/health` response includes **`version`** alongside **`status`** for Phase 10.

## Follow-on (Phase 11)

- Low-level JOG console UI calling `POST /api/v1/jog/press` and subscribing to `/ws/events`.
- Optional: install `RPi.GPIO` or `lgpio` on the Pi so gpiozero uses a stable pin factory instead of the experimental native fallback (see journal warnings when `PI_DECK_HARDWARE=auto` attempts live hardware).
