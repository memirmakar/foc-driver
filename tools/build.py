#!/usr/bin/env python3
"""Generates the FOC driver KiCad project schematics into ../hardware."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import symlib
from common import HW, Ref
import kisch
from kisch import Sheet, Project

PROJ = "foc-driver"


def write_project():
    netclasses = [
        ("Default", None, []),
        ("HV_Power", "#C81E1E", ["VBUS", "VIN_RAW", "LS_SRC", "PH*", "MOT*", "SW_*12V", "BRK_RES*"]),
        ("Gate_Power", "#E07000", ["+12V", "GVDD", "GVDD_*", "*12V*"]),
        ("LV_Power", "#B4006E", ["+5V", "+3V3", "+3V3A", "*5V*"]),
        ("Gate", "#A05000", ["GH*", "GL*"]),
        ("PWM", "#0050C8", ["PWM_*", "BRK_PWM"]),
        ("Current_Sense", "#008C8C", ["ISENSE_*", "IBUS_*", "ISA*", "ISB*"]),
        ("Analog", "#3C8C00", ["VBUS_SENSE", "NTC"]),
        ("Safety", "#D00000", ["ENABLE*", "MCU_EN", "GVDD_EN", "AUX*"]),
        ("CAN", "#7828A0", ["CAN*", "FDCAN*"]),
        ("SPI_ENC", "#00823C", ["ENC_*"]),
        ("SPI_EXT", "#5A7800", ["EXT_*"]),
        ("ABI_HALL", "#8C5A00", ["ABI*", "HALL*", "J8_*"]),
        ("ADC", "#008C8C", ["ADC_*"]),
        ("Debug", "#505050", ["SWD*", "SWO", "NRST", "UART_*", "ADDR*", "LED_*", "GPIN*", "OSC_*"]),
    ]
    classes, patterns = [], []
    for name, col, pats in netclasses:
        c = {"name": name, "bus_width": 12, "clearance": 0.2, "track_width": 0.25, "via_diameter": 0.6,
             "via_drill": 0.3, "wire_width": 6, "line_style": 0, "priority": 2147483647 if name == "Default" else 10,
             "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}
        if col:
            r, g, b = int(col[1:3], 16), int(col[3:5], 16), int(col[5:7], 16)
            c["schematic_color"] = "rgb(%d, %d, %d)" % (r, g, b)
        classes.append(c)
        for p in pats:
            patterns.append({"netclass": name, "pattern": p})
    pro = {
        "meta": {"filename": PROJ + ".kicad_pro", "version": 3},
        "net_settings": {"classes": classes, "meta": {"version": 4}, "netclass_assignments": None,
                         "netclass_patterns": patterns},
        "schematic": {"drawing": {"default_text_size": 50.0, "label_size_ratio": 0.375,
                                  "pin_symbol_size": 25.0, "text_offset_ratio": 0.15},
                      "meta": {"version": 1}},
        "sheets": [], "text_variables": {}, "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
    }
    with open(os.path.join(HW, PROJ + ".kicad_pro"), "w") as f:
        json.dump(pro, f, indent=2)
    with open(os.path.join(HW, "sym-lib-table"), "w") as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "foc-driver")(type "KiCad")'
                '(uri "${KIPRJMOD}/foc-driver.kicad_sym")(options "")(descr "FOC driver project symbols"))\n)\n')


def main():
    os.makedirs(HW, exist_ok=True)
    symlib.build(os.path.join(HW, "foc-driver.kicad_sym"))
    write_project()
    ref = Ref()
    import sheet_power_stage
    root = Sheet("FOC driver", PROJ + ".kicad_sch", "A3", title="FOC Motor Driver Rev B - MCU")
    itf = Sheet("Interfaces", "interfaces.kicad_sch", "A3", title="Interfaces: CAN, Encoders, I/O")
    itf.tag = "IF"
    ps = Sheet("Power Stage", "power_stage.kicad_sch", "A3", title="Power Stage")
    prj = Project(PROJ, root)
    root.tag, ps.tag = "MCU", "PST"
    import sheet_power_supply
    pw = Sheet("Power Supply", "power_supply.kicad_sch", "A3", title="Power Input & Supplies")
    pw.tag = "PSU"
    prj.add_sub(pw, 345.44, 40.64, 50.8, 15.24)
    prj.add_sub(ps, 345.44, 66.04, 50.8, 15.24)
    prj.add_sub(itf, 345.44, 91.44, 50.8, 15.24)
    import sheet_root
    sheet_root.build(root, ref)
    sheet_root.build_interfaces(itf, ref)
    sheet_power_supply.build(pw, ref)
    sheet_power_stage.build(ps, ref)
    from common import annotate
    annotate([root, itf, pw, ps])
    g = prj.write(HW)
    print("global nets:", len(g))


if __name__ == "__main__":
    main()
