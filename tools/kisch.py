"""Tiny KiCad schematic generator.

Loads symbols from KiCad libraries (system or project), places instances,
computes pin coordinates, and writes .kicad_sch files.  Coordinates are mm,
sheet frame (y down).  Symbol library frame is y up.
"""
import math
import os
import uuid as _uuid
from sexp import parse, dumps, Sym, find, findall

S = Sym
SYSLIB = "/usr/share/kicad/symbols"
_ns = _uuid.UUID("6c0f9e1e-2a7b-4d0e-9a51-0f0c0d0e0f10")


def uid(seed):
    return str(_uuid.uuid5(_ns, seed))


GRID = 1.27


def snap(v):
    return round(round(v / GRID) * GRID, 4)


# --------------------------------------------------------------------------
# Library handling
# --------------------------------------------------------------------------
class Library:
    def __init__(self):
        self.files = {}      # libname -> path
        self.cache = {}      # libname -> {symname: sexp}
        self.custom = {}     # "lib:name" -> sexp (already flattened, name=bare)

    def add_file(self, libname, path):
        self.files[libname] = path

    def _load(self, lib):
        if lib in self.cache:
            return self.cache[lib]
        path = self.files.get(lib, os.path.join(SYSLIB, lib + ".kicad_sym"))
        tree = parse(open(path).read())
        d = {}
        for s in findall(tree, "symbol"):
            d[s[1]] = s
        self.cache[lib] = d
        return d

    def get(self, lib_id):
        """Return flattened symbol sexp whose name is the bare symbol name."""
        if lib_id in self.custom:
            return self.custom[lib_id]
        lib, name = lib_id.split(":", 1)
        d = self._load(lib)
        s = d[name]
        ext = find(s, "extends")
        if ext is None:
            return s
        parent = self.get(lib + ":" + ext[1])
        pname = parent[1]
        out = [S("symbol"), name]
        child_props = {p[1]: p for p in findall(s, "property")}
        for x in parent[2:]:
            if isinstance(x, list) and x[0] == "property":
                out.append(child_props.pop(x[1], x))
            elif isinstance(x, list) and x[0] == "symbol":
                sub = list(x)
                sub[1] = name + sub[1][len(pname):]
                out.append(sub)
            else:
                out.append(x)
        # remaining child-only props: insert before first sub-symbol
        idx = next(i for i, x in enumerate(out) if isinstance(x, list) and x[0] == "symbol")
        for p in child_props.values():
            out.insert(idx, p)
            idx += 1
        return out


LIB = Library()


def sym_pins(sexp):
    """List of dicts: num, name, x, y, ang, length, type, unit."""
    pins = []
    base = sexp[1]
    for sub in findall(sexp, "symbol"):
        tail = sub[1][len(base) + 1:]
        unit = int(tail.split("_")[0])
        for p in findall(sub, "pin"):
            at = find(p, "at")
            pins.append(dict(num=find(p, "number")[1], name=find(p, "name")[1],
                             x=float(at[1]), y=float(at[2]), ang=float(at[3]),
                             length=float(find(p, "length")[1]),
                             type=str(p[1]), unit=unit))
    return pins


def rot(x, y, deg):
    a = math.radians(deg)
    c, s = round(math.cos(a)), round(math.sin(a))
    return x * c - y * s, x * s + y * c


# --------------------------------------------------------------------------
# Schematic
# --------------------------------------------------------------------------
def font(size=1.27, bold=False, color=None, thick=None):
    f = [S("font"), [S("size"), size, size]]
    if thick:
        f.append([S("thickness"), thick])
    if bold:
        f.append([S("bold"), S("yes")])
    if color:
        f.append([S("color")] + list(color))
    return f


def effects(size=1.27, justify=None, hide=False, bold=False, color=None):
    e = [S("effects"), font(size, bold, color)]
    if justify:
        e.append([S("justify")] + [S(j) for j in justify.split()])
    if hide:
        e.append([S("hide"), S("yes")])
    return e


class Inst:
    def __init__(self, sheet, lib_id, ref, x, y, rotn, mirror, unit, sexp):
        self.sheet, self.lib_id, self.ref = sheet, lib_id, ref
        self.x, self.y, self.rot, self.mirror, self.unit = x, y, rotn, mirror, unit
        self.pins = [p for p in sym_pins(sexp) if p["unit"] in (0, unit)]

    def _xf(self, px, py):
        # KiCad: rotate first, then mirror (mirror x = flip vertically, mirror y = flip horizontally)
        rx, ry = rot(px, py, self.rot)
        if self.mirror == "y":
            rx = -rx
        elif self.mirror == "x":
            ry = -ry
        return round(self.x + rx, 4), round(self.y - ry, 4)

    def _find(self, key):
        key = str(key)
        m = [p for p in self.pins if p["num"] == key]
        if not m:
            m = [p for p in self.pins if p["name"] == key]
        if not m:
            raise KeyError("%s: no pin %s" % (self.ref, key))
        return m[0]

    def pin(self, key):
        p = self._find(key)
        return self._xf(p["x"], p["y"])

    def pdir(self, key):
        """Outward direction (sheet angle, 0=right, 90=up) of pin."""
        p = self._find(key)
        a = (p["ang"] + 180) % 360
        dx, dy = round(math.cos(math.radians(a))), round(math.sin(math.radians(a)))
        dx, dy = rot(dx, dy, self.rot)
        if self.mirror == "y":
            dx = -dx
        elif self.mirror == "x":
            dy = -dy
        return int(round(math.degrees(math.atan2(dy, dx)))) % 360

    def allpins(self):
        return [(p["num"], p["name"]) for p in self.pins]


DIRV = {0: (1, 0), 90: (0, -1), 180: (-1, 0), 270: (0, 1)}   # sheet deltas


class Sheet:
    def __init__(self, name, filename, paper="A3", title="", project="foc-driver"):
        self.name, self.filename, self.paper, self.title = name, filename, paper, title
        self.project = project
        self.uuid = uid("sheet:" + filename)
        self.path = None          # instance path, set by Project
        self.items = []
        self.libsyms = {}
        self.insts = []
        self.wires = []           # (x1,y1,x2,y2)
        self.labels = []          # (name, x, y, ang, kind)
        self.ncs = []
        self.n = 0
        self.extra_junctions = []
        self.tag = "".join(w[0] for w in filename.replace(".kicad_sch", "").replace("-", "_").split("_")).upper()

    def _u(self, tag):
        self.n += 1
        return uid("%s:%s:%d" % (self.filename, tag, self.n))

    # ---------------- symbols
    def place(self, lib_id, ref, value, x, y, rot=0, mirror=None, unit=1,
              footprint="", props=None, fields=None, dnp=False, hide_value=False,
              in_bom=True):
        sexp = LIB.get(lib_id)
        self.libsyms[lib_id] = sexp
        inst = Inst(self, lib_id, ref, x, y, rot, mirror, unit, sexp)
        inst.value, inst.footprint = value, footprint
        inst.props = props or {}
        inst.fields = fields or {}
        inst.dnp, inst.hide_value, inst.in_bom = dnp, hide_value, in_bom
        inst.sexp = sexp
        self.insts.append(inst)
        return inst

    def _inst_sexp(self, inst):
        sx = inst.sexp
        lp = {p[1]: p for p in findall(sx, "property")}
        rot_ = inst.rot
        e = [S("symbol"), [S("lib_id"), inst.lib_id], [S("at"), inst.x, inst.y, rot_]]
        if inst.mirror:
            e.append([S("mirror"), S(inst.mirror)])
        e += [[S("unit"), inst.unit], [S("exclude_from_sim"), S("no")],
              [S("in_bom"), S("yes" if inst.in_bom else "no")], [S("on_board"), S("yes")],
              [S("dnp"), S("yes" if inst.dnp else "no")],
              [S("uuid"), uid("%s:inst:%s:%d" % (self.filename, inst.ref, inst.unit))]]
        is_power = inst.ref.startswith("#")
        vals = {"Reference": inst.ref, "Value": inst.value,
                "Footprint": inst.footprint, "Datasheet": None, "Description": None}
        vals.update(inst.props)
        order = ["Reference", "Value", "Footprint", "Datasheet", "Description"] + \
            [k for k in inst.props if k not in ("Reference", "Value", "Footprint", "Datasheet", "Description")]
        for k in order:
            v = vals.get(k)
            src = lp.get(k)
            if v is None:
                v = src[2] if src else ""
            fx = inst.fields.get(k)
            if fx is None and k in ("Reference", "Value") and _is_small2(inst):
                fx = _small2_field(inst, k)
            if fx is not None:
                px, py, just = fx[0], fx[1], (fx[2] if len(fx) > 2 else "left")
                ang = fx[3] if len(fx) > 3 else 0
                hide = False
            elif src is not None and find(src, "at"):
                at = find(src, "at")
                px, py = inst._xf(float(at[1]), float(at[2]))
                px, py = px - inst.x, py - inst.y
                ang = 0
                ef = find(src, "effects")
                j = find(ef, "justify") if ef else None
                just = " ".join(str(a) for a in j[1:]) if j else None
                if inst.rot in (90, 270) or inst.mirror:
                    just = _flip_just(just, inst)
                hide = bool(ef and find(ef, "hide")) or bool(find(src, "hide"))
            else:
                px, py, just, ang, hide = 0, 0, None, 0, True
            if k in ("Footprint", "Datasheet", "Description") or k.startswith("ki_"):
                hide = True
            if k in inst.props and k not in ("Value", "Reference") and fx is None:
                hide = True
            if k == "Value" and inst.hide_value:
                hide = True
            if k == "Reference" and is_power:
                hide = True
            ang = (ang + inst.rot) % 180
            e.append([S("property"), k, v, [S("at"), round(inst.x + px, 3), round(inst.y + py, 3), ang],
                      effects(1.27, just, hide)])
        for num, _ in inst.allpins():
            e.append([S("pin"), num, [S("uuid"), uid("%s:%s:pin:%s:%d" % (self.filename, inst.ref, num, inst.unit))]])
        e.append([S("instances"), [S("project"), self.project,
                                   [S("path"), self.path, [S("reference"), inst.ref], [S("unit"), inst.unit]]]])
        return e

    # ---------------- connectivity primitives
    def wire(self, *pts):
        pts = [(round(a, 4), round(b, 4)) for a, b in pts]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if (x1, y1) != (x2, y2):
                self.wires.append((x1, y1, x2, y2))

    def label(self, name, x, y, ang=0, kind="auto", shape="bidirectional"):
        self.labels.append([name, round(x, 4), round(y, 4), ang % 360, kind, shape])

    def nc(self, x, y):
        self.ncs.append((round(x, 4), round(y, 4)))

    def junction(self, x, y):
        self.extra_junctions.append((x, y))

    # ---------------- helpers on instances
    def pin_label(self, inst, pin, name, stub=0, shape="bidirectional"):
        x, y = inst.pin(pin)
        d = inst.pdir(pin)
        if stub:
            dx, dy = DIRV[d]
            x2, y2 = x + dx * stub, y + dy * stub
            self.wire((x, y), (x2, y2))
            x, y = x2, y2
        self.label(name, x, y, d, shape=shape)
        return x, y

    def pin_nc(self, inst, pin):
        self.nc(*inst.pin(pin))

    def power(self, net, x, y, rot=0):
        """Place power symbol with its pin at (x,y)."""
        lib_id = POWER_LIB.get(net, "foc-driver:" + net)
        self.npwr = getattr(self, "npwr", 0) + 1
        ref = "#PWR%s%03d" % (self.tag, self.npwr)
        i = self.place(lib_id, ref, net, x, y, rot, in_bom=False)
        return i

    def pin_power(self, inst, pin, net, stub=0):
        x, y = inst.pin(pin)
        if stub:
            dx, dy = DIRV[inst.pdir(pin)]
            self.wire((x, y), (x + dx * stub, y + dy * stub))
            x, y = x + dx * stub, y + dy * stub
        self.power(net, x, y)
        return x, y

    # ---------------- graphics
    def box(self, x1, y1, x2, y2, title, color):
        r, g, b = color
        self.items.append([S("rectangle"), [S("start"), x1, y1], [S("end"), x2, y2],
                           [S("stroke"), [S("width"), 0.4], [S("type"), S("dash")], [S("color"), r, g, b, 1]],
                           [S("fill"), [S("type"), S("color")], [S("color"), r, g, b, 0.06]],
                           [S("uuid"), self._u("rect")]])
        self.text(title, x1 + 1.5, y1 + 3.2, size=2.2, bold=True, color=(r, g, b, 1))

    def text(self, s, x, y, size=1.27, bold=False, color=None, justify="left bottom"):
        self.items.append([S("text"), s, [S("exclude_from_sim"), S("no")], [S("at"), x, y, 0],
                           effects(size, justify, bold=bold, color=color), [S("uuid"), self._u("text")]])

    # ---------------- output
    def pin_points(self):
        pts = []
        for i in self.insts:
            for num, _ in i.allpins():
                pts.append(i.pin(num))
        return pts

    def junctions(self):
        from collections import Counter
        c = Counter()
        for x1, y1, x2, y2 in self.wires:
            c[(x1, y1)] += 1
            c[(x2, y2)] += 1
        pinpts = set(self.pin_points())
        for p in pinpts:
            if p in c:
                c[p] += 1
        js = set(p for p, k in c.items() if k >= 3)
        # wire endpoint touching interior of another wire
        ends = list(c.keys()) + list(pinpts)
        for x1, y1, x2, y2 in self.wires:
            for (px, py) in ends:
                if (px, py) in ((x1, y1), (x2, y2)):
                    continue
                if x1 == x2 == px and min(y1, y2) < py < max(y1, y2):
                    js.add((px, py))
                elif y1 == y2 == py and min(x1, x2) < px < max(x1, x2):
                    js.add((px, py))
        js |= set(self.extra_junctions)
        # only keep T-points that involve at least one wire
        return sorted(js)

    def sexp(self, global_nets, sheets_tree=None):
        e = [S("kicad_sch"), [S("version"), 20250114], [S("generator"), "eeschema"],
             [S("generator_version"), "10.0"], [S("uuid"), self.uuid], [S("paper"), self.paper]]
        e.append([S("title_block"), [S("title"), self.title or self.name],
                  [S("date"), "2026-10-02"], [S("rev"), "B"], [S("company"), "FOC Motor Driver"]])
        ls = [S("lib_symbols")]
        for lid, sx in sorted(self.libsyms.items()):
            s2 = list(sx)
            s2[1] = lid
            ls.append(s2)
        e.append(ls)
        for (x, y) in self.junctions():
            e.append([S("junction"), [S("at"), x, y], [S("diameter"), 0], [S("color"), 0, 0, 0, 0],
                      [S("uuid"), self._u("j")]])
        for (x, y) in self.ncs:
            e.append([S("no_connect"), [S("at"), x, y], [S("uuid"), self._u("nc")]])
        for x1, y1, x2, y2 in self.wires:
            e.append([S("wire"), [S("pts"), [S("xy"), x1, y1], [S("xy"), x2, y2]],
                      [S("stroke"), [S("width"), 0], [S("type"), S("default")]], [S("uuid"), self._u("w")]])
        for name, x, y, ang, kind, shape in self.labels:
            is_g = (kind == "global") or (kind == "auto" and name in global_nets)
            just = "left" if ang in (0, 90) else "right"
            if is_g:
                e.append([S("global_label"), name, [S("shape"), S(shape)], [S("at"), x, y, ang],
                          [S("fields_autoplaced"), S("yes")], effects(1.27, just),
                          [S("uuid"), self._u("gl")],
                          [S("property"), "Intersheetrefs", "${INTERSHEET_REFS}", [S("at"), x, y, 0],
                           effects(1.27, just, hide=True)]])
            else:
                e.append([S("label"), name, [S("at"), x, y, ang], effects(1.27, just + " bottom"),
                          [S("uuid"), self._u("l")]])
        e += self.items
        for i in self.insts:
            e.append(self._inst_sexp(i))
        if sheets_tree:
            e += sheets_tree
        return e


def _is_small2(inst):
    return inst.lib_id.split(":")[1] in SMALL2


SMALL2 = {"R_Small_US", "C_Small", "L_Small", "C_Polarized_Small", "D_Small", "D_Zener_Small",
          "D_Schottky_Small", "D_TVS_Small", "FerriteBead_Small", "LED_Small", "R_Small", "Thermistor_NTC_Small"}


HORIZ2 = {"D_Small", "D_Zener_Small", "D_Schottky_Small", "D_TVS_Small", "LED_Small"}


def _small2_field(inst, k):
    vertical = (inst.rot in (0, 180)) != (inst.lib_id.split(":")[1] in HORIZ2)
    if vertical:
        return (1.9, -0.95, "left") if k == "Reference" else (1.9, 0.95, "left")
    return (0, -2.2, "") if k == "Reference" else (0, 2.2, "")


def _flip_just(just, inst):
    return just


POWER_LIB = {"GND": "power:GND"}


class Project:
    def __init__(self, name, root):
        self.name, self.root = name, root
        self.subs = []     # (sheet, x, y, w, h)
        root.path = "/" + root.uuid

    def add_sub(self, sheet, x, y, w, h):
        self.subs.append((sheet, x, y, w, h))

    def write(self, outdir):
        # global nets = label names used on >1 sheet
        sheets = [self.root] + [s for s, *_ in self.subs]
        use = {}
        for sh in sheets:
            for lb in sh.labels:
                use.setdefault(lb[0], set()).add(sh.filename)
        gnets = {n for n, f in use.items() if len(f) > 1}
        tree = []
        for k, (sh, x, y, w, h) in enumerate(self.subs):
            su = uid("sheetsym:" + sh.filename)
            sh.path = self.root.path + "/" + su
            tree.append([S("sheet"), [S("at"), x, y], [S("size"), w, h], [S("exclude_from_sim"), S("no")],
                         [S("in_bom"), S("yes")], [S("on_board"), S("yes")], [S("dnp"), S("no")],
                         [S("fields_autoplaced"), S("yes")],
                         [S("stroke"), [S("width"), 0.1524], [S("type"), S("solid")]],
                         [S("fill"), [S("color"), 0, 0, 0, 0.0]], [S("uuid"), su],
                         [S("property"), "Sheetname", sh.name, [S("at"), x, y - 0.7, 0],
                          effects(1.27, "left bottom")],
                         [S("property"), "Sheetfile", sh.filename, [S("at"), x, y + h + 0.6, 0],
                          effects(1.27, "left top")],
                         [S("instances"), [S("project"), self.name,
                                           [S("path"), self.root.path, [S("page"), str(k + 2)]]]]])
        for sh in sheets:
            extra = tree if sh is self.root else None
            e = sh.sexp(gnets, extra)
            if sh is self.root:
                e.append([S("sheet_instances"), [S("path"), "/", [S("page"), "1"]]])
            e.append([S("embedded_fonts"), S("no")])
            with open(os.path.join(outdir, sh.filename), "w") as f:
                f.write(dumps(e) + "\n")
        return gnets
