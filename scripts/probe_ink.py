#!/usr/bin/env python3
"""Angle reel des textes d'un PSD (analyse des pixels) compare a la matrice TySh.
Usage : probe_ink.py FRAGMENT [N]"""
import math
import sys
from pathlib import Path

import numpy as np
from psd_tools import PSDImage

frag = sys.argv[1]
top = int(sys.argv[2]) if len(sys.argv) > 2 else 24
f = next(p for p in sorted(Path("examples/psd").glob("*.psd")) if frag in p.name)
psd = PSDImage.open(str(f))


def chain(layer):
    names, p = [], layer.parent
    while p is not None and p is not psd:
        names.append(str(p.name)[:12] + ("" if p.visible else "(masque)"))
        p = p.parent
    return "/".join(reversed(names))


def ink(layer):
    try:
        im = layer.topil()
    except Exception:
        return None
    if im is None:
        return None
    a = np.array(im.convert("RGBA"))[:, :, 3]
    ys, xs = np.nonzero(a > 40)
    if len(xs) < 30:
        return None
    w, v = np.linalg.eigh(np.cov(np.stack([xs - xs.mean(), ys - ys.mean()])))
    ang = math.degrees(math.atan2(v[1, 1], v[0, 1]))
    ang = ang - 180 if ang > 90 else ang + 180 if ang <= -90 else ang
    return dict(w=int(xs.max() - xs.min() + 1), h=int(ys.max() - ys.min() + 1), x0=int(xs.min()), y0=int(ys.min()),
                x1=int(a.shape[1] - 1 - xs.max()), y1=int(a.shape[0] - 1 - ys.max()),
                ang=ang, el=math.sqrt(w[1] / max(w[0], 1e-9)))


rows = []
for l in psd.descendants():
    if type(l).__name__ != "TypeLayer":
        continue
    tf = [float(x) for x in l.transform]
    b = l.bbox
    k = ink(l)
    area = (b[2] - b[0]) * (b[3] - b[1])
    txt = (l.text or "").replace("\r", "/").replace("\n", "/")[:13]
    rows.append((area, "%-15r vis=%d chaine=%-30s TySh=%5.1f bbox=%dx%d %s" % (
        txt, int(l.visible), chain(l)[:30], math.degrees(math.atan2(tf[1], tf[0])), b[2] - b[0], b[3] - b[1],
        ("ink=%dx%d marges h/b=%d/%d g/d=%d/%d angle_pixels=%s" % (
            k["w"], k["h"], k["y0"], k["y1"], k["x0"], k["x1"],
            "%5.1f" % k["ang"] if k["el"] > 3.5 else "-")) if k else "ink=n/a")))
print("==", f.name)
for _, line in sorted(rows, reverse=True)[:top]:
    print(line)
