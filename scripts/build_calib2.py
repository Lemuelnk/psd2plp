#!/usr/bin/env python3
"""CALIB2 : taille et rotation du texte (a ouvrir dans PixelLab).

Planche taille   : la barre rouge a la largeur que doit avoir "HHHHHHHH" si text_size est
                   la taille em en pixels canvas. Comparer la fin du texte et la fin de la barre.
Planche rotation : boite grise + texte tournes du meme angle. Le texte doit rester dans la boite
                   si PixelLab tourne autour du centre.
"""
import sys
from pathlib import Path

from PIL import ImageFont

from psd2plp.config import FONTS_DIR
from psd2plp_mcp.plp_generator import generate_plp

FONT = "Montserrat-Bold"
TTF = FONTS_DIR / f"{FONT}.ttf"
out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/calib")
out.mkdir(parents=True, exist_ok=True)
objs = []


def text(x, y, t, size, **kw):
    objs.append({"kind": "text", "x": x, "y": y, "text": t, "text_size": size,
                 "text_color": "#000000", "font_family": FONT, **kw})


def rect(x, y, w, h, color, rot=0):
    objs.append({"kind": "shape", "shape_type": "rect", "x": x, "y": y, "width": w,
                 "height": h, "fill_color": color, "rotation": rot})


y0 = 100
for em in (40, 80, 120):
    width = ImageFont.truetype(str(TTF), em).getlength("HHHHHHHH")
    text(140, y0, "HHHHHHHH", em)
    rect(140, y0 + int(em * 1.35), round(width), 8, "#E53935")
    print(f"taille {em}: barre attendue {round(width)} px")
    y0 += int(em * 1.35) + 60

for cx, cy, ang in [(200, 900, 15), (540, 900, 45), (880, 900, 90),
                    (200, 1250, 0), (540, 1250, -30), (880, 1250, -90)]:
    w, h = 300, 70
    rect(cx - w / 2, cy - h / 2, w, h, "#CFD8DC", ang)
    text(cx - w / 2, cy - h / 2 + 14, f"ROT {ang}", 32, rotation=ang, max_width=w)

p = out / "CALIB2.plp"
p.unlink(missing_ok=True)
r = generate_plp({"width": 1080, "height": 1500, "background_color": "#FFFFFF", "objects": objs}, p)
print("CALIB2 OK:", p, r["objects"], "objets", "warnings:", r["warnings"])
