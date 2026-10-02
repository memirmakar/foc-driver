"""Builds the project symbol library hardware/foc-driver.kicad_sym."""
import copy
from sexp import Sym as S, find, findall, dumps
import kisch
from kisch import LIB

P = 2.54


def _prop(k, v, x, y, hide=False, just=None):
    e = [S("property"), k, v, [S("at"), x, y, 0], kisch.effects(1.27, just, hide)]
    return e


def _pin(num, name, typ, x, y, ang, length=P, alts=None):
    p = [S("pin"), S(typ), S("line"), [S("at"), x, y, ang], [S("length"), length],
         [S("name"), name, kisch.effects(1.27)], [S("number"), num, kisch.effects(1.27)]]
    for a in alts or []:
        p.append(a)
    return p


def make_ic(name, left, right, top=(), bottom=(), width=15.24, ref="U", value=None,
            footprint="", datasheet="", desc="", kw=""):
    """left/right/top/bottom: lists of (num, name, type[, alts]) or None for a gap.
    Pin pitch 2.54 mm.  Returns flattened symbol sexp."""
    n_side = max(len(left), len(right))
    n_tb = max(len(top), len(bottom), 0)
    width = max(width, (n_tb + 1) * P)
    h = (n_side + 1) * P
    h = round(h / P) * P
    w2 = round(width / 2 / P) * P
    y0 = (n_side - 1) * P / 2   # first pin y
    y0 = round(y0 / 1.27) * 1.27
    body = [S("symbol"), name + "_0_1",
            [S("rectangle"), [S("start"), -w2, y0 + P], [S("end"), w2, y0 - n_side * P],
             [S("stroke"), [S("width"), 0.254], [S("type"), S("default")]],
             [S("fill"), [S("type"), S("background")]]]]
    pins = [S("symbol"), name + "_1_1"]
    top_y, bot_y = y0 + P, y0 - n_side * P

    def add(lst, xy_fn, ang):
        for i, it in enumerate(lst):
            if it is None:
                continue
            num, nm, typ = it[0], it[1], it[2]
            alts = it[3] if len(it) > 3 else None
            x, y = xy_fn(i)
            pins.append(_pin(num, nm, typ, x, y, ang, alts=alts))
    add(left, lambda i: (-w2 - P, y0 - i * P), 0)
    add(right, lambda i: (w2 + P, y0 - i * P), 180)
    tx0 = -(len(top) - 1) * P / 2
    tx0 = round(tx0 / 1.27) * 1.27
    add(top, lambda i: (tx0 + i * P, top_y + P), 270)
    bx0 = round(-(len(bottom) - 1) * P / 2 / 1.27) * 1.27
    add(bottom, lambda i: (bx0 + i * P, bot_y - P), 90)
    sym = [S("symbol"), name,
           [S("pin_names"), [S("offset"), 0.762]],
           [S("exclude_from_sim"), S("no")], [S("in_bom"), S("yes")], [S("on_board"), S("yes")],
           _prop("Reference", ref, -w2, top_y + 1.27 + (P if top else 0), just="left bottom"),
           _prop("Value", value or name, w2, top_y + 1.27 + (P if top else 0), just="right bottom"),
           _prop("Footprint", footprint, 0, 0, True),
           _prop("Datasheet", datasheet, 0, 0, True),
           _prop("Description", desc, 0, 0, True),
           _prop("ki_keywords", kw, 0, 0, True),
           body, pins]
    return sym


def make_power(net):
    s = copy.deepcopy(LIB.get("power:VDD"))
    s[1] = net
    for x in s:
        if isinstance(x, list) and x[0] == "property":
            if x[1] == "Value":
                x[2] = net
            if x[1] == "Description":
                x[2] = 'Power symbol creates a global label with name "%s"' % net
        if isinstance(x, list) and x[0] == "symbol":
            x[1] = net + x[1][3:]
    return s


def mcu_symbol():
    """STM32G431RBTx redrawn, grouped by function.  Pin numbers/names/types and
    alternates are copied verbatim from the KiCad library symbol."""
    src = LIB.get("MCU_ST_STM32G4:STM32G431RBTx")
    raw = {}
    for sub in findall(src, "symbol"):
        for p in findall(sub, "pin"):
            num = find(p, "number")[1]
            raw[num] = (find(p, "name")[1], str(p[1]), findall(p, "alternate"))

    def pn(name):
        m = [k for k, v in raw.items() if v[0] == name]
        assert len(m) == 1, name
        k = m[0]
        return (k, raw[k][0], raw[k][1], raw[k][2])

    def pk(num):
        return (num, raw[num][0], raw[num][1], raw[num][2])

    left = [pn("PG10"), None, pn("PF0"), pn("PF1"), None,
            pn("PC1"), pn("PA7"), pn("PB1"), pn("PA0"), pn("PC0"), pn("PB0"), pn("PA1"), pn("PC2"), None,
            pn("PA2"), pn("PA3"), None,
            pn("PA13"), pn("PA14"), pn("PB3"), None,
            pn("PB10"), pn("PB11"), pn("PB12"), pn("PB2"), None,
            pn("PC13"), pn("PC14"), pn("PC15")]
    right = [pn("PA8"), pn("PB13"), pn("PA9"), pn("PB14"), pn("PA10"), pn("PB15"), pn("PA11"), pn("PC5"), None,
             pn("PC3"), pn("PC4"), None,
             pn("PA5"), pn("PA6"), pn("PB5"), pn("PA4"), None,
             pn("PC10"), pn("PC11"), pn("PC12"), pn("PA15"), None,
             pn("PB8"), pn("PB9"), None,
             pn("PC6"), pn("PC7"), pn("PC8"), None,
             pn("PB4"), pn("PD2"), pn("PB7"), pn("PC9"), pn("PB6"), pn("PA12")]
    top = [pk("1"), pk("16"), pk("32"), pk("48"), pk("64"), None, pk("28"), pk("29")]
    bottom = [pk("15"), pk("31"), pk("47"), pk("63"), None, pk("27")]
    used = [x[0] for x in left + right + top + bottom if x]
    assert sorted(used, key=int) == sorted(raw, key=int), set(raw) - set(used)
    sym = make_ic("STM32G431RBTx", left, right, top, bottom, width=35.56,
                  footprint="Package_QFP:LQFP-64_10x10mm_P0.5mm",
                  datasheet="https://www.st.com/resource/en/datasheet/stm32g431rb.pdf",
                  desc="STM32G431RBT6, Cortex-M4F 170 MHz, 128 KB flash, LQFP-64 (redrawn, grouped by function)",
                  kw="STM32G4 ARM Cortex-M4")
    return sym, raw


def build(path):
    syms = []
    # DRV8300D, TSSOP-20 (PW) pinout, SLVSFG5D Figure 6-2
    syms.append(make_ic(
        "DRV8300DPW",
        left=[("1", "INHA", "input"), ("4", "INLA", "input"), None,
              ("2", "INHB", "input"), ("5", "INLB", "input"), None,
              ("6", "INLC", "input"), ("3", "INHC", "input"), None, None, None, None, None, None],
        right=[("20", "BSTA", "passive"), ("19", "GHA", "output"), ("18", "SHA", "passive"), ("11", "GLA", "output"), None,
               ("17", "BSTB", "passive"), ("16", "GHB", "output"), ("15", "SHB", "passive"), ("10", "GLB", "output"), None,
               ("14", "BSTC", "passive"), ("13", "GHC", "output"), ("12", "SHC", "passive"), ("9", "GLC", "output")],
        top=[("7", "GVDD", "power_in")], bottom=[("8", "GND", "power_in")], width=20.32,
        footprint="Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
        datasheet="https://www.ti.com/lit/ds/symlink/drv8300.pdf",
        desc="100-V three-phase half-bridge gate driver, integrated bootstrap diodes, fixed 200 ns dead time, TSSOP-20",
        kw="gate driver half bridge BLDC"))
    # LM5163, SO-8 PowerPAD (DDA)
    syms.append(make_ic(
        "LM5163DDA",
        left=[("2", "VIN", "power_in"), ("3", "EN/UVLO", "input"), ("4", "RON", "passive")],
        right=[("7", "BST", "passive"), ("8", "SW", "power_out"), ("5", "FB", "input")],
        bottom=[("1", "GND", "power_in"), ("9", "EP", "passive"), ("6", "PGOOD", "open_collector")], width=20.32,
        footprint="Package_SO:TI_SO-PowerPAD-8_ThermalVias",
        datasheet="https://www.ti.com/lit/ds/symlink/lm5163.pdf",
        desc="100-V 0.5-A synchronous COT buck converter, SO-8 PowerPAD",
        kw="buck regulator 100V"))
    mcu, raw = mcu_symbol()
    syms.append(mcu)
    for net in ["+3V3", "+3V3A", "+5V", "+12V", "GVDD", "VBUS"]:
        syms.append(make_power(net))
    lib = [S("kicad_symbol_lib"), [S("version"), 20251024], [S("generator"), "kisch"],
           [S("generator_version"), "10.0"]] + syms
    open(path, "w").write(dumps(lib) + "\n")
    return syms, raw


if __name__ == "__main__":
    import sys
    syms, raw = build(sys.argv[1])
    # verify MCU pins identical to library original
    from kisch import sym_pins
    mine = {p["num"]: (p["name"], p["type"]) for p in sym_pins(syms[2])}
    orig = {k: (v[0], v[1]) for k, v in raw.items()}
    assert mine == orig, "MCU pin mismatch"
    print("ok", len(mine), "MCU pins identical")
