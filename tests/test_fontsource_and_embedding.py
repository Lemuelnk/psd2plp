import json
import zipfile

import pytest

from psd2plp_mcp import font_engine
from psd2plp.spec.builder import plp_from_spec
from psd2plp.spec.schema import Spec, SpecCanvas, SpecText
from psd2plp.pixellab.writer import write_plp


def test_fontsource_variant_prefers_exact_weight_style_and_subset():
    details = {
        "id": "demo-font",
        "family": "Demo Font",
        "defSubset": "latin",
        "variants": {
            "400": {
                "normal": {
                    "latin": {
                        "url": {
                            "ttf": "https://cdn.jsdelivr.net/fontsource/fonts/demo-font@1.0.0/latin-400-normal.ttf"
                        }
                    }
                }
            },
            "700": {
                "italic": {
                    "latin-ext": {
                        "url": {
                            "ttf": "https://cdn.jsdelivr.net/fontsource/fonts/demo-font@1.0.0/latin-ext-700-italic.ttf"
                        }
                    }
                }
            },
        },
    }

    selected = font_engine._select_fontsource_variant(
        details, weight=700, style="italic", subset="latin-ext"
    )

    assert selected["weight"] == 700
    assert selected["style"] == "italic"
    assert selected["subset"] == "latin-ext"


def test_fontsource_variant_rejects_untrusted_asset_host():
    details = {
        "id": "demo-font",
        "variants": {
            "400": {
                "normal": {
                    "latin": {
                        "url": {"ttf": "https://example.com/font.ttf"}
                    }
                }
            }
        },
    }

    with pytest.raises(ValueError, match="approved CDN"):
        font_engine._select_fontsource_variant(details)


def test_resolve_font_file_uses_repository_relative_path(tmp_path, monkeypatch):
    monkeypatch.setattr(font_engine, "HERE", tmp_path)
    monkeypatch.setattr(font_engine, "LIBRARY_DIR", tmp_path / "media" / "fonts")
    catalog_path = tmp_path / "catalog.json"
    monkeypatch.setattr(font_engine, "CATALOG_PATH", catalog_path)
    font_path = tmp_path / "data" / "fonts" / "downloaded" / "demo.ttf"
    font_path.parent.mkdir(parents=True)
    font_path.write_bytes(b"\x00\x01\x00\x00demo")
    catalog_path.write_text(json.dumps({
        "families": [{
            "id": "demo-font",
            "family": "Demo Font",
            "variants": [{
                "format": "ttf",
                "file": "data/fonts/downloaded/demo.ttf",
                "weight": 400,
                "style": "normal",
            }],
        }]
    }), encoding="utf-8")

    resolved = font_engine.resolve_font_file("demo-font", 400, "normal")

    assert resolved["path"] == font_path
    assert resolved["path"].read_bytes().endswith(b"demo")


def test_resolve_font_file_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(font_engine, "HERE", tmp_path)
    monkeypatch.setattr(font_engine, "LIBRARY_DIR", tmp_path / "media" / "fonts")
    catalog_path = tmp_path / "catalog.json"
    monkeypatch.setattr(font_engine, "CATALOG_PATH", catalog_path)
    catalog_path.write_text(json.dumps({
        "families": [{
            "id": "demo-font",
            "family": "Demo Font",
            "variants": [{
                "format": "ttf",
                "file": "../outside.ttf",
                "weight": 400,
                "style": "normal",
            }],
        }]
    }), encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        font_engine.resolve_font_file("demo-font")


def test_builder_embeds_downloaded_ttf_as_plp_resource(tmp_path):
    font_path = tmp_path / "demo.ttf"
    font_path.write_bytes(b"\x00\x01\x00\x00demo-font-binary")
    spec = Spec(
        canvas=SpecCanvas(width=400, height=300, bg="#FFFFFF", margin=10),
        objects=[
            SpecText(
                text="Editable title",
                x=20,
                y=30,
                size_px=32,
                font="Demo Font",
                font_path=str(font_path),
                color="#000000",
            )
        ],
    )

    project = plp_from_spec(spec, plp_name="font-test")
    output = tmp_path / "font-test.plp"
    write_plp(project, output, plp_name="font-test")

    with zipfile.ZipFile(output) as archive:
        data = json.loads(archive.read("data.plab").decode("utf-8"))
        text_object = data["objectsBundle"]["text0"]
        font_path_in_plp = text_object["textTextFont"]["interval1"]["textsIntervalsFont"]
        resource_name = font_path_in_plp.rsplit("/", 1)[-1]

        assert f"res/{resource_name}" in archive.namelist()
        assert archive.read(f"res/{resource_name}") == font_path.read_bytes()



def test_sync_fontsource_catalog_merges_full_directory(monkeypatch):
    catalog = {
        "families": [
            {
                "id": "roboto",
                "family": "Roboto",
                "category": "sans-serif",
                "tags": ["clean"],
                "providers": ["google_fonts"],
                "variants": [],
                "custom": False,
            }
        ]
    }
    saved = []
    records = [
        {
            "id": "roboto",
            "family": "Roboto",
            "category": "sans-serif",
            "weights": [400, 700],
            "styles": ["normal", "italic"],
            "subsets": ["latin"],
            "variable": False,
            "version": "v30",
            "type": "google",
            "defSubset": "latin",
        },
        {
            "id": "some-open-font",
            "family": "Some Open Font",
            "category": "display",
            "weights": [400],
            "styles": ["normal"],
            "subsets": ["latin"],
            "variable": False,
            "version": "v1",
            "type": "local",
            "defSubset": "latin",
        },
    ]
    monkeypatch.setattr(font_engine, "_fontsource_get_all_fonts", lambda: records)
    monkeypatch.setattr(font_engine, "_load_catalog", lambda: catalog)
    monkeypatch.setattr(font_engine, "_save_catalog", lambda value: saved.append(value.copy()))

    result = font_engine.sync_fontsource_catalog()

    assert result["added_count"] == 1
    assert result["updated_count"] == 1
    assert catalog["families"][0]["fontsource_id"] == "roboto"
    added = next(f for f in catalog["families"] if f["family"] == "Some Open Font")
    assert added["fontsource_id"] == "some-open-font"
    assert added["availability"] == "catalog_only"
    assert saved
