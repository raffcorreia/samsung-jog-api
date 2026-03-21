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

## Role in the system

Instead of using DDC as the only control path, `samsung-jog-api` uses it where it is strongest:

- confirm current input with `VCP 0x60`
- read or set brightness with `VCP 0x10`
- control standby with `VCP 0xD6`
- verify that the monitor is alive and reachable over the video link
- provide state to the local UI without needing to infer everything from blind menu timing

## Known gaps

- raw command transcripts are not yet included
- error behavior across different active inputs is not yet recorded
- reliability of writes other than brightness and power is not yet documented
- behavior during Picture-by-Picture modes is not yet captured here

## Suggested follow-up

- add dated command examples and outputs
- document transport assumptions such as host OS, cable, and active input
- record failure modes when DDC is unavailable or partially functional
