# Phase 4 Analog Drive BOM

## Purpose

This BOM defines the selected component direction and default passive values for `Phase 4: Analog Drive Circuit Design`.

It covers only the analog drive subcircuit for reproducing `JOG` resistance states on `KEY_ADC1` and `KEY_ADC2`.


## KiCad-Generated BOM Artifact

A KiCad-10 CSV BOM is tracked at:

- [`hardware/kicad/phase-4-analog-drive/phase-4-analog-drive.bom.csv`](../../hardware/kicad/phase-4-analog-drive/phase-4-analog-drive.bom.csv)

This markdown BOM is the review-friendly version; the CSV is the KiCad export artifact used for PCB-oriented workflows.

## Selected Core Parts

| RefDes | Qty | Part | Package | Purpose | Notes |
| --- | --- | --- | --- | --- | --- |
| `U1` | 1 | `SN74LV4066APWR` | `TSSOP-14` | `KEY_ADC2` per-leg analog switch bank | 4 independent bilateral switch channels for `LEFT`, `RIGHT`, `DOWN`, `UP` |
| `U2` | 1 | `SN74LVC1G66DBVR` | `SOT-23-5` | `KEY_ADC1` center pull-down gating | single bilateral analog switch for the center resistor leg |

## Default Passive Values

| RefDes | Qty | Value | Notes |
| --- | --- | --- | --- |
| `R1` | 1 | `30 kOhm` | `KEY_ADC2_LEFT` validated commercial substitute for `32.8 kOhm` measured target |
| `R2` | 1 | `10 kOhm` | `KEY_ADC2_RIGHT` validated commercial substitute for `9 kOhm` measured target |
| `R3` | 1 | `3.3 kOhm` | `KEY_ADC2_DOWN` measured target leg |
| `R4` | 1 | `22 kOhm` | `KEY_ADC2_UP` validated commercial substitute for `22.8 kOhm` measured target |
| `R5` | 1 | `DNP`, `1%` | optional `KEY_ADC2` calibration leg reserved for later tuning |
| `R6` | 1 | `22 kOhm` | `KEY_ADC1_CENTER` validated commercial substitute for `22.71 kOhm` measured target |
| `R7` | 1 | `100 kOhm`, `1%` | `ADC2_LEFT_EN` default-off bias |
| `R8` | 1 | `100 kOhm`, `1%` | `ADC2_RIGHT_EN` default-off bias |
| `R9` | 1 | `100 kOhm`, `1%` | `ADC2_DOWN_EN` default-off bias |
| `R10` | 1 | `100 kOhm`, `1%` | `ADC2_UP_EN` default-off bias |
| `R11` | 1 | `100 kOhm`, `1%` | `ADC1_CENTER_EN` default-off bias |
| `C1` | 1 | `100 nF`, `X7R` | local decoupling at `U1` |
| `C2` | 1 | `100 nF`, `X7R` | local decoupling at `U2` |
| `C3` | 1 | `1 uF`, `X7R` | local bulk decoupling on `3.3V` |
| `C4` | 1 | `1 nF`, `DNP` | optional edge-shaping footprint if switching transients require damping |

## Interface Placeholders

| RefDes | Qty | Part / Type | Purpose |
| --- | --- | --- | --- |
| `J1` | 1 | `1x3` monitor-drive header | `GND`, `KEY_ADC2`, `KEY_ADC1` to monitor-side harness |
| `J2` | 1 | `1x7` host-control header | `3.3V`, `GND`, `ADC2_LEFT_EN`, `ADC2_RIGHT_EN`, `ADC2_DOWN_EN`, `ADC2_UP_EN`, `ADC1_CENTER_EN` |
| `TP1-TP7` | 7 | test points | `KEY_ADC2_DRIVE`, `KEY_ADC1_DRIVE`, `LEFT_EN`, `RIGHT_EN`, `DOWN_EN`, `UP_EN`, `CENTER_EN` |

## Channel Allocation

### `SN74LV4066APWR` (`U1`)

- four independent channels connect `KEY_ADC2` to four dedicated resistor legs toward `GND`
- each directional resistor leg has its own enable input
- all channels remain isolated unless their specific enable line is asserted

### `SN74LVC1G66DBVR` (`U2`)

- toggles `KEY_ADC1` center resistor leg to `GND`
- defaults to open/high-impedance when not enabled

## Current Design Intent

- controller never sources voltage onto monitor lines
- controller only switches resistance-to-ground states
- default inactive state is high-impedance on both driven channels
- each switch enable line has a hardware default-off bias resistor
- software still enforces one action at a time, but the hardware default state is already safe before firmware starts

## Open Items For Later Phases

- final production resistor selection after first switched prototype confirms tolerance against the measured target values
- confirmation whether additional series protection is needed for ESD robustness
- final connector family and keyed harness selection
