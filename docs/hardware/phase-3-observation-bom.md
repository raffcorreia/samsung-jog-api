# Phase 3 Observation BOM

## Purpose

This BOM defines the selected parts and default passive values for `Phase 3: Bus Observation Circuit Design`.

It covers only the observation subcircuit:

- `KEY_ADC1` buffered digital observation
- `KEY_ADC2` analog observation
- `KEY_LED` buffered observation with digital interpretation
- local support components needed for this subcircuit

It does not define the final integrated controller-board connectors, board outline, or GPIO assignment. Those belong to later phases.

## Selected Core Parts

| RefDes | Qty | Part | Package | Purpose | Notes |
| --- | --- | --- | --- | --- | --- |
| `U1` | 1 | `TLV9064IDR` | `SOIC-14` | Quad high-input-impedance observation buffer | Channels allocated to `KEY_ADC2`, `KEY_ADC1`, `KEY_LED`, and one spare |
| `U2` | 1 | `ADS1114IDGST` | `VSSOP-10` | 16-bit I2C ADC for analog `KEY_ADC2` observation | `ALERT/RDY` should be routed to the host for interrupt-assisted sampling |
| `U3` | 1 | `74LVC1G17GW` | `SOT-353` | Schmitt-trigger buffer for `KEY_ADC1` digital interpretation | Powered from `3.3V` |
| `U4` | 1 | `74LVC1G17GW` | `SOT-353` | Schmitt-trigger buffer for `KEY_LED` digital interpretation | Powered from `3.3V` |

## Default Passive Values

| RefDes | Qty | Value | Notes |
| --- | --- | --- | --- |
| `R1` | 1 | `10 kOhm`, `1%` | Series resistor on `KEY_ADC2` observation input |
| `R2` | 1 | `10 kOhm`, `1%` | Series resistor on `KEY_ADC1` observation input |
| `R3` | 1 | `10 kOhm`, `1%` | Series resistor on `KEY_LED` observation input |
| `R4` | 1 | `4.7 kOhm`, `1%` | `I2C` pull-up from `SDA` to `3.3V` |
| `R5` | 1 | `4.7 kOhm`, `1%` | `I2C` pull-up from `SCL` to `3.3V` |
| `C1` | 1 | `100 nF`, `X7R` | Local decoupling at `U1` |
| `C2` | 1 | `100 nF`, `X7R` | Local decoupling at `U2` |
| `C3` | 1 | `100 nF`, `X7R` | Local decoupling at `U3` |
| `C4` | 1 | `100 nF`, `X7R` | Local decoupling at `U4` |
| `C5` | 1 | `1 uF`, `X7R` | Local bulk decoupling on `3.3V` rail near analog front end |
| `C6` | 1 | `1 nF`, `DNP` | Optional noise filter footprint for `KEY_ADC2` after bench validation |
| `C7` | 1 | `1 nF`, `DNP` | Optional noise filter footprint for `KEY_ADC1` after bench validation |
| `C8` | 1 | `1 nF`, `DNP` | Optional noise filter footprint for `KEY_LED` after bench validation |

## Interface Placeholders

These are temporary Phase 3 placeholders so the observation subcircuit can be reviewed and prototyped. Final connector selection belongs to the integrated-board phase.

| RefDes | Qty | Part / Type | Purpose |
| --- | --- | --- | --- |
| `J1` | 1 | `1x4` temporary observation header | `GND`, `KEY_ADC2`, `KEY_ADC1`, `KEY_LED` from monitor side |
| `J2` | 1 | `1x7` temporary host header | `3.3V`, `GND`, `SDA`, `SCL`, `ADC_ALERT`, `KEY1_IN_GPIO`, `LED_IN_GPIO` to host |
| `TP1-TP7` | 7 | test points | `KEY_ADC2_BUF`, `KEY_ADC1_BUF`, `KEY_LED_BUF`, `SDA`, `SCL`, `ADC_ALERT`, `3.3V` |

## Channel Allocation

### `TLV9064IDR`

- `U1A`: `KEY_ADC2` buffer
- `U1B`: `KEY_ADC1` buffer
- `U1C`: `KEY_LED` buffer
- `U1D`: spare channel for debug, later conditioning, or future observation needs

### `ADS1114IDGST`

- `AINP`: `KEY_ADC2_BUF`
- `AINN`: `GND` for single-ended use
- `ADDR`: tie to `GND` for the default `I2C` address unless later integration needs a different address
- `ALERT/RDY`: route to host GPIO or test point for interrupt-assisted observation

### `74LVC1G17GW`

- `U3`: `KEY_ADC1_BUF` -> `KEY1_IN_GPIO`
- `U4`: `KEY_LED_BUF` -> `LED_IN_GPIO`

## Current Design Intent

- `KEY_ADC2` stays analog through the op-amp buffer and into the ADC
- `KEY_ADC1` is buffered first and then converted into a clean digital input through `U3`
- `KEY_LED` is buffered first and then converted into a clean digital input through `U4`
- software classifies `KEY_ADC2` analog ranges later, while `KEY_ADC1` and `KEY_LED` are treated as digital states after thresholding
- optional RC filters are intentionally `DNP` until bench noise proves they are needed

## Open Items For Later Phases

- final connector families
- final GPIO pin assignment
- final integrated board outline and mechanical features
- whether extra line protection beyond the current series-resistor strategy is required after bench testing
- whether `KEY_LED` needs any threshold tweaks after prototype validation
