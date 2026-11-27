#!/usr/bin/env python3
"""Gros calques d'un PSD (placeholders, masques, ecretage). Usage : inspect_layers.py FRAGMENT [N]"""
import sys
from pathlib import Path

from psd_tools import PSDImage

frag = sys.argv[1]
top = int(sys.argv[2]) if len(sys.argv) > 2 else 22
f = next(p for p in sorted(Path("examples/psd").glob("*.psd")) if frag in p.name)
psd = PSDImage.open(str(f))
W, H = psd.width, psd.height


def g(fn):
    try:
        return fn()
    except Exception:
        return None


rows = []
for l in psd.descendants():
    b = l.bbox
    area = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    if area < 0.04 * W * H:
        continue
    depth, p = 0, l.parent
    while p is not None and p is not psd:
        depth += 1
        p = p.parent
    rows.append((area, depth, type(l).__name__, str(l.name)[:26], tuple(b), l.visible,
                 round(l.opacity / 255 * 100), str(l.blend_mode).split(".")[-1],
                 g(lambda: tuple(l.vector_mask.bbox) if l.has_vector_mask() else None),
                 g(lambda: tuple(l.mask.bbox) if l.mask is not None else None),
                 g(lambda: l.clipping_layer),
                 g(lambda: l.smart_object.kind if type(l).__name__ == "SmartObjectLayer" else None)))
print(f.name, W, "x", H, "| calques >4 % du canevas :", len(rows))
print("(prof, type, nom, bbox, visible, opacite, fusion, masque vectoriel, masque raster, ecretage, objet dynamique)")
for r in sorted(rows, reverse=True)[:top]:
    print(r[1:])
