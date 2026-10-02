"""Shared helpers / footprints for the FOC driver schematic build."""
import os
import kisch
from kisch import LIB

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hardware")
LIB.add_file("foc-driver", os.path.join(HW, "foc-driver.kicad_sym"))

FP = dict(
    R0402="Resistor_SMD:R_0402_1005Metric",
    R0603="Resistor_SMD:R_0603_1608Metric",
    R0805="Resistor_SMD:R_0805_2012Metric",
    R1206="Resistor_SMD:R_1206_3216Metric",
    C0402="Capacitor_SMD:C_0402_1005Metric",
    C0603="Capacitor_SMD:C_0603_1608Metric",
    C0805="Capacitor_SMD:C_0805_2012Metric",
    C1206="Capacitor_SMD:C_1206_3216Metric",
    C1210="Capacitor_SMD:C_1210_3225Metric",
    SHUNT="Resistor_SMD:R_Shunt_Vishay_WSK2512_6332Metric_T1.19mm",
    SOD323="Diode_SMD:D_SOD-323",
    SOD123="Diode_SMD:D_SOD-123",
    SMA="Diode_SMD:D_SMA",
    SMC="Diode_SMD:D_SMC",
    SOT23="Package_TO_SOT_SMD:SOT-23",
    SOT235="Package_TO_SOT_SMD:SOT-23-5",
    LED0603="LED_SMD:LED_0603_1608Metric",
    FB0603="Inductor_SMD:L_0603_1608Metric",
    TDSON="Package_TO_SOT_SMD:TDSON-8-1",
    DPAK="Package_TO_SOT_SMD:TO-252-2",
)


class Ref:
    """Reference designator allocator.  Explicit refs are reserved and skipped by auto-numbering."""
    RESERVED = {"D%d" % i for i in range(1, 14)}

    def __init__(self):
        self.n = {}
        self.used = set(self.RESERVED)

    def __call__(self, prefix, num=None):
        if num is not None:
            r = "%s%d" % (prefix, num)
            self.used.add(r)
            return r
        while True:
            self.n[prefix] = self.n.get(prefix, 0) + 1
            r = "%s%d" % (prefix, self.n[prefix])
            if r not in self.used:
                self.used.add(r)
                return r


def R(sh, ref, val, x, y, rot=0, fp="R0603", **kw):
    return sh.place("Device:R_Small_US", ref, val, x, y, rot, footprint=FP.get(fp, fp), **kw)


def C(sh, ref, val, x, y, rot=0, fp="C0603", **kw):
    return sh.place("Device:C_Small", ref, val, x, y, rot, footprint=FP.get(fp, fp), **kw)


def annotate(sheets, prefixes=("R", "C", "D")):
    """Renumber auto-placed passives sheet by sheet, sorted by X then Y (KiCad default order).
    Refs below the per-prefix floor (explicit, BOM-fixed) are kept."""
    floor = {"R": 1, "C": 1, "D": 14}
    for pfx in prefixes:
        n = floor[pfx]
        for sh in sheets:
            insts = [i for i in sh.insts if i.ref.startswith(pfx) and i.ref[len(pfx):].isdigit()
                     and int(i.ref[len(pfx):]) >= floor[pfx]]
            insts.sort(key=lambda i: (round(i.x, 2), round(i.y, 2)))
            for i in insts:
                i.ref = "%s%d" % (pfx, n)
                n += 1
