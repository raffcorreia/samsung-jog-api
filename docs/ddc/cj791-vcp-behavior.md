# CJ791 DDC and VCP Behavior

## Scope

This document records DDC/CI observations for the Samsung `LC34J791WTNXZA / CJ791`.

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

More specifically, the practical source-switching problem is not `set input to HDMI`. It is `cycle inputs until readback says HDMI`. That makes `VCP 0x60` especially important, because it tells the controller when to stop.

## Observed monitor information

DDC-reported information observed on this monitor:

- model string: `FALCON`
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

Confirmed useful result for future hardware extensions:

- monitor volume control over `VCP 0x62` works and is a good candidate for a future physical volume knob on the control deck

## LED-correlated command acceptance observations

The front-panel `LED` appears to act as a practical acceptance cue for some monitor actions, even when the visible effect takes longer to complete.

Observed behavior:

- when volume is changed over `VCP 0x62`, the `LED` blinks when the monitor accepts and applies the new value
- if volume changes are stepped slowly but still within the monitor's coalescing window, intermediate steps may not trigger a blink because the monitor has not yet committed the change
- once the volume reaches `100`, the `LED` does not blink immediately; instead the blink arrives about `1-2s` later, which matches the same delay observed when the monitor commits ordinary volume changes after input activity stops
- when the input is changed, the `LED` blinks first as an acceptance signal and the monitor then begins the actual source-transition process

Current interpretation:

- `LED` blink behavior is useful as an immediate local signal that a command was accepted
- for volume control, the blink appears to correlate with delayed commit rather than with the instant a step request is sent
- for input changes, the blink still appears to correlate more closely with command acceptance than with completion of the full visible workflow
- this makes `LED` observation potentially useful for pacing repeated commands and detecting boundary conditions during interactive control flows

These observations should be treated as behavioral findings from the current unit and should be expanded later with dated transcripts, input-specific notes, and timing measurements.

Future investigation:

- whether `DDC` power control or a `JOG`-driven power-off workflow can turn the monitor off while still preserving power to attached `USB` or `Thunderbolt` devices

## Role in the system

Instead of using DDC as the only control path, `samsung-jog-api` uses it where it is strongest:

- confirm current input with `VCP 0x60`
- read or set brightness with `VCP 0x10`
- control standby with `VCP 0xD6`
- verify that the monitor is alive and reachable over the video link
- provide state to the local UI without needing to infer everything from blind menu timing

This creates two obvious workflow modes:

- `DDC` mode: read current input and use that state to terminate source-cycling and other stateful menu workflows
- `Blind` mode: when `DDC` cannot be trusted, ask the user for current and desired input so blind source-cycling still has a defined starting point

## Known gaps

- raw command transcripts are not yet included
- error behavior across different active inputs is not yet recorded
- reliability of writes other than brightness and power is not yet documented
- behavior during Picture-by-Picture modes is not yet captured here
- whether `VCP 0x60` remains trustworthy during all source-transition and `PIP` workflows is not yet fully documented

## Suggested follow-up

- add dated command examples and outputs
- document transport assumptions such as host OS, cable, and active input
- record failure modes when DDC is unavailable or partially functional
