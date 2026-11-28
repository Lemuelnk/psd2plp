#!/usr/bin/env python3
"""Metriques de polices (tables sfnt) comparees aux mesures PixelLab de CALIB5."""
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from probe_text import font_index  # noqa: E402

# Mesures dans PixelLab (CALIB5, em = 100 px canvas, boite en x = 140.3) : (decalage de la ligne de base, decalage du bord gauche du H)
OBS = {"BebasNeue-Regular": (89.7, 12.7), "Montserrat-Bold": (108.3, 16.7),
       "Rubik-SemiBold": (109.6, 16.7), "Poppins-Bold": (110.7, 14.7)}


def sfnt(path):
    b = Path(path).read_bytes()
    n = struct.unpack_from(">H", b, 4)[0]
    t = {}
    for i in range(n):
        tag, _cs, off, _ln = struct.unpack_from(">4sIII", b, 12 + 16 * i)
        t[tag.decode("latin1")] = off
    upm = struct.unpack_from(">H", b, t["head"] + 18)[0]
    out = {"yMax": struct.unpack_from(">h", b, t["head"] + 42)[0] / upm,
           "hhea": struct.unpack_from(">h", b, t["hhea"] + 4)[0] / upm}
    if "OS/2" in t:
        o = t["OS/2"]
        out["typo"] = struct.unpack_from(">h", b, o + 68)[0] / upm
        out["win"] = struct.unpack_from(">H", b, o + 74)[0] / upm
    return out


def glyph_h(path):
    f = ImageFont.truetype(str(path), 1000)
    im = Image.new("L", (2400, 2400), 0)
    ImageDraw.Draw(im).text((700, 1600), "H", font=f, anchor="ls", fill=255)
    x0, y0, _x1, _y1 = im.getbbox()
    return (x0 - 700) / 1000, (1600 - y0) / 1000


idx = font_index()
from psd2plp.config import FONTS_DIR  # noqa: E402
for _p in FONTS_DIR.glob("*.ttf"):
    idx.setdefault(_p.stem.lower(), _p)
print("police | base observee | hhea typo win yMax | lsb(H) cap | marge gauche implicite (px a em=100)")
for name, (base, left) in OBS.items():
    p = idx.get(name.lower())
    if not p:
        print(name, ": police introuvable")
        continue
    m = sfnt(p)
    lsb, cap = glyph_h(p)
    print("%-18s base=%.3f | hhea=%.3f typo=%.3f win=%.3f yMax=%.3f | lsb=%.3f cap=%.3f | marge=%.1f" % (
        name, base / 100, m["hhea"], m.get("typo", 0), m.get("win", 0), m["yMax"], lsb, cap, left - lsb * 100))
    print("   ecart base - metrique :", {k: round(base / 100 - v, 3) for k, v in m.items()})
