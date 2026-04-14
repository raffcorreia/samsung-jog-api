# Phase 11 Execution Record

**Status:** **in progress.** UI, API usage, and tests are in the repository; **live GPIO on the deck host** (prototype → appliance) is **still open** — see [Deck host live hardware](#deck-host-live-hardware) below.

**Date:** 2026-04-13 (updated 2026-04-14)

## Summary

Phase 11 delivers the **low-level JOG console UI** per [Implementation Plan — Phase 11](plan.md#phase-11-low-level-jog-console-ui) and [Solution Overview — First usable controller](../design/solution-overview.md). The plan explicitly treats **this phase** as the place to **finish** moving off pure prototype hand-waving: Phase 6 / Phase 8 proved the circuit and scripts on a bench; **Phase 11 must make `PI_DECK_HARDWARE=live` work on the kiosk Raspberry Pi** so taps in the UI become real `JOG` pulses.

**Done in repo:**

- **Frontend:** React + TypeScript + Vite under `frontend/`, production build emitted to `backend/src/pi_deck/static/` (served by FastAPI with the Phase 10 API).
- **Controls:** `up`, `down`, `left`, `right`, `center` with **press-and-hold** mapped to a single `POST /api/v1/jog/press` using measured duration (`duration_ms`).
- **Feedback:** HTTP **409** bodies from the jog endpoint are surfaced in the **live log**; websocket envelopes (`command`, `control`, `bus`) are formatted into the same log stream.
- **Layout:** Touch-oriented D-pad + status strip, optimized for **1024×600** landscape; same bundle is used for kiosk and LAN (relative API/WebSocket URLs).
- **Tests:** Vitest tests for REST jog client behavior, websocket log formatting, and App-level websocket → log integration (`frontend/`).
- **Kiosk:** [scripts/kiosk/pi-deck-chromium-kiosk.sh](../../scripts/kiosk/pi-deck-chromium-kiosk.sh) (JOG UI, `/health` gate, `--disable-features=Translate`) + [pi-deck-kiosk.desktop](../../scripts/kiosk/pi-deck-kiosk.desktop) installed by [install_pi_deck_kiosk_autostart.sh](../../scripts/host/install_pi_deck_kiosk_autostart.sh). Pointer: `unclutter` on X11; optional `wlrctl pointer hide` on Wayland when installed.
- **Policy:** `PI_DECK_HARDWARE=live` in [systemd template](../../config/systemd/pi-deck.service); no silent `auto` → mock fallback — GPIO init failures are visible in `journalctl`.

## Deck host live hardware

**Scope:** Phase 11 **includes** fixing gpiozero / Linux GPIO bring-up on the **deck host** (`pi-deck` service) so `LiveDeckHardware` constructs without error and `hardware.pulse` drives the Phase 6–style lines. This is not deferred to a separate “prototype” phase — the prototype validated the **design**; this phase validates the **appliance**.

**As of 2026-04-14**, with `Environment=PI_DECK_HARDWARE=live`, startup can still fail during `DigitalInputDevice` / sysfs export (`OSError: [Errno 22] Invalid argument` with the native pin factory). **Exit for Phase 11** requires resolving that on the real host (typical levers: `GPIOZERO_PIN_FACTORY`, `lgpio` / `RPi.GPIO`, `gpio` group, BCM vs wiring, see [GPIO bench probe](../runbooks/gpio-bench-probe.md) and Phase 10 notes).

**When fixed, paste here:** `GET /api/v1/status` from the Pi showing `"hardware":"live"`, plus a one-line note (e.g. pin factory used). Replace or supplement the host health snapshot below if `/health` was down during the failure window.

## Operational entry points

| Item | Role |
|------|------|
| `frontend/package.json` | `npm run build` → static assets into `backend/src/pi_deck/static/` |
| `pi_deck.api.app:create_app` | Serves built UI and Phase 10 REST + `/ws/events` |

## Exit criteria (from plan)

| Criterion | Evidence |
|-----------|----------|
| User can control the monitor via low-level JOG from the deck UI | JOG console issues timed `jog/press` calls; hold = one request with elapsed duration. |
| No unvalidated high-level monitor feature UI | Only the low-level JOG console is implemented. |
| Frontend tests for command feedback and websocket-driven state | Vitest suite under `frontend/src/`. |
| Host health gate | Snapshot below (deck host). |

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
