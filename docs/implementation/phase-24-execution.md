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
| `0x48=0x0F` | PIP mode active |
| `0x48=0x00` | PBP or single-source mode |
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

Investigation scripts: `scripts/i2c-scan.py`.

---

## Remaining work

- Re-capture all PBP states (6 combos × 2 sound positions) with clean protocol — E0–E3 data contaminated
- Re-capture single-source states (TB, DP, HDMI) for clean E0–E3 baseline
- Software integration: feed VCP 0x60 + `0x48` into the monitor state model
- Verify DDC write reliability (input switching, brightness) under normal operating conditions

---

## Host health gate

*Deferred — investigation phase only; no new service behavior introduced yet. Gate to be satisfied when DDC reads are wired into the control model.*
