"""Power stage: 2x DRV8300, 4 half-bridges (Q1-Q8), in-line shunts + INA240, bus shunt RS3."""
from common import R, C, FP

FET = "Transistor_FET:CSD19534Q5A"
BLUE = (0, 70, 160)
RED = (170, 20, 20)
GREEN = (0, 120, 60)
PURP = (110, 40, 140)
BROWN = (130, 80, 20)


def gate_net(sh, ref, xg, gy, glabel, dref, ron="33R", roff="10R"):
    """Gate network into a FET gate at (xg, gy): Ron from driver, Roff + diode for fast turn-off."""
    above = {"Reference": (0, -4.06, ""), "Value": (0, -2.29, "")}
    below = {"Reference": (0, 2.29, ""), "Value": (0, 4.06, "")}
    R(sh, ref("R"), ron, xg - 10.16, gy, rot=90, fields=above)
    sh.wire((xg - 7.62, gy), (xg, gy))
    sh.wire((xg - 12.7, gy), (xg - 20.32, gy))
    sh.label(glabel, xg - 20.32, gy, 180)
    y2 = gy + 5.08
    sh.place("Device:D_Small", dref, "BAT54", xg - 12.7, y2, footprint=FP["SOD323"], fields=below)
    R(sh, ref("R"), roff, xg - 5.08, y2, rot=90, fields=below)
    sh.wire((xg - 10.16, y2), (xg - 7.62, y2))
    sh.wire((xg - 15.24, gy), (xg - 15.24, y2))
    sh.wire((xg - 2.54, y2), (xg - 2.54, gy))


def half_bridge(sh, ref, k, bx, by, shunt=None):
    """Half-bridge HBk.  Origin (bx, by) = top-left of block."""
    qh = sh.place(FET, ref("Q", 2 * k - 1), "CSD19534Q5A", bx + 48.26, by + 25.4, footprint=FP["TDSON"])
    ql = sh.place(FET, ref("Q", 2 * k), "CSD19534Q5A", bx + 48.26, by + 63.5, footprint=FP["TDSON"])
    gate_net(sh, ref, bx + 43.18, by + 25.4, "GH%d" % k, ref("D", 2 * k))
    gate_net(sh, ref, bx + 43.18, by + 63.5, "GL%d" % k, ref("D", 2 * k + 1))
    xs = bx + 50.8
    sh.wire((xs, by + 20.32), (xs, by + 15.24))
    sh.power("VBUS", xs, by + 15.24)
    sh.wire((xs, by + 30.48), (xs, by + 58.42))
    yp = by + 45.72
    # low-side source -> bus-return node LS_SRC (through RS3 to GND)
    sh.wire((xs, by + 68.58), (xs, by + 71.12), (xs + 5.08, by + 71.12))
    sh.label("LS_SRC", xs + 5.08, by + 71.12, 0)
    if shunt is None:
        sh.wire((xs, yp), (xs + 7.62, yp))
        sh.label("PH%d" % k, xs + 7.62, yp, 0)
    else:
        rs_ref, ina_ref, mot, isense = shunt
        sh.wire((xs, yp), (bx + 60.96, yp))
        sh.label("PH%d" % k, bx + 53.34, yp, 0)
        rs = sh.place("Device:R_Shunt", rs_ref, "4mR 1W", bx + 66.04, yp, rot=90, footprint=FP["SHUNT"],
                      fields={"Reference": (0, 3.0, ""), "Value": (0, 4.8, "")})
        sh.wire(rs.pin("4"), (bx + 81.28, yp))
        sh.label(mot, bx + 81.28, yp, 0)
        ux, uy = bx + 81.28, by + 22.86
        ina = sh.place("Amplifier_Current:INA240A2D", ina_ref, "INA240A2D", ux, uy,
                       footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                       fields={"Reference": (-5.08, -7.4, "right"), "Value": (-5.08, -5.6, "right")})
        p2, p3 = rs.pin("2"), rs.pin("3")
        sh.wire(p2, (p2[0], uy - 2.54), ina.pin("8"))           # phase-side sense -> IN+
        sh.wire(p3, (p3[0], uy + 2.54), ina.pin("1"))           # motor-side sense -> IN-
        vp = ina.pin("6")
        sh.wire(vp, (vp[0], vp[1] - 5.08), (vp[0] + 15.24, vp[1] - 5.08))
        sh.power("+3V3A", vp[0], vp[1] - 5.08)
        C(sh, ref("C"), "100nF", vp[0] + 15.24, vp[1] - 2.54, fp="C0603")
        sh.power("GND", vp[0] + 15.24, vp[1])
        g, r2, r1 = ina.pin("2"), ina.pin("3"), ina.pin("7")
        sh.wire(g, (g[0], g[1] + 2.54), (r2[0], r2[1] + 2.54), r2)
        sh.power("GND", g[0], g[1] + 2.54)
        sh.wire(r1, (r1[0], r1[1] + 5.08), (r1[0] + 5.08, r1[1] + 5.08))
        sh.power("+3V3A", r1[0] + 5.08, r1[1] + 5.08)
        o = ina.pin("5")
        sh.wire(o, (o[0] + 5.08, o[1]))
        sh.label(isense, o[0] + 5.08, o[1], 0)
    # local HF decoupling: 2x 2.2uF 100V X7R 1210 per leg
    cx = bx + 81.28
    C(sh, ref("C"), "2.2uF 100V", cx, by + 60.96, fp="C1210",
      fields={"Reference": (-1.9, -0.95, "right"), "Value": (-1.9, 0.95, "right")})
    C(sh, ref("C"), "2.2uF 100V", cx + 5.08, by + 60.96, fp="C1210")
    sh.wire((cx, by + 58.42), (cx + 5.08, by + 58.42))
    sh.power("VBUS", cx + 2.54, by + 58.42)
    sh.wire((cx, by + 63.5), (cx + 5.08, by + 63.5), (cx + 5.08, by + 66.04), (cx + 7.62, by + 66.04))
    sh.label("LS_SRC", cx + 7.62, by + 66.04, 0)


def driver(sh, ref, uref, dx, dy, phases, inputs, spare_c):
    """DRV8300 at (dx, dy).  phases: [(k, 'A'), (k, 'B')], inputs: label names for left pins."""
    u = sh.place("foc-driver:DRV8300DPW", uref, "DRV8300DPWR", dx, dy, footprint="Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm",
                 fields={"Reference": (3.81, 21.6, "left"), "Value": (3.81, 23.4, "left")})
    for pin, net in inputs.items():
        if net == "GND":
            continue
        sh.pin_label(u, pin, net)
    gnd_in = [p for p, n in inputs.items() if n == "GND"]
    if gnd_in:
        pts = []
        for p in gnd_in:
            x, y = u.pin(p)
            sh.wire((x, y), (x - 2.54, y))
            pts.append((x - 2.54, y))
        pts.sort(key=lambda a: a[1])
        sh.wire(pts[0], pts[-1])
        sh.power("GND", *pts[-1])
    for k, ch in phases:
        bst, gh, shp, gl = u.pin("BST" + ch), u.pin("GH" + ch), u.pin("SH" + ch), u.pin("GL" + ch)
        xc = bst[0] + 10.16
        sh.wire(bst, (xc, bst[1]))
        C(sh, ref("C"), "1uF 25V", xc, gh[1], fp="C0603")
        sh.wire(shp, (xc + 12.7, shp[1]))
        sh.label("PH%d" % k, xc + 12.7, shp[1], 0)
        sh.label("GH%d" % k, gh[0], gh[1], 0)
        sh.label("GL%d" % k, gl[0], gl[1], 0)
    for p, net in spare_c.items():
        if net is None:
            sh.pin_nc(u, p)
        else:
            sh.pin_label(u, p, net)
    # GVDD + decoupling
    gv = u.pin("GVDD")
    yr = gv[1] - 7.62
    sh.wire(gv, (gv[0], yr), (gv[0] - 25.4, yr))
    sh.power("GVDD", gv[0], yr)
    C(sh, ref("C"), "10uF 25V", gv[0] - 15.24, yr + 2.54, fp="C0805")
    C(sh, ref("C"), "100nF", gv[0] - 25.4, yr + 2.54, fp="C0603")
    sh.power("GND", gv[0] - 15.24, yr + 5.08)
    sh.power("GND", gv[0] - 25.4, yr + 5.08)
    sh.pin_power(u, "GND", "GND")
    return u


def build(sh, ref):
    # ---------------- gate drivers
    dx = 55.88
    driver(sh, ref, "U3", dx, 73.66, [(1, "A"), (2, "B")],
           {"INHA": "PWM_H1", "INLA": "PWM_L1", "INHB": "PWM_H2", "INLB": "PWM_L2",
            "INHC": "GND", "INLC": "BRK_PWM"},
           {"BSTC": None, "GHC": None, "SHC": None, "GLC": "GL_BRK"})
    driver(sh, ref, "U4", dx, 147.32, [(3, "A"), (4, "B")],
           {"INHA": "PWM_H3", "INLA": "PWM_L3", "INHB": "PWM_H4", "INLB": "PWM_L4",
            "INHC": "GND", "INLC": "GND"},
           {"BSTC": None, "GHC": None, "SHC": None, "GLC": None})
    sh.box(15.24, 30.48, 96.52, 190.5, "GATE DRIVERS", BLUE)
    sh.text("DRV8300D TSSOP: fixed 200 ns dead time + cross-conduction lockout.\n"
            "MCU TIM1 DTG is a backup (50-100 ns).  CBST <= 1 uF.\n"
            "U3 channel C: low side only -> optional brake chopper Q9 (DNP).",
            17.78, 186.69, size=1.27)
    # ---------------- half bridges
    half_bridge(sh, ref, 1, 96.52, 33.02, shunt=("RS1", "U5", "MOT1", "ISENSE_A"))
    half_bridge(sh, ref, 2, 193.04, 33.02)
    half_bridge(sh, ref, 3, 96.52, 114.3, shunt=("RS2", "U6", "MOT3", "ISENSE_B"))
    half_bridge(sh, ref, 4, 193.04, 114.3)
    sh.box(101.6, 30.48, 295.91, 190.5, "HALF BRIDGES + IN-LINE CURRENT SENSE", RED)
    right_column(sh, ref)


def bus_shunt(sh, ref, rx, ry):
    """RS3: all low-side sources -> RS3 -> GND.  Kelvin sense -> RC -> MCU OPAMP3 (PB0)."""
    rs = sh.place("Device:R_Shunt", "RS3", "3mR 2W", rx, ry, footprint=FP["SHUNT"],
                  fields={"Reference": (-2.54, -0.95, "right"), "Value": (-2.54, 0.95, "right")})
    p1, p4, p2, p3 = rs.pin("1"), rs.pin("4"), rs.pin("2"), rs.pin("3")
    sh.wire(p1, (p1[0], p1[1] - 5.08), (p1[0] - 7.62, p1[1] - 5.08))
    sh.label("LS_SRC", p1[0] - 7.62, p1[1] - 5.08, 180)
    sh.power("GND", *p4)
    sh.wire(p3, (p3[0] + 5.08, p3[1]))
    sh.power("GND", p3[0] + 5.08, p3[1])
    sh.wire(p2, (p2[0] + 5.08, p2[1]))
    R(sh, ref("R"), "100R", p2[0] + 7.62, p2[1], rot=90)
    xn = p2[0] + 10.16
    sh.wire((xn, p2[1]), (xn + 10.16, p2[1]))
    C(sh, ref("C"), "1nF", xn + 5.08, p2[1] + 2.54)
    sh.power("GND", xn + 5.08, p2[1] + 5.08)
    sh.label("IBUS_SENSE", xn + 10.16, p2[1], 0)


def ntc(sh, ref, x, y):
    sh.power("+3V3A", x, y)
    R(sh, ref("R"), "10k 1%", x, y + 2.54)
    sh.place("Device:Thermistor_NTC", "RT1", "10k B3950", x, y + 8.89, footprint=FP["R0603"],
             fields={"Reference": (-2.54, -0.95, "right"), "Value": (-2.54, 0.95, "right")})
    sh.wire((x, y + 5.08), (x + 15.24, y + 5.08))
    C(sh, ref("C"), "100nF", x + 15.24, y + 7.62)
    sh.power("GND", x + 15.24, y + 10.16)
    sh.power("GND", x, y + 12.7)
    sh.wire((x + 15.24, y + 5.08), (x + 22.86, y + 5.08))
    sh.label("NTC", x + 22.86, y + 5.08, 0)


def motor_conn(sh, x, y):
    j = sh.place("Connector_Generic:Conn_01x04", "J3", "MOTOR", x, y, footprint="",
                 props={"Note": "A+ A- B+ B- (BLDC: U V W -)"},
                 fields={"Reference": (-1.27, -5.08, "left"), "Value": (-1.27, 7.62, "left")})
    for pin, net in zip("1234", ["MOT1", "PH2", "MOT3", "PH4"]):
        sh.pin_label(j, pin, net, stub=2.54)
    sh.text("1: A+ (U)   2: A- (V)\n3: B+ (W)   4: B-", x - 22.86, y + 12.7)


def brake_chopper(sh, ref, x, y):
    """Optional brake chopper (DNP): U3 GLC -> Q9, brake resistor on J9."""
    q = sh.place(FET, "Q9", "CSD19534Q5A", x, y, footprint=FP["TDSON"], dnp=True)
    g = q.pin("G")
    R(sh, ref("R"), "10R", g[0] - 5.08, g[1], rot=90, dnp=True)
    sh.wire((g[0] - 2.54, g[1]), g)
    sh.wire((g[0] - 7.62, g[1]), (g[0] - 12.7, g[1]))
    sh.label("GL_BRK", g[0] - 12.7, g[1], 180)
    s_ = q.pin("S")
    sh.wire(s_, (s_[0], s_[1] + 2.54), (s_[0] + 5.08, s_[1] + 2.54))
    sh.label("LS_SRC", s_[0] + 5.08, s_[1] + 2.54, 0)
    d = q.pin("D")
    j = sh.place("Connector_Generic:Conn_01x02", "J9", "BRAKE_RES", x + 17.78, y - 12.7, footprint="",
                 dnp=True, fields={"Reference": (-1.27, -2.54, "left"), "Value": (-1.27, 5.08, "left")})
    p1, p2 = j.pin("1"), j.pin("2")
    sh.wire(d, (d[0], p2[1]), p2)
    sh.wire(p1, (p1[0] - 5.08, p1[1]))
    sh.power("VBUS", p1[0] - 5.08, p1[1])


def right_column(sh, ref):
    bus_shunt(sh, ref, 317.5, 60.96)
    sh.text("Kelvin: route RS3 sense pair separately;\nsense return lands on RS3 GND pad.\n"
            "OPAMP3 PGA -> COMP1 -> TIM1_BKIN\n(shoot-through / leg short / bus OC).", 304.8, 78.74)
    sh.box(299.72, 40.64, 360.68, 85.09, "BUS SHUNT RS3", BROWN)
    ntc(sh, ref, 320.04, 100.33)
    sh.text("Place RT1 on FET copper.", 304.8, 120.65)
    sh.box(299.72, 90.17, 360.68, 124.46, "FET TEMP", GREEN)
    motor_conn(sh, 393.7, 55.88)
    sh.box(365.76, 40.64, 411.48, 76.2, "MOTOR", RED)
    brake_chopper(sh, ref, 383.54, 104.14)
    sh.text("DNP: fit only if regen\nenergy needs dumping.", 368.3, 120.65)
    sh.box(365.76, 81.28, 411.48, 124.46, "BRAKE CHOPPER (DNP)", PURP)
