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
- features: `Picture-in-Picture`, `Picture-by-Picture`, built-in OSD, front `JOG` control

## JOG hardware

Samsung refers to the front control as the `JOG` button. On this monitor the front-panel board appears to behave like a passive input board connected back to the main board.

The relevant connector is documented as `CN1001` on the monitor main board with this pinout:

- pin 1: `GND`
- pin 2: `KEY_ADC2`
- pin 3: `KEY_ADC1`
- pin 4: `KED_LED`
- pin 5: `NC`

This matters because it suggests the `JOG` is not simply a bank of digital switches. The monitor appears to read button activity through analog key-sense lines.

The `KED_LED` line is also important. It is not just a cosmetic output if it can be observed reliably by the controller, because front-panel `LED` behavior may provide useful confirmation cues during input changes, idle states, and some OSD workflows.

## Resistor ladder behavior

Measured with the joystick board disconnected, the key channels present distinct resistance-to-ground values.

`KEY_ADC2` directional channel:

- `Down`: `3.3 kOhm`
- `Right`: `9 kOhm`
- `Up`: `22.6 kOhm`
- `Left`: `32.8 kOhm`

`KEY_ADC1` center channel:

- `Center`: `23 kOhm`

## Measurement notes

To keep future measurements comparable, record:

- date
- monitor model and any visible board revision
- meter model
- whether the `JOG` board is connected or disconnected
- probe placement

Recommended measurement sequence:

1. Identify connector `CN1001` and confirm pin orientation.
2. Confirm `GND`, `KEY_ADC1`, and `KEY_ADC2`.
3. Measure idle resistance to ground for `KEY_ADC1` and `KEY_ADC2`.
4. Measure resistance to ground while actuating each directional `JOG` action.
5. Measure resistance to ground while pressing center.
6. Repeat measurements at least once to check consistency.
7. Record any unstable or ambiguous values.

Suggested evidence table:

| Line | Action | Resistance | Notes |
| --- | --- | --- | --- |
| `KEY_ADC2` | `Down` | | |
| `KEY_ADC2` | `Right` | | |
| `KEY_ADC2` | `Up` | | |
| `KEY_ADC2` | `Left` | | |
| `KEY_ADC1` | `Center` | | |
| `KEY_ADC1` | `Idle` | | |
| `KEY_ADC2` | `Idle` | | |

Suggested `LED` evidence table:

| Scenario | LED state or pattern | Timing | Notes |
| --- | --- | --- | --- |
| idle | | | |
| input switch start | | | |
| input switch complete | | | |
| menu open | | | |
| scroll limit reached | | | |

## Interpretation

Current interpretation:

- `KEY_ADC2` is a resistor ladder for the four directional actions
- `KEY_ADC1` is a separate analog sense line for center or enter
- the monitor likely decodes button presses by reading analog thresholds on those ADC inputs
- the front `LED` may provide observable feedback that can be sampled as part of control confirmation

This is why an inline electrical emulator is attractive. The system does not necessarily need to reverse engineer every internal software path if it can present the same resistance values the original `JOG` board presents.

## Known gaps

- idle-state measurements are not yet documented here
- tolerance ranges for each button value are not yet known
- the electrical characteristics and exact semantics of `KED_LED` still need confirmation
- contention behavior between the original board and a parallel controller is not yet characterized

## Suggested follow-up

- repeat all resistance measurements and record date, tool, and conditions
- capture photos of connector orientation and wiring colors
- record whether measurements differ while the board is connected versus isolated
- record `LED` behavior during input changes, idle state, and menu navigation
- test whether button recognition is tolerant to nearby resistor substitutions
