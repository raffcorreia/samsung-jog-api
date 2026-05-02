# Samsung C34J79x — Raw I2C Scan Findings

Phase 24 investigation. Raw I2C reads via `smbus2` on I2C bus 13, bypassing DDC/CI protocol.
DDC only surfaces what the firmware advertises; direct I2C exposes the full scaler register map.

Script: `scripts/i2c-scan.py`

---

## Device map — I2C bus 13

| Address | Device | Notes |
|---------|--------|-------|
| `0x37` | DDC/CI controller (8051 MCU) | Raw I2C returns bus echo only; must use DDC/CI protocol |
| `0x50` | EDID ROM | |
| `0x54` | Likely HDCP controller | Activates when Pi HDMI port is outputting; not display-state-dependent |
| `0x58` | Novatek scaler SoC (probable) | 256/256 registers readable; holds live scaler and pipeline state |

---

## DDC VCP 0x60 — most reliable source indicator

Read via DDC/CI protocol on device 0x37 (no ddcutil needed). Unaffected by OSD or overlays.

| Value | Source |
|-------|--------|
| `0x01` | HDMI |
| `0x03` | DisplayPort |
| `0x04` | Thunderbolt / USB-C |

In PBP mode: reports the left/primary source.
In PIP mode: reports the main (large) source.

---

## Device 0x58 — register reference

### Reliable registers

| Register | Meaning |
|----------|---------|
| `0x48=0x0F` | PIP mode active (was `0x00` in all PBP and single-source captures) |
| `0x48=0x00` | PBP or single-source mode |
| `0x4A=0x00` | Sound routed left |
| `0x4A=0x02` | Sound routed right |
| `0xA1=0x00` | No active video signal |
| `0x02=0x79` | Scan sanity check — confirms scaler is in a normal active state |

### Persistently noisy registers — exclude from detection logic

These change between reads of the same state and carry no reliable state information:

- `0x3C`, `0x3D`, `0x3E` — free-running counters
- `0xA0`, `0xA3`, `0xA5` — active-state noise, no stable value
- `0xA1` — toggles between `0x21` and `0x22` unpredictably during active video
- `0x0B`, `0x0C`, `0x0D` — toggle between two fixed values on a ~2–4s period; likely frame sync counters
- `0x1F` — oscillates between `0x00` and `0xEE`

---

## PIP mode — E0–E3 pipeline register matrix

> All PIP scans: style = **Wide**, position = **top-left** (position has no effect on any register — see below).
> All confirmed clean: `0x58:0x02=0x79`, `0xE1≠0xFA` at scan time.

| Directory | Main | PIP | Size | VCP 0x60 | 0xE0 | 0xE1 | 0xE2 | 0xE3 |
|-----------|------|-----|------|----------|------|------|------|------|
| `pip-size1-tb-small-dp-main` | DP | TB | 1 | `0x03` | `0x80` | `0xE2` | `0x00` | `0x00` |
| `pip-size2-tb-small-dp-main` | DP | TB | 2 | `0x03` | `0x40` | `0x8C` | `0x01` | `0x2E` |
| `pip-size3-tb-small-dp-main` | DP | TB | 3 | `0x03` | `0x40` | `0x8C` | `0x01` | `0x2E` |
| `pip-size1-hdmi-small-dp-main` | DP | HDMI | 1 | `0x03` | `0x40` | `0x4E` | `0x00` | `0x00` |
| `pip-size2-hdmi-small-dp-main` | DP | HDMI | 2 | `0x03` | `0x40` | `0x8C` | `0x01` | `0x2E` |
| `pip-size3-hdmi-small-dp-main` | DP | HDMI | 3 | `0x03` | `0x80` | `0xE2` | `0x00` | `0x00` |
| `pip-size1-hdmi-small-tb-main` | TB | HDMI | 1 | `0x04` | `0x40` | `0x35` | `0x05` | `0x20` |
| `pip-size3-hdmi-small-tb-main` | TB | HDMI | 3 | `0x04` | `0x40` | `0x35` | `0x05` | `0x20` |
| `pip-size3-tb-small-hdmi-main` | HDMI | TB | 3 | `0x01` | `0x80` | `0xE2` | `0x00` | `0x00` |

### Key findings from the matrix

- **TB main is fully blind** — E0–E3 are identical (`0x40/0x35/0x05/0x20`) regardless of PIP source or size.
  Cannot detect PIP source, size, or position from registers when TB is the main source.
- **PIP source is not independently detectable for DP main** — TB pip and HDMI pip at size2 produce identical
  E0–E3 values; same at size3 vs size1. Only size1 HDMI pip has a unique value (`0xE1=0x4E`).
- **E0–E3 encode a non-linear combination** of main source, PIP source, and size simultaneously.
  Cannot decode any single dimension independently.
- **VCP 0x60 identifies main source reliably** regardless of PIP source, size, or position.

### Contamination note

`pip-size1-hdmi-small-dp-main` was recaptured on 2026-05-02 after the original scan was found contaminated —
E0–E3 matched the Menu2 OSD state exactly, indicating the OSD was still open when the original scan ran.
The recheck confirmed the clean values above.

---

## PIP window position — register invisible

Tested on HDMI pip / TB main / size1 across all four positions (top-left, top-right, bottom-left, bottom-right).
Full 256-register diff showed no differences in any stable register across all positions.
**PIP window position has no effect on any 0x58 register.**

---

## OSD / overlay register behaviour

Tested 2026-05-02 via scripted button presses, full 256-register scan at 1s intervals.
State: TB main / HDMI pip / size1 / Wide / top-left.

### What is reliable

- **`0xE1=0xFA`** — fires when Menu1 OSD is open (including after UP navigation). Use as a scan guard:
  if `0xE1=0xFA`, abort and retry — the scan will be contaminated.
- **`0xE3=0x6E`** — appears after UP navigation within Menu1. `0x00` at the first Menu1 item.
- **`0xA7=0x00`** — drops during a physical button press, recovers to `0xF8` within ~500ms.

### What cannot be tracked

- **Menu2 is register-identical to baseline.** When CENTER is pressed from Menu1+UP, `0xE1` drops from
  `0xFA` back to its baseline value within ~1s. Registers look exactly like OSD-closed from that point.
  There is no way to tell from 0x58 whether Menu2 is on screen.
- **OSD inactivity close (~18–20s after last input in Menu2) produces no detectable register change.**
  Full 256-register scans at 1s intervals throughout the close window showed nothing definitive.
- **`0xE1=0xFA` is a Menu1 indicator only, not a universal OSD indicator.** The clean-scan guard
  only protects against Menu1 contamination; Menu2 contamination is invisible.

### Suspicious registers observed at OSD close

A one-sample transient was caught at the moment the OSD appeared to close (~+18s after Menu2 entry):
`0x4A`, `0x0D`, and `0x11` all read `0x00` simultaneously, recovering at the next 1s sample.
`0x4A` (sound routing) is normally rock-solid at rest. Not conclusive — the full scan takes ~1s to
execute, so these may have been caught mid-transition rather than representing a stable state.

---

## ⚠️ E0–E3 contamination warning

All PBP scan data for `0xE0`–`0xE3` is potentially contaminated — input-change notifications and OSD
menus were likely displayed during those captures.

**Protocol for clean captures:**
1. Wait for all on-screen messages to fully dismiss
2. Confirm `0xE1 ≠ 0xFA` (no Menu1 OSD open)
3. Be aware that Menu2 is undetectable — wait at least 25s after any OSD interaction before scanning

---

## Scan file index

### Baseline / single-source (Phase 24 initial scans)

| File | State |
|------|-------|
| `i2c-scan-idle-20260501-210013.jsonl` | Monitor idle, no active source |
| `i2c-0x58-on-idle-20260501-212914.jsonl` | 0x58 only, post-reboot idle |
| `i2c-0x58-tb-active-20260501-214114.jsonl` | 0x58 only, Thunderbolt active |
| `i2c-all-tb-active-20260501-215231.jsonl` | All devices, Thunderbolt active |
| `i2c-all-dp-active-20260501-220136.jsonl` | All devices, DisplayPort active |
| `i2c-all-hdmi-active-20260501-222201.jsonl` | All devices, HDMI active (Pi, incompatible resolution) |

### PBP (contaminated — E0–E3 not trustworthy)

`pbp-*/` — all 6 combinations × 2 sound positions. E0–E3 captured with input-change messages on screen.

### PIP (clean, Wide style, top-left unless noted)

See matrix table above. Position scans (top-right, bottom-left, bottom-right) stored under
`pip-size1-hdmi-small-tb-main-{topright,bottomleft,bottomright}/` — confirmed identical to top-left.
