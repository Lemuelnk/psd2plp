# psd2plp

Convertisseur PSD → PLP (format de projet PixelLab) et outils SVG ↔ PLP.

> État : pipeline PSD → PLP fonctionnel. SVG ↔ PLP en cours de conception.

## Quick start

    pip install psd-tools Pillow
    python -m psd2plp.cli convert mon_fichier.psd -o output/mon_projet.plp

## Font Engine et génération par prompt

Le serveur MCP local expose aussi le Font Engine et le générateur PLP :

- Synchronisation du catalogue public Fontsource et recherche locale des familles.
- Téléchargement à la demande de variantes TTF depuis Fontsource ou Google Fonts.
- Import de polices personnalisées TTF/OTF avec déclaration de licence.
- Intégration des variantes TTF téléchargées dans les ressources du PLP généré.
- Conservation du texte éditable ; la compatibilité réelle des polices doit encore être vérifiée par ouverture, sauvegarde et réouverture dans PixelLab.

Le serveur MCP est un processus local en stdio ; cette configuration ne constitue pas un service distant accessible automatiquement depuis ChatGPT mobile.

Voir [docs/FONT_ENGINE.md](docs/FONT_ENGINE.md) et [le workflow prompt-to-plp](plugins/skills/prompt-to-plp/SKILL.md).

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
