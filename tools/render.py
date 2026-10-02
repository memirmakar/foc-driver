#!/usr/bin/env python3
"""Render a schematic sheet (or a mm-region of it) to PNG for visual review.

usage: render.py <sheet.kicad_sch> <out.png> [x1 y1 x2 y2] [--ppm N]
Region in sheet millimetres.  --ppm = pixels per mm (default: fit 1800 px wide).
"""
import os
import re
import subprocess
import sys
import glob

KCLI = "/home/memro/.backplane-bend/kicad/10.0.6/bin/kicad-cli"


def main():
    a = sys.argv[1:]
    ppm = None
    if "--ppm" in a:
        i = a.index("--ppm")
        ppm = float(a[i + 1])
        del a[i:i + 2]
    sch, out = a[0], a[1]
    region = [float(v) for v in a[2:6]] if len(a) >= 6 else None
    tmp = "/tmp/kisch_render"
    os.makedirs(tmp, exist_ok=True)
    for f in glob.glob(tmp + "/*.svg"):
        os.remove(f)
    subprocess.run([KCLI, "sch", "export", "svg", "-o", tmp, "--exclude-drawing-sheet" if region else "--no-background-color", sch],
                   check=True, capture_output=True)
    base = os.path.splitext(os.path.basename(sch))[0]
    svgs = glob.glob(tmp + "/*.svg")
    # pick the svg that corresponds to the requested sheet
    svg = None
    exact = [s for s in svgs if os.path.basename(s) == base + ".svg"]
    if exact:
        svg = exact[0]
    if svg is None:
        # hierarchical export names pages <root>-<sheetname>.svg; match by sheet name
        cand = [s for s in svgs if base.replace("_", "") in os.path.basename(s).replace("_", "").replace("-", "")]
        svg = cand[-1] if cand else svgs[0]
    txt = open(svg).read(4000)
    m = re.search(r'width="([\d.]+)mm" height="([\d.]+)mm"', txt)
    W, H = float(m.group(1)), float(m.group(2))
    if region:
        x1, y1, x2, y2 = region
        if ppm is None:
            ppm = min(1800 / (x2 - x1), 1800 / (y2 - y1))
    else:
        x1, y1, x2, y2 = 0, 0, W, H
        ppm = ppm or 1800 / W
    full = tmp + "/full.png"
    subprocess.run(["rsvg-convert", "-w", str(int(W * ppm)), "-b", "white", svg, "-o", full], check=True)
    if region:
        subprocess.run(["magick", full, "-crop", "%dx%d+%d+%d" % ((x2 - x1) * ppm, (y2 - y1) * ppm, x1 * ppm, y1 * ppm),
                        "+repage", out], check=True)
    else:
        import shutil
        shutil.move(full, out)
    print(out, svg)


if __name__ == "__main__":
    main()
