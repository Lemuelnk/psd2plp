#!/usr/bin/env python3
"""CALIB3 : alignement de paragraphes (lignes de largeurs differentes).

Chaque bloc : ligne courte (A<valeur>), ligne longue (W), ligne tres courte (ii).
Une barre rouge marque le bord gauche (shapeX). On regarde comment les lignes sont
placees les unes par rapport aux autres : gauche, centre ou droite.
"""
import json
import sys
import zipfile
from pathlib import Path

from psd2plp_mcp.plp_generator import generate_plp

out = Path(sys.argv[1] if len(sys.argv) > 1 else "/storage/emulated/0/pixelLab/psd2plp_out")
vals = [8388659, 8388657, 8388661, 49, 17, 51, 53, 8388658]
objs = []
for i, v in enumerate(vals):
    x = 70 if i % 2 == 0 else 590
    y = 60 + (i // 2) * 300
    objs.append({"kind": "shape", "shape_type": "rect", "x": x - 20, "y": y - 10,
                 "width": 4, "height": 190, "fill_color": "#E53935"})
    objs.append({"kind": "text", "x": x, "y": y, "text": f"A{v}\nWWWWWWWWWWWW\nii", "text_size": 34,
                 "text_color": "#000000", "font_family": "Montserrat-Bold"})

p = out / "CALIB3.plp"
p.unlink(missing_ok=True)
generate_plp({"width": 1080, "height": 1300, "background_color": "#FFFFFF", "objects": objs}, p)
zin = zipfile.ZipFile(p)
entries = [(n, zin.read(n)) for n in zin.namelist()]
zin.close()
with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
    for n, b in entries:
        if n.endswith("data.plab"):
            d = json.loads(b)
            for o in d["objectsBundle"].values():
                t = o.get("textTextString", "")
                if t.startswith("A") and "\n" in t:
                    o["textAlignment"] = int(t.split("\n")[0][1:])
            b = json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        z.writestr(n, b)
print("CALIB3 OK:", p)
