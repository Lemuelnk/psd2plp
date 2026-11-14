# Workflow psd2plp

## Arborescence

Code dans `$HOME/lnk-projects/` (exec autorisé, git-friendly).
Assets lourds dans `~/storage/shared/` (accès Android partagé).

    ~/lnk-projects/
      psd2plp/                 <- Code source (ce repo)
        .git/                  <- 147M d'historique
        src/                   <- Package Python
        tools/brand-to-plp/    <- Fork scripts lnk-brand
        docs/                  <- Documentation
        examples/specs/        <- Specs JSON (petits)
        examples/psd -> symlink
        examples/plp -> symlink
        output -> symlink

    ~/storage/shared/LNK_WORKS/
      psd2plp_data/            <- Assets lourds (non versionnés)
        examples/psd/          <- 255M de PSD de test
        examples/plp/          <- 130M de PLP de référence
        output/                <- PLP générés (5M+)
      lnk-brand/               <- Projet branding séparé
        03-assets/fonts/subset/  <- TTF utilisés

    /storage/emulated/0/pixelLab/
      psd2plp_out/             <- Cible de déploiement PixelLab
      presets/                 <- Géré par PixelLab (NE PAS TOUCHER)

## Variables d'environnement

Toutes les valeurs par défaut pointent vers l'arborescence ci-dessus.
Surchargeables :

    PSD2PLP_DATA_ROOT   # défaut : ~/storage/shared/LNK_WORKS/psd2plp_data
    LNK_BRAND_ROOT      # défaut : ~/storage/shared/LNK_WORKS/lnk-brand
    LNK_BRAND_FONTS     # défaut : $LNK_BRAND_ROOT/03-assets/fonts/subset
    PIXELLAB_ROOT       # défaut : /storage/emulated/0/pixelLab

Toutes définies dans `src/psd2plp/config.py`.

## Workflow quotidien

### Convertir un PSD en PLP

    cd ~/lnk-projects/psd2plp
    python -m psd2plp.cli convert examples/psd/mon.psd -o output/mon.plp

### Convertir un SVG en PLP

    python -m psd2plp.cli convert mon.svg -o output/mon.plp

### Générer un PLP depuis un spec JSON

    python -m psd2plp.cli from-spec examples/specs/poster_demo.json -o output/poster.plp

### Déployer dans PixelLab

    bash scripts/push-to-pixellab.sh output/mon.plp
    # ou tout :
    bash scripts/push-to-pixellab.sh

### Régénérer les SVG brand-to-plp

    bash tools/brand-to-plp/run.sh citation light mother
    bash tools/brand-to-plp/run.sh announce dark mother

### Convertir un SVG brand-to-plp en PLP

    python3 -c "
    import sys
    sys.path.insert(0, 'tools/brand-to-plp')
    from converter.svg_to_plp import svg_to_plp
    from psd2plp.pixellab.writer import write_plp
    proj = svg_to_plp('/chemin/svg')
    write_plp(proj, 'output/mon.plp')
    "

## Règles d'or

1. **JAMAIS écrire dans `pixelLab/presets/`** — c'est géré par PixelLab
2. Les assets lourds (PSD, PLP) restent dans `psd2plp_data/`
3. Les specs JSON (petits) restent dans `examples/specs/` (versionnés)
4. Tout code source dans `~/lnk-projects/psd2plp/`
5. Symlinks pour compatibilité : `examples/psd`, `examples/plp`, `output`

## Installer le projet (première fois)

    cd ~/lnk-projects/psd2plp
    pip install -e .
    # vérif :
    python -m psd2plp.cli --help
