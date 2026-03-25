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
- basic `KEY_LED` electrical readability
- confirmation that the original physical `JOG` can remain preserved

## Required Evidence

### Photos

- connector `CN1001` in context
- connector orientation close-up
- wiring colors or harness orientation
- `JOG` board and cable routing

Selected reference photos already copied into the repo:

- main board context: [cj791-mainboard-full.jpg](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/assets/hardware/cj791-mainboard-full.jpg)
- pushbutton and connector close-up: [cj791-pushbutton-close.jpg](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/assets/hardware/cj791-pushbutton-close.jpg)
- joystick board connection: [cj791-joystick-board-connection.jpg](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/assets/hardware/cj791-joystick-board-connection.jpg)
- joystick board rear view: [cj791-joystick-back.jpg](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/assets/hardware/cj791-joystick-back.jpg)

<p align="center">
  <img src="../assets/hardware/cj791-mainboard-full.jpg" alt="CJ791 main board full view" width="48%" />
  <img src="../assets/hardware/cj791-pushbutton-close.jpg" alt="CJ791 pushbutton and connector close view" width="48%" />
</p>

<p align="center">
  <img src="../assets/hardware/cj791-joystick-board-connection.jpg" alt="CJ791 joystick board connection" width="48%" />
  <img src="../assets/hardware/cj791-joystick-back.jpg" alt="CJ791 joystick board rear side" width="48%" />
</p>

### Meter metadata

- measurement date
- meter model
- whether the board was connected or disconnected
- probe placement notes

Current recorded metadata for this evidence set:

- measurement date: `03/24/2026`
- meter model: `EEVBlog 121GW`
- board state during the voltage and LED measurements: connected, powered, and functional
- ambiguity or instability observed: none

### Key-line evidence table

| Line | State | Measurement type | Value | Board connected? | Notes |
| --- | --- | --- | --- | --- | --- |
| `KEY_ADC2` | `Idle` | voltage to `GND` | `3.29V` | yes | latest powered measurement set |
| `KEY_ADC2` | `Down` | voltage to `GND` | `1.35V` | yes | latest powered measurement set |
| `KEY_ADC2` | `Down` | resistance to `GND` | `3.3 kOhm` | yes | latest powered measurement set |
| `KEY_ADC2` | `Right` | voltage to `GND` | `2.16V` | yes | latest powered measurement set |
| `KEY_ADC2` | `Right` | resistance to `GND` | `9 kOhm` | yes | latest powered measurement set |
| `KEY_ADC2` | `Up` | voltage to `GND` | `0.01V` | yes | latest powered measurement set |
| `KEY_ADC2` | `Up` | resistance to `GND` | `22.8 Ohm` | yes | latest powered measurement set |
| `KEY_ADC2` | `Left` | voltage to `GND` | `2.88V` | yes | latest powered measurement set |
| `KEY_ADC2` | `Left` | resistance to `GND` | `32.8 kOhm` | yes | latest powered measurement set |
| `KEY_ADC1` | `Idle` | voltage to `GND` | `3.29V` | yes | latest powered measurement set |
| `KEY_ADC1` | `Center` | voltage to `GND` | `0.01V` | yes | latest powered measurement set |
| `KEY_ADC1` | `Center` | resistance to `GND` | `22.71 Ohm` | yes | latest powered measurement set |

### `KEY_LED` basic evidence table

| State | Measurement type | Value | Measurement method | Notes |
| --- | --- | --- | --- | --- |
| idle | voltage or logical level | | | |
| active | voltage or logical level | | | |

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
9. confirm whether `KEY_LED` can be read as a usable controller input and note its basic on or off behavior
10. note any contradiction, tolerance issue, or instability

## Open Questions

- do the measured resistor values vary materially when the board remains connected?
- can `KEY_LED` be read safely as a simple controller input without disturbing monitor behavior?
- are the documented resistor values exact enough for hardware design, or should acceptable ranges be defined now?
- is any mechanical or electrical change needed to preserve the original `JOG` inline?

## Current Status

Phase 2 has started.

Current confirmed evidence:

- the photo set in this repo is considered sufficient to treat `CN1001` orientation and connector context as visually unambiguous
- `KEY_ADC1` idle voltage to `GND`: initially `3.3V`, latest powered set `3.29V`
- `KEY_ADC2` idle voltage to `GND`: initially `3.3V`, latest powered set `3.29V`
- `KEY_LED` idle voltage: `0V`
- `KEY_LED` active voltage with LED connected: `2.7V`
- `KEY_LED` active voltage with LED disconnected: `2.9V`
- the monitor is currently configured for `LED off when monitor is on` and `LED on when monitor is off`
- the LED is also observed to blink while the monitor is idle, but the blink frequency is intentionally deferred to the later LED characterization phase

Still pending in Phase 2:

- capture of measurement metadata such as meter model and exact measurement date if you want the record to be more formal

## Captured Evidence

### Connector and orientation

- `CN1001` connector access is available on the target unit
- the copied photo set is considered visually unambiguous enough to support connector and orientation confirmation
- the documented pin order was visually reconfirmed personally and is supported by the photo set

### Idle and basic LED measurements

| Line | State | Measurement type | Value | Board connected? | Notes |
| --- | --- | --- | --- | --- | --- |
| `KEY_ADC2` | `Idle` | voltage to `GND` | `3.3V` | yes | confirmed during Phase 2 |
| `KEY_ADC1` | `Idle` | voltage to `GND` | `3.3V` | yes | confirmed during Phase 2 |
| `KEY_LED` | `Idle` | voltage to `GND` | `0V` | yes | confirmed during Phase 2 |
| `KEY_LED` | `Active` | voltage to `GND` | `2.7V` | yes | LED connected |
| `KEY_LED` | `Active` | voltage to `GND` | `2.9V` | no | LED disconnected |

### Latest powered key-state measurements

This later powered and connected measurement set adds the observed bus voltages for each active state:

| Line | State | Voltage to `GND` | Resistance to `GND` | Board connected? | Notes |
| --- | --- | --- | --- | --- | --- |
| `KEY_ADC2` | `Idle` | `3.29V` | | yes | latest powered set |
| `KEY_ADC2` | `Left` | `2.88V` | `32.8 kOhm` | yes | latest powered set |
| `KEY_ADC2` | `Right` | `2.16V` | `9 kOhm` | yes | latest powered set |
| `KEY_ADC2` | `Up` | `0.01V` | `22.8 Ohm` | yes | latest powered set |
| `KEY_ADC2` | `Down` | `1.35V` | `3.3 kOhm` | yes | latest powered set |
| `KEY_ADC1` | `Idle` | `3.29V` | | yes | latest powered set |
| `KEY_ADC1` | `Center` | `0.01V` | `22.71 Ohm` | yes | latest powered set |

Measurement metadata for this set:

- date: `03/24/2026`
- meter: `EEVBlog 121GW`
- board state: connected, powered, and functional
- ambiguity or instability: none observed

### Board-connected versus board-disconnected comparison

- `KEY_ADC1` and `KEY_ADC2` do not change when the `JOG` board is connected or disconnected
- this was observed with the `JOG` side and either side of the cable disconnected

### Current monitor LED configuration

- configured behavior: `LED off when monitor is on`
- alternate monitor option exists: keep the LED on while the monitor is on
- observed additional behavior: the LED blinks while the monitor is idle

The exact blink frequency is intentionally not treated as a Phase 2 deliverable. That timing work belongs to the later dedicated LED characterization phase, where recording and replay can correlate LED transitions with repeated monitor actions.

### Reconfirmed resistance values

The previously documented resistance values were explicitly reconfirmed and remain the current working values:

| Line | State | Measurement type | Value | Board connected? | Notes |
| --- | --- | --- | --- | --- | --- |
| `KEY_ADC2` | `Down` | resistance to `GND` | `3.3 kOhm` | no | reconfirmed |
| `KEY_ADC2` | `Right` | resistance to `GND` | `9 kOhm` | no | reconfirmed |
| `KEY_ADC2` | `Up` | resistance to `GND` | `22.6 kOhm` | no | reconfirmed |
| `KEY_ADC2` | `Left` | resistance to `GND` | `32.8 kOhm` | no | reconfirmed |
| `KEY_ADC1` | `Center` | resistance to `GND` | `23 kOhm` | no | reconfirmed |

These earlier disconnected measurements now coexist with the later powered-and-connected voltage set above. Both are preserved because the powered measurements are directly useful for the observation-circuit thresholds, while the disconnected values remain relevant to understanding the passive `JOG` behavior.

## Exit Decision

Phase 2 can be considered complete when:

- the `CN1001` pinout is confirmed on the actual unit
- the documented `KEY_ADC1` and `KEY_ADC2` values are revalidated or corrected
- `KEY_LED` basic electrical readability is documented well enough to inform controller design
- the hardware notes are updated with any corrections

Current assessment:

- all currently planned Phase 2 validation items have been covered well enough to proceed
