# Requirements

## Purpose

This document defines the initial requirements for `samsung-jog-api`. It is a project-level statement of what the system needs to do, what constraints it operates under, and what is explicitly out of scope for early implementation.

## Functional requirements

- The system must run as a dedicated local appliance on a Raspberry Pi-based control deck.
- The system must present a touch-first local user interface for monitor control.
- The system must emulate the Samsung `CJ791` front-panel `JOG` control electrically.
- The system must support directional actions equivalent to `up`, `down`, `left`, and `right`.
- The system must support center press behavior equivalent to `enter`.
- The system should preserve use of the original front-panel `JOG` board when practical.
- The system must observe the front-panel `LED` state as a feedback input.
- The system must expose local software control through a REST API.
- The API must provide high-level actions in addition to raw low-level button primitives.
- The system should support scripted navigation sequences for common OSD workflows.
- The system should read monitor state through DDC/CI whenever reliable and available.
- The system should use front-panel `LED` behavior as an additional confirmation signal for monitor-state changes and OSD workflows.
- The system should provide direct software control for features that already work over DDC, such as brightness and power state.
- The system should provide enough state to support a local touch-screen UI.
- The system must model input switching as source cycling rather than assuming direct selection is available.
- The system must support a `DDC`-aware operating mode where current input state is read and used to terminate source-cycling and related workflows.
- The system must support a `manual` operating mode for blind workflows when `DDC` readback is unavailable or unreliable.
- In `manual` mode, the UI must let the user specify current input and desired input so the controller can calculate how far to cycle.
- The device must auto-start the application stack on boot.
- The device must recover automatically after process crashes or system reboots.
- The device should not require a keyboard for normal operation.
- The frontend and backend must communicate locally over `localhost`.

## Non-functional requirements

- The system must prioritize repeatable behavior over broad feature count.
- The system must behave like an always-on kiosk appliance.
- The system should operate locally without dependence on cloud services.
- The system should be understandable and maintainable by a single developer.
- The system should preserve a clear separation between hardware control, monitor-state readback, API behavior, and UI logic.
- The system should make hardware assumptions explicit and versioned.
- The system should record observed behavior with enough detail to reproduce measurements later.
- The system should degrade gracefully when external APIs or DDC readback are unavailable.
- The software stack should remain lightweight enough for Raspberry Pi 2 B-class hardware.

## Constraints

- The target monitor is currently the Samsung `LC34J791WTNXZA / CJ791`.
- The intended host platform is currently a Raspberry Pi 2 B with `1 GB` RAM.
- The monitor does not appear to expose full input switching reliably through `DDC/CI` alone.
- The front-panel control path is analog, not purely digital.
- Hardware modification is expected and accepted.
- The repository may need to carry both design-time notes and implementation-time code for some period.

## Assumptions

- The monitor decodes front-panel actions by measuring analog thresholds on `KEY_ADC1` and `KEY_ADC2`.
- Reproducing the original resistance values closely enough will allow the monitor to interpret emulated actions as native `JOG` input.
- DDC/CI remains useful as a feedback and telemetry channel even where it is incomplete as a control channel.
- Input changes are reached by cycling through sources rather than reliably selecting a named input directly.
- The front-panel `LED` exposes observable behavior that can help confirm state changes such as input switching, idle state, and some menu boundary conditions.
- Common user goals can be represented as a combination of low-level button actions, `DDC` readback, and `LED`-assisted feedback.
- When `DDC` is unavailable, the user can still drive blind workflows if the system is told the current and desired input state.

## Out of scope for initial implementation

- support for unrelated monitor models without confirmed measurements
- remote internet-facing control
- manufacturer-safe or warranty-safe installation
- a generalized monitor automation framework
- complete elimination of blind timing in every workflow
- Bluetooth device integration
- ESP32 or microcontroller companion work
- mobile applications

## Open requirements questions

- What latency is acceptable between API request and monitor-visible action
- What level of hardware isolation is required to safely share the original `JOG` board and an inline controller
- Whether the first implementation should use fixed resistor switching, digital potentiometers, or another analog method
- How the `KED_LED` line behaves electrically and how reliably it can be sampled by the controller
- Whether the UI should run in Chromium kiosk mode or a more native runtime
- Whether a read-only root filesystem is worth the operational complexity for the first deployment
