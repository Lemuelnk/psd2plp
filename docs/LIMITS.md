# Limites connues

## Ce qui marche

- Positions / tailles / rotations des calques
- Couleurs de texte (y compris par run)
- Contenu texte (retour chariot converti en \n)
- Shapes rasterisés en PNG
- Color overlay
- Skip adjustment layers
- Rasterisation des groupes à blend modes complexes
- Thumb réel (composite global)

## Ce qui ne marche pas / partiellement

### Polices
On n'embarque PAS les fonts du PSD dans res/. PixelLab utilise sa
police par défaut. Les textes auront donc une police différente du PSD.

Cause : FontSet du PSD donne le nom (Rubik-Bold, August-Shining) mais
le fichier .otf/.ttf n'est pas dans le PSD. Il faut un mapping
nom → fichier local.

### Drop shadow / stroke
psd/effects.py sait les lire, mais le writer.py ne les écrit pas encore
dans les clés shapeShadowEnabled / shapeStrokeEnabled / etc.

### Vraies formes vectorielles (partiel)
Côté PSD : toutes les ShapeLayer sont rasterisées en PNG.
Côté SVG : les primitives <rect>, <circle>, <ellipse>, <polygon 3pts>
sont mappées vers des formes NATIVES PixelLab (shapeImageShapeType=5,
qUDmYrz décodé). Les paths complexes restent en raster.

Décodage qUDmYrz : voir DECISIONS.md 2026-11-09.

### Groupes PixelLab
La hiérarchie des groupes PSD est aplatie. PixelLab ne semble pas avoir
de groupes dans objectsBundle — à vérifier.

### SmartObjects placeholder
Les SmartObjects "Place Your Image Here" deviennent des rectangles gris.
C'est attendu : dans PixelLab, l'utilisateur clique dessus pour mettre
son image.

### Effets 3D, emboss, gradients multiples
Pas d'équivalent PixelLab ou pas implémentés. Ignorés.

### Blend modes
Un groupe avec blend modes non-NORMAL est composé à plat. Les calques
individuels avec blend_mode différent sont appliqués par-dessus sans
modulation (équivalent à NORMAL).

### SVG ↔ PLP
En cours de conception. Aucune fonctionnalité.

### Génération par prompt / spec (`generate_plp`)
- `raw_properties` et `raw_root_properties` sont ignorés (avertissement dans la réponse).
- Famille non téléchargée : erreur explicite. Fichier Montserrat/OpenSans absent du subset lnk-brand : le texte sort sans police embarquée (police par défaut de PixelLab) avec un avertissement.
- Un texte n'utilise qu'une police (pas de mélange par intervalles).
- Pas de calcul de retour à la ligne côté générateur : utiliser `\n`.
- Compatibilité PixelLab d'un projet généré : test sur l'appareil encore à faire.

## Bugs / points ouverts

- Thumb via composite() peut échouer sur des PSD avec ressources
  inconnues (warning "Unknown image resource 1092"). Fallback gris.
- Les PSD avec beaucoup de calques très imbriqués peuvent produire des
  timings de conversion longs (> 30s).
