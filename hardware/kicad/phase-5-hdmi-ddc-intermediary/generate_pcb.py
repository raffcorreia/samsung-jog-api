from pathlib import Path
import pcbnew


PROJECT_DIR = Path(__file__).resolve().parent
BOARD_PATH = PROJECT_DIR / "phase-5-hdmi-ddc-intermediary.kicad_pcb"

LIB_ROOT = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
LIBS = {
    "Connector_Video": str(LIB_ROOT / "Connector_Video.pretty"),
    "Package_SO": str(LIB_ROOT / "Package_SO.pretty"),
    "Package_TO_SOT_SMD": str(LIB_ROOT / "Package_TO_SOT_SMD.pretty"),
    "Resistor_SMD": str(LIB_ROOT / "Resistor_SMD.pretty"),
    "Capacitor_SMD": str(LIB_ROOT / "Capacitor_SMD.pretty"),
    "Connector_PinHeader_2.54mm": str(LIB_ROOT / "Connector_PinHeader_2.54mm.pretty"),
}


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def pt(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def load_fp(lib: str, name: str) -> pcbnew.FOOTPRINT:
    fp = pcbnew.FootprintLoad(LIBS[lib], name)
    if fp is None:
        raise RuntimeError(f"missing footprint {lib}:{name}")
    return fp


def pad_map(fp: pcbnew.FOOTPRINT):
    pads = {}
    for pad in fp.Pads():
        pads.setdefault(pad.GetNumber(), []).append(pad)
    return pads


NETS = {
    "GND",
    "+5V_PI",
    "+3V3_PI",
    "TMDS2_P",
    "TMDS2_N",
    "TMDS1_P",
    "TMDS1_N",
    "TMDS0_P",
    "TMDS0_N",
    "TMDSCLK_P",
    "TMDSCLK_N",
    "CEC",
    "UTILITY",
    "SCL_SRC",
    "SDA_SRC",
    "SCL_DDC",
    "SDA_DDC",
    "HDMI_5V_SRC",
    "HDMI_5V_MON",
    "HPD_MON_SRC",
    "PI_SCL",
    "PI_SDA",
    "PI_DDC_DISC_REQ",
    "TCA4307_EN",
    "DDC_READY",
    "SRC_5V_SENSE",
    "HPD_SENSE",
    "VSNS_SET",
    "ILIM_SET",
    "MON_5V_DISABLE",
    "PIN18_STAT",
    "RESERVED_GPIO",
}


FOOTPRINTS = {
    "J1": ("Connector_Video", "HDMI_A_Amphenol_10029449-x01xLF_Horizontal", (20.0, 57.0), 180),
    "J2": ("Connector_Video", "HDMI_A_Amphenol_10029449-x01xLF_Horizontal", (90.0, 57.0), 180),
    "J3": ("Connector_PinHeader_2.54mm", "PinHeader_1x12_P2.54mm_Vertical", (103.0, 18.0), 0),
    "U1": ("Package_SO", "MSOP-8_3x3mm_P0.65mm", (38.0, 20.0), 0),
    "U2": ("Package_TO_SOT_SMD", "SOT-23-8", (57.0, 20.0), 180),
    "U3": ("Package_SO", "TSSOP-8_4.4x3mm_P0.65mm", (58.0, 40.0), 0),
    "Q1": ("Package_TO_SOT_SMD", "SOT-23", (28.0, 35.0), 0),
    "R1": ("Resistor_SMD", "R_0603_1608Metric", (23.0, 30.0), 90),
    "R2": ("Resistor_SMD", "R_0603_1608Metric", (23.0, 35.0), 90),
    "R3": ("Resistor_SMD", "R_0603_1608Metric", (48.0, 28.0), 90),
    "R4": ("Resistor_SMD", "R_0603_1608Metric", (64.0, 28.0), 90),
    "R5": ("Resistor_SMD", "R_0603_1608Metric", (68.0, 28.0), 90),
    "R6": ("Resistor_SMD", "R_0603_1608Metric", (42.0, 44.0), 90),
    "R7": ("Resistor_SMD", "R_0603_1608Metric", (42.0, 49.0), 90),
    "R8": ("Resistor_SMD", "R_0603_1608Metric", (74.0, 44.0), 90),
    "R9": ("Resistor_SMD", "R_0603_1608Metric", (74.0, 49.0), 90),
    "R10": ("Resistor_SMD", "R_0603_1608Metric", (49.0, 40.0), 0),
    "R11": ("Resistor_SMD", "R_0603_1608Metric", (68.0, 36.0), 90),
    "R12": ("Resistor_SMD", "R_0603_1608Metric", (49.0, 35.0), 90),
    "C1": ("Capacitor_SMD", "C_0603_1608Metric", (33.5, 20.0), 90),
    "C2": ("Capacitor_SMD", "C_0603_1608Metric", (53.0, 46.0), 90),
    "C3": ("Capacitor_SMD", "C_0603_1608Metric", (47.0, 44.0), 90),
    "C4": ("Capacitor_SMD", "C_0603_1608Metric", (79.0, 40.0), 90),
}

VALUES = {
    "J1": "HDMI_SOURCE",
    "J2": "HDMI_MONITOR",
    "J3": "PI_HOST_CTRL",
    "U1": "TCA4307DGKR",
    "U2": "PCA9306DCTR",
    "U3": "TPS2113APWR",
    "Q1": "2N7002",
    "R1": "100k", "R2": "100k", "R3": "10k", "R4": "4.7k", "R5": "4.7k",
    "R6": "100k", "R7": "100k", "R8": "100k", "R9": "100k", "R10": "100k",
    "R11": "100k", "R12": "1k",
    "C1": "100n", "C2": "100n", "C3": "100n", "C4": "100n",
}


PAD_NETS = {
    "J1": {
        "1": "TMDS2_P", "2": "GND", "3": "TMDS2_N", "4": "TMDS1_P", "5": "GND",
        "6": "TMDS1_N", "7": "TMDS0_P", "8": "GND", "9": "TMDS0_N", "10": "TMDSCLK_P",
        "11": "GND", "12": "TMDSCLK_N", "13": "CEC", "14": "UTILITY", "15": "SCL_SRC",
        "16": "SDA_SRC", "17": "GND", "18": "HDMI_5V_SRC", "19": "HPD_MON_SRC", "SH": "GND",
    },
    "J2": {
        "1": "TMDS2_P", "2": "GND", "3": "TMDS2_N", "4": "TMDS1_P", "5": "GND",
        "6": "TMDS1_N", "7": "TMDS0_P", "8": "GND", "9": "TMDS0_N", "10": "TMDSCLK_P",
        "11": "GND", "12": "TMDSCLK_N", "13": "CEC", "14": "UTILITY", "15": "SCL_DDC",
        "16": "SDA_DDC", "17": "GND", "18": "HDMI_5V_MON", "19": "HPD_MON_SRC", "SH": "GND",
    },
    "J3": {
        "1": "+5V_PI", "2": "+3V3_PI", "3": "GND", "4": "PI_SCL", "5": "PI_SDA", "6": "PI_DDC_DISC_REQ",
        "7": "MON_5V_DISABLE", "8": "SRC_5V_SENSE", "9": "DDC_READY", "10": "PIN18_STAT",
        "11": "HPD_SENSE", "12": "RESERVED_GPIO",
    },
    "U1": {"1": "TCA4307_EN", "2": "SCL_DDC", "3": "SCL_SRC", "4": "GND", "5": "DDC_READY", "6": "SDA_SRC", "7": "SDA_DDC", "8": "+5V_PI"},
    "U2": {"1": "GND", "2": "+3V3_PI", "3": "PI_SCL", "4": "PI_SDA", "5": "SDA_DDC", "6": "SCL_DDC", "7": "+5V_PI", "8": "+5V_PI"},
    "U3": {"1": "HDMI_5V_SRC", "2": "HDMI_5V_MON", "3": "+5V_PI", "4": "GND", "5": "ILIM_SET", "6": "VSNS_SET", "7": "MON_5V_DISABLE", "8": "PIN18_STAT"},
    "Q1": {"1": "PI_DDC_DISC_REQ", "2": "TCA4307_EN", "3": "GND"},
    "R1": {"1": "+5V_PI", "2": "TCA4307_EN"},
    "R2": {"1": "PI_DDC_DISC_REQ", "2": "GND"},
    "R3": {"1": "+3V3_PI", "2": "DDC_READY"},
    "R4": {"1": "+5V_PI", "2": "SCL_DDC"},
    "R5": {"1": "+5V_PI", "2": "SDA_DDC"},
    "R6": {"1": "HDMI_5V_SRC", "2": "SRC_5V_SENSE"},
    "R7": {"1": "SRC_5V_SENSE", "2": "GND"},
    "R8": {"1": "HPD_MON_SRC", "2": "HPD_SENSE"},
    "R9": {"1": "HPD_SENSE", "2": "GND"},
    "R10": {"1": "HDMI_5V_SRC", "2": "VSNS_SET"},
    "R11": {"1": "GND", "2": "MON_5V_DISABLE"},
    "R12": {"1": "ILIM_SET", "2": "GND"},
    "C1": {"1": "+5V_PI", "2": "GND"},
    "C2": {"1": "+5V_PI", "2": "GND"},
    "C3": {"1": "HDMI_5V_SRC", "2": "GND"},
    "C4": {"1": "HDMI_5V_MON", "2": "GND"},
}


DIRECT_J1_J2_NETS = [
    "TMDS2_P", "TMDS2_N", "TMDS1_P", "TMDS1_N", "TMDS0_P", "TMDS0_N",
    "TMDSCLK_P", "TMDSCLK_N", "CEC", "UTILITY",
]


def add_track(board, net, points, width=0.2, layer=pcbnew.F_Cu):
    for start, end in zip(points, points[1:]):
        if start == end:
            continue
        track = pcbnew.PCB_TRACK(board)
        track.SetNet(net)
        track.SetLayer(layer)
        track.SetWidth(mm(width))
        track.SetStart(pt(*start))
        track.SetEnd(pt(*end))
        board.Add(track)


def add_via(board, net, x, y, drill=0.3, diameter=0.6):
    via = pcbnew.PCB_VIA(board)
    via.SetNet(net)
    via.SetPosition(pt(x, y))
    via.SetDrill(mm(drill))
    via.SetWidth(mm(diameter))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)


def track_to_pad(board, net, start, pad, layer=pcbnew.F_Cu, width=0.2):
    end = (pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y))
    add_track(board, net, [start, end], width=width, layer=layer)


def add_zone(board, net, layer, points, clearance=0.2, min_thickness=0.2):
    zone = pcbnew.ZONE(board)
    zone.SetNet(net)
    zone.SetLayer(layer)
    zone.SetLocalClearance(mm(clearance))
    zone.SetMinThickness(mm(min_thickness))
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in points:
        outline.Append(mm(x), mm(y))
    board.Add(zone)


def fanout_to_via(board, net, pad, via_xy, width=0.2):
    pad_xy = (pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y))
    add_track(board, net, [pad_xy, via_xy], width=width, layer=pcbnew.F_Cu)
    add_via(board, net, via_xy[0], via_xy[1])


def route_via_link(board, net, src_pad, src_via_xy, dst_via_xy, dst_pad, width=0.2, mid_layer=pcbnew.B_Cu):
    fanout_to_via(board, net, src_pad, src_via_xy, width=width)
    add_track(board, net, [src_via_xy, dst_via_xy], width=width, layer=mid_layer)
    add_via(board, net, dst_via_xy[0], dst_via_xy[1])
    add_track(
        board,
        net,
        [dst_via_xy, (pcbnew.ToMM(dst_pad.GetPosition().x), pcbnew.ToMM(dst_pad.GetPosition().y))],
        width=width,
        layer=pcbnew.F_Cu,
    )


def build_board():
    board = pcbnew.BOARD()
    board.SetFileName(str(BOARD_PATH))

    settings = board.GetDesignSettings()
    settings.SetCopperLayerCount(4)

    nets = {}
    for name in sorted(NETS):
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net

    footprints = {}
    for ref, (lib, fp_name, (x, y), rotation) in FOOTPRINTS.items():
        fp = load_fp(lib, fp_name)
        fp.SetReference(ref)
        fp.SetValue(VALUES[ref])
        fp.SetPosition(pt(x, y))
        fp.SetOrientationDegrees(rotation)
        board.Add(fp)
        footprints[ref] = fp

    for ref, pin_map in PAD_NETS.items():
        pads = pad_map(footprints[ref])
        for pin, net_name in pin_map.items():
            for pad in pads[pin]:
                pad.SetNet(nets[net_name])

    # Board outline
    for start, end in [((0, 0), (110, 0)), ((110, 0), (110, 65)), ((110, 65), (0, 65)), ((0, 65), (0, 0))]:
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetStart(pt(*start))
        shape.SetEnd(pt(*end))
        shape.SetWidth(mm(0.1))
        board.Add(shape)

    # Silkscreen
    text = pcbnew.PCB_TEXT(board)
    text.SetText("Phase 5 HDMI DDC Intermediary Rev A")
    text.SetLayer(pcbnew.F_SilkS)
    text.SetPosition(pt(55, 58))
    text.SetTextSize(pcbnew.VECTOR2I(mm(1.2), mm(1.2)))
    board.Add(text)

    pads = {ref: pad_map(fp) for ref, fp in footprints.items()}

    def pad_xy(ref, pin, index=0):
        pad = pads[ref][pin][index]
        return (pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y))

    gnd = nets["GND"]
    p5 = nets["+5V_PI"]
    p33 = nets["+3V3_PI"]

    # Ground planes handle nearly all ground connectivity cleanly.
    add_zone(board, gnd, pcbnew.F_Cu, [(0.25, 0.25), (109.75, 0.25), (109.75, 64.75), (0.25, 64.75)])
    add_zone(board, gnd, pcbnew.B_Cu, [(0.25, 0.25), (109.75, 0.25), (109.75, 64.75), (0.25, 64.75)])

    # Power rails on the back layer, kept well above the active routing area.
    add_track(board, p5, [(20.5, 12), (106, 12)], width=0.5, layer=pcbnew.In2_Cu)
    add_track(board, p33, [(46, 8), (106, 8)], width=0.4, layer=pcbnew.In2_Cu)

    def power_branch_via(ref, pin, net, via_xy, rail_y, width=0.25):
        fanout_to_via(board, net, pads[ref][pin][0], via_xy, width=width)
        add_track(board, net, [via_xy, (via_xy[0], rail_y)], width=width, layer=pcbnew.In2_Cu)

    add_track(board, p5, [pad_xy("J3", "1"), (103.0, 12.0)], width=0.25, layer=pcbnew.In2_Cu)
    add_track(board, p33, [pad_xy("J3", "2"), (105.5, 20.54), (105.5, 8.0)], width=0.25, layer=pcbnew.In2_Cu)

    power_branch_via("U1", "8", p5, (42.5, 17.8), 12.0)
    power_branch_via("U2", "2", p33, (62.0, 24.5), 8.0)
    power_branch_via("U2", "7", p5, (52.0, 22.5), 12.0)
    add_track(board, p5, [pad_xy("U2", "8"), (53.8, 20.975)], width=0.25)
    power_branch_via("U3", "3", p5, (52.5, 42.0), 12.0)
    power_branch_via("R1", "1", p5, (20.5, 31.0), 12.0)
    power_branch_via("R4", "1", p5, (66.0, 30.5), 12.0)
    power_branch_via("R5", "1", p5, (70.0, 30.5), 12.0)
    power_branch_via("C1", "1", p5, (29.0, 22.0), 12.0)
    power_branch_via("C2", "1", p5, (51.0, 48.0), 12.0)
    power_branch_via("R3", "1", p33, (50.0, 30.5), 8.0)

    # Direct HDMI pass-through in a dedicated corridor above the connector shell pads.
    direct_y = {
        "TMDS2_P": 60.0,
        "TMDS2_N": 59.2,
        "TMDS1_P": 58.4,
        "TMDS1_N": 57.6,
        "TMDS0_P": 56.8,
        "TMDS0_N": 56.0,
        "TMDSCLK_P": 55.2,
        "TMDSCLK_N": 54.4,
        "CEC": 53.6,
        "UTILITY": 52.8,
    }
    for net_name in DIRECT_J1_J2_NETS:
        j1_pad = next(p for num, lst in pads["J1"].items() for p in lst if PAD_NETS["J1"].get(num) == net_name)
        j2_pad = next(p for num, lst in pads["J2"].items() for p in lst if PAD_NETS["J2"].get(num) == net_name)
        p1 = (pcbnew.ToMM(j1_pad.GetPosition().x), pcbnew.ToMM(j1_pad.GetPosition().y))
        p2 = (pcbnew.ToMM(j2_pad.GetPosition().x), pcbnew.ToMM(j2_pad.GetPosition().y))
        y_mid = direct_y[net_name]
        route_via_link(board, nets[net_name], j1_pad, (p1[0], y_mid), (p2[0], y_mid), j2_pad, width=0.2, mid_layer=pcbnew.In1_Cu)

    # Controlled connector nets enter the upper component area through B.Cu feeders.
    fanout_to_via(board, nets["SCL_SRC"], pads["J1"]["15"][0], (22.25, 40.0))
    fanout_to_via(board, nets["SDA_SRC"], pads["J1"]["16"][0], (22.75, 38.0))
    fanout_to_via(board, nets["SCL_DDC"], pads["J2"]["15"][0], (92.25, 40.0))
    fanout_to_via(board, nets["SDA_DDC"], pads["J2"]["16"][0], (92.75, 38.0))

    add_track(board, nets["SCL_SRC"], [(22.25, 40.0), (22.25, 24.0), (29.5, 24.0), (29.5, 22.0), (31.0, 22.0)], width=0.2, layer=pcbnew.B_Cu)
    add_track(board, nets["SDA_SRC"], [(22.75, 38.0), (22.75, 22.0), (42.5, 22.0), (42.5, 20.325)], width=0.2, layer=pcbnew.B_Cu)
    fanout_to_via(board, nets["SCL_SRC"], pads["U1"]["3"][0], (31.0, 22.0))
    fanout_to_via(board, nets["SDA_SRC"], pads["U1"]["6"][0], (42.5, 20.325))

    add_track(board, nets["SCL_DDC"], [(92.25, 40.0), (92.25, 24.5), (60.0, 24.5), (60.0, 22.5)], width=0.2, layer=pcbnew.B_Cu)
    add_track(board, nets["SDA_DDC"], [(92.75, 38.0), (92.75, 23.0), (64.5, 23.0), (64.5, 15.5)], width=0.2, layer=pcbnew.B_Cu)
    fanout_to_via(board, nets["SCL_DDC"], pads["U2"]["6"][0], (60.0, 22.5))
    fanout_to_via(board, nets["SDA_DDC"], pads["U2"]["5"][0], (64.5, 15.5))

    # Upper-area local interconnect for the DDC side.
    add_track(board, nets["SCL_DDC"], [(60.0, 22.5), (60.0, 18.0), (50.0, 18.0), (50.0, 19.675), pad_xy("U1", "2")], width=0.2)
    add_track(board, nets["SDA_DDC"], [(64.5, 15.5), (50.0, 15.5), (50.0, 19.025), pad_xy("U1", "7")], width=0.2)
    add_track(board, nets["SCL_DDC"], [(60.0, 22.5), (60.0, 27.175), pad_xy("R4", "2")], width=0.2)
    add_track(board, nets["SDA_DDC"], [(64.5, 15.5), (67.0, 15.5), (67.0, 27.175), pad_xy("R5", "2")], width=0.2)

    # Pi-side I2C and control. Keep the long ownership/status runs on B.Cu.
    fanout_to_via(board, nets["PI_SCL"], pads["J3"]["4"][0], (99.5, 25.62))
    fanout_to_via(board, nets["PI_SDA"], pads["J3"]["5"][0], (98.5, 28.16))
    fanout_to_via(board, nets["PI_SCL"], pads["U2"]["3"][0], (63.5, 20.5))
    fanout_to_via(board, nets["PI_SDA"], pads["U2"]["4"][0], (63.5, 18.2))
    add_track(board, nets["PI_SCL"], [(99.5, 25.62), (99.5, 13.5), (64.5, 13.5), (64.5, 20.5), (63.5, 20.5)], width=0.2, layer=pcbnew.B_Cu)
    add_track(board, nets["PI_SDA"], [(98.5, 28.16), (98.5, 11.5), (61.5, 11.5), (61.5, 18.2), (63.5, 18.2)], width=0.2, layer=pcbnew.B_Cu)

    add_track(board, nets["TCA4307_EN"], [pad_xy("U1", "1"), (31.5, 19.025), (31.5, 31.5), (24.5, 31.5), pad_xy("R1", "2")], width=0.2)
    add_track(board, nets["TCA4307_EN"], [pad_xy("Q1", "2"), (26.0, 35.95), (26.0, 31.5), (24.5, 31.5)], width=0.2)
    fanout_to_via(board, nets["PI_DDC_DISC_REQ"], pads["J3"]["6"][0], (97.5, 30.7))
    fanout_to_via(board, nets["PI_DDC_DISC_REQ"], pads["Q1"]["1"][0], (24.0, 32.5))
    add_track(board, nets["PI_DDC_DISC_REQ"], [(97.5, 30.7), (97.5, 33.0), (24.0, 33.0), (24.0, 32.5)], width=0.2, layer=pcbnew.B_Cu)
    add_track(board, nets["PI_DDC_DISC_REQ"], [pad_xy("R2", "1"), (24.5, 35.825), (24.5, 32.5), (24.0, 32.5)], width=0.2)
    add_track(board, nets["DDC_READY"], [pad_xy("U1", "5"), (44.5, 20.975), (44.5, 27.175), pad_xy("R3", "2")], width=0.2)
    fanout_to_via(board, nets["DDC_READY"], pads["J3"]["9"][0], (94.5, 38.32))
    fanout_to_via(board, nets["DDC_READY"], pads["R3"]["2"][0], (44.0, 26.0))
    add_track(board, nets["DDC_READY"], [(94.5, 38.32), (94.5, 29.0), (44.0, 29.0), (44.0, 26.0)], width=0.2, layer=pcbnew.B_Cu)

    # HDMI +5V select and sensing.
    add_track(board, nets["HDMI_5V_SRC"], [pad_xy("J1", "18"), (23.75, 48.5), (44.0, 48.5), (44.0, 39.025), pad_xy("U3", "1")], width=0.25)
    add_track(board, nets["HDMI_5V_SRC"], [pad_xy("R6", "1"), (42.0, 44.825), (42.0, 47.0), (45.0, 47.0)], width=0.25)
    add_track(board, nets["HDMI_5V_SRC"], [pad_xy("R10", "1"), (48.175, 40.0), (45.0, 40.0), (45.0, 47.0)], width=0.25)
    add_track(board, nets["HDMI_5V_SRC"], [pad_xy("C3", "1"), (47.0, 44.775), (47.0, 47.0), (45.0, 47.0)], width=0.25)

    add_track(board, nets["SRC_5V_SENSE"], [pad_xy("R6", "2"), (40.5, 43.175), (40.5, 49.825), pad_xy("R7", "1")], width=0.2)
    fanout_to_via(board, nets["SRC_5V_SENSE"], pads["J3"]["8"][0], (95.5, 35.78))
    fanout_to_via(board, nets["SRC_5V_SENSE"], pads["R7"]["1"][0], (44.5, 50.0))
    add_track(board, nets["SRC_5V_SENSE"], [(95.5, 35.78), (95.5, 51.5), (44.5, 51.5), (44.5, 50.0)], width=0.2, layer=pcbnew.B_Cu)

    add_track(board, nets["HDMI_5V_MON"], [pad_xy("U3", "2"), (64.0, 39.675), (64.0, 50.5), (93.75, 50.5), pad_xy("J2", "18")], width=0.25)
    add_track(board, nets["HDMI_5V_MON"], [pad_xy("C4", "1"), (79.0, 40.775), (79.0, 50.5)], width=0.25)

    add_track(board, nets["VSNS_SET"], [pad_xy("R10", "2"), (52.0, 40.0), (52.0, 41.8), (60.8625, 41.8), pad_xy("U3", "6")], width=0.2)
    add_track(board, nets["ILIM_SET"], [pad_xy("R12", "1"), (50.5, 35.825), (50.5, 42.8), (59.5, 42.8), (59.5, 40.975), pad_xy("U3", "5")], width=0.2)
    fanout_to_via(board, nets["MON_5V_DISABLE"], pads["J3"]["7"][0], (96.5, 33.24))
    fanout_to_via(board, nets["MON_5V_DISABLE"], pads["R11"]["2"][0], (75.0, 33.0))
    add_track(board, nets["MON_5V_DISABLE"], [(96.5, 33.24), (96.5, 31.0), (75.0, 31.0), (75.0, 33.0)], width=0.2, layer=pcbnew.B_Cu)
    add_track(board, nets["MON_5V_DISABLE"], [pad_xy("U3", "7"), (62.5, 39.675), (62.5, 35.175), pad_xy("R11", "2")], width=0.2)
    fanout_to_via(board, nets["PIN18_STAT"], pads["J3"]["10"][0], (93.5, 40.86))
    fanout_to_via(board, nets["PIN18_STAT"], pads["U3"]["8"][0], (82.0, 38.0))
    add_track(board, nets["PIN18_STAT"], [(93.5, 40.86), (93.5, 36.5), (82.0, 36.5), (82.0, 38.0)], width=0.2, layer=pcbnew.B_Cu)

    # HPD pass-through plus observe.
    add_track(board, nets["HPD_MON_SRC"], [pad_xy("J1", "19"), (24.25, 54.0), (94.25, 54.0), pad_xy("J2", "19")], width=0.2)
    add_track(board, nets["HPD_MON_SRC"], [pad_xy("R8", "1"), (72.5, 44.825), (72.5, 54.0)], width=0.2)
    add_track(board, nets["HPD_SENSE"], [pad_xy("R8", "2"), (76.5, 43.175), (76.5, 49.825), pad_xy("R9", "1")], width=0.2)
    fanout_to_via(board, nets["HPD_SENSE"], pads["J3"]["11"][0], (92.5, 43.4))
    fanout_to_via(board, nets["HPD_SENSE"], pads["R9"]["1"][0], (77.5, 48.0))
    add_track(board, nets["HPD_SENSE"], [(92.5, 43.4), (92.5, 47.0), (77.5, 47.0), (77.5, 48.0)], width=0.2, layer=pcbnew.B_Cu)

    board.BuildConnectivity()
    board.Save(str(BOARD_PATH))


if __name__ == "__main__":
    build_board()
