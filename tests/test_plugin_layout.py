import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_plugin_manifests_are_valid_json():
    assert _load(".claude-plugin/marketplace.json")["plugins"]
    assert _load("plugins/claude/.claude-plugin/plugin.json")["name"]
    assert "mcpServers" in _load("plugins/claude/.mcp.json")


def test_marketplace_sources_exist():
    for entry in _load(".claude-plugin/marketplace.json")["plugins"]:
        assert (ROOT / entry["source"]).is_dir()


def test_plugin_skill_copies_match_reference():
    reference = (ROOT / "plugins/skills/prompt-to-plp/SKILL.md").read_text(encoding="utf-8")
    copies = list(ROOT.glob("plugins/*/skills/prompt-to-plp/SKILL.md"))
    copies.append(ROOT / "skills/prompt-to-plp/SKILL.md")
    assert copies
    for copy in copies:
        assert copy.read_text(encoding="utf-8") == reference, f"{copy} differs: run scripts/sync-plugin-skills.sh"


def test_other_assistant_manifests_are_valid():
    gemini = _load("gemini-extension.json")
    assert gemini["mcpServers"]["psd2plp"]["command"] == "psd2plp-mcp"
    assert _load("plugins/chatgpt/plugin.json")["name"]
    assert _load("plugins/chatgpt/mcp.json")["mcpServers"]["psd2plp"]["command"] == "psd2plp-mcp"
    market = _load(".agents/plugins/marketplace.json")
    for entry in market["plugins"]:
        assert (ROOT / entry["source"]["path"] / "plugin.json").is_file()
