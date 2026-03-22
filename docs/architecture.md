# Architecture

## Summary

`samsung-jog-api` is built around a hybrid control architecture for the Samsung `CJ791` monitor:

- electrically emulate the front-panel `JOG` control path
- expose that behavior through a local REST API
- pair it with a small local touch UI running on a Raspberry Pi control deck
- use DDC/CI and front-panel `LED` observation as complementary feedback and status channels whenever possible

The guiding idea is simple: the monitor already knows how to respond to its own front-panel controls, so the most robust path to full control is to reproduce those same electrical states instead of relying on unsupported software-only shortcuts.

## Why this project exists

The CJ791 is a capable monitor, but it is frustrating to automate.

- It has multiple useful inputs: `HDMI`, `DisplayPort`, and `Thunderbolt / USB-C`
- It has a rear-mounted `JOG` control that can navigate the on-screen display and trigger functions the normal software control path cannot, but it is inconvenient to use repeatedly
- It exposes DDC/CI, which is enough to read some state and control some functions
- But it does not reliably expose the full monitor control surface over DDC alone

In a setup where the monitor acts like part of a desk controller, KVM-like workflow, wall panel, or local touch-screen system, blind software-only control is not enough. It needs a control path that matches what a human can do with the physical `JOG` button.

## Why the destructive part

This project intentionally takes an invasive approach.

The front-panel `JOG` assembly is connected to the monitor main board through a small harness. Rather than using motors, servos, or guessed internal software protocols, the plan is to intercept that harness and electrically reproduce the same button states the monitor already understands.

That is the destructive part:

- the monitor must be opened
- access to the front-panel control board and cable is required
- the cable may need to be cut, extended, or replaced with an inline harness
- a custom controller board can then sit between the original `JOG` board and the monitor

This is destructive in the sense that it modifies the physical monitor wiring and is not a stock, warranty-safe accessory. It is still a pragmatic choice because it targets the monitor's native control mechanism instead of relying on brittle mechanical hacks.

## Control model

The intended control model combines two different paths:

- `JOG` emulation for actions that require authentic front-panel behavior
- `DDC/CI` for readback, health checks, and functions that already work reliably
- front-panel `LED` observation for local visual confirmation of monitor behavior
- a local kiosk device as the dedicated human interface layer

At the API layer, the monitor should look like a normal controllable device rather than a collection of resistor values and timing hacks.

One important constraint is that input changes are not reliably direct-addressable. In practice, the monitor behaves like it exposes `next input` behavior through the OSD path, so source control depends on knowing the current input and cycling until the desired state is reached.

## Planned control method

The hardware plan is to insert a controller inline with the `JOG` harness.

The controller will:

- leave the original front-panel board usable when desired
- reproduce the same resistance-to-ground states for `KEY_ADC1` and `KEY_ADC2`
- observe the front `LED` line and expose its state to higher layers
- expose a local API for high-level actions such as `up`, `down`, `left`, `right`, `enter`, `back`, `open-menu`, and scripted navigation sequences
- support a Raspberry Pi-based local touch UI that calls the same API in kiosk mode

Example higher-level actions:

- switch to the next available input
- cycle from one known input to another known input
- open source list
- navigate to `Picture-by-Picture`
- toggle a known setting
- wake or sleep the monitor

## How DDC fits into the design

DDC/CI is a complementary readback channel, not the only control path.

Instead of using DDC as the entire solution, `samsung-jog-api` uses it where it is strongest:

- confirm current input with `VCP 0x60`
- read or set brightness with `VCP 0x10`
- control standby with `VCP 0xD6`
- verify that the monitor is alive and reachable over the video link
- provide state to the local UI without inferring everything from blind menu timing

The front-panel `LED` is the other important feedback source:

- observe blink patterns during input changes
- detect visible confirmation cues when a menu or scroll path reaches its boundary
- distinguish some idle versus active monitor states even when `DDC` is incomplete or delayed

## Operating modes

Two obvious operating modes fall out of this design:

- `DDC` mode: use `DDC` readback to know the current input and stop source-cycling or `PIP` navigation when the target state is reached
- `manual` mode: when `DDC` is unavailable or untrustworthy, ask the user for current input and desired input, then execute the required blind cycling sequence

This distinction matters because the monitor does not provide a reliable direct `go to HDMI` or `go to Thunderbolt` control path. The safe abstraction is not direct selection. It is controlled cycling with feedback where available.

This hybrid model is the point of the project:

- `JOG` emulation gives access to the same menu and navigation path as a human user
- `DDC` provides machine-readable feedback and state
- `LED` observation provides immediate local feedback from the front-panel path itself
- the control deck turns those capabilities into an always-on appliance-like interface

That is much more robust than using only blind button presses, and much more capable than relying on DDC alone on this monitor. Blind-button operation is still possible, but this project prefers a feedback-aware path when available.

## Project goals

- build a reliable inline `JOG` controller for the Samsung `CJ791`
- expose monitor actions through a local REST API
- provide a Raspberry Pi-based local touch-screen UI for everyday use
- use `DDC/CI` and front-panel `LED` state for feedback and status, and `DDC/CI` for supported direct controls
- keep the design understandable enough that other Samsung owners can adapt it

## Related documents

- [Requirements](requirements.md)
- [Solution Overview](design/solution-overview.md)
- [CJ791 JOG Board Notes](hardware/cj791-jog-board.md)
- [CJ791 DDC and VCP Behavior](ddc/cj791-vcp-behavior.md)
