# Phase 2 Execution Record

## Purpose

This document records the actual execution of `Phase 2: Hardware Validation` on the target Samsung `CJ791` monitor.

It complements:

- [Implementation Plan](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/implementation/plan.md)
- [CJ791 JOG Board Notes](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/hardware/cj791-jog-board.md)

## Target Hardware

- monitor model: `Samsung LC34J791WTNXZA / CJ791`
- relevant connector: `CN1001`
- relevant lines:
  - `GND`
  - `KEY_ADC2`
  - `KEY_ADC1`
  - `KEY_LED`

## Goal

Confirm that the currently documented electrical model still matches the actual target hardware before controller-circuit design begins.

## Validation Scope

- `CN1001` pinout confirmation
- `KEY_ADC1` idle and center measurement
- `KEY_ADC2` idle and directional measurements
- `KEY_LED` viability as a feedback source
- confirmation that the original physical `JOG` can remain preserved

## Required Evidence

### Photos

- connector `CN1001` in context
- connector orientation close-up
- wiring colors or harness orientation
- `JOG` board and cable routing

### Meter metadata

- measurement date
- meter model
- whether the board was connected or disconnected
- probe placement notes

### Key-line evidence table

| Line | State | Measurement type | Value | Board connected? | Notes |
| --- | --- | --- | --- | --- | --- |
| `KEY_ADC2` | `Idle` | voltage to `GND` | | | |
| `KEY_ADC2` | `Down` | resistance to `GND` | | | |
| `KEY_ADC2` | `Right` | resistance to `GND` | | | |
| `KEY_ADC2` | `Up` | resistance to `GND` | | | |
| `KEY_ADC2` | `Left` | resistance to `GND` | | | |
| `KEY_ADC1` | `Idle` | voltage to `GND` | | | |
| `KEY_ADC1` | `Center` | resistance to `GND` | | | |

### `KEY_LED` evidence table

| Scenario | LED state or pattern | Timing | Measurement method | Notes |
| --- | --- | --- | --- | --- |
| idle | | | | |
| menu open | | | | |
| input switch start | | | | |
| input switch complete | | | | |
| scroll limit reached | | | | |

## Expected Reference Values

Current documented reference values from the existing hardware notes:

### `KEY_ADC2`

- idle: `3.3V` to `GND`
- `Down`: `3.3 kOhm` to `GND`
- `Right`: `9 kOhm` to `GND`
- `Up`: `22.6 kOhm` to `GND`
- `Left`: `32.8 kOhm` to `GND`

### `KEY_ADC1`

- idle: `3.3V` to `GND`
- `Center`: `23 kOhm` to `GND`

These values are not assumed correct for controller design until revalidated here.

## Execution Checklist

1. confirm the monitor identity and access to `CN1001`
2. photograph the connector and harness orientation
3. confirm pin order on the actual unit
4. measure idle voltage on `KEY_ADC1` and `KEY_ADC2`
5. measure directional resistance values on `KEY_ADC2`
6. measure center resistance value on `KEY_ADC1`
7. repeat key measurements at least once
8. check whether results differ with the board connected versus disconnected
9. characterize `KEY_LED` enough to decide whether it is usable as a controller feedback input
10. note any contradiction, tolerance issue, or instability

## Open Questions

- do the measured resistor values vary materially when the board remains connected?
- how stable is `KEY_LED` under a meter or scope probe?
- are the documented resistor values exact enough for hardware design, or should acceptable ranges be defined now?
- is any mechanical or electrical change needed to preserve the original `JOG` inline?

## Current Status

Phase 2 has started.

No new measurement data has been captured in this execution record yet.

## Exit Decision

Phase 2 can be considered complete when:

- the `CN1001` pinout is confirmed on the actual unit
- the documented `KEY_ADC1` and `KEY_ADC2` values are revalidated or corrected
- `KEY_LED` viability is documented well enough to inform controller design
- the hardware notes are updated with any corrections
