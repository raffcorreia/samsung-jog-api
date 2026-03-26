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
| `U1` | 1 | `TMUX1108PWR` | `TSSOP-16` | `KEY_ADC2` switched resistor-state selection | 8:1 mux style analog switch for one-of-many resistor-leg selection |
| `U2` | 1 | `TS5A3159DBVR` | `SOT-23-6` | `KEY_ADC1` center pull-down gating | used to apply or release center-state resistor leg |
| `U3` | 1 | `SN74LVC1G04DBVR` | `SOT-23-5` | optional logic inversion / timing conditioning | populate only if firmware polarity/timing integration requires it |

## Default Passive Values

| RefDes | Qty | Value | Notes |
| --- | --- | --- | --- |
| `R1` | 1 | `10 kOhm`, `1%` | `KEY_ADC2_LEFT` target leg |
| `R2` | 1 | `22 kOhm`, `1%` | `KEY_ADC2_RIGHT` target leg |
| `R3` | 1 | `39 kOhm`, `1%` | `KEY_ADC2_DOWN` target leg |
| `R4` | 1 | `68 kOhm`, `1%` | `KEY_ADC2_UP` target leg |
| `R5` | 1 | `0 Ohm`, `1%` | optional direct pull-down test leg for calibration/debug |
| `R6` | 1 | `0 Ohm`, `1%` | `KEY_ADC1_CENTER` pull-down leg |
| `R7` | 1 | `100 kOhm`, `1%` | gate pulldown for fail-safe default-off behavior |
| `R8` | 1 | `100 kOhm`, `1%` | enable-line pulldown for fail-safe default-off behavior |
| `C1` | 1 | `100 nF`, `X7R` | local decoupling at `U1` |
| `C2` | 1 | `100 nF`, `X7R` | local decoupling at `U2` |
| `C3` | 1 | `1 uF`, `X7R` | local bulk decoupling on `3.3V` |
| `C4` | 1 | `1 nF`, `DNP` | optional edge-shaping footprint if switching transients require damping |

## Interface Placeholders

| RefDes | Qty | Part / Type | Purpose |
| --- | --- | --- | --- |
| `J1` | 1 | `1x3` monitor-drive header | `GND`, `KEY_ADC2`, `KEY_ADC1` to monitor-side harness |
| `J2` | 1 | `1x6` host-control header | `3.3V`, `GND`, `ADC2_SEL0`, `ADC2_SEL1`, `ADC2_EN`, `ADC1_CENTER_EN` |
| `TP1-TP6` | 6 | test points | `KEY_ADC2_DRIVE`, `KEY_ADC1_DRIVE`, `SEL0`, `SEL1`, `ADC2_EN`, `ADC1_EN` |

## Channel Allocation

### `TMUX1108PWR` (`U1`)

- common node tied to `KEY_ADC2`
- one selected channel at a time connects `KEY_ADC2` to a chosen resistor leg toward `GND`
- unselected channels remain isolated

### `TS5A3159DBVR` (`U2`)

- toggles `KEY_ADC1` center resistor leg to `GND`
- defaults to open/high-impedance when not enabled

## Current Design Intent

- controller never sources voltage onto monitor lines
- controller only switches resistance-to-ground states
- default inactive state is high-impedance on both driven channels
- drive arbitration and break-before-make behavior are enforced in software

## Open Items For Later Phases

- per-state resistor trim based on prototype voltage measurements
- confirmation whether additional series protection is needed for ESD robustness
- final connector family and keyed harness selection
