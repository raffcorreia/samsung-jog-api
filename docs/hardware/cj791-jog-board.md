# CJ791 JOG Board Notes

## Scope

This document records the current hardware observations for the Samsung `LC34J791WTNXZA / CJ791` front-panel `JOG` control path.

## Monitor information

Target monitor:

- model: `Samsung LC34J791WTNXZA`
- marketing name: `Samsung CJ791`
- panel size: `34-inch ultrawide curved`
- resolution: `3440x1440`
- inputs: `HDMI`, `DisplayPort`, `Thunderbolt 3 / USB-C`
- features: `Picture-in-Picture`, `Picture-by-Picture`, built-in OSD, rear-mounted `JOG` control

## JOG hardware

Samsung refers to the rear control as the `JOG` button. On this monitor the rear control board appears to behave like a passive input board connected back to the main board.

The relevant connector is documented as `CN1001` on the monitor main board with this pinout:

- pin 1: `GND`
- pin 2: `KEY_ADC2`
- pin 3: `KEY_ADC1`
- pin 4: `KEY_LED`
- pin 5: `NC`

This matters because it suggests the `JOG` is not a bank of ordinary digital switch lines. The monitor appears to read button activity through analog key-sense lines.

The `KEY_LED` line is also important. It is not just a cosmetic output if it can be observed reliably by the controller, because front-panel `LED` behavior may provide useful confirmation cues during input changes, idle states, and some OSD workflows.

## Current electrical model

Current working model:

- `KEY_ADC1` and `KEY_ADC2` idle high at about `3.3V` relative to `GND`
- button actions are represented by distinct resistance-to-ground values on those lines
- `KEY_ADC2` carries the four directional actions
- `KEY_ADC1` carries center or enter
- `KEY_LED` is a separate observable signal and should be treated as input-only in the external controller

This is why an inline electrical emulator is attractive. The system does not necessarily need to reverse engineer every internal software path if it can present the same electrical behavior the original `JOG` board presents.

## Idle bus state

Measured idle voltage relative to `GND`:

| Line | Idle voltage |
| --- | --- |
| `KEY_ADC1` | `3.3V` |
| `KEY_ADC2` | `3.3V` |

Interpretation:

- both key lines appear to be pulled high in idle state
- actions are then likely detected by the monitor as changes toward ground through known resistor values

## Measured input behavior

These measurements were taken with the joystick board disconnected and resistance measured to ground.

### `KEY_ADC2` directional channel

| State | Measurement |
| --- | --- |
| `Idle` | `3.3V` to `GND` |
| `Down` | `3.3 kOhm` to `GND` |
| `Right` | `9 kOhm` to `GND` |
| `Up` | `22.6 kOhm` to `GND` |
| `Left` | `32.8 kOhm` to `GND` |

### `KEY_ADC1` center channel

| State | Measurement |
| --- | --- |
| `Idle` | `3.3V` to `GND` |
| `Center` | `23 kOhm` to `GND` |

## Interpretation

Current interpretation:

- `KEY_ADC2` is a resistor ladder for the four directional actions
- `KEY_ADC1` is a separate analog sense line for center or enter
- the monitor likely decodes button presses by reading analog thresholds on those ADC inputs
- the front `LED` may provide observable feedback that can be sampled as part of control confirmation

## External controller responsibilities

The external controller board is expected to handle at least these responsibilities:

- observe `KEY_ADC1`
- observe `KEY_ADC2`
- observe `KEY_LED`
- drive `KEY_ADC1` with the required analog behavior
- drive `KEY_ADC2` with the required analog behavior
- preserve use of the original physical `JOG`

The design should explicitly separate:

- observe bus responsibilities
- drive bus responsibilities

even if those paths eventually share board-level circuitry.

## Measurement notes

To keep future measurements comparable, record:

- date
- monitor model and any visible board revision
- meter model
- whether the `JOG` board is connected or disconnected
- probe placement

Recommended measurement sequence:

1. Identify connector `CN1001` and confirm pin orientation.
2. Confirm `GND`, `KEY_ADC1`, `KEY_ADC2`, and `KEY_LED`.
3. Measure idle voltage to ground for `KEY_ADC1` and `KEY_ADC2`.
4. Measure resistance to ground while actuating each directional `JOG` action.
5. Measure resistance to ground while pressing center.
6. Repeat measurements at least once to check consistency.
7. Record any unstable or ambiguous values.

Suggested key-line evidence table:

| Line | State | Measurement type | Value | Notes |
| --- | --- | --- | --- | --- |
| `KEY_ADC2` | `Idle` | voltage | | |
| `KEY_ADC2` | `Down` | resistance | | |
| `KEY_ADC2` | `Right` | resistance | | |
| `KEY_ADC2` | `Up` | resistance | | |
| `KEY_ADC2` | `Left` | resistance | | |
| `KEY_ADC1` | `Idle` | voltage | | |
| `KEY_ADC1` | `Center` | resistance | | |

Suggested `LED` evidence table:

| Scenario | LED state or pattern | Timing | Notes |
| --- | --- | --- | --- |
| idle | | | |
| input switch start | | | |
| input switch complete | | | |
| menu open | | | |
| scroll limit reached | | | |

## Known gaps

- tolerance ranges for each button value are not yet known
- the electrical characteristics and exact semantics of `KEY_LED` still need confirmation
- contention behavior between the original board and an inline controller is not yet fully characterized
- acceptable tolerance around each resistor value is not yet documented

## Suggested follow-up

- repeat all voltage and resistance measurements and record date, tool, and conditions
- capture photos of connector orientation and wiring colors
- record whether measurements differ while the board is connected versus isolated
- record `LED` behavior during input changes, idle state, and menu navigation
- test whether button recognition is tolerant to nearby resistor substitutions
