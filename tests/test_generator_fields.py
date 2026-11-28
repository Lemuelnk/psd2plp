import pytest

from psd2plp.spec.builder import plp_from_spec
from psd2plp.spec.schema import Spec, SpecCanvas, SpecText
from psd2plp_mcp.plp_generator import _convert_text


def _text_obj(proj):
    return next(o for o in proj.objects if o.kind == "text")


def test_convert_text_reads_mcp_alignment_and_spacing_fields():
    t = _convert_text({
        "kind": "text", "x": 10, "y": 20, "text": "Hello", "text_size": 50,
        "alignment": 53, "max_width": 300, "letter_spacing": 2.5,
        "line_spacing": 4, "hidden": True, "locked": True,
    })
    assert t.align == "right"
    assert t.size_px == pytest.approx(35.0)
    assert t.max_width == 300.0
    assert t.letter_spacing == 2.5
    assert t.line_spacing == 4.0
    assert t.hidden is True and t.locked is True


def test_builder_passes_text_options_to_plp_object():
    spec = Spec(
        canvas=SpecCanvas(width=1000, height=1000),
        objects=[SpecText(text="Hi", x=0, y=0, max_width=500.0, letter_spacing=3.0,
                          line_spacing=2.0, hidden=True, locked=True)],
    )
    t = _text_obj(plp_from_spec(spec, plp_name="opts_test"))
    assert t.letter_spacing == 3.0
    assert t.line_spacing == 2.0
    assert t.hidden is True and t.locked is True
    assert t.max_width > 0


def test_builder_embeds_otf_as_plp_resource(tmp_path):
    font = tmp_path / "Demo.otf"
    font.write_bytes(b"OTTO" + b"\x00" * 64)
    spec = Spec(
        canvas=SpecCanvas(width=400, height=400),
        objects=[SpecText(text="Hi", x=10, y=10, font="Demo", font_path=str(font))],
    )
    proj = plp_from_spec(spec, plp_name="otf_test")
    assert any(r.kind == "otf" and r.data.startswith(b"OTTO") for r in proj.resources)
    assert _text_obj(proj).font_resource
