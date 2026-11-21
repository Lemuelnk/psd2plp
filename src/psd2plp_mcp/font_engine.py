"""Font catalog, recommendation, import and Google Fonts TTF resolver.

This module deliberately does not write a guessed PixelLab font field into
PLP JSON. Native font binding must be confirmed against a PixelLab-generated
reference project before the compatibility layer applies it.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import struct
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any

import os as _os
HERE = Path(__file__).resolve().parents[2]  # racine du repo
LIBRARY_DIR = Path(_os.environ.get("PSD2PLP_FONT_LIBRARY", HERE / "media" / "fonts"))
SEED_PATH = LIBRARY_DIR / "catalog.seed.json"
CATALOG_PATH = LIBRARY_DIR / "catalog.json"
# Dossier pour les TTF téléchargés et custom (gitignoré)
DOWNLOADS_DIR = Path(_os.environ.get("PSD2PLP_FONT_DOWNLOADS", HERE / "data" / "fonts" / "downloaded"))
CUSTOM_DIR = Path(_os.environ.get("PSD2PLP_FONT_CUSTOM", HERE / "data" / "fonts" / "custom"))
INPUT_FONT_DIR = Path(_os.environ.get("PSD2PLP_FONT_INPUT", HERE / "data" / "fonts" / "input"))
CUSTOM_DIR = CUSTOM_DIR
DOWNLOAD_DIR = DOWNLOADS_DIR
MAX_FONT_BYTES = 32 * 1024 * 1024
MAX_HTTP_BYTES = 16 * 1024 * 1024
ALLOWED_FONT_EXTENSIONS = {".ttf", ".otf"}
GOOGLE_RAW = "https://raw.githubusercontent.com/google/fonts/main"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug or len(slug) > 80:
        raise ValueError("Invalid font family name.")
    return slug


def _load_catalog() -> dict:
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    if not CATALOG_PATH.exists():
        seed = json.loads(SEED_PATH.read_text("utf-8"))
        CATALOG_PATH.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", "utf-8")
    data = json.loads(CATALOG_PATH.read_text("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("families"), list):
        raise ValueError("Font catalog is corrupt.")
    return data


def _save_catalog(data: dict) -> None:
    tmp = CATALOG_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
    tmp.replace(CATALOG_PATH)


def list_fonts(query: str = "", category: str = "", limit: int = 30, include_custom: bool = True) -> dict:
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100.")
    data = _load_catalog()
    q, cat = query.casefold().strip(), category.casefold().strip()
    found = []
    for family in data["families"]:
        if family.get("custom") and not include_custom:
            continue
        if cat and family.get("category", "").casefold() != cat:
            continue
        haystack = " ".join([family.get("family", ""), family.get("category", ""), *family.get("tags", [])]).casefold()
        if q and q not in haystack:
            continue
        found.append({k: family.get(k) for k in ("id", "family", "category", "tags", "providers", "fontsource_package_candidate", "fontsource_status", "availability", "license", "license_status", "custom", "variants")})
    found.sort(key=lambda x: (not x.get("custom", False), x["family"].casefold()))
    return {"count": len(found), "returned": min(limit, len(found)), "catalog_version": data.get("catalog_version"), "fonts": found[:limit]}


def get_font(family_id: str) -> dict:
    data = _load_catalog()
    for family in data["families"]:
        if family.get("id") == family_id or family.get("family", "").casefold() == family_id.casefold():
            return family
    raise KeyError(f"Unknown font family: {family_id}")


def recommend_fonts(style: str, usage: str = "headline", language: str = "en", limit: int = 8) -> dict:
    if not 1 <= int(limit) <= 20:
        raise ValueError("limit must be between 1 and 20.")
    style_terms = set(re.findall(r"[a-z0-9]+", style.casefold()))
    aliases = {
        "luxury": {"luxury", "elegant", "fashion", "formal"},
        "elegant": {"elegant", "luxury", "formal", "wedding"},
        "modern": {"modern", "geometric", "clean"},
        "gospel": {"impact", "headline", "display", "bold", "poster"},
        "sport": {"sport", "impact", "condensed", "headline"},
        "birthday": {"celebration", "playful", "friendly", "script"},
        "wedding": {"wedding", "luxury", "elegant", "formal"},
        "tech": {"tech", "futuristic", "geometric", "technical"},
        "editorial": {"editorial", "literary", "serif"},
        "street": {"urban", "street", "poster", "impact"},
    }
    style_expanded = set(style_terms)
    for term in list(style_terms):
        style_expanded.update(aliases.get(term, set()))
    role_terms = {
        "headline": {"impact", "headline", "display", "poster", "condensed"},
        "title": {"headline", "display", "elegant", "editorial"},
        "body": {"readable", "body", "clean", "editorial"},
        "paragraph": {"readable", "body", "clean", "editorial"},
        "caption": {"readable", "body", "clean"},
    }.get(usage.casefold(), set())
    data = _load_catalog()
    scored = []
    for family in data["families"]:
        tags = set(family.get("tags", [])) | {family.get("category", "")}
        style_score = len(style_expanded & tags)
        role_score = len(role_terms & tags)
        score = style_score * 3 + role_score
        if usage.casefold() in ("headline", "title") and family.get("category") == "display": score += 1
        if style_expanded & {"luxury", "elegant", "wedding", "formal", "fashion"} and family.get("category") == "serif": score += 2
        if style_expanded & {"handwritten", "signature", "script", "calligraphy"} and family.get("category") == "script": score += 2
        if language.casefold().startswith(("fr", "en", "sw", "ln")) and family.get("category") in ("sans-serif", "serif"): score += 1
        if score:
            scored.append((score, family["family"].casefold(), family))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return {"style": style, "usage": usage, "language": language, "recommendations": [
        {"id": f["id"], "family": f["family"], "category": f["category"], "tags": f.get("tags", []), "score": score,
         "availability": f.get("availability"), "providers": f.get("providers", [])}
        for score, _, f in scored[:limit]
    ], "note": "Recommendations rank catalog metadata; they do not yet prove PixelLab device availability."}



def _fontsource_get(property_name: str) -> dict:
    allowed = {"family", "weights", "styles", "subsets", "type", "category", "variable", "version", "lastModified"}
    if property_name not in allowed:
        raise ValueError("Unsupported Fontsource fontlist property.")
    url = f"https://api.fontsource.org/fontlist?{property_name}"
    req = urllib.request.Request(url, headers={"User-Agent": "LNK-PixelLab-FontEngine/0.2", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as response:
        if not response.geturl().startswith("https://api.fontsource.org/"):
            raise ValueError("Unexpected redirect host while querying Fontsource.")
        raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("Fontsource catalog response exceeds 8 MiB.")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Fontsource {property_name} response must be a JSON object.")
    return value


def sync_fontsource_catalog() -> dict:
    """Refresh Fontsource metadata for the starter catalog; no font binaries are fetched."""
    props = {name: _fontsource_get(name) for name in ("family", "weights", "styles", "subsets", "type", "category", "variable", "version", "lastModified")}
    normalized = {}
    for font_id, family_name in props["family"].items():
        key = re.sub(r"[^a-z0-9]+", "", str(family_name).casefold())
        normalized[key] = font_id
    data = _load_catalog()
    matched = []
    missing = []
    for family in data["families"]:
        if family.get("custom"):
            continue
        key = re.sub(r"[^a-z0-9]+", "", family.get("family", "").casefold())
        font_id = normalized.get(key)
        if not font_id:
            family["fontsource_status"] = "not_found"
            missing.append(family["family"])
            continue
        family["fontsource_id"] = font_id
        family["fontsource_status"] = "verified"
        family["fontsource_package_candidate"] = "@fontsource/" + font_id
        family["fontsource_weights"] = props["weights"].get(font_id, [])
        family["fontsource_styles"] = props["styles"].get(font_id, [])
        family["fontsource_subsets"] = props["subsets"].get(font_id, [])
        family["fontsource_type"] = props["type"].get(font_id)
        family["fontsource_category"] = props["category"].get(font_id)
        family["fontsource_variable"] = props["variable"].get(font_id)
        family["fontsource_version"] = props["version"].get(font_id)
        family["fontsource_last_modified"] = props["lastModified"].get(font_id)
        if "fontsource" not in family.setdefault("providers", []):
            family["providers"].append("fontsource")
        matched.append(family["family"])
    data["fontsource_synced_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    _save_catalog(data)
    return {"synced": True, "matched_count": len(matched), "not_found_count": len(missing),
            "matched_families": matched, "not_found_families": missing,
            "note": "Fontsource metadata is synchronized. This endpoint does not download font binaries; Google Fonts remains the TTF source and custom imports remain local."}

def _font_magic(path: Path) -> str:
    with path.open("rb") as f:
        magic = f.read(4)
    if magic == b"OTTO": return "otf"
    if magic in (b"\x00\x01\x00\x00", b"true"): return "ttf"
    raise ValueError("Unsupported font binary. Only valid SFNT TTF/OTF files are accepted (not WOFF/WOFF2/TTC).")


def _sfnt_tables(path: Path) -> dict[str, tuple[int, int]]:
    size = path.stat().st_size
    with path.open("rb") as f:
        header = f.read(12)
        if len(header) != 12: raise ValueError("Truncated font file.")
        _, count, _, _, _ = struct.unpack(">4sHHHH", header)
        if count > 256: raise ValueError("Invalid SFNT table count.")
        tables = {}
        for _ in range(count):
            row = f.read(16)
            if len(row) != 16: raise ValueError("Truncated SFNT table directory.")
            tag, _checksum, offset, length = struct.unpack(">4sIII", row)
            if offset + length > size: raise ValueError("Font table points outside the file.")
            tables[tag.decode("ascii", "replace")] = (offset, length)
    return tables


def _font_names(path: Path, tables: dict) -> tuple[str | None, str | None, int | None]:
    family = subfamily = None
    weight = None
    with path.open("rb") as f:
        if "name" in tables:
            off, length = tables["name"]
            f.seek(off); raw = f.read(length)
            if len(raw) >= 6:
                _fmt, count, string_off = struct.unpack_from(">HHH", raw, 0)
                if count <= 1024:
                    candidates = {1: [], 2: [], 4: [], 6: [], 16: [], 17: []}
                    for i in range(count):
                        pos = 6 + i * 12
                        if pos + 12 > len(raw): break
                        platform, encoding, language, name_id, nlen, noff = struct.unpack_from(">HHHHHH", raw, pos)
                        if name_id not in candidates or string_off + noff + nlen > len(raw): continue
                        val = raw[string_off + noff:string_off + noff + nlen]
                        try:
                            decoded = val.decode("utf-16-be" if platform in (0, 3) else "mac_roman", "replace").strip("\x00\ufeff ")
                        except Exception: continue
                        if decoded: candidates[name_id].append((language == 0x0409, decoded))
                    def pick(k):
                        vals = sorted(candidates[k], key=lambda x: not x[0])
                        return vals[0][1] if vals else None
                    family = pick(16) or pick(1)
                    subfamily = pick(17) or pick(2)
        if "OS/2" in tables:
            off, length = tables["OS/2"]
            if length >= 6:
                f.seek(off + 4); weight = struct.unpack(">H", f.read(2))[0]
                if not 1 <= weight <= 1000: weight = None
    return family, subfamily, weight


def import_custom_font(filename: str, license_name: str, family_name: str = "", designer: str = "", license_url: str = "", weight: int = 0, style: str = "normal") -> dict:
    p = PurePosixPath(filename)
    if p.is_absolute() or ".." in p.parts or len(p.parts) != 1:
        raise ValueError("filename must be a single filename inside input/fonts/.")
    source = (INPUT_FONT_DIR / p.name).resolve()
    if INPUT_FONT_DIR.resolve() not in source.parents or not source.is_file():
        raise FileNotFoundError("Place the font file in the plugin input/fonts/ directory first.")
    if source.suffix.lower() not in ALLOWED_FONT_EXTENSIONS:
        raise ValueError("Only .ttf and .otf files can be imported.")
    if source.stat().st_size > MAX_FONT_BYTES:
        raise ValueError("Font file exceeds 32 MiB.")
    fmt = _font_magic(source)
    tables = _sfnt_tables(source)
    embedded_family, embedded_style, embedded_weight = _font_names(source, tables)
    family_name = (family_name or embedded_family or source.stem).strip()
    if not family_name or len(family_name) > 120: raise ValueError("A valid family_name is required.")
    license_name = license_name.strip()
    if not license_name: raise ValueError("license_name is required; do not import fonts with unknown redistribution rights.")
    style = (style or ("italic" if embedded_style and "italic" in embedded_style.casefold() else "normal")).casefold()
    if style not in ("normal", "italic", "oblique"): raise ValueError("style must be normal, italic or oblique.")
    weight = int(weight or embedded_weight or 400)
    if not 1 <= weight <= 1000: raise ValueError("weight must be between 1 and 1000.")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    slug = _slug(family_name)
    dest_dir = CUSTOM_DIR / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{slug}-{weight}-{style}-{digest[:10]}.{fmt}"
    if not dest.exists(): shutil.copyfile(source, dest)
    data = _load_catalog()
    family = next((f for f in data["families"] if f.get("id") == "custom-" + slug), None)
    if family is None:
        family = {"id": "custom-" + slug, "family": family_name, "category": "custom", "tags": ["custom", "user-imported"],
                  "providers": ["lnk_custom"], "availability": "local", "license": license_name,
                  "license_status": "user_declared", "custom": True, "designer": designer or None,
                  "license_url": license_url or None, "variants": []}
        data["families"].append(family)
    variant = {"weight": weight, "style": style, "format": fmt, "file": str(dest.relative_to(LIBRARY_DIR.parent)).replace("\\", "/"),
               "sha256": digest, "bytes": dest.stat().st_size, "embedded_subfamily": embedded_style}
    if not any(v.get("sha256") == digest for v in family["variants"]): family["variants"].append(variant)
    _save_catalog(data)
    return {"imported": True, "family": family_name, "family_id": family["id"], "variant": variant,
            "license": license_name, "license_url": license_url or None,
            "note": "Custom font stored locally. PLP font binding remains pending native PixelLab schema verification."}


def _http_get(url: str) -> bytes:
    if not url.startswith(GOOGLE_RAW + "/"):
        raise ValueError("Download URL is outside the approved Google Fonts raw repository.")
    req = urllib.request.Request(url, headers={"User-Agent": "LNK-PixelLab-FontEngine/0.2"})
    with urllib.request.urlopen(req, timeout=20) as response:
        final = response.geturl()
        if not final.startswith("https://raw.githubusercontent.com/google/fonts/"):
            raise ValueError("Unexpected redirect host while downloading font asset.")
        data = response.read(MAX_HTTP_BYTES + 1)
        if len(data) > MAX_HTTP_BYTES: raise ValueError("Remote font asset exceeds 16 MiB.")
        return data


def download_google_font(family_id: str, weight: int = 400, style: str = "normal") -> dict:
    family = get_font(family_id)
    if family.get("custom"): raise ValueError("Custom fonts are already stored locally.")
    slug = family.get("google_fonts_slug") or family["id"]
    metadata = None; used_folder = None
    for folder in ("ofl", "apache", "ufl"):
        url = f"{GOOGLE_RAW}/{folder}/{slug}/METADATA.pb"
        try:
            metadata = _http_get(url).decode("utf-8")
            used_folder = folder
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in (404, 410): raise
    if metadata is None: raise FileNotFoundError(f"Google Fonts metadata not found for {family['family']}.")
    blocks = re.findall(r"fonts\s*\{([^{}]*)\}", metadata, re.S)
    matches = []
    for block in blocks:
        fm = re.search(r'filename:\s*"([^"]+\.ttf)"', block)
        wm = re.search(r"weight:\s*(\d+)", block)
        sm = re.search(r'style:\s*"([^"]+)"', block)
        if not fm: continue
        filename = fm.group(1)
        if "/" in filename or ".." in filename: continue
        matches.append({"filename": filename, "weight": int(wm.group(1)) if wm else 400, "style": sm.group(1) if sm else "normal"})
    if not matches: raise ValueError("No compatible TTF files were listed in Google Fonts metadata.")
    desired_style = style.casefold()
    selected = min(matches, key=lambda x: (x["style"] != desired_style, abs(x["weight"] - int(weight))))
    raw_font = _http_get(f"{GOOGLE_RAW}/{used_folder}/{slug}/{selected['filename']}")
    if len(raw_font) > MAX_FONT_BYTES: raise ValueError("Downloaded font exceeds 32 MiB.")
    temp = DOWNLOAD_DIR / "tmp-font.ttf"
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    temp.write_bytes(raw_font)
    if _font_magic(temp) != "ttf":
        temp.unlink(missing_ok=True); raise ValueError("Google Fonts asset was not a TTF file.")
    digest = hashlib.sha256(raw_font).hexdigest()
    dest_dir = DOWNLOAD_DIR / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / selected["filename"]
    if not dest.exists(): dest.write_bytes(raw_font)
    temp.unlink(missing_ok=True)
    license_file = "OFL.txt" if re.search(r'license:\s*"OFL"', metadata) else ("UFL.txt" if re.search(r'license:\s*"UFL"', metadata) else "LICENSE.txt")
    license_text = None
    try: license_text = _http_get(f"{GOOGLE_RAW}/{used_folder}/{slug}/{license_file}").decode("utf-8", "replace")
    except Exception: pass
    data = _load_catalog()
    for item in data["families"]:
        if item["id"] == family["id"]:
            item["availability"] = "downloaded"
            item["license"] = "OFL-1.1" if license_file == "OFL.txt" else ("UFL-1.0" if license_file == "UFL.txt" else "see_license_file")
            item["license_status"] = "source_metadata"
            variant = {"weight": selected["weight"], "style": selected["style"], "format": "ttf",
                       "file": str(dest.relative_to(LIBRARY_DIR.parent)).replace("\\", "/"), "sha256": digest, "bytes": len(raw_font)}
            if not any(v.get("sha256") == digest for v in item.get("variants", [])):
                item.setdefault("variants", []).append(variant)
            if license_text:
                (dest_dir / license_file).write_text(license_text, "utf-8")
            break
    _save_catalog(data)
    return {"downloaded": True, "family": family["family"], "variant": selected,
            "file": str(dest.relative_to(LIBRARY_DIR.parent)).replace("\\", "/"), "bytes": len(raw_font),
            "sha256": digest, "license_file": license_file,
            "note": "TTF downloaded for local use. This does not establish that PixelLab embeds or resolves it inside PLP projects."}
