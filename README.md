# psd2plp

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

Convertisseur **PSD -> PLP** (format de projet PixelLab) et **SVG -> PLP**
avec formes natives editables.

> Etat : pipeline PSD -> PLP et SVG -> PLP fonctionnels. Teste sur
> Termux, Linux et macOS.

## Fonctionnalites

- **PSD -> PLP** : calques texte (position, taille, rotation, couleur,
  multi-runs), shapes raster, color overlay, skip des adjustment layers,
  rasterisation auto des groupes a blend modes complexes
- **SVG -> PLP** : `<rect>`, `<circle>`, `<ellipse>`, `<polygon>` deviennent
  des **formes natives PixelLab editables** (`shapeImageShapeType=5` avec
  `qUDmYrz`), les paths complexes restent en raster haute resolution
- **Thumb intelligent** : PNG RGBA si transparence detectee, JPEG sinon
- **CLI auto-detecte** l'extension source

## Quick start

    pip install psd-tools Pillow scikit-image cairosvg
    pip install -e .

    # Convertir un PSD
    python -m psd2plp.cli convert mon_fichier.psd -o output/mon_projet.plp

    # Convertir un SVG
    python -m psd2plp.cli convert mon_logo.svg -o output/mon_logo.plp

## Documentation

- [SETUP.md](docs/SETUP.md) — installation Termux / Linux
- [PLP_FORMAT.md](docs/PLP_FORMAT.md) — **specification complete du
  format PLP** (structure ZIP, data.plab, container 708, couleurs ARGB,
  `qUDmYrz`)
- [COMMANDS.md](docs/COMMANDS.md) — CLI, tests, deploiement PixelLab
- [DECISIONS.md](docs/DECISIONS.md) — journal des choix techniques
- [LIMITS.md](docs/LIMITS.md) — contraintes et fonctionnalites partielles

## Structure

    src/psd2plp/
      cli.py               point d'entree CLI
      convert.py           orchestration PSD/SVG -> PLP
      psd/                 lecture PSD (psd-tools)
      mapping/             PSD -> PlpProject
      pixellab/            modele + reader/writer PLP
      svg/                 SVG -> PLP (formes natives + raster)
    tools/brand-to-plp/
      adapted/             scripts SVG enrichis (fork)
      converter/           SVG enrichi -> PlpProject

## Dependances

- [psd-tools](https://github.com/psd-tools/psd-tools) (MIT) — lecture PSD
- [Pillow](https://python-pillow.org/) (HPND) — manipulation d'images
- [scikit-image](https://scikit-image.org/) (BSD-3) — compositing PSD
  avance
- [cairosvg](https://cairosvg.org/) (LGPL-3) — rasterisation SVG

## Ce que ce projet n'est **pas**

- Ce n'est **pas** une re-implementation de PixelLab. C'est un
  convertisseur tiers qui produit des fichiers `.plp` valides.
- Ce n'est **pas** un moyen d'avoir du vectoriel editable dans PixelLab
  pour les logos complexes : PixelLab ne stocke pas de paths vectoriels,
  seulement des formes predefinies (rect, oval, tri) et des rasters.

## Licence

Apache 2.0 — voir [LICENSE](LICENSE).

## Remerciements

Merci aux mainteneurs de `psd-tools` et a la communaute PixelLab pour
les samples de reference qui ont permis de reverse-engineer le format
`.plp`.
