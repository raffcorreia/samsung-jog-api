# Phase 6 Execution Record

## Purpose

This document records the intended execution outcome for `Phase 6: Discrete-Component Protoboard Validation`.

It complements:

- [Implementation Plan](./plan.md)
- [Requirements](../requirements.md)
- [CJ791 JOG Board Notes](../hardware/cj791-jog-board.md)
- [Phase 6 Protoboard BOM](../hardware/phase-6-protoboard-bom.md)
- [Phase 6 Protoboard Schematic](../hardware/phase-6-protoboard-schematic.md)

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
- each driven action uses its own dedicated GPIO-controlled discrete transistor path
- `2N3904` is the preferred switching transistor for the Phase 6 protoboard

## Raspberry Pi Pin Map

- `3.3V rail`: physical pin `1`
- `GND`: physical pin `6`
- `I2C SDA`: `GPIO2`, physical pin `3`
- `I2C SCL`: `GPIO3`, physical pin `5`
- `ADS1115 ALERT/RDY`: `GPIO17`, physical pin `11`
- `KEY_ADC1` digital input: `GPIO27`, physical pin `13`
- `KEY_LED` digital input: `GPIO22`, physical pin `15`
- `CENTER` drive: `GPIO5`, physical pin `29`
- `UP` drive: `GPIO6`, physical pin `31`
- `DOWN` drive: `GPIO13`, physical pin `33`
- `LEFT` drive: `GPIO19`, physical pin `35`
- `RIGHT` drive: `GPIO26`, physical pin `37`

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
