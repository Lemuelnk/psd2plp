import json

from psd2plp_mcp import font_engine, paths


def test_seed_catalog_is_shipped_inside_the_package():
    assert font_engine.SEED_PATH.is_file()
    assert font_engine.SEED_PATH.parent == paths.PACKAGE_DIR / "data"
    json.loads(font_engine.SEED_PATH.read_text(encoding="utf-8"))


def test_psd2plp_home_env_overrides_default(monkeypatch, tmp_path):
    monkeypatch.setenv("PSD2PLP_HOME", str(tmp_path))
    assert paths.resolve_home() == tmp_path.resolve()


def test_installed_package_defaults_to_user_directory(monkeypatch, tmp_path):
    monkeypatch.delenv("PSD2PLP_HOME", raising=False)
    monkeypatch.setattr(paths, "is_checkout", lambda: False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert paths.resolve_home() == (tmp_path / ".psd2plp").resolve()
