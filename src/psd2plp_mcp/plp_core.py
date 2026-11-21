from __future__ import annotations

import base64
import json
import math
import re
import struct
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Any

REF_WIDTH = 708
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_DATA_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 512
MAX_OBJECTS = 500
MAX_RESOURCE_BYTES = 16 * 1024 * 1024
ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

DEFAULT_GRADIENT = "v2;3;50/0/50/100;-3355444/-12303292;0.0/1.0"
DEFAULT_BG_GRADIENT = "v2;3;0/54/100/54;-13500114/-63832;0.0/1.0"

DEFAULT_CROP = {
    "mHbGHc": False, "n7gV4v": False, "cropInfCirc": False,
    "cropInfoPorLeft": 0, "cropInfRot": 0, "cropInfoPorTop": 0,
    "cropInfoPorBottom": 100000, "cropInfoPorRight": 100000,
}

# Defaults are based on the inspected LNK Studio writers. They are not an
# official PixelLab schema and must be validated against native PixelLab files.
SHAPE_DEFAULTS = {
    "shapeOpacityShadowInclude": False, "shapeThreeDStokeInclude": True,
    "DL4VOEC": 0, "shapeThreeDDepthColorFill": -16776961,
    "shapeEmbossIntensity": 80, "objectHidden": False, "shapeStrokeColor": -1,
    "shapeStrokeWidth": 2, "shapeRemoveColorCT": ["-1", "100"],
    "objectLocked": False, "shapeThreeDDepthColorAutomatic": True,
    "shapeThreeDLightingSpecularHardness": 80, "shapeEmbossEnabled": False,
    "shapeImageSrcV2": True, "shapeInnerEnabled": False, "sBmE43": False,
    "sDFkd3": {"imgSrcAssetFolder": False}, "shapeShadowColor": -16777216,
    "shapeShadowEnabled": False, "shapeShadowDx": 0, "shapeShadowDy": 0,
    "shapeEmbossAmbient": 70, "shapeThreeDLightingShadow": 10, "ShpThObAng": 45,
    "shapeImageCropInfo": DEFAULT_CROP, "shapeRotationX": 0, "shapeRotationY": 0,
    "shapeStrokeEnabled": False, "sCOG": DEFAULT_GRADIENT, "5cAUm": False,
    "Erasi": 0, "J4lv1": DEFAULT_CROP, "M3XGT": 10, "sCOfT": 1,
    "shapeInnerRadius": 10, "shapeThreeDDepthDarken": 30,
    "shapeRemoveColorBlur": 0, "shapeThreeDEnabled": False,
    "shapeThreeDViewType": 1, "shapePerspectiveP1X": 0, "shapePerspectiveP1Y": 0,
    "shapePerspectiveP2X": 1000, "shapePerspectiveP2Y": 0,
    "shapePerspectiveP3X": 1000, "shapePerspectiveP3Y": 1000,
    "shapePerspectiveP4X": 0, "shapePerspectiveP4Y": 1000,
    "shapeInnerDx": 0, "shapeInnerDy": 0, "shapeEmbossLightAngle": 90,
    "shapeThreeDDepthFillType": 1, "shapeThreeDLightingIntensity": 80,
    "shapeThreeDDepth": 25, "shapeThreeDLightingEnabled": True,
    "shapeInnerColor": -16777216, "shapeEmbossHardness": 20,
    "gnnMUtYI": 0, "shapeEmbossBevel": 40, "wYdWdLnz": 0,
    "shapeThreeDDepthGradientFillV2": DEFAULT_GRADIENT,
    "shapeRemoveColorEnabled": False, "shapeOpacity": 100,
    "shapeColorOverlayEnabled": False, "shapeShadowRadius": "10.0",
}

TEXT_DEFAULTS = {
    "textOpacity": 100, "textJustify": False, "textInnerEnabled": False,
    "textOuterDx": 0, "textOuterDy": 0, "textReflectionOffset": 0,
    "textThreeDDepthFillType": 1, "textThreeDDepth": 25,
    "textThreeDViewType": 1, "textEmbossBevel": 30, "ZpG28v": 0,
    "objectHidden": False, "textBgEnabled": False, "textBgPaddingLeft": 0,
    "objectLocked": False, "textThreeDLightingIntensity": 80,
    "textEmbossHardness": 40, "textThreeDShadowTransparency": 40,
    "textLetterSpacing": 0, "deNYb4": 0, "textTextSize": "32.0",
    "textThreeDDepthGradientFillV2": DEFAULT_GRADIENT, "textThreeDObAn": 45,
    "textBgPaddingRight": 0, "textPerEn": False, "textThreeDLightingEnabled": True,
    "textUnder": {}, "textBgColor": -1275068416, "textBold": {},
    "textRotationX": 0, "textRotationY": 0, "textEmbossEnabled": False,
    "textThreeDDepthDarken": 30, "textTextureImageSrc": {"imgSrcAssetFolder": False},
    "textTextureImageSrcV2": True, "textThreeDShadowBlur": 25, "textTextCurve": 0,
    "textThreeDLightingSpecularHardness": 50, "textBgBorderRadius": 0,
    "textThreeDShadowExpand": 10, "textTextureMaintainAspect": False,
    "textEmbossAmbient": 50, "textEmbossIncludeStroke": False,
    "textStrokeColor": -16777216, "textStrokeWidth": "4.0",
    "textThreeDDepthColorAutomatic": True, "textThreeDShadowColor": -16777216,
    "textBgPaddingTop": 0, "textBgFillType": 1, "B8aw": True,
    "textOuterRadius": "10.0", "textEmbossIntensity": 60,
    "textThreeDStokeInclude": True, "textStrokeEnabled": False,
    "textBgGradientV2": DEFAULT_GRADIENT, "textBgPaddingBottom": 0,
    "textOpacityShadowInclude": False, "textStrokeFillType": 1,
    "textThreeDDepthColorFill": -16776961, "textStrokeGradientV2": DEFAULT_GRADIENT,
    "textLineSpacing": 0, "textThreeDShadowEnabled": False,
    "textTextGradientV2": DEFAULT_GRADIENT, "textReflectionEnabled": False,
    "textInnerColor": -16777216, "textThreeDEnabled": False,
    "textInnerDx": "0.0", "textInnerDy": "0.0",
    "textTextureImageCropInfo": DEFAULT_CROP, "textOuterGlowEnabled": False,
    "textTextureScale": 10, "textInnerRadius": "3.0", "textItalic": {},
    "textOuterColor": -16777216, "textPerP1X": 0, "textPerP1Y": 0,
    "textPerP2X": 1000, "textPerP2Y": 0, "textPerP3X": 1000,
    "textPerP3Y": 1000, "textPerP4X": 0, "textPerP4Y": 1000,
    "textTextFillType": 1, "textThreeDLightingShadow": 40,
    "textAlignment": 8388659, "textEmbossLightAngle": 90, "tLSWrds": False,
    "textOuterEnabled": False,
}

def _rand_name(length: int, used: set[str]) -> str:
    import secrets
    while True:
        value = "".join(secrets.choice(ALPHABET) for _ in range(length))
        if value not in used:
            used.add(value)
            return value

def argb_signed(value: Any) -> int:
    """Accept a signed ARGB integer or #RRGGBB/#AARRGGBB string."""
    if isinstance(value, bool):
        raise ValueError("A boolean is not a color.")
    if isinstance(value, int):
        if value < -(2**31) or value > 2**32 - 1:
            raise ValueError("ARGB integer is outside 32-bit range.")
        return value if value < 2**31 else value - 2**32
    if not isinstance(value, str):
        raise ValueError("Color must be an integer or hex string.")
    s = value.strip().lstrip("#")
    if len(s) == 6:
        s = "FF" + s
    if len(s) != 8 or not re.fullmatch(r"[0-9a-fA-F]{8}", s):
        raise ValueError(f"Invalid ARGB color: {value!r}")
    n = int(s, 16)
    return n if n < 2**31 else n - 2**32

def _png_rgba(width: int, height: int) -> bytes:
    w, h = max(1, min(int(width), 512)), max(1, min(int(height), 512))
    raw = b"".join(b"\x00" + b"\x00" * (w * 4) for _ in range(h))
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">2I5B", w, h, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

def _native_shape(shape_type: str, fill_color: int, radius_pct: int = 0) -> dict:
    return {
        "mrdCt2Pon": {
            "5CVh": DEFAULT_GRADIENT, "9vwh": fill_color,
            "A67W": DEFAULT_GRADIENT, "JrtC": 1, "NyqG": 1,
            "UJ3K": -16777216, "vtf8": 0, "yMR4": 0,
        },
        "wAmp2k": 0,
        "vCScn1x": ["0.0000", "0.0000", "100.0000", "100.0000"],
        "3GsP": 255, "UTRQ": 0, "mfp2JbFB": shape_type,
        "2Xskb7": int(radius_pct), "3JaWTe": 255,
    }

def _validate_project_spec(spec: dict) -> None:
    if not isinstance(spec, dict):
        raise ValueError("Project specification must be an object.")
    width, height = spec.get("width"), spec.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        raise ValueError("width and height must be integers.")
    if not (1 <= width <= 12000 and 1 <= height <= 12000):
        raise ValueError("Canvas dimensions must be between 1 and 12000.")
    objects = spec.get("objects", [])
    if not isinstance(objects, list) or len(objects) > MAX_OBJECTS:
        raise ValueError(f"objects must be a list of at most {MAX_OBJECTS} items.")
    for i, obj in enumerate(objects):
        if not isinstance(obj, dict):
            raise ValueError(f"Object {i} must be an object.")
        if obj.get("kind") not in ("text", "shape"):
            raise ValueError(f"Object {i}: kind must be 'text' or 'shape'.")
        for key in ("x", "y"):
            if not isinstance(obj.get(key, 0), (int, float)):
                raise ValueError(f"Object {i}: {key} must be numeric.")
        if obj["kind"] == "shape":
            for key in ("width", "height"):
                if not isinstance(obj.get(key), (int, float)) or obj[key] <= 0:
                    raise ValueError(f"Object {i}: {key} must be a positive number.")
        else:
            if not isinstance(obj.get("text", ""), str):
                raise ValueError(f"Object {i}: text must be a string.")

def build_document(spec: dict) -> dict:
    _validate_project_spec(spec)
    width, height = spec["width"], spec["height"]
    container_w = REF_WIDTH
    container_h = round(REF_WIDTH * height / width)
    bg_color = argb_signed(spec.get("background_color", "#FFFFFFFF"))
    scale = REF_WIDTH / width
    bundle, ids = {}, []
    used_refs = set()
    shape_i = text_i = 0

    for obj in spec.get("objects", []):
        kind = obj["kind"]
        ref = obj.get("reference") or _rand_name(5, used_refs)
        used_refs.add(ref)
        x = round(float(obj.get("x", 0)) * scale)
        y = round(float(obj.get("y", 0)) * scale)
        opacity = max(0, min(100, int(obj.get("opacity", 100))))
        rotation = str(float(obj.get("rotation", 0)))
        raw = obj.get("raw_properties") or {}
        if not isinstance(raw, dict):
            raise ValueError("raw_properties must be an object when supplied.")

        if kind == "shape":
            key = f"shape{shape_i}"; shape_i += 1
            fill = argb_signed(obj.get("fill_color", "#FFFFFFFF"))
            width_plp = float(obj["width"]) * scale
            height_plp = float(obj["height"]) * scale
            d = dict(SHAPE_DEFAULTS)
            d.update({
                "shapeX": x, "shapeY": y, "shapeWidth": str(width_plp),
                "shapeHeight": str(height_plp), "shapeRotation": rotation,
                "shapeOpacity": opacity, "shapeReference": ref,
                "shapeOldContainerWidth": container_w,
                "shapeOldContainerHeight": container_h,
                "shapeImageShapeType": 5,
                "shapeColorOverlayColor": fill,
                "shapeColorOverlayEnabled": False,
                "objectHidden": bool(obj.get("hidden", False)),
                "objectLocked": bool(obj.get("locked", False)),
                "qUDmYrz": _native_shape(
                    obj.get("shape_type", "rect"), fill,
                    max(0, min(100, int(obj.get("radius_pct", 0))))
                ),
            })
            # Native type names documented by the inspected implementation.
            if obj.get("shape_type", "rect") not in ("rect", "oval", "tri1"):
                raise ValueError("shape_type must be rect, oval, or tri1.")
            d.update(raw)
        else:
            key = f"text{text_i}"; text_i += 1
            text_value = obj.get("text", "")
            text_size = float(obj.get("text_size", 32)) * scale
            text_color = argb_signed(obj.get("text_color", "#FFFFFFFF"))
            alignment = int(obj.get("alignment", 8388659))
            if alignment not in (8388659, 8388658, 8388657):
                raise ValueError("alignment must be 8388659 (left), 8388658 (center), or 8388657 (right).")
            max_width = obj.get("max_width", -1)
            if max_width != -1:
                max_width = int(float(max_width) * scale)
            d = dict(TEXT_DEFAULTS)
            d.update({
                "shapeX": x, "shapeY": y, "textRotation": rotation,
                "textOpacity": opacity, "textReference": ref,
                "shapeOldContainerWidth": container_w,
                "shapeOldContainerHeight": container_h,
                "textTextString": text_value, "textTextSize": str(text_size),
                "textLetterSpacing": float(obj.get("letter_spacing", 0)),
                "textLineSpacing": float(obj.get("line_spacing", 0)),
                "textMaxWidth": max_width, "textAlignment": alignment,
                "textTextColor": {"interval1": {
                    "textsIntervalsStart": 0, "textsIntervalsEnd": len(text_value),
                    "textsIntervalsColor": text_color,
                }},
                "textTextFont": {},
                "objectHidden": bool(obj.get("hidden", False)),
                "objectLocked": bool(obj.get("locked", False)),
            })
            d.update(raw)
        bundle[key] = d
        ids.append(key)

    doc = {
        "bgWidth": width, "bgHeight": height,
        "bgActualWidth": width, "bgActualHeight": height,
        "bgColor": bg_color, "bgRotation": 0,
        "objectsBundle": bundle, "objectsIds": ids,
        "objectsSelectedReference": "0", "currTab": 0,
        "bgPhotoForcedDim": True, "bgType": 1 if bg_color != -1 else 0,
        "bgPhotoV2": True, "bgPhotoSrc": {"imgSrcAssetFolder": False},
        "bgPhotoCrop": DEFAULT_CROP,
        "effectBrightnessVal": 0, "effectHueVal": 0,
        "effectSaturationVal": 0, "effectContrastVal": 0,
        "effectVignetteEnabled": False, "effectVignetteAlpha": 170,
        "effectVignetteColor": -16777216, "effectNoiseEnabled": False,
        "effectNoiseAlpha": 50, "effectNoiseVal2": 7,
        "effectStripesEnabled": False, "effectStripesAlpha": 16,
        "effectStripesVal2": 3, "bgGradientV2": DEFAULT_BG_GRADIENT,
    }
    # Keep caller-supplied unknown root fields without replacing structural fields.
    for k, v in (spec.get("raw_root_properties") or {}).items():
        if k not in doc and not k.startswith("_"):
            doc[k] = v
    return doc

def write_plp(spec: dict, output_path: Path) -> dict:
    _validate_project_spec(spec)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() != ".plp":
        raise ValueError("Output filename must end in .plp.")
    if output_path.name in (".", ".."):
        raise ValueError("Invalid output filename.")
    doc = build_document(spec)
    thumb = _png_rgba(spec["width"], spec["height"])
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.plab", json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        zf.writestr("thumb", thumb)
    report = validate_plp(output_path)
    if not report["valid"]:
        output_path.unlink(missing_ok=True)
        raise ValueError("Generated PLP failed validation: " + "; ".join(report["errors"]))
    return {
        "path": str(output_path.resolve()),
        "bytes": output_path.stat().st_size,
        "objects": len(doc["objectsIds"]),
        "canvas": [spec["width"], spec["height"]],
        "validation": report,
        "limitations": [
            "MVP emits editable native text and primitive shape objects only.",
            "Font families are recorded in a companion manifest only; native PLP font binding and font embedding are not yet implemented.",
            "Images, advanced effects and complex gradients are not yet generated.",
            "PixelLab open/save compatibility still requires testing in the target app version.",
        ],
    }

def _safe_zip_entries(zf: zipfile.ZipFile) -> list[str]:
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise ValueError("Archive contains too many entries.")
    total = sum(i.file_size for i in infos)
    if total > MAX_ARCHIVE_BYTES:
        raise ValueError("Uncompressed archive exceeds the safety limit.")
    for info in infos:
        p = PurePosixPath(info.filename.lstrip("/"))
        if p.is_absolute() or ".." in p.parts:
            raise ValueError("Archive contains an unsafe path.")
        if info.file_size > MAX_RESOURCE_BYTES:
            raise ValueError("Archive entry exceeds the resource size limit.")
    return [i.filename for i in infos]

def inspect_plp(path: Path) -> dict:
    with zipfile.ZipFile(path, "r") as zf:
        names = _safe_zip_entries(zf)
        if "data.plab" not in names:
            raise ValueError("Missing required data.plab entry.")
        info = zf.getinfo("data.plab")
        if info.file_size > MAX_DATA_BYTES:
            raise ValueError("data.plab exceeds the size limit.")
        data = json.loads(zf.read("data.plab").decode("utf-8"))
        bundle = data.get("objectsBundle", {})
        ids = data.get("objectsIds", [])
        return {
            "canvas": {"width": data.get("bgWidth"), "height": data.get("bgHeight")},
            "object_count": len(ids),
            "objects": [
                {"id": oid, "kind": "text" if str(oid).startswith("text") else "shape",
                 "text": bundle.get(oid, {}).get("textTextString")}
                for oid in ids if oid in bundle
            ],
            "resource_entries": [n for n in names if n.lstrip("/").startswith("res/")],
            "entries": names,
            "root_keys": sorted(data.keys()),
        }

def validate_plp(path: Path) -> dict:
    errors, warnings = [], []
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = _safe_zip_entries(zf)
            normalized = {n.lstrip("/") for n in names}
            if "data.plab" not in normalized:
                errors.append("Missing data.plab.")
                return {"valid": False, "errors": errors, "warnings": warnings}
            data_info = zf.getinfo(next(n for n in names if n.lstrip("/") == "data.plab"))
            if data_info.file_size > MAX_DATA_BYTES:
                errors.append("data.plab exceeds the size limit.")
                return {"valid": False, "errors": errors, "warnings": warnings}
            data = json.loads(zf.read(next(n for n in names if n.lstrip("/") == "data.plab")).decode("utf-8"))
            if not isinstance(data, dict):
                errors.append("data.plab root must be a JSON object.")
            bundle, ids = data.get("objectsBundle"), data.get("objectsIds")
            if not isinstance(bundle, dict):
                errors.append("objectsBundle must be an object.")
            if not isinstance(ids, list):
                errors.append("objectsIds must be an array.")
            if isinstance(bundle, dict) and isinstance(ids, list):
                if len(ids) > MAX_OBJECTS:
                    errors.append("Too many objects.")
                if len(ids) != len(set(ids)):
                    errors.append("objectsIds contains duplicate identifiers.")
                for oid in ids:
                    if oid not in bundle:
                        errors.append(f"Object id {oid!r} is missing from objectsBundle.")
            for key in ("bgWidth", "bgHeight", "bgActualWidth", "bgActualHeight"):
                if not isinstance(data.get(key), (int, float)) or data[key] <= 0:
                    errors.append(f"{key} must be a positive number.")
            if "thumb" not in normalized:
                warnings.append("thumb entry is absent.")
            for entry in names:
                if entry.lstrip("/").startswith("res/") and entry.endswith("/"):
                    continue
        return {"valid": not errors, "errors": errors, "warnings": warnings}
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError, KeyError, OSError, ValueError) as exc:
        errors.append(str(exc))
        return {"valid": False, "errors": errors, "warnings": warnings}
