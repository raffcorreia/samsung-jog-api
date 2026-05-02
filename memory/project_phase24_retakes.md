---
name: Phase 24 retakes — scheduled for 2026-05-03
description: Register reads to retake during next session to complete the Phase 24 investigation
type: project
---

Retakes agreed on 2026-05-02. Do these in one session in the order listed.

**Why:** Several captures are missing or unreliable; `0x48` meaning is unresolved; PBP E0-E3 are all contaminated.

**How to apply:** Run through this list top to bottom. Each capture needs clean protocol: `0x02=0x79` guard, `0xE1≠0xFA`, 25s elapsed after any OSD interaction.

## Priority 1 — resolve `0x48`

Goal: understand what `0x48` actually encodes. Capture each mode and note the value.

- Single-source DP — read `0x48`
- Single-source TB — read `0x48`
- Single-source HDMI — read `0x48`
- PBP: two combos, e.g. DP|HDMI and TB|HDMI — read `0x48`

Expected outcome: confirms whether `0x48=0x0F` is truly universal or has a mode-specific value anywhere.

## Priority 2 — single-source E0-E3 baseline

Early single-source scans are unreliable (monitor may have been in PIP mode). Need clean re-captures.

- Single-source HDMI — full register scan
- Single-source DP — full register scan
- Single-source TB — full register scan

Use a proper HDMI source (not Pi incompatible resolution) for HDMI if possible.

## Priority 3 — PBP E0-E3 (all 12 combos)

All 12 PBP captures (6 combos × 2 audio positions) had OSD/input-change notifications on screen.
Need clean re-captures using 25s wait protocol.

Combos:
- DP | HDMI — audio left, audio right
- DP | TB — audio left, audio right
- HDMI | DP — audio left, audio right
- HDMI | TB — audio left, audio right
- TB | DP — audio left, audio right
- TB | HDMI — audio left, audio right

## Priority 4 — PIP audio independence check

All existing PIP captures used audio right (`0x4A=0x02`). Capture at least one PIP state with audio left
to confirm E0-E3 are unaffected by audio routing.

- PIP: main DP / pip TB / size 1 — audio left

## Priority 5 — missing PIP sizes

- PIP: main TB / pip HDMI / size 2
- PIP: main HDMI / pip TB / size 1 and size 2
