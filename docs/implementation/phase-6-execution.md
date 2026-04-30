# Phase 6 Execution Record

## Purpose

This document records the intended execution outcome for `Phase 6: Discrete-Component Protoboard Validation`.

It complements:

- [Implementation Plan](./plan.md)
- [Requirements](../requirements.md)
- [CJ791 JOG Board Notes](../hardware/cj791-jog-board.md)
- [Phase 6 Protoboard BOM](../hardware/protoboard-bom.md)
- [Phase 6 Protoboard Schematic](../hardware/protoboard-schematic.md)

## Goal

Build and validate a practical protoboard proof of concept that uses mostly discrete components and freely available Raspberry Pi `GPIO` so software production and testing can begin before the final integrated board exists.

This phase is intentionally a separate prototype circuit, not the final integrated hardware topology from Phases 3 and 4.
The Phase 6 hardware is for reference and proof-of-concept use only, not for reuse as the final integrated board.

## Scope

In scope:

- protoboard wiring for low-level `JOG` observation and drive
- `ADS1115` observation of `KEY_ADC2`
- `ADS1115 ALERT/RDY` integration to a Raspberry Pi GPIO
- direct Raspberry Pi observation of `KEY_ADC1` and `KEY_LED` through simple conditioning
- one-discrete-switch-per-action drive strategy using `2N3904`
- generous GPIO use for simplicity
- direct monitor `HDMI` connection with no Phase 5 intermediary dependency
- intentionally simplified wiring that may differ from the final integrated board
- no Phase 5 `HDMI` split, source arbitration, or custom `I2C` / `DDC` communication path

Out of scope:

- GPIO optimization
- integrated manufacturable PCB
- final connector families
- final `HDMI/DDC` intermediary hardware
- final production-grade signal conditioning
- final `HDMI` split or custom `I2C` / `DDC` transport hardware

## Locked Phase 6 Assumptions

- the monitor remains connected directly over `HDMI`
- the protoboard only needs to prove the `JOG` observation and drive concept
- `KEY_ADC2` is the only line that requires analog observation in this phase
- `KEY_ADC2` is observed through `ADS1115`
- `ADS1115 ALERT/RDY` is wired to a Raspberry Pi GPIO and used as an interrupt-style signal
- `KEY_ADC1` and `KEY_LED` are treated as digital-style observation lines in this phase
- `KEY_ADC1` is the center / enter action only; it should not produce sideways navigation on the monitor
- each driven action uses its own dedicated GPIO-controlled discrete transistor path
- `2N3904` is the preferred switching transistor for the Phase 6 protoboard

## Raspberry Pi Pin Map

| Function | GPIO (BCM) | Physical pin | Direction | Added |
|----------|-----------|--------------|-----------|-------|
| 3.3V rail | — | 1 | Power | Ph. 6 |
| 5V rail | — | 2 | Power | Ph. 21 |
| GND | — | 6 | Ground | Ph. 6 |
| I2C SDA (ADS1115) | GPIO2 | 3 | I2C | Ph. 6 |
| I2C SCL (ADS1115) | GPIO3 | 5 | I2C | Ph. 6 |
| ADS1115 ALERT/RDY | GPIO17 | 11 | Input | Ph. 6 |
| KEY_ADC1 digital input | GPIO27 | 13 | Input | Ph. 6 |
| KEY_LED digital input | GPIO22 | 15 | Input | Ph. 6 |
| CENTER drive | GPIO5 | 29 | Output | Ph. 6 |
| UP drive | GPIO6 | 31 | Output | Ph. 6 |
| DOWN drive | GPIO13 | 33 | Output | Ph. 6 |
| LEFT drive | GPIO19 | 35 | Output | Ph. 6 |
| RIGHT drive | GPIO26 | 37 | Output | Ph. 6 |
| `display_power_en` (Q9 base via R21) | GPIO24 | 18 | Output | Ph. 21 |
| Display toggle button (SW1, active-low) | GPIO4 | 7 | Input | Ph. 22 |
| WS2812B LED data SPI MOSI (via U1 level shifter) | GPIO10 | 19 | Output | Ph. 22 |

## Target Deliverables

- reviewable protoboard schematic
- reviewable protoboard BOM
- documented GPIO pin map
- documented wiring notes sufficient to reproduce the bench setup
- a working prototype good enough to unblock software production and test

## Current Schematic Direction

The Phase 6 protoboard schematic is split into three practical blocks:

1. observation block
   - `KEY_ADC2` into `ADS1115`
   - `ADS1115 ALERT/RDY` to Raspberry Pi GPIO
   - `KEY_ADC1` conditioned to Pi GPIO
   - `KEY_LED` conditioned to Pi GPIO

2. drive block
   - one `2N3904` low-side switch per logical action
   - one resistor leg per action using the tested resistor values from earlier phases
   - default-off base pull-down on every channel

3. Pi interface block
   - `3.3V` protoboard logic and ADC supply
   - `GND`
   - `GPIO2/GPIO3` for `I2C`
   - `GPIO17` for `ALERT/RDY`
   - five dedicated drive GPIO outputs
   - two dedicated observation GPIO inputs

## Bench Observation

### Observation base resistors — increased from `10 kOhm` to `100 kOhm`

The initial protoboard used `10 kOhm` resistors for `R1` (`MON_KEY_ADC1 → Q1 base`) and `R3` (`MON_KEY_LED → Q2 base`). During bench testing the `10 kOhm` value on `R1` caused the monitor OSD to misbehave whenever the `KEY1` action was active. Both `R1` and `R3` were increased to `100 kOhm` to keep the observation path consistently high-impedance across all monitored lines. The schematic and BOM already reflect these corrected values.

The root cause is the transistor-based observation topology: the base resistor directly sets how much current is drawn from the monitor bus while the key line is active. A `10 kOhm` base resistor presents enough loading to disturb the resistor-ladder decoding on `KEY_ADC1`.

Observed symptoms with `10 kOhm`:

- the OSD became visibly corrupted while open
- the menu appeared to wander into unrelated configuration areas such as gamma settings
- sometimes the user could back out and exit
- other times the monitor appeared to restart the current connection or briefly flash

Interpretation:

- this is not expected `KEY_ADC1` behavior
- `KEY1` should map only to the center / enter action
- sideways navigation implies the bus is being loaded or perturbed enough to create false key decoding
- `100 kOhm` was better than `10 kOhm`, but the practical bench threshold remained close to `120 kOhm` in this prototype

Note: this sensitivity is specific to the Phase 6 transistor-based observation path. Phase 3 uses a high-impedance op-amp buffer (`TLV9064`) as the first stage, with `10 kOhm` parts serving only as series input protection resistors. The op-amp input impedance is in the megaohm range, so bus loading in Phase 3 is negligible regardless of the protection resistor value.

### `KEY_ADC2` ADC isolation — added `100 kOhm` series resistor

During Phase 18 display/power bring-up, a Phase 6 power-sequencing defect was found: when the Raspberry Pi was powered off, the `ADS1115` also lost power, but `MON_KEY_ADC2` remained connected directly to `ADS1115 AIN0`. The unpowered ADC input loaded/clamped the monitor key line to about `1.3V`, which is close to the measured `KEY_ADC2 down` state and caused the monitor to see a false key action.

The protoboard was updated with a `100 kOhm` series isolation resistor (`R20`) between `MON_KEY_ADC2` and `ADS1115 AIN0`.

Validation result:

- with the Pi off, the monitor is no longer disturbed
- with the Pi disconnected from power, the monitor is still no longer disturbed
- the unpowered `ADS1115` no longer appears to force `KEY_ADC2` into a false key state

This confirms that Phase 6 must not connect monitor key lines directly to unpowered silicon. Later integrated-board designs should preserve a high-impedance or power-safe observation path for `KEY_ADC2`.

## Exit Criteria

- the protoboard can generate all required low-level `JOG` actions reliably
- the observation path is good enough to support software development and testing
- the prototype no longer depends on the final integrated board to start backend and UI bring-up
- the prototype remains a proof of concept rather than the final integrated circuit design
- the prototype hardware is reference-only and is not intended to be reused as the final integrated board
- later hardware work is primarily consolidation and manufacturability, not concept discovery

## Deliverables Completed

- documented the Phase 6 protoboard schematic with explicit active-component and net mapping
- documented the Phase 6 protoboard BOM for the discrete validation build
- recorded the Raspberry Pi GPIO pin map for observation, drive, and `ADS1115` integration
- fixed the prototype around a one-discrete-switch-per-action drive strategy using `2N3904`
- fixed `ADS1115` as the accepted `KEY_ADC2` observation path with `ALERT/RDY` wired to a Pi GPIO
- recorded the direct-monitor `HDMI` assumption so software bring-up does not wait on the later intermediary hardware

## Exit-Criteria Assessment

Phase 6 is complete at the protoboard-validation definition level.

The final documented state now includes:

- a reviewable protoboard schematic for the validation build
- a reviewable protoboard BOM for the discrete prototype
- a fixed Raspberry Pi pin map for the Phase 6 observation and drive paths
- a documented hardware direction that is sufficient to unblock backend and UI bring-up before the integrated board exists

Known limitation:

- this execution record defines and locks the validation build, but bench assembly and hardware-in-loop proof still remain part of the later implementation path
- the `KEY_ADC1` observation path appears sensitive to resistor value in the POC, and values below roughly `120 kOhm` can corrupt OSD behavior instead of producing a clean center-only input
