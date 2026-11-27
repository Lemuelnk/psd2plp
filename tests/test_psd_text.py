from types import SimpleNamespace

import pytest

from psd2plp.mapping import psd_to_plp as m

SCALE = 708 / 1080


def _layer(font_size=40.0, just=0, transform=(1.0, 0.0, 0.0, 1.0, 0.0, 0.0)):
    return SimpleNamespace(
        transform=transform,
        engine_dict={
            "StyleRun": {"RunArray": [{"StyleSheet": {"StyleSheetData": {"FontSize": font_size}}}]},
            "ParagraphRun": {"RunArray": [{"ParagraphSheet": {"Properties": {"Justification": just}}}]},
        },
    )


def test_text_size_is_em_scaled_to_container():
    assert m._text_size(_layer(40.0), SCALE, 30) == pytest.approx(40.0 * SCALE)


def test_left_text_is_anchored_on_left_edge_without_box():
    g = m._text_geometry(_layer(just=0), SCALE, "Hello", (100, 200, 400, 240))
    assert g["x"] == pytest.approx(100 * SCALE)
    assert g["y"] == pytest.approx(200 * SCALE)
    assert g["max_width"] == -1 and g["alignment"] == m.ALIGN["left"]


def test_centered_text_box_is_centered_on_ink():
    g = m._text_geometry(_layer(just=2), SCALE, "Hello", (300, 100, 700, 140))
    assert g["alignment"] == m.ALIGN["center"]
    assert g["x"] + g["max_width"] / 2 == pytest.approx(500 * SCALE, abs=1.0)
    assert g["max_width"] > 400 * SCALE


def test_right_text_box_keeps_right_edge():
    g = m._text_geometry(_layer(just=1), SCALE, "Hello", (300, 100, 700, 140))
    assert g["alignment"] == m.ALIGN["right"]
    assert g["x"] + g["max_width"] == pytest.approx(700 * SCALE, abs=1.0)


def test_rotated_text_pivots_on_ink_center():
    t = (0.0, 1.0, -1.0, 0.0, 0.0, 0.0)
    g = m._text_geometry(_layer(just=0, transform=t), SCALE, "now", (861, 213, 1000, 660))
    assert g["rotation"] == pytest.approx(90.0)
    assert g["x"] + g["max_width"] / 2 == pytest.approx(930.5 * SCALE, abs=1.0)
    assert g["max_width"] >= 447 * SCALE


def test_right_text_box_stays_inside_canvas():
    g = m._text_geometry(_layer(just=1), SCALE, "Hello", (77, 1089, 443, 1150), 1080)
    assert g["x"] >= 0
    assert g["x"] + g["max_width"] == pytest.approx(443 * SCALE, abs=1.0)


def test_centered_text_box_stays_inside_canvas_and_centered():
    g = m._text_geometry(_layer(just=2), SCALE, "Hello", (10, 100, 200, 140), 1080)
    assert g["x"] >= 0
    assert g["x"] + g["max_width"] / 2 == pytest.approx(105 * SCALE, abs=1.0)


def test_apply_caps_uppercases_only_runs_with_all_caps():
    sheet = lambda caps: {"StyleSheet": {"StyleSheetData": {"FontCaps": caps}}}
    layer = SimpleNamespace(engine_dict={"StyleRun": {"RunArray": [sheet(2), sheet(0)], "RunLengthArray": [3, 4]}})
    assert m._apply_caps(layer, "abcdefg") == "ABCdefg"


def test_apply_caps_uppercases_only_runs_with_all_caps():
    sheet = lambda caps: {"StyleSheet": {"StyleSheetData": {"FontCaps": caps}}}
    layer = SimpleNamespace(engine_dict={"StyleRun": {"RunArray": [sheet(2), sheet(0)], "RunLengthArray": [3, 4]}})
    assert m._apply_caps(layer, "abcdefg") == "ABCdefg"
