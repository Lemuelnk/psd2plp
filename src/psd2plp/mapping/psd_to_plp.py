from __future__ import annotations
import io
import math
from psd_tools import PSDImage
from PIL import Image
from psd2plp.pixellab.model import PlpProject, PlpObject, PlpResource, argb_to_int
from psd2plp.psd.effects import read_effects


def _layer_png(layer) -> bytes | None:
    try:
        has_mask = getattr(layer, "mask", None) is not None
        if layer.is_group() or has_mask:
            img = layer.composite()
        else:
            img = layer.topil()
    except Exception:
        return None
    if img is None:
        return None
    if img.mode not in ("RGBA", "RGB"):
        img = img.convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _first_run(layer):
    eng = layer.engine_dict or {}
    runs = eng.get("StyleRun", {}).get("RunArray", [])
    if not runs:
        return {}
    return runs[0].get("StyleSheet", {}).get("StyleSheetData", {})


def _text_color(layer) -> int:
    d = _first_run(layer)
    fc = d.get("FillColor")
    if not hasattr(fc, "get"):
        return -1
    v = fc.get("Values")
    if not v or len(v) < 4:
        return -1
    # Format Adobe : [A, R, G, B]
    a = max(0, min(255, int(round(v[0] * 255))))
    r = max(0, min(255, int(round(v[1] * 255))))
    g = max(0, min(255, int(round(v[2] * 255))))
    b = max(0, min(255, int(round(v[3] * 255))))
    return argb_to_int(r, g, b, a)


def _matrix_scale_y(layer) -> float:
    t = tuple(layer.transform)
    c, d = t[2], t[3]
    return (c*c + d*d) ** 0.5


def _matrix_rotation(layer) -> float:
    t = tuple(layer.transform)
    a, b = t[0], t[1]
    import math
    return math.degrees(math.atan2(b, a))


def _text_size(layer, scale, bbox_h) -> float:
    d = _first_run(layer)
    fs = float(d.get("FontSize") or 32.0)
    sy = _matrix_scale_y(layer) or 1.0
    return max(8.0, fs * sy * scale * TEXT_SIZE_FACTOR)


REF_WIDTH = 708

# CALIB2 (PixelLab) : textTextSize = taille em en px du conteneur ; le PSD donne la taille em en px.
TEXT_SIZE_FACTOR = 1.0
# Valeurs de textAlignment vues dans des PLP natifs (constantes Gravity d'Android). A confirmer avec CALIB3.
ALIGN = {"left": 8388659, "center": 17, "right": 53}
ROTATION_EPS = 0.5       # degres
LINE_HEIGHT_EM = 1.2     # hauteur de ligne estimee, pour placer le pivot de rotation


def _justification(layer) -> str:
    """left / center / right (Photoshop : 0 gauche, 1 droite, 2 centre)."""
    try:
        runs = (layer.engine_dict or {}).get("ParagraphRun", {}).get("RunArray", [])
        j = int(runs[0]["ParagraphSheet"]["Properties"].get("Justification", 0))
    except Exception:
        return "left"
    return {1: "right", 2: "center"}.get(j, "left")


def _text_geometry(layer, scale, txt, bbox, doc_w=1080.0) -> dict:
    """Position, largeur de boite, alignement et angle d'un texte PSD (en px du conteneur).

    Sans rotation : gauche = ancre au bord gauche ; centre/droite = boite un peu plus large que
    l'encre, ancree au centre / au bord droit, pour que le texte reste bien place meme si la
    police de remplacement a une autre largeur.
    Avec rotation : PixelLab tourne autour du centre de la boite (CALIB2) ; on centre donc la
    boite sur le centre de l'encre et on centre le texte dedans.
    """
    x0, y0, x1, y1 = bbox
    W, H = x1 - x0, y1 - y0
    em = _text_size(layer, scale, H) / scale
    n_lines = txt.count("\n") + 1
    theta = _matrix_rotation(layer)
    just = _justification(layer)

    if abs(theta) < ROTATION_EPS:
        if just == "left":
            return dict(x=x0 * scale, y=y0 * scale, max_width=-1, alignment=ALIGN["left"], rotation=0.0)
        pad = max(12.0, 0.2 * W)
        if just == "center":
            cx = (x0 + x1) / 2.0
            hw = max(W / 2.0, min(W / 2.0 + pad, cx, doc_w - cx))
            bx, bw = cx - hw, 2.0 * hw
        else:
            bx = max(0.0, x1 - (W + 2 * pad))
            bw = max(x1 - bx, W)
        return dict(x=bx * scale, y=y0 * scale, max_width=int(round(bw * scale)),
                    alignment=ALIGN[just], rotation=0.0)

    t = math.radians(theta)
    c, s_ = abs(math.cos(t)), abs(math.sin(t))
    h = em * LINE_HEIGHT_EM * n_lines
    w = (W - h * s_) / c if c >= s_ else (H - h * c) / s_
    w = max(w, 1.0)
    pad = max(12.0, 0.2 * w)
    bw = w + 2 * pad
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    return dict(x=(cx - bw / 2.0) * scale, y=(cy - h / 2.0) * scale, max_width=int(round(bw * scale)),
                alignment=ALIGN["center"], rotation=theta)


def _group_has_blend(group) -> bool:
    try:
        for sub in group.descendants():
            bm = str(getattr(sub, "blend_mode", "") or "")
            if bm and "NORMAL" not in bm and "PASS_THROUGH" not in bm:
                return True
    except Exception:
        return False
    return False


def convert_psd(psd_path: str, bg_color: int = -1) -> PlpProject:
    psd = PSDImage.open(psd_path)
    scale = REF_WIDTH / psd.width
    container_h = round(psd.height * scale)
    proj = PlpProject(width=psd.width, height=psd.height, bg_color=bg_color)
    proj.raw_template["_container_w"] = int(REF_WIDTH)
    proj.raw_template["_container_h"] = int(container_h)
    used = set()

    def walk(container):
        # psd-tools itère déjà du bas vers le haut
        for layer in list(container):
            if not layer.visible:
                continue
            b = layer.bbox
            w, h = b[2] - b[0], b[3] - b[1]

            if layer.is_group():
                # Composite le groupe s'il contient des blend modes non-NORMAL
                if _group_has_blend(layer):
                    png = _layer_png(layer)
                    if png is not None:
                        rname = f"r{len(used):04d}"
                        used.add(rname)
                        proj.resources.append(PlpResource(name=rname, kind="png", data=png))
                        proj.objects.append(PlpObject(
                            kind="shape",
                            x=b[0] * scale, y=b[1] * scale,
                            width=w * scale, height=h * scale,
                            opacity=int(layer.opacity / 255 * 100),
                            resource_name=rname,
                            image_shape_type=2,
                        ))
                    continue
                walk(layer)
                continue

            kind = type(layer).__name__

            if kind == "TypeLayer":
                txt = (layer.text or "").replace("\r", "\n")
                if not txt.strip():
                    continue
                g = _text_geometry(layer, scale, txt, b, psd.width)
                proj.objects.append(PlpObject(
                    kind="text",
                    x=g["x"], y=g["y"],
                    text=txt,
                    text_size=_text_size(layer, scale, h),
                    text_color=_text_color(layer),
                    opacity=int(layer.opacity / 255 * 100),
                    max_width=g["max_width"],
                    alignment=g["alignment"],
                    rotation=g["rotation"],
                ))
                continue

            # tout le reste → raster PNG
            png = _layer_png(layer)
            if png is None:
                continue
            rname = f"r{len(used):04d}"
            used.add(rname)
            proj.resources.append(PlpResource(name=rname, kind="png", data=png))
            fx = read_effects(layer)
            obj = PlpObject(
                kind="shape",
                x=b[0] * scale, y=b[1] * scale,
                width=w * scale, height=h * scale,
                opacity=int(layer.opacity / 255 * 100),
                resource_name=rname,
                image_shape_type=2,
            )
            if fx.overlay and fx.overlay.enabled:
                obj.fill_color = fx.overlay.color
                obj.use_overlay = True
            proj.objects.append(obj)

    walk(psd)

    # Thumb : composite global (nécessite scikit-image)
    try:
        thumb = psd.composite()
        if thumb is not None:
            if thumb.mode != "RGBA":
                thumb = thumb.convert("RGBA")
            thumb.thumbnail((512, 512))
            buf = io.BytesIO()
            thumb.save(buf, format="PNG", optimize=True)
            proj.raw_template["_thumb_bytes"] = buf.getvalue()
    except Exception:
        pass
    return proj
