# Décisions techniques

Journal append-only. Chaque décision est datée et justifiée.

---

## 2026-10-03 — Format PLP = ZIP + JSON

Le fichier .plp est une archive ZIP contenant data.plab (JSON) et thumb.
Les ressources sont dans res/XXXX avec des noms 4 chars.

Conséquence : zipfile + json suffisent pour lire/écrire. Aucun parsing
binaire nécessaire.

---

## 2026-10-03 — Repère interne : container 708

Toutes les coordonnées des objets sont dans un repère interne de 708 px
de large, pas en pixels canvas. Vérifié sur Badge.plp (2480×3508 →
container 708×1001) et Vdjdkdk.plp (4×5 → 708×885).

Conséquence : scale = 708 / psd.width appliqué à toutes les coordonnées
et tailles.

---

## 2026-10-13 — Ordre de lecture des calques PSD

psd-tools itère déjà du bas vers le haut (index 0 = plus bas), ce qui
correspond à objectsIds en PLP. Retirer le reversed() qui avait été
ajouté par erreur.

---

## 2026-10-14 — Couleurs texte PSD : [A, R, G, B]

FillColor.Values de PSD est au format [A, R, G, B] en floats 0-1 (pas
[R, G, B, A]). Convertir via argb_to_int(r, g, b, a).

Piège : FillColor est un psd_tools.psd.engine_data.Dict, pas un dict
Python. isinstance(fc, dict) échoue. Utiliser hasattr(fc, "get").

---

## 2026-10-14 — Couleurs overlay PSD : échelle 0-255

Les valeurs RGB du color overlay peuvent être en 0-255 (Rd=246, Grn=245).
Détection : si r, g, b <= 1.0 → ×255, sinon laisser tel quel.

---

## 2026-10-14 — Skip des adjustment layers

BrightnessContrast, Levels, Curves, HueSaturation, GradientFill,
SolidColorFill, etc. ne sont pas mappables dans PixelLab. Les skipper
silencieusement plutôt que de produire un calque vide.

---

## 2026-10-14 — Rasterisation auto des groupes à blend modes

Un groupe contenant des calques avec blend_mode non-NORMAL / non-PASS_THROUGH
(ex: SCREEN, LINEAR_DODGE) est composite en un seul PNG au lieu d'être
traversé récursivement.

Raison : PixelLab ne supporte pas ces modes, et un rendu à plat vaut mieux
qu'un rendu faux.

---

## 2026-11-09 — Thumb via psd.composite()

Le thumb est généré via psd.composite() (compositing global PSD).
Nécessite scikit-image. Sur Termux : pkg install tur-repo puis
pkg install python-scikit-image.

Fallback gris si composite() échoue.


---

## 2026-11-09 — Formes natives PixelLab : décodage qUDmYrz

En analysant 6 samples contrôlés (Square, Cercle, Tri + 3 colorés avec
radius), on a décodé le format des formes natives (shapeImageShapeType=5).

Structure de qUDmYrz :
  mfp2JbFB : 'rect' | 'oval' | 'tri1' (type de forme)
  vCScn1x  : [x0%, y0%, x1%, y1%] bounds normalisés 0-100 du container
  mrdCt2Pon.9vwh : couleur fill ARGB signée
  2Xskb7   : radius en % du plus petit côté
  wAmp2k, 3GsP, UTRQ, 3JaWTe : valeurs fixes

PIEGE majeur : la couleur passe par 9vwh, PAS par shapeColorOverlayColor
(qui reste à -65536 avec overlay=False). Renseigner 9vwh uniquement
suffit. Testé avec 3 couleurs (rouge #FF0000 = -65536, vert pur =
-16711936, jaune #FFFF00 = -256).

Le radius 2Xskb7 est en % (0=carré, 30=arrondi à 30% du petit côté).

Triangle tri1 : rendu équilatéral natif (ratio ~1.15). Ne pas l'utiliser
pour des triangles non-équilatéraux (ex: 2:1). Détection : ratio w/h
entre 0.95 et 1.25.

Implémentation : src/psd2plp/svg/native_shape.py + routing dans
to_plp.py (_element_to_plp). Les paths SVG complexes restent en raster.
