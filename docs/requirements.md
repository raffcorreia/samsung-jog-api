# Requirements

## Purpose

This document defines the functional and non-functional requirements for `samsung-jog-api` as a local control deck for the Samsung `CJ791` monitor. The system combines a local kiosk UI, a backend control service, analog `JOG` emulation, `DDC/CI` readback, and front-panel `LED` observation.

This is explicitly a hardware-and-software project. The system requires interface hardware that can bridge between the host's control interfaces and the monitor's analog key and signal paths.

The purpose of this document is to define the system's required behavior, constraints, and acceptance expectations. Setup procedures, implementation details, and exploratory notes belong in other documents unless they are necessary to clarify a requirement.

## System overview

The system consists of:

- a local host device with a display and kiosk-style user interface
- a local frontend UI
- a local backend service
- custom hardware that emulates the monitor's front-panel `JOG` inputs through the monitor's analog key lines
- custom hardware that reads the front-panel `LED` signal and other relevant monitor-side signals
- `DDC/CI` integration for monitor-state readback and supported direct controls

The target monitor is currently the Samsung `LC34J791WTNXZA / CJ791`.

## Functional requirements

### Device and UI

- The system must run as a dedicated local appliance on a control deck or equivalent local host device.
- The system must present a touch-first graphical UI on the device display.
- The UI must run in kiosk mode.
- The UI must be accessible both on the device itself and remotely from other clients on the same trusted local network, such as a phone or another computer.
- The UI must be fully implemented in English.
- The UI must support light mode and dark mode.
- The device must auto-start the application stack on boot.
- The device must recover automatically after process crashes or system reboots.
- Normal operation must not require a keyboard.

### Dashboard and widgets

- The UI must display a clock widget.
- The UI must display a month calendar widget with today's date selected and today's appointments list.
- The UI must display a notes widget.
- The UI must display system performance widgets including:
  - throttling status
  - CPU usage
  - memory usage
- The performance area must support a detailed view showing:
  - storage usage
  - network usage

### Monitor control

- The system must control the monitor by electrically reproducing the analog behavior of the front-panel `JOG` controls.
- The system must expose low-level `JOG` actions equivalent to `up`, `down`, `left`, `right`, and center press.
- The system should preserve use of the original front-panel `JOG` board when practical and electrically safe.
- The system must support recording and replaying `JOG` action sequences so repeatable OSD workflows can be captured and reused.
- The system must expose monitor control through a local backend API.
- The API must support both low-level primitives and higher-level monitor actions.

### Input switching and operating modes

- The system must model input switching as source cycling rather than assuming reliable direct selection is available.
- The system must treat current input state as operationally important for source switching.
- The system must support a `DDC` mode in which current input state is read from the monitor and used to terminate source-cycling at the correct target input.
- The system must support a `manual` mode for blind workflows when `DDC` readback is unavailable or unreliable.
- In `manual` mode, the UI must let the user choose the current input and desired input so the controller can calculate how far to cycle.
- In `DDC` mode, the UI should allow simplified target-driven source selection.

### Picture-in-Picture and related monitor workflows

- The system must support enabling and configuring `PiP`.
- The UI must provide a `PiP` action that lets the user choose the left input and right input.
- In `DDC` mode, the system should simplify `PiP` configuration by using available monitor-state feedback.
- In `manual` mode, the system must still allow `PiP` workflows using user-provided starting state and blind `JOG` sequencing.

### DDC and LED feedback

- The system must read monitor state through `DDC/CI` whenever reliable and available.
- The system must provide direct software control for features that already work over `DDC`, such as brightness and power state.
- The system must preserve practical use of the monitor's `HDMI` input while maintaining a `DDC` communication path for the control deck.
- The system must include interface hardware that allows an external device to use the monitor's `HDMI` input while the control deck also communicates with the monitor over `DDC`.
- The system must observe the front-panel `LED` state as a feedback input.
- The system should use front-panel `LED` behavior as an additional confirmation signal for monitor-state changes and OSD workflows.
- The UI should reflect relevant `LED` activity visually.
- `LED` signals may be used as command acknowledgment where their meaning is sufficiently characterized.

### Shared state and synchronization

- The system must maintain a single coherent model of `JOG` control ownership and current monitor interaction state.
- The system must prevent conflicting concurrent `JOG` actions from being executed at the same time.
- The system must support real-time communication between frontend clients and the backend.
- Any action performed in one UI instance must be reflected in all connected UI instances.
- Real-time synchronization must include:
  - button presses
  - state changes
  - monitor interactions

## Hardware requirements

### JOG control path

- The system must simulate the monitor's resistive analog key inputs.
- The system must interface with `KEY_ADC1` and `KEY_ADC2`.
- The system must reproduce the required analog states safely and repeatably.
- The project must define and document the electronic components used in the control path.

### Signal reading

- The system must be able to observe the relevant monitor-side signals needed for control-state awareness.
- The system must read or infer the state of `KEY_ADC1` and `KEY_ADC2` as needed for validation and arbitration.
- The system must detect both:
  - system-generated inputs
  - manual user inputs on the physical control path
- The system must provide a hardware path for shared or multiplexed `HDMI` and `DDC` access so monitor input availability is not unnecessarily reduced by the control deck.

### LED input

- The `KED_LED` signal must be connected as input only.
- The system must not drive the monitor's `LED` output line.

### Physical controls and design outputs

- The system must include a physical button for toggling the display power, while the deck itself remains powered so it can continue controlling the monitor.
- The project must include and document:
  - circuit design
  - component specification and `BOM`
  - PCB design, if applicable

## Software architecture requirements

### Layers

The system must be organized into these logical layers:

- hardware control layer
- backend API layer
- frontend UI layer

### Communication

- The frontend and backend must communicate locally over `localhost`.
- The system must support bidirectional communication between frontend and backend.
- Real-time communication is required.

### Deployment

- Deployment may be manual in the current phase.
- Host-device administration may be performed over the local network using `SSH` with public-key authentication when applicable.
- `CI/CD` is out of scope for the current phase.

## Security requirements

### Current phase

- The system must run with an auto-login kiosk user.
- No password is required for local UI access on the kiosk device itself.
- Remote UI and API access must be limited to the trusted local network.
- External internet exposure is out of scope and should be avoided by default.

### Minimal protection

- The system should support optional token-based authentication for API access.

### Future considerations

- authentication and authorization mechanisms
- secure remote access
- role-based access control
- API security hardening

## Non-functional requirements

### Testing

- Testing is a project requirement.
- Testing must cover:
  - backend logic
  - frontend behavior
  - hardware interaction
- No task should be treated as complete before the relevant test coverage has passed.

### Performance

- The system must monitor host-device performance continuously during normal operation.
- The system must detect and expose throttling conditions.
- The software stack should remain lightweight enough for the initial target host class.

### Reliability

- The system must operate continuously in kiosk mode.
- The UI must recover automatically after crashes or reboot.
- The system should degrade gracefully when `DDC` readback is unavailable.
- The system should remain usable in `manual` mode when `DDC` state is unavailable.

### Usability

- The UI must be touch-friendly.
- The UI must adapt to the target screen size and orientation used by the control deck.
- The UI should make the active operating mode clear to the user.

### Maintainability

- The system should preserve a clear separation between hardware control, monitor-state readback, API behavior, and UI logic.
- Hardware assumptions and measured monitor behavior must be documented explicitly.

## Assumptions

- The monitor decodes front-panel actions by measuring analog thresholds on `KEY_ADC1` and `KEY_ADC2`.
- Reproducing the original resistance values closely enough will allow the monitor to interpret emulated actions as native `JOG` input.
- `DDC/CI` remains useful as a feedback and telemetry channel even where it is incomplete as a control channel.
- Input changes are reached by cycling through sources rather than reliably selecting a named input directly.
- The front-panel `LED` exposes observable behavior that can help confirm state changes such as input switching, idle state, and some menu boundary conditions.
- Common user goals can be represented as a combination of low-level button actions, `DDC` readback, `LED`-assisted feedback, and user-provided current-state information when needed.

## Constraints

- The target monitor is currently the Samsung `LC34J791WTNXZA / CJ791`.
- The monitor does not appear to expose full input switching reliably through `DDC/CI` alone.
- Occupying the monitor's `HDMI` path for `DDC` communication would reduce practical input availability unless compensated by custom interface hardware.
- The front-panel control path is analog, not purely digital.
- Hardware modification is expected and accepted.

## Acceptance criteria

The following criteria should be used to judge whether the initial implementation satisfies the requirements:

- Kiosk recovery: after reboot or a forced frontend crash, the device returns automatically to the kiosk UI without manual intervention.
- Local and remote UI access: the UI is usable on the kiosk itself and from another device on the same local network.
- `JOG` control: the system can perform each low-level `JOG` action and the monitor responds as expected.
- `DDC` mode source switching: from a known source, requesting a target source results in the monitor stopping on the requested source as confirmed by `DDC`.
- `Manual` mode source switching: given a user-selected `from` source and `to` source, the system performs the expected source-cycle sequence without relying on hidden state.
- `PiP` configuration: the system can execute a `PiP` workflow where the user selects left and right inputs.
- `LED` capture: the system can observe and expose `LED` behavior during at least idle state and source switching.
- `HDMI` preservation: the control deck maintains `DDC` communication without permanently sacrificing the monitor's practical `HDMI` input for external devices.
- Arbitration: conflicting simultaneous `JOG` actions are blocked, queued, or rejected consistently.
- Synchronization: actions and state changes in one client are reflected in other connected clients in near real time.
- Testing gate: backend, frontend, and hardware-facing tests pass before a feature is considered complete.

## Out of scope for the current phase

- support for unrelated monitor models without confirmed measurements
- external internet-facing access
- mobile native applications
- `ESP32` or other microcontroller companion work
- a physical volume knob, even though monitor volume control over `DDC` has been confirmed to work
- voice control
- multi-deck scaling
- `CI/CD`
- advanced authentication and authorization
