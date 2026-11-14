"""Chemins centralisés pour psd2plp.

Toutes les variables sont configurables via variables d'environnement.
Les valeurs par défaut correspondent à l'arborescence Termux de dev.

- PSD2PLP_DATA_ROOT : racine des assets lourds (PSD, PLP, output)
- LNK_BRAND_ROOT    : projet lnk-brand (scripts de génération)
- LNK_BRAND_FONTS   : dossier des fonts subset TTF
"""
from __future__ import annotations
import os
from pathlib import Path


HOME = Path(os.environ.get("HOME", "~")).expanduser()


def _default_data_root() -> Path:
    return HOME / "storage" / "shared" / "LNK_WORKS" / "psd2plp_data"


def _default_brand_root() -> Path:
    return HOME / "storage" / "shared" / "LNK_WORKS" / "lnk-brand"


DATA_ROOT = Path(os.environ.get("PSD2PLP_DATA_ROOT", _default_data_root()))
BRAND_ROOT = Path(os.environ.get("LNK_BRAND_ROOT", _default_brand_root()))
FONTS_DIR = Path(os.environ.get(
    "LNK_BRAND_FONTS", BRAND_ROOT / "03-assets" / "fonts" / "subset",
))

# Dossiers dérivés
EXAMPLES_PSD = DATA_ROOT / "examples" / "psd"
EXAMPLES_PLP = DATA_ROOT / "examples" / "plp"
OUTPUT_DIR = DATA_ROOT / "output"

# Cible de déploiement PixelLab
PIXELLAB_ROOT = Path(os.environ.get(
    "PIXELLAB_ROOT", Path("/storage/emulated/0/pixelLab"),
))
PIXELLAB_OUT = PIXELLAB_ROOT / "psd2plp_out"


def ensure_dirs() -> None:
    """Crée les dossiers de sortie si absents."""
    for p in (DATA_ROOT, EXAMPLES_PSD, EXAMPLES_PLP, OUTPUT_DIR, PIXELLAB_OUT):
        p.mkdir(parents=True, exist_ok=True)
