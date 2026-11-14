"""Spec -> PlpProject."""
from __future__ import annotations
import io
import os
from pathlib import Path

from PIL import Image

from psd2plp.pixellab.model import PlpProject, PlpObject, PlpResource, argb_to_int
from psd2plp.svg.native_shape import _build_shape_params
from .schema import Spec, SpecText, SpecShape, SpecImage


def _argb_to_rgba(v: int) -> tuple:
    if v < 0:
        v += 1 << 32
    a = (v >> 24) & 0xFF
    r = (v >> 16) & 0xFF
    g = (v >> 8) & 0xFF
    b = v & 0xFF
    return (r, g, b, a)


def _render_shape_png(shape_type: str, w: int, h: int, fill_argb: int,
                       radius_pct: float = 0) -> bytes:
    """Rasterise une forme native en PNG (fallback requis par PixelLab)."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (max(1, w), max(1, h)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rgba = _argb_to_rgba(fill_argb)

    if shape_type == "oval":
        draw.ellipse([(0, 0), (w - 1, h - 1)], fill=rgba)
    elif shape_type == "tri1":
        draw.polygon([(w // 2, 0), (0, h - 1), (w - 1, h - 1)], fill=rgba)
    else:  # rect
        if radius_pct > 0:
            r = int(min(w, h) * radius_pct / 100.0)
            r = max(0, min(r, min(w, h) // 2))
            draw.rounded_rectangle([(0, 0), (w - 1, h - 1)], radius=r, fill=rgba)
        else:
            draw.rectangle([(0, 0), (w - 1, h - 1)], fill=rgba)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


REF_WIDTH = 708
CAP_RATIO = 0.70
ASCENDER_ABOVE_CAP = 0.268

from psd2plp.config import FONTS_DIR


def _hex_to_argb(hex_color: str) -> int:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) >= 6:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        return argb_to_int(r, g, b, 255)
    return -1


def _measure_text_width_px(text: str, font_name: str, size_px: float) -> float | None:
    """Mesure la vraie largeur du texte via PIL, en pixels canvas."""
    ttf = FONTS_DIR / f"{font_name}.ttf"
    if not ttf.exists():
        return None
    try:
        from PIL import ImageFont
        # font_size_em = size_px / CAP_RATIO (size_px est cap-height)
        font_size_em = size_px / CAP_RATIO
        f = ImageFont.truetype(str(ttf), int(round(font_size_em)))
        bbox = f.getbbox(text)
        return float(bbox[2] - bbox[0])
    except Exception:
        return None


def _build_text(o: SpecText, container_w: int, container_h: int,
                 doc_w: float, doc_h: float, add_resource, add_font,
                 ref: str, max_width: float = None) -> PlpObject:
    # Auto-fit : mesure reelle via PIL, puis scale si debordement
    size_px = o.size_px
    final_width = None
    if max_width and max_width > 0 and o.text:
        measured = _measure_text_width_px(o.text, o.font, size_px)
        if measured is None:
            # Fallback heuristique si PIL ne peut pas lire la font
            n_chars = len(o.text)
            measured = n_chars * (size_px / CAP_RATIO) * 0.58
        if measured > max_width:
            size_px = size_px * (max_width / measured) * 0.98
            final_width = _measure_text_width_px(o.text, o.font, size_px)
        else:
            final_width = measured
    # Font
    font_res = add_font(o.font)
    # Size : size_px est une hauteur de capitale en px canvas -> em
    font_size_em = size_px / CAP_RATIO
    # Position X : si align=center, on recentre sur le canvas
    x_canvas = o.x
    if o.align == "center" and final_width is not None:
        x_canvas = (doc_w - final_width) / 2.0
    elif o.align == "right" and final_width is not None:
        x_canvas = doc_w - final_width - (doc_w - (doc_w - 2 * 80)) / 2.0
        # simplifie : aligne au bord droit du canvas moins la marge
        x_canvas = doc_w - final_width - 80

    # Convert canvas -> container
    cx = x_canvas * container_w / doc_w
    cy = o.y * container_h / doc_h
    c_size = font_size_em * container_w / doc_w

    # Couleur principale
    base_color = _hex_to_argb(o.color)
    runs = None
    if o.runs:
        runs = [(int(r["length"]), _hex_to_argb(r["color"])) for r in o.runs]

    # Alignement -> bitfield PixelLab
    align_map = {"left": 8388659, "center": 8388658, "right": 8388657}
    alignment = align_map.get(o.align, 8388659)

    obj = PlpObject(
        kind="text",
        x=cx, y=cy,
        text=o.text,
        text_size=c_size,
        text_color=base_color,
        opacity=o.opacity,
        rotation=o.rotation,
        reference=ref,
        font_resource=font_res,
        alignment=alignment,
    )
    if runs:
        obj.text_runs = runs
    return obj


def _build_shape(o: SpecShape, container_w: int, container_h: int,
                  doc_w: float, doc_h: float, add_resource, ref: str) -> PlpObject:
    # PixelLab utilise le referentiel 708 pour les bounds des formes natives
    x0_pct = o.x / doc_w * 100.0
    y0_pct = o.y / doc_h * 100.0
    x1_pct = (o.x + o.w) / doc_w * 100.0
    y1_pct = (o.y + o.h) / doc_h * 100.0
    vc = [f"{x0_pct:.4f}", f"{y0_pct:.4f}", f"{x1_pct:.4f}", f"{y1_pct:.4f}"]

    shape_type = {"rect": "rect", "oval": "oval", "tri": "tri1"}[o.kind]
    fill = _hex_to_argb(o.fill)
    # Clamp radius : max 50% du plus petit cote
    radius = max(0.0, min(o.radius_pct, 50.0))
    params = _build_shape_params(shape_type, vc, fill, radius)

    cx = o.x * container_w / doc_w
    cy = o.y * container_h / doc_h
    cw = o.w * container_w / doc_w
    ch = o.h * container_h / doc_h

    # PixelLab EXIGE un PNG fallback meme pour les formes natives.
    # On rasterise avec PIL a une taille raisonnable pour ne pas exploser.
    png_w = max(2, int(round(o.w)))
    png_h = max(2, int(round(o.h)))
    # Limite pour eviter des PNG gigantesques
    max_dim = 2048
    if png_w > max_dim or png_h > max_dim:
        ratio = max_dim / max(png_w, png_h)
        png_w = max(2, int(png_w * ratio))
        png_h = max(2, int(png_h * ratio))
    png = _render_shape_png(shape_type, png_w, png_h, fill, radius)
    res_name = add_resource(png)

    obj = PlpObject(
        kind="shape",
        x=cx, y=cy, width=cw, height=ch,
        opacity=o.opacity,
        rotation=o.rotation,
        image_shape_type=5,
        reference=ref,
        fill_color=fill,
        resource_name=res_name,
    )
    obj.qUDmYrz = params
    return obj


def _build_image(o: SpecImage, container_w: int, container_h: int,
                  doc_w: float, doc_h: float, add_resource, ref: str) -> PlpObject:
    src = Path(o.path)
    if not src.exists():
        raise FileNotFoundError(f"Image introuvable : {o.path}")
    raw = src.read_bytes()
    # Verifier que c'est bien une image
    try:
        Image.open(io.BytesIO(raw)).verify()
    except Exception:
        raise ValueError(f"Pas une image valide : {o.path}")
    res = add_resource(raw)

    cx = o.x * container_w / doc_w
    cy = o.y * container_h / doc_h
    cw = o.w * container_w / doc_w
    ch = o.h * container_h / doc_h

    return PlpObject(
        kind="shape",
        x=cx, y=cy, width=cw, height=ch,
        opacity=o.opacity,
        rotation=o.rotation,
        image_shape_type=2,
        resource_name=res,
        reference=ref,
    )


def plp_from_spec(spec: Spec, plp_name: str = "untitled") -> PlpProject:
    doc_w = spec.canvas.width
    doc_h = spec.canvas.height
    container_w = REF_WIDTH
    container_h = round(REF_WIDTH * doc_h / doc_w)

    proj = PlpProject(
        width=int(doc_w),
        height=int(doc_h),
        bg_color=_hex_to_argb(spec.canvas.bg),
    )
    proj.raw_template["_container_w"] = container_w
    proj.raw_template["_container_h"] = int(container_h)

    used_res = set()
    used_fonts = {}

    def add_resource(raw: bytes) -> str:
        name = f"r{len(used_res):04d}"
        used_res.add(name)
        proj.resources.append(PlpResource(name=name, kind="png", data=raw))
        return name

    def add_font(font_name: str) -> str | None:
        if font_name in used_fonts:
            return used_fonts[font_name]
        ttf = FONTS_DIR / f"{font_name}.ttf"
        if not ttf.exists():
            return None
        name = f"r{len(used_res):04d}"
        used_res.add(name)
        proj.resources.append(PlpResource(name=name, kind="ttf", data=ttf.read_bytes()))
        used_fonts[font_name] = name
        return name

    margin_px = spec.canvas.margin
    max_text_w = doc_w - 2 * margin_px

    for i, obj in enumerate(spec.objects):
        ref = f"s{i:04d}"
        if isinstance(obj, SpecText):
            plp_obj = _build_text(obj, container_w, container_h, doc_w, doc_h,
                                   add_resource, add_font, ref,
                                   max_width=max_text_w)
        elif isinstance(obj, SpecShape):
            plp_obj = _build_shape(obj, container_w, container_h, doc_w, doc_h,
                                    add_resource, ref)
        elif isinstance(obj, SpecImage):
            plp_obj = _build_image(obj, container_w, container_h, doc_w, doc_h,
                                    add_resource, ref)
        else:
            continue
        proj.objects.append(plp_obj)

    # Thumb : on rasterise un canvas simple (bg + objets composes via PIL)
    _build_thumb(proj, spec)

    return proj


def _build_thumb(proj: PlpProject, spec: Spec):
    """Genere un thumb composite simple via PIL (sans SVG).
    Estime : bg color + rectangles de toutes les shapes pour donner un apercu.
    """
    try:
        W = min(spec.canvas.width, 512)
        H = int(min(spec.canvas.height, 512) * spec.canvas.height / spec.canvas.width)
        img = Image.new("RGBA", (W, H), _argb_to_rgba(_hex_to_argb(spec.canvas.bg)))
        # TODO : composer les shapes/text pour un thumb plus fidele
        # Pour l'instant c'est juste le bg, ce qui suffit pour lister
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        proj.raw_template["_thumb_bytes"] = buf.getvalue()
    except Exception:
        pass


def _argb_to_rgba(v: int) -> tuple:
    if v < 0:
        v += 1 << 32
    a = (v >> 24) & 0xFF
    r = (v >> 16) & 0xFF
    g = (v >> 8) & 0xFF
    b = v & 0xFF
    return (r, g, b, a)
