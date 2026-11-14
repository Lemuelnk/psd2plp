from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Bounds:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    def to_list(self) -> list[float]:
        return [self.left, self.top, self.right, self.bottom]


@dataclass
class PSDLayer:
    name: str
    kind: str
    bounds: Bounds
    visible: bool = True
    opacity: float = 1.0
    parent: str | None = None
    index: int = 0
    depth: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PSDGroup(PSDLayer):
    children: list[PSDLayer] = field(default_factory=list)


@dataclass
class PSDTextLayer(PSDLayer):
    text: str = ""
    text_type: str = ""

    transform: tuple[float, ...] = field(default_factory=tuple)

    text_data: Any = None


@dataclass
class PSDShapeLayer(PSDLayer):
    shape_type: str | None = None
    fill_color: str | None = None
    stroke_color: str | None = None
    stroke_width: float | None = None


@dataclass
class PSDImageLayer(PSDLayer):
    source_type: str = "raster"
    resource_id: str | None = None


@dataclass
class PSDDocument:
    filename: str
    width: int
    height: int
    color_mode: str
    depth: int
    layers: list[PSDLayer] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def canvas_size(self) -> tuple[int, int]:
        return self.width, self.height

    def count_layers(self) -> int:
        return sum(_count_layer(layer) for layer in self.layers)


def _count_layer(layer: PSDLayer) -> int:
    count = 1

    if isinstance(layer, PSDGroup):
        count += sum(_count_layer(child) for child in layer.children)

    return count
