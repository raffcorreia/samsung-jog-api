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

Practical direction notes for these lines:

- `pin 18` must be treated as both a source-presence signal and a controllable monitor-side presence input
- the controller should sense whether an external computer is presenting `+5V` on source-side `pin 18`
- the controller should also be able to present monitor-side `pin 18` from either the external source or a Pi-generated local `+5V` rail
- the project must not assume the monitor will answer `HDMI`-side `DDC` normally when no monitor-side `pin 18` `+5V` is present
- `pin 19` `HPD` is a monitor-to-source signal, so the clean default is pass-through plus Pi-side observation unless later testing proves active `HPD` conditioning is required

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

### Candidate D: Attached Pi Listener/Slave Plus Temporary Source Disconnect

Keep the Pi attached to the live `DDC` bus during ordinary source-owned operation as an additional non-owning bus participant so it can observe traffic and detect idle without extra observation GPIOs.

Normal model:

- external computer remains the only `DDC` master during normal attached operation
- monitor remains the real target slave
- Pi remains attached in a listener or slave-capable role and may log traffic
- when the Pi needs a monitor transaction, hardware disconnects the external source from monitor-side `DDC`
- Pi then uses its own master-mode `I2C` interface to talk to the monitor
- after the short transaction, the source path is restored

Decision:

- selected for current Phase 5 exploration

Why:

- avoids extra GPIOs dedicated only to `SCL` / `SDA` idle observation
- allows the Pi to observe and log host-side `DDC` traffic for later learning
- preserves the rule that only one master owns monitor-side `DDC` at a time
- stays materially simpler than full monitor emulation

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

- attached Pi listener/slave plus temporary source disconnect for Pi-owned transactions
- preserve ordinary source access to monitor `EDID` over the normal path
- external-source `pin 18` presence sensing
- selectable monitor-side `pin 18` source: external pass-through or Pi-generated `+5V`
- plus careful `HPD` handling

Current implementation bias inside that direction:

- keep the Pi attached to the source-owned `DDC` bus in a non-owning listener or slave-capable role during normal operation
- use that attached Pi path to observe traffic and infer bus-idle state without extra dedicated `SCL` / `SDA` observation GPIOs
- when the Pi needs its own monitor transaction, disconnect the external source path from monitor-side `DDC`, then let the Pi act as master
- sense source-side `pin 18` to detect whether an external computer is attached
- allow the controller to drive monitor-side `pin 18` from a local regulated `+5V` rail when Pi-only `DDC` access is needed
- isolate the external source `+5V` path from the Pi-generated `+5V` path so they can never backfeed into each other
- treat `pin 18` as a small source-selection problem, not as a permanently fixed pass-through signal
- treat `pin 19` as direct monitor-to-source `HPD` pass-through with observation first
- only add active `HPD` conditioning or source-presence assist circuitry if later validation shows it is required

This is best described as a smart `HDMI` intermediary for the `DDC` and presence sideband signals, not as a passive tap and not as a full `HDMI` video proxy.

## Reference Diagram

Current transport concept diagram:

![Phase 5 HDMI and DDC transport concept](../assets/hardware/phase-5-hdmi-ddc-transport-diagram.svg)

The diagram shows:

- which `HDMI` pins pass through directly
- which sideband pins are intercepted or controlled
- the intended `DDC` ownership switch point
- the `HPD` and source / Pi-selected `+5V` handling blocks
- the Raspberry Pi control relationship to those blocks

## Design Intent

The final transport subsystem should provide these behaviors.

### Toward the external computer

It should preserve a usable monitor connection as much as practical without adding unnecessary transport complexity in this phase.

That means:

- the source should still be able to query the monitor's ordinary `EDID`
- `HPD` should not toggle unnecessarily
- normal display re-enumeration should be avoided during routine Pi monitor queries
- when an external source is attached, its `+5V` should remain the default monitor-side `pin 18` source unless the controller deliberately changes state

### Toward the monitor

The controller should be able to access the monitor-side `DDC` bus when needed.

That means:

- the Pi can temporarily own monitor-side `SCL` and `SDA`
- the Pi may remain attached to the source-owned `DDC` bus in a non-owning listener or slave-capable role during normal operation
- Pi monitor transactions should be short and explicit
- the computer and Pi should not both be active as masters on monitor-side `DDC` at the same time
- the controller may need to present monitor-side `pin 18` from a local `+5V` source when no external computer is attached
- Pi takeover should only occur after the source-owned `DDC` bus appears idle

## Required Subsystems

The transport design now assumes the need for these functional blocks:

- source-side `HDMI` connector interface
- monitor-side `HDMI` connector interface
- attached Pi `DDC` interface that can remain present during source-owned operation
- source-path disconnect or ownership-switch hardware for temporary Pi master transactions
- source-side `pin 18` presence sensing
- local regulated `+5V` generation for optional monitor-side `pin 18` assertion
- `pin 18` source-selection and backfeed-isolation hardware
- `HPD` handling or controlled pass-through path
- Raspberry Pi control interface for selecting `DDC` ownership

This means the long-term hardware design is not just "add an `HDMI` connector to the main controller board." It needs a defined sideband-transport strategy.

## PCB Design Approach

The Phase 5 PCB should be designed as a deliberate sideband-transport board, not as an autorouted generic breakout.

Selected PCB-design approach:

- place `HDMI source` and `HDMI monitor` connectors side by side on the same external board edge
- keep the Raspberry Pi control header on the opposite side of the board
- route the high-speed `HDMI` pass-through pins as short, direct connector-to-connector connections with minimal interruption
- route only the controlled sideband signals through the active circuitry:
  - `DDC SCL`
  - `DDC SDA`
  - `pin 18 +5V`
  - `pin 19 HPD`
- treat the board as a mixed-criticality layout:
  - direct pass-through for the untouched `HDMI` lines
  - deliberate manual escape routing for the sideband and control nets
- prefer solid copper reference planes and short fanout paths over long stitched ground traces
- use at least a 2-layer board, with permission to move to 4 layers if routing quality or return-path quality demands it

Explicit Phase 5 rule:

- do not rely on generic autorouting or AI-generated routing as the design method for this board

Why:

- the board combines dense `HDMI` connector geometry with a small number of intentionally intercepted sideband nets
- the routing priorities are architectural, not just net-completion oriented
- careless auto-generated routing can easily create shorts, poor connector escapes, and misleadingly "complete" boards that are not manufacturable

So the expected implementation method is:

- manual placement
- manual routing strategy
- DRC-driven cleanup
- explicit review of connector escape quality and sideband net ownership paths

## Expected Operating States

### State 1: No external computer attached

- Pi presents monitor-side `pin 18` from the local regulated `+5V` source
- Pi owns monitor-side `DDC`
- Pi may query the monitor freely
- Pi may issue supported `DDC/CI` commands

This state assumes the monitor will treat the locally presented `pin 18` `+5V` as sufficient presence for `HDMI`-side `DDC`. That remains a validation target until tested on the actual unit.

### State 2: External computer attached, normal operation

- external source `+5V` is detected on source-side `pin 18`
- external source `+5V` is the default monitor-side `pin 18` source
- computer owns monitor-side `DDC`
- Pi remains attached in a non-owning listener or slave-capable role and may observe traffic
- `EDID` and `HPD` remain stable for the computer

### State 3: Pi temporary control transaction

- monitor-side `pin 18` remains valid from the selected source
- the external source path is disconnected from monitor-side `DDC`
- Pi temporarily owns monitor-side `DDC` as master
- Pi performs a short query or command
- the external source path is restored

This state should be used sparingly. The project should not assume aggressive polling while a normal source is attached.

### State 4: Source-selection conflict or fault

- external-source `+5V` and Pi-generated `+5V` must never be tied together
- hardware defaults should prevent backfeed even if firmware is misconfigured
- on ambiguous state or fault, the transport should prefer isolating the two `+5V` sources over trying to preserve a guessed operating mode

## Practical Rules

The selected transport direction implies these design rules:

- do not rely on passive parallel multi-master `DDC`
- do not assume `EDID` is only read once at startup
- do not toggle `HPD` casually
- do not poll monitor `DDC` aggressively while an external computer is attached
- keep Pi `DDC` ownership windows short
- prefer monitor queries on demand rather than continuous high-rate monitoring over shared `HDMI`
- treat source `pin 18` sensing and monitor-side `pin 18` source selection as separate functions
- never allow Pi-generated `+5V` to backfeed into the external source
- keep the monitor-side `pin 18` source-selection logic explicit rather than implicit
- treat `SCL` and `SDA` as a controlled pair during source disconnect and Pi master takeover
- treat `DDC` bus idle as `SCL = high` and `SDA = high`
- require a bus-idle determination before Pi takeover
- assume the bus may be busy whenever either `SCL` or `SDA` is low
- use temporary source disconnect and master ownership control, not Pi-side monitor emulation, to avoid source/Pi communication conflicts

## DDC Takeover Rules

The current Phase 5 communication-arbitration rule is:

- the external computer is the default `DDC` owner whenever attached
- the Pi may remain attached to the live bus in a non-owning listener or slave-capable role during source-owned operation
- the Pi may only take monitor-side `DDC` for short, explicit transactions after the external source path is disconnected
- the Pi must not emulate the monitor or answer computer-side `DDC` requests in this phase

Practical bus-idle interpretation:

- idle bus: `SCL = high` and `SDA = high`
- potentially busy bus: either `SCL` or `SDA` low

Recommended Pi takeover sequence:

1. detect that an external source is attached if source-side `pin 18` is present
2. observe or infer source-bus idle from the attached Pi listener/slave role
3. wait until the source-owned bus appears idle
4. disconnect the external source path from monitor-side `DDC`
5. let the Pi act as master for one short query or command
6. restore the external source path

Important limitation:

- seeing both lines high means the bus is currently idle, but it does not guarantee the source will not begin a new transaction immediately after that observation
- Pi takeover should therefore be treated as a deliberate, brief interruption window rather than as perfectly cooperative arbitration
- the viability of an attached Pi listener or slave-capable role still depends on clean electrical behavior and reliable bus-role transition under Raspberry Pi OS

## Proposed Electrical Architecture

The current Phase 5 electrical direction is a sideband-only intermediary that leaves the `HDMI` high-speed video lanes untouched and only intervenes on:

- `DDC SCL`
- `DDC SDA`
- `pin 18` `+5V`
- `pin 19` `HPD`
- `GND`

This is not a full `HDMI` repeater or proxy. It is a controlled sideband transport board.

### Electrical Design Goals

The electrical schematic should satisfy these rules:

- the external computer must be the default `DDC` owner when attached
- the Pi must talk only to the real monitor, not emulate it
- the Pi `I2C` domain must not be directly exposed to a raw `HDMI/DDC` voltage domain without proper interfacing
- the monitor-side `DDC` bus must connect to only one master at a time
- source-side `pin 18` and Pi-generated `pin 18` must never backfeed each other
- loss of Pi software control should fall back to a safe source-owned state whenever possible

### DDC Electrical Topology

The preferred schematic shape is:

1. source-side `HDMI` connector exposes `SCL_SRC` and `SDA_SRC`
2. monitor-side `HDMI` connector exposes `SCL_MON` and `SDA_MON`
3. Pi-side `I2C` exposes `SCL_PI_3V3` and `SDA_PI_3V3`
4. Pi-side `I2C` passes through a bidirectional level-translation stage to create a Pi-owned `DDC`-compatible side
5. during normal operation, the translated Pi `DDC` path remains attached to the live `DDC` bus in a non-owning listener or slave-capable role
6. a controlled source-disconnect function can temporarily isolate the external source path from monitor-side `DDC` so the Pi can act as master

Functionally:

- source-owned state:
  - `SCL_SRC -> SCL_MON`
  - `SDA_SRC -> SDA_MON`
  - Pi translated `DDC` path remains attached for observation or slave-capable presence, but is not the active master

- Pi-owned state:
  - source path to monitor-side `DDC` is disconnected
  - Pi translated `SCL -> SCL_MON`
  - Pi translated `SDA -> SDA_MON`

This means the design uses explicit source disconnect and Pi master takeover rather than a strict two-fully-detached-masters mux as the primary architecture.

### Why Level Translation Is Included

The Pi-side `I2C` bus is a `3.3V` domain. `HDMI/DDC` must be treated as a separate bus domain whose pull-up and electrical expectations are not assumed to be safely Pi-native.

So the Phase 5 electrical direction is:

- no direct Pi GPIO connection to raw `HDMI` `SCL` / `SDA`
- include a bidirectional `I2C`-appropriate level-translation stage on the Pi path
- place ownership switching on the translated `DDC` side, not directly on raw Pi GPIO pins

This keeps the Pi electrically conservative and avoids baking an unsafe single-voltage assumption into the design.

### DDC Switch Requirements

The `DDC` control block should meet these functional requirements:

- allow the Pi to remain attached during source-owned operation without becoming the active master
- disconnect the external source path from monitor-side `DDC` when the Pi needs master ownership
- treat `SCL` and `SDA` as a coordinated pair during disconnect and reconnect
- present low added capacitance and low on-resistance
- tolerate open-drain bidirectional signaling cleanly
- default to the external-source path when unpowered or when the controller is not actively taking ownership

The preferred class of part is therefore:

- an `I2C`-appropriate disconnect or bus-control element that can isolate the source path cleanly during Pi-owned transactions

The preferred class is not:

- passive parallel wiring
- a generic logic mux chosen without regard to open-drain bus behavior
- Pi-driven monitor emulation hardware

### Source Presence And Monitor-Side `+5V`

The `pin 18` electrical path should be drawn as two different functions.

#### 1. Source-presence sense

Source-side `pin 18` should feed a high-impedance sense path toward the controller logic.

That sense path should:

- detect whether an external computer is attached and powered enough to present `+5V`
- avoid materially loading the source
- preferably expose a clean logic-level signal to the Pi through a divider, comparator, or protected sense input

#### 2. Monitor-side `+5V` source select

Monitor-side `pin 18` should come from exactly one of:

- external-source `pin 18`
- Pi-generated regulated `+5V`

The schematic should therefore include:

- a local regulated `+5V` source
- explicit source-selection or ideal-diode / power-mux behavior
- backfeed blocking between the two sources
- current limiting or fault protection on the Pi-generated path

Preferred default behavior:

- if external `pin 18` is present and no override is active, the monitor sees the external source `+5V`
- if no external `pin 18` is present and Pi-only `DDC` mode is requested, the monitor may see Pi-generated `+5V`

### `HPD` Electrical Direction

For this phase, `pin 19` `HPD` should remain electrically simple:

- default pass-through from monitor to source
- optional observation by the controller
- no active synthesis or gating required in the base schematic unless later testing proves it necessary

That keeps the initial Phase 5 electrical schema focused on `DDC` ownership and `pin 18` presence handling.

### Suggested Schematic Blocks

The Phase 5 schematic should be organized into these blocks:

- `HDMI Source Connector`
- `HDMI Monitor Connector`
- `TMDS/CEC Pass-Through`
- `Attached Pi DDC Interface`
- `Source DDC Disconnect Control`
- `Pi I2C Level Translation`
- `Source +5V Presence Detect`
- `Monitor +5V Source Select`
- `HPD Pass-Through And Observe`
- `Pi Control GPIO And Status Inputs`
- `Power Regulation And Protection`

### Recommended Default States

Hardware defaults matter as much as software policy.

Recommended defaults:

- `DDC_SOURCE_PATH = CONNECTED`
- `MONITOR_5V_SEL = SOURCE` when external source `+5V` is present
- Pi-generated `+5V` disabled by default
- `HPD` direct pass-through by default

In practical terms, if the controller is reset, unconfigured, or crashed, the safest behavior is:

- external computer still sees the monitor as normally as possible
- Pi loses active control first
- conflicting `+5V` drive is prevented in hardware, not merely by firmware

### Protection And Support Components

The Phase 5 electrical schema should reserve room for at least:

- ESD protection appropriate for the `HDMI` sideband lines
- current limiting or load-switch protection on Pi-generated `+5V`
- pull-up strategy review on the Pi side of the level translator
- optional weak pull or bias resistors that enforce safe switch defaults at boot
- optional test points for:
  - source-side `SCL`
  - source-side `SDA`
  - monitor-side `SCL`
  - monitor-side `SDA`
  - source-side `pin 18`
  - monitor-side `pin 18`
  - `HPD`

### Current Recommendation

The current recommended Phase 5 schematic direction is:

- leave high-speed `HDMI` lanes as direct pass-through
- keep the Pi attached to the live `DDC` bus through an `I2C`-appropriate translated interface during normal source-owned operation
- implement Pi transactions by temporarily disconnecting the external source path from monitor-side `DDC`
- insert bidirectional level translation between Pi `3.3V` `I2C` and the attached `DDC` path
- sense source-side `pin 18`
- provide Pi-generated regulated `+5V` for optional monitor-side presence
- use explicit source selection and backfeed blocking for monitor-side `pin 18`
- keep `HPD` as pass-through plus observation in the base design

This gives the project a realistic electrical schematic target without turning Phase 5 into a full display-emulation design.

## Alternative Deferred Architecture

The main alternative kept in reserve is a stricter pure ownership-switch design:

- the Pi is electrically detached from monitor-side `DDC` during normal source-owned operation
- source-side `SCL` and `SDA` are the only lines connected to the monitor in normal operation
- Pi uses separate observation or GPIO-based sensing to determine bus-idle state
- when the Pi needs a transaction, a dedicated 2:1 `DDC` switch or mux moves monitor-side `DDC` ownership from source to Pi

Why it remains a valid fallback:

- it keeps the Pi electrically absent from the live monitor bus until needed
- it reduces dependence on Pi slave or listener behavior under Linux
- it may be electrically easier to reason about if the attached-listener approach proves noisy or awkward

Why it is not the current first-choice path:

- it consumes extra observation resources if clean idle detection is still required
- it gives up the opportunity to log ordinary host `DDC` traffic directly
- it is less aligned with the current desire to learn from live `DDC` traffic before finalizing the transport design

## Current Development Compromise

For development, a temporary sacrificial `HDMI` path is still acceptable.

That remains only a development compromise. It is not the approved final-system assumption.

## Deferred Detailed Decisions

Phase 5 selects the direction, but does not yet fully lock:

- exact `DDC` switch or mux part family
- exact `pin 18` source-selection implementation
- exact current-limit and fault-protection strategy for Pi-generated `+5V`
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
- the monitor answers `HDMI`-side `DDC` when no external computer is attached and monitor-side `pin 18` is driven from the Pi-generated `+5V` source
- source-side `pin 18` presence sensing is reliable and does not materially load the external source
- `pin 18` source selection does not backfeed or otherwise disturb the external computer
- takeover and release do not cause unacceptable display re-enumeration
- `HPD` behavior remains stable during normal operation
- the monitor's practical `HDMI` input remains usable for a real external source

## Outcome

Phase 5 now approves a clear hardware direction:

- not a passive `DDC` tap
- not permanent `HDMI` sacrifice as a final-system assumption
- not a full active `HDMI` proxy
- yes to switched `DDC` ownership with ordinary monitor `EDID` still reachable by the source, external `pin 18` presence sensing, selectable monitor-side `pin 18` source ownership, and careful `HPD` handling
