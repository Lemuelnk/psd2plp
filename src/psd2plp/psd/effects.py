from __future__ import annotations
from dataclasses import dataclass


@dataclass
class PSDEffectShadow:
    enabled: bool = False
    color: int = -16777216
    opacity: int = 75
    angle: float = 120.0
    distance: float = 5.0
    size: float = 5.0
    blur: float = 5.0


@dataclass
class PSDEffectStroke:
    enabled: bool = False
    color: int = -16777216
    size: float = 3.0
    position: str = "outside"


@dataclass
class PSDEffectColorOverlay:
    enabled: bool = False
    color: int = -65536
    opacity: int = 100


@dataclass
class PSDEffects:
    shadow: PSDEffectShadow = None
    stroke: PSDEffectStroke = None
    overlay: PSDEffectColorOverlay = None


def _to_signed(r, g, b, a):
    v = (a << 24) | (r << 16) | (g << 8) | b
    return v - (1 << 32) if v >= (1 << 31) else v


def _color_to_int(c):
    if c is None:
        return -16777216
    try:
        r0, g0, b0 = float(c[0]), float(c[1]), float(c[2])
        # Adobe peut renvoyer 0-1 ou 0-255 selon la source
        if r0 <= 1.0 and g0 <= 1.0 and b0 <= 1.0:
            r0, g0, b0 = r0 * 255, g0 * 255, b0 * 255
        r = max(0, min(255, int(round(r0))))
        g = max(0, min(255, int(round(g0))))
        b = max(0, min(255, int(round(b0))))
        return _to_signed(r, g, b, 255)
    except Exception:
        return -16777216


def read_effects(layer) -> PSDEffects:
    fx = PSDEffects()
    try:
        effects = layer.effects
    except Exception:
        return fx
    if effects is None or not getattr(effects, "enabled", False):
        return fx

    items = getattr(effects, "items", []) or []

    for it in items:
        cls = type(it).__name__

        if cls == "DropShadow" or "DropShadow" in cls:
            fx.shadow = PSDEffectShadow(
                enabled=True,
                color=_color_to_int(getattr(it, "color", None)),
                opacity=int(float(getattr(it, "opacity", 100) or 100)),
                angle=float(getattr(it, "angle", 120) or 120),
                distance=float(getattr(it, "distance", 5) or 5),
                size=float(getattr(it, "size", 5) or 5),
                blur=float(getattr(it, "size", 5) or 5),
            )

        elif cls == "Stroke" or "Stroke" in cls:
            fx.stroke = PSDEffectStroke(
                enabled=True,
                color=_color_to_int(getattr(it, "color", None)),
                size=float(getattr(it, "size", 3) or 3),
                position=str(getattr(it, "position", "outside")),
            )

        elif "ColorOverlay" in cls or "SolidColor" in cls:
            val = getattr(it, "value", None) or {}
            clr = None
            try:
                clr = val.get(b"Clr ") if hasattr(val, "get") else None
            except Exception:
                clr = None
            rgb = None
            if clr is not None:
                try:
                    rgb = (
                        clr[b"Rd  "],
                        clr[b"Grn "],
                        clr[b"Bl  "],
                    )
                except Exception:
                    rgb = None
            fx.overlay = PSDEffectColorOverlay(
                enabled=True,
                color=_color_to_int(rgb),
                opacity=int(float((val.get(b"Opct") if hasattr(val, "get") else 100) or 100)),
            )

    return fx
