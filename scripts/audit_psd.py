#!/usr/bin/env python3
"""Audit des PSD : contenu + resultat de la conversion (lecture seule).

Usage : python3 scripts/audit_psd.py [dossier] [--timeout 120] [--out DIR] [--only TEXTE] [--limit N]
Ecrit un JSON par PSD dans --out (defaut ~/.cache/psd2plp_audit) ; ne modifie ni les PSD ni le depot.
"""
from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path


def _s(v):
    return str(v).replace("\ufeff", "").strip().strip("'\"")


def inspect_one(psd_path: Path) -> dict:
    from psd_tools import PSDImage
    from psd2plp.mapping.psd_to_plp import convert_psd, _group_has_blend

    res = {"name": psd_path.name, "size_mb": round(psd_path.stat().st_size / 1e6, 1)}
    t0 = time.time()
    psd = PSDImage.open(str(psd_path))
    res.update(width=psd.width, height=psd.height, mode=str(psd.color_mode), depth=psd.depth)
    kinds, blends, fx = collections.Counter(), collections.Counter(), collections.Counter()
    fonts, just, c = collections.Counter(), collections.Counter(), collections.Counter()
    for l in psd.descendants():
        c["layers"] += 1
        kinds[type(l).__name__] += 1
        if not l.visible:
            c["hidden"] += 1
        if l.is_group():
            c["groups"] += 1
            if _group_has_blend(l):
                c["groups_blend"] += 1
        bm = str(getattr(l, "blend_mode", "") or "")
        if bm and "NORMAL" not in bm and "PASS_THROUGH" not in bm:
            blends[bm.split(".")[-1]] += 1
        try:
            if getattr(l, "mask", None) is not None:
                c["masks"] += 1
            if l.has_vector_mask():
                c["vector_masks"] += 1
            if getattr(l, "clipping_layer", False):
                c["clipping"] += 1
        except Exception:
            pass
        try:
            for e in (l.effects or []):
                fx[type(e).__name__] += 1
        except Exception:
            pass
        if type(l).__name__ == "TypeLayer":
            c["text"] += 1
            try:
                eng = l.engine_dict or {}
                fontset = [_s(f.get("Name")) for f in (l.resource_dict or {}).get("FontSet", [])]
                runs = eng.get("StyleRun", {}).get("RunArray", [])
                cols, idx = set(), set()
                for r in runs:
                    d = r.get("StyleSheet", {}).get("StyleSheetData", {})
                    fc = d.get("FillColor")
                    if hasattr(fc, "get") and fc.get("Values"):
                        cols.add(tuple(round(float(x), 2) for x in fc.get("Values")))
                    if d.get("Font") is not None:
                        idx.add(int(d.get("Font")))
                for i in (idx or {0}):
                    if i < len(fontset):
                        fonts[fontset[i]] += 1
                if len(runs) > 1:
                    c["text_multi_run"] += 1
                if len(cols) > 1:
                    c["text_multi_color"] += 1
                if len(idx) > 1:
                    c["text_multi_font"] += 1
                for pr in eng.get("ParagraphRun", {}).get("RunArray", [])[:1]:
                    just[str(pr.get("ParagraphSheet", {}).get("Properties", {}).get("Justification"))] += 1
            except Exception:
                c["text_errors"] += 1
    res.update(counts=dict(c), kinds=dict(kinds), blends=dict(blends), effects=dict(fx),
               fonts=dict(fonts), justification=dict(just), inspect_s=round(time.time() - t0, 1))

    def cand(container):
        n = 0
        for l in container:
            if not l.visible:
                continue
            if l.is_group():
                n += 1 if _group_has_blend(l) else cand(l)
            elif type(l).__name__ == "TypeLayer" and not (l.text or "").strip():
                continue
            else:
                n += 1
        return n

    conv, t1 = {}, time.time()
    try:
        proj = convert_psd(str(psd_path))
        conv.update(ok=True, objects=len(proj.objects), resources=len(proj.resources),
                    text_objects=sum(1 for o in proj.objects if o.kind == "text"),
                    candidates=cand(psd), has_thumb=("_thumb_bytes" in proj.raw_template),
                    res_mb=round(sum(len(r.data) for r in proj.resources) / 1e6, 1))
        conv["dropped"] = conv["candidates"] - conv["objects"]
    except Exception as e:
        conv.update(ok=False, error=f"{type(e).__name__}: {e}"[:300], trace=traceback.format_exc()[-600:])
    conv["seconds"] = round(time.time() - t1, 1)
    res["convert"] = conv
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", default="examples/psd")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--out", default=str(Path.home() / ".cache" / "psd2plp_audit"))
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--one")
    a = ap.parse_args()
    out = Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    if a.one:
        p = Path(a.one)
        r = inspect_one(p)
        (out / (p.stem + ".json")).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        return

    files = [p for p in sorted(Path(a.dir).glob("*.psd")) if a.only.lower() in p.name.lower()]
    if a.limit:
        files = files[: a.limit]
    results = []
    for p in files:
        jf = out / (p.stem + ".json")
        jf.unlink(missing_ok=True)
        try:
            cp = subprocess.run([sys.executable, __file__, "--one", str(p), "--out", str(out)],
                                timeout=a.timeout, capture_output=True, text=True)
            if jf.exists():
                r = json.loads(jf.read_text(encoding="utf-8"))
            else:
                r = {"name": p.name, "convert": {"ok": False, "error": "crash: " + (cp.stderr or "")[-200:], "seconds": 0}}
        except subprocess.TimeoutExpired:
            r = {"name": p.name, "convert": {"ok": False, "error": "timeout>%ds" % a.timeout, "seconds": a.timeout}}
        results.append(r)
        cv, ct = r.get("convert", {}), r.get("counts", {})
        status = "ok" if cv.get("ok") else "ECHEC " + str(cv.get("error", ""))[:60]
        print(f"{r['name'][:34]:34} {r.get('width', 0)}x{r.get('height', 0)} L{ct.get('layers', 0):>4} "
              f"T{ct.get('text', 0):>3} fx{sum(r.get('effects', {}).values()):>3} bg{ct.get('groups_blend', 0):>2} "
              f"drop{cv.get('dropped', 0):>3} {cv.get('seconds', 0):>6}s {status}", flush=True)

    ok = [r for r in results if r.get("convert", {}).get("ok")]
    print("\n===== RECAPITULATIF =====")
    print(f"PSD audites : {len(results)} | convertis sans exception : {len(ok)} | echecs : {len(results) - len(ok)}")
    tot = collections.Counter()
    for key in ("effects", "blends", "fonts", "kinds", "justification"):
        tot[key] = collections.Counter()
        for r in results:
            tot[key].update(r.get(key, {}))
    for label, key in (("Effets de calque", "effects"), ("Modes de fusion", "blends"),
                       ("Types de calques", "kinds"), ("Justification texte", "justification")):
        print(f"{label} : {dict(tot[key].most_common(12))}")
    print("Polices (top 25) :", dict(tot["fonts"].most_common(25)))
    for label, key in (("PSD avec texte multi-couleur", "text_multi_color"), ("PSD avec texte multi-police", "text_multi_font"),
                       ("PSD avec masques", "masks"), ("PSD avec masques vectoriels", "vector_masks"),
                       ("PSD avec calques d'ecretage", "clipping"), ("PSD avec groupes a modes de fusion", "groups_blend")):
        print(f"{label} : {sum(1 for r in results if r.get('counts', {}).get(key))}")
    print("PSD avec effets de calque :", sum(1 for r in results if r.get("effects")))
    print("PSD avec calques perdus (drop>0) :", [r["name"][:26] for r in ok if r["convert"].get("dropped", 0) > 0][:15])
    print("Echecs :", [(r["name"][:26], r["convert"].get("error", "")[:50]) for r in results if not r.get("convert", {}).get("ok")])
    print("Les plus lents :", sorted(((r["convert"].get("seconds", 0), r["name"][:26]) for r in results), reverse=True)[:5])


if __name__ == "__main__":
    main()
