---
name: Project Overview — samsung-jog-api-2
description: High-level goal, phase structure, current status, and Phase 7 architecture decisions
type: project
---

Hardware + software project to build a Raspberry Pi 2B-based control deck for a Samsung LC34J791WTNXZA (CJ791) ultrawide monitor. The monitor's only input mechanism is a physical JOG (joystick) on the rear. The goal is to electrically emulate the JOG via resistance-to-ground states on KEY_ADC1/KEY_ADC2 lines, observe KEY_LED feedback, maintain DDC/CI communication, and expose control through a local REST API + WebSocket with a React/TypeScript kiosk UI on a Waveshare 7" DSI display.

**Phase structure (20 phases, 0–19). Phases 0–6 design-complete. Phase 8 complete (see `docs/implementation/phase-8-execution.md`). Phase 7 KiCad/layout in progress. Current focus: Phase 9+. Phases 10–19 not started.**

**Hardware vs software sequencing:** Phase 8+ low-level software is brought up on the **Phase 6 GPIO map** first. When Phase 7 boards are fabricated, an **extra migration phase** will be inserted (slot TBD) to remap GPIO and retest software against the **Phase 7 pinout** — see `docs/implementation/plan.md` (“Deferred integrated-board GPIO and software migration”).

**Why:** Input switching on the CJ791 is cycle-through-inputs only. DDC alone can't switch; JOG alone can't read state. Both are needed together.

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
- Board 1: hardware/kicad/phase-7-controller-board/
- Board 2: hardware/kicad/phase-7-hdmi-ddc-board/

**Execution record:** docs/implementation/phase-7-execution.md

**Status as of 2026-04-11:** Execution record written. KiCad schematics in progress. PCB layout not yet done.
