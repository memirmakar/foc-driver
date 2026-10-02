"""Root sheet: STM32G431RBT6 + clock/reset/decoupling, SWD/UART, CAN-FD, AS5047D,
external SPI encoder, ABI/Hall input, ENABLE/GPIO, AUX output, status LEDs."""
from common import R, C, FP

BLUE = (0, 70, 160)
CANC = (110, 40, 140)
GREEN = (0, 120, 60)
OLIVE = (90, 110, 0)
BROWN = (130, 80, 20)
GREY = (80, 80, 80)
SAFE = (200, 0, 0)
RED = (170, 20, 20)
TEAL = (0, 120, 120)

LFT = {"Reference": (-1.9, -0.95, "right"), "Value": (-1.9, 0.95, "right")}
ABOVE = {"Reference": (0, -4.06, ""), "Value": (0, -2.29, "")}
BELOW = {"Reference": (0, 2.29, ""), "Value": (0, 4.06, "")}

LEFT_NETS = {
    "PG10": "NRST", "PF0": "OSC_IN", "PF1": "OSC_OUT",
    "PA0": "VBUS_SENSE", "PC0": "NTC", "PC1": "ADC_IA", "PA7": "ADC_IB", "PB0": "IBUS_SENSE", "PB1": "IBUS_AMP",
    "PA2": "UART_TX", "PA3": "UART_RX", "PA13": "SWDIO", "PA14": "SWCLK", "PB3": "SWO",
    "PB10": "ADDR0", "PB11": "ADDR1", "PB12": "ADDR2", "PB2": "ADDR3", "PC13": "GPIN1",
}
RIGHT_NETS = {
    "PA8": "PWM_H1", "PB13": "PWM_L1", "PA9": "PWM_H2", "PB14": "PWM_L2",
    "PA10": "PWM_H3", "PB15": "PWM_L3", "PA11": "PWM_H4", "PC5": "PWM_L4",
    "PC3": "ENABLE", "PC4": "MCU_EN",
    "PA5": "ENC_SCK", "PA6": "ENC_MISO", "PB5": "ENC_MOSI", "PA4": "ENC_CS",
    "PC10": "EXT_SCK", "PC11": "EXT_MISO", "PC12": "EXT_MOSI", "PA15": "EXT_CS",
    "PB8": "CAN_RX", "PB9": "CAN_TX", "PC6": "ABI_1", "PC7": "ABI_2", "PC8": "ABI_3",
    "PB6": "BRK_PWM", "PB7": "GPIN2", "PB4": "LED_ERR", "PD2": "LED_STAT", "PC9": "AUX_EN",
}
NC_PINS = ["PA1", "PC2", "PC14", "PC15", "PA12"]


def mcu(sh, ref, X, Y):
    u = sh.place("foc-driver:STM32G431RBTx", "U1", "STM32G431RBT6", X, Y,
                 footprint="Package_QFP:LQFP-64_10x10mm_P0.5mm",
                 fields={"Reference": (-40.64, 40.64, "left"), "Value": (-40.64, 42.42, "left")})
    for p, n in LEFT_NETS.items():
        sh.label(n, *u.pin(p), 180)
    for p, n in RIGHT_NETS.items():
        sh.label(n, *u.pin(p), 0)
    for p in NC_PINS:
        sh.pin_nc(u, p)
    # VDD / VBAT -> +3V3 rail with decoupling
    tops = [u.pin(n) for n in ("1", "16", "32", "48", "64")]
    yr = tops[0][1] - 7.62
    for p in tops:
        sh.wire(p, (p[0], yr))
    xs = [X - 22.86, X - 33.02, X - 43.18, X - 53.34, X - 63.5]
    sh.wire(tops[-1] and (tops[-1][0], yr), (X - 68.58, yr))
    sh.power("+3V3", X - 68.58, yr)
    for i, x in enumerate(xs):
        C(sh, ref("C"), "4.7uF" if i == 0 else "100nF", x, yr + 2.54, fp="C0805" if i == 0 else "C0603")
        sh.power("GND", x, yr + 5.08)
    # VDDA + VREF+ -> +3V3A
    va = [u.pin("28"), u.pin("29")]
    for p in va:
        sh.wire(p, (p[0], yr))
    sh.wire((va[0][0], yr), (X + 48.26, yr))
    sh.power("+3V3A", X + 48.26, yr)
    for x, v in ((X + 20.32, "1uF"), (X + 30.48, "100nF"), (X + 40.64, "100nF")):
        C(sh, ref("C"), v, x, yr + 2.54)
        sh.power("GND", x, yr + 5.08)
    sh.text("VDD x4 + VBAT", X - 63.5, yr - 3.81)
    sh.text("VREF+ = VDDA", X + 20.32, yr - 3.81)
    # VSS / VSSA
    bots = [u.pin(n) for n in ("15", "31", "47", "63", "27")]
    yb = bots[0][1] + 2.54
    for p in bots:
        sh.wire(p, (p[0], yb))
    sh.wire((bots[0][0], yb), (bots[-1][0], yb))
    sh.power("GND", X, yb)
    return u


def clock_reset(sh, ref, Cx, Cy, Nx, Ny):
    y1 = sh.place("Device:Crystal_GND24_Small", "Y1", "24MHz", Cx, Cy,
                  footprint="Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
                  props={"MPN": "ECS-240-12-37B-CKY-TR"},
                  fields={"Reference": (0, -5.59, ""), "Value": (0, -3.81, "")})
    sh.wire((Cx - 2.54, Cy), (Cx - 12.7, Cy))
    sh.wire((Cx + 2.54, Cy), (Cx + 12.7, Cy))
    sh.label("OSC_IN", Cx - 12.7, Cy, 180)
    sh.label("OSC_OUT", Cx + 12.7, Cy, 0)
    C(sh, ref("C"), "15pF", Cx - 7.62, Cy + 2.54, fields=LFT)
    C(sh, ref("C"), "15pF", Cx + 7.62, Cy + 2.54)
    sh.power("GND", Cx - 7.62, Cy + 5.08)
    sh.power("GND", Cx + 7.62, Cy + 5.08)
    sh.power("GND", Cx, Cy + 2.54)
    # NRST: 100 nF + reset button (BOOT0 handled by option byte nSWBOOT0 = 0)
    sh.label("NRST", Nx, Ny, 180)
    sh.wire((Nx, Ny), (Nx + 15.24, Ny))
    C(sh, ref("C"), "100nF", Nx + 5.08, Ny + 2.54)
    sh.power("GND", Nx + 5.08, Ny + 5.08)
    sh.place("Switch:SW_Push", "SW1", "RESET", Nx + 15.24, Ny + 5.08, rot=90,
             footprint="Button_Switch_SMD:SW_SPST_B3U-1000P",
             fields={"Reference": (3.81, -0.95, "left"), "Value": (3.81, 0.95, "left")})
    sh.power("GND", Nx + 15.24, Ny + 10.16)


def debug(sh, ref, x, y):
    j = sh.place("Connector:Conn_ARM_JTAG_SWD_10", "J7", "SWD", x, y,
                 footprint="Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD",
                 fields={"Reference": (-10.16, -17.78, "left"), "Value": (-10.16, 17.78, "left")})
    for p, n in (("2", "SWDIO"), ("4", "SWCLK"), ("6", "SWO"), ("10", "NRST")):
        sh.pin_label(j, p, n, stub=2.54)
    sh.pin_nc(j, "7")
    sh.pin_nc(j, "8")
    sh.pin_power(j, "1", "+3V3")
    g, gd = j.pin("3"), j.pin("9")
    sh.wire(gd, (gd[0], gd[1] + 2.54), (g[0], g[1] + 2.54), g)
    sh.power("GND", g[0], g[1] + 2.54)
    u = sh.place("Connector_Generic:Conn_01x03", "J10", "UART", x + 45.72, y,
                 footprint="Connector_JST:JST_GH_SM03B-GHS-TB_1x03-1MP_P1.25mm_Horizontal",
                 fields={"Reference": (-1.27, -5.08, "left"), "Value": (-1.27, 5.08, "left")})
    sh.pin_label(u, "1", "UART_TX", stub=2.54)
    sh.pin_label(u, "2", "UART_RX", stub=2.54)
    p3 = u.pin("3")
    sh.wire(p3, (p3[0] - 2.54, p3[1]))
    sh.power("GND", p3[0] - 2.54, p3[1])
    sh.text("UART_TX = MCU output (USART2)", x + 22.86, y + 10.16)


def can_addr(sh, ref, x, y):
    s = sh.place("Switch:SW_DIP_x04", "SW2", "CAN_ADDR", x, y,
                 footprint="Button_Switch_SMD:SW_DIP_SPSTx04_Slide_6.7x11.72mm_W8.61mm_P2.54mm_LowProfile",
                 fields={"Reference": (0, -11.43, ""), "Value": (0, -9.65, "")})
    for p, n in zip("1234", ["ADDR0", "ADDR1", "ADDR2", "ADDR3"]):
        sh.pin_label(s, p, n, stub=2.54)
    pts = []
    for p in "8765":
        px, py = s.pin(p)
        sh.wire((px, py), (px + 2.54, py))
        pts.append((px + 2.54, py))
    sh.wire(pts[0], pts[-1])
    sh.power("GND", *pts[-1])
    sh.text("MCU internal pull-ups; switch ON = 0.", x - 17.78, y + 10.16)


def analog_front(sh, ref, x, y):
    for i, (src, dst) in enumerate((("ISENSE_A", "ADC_IA"), ("ISENSE_B", "ADC_IB"))):
        yy = y + i * 12.7
        sh.label(src, x, yy, 180)
        sh.wire((x, yy), (x + 2.54, yy))
        R(sh, ref("R"), "100R", x + 5.08, yy, rot=90, fields=ABOVE)
        sh.wire((x + 7.62, yy), (x + 17.78, yy))
        C(sh, ref("C"), "1nF", x + 12.7, yy + 2.54)
        sh.power("GND", x + 12.7, yy + 5.08)
        sh.label(dst, x + 17.78, yy, 0)
    yy = y + 30.48
    sh.label("IBUS_AMP", x, yy, 180)
    sh.wire((x, yy), (x + 7.62, yy))
    sh.place("Connector:TestPoint", "TP1", "IBUS_AMP", x + 7.62, yy, footprint="TestPoint:TestPoint_Pad_D1.0mm",
             fields={"Reference": (1.9, -3.2, "left"), "Value": (1.9, -1.4, "left")})
    sh.text("PB1 = OPAMP3_VOUT (internal PGA) = COMP1_INP", x - 12.7, yy + 5.08)


def leds(sh, ref, x, y):
    for i, (net, col) in enumerate((("LED_STAT", "GRN"), ("LED_ERR", "RED"))):
        yy = y + i * 10.16
        sh.label(net, x, yy, 180)
        sh.wire((x, yy), (x + 2.54, yy))
        R(sh, ref("R"), "1k", x + 5.08, yy, rot=90, fields=ABOVE)
        sh.wire((x + 7.62, yy), (x + 10.16, yy))
        sh.place("Device:LED_Small", "LED%d" % (i + 1), col, x + 12.7, yy, mirror="y", footprint=FP["LED0603"],
                 fields=ABOVE)
        sh.wire((x + 15.24, yy), (x + 17.78, yy))
        sh.power("GND", x + 17.78, yy)


def pwm_pulldowns(sh, ref, x, y):
    for k, nets in enumerate((["PWM_H1", "PWM_L1", "PWM_H2", "PWM_L2"], ["PWM_H3", "PWM_L3", "PWM_H4", "PWM_L4"])):
        rx = x
        rn = sh.place("Device:R_Pack04", "RN%d" % (k + 1), "4x100k", rx, y + k * 20.32, rot=270,
                      footprint="Resistor_SMD:R_Array_Convex_4x0603",
                      fields={"Reference": (0, -8.89, ""), "Value": (0, -7.11, "")})
        for p, n in zip("1234", nets):
            sh.pin_label(rn, p, n, stub=2.54)
        pts = []
        for p in "8765":
            px, py = rn.pin(p)
            sh.wire((px, py), (px + 2.54, py))
            pts.append((px + 2.54, py))
        sh.wire(pts[0], pts[-1])
        sh.power("GND", *pts[-1])
    sh.text("PWM pull-downs: bridge off while\nMCU is in reset / unprogrammed.", x - 15.24, y + 35.56)


def can(sh, ref, x, y):
    u = sh.place("Interface_CAN_LIN:TJA1051T-3", "U9", "TJA1051T/3", x, y,
                 footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                 fields={"Reference": (6.35, 11.43, "left"), "Value": (6.35, 13.21, "left")})
    sh.pin_label(u, "TXD", "CAN_TX")
    sh.pin_label(u, "RXD", "CAN_RX")
    sh.pin_label(u, "CANH", "CANH", stub=2.54)
    sh.pin_label(u, "CANL", "CANL", stub=2.54)
    s = u.pin("S")
    sh.wire(s, (s[0] - 2.54, s[1]))
    sh.power("GND", s[0] - 2.54, s[1])
    vio = u.pin("VIO")
    sh.wire(vio, (vio[0] - 12.7, vio[1]))
    sh.power("+3V3", vio[0] - 12.7, vio[1])
    C(sh, ref("C"), "100nF", vio[0] - 10.16, vio[1] + 2.54, fields=LFT)
    sh.power("GND", vio[0] - 10.16, vio[1] + 5.08)
    vcc = u.pin("VCC")
    sh.wire(vcc, (vcc[0], vcc[1] - 5.08), (vcc[0] + 15.24, vcc[1] - 5.08))
    sh.power("+5V", vcc[0], vcc[1] - 5.08)
    C(sh, ref("C"), "100nF", vcc[0] + 15.24, vcc[1] - 2.54)
    sh.power("GND", vcc[0] + 15.24, vcc[1])
    sh.pin_power(u, "GND", "GND")
    # ESD
    ex, ey = x + 35.56, y + 2.54
    e = sh.place("Power_Protection:NUP2105L", "D12", "PESD2CANFD", ex, ey, footprint=FP["SOT23"],
                 fields={"Reference": (5.08, -1.27, "left"), "Value": (5.08, 0.51, "left")})
    sh.pin_label(e, "1", "CANH", stub=2.54)
    sh.pin_label(e, "2", "CANL", stub=2.54)
    sh.power("GND", *e.pin("3"))
    # split termination, jumper-selectable (fit jumper on last node only)
    tx, ty = x - 15.24, y + 22.86
    sh.label("CANH", tx, ty, 180)
    sh.wire((tx, ty), (tx + 2.54, ty))
    R(sh, ref("R"), "60.4R", tx + 5.08, ty, rot=90, fp="R0805", fields=ABOVE)
    sh.wire((tx + 7.62, ty), (tx + 12.7, ty))
    R(sh, ref("R"), "60.4R", tx + 15.24, ty, rot=90, fp="R0805", fields=ABOVE)
    sh.wire((tx + 17.78, ty), (tx + 20.32, ty))
    sh.place("Jumper:Jumper_2_Open", "JP1", "TERM", tx + 25.4, ty,
             footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", fields=ABOVE)
    sh.wire((tx + 30.48, ty), (tx + 33.02, ty))
    sh.label("CANL", tx + 33.02, ty, 0)
    sh.wire((tx + 10.16, ty), (tx + 10.16, ty + 2.54))
    C(sh, ref("C"), "4.7nF", tx + 10.16, ty + 5.08)
    sh.power("GND", tx + 10.16, ty + 7.62)


def encoder(sh, ref, x, y):
    u = sh.place("Sensor_Magnetic:AS5047D", "U2", "AS5047D-ATST", x, y,
                 footprint="Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
                 fields={"Reference": (-10.16, -15.24, "left"), "Value": (2.54, 15.24, "left")})
    for p, n in (("1", "ENC_CS"), ("2", "ENC_SCK"), ("3", "ENC_MISO"), ("4", "ENC_MOSI")):
        sh.pin_label(u, p, n)
    for p in ("6", "7", "8", "9", "10", "14"):
        sh.pin_nc(u, p)
    t = u.pin("5")
    sh.wire(t, (t[0] - 2.54, t[1]))
    sh.power("GND", t[0] - 2.54, t[1])
    v3 = u.pin("12")
    sh.wire(v3, (v3[0] - 15.24, v3[1]))
    sh.power("+3V3A", v3[0] - 15.24, v3[1])
    vdd = u.pin("11")
    sh.wire(vdd, (vdd[0], vdd[1] - 5.08), (vdd[0] + 27.94, vdd[1] - 5.08))
    sh.power("+3V3A", vdd[0], vdd[1] - 5.08)
    C(sh, ref("C"), "100nF", vdd[0] + 17.78, vdd[1] - 2.54)
    C(sh, ref("C"), "1uF", vdd[0] + 27.94, vdd[1] - 2.54)
    sh.power("GND", vdd[0] + 17.78, vdd[1])
    sh.power("GND", vdd[0] + 27.94, vdd[1])
    sh.pin_power(u, "13", "GND")
    sh.text("3.3 V mode: VDD and VDD3V3 both on +3V3A.\nU2 on BOTTOM side, board centre, on magnet axis.",
            x - 22.86, y + 22.86)


def ext_spi(sh, ref, x, y):
    j = sh.place("Connector_Generic:Conn_01x06", "J4", "EXT_SPI_ENC", x, y,
                 footprint="Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal",
                 fields={"Reference": (-1.27, -7.62, "left"), "Value": (-1.27, 10.16, "left")})
    p1 = j.pin("1")
    sh.wire(p1, (p1[0] - 2.54, p1[1]))
    sh.power("+3V3", p1[0] - 2.54, p1[1])
    p6 = j.pin("6")
    sh.wire(p6, (p6[0] - 2.54, p6[1]))
    sh.power("GND", p6[0] - 2.54, p6[1])
    p2 = j.pin("2")
    rx = p2[0] - 15.24
    rn = sh.place("Device:R_Pack04", "RN3", "4x33R", rx, p2[1] + 5.08, rot=270,
                  footprint="Resistor_SMD:R_Array_Convex_4x0603",
                  fields={"Reference": (0, -8.89, ""), "Value": (0, -7.11, "")})
    for k, (a, b, n) in enumerate((("1", "8", "EXT_SCK"), ("2", "7", "EXT_MISO"), ("3", "6", "EXT_MOSI"),
                                   ("4", "5", "EXT_CS"))):
        sh.wire(rn.pin(b), j.pin(str(k + 2)))
        sh.pin_label(rn, a, n, stub=2.54)
    sh.text("Series R: cable ringing /\nESD current limit.", x - 71.12, y + 12.7)


def abi_hall(sh, ref, x, y):
    j = sh.place("Connector_Generic:Conn_01x05", "J8", "ABI_HALL", x, y,
                 footprint="Connector_JST:JST_GH_SM05B-GHS-TB_1x05-1MP_P1.25mm_Horizontal",
                 fields={"Reference": (-1.27, -7.62, "left"), "Value": (-1.27, 7.62, "left")})
    p1 = j.pin("1")
    sh.wire(p1, (p1[0] - 2.54, p1[1]))
    sh.power("+5V", p1[0] - 2.54, p1[1])
    p5 = j.pin("5")
    sh.wire(p5, (p5[0] - 2.54, p5[1]))
    sh.power("GND", p5[0] - 2.54, p5[1])
    for k in range(3):
        sh.pin_label(j, str(k + 2), "J8_CH%d" % (k + 1), stub=2.54)
    # series 1k (RN4) and selectable pull-ups (RN5 + JP2)
    rx, ry = x - 30.48, y + 22.86
    rn = sh.place("Device:R_Pack04", "RN4", "4x1k", rx, ry, rot=270, footprint="Resistor_SMD:R_Array_Convex_4x0603",
                  fields={"Reference": (0, -8.89, ""), "Value": (0, -7.11, "")})
    for k, (a, b) in enumerate((("1", "8"), ("2", "7"), ("3", "6"))):
        sh.pin_label(rn, a, "ABI_%d" % (k + 1), stub=2.54)
        sh.pin_label(rn, b, "J8_CH%d" % (k + 1), stub=2.54)
    sh.pin_nc(rn, "4")
    sh.pin_nc(rn, "5")
    px, py = x - 30.48, y + 40.64
    rp = sh.place("Device:R_Pack04", "RN5", "4x4.7k", px, py, rot=270, footprint="Resistor_SMD:R_Array_Convex_4x0603",
                  fields={"Reference": (0, -8.89, ""), "Value": (0, -7.11, "")})
    for k, a in enumerate("123"):
        sh.pin_label(rp, a, "J8_CH%d" % (k + 1), stub=2.54)
    sh.pin_nc(rp, "4")
    sh.pin_nc(rp, "5")
    pts = []
    for b in "876":
        bx, by = rp.pin(b)
        sh.wire((bx, by), (bx + 2.54, by))
        pts.append((bx + 2.54, by))
    sh.wire(pts[0], pts[-1])
    sh.wire(pts[0], (pts[0][0] + 2.54, pts[0][1]))
    sh.place("Jumper:SolderJumper_2_Open", "JP2", "PULLUP", pts[0][0] + 7.62, pts[0][1],
             footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", fields=ABOVE)
    sh.wire((pts[0][0] + 12.7, pts[0][1]), (pts[0][0] + 15.24, pts[0][1]))
    sh.power("+3V3", pts[0][0] + 15.24, pts[0][1])
    sh.text("JP2 closed: pull-ups for\nopen-collector Hall sensors.", px - 17.78, py + 7.62)
    # clamps at MCU side
    for k in range(3):
        dx, dy = x - 81.28, y + k * 15.24
        d = sh.place("Diode:BAT54S", ref("D"), "BAT54S", dx, dy, footprint=FP["SOT23"],
                     fields={"Reference": (0, -6.35, ""), "Value": (0, -4.57, "")})
        a, kk, com = d.pin("1"), d.pin("2"), d.pin("3")
        sh.wire(a, (a[0] - 2.54, a[1]))
        sh.power("GND", a[0] - 2.54, a[1])
        sh.wire(kk, (kk[0] + 2.54, kk[1]))
        sh.power("+3V3", kk[0] + 2.54, kk[1])
        sh.wire(com, (com[0], com[1] + 2.54), (com[0] + 7.62, com[1] + 2.54))
        sh.label("ABI_%d" % (k + 1), com[0] + 7.62, com[1] + 2.54, 0)


def enable_io(sh, ref, x, y):
    j = sh.place("Connector_Generic:Conn_01x05", "J6", "ENABLE_IO", x, y,
                 footprint="Connector_JST:JST_GH_SM05B-GHS-TB_1x05-1MP_P1.25mm_Horizontal",
                 fields={"Reference": (-1.27, -7.62, "left"), "Value": (-1.27, 7.62, "left")})
    p1 = j.pin("1")
    sh.wire(p1, (p1[0] - 2.54, p1[1]))
    sh.power("+3V3", p1[0] - 2.54, p1[1])
    p5 = j.pin("5")
    sh.wire(p5, (p5[0] - 2.54, p5[1]))
    sh.power("GND", p5[0] - 2.54, p5[1])
    p2 = j.pin("2")
    rx = p2[0] - 15.24
    rn = sh.place("Device:R_Pack04", "RN6", "4x1k", rx, p2[1] + 5.08, rot=270,
                  footprint="Resistor_SMD:R_Array_Convex_4x0603",
                  fields={"Reference": (0, -8.89, ""), "Value": (0, -7.11, "")})
    for k, (a, b, n) in enumerate((("1", "8", "GPIN1"), ("2", "7", "GPIN2"), ("3", "6", "ENABLE"))):
        sh.wire(rn.pin(b), j.pin(str(k + 2)))
        sh.pin_label(rn, a, n, stub=2.54)
    sh.pin_nc(rn, "4")
    sh.pin_nc(rn, "5")
    # ENABLE pull-down: unplugged connector = drive disabled
    ex, ey = x - 40.64, y + 17.78
    sh.label("ENABLE", ex, ey, 180)
    sh.wire((ex, ey), (ex + 5.08, ey))
    R(sh, ref("R"), "100k", ex + 5.08, ey + 2.54)
    sh.power("GND", ex + 5.08, ey + 5.08)
    sh.text("ENABLE -> TIM1_BKIN2 (PC3) + U11 AND\n-> GVDD switch. 3.3 V / 5 V logic input.",
            x - 73.66, y + 35.56)


def aux_out(sh, ref, x, y):
    """AUX high-side output from VBUS (brake / fan / solenoid), 100 % duty capable."""
    q = sh.place("Transistor_FET:Q_PMOS_GSD", "Q11", "P-FET >=100V (TBD)", x, y, mirror="x", footprint=FP["DPAK"],
                 fields={"Reference": (5.08, -0.95, "left"), "Value": (5.08, 0.95, "left")})
    s, d, g = q.pin("S"), q.pin("D"), q.pin("G")
    yt = s[1] - 5.08
    sh.wire(s, (s[0], yt), (s[0] - 22.86, yt))
    sh.power("VBUS", s[0], yt)
    sh.wire((s[0] - 15.24, yt), (s[0] - 15.24, yt + 2.54))
    R(sh, ref("R"), "10k", s[0] - 15.24, yt + 5.08)
    sh.wire((s[0] - 15.24, yt + 7.62), (s[0] - 15.24, g[1]))
    sh.wire((s[0] - 22.86, yt), (s[0] - 22.86, yt + 2.54))
    sh.place("Device:D_Zener_Small", "D13", "15V", s[0] - 22.86, yt + 5.08, rot=270, footprint=FP["SOD323"])
    sh.wire((s[0] - 22.86, yt + 7.62), (s[0] - 22.86, g[1]))
    sh.wire(g, (s[0] - 30.48, g[1]))
    R(sh, ref("R"), "10k", s[0] - 33.02, g[1], rot=90, fields=ABOVE)
    qx = s[0] - 40.64
    q2 = sh.place("Transistor_FET:BSS123", "Q14", "BSS123", qx - 2.54, g[1] + 10.16, footprint=FP["SOT23"],
                  fields={"Reference": (5.08, -0.95, "left"), "Value": (5.08, 0.95, "left")})
    sh.wire((s[0] - 35.56, g[1]), (qx, g[1]), q2.pin("D"))
    sh.power("GND", *q2.pin("S"))
    gg = q2.pin("G")
    sh.wire(gg, (gg[0] - 10.16, gg[1]))
    sh.label("AUX_EN", gg[0] - 10.16, gg[1], 180)
    sh.wire((gg[0] - 5.08, gg[1]), (gg[0] - 5.08, gg[1] + 2.54))
    R(sh, ref("R"), "100k", gg[0] - 5.08, gg[1] + 5.08, fields=LFT)
    sh.power("GND", gg[0] - 5.08, gg[1] + 7.62)
    # output
    yo = d[1] + 5.08
    sh.wire(d, (d[0], yo), (d[0] + 20.32, yo))
    sh.label("AUX_OUT", d[0] + 1.27, yo, 0)
    sh.wire((d[0] + 10.16, yo), (d[0] + 10.16, yo + 2.54))
    sh.place("Device:D_Small", "D10", "SS110", d[0] + 10.16, yo + 5.08, rot=270, footprint=FP["SMA"], fields=LFT)
    sh.power("GND", d[0] + 10.16, yo + 7.62)
    j = sh.place("Connector_Generic:Conn_01x02", "J5", "AUX_OUT", d[0] + 25.4, yo, footprint="",
                 fields={"Reference": (-1.27, -2.54, "left"), "Value": (-1.27, 5.08, "left")})
    p2 = j.pin("2")
    sh.wire(p2, (p2[0] - 2.54, p2[1]))
    sh.power("GND", p2[0] - 2.54, p2[1])


NOTES = """1. Option bytes: nSWBOOT0 = 0 (PB8 = BOOT0 is shared with FDCAN1_RX).
2. TIM1 complementary PWM, CH1-CH4 + CH1N-CH4N, centre aligned 30 kHz (20-50 kHz).
   DTG 50-100 ns is a backup only: DRV8300D inserts a fixed 200 ns dead time.
3. Duty limit 97-98 % (bootstrap refresh). Pre-charge bootstraps (low sides on)
   after every enable and after Hi-Z.
4. Hardware trips: RS3 -> PB0 OPAMP3 (PGA) -> PB1 -> COMP1 -> TIM1_BKIN.
   IA PC1 -> COMP3, IB PA7 -> COMP2 (DAC thresholds). ENABLE PC3 -> TIM1_BKIN2.
5. ADC: IA PC1 = ADC1_IN7 and IB PA7 = ADC2_IN4 (simultaneous), VBUS PA0, NTC PC0.
6. No brake chopper fitted: limit regen via VBUS monitoring (Q9/J9 footprint is DNP).
7. External encoder uses SPI3 (SPI2 SCK only on PB13/PF1, both in use).
8. ABI / Hall on TIM3 CH1-CH3 (encoder mode or Hall XOR interface)."""


def build(sh, ref):
    X, Y = 228.6, 114.3
    mcu(sh, ref, X, Y)
    clock_reset(sh, ref, 160.02, 78.74, 147.32, 101.6)
    pwm_pulldowns(sh, ref, 307.34, 86.36)
    sh.box(127.0, 38.1, 335.28, 175.26, "MCU  STM32G431RBT6", BLUE)
    debug(sh, ref, 40.64, 60.96)
    sh.box(15.24, 33.02, 120.65, 88.9, "DEBUG: SWD + UART", GREY)
    can_addr(sh, ref, 50.8, 106.68)
    sh.box(15.24, 93.98, 120.65, 124.46, "CAN NODE ADDRESS", GREY)
    analog_front(sh, ref, 38.1, 142.24)
    sh.box(15.24, 129.54, 120.65, 180.34, "ADC INPUT RC", TEAL)
    leds(sh, ref, 38.1, 196.85)
    sh.box(15.24, 185.42, 120.65, 218.44, "STATUS LEDS", GREEN)
    sh.text(NOTES, 130.81, 187.96, size=1.5, justify="left top")
    sh.box(127.0, 180.34, 335.28, 222.25, "DESIGN NOTES (Rev B)", GREY)


def build_interfaces(sh, ref):
    can(sh, ref, 50.8, 66.04)
    sh.box(15.24, 33.02, 105.41, 101.6, "CAN-FD  (U9 TJA1051T/3)", CANC)
    ext_spi(sh, ref, 91.44, 124.46)
    sh.box(15.24, 106.68, 105.41, 147.32, "EXTERNAL SPI ENCODER  (J4)", OLIVE)
    encoder(sh, ref, 160.02, 66.04)
    sh.box(110.49, 33.02, 205.74, 101.6, "MAGNETIC ENCODER  (U2 AS5047D)", GREEN)
    enable_io(sh, ref, 189.23, 124.46)
    sh.box(110.49, 106.68, 205.74, 167.64, "ENABLE + GPIO  (J6)", SAFE)
    abi_hall(sh, ref, 312.42, 48.26)
    sh.box(210.82, 33.02, 325.12, 101.6, "ABI ENCODER / HALL INPUT  (J8)", BROWN)
    aux_out(sh, ref, 284.48, 134.62)
    sh.box(210.82, 106.68, 325.12, 162.56, "AUX HIGH-SIDE OUTPUT  (J5)", RED)
