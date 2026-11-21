"""Schema declaratif pour generer un PLP sans code.

Un Spec est un dict serialisable JSON qui decrit un visuel complet :
- canvas (dimensions, couleur de fond)
- objects (textes, formes natives, images)

Exemple minimal :

    {
      "canvas": {"width": 1080, "height": 1080, "bg": "#001A17"},
      "objects": [
        {"kind": "text", "text": "HELLO", "x": 80, "y": 200,
         "size_px": 140, "font": "Montserrat-ExtraBold",
         "color": "#FFC107"},
        {"kind": "rect", "x": 80, "y": 400, "w": 920, "h": 8,
         "fill": "#FF7043"},
        {"kind": "oval", "x": 500, "y": 500, "w": 300, "h": 300,
         "fill": "#009688"},
        {"kind": "image", "path": "logo.png",
         "x": 80, "y": 900, "w": 200, "h": 60}
      ]
    }
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


# Fonts disponibles dans le subset lnk-brand (a adapter selon le projet)
KNOWN_FONTS = {
    "Montserrat-Regular",
    "Montserrat-SemiBold",
    "Montserrat-Bold",
    "Montserrat-ExtraBold",
    "MontserratAlternates-ExtraBold",
    "OpenSans-Regular",
    "OpenSans-SemiBold",
}


@dataclass
class SpecCanvas:
    width: int
    height: int
    bg: str = "#FFFFFF"  # couleur hex
    margin: float = 80.0  # marge de securite pour auto-fit


@dataclass
class SpecText:
    kind: Literal["text"] = "text"
    text: str = ""
    x: float = 0.0
    y: float = 0.0
    size_px: float = 40.0
    font: str = "Montserrat-Regular"
    font_path: str | None = None  # chemin TTF local résolu par le Font Engine
    color: str = "#000000"
    align: Literal["left", "center", "right"] = "left"
    opacity: int = 100
    rotation: float = 0.0
    # runs multi-couleurs : [{"length": 6, "color": "#001A17"}, ...]
    runs: list[dict] | None = None


@dataclass
class SpecShape:
    kind: Literal["rect", "oval", "tri"] = "rect"
    x: float = 0.0
    y: float = 0.0
    w: float = 100.0
    h: float = 100.0
    fill: str = "#000000"
    radius_pct: float = 0.0  # 0 = carre, 30 = arrondi 30% du petit cote
    opacity: int = 100
    rotation: float = 0.0


@dataclass
class SpecImage:
    kind: Literal["image"] = "image"
    path: str = ""
    x: float = 0.0
    y: float = 0.0
    w: float = 100.0
    h: float = 100.0
    opacity: int = 100
    rotation: float = 0.0


SpecObject = SpecText | SpecShape | SpecImage


@dataclass
class Spec:
    canvas: SpecCanvas
    objects: list[SpecObject] = field(default_factory=list)


def parse_spec(data: dict) -> Spec:
    """Parse un dict JSON en Spec validee."""
    c = data["canvas"]
    canvas = SpecCanvas(
        width=int(c["width"]),
        height=int(c["height"]),
        bg=c.get("bg", "#FFFFFF"),
        margin=float(c.get("margin", 80.0)),
    )
    objects = []
    for obj in data.get("objects", []):
        kind = obj.get("kind")
        if kind == "text":
            font = obj.get("font", "Montserrat-Regular")
            if font not in KNOWN_FONTS:
                raise ValueError(f"Font inconnue : {font}. Disponibles : {sorted(KNOWN_FONTS)}")
            objects.append(SpecText(
                text=obj["text"],
                x=float(obj.get("x", 0)),
                y=float(obj.get("y", 0)),
                size_px=float(obj["size_px"]),
                font=font,
                color=obj.get("color", "#000000"),
                align=obj.get("align", "left"),
                opacity=int(obj.get("opacity", 100)),
                rotation=float(obj.get("rotation", 0)),
                runs=obj.get("runs"),
            ))
        elif kind in ("rect", "oval", "tri"):
            objects.append(SpecShape(
                kind=kind,
                x=float(obj.get("x", 0)),
                y=float(obj.get("y", 0)),
                w=float(obj["w"]),
                h=float(obj["h"]),
                fill=obj.get("fill", "#000000"),
                radius_pct=float(obj.get("radius_pct", 0)),
                opacity=int(obj.get("opacity", 100)),
                rotation=float(obj.get("rotation", 0)),
            ))
        elif kind == "image":
            objects.append(SpecImage(
                path=obj["path"],
                x=float(obj.get("x", 0)),
                y=float(obj.get("y", 0)),
                w=float(obj["w"]),
                h=float(obj["h"]),
                opacity=int(obj.get("opacity", 100)),
                rotation=float(obj.get("rotation", 0)),
            ))
        else:
            raise ValueError(f"kind inconnu : {kind}")
    return Spec(canvas=canvas, objects=objects)
