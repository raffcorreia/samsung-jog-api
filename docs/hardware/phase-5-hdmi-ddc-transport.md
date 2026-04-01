# Phase 5 HDMI And DDC Transport Design

## Purpose

This document records the selected transport direction for preserving practical `HDMI` use on the Samsung `CJ791` while still maintaining a reliable `DDC/CI` path for the controller.

It turns the Phase 5 transport brainstorming into a concrete project direction that later hardware phases can consume.

## Problem Statement

The project wants the controller to use `DDC/CI` over the monitor's `HDMI` path without permanently occupying that `HDMI` input.

The controller should be able to:

- read monitor state through `DDC/CI`
- send supported `DDC/CI` commands
- coexist with a normal external `HDMI` source
- preserve a stable user experience for that external source

At the same time, the connected computer should keep seeing behavior close to a normal monitor connection.

## Relevant HDMI Signals

The critical `HDMI` sideband signals for this phase are:

- `pin 15`: `DDC SCL`
- `pin 16`: `DDC SDA`
- `pin 17`: `DDC GND`
- `pin 18`: `+5V`
- `pin 19`: `HPD`

These lines matter because `DDC` is already used by the source and monitor for:

- `EDID`
- ordinary monitor-side `DDC/CI`
- other source/display coordination that may occur after initial connect

## Why Passive Tapping Is Rejected

A raw parallel connection between:

- source
- monitor
- Raspberry Pi controller

is not an acceptable final design.

Reasons:

- the source and monitor already assume ownership of the `DDC` bus
- the Pi would become an additional master on a live bus
- extra capacitance and stubs can degrade signal integrity
- uncontrolled multi-master behavior creates collision and retry risk
- failures could affect `EDID`, display bring-up, or later monitor communication

The issue is not just `I2C` addressing. The issue is uncontrolled shared ownership of an already-live `HDMI` control channel.

## Candidate Directions

### Candidate A: Passive Parallel DDC Tap

Attach the Pi directly to the same `DDC` wires used by the computer and monitor.

Decision:

- rejected for final design

Why:

- electrically risky
- protocol ownership is ambiguous
- too fragile for a production-worthy transport design

### Candidate B: Switched DDC Ownership

Only one controller talks to the monitor-side `DDC` bus at a time.

Normal model:

- external computer owns `DDC` during normal attached operation
- Pi remains electrically disconnected from monitor-side `DDC`
- Pi temporarily takes ownership only for short monitor transactions

Decision:

- selected as the core transport direction

Why:

- avoids uncontrolled shared-master behavior
- preserves a realistic path to custom hardware
- gives the Pi direct monitor access when needed
- keeps the design much simpler than a full `HDMI` proxy

### Candidate C: Full HDMI Proxy Or Bridge

Insert hardware that behaves like a full `HDMI` intermediary, potentially managing `EDID`, `HPD`, and all `DDC` traffic in a fully active way.

Decision:

- rejected for the current project phase

Why:

- too complex for the current hardware plan
- would require specialized `HDMI` hardware beyond the current direction
- poor fit for a Raspberry Pi-centric control deck architecture

## Selected Direction

The selected Phase 5 direction is:

- switched `DDC` ownership
- preserve ordinary source access to monitor `EDID` over the normal path
- plus careful `HPD` handling

This is best described as a smart `HDMI` intermediary for the `DDC` and presence sideband signals, not as a passive tap and not as a full `HDMI` video proxy.

## Reference Diagram

Current transport concept diagram:

![Phase 5 HDMI and DDC transport concept](../assets/hardware/phase-5-hdmi-ddc-transport-diagram.svg)

The diagram shows:

- which `HDMI` pins pass through directly
- which sideband pins are intercepted or controlled
- the intended `DDC` ownership switch point
- the `HPD` and source `+5V` handling blocks
- the Raspberry Pi control relationship to those blocks

## Design Intent

The final transport subsystem should provide these behaviors.

### Toward the external computer

It should preserve a usable monitor connection as much as practical without adding unnecessary transport complexity in this phase.

That means:

- the source should still be able to query the monitor's ordinary `EDID`
- `HPD` should not toggle unnecessarily
- normal display re-enumeration should be avoided during routine Pi monitor queries

### Toward the monitor

The controller should be able to access the monitor-side `DDC` bus when needed.

That means:

- the Pi can temporarily own monitor-side `SCL` and `SDA`
- Pi monitor transactions should be short and explicit
- the computer and Pi should not both be active on monitor-side `DDC` at the same time

## Required Subsystems

The transport design now assumes the need for these functional blocks:

- source-side `HDMI` connector interface
- monitor-side `HDMI` connector interface
- `DDC` switch, mux, or bus-switch hardware
- `HPD` handling or controlled pass-through path
- Raspberry Pi control interface for selecting `DDC` ownership

This means the long-term hardware design is not just "add an `HDMI` connector to the main controller board." It needs a defined sideband-transport strategy.

## Expected Operating States

### State 1: No external computer attached

- Pi owns monitor-side `DDC`
- Pi may query the monitor freely
- Pi may issue supported `DDC/CI` commands

### State 2: External computer attached, normal operation

- computer owns monitor-side `DDC`
- Pi does not drive the monitor-side `DDC` bus
- `EDID` and `HPD` remain stable for the computer

### State 3: Pi temporary control transaction

- monitor-side `DDC` is switched away from the external computer
- Pi temporarily owns monitor-side `DDC`
- Pi performs a short query or command
- ownership returns to the external computer

This state should be used sparingly. The project should not assume aggressive polling while a normal source is attached.

## Practical Rules

The selected transport direction implies these design rules:

- do not rely on passive parallel multi-master `DDC`
- do not assume `EDID` is only read once at startup
- do not toggle `HPD` casually
- do not poll monitor `DDC` aggressively while an external computer is attached
- keep Pi `DDC` ownership windows short
- prefer monitor queries on demand rather than continuous high-rate monitoring over shared `HDMI`

## Current Development Compromise

For development, a temporary sacrificial `HDMI` path is still acceptable.

That remains only a development compromise. It is not the approved final-system assumption.

## Deferred Detailed Decisions

Phase 5 selects the direction, but does not yet fully lock:

- exact `DDC` switch or mux part family
- whether `HPD` is passed through, buffered, gated, or selectively synthesized
- exact timing rules for Pi ownership takeover and release
- how much disruption a short Pi takeover causes on a real attached computer
- whether the transport should live on the integrated controller board or on a separate intermediary board

## Descoped Complexity

Dedicated `EDID` emulation was considered and intentionally descoped from Phase 5.

Reason:

- it adds extra hardware and routing complexity beyond the immediate goal
- the current phase goal is monitor `DDC` access without unsafe passive bus sharing
- the external source should still be allowed to query the monitor's own `EDID` through the normal path

## Verification Direction For Later Phases

Later implementation should verify:

- external computer can still query the monitor's `EDID`
- ordinary display bring-up works through the intermediary
- Pi can take monitor-side `DDC` ownership and successfully complete short transactions
- takeover and release do not cause unacceptable display re-enumeration
- `HPD` behavior remains stable during normal operation
- the monitor's practical `HDMI` input remains usable for a real external source

## Outcome

Phase 5 now approves a clear hardware direction:

- not a passive `DDC` tap
- not permanent `HDMI` sacrifice as a final-system assumption
- not a full active `HDMI` proxy
- yes to switched `DDC` ownership with ordinary monitor `EDID` still reachable by the source, plus careful `HPD` handling
