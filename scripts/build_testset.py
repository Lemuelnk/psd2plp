#!/usr/bin/env python3
"""Genere le jeu de test nomme (ALPHA, BRAVO...) avec le moteur courant.

Usage : python3 scripts/build_testset.py DOSSIER_SORTIE [CODE ...]
"""
import json
import sys
from pathlib import Path

from psd2plp.convert import convert

ROOT = Path(__file__).resolve().parent.parent
TESTSET = json.loads(Path(__file__).with_name("testset.json").read_text(encoding="utf-8"))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    psds = sorted((ROOT / "examples" / "psd").glob("*.psd"))
    for code in sys.argv[2:] or list(TESTSET):
        f = next(p for p in psds if TESTSET[code]["match"] in p.name)
        dest = out / f"{code}.plp"
        convert(str(f), str(dest), plp_name=code)
        print(code, "<-", f.name, round(dest.stat().st_size / 1e6, 2), "Mo")


if __name__ == "__main__":
    main()
