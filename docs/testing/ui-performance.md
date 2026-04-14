# JOG UI performance — documenting current status

## Canonical tool

Host and **`pi-deck` HTTP health** (the right baseline for “is the deck slow?”) are captured with the **existing** script:

**[`scripts/pi-deck-host-health.py`](../../scripts/pi-deck-host-health.py)**

That is the same utility called out in the [Host health gate](../implementation/plan.md#host-health-gate-feature-phases-1019), [test strategy](test-strategy.md), and phase execution records. Use the **default human-readable text** output for documentation (`--json` is optional for tooling only).

## How to record the current performance status

**On the Raspberry Pi** (SSH session or local terminal):

```bash
python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py
```

**From your dev machine** (paste into a note or append to a phase doc):

```bash
ssh rafael@10.0.0.11 'python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py'
```

Adjust user/host if yours differ.

## Before you measure (UI deploy)

If you care that the kiosk matches a given build, deploy static assets and restart the service **first**, then run the health script:

```bash
./scripts/host/deploy_pi_deck_ui.sh
ssh rafael@10.0.0.11 'python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py'
```

## How to read the output

- **`[pi-deck HTTP]`** — `GET http://127.0.0.1:8756/health` from **on the Pi**. Fast loopback here means the Python/uvicorn path is responsive; if the **on-screen kiosk** still feels laggy, suspect **Chromium rendering / JS** on the device, not the health check alone.
- **`[raspberry_pi]`** — temperature and `get_throttled`; active throttle or under-voltage flags explain uneven UI.
- **`[cpu]` / `[memory]`** — load and memory pressure while you snapshot.
- **`[systemd]`** — confirm `pi-deck.service` is **active**.

## Subjective UI vs this snapshot

Driving the UI from **another PC** over the LAN adds **network RTT** on every request and WebSocket message compared to touching the Pi directly. When filing a performance issue, say **which client** (kiosk on HDMI vs browser on laptop) and paste **one full** `pi-deck-host-health.py` run from the Pi taken at the same time.

## Related

- [Test strategy](test-strategy.md) — automated tests and `E2E_BASE_URL`.
- [Phase 9 platform runbook](../runbooks/phase-9-platform-bring-up.md) — systemd and kiosk.
