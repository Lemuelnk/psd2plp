"""Mapping SVG primitive -> forme native PixelLab (shapeImageShapeType=5)."""
from __future__ import annotations
import xml.etree.ElementTree as ET


# Template décodé depuis les 3 samples (Square/Cercle/Tri)
NATIVE_TEMPLATE = {
    "mrdCt2Pon": {
        "5CVh": "v2;3;50/0/50/100;-3355444/-12303292;0.0/1.0",
        "9vwh": -1,  # couleur fill ARGB
        "A67W": "v2;3;50/0/50/100;-3355444/-12303292;0.0/1.0",
        "JrtC": 1, "NyqG": 1, "UJ3K": -16777216,
        "vtf8": 0, "yMR4": 0,
    },
    "wAmp2k": 0,
    "vCScn1x": ["0.0", "0.0", "100.0", "100.0"],  # bounds %
    "3GsP": 255,
    "UTRQ": 0,
    "mfp2JbFB": "rect",  # type
    "2Xskb7": 0,  # radius
    "3JaWTe": 255,
}


def _tag(elem) -> str:
    return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag


def _attr_float(elem, name, default=0.0) -> float:
    v = elem.get(name)
    if v is None:
        return default
    try:
        return float(v.strip().replace("px", "").replace("%", ""))
    except ValueError:
        return default


def _fill_color(elem) -> int | None:
    """Retourne ARGB signé ou None si pas de fill."""
    fill = elem.get("fill")
    if fill is None:
        return -16777216  # noir par défaut
    if fill in ("none", "transparent"):
        return None
    if fill.startswith("#"):
        h = fill[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            v = (255 << 24) | (r << 16) | (g << 8) | b
            return v - (1 << 32) if v >= (1 << 31) else v
    # rgb(r,g,b)
    if fill.startswith("rgb("):
        try:
            nums = fill[4:-1].split(",")
            r = int(nums[0].strip())
            g = int(nums[1].strip())
            b = int(nums[2].strip())
            v = (255 << 24) | (r << 16) | (g << 8) | b
            return v - (1 << 32) if v >= (1 << 31) else v
        except Exception:
            pass
    return -16777216


def try_native_shape(elem, canvas_w: float, canvas_h: float,
                      container_w: int, container_h: int) -> dict | None:
    """Si l'element est une forme native mappable, retourne les params.
    Sinon None (il faudra rasteriser)."""
    tag = _tag(elem)
    fill = _fill_color(elem)
    if fill is None:
        return None  # pas de fill, inutile

    if tag == "rect":
        x = _attr_float(elem, "x")
        y = _attr_float(elem, "y")
        w = _attr_float(elem, "width")
        h = _attr_float(elem, "height")
        rx = _attr_float(elem, "rx", 0.0)
        ry = _attr_float(elem, "ry", rx)
        radius = max(rx, ry)
        # radius en % du plus petit cote
        min_side = min(w, h) if min(w, h) > 0 else 1
        radius_pct = radius / min_side * 100.0

        shape_type = "rect"
        if radius_pct > 0.5:
            shape_type = "rect"  # radius géré par 2Xskb7
        vc = _bounds_pct(x, y, w, h, canvas_w, canvas_h)
        return _build_shape_params("rect", vc, fill, radius_pct)

    if tag == "circle":
        cx = _attr_float(elem, "cx")
        cy = _attr_float(elem, "cy")
        r = _attr_float(elem, "r")
        vc = _bounds_pct(cx - r, cy - r, 2 * r, 2 * r, canvas_w, canvas_h)
        return _build_shape_params("oval", vc, fill, 0)

    if tag == "ellipse":
        cx = _attr_float(elem, "cx")
        cy = _attr_float(elem, "cy")
        rx = _attr_float(elem, "rx")
        ry = _attr_float(elem, "ry")
        vc = _bounds_pct(cx - rx, cy - ry, 2 * rx, 2 * ry, canvas_w, canvas_h)
        return _build_shape_params("oval", vc, fill, 0)

    return None


def _bounds_pct(x, y, w, h, canvas_w, canvas_h) -> list[str]:
    x0 = x / canvas_w * 100.0
    y0 = y / canvas_h * 100.0
    x1 = (x + w) / canvas_w * 100.0
    y1 = (y + h) / canvas_h * 100.0
    return [f"{x0:.4f}", f"{y0:.4f}", f"{x1:.4f}", f"{y1:.4f}"]


def _build_shape_params(shape_type: str, vc: list[str],
                        fill_argb: int, radius_pct: float) -> dict:
    import copy
    params = copy.deepcopy(NATIVE_TEMPLATE)
    params["mfp2JbFB"] = shape_type
    params["vCScn1x"] = vc
    params["mrdCt2Pon"]["9vwh"] = fill_argb
    params["2Xskb7"] = int(round(radius_pct))
    return params


def native_shape_as_plp_object(params: dict, canvas_w: float, canvas_h: float,
                                ref: str, container_w: int, container_h: int):
    """Construit les donnees d'un PlpObject natif (shapeImageShapeType=5)."""
    from psd2plp.pixellab.model import PlpObject

    # Convertit les bounds % en coordonnees container
    x0, y0, x1, y1 = [float(v) for v in params["vCScn1x"]]
    cx0 = x0 / 100.0 * container_w
    cy0 = y0 / 100.0 * container_h
    cx1 = x1 / 100.0 * container_w
    cy1 = y1 / 100.0 * container_h

    obj = PlpObject(
        kind="shape",
        x=cx0, y=cy0,
        width=cx1 - cx0,
        height=cy1 - cy0,
        opacity=100,
        image_shape_type=5,
        reference=ref,
    )
    # Stocke les params qUDmYrz pour que le writer les écrive
    obj.qUDmYrz = params
    return obj
