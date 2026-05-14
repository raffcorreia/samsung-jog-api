# Phase 24 Execution Record

## Purpose

Track **Phase 24: DDC Capability Investigation** per [Implementation Plan](./plan.md).

## Status

**Investigation complete.** Full 35-test-case capture matrix recorded and analysed. Interactive register explorer built and deployed. Layout-mode detection via I2C proven not feasible from observable registers; primary input and physical port presence are reliably readable. Software integration and physical port connectivity experiment (HDMI-only isolation) remain as follow-on work.

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

Full results in [`docs/investigation/ddc-scan/`](../investigation/ddc-scan/README.md).

---

### Raw I2C scan — device map on bus 13

Here, **bus 13** means the Linux monitor-facing I2C adapter exposed as `/dev/i2c-13` in this setup. It is the host-side bus used to reach the monitor's DDC/CI endpoint and other readable monitor-side I2C devices.

Direct smbus2 reads, bypassing DDC/CI entirely.

| Address | Device | Notes |
|---------|--------|-------|
| `0x37` | DDC/CI controller (8051 MCU) | Raw I2C returns bus echo only; must use DDC/CI protocol |
| `0x3A` | Unknown monitor-side device | Discovered on 2026-05-04 bus sweep; 256/256 registers readable in single-source TB state |
| `0x50` | EDID ROM | |
| `0x54` | Likely HDCP controller | Activates when Pi HDMI port is outputting; not display-state-dependent |
| `0x58` | Novatek scaler SoC (probable) | 256/256 registers readable; holds live scaler and pipeline state |

Bus discovery retake on 2026-05-04 (single-source TB) found five readable addresses on `/dev/i2c-13`:
`0x37`, `0x3A`, `0x50`, `0x54`, and `0x58`. Future repeated captures should include `0x3A`
alongside `0x54`, `0x58`, and the full DDC VCP sweep on `0x37`.

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

All scan evidence committed to [`docs/investigation/i2c-scan/`](../investigation/i2c-scan/README.md) and [`docs/investigation/ddc-scan/`](../investigation/ddc-scan/README.md). Full findings, contamination notes, register reference, and scan file index are in [`docs/investigation/i2c-scan/README.md`](../investigation/i2c-scan/README.md).

Investigation scripts: [`tools/scripts/collect-register-capture.py`](../../tools/scripts/collect-register-capture.py).

---

### Interactive register explorer

Built and deployed at [`tools/register-explorer/`](../../tools/register-explorer/index.html) — a local, server-optional interactive HTML page that loads all canonical capture JSON files and presents them in a single navigable view.

**Features:**

- All five devices in one view: `0x3A`, `0x50`, `0x54`, `0x58`, `0x37_ddc`
- Test-case preset buttons (TC1–TC50+) that pre-fill all filter dropdowns in one click
- Filter by: power state, layout mode, primary input, secondary input, PIP size, audio side, jog button, signal state, metadata certainty, OSD visibility
- "Show only varying registers" toggle — hides registers constant across the filtered capture set
- Per-register value colour coding and user-defined labels
- Relevant/irrelevant register tagging persisted in browser localStorage
- Cell click shows raw value and source filename
- Side-by-side capture comparison mode

**Build:** [`tools/scripts/build-register-explorer-data.py`](../../tools/scripts/build-register-explorer-data.py) regenerates `tools/register-explorer/data/register-explorer.json` from all captures under [`docs/investigation/register-captures/`](../investigation/register-captures/). Run after every new capture import.

**Capture pipeline:** [`tools/scripts/collect-register-capture.py`](../../tools/scripts/collect-register-capture.py) (interactive, runs on Pi) → scp pull → patch `jog_button` and `metadata_certainty` fields → [`tools/scripts/backfill-test-case.py`](../../tools/scripts/backfill-test-case.py) → `build-register-explorer-data.py`.

---

### Full 35-test-case capture matrix

All 35 canonical test cases captured and imported with double-pass verification (two independent captures per test case, majority-vote reads per register). Total capture set: 81 files covering all single, PIP, and PBP combinations across TB, HDMI, and DP inputs; standby and idle baselines included.

Capture read strategy: majority-vote per register (up to 5 reads, 3-match consensus), flagging registers that never reached consensus. All captures use `flags.include_in_explorer: true` and `flags.metadata_certainty: "high"`.

---

### Comprehensive register analysis — layout-mode detection

After importing the full matrix and analysing all varying registers across all five devices (`0x3A`, `0x50`, `0x54`, `0x58`, `0x37_ddc`), the following was established:

**What is reliably readable:**

| Register | Meaning | Values |
|----------|---------|--------|
| `0x37_ddc VCP 0x60` | Primary input source | `0x04`=TB, `0x01`=HDMI, `0x03`=DP |
| `0x58:0xBC` | Active vs standby/idle | `0x01`=active, `0x00`=standby or idle |

**VCP 0x60** is stable and consistent across all 35 test cases (one anomaly on TC15, likely a transient). It identifies the primary source regardless of layout mode, PIP size, or audio side. Standby also returns `0x04` (same as TB), so `0x58:0xBC` is required to distinguish TB-active from standby.

**What is not detectable from registers:**

| State dimension | Conclusion |
|----------------|------------|
| Layout mode (single / PIP / PBP) | Not encoded in any observable register across all five devices |
| Secondary / window input source | Not detectable independently of primary input |
| PIP size | `0x58:0xE0–0xE3` vary with PIP configuration but encode pixel geometry (resolution + size combined); the same values appear in single-source states. No clean size enum exists. |
| Audio side (left / right) | Not detectable from any register |

**Device-level conclusions:**

- **`0x3A` (HDCP 1.4 receiver):** Registers `0x08`–`0x09` (Ri') and `0x0A` (Pj') do vary across captures but carry HDCP link-verification frame counters that update every 128 frames (~2s at 60 Hz). The values reflect HDCP session timing, not layout state. All 11 HDMI-primary captures share identical Ri' values regardless of single/PIP/PBP layout, confirming session-based rather than layout-based encoding.
- **`0x50` (EDID ROM):** Many registers vary but encode PIP window pixel geometry, not a layout mode flag. Not useful for state detection.
- **`0x54`:** Register `0x10` varies, but its behaviour is governed by physical port connectivity rather than display layout (see connectivity experiment below).
- **`0x58`:** Registers `0x3C`, `0x3D`, `0x3E`, `0xA0`, `0xA3` are free-running counters with no layout correlation. `0xE0–0xE3` encode pipeline geometry whose same values appear across single-source and multi-source states, making layout inference impossible.
- **`0x37_ddc` (raw register scan):** All responding registers return `0x6E` or `0xBE` (device address echo). The `0x37` device is a protocol-only DDC/CI controller, not a memory-mapped register bank. VCP codes must be accessed via DDC/CI protocol, not raw I2C byte reads.

---

### Physical port connectivity experiment

Targeted experiment to determine whether the physical presence of each cable (regardless of whether it is the active source) is detectable from registers. Single-source test cases TC3 (TB primary), TC14 (HDMI primary), and TC25 (DP primary) were captured across all reachable port-connected subsets by disconnecting cables one at a time. Two passes per configuration for stability verification.

**Configurations tested:**

- TC3: `dp+hdmi+tb` (baseline) vs `hdmi+tb` (DP cable removed)
- TC14: `dp+hdmi+tb` (baseline) vs `dp+hdmi` (TB removed) vs `hdmi+tb` (DP removed) vs `hdmi` (both removed)
- TC25: `dp+hdmi+tb` (baseline) vs `dp+hdmi` (TB removed)

**Results:**

| Register | TB removed | DP removed | Notes |
|----------|-----------|-----------|-------|
| `0x58:0xA1` | non-zero → `0x00` | no change | **TB physical connection indicator** |
| `0x58:0xA3` | no change | `0xDC–0xDE → 0x01` | **DP physical connection indicator** |
| `0x54:0x10` | `0x01 → 0x03` | `0x01 → 0x03` | Changes on either removal; not port-specific alone |
| `0x37_ddc:0xFE` | `0x02 → 0x01` | `0x02 → 0x01` | `0x02` only when all three ports present |
| `0x58:0xA5` | `0xB3 → 0x00` | no change | Mirrors `0xA1` but noisy within groups |

**Decoding rules:**

- **`0x58:0xA1 = 0x00`** → TB cable is not physically connected. Any non-zero value → TB present. Stable across all passes; does not change when DP is removed. The specific non-zero value varies between passes (`0x21` and `0x22` observed in single-source states) and may differ in PIP/PBP configurations — only the zero/non-zero distinction is reliable.
- **`0x58:0xA3 = 0x01`** → DP cable is not physically connected. Values in the `0xDA–0xE0` range → DP present. The specific value within that range is a cycling counter and varies between passes; only the `0x01` sentinel is significant. Does not change when TB is removed.
- **`0x54:0x10`** alone cannot identify which port is absent; it requires combination with `0xA1` and `0xA3` to disambiguate. Additional context: `0x54:0x10 = 0x01` also appears when DP is connected but not the primary source (single-TB or single-HDMI with all ports present), and `0x03` when DP is the primary source even with all ports connected — so this register reflects both DP-active state and DP-absent state as the same value.
- **`0x37_ddc:0xFE`** is a useful "all three connected" gate: `0x02` confirms dp+hdmi+tb all present; any other value means at least one port is missing, but does not identify which.

**Not yet tested:** HDMI cable removal with TB and DP still connected. No HDMI-specific isolation register has been identified from the data collected. A `dp+tb` (HDMI removed) capture set would be needed to confirm or rule out a HDMI presence indicator.

---

## Remaining work

- **HDMI isolation capture:** repeat connectivity experiment with only HDMI disconnected (dp+tb connected) on TC3 or TC25 to find or rule out a HDMI-specific presence register
- **Software integration:** wire `VCP 0x60` + `0x58:0xBC` into the monitor state model as the primary-input and power-state signals
- **Port presence integration:** expose `0x58:0xA1` (TB) and `0x58:0xA3` (DP) in the state model for cable-presence detection
- Verify DDC write reliability (input switching, brightness) under normal operating conditions

---

## Host health gate

*Deferred — investigation phase only; no new service behavior introduced yet. Gate to be satisfied when DDC reads are wired into the control model.*
