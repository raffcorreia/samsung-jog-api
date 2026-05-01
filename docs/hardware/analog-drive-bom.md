# Phase 4 Analog Drive BOM

## Purpose

This BOM defines the selected component direction and default passive values for `Phase 4: Analog Drive Circuit Design`.

It covers only the analog drive subcircuit for reproducing `JOG` resistance states on `KEY_ADC1` and `KEY_ADC2`.


## BOM Artifact

A JLC-oriented CSV BOM is tracked at:

- [`hardware/kicad/analog-drive/analog-drive.bom.csv`](../../hardware/kicad/analog-drive/analog-drive.bom.csv)

This markdown BOM is the review-friendly version; the CSV is the fabrication-oriented artifact used for PCB ordering and assembly preparation.

## Selected Core Parts

| RefDes | Qty | Part | Package | Purpose | JLCPCB / LCSC | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `U1` | 1 | `MC74HC4066ADTR2G` | `TSSOP-14` | `KEY_ADC2` per-leg analog switch bank | `C233537` | JLC-orderable prototype choice; higher on-resistance than the original LV4066A target, but retained to keep the board fully orderable |
| `U2` | 1 | `74LVC1G66LT05ARCQ` | `SOT-23-5` | `KEY_ADC1` center pull-down gating | `C46553572` | JLC-orderable single analog switch for the center path |

## Default Passive Values

| RefDes | Qty | Value | JLCPCB / LCSC | Notes |
| --- | --- | --- | --- | --- |
| `R1` | 1 | `30 kOhm` | `C2889371` | `KEY_ADC2_LEFT` tested commercial value; exact JLC match is currently low stock, so verify before ordering |
| `R2` | 1 | `10 kOhm` | `C5362358` | `KEY_ADC2_RIGHT` tested commercial value |
| `R3` | 1 | `3.3 kOhm` | `C3017726` | `KEY_ADC2_DOWN` tested commercial value |
| `R4` | 1 | `22 Ohm` | — | `KEY_ADC2_UP` tested commercial value; LCSC part number to be confirmed for 22 Ohm 0402 |
| `R6` | 1 | `22 Ohm` | — | `KEY_ADC1_CENTER` tested commercial value; LCSC part number to be confirmed for 22 Ohm 0402 |
| `R7-R11` | 5 | `100 kOhm`, `1%` | `C25803` | default-off bias for all five control nets |
| `C1-C2` | 2 | `100 nF`, `X7R` | `C14663` | local decoupling at `U1` and `U2` |
| `C3` | 1 | `1 uF`, `X5R/X7R` | `C15849` | local bulk decoupling on `3.3V` |

## Interface And Assembly Notes

| RefDes | Qty | Part / Type | Purpose |
| --- | --- | --- | --- |
| `J1` | 1 | `1x3` monitor-drive header | `KEY_ADC1`, `KEY_ADC2`, `GND` to the monitor-side harness; through-hole, manual assembly |
| `J2` | 1 | `1x7` host-control header | `CENTER_EN`, `UP_EN`, `DOWN_EN`, `RIGHT_EN`, `LEFT_EN`, `GND`, `3.3V`; through-hole, manual assembly |

## PCB Outcome

- the phase-4 KiCad PCB is now a routed compact prototype board in [`hardware/kicad/analog-drive/analog-drive.kicad_pcb`](../../hardware/kicad/analog-drive/analog-drive.kicad_pcb)
- KiCad successfully exports front-side placement CSV, gerbers, and 3D board renders from the board file
- standard KiCad 3D models are now attached to the board footprints for connectors, ICs, passives, and capacitors
- `kicad-cli pcb drc` still crashes in this environment with a KiCad `10.0.0` macOS CLI runtime error, so final clearance review still needs an interactive KiCad GUI pass before ordering

## Channel Allocation

### `MC74HC4066ADTR2G` (`U1`)

- four independent channels connect `KEY_ADC2` to four dedicated resistor legs toward `GND`
- each directional resistor leg has its own enable input
- all channels remain isolated unless their specific enable line is asserted

### `74LVC1G66LT05ARCQ` (`U2`)

- toggles `KEY_ADC1` center resistor leg to `GND`
- defaults to open/high-impedance when not enabled

## Current Design Intent

- controller never sources voltage onto monitor lines
- controller only switches resistance-to-ground states
- default inactive state is high-impedance on both driven channels
- each switch enable line has a hardware default-off bias resistor
- software still enforces one action at a time, but the hardware default state is already safe before firmware starts

## Remaining Risks

- `U1` is now JLC-orderable, but it is a `74HC4066`-class part rather than the original lower-on-resistance `LV4066A` target, so final bench confirmation on the assembled board is still required
- the selected `30 kOhm` JLC resistor is currently a low-stock listing; if it disappears, swap to a validated stocked alternative before release
- final connector family and keyed harness choice still belongs to the integrated-board phase
- final PCB sign-off is still pending a successful GUI DRC pass because the CLI DRC path is currently unreliable in this environment
