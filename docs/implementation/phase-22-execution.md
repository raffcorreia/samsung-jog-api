# Phase 22 Execution Record

## Purpose

Track **Phase 22: Physical Display and Pi Power Button** per [Implementation Plan](./plan.md).

## Status

**In progress.**

## Working Goal

Define and validate a physical local power-control path: a hardware button for display on/off and a practical strategy for physically waking or powering on the Raspberry Pi when software UI is unavailable.

## Key Questions to Resolve

1. What should one physical button do — display toggle only, or also Pi shutdown/wake?
2. How does Pi 5 handle a physical power button natively?
3. What is the equivalent path for Pi 2?
4. Single button or separate buttons for display vs Pi power?
5. How does the physical button relate to the existing software PowerMenu?

## Pi 5 — Native Power Button Interface

Raspberry Pi 5 has a dedicated **J2** 2-pin header (`PWR_BTN` / `GLOBAL_EN`) wired to the MxL7704 PMIC:

- **While running:** short press triggers a clean OS shutdown (PMIC signals halt)
- **While halted/off:** any press wakes and boots the Pi
- No software configuration required — behaviour is handled entirely by the PMIC and RP1 chip
- A momentary normally-open button across J2 is sufficient

This is the cleanest path: wire one button to J2 and the Pi handles shutdown and wake natively.

## Pi 2 — Power Button Interface

Raspberry Pi 2 has no PMIC or native power-button header. Available options:

| Option | What it does | Limitation |
|--------|-------------|------------|
| **RUN pin header** | Resets the CPU (equivalent to pulling RESET low) | Not a clean shutdown; does not wake from a software halt |
| **GPIO shutdown button** | GPIO + software daemon triggers clean shutdown | Cannot wake from halt — Pi is off, GPIO ISR is not running |
| **External power supervisor** | Always-on MCU or relay cuts/restores 5V to Pi | Requires additional always-on hardware circuit |
| **Operational limitation** | Document that Pi 2 must be woken by restoring USB-C power | No extra hardware needed; operator must physically unplug/replug |

## Decisions

_To be filled in during phase execution._

## GPIO Assignments (Phase 22 additions)

| Signal | GPIO (BCM) | Physical pin | Direction |
|--------|-----------|--------------|-----------|
| `display_btn` — display toggle button (active low) | GPIO4 | 7 | Input |
| `led_data` — WS2812B LED data out (SPI0 MOSI) | GPIO10 | 19 | Output |

GPIO10 (SPI0 MOSI) is used for WS2812B because Pi 5's RP1 chip does not expose the GPU DMA mailbox required by `rpi_ws281x`.  The SPI bus encodes each WS2812B bit as 4 SPI clock cycles at 3.2 MHz (312.5 ns/cycle), producing the required NRZ waveform entirely in hardware without root or DMA access.  SPI is accessible via `/dev/spidev10.0` on Pi 5.  On Pi 4 and earlier, SPI0 is at `/dev/spidev0.0` on the same GPIO10 pin — no wiring change needed between Pi generations.

## Component Designator Map (Phase 22 protoboard additions)

Continues the Phase 21 numbering (last used: Q9, R24, C4, no U or SW designators before this phase).

| Ref | Value | Function |
|-----|-------|----------|
| `SW1` | Momentary SPST NO | Display toggle button (GPIO4 → GND when pressed) |
| `R25` | 10 kΩ | GPIO4 hardware pull-up to 3.3V |
| `C5` | 100 nF | GPIO4 debounce cap to GND |
| `U2` | SN74AHCT125 (or equivalent) | 3.3V→5V level shifter, GPIO10 (SPI MOSI) → WS2812B DIN |

## Protoboard Wiring — Button Circuit

```
+3V3 (pin 1) ──── R25 (10 kΩ) ──── GPIO4 (pin 7) ──── SW1 ──── GND
                                         │
                                    C5 (100 nF)
                                         │
                                        GND
```

- R25: pull-up keeps GPIO4 HIGH when button is not pressed.
- SW1: connects GPIO4 to GND when pressed (active-low input).
- C5: debounce; 100 nF across GPIO4-GND smooths mechanical contact bounce.
- Software uses `gpiozero.Button(4)` with `pull_up=True` (internal + external pull-up).

## Protoboard Wiring — LED Level Shifter

```
GPIO10 (pin 19, SPI0 MOSI) ──── U2.A (3.3V IN)    U2.Y (5V OUT) ──── LED DIN
                                  U2.GND ──── GND
                                  U2.VCC ──── 5V (pin 2)

LED chain: DIN → LED1 → DOUT → (next LED DIN if chained)
LED GND → GND rail
LED 5V → 5V rail
```

- U1 level shifter: data-in at 3.3V logic (GPIO10 / SPI MOSI), data-out at 5V logic to WS2812B.
- Pi 5 uses SPI (not DMA/PWM) because RP1 has no GPU mailbox; `StatusLedService` uses `spidev` at 3.2 MHz.
- Each WS2812B bit is encoded as 4 SPI clock cycles (4-bit nibble: 1110='1', 1000='0').
- Chain is expandable: additional LEDs connect DOUT → DIN with no GPIO changes.

## PowerMenu Redesign

### Action Dialog

Replace the current two-option dialog (Display / Power off) with three options:

| Option | Size | Behavior |
|--------|------|----------|
| **Display only** | normal | toggle display on/off (existing path) |
| **Reset** | small | navigate to countdown screen (10 s) → reboot |
| **Power off** | small, dangerous | navigate to confirmation screen → countdown screen (10 s) → halt |

### Confirmation Screen (reusable)

Shown before Power off only. Text must explain that the deck **cannot be restored without physically unplugging and replugging power**. Screen must be implemented as a reusable component parameterized by message, confirm label, and on-confirm action.

### Countdown Screen (reusable — single component)

Single countdown component used by both Reset and Power off paths. Parameters:
- duration (10 s for both actions; previously may have been shorter)
- on-complete action (reboot | halt)
- cancelable (user can go back before countdown expires)

No duplicate countdown screens.

## Evidence Checklist

- ⬜ Pi 5 power button behavior defined and documented
- ⬜ Pi 2 power button strategy decided (or limitation documented)
- ⬜ Display on/off button wiring defined
- ⬜ Single vs separate buttons decided
- ⬜ Debounce and press-duration requirements defined
- ⬜ Physical button design does not conflict with GPIO24 display circuit
- ⬜ Integrated-board requirements updated
- ⬜ PowerMenu action dialog updated: Display / Reset / Power off with correct sizing
- ⬜ Power off confirmation uses existing `ConfirmDialog` component
- ⬜ Countdown screen is a single reusable component (10 s, parameterized)
- ⬜ Reset path: dialog → countdown → reboot works end-to-end
- ⬜ Power off path: dialog → confirmation → countdown → halt works end-to-end
- ⬜ WS2812B wired on GPIO10 (SPI0 MOSI, pin 19) via 3.3V→5V level shifter
- ⬜ `StatusLedService` implemented using `rpi_ws281x`
- ⬜ Healthy state (solid green) confirmed on hardware
- ⬜ `StatusLedService` integrated into service lifecycle
- ⬜ Host health gate passes
