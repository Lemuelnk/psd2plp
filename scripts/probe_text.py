#!/usr/bin/env python3
"""Sonde de texte : metriques de polices (PIL) et donnees de rotation (psd-tools).

  python3 scripts/probe_text.py psd FRAGMENT     # textes d'un PSD : taille, police, rotation, decalages prevus
  python3 scripts/probe_text.py calib5 DOSSIER   # planche CALIB5 : decalage vertical / horizontal des polices
"""
import math
import os
import sys
from pathlib import Path

from PIL import ImageFont

FONT_DIRS = [Path("/storage/emulated/0/pixelLab/fonts"), Path("/storage/emulated/0/pixelLab/fonts_old_backup")]
WANT = ["BebasNeue-Regular", "PlusJakartaSans-Bold", "SpaceGrotesk-Bold", "Montserrat-Bold",
        "Antonio-Bold", "Rubik-SemiBold", "Poppins-Bold"]


def s(v):
    return str(v).strip("'\" \ufeff")


def font_index():
    idx = {}
    for base in FONT_DIRS:
        for root, _dirs, files in os.walk(base):
            for fn in files:
                if fn.lower().endswith((".ttf", ".otf")):
                    idx.setdefault(Path(fn).stem.lower(), Path(root) / fn)
    return idx


def metrics(path, ch="H"):
    f = ImageFont.truetype(str(path), 1000)
    asc, desc = f.getmetrics()
    box = f.getbbox("H", anchor="ls")
    lsb = f.getbbox(ch, anchor="ls")[0] if ch.strip() else 0
    return asc / 1000, desc / 1000, -box[1] / 1000, lsb / 1000


def cookie(eng):
    try:
        ch = eng["Rendered"]["Shapes"]["Children"][0]["Cookie"]["Photoshop"]
        return {k: str(ch[k])[:140] for k in ("PointBase", "Base") if k in ch}
    except Exception as e:
        return "n/a (%s)" % type(e).__name__


def probe_psd(frag):
    from psd_tools import PSDImage

    f = next(p for p in sorted(Path("examples/psd").glob("*.psd")) if frag in p.name)
    psd = PSDImage.open(str(f))
    idx = font_index()
    print("==", f.name, psd.width, "x", psd.height)
    rows, extra = [], []
    for l in psd.descendants():
        if type(l).__name__ != "TypeLayer":
            continue
        txt = (l.text or "").replace("\r", "/").replace("\n", "/")
        try:
            eng = l.engine_dict or {}
            fs = [s(x.get("Name")) for x in (l.resource_dict or {}).get("FontSet", [])]
            sheet = eng["StyleRun"]["RunArray"][0]["StyleSheet"]["StyleSheetData"]
            fi = sheet.get("Font")
            ps = fs[int(fi)] if fi is not None and int(fi) < len(fs) else "?"
            tf = [float(x) for x in l.transform]
            em = float(sheet.get("FontSize") or 0) * (math.hypot(tf[2], tf[3]) or 1.0)
            rot = math.degrees(math.atan2(tf[1], tf[0]))
            try:
                j = int(eng["ParagraphRun"]["RunArray"][0]["ParagraphSheet"]["Properties"].get("Justification", 0))
                just = {0: "G", 1: "D", 2: "C"}.get(j, "?")
            except Exception:
                just = "?"
        except Exception as e:
            rows.append((0, "%r erreur %s" % (txt[:16], type(e).__name__)))
            continue
        path = idx.get(ps.lower())
        if path:
            asc, desc, cap, lsb = metrics(path, txt[:1] or "H")
            m = "asc=%.3f cap=%.3f y+=%5.1f x+=%4.1f" % (asc, cap, (asc - cap) * em, lsb * em)
        else:
            m = "police introuvable"
        b = tuple(int(v) for v in l.bbox)
        rows.append((em, "%-18r em=%6.1f %-26s rot=%6.1f j=%s bbox=%s | %s" % (txt[:16], em, ps[:26], rot, just, b, m)))
        if abs(rot) > 0.5 or any(txt.lower().startswith(k) for k in ("www", "ball", "tackles", "now", "match")):
            extra.append((txt[:14], [round(x, 2) for x in tf], getattr(l, "text_type", None),
                          str(getattr(l, "warp", None))[:70], cookie(eng)))
    for _, line in sorted(rows, key=lambda r: -r[0])[:20]:
        print(line)
    print("--- donnees de rotation (texte, transform, type, warp, cookie) ---")
    for e in extra[:6]:
        print(e)


def calib5(out):
    from psd2plp.config import FONTS_DIR
    from psd2plp.pixellab.writer import write_plp
    from psd2plp.spec.builder import plp_from_spec
    from psd2plp.spec.schema import Spec, SpecCanvas, SpecShape, SpecText

    idx = font_index()
    fonts = []
    for name in WANT:
        p = idx.get(name.lower())
        if p is None and (FONTS_DIR / f"{name}.ttf").exists():
            p = FONTS_DIR / f"{name}.ttf"
        if p is not None:
            fonts.append((name, Path(p)))
    fonts = fonts[:5]
    if not fonts:
        print("aucune police trouvee ; exemples dans pixelLab/fonts :", sorted(idx)[:25])
        return
    EM = 100.0
    texts, lines = [], []
    for i, (name, p) in enumerate(fonts):
        y0 = 80 + i * 200
        asc, desc, cap, lsb = metrics(p)
        print("%-24s asc=%.3f desc=%.3f cap=%.3f lsb(H)=%.3f  -> y+=%.1f x+=%.1f (em=100)" %
              (name, asc, desc, cap, lsb, (asc - cap) * EM, lsb * EM))
        texts.append(SpecText(text="HHHH xg", x=140, y=y0, size_px=EM * 0.7, font="Montserrat-Regular",
                              font_path=str(p), color="#000000"))
        texts.append(SpecText(text=name, x=640, y=y0 + 125, size_px=14, font="Montserrat-Bold", color="#444444"))
        lines += [
            SpecShape(kind="rect", x=60, y=y0, w=900, h=2, fill="#E53935"),                       # haut de la boite
            SpecShape(kind="rect", x=60, y=y0 + (asc - cap) * EM, w=900, h=2, fill="#1E88E5"),    # haut des capitales prevu
            SpecShape(kind="rect", x=60, y=y0 + asc * EM, w=900, h=2, fill="#43A047"),            # ligne de base prevue
            SpecShape(kind="rect", x=140, y=y0, w=2, h=170, fill="#E53935"),                      # bord gauche de la boite
            SpecShape(kind="rect", x=140 + lsb * EM, y=y0 + 20, w=2, h=130, fill="#1E88E5"),      # bord gauche prevu de l'encre
        ]
    spec = Spec(canvas=SpecCanvas(width=1080, height=80 + len(fonts) * 200 + 40, bg="#FFFFFF", margin=80),
                objects=texts + lines)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    proj = plp_from_spec(spec, plp_name="CALIB5")
    write_plp(proj, out / "CALIB5.plp", plp_name="CALIB5")
    print("CALIB5 OK:", out / "CALIB5.plp", "|", len(fonts), "polices")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("psd", "calib5"):
        sys.exit(__doc__)
    (probe_psd if sys.argv[1] == "psd" else calib5)(sys.argv[2])
