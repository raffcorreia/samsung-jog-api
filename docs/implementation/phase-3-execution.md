# Phase 3 Execution Record

## Purpose

This document records the actual execution of `Phase 3: Bus Observation Circuit Design`.

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
- BOM: [phase-3-observation-bom.md](/Users/raffcorreia/dev/src/raffcorreia/samsung-jog-api/docs/hardware/phase-3-observation-bom.md)

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
- powered state set: `KEY_ADC1` idle `3.29V`, center `0.01V`
- powered state set: `KEY_ADC2` idle `3.29V`, `left` `2.88V`, `right` `2.16V`, `down` `1.35V`, `up` `0.01V`
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

Use buffered analog observation only where it is needed, and buffered high-impedance observation with digital-threshold interpretation where the measured voltage separation makes it practical.

Pros:

- matches the actual signal characteristics better
- keeps `KEY_ADC2` observable as analog state
- allows `KEY_ADC1` and `KEY_LED` to behave more like interrupt-friendly digital inputs after buffering
- reduces dependence on a multiplexed ADC path for multiple signals

Cons:

- mixed implementation paths
- slightly more board complexity than a fully digital approach

## Current Recommendation

The current recommended direction is `Candidate C`.

Rationale:

- `KEY_ADC2` remains a true multi-state analog input and should stay observable as analog during the first hardware implementation
- the latest powered measurements show that `KEY_ADC1` center collapses very close to ground and is strongly separable from idle
- `KEY_LED` already looks suitable for high-or-low observation after a high-impedance probe stage
- this keeps analog complexity only where it is justified and makes `KEY_ADC1` and `KEY_LED` easier to surface as GPIO-level events

## Selected Observation Architecture

The current Phase 3 design decision is to use a hybrid observation path:

- `KEY_ADC1` observed through a high-impedance buffered path and then interpreted digitally
- `KEY_ADC2` observed as analog through a high-impedance buffered path
- `KEY_LED` observed through a buffered high-impedance path and then interpreted digitally

This is now the selected architecture for the next phase, unless later bench testing reveals that the chosen analog front end disturbs the bus or produces unstable readings.

### Selected `KEY_ADC2` observation path

For `KEY_ADC2`, the preferred topology is:

1. monitor-side tap from `CN1001`
2. input protection resistor on each observed line
3. optional small RC filter only if noise proves problematic
4. high-input-impedance rail-to-rail buffer stage
5. external SPI ADC readable by the Raspberry Pi

This keeps the monitor-side loading low, preserves analog visibility, and gives software the raw observations it needs to classify the directional states and later tune thresholds. SPI is used instead of I2C to keep the Pi's I2C bus free for DDC/CI communication in Phase 5.

### Selected `KEY_ADC1` observation path

For `KEY_ADC1`, the preferred topology is:

1. monitor-side tap from `CN1001`
2. input protection resistor
3. high-input-impedance rail-to-rail buffer stage
4. Schmitt-trigger or equivalent threshold stage
5. Raspberry Pi-readable digital input path

This is now preferred because the latest powered measurements show a large voltage gap between `idle` and `center`, making a digital post-buffer interpretation reasonable for this channel.

### Selected `KEY_LED` observation path

For `KEY_LED`, the preferred topology is:

1. monitor-side tap from `CN1001`
2. input protection resistor
3. high-input-impedance buffer or equivalent probe stage
4. optional clamp or logic-conditioning stage if bench testing shows it is needed
5. Raspberry Pi-readable digital input path

At this stage `KEY_LED` does not need to be treated as a full analog recording channel. The current design goal is to expose low-or-high state transitions safely and reliably without materially loading the LED line.

## Component Direction

Phase 3 now locks both the component direction and the first exact part set for the reviewable observation design.

### `KEY_ADC2` observation component direction

`KEY_ADC2` should be observed with:

- a rail-to-rail high-input-impedance analog buffer stage
- an external SPI ADC
- a Raspberry Pi software path that reads raw ADC values over SPI and maps them into logical states

Preferred component classes:

- quad or dual rail-to-rail op-amp suitable for unity-gain buffering at `3.3V`
- external SPI ADC so the Raspberry Pi does not need direct analog input hardware

Why this direction is selected:

- the Raspberry Pi does not provide native analog inputs
- `KEY_ADC2` is fundamentally multi-state analog and should stay observable as analog in the first implementation
- using an external ADC keeps the software model clean while preserving state information
- SPI is preferred over I2C to keep `SDA`/`SCL` free for DDC/CI monitor communication in Phase 5
- polling over SPI at sufficient intervals is adequate for human-driven JOG activity — the Pi is not in a sleep-between-events context where interrupt-driven sampling would matter

### `KEY_ADC1` component direction

`KEY_ADC1` should be observed with:

- a high-input-impedance buffer stage
- a digital threshold or Schmitt-trigger stage
- a Raspberry Pi GPIO input

Why this direction is selected:

- the latest powered measurements show a strong separation between `idle` and `center`
- `KEY_ADC1` is effectively binary on this monitor
- removing `KEY_ADC1` from the ADC path avoids relying on multiplexed ADC observation for two different key buses

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

These reference families capture the reasoning behind the selected parts and remain valid alternates if later bench testing forces a package or sourcing change.

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

- SPI interface
- 1 analog channel (only `KEY_ADC2` uses the ADC path)
- input range compatible with `0V` to `3.3V`
- enough sample rate for repeated human-driven `JOG` activity and later recording
- SOIC-8 or equivalent SMD package for JLCPCB assembly

Reference examples to evaluate:

- `MCP3201` — 1-channel 12-bit SPI ADC, SOIC-8, well-supported on Raspberry Pi
- similar single-channel SPI ADCs with adequate resolution and software support

### Digital input path for `KEY_ADC1` and `KEY_LED`

Target characteristics:

- protected Raspberry Pi-readable digital input after a high-impedance probe stage
- simple high-or-low interpretation
- Schmitt-trigger behavior preferred
- optional extra logic conditioning only if later bench tests show it is needed

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

- whether a small RC filter is needed on the observed key buses
- exact protection values for the observed lines
- whether `KEY_LED` needs extra conditioning beyond a buffered protected digital-input path

## Exact Part Selection

The Phase 3 observation circuit uses these locked parts:

| Ref | Part | Package | LCSC | Notes |
|-----|------|---------|------|-------|
| U1 | TLV9064IDR | SOIC-14 | C388176 | Quad rail-to-rail op-amp, buffers all three lines + spare |
| U2 | MCP3201-CI/SN | SOIC-8 | C511293 | 12-bit SPI ADC, single channel for KEY_ADC2 analog observation |
| U3 | 74LVC1G17GW | SC-70-5 | C426705 | Schmitt buffer for KEY_ADC1 |
| U4 | 74LVC1G17GW | SC-70-5 | C426705 | Schmitt buffer for KEY_LED |

Rationale:

- `TLV9064IDR` provides four low-voltage rail-to-rail op-amp channels so the two analog key buses and the LED line can all be buffered while leaving one spare channel
- `MCP3201-CI/SN` keeps `KEY_ADC2` observable as an analog signal through a Pi-friendly `SPI` ADC path. Single-channel 12-bit SOIC-8 — right-sized for this design (only one analog channel needed), frees `SDA`/`SCL` entirely for Phase 5 DDC/CI communication. Selected over `MCP3008` (8-channel, overkill) and `MCP3001` (critically low LCSC stock)
- `74LVC1G17GW` provides a clean digital interpretation stage for buffered `KEY_ADC1` and `KEY_LED`

## Default Component Values

The locked passive values and LCSC part numbers for fabrication:

| Ref | Value | Footprint | LCSC | Purpose |
|-----|-------|-----------|------|---------|
| R1, R2, R3 | 10 kΩ 1% | 0402 | C25744 | Series input protection |
| R6, R7 | 0 Ω | 0402 | C17168 | Optional signal routing jumpers |
| C1, C2, C3, C4 | 100 nF X5R | 0402 | C307331 | Local decoupling (one per IC) |
| C5 | 1 µF X5R | 0402 | C52923 | Bulk decoupling on 3.3V rail |
| C6, C7, C8 | 1 nF C0G | 0402 | C1525 | RC filter caps on observed key lines (populated) |

All passives are 0402. All LCSC numbers confirmed in-stock at time of order.

R4 and R5 (I2C pull-ups) are removed. The SPI interface of the `MCP3201` does not require pull-up resistors.

## SPI Polling Note

The `MCP3201` uses SPI and has no interrupt or `ALERT/RDY` equivalent. All reads are Pi-initiated.

Important behavior:

- the ADC result is read over SPI on demand — the Pi sends a conversion request and receives the result in the same transaction
- `KEY_ADC2` is observed by polling: a background task reads the ADC at a fixed interval and classifies the result
- `KEY_ADC1` and `KEY_LED` continue to be surfaced as GPIO-level events after buffering and thresholding — unaffected by the ADC interface change
- polling at 10 ms intervals gives 100 samples per second, which is more than sufficient for human-driven JOG activity
- the Pi runs a full software stack continuously and is not in a sleep-between-events context where interrupt-driven ADC sampling would provide a meaningful advantage
- the primary reason for choosing SPI is to keep `SDA`/`SCL` free for Phase 5 DDC/CI communication

## Phase 3 Deliverable Set

The reviewable deliverables for this phase are now:

- observation-path concept diagram
- KiCad observation schematic
- exact selected observation parts
- default component values
- observation BOM
- observation verification plan

## Approval Decision

Current Phase 3 approval decision:

- approve hybrid observation architecture
- approve analog observation for `KEY_ADC2`
- approve high-impedance buffered observation with digital interpretation for `KEY_ADC1`
- approve high-impedance buffered observation with digital interpretation for `KEY_LED`
- approve software-side classification of `KEY_ADC2` analog ranges
- approve digital threshold interpretation for `KEY_ADC1` after buffering
- approve single-channel ADC direction for `KEY_ADC2` rather than multiplexed ADC observation of both key buses
- approve SPI ADC (`MCP3201-CI/SN`) in place of I2C ADC (`ADS1115IDGSR`) to preserve `SDA`/`SCL` for Phase 5 DDC/CI communication
- approve polling-based ADC observation over SPI in place of interrupt-assisted `ALERT/RDY` observation

These decisions are sufficient to proceed into detailed circuit selection and later implementation work.

## Previously Open Design Decisions

The earlier broader open items are now narrowed by the selected architecture:

- exact analog front-end topology for `KEY_ADC2`
- exact ADC and buffer selection
- voltage-protection approach for Raspberry Pi-facing inputs
- acceptable threshold and tolerance ranges for `KEY_ADC1`
- acceptable threshold and tolerance ranges for `KEY_ADC2` software classification
- whether `KEY_LED` needs extra conditioning beyond a buffered protected digital-input path

## Deliverables To Close Phase 3

- approved observation-path architecture
- approved key-bus observation schematic
- approved `KEY_LED` observation schematic path
- approved observation BOM
- documented rationale for the selected observation approach
- defined verification plan for the implemented observation path

## Fabrication Files

### Rev A (ADS1115 / I2C — superseded)

KiCad project: `hardware/kicad/phase-3-observation-reva/`

| File | Purpose |
|------|---------|
| `phase-3-observation-reva.kicad_sch` | Schematic (Rev A, ADS1115-based, I2C) |
| `phase-3-observation-reva.kicad_pcb` | PCB (Rev A) |
| `production/phase-3-observation-reva.zip` | Gerbers for JLCPCB fabrication (Rev A) |
| `production/bom.csv` | JLCPCB-format BOM with LCSC part numbers (Rev A) |
| `production/positions.csv` | JLCPCB-format CPL with corrected IC rotations (Rev A) |

### Rev B (MCP3201 / SPI — current)

KiCad project: `hardware/kicad/phase-3-observation-revb/` — **schematic to be redrawn in KiCad**

The `MCP3201-CI/SN` (SOIC-8) has a different package and pinout from the `ADS1115IDGSR` (MSOP-10) it replaces. The Rev B schematic cannot be produced by editing the Rev A file in place — it requires a new KiCad schematic.

Key schematic changes from Rev A to Rev B:

- `U2`: replace `ADS1115IDGSR` (MSOP-10, I2C) with `MCP3201-CI/SN` (SOIC-8, SPI)
- remove `R4` and `R5` (I2C pull-ups — not needed for SPI)
- replace `I2C_SDA`, `I2C_SCL`, `ADC_ALERT` net labels with `SPI_MISO`, `SPI_CLK`, `SPI_CS`
- update `J2` host header: replace `SDA`, `SCL`, `ADC_ALERT` pins with `SPI_MISO`, `SPI_CLK`, `SPI_CS`

## Schematic Corrections (Post-Review)

The following errors were identified and corrected in the schematic after the initial fabrication file generation. These corrections do not affect the PCB layout or BOM — only the schematic topology.

### Op-amp voltage-follower wiring (U1A, U1B, U1C)

All three active op-amp channels had positive feedback instead of negative feedback. The output was wired back to IN+ and the SENSE signal was wired to IN−, which is an oscillator topology, not a unity-gain buffer.

Fixed: SENSE now connects to IN+ (non-inverting input). Output feeds back to IN− (negative feedback). SENSE routing uses an L-shaped detour for units A and B to avoid a routing conflict with the IN− pin on the same vertical trace.

### U1D (spare op-amp channel) missing

U1D had been accidentally removed from the schematic. The spare channel was not visible, leaving the unused op-amp inputs floating.

Fixed: U1D symbol restored. IN+ tied to GND, output looped back to IN− — correct safe termination for an unused rail-to-rail op-amp.

### TLV9064IDR power pin labels reversed (U1E)

The schematic had pin 4 labeled V+ and pin 11 labeled V−. The TLV9064IDR datasheet shows the opposite: pin 4 is V− (negative supply) and pin 11 is V+ (positive supply). This is the reverse of the classic LM324 convention. The chip would have been powered with reversed supply rails.

Fixed: pin 4 → GND (V−), pin 11 → +3V3 (V+). The embedded library symbol was also corrected to match.

### C6/C7/C8 changed from DNP to populated

C6, C7, and C8 (1 nF C0G RC filter caps on the observed key lines) were originally marked DNP. Changed to populated by default.

### PWR_FLAG placement

#FLG01 (PWR_FLAG) was stranded — not connected to any net. Fixed by moving it onto the GND net. #FLG02 remains on the +3V3 net. Each power net now has exactly one PWR_FLAG for ERC compliance.

### C1 repositioned

C1 (100 nF decoupling) was moved from its original position near U1E to sit adjacent to C5 near the +3V3/GND rail junction. Both are bulk/decoupling caps on the same rail; keeping them together improves schematic readability. PCB placement is unaffected.

---

## Current Status

Phase 3 Rev B is in progress. ADC changed from I2C (`ADS1115IDGSR`) to SPI (`MCP3201-CI/SN`) to preserve `SDA`/`SCL` for Phase 5 DDC/CI communication.

- architecture selected and locked: Candidate C hybrid
- Rev A schematic corrected and reviewed (see Schematic Corrections above)
- Rev B documentation and BOM updated
- Rev B KiCad schematic: **pending** — requires new schematic in KiCad (different package and pinout, cannot be edited in place from Rev A)
- Rev B PCB: pending schematic completion
- Rev B Gerbers, BOM, and CPL: pending PCB completion
