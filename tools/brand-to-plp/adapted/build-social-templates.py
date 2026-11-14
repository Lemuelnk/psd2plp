#!/usr/bin/env python3
"""
Générateur de templates sociaux LNK.

================================================================================
USAGE
================================================================================

    python3 scripts/build-social-templates.py <template> <mode> [branch] [motif]

Arguments :
    template : citation | announce | story
    mode     : light | dark
    branch   : (optionnel) mother (défaut) | design-touch | dev | print | play | cine
    motif    : (optionnel) A | B | C | D | E (défaut = A)

================================================================================
TEMPLATES DISPONIBLES
================================================================================

    citation : T1 — Post carré 1080×1080 (manifeste, citation)
               Contenu : eyebrow + titre 3 lignes + sous-titre + logo
               Recommandé : motif A (coin sup. droit) ou C (vertex géant)

    announce : T2 — Post portrait 1080×1350 (annonce, 4:5)
               Contenu : eyebrow + titre 2 lignes + zone visuelle + CTA + logo
               Recommandé : motif B (bande bas)

    story    : T3 — Story 1080×1920 (9:16)
               Contenu : eyebrow + titre 3 lignes + zone visuelle + CTA + logo
               Recommandé : motif D (cercle loupe)

================================================================================
MOTIFS (variantes de fond)
================================================================================

    A : Grille coin sup. droit, masque radial
        → Subtil, présent sans envahir
        → Usage : posts éditoriaux

    B : Bande bas 260px, fade vertical
        → Ancre le bas, contenu domine
        → Usage : posts avec zone visuelle

    C : Un seul vertex géant 500px ancré bas-droite, opacité 8%
        → Ultra sobre, signature discrète
        → Usage : posts premium, dark mode

    D : Grille dans un cercle masque (380px rayon) en coin sup. GAUCHE
        → Effet "loupe", concentré
        → Usage : stories, formats verticaux longs

    E : Bandes latérales gauche + droite (fade radial sur les bords)
        → Motif sur les côtés, centre libre pour contenu
        → Usage : formats portrait (annonce 4:5)

================================================================================
EXEMPLES
================================================================================

    python3 scripts/build-social-templates.py citation light
    → citation-light-A.png (motif A par défaut)

    python3 scripts/build-social-templates.py announce dark design-touch
    → announce-dark-A.png (branche DT, motif A)

    python3 scripts/build-social-templates.py story light mother C
    → story-light-C.png (mère, motif C)

================================================================================
SORTIE
================================================================================

    PNG + SVG dans : 04-exports/social/<folder>/<branch>/  (folder = posts/stories/avatars/covers)
    Nommage : <template>-<mode>-<motif>.png

================================================================================
DOCUMENTATION
================================================================================

    Voir 04-exports/social/README.md pour la matrice complète.
    Voir scripts/README.md pour la documentation des autres scripts.
"""


import re, subprocess, sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

import os as _os
ROOT = Path(_os.environ.get("LNK_BRAND_ROOT", Path(__file__).resolve().parents[1]))
FONT_ALT = next(ROOT.glob("03-assets/fonts/**/MontserratAlternates-ExtraBold.ttf"))
FONT_HEAD = next(ROOT.glob("03-assets/fonts/**/Montserrat-ExtraBold.ttf"))
FONT_HEAD_BOLD = next(ROOT.glob("03-assets/fonts/**/Montserrat-Bold.ttf"))
FONT_HEAD_SEMI = next(ROOT.glob("03-assets/fonts/**/Montserrat-SemiBold.ttf"))
FONT_BODY = next(ROOT.glob("03-assets/fonts/**/OpenSans-Regular.ttf"))
FONT_BODY_SEMI = next(ROOT.glob("03-assets/fonts/**/OpenSans-SemiBold.ttf"))
LOGO_DIR = ROOT / "03-assets/logos/mother"

DEEP_GREEN = "#001A17"
MINT_WHITE = "#F4F9F8"
TINT_LIGHT = "#EDF2F1"  # 3% de Deep Green dans Mint White
TINT_DARK  = "#07211E"  # 3% de Mint White dans Deep Green
YELLOW = "#FFC107"
ORANGE = "#FF7043"


# ============================================================
# Branches
# ============================================================
BRANCHES = {
    "design-touch": {
        "slug": "design-touch",
        "name": "LNK DESIGN TOUCH",
        "manifesto": "Créativité",
        "subtitle": "Design · Branding · Motion · Impression",
        "color": "#00A896",
        "color_light": "#00D9BE",
        "accent": "#00A896",
        "logo": "lnk-horizontal-design-touch-light.svg",
    },
    "dev": {
        "slug": "dev",
        "name": "LNK DEV",
        "manifesto": "Code",
        "subtitle": "Développement · Produits numériques",
        "color": "#2D6FBF",
        "color_light": "#5BA8E0",
        "accent": "#2D6FBF",
        "logo": "lnk-horizontal-dev-light.svg",
    },
    "print": {
        "slug": "print",
        "name": "LNK PRINT",
        "manifesto": "Impression",
        "subtitle": "Impression · Supports physiques",
        "color": "#C76A1F",
        "color_light": "#F0913D",
        "accent": "#C76A1F",
        "logo": "lnk-horizontal-print-light.svg",
    },
    "play": {
        "slug": "play",
        "name": "LNK PLAY",
        "manifesto": "Jeu",
        "subtitle": "Gaming · Expériences interactives",
        "color": "#8E4FB5",
        "color_light": "#B87BE0",
        "accent": "#8E4FB5",
        "logo": "lnk-horizontal-play-light.svg",
    },
    "cine": {
        "slug": "cine",
        "name": "LNK CINÉ",
        "manifesto": "Cinéma",
        "subtitle": "Cinéma · Audiovisuel",
        "color": "#C13A3C",
        "color_light": "#E85A5B",
        "accent": "#C13A3C",
        "logo": "lnk-horizontal-cine-light.svg",
    },
}


# ============================================================
# Motif Louis Vuitton (V3-medium-5 validé)
# ============================================================
import re as _re
_VERTEX_PATHS = None
_VERTEX_VB = None
_SYMBOL_PATHS = None
_SYMBOL_VB = None

# ============================================================
# Helpers accents + contraste (WCAG)
# ============================================================
def _relative_luminance(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = [int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4)]
    def f(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contrast_ratio(fg, bg):
    L1 = _relative_luminance(fg)
    L2 = _relative_luminance(bg)
    Lmax, Lmin = max(L1, L2), min(L1, L2)
    return (Lmax + 0.05) / (Lmin + 0.05)


def cta_text_on(accent_hex):
    c_deep = _contrast_ratio(DEEP_GREEN, accent_hex)
    c_mint = _contrast_ratio(MINT_WHITE, accent_hex)
    return DEEP_GREEN if c_deep >= c_mint else MINT_WHITE


def get_brand_accent(mode, branch):
    """Accent unique par mode :
    - Studio : ORANGE (light) / YELLOW (dark)
    - Branche : color (base, light) / color_light (clair, dark)
    """
    if branch is None:
        return ORANGE if mode == 'light' else YELLOW
    return branch["color"] if mode == 'light' else branch["color_light"]


def _load_vertex():
    global _VERTEX_PATHS, _VERTEX_VB
    if _VERTEX_PATHS is not None:
        return _VERTEX_PATHS, _VERTEX_VB
    src = ROOT / "03-assets/logos/original/vertex.svg"
    content = src.read_text()
    vb = _re.search(r'viewBox="([^"]+)"', content).group(1)
    paths = _re.findall(r'<path[^>]*/>', content)
    _VERTEX_PATHS = paths
    _VERTEX_VB = vb
    return paths, vb

def _load_symbol():
    global _SYMBOL_PATHS, _SYMBOL_VB
    if _SYMBOL_PATHS is not None:
        return _SYMBOL_PATHS, _SYMBOL_VB
    src = ROOT / "03-assets/logos/original/symbol.svg"
    content = src.read_text()
    vb = _re.search(r'viewBox="([^"]+)"', content).group(1)
    paths = _re.findall(r'<path[^>]*/>', content)
    _SYMBOL_PATHS = paths
    _SYMBOL_VB = vb
    return paths, vb


_SPARK_CACHE = {}
def _load_spark(variant="geometric"):
    """Retourne (shape_xml, bbox) pour le spark demande.
    variant = 'geometric' (polygon net) ou 'curved' (courbes Bezier)
    bbox = (x_min, y_min, x_max, y_max) extrait a la main.
    """
    if variant in _SPARK_CACHE:
        return _SPARK_CACHE[variant]
    fname = f"spark-{variant}.svg"
    src = ROOT / "03-assets/logos/original" / fname
    content = src.read_text()
    if variant == "geometric":
        # polygon points="130,25 65,110 105,110 70,175 135,90 95,90"
        m = _re.search(r'<polygon points="([^"]+)"[^>]*/>', content)
        if not m:
            raise ValueError(f"Polygon introuvable dans {fname}")
        pts = m.group(1)
        shape = f'<polygon points="{pts}" fill="currentColor"/>'
        bbox = (65.0, 25.0, 135.0, 175.0)  # xmin, ymin, xmax, ymax
    elif variant == "curved":
        m = _re.search(r'<path d="([^"]+)"[^>]*/>', content)
        if not m:
            raise ValueError(f"Path introuvable dans {fname}")
        d = m.group(1)
        shape = f'<path d="{d}" fill="currentColor"/>'
        bbox = (65.0, 25.0, 135.0, 175.0)
    else:
        raise ValueError(f"Spark inconnu : {variant}")
    _SPARK_CACHE[variant] = (shape, bbox)
    return shape, bbox


# ============================================================
# Motifs signature (1 par marque, 6 au total)
# ============================================================
def _spark_place(shape_xml, bbox, cx, cy, size, rotation, color, opacity):
    """Place un spark (eclair) centre a (cx, cy), taille `size` (hauteur),
    rotation `rotation` degres, couleur, opacite."""
    xmin, ymin, xmax, ymax = bbox
    w = xmax - xmin
    h = ymax - ymin
    scale = size / h
    # Point central du spark dans son viewBox
    scx = (xmin + xmax) / 2
    scy = (ymin + ymax) / 2
    # Translation : on centre le spark sur (cx, cy)
    tx = cx - scx * scale
    ty = cy - scy * scale
    return (
        f'<g transform="translate({cx:.2f} {cy:.2f}) rotate({rotation}) '
        f'translate({-cx:.2f} {-cy:.2f}) translate({tx:.4f} {ty:.4f}) '
        f'scale({scale:.4f})" fill="{color}" opacity="{opacity}">{shape_xml}</g>'
    )


# ============================================================================
# VERTEX MONUMENTAL — remplace build_vertex_pattern
# ============================================================================
# Règles validées (2026-11-10) :
#   Formats ratio <= 1.5 (carré, portrait, story) :
#     - 75% de H, base au bord bas, bord gauche à 60% du canvas
#   Formats ratio > 1.5 (horizontal) :
#     - 100% de H, base au bord bas, débordement à droite 50% -> 25%
#       (formule : pct = 0.50 - (min(ratio,5)-1.5)/3.5 * 0.25)
#   Couleur solide (TINT_LIGHT / TINT_DARK), pas d'opacité, pas de fade.

_VERTEX_BOUNDS = {
    "left":   -15.56,
    "right":   465.56,
    "top":    -2021.00,
    "bottom": -1123.21,
}


def motif_vertex_monumental(W, H, mode):
    """Vertex monumental (cercle + triangle) sur fond neutre solide."""
    color = TINT_DARK if mode == "dark" else TINT_LIGHT
    paths, _vb = _load_vertex()

    bl = _VERTEX_BOUNDS["left"]
    br = _VERTEX_BOUNDS["right"]
    bt = _VERTEX_BOUNDS["top"]
    bb = _VERTEX_BOUNDS["bottom"]
    shape_w = br - bl
    shape_h = bb - bt
    shape_ratio = shape_w / shape_h

    ratio = W / H

    if ratio <= 1.5:
        target_h = H * 0.75
        target_w = target_h * shape_ratio
        target_x = W * 0.60
        target_y = H - target_h
    else:
        target_h = H * 1.00
        target_w = target_h * shape_ratio
        pct = 0.50 - (min(ratio, 5.0) - 1.5) / 3.5 * 0.25
        target_x = W - target_w * (1 - pct)
        if target_x < 0:
            target_x = 0
        target_y = H - target_h

    paths_ro = "".join(
        _re.sub(r'fill="[^"]*"', f'fill="{color}"', p) for p in paths
    )
    inner = (
        f'<svg x="{target_x:.2f}" y="{target_y:.2f}" '
        f'width="{target_w:.2f}" height="{target_h:.2f}" '
        f'viewBox="{bl} {bt} {shape_w} {shape_h}" '
        f'preserveAspectRatio="none" overflow="visible">'
        f'{paths_ro}'
        f'</svg>'
    )
    return "", inner


# ============================================================================
# MOTIFS SIGNATURE — 1 élément + 1 logique de disposition par marque
# ============================================================================
# Sources : 03-assets/logos/original/{vertex,cercle,triangle,carre,spark}.svg
# Contrainte : chaque motif est LOCALISE (jamais en revêtement du canvas).
# ~40% du canvas max, toujours dans la moitié droite (texte reste à gauche).

ELEMENT_FILES = {
    "vertex":   "vertex.svg",
    "cercle":   "cercle.svg",
    "triangle": "triangle.svg",
    "carre":    "carre.svg",
    "spark":    "spark.svg",
}
_element_cache = {}


# Filtre de tags par élément (spark a un rect de fond à ignorer,
# carre EST un rect, vertex/cercle/triangle sont des paths)
_ELEMENT_TAGS = {
    "vertex":   ["path"],
    "cercle":   ["path"],
    "triangle": ["path"],
    "carre":    ["rect"],
    "spark":    ["polygon"],
}


def _load_element(name):
    """Charge un élément SVG source, retourne (paths, viewBox)."""
    if name in _element_cache:
        return _element_cache[name]
    svg_dir = ROOT / "03-assets/logos/original"
    src = (svg_dir / ELEMENT_FILES[name]).read_text()
    m = re.search(r'viewBox="([^"]+)"', src)
    vb = tuple(float(x) for x in m.group(1).split())
    tags = _ELEMENT_TAGS.get(name, ["path"])
    paths = []
    for tag in tags:
        paths.extend(re.findall(rf'<{tag}[^>]*?/>', src))
    _element_cache[name] = (paths, vb)
    return paths, vb


def _recolor(paths, color):
    """Force fill=color sur tous. Si un stroke existe, on le recolore aussi
    (même couleur que le fill) pour préserver l'arrondi des pointes (spark)."""
    res = []
    for p in paths:
        p = re.sub(r'fill="[^"]*"', f'fill="{color}"', p)
        if 'stroke="' in p:
            p = re.sub(r'stroke="[^"]*"', f'stroke="{color}"', p)
        res.append(p)
    return res


def _place_element(name, cx, cy, size, rotation, opacity, color):
    """Place un élément (recoloré) à (cx, cy) avec rotation et opacité."""
    paths, vb = _load_element(name)
    vx, vy, vw, vh = vb
    sc = size / vh
    tx = cx - (vx + vw/2) * sc
    ty = cy - (vy + vh/2) * sc
    inner = "".join(_recolor(paths, color))
    return (
        f'<g transform="translate({cx:.2f} {cy:.2f}) rotate({rotation:.2f}) '
        f'translate({-cx:.2f} {-cy:.2f}) translate({tx:.4f} {ty:.4f}) '
        f'scale({sc:.6f})" opacity="{opacity:.3f}">{inner}</g>'
    )


def _hash(seed, i):
    """Pseudo-random déterministe (0..1) — même seed = même motif."""
    return ((seed * 7919 + i * 104729) % 10000) / 10000.0


# ---- MOTIF 1 : STUDIO — Constellation ---------------------------------------
def motif_studio(W, H, mode):
    """Constellation : vertex sur grille 3x4 espacée, quadrant droit.
    Jitter léger pour l'organique. Fade horizontal 0->0.15."""
    color = MINT_WHITE if mode == "dark" else DEEP_GREEN
    parts = []
    x_limit = W * 0.60
    zone_w = W - x_limit
    zone_h = H * 0.90
    y0 = H * 0.05
    cols, rows = 3, 4
    cell_w = zone_w / cols
    cell_h = zone_h / rows
    sizes = [50, 70, 90, 110, 130]
    idx = 0
    for r in range(rows):
        for c in range(cols):
            # Jitter déterministe (±15% de la cellule)
            jx = (_hash(11, idx) - 0.5) * cell_w * 0.30
            jy = (_hash(17, idx) - 0.5) * cell_h * 0.30
            cx = x_limit + (c + 0.5) * cell_w + jx
            cy = y0 + (r + 0.5) * cell_h + jy
            size = sizes[idx % len(sizes)]
            rot = _hash(23, idx) * 60 - 30
            progress = (cx - x_limit) / zone_w
            opacity = progress * 0.15
            if opacity >= 0.01:
                parts.append(_place_element("vertex", cx, cy, size, rot, opacity, color))
            idx += 1
    return "", "".join(parts)


def motif_dt(W, H, mode):
    """Spark : un seul éclair très grand (75% hauteur canvas), sans rotation, transparent."""
    color = MINT_WHITE if mode == "dark" else DEEP_GREEN

    cx = W * 0.80
    cy = H * 0.50
    size = H * 1.00        # 100% de la hauteur du canvas
    rot = 0                # droit, pas de rotation
    opacity = 0.05

    parts = [_place_element("spark", cx, cy, size, rot, opacity, color)]
    return "", "".join(parts)


def motif_dev(W, H, mode):
    """Grille de petits carrés ancrée au bord DROIT.
    - 60% du canvas à gauche = totalement vide
    - Motif sur les 40% de droite
    - Fade atteint 0 à x = W*0.60 (= 40% depuis la droite)
    """
    color = MINT_WHITE if mode == "dark" else DEEP_GREEN
    parts = []

    cell = 28
    gap = cell * 2
    step = cell + gap

    # 60% vide à gauche, motif sur les 40% de droite
    x_limit = W * 0.60

    cols = int((W - x_limit) / step) + 2
    rows = int(H / step) + 2

    total_h = rows * step - gap
    y_start = (H - total_h) / 2

    for r in range(rows):
        for c in range(cols):
            cx = W - c * step - cell / 2
            if cx < x_limit:
                break

            progress = (cx - x_limit) / (W - x_limit)
            opacity = progress * 0.15
            if opacity < 0.01:
                continue

            cy = y_start + r * step + cell / 2
            parts.append(_place_element("carre", cx, cy, cell, 0, opacity, color))

    return "", "".join(parts)


def motif_print(W, H, mode):
    """Trame : triangles en quinconce, fondu depuis la droite. 60% gauche = vide."""
    color = MINT_WHITE if mode == "dark" else DEEP_GREEN
    parts = []
    x_limit = W * 0.60
    cell = 26
    gap = cell * 2
    step = cell + gap
    cols = int((W - x_limit) / step) + 2
    rows = int(H / step) + 2
    total_h = rows * step - gap
    y_start = (H - total_h) / 2
    for r in range(rows):
        offset = (step / 2) if r % 2 else 0
        for c in range(cols):
            cx = W - c * step - cell / 2 - offset
            if cx < x_limit:
                break
            progress = (cx - x_limit) / (W - x_limit)
            opacity = progress * 0.15
            if opacity < 0.01:
                continue
            cy = y_start + r * step + cell / 2
            parts.append(_place_element("triangle", cx, cy, cell, 0, opacity, color))
    return "", "".join(parts)


def motif_play(W, H, mode):
    """Éclats : cercles + triangles sur grille 3x3 espacée, quadrant droit.
    Jitter léger + rotations libres. Fade horizontal 0->0.15."""
    color = MINT_WHITE if mode == "dark" else DEEP_GREEN
    parts = []
    x_limit = W * 0.60
    zone_w = W - x_limit
    zone_h = H * 0.90
    y0 = H * 0.05
    cols, rows = 3, 3
    cell_w = zone_w / cols
    cell_h = zone_h / rows
    idx = 0
    for r in range(rows):
        for c in range(cols):
            jx = (_hash(71, idx) - 0.5) * cell_w * 0.25
            jy = (_hash(73, idx) - 0.5) * cell_h * 0.25
            cx = x_limit + (c + 0.5) * cell_w + jx
            cy = y0 + (r + 0.5) * cell_h + jy
            size = 70 + _hash(79, idx) * 50
            rot = _hash(83, idx) * 360
            progress = (cx - x_limit) / zone_w
            opacity = progress * 0.15
            if opacity >= 0.01:
                elem = "cercle" if idx % 2 == 0 else "triangle"
                parts.append(_place_element(elem, cx, cy, size, rot, opacity, color))
            idx += 1
    return "", "".join(parts)


def motif_cine(W, H, mode):
    """Concentrique : cercles depuis un focus bas-droite (92%, 70%)."""
    color = MINT_WHITE if mode == "dark" else DEEP_GREEN
    parts = []
    cx = W * 0.92
    cy = H * 0.70
    for i, size in enumerate([100, 200, 320, 460, 620, 800]):
        opacity = 0.15 * (1 - i / 7)
        if opacity < 0.01:
            break
        parts.append(_place_element("cercle", cx, cy, size, 0, opacity, color))
    return "", "".join(parts)


MOTIF_DISPATCHER = {
    "mother":       motif_studio,
    "studio":       motif_studio,
    "design-touch": motif_dt,
    "dt":           motif_dt,
    "dev":          motif_dev,
    "print":        motif_print,
    "play":         motif_play,
    "cine":         motif_cine,
}


def build_signature_motif(W, H, mode, branch_slug):
    """Dispatcher : retourne (defs, body) selon la branche."""
    fn = MOTIF_DISPATCHER.get(branch_slug, motif_studio)
    return fn(W, H, mode)


def build_vertex_pattern(W, H, mode, variant="A"):
    """
    Motif de fond avec le vertex LNK répété.
    
    Variantes disponibles (chaque option a un usage type) :
    
    - "A" : Grille en coin supérieur droit avec masque radial.
             Le motif s'estompe vers le centre. Subtil, présent sans envahir.
             Usage type : T1 Citation, posts éditoriaux.
    
    - "B" : Bande bas de 260px avec fade vertical.
             Le motif ancre le bas du canvas. Contenu domine le haut.
             Usage type : T2 Annonce, posts avec zone visuelle.
    
    - "C" : Un seul vertex géant (500px) ancré en bas-droite, opacité 8%.
             Ultra sobre. Signature discrète.
             Usage type : T1 Citation sur dark, posts premium.
    
    - "D" : Grille en coin supérieur droit dans un cercle masque (380px de rayon).
             Effet "loupe" sur le motif, plus concentré.
             Usage type : T3 Story, formats verticaux longs.
    
    Paramètres :
    - W, H    : dimensions du canvas
    - mode    : "light" (fond Mint White) ou "dark" (fond Deep Green)
    - variant : "A" | "B" | "C" | "D"
    
    Retourne : contenu SVG (défs + body) à injecter dans le template.
    """
    paths_raw, _vb = _load_vertex()
    color = MINT_WHITE if mode == "dark" else DEEP_GREEN
    paths = [_re.sub(r'fill="[^"]*"', f'fill="{color}"', p) for p in paths_raw]
    vb_x, vb_y, vb_w, vb_h = -15.56, -2021, 481, 898

    def make_grid(cell_size, vertex_ratio, rotate, opacity):
        vw = cell_size * vertex_ratio
        sc = vw / vb_w
        rows = int(H / cell_size) + 2
        cols = int(W / cell_size) + 2
        g = ""
        for r in range(rows):
            for c in range(cols):
                x = c * cell_size + (cell_size / 2 if r % 2 == 1 else 0)
                y = r * cell_size - cell_size / 2
                cx = x + cell_size / 2
                cy = y + cell_size / 2
                g += f'<g transform="translate({cx:.1f} {cy:.1f}) rotate({rotate}) scale({sc:.4f}) translate({-vb_x - vb_w/2:.2f} {-vb_y - vb_h/2:.2f})" opacity="{opacity}">{"".join(paths)}</g>'
        return g

    if variant == "none":
        # Pas de motif : retourner vide
        return "", ""

    if variant == "A":
        # Coin sup. droit, masque radial
        pattern = make_grid(cell_size=180, vertex_ratio=0.40, rotate=-30, opacity=0.08)
        defs = (
            f'<radialGradient id="motif-mask-A" cx="1" cy="0" r="0.7" gradientUnits="objectBoundingBox">'
            f'<stop offset="0%" stop-color="white" stop-opacity="1"/>'
            f'<stop offset="60%" stop-color="white" stop-opacity="0.3"/>'
            f'<stop offset="100%" stop-color="white" stop-opacity="0"/>'
            f'</radialGradient>'
            f'<mask id="mask-A"><rect width="{W}" height="{H}" fill="url(#motif-mask-A)"/></mask>'
        )
        body = f'<g mask="url(#mask-A)">{pattern}</g>'
        return defs, body

    elif variant == "B":
        # Bande bas proportionnelle à la hauteur (260px pour 1080px, ~325px pour 1350, ~460px pour 1920)
        band_h = int(H * 0.24)
        pattern = make_grid(cell_size=160, vertex_ratio=0.40, rotate=-30, opacity=0.10)
        defs = (
            f'<linearGradient id="motif-mask-B" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="{1 - band_h/H:.3f}" stop-color="white" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="white" stop-opacity="1"/>'
            f'</linearGradient>'
            f'<mask id="mask-B"><rect width="{W}" height="{H}" fill="url(#motif-mask-B)"/></mask>'
        )
        body = f'<g mask="url(#mask-B)">{pattern}</g>'
        return defs, body

    elif variant == "C":
        # Vertex géant ancré bas-droite
        # Le bas du vertex descend de 20% SOUS le cadre (donc 20% du vertex disparaît)
        # → 80% du vertex reste visible, tous formats confondus
        VERTEX_HEIGHT = 500
        BELOW_RATIO = 0.20      # 20% du vertex sous le cadre
        below = VERTEX_HEIGHT * BELOW_RATIO   # 100px sous le cadre
        s_scale = VERTEX_HEIGHT / vb_h
        w_scaled = vb_w * s_scale
        x = W - w_scaled + 100
        y = H - (VERTEX_HEIGHT - below)       # top = H - 400, bottom = H + 100
        body = (
            f'<g transform="translate({x:.1f} {y:.1f}) scale({s_scale:.4f}) '
            f'translate({-vb_x:.2f} {-vb_y:.2f})" opacity="0.08">{"".join(paths)}</g>'
        )
        return "", body

    elif variant == "D":
        # Cercle masque en coin sup. DROIT (fix userSpaceOnUse)
        pattern = make_grid(cell_size=140, vertex_ratio=0.40, rotate=-30, opacity=0.10)
        cx, cy, r = W - 50, 50, 380
        defs = (
            f'<radialGradient id="motif-mask-D" gradientUnits="userSpaceOnUse" '
            f'cx="{cx}" cy="{cy}" r="{r}">'
            f'<stop offset="0%" stop-color="white" stop-opacity="1"/>'
            f'<stop offset="70%" stop-color="white" stop-opacity="0.5"/>'
            f'<stop offset="100%" stop-color="white" stop-opacity="0"/>'
            f'</radialGradient>'
            f'<mask id="mask-D" maskUnits="userSpaceOnUse">'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#motif-mask-D)"/>'
            f'</mask>'
        )
        body = f'<g mask="url(#mask-D)">{pattern}</g>'
        return defs, body

    elif variant == "E":
        # Motif visible à DROITE, invisible à GAUCHE
        # Gradient horizontal (0% = bord gauche, 100% = bord droit) :
        #   - 0-60% depuis la gauche : totalement invisible (stop-opacity 0)
        #   - 60-100% depuis la gauche : fade progressif vers visible
        #   - bord droit : pleinement visible (opacity 1)
        # = fade zone de 40% depuis la droite
        pattern = make_grid(cell_size=180, vertex_ratio=0.40, rotate=-30, opacity=0.10)
        defs = (
            f'<linearGradient id="motif-mask-E" x1="0%" y1="0%" x2="100%" y2="0%">'
            f'<stop offset="0%" stop-color="white" stop-opacity="0"/>'
            f'<stop offset="60%" stop-color="white" stop-opacity="0"/>'
            f'<stop offset="80%" stop-color="white" stop-opacity="0.5"/>'
            f'<stop offset="100%" stop-color="white" stop-opacity="1"/>'
            f'</linearGradient>'
            f'<mask id="mask-E"><rect width="{W}" height="{H}" fill="url(#motif-mask-E)"/></mask>'
        )
        body = f'<g mask="url(#mask-E)">{pattern}</g>'
        return defs, body

    else:
        # Fallback : variant inconnue → pas de motif
        return "", ""


_fc = {}
def _font(path):
    if path not in _fc: _fc[path] = TTFont(str(path))
    return _fc[path]

_cap_h_cache = {}
def get_cap_height_H(font_path):
    """Hauteur cap du H (font units), cache. Référence uniforme pour titres."""
    if font_path in _cap_h_cache:
        return _cap_h_cache[font_path]
    f = _font(font_path)
    cmap = f.getBestCmap()
    gn = cmap.get(ord('H'))
    if not gn:
        _cap_h_cache[font_path] = 700.0
        return 700.0
    bp = BoundsPen(f.getGlyphSet())
    f.getGlyphSet()[gn].draw(bp)
    result = bp.bounds[3] if bp.bounds else 700.0
    _cap_h_cache[font_path] = result
    return result


def build_text_grid(text, font_path, H_px, color, tracking=0.0):
    """
    Construit un texte ancre sur la grille typographique H (cap height).

    Retourne un dict :
      - 'svg'          : <g> avec cap line a y=0 et baseline a y=H_px
      - 'width'        : largeur du texte en px
      - 'H_px'         : hauteur cap (reference)
      - 'ascender_px'  : debordement au-dessus de la cap line (accents, points)
      - 'descender_px' : debordement sous la baseline (g, p, y)
      - 'bbox_top'     : min y (peut etre negatif si ascender)
      - 'bbox_bottom'  : max y (peut etre > H_px si descender)
      - 'bbox_height'  : ascender_px + H_px + descender_px
    """
    f = _font(font_path)
    cmap = f.getBestCmap()
    gs = f.getGlyphSet()
    hmtx = f['hmtx']
    upm = f['head'].unitsPerEm
    track = upm * tracking

    cap_H = get_cap_height_H(font_path)  # font units
    scale = H_px / cap_H  # font units -> px

    kern = f.get('kern')
    kl = {}
    if kern:
        for t in kern.kernTables:
            try: kl.update(t.kernTable)
            except: pass

    x = 0
    parts = []
    prev = None
    xmin = 1e18
    xmax = -1e18
    ymin_font = 1e18
    ymax_font = -1e18

    for ch in text:
        gn = cmap.get(ord(ch))
        if not gn:
            prev = ch
            continue
        if prev is not None:
            x += kl.get((prev, ch), 0)

        pen = SVGPathPen(gs)
        gs[gn].draw(TransformPen(pen, Transform().translate(x, 0)))
        if pen.getCommands().strip():
            parts.append(pen.getCommands())

        bp = BoundsPen(gs)
        gs[gn].draw(TransformPen(bp, Transform().translate(x, 0)))
        if bp.bounds:
            xmin = min(xmin, bp.bounds[0])
            xmax = max(xmax, bp.bounds[2])
            ymin_font = min(ymin_font, bp.bounds[1])
            ymax_font = max(ymax_font, bp.bounds[3])

        x += hmtx[gn][0] + track
        prev = ch

    raw = " ".join(parts)
    if not raw:
        return None

    # Debordements en px
    ascender_px = max(0.0, (ymax_font - cap_H) * scale)
    descender_px = max(0.0, -ymin_font * scale)

    # Matrice : cap line a y=0, baseline a y=H_px
    # y_svg = cap_H * scale - y_font * scale = H_px - y_font * scale
    # (donc cap line -> 0, baseline -> H_px)
    # Extrait le nom de la font (dernier segment du path)
    font_name = font_path.stem if hasattr(font_path, "stem") else str(font_path).split("/")[-1].replace(".ttf", "")
    # Note : attributs data-plp-* pour le converter Python (psd2plp).
    # Ignorés par rsvg-convert et les navigateurs, lus uniquement par
    # tools/brand-to-plp/converter.
    txt_escaped = (text.replace("&", "&amp;").replace("<", "&lt;")
                       .replace(">", "&gt;").replace('"', "&quot;"))
    g = (
        f'<g transform="matrix({scale:.6f} 0 0 {-scale:.6f} '
        f'{-xmin*scale:.4f} {H_px:.4f})" fill="{color}" '
        f'data-plp-text="{txt_escaped}" '
        f'data-plp-size="{H_px:.2f}" '
        f'data-plp-color="{color}" '
        f'data-plp-font="{font_name}" '
        f'data-plp-tracking="{tracking}">'
        f'<path d="{raw}"/></g>'
    )

    # advance = position finale du curseur (inclut l'espace final)
    # On retire le tracking du dernier char s'il y en a
    advance_raw = x - track if track != 0 else x
    return {
        'svg': g,
        'width': (xmax - xmin) * scale,
        'advance': advance_raw * scale,
        'H_px': H_px,
        'ascender_px': ascender_px,
        'descender_px': descender_px,
        'bbox_top': -ascender_px,
        'bbox_bottom': H_px + descender_px,
        'bbox_height': ascender_px + H_px + descender_px,
    }


def build_text(text, font_path, target_h, color, tracking=0.0, use_cap_h=False):
    """Wrapper de compatibilité : appelle build_text_grid en interne.
    Retourne (svg, width, H_px, bbox_top) pour rester compatible avec
    l'ancienne signature utilisée par les templates (eyebrow, subtitle, CTA).
    """
    r = build_text_grid(text, font_path, target_h, color, tracking=tracking)
    if r is None:
        return "", 0, 0, 0
    return r['svg'], r['width'], r['H_px'], r['bbox_top']


def fit_text_grid(text, font_path, H_start, max_width, tracking=0.0):
    """Ajuste H_px pour que le texte tienne dans max_width. Retourne le dict."""
    H = H_start
    for _ in range(25):
        r = build_text_grid(text, font_path, H, "#000", tracking=tracking)
        if r is None:
            return None
        if r['width'] <= max_width:
            return build_text_grid(text, font_path, H, "#000", tracking=tracking)
        H *= 0.93
    return build_text_grid(text, font_path, H, "#000", tracking=tracking)



def resolve_logo_path(name, branch_slug=None):
    """Retourne le Path absolu du logo, selon le nom et la branche."""
    if branch_slug:
        p = ROOT / "03-assets/logos/sub-brands" / branch_slug / "02-horizontal" / name
    else:
        if name.startswith("lnk-horizontal"):
            p = LOGO_DIR / "02-horizontal" / name
        elif name.startswith("02-horizontal/"):
            p = LOGO_DIR / name
        else:
            p = LOGO_DIR / name
    return p


def read_logo(name, branch=None):
    if branch:
        p = ROOT / "03-assets/logos/sub-brands" / branch / "02-horizontal" / name
    else:
        # Mère : les logos horizontaux sont dans 02-horizontal/
        if name.startswith("lnk-horizontal"):
            p = LOGO_DIR / "02-horizontal" / name
        else:
            p = LOGO_DIR / name
    if not p.exists(): return None, None
    content = p.read_text().replace('<?xml version="1.0" encoding="UTF-8"?>', '').strip()
    import re
    vb = re.search(r'viewBox="([^"]+)"', content)
    inner_match = re.search(r'<svg[^>]*>(.*)</svg>', content, re.DOTALL)
    if not vb or not inner_match: return None, None
    return inner_match.group(1), vb.group(1)

_logo_png_cache = {}
def read_logo_as_png_base64(svg_path, width=800):
    """Convertit un SVG logo en PNG base64 (cache par chemin + largeur).
    Bypass le probleme rsvg-convert avec 3+ niveaux de g transform imbriques."""
    import subprocess, base64
    key = (str(svg_path), width)
    if key in _logo_png_cache:
        return _logo_png_cache[key]
    if not svg_path.exists():
        return None
    result = subprocess.run(
        ["rsvg-convert", "-w", str(width), str(svg_path)],
        capture_output=True, check=True
    )
    b64 = base64.b64encode(result.stdout).decode('ascii')
    _logo_png_cache[key] = b64
    return b64


def place_logo(svg_inner, vb, x, y, width, height, svg_path=None):
    """Place un logo en <image href="data:image/png;base64,..."/>.
    La HAUTEUR est la référence unique. La largeur est calculée depuis le ratio.
    Cela garantit que le mot 'lnk' a la même hauteur partout (Studio = DT),
    même si DT est plus large (design touch = plus de caractères).
    `width` est ignoré (gardé pour compatibilité de signature)."""
    if not svg_inner: return ""
    if svg_path and svg_path.exists():
        b64 = read_logo_as_png_base64(svg_path, width=800)
        if b64:
            parts = [float(v) for v in vb.split()]
            vb_w, vb_h = parts[2], parts[3]
            ratio = vb_w / vb_h
            actual_h = height  # hauteur fixe, source de vérité
            actual_w = actual_h * ratio
            return f'<image x="{x:.2f}" y="{y:.2f}" width="{actual_w:.2f}" height="{actual_h:.2f}" href="data:image/png;base64,{b64}" preserveAspectRatio="xMinYMid meet"/>'
    # Fallback (g transform)
    parts = [float(v) for v in vb.split()]
    vb_x, vb_y, vb_w, vb_h = parts
    scale = height / vb_h
    tx = x - vb_x * scale
    ty = y - vb_y * scale
    return f'<g transform="translate({tx:.4f} {ty:.4f}) scale({scale:.6f})">{svg_inner}</g>'

def measure_word(text, font_path, target_h, tracking=0):
    """Retourne (svg_group, width, height, ymin)."""
    return build_text(text, font_path, target_h, "#000", tracking)

def fit_text(text, font_path, max_width, max_height, tracking=0):
    """Trouve la taille optimale pour que text tienne dans max_width x max_height."""
    # Mesure à taille 100 pour ratio
    _, w100, _, _ = build_text(text, font_path, 100, "#000", tracking)
    if w100 == 0: return 100
    # Taille limitée par largeur
    size_by_width = (max_width / w100) * 100
    # Taille limitée par hauteur
    size_by_height = max_height
    return min(size_by_width, size_by_height)

def wrap(w, h, content, bg, defs=""):
    defs_block = f"<defs>{defs}</defs>" if defs else ""
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">{defs_block}<rect width="{w}" height="{h}" fill="{bg}"/>{content}</svg>\n'

# ============================================================
# T1 — Citation (1080x1080)
# ============================================================
def template_citation(mode, branch=None, variant="A"):
    W, H = 1080, 1080
    PAD = 80
    accent = get_brand_accent(mode, branch)
    if mode == 'light':
        bg = MINT_WHITE
        text_color = DEEP_GREEN
        eyebrow_color = DEEP_GREEN
        logo_file = "lnk-horizontal-light.svg" if not branch else branch["logo"]
    else:
        bg = DEEP_GREEN
        text_color = MINT_WHITE
        eyebrow_color = MINT_WHITE
        logo_file = "lnk-horizontal-dark.svg" if not branch else branch["logo"].replace("-light", "-dark")

    max_text_w = W - 2 * PAD
    font = FONT_HEAD

    # Lignes multi-couleur (grille H)
    lines_segments = [
        [("Votre ", text_color), ("idée", accent)],
        [("Notre ", text_color), ("créativité", accent)],
        [("Votre ", text_color), ("succès", accent)],
    ]

    def measure_line_width(segments, H_val):
        total = 0
        for txt, _c in segments:
            r = build_text_grid(txt, font, H_val, "#000")
            if r: total += r['advance']
        return total

    H_target = 130
    for _ in range(25):
        max_w = max(measure_line_width(seg, H_target) for seg in lines_segments)
        if max_w <= max_text_w:
            break
        H_target *= 0.92

    rendered_lines = []
    for segments in lines_segments:
        parts = []
        x_off = 0
        _max_desc = 0.0
        _max_asc = 0.0
        for txt, color in segments:
            r = build_text_grid(txt, font, H_target, color)
            if r:
                parts.append((r['svg'], r['width'], x_off))
                x_off += r['advance']  # advance inclut l'espace final
                _max_desc = max(_max_desc, r['descender_px'])
                _max_asc = max(_max_asc, r['ascender_px'])
        rendered_lines.append({'parts': parts, 'width': x_off, 'descender': _max_desc, 'ascender': _max_asc})

    # Grille verticale
    LINE_HEIGHT = H_target * 1.30  # interligne fixe = 30% du H
    PAD_SAFETY = H_target * 0.30
    MIN_GAP = 0  # pas de poussee dynamique (test)
    step = LINE_HEIGHT
    for _i in range(1, len(rendered_lines)):
        _needed = H_target + rendered_lines[_i-1]['descender'] + rendered_lines[_i]['ascender'] + MIN_GAP
        step = max(step, _needed)

    eyebrow_text = f"{branch['name']} · MANIFESTO" if branch else "LNK STUDIO · MANIFESTO"
    eyebrow, _, _, _ = build_text(eyebrow_text, FONT_HEAD_SEMI, 22, eyebrow_color, tracking=0.12)
    subtitle, _, _, _ = build_text("Design · Branding · Motion · Impression", FONT_BODY, 28, text_color)

    # Logo en bas
    logo_inner, logo_vb = read_logo(logo_file, branch=branch["slug"] if branch else None)
    logo_h = 130
    _vb_parts = [float(v) for v in logo_vb.split()]
    _vb_w, _vb_h = _vb_parts[2], _vb_parts[3]
    logo_w = logo_h * (_vb_w / _vb_h)
    logo_x = PAD
    logo_y = H - PAD - logo_h
    logo_path = resolve_logo_path(logo_file, branch['slug'] if branch else None)
    logo_svg = place_logo(logo_inner, logo_vb, logo_x, logo_y, logo_w, logo_h, svg_path=logo_path)

    # Positions verticales (grille H)
    y_eyebrow = PAD
    y_cap_1 = y_eyebrow + 110 + PAD_SAFETY
    y_caps = [y_cap_1]
    for _i in range(len(rendered_lines) - 1):
        y_caps.append(y_caps[-1] + step)
    y_baseline_last = y_caps[-1] + H_target
    y_sub = y_baseline_last + PAD_SAFETY + 30

    g = f'<g transform="translate({PAD} {y_eyebrow})">{eyebrow}</g>'
    for _line, y_cap in zip(rendered_lines, y_caps):
        for seg_g, w, x_off in _line['parts']:
            g += f'<g transform="translate({PAD + x_off} {y_cap})">{seg_g}</g>'
    g += f'<g transform="translate({PAD} {y_sub})">{subtitle}</g>'
    g += logo_svg

    # Mention commerciale (branches uniquement, haut-droit, pas de note de pied)
    if branch:
        g += render_commercial_mention(W, H, PAD, mode, eyebrow_color)

    motif_defs, motif_body = motif_vertex_monumental(W, H, mode)
    return wrap(W, H, motif_body + g, bg, defs=motif_defs)


def template_announce(mode, branch=None, variant="A"):
    W, H = 1080, 1350
    PAD = 80
    accent = get_brand_accent(mode, branch)
    cta_bg = accent
    cta_text = cta_text_on(accent)
    if mode == 'light':
        bg = MINT_WHITE
        text_color = DEEP_GREEN
        eyebrow_color = DEEP_GREEN
        logo_file = "02-horizontal/lnk-horizontal-light.svg" if not branch else branch["logo"]
    else:
        bg = DEEP_GREEN
        text_color = MINT_WHITE
        eyebrow_color = MINT_WHITE
        logo_file = "02-horizontal/lnk-horizontal-dark.svg" if not branch else branch["logo"].replace("-light", "-dark")

    max_text_w = W - 2 * PAD
    font = FONT_HEAD

    # Titre 2 lignes (grille H)
    lines_segments = [
        [("Votre marque,", text_color)],
        [("réinventée.", accent)],
    ]

    def measure_line_width(segments, H_val):
        total = 0
        for txt, _c in segments:
            r = build_text_grid(txt, font, H_val, "#000")
            if r: total += r['advance']
        return total

    H_target = 110
    for _ in range(25):
        max_w = max(measure_line_width(seg, H_target) for seg in lines_segments)
        if max_w <= max_text_w:
            break
        H_target *= 0.92

    rendered_lines = []
    for segments in lines_segments:
        parts = []
        x_off = 0
        _max_desc = 0.0
        _max_asc = 0.0
        for txt, color in segments:
            r = build_text_grid(txt, font, H_target, color)
            if r:
                parts.append((r['svg'], r['width'], x_off))
                x_off += r['advance']  # advance inclut l'espace final
                _max_desc = max(_max_desc, r['descender_px'])
                _max_asc = max(_max_asc, r['ascender_px'])
        rendered_lines.append({'parts': parts, 'width': x_off, 'descender': _max_desc, 'ascender': _max_asc})

    # Grille verticale
    LINE_HEIGHT = H_target * 1.30  # interligne fixe = 30% du H
    PAD_SAFETY = H_target * 0.30
    MIN_GAP = 0  # pas de poussee dynamique (test)
    step = LINE_HEIGHT
    for _i in range(1, len(rendered_lines)):
        _needed = H_target + rendered_lines[_i-1]['descender'] + rendered_lines[_i]['ascender'] + MIN_GAP
        step = max(step, _needed)

    # Eyebrow + subtitle + CTA label
    eyebrow, _, _, _ = build_text("LNK STUDIO · NOUVEAU PROJET", FONT_HEAD_SEMI, 22, eyebrow_color, tracking=0.12)
    subtitle, _, _, _ = build_text("Identité visuelle · Design · Déploiement", FONT_BODY, 26, text_color)
    cta_label, cta_w, cta_h, _ = build_text("Découvrir →", FONT_HEAD_BOLD, 30, cta_text)
    cta_padding_x = 50
    cta_padding_y = 28
    cta_total_w = cta_w + cta_padding_x * 2
    cta_total_h = cta_h + cta_padding_y * 2
    cta_radius = cta_total_h / 2

    # Logo en bas
    logo_inner, logo_vb = read_logo(logo_file, branch=branch["slug"] if branch else None)
    logo_h = 130
    _vb_parts = [float(v) for v in logo_vb.split()]
    _vb_w, _vb_h = _vb_parts[2], _vb_parts[3]
    logo_w = logo_h * (_vb_w / _vb_h)  # largeur réelle calculée
    logo_x = PAD  # aligné à gauche
    logo_y = H - PAD - logo_h
    logo_path = resolve_logo_path(logo_file, branch['slug'] if branch else None)
    logo_svg = place_logo(logo_inner, logo_vb, logo_x, logo_y, logo_w, logo_h, svg_path=logo_path)

    # Positions verticales (grille H)
    y_eyebrow = PAD
    y_cap_1 = y_eyebrow + 110 + PAD_SAFETY
    y_caps = [y_cap_1]
    for _i in range(len(rendered_lines) - 1):
        y_caps.append(y_caps[-1] + step)
    y_baseline_last = y_caps[-1] + H_target
    y_sub = y_baseline_last + PAD_SAFETY + 30

    # Zone visuelle
    visual_top = y_sub + 60
    visual_y = visual_top
    visual_x = PAD
    visual_w = W - 2 * PAD

    # CTA au-dessus du logo
    cta_x = PAD
    cta_y = logo_y - cta_total_h - 50

    # Hauteur dispo pour la zone visuelle
    visual_h = cta_y - 40 - visual_y

    g = f'<g transform="translate({PAD} {y_eyebrow})">{eyebrow}</g>'
    for _line, y_cap in zip(rendered_lines, y_caps):
        for seg_g, w, x_off in _line['parts']:
            g += f'<g transform="translate({PAD + x_off} {y_cap})">{seg_g}</g>'
    g += f'<g transform="translate({PAD} {y_sub})">{subtitle}</g>'

    # Zone visuelle
    visual_fill = "rgba(0,26,23,0.06)" if mode == "light" else "rgba(244,249,248,0.08)"
    g += f'<rect x="{visual_x}" y="{visual_y}" width="{visual_w}" height="{visual_h}" fill="{visual_fill}" rx="16"/>'
    visual_label, _, _, _ = build_text("[ Zone visuelle — photo / mockup ]", FONT_BODY, 22, text_color)
    g += f'<g transform="translate({visual_x + visual_w/2 - 180} {visual_y + visual_h/2})">{visual_label}</g>'

    # CTA pill
    g += f'<rect x="{cta_x}" y="{cta_y}" width="{cta_total_w}" height="{cta_total_h}" rx="{cta_radius}" fill="{cta_bg}"/>'
    g += f'<g transform="translate({cta_x + cta_padding_x} {cta_y + cta_padding_y})">{cta_label}</g>'

    g += logo_svg

    # Mention commerciale (branches uniquement, haut-droit, pas de note de pied)
    if branch:
        g += render_commercial_mention(W, H, PAD, mode, eyebrow_color)

    motif_defs, motif_body = motif_vertex_monumental(W, H, mode)
    return wrap(W, H, motif_body + g, bg, defs=motif_defs)


def template_story(mode, branch=None, variant="A"):
    W, H = 1080, 1920
    PAD = 60
    # Safe zone Stories : 250px top, 340px bottom (UI Instagram)
    SAFE_TOP = 250
    SAFE_BOTTOM = 340

    accent = get_brand_accent(mode, branch)
    cta_bg = accent
    cta_text = cta_text_on(accent)
    if mode == 'light':
        bg = MINT_WHITE
        text_color = DEEP_GREEN
        eyebrow_color = DEEP_GREEN
        logo_file = "02-horizontal/lnk-horizontal-light.svg" if not branch else branch["logo"]
    else:
        bg = DEEP_GREEN
        text_color = MINT_WHITE
        eyebrow_color = MINT_WHITE
        logo_file = "02-horizontal/lnk-horizontal-dark.svg" if not branch else branch["logo"].replace("-light", "-dark")

    max_text_w = W - 2 * PAD

    # Eyebrow
    eyebrow, _, _, _ = build_text("LNK STUDIO · STORY", FONT_HEAD_SEMI, 24, eyebrow_color, tracking=0.12)

    # Titre 3 lignes (grille H)
    lines_segments = [
        [("Ensemble,", text_color)],
        [("donnons vie", accent)],
        [("à vos projets.", text_color)],
    ]

    def measure_line_width(segments, H):
        total = 0
        for txt, _c in segments:
            r = build_text_grid(txt, font, H, "#000")
            if r: total += r['width']
        return total

    font = FONT_HEAD
    H_target = 110
    for _ in range(25):
        max_w = max(measure_line_width(seg, H_target) for seg in lines_segments)
        if max_w <= max_text_w:
            break
        H_target *= 0.92

    # Construire les lignes (grille H)
    rendered_lines = []
    for segments in lines_segments:
        parts = []
        x_off = 0
        _max_desc = 0.0
        _max_asc = 0.0
        for txt, color in segments:
            r = build_text_grid(txt, font, H_target, color)
            if r:
                parts.append((r['svg'], r['width'], x_off))
                x_off += r['advance']
                _max_desc = max(_max_desc, r['descender_px'])
                _max_asc = max(_max_asc, r['ascender_px'])
        rendered_lines.append({'parts': parts, 'width': x_off, 'descender': _max_desc, 'ascender': _max_asc})

    # Grille verticale
    LINE_HEIGHT = H_target * 1.40
    PAD_SAFETY = H_target * 0.30
    MIN_GAP = H_target * 0.12
    step = LINE_HEIGHT
    for _i in range(1, len(rendered_lines)):
        _needed = H_target + rendered_lines[_i-1]['descender'] + rendered_lines[_i]['ascender'] + MIN_GAP
        step = max(step, _needed)

    # Sous-titre
    subtitle, _, _, _ = build_text("Design · Branding · Impression · Motion", FONT_BODY, 26, text_color)

    # CTA WhatsApp (comme dans ton affiche)
    cta_label, cta_w, cta_h, _ = build_text("ÉCRIVEZ-NOUS SUR WHATSAPP", FONT_HEAD_BOLD, 26, cta_text)
    cta_padding_x = 60
    cta_padding_y = 32
    cta_total_w = cta_w + cta_padding_x * 2
    cta_total_h = cta_h + cta_padding_y * 2
    cta_radius = cta_total_h / 2

    # ============================================================
    # Positions calculées depuis le BAS — Story T3 (grille H)
    # ============================================================
    safe_bottom_y = H - SAFE_BOTTOM

    # 1. Logo (0px de marge sous lui, juste au-dessus de la safe zone)
    logo_inner, logo_vb = read_logo(logo_file, branch=branch["slug"] if branch else None)
    logo_h = 130
    # Calculer la largeur réelle depuis le ratio du viewBox pour centrer correctement
    _vb_parts = [float(v) for v in logo_vb.split()]
    _vb_w, _vb_h = _vb_parts[2], _vb_parts[3]
    _ratio = _vb_w / _vb_h
    logo_w = logo_h * _ratio  # largeur réelle calculée
    logo_x = (W - logo_w) / 2  # centrage sur la largeur réelle
    logo_y = safe_bottom_y - logo_h

    # 2. CTA (20px seulement au-dessus du logo)
    cta_x = (W - cta_total_w) / 2
    cta_y = logo_y - cta_total_h - 20

    # 3. Zone visuelle (20px au-dessus du CTA, hauteur dynamique agrandie)
    visual_x = PAD
    visual_w = W - 2 * PAD
    visual_bottom = cta_y - 20

    # 4. Textes (grille H, cap line à cap line)
    y_eyebrow = SAFE_TOP + 40
    y_cap_1 = y_eyebrow + 110 + PAD_SAFETY
    y_caps = [y_cap_1]
    for _i in range(len(rendered_lines) - 1):
        y_caps.append(y_caps[-1] + step)
    y_baseline_last = y_caps[-1] + H_target
    y_sub = y_baseline_last + PAD_SAFETY + 30

    # Zone visuelle : entre sous-titre et CTA
    visual_y = y_sub + 40
    visual_h = visual_bottom - visual_y

    g = f'<g transform="translate({PAD} {y_eyebrow})">{eyebrow}</g>'
    for _line, y_cap in zip(rendered_lines, y_caps):
        for seg_g, w, x_off in _line['parts']:
            g += f'<g transform="translate({PAD + x_off} {y_cap})">{seg_g}</g>'
    g += f'<g transform="translate({PAD} {y_sub})">{subtitle}</g>'

    # Zone visuelle subtile
    visual_fill = "rgba(0,26,23,0.06)" if mode == "light" else "rgba(244,249,248,0.08)"
    g += f'<rect x="{visual_x}" y="{visual_y}" width="{visual_w}" height="{visual_h}" fill="{visual_fill}" rx="16"/>'
    visual_label, _, _, _ = build_text("[ Zone visuelle — photo / mockup ]", FONT_BODY, 22, text_color)
    g += f'<g transform="translate({visual_x + visual_w/2 - 180} {visual_y + visual_h/2})">{visual_label}</g>'

    # CTA WhatsApp pill
    g += f'<rect x="{cta_x}" y="{cta_y}" width="{cta_total_w}" height="{cta_total_h}" rx="{cta_radius}" fill="{cta_bg}"/>'
    g += f'<g transform="translate({cta_x + cta_padding_x} {cta_y + cta_padding_y})">{cta_label}</g>'

    # Logo
    logo_path = resolve_logo_path(logo_file, branch['slug'] if branch else None)
    g += place_logo(logo_inner, logo_vb, logo_x, logo_y, logo_w, logo_h, svg_path=logo_path)

    # Mention commerciale (branches uniquement, haut-droit, pas de note de pied)
    if branch:
        g += render_commercial_mention(W, H, PAD, mode, eyebrow_color)

    # Motif LV en fond (variante paramétrable)
    motif_defs, motif_body = motif_vertex_monumental(W, H, mode)
    return wrap(W, H, motif_body + g, bg, defs=motif_defs)


# ============================================================
# T4 — Avatar (favicon + apple-touch, 800x800)
# ============================================================
def template_avatar(mode, branch=None, variant="favicon"):
    """
    Avatar 800x800.

    variant = "favicon"     : canvas Mint White + cercle Deep Green 100% + vertex 75%
    variant = "apple-touch" : canvas (Mint/Deep) + squircle opposé 75% + symbole 75%
                              (mode light ou dark pilote les couleurs)
    """
    W, H = 800, 800

    # Couleurs du vertex selon mode + branche (Option A : inversion partout)
    # - Favicon + Apple Touch light (canvas Mint) : cercle = light, triangle = base
    # - Apple Touch dark (canvas Deep)           : cercle = base,  triangle = light
    if branch is None:
        # Mère : jaune / orange
        if variant == "apple-touch" and mode == "dark":
            circle_color = ORANGE    # #FF7043
            triangle_color = YELLOW  # #FFC107
        else:
            circle_color = YELLOW    # #FFC107
            triangle_color = ORANGE  # #FF7043
    else:
        # Branches : duo-ton color / color_light
        if variant == "apple-touch" and mode == "dark":
            circle_color = branch["color"]
            triangle_color = branch["color_light"]
        else:
            circle_color = branch["color_light"]
            triangle_color = branch["color"]

    # Charger vertex (2 paths : cercle, triangle) et symbol (5 paths : 3 barres + vertex)
    vertex_paths, vertex_vb = _load_vertex()
    symbol_paths, symbol_vb = _load_symbol()
    svx, svy, svw, svh = [float(x) for x in vertex_vb.split()]
    spx, spy, spw, sph = [float(x) for x in symbol_vb.split()]

    def recolor_path(path, old_color, new_color):
        return _re.sub(r'fill="[^"]*"', f'fill="{new_color}"', path)

    def vertex_colored(override_circle=None, override_triangle=None):
        c = override_circle or circle_color
        t = override_triangle or triangle_color
        # path[0] = cercle, path[1] = triangle
        p0 = recolor_path(vertex_paths[0], "#ffc107", c)
        p1 = recolor_path(vertex_paths[1], "#ff7043", t)
        return [p0, p1]

    def symbol_colored(bars_color):
        # symbol.svg : path[0,1,4] = barres, path[2] = cercle, path[3] = triangle
        result = []
        for i, path in enumerate(symbol_paths):
            if i in (2,):  # cercle
                result.append(recolor_path(path, "#ffc107", circle_color))
            elif i in (3,):  # triangle
                result.append(recolor_path(path, "#ff7043", triangle_color))
            else:  # barres
                result.append(recolor_path(path, "#009688", bars_color))
                result[-1] = result[-1].replace("#009388", bars_color)
        return result

    def _wrap(w, h, defs, body, bg):
        defs_block = f"<defs>{defs}</defs>" if defs else ""
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">'
            f'{defs_block}<rect width="{w}" height="{h}" fill="{bg}"/>{body}</svg>\n'
        )

    def sub_svg(vb, vb_x, vb_y, vb_w, vb_h, target_x, target_y, target_w, target_h, content):
        """Sous-SVG qui place un contenu dans une zone avec centrage et scaling."""
        return (
            f'<svg x="{target_x:.1f}" y="{target_y:.1f}" width="{target_w:.1f}" height="{target_h:.1f}" '
            f'viewBox="{vb_x:.2f} {vb_y:.2f} {vb_w:.2f} {vb_h:.2f}" '
            f'preserveAspectRatio="xMidYMid meet">{content}</svg>'
        )

    if variant == "favicon":
        # Canvas Mint White, cercle Deep Green 100%, vertex 75% du diametre
        bg = MINT_WHITE
        circle_diameter = W  # 100% du canvas
        vertex_size = circle_diameter * 0.75
        cx, cy = W / 2, H / 2
        # Cercle
        body = f'<circle cx="{cx}" cy="{cy}" r="{circle_diameter/2}" fill="{DEEP_GREEN}"/>'
        # Vertex dans un sous-SVG
        vx = cx - vertex_size / 2
        vy = cy - vertex_size / 2
        body += sub_svg(vertex_vb, svx, svy, svw, svh, vx, vy, vertex_size, vertex_size, "".join(vertex_colored()))
        return _wrap(W, H, "", body, bg)

    elif variant == "apple-touch":
        # Canvas : light = Mint, dark = Deep
        if mode == "light":
            bg = MINT_WHITE
            squircle_color = DEEP_GREEN
            bars_color = MINT_WHITE
        else:
            bg = DEEP_GREEN
            squircle_color = MINT_WHITE
            bars_color = DEEP_GREEN

        squircle_size = W * 0.75    # 600
        squircle_radius = squircle_size * 0.225
        sx = (W - squircle_size) / 2
        sy = (H - squircle_size) / 2

        # Squircle
        body = f'<rect x="{sx}" y="{sy}" width="{squircle_size}" height="{squircle_size}" rx="{squircle_radius}" ry="{squircle_radius}" fill="{squircle_color}"/>'

        # Symbole 75% du squircle (= 450)
        sym_size = squircle_size * 0.75
        sym_x = (W - sym_size) / 2
        sym_y = (H - sym_size) / 2
        body += sub_svg(symbol_vb, spx, spy, spw, sph, sym_x, sym_y, sym_size, sym_size, "".join(symbol_colored(bars_color)))
        return _wrap(W, H, "", body, bg)

    else:
        raise ValueError(f"Variant avatar inconnue : {variant} (attendu : favicon | apple-touch)")



# ============================================================
# Config des covers (6 formats par reseau)
# ============================================================
COVER_FORMATS = {
    # `safe` = (x, y, w, h) : boite dans laquelle le bloc logo+baseline doit tenir.
    # Si absent, fallback sur `padding` uniforme.
    # `logo_pos` : top-left | top-right | middle-left | middle-right | center
    "x-header": {
        "w": 1500, "h": 500,
        "logo_pos": "top-right",
        "logo_h": 150,
        "safe": (480, 60, 960, 380),  # droite de l'avatar (coin bas-gauche)
    },
    "facebook-cover": {
        "w": 820, "h": 360,
        "logo_pos": "center",
        "logo_h": 80,
        "padding": 40,
    },
    "linkedin-personal": {
        "w": 1584, "h": 396,
        "logo_pos": "middle-right",
        "logo_h": 100,
        "padding": 60,
    },
    "linkedin-page": {
        "w": 4200, "h": 700,
        "logo_pos": "center",
        "logo_h": 160,
        "padding": 80,
    },
    "youtube-banner": {
        "w": 2560, "h": 1440,
        "logo_pos": "center",
        "logo_h": 200,
        "safe": (507, 509, 1546, 423),  # safe zone YouTube (tous ecrans)
    },
    "google-cover": {
        "w": 1024, "h": 576,
        "logo_pos": "center",
        "logo_h": 150,
        "padding": 60,
    },
    "behance-banner": {
        "w": 3200, "h": 410,
        "logo_pos": "center",
        "logo_h": 120,
        "padding": 50,
    },
}
COVER_DIMS = {k: (v["w"], v["h"]) for k, v in COVER_FORMATS.items()}


# ============================================================
# T5 — Cover generique (parametrable par format)
# ============================================================
def template_cover(mode, branch=None, variant="A", fmt="x-header"):
    """Cover : logo + baseline, positionnes dans la safe zone du reseau.

    Formats : x-header, facebook-cover, linkedin-personal, linkedin-page,
              youtube-banner, google-cover, behance-banner

    `logo_pos` controle l'ancrage du bloc (logo + baseline) :
      top-left | top-right | middle-left | middle-right | center
    `safe` (optionnel) restreint le placement dans une sous-zone du canvas.
    """
    cfg = COVER_FORMATS[fmt]
    W, H = cfg["w"], cfg["h"]
    bg = MINT_WHITE if mode == "light" else DEEP_GREEN
    text_color = DEEP_GREEN if mode == "light" else MINT_WHITE

    # --- Logo file ---
    logo_file = "lnk-horizontal-light.svg" if mode == "light" else "lnk-horizontal-dark.svg"
    if branch:
        logo_file = branch["logo"].replace("-light", f"-{mode}")

    logo_inner, logo_vb = read_logo(logo_file, branch=branch["slug"] if branch else None)
    if not logo_inner:
        print(f"  WARN : logo introuvable pour {fmt} / {mode} / {branch}")
        logo_inner = ""
        logo_vb = "0 0 100 100"

    # --- Dimensions logo (hauteur = reference) ---
    logo_h = cfg["logo_h"]
    vb_parts = [float(x) for x in logo_vb.split()]
    vb_w, vb_h = vb_parts[2], vb_parts[3]
    logo_w = logo_h * (vb_w / vb_h)

    # --- Baseline ---
    baseline_text = branch["subtitle"] if branch else "Ensemble, donnons vie a vos projets"
    baseline_target_h = max(20, int(logo_h * 0.25))
    baseline_svg, baseline_w, baseline_h_actual, _ = build_text(
        baseline_text, FONT_BODY, baseline_target_h, text_color
    )

    gap = int(logo_h * 0.15)
    block_w = max(logo_w, baseline_w)
    block_h = logo_h + gap + baseline_h_actual

    # --- Zone de placement ---
    if "safe" in cfg:
        sx, sy, sw, sh = cfg["safe"]
    else:
        pad = cfg.get("padding", 60)
        sx, sy = pad, pad
        sw, sh = W - 2 * pad, H - 2 * pad

    # --- Ancrage du bloc ---
    pos = cfg["logo_pos"]
    if pos == "center":
        block_x = sx + (sw - block_w) / 2
        block_y = sy + (sh - block_h) / 2
    elif pos == "top-left":
        block_x, block_y = sx, sy
    elif pos == "top-right":
        block_x, block_y = sx + sw - block_w, sy
    elif pos == "middle-left":
        block_x, block_y = sx, sy + (sh - block_h) / 2
    elif pos == "middle-right":
        block_x, block_y = sx + sw - block_w, sy + (sh - block_h) / 2
    else:
        raise ValueError(f"logo_pos inconnu : {pos}")

    # --- Alignement interne (logo et baseline partagent le meme ancrage) ---
    if pos == "center":
        logo_x = block_x + (block_w - logo_w) / 2
        baseline_x = block_x + (block_w - baseline_w) / 2
    elif pos in ("top-right", "middle-right"):
        logo_x = block_x + (block_w - logo_w)
        baseline_x = block_x + (block_w - baseline_w)
    else:
        logo_x = block_x
        baseline_x = block_x

    logo_y = block_y
    baseline_y = block_y + logo_h + gap

    # --- Render ---
    logo_path = resolve_logo_path(logo_file, branch["slug"] if branch else None)
    logo_svg = place_logo(logo_inner, logo_vb, logo_x, logo_y, logo_w, logo_h, svg_path=logo_path) if logo_inner else ""
    baseline_g = f'<g transform="translate({baseline_x:.2f} {baseline_y:.2f})">{baseline_svg}</g>'

    motif_defs, motif_body = motif_vertex_monumental(W, H, mode)
    return wrap(W, H, motif_body + logo_svg + baseline_g, bg, defs=motif_defs)


def template_pinterest_pin(mode, branch=None, variant="A"):
    """Pinterest pin vertical 1000x1500.
    Contenu : eyebrow + titre 2-3 lignes + sous-titre + zone visuelle + logo.
    """
    W, H = 1000, 1500
    PAD = 70
    accent = get_brand_accent(mode, branch)
    if mode == 'light':
        bg = MINT_WHITE
        text_color = DEEP_GREEN
        eyebrow_color = DEEP_GREEN
        logo_file = "02-horizontal/lnk-horizontal-light.svg" if not branch else branch["logo"]
    else:
        bg = DEEP_GREEN
        text_color = MINT_WHITE
        eyebrow_color = MINT_WHITE
        logo_file = "02-horizontal/lnk-horizontal-dark.svg" if not branch else branch["logo"].replace("-light", "-dark")

    max_text_w = W - 2 * PAD
    font = FONT_HEAD

    # Titre 3 lignes
    lines_segments = [
        [("L'inspiration", text_color)],
        [("qui donne", text_color)],
        [("vie.", accent)],
    ]

    def measure_line_width(segments, H_val):
        total = 0
        for txt, _c in segments:
            r = build_text_grid(txt, font, H_val, "#000")
            if r: total += r['advance']
        return total

    H_target = 90
    for _ in range(25):
        max_w = max(measure_line_width(seg, H_target) for seg in lines_segments)
        if max_w <= max_text_w:
            break
        H_target *= 0.92

    rendered_lines = []
    for segments in lines_segments:
        parts = []
        x_off = 0
        _max_desc = 0.0
        _max_asc = 0.0
        for txt, color in segments:
            r = build_text_grid(txt, font, H_target, color)
            if r:
                parts.append((r['svg'], r['width'], x_off))
                x_off += r['advance']
                _max_desc = max(_max_desc, r['descender_px'])
                _max_asc = max(_max_asc, r['ascender_px'])
        rendered_lines.append({'parts': parts, 'width': x_off, 'descender': _max_desc, 'ascender': _max_asc})

    LINE_HEIGHT = H_target * 1.30  # interligne fixe = 30% du H
    PAD_SAFETY = H_target * 0.30
    MIN_GAP = 0  # pas de poussee dynamique (test)
    step = LINE_HEIGHT
    for _i in range(1, len(rendered_lines)):
        _needed = H_target + rendered_lines[_i-1]['descender'] + rendered_lines[_i]['ascender'] + MIN_GAP
        step = max(step, _needed)

    eyebrow, _, _, _ = build_text("LNK STUDIO · INSPIRATION", FONT_HEAD_SEMI, 20, eyebrow_color, tracking=0.12)
    subtitle, _, _, _ = build_text("Design · Branding · Motion · Impression", FONT_BODY, 24, text_color)

    # Logo (basé sur hauteur cible 120px)
    logo_inner, logo_vb = read_logo(logo_file, branch=branch["slug"] if branch else None)
    logo_h = 120
    _vb = [float(v) for v in logo_vb.split()]
    logo_w = logo_h * (_vb[2] / _vb[3])
    logo_x = PAD
    logo_y = H - PAD - logo_h
    logo_path = resolve_logo_path(logo_file, branch["slug"] if branch else None)
    logo_svg = place_logo(logo_inner, logo_vb, logo_x, logo_y, logo_w, logo_h, svg_path=logo_path)

    y_eyebrow = PAD
    y_cap_1 = y_eyebrow + 100 + PAD_SAFETY
    y_caps = [y_cap_1]
    for _i in range(len(rendered_lines) - 1):
        y_caps.append(y_caps[-1] + step)
    y_baseline_last = y_caps[-1] + H_target
    y_sub = y_baseline_last + PAD_SAFETY + 30

    # Zone visuelle
    visual_y = y_sub + 60
    visual_x = PAD
    visual_w = W - 2 * PAD
    visual_h = (logo_y - 60) - visual_y

    g = f'<g transform="translate({PAD} {y_eyebrow})">{eyebrow}</g>'
    for _line, y_cap in zip(rendered_lines, y_caps):
        for seg_g, w, x_off in _line['parts']:
            g += f'<g transform="translate({PAD + x_off} {y_cap})">{seg_g}</g>'
    g += f'<g transform="translate({PAD} {y_sub})">{subtitle}</g>'

    visual_fill = "rgba(0,26,23,0.06)" if mode == "light" else "rgba(244,249,248,0.08)"
    g += f'<rect x="{visual_x}" y="{visual_y}" width="{visual_w}" height="{visual_h}" fill="{visual_fill}" rx="16"/>'
    visual_label, _, _, _ = build_text("[ Zone visuelle — photo / mockup ]", FONT_BODY, 20, text_color)
    g += f'<g transform="translate({visual_x + visual_w/2 - 160} {visual_y + visual_h/2})">{visual_label}</g>'

    g += logo_svg

    if branch:
        g += render_commercial_mention(W, H, PAD, mode, text_color)

    motif_defs, motif_body = motif_vertex_monumental(W, H, mode)
    return wrap(W, H, motif_body + g, bg, defs=motif_defs)


# ============================================================
# T7 — YouTube Thumbnail (1280x720, ratio 16:9)
# ============================================================
def template_youtube_thumbnail(mode, branch=None, variant="A"):
    """YouTube thumbnail 1280x720. Titre TRÈS court (2-4 mots), lisible en 320x180."""
    W, H = 1280, 720
    PAD = 60
    accent = get_brand_accent(mode, branch)
    if mode == 'light':
        bg = MINT_WHITE
        text_color = DEEP_GREEN
        eyebrow_color = DEEP_GREEN
        logo_file = "02-horizontal/lnk-horizontal-light.svg" if not branch else branch["logo"]
    else:
        bg = DEEP_GREEN
        text_color = MINT_WHITE
        eyebrow_color = MINT_WHITE
        logo_file = "02-horizontal/lnk-horizontal-dark.svg" if not branch else branch["logo"].replace("-light", "-dark")

    max_text_w = W - 2 * PAD
    font = FONT_HEAD

    # Titre 2 lignes TRÈS courtes
    lines_segments = [
        [("Créer.", text_color)],
        [("Vite.", accent)],
    ]

    def measure_line_width(segments, H_val):
        total = 0
        for txt, _c in segments:
            r = build_text_grid(txt, font, H_val, "#000")
            if r: total += r['advance']
        return total

    # YouTube = grande taille pour lisibilité miniature
    H_target = 220
    for _ in range(25):
        max_w = max(measure_line_width(seg, H_target) for seg in lines_segments)
        if max_w <= max_text_w * 0.6:
            break
        H_target *= 0.92

    rendered_lines = []
    for segments in lines_segments:
        parts = []
        x_off = 0
        _max_desc = 0.0
        _max_asc = 0.0
        for txt, color in segments:
            r = build_text_grid(txt, font, H_target, color)
            if r:
                parts.append((r['svg'], r['width'], x_off))
                x_off += r['advance']
                _max_desc = max(_max_desc, r['descender_px'])
                _max_asc = max(_max_asc, r['ascender_px'])
        rendered_lines.append({'parts': parts, 'width': x_off, 'descender': _max_desc, 'ascender': _max_asc})

    LINE_HEIGHT = H_target * 1.30  # interligne fixe = 30% du H
    PAD_SAFETY = H_target * 0.30
    MIN_GAP = 0  # pas de poussee dynamique (test)
    step = LINE_HEIGHT
    for _i in range(1, len(rendered_lines)):
        _needed = H_target + rendered_lines[_i-1]['descender'] + rendered_lines[_i]['ascender'] + MIN_GAP
        step = max(step, _needed)

    subtitle, _, _, _ = build_text("Design · Branding · Motion", FONT_BODY, 32, text_color)

    # Logo 80px
    logo_inner, logo_vb = read_logo(logo_file, branch=branch["slug"] if branch else None)
    logo_h = 80
    _vb = [float(v) for v in logo_vb.split()]
    logo_w = logo_h * (_vb[2] / _vb[3])
    logo_x = PAD
    logo_y = H - PAD - logo_h
    logo_path = resolve_logo_path(logo_file, branch["slug"] if branch else None)
    logo_svg = place_logo(logo_inner, logo_vb, logo_x, logo_y, logo_w, logo_h, svg_path=logo_path)

    # Layout : titre à gauche, zone visuelle à droite
    y_cap_1 = PAD + PAD_SAFETY
    y_caps = [y_cap_1]
    for _i in range(len(rendered_lines) - 1):
        y_caps.append(y_caps[-1] + step)
    y_baseline_last = y_caps[-1] + H_target
    y_sub = y_baseline_last + PAD_SAFETY + 30

    g = ""
    for _line, y_cap in zip(rendered_lines, y_caps):
        for seg_g, w, x_off in _line['parts']:
            g += f'<g transform="translate({PAD + x_off} {y_cap})">{seg_g}</g>'
    g += f'<g transform="translate({PAD} {y_sub})">{subtitle}</g>'

    # Zone visuelle à droite
    visual_x = W * 0.55
    visual_y = PAD
    visual_w = W - visual_x - PAD
    visual_h = H - 2 * PAD - logo_h - 20
    visual_fill = "rgba(0,26,23,0.06)" if mode == "light" else "rgba(244,249,248,0.08)"
    g += f'<rect x="{visual_x}" y="{visual_y}" width="{visual_w}" height="{visual_h}" fill="{visual_fill}" rx="16"/>'
    visual_label, _, _, _ = build_text("[ Visuel ]", FONT_BODY, 24, text_color)
    g += f'<g transform="translate({visual_x + visual_w/2 - 60} {visual_y + visual_h/2})">{visual_label}</g>'

    g += logo_svg

    if branch:
        g += render_commercial_mention(W, H, PAD, mode, text_color, y=H - PAD - 30)

    motif_defs, motif_body = motif_vertex_monumental(W, H, mode)
    return wrap(W, H, motif_body + g, bg, defs=motif_defs)


# ============================================================
# T8 — Behance Project Cover (1400x788, ~16:9)
# ============================================================
def template_behance_project(mode, branch=None, variant="A"):
    """Behance project cover 1400x788. Eyebrow + titre + sous-titre + logo."""
    W, H = 1400, 788
    PAD = 80
    accent = get_brand_accent(mode, branch)
    if mode == 'light':
        bg = MINT_WHITE
        text_color = DEEP_GREEN
        eyebrow_color = DEEP_GREEN
        logo_file = "02-horizontal/lnk-horizontal-light.svg" if not branch else branch["logo"]
    else:
        bg = DEEP_GREEN
        text_color = MINT_WHITE
        eyebrow_color = MINT_WHITE
        logo_file = "02-horizontal/lnk-horizontal-dark.svg" if not branch else branch["logo"].replace("-light", "-dark")

    max_text_w = W - 2 * PAD
    font = FONT_HEAD

    # Titre 1-2 lignes
    lines_segments = [
        [("Identité visuelle", text_color)],
        [("& branding", accent)],
    ]

    def measure_line_width(segments, H_val):
        total = 0
        for txt, _c in segments:
            r = build_text_grid(txt, font, H_val, "#000")
            if r: total += r['advance']
        return total

    H_target = 110
    for _ in range(25):
        max_w = max(measure_line_width(seg, H_target) for seg in lines_segments)
        if max_w <= max_text_w:
            break
        H_target *= 0.92

    rendered_lines = []
    for segments in lines_segments:
        parts = []
        x_off = 0
        _max_desc = 0.0
        _max_asc = 0.0
        for txt, color in segments:
            r = build_text_grid(txt, font, H_target, color)
            if r:
                parts.append((r['svg'], r['width'], x_off))
                x_off += r['advance']
                _max_desc = max(_max_desc, r['descender_px'])
                _max_asc = max(_max_asc, r['ascender_px'])
        rendered_lines.append({'parts': parts, 'width': x_off, 'descender': _max_desc, 'ascender': _max_asc})

    LINE_HEIGHT = H_target * 1.30  # interligne fixe = 30% du H
    PAD_SAFETY = H_target * 0.30
    MIN_GAP = 0  # pas de poussee dynamique (test)
    step = LINE_HEIGHT
    for _i in range(1, len(rendered_lines)):
        _needed = H_target + rendered_lines[_i-1]['descender'] + rendered_lines[_i]['ascender'] + MIN_GAP
        step = max(step, _needed)

    eyebrow, _, _, _ = build_text("BEHANCE · LNK STUDIO", FONT_HEAD_SEMI, 22, eyebrow_color, tracking=0.12)
    subtitle, _, _, _ = build_text("Étude de cas · Direction artistique · Motion", FONT_BODY, 26, text_color)

    # Logo 110px
    logo_inner, logo_vb = read_logo(logo_file, branch=branch["slug"] if branch else None)
    logo_h = 110
    _vb = [float(v) for v in logo_vb.split()]
    logo_w = logo_h * (_vb[2] / _vb[3])
    logo_x = PAD
    logo_y = H - PAD - logo_h
    logo_path = resolve_logo_path(logo_file, branch["slug"] if branch else None)
    logo_svg = place_logo(logo_inner, logo_vb, logo_x, logo_y, logo_w, logo_h, svg_path=logo_path)

    y_eyebrow = PAD
    y_cap_1 = y_eyebrow + 80 + PAD_SAFETY
    y_caps = [y_cap_1]
    for _i in range(len(rendered_lines) - 1):
        y_caps.append(y_caps[-1] + step)
    y_baseline_last = y_caps[-1] + H_target
    y_sub = y_baseline_last + PAD_SAFETY + 30

    g = f'<g transform="translate({PAD} {y_eyebrow})">{eyebrow}</g>'
    for _line, y_cap in zip(rendered_lines, y_caps):
        for seg_g, w, x_off in _line['parts']:
            g += f'<g transform="translate({PAD + x_off} {y_cap})">{seg_g}</g>'
    g += f'<g transform="translate({PAD} {y_sub})">{subtitle}</g>'

    g += logo_svg

    if branch:
        g += render_commercial_mention(W, H, PAD, mode, text_color)

    motif_defs, motif_body = motif_vertex_monumental(W, H, mode)
    return wrap(W, H, motif_body + g, bg, defs=motif_defs)


# ============================================================
# MENTION REGISTRY — mention unique, jamais repetee.
# Charte : sur les posts/stories de BRANCHES uniquement, mention "by LNK Studio"
# en coin haut-droit, sans asterisque ni note de pied. Le logo des branches est
# nu (sans mention gravee) : voir build-sub-brand.py with_mention=False.
MENTION_REGISTRY = {
    "commercial": {
        "text": "by LNK Studio",
        "opacity": 0.75,
    },
}


def render_commercial_mention(W, H, PAD, mode, color, y=None):
    """Retourne le SVG de la mention placee en coin haut-droit (ou y custom).
    Par defaut y=PAD (aligne sur l'eyebrow). Peut etre override pour les
    templates sans eyebrow (youtube-thumbnail).
    """
    text = MENTION_REGISTRY["commercial"]["text"]
    mention_svg, mention_w, _, _ = build_text(
        text, FONT_BODY, 20, color, tracking=0.04,
    )
    x = W - PAD - mention_w
    yy = y if y is not None else PAD
    return f'<g transform="translate({x:.2f} {yy:.2f})" opacity="{MENTION_REGISTRY["commercial"]["opacity"]}">{mention_svg}</g>'


def template_cover_portfolio(mode, branch=None, variant="A", fmt="x-header"):
    """Cover "écosystème" : logo Studio + les 5 logos branches.
    Utilisé pour annonces corporate, page À propos, LinkedIn page about.
    `branch` est ignoré (toujours 6 logos : Studio + 5 branches).
    """
    cfg = COVER_FORMATS[fmt]
    W, H = cfg["w"], cfg["h"]
    bg = MINT_WHITE if mode == "light" else DEEP_GREEN

    # Zone safe
    if "safe" in cfg:
        sx, sy, sw, sh = cfg["safe"]
    else:
        pad = cfg.get("padding", 60)
        sx, sy = pad, pad
        sw, sh = W - 2 * pad, H - 2 * pad

    # --- Logo Studio (haut, centré) ---
    studio_file = "lnk-horizontal-light.svg" if mode == "light" else "lnk-horizontal-dark.svg"
    studio_inner, studio_vb = read_logo(studio_file, branch=None)
    studio_h = sh * 0.38  # Augmenté pour les formats larges
    _vb = [float(v) for v in studio_vb.split()]
    studio_w = studio_h * (_vb[2] / _vb[3])
    studio_x = sx + (sw - studio_w) / 2
    studio_y = sy + sh * 0.10
    studio_path = resolve_logo_path(studio_file, None)
    studio_svg = place_logo(studio_inner, studio_vb, studio_x, studio_y, studio_w, studio_h, svg_path=studio_path)

    # --- 5 logos branches (bas, alignés) ---
    BRANCH_ORDER = ["design-touch", "dev", "print", "play", "cine"]
    branch_h_target = sh * 0.22  # Augmenté pour les formats larges

    branch_items = []
    for bslug in BRANCH_ORDER:
        b = BRANCHES[bslug]
        bfile = b["logo"].replace("-light", f"-{mode}")
        b_inner, b_vb = read_logo(bfile, branch=bslug)
        if not b_inner:
            continue
        _bvb = [float(v) for v in b_vb.split()]
        b_w = branch_h_target * (_bvb[2] / _bvb[3])
        b_path = resolve_logo_path(bfile, bslug)
        branch_items.append({
            "inner": b_inner, "vb": b_vb, "path": b_path,
            "w": b_w, "h": branch_h_target,
        })

    if not branch_items:
        motif_defs, motif_body = motif_vertex_monumental(W, H, mode)
        return wrap(W, H, motif_body + studio_svg, bg, defs=motif_defs)

    # Espacement + réduction si nécessaire
    gap_branches = sw * 0.025
    total_w = sum(b["w"] for b in branch_items) + gap_branches * (len(branch_items) - 1)

    if total_w > sw:
        ratio = sw / total_w
        for b in branch_items:
            b["w"] *= ratio
            b["h"] *= ratio
        total_w = sw
        gap_branches = 0

    branch_h = branch_items[0]["h"]
    branch_y = sy + sh - branch_h - sh * 0.10
    branch_x = sx + (sw - total_w) / 2

    branches_g = ""
    cx = branch_x
    for b in branch_items:
        branches_g += place_logo(b["inner"], b["vb"], cx, branch_y, b["w"], b["h"], svg_path=b["path"])
        cx += b["w"] + gap_branches

    motif_defs, motif_body = motif_vertex_monumental(W, H, mode)
    return wrap(W, H, motif_body + studio_svg + branches_g, bg, defs=motif_defs)


# ============================================================
# OG Image + Twitter Card — 1200×630 (usage web)
# ============================================================
def template_og_image(mode, branch=None, variant="A"):
    """OG Image 1200×630 (Open Graph standard, utilisé sur Facebook,
    LinkedIn, Slack, WhatsApp, iMessage, Discord, etc.).
    Design : logo Studio centré + baseline. Pas de motif.
    """
    W, H = 1200, 630
    bg = MINT_WHITE if mode == "light" else DEEP_GREEN
    text_color = DEEP_GREEN if mode == "light" else MINT_WHITE
    muted_color = "#5A6E6B" if mode == "light" else "#9AACAA"

    # Logo centré
    logo_file = "lnk-horizontal-light.svg" if mode == "light" else "lnk-horizontal-dark.svg"
    logo_inner, logo_vb = read_logo(logo_file, branch=None)
    logo_h = int(H * 0.28)  # 176 px
    _vb = [float(v) for v in logo_vb.split()]
    logo_w = logo_h * (_vb[2] / _vb[3])
    logo_x = (W - logo_w) / 2
    logo_y = (H - logo_h) / 2 - H * 0.06  # légèrement au-dessus du centre
    logo_path = resolve_logo_path(logo_file, None)
    logo_svg = place_logo(logo_inner, logo_vb, logo_x, logo_y, logo_w, logo_h, svg_path=logo_path)

    # Baseline sous le logo
    baseline_text = "Ensemble, donnons vie à vos projets"
    baseline_svg, baseline_w, baseline_h, _ = build_text(
        baseline_text, FONT_BODY, int(H * 0.045), muted_color, tracking=0.02,
    )
    baseline_x = (W - baseline_w) / 2
    baseline_y = logo_y + logo_h + H * 0.10
    baseline_g = f'<g transform="translate({baseline_x:.2f} {baseline_y:.2f})">{baseline_svg}</g>'

    # URL en bas
    url_svg, url_w, _, _ = build_text(
        "lnk-studio.com", FONT_BODY, int(H * 0.035), text_color, tracking=0.04,
    )
    url_x = (W - url_w) / 2
    url_y = H - H * 0.08
    url_g = f'<g transform="translate({url_x:.2f} {url_y:.2f})" opacity="0.6">{url_svg}</g>'

    content = logo_svg + baseline_g + url_g
    return wrap(W, H, content, bg)


def template_twitter_card(mode, branch=None, variant="A"):
    """Twitter Card 1200×630 (summary_large_image).
    Design identique à OG (Twitter utilise le même ratio 1.91:1).
    """
    return template_og_image(mode, branch, variant)


TEMPLATES = {
    "citation": template_citation,
    "announce": template_announce,
    "story": template_story,
    "avatar": template_avatar,
    "pinterest-pin": template_pinterest_pin,
    "youtube-thumbnail": template_youtube_thumbnail,
    "behance-project": template_behance_project,
    "cover-x":                 lambda mode, branch, variant: template_cover(mode, branch, variant, "x-header"),
    "cover-facebook":          lambda mode, branch, variant: template_cover(mode, branch, variant, "facebook-cover"),
    "cover-linkedin-personal": lambda mode, branch, variant: template_cover(mode, branch, variant, "linkedin-personal"),
    "cover-linkedin-page":     lambda mode, branch, variant: template_cover(mode, branch, variant, "linkedin-page"),
    "cover-youtube":           lambda mode, branch, variant: template_cover(mode, branch, variant, "youtube-banner"),
    "cover-google":            lambda mode, branch, variant: template_cover(mode, branch, variant, "google-cover"),
    "cover-behance-banner":    lambda mode, branch, variant: template_cover(mode, branch, variant, "behance-banner"),
    # Portfolio (Studio + 5 branches) — pour annonces groupe
    "cover-x-portfolio":                 lambda mode, branch, variant: template_cover_portfolio(mode, branch, variant, "x-header"),
    "cover-facebook-portfolio":          lambda mode, branch, variant: template_cover_portfolio(mode, branch, variant, "facebook-cover"),
    "cover-linkedin-personal-portfolio": lambda mode, branch, variant: template_cover_portfolio(mode, branch, variant, "linkedin-personal"),
    "cover-linkedin-page-portfolio":     lambda mode, branch, variant: template_cover_portfolio(mode, branch, variant, "linkedin-page"),
    "cover-youtube-portfolio":           lambda mode, branch, variant: template_cover_portfolio(mode, branch, variant, "youtube-banner"),
    "cover-google-portfolio":            lambda mode, branch, variant: template_cover_portfolio(mode, branch, variant, "google-cover"),
    "cover-behance-portfolio":           lambda mode, branch, variant: template_cover_portfolio(mode, branch, variant, "behance-banner"),
    # Web (OG + Twitter Card)
    "og-image":     template_og_image,
    "twitter-card": template_twitter_card,
}

def main():
    if len(sys.argv) < 3:
        print("Usage : build-social-templates.py <template> <mode> [branch] [motif]")
        print("Templates : " + ", ".join(TEMPLATES.keys()))
        print("Modes     : light, dark")
        print("Branches  : mother, " + ", ".join(BRANCHES.keys()))
        print("Motifs    : A, B, C, D")
        sys.exit(1)
    template = sys.argv[1]
    mode = sys.argv[2]
    branch_slug = sys.argv[3] if len(sys.argv) > 3 else "mother"
    raw_arg = sys.argv[4] if len(sys.argv) > 4 else "A"
    if template == "avatar":
        motif = raw_arg.lower()
        if motif not in ("favicon", "apple-touch"):
            print(f"✗ Variante avatar inconnue : {motif} (attendu : favicon | apple-touch)")
            sys.exit(1)
    else:
        motif = raw_arg.upper()
        if motif not in ("A", "B", "C", "D", "E", "NONE"):
            print(f"✗ Motif inconnu : {motif} (attendu : A, B, C, D, E, NONE)")
            sys.exit(1)
    if template not in TEMPLATES:
        print(f"✗ Template inconnu : {template}"); sys.exit(1)
    if mode not in ("light", "dark"):
        print(f"✗ Mode inconnu : {mode}"); sys.exit(1)

    # Mapping template → sous-dossier de sortie
    TEMPLATE_FOLDER = {
        "citation": "posts",
        "announce": "posts",
        "story": "stories",
        "avatar": "avatars",
        "pinterest-pin": "posts",
        "youtube-thumbnail": "posts",
        "behance-project": "posts",
        "cover-x":                 "covers",
        "cover-facebook":          "covers",
        "cover-linkedin-personal": "covers",
        "cover-linkedin-page":     "covers",
        "cover-youtube":           "covers",
        "cover-google":            "covers",
        "cover-behance-banner":    "covers",
        "cover-x-portfolio":                 "covers",
        "cover-facebook-portfolio":          "covers",
        "cover-linkedin-personal-portfolio": "covers",
        "cover-linkedin-page-portfolio":     "covers",
        "cover-youtube-portfolio":           "covers",
        "cover-google-portfolio":            "covers",
        "cover-behance-portfolio":           "covers",
        "og-image":     "05-web/og",
        "twitter-card": "05-web/og",
    }
    folder = TEMPLATE_FOLDER.get(template, "posts")

    # Cas spécial : templates web (05-web/og) — destination racine web
    if folder.startswith("05-web"):
        out_dir = ROOT / folder
        branch = None
    elif branch_slug == "mother":
        out_dir = ROOT / "04-exports/social" / folder / "mother"
        branch = None
    else:
        out_dir = ROOT / "04-exports/social" / folder / branch_slug
        branch = BRANCHES[branch_slug]
    out_dir.mkdir(parents=True, exist_ok=True)
    svg = TEMPLATES[template](mode, branch=branch, variant=motif)
    if template == "avatar":
        # Nom : avatar-favicon.png ou avatar-apple-touch-light/dark.png
        if motif == "favicon":
            base = "avatar-favicon"
        else:
            base = f"avatar-apple-touch-{mode}"
    elif motif == "NONE":
        # Pas de motif : nom = template-mode (sans suffixe)
        base = f"{template}-{mode}"
    else:
        base = f"{template}-{mode}-{motif}"
    svg_path = out_dir / f"{base}.svg"
    svg_path.write_text(svg)
    print(f"  ✓ {svg_path.relative_to(ROOT)}")

    png_path = out_dir / f"{base}.png"
    # Dimensions selon le template
    base_dims = {
        "citation": (1080, 1080),
        "announce": (1080, 1350),
        "story": (1080, 1920),
        "avatar": (800, 800),
        "pinterest-pin": (1000, 1500),
        "youtube-thumbnail": (1280, 720),
        "behance-project": (1400, 788),
        "og-image":     (1200, 630),
        "twitter-card": (1200, 630),
    }
    # Covers : mapping template name -> format key dans COVER_DIMS
    COVER_KEYS = {
        "cover-x":                 "x-header",
        "cover-facebook":          "facebook-cover",
        "cover-linkedin-personal": "linkedin-personal",
        "cover-linkedin-page":     "linkedin-page",
        "cover-youtube":           "youtube-banner",
        "cover-google":            "google-cover",
        "cover-behance-banner":    "behance-banner",
        "cover-x-portfolio":                 "x-header",
        "cover-facebook-portfolio":          "facebook-cover",
        "cover-linkedin-personal-portfolio": "linkedin-personal",
        "cover-linkedin-page-portfolio":     "linkedin-page",
        "cover-youtube-portfolio":           "youtube-banner",
        "cover-google-portfolio":            "google-cover",
        "cover-behance-portfolio":           "behance-banner",
    }
    if template in COVER_KEYS:
        w, h = COVER_DIMS[COVER_KEYS[template]]
    else:
        w, h = base_dims.get(template, (1080, 1080))
    subprocess.run(["rsvg-convert", "-w", str(w), "-h", str(h), "-o", str(png_path), str(svg_path)], check=True)
    print(f"  ✓ {png_path.relative_to(ROOT)} ({w}x{h})")

if __name__ == "__main__":
    main()
