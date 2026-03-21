# samsung-jog-api

samsung-jog-api started as a personal solution for the Samsung CJ791 monitor I own, built around a simple idea:

- emulate the front-panel `JOG` button electrically
- expose that control through a local REST API
- pair it with a small local touch UI
- use DDC/CI as a feedback and status channel whenever possible

This project is focused on the Samsung **LC34J791WTNXZA / CJ791** I use daily. The same approach may apply to related Samsung monitors with a similar multi-jog front-panel board, but this repository is organized around the CJ791 hardware in my setup.

## Why this project exists

The CJ791 is a capable monitor, but it is frustrating to automate.

- It has multiple useful inputs: `HDMI`, `DisplayPort`, and `Thunderbolt / USB-C`
- It has a front `JOG` control that can navigate the on-screen display and trigger functions the normal software control path cannot
- It exposes DDC/CI, which is enough to read some state and control some functions
- But it does not reliably expose the full monitor control surface over DDC alone

In my setup, with the monitor acting like a part of a desk controller, KVM-like setup, wall panel, or touch-screen control surface, blind software-only control is not enough. It needs a control path that matches what I can do with the physical `JOG` button.

## Why the destructive part

I intentionally take an invasive approach.

The front-panel `JOG` assembly is connected to the monitor main board through a small harness. Rather than trying to glue motors onto the button, tape servos to the bezel, or guess unsupported internal protocols, my plan is to intercept that harness and electrically reproduce the same button states the monitor already understands.

That is the "destructive" part:

- the monitor must be opened
- access to the front-panel control board and cable is required
- the cable may need to be cut, extended, or replaced with an inline harness
- a custom controller board can then sit between the original `JOG` board and the monitor

This is destructive in the sense that it modifies the physical monitor wiring and is not a stock, warranty-safe accessory. It is still a pragmatic choice because it targets the monitor's native control mechanism instead of relying on brittle mechanical hacks.

## Why not DDC alone

DDC/CI is still a major part of the design, just not the only part.

On this monitor, DDC is useful for:

- reading the current input state through `VCP 0x60`
- reading general monitor capabilities
- controlling brightness with `VCP 0x10`
- controlling standby power with `VCP 0xD6`
- triggering the monitor information OSD with proprietary `VCP 0xE6 = 0x01`

Known CJ791 input values reported over DDC:

- `0x01` = `HDMI`
- `0x03` = `DisplayPort`
- `0x04` = `Thunderbolt / USB-C`

In practice, the monitor acknowledges standard DDC traffic, but `setvcp 0x60` does not successfully switch inputs on this unit. That makes DDC a good feedback channel, but not a complete control channel for the full user experience.

So in practice for my setup the architecture becomes:

- use the `JOG` path for actions that need true front-panel behavior
- use DDC for state readback and functions that already work well

## Monitor information

Target monitor:

- Model: `Samsung LC34J791WTNXZA`
- Marketing name: `Samsung CJ791`
- Panel size: `34-inch ultrawide curved`
- Resolution: `3440x1440`
- Inputs: `HDMI`, `DisplayPort`, `Thunderbolt 3 / USB-C`
- Features: `Picture-in-Picture`, `Picture-by-Picture`, built-in OSD, front `JOG` control

DDC-reported information observed on this monitor:

- Model string: `FALCON`
- MCCS version: `2.0`

Useful DDC VCP features observed:

- `0x10` brightness
- `0x12` contrast
- `0x14` color preset
- `0x60` input source readback
- `0x62` speaker volume
- `0xD6` power state
- `0xCA` OSD enable
- `0xCC` OSD language

Samsung-specific observed behavior:

- `VCP 0xE6 = 0x01` shows the monitor information OSD

## The JOG hardware

Samsung refers to the front control as the `JOG` button. On this monitor the front-panel board is effectively a passive input board connected back to the main board.

The relevant connector is documented as `CN1001` in the monitor main board with this pinout:

- pin 1: `GND`
- pin 2: `KEY_ADC2`
- pin 3: `KEY_ADC1`
- pin 4: `KED_LED`
- pin 5: `NC`

This matters because it tells us the `JOG` is not just a set of separate digital switches. The monitor reads it through analog key-sense lines.

### Resistor ladder behavior

Measured with the joystick board disconnected, the key channels present distinct resistance-to-ground values:

`KEY_ADC2` directional channel:

- `Down`: `3.3 kOhm`
- `Right`: `9 kOhm`
- `Up`: `22.6 kOhm`
- `Left`: `32.8 kOhm`

`KEY_ADC1` center channel:

- `Center`: `23 kOhm`

That strongly suggests:

- `KEY_ADC2` is a resistor ladder for the four directional actions
- `KEY_ADC1` is a separate analog sense line for center / enter
- the monitor decodes button presses by reading analog thresholds on those ADC inputs

This is exactly why an inline electrical emulator is attractive. We do not need to reverse engineer every internal software path if we can present the same resistance values the original `JOG` board presents.

## Planned control method

The hardware plan is to insert my controller inline with the `JOG` harness.

The controller will:

- leave the original front-panel board usable when desired
- reproduce the same resistance-to-ground states for `KEY_ADC1` and `KEY_ADC2`
- optionally drive or observe the front LED line if useful
- expose a local API for high-level actions such as `up`, `down`, `left`, `right`, `enter`, `back`, `open-menu`, and scripted navigation sequences
- host a small local touch UI that calls the same API

At the API layer in my system, the monitor should look like a normal controllable device rather than a bundle of raw resistor values.

Example higher-level actions:

- switch to the next available input
- open source list
- navigate to `Picture-by-Picture`
- toggle a known setting
- wake or sleep the monitor

## How DDC fits into the design

DDC is the complementary readback channel.

Instead of using DDC as the only control path, `samsung-jog-api` uses it where it is strongest:

- confirm current input with `VCP 0x60`
- read or set brightness with `VCP 0x10`
- control standby with `VCP 0xD6`
- verify that the monitor is alive and reachable over the video link
- provide state to the local UI without needing to infer everything from blind menu timing

This hybrid model is the point of the project:

- `JOG` emulation gives access to the same menu and navigation path as a human user
- `DDC` provides machine-readable feedback and state

That is much more robust than using only blind button presses, and much more capable than relying on DDC alone on this monitor. Even though using the jog controller in blind-button mode is possible, this project supports that mode as well and prefers giving you a reliable, feedback-aware path first.

## Project goals

- Build a reliable inline `JOG` controller for the Samsung CJ791
- Expose monitor actions through a local REST API
- Provide a local touch-screen UI for everyday use
- Use DDC/CI for feedback, status, and supported direct controls
- Keep the design understandable enough that other Samsung owners can adapt it

## Safety and scope

This project is for people who are comfortable modifying hardware they own.

- Opening the monitor can damage clips, cables, or boards
- Cutting or extending the `JOG` harness can permanently alter the monitor
- Mistakes on the key lines can damage the monitor input circuitry
- Nothing here should be treated as warranty-safe

The purpose of this repository is not to preserve stock condition. The purpose is to create a practical, local, programmable control interface for a monitor whose original user interface is difficult to automate cleanly.
