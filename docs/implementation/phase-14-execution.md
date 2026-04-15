# Phase 14 Execution Record

**Status:** complete

**Date:** 2026-04-15

## Summary

Phase 14 moves live log ownership from the browser to the backend.

The backend now owns a bounded log history, emits structured `log/entry` WebSocket events, replays recent history to each new WebSocket client, and broadcasts the same log stream to all connected clients. The frontend no longer formats command/control/bus events into local log lines; it renders backend log entries only.

Final Phase 14 deployment: `0.1.0+r22` on the live deck host.

## Design decisions

- The canonical live log event is a normal `WsEventV1` envelope with `category="log"` and `type="entry"`.
- Each log entry carries `level`, `source`, and `message` in `data`, with the backend timestamp in `ts`.
- The backend log buffer stores the last `220` entries, matching the previous frontend display cap while moving ownership server-side.
- Every backend command/control/bus event is recorded into the backend live log even when no WebSocket clients are connected.
- WebSocket clients receive:
  - a `control/connected` status envelope
  - replayed backend `log/entry` history
  - live command/control/bus envelopes plus live `log/entry` envelopes
- UI-originated log messages use `POST /api/v1/log`. This keeps UI stubs such as the record button from mutating browser-owned log history.
- The frontend keeps only a render cache of received backend entries. It clears that cache on each new WebSocket session and repopulates from backend replay.
- Rendered log lines include backend timestamp, source/category, and message.

## Done in repo

- **`backend/src/pi_deck/services/live_log.py`** — new backend-owned live log service with bounded replay buffer, event-to-log formatting, direct publish support, and per-client replay.
- **`backend/src/pi_deck/models/schemas.py`** — added `LogIn` and `ws_log_entry`.
- **`backend/src/pi_deck/api/app.py`** — creates one `LiveLogService` in app lifespan and shares it through `app.state`.
- **`backend/src/pi_deck/api/router.py`** — adds `POST /api/v1/log`; WebSocket connect now sends status, replays log history, and records the connection in the backend log.
- **`backend/src/pi_deck/services/deck_control.py`** — records every emitted backend event into `LiveLogService` before broadcasting.
- **`backend/tests/test_phase14_live_log.py`** — tests history replay, command-event log emission, and two-client log sync.
- **`frontend/src/hooks/useDeckEvents.ts`** — removed browser-side event formatting and requestAnimationFrame log batching; now renders only backend `log/entry` messages.
- **`frontend/src/api/client.ts`** — added `postLogEntry`.
- **`frontend/src/log/formatWsEvent.ts`** and its test were removed because log formatting is now backend-owned.
- **Frontend tests** were updated so App-level log rendering verifies backend `log/entry` consumption.

## Operational entry points

| Item | Role |
|------|------|
| `LiveLogService` | Backend-owned live log buffer and formatter |
| `POST /api/v1/log` | UI-originated log entry append |
| `GET /ws/events` | WebSocket stream; includes replayed and live `log/entry` envelopes |
| `LiveLogWidget` | Stateless renderer for received backend log lines |

## Exit criteria

| Criterion | Status |
|-----------|--------|
| Opening a new browser tab shows recent log history immediately | Done — WebSocket replay sends backend `log/entry` history on connect; live Pi smoke test confirmed replay. |
| Two simultaneous browser clients see the same log stream in sync | Done — backend test and live Pi smoke test confirmed both clients receive the same entry. |
| No log state lives in the browser | Done — browser no longer formats or owns log history; it renders backend entries and clears/replays on WebSocket session start. |
| Host health gate | Done — snapshot below. |

## Verification

Commands run from the dev machine:

```bash
cd backend
./.venv/bin/pytest
./.venv/bin/ruff check src/pi_deck/api/router.py src/pi_deck/services/deck_control.py src/pi_deck/services/live_log.py tests/test_phase14_live_log.py

cd ../frontend
npm test -- --run
npm run build

PI_TARGET=user@pi-hostname ./scripts/deploy.sh
```

Results:

- Backend tests: 27 passed.
- Frontend tests: 13 files passed, 43 tests passed.
- Targeted Ruff check for Phase 14 files: passed.
- Frontend production build: passed.
- Deploy: completed as `0.1.0+r22`, live hardware, JOG mode, idle.

Deploy status:

```json
{
  "version": "0.1.0+r22",
  "hardware": "live",
  "operating_mode": "jog",
  "control_state": "idle",
  "signals": {
    "key_adc1_active": true,
    "key_led_active": false
  }
}
```

Runtime smoke checks on the deployed backend:

```text
log replay: {"category": "log", "data": {"level": "info", "message": "phase14 r22 replay smoke", "source": "smoke"}, "ts": "2026-04-15T17:14:11.580502Z", "type": "entry", "v": 1}
two clients: {"client1": {"level": "info", "message": "phase14 r22 two client smoke", "source": "smoke"}, "client2": {"level": "info", "message": "phase14 r22 two client smoke", "source": "smoke"}}
```

Note: full `ruff check .` still reports unrelated pre-existing long-line violations in older files. The Phase 14 files pass targeted Ruff.

## Host health snapshot

Output of `python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py` on the deck host after the `r22` deploy:

```text
pi-deck host health  |  2026-04-15T17:14:12.521068+00:00
hostname: pi-deck

[python]
  executable: /usr/bin/python3
  version:    3.13.5
  platform:   Linux-6.18.18-v7+-armv7l-with-glibc2.41
  pi_deck:    importable=True  package_version=0.1.0

[cpu]
  model: ARMv7 Processor rev 5 (v7l)
  logical cpus: 4
  load average (1 / 5 / 15 min): 0.63  0.26  0.17

[memory]
  RAM:  total 0.90 GiB  available 0.55 GiB  (MemTotal/MemAvailable KiB: 942120 / 572792)
  swap: total 0.90 GiB  free 0.90 GiB  (KiB: 942076 / 941668)

[disk]  mount /
  size 56.49 GiB  used 4.98 GiB  avail 49.17 GiB  (8.81% used)

[thermal]  sysfs zones
  thermal_zone0  cpu-thermal  47.6 °C

[raspberry_pi]  vcgencmd (SoC voltage / throttling)
  temperature: temp=48.2'C
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
