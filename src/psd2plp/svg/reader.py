"""SVG -> intermediate object model."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SvgDocument:
    width: float
    height: float
    viewbox: tuple | None = None
    root: ET.Element | None = None


def _parse_dim(s: str | None) -> float | None:
    if s is None:
        return None
    s = s.strip()
    for unit in ("px", "pt", "mm", "cm", "in"):
        if s.endswith(unit):
            s = s[: -len(unit)]
            break
    try:
        return float(s)
    except ValueError:
        return None


def read_svg(path: str | Path) -> SvgDocument:
    tree = ET.parse(str(path))
    root = tree.getroot()
    width = _parse_dim(root.get("width"))
    height = _parse_dim(root.get("height"))
    viewbox = None
    vb = root.get("viewBox")
    if vb:
        try:
            parts = [float(x) for x in vb.replace(",", " ").split()]
            if len(parts) == 4:
                viewbox = tuple(parts)
        except ValueError:
            pass
    if (width is None or width <= 0) and viewbox:
        width = viewbox[2]
    if (height is None or height <= 0) and viewbox:
        height = viewbox[3]
    if not width or not height:
        raise ValueError(f"SVG sans dimensions valides : width={width}, height={height}")
    return SvgDocument(width=width, height=height, viewbox=viewbox, root=root)
