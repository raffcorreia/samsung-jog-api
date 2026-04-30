# Implementation Plan

## Phase Index

- [Host health gate (feature phases 10–32)](#host-health-gate-feature-phases-1032)
- [Phase 0: Documentation and Evidence Capture](#phase-0-documentation-and-evidence-capture)
- [Phase 1: Host Preparation and Conservative OS Cleanup](#phase-1-host-preparation-and-conservative-os-cleanup)
- [Phase 2: Hardware Validation](#phase-2-hardware-validation)
- [Phase 3: Bus Observation Circuit Design](#phase-3-bus-observation-circuit-design)
- [Phase 4: Analog Drive Circuit Design](#phase-4-analog-drive-circuit-design)
- [Phase 5: HDMI and DDC Communication Design](#phase-5-hdmi-and-ddc-communication-design)
- [Phase 6: Discrete-Component Protoboard Validation](#phase-6-discrete-component-protoboard-validation)
- [Phase 7: Integrated Controller Board Design](#phase-7-integrated-controller-board-design)
- [Phase 8: GPIO Assignment and Low-Level Control Prototype](#phase-8-gpio-assignment-and-low-level-control-prototype)
- [Phase 9: Local Platform Bring-Up](#phase-9-local-platform-bring-up)
- [Phase 10: Local API](#phase-10-local-api)
- [Phase 11: Low-Level JOG Console UI](#phase-11-low-level-jog-console-ui)
- [Phase 12: Deployment and Version Tracking](#phase-12-deployment-and-version-tracking)
- [Phase 13: Full-Screen UI Layout with Placeholders](#phase-13-full-screen-ui-layout-with-placeholders)
- [Phase 14: Log Architecture Refactor](#phase-14-log-architecture-refactor)
- [Phase 15: Observation Bus and Hardware Interface](#phase-15-observation-bus-and-hardware-interface)
- [Phase 16: Recording and Replay Subsystem](#phase-16-recording-and-replay-subsystem)
- [Phase 17: Development Fixture](#phase-17-development-fixture)
- [Phase 18: Display and Touch Validation](#phase-18-display-and-touch-validation)
- [Phase 19: Display Usability and Power Hardening](#phase-19-display-usability-and-power-hardening)
- [Phase 20: Raspberry Pi 5 Rebuild and Display Performance Validation](#phase-20-raspberry-pi-5-rebuild-and-display-performance-validation)
- [Phase 21: Display Power Control Circuit](#phase-21-display-power-control-circuit)
- [Phase 22: Documentation Reorganization](#phase-22-documentation-reorganization)
- [Phase 23: Physical Display and Pi Power Button](#phase-23-physical-display-and-pi-power-button)
- [Phase 24: DDC Capability Investigation](#phase-24-ddc-capability-investigation)
- [Phase 25: LED Feedback Characterization](#phase-25-led-feedback-characterization)
- [Phase 26: State Investigation and Sequence Cleanup](#phase-26-state-investigation-and-sequence-cleanup)
- [Phase 27: Deck Settings, Block Editor, and Recording Visualisation](#phase-27-deck-settings-block-editor-and-recording-visualisation)
- [Phase 28: Productized Monitor Features](#phase-28-productized-monitor-features)
- [Phase 29: Dashboard Data-Source Spike](#phase-29-dashboard-data-source-spike)
- [Phase 30: Dashboard Widgets](#phase-30-dashboard-widgets)
- [Phase 31: Custom Hardware Installation, DDC Migration, and Configuration Revert](#phase-31-custom-hardware-installation-ddc-migration-and-configuration-revert)
- [Phase 32: Stabilization](#phase-32-stabilization)
- [Deferred: Integrated-board GPIO and software migration](#deferred-integrated-board-gpio-and-software-migration)

## Summary

This document describes the proposed implementation order for `samsung-jog-api`.

The overall strategy is:

1. finish defining and documenting the system
2. prepare the host platform
3. validate and design the custom hardware
4. bring up low-level control end to end
5. add recording and replay so monitor workflows can be investigated repeatably
6. improve the recording workspace with settings and a block-mode editor
7. investigate `DDC` and `LED` behavior using those repeatable tools
8. turn validated findings into productized monitor features
9. finish dashboard and stabilization work

This order matters because many higher-level features depend on being able to send low-level `JOG` actions, repeat them, and correlate them with `DDC` and `LED` feedback.

## Host health gate (feature phases 10–32)

Phases **10–32** introduce or expand product behavior on the **Raspberry Pi control deck**. Completing any of these phases (closing the phase in the implementation plan) requires a **host health snapshot** so regressions in power, thermals, storage, or runtime health are visible over time.

**Procedure (run on the deck host):**

1. Run **`python3 scripts/pi-deck-host-health.py`** (default: **human-readable text**). The script reports Python runtime, CPU load, memory and swap, disk use on `/`, thermal zones, Raspberry Pi `vcgencmd` temperature/voltage/throttling when available, optional `systemd` status for `pi-deck` and `lightdm`, and a localhost check to `http://127.0.0.1:8756/health`. Optional **`--json`** exists only for tooling or archives — **do not use JSON as the primary documentation** in execution records.
2. Paste the **full default (text) output** into that phase’s **Markdown execution record** under a heading such as `## Host health snapshot` (a fenced code block is fine), with the **date** and **host** clear from the output or a one-line note.
3. Briefly **review** the snapshot: e.g. `get_throttled` flags should not show sustained under-voltage or active throttling under normal idle/deck workload; root filesystem use should remain in a safe band for the SD card. Exact numeric thresholds are project judgment — the point is **documented evidence** each phase.

Phases **10–32** inherit this gate unless a phase is explicitly documentation-only (then note *N/A* in the execution record).

## Deferred integrated-board GPIO and software migration

Phase 7 (integrated `KiCad` boards) may still be in layout or fabrication while software advances. Low-level work from Phase 8 onward is therefore validated first on the **Phase 6 discrete protoboard**, whose **GPIO map differs** from the final integrated assignment (see [Phase 6 Execution Record](./phase-6-execution.md) vs [Phase 7 Execution Record](./phase-7-execution.md)).

When Phase 7 hardware is ready, the plan will **insert an additional phase** at a **TBD slot** (for example after intermediate milestones — numbering is chosen at insertion time so the surrounding order stays coherent). That phase will cover:

- remapping GPIO and host configuration from the Phase 6 baseline to the Phase 7 pinout
- adapting and re-validating software, tests, and automation that assumed Phase 6 pins
- updating operational docs and runbooks that reference specific BCM GPIO numbers or physical pins

Until that migration phase runs, treat the **Phase 6 GPIO map** as the authoritative software bring-up reference for hardware-facing code.

## Testing Strategy

Testing should be introduced alongside implementation, not saved for the end.

The implementation is expected to grow these testing layers over time:

- backend tests for API behavior, arbitration, validation, and service logic
- frontend tests for control feedback, websocket-driven state updates, and key user interactions
- hardware-facing verification tests for low-level `JOG`, `LED`, and `DDC` behavior
- sequence-schema and sequence-runner validation tests
- integration tests for productized monitor workflows

Detailed test design still needs its own document, but no phase should be treated as complete without the relevant tests for that phase.

For **Phases 10–32**, also satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in the phase execution record.

## Phase 0: Documentation and Evidence Capture

### Goal

Finish the planning and evidence baseline so implementation can begin with a stable definition of the system.

### Scope

- requirements
- solution design
- hardware notes
- implementation plan
- measured monitor evidence
- known future investigations

### Deliverables

- approved requirements document
- approved solution overview
- updated hardware notes with current measurements
- implementation plan with ordered phases and priorities
- repository structure ready for implementation

### Exit criteria

- the system scope is clear enough that hardware and software implementation can begin
- current measurements and assumptions are documented
- known open investigations are captured explicitly instead of being hidden assumptions

## Phase 1: Host Preparation and Conservative OS Cleanup

### Goal

Prepare the Raspberry Pi host so it is stable, reproducible, and ready for kiosk and hardware work.

### Scope

- Raspberry Pi OS Lite or equivalent base image
- conservative package cleanup
- repeatable host-preparation notes
- avoid unnecessary software and services

### Tasks

- validate the Raspberry Pi base image and software state
- identify software and services that are unnecessary for this project
- perform conservative cleanup rather than aggressive minimization
- document exactly what was removed, disabled, or changed
- create repeatable host-preparation scripts for baseline capture, cleanup review, cleanup application, and smoke checks
- create a cleanup-config template that can be copied to the actual host without committing machine-specific choices
- keep generated host-baseline artifacts out of git
- update the repository status to reflect the start of Phase 1
- create a backup image once the host baseline is considered ready

### Deliverables

- prepared Raspberry Pi host
- documented cleanup and preparation procedure
- repeatable host-preparation scripts
- local-only cleanup configuration template
- baseline image or reproducible setup record

### Exit criteria

- the host boots cleanly
- unnecessary services are reduced
- the preparation steps are documented well enough to repeat later

## Phase 2: Hardware Validation

### Goal

Confirm the measured electrical behavior of the monitor control path before committing to controller circuitry.

### Scope

- `CN1001` validation
- `KEY_ADC1` and `KEY_ADC2` validation
- basic `KEY_LED` electrical validation
- original `JOG` behavior observation

### Tasks

- confirm `CN1001` pinout on the actual target unit
- re-measure idle voltage on `KEY_ADC1` and `KEY_ADC2`
- re-measure resistance-to-ground for each directional action and center press
- capture connector photos, orientation, and wiring notes
- confirm whether measurements differ with the board connected versus disconnected
- confirm whether `KEY_LED` is electrically readable as a simple input and note its basic on or off behavior
- confirm the physical `JOG` can remain preserved as a hard requirement

### Deliverables

- updated measurement records
- updated hardware notes
- confidence that the current electrical model is accurate enough for controller design

### Exit criteria

- idle and action measurements are confirmed on the target hardware
- no critical contradiction exists between the documented model and the real monitor

## Phase 3: Bus Observation Circuit Design

### Goal

Design, document, and approve the complete observation circuit needed to observe the monitor-side signals continuously.

### Scope

- observation of `KEY_ADC1`
- observation of `KEY_ADC2`
- observation of `KEY_LED`
- safe interface between monitor-side signals and Raspberry Pi inputs
- component selection for the observation path
- observation BOM and schematic

### Tasks

- define the observation-path requirements
- determine how to sense bus activity safely without disturbing the monitor behavior
- determine how continuous observation will be exposed to software
- document the observation circuitry candidates
- select the observation-path component families and exact parts
- produce the observation-path schematic
- produce the observation-path BOM
- review and approve the observation design
- define how the observation path will be verified during implementation

### Deliverables

- approved observation-path design
- documented component and topology decisions
- observation schematic
- observation BOM
- observation verification approach

### Exit criteria

- there is an approved observation circuit for continuous safe observation of the relevant monitor-side signals
- the observation circuit has a reviewable schematic and BOM
- the observation path is documented well enough to be integrated into a full controller board

## Phase 4: Analog Drive Circuit Design

### Goal

Design, document, and approve the complete analog drive circuit needed to reproduce the monitor's analog `JOG` behavior.

### Scope

- drive path for `KEY_ADC1`
- drive path for `KEY_ADC2`
- safe interaction with the preserved original `JOG`
- analog resistor-state reproduction
- component selection for the drive path
- drive BOM and schematic

### Tasks

- define the required analog states to reproduce
- evaluate candidate circuit approaches for presenting resistance-to-ground states
- define how the original `JOG` remains preserved
- define how drive and observe paths coexist
- document the analog drive design candidates
- select the drive-path component families and exact parts
- produce the analog drive schematic
- produce the analog drive BOM
- review and approve the analog drive design
- define how the analog drive path will be verified during implementation

### Deliverables

- approved analog drive design
- documented component and topology decisions
- analog drive schematic
- analog drive BOM
- analog drive verification approach

### Exit criteria

- there is an approved analog drive circuit for reproducing the required analog states safely and repeatably
- the drive circuit has a reviewable schematic and BOM
- the drive path is documented well enough to be integrated into a full controller board

## Phase 5: HDMI and DDC Communication Design

### Goal

Define and validate how the final system preserves practical use of the monitor's `HDMI` input while still maintaining a reliable `DDC` communication path.

### Scope

- `HDMI` and `DDC` transport strategy
- evaluation of shared or multiplexed `HDMI` / `DDC` access
- impact on final controller-board interfaces
- custom hardware needed beyond the core controller board, if any
- deck-display selection tied to the final hardware connector and enclosure assumptions

### Tasks

- document the current development compromise of temporary full `HDMI` takeover
- define the final-system requirement for preserving practical `HDMI` use
- evaluate candidate approaches for shared or multiplexed `HDMI` / `DDC` access
- determine how the chosen transport approach affects connectors, harnessing, and board interfaces
- identify any additional custom hardware required beyond the controller board itself
- compare practical Raspberry Pi-compatible touch-display options from relevant vendors
- select the deck display that best fits the project's size, mounting, interface, and integration goals
- document the chosen display and preserve the comparison artifact in the repo
- document the selected transport direction and its rationale
- define how the chosen transport approach will be verified later in implementation

### Deliverables

- approved `HDMI` / `DDC` communication direction for the final system
- documented rationale for the chosen transport approach
- defined interface impact on the integrated hardware design
- approved deck-display selection for the control deck
- preserved display-comparison artifact for later reference
- communication verification approach

### Exit criteria

- the project has an approved direction for preserving practical `HDMI` use while maintaining `DDC` communication
- the hardware plan no longer depends on permanent `HDMI` sacrifice as a final-system assumption
- the project has an approved deck-display choice rather than only generic target characteristics

## Phase 6: Discrete-Component Protoboard Validation

### Goal

Build and validate a practical protoboard proof of concept that uses mostly discrete components and freely available Raspberry Pi `GPIO` so software production and test can begin before the final integrated board exists.

This phase is intentionally a separate prototype circuit, not the final integrated hardware topology that Phase 7 will design from the Phase 3 and Phase 4 results.
The Phase 6 hardware is reference-only proof-of-concept hardware and is not intended to become the final integrated board.

### Scope

- bench or protoboard implementation using mostly discrete components
- `ADS1115` is the accepted analog-observation ADC for `KEY_ADC2` in this phase
- `ADS1115 ALERT/RDY` may be used as an interrupt-style signal to the Raspberry Pi
- no GPIO-minimization requirement; use as many Raspberry Pi `GPIO` lines as needed
- monitor remains connected directly over `HDMI` without the final `HDMI/DDC` intermediary in the path
- no multiplexer pressure for the protoboard if separate GPIO-controlled paths are simpler
- validation of the core observation and analog-drive concepts
- software-unblocking prototype sufficient for low-level control bring-up and testing
- intentionally simplified wiring that may differ from the final integrated board
- no Phase 5 `HDMI` split, source arbitration, or custom `I2C` / `DDC` transport prototype work

### Tasks

- build a protoboard version of the monitor-control concept using mostly discrete components that are easy to source and hand-wire
- use `ADS1115` for `KEY_ADC2` analog observation
- wire `ADS1115 ALERT/RDY` to a Raspberry Pi GPIO so the prototype can use interrupt-style ADC readiness or threshold signaling
- keep `KEY_ADC1` and `KEY_LED` on direct GPIO or simple conditioning paths unless testing proves more analog handling is required
- wire the monitor directly rather than routing it through the final `HDMI` intermediary hardware
- allocate Raspberry Pi `GPIO` lines freely for validation convenience rather than optimizing pin usage yet
- avoid mux-driven optimization if dedicated GPIO-controlled discrete paths are simpler for the prototype
- validate that each required low-level `JOG` action can be generated reliably from the protoboard
- validate that the observation path is good enough to support software development and testing even if it is not yet the final integrated implementation
- document any timing, signal-integrity, or practical wiring issues discovered during the protoboard stage
- record the protoboard wiring, parts used, and software assumptions clearly enough to reproduce the setup
- define what must change before the concept can be migrated into the integrated board design with reduced GPIO usage and better integration

### Deliverables

- working mostly-discrete protoboard validation setup
- documented protoboard wiring and component choices, including any allowed non-discrete helper parts such as `ADS1115`
- validated low-level hardware concept sufficient to unblock software production and test
- notes on what the later integrated board must improve, consolidate, or replace

### Exit criteria

- the project has a working protoboard implementation that proves the concept without depending on the final integrated board architecture
- software bring-up and test no longer depend on waiting for the final integrated board
- the remaining integrated-board work is primarily consolidation, manufacturability, connector/mechanical integration, and GPIO reduction rather than basic concept discovery
- Phase 6 hardware is treated as reference-only and is not carried forward as the final integrated design

## Phase 7: Integrated Controller Board Design

### Goal

Combine the validated outputs of Phase 3 observation, Phase 4 drive, Phase 5 `HDMI` / `DDC`, and Phase 6 protoboard work into a manufacturable controller-board design, then define the full host integration.

### Scope

- integrated controller schematic that merges the approved observation and drive circuits
- board-level use of the Phase 5 `HDMI` / `DDC` transport direction
- GPIO allocation informed by the Phase 6 protoboard validation results
- integrated display-power control path for the deck display
- physical local power-button support for display power control and host wake/power behavior
- PCB design and mechanical constraints
- connectors and harness strategy
- display and host power connections as needed
- board size and mounting approach
- manufacturability review

### Tasks

- combine the Phase 3 observation circuit results and Phase 4 analog-drive circuit results into one integrated schematic
- incorporate the Phase 5 `HDMI` / `DDC` communication direction into the board interfaces and connector strategy
- use Phase 6 protoboard lessons to decide which GPIO paths stay discrete, which get consolidated, and what must change for the integrated board
- define all required monitor-side, host-side, and display-side interfaces
- assign GPIO usage after the approved hardware design is known
- define which pins are input-only, output-only, or otherwise constrained
- integrate the display-power control requirements into the controller-board design so display on/off is a first-class board function
- define how a physical local power button is wired and handled on the integrated board
- define whether that button supports display-only toggle, Pi shutdown request, and Pi wake/power-on, and document any Raspberry Pi model differences
- include any always-on or out-of-band circuitry required so a physical button can wake or start the Pi even when the main software stack is off
- define connector choices for:
  - monitor-side harness
  - original `JOG` harness
  - Raspberry Pi interface
  - display power or related host-side power connections if required
  - any `HDMI` / `DDC` transport-related interfaces required by the chosen communication design
- define board dimensions and mechanical constraints
- define mounting holes, screw usage, and cable-routing assumptions
- define the PCB stack-up and board-level layout constraints
- produce the integrated controller schematic
- produce the integrated controller BOM
- produce the first PCB layout
- review the board for manufacturability and assembly risk

### Deliverables

- integrated controller schematic
- integrated controller BOM
- GPIO map
- PCB layout
- documented display-power control and physical power-button design
- documented connector and mechanical decisions
- manufacturability review notes

### Exit criteria

- the Phase 3, Phase 4, Phase 5, and Phase 6 results are represented in one coherent controller-board design
- the approved `HDMI` / `DDC` communication direction is reflected in the integrated hardware design
- display power control and the physical power-button path are accounted for in the integrated-board design
- all required pins and interfaces are defined
- the board is documented well enough to prototype or manufacture

## Phase 8: GPIO Assignment and Low-Level Control Prototype

**Status: complete.** Record: [Phase 8 Execution Record](./phase-8-execution.md).

### Goal

Build and validate low-level hardware control on a working prototype. **Current approach:** use the **Phase 6 protoboard** and its documented GPIO map first; the **integrated Phase 7 boards** are tracked separately and will trigger a [deferred migration phase](#deferred-integrated-board-gpio-and-software-migration) when they exist.

### Scope

- low-level hardware control prototype
- validation of basic `JOG` actions
- timing characterization

### Tasks

- build or reuse the Phase 6 bench prototype (or first integrated hardware when available)
- verify that each low-level `JOG` action is correctly interpreted by the monitor
- measure press, hold, repeat, and release timing
- record any timing sensitivity or debounce-like behavior
- validate the observation path against the approved design
- add hardware-facing verification tests for each low-level `JOG` action

### Deliverables

- working low-level control prototype
- verified timing baselines for individual `JOG` actions
- initial prototype validation notes

### Exit criteria

- the system can reliably perform each low-level `JOG` action through the custom hardware used for bring-up (Phase 6 protoboard until the deferred integrated-board migration runs)
- the observation and drive paths behave consistently enough to support later platform and API work

### Execution record

Complete: [Phase 8 Execution Record](./phase-8-execution.md) (2026-04-12). Bench validation confirmed jog behavior via the Phase 6 hardware path (including manual transistor-level actuation before the Pi was wired). Precise timing capture, ADS1115 baselines, and Pi-driven GPIO bench script runs are documented as immediate follow-on software work.

**How to run the bench script:** [GPIO bench probe (protoboard)](../runbooks/gpio-bench-probe.md).

## Phase 9: Local Platform Bring-Up

**Status: complete.** Record: [Phase 9 Execution Record](./phase-9-execution.md). Runbook: [Phase 9 platform bring-up](../runbooks/phase-9-platform-bring-up.md).

### Goal

Make the deck boot into its intended local runtime and behave like a dedicated appliance.

### Scope

- browser kiosk setup
- process supervision
- local application startup
- log-file behavior

### Tasks

- provision the runtime on the prepared Raspberry Pi host
- configure browser auto-start in kiosk mode
- ensure the display launches into the intended UI automatically
- configure `systemd` service management
- define crash recovery and restart behavior
- configure file logging with one log file per day and three months retention
- verify reboot and process-restart recovery behavior

### Deliverables

- Raspberry Pi boots into kiosk mode automatically
- supervised application runtime
- logging retention policy implemented

### Exit criteria

- the deck boots into the application without manual intervention
- the kiosk runtime recovers from process failures

**Deferred (not part of Phase 9 exit):** hide the mouse pointer on the kiosk display. Wayland (e.g. labwc) needs a compositor-specific or session-level approach; X11 can use `unclutter`. Tracked under Phase 11 as kiosk / touch UX polish alongside the first real UI.

## Phase 10: Local API

### Goal

Define and implement the local backend command surface that all UI and control flows use.

### Scope

- REST endpoints
- WebSocket endpoint
- low-level command surface
- status exposure

### Tasks

- define low-level command endpoints
- define status and health endpoints
- define websocket event categories
- define validation and error responses
- represent command rejection reasons explicitly
- expose operating mode and control state where needed
- add backend/API tests for request validation, websocket event shape, and error responses

### Deliverables

- stable local API for low-level control and status
- websocket event stream for live UI updates

### Exit criteria

- the frontend can drive low-level control and receive live state from the backend
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase’s execution record

## Phase 11: Low-Level JOG Console UI

**Status: completed.** Record: [Phase 11 Execution Record](./phase-11-execution.md). **Repository:** React UI, kiosk polish, automated tests, and **live hardware on the deck Raspberry Pi** — `PI_DECK_HARDWARE=live`, `GET /api/v1/status` reports `hardware: live`, and the JOG console drives the monitor end-to-end from the appliance (verified on the project deck host).

Phase 6 / Phase 8 work validated the **protoboard concept** and scripts on a bench; this phase closed the gap to the **kiosk appliance** with the same stack under `PI_DECK_HARDWARE=live` (pin factory, permissions, [Phase 6 execution](./phase-6-execution.md) pin map / `pi_deck.hardware`).

### Goal

Build the first usable controller UI for direct monitor interaction **and** close prototype→deck gaps so low-level `JOG` reaches hardware from the production host.

### Scope

- direct `JOG` control
- visible command success/failure
- live log view
- touch-first layout
- **deck host:** `LiveDeckHardware` initializes successfully (`pi-deck` stays up with `PI_DECK_HARDWARE=live`); gpiozero/GPIO issues seen on the appliance are **in scope for this phase** (not “some other future phase”)

At this stage, this raw `JOG` controller should be the only monitor-control UI exposed.

### Tasks

- implement `up`, `down`, `left`, `right`, and `center`
- support press and hold interactions
- expose error feedback when a command is rejected
- show live log output
- make the UI usable on the `1280×800` deck display
- keep the same UI reachable on the LAN
- add frontend tests for command feedback and websocket-driven UI state
- hide or tame the kiosk pointer for touch-first use (deferred from Phase 9; Wayland vs X11)
- **live hardware bring-up on the deck** (pin factory `GPIOZERO_PIN_FACTORY` if needed, group membership, BCM wiring vs [protoboard map](../../backend/src/pi_deck/hardware/protoboard_pins.py)) — **done** on the reference appliance; see Phase 11 execution record

### Deliverables

- first usable controller UI
- touch-driven low-level monitor control from the deck and LAN **with physical JOG actuation on the Phase 6–style wiring attached to that deck**

### Exit criteria

- a user can directly control the monitor through the deck UI using low-level `JOG` actions **on the deck host with live hardware** (not mock-only)
- no unvalidated high-level monitor feature UI is exposed yet
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase’s execution record

## Phase 12: Deployment and Version Tracking

### Goal

Establish a single, agent-authorizable deploy script that pushes the latest code to the deck Pi, restarts all services, and refreshes Chromium in kiosk mode. Introduce a version counter so every deployment is visible in the UI.

### Scope

- `rsync`-based deploy from the dev machine to the Pi (no git pull on the Pi, no CI/CD)
- service restart after copy
- Chromium kiosk refresh
- `status.version` field on the backend, incremented each deploy
- version badge in the UI

### Tasks

- write a single deploy script (`scripts/deploy.sh` or similar) that:
  - `rsync`s the repository to the Pi over SSH
  - restarts the `pi-deck` systemd service (and any other managed services)
  - sends a keypress or remote-debugging command to refresh Chromium in kiosk mode without relaunching the full session
  - increments a persistent version counter on the Pi (e.g. a plain file or env var baked in at deploy time)
- expose `version` in `GET /api/v1/status` response
- add a floating version badge in the top-left corner of the UI, sourced from `status.version`
- document the script as the canonical deploy method; make it safe to run repeatedly
- add the script to the agent authorization list so it can be invoked without per-run confirmation

### Deliverables

- `scripts/deploy.sh` (or equivalent) that is the one and only deploy mechanism
- `status.version` in the API and visible in the UI

### Exit criteria

- running the deploy script from the dev machine results in the Pi running the latest code with a freshly reloaded kiosk and an incremented version number visible in the UI
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase's execution record

## Phase 13: Full-Screen UI Layout with Placeholders

**Status:** completed. See [Phase 13 Execution Record](./phase-13-execution.md).

### Goal

Build the target UI shell at `1280×800` with correct proportions, real functional widgets where they exist today, and static placeholder panels for everything that is not yet wired to real data.

### Scope

- top bar with clock and action buttons
- left column with power button and JOG widget
- bottom log panel
- placeholder calendar and placeholder notes
- all panels sized and positioned for `1280×800`

### Tasks

- design the full-screen layout grid for `1280×800`
- implement a top bar containing:
  - clock on the left (display only for now; real time wiring comes in a later phase)
  - settings button and any other header actions on the right
- implement a left column containing:
  - power button (visible; behavior can be a stub)
  - the **real, functional JOG widget** from Phase 11
- implement a bottom panel showing the **real live log** from Phase 11
- implement a placeholder calendar panel with hardcoded mock entries
- implement a placeholder notes panel with hardcoded mock content
- ensure no panel overflows or breaks the layout at exactly `1280×800`
- keep placeholder panels visually distinct (e.g. labelled "coming soon" or greyed) so the intent is clear
- add frontend tests for layout rendering at the target resolution

### Deliverables

- full-screen UI shell at `1280×800` with real JOG and log panels and placeholder calendar and notes

### Exit criteria

- the deck display shows the complete intended layout with correct proportions
- no real feature work is blocked waiting on this layout
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase's execution record

## Phase 14: Log Architecture Refactor

**Status:** completed. See [Phase 14 Execution Record](./phase-14-execution.md).

### Goal

Move log ownership from the browser to the backend so logs are durable across sessions, available to all connected clients simultaneously, and not lost on refresh or reconnect.

### Scope

- backend log collection and formatting
- WebSocket delivery of log events to all clients
- replay of recent log history on new WebSocket connection
- frontend reduced to a pure log renderer

### Tasks

- define a structured log event shape for WebSocket delivery (level, timestamp, message, source)
- implement a server-side log buffer (last N entries or last X minutes) that survives browser disconnects
- emit log events over the existing WebSocket connection to all connected clients
- on new WebSocket connection, replay the buffered log history before switching to live events so the browser has immediate context
- remove any log collection or formatting logic from the frontend; the UI only receives and renders
- ensure log events from all backend services (hardware, API, sequence runner, etc.) flow through the central buffer
- add backend tests for log buffering, replay on connect, and delivery to multiple simultaneous clients

### Deliverables

- backend-owned log stream delivered over WebSocket with history replay on connect
- frontend is a stateless log renderer

### Exit criteria

- opening a new browser tab shows recent log history immediately without any action from the user
- two simultaneous browser clients see the same log stream in sync
- no log state lives in the browser
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase's execution record

## Phase 15: Observation Bus and Hardware Interface

**Status:** **closed** (merged to `main`, 2026-04-16). [Phase 15 Execution Record](./phase-15-execution.md) (host health gate satisfied). Design detail: [phase-15-observation-telemetry.md](./phase-15-observation-telemetry.md).

### Goal

Complete the hardware observation loop: `ADS1115 ALERT/RDY` as a real interrupt, full decode of `KEY_ADC1` / `KEY_ADC2` / `KEY_LED` into domain events, and make the observation bus the single authority for WebSocket broadcasts about what the hardware is doing — including physical JOG presses.

### Scope

- ADS1115 `ALERT/RDY` edge path plus asyncio watchdog (continuous conversion / conversion-ready ALERT; not “zero polling” for the whole bus)
- decode of `KEY_ADC1` and `KEY_ADC2` into directional hold/release events
- `KEY_LED` on/off event detection
- observation-backed domain events as the single WebSocket broadcast source
- physical JOG mirrored in the UI ring
- optimistic UI on the initiating browser; confirmed stream for all clients

### Tasks

- wire `ADS1115 ALERT/RDY` to a Pi GPIO and configure the comparator threshold so the interrupt fires when a key changes state
- implement an interrupt handler that reads the ADC value once on alert rather than polling
- decode the ADC reading into a domain event: which direction (`up`, `down`, `left`, `right`, `center`), press or release, and timestamp
- implement `KEY_LED` observation (GPIO input or ADC depending on Phase 6 wiring) and emit `led_on` / `led_off` domain events
- make observation-backed domain events the single producer of `held` / `released` / `led_changed` WebSocket broadcasts to all clients — remove duplicate emissions from the command path for the same physical transitions
- ensure physical front-panel JOG use produces the same `held`/`released` ring animation in the UI as a deck tap (observation does not distinguish who caused the change)
- on the initiating browser: render optimistic feedback immediately on REST success; reconcile to a confirmed/virtual style (e.g. distinct color) when the observation event arrives
- other browsers: show only the confirmed (observation-aligned) state
- treat any disagreement between drive and sense as a defect to investigate, not a UX tolerance to hide
- add backend tests for interrupt handling, ADC decode, LED event emission, and domain event broadcast; add frontend tests for optimistic vs confirmed ring state

### Deliverables

- interrupt-driven `ADS1115` observation replacing any polling path
- full observation decode for all JOG directions and LED state
- single WebSocket broadcast authority (observation bus)
- physical JOG mirrored in the deck UI

### Exit criteria

- pressing the physical monitor JOG is reflected in the deck UI ring
- `KEY_LED` state changes appear as domain events in the WebSocket stream
- no duplicate held/released events when a deck tap triggers a GPIO drive
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase's execution record

### Open Defects Carried Forward

- `KEY_ADC2` observation has shown an intermittent live-runtime failure where directional bus observation stops updating while the application remains up
- first noted during Phase 15 and initially suspected to be a protoboard wiring/pin issue; observed again during Phase 16, which weakens the assumption that the fault is purely physical wiring
- on the later occurrence, redeploying/restarting the application restored `KEY_ADC2` observation, so software runtime, driver state, or observation-task lifecycle must be treated as plausible causes
- treat this as an active defect on the observation path before relying on long-running recording, replay, or `DDC`/`LED` correlation work
- when reproducing or closing this defect, capture whether `KEY_ADC1` and `KEY_LED` remained alive, whether `ADS1115 ALERT/RDY` still toggled, and whether only process restart or full host reboot restores `KEY_ADC2`

## Phase 16: Recording and Replay Subsystem

**Status:** **closed** 2026-04-23. [Phase 16 Execution Record](./phase-16-execution.md) (host health gate satisfied).

### Goal

Add the tooling needed to record, store, replay, edit, and promote monitor interaction sequences.

### Scope

- canonical JSON recording format
- sequence runner
- recording management
- replay tools

### Tasks

- define the canonical JSON recording format
- implement validation for recordings as domain objects
- implement the unified sequence runner
- enforce sequence validation before execution
- enforce sequence timeout and no-runaway behavior
- reject concurrent sequence execution
- support immediate manual abort
- support `hold`, `release`, `delay`, `wait_led`, and `wait_ddc` events
- support polling interval and timeout behavior for wait events
- store recordings in a writable local directory
- use the observation bus as the recording source of truth so both deck-driven and physical JOG activity can be captured
- auto-save raw captures on stop with a timestamp filename; renaming can happen later from the UI
- place recording and replay tools in a large right-side recording workspace popup that respects the Phase 13 popup rules and fits the fixed `1280×800` kiosk layout
- provide replay, stop, rename, upload, download, and delete actions in that workspace
- add a reusable centered confirmation popup standard for destructive yes/no actions such as delete
- add schema validation tests and sequence-runner tests for timeout, abort, and rejection behavior
- keep the intermittent `KEY_ADC2` observation-stall defect visible during Phase 16 validation because it can invalidate long recordings and mislead replay analysis

### Deliverables

- validated sequence format
- working sequence runner
- recording and replay UI tools

### Exit criteria

- sequences can be recorded, replayed, stopped, and validated reliably
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase’s execution record

## Phase 17: Development Fixture

**Status:** closed 2026-04-20 as a crude open support. See [Phase 17 execution record](./phase-17-execution.md).

### Goal

Build a minimal open-frame structure that holds the Raspberry Pi, the Phase 6 protoboard, and the monitor harness in a repeatable, stable position for ongoing development, testing, and design validation.

### Scope

- structural skeleton only — no cover, no enclosure
- positions the Pi and protoboard in a fixed spatial relationship
- routes and retains the monitor harness without strain on connectors
- serves as a POC for the eventual integrated board layout

### Tasks

- design a skeletal frame that mounts the Raspberry Pi and protoboard side by side or in a stacked configuration
- evaluate Pi orientation options:
  - horizontal, processor facing up (natural cooling, good cable access)
  - vertical, processor facing away from the display (improved airflow on the Pi side, keeps heat away from the screen)
- validate connector clearances and harness routing for the JST PH monitor harness, GPIO ribbon, and USB power
- validate hole positions and standoff spacings against actual hardware dimensions
- fabricate or print the skeleton
- verify that all connectors can be seated and removed without disassembling the frame
- document the chosen orientation rationale and any clearance constraints discovered
- do not add covers, side panels, or cosmetic elements — those are deferred to a later enclosure phase

### Deliverables

- fabricated open-frame development fixture
- documented Pi orientation decision with airflow and access rationale
- validated connector positions and harness routing

### Exit criteria

- Pi and protoboard are mounted in a stable, repeatable position
- all connectors are accessible without disassembly
- harness routing is strain-free and does not limit reassembly
- chosen Pi orientation is documented with reasoning

## Phase 18: Display and Touch Validation

**Status:** closed 2026-04-22. See [Phase 18 execution record](./phase-18-execution.md).

### Goal

Install the Waveshare 7" DSI display, validate the touch controller, and confirm that the touch I²C bus coexists safely with the ADS1115 and DDC/CI devices already on GPIO2/3.

### Scope

- physical display installation in the development fixture
- touch controller bring-up and address enumeration on the shared I²C bus
- I²C bus coexistence verification across all three device classes
- Chromium kiosk mode validation on the installed hardware

### Tasks

- mount the Waveshare 7" DSI (E) display in the development fixture and connect the DSI ribbon and power
- boot the Pi with the display attached and confirm framebuffer / HDMI output redirects to the DSI panel
- enumerate I²C bus at runtime: confirm ADS1115 address (`0x48`), DDC/CI address (`0x37`), and the Waveshare touch controller address do not collide
- verify that `i2c-tools` `i2cdetect` output matches the expected device map with all three devices present and active
- validate touch input coordinates under Chromium kiosk mode on the 1280×800 target resolution
- confirm the existing ADC polling loop and DDC ping paths continue to function correctly while the touch controller is active
- document the confirmed I²C address map: ADS1115, DDC/CI, and touch controller
- document any required `/boot/config.txt` or `dtoverlay` changes for the DSI panel

### Deliverables

- display and touch controller physically installed in the development fixture
- documented I²C address map with all three bus participants confirmed
- kiosk mode validated on actual hardware at 1280×800

### Exit criteria

- display produces correct 1280×800 output under Chromium kiosk mode
- touch input is recognized and coordinates are accurate across the screen
- ADS1115 ADC polling, DDC/CI communication, and touch I²C traffic coexist without address conflicts or interference
- the confirmed device address map is recorded in the execution record

## Phase 19: Display Usability and Power Hardening

**Status:** closed 2026-04-22. See [Phase 19 Execution Record](./phase-19-execution.md).

### Goal

Harden the Waveshare DSI display experience after Phase 18 bring-up by adding operator-facing display power and brightness controls, preserving the DSI-only kiosk policy, and adding a visual test screen for panel readability/color/edge validation.

### Scope

- display power control from the existing top-bar power button
- Raspberry Pi shutdown flow from the same power menu
- display brightness control in Settings, capped at the validated safe maximum
- color/edge validation screen for the 7-inch DSI panel
- follow-up documentation for display usability, power draw, and unsafe output modes discovered in Phase 18
- validation of whether the panel/backlight firmware already persists brightness across reboot before adding application persistence code

### Tasks

- make the top-bar power button functional
- when the display is on, pressing the power button opens the standard popup component with three choices:
  - `Display`: power off the DSI display immediately, starting with the conservative backlight-off path; only disable/suspend touch if the driver exposes a safe and repeatable control path
  - `Pi`: open a second confirmation popup with a 5-second shutdown countdown, a `Now` button to shut down immediately, and a `Cancel` button to abort
  - `Cancel`: close the popup without action
- use a Raspberry Pi symbol/icon for the `Pi` shutdown choice
- when the display is off, pressing the power button from a remote browser session should power the DSI display back on
- add backend API endpoints/service boundaries for display brightness, display power state, and Pi shutdown; UI code must not manipulate sysfs or system commands directly
- keep display power/brightness state backend-managed so the kiosk browser and any remote browser see consistent state
- add a Settings brightness slider
- map slider `0%` through `100%` onto backlight values `0` through `170`, because `170/255` is the current validated safe ceiling
- show a Settings note explaining that brightness is capped below hardware maximum because higher values caused artifacts/power/display instability during Phase 18; include both `170/255` and the approximate hardware percentage
- test whether the selected brightness survives reboot before implementing any extra application-level brightness persistence
- if the display does not reliably preserve brightness, restore the selected brightness from the backend at service/app startup rather than relying on browser state
- add a Settings color-check control that opens a full-screen validation page
- the color-check page should include solid red/green/blue/white/black/gray, grayscale bands, small-text/readability samples, and visible top, bottom, left, and right edge lines to confirm panel alignment/cropping
- preserve the Phase 18 HDMI policy: DSI is the only kiosk visual output; HDMI remains DDC/CI-only via `video=HDMI-A-1:d`
- document whether display power-off actually saves meaningful power and whether touch is disabled, still active, or separately controllable
- benchmark/document power and throttle behavior at representative brightness points after the software cap is implemented, including `0`, the chosen comfortable/default value, and `170`

### Deliverables

- functional display/Pi power menu from the top bar
- brightness control in Settings capped to the safe Phase 18 maximum
- full-screen display color/edge validation page
- documented display power-off behavior, including whether touch is also disabled
- updated runbook/execution notes for the final brightness default, reboot persistence finding, and any boot-time restore mechanism if one is actually needed

### Exit criteria

- display can be powered off and back on from the UI/API without destabilizing the kiosk session
- Pi shutdown flow requires explicit confirmation or countdown completion and can be cancelled
- brightness behavior after reboot is explicitly tested and documented; if panel persistence is unreliable, the backend restores brightness predictably after service/app startup
- brightness cannot exceed `170/255` through the UI/API
- color/edge validation page renders correctly on the DSI panel
- power/throttle measurements are recorded for the capped brightness range
- host health gate passes with the new display controls installed

## Phase 20: Raspberry Pi 5 Rebuild and Display Performance Validation

**Status:** planned. See [Phase 20 Execution Record](./phase-20-execution.md).

### Goal

Rebuild the control deck on the Raspberry Pi 5 16GB and repeat the infrastructure, platform, deploy, display, touch, and performance validation path without doing new product-code development. This phase exists to rule out Raspberry Pi 2 compatibility and performance limits as the cause of the current Chromium and display-quality concerns, and to verify that the earlier host-preparation and bring-up results are still reproducible with the current scripts.

### Scope

- fresh Raspberry Pi 5 host preparation using the current Phase 1 runbook and scripts
- repeat Phase 9 local platform bring-up on the Pi 5
- deploy the current application using the canonical `scripts/deploy.sh`
- migrate the Phase 6 protoboard GPIO wiring to the Pi 5 40-pin header using the same BCM map
- bring up the Waveshare DSI display, touch, kiosk, display power, and brightness controls on Pi 5 hardware
- compare display quality, Chromium responsiveness, CPU/memory pressure, thermals, throttling flags, and perceived touch latency against the Raspberry Pi 2 baseline from Phases 18 and 19
- confirm whether the Phase 18/19 display findings remain true, improve, or are Pi 2-specific
- no new feature development unless a Pi 5-only compatibility defect blocks bring-up or validation

### Required phase execution sequence

Run the validation in this order so differences are attributable and the prior phase results are explicitly refreshed:

1. Re-run **Phase 1: Host Preparation and Conservative OS Cleanup** on the Raspberry Pi 5, capturing pre-cleanup and post-cleanup host state.
2. Re-run **Phase 9: Local Platform Bring-Up** on the Raspberry Pi 5, including desktop stack, Chromium kiosk autostart, systemd service installation, and host health snapshot.
3. Re-run **Phase 12: Deployment and Version Tracking** by deploying from the development machine with `scripts/deploy.sh`; do not hand-copy partial code.
4. Re-run the hardware-facing portions of **Phase 8** and **Phase 15** enough to prove the Phase 6 GPIO/protoboard map still drives and observes `JOG`, `KEY_ADC1`, `KEY_ADC2`, `KEY_LED`, and `ADS1115 ALERT/RDY` correctly on the Pi 5.
5. Re-run **Phase 18: Display and Touch Validation** on the Pi 5, including DSI display mode, touch coordinates, I2C device map, HDMI-disabled DDC-only policy, and coexistence with the project I2C bus.
6. Re-run **Phase 19: Display Usability and Power Hardening** on the Pi 5, including brightness cap behavior, display power-off/on behavior, color/edge validation, reboot persistence, and power/throttle benchmark points.
7. Run a focused Chromium/display performance comparison: cold boot to usable kiosk, UI interaction latency, Settings/color-check navigation, live log scroll/rendering, remote-browser interaction, sustained idle for at least 30 minutes, and host health after the sustained run.
8. Record the conclusion before resuming feature phases: Pi 5 accepted as the new deck host, Pi 2 issue ruled in/out, or a specific remaining display/panel/software issue identified.

### Tasks

- prepare the Pi 5 storage, OS image, power supply, network, SSH, and hostname without reusing the Pi 2 host state as evidence
- capture Phase 1 baseline artifacts under `artifacts/host-prep/` on the Pi 5
- install the backend service, graphical stack, kiosk autostart, and keyring suppression using existing scripts
- deploy the current repo to the Pi 5 with `scripts/deploy.sh`
- update or override `PI_TARGET` for the Pi 5 without changing the deploy script's single canonical workflow
- wire the Pi 5 header according to [Phase 20 Pi 5 GPIO schema](../hardware/phase-20-pi5-gpio-schema.md)
- validate `gpiozero` pin factory compatibility on Pi 5; prefer `lgpio` if needed by the OS image, but record the actual setting
- verify `i2c_arm`, project I2C bus, `ADS1115`, DDC bus, DSI touch/panel bus, and `/sys/class/backlight` paths
- confirm whether `video=HDMI-A-1:d` is still required and still preserves DDC/CI access
- compare Chromium mode choices on Pi 5 (`x11`/Xwayland vs native Wayland) using the same UI and font configuration from Phase 19; preserve the better-performing path with evidence
- re-test the display brightness range and artifact threshold rather than assuming the Pi 2 `170/255` cap is still the Pi 5 limit
- run `python3 scripts/pi-deck-host-health.py` at each close point and paste the default text output into the Phase 20 execution record

### Deliverables

- Raspberry Pi 5 running the deployed control deck as the active validation host
- Phase 20 execution record with host-prep, platform, deploy, GPIO, display, touch, and performance evidence
- Pi 5 GPIO schema and wiring checklist for the Phase 6 protoboard map
- comparison table against the Pi 2 Phase 18/19 baseline for display artifacts, Chromium responsiveness, resource use, thermals, and throttling
- explicit decision on whether future phases continue on Pi 5

### Exit criteria

- Pi 5 can boot directly into the kiosk and serve the current application through `pi-deck.service`
- canonical deploy script updates the Pi 5 and increments the visible version
- Phase 6 protoboard wiring functions on the Pi 5 using the documented BCM/physical pin map, or any required compatibility change is documented
- DSI display, touch, backlight, display power control, and color/edge validation are re-tested on Pi 5
- Chromium performance and display quality are judged with captured evidence, not inferred from the Pi 2 results
- earlier infrastructure/preparation phase assumptions are either confirmed current or corrected in the relevant runbooks
- host health gate passes on the Pi 5 after sustained kiosk use

## Phase 21: Display Power Control Circuit

### Goal

Design and validate a hardware circuit that lets the Raspberry Pi switch the Waveshare DSI display's 5V supply on and off under software control, eliminating the inrush-induced Pi shutdown seen in Phases 19 and 20.

### Background

Phases 19 and 20 confirmed that hot-plugging the display's 5V line while the Pi is running causes a shutdown — Pi 5 is worse than Pi 2 (full shutdown vs brown-out reset). Software-only display off (`brightness=0` + `wlr-randr --off`) saves ~1.9 W but leaves the display powered. A controlled high-side switch on the display's 5V rail solves both problems: true display power-off and safe inrush-limited reconnection without exposing the Pi's own 5V rail to the transient.

### Scope

- PNP high-side switch (`S8550`) controlled by a GPIO-driven NPN stage (`2N3904`)
- RC soft-start network on the PNP base to limit inrush on turn-on
- bulk output capacitor for load transient smoothing
- GPIO24 as the display power control output
- protoboard prototype; no new PCB in this phase
- backend GPIO control and API endpoint for display power on/off
- integration with the existing `DisplayService` power methods

### Tasks

- assemble the Phase 21 display power circuit on the existing Phase 6 protoboard
- wire GPIO24 → NPN driver → PNP high-side switch → display 5V+
- verify soft-start: display turns on cleanly with no Pi voltage droop
- verify turn-off: display 5V collapses cleanly without disrupting the Pi
- verify that repeated on/off cycles do not cause Pi instability
- add `GPIO24` to `protoboard_pins.py` as `display_power_en`
- wire `DisplayService.power_on()` and `power_off()` to toggle `GPIO24` in addition to the existing backlight and wlr-randr steps
- expose `POST /api/v1/system/display/on` and `POST /api/v1/system/display/off` if not already present (or extend the existing endpoint)
- run the host health gate after sustained on/off cycling

### Deliverables

- Phase 21 display power circuit assembled on protoboard
- Phase 21 display power schematic added to `docs/hardware/phase-6-protoboard-schematic.md`
- Phase 20 GPIO schema updated with GPIO24
- backend `display_power_en` GPIO wired into `DisplayService`
- Phase 21 execution record with evidence of clean switching

### Exit criteria

- display can be powered on and off via API without causing a Pi reset or shutdown
- soft-start limits inrush: no visible voltage sag on the Pi 5V rail during turn-on
- repeated on/off cycles (≥ 10) complete without Pi instability
- `DisplayService.power_on()` and `power_off()` coordinate backlight, wlr-randr, and `GPIO24` in the correct sequence
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase's execution record

## Phase 22: Documentation Reorganization

### Goal

Reorganize project documentation and repository artifact structure so durable reference material is named, placed, and linked by what it is, while phase-specific history remains isolated to execution records.

### Background

The repository has accumulated a mix of **historical** and **living** documents, plus a mix of **code**, **hardware artifacts**, and **documentation assets** at the top level. Execution records are correctly phase-scoped, but several shared hardware and reference documents still carry phase-based names from when they were first created. The repository also mixes folder organization by technical layer (`frontend/`, `backend/`), by reader purpose (`docs/...`), and by project history (`hardware/.../phase-*`).

This creates two problems:

- readers cannot easily tell whether a document is the current reference or a frozen phase artifact
- the repository structure becomes harder to navigate because folder purpose and source-of-truth boundaries are not stated explicitly

This phase must treat renames and moves as **compatibility-sensitive changes**. Hardware project files, generated artifacts, scripts, and Markdown links may already depend on current paths. A cleanup that breaks `KiCad` project references, fabrication outputs, or existing documentation links would make the repository cleaner in appearance while making it less usable in practice.

The project should follow the same rule already used successfully in code: implementation history may be tracked by phase, but reusable artifacts should be named by purpose.

### Scope

- documentation naming policy for phase records versus living reference documents
- repository organization policy for code, hardware artifacts, and documentation support assets
- renaming shared docs whose current names are phase-scoped but whose role is not
- clarifying the purpose of top-level and major subfolders
- documentation indexes and inbound links for discoverability
- reference updates across the repo so renamed docs remain easy to find

### Tasks

- define and document the naming rule: phase names are for execution/history documents; descriptive names are for living reference documents, runbooks, schemas, BOMs, and shared hardware notes
- define and document the repository-organization rule: code trees are organized by implementation boundary, hardware trees by artifact/board, and docs by reader purpose
- identify documentation files whose names describe the phase that created them rather than the artifact they contain
- rename those files to artifact-based names
- decide and document the role of `hardware/` versus `docs/hardware/`
- decide and document where explanatory images belong versus artifact images generated from hardware work
- add a top-level repository structure section or document that explains what each major folder is for
- add local README/index files where needed so important directories explain themselves in place
- inventory rename/move risks before changing paths, especially for `KiCad` projects, generated outputs, scripts, and Markdown references
- update any affected `KiCad` project references, helper scripts, generated-file expectations, and document links as part of the same change
- update links and textual references throughout the repo so all renamed docs resolve cleanly
- add a `docs/hardware/README.md` or equivalent index that lists the hardware reference documents and what each one covers
- ensure every important document has at least one obvious inbound link from the plan, README, an index page, or the relevant execution record
- preserve provenance inside document content where useful, without using the filename itself as the historical record
- confirm that later phases reference the renamed living docs rather than phase-scoped filenames
- verify after each rename/move that `KiCad` projects still open correctly and that existing Markdown references still resolve

### Deliverables

- documented repository rule for documentation naming and organization
- documented repository structure guide describing the purpose of each major folder
- renamed living reference documents using artifact-based names
- hardware/documentation index pages that make the structure navigable
- updated links across README, plan, execution records, and reference docs

### Exit criteria

- readers can distinguish phase history from current reference material by document name alone
- shared docs are named by artifact or purpose, not by the phase that first created them
- the role of `backend/`, `frontend/`, `hardware/`, `docs/`, and other major folders is explicitly documented
- important docs are reachable through obvious links rather than requiring directory browsing
- later phases can continue adding documentation without reintroducing phase-scoped names for living artifacts
- no repository cleanup in this phase leaves broken `KiCad` references, broken scripts, or broken Markdown links behind

## Phase 23: Physical Display and Pi Power Button

### Goal

Define and validate a physical local power-control path so an operator can turn the deck display on and off from hardware, and determine a practical strategy for physically waking or powering on the Raspberry Pi.

### Background

The project already has software-managed display power control, but there is still no dedicated physical hardware button for local display on/off. That leaves a gap in the control deck as a physical appliance: if the Pi is shut down, software UI controls are unavailable, and a local operator still needs a practical way to bring the system back.

Raspberry Pi model differences matter here:

- Raspberry Pi 5 has a native power-button path
- Raspberry Pi 2 does not provide the same user-facing wake/power-button behavior

This phase therefore cannot assume that one simple wiring approach automatically covers both hosts. It must determine whether the project can support one shared physical-button strategy across both Pi 5 and Pi 2, or whether Pi 2 requires an auxiliary circuit or a documented operational limitation.

The outcome must be explicit, because the integrated controller board (Phase 7) and later installation work depend on knowing what this button is supposed to do electrically and operationally.

### Scope

- local physical button for deck-display on/off
- physical wake / power-on strategy for Raspberry Pi 5
- physical wake / power-on strategy for Raspberry Pi 2, or an explicit decision that a different path is required
- relationship between physical button behavior and software shutdown behavior
- any additional always-on circuitry, latch, supervisor, or header-level wiring needed to support physical wake/power-on

### Tasks

- define the desired user-facing behavior for a physical local power button:
  - display-only toggle
  - Pi shutdown request while running
  - Pi wake / power-on while off
- document the electrical interfaces available on Raspberry Pi 5 for physical wake / power-on integration
- document the electrical interfaces available on Raspberry Pi 2 and determine whether an equivalent physical wake / power-on path exists
- evaluate whether a single hardware button can safely support both display control and Pi wake/power-on, or whether those functions should remain separate
- evaluate candidate solutions for Pi 2 physical start-up if no direct equivalent exists, including whether an auxiliary always-on circuit is required
- define debounce, press-duration, and fail-safe expectations for the physical button path
- verify that the chosen physical-button design does not conflict with existing display-power control circuitry or Raspberry Pi power integrity
- update the integrated-board assumptions so Phase 7 and later hardware work include the chosen button behavior
- document any model-specific limitations clearly if Pi 2 and Pi 5 cannot share the same exact implementation

### Deliverables

- documented physical-button behavior model for display and host power control
- chosen Raspberry Pi 5 wake / power-on integration approach
- chosen Raspberry Pi 2 wake / power-on integration approach, or documented reason it must differ
- defined hardware requirements for the integrated board and harnessing
- execution record with electrical and practical decision rationale

### Exit criteria

- the project has a clear physical-button strategy for local display on/off
- the project has a clear and documented answer for how Pi 5 is physically woken or powered on
- the project has a clear and documented answer for how Pi 2 is physically woken or powered on, or an explicit limitation if exact parity is not practical
- later hardware phases no longer need to guess what the physical local power button is supposed to do
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase’s execution record

## Phase 24: DDC Capability Investigation

### Goal

Use repeatable low-level control and replay to fully characterize how `DDC` can help the system.

### Scope

- input readback
- brightness
- volume
- power-related behavior
- `DDC` timing and reliability

### Note on monitor configuration changes

`DDC` investigation uses the `HDMI` connection as the transport. Supporting two monitors (e.g. the Samsung CJ791 alongside a development display) may require temporary monitor configuration changes — input source settings, display clone/extend mode, or EDID-related workarounds. These changes are investigation-phase workarounds only.

When the custom hardware (Phase 7 integrated board) is installed, `DDC` communication will migrate to direct `I2C` and the `HDMI` connection will no longer be required for control. All monitor configuration changes forced during this phase must be reverted at that point. See [Phase 31](#phase-31-custom-hardware-installation-ddc-migration-and-configuration-revert).

### Tasks

- repeat key monitor workflows while querying `DDC`
- determine which `DDC` reads are stable and useful
- determine which writes are reliable enough to use
- measure how long input changes take to appear over `DDC`
- document `DDC` behavior during source cycling and related workflows
- feed normalized `DDC` status into the control model
- add verification coverage for supported `DDC` reads and writes
- record all monitor configuration changes made during this phase so they can be cleanly reverted in Phase 31

### Deliverables

- validated `DDC` behavior model
- updated DDC notes and usable read/write rules
- log of monitor configuration changes made during investigation

### Exit criteria

- the project knows which `DDC` features are safe to depend on and where `DDC` timing matters
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase’s execution record

## Phase 25: LED Feedback Characterization and Monitor State Model

### Goal

Determine how useful `KEY_LED` is as a control-feedback signal, fully characterise monitor power states from the existing observation bus, and update the UI to reflect those states.

### Scope

- input-change feedback
- idle behavior
- OSD boundary cues
- monitor state detection: **ON / IDLE / OFF / POWERED OFF**
- UI representation of all four monitor states

### Background

Four observable monitor states need to be handled:

- **ON** — monitor active; `KEY_LED` alternates on/off at idle; `KEY_ADC1` and `KEY_ADC2` produce valid JOG signals only on interaction.
- **IDLE** — monitor in power-save / no-signal; `KEY_LED` blink pattern differs from ON; already partially visible in the UI via the live LED indicator.
- **OFF** — monitor soft-powered off via its own power button (standby); DDC may or may not respond; bus signals settle.
- **POWERED OFF** — monitor physically unplugged or hard power cut; no DDC response; characteristic bus fingerprint observed (see below).

#### POWERED OFF bus fingerprint

When the monitor loses power, the observation bus produces a distinctive and **unforgeable** transient:

1. `KEY_ADC1` goes active (reads as pressed) — the monitor’s internal pull-up collapses, leaving the line at 0 V.
2. `KEY_ADC2` sweeps through direction thresholds — the resistor-ladder voltage decays through each threshold as the supply drains.
3. Both buses **stay held in those states indefinitely** — with no power to restore the pull-ups or the ladder reference, neither signal returns to neutral.

This two-part signature (simultaneous transition + indefinite hold) is physically impossible during any valid JOG interaction: real presses are momentary and only one bus changes at a time. A timeout of 2–3 seconds of both buses stuck confirms POWERED OFF with no ambiguity.

Recovery: when the monitor powers back on, pull-ups restore and the resistor ladder re-settles — the transition out of "both stuck" is the POWERED ON confirmation.

#### Active probe for ON vs OFF/IDLE

Send a known JOG command that reliably produces a `KEY_LED` blink. If the LED responds → monitor is ON. No LED response + clean bus → OFF or IDLE (distinguish further by signal levels and DDC if available).

### Tasks

- use recording and replay to correlate `KEY_LED` behavior with repeated monitor actions
- repeat controlled monitor sequences while observing `KEY_LED`
- record blink patterns and timing across all four states
- identify any repeatable LED cues that can be used to gate continuation
- implement passive POWERED OFF detection from simultaneous + persistent bus hold
- implement active probe (JOG → LED response) for ON vs OFF/IDLE discrimination
- determine where LED feedback is useful and where it is too ambiguous
- add verification coverage for LED event detection and timing assumptions
- update the UI to surface monitor state (ON / IDLE / OFF / POWERED OFF) — IDLE is already partially represented via the live LED indicator

### Deliverables

- validated `LED` behavior model across all four monitor states
- software monitor-state detector driven from the existing observation bus
- UI updated to represent ON / IDLE / OFF / POWERED OFF
- guidance on where `wait_led` events are meaningful

### Exit criteria

- the project knows when LED feedback can be trusted as part of sequence execution
- monitor state is reliably detected and surfaced in the UI
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase’s execution record

## Phase 26: State Investigation and Sequence Cleanup

### Goal

Turn raw recordings and low-level investigation into reusable, cleaner monitor workflows.

### Scope

- cleanup of recorded sequences
- timing refinement
- start-state assumptions
- end-state verification

### Tasks

- inspect raw recordings
- edit and normalize their structure
- refine timing between actions
- annotate or encode start and end assumptions
- verify sequence success against `DDC` and `LED` where possible
- rename recordings into meaningful workflow names
- add repeatable validation steps for promoted sequence files

### Deliverables

- cleaned and named reusable sequence files
- evidence of which sequences are production-worthy

### Exit criteria

- important monitor workflows are represented by stable, reusable, named sequence files
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase’s execution record

## Phase 27: Deck Settings, Block Editor, and Recording Visualisation

### Goal

Introduce system-wide deck configuration and give operators a visual way to inspect and edit recordings without touching raw JSON. Settings live at the system level — not inside the recording workspace — so they are available to any feature that executes JOG sequences, including productized monitor features in later phases.

### Background

Phase 16 validated that the Samsung CJ791 requires a minimum hold duration of **50 ms** and a minimum inter-event gap of **50 ms** for reliable input registration. Values below 40 ms caused intermittent failures. These thresholds must be stored as system-wide configuration so that every sequence execution path (manual playback, productized feature buttons, future DDC sequences) reads the same values.

### Scope

- system-wide deck settings (minimum click duration, default LED wait timeout) stored in a writable local config and exposed through the main Settings page
- block-mode visual editor as an alternative to the raw text editor in the recording workspace
- both editors round-trip through the canonical V1 JSON format without data loss

### Tasks

**Deck settings (system-wide)**

- add a `DeckSettings` model: `min_click_ms` (default 50), `led_timeout_ms` (default 1800)
- persist settings in a writable local config file (alongside recordings dir or a dedicated path)
- expose via REST: `GET /api/v1/settings` and `PUT /api/v1/settings`
- add a **Settings** section to the existing Settings page (Phase 13 layout) — same location as brightness — not inside the recording workspace
- the sequence runner reads `min_click_ms` and `led_timeout_ms` from the live settings on every playback; no hardcoded thresholds in the runner
- add tests for settings persistence, defaults, and validation (e.g. `min_click_ms` must be ≥ 1)

**Block-mode editor**

- implement a block-mode view that renders a recording’s event sequence as a vertical list of typed blocks; each block shows its type and editable parameters
- support the following block types, mapping directly to V1 events:
  - `Click` — a `hold` immediately followed by a `release` within `min_click_ms`; displayed as a single operator-friendly unit; expands to `hold` + `delay(min_click_ms)` + `release` on save if no explicit delay is present in the source
  - `Hold` — a `hold` event for a JOG direction
  - `Release` — a `release` event for a JOG direction
  - `Wait for time` — a `delay` event with an editable duration
  - `Wait for LED` — a `wait_led` or blocking `led` event with editable match condition, poll interval, and timeout
- text mode and block mode are toggleable within the recording detail pane; existing text mode is unchanged
- block edits produce valid V1 JSON on save, identical to what text mode would produce for the same sequence
- parallel blocks are out of scope — no parallel commands exist in the current event model; defer if DDC introduces them
- add tests for block-to-JSON round-trip fidelity and `Click` expansion correctness

### Deliverables

- system Settings page section: minimum click time (ms), default LED timeout (ms), persisted globally
- block-mode editor with typed blocks and inline parameter editing
- text/block mode toggle in the recording workspace detail pane

### Exit criteria

- `min_click_ms` and `led_timeout_ms` are readable and writable through the Settings page and the REST API
- the sequence runner uses the live settings values on every playback; changing a setting takes effect on the next play without restarting the service
- sequences can be inspected and edited in block mode without touching raw JSON
- text mode and block mode produce identical V1 JSON for the same sequence
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase’s execution record

## Phase 28: Productized Monitor Features

### Goal

Turn validated monitor workflows into real user-facing features. Productized features are backed by recordings from the Phase 16 library: a named feature slot (PIP, input source, etc.) is assigned a recording, and pressing the feature button runs that recording using the global deck settings from Phase 27.

### Background

The recording subsystem (Phase 16) and the deck settings (Phase 27) together provide the full execution stack for monitor control. Phase 28 exposes that stack as operator-friendly feature buttons rather than raw JOG commands or manual recording playback. Features such as enabling PIP or switching input source are sequences of JOG interactions that have already been captured and validated as recordings — Phase 28 promotes them to named, always-accessible UI controls.

### Scope

- assigned recordings: a recording from the library can be assigned to a named feature slot
- feature slots: input switching, PIP, and related OSD-driven monitor features
- feature buttons in the main UI that run the assigned recording via the sequence runner
- `DDC` mode and `Blind` mode support where applicable

### Tasks

- define a `FeatureSlot` model: a named slot (e.g. `pip_enable`, `pip_disable`, `input_hdmi`, `input_dp`) with an optional assigned recording ID
- persist slot assignments via REST: `GET /api/v1/features` and `PUT /api/v1/features/{slot}`
- add feature slot assignment UI to the recording workspace: each recording can be assigned to a slot from its detail view
- add a feature panel to the main UI: one button per assigned slot; pressing it runs the assigned recording using the live deck settings from Phase 27; unassigned slots show as inactive
- implement source switching in `DDC` mode and `Blind` mode where DDC commands exist; fall back to recording-backed blind mode otherwise
- expose proper error handling and failure states (recording not found, playback busy, sequence error)
- preserve access to the raw JOG controller behind a manual-control entry point
- add integration tests for slot assignment, recording execution via slot, and unassigned-slot behaviour
- evolve the UI from raw JOG-only control into a richer named-feature control surface

### Deliverables

- feature slot assignment per recording
- named feature buttons in the main UI backed by recordings
- user-facing monitor features (PIP, input switching) that run without raw JOG interaction

### Exit criteria

- operators can assign a recording to a named feature slot and run it from the main UI with a single button press
- feature execution uses the global deck settings (`min_click_ms`, `led_timeout_ms`) from Phase 27
- the deck supports the intended monitor-control feature set beyond raw JOG commands
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase’s execution record

## Phase 29: Dashboard Data-Source Spike

### Goal

Decide how dashboard data will be sourced before widget implementation expands.

### Scope

- boot-time time synchronization
- weather provider choice
- location strategy
- local vs external data boundaries

### Tasks

- determine how the host gets correct time after boot
- determine whether time sync is OS-level only or needs application checks
- choose a weather provider strategy
- decide how location is determined without relying on typed settings
- document which widgets depend on local-only data and which need external services

### Deliverables

- dashboard data-source decisions
- time-sync strategy
- weather/location strategy

### Exit criteria

- the project knows how dashboard data will be sourced before deeper widget work begins
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase’s execution record

## Phase 30: Dashboard Widgets

### Goal

Implement the dashboard side of the product using the data-source decisions from the previous phase.

### Scope

- clock
- calendar and appointments
- notes
- host performance
- optional weather

### Tasks

- implement the frontend panels
- implement backend data providers where needed
- keep widgets architecturally separate from one another
- ensure widgets do not interfere with monitor control
- keep the layout responsive while optimizing for `1280×800`
- add frontend and backend tests for implemented widget behavior where practical

### Deliverables

- functional dashboard widgets using live/local data where possible

### Exit criteria

- the dashboard is useful and stable without compromising the monitor-control surface
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase’s execution record

## Phase 31: Custom Hardware Installation, DDC Migration, and Configuration Revert

### Goal

Install the Phase 7 integrated controller board, migrate `DDC` communication from `HDMI` to direct `I2C`, and revert all monitor configuration changes that were introduced as workarounds during Phase 24.

### Background

Phase 24 uses the `HDMI` connection as the `DDC` transport, which may require temporary monitor configuration changes (input source, display mode, EDID workarounds) to support investigation with two monitors. When the custom hardware is installed, the `I2C` bus on the controller board provides a direct `DDC/CI` path to the monitor — the `HDMI` connection is no longer needed for control. This phase removes all Phase 24 workarounds and migrates the software stack to the final hardware configuration.

This phase also incorporates the deferred GPIO and software migration from the Phase 6 protoboard to the Phase 7 integrated board (previously tracked under [Deferred integrated-board GPIO and software migration](#deferred-integrated-board-gpio-and-software-migration)).

### Scope

- physical installation of the Phase 7 integrated controller board
- GPIO remapping from Phase 6 protoboard pinout to Phase 7 integrated board pinout
- migration of `DDC` transport from `HDMI` to direct `I2C` via the controller board
- revert all monitor configuration changes logged during Phase 24
- re-validation of all features against the final hardware configuration

### Tasks

- install Phase 7 integrated controller board and validate power, GPIO, and I2C connectivity
- remap all GPIO assignments from the Phase 6 baseline to the Phase 7 pinout
- adapt and re-validate software, tests, and automation that assumed Phase 6 pins
- migrate the `DDC` service from `HDMI`-based transport to direct `I2C` on the controller board
- verify that all `DDC` features validated in Phase 24 function correctly over `I2C`
- revert monitor configuration changes recorded during Phase 24 (input source, display mode, EDID workarounds)
- confirm the `HDMI` connection is no longer required for `DDC` control
- update operational docs and runbooks that reference Phase 6 BCM GPIO numbers or HDMI DDC paths
- run full regression across JOG, LED observation, DDC, and productized features on final hardware

### Deliverables

- system running on Phase 7 hardware with no protoboard dependencies
- `DDC` communicating over `I2C` without `HDMI`
- monitor returned to its pre-investigation configuration
- updated GPIO map and software references throughout

### Exit criteria

- Phase 7 integrated board is the sole hardware interface; Phase 6 protoboard is retired
- `DDC` over `I2C` passes the same capability checks as Phase 24 `HDMI` DDC
- monitor configuration is clean — no Phase 24 workarounds remain
- all productized features from Phase 27 pass regression on final hardware
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase's execution record

## Phase 32: Stabilization

### Goal

Harden the system for regular use.

### Scope

- repeated workflow testing
- failure handling
- reboot and recovery behavior
- polish and constraints documentation

### Tasks

- test common workflows repeatedly across monitor power cycles
- validate recovery after failed navigation or missing `DDC`
- validate recovery when only `LED` feedback is available
- validate that `Blind` mode remains usable when `DDC` is missing
- validate sequence abort behavior
- document known limitations and unsafe operating conditions
- refine the API and runtime boundaries based on real usage
- run end-to-end and endurance testing before treating the system as ready for regular use

### Deliverables

- stable daily-use control deck
- documented limitations and recovery behavior

### Exit criteria

- the system is stable enough for regular daily use
- satisfy the [Host health gate](#host-health-gate-feature-phases-1032) in this phase’s execution record

## Later Extensions

- add a physical volume knob to the control deck and map it to monitor volume over `DDC`
- define how physical volume-knob movement is synchronized with local and remote UI state

## Future Investigations

- determine whether the deck display power-off action can also place the monitor into standby or power-off state
- test both `DDC` power control and `JOG`-driven OSD power workflows for that behavior
- verify whether monitor power-off or standby preserves power to attached `USB` and `Thunderbolt` devices before adopting this behavior
- evaluate whether a low-power dedicated device, such as a Raspberry Pi Zero 2 W, could be attached there purely for monitor communication
- evaluate `SSE` (`Server-Sent Events`) as an alternative to the current WebSocket event stream for one-way UI notifications, and measure whether it improves Chromium performance or stability on the Raspberry Pi deck host before considering any transport change

### Frontend build output location

Currently `frontend/` builds into `backend/src/pi_deck/static/`, placing Vite output inside the Python package source tree. This mixes frontend build artifacts with Python package contents. Since the project uses an editable install and rsync-based deploy rather than a real `pip install`, the "bundle with the package" benefit does not apply.

A cleaner structure would emit the build to a dedicated directory outside `src/` (e.g. `backend/dist/` or a repo-root `dist/`) and configure FastAPI to locate it via an env var or repo-relative path. This would require coordinated changes to `vite.config.ts`, `backend/src/pi_deck/api/app.py`, and `scripts/deploy.sh`.

Worth addressing before significant UI expansion (Phase 13 onward) adds more build output assumptions on top of the current layout.

### Documentation reorganization

This concern is now tracked explicitly as [Phase 22: Documentation Reorganization](#phase-22-documentation-reorganization).

The key rule is:

- phase names belong to execution/history records
- living reference documents should be named by artifact or purpose

That phase should run before later documentation growth compounds misleading filenames or weak navigation.

### CI/CD and update strategy

The current deploy model (`scripts/deploy.sh`: build → rsync → restart → reload) is intentional for Phase 12 but has known limitations as the project matures:

- **No artifact verification** — the deploy script does not hash or sign the transferred files; a failed rsync mid-transfer leaves the Pi in a partially updated state
- **No rollback** — there is no previous-version snapshot or rollback path if a deploy introduces a regression; the deploy counter only goes forward
- **No staging environment** — code goes directly from the dev machine to the production kiosk with no intermediate validation
- **Chromium reload is best-effort** — xdotool is not installed by default; the fallback kill-and-relaunch approach depends on display environment variables that may not be available over SSH
- **Single deploy target** — the script is hard-coded to one Pi; deploying to additional decks would require scripting around `PI_TARGET`

When the project reaches a more stable feature state, consider:

- a lightweight artifact bundle (tarball or OCI image) with a checksum so the Pi can verify before applying
- a `deploy --dry-run` mode and a `rollback` command that reverts to the previous counter-tagged snapshot
- a GitHub Actions or self-hosted CI job that builds the frontend, runs backend and frontend tests, and produces a release artifact on each merge to `main`
- replacing the rsync+restart pattern with a proper package release (`pip install pi-deck==x.y.z`) from a private or local PyPI index, so the Pi can always reconstruct a known good state
- `xdotool` added to the Pi's base image so Chromium F5 reload is always available without the kill-and-relaunch fallback

## Milestones

- milestone 1: approved observation circuit design with schematic and BOM
- milestone 2: approved analog drive circuit design with schematic and BOM
- milestone 3: approved final-system `HDMI` / `DDC` communication direction
- milestone 4: validated discrete-component protoboard implementation that unblocks software production and test
- milestone 5: approved integrated controller board design with GPIO map, PCB layout, and manufacturing-ready documentation
- milestone 6: confirmed electrical emulation of all `JOG` actions
- milestone 7: confirmed `LED` behavior model for target workflows
- milestone 8: confirmed `DDC` behavior model for target workflows
- milestone 9: working Raspberry Pi kiosk host with supervised app startup
- milestone 10: working recording and replay subsystem
- milestone 11: working local API for primitive and scripted actions
- milestone 12: working low-level `JOG` controller UI
- milestone 13: productized monitor-control features

## Immediate Next Steps

- begin Phase 20: Raspberry Pi 5 Rebuild and Display Performance Validation
- investigate the intermittent `KEY_ADC2` observation-stall defect before treating long-running recording/replay capture as trustworthy
- keep `pi_deck.hardware` as the only GPIO/`DDC` touchpoint per [Code Guidelines](../development/code-guidelines.md)
- update the `README.md` status section as implementation milestones are completed, and remove that section once the repository is no longer primarily in planning or scaffolding state
