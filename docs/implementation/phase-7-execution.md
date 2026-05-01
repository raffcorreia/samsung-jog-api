# Phase 7 Execution Record

## Purpose

This document records the execution outcome for `Phase 7: Integrated Controller Board Design`.

It complements:

- [Implementation Plan](../implementation/plan.md)
- [Solution Overview](../design/solution-overview.md)
- [Phase 3 Execution Record](./phase-3-execution.md)
- [Phase 4 Execution Record](./phase-4-execution.md)
- [Phase 5 Execution Record](./phase-5-execution.md)
- [Phase 6 Execution Record](./phase-6-execution.md)

## Goal

Combine the validated outputs of Phase 3 (observation), Phase 4 (drive), Phase 5 (`HDMI` / `DDC`), and Phase 6 (protoboard reference) into two manufacturable controller board designs ready for `JLCPCB` fabrication.

## Reference Artifacts

- Board 1 schematic: [`hardware/kicad/controller-board/controller-board.kicad_sch`](../../hardware/kicad/controller-board/controller-board.kicad_sch)
- Board 1 PCB: [`hardware/kicad/controller-board/controller-board.kicad_pcb`](../../hardware/kicad/controller-board/controller-board.kicad_pcb)
- Board 2 schematic: [`hardware/kicad/hdmi-ddc-board/hdmi-ddc-board.kicad_sch`](../../hardware/kicad/hdmi-ddc-board/hdmi-ddc-board.kicad_sch)
- Board 2 PCB: [`hardware/kicad/hdmi-ddc-board/hdmi-ddc-board.kicad_pcb`](../../hardware/kicad/hdmi-ddc-board/hdmi-ddc-board.kicad_pcb)

## Two-Board Architecture Decision

Phase 7 produces two physically separate boards that connect to each other via an inter-board header:

- **Board 1 — Controller Board**: merges the Phase 3 observation circuit and Phase 4 analog drive circuit onto one `PCB`. Interfaces directly with the `Raspberry Pi` via a `40-pin IDC` ribbon cable.
- **Board 2 — HDMI DDC Board**: carries the Phase 5 `HDMI` / `DDC` intermediary circuit unchanged, with its Pi-side header replaced by an inter-board connector that plugs into Board 1.

Board 2 connects to Board 1 via a `2×7 IDC` ribbon cable. Board 1 is the hub: it receives all power and signals from the Pi and distributes the `HDMI`-board subset to Board 2.

Phase 6 is reference only. Its discrete-transistor protoboard was the proof of concept. The integrated boards use the `IC`-based architectures from Phases 3, 4, and 5.

## Host Platform

- **Model**: Raspberry Pi 2B
- **GPIO header**: 40-pin, identical pinout to Pi 3B/4B/5
- **Power input**: micro-USB, 3A supply
- **Peripherals in production**:
  - Waveshare 7-inch DSI LCD (E), 1280×800, capacitive IPS — powered via Pi DSI
  - USB WiFi adapter — ~300 mA
- **Peripherals during development only**:
  - Logitech USB dongle (keyboard/mouse receiver) — ~100 mA

## Power Architecture

The Pi is powered by its own 3A micro-USB supply. Boards 1 and 2 draw from the Pi's GPIO rails. No external supply or onboard regulation is added to either board.

Consider adding a board-level power-enable / power-off control for the custom controller hardware, so a dedicated GPIO can disable the board completely when low if the design needs a hard off state.

### Display 5V switching — PCB design requirement

Phase 18/19 measurements established the display power breakdown:

| State | Current | Notes |
|-------|---------|-------|
| Pi on, display disconnected | 0.32 A | Pi-only baseline |
| Pi on, display software-off | 0.42 A | +0.10 A display always-on electronics |
| Pi on, display at 30% brightness | 0.59 A | +0.17 A backlight LEDs |

The Waveshare DSI display is currently powered directly from the Pi GPIO header's 5V pin. This creates two problems:

1. **Software cannot cut the always-on 0.10 A draw** — the DSI controller, Goodix touch IC (`/dev/i2c-10`), and panel regulators are live as long as the 5V line is present, regardless of software state.
2. **Hot-reconnection resets the Pi** — reconnecting the display power pin causes a voltage transient on the Pi's own 5V rail sufficient to trigger a brownout reset. Safe display power cycling is not possible with the current point-to-point wiring.

**Requirement for the PCB:** route the display's 5V supply through a GPIO-controlled high-side switch rather than directly from the Pi header pin. A P-channel MOSFET driven by a Pi GPIO via an NPN transistor is the standard approach for 5V load switching. This would:

- Allow software to fully cut display power (recovering the ~0.10 A always-on draw)
- Isolate the Pi's 5V rail from display connection transients, eliminating the reset risk
- Enable controlled power sequencing on startup and shutdown

`GPIO26` (`RESERVED_GPIO`, physical pin 37) is available for this purpose.

### Power Budget

| Consumer | Current |
|---|---|
| Raspberry Pi 2B under load | ~800 mA |
| Waveshare 7" DSI display | ~700 mA |
| USB WiFi adapter | ~300 mA |
| Board 1 + Board 2 combined | ~15 mA |
| Logitech dongle (dev only) | ~100 mA |
| **Total (production)** | **~1,815 mA** |
| **Total (development)** | **~1,915 mA** |

A 3A supply provides over 1A of headroom in both configurations.

### Power Rail Distribution

- `+3V3`: Pi GPIO pin 1 (and pin 17) → Board 1 → all logic ICs on Board 1 → also forwarded to Board 2 via J3 for `PCA9306 VREF1`.
- `+5V`: Pi GPIO pin 2 (and pin 4) → Board 1 → forwarded to Board 2 via J3 for `TCA4307 VCC`, `PCA9306 VREF2`, and `TPS2113A IN2`.
- `GND`: Pi GPIO pins 6, 9, 14, 20, 25, 30, 34, 39 → Board 1 → forwarded to Board 2 via J3.
- Board 2 also receives `HDMI_5V_SRC` from the HDMI source cable's pin 18 (handled internally by `TPS2113A`).

## GPIO Assignment

All 17 signals mapped to BCM GPIO numbers. I2C is fixed at GPIO2/GPIO3. UART pins (GPIO14, GPIO15) and SPI pins (GPIO7–GPIO11) are left free for future use.

| Pi Physical Pin | BCM GPIO | Signal | Direction | Function |
|---|---|---|---|---|
| 3 | GPIO2 | I2C_SDA | Bidirectional | I2C data (ADS1115 + PCA9306) |
| 5 | GPIO3 | I2C_SCL | Bidirectional | I2C clock |
| 11 | GPIO17 | ADC2_LEFT_EN | Pi output | Enable KEY_ADC2 left drive |
| 13 | GPIO27 | ADC2_RIGHT_EN | Pi output | Enable KEY_ADC2 right drive |
| 15 | GPIO22 | ADC2_DOWN_EN | Pi output | Enable KEY_ADC2 down drive |
| 16 | GPIO23 | ADC2_UP_EN | Pi output | Enable KEY_ADC2 up drive |
| 18 | GPIO24 | ADC1_CENTER_EN | Pi output | Enable KEY_ADC1 center drive |
| 22 | GPIO25 | PI_DDC_DISC_REQ | Pi output | Disconnect DDC source path |
| 29 | GPIO5 | MON_5V_DISABLE | Pi output | Control TPS2113A enable |
| 31 | GPIO6 | KEY1_IN_GPIO | Pi input | KEY_ADC1 digital state |
| 32 | GPIO12 | LED_IN_GPIO | Pi input | KEY_LED digital state |
| 33 | GPIO13 | ADC_ALERT | Pi input | ADS1115 ALERT/RDY interrupt |
| 35 | GPIO19 | DDC_READY | Pi input | TCA4307 READY state |
| 36 | GPIO16 | SRC_5V_SENSE | Pi input | HDMI source present |
| 37 | GPIO26 | RESERVED_GPIO | TBD | Reserved for future use |
| 38 | GPIO20 | PIN18_STAT | Pi input | TPS2113A mux status |
| 40 | GPIO21 | HPD_SENSE | Pi input | HPD state sense |

Free GPIO pins (not allocated): GPIO7, GPIO8, GPIO9, GPIO11, GPIO14, GPIO15, GPIO18 (7 free).
Note: GPIO4 (display toggle button, Ph.22) and GPIO10 (WS2812B LED SPI MOSI, Ph.22) are now assigned; GPIO24 (display_power_en, Ph.21) was already assigned.

## Connector Strategy

### Monitor Bus — J1 (Board 1)

**JST PH 2.0mm, 4-pin, through-hole (`B4B-PH-K-S(LF)(SN)`)**

The monitor cable is `30 AWG`, 4-core. `JST PH` is rated `26–32 AWG` and is therefore the correct crimp family for this wire gauge. Pre-made `JST PH` 4-pin cables are available on Amazon and AliExpress with the housing already assembled; the user solders the cable ends to the existing monitor harness.

| Pin | Net | From |
|---|---|---|
| 1 | GND | CN1001 pin 1 |
| 2 | KEY_ADC2_BUS | CN1001 pin 2 |
| 3 | KEY_ADC1_BUS | CN1001 pin 3 |
| 4 | KEY_LED_BUS | CN1001 pin 4 |

### Pi Host Interface — J2 (Board 1)

**2×20 shrouded IDC box header, 2.54mm pitch (`IDC-Header_2x20_P2.54mm_Vertical`)**

Connects to the Pi's 40-pin GPIO header via a standard 40-pin IDC ribbon cable (pre-made cables widely available). Board routes only the 17 signals it uses. The remaining 23 pin positions on the header are electrically unconnected on the board.

### Inter-Board Connection — J3 (Board 1) and J_CTRL (Board 2)

**2×7 shrouded IDC box header, 2.54mm pitch (`IDC-Header_2x07_P2.54mm_Vertical`)**

Both boards carry a matching 2×7 IDC header (14 pins). A 14-pin IDC ribbon cable with pre-made IDC snap-on connectors connects the two boards. Cables and IDC connectors are available pre-made on Amazon; no crimp tool is required for IDC assembly.

| Pin | Net | Notes |
|---|---|---|
| 1 | +5V | From Pi J2 pin 2 |
| 2 | +3V3 | From Pi J2 pin 1 |
| 3 | GND | |
| 4 | I2C_SCL | Shared I2C bus |
| 5 | I2C_SDA | Shared I2C bus |
| 6 | PI_DDC_DISC_REQ | Pi output → Board 2 Q1 gate |
| 7 | MON_5V_DISABLE | Pi output → Board 2 TPS2113A EN |
| 8 | SRC_5V_SENSE | Board 2 → Pi input |
| 9 | DDC_READY | Board 2 TCA4307 READY → Pi |
| 10 | PIN18_STAT | Board 2 TPS2113A STAT → Pi |
| 11 | HPD_SENSE | Board 2 HPD divider → Pi |
| 12 | RESERVED_GPIO | TBD |
| 13 | GND | Spare |
| 14 | NC | Spare |

## Component and Passive Standardization

All resistors and capacitors on both boards use **0603** metric footprints:

- Resistors: `Resistor_SMD:R_0603_1608Metric`
- Capacitors: `Capacitor_SMD:C_0603_1608Metric`

`0603` is the smallest footprint with broad `JLCPCB` stock coverage and acceptable hand-rework accessibility. Phase 3 used `0402`; Phase 7 upgrades all passives to `0603`.

## Board 1 — Component List

| RefDes | Value | Function | JLCPCB Part | Type |
|---|---|---|---|---|
| U1 | TLV9064IDR | Quad op-amp observation buffer | C388176 | Extended |
| U2 | ADS1015IDGSR | 12-bit 4-channel I2C ADC for KEY_ADC2 | C193969 | Extended |
| U3 | 74LVC1G17GW | Schmitt buffer KEY_ADC1 → GPIO | C426705 | Extended |
| U4 | 74LVC1G17GW | Schmitt buffer KEY_LED → GPIO | C426705 | Extended |
| U5 | MC74HC4066ADR2G | Quad analog switch, KEY_ADC2 drive | C233612 | Extended |
| U6 | 74LVC1G66LT05ARCQ | Single analog switch, KEY_ADC1 center | C46553572 | Extended |
| J1 | JST PH 4-pin | Monitor harness CN1001 | C157929 (B4B-PH-K-S) | — |
| J2 | IDC 2×20 | Pi 40-pin GPIO header | Manual THT | — |
| J3 | IDC 2×7 | Inter-board to Board 2 | Manual THT | — |
| R1, R2, R3 | 10k 1% 0603 | Sense protection resistors | C25804 | Basic |
| R4, R5 | 4.7k 1% 0603 | I2C pull-ups | C23162 | Basic |
| R6, R7 | 0 (DNP) 0603 | Optional buffer-to-ADC jumpers | C21189 | Basic |
| R8 | 30k 1% 0603 | KEY_ADC2 LEFT | C22984 | Basic |
| R9 | 10k 1% 0603 | KEY_ADC2 RIGHT | C25804 | Basic |
| R10 | 3.3k 1% 0603 | KEY_ADC2 DOWN | C22978 | Basic |
| R11 | 22k 1% 0603 | KEY_ADC2 UP | C31850 | Basic |
| R12 | 22k 1% 0603 | KEY_ADC1 CENTER | C31850 | Basic |
| R13–R17 | 100k 1% 0603 | Enable default-off pull-downs | C25803 | Basic |
| C1 | 1u 0603 | Bulk +3V3 decoupling | C15849 | Basic |
| C2–C7 | 100n 0603 | Per-IC local decoupling | C14663 | Basic |
| C8, C9, C10 | 1n 0603 | Sense line RC filters | C1588 | Basic |

> **U5 note**: Original choice MC74HC4066ADTR2G (C233537, TSSOP-14) was out of stock. Replaced with MC74HC4066ADR2G (C233612, SOIC-14). Schematic footprint updated to `Package_SO:SOIC-14_3.9x8.7mm_P1.27mm`.
>
> **U6 note**: C46553572 confirmed as SOT-23-5 at JLCPCB. Schematic footprint `Package_TO_SOT_SMD:SOT-23-5` is correct.

## Board 2 — Changes from Phase 5

Board 2 is Phase 5's `HDMI DDC Intermediary` schematic with a single connector substitution:

- **Removed**: `J3` as `Custom:Conn_01x12_Simple` (1×12 Pi direct header)
- **Added**: `J3` as `Custom:Conn_02x07_Simple` (2×7 IDC inter-board header, pins 1–12 net assignments identical to Phase 5's original J3)

All other components, nets, and circuit function are unchanged. See Phase 5 execution record for full circuit description.

Board 2 component list is identical to Phase 5 BOM. See [`docs/hardware/hdmi-ddc-transport.md`](../hardware/hdmi-ddc-transport.md).

## I2C Bus Sharing

The `ADS1115` (Board 1) and `PCA9306` (Board 2) share the same `I2C` bus (`I2C_SDA` / `I2C_SCL`). The bus is pulled up on Board 1 via R4 and R5 (4.7kΩ to +3V3). `PCA9306` is a transparent bidirectional level translator and does not have its own I2C address. `ADS1115` address is `0x48` (ADDR tied to GND).

The `I2C_SCL` and `I2C_SDA` nets on Board 1 connect to both `U2` (ADS1115) and `J3` pins 4–5, which forward them to Board 2's `PCA9306`.

## Estimated Board Dimensions

Board 1 target: approximately **55 × 40 mm**. Dominated by the 2×20 IDC header footprint (~51mm long).
Board 2 target: approximately **50 × 35 mm**. Dominated by two horizontal HDMI receptacles.

## Open Items Before Fabrication

- Complete PCB layout for both boards in KiCad GUI (component placement, copper routing, ground pours)
- Run KiCad GUI DRC on both boards before submitting to `JLCPCB`
- Validate `U5` (`MC74HC4066`) on-resistance contribution at 3.3V supply against the resistance divider values to confirm JOG classification accuracy
- Define and document board mounting hole positions and mechanical constraints
- Define inter-board cable length based on final physical enclosure layout
- Decide whether the custom board should include a GPIO-controlled global power switch so the entire board can be forced off when an enable pin is low
- **Add GPIO-controlled high-side switch for display 5V** — route the Waveshare DSI display 5V through a P-channel MOSFET (NPN-driven gate) controlled by `GPIO26`. Required to enable full software display power-off and to eliminate the Pi brownout-reset risk on display reconnection. See Power Architecture section for measurements and circuit rationale.
- **Add WS2812B status LED circuit** — GPIO10 (SPI0 MOSI, pin 19) drives a single WS2812B LED directly at 3.3V logic (no level shifter; validated in Phase 22). The LED requires a 5V supply rail and a direct data line from GPIO10. The SN74AHCT125 level shifter originally planned was removed after it caused frame corruption. Include a 10 kΩ pull-down on GPIO10/MOSI to keep the line LOW when SPI is idle. See Phase 22 execution record for full wiring details and StripDriver SPI encoding spec.
- **Add SW1 display toggle button circuit** — GPIO4 (pin 7), active-low, with R25 (10 kΩ pull-up to 3.3V) and C5 (100 nF debounce cap to GND). Validated on protoboard in Phase 22.

## Exit-Criteria Assessment

Phase 7 is complete when:

- Both board schematics pass `kicad-cli sch erc` with 0 errors
- Both board PCBs pass KiCad GUI DRC with 0 errors
- All components resolve to `JLCPCB`-orderable part numbers
- Manufacturing artifacts (Gerbers, BOM, position files) are exported and verified
