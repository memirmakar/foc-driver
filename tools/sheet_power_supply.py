"""Power input, reverse polarity, TVS, bulk, 48V->12V (LM5163), GVDD hardware enable,
12V->5V (LMR51430), 5V->3V3 LDO, 3V3A filter."""
from common import R, C, FP

RED = (170, 20, 20)
ORANGE = (200, 100, 0)
MAG = (160, 0, 100)
SAFE = (200, 0, 0)

LFT = {"Reference": (-1.9, -0.95, "right"), "Value": (-1.9, 0.95, "right")}
ABOVE = {"Reference": (0, -4.06, ""), "Value": (0, -2.29, "")}


def flag(sh, x, y):
    """PWR_FLAG hanging below a rail point (x, y)."""
    sh.wire((x, y), (x, y + 2.54))
    sh.place("power:PWR_FLAG", "#FLG%s%02d" % (sh.tag, len(sh.insts)), "PWR_FLAG", x, y + 2.54,
             rot=180, in_bom=False, fields={"Reference": (0, 1.9, ""), "Value": (0, 4.7, "")})


def flag_up(sh, x, y):
    """PWR_FLAG standing on a rail point (x, y)."""
    sh.place("power:PWR_FLAG", "#FLG%s%02d" % (sh.tag, len(sh.insts)), "PWR_FLAG", x, y,
             in_bom=False, fields={"Reference": (0, 1.9, ""), "Value": (0, -3.81, "")})


def input_stage(sh, ref):
    for jref, y in (("J1", 50.8), ("J2", 71.12)):
        j = sh.place("Connector_Generic:Conn_01x04", jref, "PWR+CAN " + ("IN" if jref == "J1" else "OUT"),
                     25.4, y, mirror="y", footprint="",
                     fields={"Reference": (0, -7.62, ""), "Value": (0, -5.84, "")})
        for pin, net in zip("123", ["VIN_RAW", "CANH", "CANL"]):
            sh.pin_label(j, pin, net, stub=2.54)
        x4, y4 = j.pin("4")
        sh.wire((x4, y4), (x4 + 2.54, y4))
        sh.power("GND", x4 + 2.54, y4)
        if jref == "J1":
            sh.wire((x4 + 2.54, y4), (x4 + 12.7, y4))
            flag(sh, x4 + 12.7, y4)
    sh.text("Daisy chain: J1/J2 in parallel.\nCurrent rating = whole chain.\nPinout proposal (connector TBD).", 17.78, 88.9)
    # reverse polarity P-FET Q10 (D = input side, S = board side)
    X, Y = 68.58, 45.72
    q = sh.place("Transistor_FET:Q_PMOS_GSD", "Q10", "P-FET >=100V (TBD)", X, Y, rot=90, footprint=FP["DPAK"],
                 fields={"Reference": (0, -8.89, ""), "Value": (0, -7.11, "")})
    d, s, g = q.pin("D"), q.pin("S"), q.pin("G")
    sh.wire(d, (d[0] - 5.08, d[1]))
    sh.label("VIN_RAW", d[0] - 5.08, d[1], 180)
    yr = s[1]
    sh.wire(s, (127.0, yr))
    sh.wire(g, (g[0], g[1] + 2.54))
    yz = g[1] + 2.54
    sh.place("Device:D_Zener_Small", "D11", "15V", X + 2.54, yz, mirror="y", footprint=FP["SOD323"],
             fields={"Reference": (5.72, -0.95, "left"), "Value": (5.72, 0.95, "left")})
    sh.wire((X + 5.08, yz), (X + 5.08, yr))
    R(sh, ref("R"), "47k", X, yz + 2.54, fields=LFT)
    sh.power("GND", X, yz + 5.08)
    # TVS + bulk
    sh.place("Device:D_Zener_Small", "D1", "SMCJ54A", 81.28, yr + 2.54, rot=270, footprint=FP["SMC"],
             props={"Description": "TVS 54V unidirectional"})
    sh.power("GND", 81.28, yr + 5.08)
    for i, x in enumerate((96.52, 114.3)):
        sh.place("Device:C_Polarized_Small", ref("C"), "100uF 100V", x, yr + 2.54,
                 footprint="Capacitor_SMD:CP_Elec_10x10.5")
        sh.power("GND", x, yr + 5.08)
    sh.power("VBUS", 127.0, yr)
    flag_up(sh, 106.68, yr)
    sh.text("C_BULK value TBD (ripple current calc).", 88.9, 55.88)
    # VBUS sense divider
    x, y = 96.52, 66.04
    sh.power("VBUS", x, y)
    R(sh, ref("R"), "100k 1%", x, y + 2.54, fp="R0805")
    R(sh, ref("R"), "5.1k 1%", x, y + 7.62)
    sh.power("GND", x, y + 10.16)
    sh.wire((x, y + 5.08), (x + 20.32, y + 5.08))
    C(sh, ref("C"), "10nF", x + 12.7, y + 7.62)
    sh.power("GND", x + 12.7, y + 10.16)
    sh.label("VBUS_SENSE", x + 20.32, y + 5.08, 0)
    sh.box(15.24, 30.48, 135.89, 96.52, "POWER INPUT / REVERSE POLARITY / TVS / BULK", RED)


def buck12(sh, ref):
    X, Y = 195.58, 58.42
    u = sh.place("foc-driver:LM5163DDA", "U7", "LM5163DDAR", X, Y, footprint="Package_SO:TI_SO-PowerPAD-8_ThermalVias",
                 fields={"Reference": (-10.16, -8.89, "left"), "Value": (10.16, -8.89, "right")})
    vin, en, ron = u.pin("VIN"), u.pin("EN/UVLO"), u.pin("RON")
    bst, sw, fb = u.pin("BST"), u.pin("SW"), u.pin("FB")
    sh.wire(vin, (X - 53.34, vin[1]))
    sh.power("VBUS", X - 53.34, vin[1])
    for x in (X - 30.48, X - 45.72):
        C(sh, ref("C"), "2.2uF 100V", x, vin[1] + 2.54, fp="C1210")
        sh.power("GND", x, vin[1] + 5.08)
    sh.wire(en, (X - 15.24, en[1]), (X - 15.24, vin[1]))
    sh.wire(ron, (X - 20.32, ron[1]))
    R(sh, ref("R"), "100k", X - 20.32, ron[1] + 2.54, fields=LFT)
    sh.power("GND", X - 20.32, ron[1] + 5.08)
    g, ep, pg = u.pin("GND"), u.pin("EP"), u.pin("PGOOD")
    sh.wire(g, (g[0], g[1] + 2.54), (ep[0], ep[1] + 2.54), ep)
    sh.power("GND", g[0], g[1] + 2.54)
    sh.nc(*pg)
    # bootstrap
    sh.wire(bst, (X + 15.24, bst[1]), (X + 15.24, Y - 7.62))
    C(sh, ref("C"), "2.2nF 50V", X + 17.78, Y - 7.62, rot=90)
    sh.wire((X + 20.32, Y - 7.62), (X + 20.32, Y))
    sh.wire(sw, (X + 25.4, sw[1]))
    sh.place("Device:L_Small", "L1", "120uH 1.65A", X + 27.94, Y, rot=90,
             footprint="Inductor_SMD:L_Coilcraft_MSS1260-XXX", fields=ABOVE)
    sh.wire((X + 30.48, Y), (X + 66.04, Y))
    # type-3 ripple injection RA/CA/CB (datasheet Fig. 7-1)
    yr = Y + 7.62
    sh.wire((X + 22.86, Y), (X + 22.86, yr), (X + 25.4, yr))
    R(sh, ref("R"), "226k", X + 27.94, yr, rot=90, fields=ABOVE)
    sh.wire((X + 30.48, yr), (X + 35.56, yr))
    C(sh, ref("C"), "3.3nF", X + 38.1, yr, rot=90, fields=ABOVE)
    sh.wire((X + 40.64, yr), (X + 40.64, Y))
    yf = Y + 15.24
    sh.wire((X + 33.02, yr), (X + 33.02, yr + 2.54))
    C(sh, ref("C"), "56pF", X + 33.02, yr + 5.08)
    sh.wire(fb, (X + 17.78, fb[1]), (X + 17.78, yf), (X + 48.26, yf))
    sh.wire((X + 48.26, Y), (X + 48.26, Y + 7.62))
    R(sh, ref("R"), "453k 1%", X + 48.26, Y + 10.16)
    sh.wire((X + 48.26, Y + 12.7), (X + 48.26, yf))
    R(sh, ref("R"), "49.9k 1%", X + 48.26, yf + 2.54)
    sh.power("GND", X + 48.26, yf + 5.08)
    C(sh, ref("C"), "22uF 25V", X + 58.42, Y + 2.54, fp="C1210")
    sh.power("GND", X + 58.42, Y + 5.08)
    sh.power("+12V", X + 66.04, Y)
    flag(sh, X + 66.04, Y)
    sh.text("TI LM5163 Fig. 7-1: 48 V -> 12 V / 0.5 A, 300 kHz COT.\n"
            "VIN/EN abs max 100 V (TVS clamp ~87 V).", X - 53.34, Y + 26.67)
    sh.box(139.7, 30.48, 275.59, 96.52, "48V -> 12V BUCK (U7 LM5163)", ORANGE)


def gvdd_switch(sh, ref):
    X, Y = 345.44, 50.8
    q = sh.place("Transistor_FET:Q_PMOS_GSD", "Q12", "P-FET 30V (TBD)", X, Y, rot=90, mirror="y",
                 footprint=FP["SOT23"], fields={"Reference": (0, -9.4, ""), "Value": (0, -7.62, "")})
    s, d, g = q.pin("S"), q.pin("D"), q.pin("G")
    y0 = s[1]
    sh.wire(s, (X - 20.32, y0))
    sh.power("+12V", X - 20.32, y0)
    sh.wire(d, (X + 33.02, y0))
    sh.power("GVDD", X + 33.02, y0)
    flag(sh, X + 33.02, y0)
    R(sh, ref("R"), "1k DNP", X + 17.78, y0 + 2.54, dnp=True)
    sh.power("GND", X + 17.78, y0 + 5.08)
    # gate: pull-up to source, pulled down through Q13
    yn = g[1] + 2.54
    sh.wire(g, (X, yn))
    sh.wire((X - 7.62, y0), (X - 7.62, y0 + 2.54))
    R(sh, ref("R"), "10k", X - 7.62, y0 + 5.08, fields=LFT)
    sh.wire((X - 7.62, y0 + 7.62), (X - 7.62, yn), (X + 2.54, yn))
    R(sh, ref("R"), "1k", X + 5.08, yn, rot=90, fields={"Reference": (0, 2.29, ""), "Value": (0, 4.06, "")})
    sh.wire((X + 7.62, yn), (X + 12.7, yn))
    q13 = sh.place("Transistor_FET:2N7002", "Q13", "2N7002", X + 10.16, yn + 10.16, footprint=FP["SOT23"])
    sh.wire((X + 12.7, yn), q13.pin("D"))
    sh.power("GND", *q13.pin("S"))
    gg = q13.pin("G")
    # U11 AND gate: ENABLE (external, also TIM1_BKIN2) AND MCU_EN
    Ux, Uy = X - 27.94, gg[1]
    u = sh.place("74xGxx:74LVC1G08", "U11", "74LVC1G08", Ux, Uy, footprint=FP["SOT235"],
                 fields={"Reference": (2.54, -11.43, "left"), "Value": (2.54, 11.43, "left")})
    o = u.pin("4")
    sh.wire(o, gg)
    sh.label("GVDD_EN", o[0] + 1.27, o[1], 0)
    xp = gg[0] - 5.08
    sh.wire((xp, gg[1]), (xp, gg[1] + 2.54))
    R(sh, ref("R"), "100k", xp, gg[1] + 5.08, fields=LFT)
    sh.power("GND", xp, gg[1] + 7.62)
    vcc = u.pin("VCC")
    sh.wire(vcc, (vcc[0], vcc[1] - 5.08), (vcc[0] - 12.7, vcc[1] - 5.08))
    sh.power("+3V3", vcc[0], vcc[1] - 5.08)
    C(sh, ref("C"), "100nF", vcc[0] - 12.7, vcc[1] - 2.54, fields=LFT)
    sh.power("GND", vcc[0] - 12.7, vcc[1])
    sh.pin_power(u, "GND", "GND")
    i1, i2 = u.pin("1"), u.pin("2")
    sh.wire(i1, (i1[0] - 10.16, i1[1]))
    sh.label("ENABLE", i1[0] - 10.16, i1[1], 180)
    sh.wire(i2, (i2[0] - 10.16, i2[1]))
    sh.label("MCU_EN", i2[0] - 10.16, i2[1], 180)
    sh.wire((i2[0] - 5.08, i2[1]), (i2[0] - 5.08, i2[1] + 2.54))
    R(sh, ref("R"), "100k", i2[0] - 5.08, i2[1] + 5.08, fields=LFT)
    sh.power("GND", i2[0] - 5.08, i2[1] + 7.62)
    sh.text("ENABLE low OR MCU_EN low -> GVDD off -> DRV8300 UVLO -> all FETs off\n"
            "(independent of MCU; TIM1_BKIN2 is the fast path).\n"
            "GVDD decay time set by driver caps; R DNP = optional bleeder.", 284.48, 93.98)
    sh.box(281.94, 30.48, 410.21, 96.52, "GVDD SWITCH = HARDWARE ENABLE", SAFE)


def buck5(sh, ref):
    Lx, Ly = 60.96, 127.0
    u = sh.place("Regulator_Switching:LMR51430", "U8", "LMR51430XDDCR", Lx, Ly, footprint="Package_TO_SOT_SMD:SOT-23-6",
                 fields={"Reference": (-7.62, -6.35, "left"), "Value": (-2.54, 10.16, "right")})
    vin, en, cb, sw, fb = u.pin("VIN"), u.pin("EN"), u.pin("CB"), u.pin("SW"), u.pin("FB")
    sh.wire(vin, (Lx - 43.18, vin[1]))
    sh.power("+12V", Lx - 43.18, vin[1])
    C(sh, ref("C"), "10uF 25V", Lx - 25.4, vin[1] + 2.54, fp="C0805")
    C(sh, ref("C"), "100nF", Lx - 38.1, vin[1] + 2.54)
    sh.power("GND", Lx - 25.4, vin[1] + 5.08)
    sh.power("GND", Lx - 38.1, vin[1] + 5.08)
    sh.wire(en, (Lx - 11.43, en[1]), (Lx - 11.43, vin[1]))
    sh.pin_power(u, "GND", "GND")
    sh.wire(cb, (Lx + 12.7, cb[1]), (Lx + 12.7, Ly - 7.62))
    C(sh, ref("C"), "100nF", Lx + 15.24, Ly - 7.62, rot=90)
    sh.wire((Lx + 17.78, Ly - 7.62), (Lx + 17.78, Ly))
    sh.wire(sw, (Lx + 22.86, sw[1]))
    sh.place("Device:L_Small", "L2", "6.8uH", Lx + 25.4, Ly, rot=90, footprint="Inductor_SMD:L_Bourns_SRN6045TA",
             fields=ABOVE)
    sh.wire((Lx + 27.94, Ly), (Lx + 68.58, Ly))
    yf = Ly + 10.16
    sh.wire(fb, (Lx + 15.24, fb[1]), (Lx + 15.24, yf), (Lx + 33.02, yf))
    sh.wire((Lx + 33.02, Ly), (Lx + 33.02, Ly + 2.54))
    R(sh, ref("R"), "100k 1%", Lx + 33.02, Ly + 5.08, fields=LFT)
    sh.wire((Lx + 33.02, Ly + 7.62), (Lx + 33.02, yf))
    R(sh, ref("R"), "13.7k 1%", Lx + 33.02, yf + 2.54, fields=LFT)
    sh.power("GND", Lx + 33.02, yf + 5.08)
    for x in (Lx + 40.64, Lx + 53.34):
        C(sh, ref("C"), "22uF 25V", x, Ly + 2.54, fp="C1206")
        sh.power("GND", x, Ly + 5.08)
    sh.power("+5V", Lx + 68.58, Ly)
    flag(sh, Lx + 68.58, Ly)
    sh.text("500 kHz variant, datasheet Table 9-1 (5 V: 6.8 uH, 2x22 uF, 100k/13.7k).\n"
            "5 V feeds CAN transceiver VCC and J8 encoder supply.", 17.78, 152.4)
    sh.box(15.24, 104.14, 135.89, 157.48, "12V -> 5V BUCK (U8 LMR51430)", MAG)


def ldo33(sh, ref):
    Ax, Ay = 175.26, 127.0
    u = sh.place("Regulator_Linear:AP2112K-3.3", "U12", "AP2112K-3.3", Ax, Ay, footprint=FP["SOT235"],
                 fields={"Reference": (-5.08, -6.35, "left"), "Value": (2.54, 10.16, "left")})
    vin, en, vo = u.pin("VIN"), u.pin("EN"), u.pin("VOUT")
    sh.wire(vin, (Ax - 25.4, vin[1]))
    sh.power("+5V", Ax - 25.4, vin[1])
    C(sh, ref("C"), "1uF", Ax - 17.78, vin[1] + 2.54, fields=LFT)
    sh.power("GND", Ax - 17.78, vin[1] + 5.08)
    sh.wire(en, (Ax - 11.43, en[1]), (Ax - 11.43, vin[1]))
    sh.pin_nc(u, "NC")
    sh.pin_power(u, "GND", "GND")
    sh.wire(vo, (Ax + 25.4, vo[1]))
    C(sh, ref("C"), "1uF", Ax + 12.7, vo[1] + 2.54)
    sh.power("GND", Ax + 12.7, vo[1] + 5.08)
    sh.power("+3V3", Ax + 20.32, vo[1])
    sh.place("Device:FerriteBead_Small", "FB1", "120R", Ax + 27.94, vo[1], rot=90, footprint=FP["FB0603"],
             fields=ABOVE)
    sh.wire((Ax + 30.48, vo[1]), (Ax + 58.42, vo[1]))
    C(sh, ref("C"), "1uF", Ax + 35.56, vo[1] + 2.54)
    C(sh, ref("C"), "100nF", Ax + 45.72, vo[1] + 2.54)
    sh.power("GND", Ax + 35.56, vo[1] + 5.08)
    sh.power("GND", Ax + 45.72, vo[1] + 5.08)
    sh.power("+3V3A", Ax + 58.42, vo[1])
    sh.text("+3V3: MCU, CAN VIO, logic (~80 mA).\n+3V3A: VDDA/VREF+, INA240, AS5047D, NTC.", 142.24, 152.4)
    sh.box(139.7, 104.14, 275.59, 157.48, "5V -> 3V3 LDO (U12) + 3V3A FILTER", MAG)


def build(sh, ref):
    input_stage(sh, ref)
    buck12(sh, ref)
    gvdd_switch(sh, ref)
    buck5(sh, ref)
    ldo33(sh, ref)
