# Phase 5 Execution Record

## Purpose

This document records the execution outcome for `Phase 5: HDMI and DDC Communication Design`.

It complements:

- [Implementation Plan](../implementation/plan.md)
- [Requirements](../requirements.md)
- [Architecture](../architecture.md)
- [Solution Overview](../design/solution-overview.md)
- [CJ791 DDC and VCP Behavior](../ddc/cj791-vcp-behavior.md)
- [Phase 5 HDMI And DDC Transport Design](../hardware/phase-5-hdmi-ddc-transport.md)

## Reference Diagram

Current Phase 5 transport concept diagram:

![Phase 5 HDMI and DDC transport concept](../assets/hardware/phase-5-hdmi-ddc-transport-diagram.svg)

## Goal

Define and approve how the final system preserves practical use of the monitor's `HDMI` input while still maintaining a reliable `DDC/CI` communication path for the controller.

## Inputs From Earlier Work

The Phase 5 decision is based on these already-established project facts:

- `DDC/CI` is useful on the `CJ791` for readback and selected direct controls
- `DDC/CI` does not replace `JOG` emulation for full monitor control on this unit
- preserving practical `HDMI` input use is a project requirement
- permanently occupying the monitor's `HDMI` path is only acceptable as a temporary development compromise
- the long-term design must avoid sacrificing the monitor's practical `HDMI` input

## Scope

In scope:

- `HDMI` and `DDC` transport direction
- evaluation of how `DDC` can coexist with a normal external `HDMI` source
- interface implications for the later integrated hardware design
- identification of whether extra transport hardware is required beyond the core controller functions

Out of scope:

- final integrated controller board layout
- exact part selection for the transport hardware
- final timing tuning for source-side takeover and release
- full `DDC` capability characterization for every monitor workflow

## Candidate Transport Directions

### Candidate A: Passive Parallel DDC Tap

Attach the Raspberry Pi directly in parallel with the source and monitor on `DDC`.

Decision:

- rejected

Reason:

- too much electrical and protocol ownership risk for a final design

### Candidate B: Switched DDC Ownership

Allow either:

- the external source
- or the Raspberry Pi

to own monitor-side `DDC`, but not both at the same time.

Decision:

- selected

Reason:

- preserves a realistic hardware implementation path
- avoids uncontrolled multi-master sharing
- still allows deliberate Pi-side monitor control and readback

### Candidate C: Full HDMI Proxy Or Bridge

Use active intermediary hardware that behaves like a true `HDMI` bridge or proxy.

Decision:

- rejected for the current project direction

Reason:

- too complex for the current hardware and cost goals

## Selected Direction

The approved Phase 5 direction is:

- switched `DDC` ownership
- preserve ordinary source access to monitor `EDID`
- plus careful `HPD` handling

With the current preferred interpretation:

- `pin 18` remains source-provided `+5V` and is treated as pass-through plus source-presence sensing
- `pin 19` `HPD` is treated as a monitor-to-source signal and defaults to pass-through plus observation
- active `HPD` conditioning or source-presence assist remains optional follow-up hardware, not a Phase 5 assumption

This means the project now assumes a smart sideband intermediary rather than:

- a passive `DDC` tap
- a permanently sacrificed `HDMI` path
- a full active `HDMI` video bridge

## Practical System Model

The selected operating model is:

1. when no external source is attached, the Pi may own monitor-side `DDC`
2. during ordinary external-source use, the external source normally owns monitor-side `DDC`
3. when the Pi needs a monitor transaction, it temporarily takes monitor-side `DDC`, performs a short query or command, and then returns ownership

Important caveat:

- item 1 is still a validation target rather than a guaranteed fact, because the monitor may not expose usable `HDMI`-side `DDC` when no external source is presenting source-side `pin 18` `+5V`

This model assumes:

- short explicit Pi transactions
- no aggressive background Pi polling while a real source is attached
- stable monitor presence toward the external source

## Why `EDID` And `HPD` Matter

The transport decision still treats `EDID` and `HPD` as important design constraints, but not as justification for adding a dedicated `EDID` emulation block in this phase.

Why:

- losing access to monitor `EDID` can trigger display reconfiguration or output re-detection
- unstable `HPD` can make the source think the monitor disconnected
- even if Pi-side `DDC` transactions work electrically, the user experience is still bad if the source keeps re-enumerating the display

So the transport design is not only a `DDC` mux problem. It is a stable-display-presence problem.

## Interface Impact On Later Phases

Phase 5 now implies that the later integrated hardware design must account for:

- source-side `HDMI` transport interface
- monitor-side `HDMI` transport interface
- monitor-side `DDC` switching or muxing
- `HPD` monitoring or control hardware
- a Pi-facing control path for transport ownership logic

This means the final hardware plan may require:

- a separate transport intermediary board
- or an expanded integrated controller board that includes the `HDMI/DDC` sideband path

The exact packaging decision is still deferred.

## Deliverables Completed

- documented the final-system requirement to preserve practical `HDMI` use
- recorded why passive parallel `DDC` sharing is rejected
- recorded why a full active `HDMI` proxy is rejected for the current project
- approved switched `DDC` ownership as the selected direction
- documented that dedicated `EDID` emulation was descoped for this phase due to extra complexity
- documented the need to preserve ordinary source access to monitor `EDID` plus careful `HPD` handling
- recorded the operating-state model for source-attached and Pi-ownership cases
- documented the later interface impact on integrated hardware design

## Exit-Criteria Assessment

Phase 5 is complete at the architectural-direction level.

The project now has:

- an approved `HDMI/DDC` communication direction for the final system
- a documented rationale for the selected direction
- a clear rejection of permanent `HDMI` sacrifice as the final-system assumption
- a defined transport impact on later hardware design phases

## Open Items Deferred To Later Phases

- exact `DDC` switch or mux part selection
- exact `HPD` electrical strategy
- whether source-side `pin 18` pass-through is sufficient for all intended Pi-side `DDC` use cases
- whether the monitor answers `HDMI`-side `DDC` with no external source attached and no source-side `pin 18` `+5V` present
- whether the transport hardware is a separate board or part of the integrated controller board
- real-world disruption testing with a normal external computer attached
- detailed verification plan for takeover timing and recovery behavior
