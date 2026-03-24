# Implementation Plan

## Summary

This document describes the proposed implementation order for `samsung-jog-api`. The goal is to de-risk hardware assumptions first, then layer software control and UI on top of known-good primitives.

## Phase 0: documentation and evidence capture

- organize requirements, design notes, and reverse-engineering records
- store photos, measurements, and raw command transcripts in predictable locations
- define a repeatable format for confirmed findings versus inference
- define the Raspberry Pi host assumptions and kiosk runtime approach

## Phase 1: hardware validation

- confirm `CN1001` pinout and wiring on the target unit
- repeat and validate resistor measurements for each `JOG` action
- determine idle-state behavior of `KEY_ADC1` and `KEY_ADC2`
- characterize the `KEY_LED` line electrically and document observable `LED` behavior patterns
- validate whether the original `JOG` board can safely remain inline

## Phase 2: bus observation hardware design

- define and review the custom hardware needed to observe `KEY_ADC1`, `KEY_ADC2`, and `KEY_LED`
- document the observation circuitry approach and approval decision

## Phase 3: analog drive hardware design

- define and review the custom hardware needed to drive `KEY_ADC1` and `KEY_ADC2`
- document the analog drive circuitry approach and approval decision

## Phase 4: GPIO assignment and low-level control prototype

- assign Raspberry Pi GPIO usage after the observation and drive circuitry are approved
- build a bench prototype that can emulate each `JOG` action
- verify that each emulated action is interpreted correctly by the monitor
- measure timing requirements for press, hold, repeat, and release behavior
- identify any debounce or threshold sensitivity in the monitor ADC interpretation

## Phase 5: DDC capability layer

- codify confirmed VCP features and monitor-specific quirks
- implement readback for input source, brightness, and power state
- verify which direct writes are reliable enough for production use
- define fallback behavior when DDC is unavailable over a given input path
- document source-cycling behavior and validate that `VCP 0x60` can be used to stop on the correct input

## Phase 6: LED feedback characterization

- capture `LED` behavior during input changes, idle states, and OSD navigation boundaries
- determine whether `LED` cues are reliable enough to use in control confirmation logic
- expose normalized `LED` state or events to the monitor control layer

## Phase 7: monitor control service

- define low-level primitives such as `press`, `hold`, `release`, and `sequence`
- implement higher-level actions such as `open-menu`, `navigate-source-list`, and `switch-to-next-input`
- integrate `DDC`-assisted and `LED`-assisted verification where they improve reliability
- add structured logging for action attempts and observed state
- implement separate control paths for `DDC` mode and `manual` blind mode

## Phase 8: local platform bring-up

- provision a Raspberry Pi OS Lite image or equivalent minimal host OS
- configure the device to auto-start the application stack on boot
- select the kiosk runtime approach
- validate local-only frontend and backend communication over `localhost`
- add process supervision and restart behavior
- implement file logging with one log file per day and three months retention

## Phase 9: recording and replay subsystem

- define the canonical JSON recording format
- support logical action events, delay events, `LED` wait events, and `DDC` wait or check events
- support polling interval and timeout behavior for wait-based events
- store recordings in a local writable directory
- support cleanup, rename, and promotion of recordings into shipped features

## Phase 10: local API

- define REST endpoints for low-level and high-level actions
- expose monitor status and health information
- define request validation and error handling behavior
- document response semantics for synchronous versus queued actions
- represent whether the system is operating in `DDC` mode or `manual` mode

## Phase 11: local UI

- build a minimal touch-friendly interface for common actions
- show current input, power state, and other useful feedback
- show relevant `LED`-derived status or activity cues when useful
- provide live log streaming in the UI
- place recording, replay, and sequence-management tools in the advanced/settings area
- design workflows around actions that are reliable and repeatable first
- validate the UI on Raspberry Pi 2 B-class hardware
- ensure normal use requires no keyboard or terminal access
- switch source-selection UX between direct target selection in `DDC` mode and `from -> to` selection in `manual` mode

## Phase 12: dashboard data-source spike

- define how the host synchronizes time after boot
- define the weather provider strategy
- define the location-source strategy for weather and related widgets
- determine which dashboard data is local-only and which depends on external services

## Phase 13: stabilization

- test common workflows repeatedly across monitor power cycles
- validate recovery behavior after failed navigation or missing DDC state
- validate recovery behavior when only `LED` feedback is available
- validate that blind `manual` mode remains usable when `DDC` state is missing
- document known limitations and unsafe operating conditions
- refine the API and implementation boundaries based on real usage
- test kiosk recovery after process crashes and full device reboot

## Later extensions

- add a physical volume knob to the control deck and map it to monitor volume over `DDC`
- define how physical volume-knob movement is synchronized with local and remote UI state

## Future investigations

- determine whether the deck display power-off action can also place the monitor into standby or power-off state
- test both `DDC` power control and `JOG`-driven OSD power workflows for that behavior
- verify whether monitor power-off or standby preserves power to attached `USB` and `Thunderbolt` devices before adopting this behavior
- investigate how to preserve practical use of the monitor's `HDMI` input while still providing `DDC` communication, beyond the temporary full `HDMI` takeover used during development
- investigate whether one of the monitor's `Thunderbolt` or `USB-C` paths can be used for `DDC` communication instead of a more complex `HDMI` sharing design
- evaluate whether a low-power dedicated device, such as a Raspberry Pi Zero 2 W, could be attached there purely for monitor communication

## Milestones

- milestone 1: confirmed electrical emulation of all `JOG` actions
- milestone 2: confirmed `LED` behavior model for target workflows
- milestone 3: confirmed `DDC` readback model for target workflows
- milestone 4: approved observation and analog drive hardware design
- milestone 5: working Raspberry Pi kiosk host with supervised app startup
- milestone 6: working recording and replay subsystem
- milestone 7: working local API for primitive and scripted actions
- milestone 8: working local UI for daily use

## Immediate next steps

- add photo assets and teardown evidence
- create the first hardware evidence records under `docs/hardware/`
- turn the DDC observations into reproducible command transcripts
- record front-panel `LED` behavior during key monitor actions
- prepare the hardware design review for observation and analog drive circuitry
- decide the initial Raspberry Pi runtime stack for frontend and backend
- update the `README.md` status section as implementation milestones are completed, and remove that section once the repository is no longer primarily in planning or scaffolding state
