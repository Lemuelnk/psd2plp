#!/usr/bin/env python3
"""CALIB4 : interlettrage et interligne (a ouvrir dans PixelLab)."""
import sys
from pathlib import Path

from PIL import ImageFont

from psd2plp.config import FONTS_DIR
from psd2plp_mcp.plp_generator import generate_plp

FONT = "Montserrat-Bold"
out = Path(sys.argv[1] if len(sys.argv) > 1 else "output")
objs = []


def text(x, y, t, size, **kw):
    objs.append({"kind": "text", "x": x, "y": y, "text": t, "text_size": size,
                 "text_color": "#000000", "font_family": FONT, **kw})


base = ImageFont.truetype(str(FONTS_DIR / f"{FONT}.ttf"), 36).getlength("WORLD CHAMPION")
objs.append({"kind": "shape", "shape_type": "rect", "x": 60, "y": 38, "width": round(base), "height": 6,
             "fill_color": "#E53935"})
y = 60
for ls in (-2, -1, 0, 0.05, 0.1, 0.5, 1, 2, 5):
    text(60, y, "WORLD CHAMPION", 36, letter_spacing=ls)
    text(760, y + 6, f"ls {ls}", 28)
    y += 70
for j, ls in enumerate((-10, 0, 10, 0.5)):
    text(60 + j * 250, 760, "LINE A\nLINE B\nLINE C", 30, line_spacing=ls)
    text(60 + j * 250, 900, f"line {ls}", 24)
p = out / "CALIB4.plp"
p.unlink(missing_ok=True)
generate_plp({"width": 1080, "height": 1000, "background_color": "#FFFFFF", "objects": objs}, p)
print("CALIB4 OK:", p)
