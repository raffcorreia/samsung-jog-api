# Phase 3 Execution Record

## Purpose

This document records the actual execution of `Phase 3: Bus Observation Hardware Design`.

It complements:

- [Implementation Plan](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/implementation/plan.md)
- [Solution Overview](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/design/solution-overview.md)
- [CJ791 JOG Board Notes](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/hardware/cj791-jog-board.md)
- [Phase 2 Execution Record](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/implementation/phase-2-execution.md)

## Goal

Produce and approve a hardware design for continuously observing `KEY_ADC1`, `KEY_ADC2`, and `KEY_LED` without disturbing normal monitor behavior or the preserved original `JOG`.

## Inputs From Phase 2

The current observation design starts from these validated monitor-side facts:

- connector: `CN1001`
- pin 1: `GND`
- pin 2: `KEY_ADC2`
- pin 3: `KEY_ADC1`
- pin 4: `KEY_LED`
- pin 5: `NC`
- `KEY_ADC1` idle: `3.3V` to `GND`
- `KEY_ADC2` idle: `3.3V` to `GND`
- `KEY_LED` idle: `0V`
- `KEY_LED` active: `2.7V` with the LED connected
- `KEY_LED` active: `2.9V` with the LED disconnected
- `KEY_ADC1` and `KEY_ADC2` action states are represented by resistance-to-ground values
- `KEY_ADC1` and `KEY_ADC2` did not materially change when the `JOG` board or cable side was connected or disconnected

## Design Scope

This phase covers only the observation path.

In scope:

- `KEY_ADC1` observation
- `KEY_ADC2` observation
- `KEY_LED` observation
- monitor-safe electrical interfacing to Raspberry Pi inputs
- software-visible output of the observed signal states

Out of scope:

- analog drive circuitry
- final Raspberry Pi GPIO assignment
- detailed `KEY_LED` semantic interpretation
- sequence recording implementation

## Functional Requirements

The observation path must:

- continuously observe `KEY_ADC1`, `KEY_ADC2`, and `KEY_LED`
- avoid materially changing monitor behavior or original `JOG` behavior
- preserve the original physical `JOG` inline
- expose enough information for bus-busy detection and later recording
- expose `KEY_LED` as a readable signal for later correlation work

## Electrical Requirements

The observation path should:

- present very high input impedance to the monitor-side signals
- never drive `KEY_ADC1`, `KEY_ADC2`, or `KEY_LED`
- safely interface monitor-side voltages to Raspberry Pi-readable inputs
- tolerate the currently observed idle and active voltages
- remain valid even if resistor-tolerance and measurement noise vary slightly around the documented values

## Software-Facing Requirements

The observation path should make it possible for software to derive:

- whether `KEY_ADC1` is idle or active
- whether `KEY_ADC2` is idle or active
- the logical `KEY_ADC2` direction when a valid directional state is present
- the logical `KEY_ADC1` center press when present
- whether `KEY_LED` is low or high
- timestamps or edge events suitable for later recording and arbitration

## Candidate Observation Approaches

### Candidate A: Comparator / Digital-Threshold Observation

Observe each line through protection and thresholding, then expose only digital state changes to the Raspberry Pi.

Pros:

- simpler Raspberry Pi integration
- easier to consume in software
- lower software processing burden

Cons:

- weaker fit for resistor-ladder decoding on `KEY_ADC1` and `KEY_ADC2`
- loses analog visibility that may matter for tolerance investigation
- risks hard-coding thresholds too early

### Candidate B: Buffered Analog Observation

Buffer each observed line with a very high-impedance analog front end and feed the resulting signals into an external ADC or equivalent analog-sensing stage before software decoding.

Pros:

- best fit for resistor-ladder observation on `KEY_ADC1` and `KEY_ADC2`
- preserves analog visibility for threshold and tolerance work
- better foundation for later recording and validation

Cons:

- more component and software complexity
- requires ADC selection and analog reference decisions

### Candidate C: Hybrid Observation

Use buffered analog observation for `KEY_ADC1` and `KEY_ADC2`, and simple digital-threshold observation for `KEY_LED`.

Pros:

- matches the actual signal characteristics better
- keeps the key buses observable as analog states
- keeps `KEY_LED` simpler where only basic readability is needed at this stage

Cons:

- mixed implementation paths
- slightly more board complexity than a fully digital approach

## Current Recommendation

The current recommended direction is `Candidate C`.

Rationale:

- `KEY_ADC1` and `KEY_ADC2` are analog resistor-ladder inputs and should remain observable as analog values during the first hardware implementation
- `KEY_LED` currently looks suitable for simpler high-or-low observation
- this keeps the observation path aligned with the known electrical model without prematurely collapsing the key buses into fixed digital thresholds

## Proposed Observation Responsibilities

The observation hardware should be responsible for:

- monitor-side input protection
- high-impedance buffering or equivalent isolation
- analog presentation of `KEY_ADC1` and `KEY_ADC2` to software-readable hardware
- digital presentation of `KEY_LED` to software-readable hardware
- preserving a stable reference to monitor `GND`

Software should remain responsible for:

- mapping observed analog ranges into logical `up`, `down`, `left`, `right`, and `center`
- deciding whether a bus is busy
- exposing events and state to the API and later recording subsystem

## Open Design Decisions

These still need explicit approval during Phase 3:

- exact analog front-end topology for `KEY_ADC1` and `KEY_ADC2`
- whether the observation path uses a discrete ADC, comparator, or another mixed-signal approach
- voltage-protection approach for Raspberry Pi-facing inputs
- acceptable threshold and tolerance ranges for classifying observed states
- whether `KEY_LED` should be treated as digital-only from the start or also left observable as analog voltage

## Deliverables To Close Phase 3

- approved observation-path architecture
- approved component-direction decision for key-bus observation
- approved component-direction decision for `KEY_LED` observation
- documented rationale for the selected observation approach
- defined verification plan for the implemented observation path

## Current Status

Phase 3 has started.

Current assessment:

- the Phase 2 evidence is sufficient to begin observation-path design
- the current leading direction is buffered analog observation for `KEY_ADC1` and `KEY_ADC2` plus simpler observation for `KEY_LED`
- exact circuit selection and component choices are still pending
