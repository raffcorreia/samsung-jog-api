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
- characterize the `KED_LED` line electrically and document observable `LED` behavior patterns
- validate whether the original `JOG` board can safely remain inline
- choose an emulation method for reproducing resistor states

## Phase 2: low-level control prototype

- build a bench prototype that can emulate each `JOG` action
- verify that each emulated action is interpreted correctly by the monitor
- measure timing requirements for press, hold, repeat, and release behavior
- identify any debounce or threshold sensitivity in the monitor ADC interpretation

## Phase 3: DDC capability layer

- codify confirmed VCP features and monitor-specific quirks
- implement readback for input source, brightness, and power state
- verify which direct writes are reliable enough for production use
- define fallback behavior when DDC is unavailable over a given input path
- document source-cycling behavior and validate that `VCP 0x60` can be used to stop on the correct input

## Phase 4: LED feedback characterization

- capture `LED` behavior during input changes, idle states, and OSD navigation boundaries
- determine whether `LED` cues are reliable enough to use in control confirmation logic
- expose normalized `LED` state or events to the monitor control layer

## Phase 5: monitor control service

- define low-level primitives such as `press`, `hold`, `release`, and `sequence`
- implement higher-level actions such as `open-menu`, `navigate-source-list`, and `switch-to-next-input`
- integrate `DDC`-assisted and `LED`-assisted verification where they improve reliability
- add structured logging for action attempts and observed state
- implement separate control paths for `DDC` mode and `manual` blind mode

## Phase 6: local platform bring-up

- provision a Raspberry Pi OS Lite image or equivalent minimal host OS
- configure the device to auto-start the application stack on boot
- select the kiosk runtime approach
- validate local-only frontend and backend communication over `localhost`
- add process supervision and restart behavior

## Phase 7: local API

- define REST endpoints for low-level and high-level actions
- expose monitor status and health information
- define request validation and error handling behavior
- document response semantics for synchronous versus queued actions
- represent whether the system is operating in `DDC` mode or `manual` mode

## Phase 8: local UI

- build a minimal touch-friendly interface for common actions
- show current input, power state, and other useful feedback
- show relevant `LED`-derived status or activity cues when useful
- design workflows around actions that are reliable and repeatable first
- validate the UI on Raspberry Pi 2 B-class hardware
- ensure normal use requires no keyboard or terminal access
- switch source-selection UX between direct target selection in `DDC` mode and `from -> to` selection in `manual` mode

## Phase 9: stabilization

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

## Milestones

- milestone 1: confirmed electrical emulation of all `JOG` actions
- milestone 2: confirmed `LED` behavior model for target workflows
- milestone 3: confirmed `DDC` readback model for target workflows
- milestone 4: working Raspberry Pi kiosk host with supervised app startup
- milestone 5: working local API for primitive and scripted actions
- milestone 6: working local UI for daily use

## Immediate next steps

- add photo assets and teardown evidence
- create the first hardware evidence records under `docs/hardware/`
- turn the DDC observations into reproducible command transcripts
- record front-panel `LED` behavior during key monitor actions
- decide the first hardware prototype approach for resistor-state emulation
- decide the initial Raspberry Pi runtime stack for frontend and backend
- update the `README.md` status section as implementation milestones are completed, and remove that section once the repository is no longer primarily in planning or scaffolding state
