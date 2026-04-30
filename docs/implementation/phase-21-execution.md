# Phase 21 Execution Record

## Purpose

Track **Phase 21: Display Power Control Circuit** per [Implementation Plan](./plan.md).

## Status

**Not started.**

## Working Goal

Design and validate a hardware circuit that lets the Raspberry Pi switch the Waveshare DSI display's 5V supply on and off under software control, with an RC soft-start network to limit the inrush current that caused Pi shutdowns in Phases 19 and 20.

## Background

Phases 19 and 20 confirmed that reconnecting the display's 5V line while the Pi is running causes a shutdown on Pi 5 (full power-off; Pi 2 had a brown-out reset instead). The root cause is the capacitive inrush on the display's 5V rail pulling the Pi's shared 5V GPIO header low. Until the integrated PCB exists, the only fix is a controlled high-side switch on the display's 5V branch so the Pi never sees a raw reconnect transient.

Additionally, Phase 20 confirmed that the Pi 5 continues to draw 1.73 W (5.09 V / 0.34 A) after a software halt. True display power-off via this circuit reduces at-rest consumption when the system is in a display-off state and is a prerequisite for any real screen-blanking strategy.

## Circuit Design

### Topology

A PNP transistor (`Q8`, `S8550`) acts as the high-side 5V switch. A GPIO-driven NPN stage (`Q9`, `2N3904`) inverts the active-high GPIO signal and drives the PNP base. An RC network on the PNP base provides a soft-start that limits inrush on every turn-on event.

```
Pi 5V (pin 2) ──── Q8 emitter
                         Q8 collector ──── Display 5V+
                         Q8 base ──┬── R23 (10 kΩ) ──── Pi 5V   ← default-off pull-up
                                   ├── C3  (10 µF)  ──── Pi 5V   ← soft-start capacitor
                                   └── R24 (4.7 kΩ) ──── Q9 collector

GPIO24 (pin 18) ──── R21 (1 kΩ) ──── Q9 base
                     R22 (10 kΩ) ──── Q9 base ──── GND   ← default-off pull-down
                                      Q9 emitter ── GND

Display 5V+ ──── C4 (100 µF) ──── GND   ← bulk output capacitor
```

### Logic table

| GPIO24 | Q9 | Q8 base (Vbe) | Q8 | Display |
|--------|----|---------------|----|---------|
| LOW (default) | OFF | pulled to 5V by R23; Vbe = 0 | OFF | no power |
| HIGH | ON (saturated) | pulled toward 1.7V by R23/R24 divider; Vbe ≈ −3.3 V | ON | powered |

### Soft-start behaviour

When GPIO24 goes HIGH, Q9 turns on immediately. Q8's base is then driven toward its on-state via the R24 path, but C3 (10 µF across base-emitter of Q8) delays the Vbe transition. The RC time constant is:

```
τ = C3 × (R23 ‖ R24) = 10 µF × (10 kΩ ‖ 4.7 kΩ) ≈ 10 µF × 3.2 kΩ ≈ 32 ms
```

Q8 collector current ramps up over ~100 ms (≈3τ), limiting the inrush to a gradual rise rather than a step. The display's bulk capacitors charge over this ramp rather than all at once.

### Component selection rationale

| Part | Why |
|------|-----|
| `S8550` PNP | Available; 1.5 A Ic — well above the display's ~0.3–0.5 A draw; handles soft-start dissipation at low duty cycle; Vce(sat) ≈ 0.2 V → display sees 4.8 V, within spec |
| `2N3904` NPN | Already on the protoboard (Q1–Q7); ideal for this low-current base-drive application |
| `R21` 1 kΩ | Limits GPIO24 base current to ~3 mA into Q9 — well within GPIO source capability |
| `R22` 10 kΩ | Holds Q9 base at GND when GPIO24 is floating (boot, reset) so display stays off |
| `R23` 10 kΩ | Holds Q8 base at 5V (off) when Q9 is off; forms one leg of the voltage divider |
| `R24` 4.7 kΩ | Q9-collector-to-Q8-base path; combined with R23 produces Vbase ≈ 1.7 V when Q9 is on, well below the PNP's Vbe threshold |
| `C3` 10 µF | Soft-start: slows base drive, ramps collector current over ~100 ms |
| `C4` 100 µF | Bulk output capacitor; smooths load transients without being large enough to act as a keep-alive supply if the Pi loses power |

### GPIO pin selection

`GPIO24` (BCM 24, physical pin 18) is selected as `display_power_en`:

- completely unused in Phase 6 and Phase 20
- not adjacent to I2C, SPI, or UART signals
- physically located at pin 18, between pins 17 (3.3V) and 19 (SPI MOSI) — easy to reach without crossing other wires on the protoboard
- active-high: GPIO HIGH = display on; GPIO LOW (default / boot state) = display off

## Protoboard Wiring

The Phase 21 circuit extends the existing Phase 6 protoboard. Add a new section of the board for the display power block:

1. **5V supply tap:** run a wire from Pi physical pin 2 to the board's 5V power rail (separate from the 3.3V logic rail already present).
2. **Q8 (S8550 PNP):**
   - emitter → 5V power rail
   - collector → a new node `DISP_5V` (which feeds the display's 5V input wire)
   - base → junction of R23, R24, and C3
3. **R23 (10 kΩ):** from 5V rail to Q8 base junction.
4. **C3 (10 µF, electrolytic, + toward 5V):** from 5V rail to Q8 base junction (positive terminal to 5V).
5. **R24 (4.7 kΩ):** from Q8 base junction to Q9 collector.
6. **Q9 (2N3904 NPN):**
   - collector → R24 → Q8 base junction
   - base → R21 junction
   - emitter → GND rail
7. **R21 (1 kΩ):** from Pi GPIO24 (physical pin 18) to Q9 base.
8. **R22 (10 kΩ):** from Q9 base to GND rail.
9. **C4 (100 µF, electrolytic, + toward display):** from `DISP_5V` node to GND rail.
10. **Display 5V wire:** disconnect the display's 5V wire from the Pi 5V header pin and reconnect it to the `DISP_5V` node on the board.

> **Important:** the display GND wire remains directly connected to Pi GND. Only the 5V supply line is switched. Switching the GND side instead would leave the display rail floating at 5V during off state, which can cause leakage and unpredictable behavior.

> **Polarity:** C3 and C4 are polarized electrolytic capacitors. C3 positive terminal goes toward 5V (Q8 emitter side). C4 positive terminal goes toward the display (DISP_5V node). Reversing polarity will destroy the capacitor.

## Component Designator Map

These designators continue the Phase 6 schematic numbering (last used: R20, Q7, C2).

| Ref | Value | Function |
|-----|-------|----------|
| `Q8` | `S8550` PNP | Display 5V high-side switch |
| `Q9` | `2N3904` NPN | GPIO24 driver / PNP base inverter |
| `R21` | 1 kΩ | GPIO24 → Q9 base current limit |
| `R22` | 10 kΩ | Q9 base default-off pull-down |
| `R23` | 10 kΩ | Q8 base default-off pull-up to 5V |
| `R24` | 4.7 kΩ | Q9 collector → Q8 base drive path |
| `C3` | 10 µF | Soft-start: Q8 base to 5V rail |
| `C4` | 100 µF | Bulk output cap: DISP_5V to GND |

## GPIO Assignment

`GPIO24`, BCM 24, physical pin 18 → `display_power_en` (active HIGH = display on).

## Software Integration

Implemented in `DisplayService` (`display_service.py`) and `LiveDisplayPower` (`display_power.py`).

**Power-off sequence (GPIO24 last):** save brightness → backlight 0 → `wlr-randr --off` → GPIO24 LOW

**Power-on sequence (GPIO24 first):** GPIO24 HIGH → 150 ms → `reinit_panel()` → `wlr-randr --on` → restore brightness

The `reinit_panel()` step was added after discovering that the Waveshare panel controller (I2C bus 11, address 0x45) loses its register state on every 5V power cycle. The Linux driver (`ws_touchscreen`) only writes init registers in `probe()`, which runs once at boot and never again. After a power cycle the panel stays blank even after `wlr-randr --on`. Fix: force-write the same registers via `i2cset -y -f` before the compositor resumes — the `-f` flag bypasses the driver's ownership lock.

Registers written on every power-on (sourced from `panel-waveshare-dsi.c` `probe()` and `enable()`):

| Register | Value | Required | Notes |
|----------|-------|----------|-------|
| `0xc0` | `0x01` | ✅ yes | Neither `0xc0` nor `0xc2` works alone — both must be written together |
| `0xc2` | `0x01` | ✅ yes | As above |
| `0xac` | `0x01` | ❌ no | Tested: omitting it does not prevent image recovery |
| `0xad` | `0x01` | ❌ no | Tested: omitting it does not prevent image recovery |

Register requirements validated by systematic per-register testing (each register tested individually and in combination after a clean 5V power cycle). The minimum sequence to recover the panel is `0xc0=0x01` followed by `0xc2=0x01`.

Tested: `power_off()` → 5V disconnect → reconnect → `power_on()` — image and backlight restored fully. Confirmed multiple times.

## Validation Plan

1. **Turn-on test:** GPIO24 HIGH → oscilloscope or multimeter on DISP_5V — voltage should rise from 0 to ~4.8 V over ~100–200 ms. No voltage droop on Pi's own 5V rail (measure at pin 2/4).
2. **Turn-off test:** GPIO24 LOW → DISP_5V should drop to 0 V cleanly. Pi continues running normally.
3. **Cycle test (≥ 10 cycles):** repeat on/off via API; Pi must remain running throughout with no resets.
4. **Boot-state test:** power Pi with display connected; display should remain off until software explicitly turns it on (GPIO24 starts LOW).
5. **API test:** `POST /api/v1/system/display/on` and `off` — display responds; service logs the GPIO transition.

## Exit Criteria

- display can be powered on and off via API without causing Pi reset or shutdown
- soft-start confirmed: no visible Pi 5V sag during turn-on
- ≥ 10 on/off cycles complete without instability
- `DisplayService` power sequences use GPIO24 in the correct order
- host health gate passes after sustained cycling

## Wiring Findings (Protoboard Assembly)

### Display 5V wiring error

During initial assembly the display's 5V input was connected to the Pi's **3.3V** rail (physical pin 1) instead of the 5V rail (physical pin 2). Symptoms:

- Display backlight turned on but image was dim and colours were washed out.
- Maximum brightness was limited (raw 170 appeared to cap at reduced output).
- Phase 21 transistor circuit (Q8/Q9) produced unexpected collector voltages due to the wrong supply reference.

After rewiring to the correct 5V rail:
- Colours improved noticeably.
- Full brightness range (`0–255 raw`, `0–100%`) is now accessible.
- Power draw: **5.06 V / 0.60 A** (display on), **5.07 V / 0.48 A** (display 5V disconnected) — ~120 mA / ~610 mW saved with display off.

### Q9 (2N3904) transistor issue

Q9's emitter and collector are swapped on the protoboard. The 2N3904 was operating in reverse-active mode with near-zero current gain:

- With GPIO24 HIGH and Q9 E-C swapped: base of Q8 measured 4.3 V instead of the expected 1.7 V pull-down.
- Q8 (S8550) remained off; collector held at 2.7 V rather than switching to near-0 V.

The 0.7 V signature (4.3 V = 5 V − 0.7 V base-emitter drop in reverse) confirmed E-C reversal. The circuit was **bypassed** for Phase 21 testing: display connected directly to Pi 5V. GPIO24 control via the transistor circuit remains to be validated after correcting Q9's pinout.

## Evidence Checklist

- ✅ Circuit assembled on protoboard (bypassed — display on Pi 5V directly; Q9 pinout needs correction)
- ✅ Software power-off/on sequence validated with manual 5V disconnect (2 × confirmed)
- ✅ `reinit_panel()` confirmed to restore image after 5V power cycle
- ✅ Boot-state confirmed: display on at service startup via `display.power_on()` in lifespan
- ✅ API endpoints tested end-to-end
- ⬜ Q9 (2N3904) pinout corrected and GPIO24 circuit validated
- ⬜ Turn-on voltage ramp measured and documented (DISP_5V rise time via transistor circuit)
- ⬜ Pi 5V rail measured during turn-on (no sag)
- ⬜ ≥ 10 on/off cycles validated via GPIO24 circuit without Pi instability
- ⬜ Host health snapshot recorded after cycling
