# Phase 24 — DDC + I2C Register Reference

Consolidated register reference for the Samsung C34J79x combining DDC/CI (device `0x37`, via VCP codes)
and raw I2C (device `0x58`, Novatek scaler SoC). All reads on I2C bus 13.

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
| `0xA1` | Signal presence — `0x00`=no active signal · `0x21`/`0x22`=active (noisy, toggles) |
| `0xE0`–`0xE3` | Pipeline config — encodes source+layout combination in PIP mode |
| `0xE1` | OSD guard — reads `0xFA` when Menu1 OSD is open; use to abort contaminated scans |

**Persistently noisy registers — exclude from all detection logic:**
`0x3C`, `0x3D`, `0x3E` (free-running counters) · `0xA0`, `0xA3`, `0xA5` (active-state noise) ·
`0x0B`, `0x0C`, `0x0D` (toggle ~2–4s, likely frame-sync counters) · `0x1F` (oscillates `0x00`↔`0xEE`)

---

## Monitor state matrix

**Legend:**
`?` = no scan file exists for this state · `⚠val` = value captured but reliability uncertain (OSD or mode contamination risk) · `act` = active-signal noise (toggles `0x21`/`0x22`) · VCP `0x60` marked `*` = inferred from monitor state, not read from that scan file (old format predated DDC reads)

All PIP captures: Wide style, audio right (`0x4A=0x02`). PIP window position has no effect on any register.

| Mode | State | VCP `0x60` | VCP `0xD6` | `0x48` | `0x4A` | `0xA1` | `0xE0` | `0xE1` | `0xE2` | `0xE3` |
|------|-------|-----------|-----------|--------|--------|--------|--------|--------|--------|--------|
| **Standby** | — | `?` | `0x04` | `?` | `?` | `?` | `?` | `?` | `?` | `?` |
| **Idle** | no signal | †last | `0x01` | `0x0F` | `0x02` | `0x00` | `0x00` | `0x00` | `0x00` | `0x00` |
| **Single** | HDMI | `0x01`* | `0x01` | `0x0F` | `0x02` | `0x22` | ⚠`0x40` | ⚠`0x83` | ⚠`0x01` | ⚠`0x20` |
| **Single** | DP | `0x03`* | `0x01` | `0x0F` | `0x02` | `0x21` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **Single** | TB | `0x04`* | `0x01` | `0x0F` | `0x02` | `0x21` | ⚠`0xF4` | ⚠`0x00` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | DP left / HDMI right — audio right | `0x03` | `0x01` | `0x0F` | `0x02` | `0x21` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | DP left / HDMI right — audio left | `0x03` | `0x01` | `?` | `?` | `?` | `?` | `?` | `?` | `?` |
| **PBP** | DP left / TB right — audio right | `0x03` | `0x01` | `0x00`† | `0x02` | `0x21` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | DP left / TB right — audio left | `0x03` | `0x01` | `?` | `?` | `?` | `?` | `?` | `?` | `?` |
| **PBP** | HDMI left / DP right — audio left | `0x01` | `0x01` | `0x0F` | `0x00` | `0x21` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | HDMI left / DP right — audio right | `0x01` | `0x01` | `0x0F` | `0x02` | `0x21` | ⚠`0x40` | ⚠`0x35` | ⚠`0x05` | ⚠`0x20` |
| **PBP** | HDMI left / TB right — audio right | `0x01` | `0x01` | `0x0F` | `0x02` | `0x21` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | HDMI left / TB right — audio left | `0x01` | `0x01` | `?` | `?` | `?` | `?` | `?` | `?` | `?` |
| **PBP** | TB left / DP right — audio right | `0x04` | `0x01` | `0x0F` | `0x02` | `0x22` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | TB left / DP right — audio left | `0x04` | `0x01` | `?` | `?` | `?` | `?` | `?` | `?` | `?` |
| **PBP** | TB left / HDMI right — audio right | `0x04` | `0x01` | `0x0F` | `0x02` | `0x21` | ⚠`0x80` | ⚠`0xE2` | ⚠`0x00` | ⚠`0x00` |
| **PBP** | TB left / HDMI right — audio left | `0x04` | `0x01` | `?` | `?` | `?` | `?` | `?` | `?` | `?` |
| **PIP** | main: DP / pip: TB / size 1 | `0x03` | `0x01` | `0x0F` | `0x02` | act | `0x80` | `0xE2` | `0x00` | `0x00` |
| **PIP** | main: DP / pip: TB / size 2 | `0x03` | `0x01` | `0x0F` | `0x02` | act | `0x40` | `0x8C` | `0x01` | `0x2E` |
| **PIP** | main: DP / pip: TB / size 3 | `0x03` | `0x01` | `0x0F` | `0x02` | act | `0x40` | `0x8C` | `0x01` | `0x2E` |
| **PIP** | main: DP / pip: HDMI / size 1 | `0x03` | `0x01` | `0x0F` | `0x02` | act | `0x40` | `0x4E` | `0x00` | `0x00` |
| **PIP** | main: DP / pip: HDMI / size 2 | `0x03` | `0x01` | `0x0F` | `0x02` | act | `0x40` | `0x8C` | `0x01` | `0x2E` |
| **PIP** | main: DP / pip: HDMI / size 3 | `0x03` | `0x01` | `0x0F` | `0x02` | act | `0x80` | `0xE2` | `0x00` | `0x00` |
| **PIP** | main: TB / pip: HDMI / size 1 | `0x04` | `0x01` | `0x0F` | `0x02` | act | `0x40` | `0x35` | `0x05` | `0x20` |
| **PIP** | main: TB / pip: HDMI / size 3 | `0x04` | `0x01` | `0x0F` | `0x02` | act | `0x40` | `0x35` | `0x05` | `0x20` |
| **PIP** | main: HDMI / pip: TB / size 3 | `0x01` | `0x01` | `0x0F` | `0x02` | act | `0x80` | `0xE2` | `0x00` | `0x00` |

† `0x48=0x00` observed in scan `pbp-dp-tb-sound-right` only. All other PBP scans show `0x48=0x0F`. Meaning of `0x48` is unresolved — retake scheduled.

† In idle, VCP `0x60` retains the last-used source and `0x4A` retains last audio state — neither resets to a sentinel value.

`*` VCP `0x60` not read from that scan file (old format predated DDC reads). Value inferred from monitor state at time of capture.

Single-source and PBP E0–E3 are marked ⚠ — those captures predate the clean-capture protocol or had OSD/input-change notifications on screen. Values are what the scan recorded, not verified clean reads.

---

## Detection rules

Given a set of clean register reads (`0x02=0x79`, `0xE1≠0xFA`, 25s elapsed after any OSD interaction):

| Question | How to answer |
|----------|---------------|
| Is the monitor in standby? | VCP `0xD6 = 0x04` |
| Is there an active signal? | `0xA1 ≠ 0x00` |
| Which source is primary? | VCP `0x60` — `0x01`=HDMI, `0x03`=DP, `0x04`=TB |
| Which side has audio? | `0x4A` — `0x00`=left/primary, `0x02`=right/secondary |
| Is PIP mode active? | `0xE0`–`0xE3` match a known PIP fingerprint (see table above) |
| Is PIP sub-source identifiable? | Only when main=DP and size=1 and `0xE1=0x4E` (HDMI pip) |
| Is PIP size identifiable? | Only size 2 (DP main, `0xE1=0x8C`); sizes 2 and 3 collide |
| Can I detect PIP state with TB main? | No — E0–E3 identical for all sizes and PIP sources |
| Is PBP mode active? | `0x48` — unresolved, retake pending |

---

## Data gaps — retakes scheduled 2026-05-03

- `0x48` meaning: need clean per-mode reads to determine what it encodes
- Single-source E0–E3: need clean re-captures (early scans have contamination risk)
- PBP audio-left states: only one audio-left PBP capture exists (HDMI left / DP right)
- PBP E0–E3: all captures have OSD/input-change contamination — full re-capture needed
- PIP audio-independence: confirm E0–E3 unchanged when `0x4A=0x00` (no audio-left PIP captures yet)
- Missing PIP sizes: TB main size 2; HDMI main sizes 1 and 2
