#!/usr/bin/env python3
"""MCP stdio server for PixelLab AI Generator and its Font Engine."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
from psd2plp_mcp.plp_core import inspect_plp, validate_plp  # noqa: E402
from psd2plp_mcp.plp_generator import generate_plp  # noqa: E402
from psd2plp_mcp.plp_engine import roundtrip_plp  # noqa: E402
from psd2plp_mcp.font_engine import (  # noqa: E402
    list_fonts, get_font, recommend_fonts, import_custom_font, download_font, sync_fontsource_catalog,
)

from psd2plp_mcp.paths import HOME as _ROOT  # noqa: E402
OUTPUT_DIR = Path(os.environ.get("PSD2PLP_OUTPUT_DIR", _ROOT / "output"))
INPUT_DIR = _ROOT / "input"
( INPUT_DIR / "fonts" ).mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEXT_OBJECT_SCHEMA = {
    "type": "object", "required": ["kind", "x", "y"],
    "properties": {
        "kind": {"type": "string", "enum": ["text", "shape"]},
        "x": {"type": "number"}, "y": {"type": "number"},
        "width": {"type": "number"}, "height": {"type": "number"},
        "text": {"type": "string"}, "text_size": {"type": "number"},
        "text_color": {"type": "string"}, "fill_color": {"type": "string"},
        "shape_type": {"type": "string", "enum": ["rect", "oval", "tri1"]},
        "radius_pct": {"type": "integer", "minimum": 0, "maximum": 100},
        "rotation": {"type": "number"}, "opacity": {"type": "integer", "minimum": 0, "maximum": 100},
        "alignment": {"type": "integer", "enum": [8388659, 51, 17, 49, 53, 8388661], "description": "textAlignment mesure dans PixelLab : 8388659 et 51 gauche, 17 et 49 centre, 53 et 8388661 droite"},
        "max_width": {"type": "number"}, "letter_spacing": {"type": "number"},
        "line_spacing": {"type": "number"}, "hidden": {"type": "boolean"},
        "locked": {"type": "boolean"}, "raw_properties": {"type": "object"},
        "font_family": {"type": "string", "description": "Catalog family ID/name. Download its TTF face with download_font before generation; the selected face is embedded as a PLP resource."},
        "font_weight": {"type": "integer", "minimum": 1, "maximum": 1000},
        "font_style": {"type": "string", "enum": ["normal", "italic"]}
    }
}

TOOLS = [
    {
        "name": "generate_plp",
        "description": "Generate an editable PixelLab PLP project with native text and primitive shapes. Downloaded TTF variants selected by font_family are embedded as PLP resources; verify opening and saving in the target PixelLab app before relying on native font compatibility.",
        "inputSchema": {"type": "object", "required": ["project_name", "width", "height", "objects"], "properties": {
            "project_name": {"type": "string"}, "width": {"type": "integer", "minimum": 1, "maximum": 12000},
            "height": {"type": "integer", "minimum": 1, "maximum": 12000},
            "background_color": {"type": "string"}, "objects": {"type": "array", "maxItems": 500, "items": TEXT_OBJECT_SCHEMA},
            "raw_root_properties": {"type": "object"}}}
    },
    {"name": "inspect_plp", "description": "Inspect a PLP file in input/ or output/.", "inputSchema": {"type": "object", "required": ["filename"], "properties": {"filename": {"type": "string"}}}},
    {"name": "validate_plp", "description": "Validate the ZIP container and structural integrity of a PLP file.", "inputSchema": {"type": "object", "required": ["filename"], "properties": {"filename": {"type": "string"}}}},
    {"name": "roundtrip_plp", "description": "Create a verified PLP copy while preserving all data.plab properties and binary resources.", "inputSchema": {"type": "object", "required": ["filename", "output_filename"], "properties": {"filename": {"type": "string"}, "output_filename": {"type": "string"}}}},
    {"name": "search_fonts", "description": "Search the synchronized font catalog and locally imported fonts by name, category or style tags.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "category": {"type": "string", "enum": ["sans-serif", "serif", "display", "script", "handwriting", "monospace", "custom"]}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}, "include_custom": {"type": "boolean"}}}},
    {"name": "recommend_fonts", "description": "Recommend type families for a design style and role (headline, title, body, paragraph).", "inputSchema": {"type": "object", "required": ["style"], "properties": {"style": {"type": "string"}, "usage": {"type": "string"}, "language": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}}},
    {"name": "get_font_details", "description": "Return metadata, provider and downloaded/local variants for one font family.", "inputSchema": {"type": "object", "required": ["family_id"], "properties": {"family_id": {"type": "string"}}}},
    {"name": "sync_fontsource_catalog", "description": "Synchronize the complete Fontsource public font directory into the searchable local catalog. Use download_font with provider=fontsource to fetch a selected TTF face.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "download_font", "description": "Download a TTF variant from Fontsource or Google Fonts and store it in the local font library. Run sync_fontsource_catalog first when using Fontsource.", "inputSchema": {"type": "object", "required": ["family_id"], "properties": {"family_id": {"type": "string"}, "weight": {"type": "integer", "minimum": 1, "maximum": 1000}, "style": {"type": "string", "enum": ["normal", "italic"]}, "provider": {"type": "string", "enum": ["auto", "fontsource", "google_fonts"]}, "subset": {"type": "string", "default": "latin"}}}},
    {"name": "import_custom_font", "description": "Import a user-owned or properly licensed TTF/OTF file placed in input/fonts/. Requires an explicit license declaration.", "inputSchema": {"type": "object", "required": ["filename", "license_name"], "properties": {"filename": {"type": "string"}, "license_name": {"type": "string"}, "family_name": {"type": "string"}, "designer": {"type": "string"}, "license_url": {"type": "string"}, "weight": {"type": "integer", "minimum": 1, "maximum": 1000}, "style": {"type": "string", "enum": ["normal", "italic", "oblique"]}}}}
]


def safe_filename(name: str, suffix: str = "") -> str:
    name = Path(name).name
    name = "".join(c for c in name if c.isalnum() or c in "-_. ").strip(" .")
    if not name: name = "untitled"
    if suffix and not name.lower().endswith(suffix): name += suffix
    return name


def resolve_input(filename: str) -> Path:
    p = Path(filename)
    if p.is_absolute() or ".." in p.parts: raise ValueError("Use a relative filename without '..'.")
    for base in (INPUT_DIR, OUTPUT_DIR):
        candidate = (base / p).resolve()
        if base.resolve() in candidate.parents and candidate.is_file(): return candidate
    raise FileNotFoundError("File not found. Place it under plugin input/ or output/.")


def result_text(value):
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, indent=2)}]}


def call_tool(name, args):
    if name == "generate_plp":
        filename = safe_filename(args["project_name"])
        if not filename.lower().endswith(".plp"): filename += ".plp"
        path = OUTPUT_DIR / filename
        if path.exists(): raise FileExistsError(f"{filename} already exists. Choose another project_name.")
        result = generate_plp(args, path)
        return result_text(result)
    if name == "inspect_plp": return result_text(inspect_plp(resolve_input(args["filename"])))
    if name == "validate_plp": return result_text(validate_plp(resolve_input(args["filename"])))
    if name == "roundtrip_plp":
        source = resolve_input(args["filename"])
        output_name = safe_filename(args["output_filename"], ".plp")
        target = OUTPUT_DIR / output_name
        if target.exists():
            raise FileExistsError(f"{output_name} already exists. Choose another output_filename.")
        return result_text(roundtrip_plp(source, target))
    if name == "search_fonts": return result_text(list_fonts(args.get("query", ""), args.get("category", ""), args.get("limit", 30), args.get("include_custom", True)))
    if name == "recommend_fonts": return result_text(recommend_fonts(args["style"], args.get("usage", "headline"), args.get("language", "en"), args.get("limit", 8)))
    if name == "get_font_details": return result_text(get_font(args["family_id"]))
    if name == "sync_fontsource_catalog": return result_text(sync_fontsource_catalog())
    if name == "download_font": return result_text(download_font(args["family_id"], args.get("weight", 400), args.get("style", "normal"), args.get("provider", "auto"), args.get("subset", "latin")))
    if name == "import_custom_font":
        return result_text(import_custom_font(args["filename"], args["license_name"], args.get("family_name", ""),
            args.get("designer", ""), args.get("license_url", ""), args.get("weight", 0), args.get("style", "normal")))
    raise ValueError(f"Unknown tool: {name}")


def send(message):
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def handle(msg):
    method, request_id = msg.get("method"), msg.get("id")
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "psd2plp", "version": "0.2.0"}}})
    elif method == "notifications/initialized": return
    elif method == "ping": send({"jsonrpc": "2.0", "id": request_id, "result": {}})
    elif method == "tools/list": send({"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}})
    elif method == "tools/call":
        params = msg.get("params", {})
        try: send({"jsonrpc": "2.0", "id": request_id, "result": call_tool(params.get("name"), params.get("arguments") or {})})
        except Exception as exc: send({"jsonrpc": "2.0", "id": request_id, "result": {"isError": True, "content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}]}})
    elif request_id is not None: send({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}})


def main():
    for line in sys.stdin:
        try:
            msg = json.loads(line)
            if isinstance(msg, dict): handle(msg)
        except Exception as exc:
            print(f"server error: {exc}", file=sys.stderr, flush=True)

if __name__ == "__main__": main()
