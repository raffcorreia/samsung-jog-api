# Phase 24 — Register Capture Plan

Ordered to minimize input changes between consecutive captures.
Within each primary-input group, transitioning Single → PIP → PBP reuses the
same main input; PIP sub-source and PBP partner change, never the primary.

Sizes for PIP: 1 = Small, 2 = Medium, 3 = Large.  
PBP audio variants: Left = left panel active, Right = right panel active (set via OSD).

---

## Baseline

| # | State | Notes |
|---|-------|-------|
| 1 | Standby | Monitor off (power button held) |
| 2 | Idle — no active signal | All sources disconnected / no sync |

---

## Group A — Primary: Thunderbolt

| # | Mode | Main / Primary | Sub / Partner | PIP Size / PBP Audio |
|---|------|---------------|---------------|----------------------|
| 3 | Single | TB | — | — |
| 4 | PIP | TB (main) | HDMI | Small |
| 5 | PIP | TB (main) | HDMI | Medium |
| 6 | PIP | TB (main) | HDMI | Large |
| 7 | PIP | TB (main) | DP | Large |
| 8 | PIP | TB (main) | DP | Medium |
| 9 | PIP | TB (main) | DP | Small |
| 10 | PBP | TB (left) | DP (right) | Audio: Left |
| 11 | PBP | TB (left) | DP (right) | Audio: Right |
| 12 | PBP | TB (left) | HDMI (right) | Audio: Left |
| 13 | PBP | TB (left) | HDMI (right) | Audio: Right |

---

## Group B — Primary: HDMI

| # | Mode | Main / Primary | Sub / Partner | PIP Size / PBP Audio |
|---|------|---------------|---------------|----------------------|
| 14 | Single | HDMI | — | — |
| 15 | PIP | HDMI (main) | TB | Small |
| 16 | PIP | HDMI (main) | TB | Medium |
| 17 | PIP | HDMI (main) | TB | Large |
| 18 | PIP | HDMI (main) | DP | Large |
| 19 | PIP | HDMI (main) | DP | Medium |
| 20 | PIP | HDMI (main) | DP | Small |
| 21 | PBP | HDMI (left) | DP (right) | Audio: Right |
| 22 | PBP | HDMI (left) | DP (right) | Audio: Left |
| 23 | PBP | HDMI (left) | TB (right) | Audio: Right |
| 24 | PBP | HDMI (left) | TB (right) | Audio: Left |

---

## Group C — Primary: DisplayPort

| # | Mode | Main / Primary | Sub / Partner | PIP Size / PBP Audio |
|---|------|---------------|---------------|----------------------|
| 25 | Single | DP | — | — |
| 26 | PIP | DP (main) | TB | Small |
| 27 | PIP | DP (main) | TB | Medium |
| 28 | PIP | DP (main) | TB | Large |
| 29 | PIP | DP (main) | HDMI | Large |
| 30 | PIP | DP (main) | HDMI | Medium |
| 31 | PIP | DP (main) | HDMI | Small |
| 32 | PBP | DP (left) | HDMI (right) | Audio: Right |
| 33 | PBP | DP (left) | HDMI (right) | Audio: Left |
| 34 | PBP | DP (left) | TB (right) | Audio: Right |
| 35 | PBP | DP (left) | TB (right) | Audio: Left |

---

## Summary

| Group | Test Cases | Primary Input |
|-------|-----------|---------------|
| Baseline | 1–2 | — |
| A | 3–13 | Thunderbolt |
| B | 14–24 | HDMI |
| C | 25–35 | DisplayPort |
| **Total** | **35** | |

## Transition Rationale

- **Single → PIP**: enabling PIP promotes single input to main, sub input added — no primary change.
- **PIP sub swap (HDMI ↔ DP)**: swap sub-source only, keep current size — then step down Large→Medium→Small to minimise size changes.
- **PIP → PBP**: PBP sub-source order starts with the same partner as the last PIP sub, so the mode switch requires no input change.
- **PBP audio flip (L → R)**: single OSD press — neither input changes.
- **Group boundary (e.g. 13 → 14)**: only place where the primary input changes.
