#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from pathlib import Path

from kicad_sch_api import create_schematic, get_symbol_cache


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "hardware" / "kicad" / "phase-3-observation-reva"
PROJECT_NAME = "phase-3-observation-reva"
SCH_PATH = OUT_DIR / f"{PROJECT_NAME}.kicad_sch"
PRO_PATH = OUT_DIR / f"{PROJECT_NAME}.kicad_pro"


def set_common_fields(component, *, description: str = "", mpn: str = "", manufacturer: str = "", lcsc: str = ""):
    if description:
        component.set_property("Description", description)
    if manufacturer:
        component.set_property("Manufacturer", manufacturer)
    if mpn:
        component.set_property("MPN", mpn)
    if lcsc:
        component.set_property("LCSC", lcsc)


def pin_pos(sch, reference: str, pin_number: str) -> tuple[float, float]:
    pos = sch.get_component_pin_position(reference, pin_number)
    if pos is None:
        raise ValueError(f"Pin position not found for {reference} pin {pin_number}")
    return (pos.x, pos.y)


def pin_label(sch, reference: str, pin_number: str, net_name: str):
    sch.add_label(net_name, pin=(reference, pin_number))


def mark_no_connect(sch, reference: str, pin_number: str):
    sch.no_connects.add(pin_pos(sch, reference, pin_number))


def add_label_at(sch, text: str, position: tuple[float, float], rotation: float = 0):
    sch.add_label(text, position=position, rotation=rotation)


def add_wire_chain(sch, *points: tuple[float, float]):
    for start, end in zip(points, points[1:]):
        sch.add_wire(start, end)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cache = get_symbol_cache()
    cache.discover_libraries(["/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"])

    sch = create_schematic(PROJECT_NAME)
    sch.set_paper_size("A3")
    sch.set_title_block(
        title="Phase 3 Observation Circuit",
        company="samsung-jog-api",
        rev="A",
        comments={
            1: "Observation-only board for KEY_ADC2, KEY_ADC1, and KEY_LED",
            2: "Generated for KiCad 10",
        },
    )

    # Connector J1: monitor-side observation input
    j1 = sch.components.add(
        "Connector_Generic:Conn_01x04",
        reference="J1",
        value="MONITOR_INPUT",
        position=(20, 60),
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    )
    set_common_fields(j1, description="Monitor-side observation connector", manufacturer="Generic", mpn="PinHeader_1x04_P2.54mm")

    # Connector J2: host-side interface
    j2 = sch.components.add(
        "Connector_Generic:Conn_01x07",
        reference="J2",
        value="HOST_IF",
        position=(240, 60),
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x07_P2.54mm_Vertical",
    )
    set_common_fields(j2, description="Host interface connector", manufacturer="Generic", mpn="PinHeader_1x07_P2.54mm")

    # Connector J3: spare buffered observation channel for future use
    j3 = sch.components.add(
        "Connector_Generic:Conn_01x02",
        reference="J3",
        value="SPARE_IF",
        position=(20, 150),
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    )
    set_common_fields(j3, description="Future spare observation connector", manufacturer="Generic", mpn="PinHeader_1x02_P2.54mm")

    # Input resistors
    r1 = sch.components.add("Device:R", reference="R1", value="10k 1%", position=(55, 34), footprint="Resistor_SMD:R_0603_1608Metric")
    r2 = sch.components.add("Device:R", reference="R2", value="10k 1%", position=(55, 60), footprint="Resistor_SMD:R_0603_1608Metric")
    r3 = sch.components.add("Device:R", reference="R3", value="10k 1%", position=(55, 86), footprint="Resistor_SMD:R_0603_1608Metric")
    for ref, comp in [("R1", r1), ("R2", r2), ("R3", r3)]:
        set_common_fields(comp, description=f"Series input resistor {ref}", manufacturer="Generic", mpn="0603WAF1002T5E")

    # Pull-ups
    r4 = sch.components.add("Device:R", reference="R4", value="4.7k 1%", position=(188, 40), footprint="Resistor_SMD:R_0603_1608Metric")
    r5 = sch.components.add("Device:R", reference="R5", value="4.7k 1%", position=(188, 52), footprint="Resistor_SMD:R_0603_1608Metric")
    for ref, comp in [("R4", r4), ("R5", r5)]:
        set_common_fields(comp, description=f"I2C pull-up {ref}", manufacturer="Generic", mpn="0603WAF4701T5E")

    # Optional filter footprints
    c6 = sch.components.add("Device:C", reference="C6", value="1n DNP", position=(83, 28), footprint="Capacitor_SMD:C_0603_1608Metric")
    c7 = sch.components.add("Device:C", reference="C7", value="1n DNP", position=(83, 60), footprint="Capacitor_SMD:C_0603_1608Metric")
    c8 = sch.components.add("Device:C", reference="C8", value="1n DNP", position=(83, 92), footprint="Capacitor_SMD:C_0603_1608Metric")
    for ref, comp in [("C6", c6), ("C7", c7), ("C8", c8)]:
        set_common_fields(comp, description=f"Optional filter capacitor {ref}", manufacturer="Generic", mpn="0603B102K500NT")

    # Use KiCad's stock LM2902 quad-op-amp symbol for a clean multi-unit schematic.
    # The actual fitted/orderable device remains TLV9064IDR via value + MPN fields.
    u1a = sch.components.add(
        "Amplifier_Operational:LM2902",
        reference="U1",
        value="TLV9064IDR",
        position=(105, 34),
        unit=1,
        footprint="Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    )
    u1b = sch.components.add(
        "Amplifier_Operational:LM2902",
        reference="U1",
        value="TLV9064IDR",
        position=(105, 60),
        unit=2,
        footprint="Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    )
    u1c = sch.components.add(
        "Amplifier_Operational:LM2902",
        reference="U1",
        value="TLV9064IDR",
        position=(105, 86),
        unit=3,
        footprint="Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    )
    u1d = sch.components.add(
        "Amplifier_Operational:LM2902",
        reference="U1",
        value="TLV9064IDR",
        position=(105, 144.78),
        unit=4,
        footprint="Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    )
    u1p = sch.components.add(
        "Amplifier_Operational:LM2902",
        reference="U1",
        value="TLV9064IDR",
        position=(105, 118),
        unit=5,
        footprint="Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    )
    set_common_fields(u1a, description="Quad RRIO op-amp buffer", manufacturer="Texas Instruments", mpn="TLV9064IDR")

    # ADC
    u2 = sch.components.add(
        "Analog_ADC:ADS1114IDGS",
        reference="U2",
        value="ADS1114IDGS",
        position=(155, 34),
        footprint="Package_SO:MSOP-10_3x3mm_P0.5mm",
    )
    set_common_fields(u2, description="16-bit single-channel I2C ADC", manufacturer="Texas Instruments", mpn="ADS1114IDGS")

    # Schmitt buffers
    u3 = sch.components.add(
        "74xGxx:74LVC1G17",
        reference="U3",
        value="74LVC1G17GW",
        position=(155, 64),
        footprint="Package_TO_SOT_SMD:SOT-353_SC-70-5",
    )
    u4 = sch.components.add(
        "74xGxx:74LVC1G17",
        reference="U4",
        value="74LVC1G17GW",
        position=(155, 92),
        footprint="Package_TO_SOT_SMD:SOT-353_SC-70-5",
    )
    set_common_fields(u3, description="Schmitt trigger buffer for KEY_ADC1", manufacturer="Nexperia", mpn="74LVC1G17GW")
    set_common_fields(u4, description="Schmitt trigger buffer for KEY_LED", manufacturer="Nexperia", mpn="74LVC1G17GW")

    # Decoupling
    c1 = sch.components.add("Device:C", reference="C1", value="100n", position=(128, 118), footprint="Capacitor_SMD:C_0603_1608Metric")
    c2 = sch.components.add("Device:C", reference="C2", value="100n", position=(172, 18), footprint="Capacitor_SMD:C_0603_1608Metric")
    c3 = sch.components.add("Device:C", reference="C3", value="100n", position=(172, 56), footprint="Capacitor_SMD:C_0603_1608Metric")
    c4 = sch.components.add("Device:C", reference="C4", value="100n", position=(172, 84), footprint="Capacitor_SMD:C_0603_1608Metric")
    c5 = sch.components.add("Device:C", reference="C5", value="1u", position=(224, 18), footprint="Capacitor_SMD:C_0603_1608Metric")
    for ref, comp, mpn in [
        ("C1", c1, "CL10B104KB8NNNC"),
        ("C2", c2, "CL10B104KB8NNNC"),
        ("C3", c3, "CL10B104KB8NNNC"),
        ("C4", c4, "CL10B104KB8NNNC"),
        ("C5", c5, "CL10A105KB8NNNC"),
    ]:
        set_common_fields(comp, description=f"Decoupling capacitor {ref}", manufacturer="Samsung Electro-Mechanics", mpn=mpn)

    # Power flags for ERC
    pf1 = sch.components.add("power:PWR_FLAG", reference="#FLG01", position=(225, 34))
    pf1.in_bom = False
    pf1.on_board = False
    pf2 = sch.components.add("power:PWR_FLAG", reference="#FLG02", position=(225, 46))
    pf2.in_bom = False
    pf2.on_board = False

    # Notes
    sch.add_text("Monitor-side connector", position=(15, 20), size=1.8)
    sch.add_text("Buffered analog path", position=(92, 20), size=1.8)
    sch.add_text("ADC and digital interpretation", position=(146, 20), size=1.8)
    sch.add_text("Host interface", position=(232, 20), size=1.8)
    sch.add_text("U1D is exposed as a spare buffered channel for future observation use", position=(72, 162), size=1.2)
    sch.add_text("AIN1 tied to GND for single-ended ADS1114 measurement", position=(145, 48), size=1.2)

    # Net labels / pin names
    for ref, pin, net in [
        ("J1", "1", "GND"),
        ("J1", "2", "KEY_ADC2_RAW"),
        ("J1", "3", "KEY_ADC1_RAW"),
        ("J1", "4", "KEY_LED_RAW"),
        ("J2", "3", "I2C_SDA"),
        ("J2", "4", "I2C_SCL"),
        ("J2", "5", "ADC_ALERT"),
        ("J2", "6", "KEY1_IN_GPIO"),
        ("J2", "7", "LED_IN_GPIO"),
        ("J3", "1", "SPARE_IN_RAW"),
        ("J3", "2", "SPARE_BUF"),
        ("R1", "1", "KEY_ADC2_RAW"),
        ("R1", "2", "KEY_ADC2_SENSE"),
        ("R2", "1", "KEY_ADC1_RAW"),
        ("R2", "2", "KEY_ADC1_SENSE"),
        ("R3", "1", "KEY_LED_RAW"),
        ("R3", "2", "KEY_LED_SENSE"),
        ("C6", "1", "KEY_ADC2_SENSE"),
        ("C6", "2", "GND"),
        ("C7", "1", "KEY_ADC1_SENSE"),
        ("C7", "2", "GND"),
        ("C8", "1", "KEY_LED_SENSE"),
        ("C8", "2", "GND"),
        ("U2", "1", "GND"),
        ("U2", "2", "ADC_ALERT"),
        ("U2", "3", "GND"),
        ("U2", "4", "KEY_ADC2_BUF"),
        ("U2", "5", "GND"),
        ("U2", "8", "+3V3"),
        ("U2", "9", "I2C_SDA"),
        ("U2", "10", "I2C_SCL"),
        ("U3", "2", "KEY_ADC1_BUF"),
        ("U3", "4", "KEY1_IN_GPIO"),
        ("U3", "3", "GND"),
        ("U3", "5", "+3V3"),
        ("U4", "2", "KEY_LED_BUF"),
        ("U4", "4", "LED_IN_GPIO"),
        ("U4", "3", "GND"),
        ("U4", "5", "+3V3"),
        ("R4", "1", "+3V3"),
        ("R4", "2", "I2C_SDA"),
        ("R5", "1", "+3V3"),
        ("R5", "2", "I2C_SCL"),
        ("C1", "1", "+3V3"),
        ("C1", "2", "GND"),
        ("C2", "1", "+3V3"),
        ("C2", "2", "GND"),
        ("C3", "1", "+3V3"),
        ("C3", "2", "GND"),
        ("C4", "1", "+3V3"),
        ("C4", "2", "GND"),
        ("C5", "1", "+3V3"),
        ("C5", "2", "GND"),
    ]:
        pin_label(sch, ref, pin, net)

    # U1 is multi-unit; place its labels and feedback wires explicitly so units do not alias.
    add_label_at(sch, "KEY_ADC2_SENSE", (97.79, 36.83), 180)
    add_label_at(sch, "KEY_ADC2_BUF", (113.03, 34.29), 0)
    add_wire_chain(sch, (97.79, 31.75), (105.41, 31.75), (105.41, 34.29), (113.03, 34.29))

    add_label_at(sch, "KEY_ADC1_SENSE", (97.79, 62.23), 180)
    add_label_at(sch, "KEY_ADC1_BUF", (113.03, 59.69), 0)
    add_wire_chain(sch, (97.79, 57.15), (105.41, 57.15), (105.41, 59.69), (113.03, 59.69))

    add_label_at(sch, "KEY_LED_SENSE", (97.79, 88.9), 180)
    add_label_at(sch, "KEY_LED_BUF", (113.03, 86.36), 0)
    add_wire_chain(sch, (97.79, 83.82), (105.41, 83.82), (105.41, 86.36), (113.03, 86.36))

    add_label_at(sch, "+3V3", (102.87, 125.73), 90)
    add_label_at(sch, "GND", (102.87, 110.49), 270)

    # Direct local wiring where analog intent should stay obvious
    sch.connect_pins_with_wire("R1", "2", "C6", "1")
    sch.connect_pins_with_wire("R2", "2", "C7", "1")
    sch.connect_pins_with_wire("R3", "2", "C8", "1")
    add_wire_chain(sch, pin_pos(sch, "C6", "2"), (82.55, 31.75))
    add_wire_chain(sch, pin_pos(sch, "C7", "2"), (82.55, 63.5))
    add_wire_chain(sch, pin_pos(sch, "C8", "2"), (82.55, 95.25))

    # Make the main signal path human-readable instead of relying only on net labels.
    add_wire_chain(sch, pin_pos(sch, "J1", "2"), (38.1, 59.69), (38.1, 30.48), pin_pos(sch, "R1", "1"))
    add_wire_chain(sch, pin_pos(sch, "J1", "3"), (38.1, 62.23), (38.1, 55.88), pin_pos(sch, "R2", "1"))
    add_wire_chain(sch, pin_pos(sch, "J1", "4"), (38.1, 64.77), (38.1, 81.28), pin_pos(sch, "R3", "1"))

    add_wire_chain(sch, pin_pos(sch, "R1", "2"), (76.2, 38.1), (76.2, 36.83), (97.79, 36.83))
    add_wire_chain(sch, pin_pos(sch, "R2", "2"), (76.2, 63.5), (76.2, 62.23), (97.79, 62.23))
    add_wire_chain(sch, pin_pos(sch, "R3", "2"), (76.2, 90.17), (76.2, 88.9), (97.79, 88.9))

    add_wire_chain(sch, (113.03, 34.29), (129.54, 34.29), (129.54, 31.75), pin_pos(sch, "U2", "4"))
    add_wire_chain(sch, (113.03, 59.69), (129.54, 59.69), (129.54, 63.5), pin_pos(sch, "U3", "2"))
    add_wire_chain(sch, (113.03, 86.36), (129.54, 86.36), (129.54, 91.44), pin_pos(sch, "U4", "2"))

    add_wire_chain(sch, pin_pos(sch, "U2", "2"), (177.8, 29.21), (177.8, 62.23), pin_pos(sch, "J2", "5"))
    add_wire_chain(sch, pin_pos(sch, "U3", "4"), (180.34, 63.5), (180.34, 64.77), pin_pos(sch, "J2", "6"))
    add_wire_chain(sch, pin_pos(sch, "U4", "4"), (182.88, 91.44), (182.88, 67.31), pin_pos(sch, "J2", "7"))

    # Spare op-amp channel wired as a future unity-gain buffer with external access.
    add_wire_chain(sch, pin_pos(sch, "J3", "1"), (38.1, 149.86), (38.1, 147.32), (97.79, 147.32))
    add_wire_chain(sch, (113.03, 144.78), (121.92, 144.78), (121.92, 142.24), (97.79, 142.24))
    add_wire_chain(sch, (113.03, 144.78), (132.08, 144.78), (132.08, 152.4), (38.1, 152.4), pin_pos(sch, "J3", "2"))

    # Make power and decoupling visibly local to each IC instead of relying on remote labels.
    add_wire_chain(sch, (128.27, 114.3), (114.3, 114.3), (114.3, 125.73), (102.87, 125.73))
    add_wire_chain(sch, (128.27, 121.92), (114.3, 121.92), (114.3, 110.49), (102.87, 110.49))
    sch.connect_pins_with_wire("U2", "8", "C2", "1")
    sch.connect_pins_with_wire("U2", "3", "C2", "2")
    sch.connect_pins_with_wire("U3", "5", "C3", "1")
    sch.connect_pins_with_wire("U3", "3", "C3", "2")
    sch.connect_pins_with_wire("U4", "5", "C4", "1")
    sch.connect_pins_with_wire("U4", "3", "C4", "2")
    sch.connect_pins_with_wire("J2", "1", "C5", "1")
    sch.connect_pins_with_wire("J2", "2", "C5", "2")
    add_wire_chain(sch, pin_pos(sch, "#FLG01", "1"), (224.79, 13.97), pin_pos(sch, "C5", "1"))
    add_wire_chain(sch, pin_pos(sch, "#FLG02", "1"), (224.79, 21.59), pin_pos(sch, "C5", "2"))
    add_wire_chain(sch, pin_pos(sch, "C5", "1"), (236.22, 13.97))
    add_wire_chain(sch, pin_pos(sch, "C5", "2"), (236.22, 21.59))
    add_label_at(sch, "+3V3", (236.22, 13.97), 0)
    add_label_at(sch, "GND", (236.22, 21.59), 0)

    # Explicit I2C pull-up and host wiring.
    add_wire_chain(sch, pin_pos(sch, "U2", "9"), (176.53, 36.83), (176.53, 43.18), pin_pos(sch, "R4", "2"))
    add_wire_chain(sch, pin_pos(sch, "R4", "2"), (210.82, 43.18), (210.82, 57.15), pin_pos(sch, "J2", "3"))
    add_wire_chain(sch, pin_pos(sch, "R4", "1"), (198.12, 35.56), (198.12, 13.97), pin_pos(sch, "C5", "1"))

    add_wire_chain(sch, pin_pos(sch, "U2", "10"), (179.07, 34.29), (179.07, 55.88), pin_pos(sch, "R5", "2"))
    add_wire_chain(sch, pin_pos(sch, "R5", "2"), (213.36, 55.88), (213.36, 59.69), pin_pos(sch, "J2", "4"))
    add_wire_chain(sch, pin_pos(sch, "R5", "1"), (200.66, 48.26), (200.66, 13.97), pin_pos(sch, "C5", "1"))

    # ADC
    mark_no_connect(sch, "U2", "6")
    mark_no_connect(sch, "U2", "7")

    # Schmitt buffers
    mark_no_connect(sch, "U3", "1")
    mark_no_connect(sch, "U4", "1")

    sch.save_as(SCH_PATH)

    # Project file: reuse the existing KiCad project structure as a template
    template_pro = REPO_ROOT / "hardware" / "kicad" / "phase-3-observation" / "phase-3-observation.kicad_pro"
    if template_pro.exists():
        shutil.copyfile(template_pro, PRO_PATH)
    elif not PRO_PATH.exists():
        PRO_PATH.write_text(json.dumps({"meta": {"filename": PRO_PATH.name, "version": 1}}, indent=2) + "\n")


if __name__ == "__main__":
    main()
