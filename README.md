# psd2plp

Convertisseur PSD → PLP (format de projet PixelLab) et outils SVG ↔ PLP.

> État : pipeline PSD → PLP fonctionnel. SVG ↔ PLP en cours de conception.

## Quick start

    pip install psd-tools Pillow
    python -m psd2plp.cli convert mon_fichier.psd -o output/mon_projet.plp

## Documentation

- docs/SETUP.md — installer sur Termux / Linux
- docs/PLP_FORMAT.md — spécification du format PLP
- docs/COMMANDS.md — commandes CLI, git, tests
- docs/DECISIONS.md — journal des choix techniques
- docs/LIMITS.md — contraintes et fonctionnalités partielles
- docs/SPEC.md — schéma JSON pour générer un PLP sans code
- docs/WORKFLOW.md — arborescence, chemins, workflow quotidien

## Structure

    src/psd2plp/
      cli.py               point d'entrée CLI
      convert.py           orchestration PSD → PLP
      psd/                 lecture PSD (psd-tools)
        reader.py
        layers.py
        text.py
        effects.py
      mapping/             PSD → PlpProject
        psd_to_plp.py
      pixellab/            modèle + reader/writer PLP
        model.py
        reader.py
        writer.py
      svg/                 SVG ↔ PLP (WIP)

## Licence

Privé.
