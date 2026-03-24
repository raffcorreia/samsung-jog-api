# Implementation Plan

## Summary

This document describes the proposed implementation order for `samsung-jog-api`.

The overall strategy is:

1. finish defining and documenting the system
2. prepare the host platform
3. validate and design the custom hardware
4. bring up low-level control end to end
5. add recording and replay so monitor workflows can be investigated repeatably
6. investigate `DDC` and `LED` behavior using those repeatable tools
7. turn validated findings into productized monitor features
8. finish dashboard and stabilization work

This order matters because many higher-level features depend on being able to send low-level `JOG` actions, repeat them, and correlate them with `DDC` and `LED` feedback.

## Testing Strategy

Testing should be introduced alongside implementation, not saved for the end.

The implementation is expected to grow these testing layers over time:

- backend tests for API behavior, arbitration, validation, and service logic
- frontend tests for control feedback, websocket-driven state updates, and key user interactions
- hardware-facing verification tests for low-level `JOG`, `LED`, and `DDC` behavior
- sequence-schema and sequence-runner validation tests
- integration tests for productized monitor workflows

Detailed test design still needs its own document, but no phase should be treated as complete without the relevant tests for that phase.

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
- create a repeatable host-preparation runbook or script where practical
- create a backup image once the host baseline is considered ready

### Deliverables

- prepared Raspberry Pi host
- documented cleanup and preparation procedure
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
- `KEY_LED` validation
- original `JOG` behavior observation

### Tasks

- confirm `CN1001` pinout on the actual target unit
- re-measure idle voltage on `KEY_ADC1` and `KEY_ADC2`
- re-measure resistance-to-ground for each directional action and center press
- capture connector photos, orientation, and wiring notes
- confirm whether measurements differ with the board connected versus disconnected
- characterize the `KEY_LED` signal enough to know whether it is viable as a feedback source
- confirm the physical `JOG` can remain preserved as a hard requirement

### Deliverables

- updated measurement records
- updated hardware notes
- confidence that the current electrical model is accurate enough for controller design

### Exit criteria

- idle and action measurements are confirmed on the target hardware
- no critical contradiction exists between the documented model and the real monitor

## Phase 3: Bus Observation Hardware Design

### Goal

Design and approve the custom hardware needed to observe the monitor-side signals continuously.

### Scope

- observation of `KEY_ADC1`
- observation of `KEY_ADC2`
- observation of `KEY_LED`
- safe interface between monitor-side signals and Raspberry Pi inputs

### Tasks

- define the observation-path requirements
- determine how to sense bus activity safely without disturbing the monitor behavior
- determine how continuous observation will be exposed to software
- document the observation circuitry candidates
- review and approve the observation design
- define how the observation path will be verified during implementation

### Deliverables

- approved observation-path design
- documented rationale and component choices

### Exit criteria

- there is an approved design for continuous safe observation of the relevant monitor-side signals

## Phase 4: Analog Drive Hardware Design

### Goal

Design and approve the custom hardware needed to reproduce the monitor's analog `JOG` behavior.

### Scope

- drive path for `KEY_ADC1`
- drive path for `KEY_ADC2`
- safe interaction with the preserved original `JOG`
- analog resistor-state reproduction

### Tasks

- define the required analog states to reproduce
- evaluate candidate circuit approaches for presenting resistance-to-ground states
- define how the original `JOG` remains preserved
- define how drive and observe paths coexist
- document the analog drive design candidates
- review and approve the analog drive design
- define how the analog drive path will be verified during implementation

### Deliverables

- approved analog drive design
- documented component and topology decisions

### Exit criteria

- there is an approved design for reproducing the required analog states safely and repeatably

## Phase 5: GPIO Assignment and Low-Level Control Prototype

### Goal

Map the approved hardware design onto Raspberry Pi GPIO usage and prove low-level control of the monitor.

### Scope

- GPIO allocation
- low-level hardware control prototype
- validation of basic `JOG` actions

### Tasks

- assign GPIO usage after the approved hardware design is known
- define which pins are input-only, output-only, or otherwise constrained
- build a bench prototype or first working hardware prototype
- verify that each low-level `JOG` action is correctly interpreted by the monitor
- measure press, hold, repeat, and release timing
- record any timing sensitivity or debounce-like behavior
- add hardware-facing verification tests for each low-level `JOG` action

### Deliverables

- GPIO map
- working low-level control prototype
- verified timing baselines for individual `JOG` actions

### Exit criteria

- the system can reliably perform each low-level `JOG` action through the custom hardware

## Phase 6: Local Platform Bring-Up

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
- hide the cursor
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

## Phase 7: Local API

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

## Phase 8: Low-Level JOG Console UI

### Goal

Build the first usable controller UI for direct monitor interaction.

### Scope

- direct `JOG` control
- visible command success/failure
- live log view
- touch-first layout

At this stage, this raw `JOG` controller should be the only monitor-control UI exposed.

### Tasks

- implement `up`, `down`, `left`, `right`, and `center`
- support press and hold interactions
- expose error feedback when a command is rejected
- show live log output
- make the UI usable on the `1024x600` target display
- keep the same UI reachable on the LAN
- add frontend tests for command feedback and websocket-driven UI state

### Deliverables

- first usable controller UI
- touch-driven low-level monitor control from the deck and LAN

### Exit criteria

- a user can directly control the monitor through the deck UI using low-level `JOG` actions
- no unvalidated high-level monitor feature UI is exposed yet

## Phase 9: Recording and Replay Subsystem

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
- support `press`, `delay`, `wait_led`, and `wait_ddc` events
- support polling interval and timeout behavior for wait events
- store recordings in a writable local directory
- place recording and replay tools in the advanced/settings area
- add schema validation tests and sequence-runner tests for timeout, abort, and rejection behavior

### Deliverables

- validated sequence format
- working sequence runner
- recording and replay UI tools

### Exit criteria

- sequences can be recorded, replayed, stopped, and validated reliably

## Phase 10: DDC Capability Investigation

### Goal

Use repeatable low-level control and replay to fully characterize how `DDC` can help the system.

### Scope

- input readback
- brightness
- volume
- power-related behavior
- `DDC` timing and reliability

### Tasks

- repeat key monitor workflows while querying `DDC`
- determine which `DDC` reads are stable and useful
- determine which writes are reliable enough to use
- measure how long input changes take to appear over `DDC`
- document `DDC` behavior during source cycling and related workflows
- feed normalized `DDC` status into the control model
- add verification coverage for supported `DDC` reads and writes

### Deliverables

- validated `DDC` behavior model
- updated DDC notes and usable read/write rules

### Exit criteria

- the project knows which `DDC` features are safe to depend on and where `DDC` timing matters

## Phase 11: LED Feedback Characterization

### Goal

Determine how useful `KEY_LED` is as a control-feedback signal.

### Scope

- input-change feedback
- idle behavior
- OSD boundary cues

### Tasks

- repeat controlled monitor sequences while observing `KEY_LED`
- record blink patterns and timing
- identify any repeatable LED cues that can be used to gate continuation
- determine where LED feedback is useful and where it is too ambiguous
- add verification coverage for `LED` event detection and timing assumptions

### Deliverables

- validated `LED` behavior model
- guidance on where `wait_led` events are meaningful

### Exit criteria

- the project knows when LED feedback can be trusted as part of sequence execution

## Phase 12: State Investigation and Sequence Cleanup

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

## Phase 13: Productized Monitor Features

### Goal

Turn validated monitor workflows into real user-facing features.

### Scope

- input switching
- `PiP`
- related OSD-driven monitor features

### Tasks

- implement source switching in `DDC` mode and `manual` mode
- productize validated `PiP` workflows
- add user-facing controls for named features
- expose proper error handling and failure states
- keep feature behavior aligned with validated sequence assumptions
- evolve the UI from raw `JOG`-only control into the richer `DDC` and `manual` mode control surface
- preserve access to the raw `JOG` controller behind a manual-control entry point
- add integration tests for source switching, `PiP`, and other productized monitor workflows

### Deliverables

- user-facing monitor features built on validated sequences

### Exit criteria

- the deck supports the intended monitor-control feature set beyond raw `JOG` commands

## Phase 14: Dashboard Data-Source Spike

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

## Phase 15: Dashboard Widgets

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
- keep the layout responsive while optimizing for `1024x600`
- add frontend and backend tests for implemented widget behavior where practical

### Deliverables

- functional dashboard widgets using live/local data where possible

### Exit criteria

- the dashboard is useful and stable without compromising the monitor-control surface

## Phase 16: Stabilization

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
- validate that blind manual mode remains usable when `DDC` is missing
- validate sequence abort behavior
- document known limitations and unsafe operating conditions
- refine the API and runtime boundaries based on real usage
- run end-to-end and endurance testing before treating the system as ready for regular use

### Deliverables

- stable daily-use control deck
- documented limitations and recovery behavior

### Exit criteria

- the system is stable enough for regular daily use

## Later Extensions

- add a physical volume knob to the control deck and map it to monitor volume over `DDC`
- define how physical volume-knob movement is synchronized with local and remote UI state

## Future Investigations

- determine whether the deck display power-off action can also place the monitor into standby or power-off state
- test both `DDC` power control and `JOG`-driven OSD power workflows for that behavior
- verify whether monitor power-off or standby preserves power to attached `USB` and `Thunderbolt` devices before adopting this behavior
- investigate how to preserve practical use of the monitor's `HDMI` input while still providing `DDC` communication, beyond the temporary full `HDMI` takeover used during development
- investigate whether one of the monitor's `Thunderbolt` or `USB-C` paths can be used for `DDC` communication instead of a more complex `HDMI` sharing design
- evaluate whether a low-power dedicated device, such as a Raspberry Pi Zero 2 W, could be attached there purely for monitor communication

## Milestones

- milestone 1: confirmed electrical emulation of all `JOG` actions
- milestone 2: confirmed `LED` behavior model for target workflows
- milestone 3: confirmed `DDC` behavior model for target workflows
- milestone 4: approved observation and analog drive hardware design
- milestone 5: working Raspberry Pi kiosk host with supervised app startup
- milestone 6: working recording and replay subsystem
- milestone 7: working local API for primitive and scripted actions
- milestone 8: working low-level `JOG` controller UI
- milestone 9: productized monitor-control features

## Immediate Next Steps

- add photo assets and teardown evidence
- create the first hardware evidence records under `docs/hardware/`
- turn the DDC observations into reproducible command transcripts
- record front-panel `LED` behavior during key monitor actions
- prepare the hardware design review for observation and analog drive circuitry
- decide the initial Raspberry Pi runtime stack for frontend and backend
- create a dedicated testing strategy document before implementation gets deep
- update the `README.md` status section as implementation milestones are completed, and remove that section once the repository is no longer primarily in planning or scaffolding state
