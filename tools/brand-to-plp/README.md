# brand-to-plp

Adaptation locale des scripts de generation de templates sociaux pour
produire des fichiers PLP editables au lieu de SVG plats.

## Origine

Fork d'un projet de branding separe (prive). Seule la partie conversion
est publiee ici :

- `adapted/` : scripts modifies pour emettre des attributs `data-plp-*`
  sur les elements SVG (texte natif, positions, tailles, couleurs)
- `converter/` : lit ces SVG enrichis et genere des `PlpProject` avec
  textes natifs editables, logos en image, decorations en raster

Les scripts source originaux (generation SVG pour site web) ne sont
**pas** inclus dans ce repo.

## Utilisation

Le converter attend un SVG enrichi par `adapted/build-social-templates.py`.
Les chemins des fonts et des assets sont configurables via variables
d'environnement (`LNK_BRAND_ROOT`, `LNK_BRAND_FONTS`).

    from tools.brand_to_plp.converter.svg_to_plp import svg_to_plp
    from psd2plp.pixellab.writer import write_plp

    proj = svg_to_plp("/path/to/enriched.svg")
    write_plp(proj, "/path/to/out.plp")

## Limites

- Depend d'une structure de projet externe (fonts TTF, assets de marque)
- Les templates specifiques (citation, announce, story) ne sont pas
  publies dans ce repo
