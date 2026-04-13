# Phase 8 Execution Record

**Status: COMPLETE** (as of 2026-04-12)

## Purpose

This document records execution for **Phase 8: GPIO assignment and low-level control prototype**, using the **Phase 6 discrete protoboard** pin map until integrated Phase 7 hardware exists (see [Implementation Plan — deferred migration](./plan.md#deferred-integrated-board-gpio-and-software-migration)).

## Reference

- GPIO map: [Phase 6 Execution Record](./phase-6-execution.md) (Raspberry Pi Pin Map)
- Software package: `backend/src/pi_deck/` (import name **`pi_deck`**; install with `pip install -e backend/` from the repository root; project file `backend/pyproject.toml`)

## Host platform (validated)

| Item | Value |
|------|--------|
| Board | Raspberry Pi 2B |
| OS | `PRETTY_NAME` / `os-release`: Raspbian GNU/Linux **13 (trixie)**, `VERSION_ID=13`, `DEBIAN_VERSION_FULL=13.4` (user also referenced Raspberry Pi OS Bookworm Lite as the base image where applicable) |

## Hardware setup (validated)

| Item | Result |
|------|--------|
| Protoboard | **Phase 6 schematic as documented** — discrete build matches the Phase 6 design intent |
| Monitor | Samsung CJ791 **powered** and connected **directly over HDMI** (no Phase 5 intermediary in this path) |
| Raspberry Pi | **Not yet connected** to the protoboard drive/observation harness for jog tests at closure of this record |

## Low-level jog behavior (bench)

Validation was performed by **manually actuating the drive transistors** (bench trigger at the transistor side), **not** yet via GPIO from the Raspberry Pi.

| Question | Answer |
|----------|--------|
| All directions work? | **Yes** — center, up, down, left, right behave as expected at the monitor |
| Default pulse width (ms) | **Not characterized numerically here.** Short manual pulses were sufficient; **precise press/hold/release timing** is deferred to runs where **software can record** timestamps (later recording / tooling phase), so measurements are repeatable |
| Hold / repeat | **Yes** — **repeat engages after ~1 s** (approximate) |
| Direction changes | **Must release one direction before starting another.** If directions overlap, the **analog path behavior changes completely** — the control stack must treat outputs as **mutually exclusive** (never drive two legs at once) |

## Digital inputs — question 8 rephrased

The earlier question was: *when the Pi reads `KEY_ADC1` and `KEY_LED` with `sjog-phase8-probe read-ins`, do the gpiozero “active” readings match what you see electrically (idle vs pressed)?*

**Answer:** Not exercised yet — the **Pi was not connected** to these lines at validation time, and **no software defaults were changed** (see below). This check is an **immediate next step** once the Pi is wired to the protoboard.

## Software defaults (unchanged)

- No changes were made to pull-up / polarity handling in code; defaults stand until the Pi is on the harness.

## ADS1115 (`KEY_ADC2`)

| Item | Decision |
|------|----------|
| AIN channel | **AIN0** — matches current wiring; **no change recommended** unless the schematic moves `KEY_ADC2` to another input |
| Idle vs active mV | **Not measured yet** — to be captured under software-controlled sampling |
| ALERT/RDY (GPIO17) | **Wired**; **intended to be used** — module `ads_alert_observe` + CLI `read-alert` provided for bring-up |

## `sjog-phase8-probe` (what it is for)

Low-level **smoke tests** on real GPIO and I²C (Pi + Phase 6 harness). **How to install and run it** (entry points, prerequisites, subcommands, troubleshooting) is defined in the project as a runbook: **[Phase 8 bench probe — execution definition](../runbooks/phase8-probe.md)**.

**Status at Phase 8 closure:** **Not run on-device yet** — operator focused on **manual transistor-level** proof; **Pi-attached runs** are the next software milestone.

## Code modules (repository)

- **Pins / actions**: `pi_deck.hardware.phase6_pins` — `Phase6Pins`, `JogAction`
- **Drive outputs**: `pi_deck.hardware.jog_drive` — `Phase6JogDrive` (active-high; **only one direction at a time** — enforced by `release_all` before `hold` / `pulse`)
- **Digital observation**: `jog_observe` (`KEY_ADC1`), `led_observe` (`KEY_LED`)
- **ADS1115 ALERT**: `ads_alert_observe` (`GPIO17`)
- **Analog observation**: `ads1115` — `Ads1115.read_single_ended_mv`
- **Bench CLI**: `sjog-phase8-probe` → `pi_deck.cli.phase8_probe` (see above)

## Bench validation checklist

- [x] Each logical jog **direction** is interpreted correctly by the monitor **via the analog drive path** (manual bench actuation)
- [x] **Repeat / hold** behavior observed (~**1 s** to repeat, approximate)
- [x] **Mutual exclusion** between directions documented (release before next; no combined drive)
- [ ] **Pi-driven** `sjog-phase8-probe` / GPIO — **pending** (next implementation step)
- [ ] **Precise** ms timing table — **deferred** to software-instrumented capture
- [ ] **ADS1115** mV baselines — **deferred** to logged sampling
- [ ] **Regression tests** in CI — **deferred** (hardware-dependent; mocks later)

## Exit-criteria assessment

**Phase 8 is complete** as of **2026-04-12** with this scope:

- **Met:** Phase 6 protoboard matches schematics; HDMI direct; **all five directions** validated at the monitor using the **custom hardware path**; **repeat delay** and **mutual-exclusion** operating rules captured; **AIN0** wiring called out; **ALERT** wired and software hooks started.
- **Explicitly out of scope for this closure:** Sub-millisecond **timing tables**, **ADS1115** voltage baselines, and **Pi-attached** GPIO/I²C verification — tracked as **immediate follow-on work** (software development and on-Pi `sjog-phase8-probe` runs).

This matches the intent to **move on to software development** while keeping the record honest about what was proven on the bench versus what remains to be exercised from the Pi.

## Follow-on work (Phase 9+ software; not required to re-open Phase 8)

1. Connect the **Raspberry Pi** to the Phase 6 harness per the pin map.
2. Run **`sjog-phase8-probe`** (`pulse`, `read-ins`, `read-alert`, `read-ads`) and adjust **digital polarity / pull** only if the schematic’s conditioning disagrees with gpiozero defaults.
3. Implement **application-level** drive and observation (mutual exclusion, optional **ALERT**-driven sampling) and add **instrumented timing** when recording tooling exists.
