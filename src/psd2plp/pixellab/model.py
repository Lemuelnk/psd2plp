from __future__ import annotations
from dataclasses import dataclass, field


def argb_to_int(r, g, b, a=255):
    v = (a << 24) | (r << 16) | (g << 8) | b
    return v - 0x100000000 if v >= 0x80000000 else v


@dataclass
class PlpResource:
    name: str
    kind: str
    data: bytes


@dataclass
class PlpObject:
    kind: str
    x: float
    y: float
    width: float = 0.0
    height: float = 0.0
    rotation: float = 0.0
    opacity: int = 100
    hidden: bool = False
    locked: bool = False
    reference: str = ""
    resource_name: str | None = None
    image_shape_type: int = 2
    fill_color: int = -65536
    use_overlay: bool = False
    text: str = ""
    font_resource: str | None = None
    text_size: float = 32.0
    text_color: int = -1
    max_width: int = -1
    alignment: int = 8388659
    letter_spacing: float = 0.0
    line_spacing: float = 0.0
    qUDmYrz: dict | None = None
    text_runs: list | None = None  # [(length, color), ...] pour textTextColor intervals


@dataclass
class PlpProject:
    width: int
    height: int
    bg_color: int = -1
    objects: list = field(default_factory=list)
    resources: list = field(default_factory=list)
    raw_template: dict = field(default_factory=dict)
