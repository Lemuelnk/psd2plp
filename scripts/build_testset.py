#!/usr/bin/env python3
"""Genere le jeu de test nomme (ALPHA, BRAVO...) avec le moteur courant.

Usage : python3 scripts/build_testset.py DOSSIER_SORTIE [CODE ...] [--suffix -F1]
"""
import json
import sys
from pathlib import Path

from psd2plp.convert import convert

ROOT = Path(__file__).resolve().parent.parent
TESTSET = json.loads(Path(__file__).with_name("testset.json").read_text(encoding="utf-8"))


def main():
    args = sys.argv[1:]
    suffix = ""
    if "--suffix" in args:
        i = args.index("--suffix")
        suffix = args[i + 1]
        del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    out = Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    psds = sorted((ROOT / "examples" / "psd").glob("*.psd"))
    for code in args[1:] or list(TESTSET):
        f = next(p for p in psds if TESTSET[code]["match"] in p.name)
        dest = out / f"{code}{suffix}.plp"
        convert(str(f), str(dest), plp_name=f"{code}{suffix}")
        print(code + suffix, "<-", f.name, round(dest.stat().st_size / 1e6, 2), "Mo")


if __name__ == "__main__":
    main()
