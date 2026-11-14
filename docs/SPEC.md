# Spec JSON — générer un PLP sans code

Un "spec" est un fichier JSON qui décrit un visuel complet. Il est
converti en .plp éditable via `psd2plp from-spec`.

## Commande

    python -m psd2plp.cli from-spec spec.json -o out.plp

## Structure

    {
      "canvas": { "width": 1080, "height": 1350, "bg": "#001A17", "margin": 80 },
      "objects": [ ... ]
    }

## canvas

- width, height : int, px canvas (requis)
- bg : str, couleur hex (défaut "#FFFFFF")
- margin : float, marge de sécurité auto-fit (défaut 80)

## objects

Tableau ordonné. Premier objet = plus bas (z-index). Types : text,
rect, oval, tri, image.

## Objet text

    {
      "kind": "text",
      "text": "Votre idée",
      "x": 80, "y": 350,
      "size_px": 110,
      "font": "Montserrat-ExtraBold",
      "color": "#F4F9F8",
      "align": "center",
      "opacity": 100,
      "rotation": 0,
      "runs": [
        {"length": 6, "color": "#F4F9F8"},
        {"length": 4, "color": "#FFC107"}
      ]
    }

Champs :
- size_px : HAUTEUR DE CAPITALE en px (pas la taille em)
- font : voir liste ci-dessous
- align : "left" (défaut), "center", "right"
- runs : optionnel, multi-couleurs par segment (somme des lengths = len(text))

Auto-fit : si le texte dépasse canvas.width - 2*margin, size_px est
réduite automatiquement (mesure réelle via PIL).

## Objet rect / oval / tri

    {
      "kind": "rect",
      "x": 80, "y": 700, "w": 920, "h": 6,
      "fill": "#FF7043",
      "radius_pct": 50
    }

radius_pct : 0-50, % du petit côté (rect uniquement).
Formes natives PixelLab = éditables dans l'app (couleur, radius, taille).

## Objet image

    {
      "kind": "image",
      "path": "/chemin/logo.png",
      "x": 80, "y": 900, "w": 200, "h": 60
    }

Embarque le fichier dans res/. Doit être PNG/JPG valide.

## Fonts disponibles

- Montserrat-Regular
- Montserrat-SemiBold
- Montserrat-Bold
- Montserrat-ExtraBold
- MontserratAlternates-ExtraBold
- OpenSans-Regular
- OpenSans-SemiBold

Configurable via LNK_BRAND_FONTS (dossier des TTF).

## Limitations actuelles

- Pas d'ombres, gradients, glow
- Pas de wrap auto (utiliser \n dans text)
- Pas de courbes / icônes custom (seulement rect/oval/tri natifs,
  reste en raster PNG)

## Exemples

- examples/specs/poster_demo.json
- examples/specs/story_demo.json
- examples/specs/carousel_slide.json
- examples/specs/multi_color_demo.json
