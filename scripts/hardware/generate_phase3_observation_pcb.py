#!/usr/bin/env python3
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


KICAD_PYTHON_SITE = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/lib/python3.9/site-packages"
KICAD_FOOTPRINTS = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")

import sys

sys.path.insert(0, KICAD_PYTHON_SITE)
import pcbnew  # type: ignore


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = REPO_ROOT / "hardware" / "kicad" / "phase-3-observation-reva"
NETLIST_PATH = PROJECT_DIR / "phase-3-observation-reva.net.xml"
PCB_PATH = PROJECT_DIR / "phase-3-observation-reva.kicad_pcb"


def mm(x: float) -> int:
    return pcbnew.FromMM(x)


def v(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def add_outline(board: pcbnew.BOARD, x: float, y: float, w: float, h: float) -> None:
    points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
    for start, end in zip(points, points[1:]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetStart(v(*start))
        seg.SetEnd(v(*end))
        seg.SetWidth(mm(0.1))
        board.Add(seg)


def load_footprint(footprint_id: str) -> pcbnew.FOOTPRINT:
    lib, name = footprint_id.split(":", 1)
    lib_path = str(KICAD_FOOTPRINTS / f"{lib}.pretty")
    fp = pcbnew.FootprintLoad(lib_path, name)
    if fp is None:
        raise RuntimeError(f"Unable to load footprint {footprint_id}")
    return fp


def parse_netlist(path: Path):
    root = ET.parse(path).getroot()

    components = {}
    for comp in root.find("components") or []:
        ref = comp.attrib["ref"]
        components[ref] = {
            "value": comp.findtext("value", ""),
            "footprint": comp.findtext("footprint", ""),
        }

    nets = {}
    for net in root.find("nets") or []:
        name = net.attrib["name"]
        nodes = [(node.attrib["ref"], node.attrib["pin"]) for node in net.findall("node")]
        nets[name] = nodes

    return components, nets


def add_nets(board: pcbnew.BOARD, nets: dict[str, list[tuple[str, str]]]):
    net_map: dict[str, pcbnew.NETINFO_ITEM] = {}
    for idx, name in enumerate(sorted(nets), start=1):
        if name.startswith("unconnected-"):
            continue
        net = pcbnew.NETINFO_ITEM(board, name)
        net.SetNetCode(idx)
        board.Add(net)
        net_map[name] = net
    return net_map


def pad_net_lookup(nets: dict[str, list[tuple[str, str]]]):
    lookup: dict[tuple[str, str], str] = {}
    for net_name, nodes in nets.items():
        if net_name.startswith("unconnected-"):
            continue
        for ref, pin in nodes:
            lookup[(ref, pin)] = net_name
    return lookup


def place(board: pcbnew.BOARD, fp: pcbnew.FOOTPRINT, ref: str, x: float, y: float, rot: float = 0.0):
    fp.SetReference(ref)
    fp.SetPosition(v(x, y))
    fp.SetOrientationDegrees(rot)
    fp.SetAttributes(fp.GetAttributes())
    board.Add(fp)


def add_track(board: pcbnew.BOARD, net: pcbnew.NETINFO_ITEM, points: list[tuple[float, float]], width_mm: float = 0.25):
    for start, end in zip(points, points[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetLayer(pcbnew.F_Cu)
        track.SetWidth(mm(width_mm))
        track.SetNet(net)
        track.SetStart(v(*start))
        track.SetEnd(v(*end))
        board.Add(track)


def main():
    components, nets = parse_netlist(NETLIST_PATH)
    board = pcbnew.BOARD()
    board.SetFileName(str(PCB_PATH))

    add_outline(board, 0, 0, 95, 65)

    net_map = add_nets(board, nets)
    pin_to_net = pad_net_lookup(nets)

    placements = {
        "J1": (6.0, 18.0, 0),
        "J2": (88.0, 18.0, 0),
        "J3": (6.0, 52.0, 0),
        "U1": (33.0, 27.0, 0),
        "U2": (55.0, 18.0, 0),
        "U3": (55.0, 33.0, 0),
        "U4": (55.0, 46.0, 0),
        "R1": (18.0, 14.0, 90),
        "R2": (18.0, 27.0, 90),
        "R3": (18.0, 40.0, 90),
        "R4": (72.0, 12.0, 90),
        "R5": (78.0, 12.0, 90),
        "C1": (41.0, 12.0, 90),
        "C2": (62.0, 10.0, 90),
        "C3": (62.0, 28.0, 90),
        "C4": (62.0, 41.0, 90),
        "C5": (86.0, 10.0, 90),
        "C6": (25.0, 14.0, 90),
        "C7": (25.0, 27.0, 90),
        "C8": (25.0, 40.0, 90),
    }

    footprints: dict[str, pcbnew.FOOTPRINT] = {}
    for ref, data in components.items():
        if ref.startswith("#"):
            continue
        fp = load_footprint(data["footprint"])
        fp.SetReference(ref)
        fp.SetValue(data["value"])
        x, y, rot = placements.get(ref, (10.0, 10.0, 0.0))
        place(board, fp, ref, x, y, rot)
        footprints[ref] = fp

    for ref, fp in footprints.items():
        for pad in fp.Pads():
            net_name = pin_to_net.get((ref, pad.GetPadName()))
            if net_name and net_name in net_map:
                pad.SetNet(net_map[net_name])

    # Simple routing for the clearly linear signal chains and local power.
    def p(ref: str, pad: str):
        return footprints[ref].FindPadByNumber(pad).GetPosition()

    def mm_xy(pos):
        return (pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))

    def route_pad_chain(net_name: str, chain: list[tuple[str, str]], width: float = 0.25):
        points = [mm_xy(p(ref, pad)) for ref, pad in chain]
        # Manhattan chain between points
        for start, end in zip(points, points[1:]):
            sx, sy = start
            ex, ey = end
            add_track(board, net_map[net_name], [(sx, sy), (ex, sy), (ex, ey)], width)

    route_pad_chain("/KEY_ADC2_RAW", [("J1", "2"), ("R1", "1")])
    route_pad_chain("/KEY_ADC2_SENSE", [("R1", "2"), ("C6", "1"), ("U1", "2")])
    route_pad_chain("/KEY_ADC2_BUF", [("U1", "1"), ("U1", "3"), ("U2", "4")])

    route_pad_chain("/KEY_ADC1_RAW", [("J1", "3"), ("R2", "1")])
    route_pad_chain("/KEY_ADC1_SENSE", [("R2", "2"), ("C7", "1"), ("U1", "6")])
    route_pad_chain("/KEY_ADC1_BUF", [("U1", "7"), ("U1", "5"), ("U3", "2")])

    route_pad_chain("/KEY_LED_RAW", [("J1", "4"), ("R3", "1")])
    route_pad_chain("/KEY_LED_SENSE", [("R3", "2"), ("C8", "1"), ("U1", "9")])
    route_pad_chain("/KEY_LED_BUF", [("U1", "8"), ("U1", "10"), ("U4", "2")])

    route_pad_chain("/ADC_ALERT", [("U2", "2"), ("J2", "5")])
    route_pad_chain("/KEY1_IN_GPIO", [("U3", "4"), ("J2", "6")])
    route_pad_chain("/LED_IN_GPIO", [("U4", "4"), ("J2", "7")])

    route_pad_chain("/I2C_SDA", [("U2", "9"), ("R4", "2"), ("J2", "3")], 0.3)
    route_pad_chain("/I2C_SCL", [("U2", "10"), ("R5", "2"), ("J2", "4")], 0.3)

    route_pad_chain("/SPARE_IN_RAW", [("J3", "1"), ("U1", "13")])
    route_pad_chain("/SPARE_BUF", [("U1", "12"), ("U1", "14"), ("J3", "2")])

    # Local +3V3 and GND stitching where components are intentionally clustered.
    for net_name, refs, width in [
        ("/+3V3", [("J2", "1"), ("C5", "1"), ("R4", "1"), ("R5", "1"), ("U2", "8"), ("C2", "1"), ("U3", "5"), ("C3", "1"), ("U4", "5"), ("C4", "1"), ("U1", "11"), ("C1", "1")], 0.4),
        ("/GND", [("J2", "2"), ("C5", "2"), ("J1", "1"), ("U2", "3"), ("C2", "2"), ("U3", "3"), ("C3", "2"), ("U4", "3"), ("C4", "2"), ("U1", "4"), ("C1", "2"), ("C6", "2"), ("C7", "2"), ("C8", "2")], 0.4),
    ]:
        pts = [mm_xy(p(ref, pad)) for ref, pad in refs]
        for start, end in zip(pts, pts[1:]):
            sx, sy = start
            ex, ey = end
            add_track(board, net_map[net_name], [(sx, sy), (sx, ey), (ex, ey)], width)

    pcbnew.SaveBoard(str(PCB_PATH), board)


if __name__ == "__main__":
    main()
