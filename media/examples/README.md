# media/examples

Screenshots et exemples visuels pour la documentation.

## Fichiers attendus

- poster_demo.png         Rendu du spec poster_demo
- story_demo.png          Rendu story
- multi_color_demo.png    Rendu multi-couleurs

## Comment regenerer

    python -m psd2plp.cli from-spec examples/specs/poster_demo.json \
        -o output/poster_demo.plp
    # puis ouvrir dans PixelLab et exporter PNG
