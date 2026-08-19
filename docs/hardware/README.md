# Hardware Reference

Living reference documents for the Samsung CJ791 JOG project hardware. These are named by artifact, not by the phase that created them. Phase-specific decisions and validation evidence belong in the corresponding execution records under `docs/implementation/`.

Return to the [project README](../../README.md), or choose a hardware topic below.

## Raspberry Pi and current protoboard

| Document | What it covers |
|---|---|
| [Raspberry Pi 5 GPIO schema](pi5-gpio-schema.md) | BCM numbers, physical pins, signal names, direction, and a visual 40-pin header reference |
| [Protoboard schematic](protoboard-schematic.md) | Wiring and circuit description for the Phase 6 protoboard, including the Raspberry Pi pinout diagram and display power control additions |
| [Protoboard BOM](protoboard-bom.md) | Component list for the Phase 6 discrete-component protoboard (current bring-up hardware) |

## Monitor interface and circuit references

| Document | What it covers |
|---|---|
| [CJ791 JOG board](cj791-jog-board.md) | Samsung CJ791 front-panel JOG board connector pinout, measured signal levels, and resistor-ladder values |
| [Observation circuit BOM](observation-bom.md) | Components for the CN1001 bus observation circuit (`KEY_ADC1`, `KEY_ADC2`, and `KEY_LED` conditioning) |
| [Analog drive circuit BOM](analog-drive-bom.md) | Components for reproducing the analog JOG resistor ladder |
| [HDMI and DDC transport](hdmi-ddc-transport.md) | HDMI/DDC/CI signal path, level shifting, and host integration |

## Diagrams and images

Diagrams are kept under [`docs/assets/hardware/`](../assets/hardware/) and are presented from the relevant reference document. For GPIO wiring, start with the [Raspberry Pi 5 GPIO schema](pi5-gpio-schema.md); for the complete circuit, use the [protoboard schematic](protoboard-schematic.md).

## Naming rule

- **This directory**: artifact-named living references (schematic descriptions, BOMs, GPIO maps, signal characterization)
- **`docs/implementation/phase-*-execution.md`**: frozen phase history (decisions made, measurements taken, work done)
- **`docs/assets/hardware/`**: diagrams and images referenced by the documents above
