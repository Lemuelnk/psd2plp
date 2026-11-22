"""Racine des donnees du serveur MCP (sorties, polices, catalogue mutable).

- PSD2PLP_HOME defini : ce dossier.
- sinon, depuis un clone du depot (pyproject.toml present) : la racine du depot.
- sinon (paquet installe) : ~/.psd2plp
"""
from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PACKAGE_SEED = PACKAGE_DIR / "data" / "catalog.seed.json"
_CHECKOUT_ROOT = PACKAGE_DIR.parents[1]


def is_checkout() -> bool:
    return (_CHECKOUT_ROOT / "pyproject.toml").is_file() and (_CHECKOUT_ROOT / "src" / "psd2plp_mcp").is_dir()


def resolve_home() -> Path:
    env = os.environ.get("PSD2PLP_HOME")
    if env:
        return Path(env).expanduser().resolve()
    if is_checkout():
        return _CHECKOUT_ROOT
    return (Path.home() / ".psd2plp").resolve()


HOME = resolve_home()
