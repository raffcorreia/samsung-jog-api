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

## Reference Diagram

Current observation-path concept diagram:

![Phase 3 observation path concept](../assets/hardware/phase-3-observation-schematic.svg)

This diagram is intentionally schematic in the architectural sense, not a finalized electrical schematic. Its purpose is to show that the observation board probes the existing bus in parallel while the original `JOG` board and front-panel LED remain connected.

Preliminary connection-level schematic:

- KiCad project: [phase-3-observation.kicad_pro](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/hardware/kicad/phase-3-observation/phase-3-observation.kicad_pro)
- KiCad schematic: [phase-3-observation.kicad_sch](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/hardware/kicad/phase-3-observation/phase-3-observation.kicad_sch)

This is the current connection-level schematic source for the observation path. It replaces the second SVG-style diagram and is intended to be the editable starting point for the actual electrical design.

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
- whether `KEY_LED` is low or high after buffered observation
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

Use buffered analog observation for `KEY_ADC1` and `KEY_ADC2`, and buffered high-impedance observation with digital-threshold interpretation for `KEY_LED`.

Pros:

- matches the actual signal characteristics better
- keeps the key buses observable as analog states
- keeps `KEY_LED` simpler where only basic readability is needed at this stage while still following the low-interference probe philosophy

Cons:

- mixed implementation paths
- slightly more board complexity than a fully digital approach

## Current Recommendation

The current recommended direction is `Candidate C`.

Rationale:

- `KEY_ADC1` and `KEY_ADC2` are analog resistor-ladder inputs and should remain observable as analog values during the first hardware implementation
- `KEY_LED` currently looks suitable for high-or-low observation after a high-impedance probe stage
- this keeps the observation path aligned with the known electrical model without prematurely collapsing the key buses into fixed digital thresholds

## Selected Observation Architecture

The current Phase 3 design decision is to use a hybrid observation path:

- `KEY_ADC1` observed as analog through a high-impedance buffered path
- `KEY_ADC2` observed as analog through a high-impedance buffered path
- `KEY_LED` observed through a buffered high-impedance path and then interpreted digitally

This is now the selected architecture for the next phase, unless later bench testing reveals that the chosen analog front end disturbs the bus or produces unstable readings.

### Selected key-bus observation path

For `KEY_ADC1` and `KEY_ADC2`, the preferred topology is:

1. monitor-side tap from `CN1001`
2. input protection resistor on each observed line
3. optional small RC filter only if noise proves problematic
4. high-input-impedance rail-to-rail buffer stage
5. external ADC readable by the Raspberry Pi

This keeps the monitor-side loading low, preserves analog visibility, and gives software the raw observations it needs to classify states and later tune thresholds.

### Selected `KEY_LED` observation path

For `KEY_LED`, the preferred topology is:

1. monitor-side tap from `CN1001`
2. input protection resistor
3. high-input-impedance buffer or equivalent probe stage
4. optional clamp or logic-conditioning stage if bench testing shows it is needed
5. Raspberry Pi-readable digital input path

At this stage `KEY_LED` does not need to be treated as a full analog recording channel. The current design goal is to expose low-or-high state transitions safely and reliably without materially loading the LED line.

## Component Direction

Phase 3 does not lock exact part numbers yet, but it does lock the component direction.

### Key-bus observation component direction

The key buses should be observed with:

- a rail-to-rail high-input-impedance analog buffer stage
- an external ADC with enough channels for at least `KEY_ADC1` and `KEY_ADC2`
- a Raspberry Pi software path that reads raw ADC values and maps them into logical states

Preferred component classes:

- quad or dual rail-to-rail op-amp suitable for unity-gain buffering at `3.3V`
- external I2C ADC so the Raspberry Pi does not need direct analog input hardware

Why this direction is selected:

- the Raspberry Pi does not provide native analog inputs
- the key buses are fundamentally analog and should stay observable as analog values in the first implementation
- using an external ADC keeps GPIO usage modest and the software model clean

### `KEY_LED` component direction

`KEY_LED` should be observed through a buffered high-impedance path first, then interpreted as a digital signal.

Preferred component classes:

- series input resistor
- high-input-impedance buffer stage or equivalent probe stage
- optional clamp or logic-conditioning stage if needed after bench validation
- Raspberry Pi GPIO input or another digital input presented to the host after buffering

Why this direction is selected:

- the measured `KEY_LED` behavior currently looks compatible with simple on-or-off observation
- direct resistor-only sensing would still draw some current and is not the best fit for the low-interference observation philosophy
- richer LED semantics are intentionally deferred to the later LED characterization phase
- there is no current need to spend analog-channel budget on `KEY_LED`

## Reference Component Shortlist

These are reference-level component targets to guide later schematic work. They are not yet locked BOM decisions.

### Analog buffer stage

Target characteristics:

- rail-to-rail input and output
- unity-gain stable
- operates from `3.3V`
- very low input bias current
- available in dual or quad package

Reference examples to evaluate:

- `MCP6002` / `MCP6004`
- similar low-power rail-to-rail op-amps with good behavior near ground and `3.3V`

### External ADC

Target characteristics:

- I2C interface
- at least 2 analog channels, with 4 preferred
- input range compatible with `0V` to `3.3V`
- enough sample rate for repeated human-driven `JOG` activity and later recording

Reference examples to evaluate:

- `ADS1115`
- similar I2C ADCs with adequate resolution and software support

### `KEY_LED` digital input path

Target characteristics:

- protected Raspberry Pi-readable digital input after a high-impedance probe stage
- simple high-or-low interpretation
- optional logic conditioning only if later bench tests show it is needed

Reference building blocks to evaluate:

- series input resistor
- op-amp or other high-input-impedance buffer stage
- optional clamp protection
- optional Schmitt-trigger conditioning only if raw GPIO edge quality proves poor

## Proposed Observation Responsibilities

The observation hardware should be responsible for:

- monitor-side input protection
- high-impedance buffering or equivalent isolation
- analog presentation of `KEY_ADC1` and `KEY_ADC2` to software-readable hardware
- high-impedance observation of `KEY_LED` followed by digital presentation to software-readable hardware
- preserving a stable reference to monitor `GND`

Software should remain responsible for:

- mapping observed analog ranges into logical `up`, `down`, `left`, `right`, and `center`
- deciding whether a bus is busy
- exposing events and state to the API and later recording subsystem

## Classification Strategy

The observation path should expose raw values first and classify in software second.

That means:

- the hardware should not try to decide `up`, `down`, `left`, or `center`
- software should map ADC ranges into logical states after real readings are collected
- threshold ranges should be derived from measured values with margin, not guessed in hardware

Expected software-visible states:

- `KEY_ADC1`: `idle`, `center`, `unknown`
- `KEY_ADC2`: `idle`, `up`, `down`, `left`, `right`, `unknown`
- `KEY_LED`: `low`, `high`

## Sampling Expectations

The observation design does not need high-speed instrumentation behavior.

It does need to:

- capture human-driven `JOG` presses and holds reliably
- expose enough temporal detail for later recording and arbitration
- leave room for repeated polling while the UI and backend are active

The practical implication is:

- the ADC path should support steady repeated sampling of both key channels
- software should store raw samples or short-window derived states during early bring-up
- exact sampling rates can remain an implementation detail, but the chosen ADC should not be so slow that short button taps become ambiguous

## Verification Plan

The implemented observation path should be verified in this order:

1. bench-check the observation hardware without the monitor connected
2. verify that the observation path does not drive any monitored line
3. connect the observation path inline with the preserved original `JOG`
4. confirm idle readings for `KEY_ADC1`, `KEY_ADC2`, and `KEY_LED`
5. confirm that physical `JOG` use still behaves normally on the monitor
6. record repeated readings for each directional action and center press
7. confirm that software can classify each logical state consistently
8. confirm that `KEY_LED` high and low transitions are visible without affecting the monitor
9. confirm that the presence of the observation path does not materially change previously validated resistance and voltage behavior

Success criteria:

- the monitor behaves normally with the observation path connected
- the key buses remain readable and classifiable
- the original `JOG` remains usable
- `KEY_LED` state transitions are visible
- no unstable or unexplained loading effects are introduced

## Remaining Design Decisions

Only a narrower set of decisions remains open after the Phase 3 architecture selection:

- exact buffer stage part number
- exact ADC part number
- whether a small RC filter is needed on the observed key buses
- exact protection values for the observed lines
- whether `KEY_LED` needs extra conditioning beyond a buffered protected digital-input path

## Approval Decision

Current Phase 3 approval decision:

- approve hybrid observation architecture
- approve analog observation for `KEY_ADC1` and `KEY_ADC2`
- approve high-impedance buffered observation with digital interpretation for `KEY_LED`
- approve software-side classification of key-bus ranges
- approve external ADC direction rather than trying to force pure Raspberry Pi digital observation on the key buses

These decisions are sufficient to proceed into detailed circuit selection and later implementation work.

## Previously Open Design Decisions

The earlier broader open items are now narrowed by the selected architecture:

- exact analog front-end topology for `KEY_ADC1` and `KEY_ADC2`
- exact ADC and buffer selection
- voltage-protection approach for Raspberry Pi-facing inputs
- acceptable threshold and tolerance ranges for classifying observed states
- whether `KEY_LED` needs extra conditioning beyond a buffered protected digital-input path

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
- the selected observation architecture is hybrid
- the selected component direction is buffered analog observation plus external ADC for `KEY_ADC1` and `KEY_ADC2`
- `KEY_LED` is selected as a simpler protected digital observation path
- exact part numbers and protection values are still pending
