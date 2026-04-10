# Phase 6 Protoboard BOM

## Parts

| Ref | Qty | Part | Value / Use |
| --- | --- | --- | --- |
| `U1` | `1` | `ADS1115` breakout | `KEY_ADC2` ADC, powered from `3.3V` |
| `Q1-Q7` | `7` | `2N3904` | `Q1-Q2` observe, `Q3-Q7` drive |
| `C1` | `1` | capacitor | `100 nF` |
| `C2` | `1` | capacitor | `1 uF` |
| `R1-R4` | `4` | resistor | `10 kOhm` |
| `R5-R9` | `5` | resistor | `4.7 kOhm` |
| `R10-R11` | `2` | resistor | `22 kOhm` |
| `R12` | `1` | resistor | `3.3 kOhm` |
| `R13` | `1` | resistor | `30 kOhm` |
| `R14` | `1` | resistor | `10 kOhm` |
| `R15-R19` | `5` | resistor | `100 kOhm` |
| `J1` | `1` | `1x4` header | monitor harness |

## Raspberry Pi Wiring

| Function | Pi Pin |
| --- | --- |
| `3.3V` | physical pin `1` |
| `GND` | physical pin `6` |
| `SDA` | `GPIO2`, physical pin `3` |
| `SCL` | `GPIO3`, physical pin `5` |
| `ALERT/RDY` | `GPIO17`, physical pin `11` |
| `KEY_ADC1` input | `GPIO27`, physical pin `13` |
| `KEY_LED` input | `GPIO22`, physical pin `15` |
| `CENTER` | `GPIO5`, physical pin `29` |
| `UP` | `GPIO6`, physical pin `31` |
| `DOWN` | `GPIO13`, physical pin `33` |
| `LEFT` | `GPIO19`, physical pin `35` |
| `RIGHT` | `GPIO26`, physical pin `37` |

## Harness

| `J1` Pin | Net |
| --- | --- |
| `1` | `GND` |
| `2` | `MON_KEY_ADC2` |
| `3` | `MON_KEY_ADC1` |
| `4` | `MON_KEY_LED` |
