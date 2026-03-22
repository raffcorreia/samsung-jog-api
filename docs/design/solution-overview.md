# Solution Overview

## Summary

The proposed solution combines an inline hardware controller with a Raspberry Pi-based local kiosk that treats the monitor as a controllable device rather than a passive display.

## Problem statement

The Samsung `CJ791` exposes useful DDC/CI functions, but it does not appear to provide a complete software control surface for the actions needed in this project. In particular, the monitor's rear-mounted `JOG` can navigate OSD paths and trigger behaviors that are not reliably available over standard DDC commands on this unit, but it is inconvenient to use repeatedly.

## Proposed solution

The solution has four major parts:

- an inline hardware module attached to the `JOG` harness
- a low-level control layer that can reproduce `JOG` electrical states
- a feedback path that combines `DDC` readback with front-panel `LED` observation
- a local REST API that exposes high-level monitor actions
- a local touch UI running on a Raspberry Pi in kiosk mode and using the same API

## Design principles

- Prefer native monitor behavior over unsupported shortcuts.
- Use DDC/CI where it is reliable, but do not force it to cover unsupported control paths.
- Treat front-panel `LED` behavior as a first-class feedback signal when it reveals monitor state changes that software APIs do not.
- Keep the low-level electrical interface separate from high-level monitor semantics.
- Keep frontend interaction simple and centralize monitor logic in the backend.
- Preserve the original front-panel controls when feasible.
- Record uncertainty explicitly and validate assumptions against measurements.
- Design the host device like an appliance: always-on, touch-only, and self-recovering.

## System context

Conceptually, the system looks like this:

`Touch UI on Raspberry Pi -> local backend service -> JOG emulator + DDC adapter -> Samsung CJ791`

and where needed:

`local backend service -> external APIs`

The API layer expresses actions like `switch-input`, `open-menu`, or `set-brightness`. Internally, those actions may be implemented by one of three paths:

- direct `DDC` command
- direct `JOG` sequence
- hybrid sequence using `JOG` for navigation with `DDC` and `LED` verification

For input selection specifically, the system should not assume a reliable direct `go to source X` operation. The practical model is source cycling:

- `Thunderbolt -> HDMI -> DisplayPort -> Thunderbolt -> ...`

That means current-state knowledge is what tells the controller when to stop. When `DDC` is working, the controller can cycle and verify. When `DDC` is not available, the workflow becomes user-assisted and blind.

There is also a physical transport constraint around `DDC`: if the control deck occupies the monitor's `HDMI` path just to gain `DDC` access, the monitor effectively loses one of its usable inputs. The design therefore needs custom interface hardware that preserves practical `HDMI` input use while still allowing the deck to communicate with the monitor over `DDC`.

The frontend should stay thin. It renders state, sends user actions, and avoids owning complex monitor workflow logic.

## Operating modes

The system should explicitly support two source-control modes:

- `DDC` mode: the backend reads current input state and can safely perform source-cycling, `PIP` changes, and related workflows while knowing when to stop
- `manual` mode: the backend cannot trust `DDC`, so the UI asks for `from` and `to` inputs and the backend performs the required blind cycling sequence

This mode split should be visible in the UI. If `DDC` state is present, the user can ask for a target state directly. If `DDC` state is not present, the UI should switch to a `from -> to` interaction model instead of pretending direct selection is possible.

## Hardware concept

The inline controller sits between the original front control board and the monitor main board. Its responsibilities are expected to include:

- reproducing the measured resistance-to-ground values for directional and center actions
- deciding when the original `JOG` board or the controller owns the line
- preventing unsafe contention between physical and emulated input paths
- observing the front `LED` line so higher layers can correlate visible behavior with control actions
- participating in or coordinating with whatever custom `HDMI` and `DDC` interface hardware is required to preserve the monitor's usable inputs

## Software concept

The software stack will likely need these logical modules:

- hardware driver abstraction for `JOG` line control
- `LED` observation or sampling abstraction
- DDC service abstraction for monitor readback and supported direct controls
- monitor behavior layer that translates high-level intents into action sequences
- mode-selection logic for `DDC`-aware versus blind workflows
- REST API layer
- local UI layer optimized for touch interaction
- kiosk/runtime layer responsible for boot behavior and process supervision

## Host platform concept

The intended host is a dedicated Raspberry Pi-based control deck:

This is the current intended implementation platform, not a product-level requirement.

- Raspberry Pi `2 B` with `1 GB` RAM
- `5"` to `7"` touch display, ideally using a non-`HDMI` connection so the `HDMI` port remains available for monitor and `DDC` workflows, and capacitive touch
- Raspberry Pi OS Lite or another minimal Linux base
- local-only frontend and backend communication over `localhost`

The control deck may later include additional physical controls beyond touch input. One confirmed future candidate is a physical volume knob that adjusts monitor volume through `DDC`, since volume control has already been observed to work over `VCP 0x62`.

Another future investigation is whether the deck's own power-off action can also send a monitor power-off or standby command, either through `DDC` or through a `JOG` workflow, without interrupting power delivery to attached `USB` or `Thunderbolt` devices.

Initial operating characteristics:

- auto-start on boot
- fullscreen kiosk behavior
- automatic restart after failure
- no keyboard required for normal use
- minimal background services

## Safety model

This project is not warranty-safe. The design should still aim to be electrically conservative:

- avoid unsafe drive conditions on analog key lines
- minimize the chance of controller and original board contention
- default to an idle state that does not look like a pressed button
- make recovery paths explicit when the monitor and software state diverge

Operationally, the kiosk should also aim to be conservative:

- avoid exposing unnecessary local services
- store secrets locally and minimally
- tolerate network and API outages without trapping the user in a broken state

## Initial design decisions to validate

- whether the original `JOG` board remains permanently inline or is switched out during emulation
- whether resistor selection is done with analog switches, relays, transistor networks, digital potentiometers, or a mixed design
- how to preserve practical use of the monitor's `HDMI` input while still giving the control deck a reliable `DDC` path
- how much OSD state can be inferred from DDC versus timing and workflow assumptions
- how much monitor state can be inferred from front-panel `LED` behavior, and how deterministic those cues are
- whether a simple stateless action API is enough or a richer monitor state machine is needed
- how the `manual` mode UX should represent `from` and `to` state for source and `PIP` workflows
- whether the first kiosk runtime should be browser-based or use a native UI stack
- whether read-only root storage is worth adopting in the first release
