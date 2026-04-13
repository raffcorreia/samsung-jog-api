# Phase 6 Protoboard Schematic

This note matches the KiCad schematic and names every active component explicitly.

## Interfaces

### Monitor Harness `J1`

| Pin | Net |
| --- | --- |
| `1` | `GND` |
| `2` | `MON_KEY_ADC2` |
| `3` | `MON_KEY_ADC1` |
| `4` | `MON_KEY_LED` |

### Raspberry Pi Direct GPIO Wiring

There is no `J2` or `J3` header in this phase.

| Pi Function | Raspberry Pi Pin |
| --- | --- |
| `logic / ADC rail` | `3.3V`, physical pin `1` |
| `GND` | physical pin `6` |
| `I2C SDA` | `GPIO2`, physical pin `3` |
| `I2C SCL` | `GPIO3`, physical pin `5` |
| `ADS1115 ALERT/RDY` | `GPIO17`, physical pin `11` |
| `KEY_ADC1` input | `GPIO27`, physical pin `13` |
| `KEY_LED` input | `GPIO22`, physical pin `15` |
| `CENTER` drive | `GPIO5`, physical pin `29` |
| `UP` drive | `GPIO6`, physical pin `31` |
| `DOWN` drive | `GPIO13`, physical pin `33` |
| `LEFT` drive | `GPIO19`, physical pin `35` |
| `RIGHT` drive | `GPIO26`, physical pin `37` |

## ADC Block

| Ref | Value | Connection |
| --- | --- | --- |
| `U1` | `ADS1115` | `AIN0 -> MON_KEY_ADC2`, `SDA -> GPIO2`, `SCL -> GPIO3`, `ALERT/RDY -> GPIO17`, `VDD -> 3.3V`, `GND -> GND` |
| `C1` | `100 nF` | `3.3V` to `GND` near `U1` |
| `C2` | `1 uF` | `3.3V` to `GND` near `U1` |

`AIN1`, `AIN2`, and `AIN3` are unused in this phase. `ADDR` is strapped to `GND`.

## Observation Channels

### `KEY_ADC1`

| Ref | Value | Connection |
| --- | --- | --- |
| `R1` | `100 kOhm` | `MON_KEY_ADC1 -> Q1 base` |
| `Q1` | `2N3904` | base from `R1`, collector (`C`) to `GPIO27`, emitter (`E`) to `GND` |
| `R2` | `10 kOhm` | `3.3V -> GPIO27` pull-up |

### `KEY_LED`

| Ref | Value | Connection |
| --- | --- | --- |
| `R3` | `10 kOhm` | `MON_KEY_LED -> Q2 base` |
| `Q2` | `2N3904` | base from `R3`, collector (`C`) to `GPIO22`, emitter (`E`) to `GND` |
| `R4` | `10 kOhm` | `3.3V -> GPIO22` pull-up |

## Drive Channels

Each drive channel uses:
- one GPIO net into a base resistor
- one `100 kOhm` base pull-down to `GND`
- one `2N3904` low-side transistor
- one action resistor between the monitor key line and the transistor collector

### Center

| Ref | Value | Connection |
| --- | --- | --- |
| `R5` | `4.7 kOhm` | `GPIO5 -> Q3 base` |
| `R15` | `100 kOhm` | `Q3 base -> GND` |
| `Q3` | `2N3904` | emitter `-> GND`, collector `-> R10` |
| `R10` | `22 kOhm` | `MON_KEY_ADC1 -> Q3 collector` |

### Up

| Ref | Value | Connection |
| --- | --- | --- |
| `R6` | `4.7 kOhm` | `GPIO6 -> Q4 base` |
| `R16` | `100 kOhm` | `Q4 base -> GND` |
| `Q4` | `2N3904` | emitter `-> GND`, collector `-> R11` |
| `R11` | `22 kOhm` | `MON_KEY_ADC2 -> Q4 collector` |

### Down

| Ref | Value | Connection |
| --- | --- | --- |
| `R7` | `4.7 kOhm` | `GPIO13 -> Q5 base` |
| `R17` | `100 kOhm` | `Q5 base -> GND` |
| `Q5` | `2N3904` | emitter `-> GND`, collector `-> R12` |
| `R12` | `3.3 kOhm` | `MON_KEY_ADC2 -> Q5 collector` |

### Left

| Ref | Value | Connection |
| --- | --- | --- |
| `R8` | `4.7 kOhm` | `GPIO19 -> Q6 base` |
| `R18` | `100 kOhm` | `Q6 base -> GND` |
| `Q6` | `2N3904` | emitter `-> GND`, collector `-> R13` |
| `R13` | `30 kOhm` | `MON_KEY_ADC2 -> Q6 collector` |

### Right

| Ref | Value | Connection |
| --- | --- | --- |
| `R9` | `4.7 kOhm` | `GPIO26 -> Q7 base` |
| `R19` | `100 kOhm` | `Q7 base -> GND` |
| `Q7` | `2N3904` | emitter `-> GND`, collector `-> R14` |
| `R14` | `10 kOhm` | `MON_KEY_ADC2 -> Q7 collector` |

## Important Interpretation

- The observation transistors `Q1` and `Q2` are simple inverting open-collector buffers into Pi GPIO: `C` goes to the GPIO input and `E` goes to `GND`.
- The drive transistors `Q3-Q7` do not source voltage onto the monitor lines.
- Each drive action connects a tested resistor leg to ground only when its GPIO is asserted.
- `ADS1115`, `I2C`, and Pi-facing pull-ups all stay on `3.3V`.
