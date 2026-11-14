"""SVG enrichi (data-plp-*) -> PlpProject.

Parcours unique de l'arbre SVG, ordre DOM préservé.
- <g data-plp-text>     -> PlpObject texte natif
- <image base64>         -> PlpObject shape (PNG embarqué)
- <rect plein canvas>    -> bgColor du canvas
- <path>/<polygon>/<svg> -> PlpObject shape (raster)
- <g>                    -> récursion
"""
from __future__ import annotations
import base64
import copy
import io
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

from psd2plp.pixellab.model import PlpProject, PlpObject, PlpResource, argb_to_int
from converter.merge_lines import merge_segments_into_lines


def _parse_matrix_ty(transform_str):
    """Retourne le ty (baseline) d'un 'matrix(a b c d e f)'."""
    if not transform_str:
        return None
    m = re.search(r"matrix\(([^)]+)\)", transform_str)
    if m:
        parts = [float(x) for x in m.group(1).replace(",", " ").split()]
        if len(parts) == 6:
            return parts[5]
    return None


def _parse_translate_y(transform_str):
    """Retourne le ty d'un 'translate(x y)'."""
    if not transform_str:
        return 0.0
    m = re.search(r"translate\(([^)]+)\)", transform_str)
    if m:
        parts = [float(x) for x in m.group(1).replace(",", " ").split()]
        if len(parts) >= 2:
            return parts[1]
        if len(parts) == 1:
            return 0.0
    return 0.0


def _extract_baseline_canvas(elem, transforms):
    """Baseline en px canvas. Combine matrix ty + translates parents."""
    # Ty du matrix sur l'element data-plp-text lui-meme
    own_ty = _parse_matrix_ty(elem.get("transform"))
    # Somme des translate Y des parents
    parent_ty = sum(_parse_translate_y(t) for t in transforms if t)
    if own_ty is None:
        # Fallback : si pas de matrix, on retourne None (bbox sera utilisee)
        return None
    return own_ty + parent_ty


REF_WIDTH = 708
SVG_NS = "http://www.w3.org/2000/svg"

# Métriques Montserrat (upm=1000) : capHeight=700, ascender=968, descender=-251
CAP_RATIO = 0.70             # capHeight / em
ASCENDER_ABOVE_CAP = 0.268   # (ascender - capHeight) / em

# Dossier des fonts subset à embarquer dans res/
FONTS_DIR = Path(os.environ.get(
    "LNK_BRAND_FONTS",
    "/storage/emulated/0/LNK_WORKS/lnk-brand/03-assets/fonts/subset",
))


def _tag(elem) -> str:
    return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag


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


def _parse_viewbox(vb: str) -> tuple:
    parts = [float(x) for x in vb.replace(",", " ").split()]
    return tuple(parts[:4])


def _wrap_with_transforms(elem, transforms, vb_w, vb_h) -> bytes:
    """Enveloppe elem avec les transforms parents empilées."""
    wrapper = ET.Element(
        f"{{{SVG_NS}}}svg",
        {"viewBox": f"0 0 {vb_w} {vb_h}", "width": str(vb_w), "height": str(vb_h)},
    )
    current = wrapper
    for t in transforms:
        g = ET.SubElement(current, f"{{{SVG_NS}}}g", {"transform": t})
        current = g
    current.append(copy.deepcopy(elem))
    return ET.tostring(wrapper, encoding="utf-8")


def _rasterize_bytes(raw: bytes, vb_w: int, vb_h: int) -> bytes | None:
    import cairosvg
    try:
        return cairosvg.svg2png(
            bytestring=raw, output_width=vb_w, output_height=vb_h,
        )
    except Exception:
        return None


def _crop_to_content(png_bytes):
    try:
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        bbox = img.getbbox()
        if bbox is None:
            return None
        cropped = img.crop(bbox)
        buf = io.BytesIO()
        cropped.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), bbox
    except Exception:
        return None


def _bbox_in_canvas(elem, transforms, doc_w, doc_h):
    """Rasterise elem avec ses transforms et retourne (png, bbox) en px canvas."""
    wrapped = _wrap_with_transforms(elem, transforms, doc_w, doc_h)
    raw = _rasterize_bytes(wrapped, int(doc_w), int(doc_h))
    if not raw:
        return None
    return _crop_to_content(raw)


def _svg_inner_transform(elem) -> str | None:
    """Transform pour un <svg> imbriqué (x/y + viewBox + width/height)."""
    x = float(elem.get("x", "0").replace("px", ""))
    y = float(elem.get("y", "0").replace("px", ""))
    w_str = elem.get("width")
    h_str = elem.get("height")
    vb = elem.get("viewBox")
    if vb and w_str and h_str:
        vbp = _parse_viewbox(vb)
        sx = float(w_str.replace("px", "")) / vbp[2]
        sy = float(h_str.replace("px", "")) / vbp[3]
        return (f"translate({x} {y}) scale({sx} {sy}) "
                f"translate({-vbp[0]} {-vbp[1]})")
    if x != 0 or y != 0:
        return f"translate({x} {y})"
    return None


def _walk(elem, transforms, doc_w, doc_h, container_w, container_h,
          add_resource, add_font_resource, out_objects, text_segments, ref_counter, proj):
    tag = _tag(elem)

    # Cas 1 : texte natif
    if tag == "g" and elem.get("data-plp-text") is not None:
        text = elem.get("data-plp-text", "")
        size_px = float(elem.get("data-plp-size", "0"))
        color = _hex_to_argb(elem.get("data-plp-color", "#000"))
        if not text or size_px <= 0:
            return
        result = _bbox_in_canvas(elem, transforms, doc_w, doc_h)
        if not result:
            return
        _, bbox = result
        font_size_canvas = size_px / CAP_RATIO

        # Baseline fiable : via transform matrix si possible
        baseline_canvas = _extract_baseline_canvas(elem, transforms)
        if baseline_canvas is not None:
            # em_top = baseline - ascender_em * font_size (font_size en em,
            # ascender = 0.968 em pour Montserrat)
            em_top_canvas = baseline_canvas - 0.968 * font_size_canvas
        else:
            # Fallback bbox (moins precis pour les accents)
            em_top_canvas = bbox[1] - ASCENDER_ABOVE_CAP * font_size_canvas
            baseline_canvas = em_top_canvas + 0.968 * font_size_canvas

        font_name = elem.get("data-plp-font", "")
        font_res = add_font_resource(font_name) if font_name else None
        text_segments.append({
            "bbox": bbox,
            "text": text,
            "color": color,
            "size_px": size_px,
            "font_size_canvas": font_size_canvas,
            "em_top_canvas": em_top_canvas,
            "baseline_canvas": baseline_canvas,
            "font_name": font_name,
            "font_res": font_res,
        })
        return

    # Cas 2 : image base64 (logo)
    if tag == "image":
        href = elem.get("href") or elem.get("xlink:href") or ""
        m = re.match(r"data:image/png;base64,(.+)", href)
        if not m:
            return
        result = _bbox_in_canvas(elem, transforms, doc_w, doc_h)
        if not result:
            return
        png, bbox = result
        res = add_resource(png)
        ref_counter[0] += 1
        x0, y0, x1, y1 = bbox
        out_objects.append(PlpObject(
            kind="shape",
            x=x0 * container_w / doc_w,
            y=y0 * container_h / doc_h,
            width=(x1 - x0) * container_w / doc_w,
            height=(y1 - y0) * container_h / doc_h,
            opacity=100,
            resource_name=res,
            image_shape_type=2,
            reference=f"i{ref_counter[0]:04d}",
        ))
        return

    # Cas 3 : rect plein canvas = bg
    if tag == "rect" and not transforms:
        rx = float(elem.get("x", "0"))
        ry = float(elem.get("y", "0"))
        rw = float(elem.get("width", "0"))
        rh = float(elem.get("height", "0"))
        if rx <= 1 and ry <= 1 and abs(rw - doc_w) < 2 and abs(rh - doc_h) < 2:
            fill = elem.get("fill", "")
            if fill.startswith("#"):
                proj.bg_color = _hex_to_argb(fill)
            return

    # Cas 4 : SVG imbriqué -> raster
    if tag == "svg":
        inner_t = _svg_inner_transform(elem)
        new_stack = transforms + [inner_t] if inner_t else transforms
        # Rasterise le SVG imbriqué lui-même (avec les transforms accumulés)
        wrapped = _wrap_with_transforms(elem, transforms, doc_w, doc_h)
        raw = _rasterize_bytes(wrapped, int(doc_w), int(doc_h))
        if raw:
            cropped = _crop_to_content(raw)
            if cropped:
                png, bbox = cropped
                res = add_resource(png)
                ref_counter[0] += 1
                x0, y0, x1, y1 = bbox
                out_objects.append(PlpObject(
                    kind="shape",
                    x=x0 * container_w / doc_w,
                    y=y0 * container_h / doc_h,
                    width=(x1 - x0) * container_w / doc_w,
                    height=(y1 - y0) * container_h / doc_h,
                    opacity=100,
                    resource_name=res,
                    image_shape_type=2,
                    reference=f"d{ref_counter[0]:04d}",
                ))
        return

    # Cas 5 : path / polygon / etc -> raster
    if tag in ("path", "polygon", "ellipse", "circle", "line", "polyline"):
        result = _bbox_in_canvas(elem, transforms, doc_w, doc_h)
        if not result:
            return
        png, bbox = result
        res = add_resource(png)
        ref_counter[0] += 1
        x0, y0, x1, y1 = bbox
        out_objects.append(PlpObject(
            kind="shape",
            x=x0 * container_w / doc_w,
            y=y0 * container_h / doc_h,
            width=(x1 - x0) * container_w / doc_w,
            height=(y1 - y0) * container_h / doc_h,
            opacity=100,
            resource_name=res,
            image_shape_type=2,
            reference=f"d{ref_counter[0]:04d}",
        ))
        return

    # Cas 6 : <g> sans data -> récursion
    if tag == "g":
        local_t = elem.get("transform")
        new_stack = transforms + [local_t] if local_t else transforms
        for child in list(elem):
            _walk(child, new_stack, doc_w, doc_h, container_w, container_h,
                  add_resource, add_font_resource, out_objects, text_segments, ref_counter, proj)
        return


def svg_to_plp(svg_path, bg_color: int = -1) -> PlpProject:
    svg_path = Path(svg_path)
    tree = ET.parse(str(svg_path))
    root = tree.getroot()

    vb = root.get("viewBox") or f"0 0 {root.get('width')} {root.get('height')}"
    doc_w, doc_h = _parse_viewbox(vb)[2:]

    container_w = REF_WIDTH
    container_h = round(REF_WIDTH * doc_h / doc_w)

    proj = PlpProject(
        width=int(round(doc_w)),
        height=int(round(doc_h)),
        bg_color=bg_color,
    )
    proj.raw_template["_container_w"] = container_w
    proj.raw_template["_container_h"] = int(container_h)

    used = set()
    font_res_map = {}

    def add_resource(png):
        name = f"r{len(used):04d}"
        used.add(name)
        proj.resources.append(PlpResource(name=name, kind="png", data=png))
        return name

    def add_font_resource(font_name):
        """Charge le TTF subset et l'ajoute comme ressource. Retourne le nom."""
        if font_name in font_res_map:
            return font_res_map[font_name]
        if not FONTS_DIR.exists():
            return None
        ttf = FONTS_DIR / f"{font_name}.ttf"
        if not ttf.exists():
            return None
        name = f"r{len(used):04d}"
        used.add(name)
        proj.resources.append(PlpResource(
            name=name, kind="ttf", data=ttf.read_bytes(),
        ))
        font_res_map[font_name] = name
        return name

    ref_counter = [0]
    text_segments = []
    for child in list(root):
        _walk(child, [], doc_w, doc_h, container_w, container_h,
              add_resource, add_font_resource, proj.objects, text_segments,
              ref_counter, proj)

    # Fusion des segments en lignes (multi-couleurs -> un seul PlpObject)
    merged = merge_segments_into_lines(text_segments)
    for line in merged:
        if line is None:
            continue
        ref_counter[0] += 1
        bbox = line["bbox"]
        obj = PlpObject(
            kind="text",
            x=bbox[0] * container_w / doc_w,
            y=line["em_top_canvas"] * container_h / doc_h,
            text=line["text"],
            text_size=line["font_size_canvas"] * container_w / doc_w,
            text_color=line["runs"][0][1] if line["runs"] else -1,
            opacity=100,
            reference=f"t{ref_counter[0]:04d}",
            font_resource=line.get("font_res"),
        )
        obj.text_runs = line["runs"]
        proj.objects.append(obj)

    # Thumb
    try:
        import cairosvg
        full = cairosvg.svg2png(url=str(svg_path),
                                 output_width=int(doc_w), output_height=int(doc_h))
        thumb = Image.open(io.BytesIO(full)).convert("RGBA")
        thumb.thumbnail((512, 512))
        has_alpha = False
        try:
            has_alpha = thumb.getchannel("A").getextrema()[0] < 255
        except Exception:
            pass
        buf = io.BytesIO()
        if has_alpha:
            thumb.save(buf, format="PNG", optimize=True)
        else:
            thumb.convert("RGB").save(buf, format="JPEG", quality=80)
        proj.raw_template["_thumb_bytes"] = buf.getvalue()
    except Exception:
        pass

    return proj
