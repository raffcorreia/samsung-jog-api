# Phase 24 — DDC + I2C Register Reference

Consolidated register reference for the Samsung C34J79x combining DDC/CI (device `0x37`, via VCP codes)
and raw I2C (device `0x58`, Novatek scaler SoC). All reads on I2C bus 13.

---

## Display state coverage

All possible display configurations across 3 sources (HDMI, DP, TB). Audio excluded — tracked separately via `0x4A`.

**Single source — 3 states**

| State | Scan |
|-------|------|
| HDMI | ⚠ Pi source, incompatible resolution |
| DP | ⚠ early scan, contamination risk |
| TB | ⚠ early scan, contamination risk |

**PBP side-by-side — 6 states** (left source = primary, reported by VCP `0x60`)

| Left | Right | Scan |
|------|-------|------|
| DP | HDMI | ⚠ OSD contamination |
| DP | TB | ⚠ OSD contamination |
| HDMI | DP | ⚠ OSD contamination |
| HDMI | TB | ⚠ OSD contamination |
| TB | DP | ⚠ OSD contamination |
| TB | HDMI | ⚠ OSD contamination |

**PIP overlay — 18 states** (main × pip × size 1/2/3)

| Main | PIP | Size 1 | Size 2 | Size 3 |
|------|-----|--------|--------|--------|
| DP | HDMI | ✓ | ✓ | ✓ |
| DP | TB | ✓ | ✓ | ✓ |
| HDMI | DP | — | — | — |
| HDMI | TB | — | — | ✓ |
| TB | DP | — | — | — |
| TB | HDMI | ✓ | — | ✓ |

**No signal / idle — 1 state:** ✓

**Standby — 1 state:** — (never captured)

**Total: 29 states. Data (clean or contaminated) for 18. Missing: all HDMI/TB-main DP-pip states, HDMI-main TB-pip sizes 1–2, TB-main HDMI-pip size 2, TB-main DP-pip all sizes.**

---

## Register map

### DDC/CI — device `0x37`

| VCP code | Name | Useful values |
|----------|------|---------------|
| `0x60` | Input Source | `0x01`=HDMI · `0x03`=DP · `0x04`=TB/USB-C |
| `0xD6` | Power Mode | `0x01`=on · `0x04`=standby |
| `0x10` | Brightness | 0–100 (readable + writable) |
| `0x62` | Audio Speaker Volume | 0–100 |

VCP `0x60` reports the **primary/left** source in PBP mode; the main (large-window) source in PIP mode.
No capability string (`0xF3` returns no data on this monitor).

### I2C device `0x58` — key registers

| Register | Meaning |
|----------|---------|
| `0x02` | Scaler sanity — must read `0x79` before trusting any other register |
| `0x48` | Display mode — meaning unresolved; see notes |
| `0x4A` | Audio routing — `0x00`=left source · `0x02`=right source |
| `0xA1` | Signal presence — `0x00`=no active signal · `0x21`/`0x22`=active (toggles, not meaningful) |
| `0xE0`–`0xE3` | Pipeline config — encodes source+layout combination in PIP mode |
| `0xE1` | OSD guard — reads `0xFA` when Menu1 OSD is open; abort scan and retry |

**Persistently noisy registers — exclude from all detection logic:**
`0x3C`, `0x3D`, `0x3E` (free-running counters) · `0xA0`, `0xA3`, `0xA5` (active-state noise) ·
`0x0B`, `0x0C`, `0x0D` (toggle ~2–4s, likely frame-sync counters) · `0x1F` (oscillates `0x00`↔`0xEE`)

---

## Monitor state matrix

**Legend:**
`?` = no scan file exists for this state · `⚠val` = value captured but potentially contaminated (OSD or mode uncertainty)

`0xA1` toggles between `0x21` and `0x22` in any active-signal state — the exact value captured depends on timing and is not meaningful. `0x00` is the reliable no-signal indicator.

VCP `0x60` and `0xD6` were not included in the earliest scan format; values marked `†` are inferred with certainty from monitor state.

All PIP captures: Wide style, audio right (`0x4A=0x02`). PIP window position has no effect on any register.

| Mode | State | VCP `0x60` | VCP `0xD6` | `0x48` | `0x4A` | `0xA1` | `0xE0` | `0xE1` | `0xE2` | `0xE3` |
|------|-------|-----------|-----------|--------|--------|--------|--------|--------|--------|--------|
| **Standby** | — | `?` | `0x04` | `?` | `?` | `?` | `?` | `?` | `?` | `?` |
| **Idle** | no signal | `?`† | `0x01`† | `0x0F` | `0x02` | `0x00` | `0x00` | `0x00` | `0x00` | `0x00` |
| **Single** | HDMI | `0x01`† | `0x01`† | `0x0F` | `0x02` | `0x22` | ⚠`0x40` | ⚠`0x83` | ⚠`0x01` | ⚠`0x20` |
| **Single** | DP | `0x03`† | `0x01`† | `0x0F` | `0x02` | `0x21` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **Single** | TB | `0x04`† | `0x01`† | `0x0F` | `0x02` | `0x21` | ⚠`0xF4` | ⚠`0x00` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | DP left / HDMI right — audio right | `0x03` | `0x01` | `0x0F` | `0x02` | `0x21` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | DP left / HDMI right — audio left | `0x03` | `0x01` | `?` | `?` | `?` | `?` | `?` | `?` | `?` |
| **PBP** | DP left / TB right — audio right | `0x03` | `0x01` | `0x00`‡ | `0x02` | `0x21` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | DP left / TB right — audio left | `0x03` | `0x01` | `?` | `?` | `?` | `?` | `?` | `?` | `?` |
| **PBP** | HDMI left / DP right — audio left | `0x01` | `0x01` | `0x0F` | `0x00` | `0x21` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | HDMI left / DP right — audio right | `0x01` | `0x01` | `0x0F` | `0x02` | `0x21` | ⚠`0x40` | ⚠`0x35` | ⚠`0x05` | ⚠`0x20` |
| **PBP** | HDMI left / TB right — audio right | `0x01` | `0x01` | `0x0F` | `0x02` | `0x22` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | HDMI left / TB right — audio left | `0x01` | `0x01` | `?` | `?` | `?` | `?` | `?` | `?` | `?` |
| **PBP** | TB left / DP right — audio right | `0x04` | `0x01` | `0x0F` | `0x02` | `0x22` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | TB left / DP right — audio left | `0x04` | `0x01` | `?` | `?` | `?` | `?` | `?` | `?` | `?` |
| **PBP** | TB left / HDMI right — audio right | `0x04` | `0x01` | `0x0F` | `0x02` | `0x21` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | TB left / HDMI right — audio left | `0x04` | `0x01` | `?` | `?` | `?` | `?` | `?` | `?` | `?` |
| **PIP** | main: DP / pip: TB / size 1 | `0x03` | `0x01` | `0x0F` | `0x02` | `0x22` | `0x80` | `0xE2` | `0x00` | `0x00` |
| **PIP** | main: DP / pip: TB / size 2 | `0x03` | `0x01` | `0x0F` | `0x02` | `0x21` | `0x40` | `0x8C` | `0x01` | `0x2E` |
| **PIP** | main: DP / pip: TB / size 3 | `0x03` | `0x01` | `0x0F` | `0x02` | `0x22` | `0x40` | `0x8C` | `0x01` | `0x2E` |
| **PIP** | main: DP / pip: HDMI / size 1 | `0x03` | `0x01` | `0x0F` | `0x02` | `0x21` | `0x40` | `0x4E` | `0x00` | `0x00` |
| **PIP** | main: DP / pip: HDMI / size 2 | `0x03` | `0x01` | `0x0F` | `0x02` | `0x21` | `0x40` | `0x8C` | `0x01` | `0x2E` |
| **PIP** | main: DP / pip: HDMI / size 3 | `0x03` | `0x01` | `0x0F` | `0x02` | `0x21` | `0x80` | `0xE2` | `0x00` | `0x00` |
| **PIP** | main: TB / pip: HDMI / size 1 | `0x04` | `0x01` | `0x0F` | `0x02` | `0x21` | `0x40` | `0x35` | `0x05` | `0x20` |
| **PIP** | main: TB / pip: HDMI / size 3 | `0x04` | `0x01` | `0x0F` | `0x02` | `0x22` | `0x40` | `0x35` | `0x05` | `0x20` |
| **PIP** | main: HDMI / pip: TB / size 3 | `0x01` | `0x01` | `0x0F` | `0x02` | `0x22` | `0x80` | `0xE2` | `0x00` | `0x00` |

† Not present in scan file (old format predated DDC reads). VCP `0x60` for idle is genuinely unknown — it retains the last-used source with no sentinel reset. VCP `0xD6=0x01` and source values are certain from monitor state.

‡ `0x48=0x00` observed in `pbp-dp-tb-sound-right` only; all other PBP scans show `0x48=0x0F`. Meaning of `0x48` is unresolved — retake scheduled.

Remaining `?` rows are states never captured: standby and the 5 PBP audio-left combos (audio was already on the right when those scans ran).

---

## Detection rules

Given a set of clean register reads (`0x02=0x79`, `0xE1≠0xFA`, 25s elapsed after any OSD interaction):

| Question | How to answer |
|----------|---------------|
| Is the monitor in standby? | VCP `0xD6 = 0x04` |
| Is there an active signal? | `0xA1 ≠ 0x00` |
| Which source is primary? | VCP `0x60` — `0x01`=HDMI, `0x03`=DP, `0x04`=TB |
| Which side has audio? | `0x4A` — `0x00`=left/primary, `0x02`=right/secondary |
| What is the secondary source? | **Not reliably detectable.** Only exception: HDMI pip / DP main / size 1 → `0xE1=0x4E`. In all other PIP configurations the secondary source cannot be distinguished from registers alone. PBP secondary source: no clean data yet. |
| Is PIP mode active? | `0xE0`–`0xE3` match a known PIP fingerprint (see table above) |
| Is PIP size identifiable? | Only size 2 (DP main, `0xE1=0x8C`); sizes 2 and 3 collide |
| Can I detect PIP state with TB main? | No — E0–E3 identical for all sizes and PIP sources |
| Is PBP mode active? | `0x48` — unresolved, retake pending |

---

## Data gaps — retakes scheduled 2026-05-03

- `0x48`: reads `0x0F` in all modes from existing data (single-source, PBP, PIP); one unexplained `0x00` in `pbp-dp-tb-sound-right` — treated as outlier, no retake needed
- Single-source E0–E3: need clean re-captures (early scans have contamination risk)
- PBP audio-left states: 5 combos never captured with audio on the left
- PBP E0–E3: all captures have OSD/input-change contamination — full re-capture needed
- PIP audio-independence: confirm E0–E3 unchanged when `0x4A=0x00`
- Missing PIP sizes: TB main size 2; HDMI main sizes 1 and 2
