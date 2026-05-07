# Phase 24 Register Analysis — Samsung C34J79x

71 register captures were taken across 35 distinct monitor states (single-source, PIP, and PBP layouts; all three inputs: Thunderbolt, HDMI, DisplayPort; all PIP sizes; both audio sides). Five register maps were scanned per capture: device 0x58 (Novatek scaler, full 256-register I2C map), device 0x54 (full 256-register I2C map), device 0x3A (full 256-register I2C map), device 0x50 (full 256-register I2C map), and DDC/CI 0x37 (all 256 VCP codes). Statistical comparison across all captures produced four confirmed findings, two tentative findings, three unresolved questions, and a set of registers confirmed too noisy to use.

---

## Confirmed Findings

### DDC 0x37 — VCP 0x60 (Input Source)

Encodes the primary/main input in all modes (single, PIP, PBP). Consistent with the DDC/CI standard VCP 0x60 specification.

| Value | Input |
|-------|-------|
| `0x01` | HDMI |
| `0x03` | DisplayPort |
| `0x04` | Thunderbolt |

---

### 0x58 Register 0xE0 (Activity / Layout Category)

| Value | Meaning |
|-------|---------|
| `0x00` | Standby or idle (no active signal in either case — indistinguishable) |
| `0x40` | Multi-source mode active (PIP or PBP — indistinguishable from this register alone) |
| `0x80` | Single source active; primary is HDMI or DP |
| `0xF4` | Single source active; primary is Thunderbolt |

**Caveat:** occasional `0x80` readings appeared in PIP captures and may be transitional noise.

---

### 0x54 Register 0x10

This was the **only register in device 0x54 that varied** across all captures.

| Value | Meaning |
|-------|---------|
| `0x01` | Single Thunderbolt mode |
| `0x03` | All other modes |

---

### DDC 0x37 — VCP 0xD6 (Power Mode)

| Value | Meaning |
|-------|---------|
| `0x01` | Monitor on (confirmed consistent) |

Standby was not scanned because the monitor must be responding to issue DDC commands. Coverage is therefore limited to the active-on state.

---

## Tentative Findings

### 0x58 Registers 0xE2 and 0xE3 (Possible PBP Indicator)

In all PBP captures: `0xE2 = 0x05`, `0xE3 = 0x20` (consistent).  
In all single-source captures: `0xE2 = 0x00`, `0xE3 = 0x00` (consistent).  
In PIP captures: mixed — both the PBP values and the single-source values appeared.

This pair may be a PBP mode flag, but PIP contamination prevents a definitive conclusion. **Needs targeted retesting.**

---

## Unresolved Questions

### Secondary Input (PIP sub-source / PBP right-panel source)

No register in device 0x58 or DDC cleanly and consistently encodes the secondary input. Registers `0x0C`, `0x0D`, and `0xDB` showed partial discrimination but with too much overlap and noise to be usable.  DDC has no standard VCP for sub-source on this monitor.

### PIP Window Size (1 / 2 / 3)

No single register cleanly encodes PIP size. Registers `0x0C`, `0xA0`, and `0xA3` showed partial patterns with overlapping value ranges across the three sizes.

### PBP / PIP Audio Side (Left / Right)

DDC VCP `0x4A` (annotated as "audio side selector") read `0x00` in all captures regardless of the audio side setting. No register in device 0x58 showed a clean left vs. right discrimination. The audio side may not be exposed in any scanned register, or may require a write-then-read sequence to observe.

---

## Noisy Registers — Do Not Use

The following registers change between consecutive reads of the same state. They are likely frame counters, internal timers, or live signal-quality metrics.

| Device | Registers |
|--------|-----------|
| 0x58 | `0x0B`, `0x0C`, `0x0D`, `0x3C`, `0x3D`, `0x3E`, `0xA0`, `0xA3`, `0xA5` |

---

## Data Quality Flag — TB-Disconnection Contamination

Captures #15–27 (Group B: HDMI primary) were taken with the Thunderbolt cable possibly physically disconnected. Any analysis involving TB as the secondary input in HDMI-primary states should be considered unreliable until retaken.

---

## Practical Decoding Algorithm (Current State of Knowledge)

| Step | Read | Condition | Conclusion |
|------|------|-----------|------------|
| 1 | DDC VCP `0x60` | — | Primary input: `0x01`=HDMI, `0x03`=DP, `0x04`=TB |
| 2 | `0x58[0xE0]` | `0x00` | Standby or idle — stop here |
| 2 | `0x58[0xE0]` | `0x80` or `0xF4` | Single-source mode; source = DDC `0x60` result |
| 2 | `0x58[0xE0]` | `0x40` | Multi-source (PIP or PBP); primary = DDC `0x60` result → continue |
| 3 | `0x58[0xE2]` and `0x58[0xE3]` | `0xE2=0x05` AND `0xE3=0x20` | **Tentatively PBP** |
| 3 | `0x58[0xE2]` and `0x58[0xE3]` | any other combination | **Tentatively PIP** |
| 4 | Secondary input | — | **UNKNOWN** |
| 5 | PIP size | — | **UNKNOWN** |
| 6 | Audio side | — | **UNKNOWN** |

---

## Next Steps

1. **Retake Group B TB-secondary captures** (#15–17, #23–24) with TB cable confirmed connected.
2. **Targeted DDC write test:** write `0x4A` via DDC and read back to confirm whether audio side is reflected in that register.
3. **Targeted PBP/PIP toggle test:** scan the register neighbourhood around `0xE2`/`0xE3` while switching PIP ↔ PBP to confirm that pair as a PBP flag.
4. **Secondary-input investigation:** may require examining write sequences via DDC or scanning a different I2C address range.
