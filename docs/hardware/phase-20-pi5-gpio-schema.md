# Phase 20 Raspberry Pi 5 GPIO Schema

This schema maps the existing Phase 6 discrete protoboard wiring onto a Raspberry Pi 5 16GB host for Phase 20 validation.

The Raspberry Pi 5 keeps the same 40-pin GPIO header pinout used by the earlier Raspberry Pi deck host. Phase 20 therefore uses the same BCM GPIO assignments as `backend/src/pi_deck/hardware/protoboard_pins.py` unless validation proves a Pi 5-specific compatibility issue.

## Interfaces

### Monitor Harness `J1`

No monitor-side wiring changes are planned for Phase 20.

| Pin | Net |
| --- | --- |
| `1` | `GND` |
| `2` | `MON_KEY_ADC2` |
| `3` | `MON_KEY_ADC1` |
| `4` | `MON_KEY_LED` |

### Raspberry Pi 5 Direct GPIO Wiring

Use BCM numbering in software and the physical header pins below for wiring.

| Pi Function | Raspberry Pi 5 Pin |
| --- | --- |
| `logic / ADC rail` | `3.3V`, physical pin `1` or `17` |
| `GND` | physical pin `6` or any other header `GND` |
| `I2C SDA` | `GPIO2`, physical pin `3` |
| `I2C SCL` | `GPIO3`, physical pin `5` |
| `ADS1115 ALERT/RDY` | `GPIO17`, physical pin `11` |
| `KEY_ADC1` input | `GPIO27`, physical pin `13` |
| `KEY_LED` input | `GPIO22`, physical pin `15` |
| `display_power_en` output (Phase 21) | `GPIO24`, physical pin `18` |
| `CENTER` drive | `GPIO5`, physical pin `29` |
| `UP` drive | `GPIO6`, physical pin `31` |
| `DOWN` drive | `GPIO13`, physical pin `33` |
| `LEFT` drive | `GPIO19`, physical pin `35` |
| `RIGHT` drive | `GPIO26`, physical pin `37` |

## 40-Pin Header Reference

Use the board silkscreen, square pad, or a known-good Raspberry Pi 40-pin reference to identify pin `1` before wiring. Do not rely on cable color or ribbon orientation alone.

| Physical | Function | Phase 20 use | Physical | Function | Phase 20 use |
| --- | --- | --- | --- | --- | --- |
| `1` | `3.3V` | logic / ADC rail | `2` | `5V` | display 5V only, if header-powered |
| `3` | `GPIO2 / SDA1` | project I2C SDA | `4` | `5V` | display 5V only, if header-powered |
| `5` | `GPIO3 / SCL1` | project I2C SCL | `6` | `GND` | common ground |
| `7` | `GPIO4` | unused | `8` | `GPIO14` | unused |
| `9` | `GND` | common ground | `10` | `GPIO15` | unused |
| `11` | `GPIO17` | `ADS1115 ALERT/RDY` | `12` | `GPIO18` | unused |
| `13` | `GPIO27` | `KEY_ADC1` input | `14` | `GND` | common ground |
| `15` | `GPIO22` | `KEY_LED` input | `16` | `GPIO23` | unused |
| `17` | `3.3V` | optional logic / ADC rail | `18` | `GPIO24` | `display_power_en` (Phase 21) |
| `19` | `GPIO10` | unused | `20` | `GND` | common ground |
| `21` | `GPIO9` | unused | `22` | `GPIO25` | unused |
| `23` | `GPIO11` | unused | `24` | `GPIO8` | unused |
| `25` | `GND` | common ground | `26` | `GPIO7` | unused |
| `27` | `GPIO0 / ID_SD` | leave unused | `28` | `GPIO1 / ID_SC` | leave unused |
| `29` | `GPIO5` | `CENTER` drive | `30` | `GND` | common ground |
| `31` | `GPIO6` | `UP` drive | `32` | `GPIO12` | unused |
| `33` | `GPIO13` | `DOWN` drive | `34` | `GND` | common ground |
| `35` | `GPIO19` | `LEFT` drive | `36` | `GPIO16` | unused |
| `37` | `GPIO26` | `RIGHT` drive | `38` | `GPIO20` | unused |
| `39` | `GND` | common ground | `40` | `GPIO21` | unused |

## Display and Touch Connections

The Waveshare DSI display path is not part of the 40-pin GPIO signal map, but it is part of Phase 20 validation:

- connect the display data ribbon to the appropriate Raspberry Pi 5 DSI connector using the correct Pi 5-compatible ribbon/adapter for the panel
- power the display from the Pi 5 `5V` header pins only if the Waveshare wiring expects header power; use physical pin `2` or `4` for `5V` and a nearby `GND`
- do not connect display power to the `3.3V` logic rail
- do not hot-plug the display 5V line while the Pi is powered; Phase 18/19 showed display power transients can reset or destabilize the host
- keep the project I2C bus on `GPIO2/GPIO3`; the DSI touch/panel devices should appear on the DSI controller/mux path, not as extra devices on the project I2C bus

## Software Mapping

The expected software map remains:

| Software field | BCM GPIO | Physical pin |
| --- | --- | --- |
| `i2c_sda` | `2` | `3` |
| `i2c_scl` | `3` | `5` |
| `ads_alert` | `17` | `11` |
| `key_adc1_digital` | `27` | `13` |
| `key_led_digital` | `22` | `15` |
| `display_power_en` | `24` | `18` |
| `drive_center` | `5` | `29` |
| `drive_up` | `6` | `31` |
| `drive_down` | `13` | `33` |
| `drive_left` | `19` | `35` |
| `drive_right` | `26` | `37` |

If Phase 20 requires a different pin factory, set it in the systemd environment and record it in the execution record. Do not change these BCM assignments unless a Pi 5-specific conflict is measured and documented.

## Validation Checklist

- `i2cdetect -y 1` sees the ADS1115 on the project I2C bus at the expected address
- `ADS1115 ALERT/RDY` toggles or is observable on `GPIO17`
- `KEY_ADC1` and `KEY_LED` digital inputs read idle and active states correctly
- each drive GPIO actuates only its intended `JOG` direction
- no unused GPIO on the header is accidentally connected to the protoboard
- display touch/panel devices enumerate on the DSI path and do not collide with the project I2C bus
- host health snapshot shows no active under-voltage or throttling during sustained kiosk use
