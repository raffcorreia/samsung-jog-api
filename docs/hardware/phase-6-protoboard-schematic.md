# Phase 6 Protoboard Schematic

## Purpose

This document defines the reviewable schematic for `Phase 6: Discrete-Component Protoboard Validation`.

It is a **build-oriented protoboard schematic**, not the final integrated controller-board schematic.

## Design Intent

The Phase 6 schematic is intentionally optimized for:

- simple protoboard assembly
- parts already on hand
- fast software unblocking
- direct signal visibility during debugging
- generous Raspberry Pi `GPIO` usage

It is intentionally **not** optimized for:

- minimum part count
- minimum GPIO count
- final PCB layout
- final production connector strategy

## External Interfaces

### Monitor JOG Harness

| Monitor pin | Net |
| --- | --- |
| pin 1 | `MON_GND` |
| pin 2 | `MON_KEY_ADC2` |
| pin 3 | `MON_KEY_ADC1` |
| pin 4 | `MON_KEY_LED` |
| pin 5 | `NC` |

### Raspberry Pi Interface

| Function | Net |
| --- | --- |
| `3.3V` | `PI_3V3` |
| `GND` | `PI_GND` |
| `I2C SDA` | `PI_SDA` |
| `I2C SCL` | `PI_SCL` |
| ADC ready / alert input | `PI_ADC_ALERT` |
| `KEY_ADC1` digital input | `PI_KEY1_IN` |
| `KEY_LED` digital input | `PI_LED_IN` |
| `CENTER` drive output | `PI_CENTER_EN` |
| `UP` drive output | `PI_UP_EN` |
| `DOWN` drive output | `PI_DOWN_EN` |
| `LEFT` drive output | `PI_LEFT_EN` |
| `RIGHT` drive output | `PI_RIGHT_EN` |

Ground rule:

- `PI_GND` and `MON_GND` are the same electrical ground in this phase

## Block 1: `KEY_ADC2` Analog Observation

### Intent

Observe `MON_KEY_ADC2` as an analog signal through `ADS1115`, and use `ALERT/RDY` as an interrupt-style signal to the Raspberry Pi.

### Connections

| From | To | Notes |
| --- | --- | --- |
| `MON_KEY_ADC2` | `ADS_AIN0` | primary analog observation channel |
| `PI_GND` | `ADS_AIN1` or `GND` reference | single-ended measurement basis |
| `PI_3V3` | `ADS_VDD` | local `3.3V` supply |
| `PI_GND` | `ADS_GND` | common ground |
| `PI_SDA` | `ADS_SDA` | `I2C` data |
| `PI_SCL` | `ADS_SCL` | `I2C` clock |
| `ADS_ALERT_RDY` | `PI_ADC_ALERT` | interrupt-style GPIO signal |

### Support Parts

- `R_ADC_SDA_PULLUP = 4.7 kOhm` to `PI_3V3` if not already present on the breakout
- `R_ADC_SCL_PULLUP = 4.7 kOhm` to `PI_3V3` if not already present on the breakout
- `C_ADC_LOCAL = 100 nF` across `ADS_VDD` to `ADS_GND`
- `C_ADC_BULK = 1 uF` across `ADS_VDD` to `ADS_GND`

### ASCII Schematic

```text
MON_KEY_ADC2 -----------------------------> ADS1115 AIN0
PI_GND -----------------------------------> ADS1115 GND
PI_3V3 -----------------------------------> ADS1115 VDD
PI_SDA -----------------------------------> ADS1115 SDA
PI_SCL -----------------------------------> ADS1115 SCL
ADS1115 ALERT/RDY ------------------------> PI_ADC_ALERT
```

## Block 2: `KEY_ADC1` Digital-Style Observation

### Intent

Treat `MON_KEY_ADC1` as a digital-style signal in this phase, using simple conditioning rather than the final observation front end.

### Recommended Prototype Conditioning

Use one `2N3904` as a simple protected buffer/inverter:

- `Q_KEY1 = 2N3904`
- `R_KEY1_BASE = 10 kOhm`
- `R_KEY1_PULLUP = 10 kOhm`

### Connections

| From | To | Notes |
| --- | --- | --- |
| `MON_KEY_ADC1` | `R_KEY1_BASE` | base drive through resistor |
| `R_KEY1_BASE` | `Q_KEY1 base` | transistor input |
| `Q_KEY1 emitter` | `PI_GND` | low-side reference |
| `Q_KEY1 collector` | `PI_KEY1_IN` | GPIO input node |
| `PI_KEY1_IN` | `R_KEY1_PULLUP` to `PI_3V3` | collector pull-up |

### ASCII Schematic

```text
MON_KEY_ADC1 -- R_KEY1_BASE(10k) --B Q_KEY1(2N3904)
                                    C-----> PI_KEY1_IN ---- R_KEY1_PULLUP(10k) ----> PI_3V3
                                    E-----> PI_GND
```

## Block 3: `KEY_LED` Digital Observation

### Intent

Treat `MON_KEY_LED` as a digital-style signal in this phase, again using simple conditioning.

### Recommended Prototype Conditioning

Use one more `2N3904` stage:

- `Q_LED = 2N3904`
- `R_LED_BASE = 10 kOhm`
- `R_LED_PULLUP = 10 kOhm`

### Connections

| From | To | Notes |
| --- | --- | --- |
| `MON_KEY_LED` | `R_LED_BASE` | base drive through resistor |
| `R_LED_BASE` | `Q_LED base` | transistor input |
| `Q_LED emitter` | `PI_GND` | low-side reference |
| `Q_LED collector` | `PI_LED_IN` | GPIO input node |
| `PI_LED_IN` | `R_LED_PULLUP` to `PI_3V3` | collector pull-up |

### ASCII Schematic

```text
MON_KEY_LED -- R_LED_BASE(10k) --B Q_LED(2N3904)
                                  C-----> PI_LED_IN ---- R_LED_PULLUP(10k) ----> PI_3V3
                                  E-----> PI_GND
```

## Block 4: Discrete `JOG` Drive Channels

### Intent

Each logical action gets its own resistor-to-ground leg and its own dedicated `2N3904` low-side switch.

This phase does **not** use a mux.

### Tested Target Resistor Values

| Action | Monitor line | Resistor |
| --- | --- | --- |
| `LEFT` | `MON_KEY_ADC2` | `30 kOhm` |
| `RIGHT` | `MON_KEY_ADC2` | `10 kOhm` |
| `DOWN` | `MON_KEY_ADC2` | `3.3 kOhm` |
| `UP` | `MON_KEY_ADC2` | `22 kOhm` |
| `CENTER` | `MON_KEY_ADC1` | `22 kOhm` |

### Per-Channel Drive Pattern

For each action channel:

- `Qx = 2N3904`
- `R_BASE_x = 4.7 kOhm` to `10 kOhm`
- `R_BASE_PULLDOWN_x = 100 kOhm`
- `R_ACTION_x = tested resistor leg`

### Wiring Pattern

```text
PI_ACTION_EN -- R_BASE_x --B Qx(2N3904)
                        |
                        +-- R_BASE_PULLDOWN_x(100k) --> PI_GND

Qx emitter -------------------------------------------> PI_GND
MON_KEY_ADCx -- R_ACTION_x -- collector Qx
```

Important interpretation:

- when the GPIO is inactive, the transistor is off and the resistor leg is disconnected
- when the GPIO is asserted, the transistor pulls the resistor leg to ground
- this reproduces the required resistance-to-ground path without sourcing voltage onto the monitor line

## Drive Channel Table

| Channel | GPIO | Monitor line | Resistor |
| --- | --- | --- | --- |
| `Q_CENTER` | `PI_CENTER_EN` | `MON_KEY_ADC1` | `22 kOhm` |
| `Q_UP` | `PI_UP_EN` | `MON_KEY_ADC2` | `22 kOhm` |
| `Q_DOWN` | `PI_DOWN_EN` | `MON_KEY_ADC2` | `3.3 kOhm` |
| `Q_LEFT` | `PI_LEFT_EN` | `MON_KEY_ADC2` | `30 kOhm` |
| `Q_RIGHT` | `PI_RIGHT_EN` | `MON_KEY_ADC2` | `10 kOhm` |

## Full Protoboard View

```text
Monitor CN1001
--------------
MON_GND -------------------------------+------------------------------- PI_GND
MON_KEY_ADC2 ----+--------------------> ADS1115 AIN0
                 |
                 +-- 30k -- Q_LEFT collector
                 +-- 10k -- Q_RIGHT collector
                 +-- 3.3k - Q_DOWN collector
                 +-- 22k -- Q_UP collector

MON_KEY_ADC1 ----+-- 22k -- Q_CENTER collector
                 |
                 +-- 10k -- Q_KEY1 base

MON_KEY_LED ----------- 10k ----------> Q_LED base

ADS1115
-------
PI_3V3 --------------------------------> VDD
PI_GND --------------------------------> GND
PI_SDA --------------------------------> SDA
PI_SCL --------------------------------> SCL
ADS_ALERT_RDY -------------------------> PI_ADC_ALERT

Digital observation
-------------------
Q_KEY1 collector ----------------------> PI_KEY1_IN with 10k pull-up to PI_3V3
Q_LED collector -----------------------> PI_LED_IN  with 10k pull-up to PI_3V3

Drive control
-------------
PI_CENTER_EN -> base resistor -> Q_CENTER base
PI_UP_EN     -> base resistor -> Q_UP base
PI_DOWN_EN   -> base resistor -> Q_DOWN base
PI_LEFT_EN   -> base resistor -> Q_LEFT base
PI_RIGHT_EN  -> base resistor -> Q_RIGHT base

All Q_* emitters ----------------------> PI_GND
All Q_* bases have 100k pull-downs ----> PI_GND
```

## Recommended Bring-Up Order

1. verify common ground and `3.3V`
2. bring up `ADS1115` and confirm `KEY_ADC2` readings
3. bring up `KEY_ADC1` and `KEY_LED` observation inputs
4. wire one drive leg only and validate its effect
5. add the remaining drive legs one by one
6. only after individual channels work, start software-side action sequencing

## Explicit Phase 6 Non-Goals

This schematic does not yet solve:

- GPIO minimization
- final PCB footprint choices
- final connectorization
- final observation-buffer architecture
- final production-safe packaging of the monitor harness
- final `HDMI/DDC` intermediary path

Those belong to the integrated-board phase after this prototype proves the concept.
