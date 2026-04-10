# Solution Overview

## Summary

The proposed solution is a Raspberry Pi-based local control deck for the Samsung `CJ791` monitor. It combines:

- a touch-first web UI
- a local backend service
- custom interface hardware for `JOG` emulation and signal observation
- `DDC/CI` readback and supported direct controls
- file-based sequence recording and replay

The design is intentionally built around the monitor behavior that has already been measured and verified:

- `JOG` input is required for OSD-driven workflows
- `DDC/CI` is useful for feedback and selected direct controls, but not for full OSD control
- front-panel `LED` behavior may provide additional feedback cues

## Design goals

- preserve the original monitor `JOG` behavior and hardware usability
- provide a usable touch controller for daily monitor control
- support LAN access through the same UI used on the deck
- allow low-level control, recording, replay, and later feature productization from recorded sequences
- keep the runtime simple enough for Raspberry Pi `2 B` hardware
- document the hardware design deeply enough to support PCB and circuit implementation

## Target implementation platform

This design phase is explicitly targeting the following implementation platform:

- Raspberry Pi `2 B v1.1`
- `1024x600` capacitive touch display
- Raspberry Pi OS Lite or equivalent terminal-only base image
- Chromium kiosk runtime
- `systemd` process supervision

This is an implementation choice for this project phase, not a product-level requirement.

## System model

Conceptually, the system looks like this:

`Touch UI / LAN UI -> backend API and websocket service -> monitor control services -> hardware interface + DDC adapter -> Samsung CJ791`

The system has four major technical areas:

- UI and application control
- monitor-control logic
- custom hardware interface
- host platform and kiosk runtime

## Functional control model

### 1. JOG-driven monitor control

The monitor's OSD-driven features are controlled through `JOG` behavior, not by direct software commands.

This means the system must support:

- low-level directional and center actions
- press and hold timing
- sequence replay
- sequence recording for later cleanup and reuse

This also means higher-level monitor features such as input switching and `PiP` configuration must be built on top of measured and verified `JOG` sequences.

### 2. DDC-assisted feedback

`DDC/CI` is used where it has already proven useful:

- current input readback
- brightness control
- volume control
- power-state related investigation
- general monitor readback

Input switching remains a cycling problem, not a direct-selection problem:

- `Thunderbolt -> HDMI -> DisplayPort -> Thunderbolt -> ...`

So `DDC` is mainly used to know when to stop cycling.

### 3. LED-assisted feedback

The front-panel `KEY_LED` line is treated as another feedback source.

It may help:

- confirm input changes
- distinguish idle versus active behavior
- reveal some OSD boundary conditions

The design should capture and expose this information, but should avoid overstating what the LED means before it has been fully characterized.

## Operating modes

The monitor-control model explicitly supports three operating modes:

### JOG mode

Used for raw low-level monitor control.

Characteristics:

- direct `up`, `down`, `left`, `right`, and `center` actions
- press and hold timing
- useful for investigation, recovery, and direct manual low-level operation
- remains available even after higher-level workflows are added

### DDC mode

Used when `DDC` readback is available and trustworthy.

Characteristics:

- current input is known
- source cycling can stop on the correct state
- `PiP` workflows can be simplified using feedback
- UI can expose target-oriented controls

### Blind mode

Used when `DDC` is unavailable, incomplete, or untrusted.

Characteristics:

- the user provides current and desired input state
- workflows assume `OSD closed` as the baseline
- source changes and `PiP` control are blind `JOG`-driven sequences
- UI must expose a `from -> to` workflow rather than pretend direct selection exists

## UI design approach

### One UI, two access patterns

There is only one UI:

- it runs locally on the deck in kiosk mode
- it is also accessible from other devices on the same trusted LAN

There is no separate deck product and remote product. The same screens and workflows are used in both cases.

### UI evolution by phase

The monitor-control UI should evolve in stages:

- early phases: raw `JOG` controller only
- after validated JSON-backed workflows exist: richer monitor features built on those workflows
- later phases: full user-facing `DDC` mode and `Blind` mode controls

This prevents the project from presenting fake higher-level controls before the underlying monitor behavior has actually been proven.

### Display target

The current design target is the `Waveshare 7inch DSI LCD (E)` (`7"`, `1280x800`, capacitive touch, `DSI`).

The UI should remain responsive for other screen sizes, but the layout and interaction density should be optimized for the selected deck display first.

### Screen model

The UI should be organized around these areas:

- main monitor control area
- dashboard area with live/local widgets
- advanced/settings area
- live log area

The advanced/settings area should include:

- recording controls
- replay tools
- sequence management
- theme and preference controls
- status and debugging information that is useful during development and bring-up

### Visual interaction direction

The UI should take inspiration from the Stream Deck style of interaction:

- icon-driven controls
- large, easy-to-press buttons
- quick visual recognition of primary actions

At the same time, the layout should remain flexible rather than forcing every element into identical button tiles.

That means:

- primary monitor controls should be large and easy to hit
- supporting widgets such as clock and calendar do not need to consume the same amount of space as primary controls
- the screen should be used intentionally based on function, not by giving every panel equal weight

### First usable controller

The first usable controller should be a direct `JOG` console:

- `up`
- `down`
- `left`
- `right`
- `center`
- press and hold support on each button
- visible feedback when a command succeeds or fails
- live log output
- recording controls in the advanced/settings area

This first controller is not the end state of the product. It is the first functional control surface from which reusable monitor features can be developed.

In the early phases, this raw `JOG` controller should be the only monitor-control UI exposed.

Only after validated sequence files exist should the UI grow into the richer feature model discussed elsewhere in the design.

Even after higher-level controls are added, the raw `JOG` controller should remain available behind a manual-control entry point for investigation, recovery, and direct low-level use.

## Sequence recording and replay design

### Purpose

Recorded sequences are central to the project.

They allow:

- exploration of unknown OSD workflows
- cleanup and editing after recording
- promotion of validated recordings into named product features
- timing refinement after capture

### Recording source

Recording observes the bus itself, not only commands sent by the app.

That means both:

- app-generated control actions
- physical monitor `JOG` actions

can become part of a recording.

### Sequence abstraction level

Sequences should be stored at the logical action layer, not at the low-level analog bus layer.

So recordings should represent things like:

- `press`
- `delay`
- `wait_led`
- `wait_ddc`

and not expose internal bus wiring details such as `KEY_ADC1` or `KEY_ADC2`.

The runtime is responsible for mapping those logical actions into:

- bus/channel selection
- resistor-state reproduction
- `DDC` readback and interpretation

### Format

The canonical sequence format should be `JSON`.

Reasons:

- ordered arrays preserve event sequence
- easy parsing and validation
- easy file-based storage
- easy editing and later extension

Each recording should include:

- metadata
- ordered events
- start and end state where known
- `DDC` status snapshots or normalized status checks where useful
- `LED` wait events where the next event should not continue until a matching `LED` cue is observed
- `DDC` wait or check events with retry interval and timeout behavior
- optional annotations for later cleanup

Event behavior should support:

- logical press or hold actions
- delays
- `LED`-triggered continuation
- `DDC` status checks and `DDC` wait loops
- configurable polling interval where repeated checks are needed
- timeout-based failure when an expected `LED` or `DDC` state never arrives

If the last event completes without timeout failure, the sequence is considered successful.

A representative shape for the recording model is:

```json
{
  "name": "enable-pip",
  "version": 1,
  "description": "Open OSD and enable PiP from OSD-closed state",
  "start_state": {
    "osd": "closed",
    "mode": "ddc"
  },
  "end_state": {
    "pip": "enabled"
  },
  "events": [
    {
      "type": "press",
      "action": "center",
      "duration_ms": 120
    },
    {
      "type": "delay",
      "duration_ms": 180
    },
    {
      "type": "wait_led",
      "match": {
        "pattern": "blink"
      },
      "poll_interval_ms": 50,
      "timeout_ms": 1500
    },
    {
      "type": "press",
      "action": "left",
      "duration_ms": 100
    },
    {
      "type": "delay",
      "duration_ms": 120
    },
    {
      "type": "wait_ddc",
      "match": {
        "input": "HDMI"
      },
      "poll_interval_ms": 200,
      "timeout_ms": 5000
    }
  ]
}
```

This example is illustrative rather than final code, but it captures the intended abstraction:

- actions remain logical rather than bus-specific
- waits are explicit event types
- timeout semantics are implicit: if a wait times out, the sequence fails

User-created recordings should live in a writable local directory.
Shipped validated sequences should live in the repository and be versioned with the code.

### Productization flow

Expected lifecycle:

1. record a raw sequence
2. inspect and clean it up
3. adjust timing if needed
4. rename it to a meaningful workflow name
5. ship it as part of an implemented feature

Example:

`recording_2026-03-23-21-55-35.json -> cleanup -> enable-pip.json`

## Runtime architecture

### Repository structure

The project should be structured like this:

```text
pi-deck/
  frontend/
  backend/
  docs/
  hardware/
```

### Production process model

Production should use:

- one backend process
- one frontend build artifact
- backend serving the built frontend
- websocket support from the backend

This reduces runtime complexity on Raspberry Pi `2 B`.

### Backend internal layers

Even though production uses a single backend process, the backend code should be layered clearly:

- API layer
- application/service layer
- hardware integration layer
- storage layer

Suggested conceptual structure:

```text
backend/
  api/
  services/
  hardware/
  storage/
  models/
```

Recommended responsibilities:

- `api`: REST endpoints, websocket endpoints, request validation, and response shaping
- `services`: command arbitration, sequence execution, monitor workflow logic, and widget/service orchestration
- `hardware`: `jog_drive`, `jog_observe`, `led_observe`, `ddc`, and `display_power`
- `storage`: recordings, settings, and other local persisted files
- `models`: typed domain objects, validation models, and error types

### Chosen stack

- Backend: `Python`
- Backend framework: `FastAPI`
- Frontend: `React`
- Frontend language: `TypeScript`
- Frontend build tool: `Vite`
- API style: `REST` + `WebSocket`
- Process supervision: `systemd`
- Kiosk browser: `Chromium`

## Sequence runner architecture

Sequence execution should be handled by a dedicated unified sequence runner rather than scattered service logic.

Its responsibilities should include:

- validating a sequence before execution
- enforcing sequence timeout and non-runaway behavior
- rejecting concurrent sequence execution
- supporting immediate manual abort
- reporting step-by-step progress and failure back to the API and UI

If a sequence is already running and another sequence is triggered, the second request should fail immediately.

Manual stop should be immediate abort, with the runner returning the system to a safe idle state where possible.

## Command arbitration architecture

Command arbitration should be split across two layers:

- service layer decides whether a command or sequence is allowed to start
- hardware layer enforces final safety at execution time

This means:

- same-bus overlaps are rejected
- busy-bus conditions return immediate failure
- separate buses may still operate in parallel when explicitly supported

## WebSocket event model

The websocket channel should be used for live system state and activity updates.

Expected event categories:

- button activity
- command accepted or rejected
- bus busy or idle state
- `DDC` status updates
- `LED` events
- recording state
- live log stream

Clock display should remain frontend-local rather than websocket-driven.
Calendar and appointment widgets should start as normal API-driven widgets and only move to push updates later if there is a real need.

## Host platform design

### OS and kiosk model

The host starts from a terminal-only Raspberry Pi OS image.

The design must include:

- conservative OS cleanup
- documentation of every host modification
- repeatable host preparation
- browser auto-start
- cursor hiding
- kiosk fullscreen behavior
- crash recovery

The deck should behave like a dedicated appliance, not like a general workstation.

### Logging model

The design includes three distinct capabilities:

- file logging
- live log streaming to the UI
- recording mode for sequence capture

File logging must be configurable and disableable to avoid unnecessary SD-card wear.

Default retention policy:

- one log file per day
- three months retention

The live log should surface:

- UI actions
- API command activity
- hardware command attempts
- bus state changes where useful
- `DDC` status and errors where useful

Log records should be unified in one file-oriented stream and one live-view stream.

Each log line should include:

- date
- time
- type or category such as `event`, `operational`, `sequence`, or `error`
- message

The file log and live log should represent the same event stream with different output destinations.

## Settings architecture

Settings should remain touch-friendly and avoid typed input wherever possible.

Initial settings should be simple toggles or discrete choices such as:

- theme
- show or hide advanced area
- enable or disable the live log panel
- default operating mode preference
- widget visibility

Future authentication or entitlements may later gate parts of the same UI, but that is not part of the current design.

## Hardware design

### Core principle

The hardware interface must explicitly separate:

- observe bus
- drive bus

These are different responsibilities even if they eventually share board-level circuitry.

### Monitor-side signals

Current known connector:

- `CN1001`

Pinout:

- pin 1: `GND`
- pin 2: `KEY_ADC2`
- pin 3: `KEY_ADC1`
- pin 4: `KEY_LED`
- pin 5: `NC`

Measured observations:

- `KEY_ADC1` idle: `3.3V` to `GND`
- `KEY_ADC2` idle: `3.3V` to `GND`

Measured resistor-to-ground values with the joystick board disconnected:

`KEY_ADC2`

- `Down`: `3.3 kOhm`
- `Right`: `9 kOhm`
- `Up`: `22.6 kOhm`
- `Left`: `32.8 kOhm`

`KEY_ADC1`

- `Center`: `23 kOhm`

### Hardware paths

The hardware architecture should include these logical paths:

- bus observation path for `KEY_ADC1`
- bus observation path for `KEY_ADC2`
- bus drive path for `KEY_ADC1`
- bus drive path for `KEY_ADC2`
- `KEY_LED` observation path
- display power button input path

The first architecture pass should define signal ownership and required host I/O categories, even if final Raspberry Pi pin assignment is completed later in implementation.

### Original JOG preservation

Preserving the original `JOG` is mandatory.

The hardware design must therefore:

- avoid breaking physical `JOG` use
- tolerate physical and software activity on the bus
- detect bus activity for arbitration purposes

### Arbitration behavior

The hardware/software behavior should be:

- if the target bus is idle, execute the command
- if the target bus is busy, fail immediately
- if a second command targets a bus already in use by the app, fail it
- allow simultaneous actions across separate buses
- do not attempt complex recovery if a physical user interferes during an app-driven action

This is intentionally simple and matches the physical reality of the shared control path.

## Dashboard widget architecture

Dashboard widgets should be treated as individual frontend and backend responsibilities rather than one monolithic dashboard subsystem.

That means:

- each widget has its own backend data provider or service when needed
- each widget has its own frontend panel or controller
- widgets should not interfere with one another unnecessarily

Expected early ownership model:

- clock: frontend-local
- calendar and appointments: backend-provided data with normal API fetch
- notes: local application data
- host performance: backend-provided host metrics

## HDMI and DDC transport design

### Current development path

For development, a temporary sacrificial `HDMI` path is acceptable. This is only a development-stage compromise.

### Long-term requirement

Keeping the monitor's `HDMI` input practically available for real devices is important to the final system. The production direction should preserve that input while still providing the control deck with a reliable `DDC` communication path.

### Practical rejected direction

`Thunderbolt` or `USB-C` was considered as a possible `DDC` path, but it is not the current project direction.

Reasoning:

- it is an obvious idea because the monitor already has two `Thunderbolt` / `USB-C` ports, so using one of them for monitor communication would appear simpler than adding dedicated `HDMI`-sharing hardware
- even if the monitor exposes usable `DDC` communication there, the project does not currently have a practical low-cost device that can attach on that path and access it in a useful way
- a simple `USB-C` connector on a cheap microcontroller board does not make that board a real `Thunderbolt` endpoint
- this makes the approach a poor fit for the current hardware plan compared with solving `HDMI` and `DDC` communication directly

### Future investigations

The solution should explicitly leave room for these follow-up investigations:

- `HDMI` sharing or multiplexing hardware for long-term `DDC` access, with priority because preserving usable `HDMI` input is important to the final system
- monitor power/standby behavior that preserves attached `USB` or `Thunderbolt` device power

## Dashboard design

The dashboard is part of the same UI and should show live/local data where possible.

Expected early widgets:

- clock
- calendar view
- appointments list
- notes
- host performance

The design should prefer:

- local OS time once synchronized after boot
- locally available host metrics
- configured location or explicit browser/user input when location is needed

External services should be used only where they actually add value.

Because Raspberry Pi does not retain reliable time across full shutdown by default, the design must include a boot-time time synchronization strategy.

Weather is also a valid future dashboard widget and should be treated as a configurable external data source rather than a hardcoded integration.

## Development phases implied by this design

This solution implies the following development order:

1. documentation and evidence capture
2. host preparation and conservative OS cleanup
3. hardware signal observation and validation
4. hardware design discussion and approval for bus observation circuitry
5. hardware design discussion and approval for analog drive circuitry
6. GPIO assignment after the approved hardware design is known
7. low-level `JOG` console UI
8. recording and replay subsystem
9. state investigation and sequence cleanup workflows
10. dashboard data-source spike for boot-time time synchronization, location strategy, and weather provider selection
11. productized monitor features built on validated sequences
12. expanded dashboard and quality-of-life features

This ordering matters because many higher-level features are blocked on sequence investigation first.

## Remaining implementation-level details

- exact electrical topology chosen during hardware design approval
- exact Raspberry Pi pin mapping after the approved hardware design is known
- exact JSON field names for the recording schema
- exact time synchronization implementation choice on the host
- exact weather provider and location-source strategy
