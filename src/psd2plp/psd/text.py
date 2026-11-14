from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PSDTextRun:
    length: int
    font_index: int | None = None
    font_name: str | None = None

    font_size: float | None = None
    faux_bold: bool = False
    faux_italic: bool = False

    auto_leading: bool = False
    leading: float | None = None

    horizontal_scale: float = 1.0
    vertical_scale: float = 1.0

    tracking: float = 0.0
    kerning: float = 0.0
    baseline_shift: float = 0.0

    font_caps: int | None = None
    font_baseline: int | None = None

    underline: bool = False
    strikethrough: bool = False
    ligatures: bool = False

    fill_color: Any = None
    stroke_color: Any = None

    fill_flag: Any = None
    stroke_flag: Any = None


@dataclass
class PSDParagraphRun:
    justification: int | None = None

    first_line_indent: float = 0.0
    start_indent: float = 0.0
    end_indent: float = 0.0

    space_before: float = 0.0
    space_after: float = 0.0

    auto_hyphenate: bool = False

    word_spacing: Any = None
    letter_spacing: Any = None
    glyph_spacing: Any = None

    auto_leading: float | None = None
    leading_type: int | None = None


@dataclass
class PSDTextFont:
    name: str
    script: int | None = None
    font_type: int | None = None
    synthetic: int | None = None


@dataclass
class PSDTextData:
    text: str
    text_type: str

    fonts: list[PSDTextFont] = field(default_factory=list)

    style_runs: list[PSDTextRun] = field(default_factory=list)
    paragraph_runs: list[PSDParagraphRun] = field(default_factory=list)

    style_run_lengths: list[int] = field(default_factory=list)
