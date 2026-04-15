# Phase 11 Execution Record

**Status:** **completed.**

**Date:** 2026-04-13 (live hardware verified 2026-04-14)

## Summary

Phase 11 delivered the **low-level JOG console UI** per [Implementation Plan — Phase 11](plan.md#phase-11-low-level-jog-console-ui) and [Solution Overview — First usable controller](../design/solution-overview.md). Phase 6 / Phase 8 proved the circuit on a bench; this phase required **`PI_DECK_HARDWARE=live` on the kiosk Raspberry Pi** so taps in the UI become real `JOG` pulses on the monitor. **That end-to-end path is verified** on the project deck host: the service runs with live hardware, status reports `hardware: live`, and **physical monitor control works from the deck UI** (and the same UI over the LAN).

**Done in repo:**

- **Frontend:** React + TypeScript + Vite under `frontend/`, production build emitted to `backend/src/pi_deck/static/` (served by FastAPI with the Phase 10 API).
- **Controls:** `up`, `down`, `left`, `right`, `center` with **press-and-hold** mapped to a single `POST /api/v1/jog/press` using measured duration (`duration_ms`).
- **Feedback:** HTTP **409** bodies from the jog endpoint are surfaced in the **live log**; websocket envelopes (`command`, `control`, `bus`) are formatted into the same log stream.
- **Layout:** Deck shell (full viewport, no “landing page” chrome), touch-oriented JOG + status strip, optimized for **1280×800** (7" DSI); same bundle is used for kiosk and LAN (relative API/WebSocket URLs).
- **Tests:** Vitest tests for REST jog client behavior, websocket log formatting, and App-level websocket → log integration (`frontend/`); Playwright e2e exercises the integrated stack.
- **Kiosk:** [scripts/kiosk/pi-deck-chromium-kiosk.sh](../../scripts/kiosk/pi-deck-chromium-kiosk.sh) (JOG UI, `/health` gate, `--disable-features=Translate`) + [pi-deck-kiosk.desktop](../../scripts/kiosk/pi-deck-kiosk.desktop) installed by [install_pi_deck_kiosk_autostart.sh](../../scripts/host/install_pi_deck_kiosk_autostart.sh). Pointer: `unclutter` on X11; optional `wlrctl pointer hide` on Wayland when installed.
- **Policy:** `PI_DECK_HARDWARE=live` in [systemd template](../../config/systemd/pi-deck.service); no silent `auto` → mock fallback — GPIO init failures are visible in `journalctl`.

## Deck host live hardware (verified)

**Deck host:** `pi-deck` (e.g. `10.0.0.11` on the project LAN).

**Verification:**

- `pi-deck.service` is active with **`Environment=PI_DECK_HARDWARE=live`** (or equivalent override).
- `GET http://127.0.0.1:8756/api/v1/status` (or via LAN) reports **`"hardware":"live"`** alongside operating mode / control state.
- **Observable:** JOG actions from the touchscreen (or LAN browser) produce the expected **physical** front-panel behavior on the Samsung CJ791 — not mock-only responses.

**Bring-up reference:** If another board or OS image shows gpiozero/sysfs issues during `DigitalInputDevice` export, use [GPIO bench probe](../runbooks/gpio-bench-probe.md), `GPIOZERO_PIN_FACTORY`, `lgpio` / `RPi.GPIO`, `gpio` group membership, and BCM vs [protoboard map](../../backend/src/pi_deck/hardware/protoboard_pins.py) wiring — the same levers documented during Phase 10 / early Phase 11 bring-up.

## Operational entry points

| Item | Role |
|------|------|
| `frontend/package.json` | `npm run build` → static assets into `backend/src/pi_deck/static/` |
| `pi_deck.api.app:create_app` | Serves built UI and Phase 10 REST + `/ws/events` |

## Exit criteria (from plan)

| Criterion | Evidence |
|-----------|----------|
| User can control the monitor via low-level JOG from the deck UI | Verified on appliance: timed `jog/press` / hold path drives real hardware. |
| No unvalidated high-level monitor feature UI | Only the low-level JOG console is implemented. |
| Frontend tests for command feedback and websocket-driven state | Vitest (+ e2e) under `frontend/`. |
| Host health gate | Snapshot below (deck host); refresh after major OS/kernel upgrades if you rely on the numbers for regression tracking. |

## Optional housekeeping (not blocking Phase 11)

These keep documentation and baselines useful; none of them re-opens the phase.

- **Refresh** `python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py` on the Pi after **kernel / firmware / power** changes and paste a new dated block below if the baseline matters for comparisons.
- **Record non-default overrides** somewhere durable (execution record footnote, local notes, or a `systemd` drop-in comment): e.g. `GPIOZERO_PIN_FACTORY` if not the default on that image.
- **Phase 12** is next per [Implementation Plan — Phase 12](plan.md#phase-12-recording-and-replay-subsystem).

## Host health snapshot

Recorded on the deck host **`pi-deck`** (`10.0.0.11`):

```bash
python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py
```

**Captured output (2026-04-13, post–Phase 11 implementation):**

```
pi-deck host health  |  2026-04-13T18:20:49.252319+00:00
hostname: pi-deck

[python]
  executable: /usr/bin/python3
  version:    3.13.5
  platform:   Linux-6.18.18-v7+-armv7l-with-glibc2.41
  pi_deck:    importable=True  package_version=0.1.0

[cpu]
  model: ARMv7 Processor rev 5 (v7l)
  logical cpus: 4
  load average (1 / 5 / 15 min): 0.00  0.00  0.00

[memory]
  RAM:  total 0.90 GiB  available 0.57 GiB  (MemTotal/MemAvailable KiB: 942120 / 598560)
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

**Review:** `get_throttled` is **`0x0`**. Root filesystem use is **~8.8%**. RAM available **0.57 GiB** of 0.90 GiB. `/health` returns **`status`** and **`version`**.

## JOG UI performance baseline

Subjective “slow kiosk” or “fast on PC, slow on Pi HDMI” reports need a **fixed procedure** so regressions are comparable.

**Canonical snapshot tool (same as [Host health gate](plan.md#host-health-gate-feature-phases-1019)):** run on the deck host:

```bash
python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py
```

Use the **default text output** (not `--json`) when pasting into execution records.

**Before comparing UI builds**, deploy the built static bundle and restart `pi-deck` so the kiosk is not on stale hashed assets:

```bash
# From dev machine, repo root (see scripts/host/deploy_pi_deck_ui.sh)
./scripts/host/deploy_pi_deck_ui.sh
```

Then re-run `pi-deck-host-health.py` on the Pi.

**How to read the snapshot for UI work**

| Section | Meaning for JOG UI |
|--------|---------------------|
| `[pi-deck HTTP]` | Loopback `GET /health` on the Pi. If this is fast but the **on-screen** UI still lags, the bottleneck is likely **Chromium / React paint** on the device, not FastAPI alone. |
| `[raspberry_pi]` → `get_throttled` | Non‑zero flags (under-voltage, throttle) can cause **uneven** frame times and missed taps. |
| `[cpu]` load | High load while idle may indicate background work competing with the browser. |
| `[systemd]` | `pi-deck.service` must be **active**; otherwise the UI cannot load or update. |

**Kiosk vs LAN browser:** Controlling the deck from **another PC** (`http://10.0.0.11:8756`) adds **network RTT** on every REST/WebSocket round-trip compared to touching the **Pi touchscreen** directly. When filing issues, state **which client** was used.

**Related:** [Test strategy — deck host snapshots](../testing/test-strategy.md#8-deck-host-health-snapshots) points to this section for **JOG kiosk / LAN** interpretation.
