# psd2plp

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

Convertisseur **PSD / SVG / Spec JSON** vers **PLP** (format de projet
PixelLab), avec serveur **MCP** pour ChatGPT et Claude, gestion de
polices, et apps web/mobile (en préparation).

## Ce que le projet fait

| Source | Moteur | Sortie |
|---|---|---|
| `.psd` (Photoshop) | `psd2plp.psd` + `psd2plp.mapping` | `.plp` éditable |
| `.svg` (vectoriel) | `psd2plp.svg` | `.plp` (formes natives + raster) |
| `.json` (spec) | `psd2plp.spec` | `.plp` (text, shapes, images) |
| prompt (LLM) | `psd2plp_mcp` + skill | `.plp` (via generate_plp) |

Le PLP produit est **éditable dans PixelLab** : textes modifiables
(fonts embarquées), formes natives (`rect`, `oval`, `tri`),
images remplaçables.

## Quick start

    pip install psd2plp
    pip install "psd2plp[mcp]"

    psd2plp convert mon.psd -o output/mon.plp
    psd2plp convert mon.svg -o output/mon.plp
    psd2plp from-spec examples/specs/poster_demo.json -o output/poster.plp
    psd2plp-mcp

## Font Engine et génération par prompt

Le serveur MCP local expose aussi le Font Engine et le générateur PLP :

- Synchronisation du catalogue public Fontsource et recherche locale des familles.
- Téléchargement à la demande de variantes TTF depuis Fontsource ou Google Fonts.
- Import de polices personnalisées TTF/OTF avec déclaration de licence.
- Intégration des variantes TTF téléchargées dans les ressources du PLP généré.
- Conservation du texte éditable ; la compatibilité réelle des polices doit encore être vérifiée par ouverture, sauvegarde et réouverture dans PixelLab.

Le serveur MCP est un processus local en stdio ; cette configuration ne constitue pas un service distant accessible automatiquement depuis ChatGPT mobile.

Voir [docs/FONT_ENGINE.md](docs/FONT_ENGINE.md) et [le workflow prompt-to-plp](plugins/skills/prompt-to-plp/SKILL.md).

## Plugin Claude Code

Installer d'abord le serveur MCP (une fois), puis le plugin :

    uv tool install git+https://github.com/Lemuelnk/psd2plp
    # ou : pip install git+https://github.com/Lemuelnk/psd2plp

Dans Claude Code :

    /plugin marketplace add Lemuelnk/psd2plp
    /plugin install psd2plp@lnk-psd2plp

Les projets générés, les polices téléchargées et le catalogue sont stockés dans `~/.psd2plp` (variable `PSD2PLP_HOME` pour changer ; `PSD2PLP_OUTPUT_DIR` pour la sortie seule). Depuis un clone du dépôt, le dossier du dépôt est utilisé.

## Structure

    src/psd2plp/                Moteur de conversion
      psd/                      Lecture PSD (psd-tools)
      svg/                      Lecture SVG (formes natives + raster)
      spec/                     Spec JSON -> PlpProject
      mapping/                  PSD -> PlpProject
      pixellab/                 Modele + reader/writer PLP
      config.py                 Chemins centralises (env vars)
      cli.py                    CLI : inspect, convert, from-spec

    src/psd2plp_mcp/            Serveur MCP (optionnel, extra [mcp])
      server.py                 Point d'entree stdio JSON-RPC
      plp_generator.py          Adaptateur vers psd2plp.spec.builder
      plp_engine.py             Roundtrip lossless d'un PLP existant
      plp_core.py               inspect_plp, validate_plp (legacy)
      font_engine.py            Catalogue 150 familles + download

    plugins/                    Configurations clients
      chatgpt/                  Manifeste plugin ChatGPT + MCP
      claude/                   Config MCP Claude
      skills/prompt-to-plp/     Skill pour LLM

    media/                      Assets versionnes (pas de code)
      fonts/catalog.seed.json   Catalogue de polices
      examples/                 Exemples visuels

    apps/                       UIs (migration future)
      pwa/                      psd2plpG (placeholder)
      android-native/           psd2plp-app (placeholder)

    data/                       Donnees locales (gitignore)
      fonts/downloaded/         TTF telecharges
      fonts/custom/             TTF custom importes
      examples/, output/        Symlinks vers psd2plp_data/

## Documentation

- [SETUP.md](docs/SETUP.md) — installation Termux / Linux / macOS
- [PLP_FORMAT.md](docs/PLP_FORMAT.md) — specification du format PLP
  (structure ZIP, data.plab, container 708, ARGB, qUDmYrz)
- [SPEC.md](docs/SPEC.md) — schema JSON pour from-spec
- [COMMANDS.md](docs/COMMANDS.md) — CLI, tests, deploiement
- [WORKFLOW.md](docs/WORKFLOW.md) — arborescence + workflow quotidien
- [DECISIONS.md](docs/DECISIONS.md) — journal des choix techniques
- [LIMITS.md](docs/LIMITS.md) — contraintes connues
- [FONT_ENGINE.md](docs/FONT_ENGINE.md) — moteur de polices
- [PLP_ENGINE.md](docs/PLP_ENGINE.md) — roundtrip lossless
- [HANDOFF.md](docs/HANDOFF.md) — pour continuer le projet sans aide

## Dependances

Moteur (installe automatiquement) :

- psd-tools (MIT) — lecture PSD
- Pillow (HPND) — images
- scikit-image (BSD-3) — compositing PSD
- cairosvg (LGPL-3) — rasterisation SVG

Serveur MCP : aucune dependance supplementaire (stdlib only).

## Licence

Apache 2.0 — voir [LICENSE](LICENSE).

## Remerciements

psd-tools et la communaute PixelLab pour les samples de reference
qui ont permis de reverse-engineer le format .plp.
