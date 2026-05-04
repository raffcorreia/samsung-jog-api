# Phase 24 Execution Record

## Purpose

Track **Phase 24: DDC Capability Investigation** per [Implementation Plan](./plan.md).

## Status

**In progress.** DDC VCP scan and raw I2C register scan complete. Monitor state model partially characterized. Software integration pending.

---

## Work completed

### DDC VCP scan — Samsung C34J79x

Full VCP code enumeration via `ddcutil` (later replaced by direct raw I2C DDC/CI reads via smbus2).

**Key findings:**

- 32 of 256 VCP codes respond on this monitor
- **VCP 0x60 (Input Source)** — most useful: `0x01`=HDMI, `0x03`=DP, `0x04`=Thunderbolt/USB-C
- **VCP 0xD6 (Power Mode)** — `0x01`=on, `0x04`=off (standby)
- **VCP 0x10 (Brightness)** — readable and writable, 0–100 range
- No capability string (`0xF3` returns no data on this monitor)
- VCP 0x60 is stable, unaffected by OSD or on-screen messages

Full results in `docs/investigation/ddc-scan/`.

---

### Raw I2C scan — device map on bus 13

Here, **bus 13** means the Linux monitor-facing I2C adapter exposed as `/dev/i2c-13` in this setup. It is the host-side bus used to reach the monitor's DDC/CI endpoint and other readable monitor-side I2C devices.

Direct smbus2 reads, bypassing DDC/CI entirely.

| Address | Device | Notes |
|---------|--------|-------|
| `0x37` | DDC/CI controller (8051 MCU) | Raw I2C returns bus echo only; must use DDC/CI protocol |
| `0x50` | EDID ROM | |
| `0x54` | Likely HDCP controller | Activates when Pi HDMI port is outputting; not display-state-dependent |
| `0x58` | Novatek scaler SoC (probable) | 256/256 registers readable; holds live scaler and pipeline state |

---

### Device 0x58 — reliable register map

| Register | Meaning |
|----------|---------|
| `0x02=0x79` | Scaler active and healthy — use as scan sanity check |
| `0x48` | Display mode — reads `0x0F` in all active states (single, PBP, PIP); meaning unresolved |
| `0x4A=0x00` | Audio routed to left source |
| `0x4A=0x02` | Audio routed to right source |
| `0xA1=0x00` | No active video signal |

**Persistently noisy registers** (exclude from all detection logic):

`0x3C`, `0x3D`, `0x3E` — free-running counters; `0xA0`, `0xA3`, `0xA5` — active-state noise;
`0x0B`, `0x0C`, `0x0D` — toggle on ~2–4s period (likely frame-sync counters);
`0x1F` — oscillates between `0x00` and `0xEE`.

---

### PIP mode characterization

All PIP captures: Wide style, all four window positions tested, using clean protocol
(`0x02=0x79` guard, 25s wait after any OSD interaction).

**`0x48=0x0F`** is the reliable PIP mode indicator. Stable across all PIP sources, sizes, and positions.

**E0–E3 pipeline register matrix:**

| State | Main | PIP | Size | VCP 0x60 | 0xE0 | 0xE1 | 0xE2 | 0xE3 |
|-------|------|-----|------|----------|------|------|------|------|
| `pip-size1-tb-small-dp-main` | DP | TB | 1 | `0x03` | `0x80` | `0xE2` | `0x00` | `0x00` |
| `pip-size2-tb-small-dp-main` | DP | TB | 2 | `0x03` | `0x40` | `0x8C` | `0x01` | `0x2E` |
| `pip-size3-tb-small-dp-main` | DP | TB | 3 | `0x03` | `0x40` | `0x8C` | `0x01` | `0x2E` |
| `pip-size1-hdmi-small-dp-main` | DP | HDMI | 1 | `0x03` | `0x40` | `0x4E` | `0x00` | `0x00` |
| `pip-size2-hdmi-small-dp-main` | DP | HDMI | 2 | `0x03` | `0x40` | `0x8C` | `0x01` | `0x2E` |
| `pip-size3-hdmi-small-dp-main` | DP | HDMI | 3 | `0x03` | `0x80` | `0xE2` | `0x00` | `0x00` |
| `pip-size1-hdmi-small-tb-main` | TB | HDMI | 1 | `0x04` | `0x40` | `0x35` | `0x05` | `0x20` |
| `pip-size3-hdmi-small-tb-main` | TB | HDMI | 3 | `0x04` | `0x40` | `0x35` | `0x05` | `0x20` |
| `pip-size3-tb-small-hdmi-main` | HDMI | TB | 3 | `0x01` | `0x80` | `0xE2` | `0x00` | `0x00` |

Key conclusions:

- **TB main is blind** — E0–E3 identical across all PIP sources and sizes when TB is main; cannot detect PIP state from registers alone
- **PIP source not independently detectable for DP main** — TB pip and HDMI pip at size2 produce identical E0–E3; same collision at size3 vs size1
- **One unique fingerprint**: HDMI pip / DP main / size1 → `0xE1=0x4E`
- **VCP 0x60 reliably identifies main source** regardless of PIP source, size, or position
- **PIP window position has no effect** — full 256-register diff across all four positions (top-left, top-right, bottom-left, bottom-right) shows no differences in any stable register

---

### OSD / overlay register behaviour

Tested via scripted jog button presses against the pi-deck API, full 256-register scans at 1s intervals.

**What is reliable:**

- **`0xE1=0xFA`** fires when Menu1 OSD is open (including during UP navigation). Use as a scan guard: if `0xE1=0xFA`, abort and retry.
- **`0xE3=0x6E`** appears after UP navigation within Menu1 (`0x00` at first Menu1 item).

**What cannot be tracked:**

- **Menu2 is register-identical to baseline.** After CENTER from Menu1+UP, `0xE1` drops from `0xFA` to its baseline value within ~1s. The registers are byte-for-byte indistinguishable from OSD-closed from that point.
- **OSD inactivity close (~18–20s) produces no detectable register change.** Full 256-register scans at 1s intervals throughout the close window showed nothing definitive.
- **`0xE1=0xFA` is a Menu1 guard only** — does not protect against Menu2 contamination.

**Suspicious one-sample transient at OSD close** (~+18s after Menu2 entry): `0x4A`, `0x0D`, and `0x11` all briefly read `0x00`, recovering at the next 1s sample. Not conclusive — full scan takes ~1s so these may have been caught mid-transition rather than representing a stable state. Not reliable enough to use.

**Practical conclusion:** Clean scan protocol requires a 25s wait after any OSD interaction (25s = 18s inactivity close + 7s margin). Use `0xE1=0xFA` only to guard against Menu1 contamination; Menu2 contamination is undetectable.

---

### PBP mode

All 6 input combinations × 2 sound positions scanned. **E0–E3 data for PBP is contaminated** — input-change notification OSDs were displayed during the original captures. Re-capture with clean protocol is needed before PBP pipeline registers can be trusted.

`0x48=0x00` confirms PBP (or single-source) mode; `0x4A` reliably identifies the active audio source in both PBP and PIP.

---

### Scan evidence

All scan evidence committed to `docs/investigation/i2c-scan/` and `docs/investigation/ddc-scan/`. Full findings, contamination notes, register reference, and scan file index are in [`docs/investigation/i2c-scan/README.md`](../investigation/i2c-scan/README.md).

Investigation scripts: `tools/scripts/collect-register-capture.py`.

---

## Remaining work

- Re-capture all PBP states (6 combos × 2 sound positions) with clean protocol — E0–E3 data contaminated
- Re-capture single-source states (TB, DP, HDMI) for clean E0–E3 baseline
- Capture missing PIP states: all TB-main/DP-pip and HDMI-main/DP-pip combos (9 states never captured)
- Software integration: feed VCP 0x60 + `0x58:0x48` into the monitor state model
- Verify DDC write reliability (input switching, brightness) under normal operating conditions

### Next: interactive register explorer

The flat markdown matrix (`phase-24-full-matrix.md`) is not navigable at scale — 29 rows × 768+ columns (256 DDC + 256 `0x58` + 256 `0x54`) cannot be meaningfully reviewed as static text.

The explorer must be backed by capture files that include the observed monitor state as first-class metadata. Register values alone are not enough; each capture has to record the operator-asserted ground truth so characterization does not depend on inferring state from the same registers under analysis.

**Required capture metadata:**

- Power state: `on` or `standby`
- Signal state: `active` or `idle/no-signal`
- Layout mode: `single`, `PBP`, or `PIP`
- Primary/left input: `HDMI`, `DP`, or `TB`
- Secondary/right input when applicable
- Audio side: `left` or `right`
- PIP main input and PIP window input when applicable
- PIP size and window position when applicable
- Whether OSD is visible at capture time
- Whether the capture is contaminated or otherwise untrusted
- Free-text notes for anything unusual during the read

**Canonical raw capture shape:**

```json
{
  "capture_id": "2026-05-02T01:03:33-04:00_pip_dp_main_hdmi_window_size1_top_right",
  "timestamp": "2026-05-02T01:03:33-04:00",
  "bus": 13,
  "state_label": "main: DP / pip: HDMI / size 1 / top-right",
  "power_state": "on",
  "signal_state": "active",
  "layout_mode": "pip",
  "primary_input": "dp",
  "secondary_input": "hdmi",
  "audio_side": "right",
  "pip": {
    "main_input": "dp",
    "window_input": "hdmi",
    "size": 1,
    "position": "top-right"
  },
  "flags": {
    "osd_visible": false,
    "contaminated": false
  },
  "notes": "",
  "devices": {
    "0x37_ddc": {
      "0x60": 3,
      "0xD6": 1
    },
    "0x54": {
      "0x00": 17,
      "0x01": 44
    },
    "0x58": {
      "0x02": 121,
      "0x48": 15,
      "0x4A": 2,
      "0xA1": 33,
      "0xE0": 64,
      "0xE1": 78,
      "0xE2": 0,
      "0xE3": 0
    }
  }
}
```

Raw captures should remain the source of truth. Any FE-friendly flattened dataset should be generated from these files rather than replacing them.

**Hypothesis to test:** `0x37_ddc`, `0x54`, and `0x58` may not be the only useful endpoints on the monitor-facing bus (`/dev/i2c-13`). Run a discovery pass against all readable device addresses, compare state-to-state variation, and promote any additional device to first-class analysis only if its registers track monitor state in a meaningful way.

**Goal:** a local interactive HTML page (no server required) that loads all scan JSONL files directly and allows:

- All devices in a single view: `0x37_ddc`, `0x54`, `0x58`
- Display states as rows, registers as columns
- Filter: show only registers that vary across states (hide constants)
- Filter by device, mode type (single / PBP / PIP / idle), specific state
- Sort rows and columns
- Color rules: highlight specific values, mark registers as noisy/excluded, flag contaminated captures
- Click a cell to see the raw value and which scan file it came from

This replaces the static matrix as the primary analysis tool and unblocks characterizing `0x54` properly.

---

## Host health gate

*Deferred — investigation phase only; no new service behavior introduced yet. Gate to be satisfied when DDC reads are wired into the control model.*
