from __future__ import annotations
import io
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
    return max(8.0, fs * sy * scale * 0.68)


REF_WIDTH = 708


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
                proj.objects.append(PlpObject(
                    kind="text",
                    x=b[0] * scale, y=b[1] * scale,
                    text=txt,
                    text_size=_text_size(layer, scale, h),
                    text_color=_text_color(layer),
                    opacity=int(layer.opacity / 255 * 100),
                    max_width=-1,
                    rotation=_matrix_rotation(layer),
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
