# Hardware Reference

Living reference documents for the Samsung CJ791 JOG project hardware. These are named by artifact, not by the phase that created them. Phase-specific decisions and validation evidence belong in the corresponding execution records under `docs/implementation/`.

## Documents

| Document | What it covers |
|---|---|
| [cj791-jog-board.md](cj791-jog-board.md) | Samsung CJ791 front-panel JOG board: connector pinout, measured signal levels, resistor-ladder values |
| [observation-bom.md](observation-bom.md) | Component list for the CN1001 bus observation circuit (KEY_ADC1, KEY_ADC2, KEY_LED conditioning path) |
| [analog-drive-bom.md](analog-drive-bom.md) | Component list for the analog JOG drive circuit (resistor-ladder reproduction) |
| [hdmi-ddc-transport.md](hdmi-ddc-transport.md) | HDMI and DDC/CI transport strategy: signal path, level shifting, and host integration |
| [protoboard-bom.md](protoboard-bom.md) | Component list for the Phase 6 discrete-component protoboard (current bring-up hardware) |
| [protoboard-schematic.md](protoboard-schematic.md) | Wiring and circuit description for the Phase 6 protoboard, including display power control additions |
| [pi5-gpio-schema.md](pi5-gpio-schema.md) | Raspberry Pi 5 GPIO assignment table: BCM numbers, physical pins, signal names, and direction |

## Naming rule

- **This directory**: artifact-named living references (schematic descriptions, BOMs, GPIO maps, signal characterization)
- **`docs/implementation/phase-*-execution.md`**: frozen phase history (decisions made, measurements taken, work done)
- **`docs/assets/hardware/`**: diagrams and images referenced by the documents above
