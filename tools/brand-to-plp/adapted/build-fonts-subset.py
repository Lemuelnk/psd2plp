#!/usr/bin/env python3
"""
Subsetting des 4 fontes de marque — produit WOFF2 (web) + TTF (print).

Sources : 03-assets/fonts/**/{Montserrat-ExtraBold,Montserrat-Bold,
          Montserrat-SemiBold,OpenSans-Regular}.ttf
Sortie web   : 05-web/fonts/*.woff2
Sortie print : 03-assets/fonts/subset/*.ttf

Unicodes : scripts/.font-subset-chars.txt (181 caractères, FR + ponctuation)

Usage :
    python3 scripts/build-fonts-subset.py            # tous
    python3 scripts/build-fonts-subset.py Montserrat-ExtraBold
"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHARS_FILE = ROOT / "scripts" / ".font-subset-chars.txt"
WEB_OUT = ROOT / "05-web" / "fonts"
PRINT_OUT = ROOT / "03-assets" / "fonts" / "subset"

FONTS = {
    # Montserrat Alternates (wordmark)
    "MontserratAlternates-ExtraBold": "03-assets/fonts/Montserrat_Alternates/MontserratAlternates-ExtraBold.ttf",
    # Montserrat (headings) — 400, 600, 700, 800
    "Montserrat-Regular":   "03-assets/fonts/Montserrat/static/Montserrat-Regular.ttf",
    "Montserrat-SemiBold":  "03-assets/fonts/Montserrat/static/Montserrat-SemiBold.ttf",
    "Montserrat-Bold":      "03-assets/fonts/Montserrat/static/Montserrat-Bold.ttf",
    "Montserrat-ExtraBold": "03-assets/fonts/Montserrat/static/Montserrat-ExtraBold.ttf",
    # Open Sans (body) — 400, 600
    "OpenSans-Regular":     "03-assets/fonts/Open_Sans/static/OpenSans-Regular.ttf",
    "OpenSans-SemiBold":    "03-assets/fonts/Open_Sans/static/OpenSans-SemiBold.ttf",
}


def subset_one(name, src_rel):
    src = ROOT / src_rel
    if not src.exists():
        print(f"  ✗ source manquante : {src_rel}")
        return None

    WEB_OUT.mkdir(parents=True, exist_ok=True)
    PRINT_OUT.mkdir(parents=True, exist_ok=True)

    src_size = src.stat().st_size

    # 1. WOFF2 (web)
    woff2 = WEB_OUT / f"{name}.woff2"
    cmd_woff2 = [
        "pyftsubset", str(src),
        f"--text-file={CHARS_FILE}",
        "--flavor=woff2",
        "--layout-features=kern,liga,calt",
        "--name-IDs=*",
        "--name-legacy",
        "--notdef-outline",
        "--recommended-glyphs",
        f"--output-file={woff2}",
    ]
    r = subprocess.run(cmd_woff2, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ✗ {name} woff2 : {r.stderr[:200]}")
        return None

    # 2. TTF subset (print / fallback)
    ttf = PRINT_OUT / f"{name}.ttf"
    cmd_ttf = [
        "pyftsubset", str(src),
        f"--text-file={CHARS_FILE}",
        "--layout-features=kern,liga,calt",
        "--name-IDs=*",
        "--name-legacy",
        "--notdef-outline",
        "--recommended-glyphs",
        f"--output-file={ttf}",
    ]
    r = subprocess.run(cmd_ttf, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ✗ {name} ttf : {r.stderr[:200]}")
        return None

    woff2_size = woff2.stat().st_size
    ttf_size = ttf.stat().st_size

    print(f"  ✓ {name}")
    print(f"      source : {src_size/1024:>6.1f} Ko")
    print(f"      woff2  : {woff2_size/1024:>6.1f} Ko  ({woff2_size/src_size*100:>4.1f}%)")
    print(f"      ttf    : {ttf_size/1024:>6.1f} Ko  ({ttf_size/src_size*100:>4.1f}%)")

    return {"name": name, "src": src_size, "woff2": woff2_size, "ttf": ttf_size}


def main():
    if not CHARS_FILE.exists():
        raise SystemExit(f"✗ {CHARS_FILE} manquant — lancer l'inventaire d'abord")

    targets = FONTS
    if len(sys.argv) > 1:
        names = sys.argv[1:]
        targets = {k: v for k, v in FONTS.items() if k in names}
        if not targets:
            raise SystemExit(f"✗ aucune fonte trouvée dans {names}")

    print(f"Subsetting {len(targets)} fonte(s)…\n")
    results = []
    for name, src_rel in targets.items():
        r = subset_one(name, src_rel)
        if r: results.append(r)
        print()

    if results:
        total_src = sum(r["src"] for r in results)
        total_woff2 = sum(r["woff2"] for r in results)
        total_ttf = sum(r["ttf"] for r in results)
        print("═" * 60)
        print(f"TOTAL source : {total_src/1024:>7.1f} Ko")
        print(f"TOTAL woff2  : {total_woff2/1024:>7.1f} Ko  ({total_woff2/total_src*100:>4.1f}%)")
        print(f"TOTAL ttf    : {total_ttf/1024:>7.1f} Ko  ({total_ttf/total_src*100:>4.1f}%)")
        print("═" * 60)


if __name__ == "__main__":
    main()
