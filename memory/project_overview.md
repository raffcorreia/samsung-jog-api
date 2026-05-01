---
name: Project Overview — samsung-jog-api-2
description: High-level goal, phase structure, current status, Phase 7 architecture decisions, and Phase 14 UI/log state
type: project
---

Hardware + software project to build a Raspberry Pi 2B-based control deck for a Samsung LC34J791WTNXZA (CJ791) ultrawide monitor. The monitor's only input mechanism is a physical JOG (joystick) on the rear. The goal is to electrically emulate the JOG via resistance-to-ground states on KEY_ADC1/KEY_ADC2 lines, observe KEY_LED feedback, maintain DDC/CI communication, and expose control through a local REST API + WebSocket with a React/TypeScript kiosk UI on a Waveshare 7" DSI display.

**Deck UI:** Phase 13 complete. Single-screen kiosk layout (**1280×800** target). Widgets use **fixed layout bands** so panels do not reflow when the log grows (log scrolls internally). Final Phase 13 geometry: top bar `48px`, left JOG column `350px`, bottom log band `200px`. Optional widget visibility is user-driven later — not implicit layout shift. Identity ("pi-deck") stays in the status/version area, not duplicated as nested marketing chrome around each control.

**Phase structure (28 phases, 0–27). Phases 0–6, 8–15, and 17–18 are closed. Phase 16 is parked because hardware access is unavailable for validation. Phase 7 KiCad/layout remains in progress. Phase 19 has not started.**

**Phase 13 UI state:** Full-screen deck shell is implemented and deployed (`0.1.0+r20`). The real JogPad remains the priority control and lives in the fixed left column. The clock uses `DSEG7 Classic` seven-segment font, enlarged and vertically centered without increasing the `48px` top bar. Settings cog is top-right. LED is an 8mm-style gray default indicator and should turn blue only for future blink/feedback events, not for steady backend `key_led_active`. Record control exists as a visual/logging stub in the upper-right of the JOG column. Calendar, notes, settings, and OSD popup are realistic stubs/placeholders for later phases.

**Phase 14 log state:** Backend-owned live logging is implemented and deployed (`0.1.0+r22`). `LiveLogService` owns the `220`-entry replay buffer and emits structured `log/entry` WebSocket events. New clients receive replayed history immediately; multiple clients receive the same live stream. Frontend log code no longer formats command/control/bus events into local history.

**Phase 16 state:** Recording and replay subsystem code is complete and merged to main. Recording workspace popup, sequence runner, upload/download/edit, and replay UI are all implemented. Hardware validation (on-device recording/replay runs, KEY_ADC2 stall visibility during long captures) is still pending, but the phase is parked because hardware access is unavailable.

**Phase 17 state:** Closed on 2026-04-20 with a crude open support to hold the monitor/control-deck hardware together. This is intentionally not a polished enclosure or detailed mechanical design.

**Phase 18 state:** Closed on 2026-04-22. Waveshare 7" DSI display and touch are working on the Pi 2 deck host. Safe maximum brightness is `170/255`. HDMI visual output destabilized DSI scanout on this stack, so HDMI is disabled as a Linux display with `video=HDMI-A-1:d` and retained for DDC/CI communication only. DDC/CI Get VCP `0x60` succeeded on HDMI DDC while DSI/touch and ADS observation remained active.

**Phase 19 state:** Planned next. Display usability and power hardening: functional display/Pi power menu, capped brightness control, display color/edge validation page, and documentation of display power-off behavior.

**Log / event hygiene (backlog):** WebSocket and derived log traffic may feel excessive or not representative of what operators care about (duplicate `bus/snapshot` with `deck_control`, telemetry poll cadence, verbosity of `command`/`control` lines). Plan a later pass to coalesce, filter, or re-level categories so the live log stays readable without losing auditability.

**Active defect:** `KEY_ADC2` live observation has stalled twice across Phase 15/16 work. In the later case, redeploying the app restored directional observation without changing wiring. Treat this as an unresolved observation-path/runtime defect, not a closed protoboard-only issue.

**Hardware vs software sequencing:** Phase 8+ low-level software is brought up on the **Phase 6 GPIO map** first. When Phase 7 boards are fabricated, an **extra migration phase** will be inserted (slot TBD) to remap GPIO and retest software against the **Phase 7 pinout** — see `docs/implementation/plan.md` ("Deferred integrated-board GPIO and software migration").

**Why:** Input switching on the CJ791 is cycle-through-inputs only. DDC alone can't switch; JOG alone can't read state. Both are needed together.

## Phase 7 Build Path

The original Phase 7 intent was a home-built board using through-hole transistors, resistors, and capacitors (except the ADS1115 which was always SMD). That path is still valid. The KiCad/PCBWay route with SMD components and proper OpAmps is an exciting upgrade opportunity that emerged during design, not a replacement for the original plan. Either path closes Phase 7 — the choice depends on how far the PCBWay enthusiasm carries through layout completion.

**Why:** Keeping the through-hole option alive avoids blocking the project on PCB fabrication if motivation or timeline shifts.

## Phase 7 Architecture (settled as of 2026-04-11)

**Two-board design:**
- Board 1 (Controller): Phase 3 + Phase 4 merged. JST PH 2.0mm 4-pin monitor harness, 2×20 IDC Pi header, 2×7 IDC inter-board connector.
- Board 2 (HDMI DDC): Phase 5 unchanged except J3 replaced with 2×7 IDC inter-board header.

**Connectors:**
- Monitor harness: JST PH 2.0mm 4-pin (B4B-PH-K-S, C157929 at JLCPCB). 30AWG 4-core cable.
- Pi interface: 2×20 shrouded IDC box header + 40-pin ribbon cable.
- Inter-board: 2×7 shrouded IDC box header + 14-pin ribbon cable (pre-made IDC cables).

**Power:** Pi powered by its own 3A micro-USB supply. Pi GPIO rails power boards (no onboard regulation on boards). Pi 2B + Waveshare 7" DSI + USB WiFi + boards = ~1.82A, well within 3A supply.

**GPIO (17 signals used, 9 free):**
- GPIO2/3: I2C SDA/SCL (fixed)
- GPIO17,27,22,23,24: ADC2_LEFT/RIGHT/DOWN/UP_EN, ADC1_CENTER_EN (outputs)
- GPIO25: PI_DDC_DISC_REQ (output)
- GPIO5: MON_5V_DISABLE (output)
- GPIO6,12,13: KEY1_IN_GPIO, LED_IN_GPIO, ADC_ALERT (inputs)
- GPIO19,16,26,20,21: DDC_READY, SRC_5V_SENSE, RESERVED, PIN18_STAT, HPD_SENSE (inputs)

**Passives:** All 0603 metric throughout both boards.

**Peripherals:**
- Waveshare 7" DSI LCD (E), 1280×800 (~700mA)
- USB WiFi adapter (~300mA)
- Logitech USB dongle (development only, ~100mA)

**KiCad files location:**
- Board 1: hardware/kicad/controller-board/
- Board 2: hardware/kicad/hdmi-ddc-board/

**Execution record:** docs/implementation/phase-7-execution.md

**Status as of 2026-04-11:** Execution record written. KiCad schematics in progress. PCB layout not yet done.
