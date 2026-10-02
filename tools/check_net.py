#!/usr/bin/env python3
"""Deterministic connectivity checks on the exported KiCad netlist.

usage: check_net.py <netlist.net>
"""
import sys
from sexp import parse, find, findall

t = parse(open(sys.argv[1]).read())
pin2net, nets = {}, {}
for n in findall(find(t, "nets"), "net"):
    name = find(n, "name")[1]
    nodes = [(find(x, "ref")[1], find(x, "pin")[1]) for x in findall(n, "node")]
    nets[name] = nodes
    for nd in nodes:
        pin2net[nd] = name

fails = 0


def net(ref, pin):
    return pin2net.get((ref, str(pin)))


def same(*pins, msg=""):
    global fails
    ns = {net(r, p) for r, p in pins}
    if len(ns) != 1 or None in ns:
        fails += 1
        print("FAIL same:", msg, [(r, p, net(r, p)) for r, p in pins])


def on(ref, pin, name):
    global fails
    n = net(ref, pin)
    if n is None or n.split("/")[-1] != name:
        fails += 1
        print("FAIL on: %s.%s expected %s got %s" % (ref, pin, name, n))


def via2(a, b, part):
    """a and b connected through 2-pin part (either orientation)."""
    global fails
    na, nb = net(*a), net(*b)
    p1, p2 = net(part, 1), net(part, 2)
    if {na, nb} != {p1, p2}:
        fails += 1
        print("FAIL via %s: %s=%s %s=%s part=%s/%s" % (part, a, na, b, nb, p1, p2))


def comps_on(name):
    for k, v in nets.items():
        if k.split("/")[-1] == name:
            return v
    return []


# ---- PWM: MCU -> DRV8300
# U3 = HB1/HB2/HB3 (BLDC on one driver), U4 = HB4 + brake chopper on channel B
for mpin, drv, dpin in [(42, "U3", 1), (35, "U3", 4), (43, "U3", 2), (36, "U3", 5),
                        (44, "U3", 3), (37, "U3", 6), (45, "U4", 1), (23, "U4", 4), (59, "U4", 5)]:
    same(("U1", mpin), (drv, dpin), msg="PWM U1.%d" % mpin)
on("U4", 2, "GND"); on("U4", 3, "GND"); on("U4", 6, "GND")
on("U4", 10, "GL_BRK")
on("U3", 7, "GVDD"); on("U4", 7, "GVDD"); on("U3", 8, "GND"); on("U4", 8, "GND")
# ---- half bridges: driver SH = high-FET source = low-FET drain ; BST cap across BST-SH
legs = [("U3", 20, 19, 18, 11, "Q1", "Q2"), ("U3", 17, 16, 15, 10, "Q3", "Q4"),
        ("U3", 14, 13, 12, 9, "Q5", "Q6"), ("U4", 20, 19, 18, 11, "Q7", "Q8")]
for drv, bst, gh, shp, gl, qh, ql in legs:
    same((drv, shp), (qh, 1), (ql, 5), msg="phase " + qh)
    on(qh, 5, "VBUS")
    on(ql, 1, "LS_SRC")
    # bootstrap cap: some C with one pin on BST and other on SH
    cb = [r for r, p in nets[net(drv, bst)] if r.startswith("C")]
    assert cb, "no bootstrap cap on %s.%d" % (drv, bst)
    c = cb[0]
    if {net(c, 1), net(c, 2)} != {net(drv, bst), net(drv, shp)}:
        fails += 1
        print("FAIL bootstrap", drv, bst)
    # gate: GH net contains Ron + diode; gate net contains Ron + Roff
    for dpin, q in ((gh, qh), (gl, ql)):
        g_drv, g_fet = net(drv, dpin), net(q, 4)
        rs = {r for r, p in nets[g_drv] if r.startswith("R")} & {r for r, p in nets[g_fet] if r.startswith("R")}
        if len(rs) != 1:
            fails += 1
            print("FAIL gate Ron", q, rs)
        ds = [r for r, p in nets[g_drv] if r.startswith("D")]
        if not ds or net(ds[0], 1) != g_drv:       # diode cathode (pin1) at driver side
            fails += 1
            print("FAIL gate diode orientation", q, ds)
# ---- shunts / INA240
for rs, ina, qh, jpin, mcu_pin in (("RS1", "U5", "Q1", 1, 9), ("RS2", "U6", "Q5", 3, 21)):
    same((rs, 1), (qh, 1), msg=rs + " phase side")
    same((rs, 2), (ina, 8), msg=rs + " IN+ phase-side sense")
    same((rs, 3), (ina, 1), msg=rs + " IN- motor-side sense")
    same((rs, 4), ("J3", jpin), msg=rs + " motor")
    on(ina, 7, "+3V3A"); on(ina, 3, "GND"); on(ina, 6, "+3V3A")
    # INA out -> 100R -> MCU ADC pin
    rr = [r for r, p in nets[net(ina, 5)] if r.startswith("R")]
    assert rr and net(rr[0], 1) in (net("U1", mcu_pin),) or net(rr[0], 2) == net("U1", mcu_pin), ina
same(("J3", 2), ("Q3", 1), msg="J3.2 = PH2"); same(("J3", 4), ("Q7", 1), msg="J3.4 = PH4")
on("RS3", 1, "LS_SRC"); on("RS3", 4, "GND"); on("RS3", 3, "GND")
rr = [r for r, p in nets[net("RS3", 2)] if r.startswith("R") and r != "RS3"]
via2(("RS3", 2), ("U1", 24), rr[0])
# ---- analog
on("U1", 12, "VBUS_SENSE"); on("U1", 8, "NTC"); on("U1", 25, "IBUS_AMP")
# ---- safety chain
same(("U1", 11), ("U11", 1), msg="ENABLE -> PC3 (BKIN2) + AND")
same(("U1", 22), ("U11", 2), msg="MCU_EN")
same(("U11", 4), ("Q13", 1), msg="GVDD_EN -> Q13 gate")
on("Q12", 2, "+12V"); on("Q12", 3, "GVDD")

# ---- supplies
on("U7", 2, "VBUS"); on("U7", 3, "VBUS"); on("U8", 3, "+12V"); on("U12", 1, "+5V"); on("U12", 5, "+3V3")
for p in (16, 32, 48, 64, 1):
    on("U1", p, "+3V3")
for p in (28, 29):
    on("U1", p, "+3V3A")
for p in (15, 31, 47, 63, 27):
    on("U1", p, "GND")
on("Q10", 2, "VBUS"); on("Q10", 3, "VIN_RAW"); on("D1", 1, "VBUS"); on("D1", 2, "GND")
same(("J1", 1), ("J2", 1), ("Q10", 3), msg="VIN_RAW")
# ---- CAN
same(("U1", 62), ("U9", 1), msg="CAN_TX"); same(("U1", 61), ("U9", 4), msg="CAN_RX")
same(("U9", 7), ("J1", 2), ("J2", 2), ("D12", 1), msg="CANH")
same(("U9", 6), ("J1", 3), ("J2", 3), ("D12", 2), msg="CANL")
on("U9", 3, "+5V"); on("U9", 5, "+3V3"); on("U9", 8, "GND")
# ---- encoder SPI1
for a, b in ((18, 1), (19, 2), (20, 3), (58, 4)):
    same(("U1", a), ("U2", b), msg="SPI1 U1.%d" % a)
on("U2", 11, "+3V3A"); on("U2", 12, "+3V3A"); on("U2", 5, "GND")
# ---- SWD
same(("U1", 49), ("J7", 2)); same(("U1", 50), ("J7", 4)); same(("U1", 56), ("J7", 6)); same(("U1", 7), ("J7", 10))
# ---- external SPI via RN3, ABI via RN4, ENABLE/GPIO via RN6
for mpin, rn_l, rn_r, jref, jpin in ((52, 1, 8, "J4", 2), (53, 2, 7, "J4", 3), (54, 3, 6, "J4", 4), (51, 4, 5, "J4", 5)):
    same(("U1", mpin), ("RN3", rn_l)); same(("RN3", rn_r), (jref, jpin))
for mpin, a, b, jpin in ((38, 1, 8, 2), (39, 2, 7, 3), (40, 3, 6, 4)):
    same(("U1", mpin), ("RN4", a)); same(("RN4", b), ("J8", jpin))
for mpin, a, b, jpin in ((2, 1, 8, 2), (60, 2, 7, 3), (11, 3, 6, 4)):
    same(("U1", mpin), ("RN6", a)); same(("RN6", b), ("J6", jpin))
# ---- AUX
on("Q11", 2, "VBUS"); same(("Q11", 3), ("J5", 1), ("D10", 1), msg="AUX_OUT")
same(("U1", 41), ("Q14", 1), msg="AUX_EN")

# single-pin nets (likely unconnected labels)
for k, v in nets.items():
    if len(v) == 1 and not k.startswith("unconnected"):
        print("single-node net:", k, v)
print("FAILS:", fails, " nets:", len(nets))
