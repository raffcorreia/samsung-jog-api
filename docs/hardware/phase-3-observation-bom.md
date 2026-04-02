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
| `U2` | 1 | `MCP3201-CI/SN` | `SOIC-8` | 12-bit SPI ADC for analog `KEY_ADC2` observation | Single-channel; Pi polls over SPI. Frees `SDA`/`SCL` for Phase 5 DDC/CI |
| `U3` | 1 | `74LVC1G17GW` | `SOT-353` | Schmitt-trigger buffer for `KEY_ADC1` digital interpretation | Powered from `3.3V` |
| `U4` | 1 | `74LVC1G17GW` | `SOT-353` | Schmitt-trigger buffer for `KEY_LED` digital interpretation | Powered from `3.3V` |

## Default Passive Values

| RefDes | Qty | Value | Notes |
| --- | --- | --- | --- |
| `R1` | 1 | `10 kOhm`, `1%` | Series resistor on `KEY_ADC2` observation input |
| `R2` | 1 | `10 kOhm`, `1%` | Series resistor on `KEY_ADC1` observation input |
| `R3` | 1 | `10 kOhm`, `1%` | Series resistor on `KEY_LED` observation input |
| ~~`R4`~~ | — | removed | I2C pull-up — not needed for SPI |
| ~~`R5`~~ | — | removed | I2C pull-up — not needed for SPI |
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
| `J2` | 1 | `1x7` temporary host header | `3.3V`, `GND`, `SPI_MISO`, `SPI_CLK`, `SPI_CS`, `KEY1_IN_GPIO`, `LED_IN_GPIO` to host |
| `TP1-TP7` | 7 | test points | `KEY_ADC2_BUF`, `KEY_ADC1_BUF`, `KEY_LED_BUF`, `SDA`, `SCL`, `ADC_ALERT`, `3.3V` |

## Channel Allocation

### `TLV9064IDR`

- `U1A`: `KEY_ADC2` buffer
- `U1B`: `KEY_ADC1` buffer
- `U1C`: `KEY_LED` buffer
- `U1D`: spare channel for debug, later conditioning, or future observation needs

### `MCP3201-CI/SN`

- `IN+`: `KEY_ADC2_BUF`
- `IN-`: `GND` for single-ended use
- `CS`: driven low by Pi to start a conversion; pulled high to end transaction
- `CLK`: SPI clock from Pi
- `DOUT`: 12-bit result clocked out to Pi on `SPI_MISO`

### `74LVC1G17GW`

- `U3`: `KEY_ADC1_BUF` -> `KEY1_IN_GPIO`
- `U4`: `KEY_LED_BUF` -> `LED_IN_GPIO`

## Current Design Intent

- `KEY_ADC2` stays analog through the op-amp buffer and into the SPI ADC (`MCP3201-CI/SN`)
- `KEY_ADC1` is buffered first and then converted into a clean digital input through `U3`
- `KEY_LED` is buffered first and then converted into a clean digital input through `U4`
- software classifies `KEY_ADC2` analog ranges by polling the ADC over SPI; `KEY_ADC1` and `KEY_LED` are treated as digital states after thresholding
- `SDA`/`SCL` are not used by the observation board — reserved for Phase 5 DDC/CI communication
- optional RC filters are intentionally `DNP` until bench noise proves they are needed

## Open Items For Later Phases

- final connector families
- final GPIO pin assignment
- final integrated board outline and mechanical features
- whether extra line protection beyond the current series-resistor strategy is required after bench testing
- whether `KEY_LED` needs any threshold tweaks after prototype validation
