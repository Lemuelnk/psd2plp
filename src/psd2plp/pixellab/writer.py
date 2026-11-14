from __future__ import annotations
import io, json, random, string, zipfile
from pathlib import Path
from PIL import Image
from .model import PlpProject, PlpObject, PlpResource

A = string.ascii_letters + string.digits


def _rname(used):
    while True:
        n = "".join(random.choices(A, k=4))
        if n not in used:
            used.add(n); return n


def _rref(used):
    while True:
        n = "".join(random.choices(A, k=5))
        if n not in used:
            used.add(n); return n


DEFAULT_SHAPE = {
    "shapeOpacityShadowInclude": False, "shapeThreeDStokeInclude": True,
    "DL4VOEC": 0, "shapeThreeDDepthColorFill": -16776961,
    "shapeEmbossIntensity": 80, "objectHidden": False,
    "shapeStrokeColor": -1, "shapeStrokeWidth": 2,
    "shapeRemoveColorCT": ["-1", "100"], "objectLocked": False,
    "shapeThreeDDepthColorAutomatic": True,
    "shapeThreeDLightingSpecularHardness": 80, "shapeEmbossEnabled": False,
    "shapeImageSrcV2": True, "shapeInnerEnabled": False,
    "sBmE43": False, "sDFkd3": {"imgSrcAssetFolder": False},
    "shapeShadowColor": -16777216, "shapeOldContainerHeight": 1001,
    "shapeShadowEnabled": False, "shapeShadowDx": 0, "shapeShadowDy": 0,
    "shapeEmbossAmbient": 70, "shapeColorOverlayColor": -65536,
    "shapeThreeDLightingShadow": 10, "ShpThObAng": 45,
    "shapeImageCropInfo": {"mHbGHc": False, "n7gV4v": False, "cropInfCirc": False,
        "cropInfoPorLeft": 0, "cropInfRot": 0, "cropInfoPorTop": 0,
        "cropInfoPorBottom": 100000, "cropInfoPorRight": 100000},
    "shapeOldContainerWidth": 708, "shapeRotationX": 0, "shapeRotationY": 0,
    "shapeStrokeEnabled": False,
    "sCOG": "v2;3;50/0/50/100;-3355444/-12303292;0.0/1.0",
    "5cAUm": False, "Erasi": 0,
    "J4lv1": {"mHbGHc": False, "n7gV4v": False, "cropInfCirc": False,
        "cropInfoPorLeft": 0, "cropInfRot": 0, "cropInfoPorTop": 0,
        "cropInfoPorBottom": 100000, "cropInfoPorRight": 100000},
    "M3XGT": 10, "sCOfT": 1, "shapeInnerRadius": 10,
    "shapeThreeDDepthDarken": 30, "shapeRotation": "0",
    "shapeRemoveColorBlur": 0, "shapeThreeDEnabled": False,
    "shapeThreeDViewType": 1, "shapePerspectiveP1X": 0, "shapePerspectiveP1Y": 0,
    "shapePerspectiveP2X": 1000, "shapePerspectiveP2Y": 0,
    "shapePerspectiveP3X": 1000, "shapePerspectiveP3Y": 1000,
    "shapePerspectiveP4X": 0, "shapePerspectiveP4Y": 1000,
    "shapePerspectiveEnabled": False, "shapeImageShapeType": 2,
    "shapeInnerDx": 0, "shapeInnerDy": 0, "shapeEmbossLightAngle": 90,
    "shapeThreeDDepthFillType": 1, "shapeThreeDLightingIntensity": 80,
    "shapeThreeDDepth": 25, "shapeThreeDLightingEnabled": True,
    "shapeInnerColor": -16777216, "shapeEmbossHardness": 20,
    "gnnMUtYI": 0, "shapeEmbossBevel": 40, "wYdWdLnz": 0,
    "shapeThreeDDepthGradientFillV2": "v2;3;50/0/50/100;-3355444/-12303292;0.0/1.0",
    "shapeRemoveColorEnabled": False, "shapeOpacity": 100,
    "shapeColorOverlayEnabled": False, "shapeShadowRadius": "10.0",
}

DEFAULT_TEXT = {
    "textOpacity": 100, "textJustify": False, "textInnerEnabled": False,
    "textOuterDx": 0, "textOuterDy": 0, "textReflectionOffset": 0,
    "textThreeDDepthFillType": 1, "textThreeDDepth": 25,
    "textThreeDViewType": 1, "textEmbossBevel": 30, "ZpG28v": 0,
    "objectHidden": False, "textBgEnabled": False, "textBgPaddingLeft": 0,
    "objectLocked": False, "textThreeDLightingIntensity": 80,
    "textEmbossHardness": 40, "textThreeDShadowTransparency": 40,
    "textLetterSpacing": 0, "deNYb4": 0, "textTextSize": "32.0",
    "textThreeDDepthGradientFillV2": "v2;3;50/0/50/100;-3355444/-12303292;0.0/1.0",
    "textThreeDObAn": 45, "textBgPaddingRight": 0, "textPerEn": False,
    "textThreeDLightingEnabled": True, "textUnder": {},
    "textBgColor": -1275068416, "textBold": {},
    "textRotationX": 0, "textRotationY": 0, "textEmbossEnabled": False,
    "textThreeDDepthDarken": 30,
    "textTextureImageSrc": {"imgSrcAssetFolder": False},
    "textTextureImageSrcV2": True, "textThreeDShadowBlur": 25,
    "textTextCurve": 0, "shapeOldContainerHeight": 1001,
    "textThreeDLightingSpecularHardness": 50,
    "textBgBorderRadius": 0, "textThreeDShadowExpand": 10,
    "textRotation": "0", "textTextureMaintainAspect": False,
    "textEmbossAmbient": 50, "textEmbossIncludeStroke": False,
    "textStrokeColor": -16777216, "textStrokeWidth": "4.0",
    "textThreeDDepthColorAutomatic": True, "textThreeDShadowColor": -16777216,
    "shapeOldContainerWidth": 708, "textBgPaddingTop": 0,
    "textBgFillType": 1, "B8aw": True, "textOuterRadius": "10.0",
    "textEmbossIntensity": 60, "textThreeDStokeInclude": True,
    "textStrokeEnabled": False,
    "textBgGradientV2": "v2;3;50/0/50/100;-3355444/-12303292;0.0/1.0",
    "textBgPaddingBottom": 0, "textOpacityShadowInclude": False,
    "textStrokeFillType": 1, "textThreeDDepthColorFill": -16776961,
    "textStrokeGradientV2": "v2;3;50/0/50/100;-3355444/-12303292;0.0/1.0",
    "textLineSpacing": 0, "textThreeDShadowEnabled": False,
    "textTextGradientV2": "v2;3;50/0/50/100;-3355444/-12303292;0.0/1.0",
    "textReflectionEnabled": False, "textInnerColor": -16777216,
    "textThreeDEnabled": False, "textInnerDx": "0.0", "textInnerDy": "0.0",
    "textTextureImageCropInfo": {"mHbGHc": False, "n7gV4v": False, "cropInfCirc": False,
        "cropInfoPorLeft": 0, "cropInfRot": 0, "cropInfoPorTop": 0,
        "cropInfoPorBottom": 100000, "cropInfoPorRight": 100000},
    "textOuterGlowEnabled": False, "textTextureScale": 10,
    "textInnerRadius": "3.0", "textItalic": {},
    "textOuterColor": -16777216, "textPerP1X": 0, "textPerP1Y": 0,
    "textPerP2X": 1000, "textPerP2Y": 0, "textPerP3X": 1000, "textPerP3Y": 1000,
    "textPerP4X": 0, "textPerP4Y": 1000, "textTextFillType": 1,
    "textThreeDLightingShadow": 40, "textAlignment": 8388659,
    "textEmbossLightAngle": 90, "tLSWrds": False, "textOuterEnabled": False,
}


def _build_shape(o, name, cw=708, ch=1001):
    d = dict(DEFAULT_SHAPE)
    d.update({
        "shapeOldContainerWidth": cw, "shapeOldContainerHeight": ch,
        "shapeX": int(round(o.x)), "shapeY": int(round(o.y)),
        "shapeWidth": str(o.width), "shapeHeight": str(o.height),
        "shapeRotation": str(o.rotation), "shapeOpacity": o.opacity,
        "objectHidden": o.hidden, "objectLocked": o.locked,
        "shapeReference": o.reference,
        "shapeImageShapeType": o.image_shape_type,
        "shapeColorOverlayColor": o.fill_color,
        "shapeColorOverlayEnabled": bool(getattr(o, "use_overlay", False)),
    })
    if o.resource_name:
        d["shapeImageSrc"] = {
            "imgSrcPath": f"/storage/emulated/0/pixelLab/presets/{name}/res/{o.resource_name}",
            "imgSrcSourceType": "local_file", "imgSrcAssetFolder": False,
        }
    if getattr(o, "qUDmYrz", None):
        d["qUDmYrz"] = o.qUDmYrz
    return d


def _build_text(o, name, cw=708, ch=1001):
    d = dict(DEFAULT_TEXT)
    n = len(o.text)
    d.update({
        "shapeOldContainerWidth": cw, "shapeOldContainerHeight": ch,
        "shapeX": int(round(o.x)), "shapeY": int(round(o.y)),
        "textRotation": str(o.rotation), "textOpacity": o.opacity,
        "objectHidden": o.hidden, "objectLocked": o.locked,
        "textReference": o.reference, "textTextString": o.text,
        "textTextSize": str(o.text_size),
        "textLetterSpacing": o.letter_spacing,
        "textLineSpacing": o.line_spacing,
        "textMaxWidth": o.max_width, "textAlignment": o.alignment,
    })

    # Couleur(s) : pattern PixelLab = interval1 est le fallback global
    # (start=0, end=N, couleur du premier run). Les runs suivants sont des
    # overrides spécifiques (interval2, interval3...).
    runs = getattr(o, "text_runs", None)
    if runs and len(runs) > 1:
        base_color = int(runs[0][1])
        intervals = {
            "interval1": {
                "textsIntervalsStart": 0,
                "textsIntervalsEnd": n,
                "textsIntervalsColor": base_color,
            },
        }
        # Overrides : chaque run dont la couleur diffère de la base
        idx = 2
        start = 0
        for length, color in runs:
            end = start + int(length)
            if int(color) != base_color:
                intervals[f"interval{idx}"] = {
                    "textsIntervalsStart": start,
                    "textsIntervalsEnd": end,
                    "textsIntervalsColor": int(color),
                }
                idx += 1
            start = end
        d["textTextColor"] = intervals
    else:
        d["textTextColor"] = {"interval1": {
            "textsIntervalsStart": 0, "textsIntervalsEnd": n,
            "textsIntervalsColor": o.text_color,
        }}
    if o.font_resource:
        d["textTextFont"] = {"interval1": {
            "textsIntervalsStart": 0, "textsIntervalsEnd": n,
            "textsIntervalsFont": f"/storage/emulated/0/pixelLab/presets/{name}/res/{o.font_resource}"}}
    else:
        d["textTextFont"] = {}
    return d


def write_plp(project, out_path, plp_name=None):
    out_path = Path(out_path)
    plp_name = plp_name or out_path.stem
    used_res, used_ref, res_map = set(), set(), {}
    for r in project.resources:
        res_map[r.name] = _rname(used_res)

    cw = project.raw_template.get("_container_w", 708)
    ch = project.raw_template.get("_container_h", 1001)

    bundle, ids = {}, []
    si = ti = 0
    for o in project.objects:
        o.reference = o.reference or _rref(used_ref)
        if o.resource_name in res_map:
            o.resource_name = res_map[o.resource_name]
        if o.font_resource in res_map:
            o.font_resource = res_map[o.font_resource]
        if o.kind == "shape":
            k = f"shape{si}"; bundle[k] = _build_shape(o, plp_name, cw, ch); si += 1
        elif o.kind == "text":
            k = f"text{ti}"; bundle[k] = _build_text(o, plp_name, cw, ch); ti += 1
        else:
            continue
        ids.append(k)

    data = dict(project.raw_template) if project.raw_template else {}
    data.update({
        "bgWidth": project.width, "bgHeight": project.height,
        "bgActualWidth": project.width, "bgActualHeight": project.height,
        "bgColor": project.bg_color, "bgRotation": 0,
        "objectsBundle": bundle, "objectsIds": ids,
        "objectsSelectedReference": "0", "currTab": 0,
    })
    data.setdefault("bgPhotoForcedDim", True)
    data.setdefault("bgType", 1 if project.bg_color is not None and project.bg_color != -1 else 0)
    data.setdefault("bgPhotoV2", True)
    data.setdefault("bgPhotoSrc", {"imgSrcAssetFolder": False})
    data.setdefault("bgPhotoCrop", {"mHbGHc": False, "n7gV4v": False,
        "cropInfCirc": False, "cropInfoPorLeft": 0, "cropInfRot": 0,
        "cropInfoPorTop": 0, "cropInfoPorBottom": 100000, "cropInfoPorRight": 100000})
    for k in ("Brightness", "Hue", "Saturation", "Contrast"):
        data.setdefault(f"effect{k}Val", 0)
    data.setdefault("effectVignetteEnabled", False)
    data.setdefault("effectVignetteAlpha", 170)
    data.setdefault("effectVignetteColor", -16777216)
    data.setdefault("effectNoiseEnabled", False)
    data.setdefault("effectNoiseAlpha", 50)
    data.setdefault("effectNoiseVal2", 7)
    data.setdefault("effectStripesEnabled", False)
    data.setdefault("effectStripesAlpha", 16)
    data.setdefault("effectStripesVal2", 3)
    data.setdefault("bgGradientV2", "v2;3;0/54/100/54;-13500114/-63832;0.0/1.0")

    thumb = project.raw_template.get("_thumb_bytes")
    if thumb is None:
        tb = io.BytesIO()
        Image.new("RGBA", (min(project.width, 512) or 1, min(project.height, 512) or 1),
                  (0, 0, 0, 0)).save(tb, format="PNG", optimize=True)
        thumb = tb.getvalue()

    data = {k: v for k, v in data.items() if not k.startswith("_")}

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("data.plab", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        z.writestr("thumb", thumb)
        for r in project.resources:
            z.writestr(f"res/{res_map[r.name]}", r.data)
    return out_path
