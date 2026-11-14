from pathlib import Path

from psd_tools import PSDImage

from psd2plp.psd.layers import (
    Bounds,
    PSDDocument,
    PSDGroup,
    PSDImageLayer,
    PSDLayer,
    PSDShapeLayer,
    PSDTextLayer,
)
from psd2plp.psd.text import (
    PSDParagraphRun,
    PSDTextData,
    PSDTextFont,
    PSDTextRun,
)


def read_psd(path: str | Path) -> PSDDocument:
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"PSD introuvable : {path}")

    psd = PSDImage.open(path)

    return PSDDocument(
        filename=path.name,
        width=psd.width,
        height=psd.height,
        color_mode=_color_mode_name(psd.color_mode),
        depth=psd.depth,
        layers=_read_layers(psd),
    )


def inspect_psd(path: str | Path) -> dict:
    document = read_psd(path)

    return {
        "file": document.filename,
        "width": document.width,
        "height": document.height,
        "color_mode": document.color_mode,
        "depth": document.depth,
        "layer_count": document.count_layers(),
        "layers": [_layer_to_dict(layer) for layer in document.layers],
    }


def _read_layers(container, parent=None, depth=0):
    layers = []

    for index, layer in enumerate(container):
        converted = _convert_layer(
            layer,
            index=index,
            parent=parent,
            depth=depth,
        )

        layers.append(converted)

    return layers


def _convert_layer(layer, index, parent, depth):
    bounds = Bounds(*layer.bbox)

    common = {
        "name": layer.name or "",
        "kind": _kind_name(layer),
        "bounds": bounds,
        "visible": layer.visible,
        "opacity": layer.opacity / 255.0,
        "parent": parent,
        "index": index,
        "depth": depth,
    }

    if layer.is_group():
        return PSDGroup(
            **common,
            children=_read_layers(
                layer,
                parent=layer.name,
                depth=depth + 1,
            ),
        )

    if _is_text_layer(layer):
        text_data = _extract_text_data(layer)

        return PSDTextLayer(
            **common,
            text=text_data.text,
            text_type=text_data.text_type,
            transform=tuple(layer.transform),
            text_data=text_data,
        )

    if _is_shape_layer(layer):
        return PSDShapeLayer(**common)

    if _is_image_layer(layer):
        return PSDImageLayer(
            **common,
            source_type=_image_source_type(layer),
        )

    return PSDLayer(**common)


def _kind_name(layer) -> str:
    return type(layer).__name__


def _is_text_layer(layer) -> bool:
    return type(layer).__name__ == "TypeLayer"


def _is_shape_layer(layer) -> bool:
    return type(layer).__name__ == "ShapeLayer"


def _is_image_layer(layer) -> bool:
    return type(layer).__name__ in {
        "PixelLayer",
        "SmartObjectLayer",
    }


def _image_source_type(layer) -> str:
    kind = type(layer).__name__

    if kind == "SmartObjectLayer":
        return "smart_object"

    return "raster"

def _extract_text_data(layer) -> PSDTextData:
    engine = layer.engine_dict or {}

    text = layer.text or ""
    text_type = str(layer.text_type)

    font_set = layer.document_resources.get("FontSet", [])

    fonts = []

    for font in font_set:
        fonts.append(
            PSDTextFont(
                name=str(font.get("Name", "")).strip("'"),
                script=_safe_int(font.get("Script")),
                font_type=_safe_int(font.get("FontType")),
                synthetic=_safe_int(font.get("Synthetic")),
            )
        )

    style_run = engine.get("StyleRun", {})
    run_array = style_run.get("RunArray", [])
    run_lengths = style_run.get("RunLengthArray", [])

    style_runs = []

    for index, run in enumerate(run_array):
        data = (
            run
            .get("StyleSheet", {})
            .get("StyleSheetData", {})
        )

        font_index = _safe_int(data.get("Font"))

        font_name = None

        if (
            font_index is not None
            and 0 <= font_index < len(fonts)
        ):
            font_name = fonts[font_index].name

        length = (
            _safe_int(run_lengths[index])
            if index < len(run_lengths)
            else 0
        )

        style_runs.append(
            PSDTextRun(
                length=length,
                font_index=font_index,
                font_name=font_name,
                font_size=_safe_float(data.get("FontSize")),
                faux_bold=_safe_bool(data.get("FauxBold")),
                faux_italic=_safe_bool(data.get("FauxItalic")),
                auto_leading=_safe_bool(data.get("AutoLeading")),
                leading=_safe_float(data.get("Leading")),
                horizontal_scale=_safe_float(
                    data.get("HorizontalScale"),
                    1.0,
                ),
                vertical_scale=_safe_float(
                    data.get("VerticalScale"),
                    1.0,
                ),
                tracking=_safe_float(
                    data.get("Tracking"),
                    0.0,
                ),
                kerning=_safe_float(
                    data.get("Kerning"),
                    0.0,
                ),
                baseline_shift=_safe_float(
                    data.get("BaselineShift"),
                    0.0,
                ),
                font_caps=_safe_int(data.get("FontCaps")),
                font_baseline=_safe_int(
                    data.get("FontBaseline")
                ),
                underline=_safe_bool(
                    data.get("Underline")
                ),
                strikethrough=_safe_bool(
                    data.get("Strikethrough")
                ),
                ligatures=_safe_bool(
                    data.get("Ligatures")
                ),
                fill_color=data.get("FillColor"),
                stroke_color=data.get("StrokeColor"),
                fill_flag=data.get("FillFlag"),
                stroke_flag=data.get("StrokeFlag"),
            )
        )

    paragraph_run = engine.get("ParagraphRun", {})
    paragraph_array = paragraph_run.get("RunArray", [])

    paragraph_runs = []

    for run in paragraph_array:
        props = (
            run
            .get("ParagraphSheet", {})
            .get("Properties", {})
        )

        paragraph_runs.append(
            PSDParagraphRun(
                justification=_safe_int(
                    props.get("Justification")
                ),
                first_line_indent=_safe_float(
                    props.get("FirstLineIndent"),
                    0.0,
                ),
                start_indent=_safe_float(
                    props.get("StartIndent"),
                    0.0,
                ),
                end_indent=_safe_float(
                    props.get("EndIndent"),
                    0.0,
                ),
                space_before=_safe_float(
                    props.get("SpaceBefore"),
                    0.0,
                ),
                space_after=_safe_float(
                    props.get("SpaceAfter"),
                    0.0,
                ),
                auto_hyphenate=_safe_bool(
                    props.get("AutoHyphenate")
                ),
                word_spacing=props.get("WordSpacing"),
                letter_spacing=props.get("LetterSpacing"),
                glyph_spacing=props.get("GlyphSpacing"),
                auto_leading=_safe_float(
                    props.get("AutoLeading")
                ),
                leading_type=_safe_int(
                    props.get("LeadingType")
                ),
            )
        )

    return PSDTextData(
        text=text,
        text_type=text_type,
        fonts=fonts,
        style_runs=style_runs,
        paragraph_runs=paragraph_runs,
        style_run_lengths=[
            _safe_int(value)
            for value in run_lengths
        ],
    )

def _safe_int(value, default=None):
    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=None):
    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value, default=False):
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.lower() == "true"

    return bool(value)


def _extract_text(layer) -> str:
    try:
        return layer.text or ""
    except Exception:
        return ""


def _layer_to_dict(layer):
    result = {
        "name": layer.name,
        "kind": layer.kind,
        "bounds": layer.bounds.to_list(),
        "width": layer.bounds.width,
        "height": layer.bounds.height,
        "visible": layer.visible,
        "opacity": layer.opacity,
        "parent": layer.parent,
        "index": layer.index,
        "depth": layer.depth,
    }

    if isinstance(layer, PSDGroup):
        result["children"] = [
            _layer_to_dict(child)
            for child in layer.children
        ]

    if isinstance(layer, PSDTextLayer):
        result["text"] = layer.text
        result["text_type"] = layer.text_type
        result["transform"] = list(layer.transform)

        if layer.text_data is not None:
            result["text_data"] = {
                "text": layer.text_data.text,
                "text_type": layer.text_data.text_type,
                "fonts": [
                    {
                        "name": font.name,
                        "script": font.script,
                        "font_type": font.font_type,
                        "synthetic": font.synthetic,
                    }
                    for font in layer.text_data.fonts
                ],
                "style_run_lengths": layer.text_data.style_run_lengths,
                "style_runs": [
                    {
                        "length": run.length,
                        "font_index": run.font_index,
                        "font_name": run.font_name,
                        "font_size": run.font_size,
                        "faux_bold": run.faux_bold,
                        "faux_italic": run.faux_italic,
                        "auto_leading": run.auto_leading,
                        "leading": run.leading,
                        "horizontal_scale": run.horizontal_scale,
                        "vertical_scale": run.vertical_scale,
                        "tracking": run.tracking,
                        "kerning": run.kerning,
                        "baseline_shift": run.baseline_shift,
                        "font_caps": run.font_caps,
                        "font_baseline": run.font_baseline,
                        "underline": run.underline,
                        "strikethrough": run.strikethrough,
                        "ligatures": run.ligatures,
                        "fill_color": str(run.fill_color),
                        "stroke_color": str(run.stroke_color),
                    }
                    for run in layer.text_data.style_runs
                ],
                "paragraph_runs": [
                    {
                        "justification": paragraph.justification,
                        "first_line_indent": paragraph.first_line_indent,
                        "start_indent": paragraph.start_indent,
                        "end_indent": paragraph.end_indent,
                        "space_before": paragraph.space_before,
                        "space_after": paragraph.space_after,
                        "auto_hyphenate": paragraph.auto_hyphenate,
                        "word_spacing": str(paragraph.word_spacing),
                        "letter_spacing": str(paragraph.letter_spacing),
                        "glyph_spacing": str(paragraph.glyph_spacing),
                        "auto_leading": paragraph.auto_leading,
                        "leading_type": paragraph.leading_type,
                    }
                    for paragraph in layer.text_data.paragraph_runs
                ],
            }

    if isinstance(layer, PSDImageLayer):
        result["source_type"] = layer.source_type

    return result


def _color_mode_name(mode) -> str:
    names = {
        0: "Bitmap",
        1: "Grayscale",
        2: "Indexed",
        3: "RGB",
        4: "CMYK",
        7: "Multichannel",
        8: "Duotone",
        9: "Lab",
    }

    try:
        value = int(mode)
    except (TypeError, ValueError):
        return str(mode)

    return names.get(value, f"Unknown ({value})")
