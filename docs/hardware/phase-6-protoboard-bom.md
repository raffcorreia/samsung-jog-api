# Phase 6 Protoboard BOM

## Purpose

This BOM defines the practical prototype parts for `Phase 6: Discrete-Component Protoboard Validation`.

This phase is intentionally **not** the final integrated-board BOM.

The goal here is:

- prove the monitor-control concept quickly on a protoboard
- unblock software production and testing
- avoid dependence on the final integrated-board part stack
- use mostly discrete parts and as many Raspberry Pi `GPIO` lines as needed
- keep the monitor connected directly over `HDMI`

## Phase 6 Prototype Assumptions

- `KEY_ADC2` is observed through `ADS1115`
- `ADS1115 ALERT/RDY` is wired to a Raspberry Pi GPIO
- `KEY_ADC1` is treated as a direct or simply conditioned digital-style input
- `KEY_LED` is treated as a direct or simply conditioned digital-style input
- each driven `JOG` action may use its own dedicated GPIO-controlled discrete switch
- no mux optimization is required in this phase
- no GPIO-minimization is required in this phase

## Required Core Parts

| Qty | Part | Preferred Form | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `1` | Raspberry Pi with accessible `GPIO` | existing host | prototype controller | Any Pi already chosen for the project is acceptable |
| `1` | `ADS1115` breakout or module | through-hole friendly | `KEY_ADC2` analog observation | Use the module you already have |
| `1` | protoboard or solderable breadboard | through-hole | permanent-ish prototype wiring | Preferred over a loose solderless breadboard once values are confirmed |
| `1` | solderless breadboard | optional but strongly recommended | first-pass wiring and iteration | Useful before committing to soldered protoboard |
| `1` | `3.3V/GND/GPIO` breakout approach | header or cobbler | Pi wiring convenience | Any existing Pi breakout is fine |

## Discrete Drive Parts

These parts implement the low-level `JOG` resistor-to-ground actions without relying on the final analog-switch ICs.

| Qty | Part | Preferred Form | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `5` | `2N3904` | through-hole | low-side switching of resistor legs | One each for `CENTER`, `UP`, `DOWN`, `LEFT`, `RIGHT` |
| `5` | `4.7 kOhm` to `10 kOhm` resistors | through-hole | base resistors | one per transistor; exact value can be chosen during protoboard bring-up |
| `5` | `100 kOhm` resistors | through-hole | base pull-downs | keep all transistors off by default |
| `1` | `30 kOhm`, `1%` resistor | through-hole | `KEY_ADC2_LEFT` tested value | from Phase 4 tested set |
| `1` | `10 kOhm`, `1%` resistor | through-hole | `KEY_ADC2_RIGHT` tested value | from Phase 4 tested set |
| `1` | `3.3 kOhm`, `1%` resistor | through-hole | `KEY_ADC2_DOWN` tested value | from Phase 4 tested set |
| `2` | `22 kOhm`, `1%` resistors | through-hole | `KEY_ADC2_UP` and `KEY_ADC1_CENTER` tested values | from Phase 4 tested set |

Recommended BJT switching model for this phase:

- emitter to `GND`
- collector to the bottom of the selected resistor leg
- top of the resistor leg to the corresponding monitor key line
- Raspberry Pi GPIO drives the base through the base resistor
- `100 kOhm` base pull-down keeps the channel off by default

## Observation And Input-Conditioning Parts

These parts keep the observation side simple and protoboard-friendly.

| Qty | Part | Preferred Form | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `2` | signal-conditioning channels for Pi digital inputs | choose one of the options below | `KEY_ADC1` and `KEY_LED` safe readback | Do not assume raw monitor lines are Pi-safe until bench voltage confirms it |
| `2` | `2N3904` or similar NPN transistors | through-hole | optional simple transistor buffer/inverter | Use if direct divider-to-GPIO is not comfortable |
| `2` | `10 kOhm` resistors | through-hole | base/input resistors for optional NPN stages | one per conditioned digital input |
| `2` | `10 kOhm` resistors | through-hole | collector pull-ups for optional NPN stages | one per conditioned digital input |
| `4` | `100 kOhm` resistors | through-hole | optional divider / bias parts | use as needed for simple conditioning |

Recommended interpretation:

- simplest acceptable path:
  - `KEY_ADC2` through `ADS1115`
  - `KEY_ADC1` and `KEY_LED` through simple resistor/transistor conditioning into Pi GPIO
- direct raw connection from monitor lines to Pi GPIO should only be used if bench voltage and fault behavior are explicitly confirmed safe first

## `ADS1115` Support Parts

| Qty | Part | Preferred Form | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `2` | `4.7 kOhm` resistors | through-hole | `I2C` pull-ups for `SDA` and `SCL` | only if not already present on the breakout |
| `1` | hookup for `ALERT/RDY` | jumper lead | interrupt-style ADC signal to Pi | required for the current Phase 6 plan |
| `1` | hookup for `ADDR` | jumper / strap | address selection | tie as needed for the breakout in use |

## Decoupling And Stability Parts

| Qty | Part | Preferred Form | Purpose | Notes |
| --- | --- | --- | --- | --- |
| `4-8` | `100 nF` capacitors | through-hole | local decoupling and noise cleanup | place near active modules and switch wiring as practical |
| `1-2` | `1 uF` capacitors | through-hole | local bulk decoupling | useful near the `ADS1115` module and switching section |

## Harness / Wiring Parts

| Qty | Part | Purpose | Notes |
| --- | --- | --- | --- |
| `1` | monitor harness breakout | connect to `KEY_ADC1`, `KEY_ADC2`, `KEY_LED`, `GND` | can be temporary header, solder leads, or breakout adapter |
| `1` | Pi-side control header or wire bundle | connect drive GPIOs, digital inputs, `I2C`, `ALERT/RDY`, `3.3V`, `GND` | no pin-efficiency target in this phase |
| `1` | common ground distribution strip | reduce protoboard wiring errors | strongly recommended |
| `1` | resistor-leg selection area | keep each driven action isolated and easy to probe | a small terminal strip or labeled proto area is enough |
| `1 set` | dupont jumpers / hookup wire | all interconnects | both male-female and male-male are usually useful |

## Recommended GPIO Budget For Phase 6

A practical Phase 6 allocation is:

- `5` GPIO outputs for drive:
  - `CENTER_EN`
  - `UP_EN`
  - `DOWN_EN`
  - `LEFT_EN`
  - `RIGHT_EN`
- `2` GPIO inputs for digital observation:
  - `KEY_ADC1_IN`
  - `KEY_LED_IN`
- `2` GPIOs for `I2C`:
  - `SDA`
  - `SCL`
- `1` GPIO input for `ADS1115 ALERT/RDY`

Total expected GPIO use:

- `10` Raspberry Pi GPIO signals, plus `3.3V` and `GND`

This is intentionally generous for the prototype.

## Minimum Bring-Up Set

If you want the smallest useful first build, this is the minimum set to check for immediately:

- Raspberry Pi
- `ADS1115`
- `5` `2N3904`
- `5` base resistors (`4.7 kOhm` to `10 kOhm`)
- `5` `100 kOhm` base pull-downs
- tested resistor set:
  - `30 kOhm`
  - `10 kOhm`
  - `3.3 kOhm`
  - `22 kOhm x2`
- enough parts to safely condition `KEY_ADC1` and `KEY_LED` into Pi GPIO
- protoboard or breadboard
- jumper wires
- monitor harness breakout

## Nice-To-Have Bench Items

| Qty | Part | Purpose |
| --- | --- | --- |
| `1` | logic analyzer | verify GPIO timing and `ALERT/RDY` behavior |
| `1` | oscilloscope | inspect key-line transitions and noise |
| `1` | DMM | verify resistor-state behavior and idle voltages |
| `1` | spare resistor assortment | tune conditioning if the monitor-side voltages differ slightly from expectation |

## What This BOM Intentionally Excludes

This Phase 6 BOM does **not** assume:

- final integrated PCB parts
- final `HDMI/DDC` intermediary hardware
- GPIO optimization
- the final analog-switch IC stack from the integrated design
- the full observation-buffer IC stack from the final observation design

Those belong to later phases after the concept is proven on the protoboard.
