# Format PLP

Un fichier .plp est une archive ZIP (renommable en .zip) contenant :

    mon_projet.plp
      data.plab     JSON UTF-8, description complète du projet
      thumb         JPG, miniature pour la liste des presets
      res/XXXX      ressources binaires (nom = 4 chars base64-ish)

## Types de ressources

    Signature                     Type
    \x89PNG                       PNG (transparence)
    \xff\xd8\xff                  JPG (photo)
    OTTO                          police OpenType
    \x00\x01\x00\x00 / true / ttcf  police TrueType

Référencées dans data.plab par :
    /storage/emulated/0/pixelLab/presets/{nom_plp}/res/{XXXX}

## data.plab — racine

Clés principales :
- bgWidth / bgHeight : dimensions canvas réelles (ex: 1080×1350)
- bgColor : ARGB signé 32-bit
- bgPhotoSrc, bgPhotoCrop, bgGradientV2 : fond (optionnel)
- objectsBundle : dict { "shape0": {...}, "text0": {...} }
- objectsIds : ordre z, du bas vers le haut

## Repère interne : container 708

Les coordonnées des objets ne sont PAS en pixels du canvas. PixelLab
utilise un repère interne de 708 px de large, dont la hauteur dépend
du ratio :

    container_w = 708
    container_h = round(708 * (psd_height / psd_width))
    scale       = 708 / psd_width

Ex : 1080×1350 → container 708×885, scale 0.6555.

Chaque objet stocke shapeOldContainerWidth / shapeOldContainerHeight.

## Objets shape

Champs clés (voir DEFAULT_SHAPE dans writer.py pour la liste complète,
environ 70 clés) :

    Champ                        Type    Notes
    shapeX, shapeY               int     coin haut-gauche, container
    shapeWidth, shapeHeight      str     ex "636.54"
    shapeRotation                str     degrés
    shapeOpacity                 int     0-100
    shapeReference               str     ID court base64-ish
    shapeImageShapeType          int     2=image, 5=forme géométrique
    shapeColorOverlayEnabled     bool
    shapeColorOverlayColor       int     ARGB signé
    shapeImageSrc.imgSrcPath     str     chemin vers /res/XXXX

## Objets text

    Champ                        Type    Notes
    shapeX, shapeY               int     coin haut-gauche du texte
    textTextString               str     \n pour retours à la ligne
    textTextSize                 str     ex "31.85"
    textRotation                 str     degrés
    textTextColor...Color        int     ARGB signé
    textTextFont...Font          str     chemin font (optionnel)
    textMaxWidth                 int     -1 = pas de contrainte
    textAlignment                int     bitfield (8388659 = left)

## Couleurs

ARGB 32-bit signé. Conversions :

    Valeur        Couleur
    -1            blanc  0xFFFFFFFF
    -16777216     noir   0xFF000000
    -65536        rouge  0xFFFF0000
    -1176832      jaune  0xFFEE0B00

## Ce que PixelLab modifie à la sauvegarde

Comparaison faite sur food_B.plp (généré) vs food_B (2).plp (sauvegardé) :

- Renomme les ressources (9SJY → GmVI), garde parfois les anciennes
- Round les floats en float32 (636.5444444 → 636.54443)
- Arrondit les rotations quasi-nulles (3.8e-14 → 0)
- Remplit textTextFont: {} s'il était absent
- Renumérote les IDs en séquence globale (shape0..6, text7..9, shape10..)
- Chemins ZIP avec / initial (/res/X au lieu de res/X)

Aucune de ces modifications n'affecte le rendu — notre format est validé.
