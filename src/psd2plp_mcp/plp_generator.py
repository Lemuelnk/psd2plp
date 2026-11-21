"""Adaptateur entre le spec du plugin et le moteur psd2plp.

Le plugin accepte un spec JSON avec les clés :
  - width, height, background_color
  - objects: [{kind, x, y, width, height, fill_color, shape_type,
               radius_pct, text, font_family, font_size, text_color,
               align, opacity, rotation}]

psd2plp attend un Spec avec :
  - canvas: {width, height, bg}
  - objects: [SpecText | SpecShape | SpecImage]

Ce module traduit l'un vers l'autre, puis appelle plp_from_spec() +
write_plp() de psd2plp (qui gère res/, fonts embarquées, PNG fallback,
thumb composite).
"""
from __future__ import annotations
import json
import tempfile
from pathlib import Path

from psd2plp.spec.builder import plp_from_spec
from psd2plp.spec.schema import (
    Spec, SpecCanvas, SpecText, SpecShape, SpecImage,
)
from psd2plp.pixellab.writer import write_plp as _psd2plp_write
from psd2plp_mcp.font_engine import resolve_font_file


# --- Conversion couleurs ---

def _normalize_hex(value) -> str:
    """Accepte #RGB, #RRGGBB, #AARRGGBB, ou int ARGB signé."""
    if isinstance(value, int):
        v = value if value >= 0 else value + (1 << 32)
        a = (v >> 24) & 0xFF
        r = (v >> 16) & 0xFF
        g = (v >> 8) & 0xFF
        b = v & 0xFF
        # psd2plp attend #RRGGBB (alpha supporté mais optionnel)
        return f"#{r:02X}{g:02X}{b:02X}"
    s = str(value).strip()
    if not s.startswith("#"):
        s = "#" + s
    h = s[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8:
        # AARRGGBB -> on garde RGB, alpha géré séparément
        h = h[2:]
    return f"#{h.upper()}"


# --- Conversion des objets ---

def _convert_text(obj: dict) -> SpecText:
    # psd2plp : size_px = cap-height en pixels canvas
    # Le plugin fournit font_size qui est probablement la taille em
    # → on assume cap_ratio = 0.7 (Montserrat)
    raw_size = float(obj.get("text_size", obj.get("font_size", obj.get("size_px", 40))))
    size_px = raw_size * 0.7  # em -> cap-height (existing generator unit conversion)

    requested_family = obj.get("font_family")
    font_weight = int(obj.get("font_weight", 400))
    font_style = obj.get("font_style", "normal")
    font_path = None
    font = obj.get("font") or "Montserrat-Regular"
    bundled_faces = {
        "Montserrat-Regular", "Montserrat-SemiBold", "Montserrat-Bold",
        "Montserrat-ExtraBold", "MontserratAlternates-ExtraBold",
        "OpenSans-Regular", "OpenSans-SemiBold",
    }
    if requested_family:
        if str(requested_family) in bundled_faces:
            font = str(requested_family)
        else:
            try:
                resolved = resolve_font_file(str(requested_family), font_weight, font_style)
            except (KeyError, FileNotFoundError) as exc:
                raise ValueError(str(exc)) from exc
            font = str(requested_family)
            font_path = str(resolved["path"])
    elif "." in font or "/" in font:
        font = font.split("/")[-1].split(".")[0]

    align = obj.get("align") or obj.get("text_align") or "left"
    if align in ("start",):
        align = "left"
    elif align in ("end",):
        align = "right"
    elif align not in ("left", "center", "right"):
        align = "left"

    return SpecText(
        text=str(obj.get("text", "")),
        x=float(obj.get("x", 0)),
        y=float(obj.get("y", 0)),
        size_px=size_px,
        font=font,
        font_path=font_path,
        color=_normalize_hex(obj.get("text_color", obj.get("color", "#000000"))),
        align=align,
        opacity=int(obj.get("opacity", 100)),
        rotation=float(obj.get("rotation", 0)),
    )


def _convert_shape(obj: dict) -> SpecShape:
    st = obj.get("shape_type", "rect")
    if st == "tri1":
        st = "tri"
    if st not in ("rect", "oval", "tri"):
        raise ValueError(f"shape_type non supporté : {st}")
    return SpecShape(
        kind=st,
        x=float(obj.get("x", 0)),
        y=float(obj.get("y", 0)),
        w=float(obj.get("width", obj.get("w", 100))),
        h=float(obj.get("height", obj.get("h", 100))),
        fill=_normalize_hex(obj.get("fill_color", obj.get("fill", "#000000"))),
        radius_pct=float(obj.get("radius_pct", 0)),
        opacity=int(obj.get("opacity", 100)),
        rotation=float(obj.get("rotation", 0)),
    )


def _convert_image(obj: dict) -> SpecImage:
    return SpecImage(
        path=obj["path"],
        x=float(obj.get("x", 0)),
        y=float(obj.get("y", 0)),
        w=float(obj.get("width", obj.get("w", 100))),
        h=float(obj.get("height", obj.get("h", 100))),
        opacity=int(obj.get("opacity", 100)),
        rotation=float(obj.get("rotation", 0)),
    )


def _convert_spec(spec: dict) -> Spec:
    c = spec
    canvas = SpecCanvas(
        width=int(c["width"]),
        height=int(c["height"]),
        bg=_normalize_hex(c.get("background_color", "#FFFFFF")),
        margin=float(c.get("margin", 80)),
    )
    objects = []
    for obj in c.get("objects", []):
        kind = obj.get("kind")
        if kind == "text":
            objects.append(_convert_text(obj))
        elif kind == "shape":
            objects.append(_convert_shape(obj))
        elif kind == "image":
            objects.append(_convert_image(obj))
        else:
            raise ValueError(f"kind inconnu : {kind}")
    return Spec(canvas=canvas, objects=objects)


# --- API publique ---

def generate_plp(spec: dict, output_path: Path) -> dict:
    """Génère un PLP via le moteur psd2plp.

    Lève ValueError si le spec est invalide ou si la génération échoue.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() != ".plp":
        raise ValueError("Le nom de fichier doit finir par .plp")

    converted = _convert_spec(spec)
    proj = plp_from_spec(converted, plp_name=output_path.stem)

    # write_plp écrit dans un chemin temporaire puis déplace,
    # pour ne pas laisser de fichier partiel en cas d'erreur
    with tempfile.NamedTemporaryFile(
        suffix=".plp", delete=False, dir=output_path.parent,
    ) as tf:
        tmp = Path(tf.name)
    try:
        _psd2plp_write(proj, tmp, plp_name=output_path.stem)
        tmp.replace(output_path)
    finally:
        tmp.unlink(missing_ok=True)

    n_text = sum(1 for o in proj.objects if o.kind == "text")
    n_shape = sum(1 for o in proj.objects if o.kind == "shape")
    return {
        "path": str(output_path.resolve()),
        "bytes": output_path.stat().st_size,
        "objects": len(proj.objects),
        "text": n_text,
        "shape": n_shape,
        "resources": len(proj.resources),
        "canvas": [proj.width, proj.height],
        "engine": "psd2plp.spec.builder",
        "limitations": [
            "Fonts: embedded subset from lnk-brand (Montserrat, OpenSans). "
            "Le catalogue du plugin ne sert que pour la recherche.",
            "Images: PNG/JPG embarqués dans res/. SVG non supporté.",
            "Effets avancés (ombres, gradients, glow) non générés pour l'instant.",
        ],
    }
