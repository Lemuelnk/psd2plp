"""Loss-preserving PLP archive reader/writer.

This module deliberately keeps the complete data.plab document and every
archive resource instead of reducing objects to a lossy intermediate model.
It uses only the Python standard library.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_DATA_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 512
MAX_ENTRY_BYTES = 16 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1000


def _canonical_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\x00" in name:
        raise ValueError("Archive contains an invalid entry name.")
    normalized = name.replace("\\", "/")
    # PixelLab archives may prefix resource paths with '/'. Treat that as
    # archive-root notation, never as a filesystem absolute path.
    normalized = normalized.lstrip("/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError("Archive contains an unsafe path.")
    if any(":" in part for part in path.parts):
        raise ValueError("Archive contains a drive-like path.")
    return path.as_posix()


def _inspect_entries(zf: zipfile.ZipFile) -> tuple[list[zipfile.ZipInfo], dict[str, zipfile.ZipInfo]]:
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise ValueError("Archive contains too many entries.")
    total = 0
    by_name: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        name = _canonical_name(info.filename)
        if name in by_name:
            raise ValueError(f"Archive contains duplicate normalized entry: {name}")
        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            raise ValueError("Symbolic links are not allowed in PLP archives.")
        if info.file_size > MAX_ENTRY_BYTES:
            raise ValueError(f"Archive entry exceeds the {MAX_ENTRY_BYTES}-byte limit: {name}")
        total += info.file_size
        if total > MAX_ARCHIVE_BYTES:
            raise ValueError("Uncompressed archive exceeds the safety limit.")
        if info.file_size and info.compress_size == 0:
            raise ValueError(f"Invalid compressed size for archive entry: {name}")
        if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
            raise ValueError(f"Suspicious compression ratio for archive entry: {name}")
        by_name[name] = info
    if "data.plab" not in by_name:
        raise ValueError("Missing required data.plab entry.")
    if by_name["data.plab"].file_size > MAX_DATA_BYTES:
        raise ValueError("data.plab exceeds the size limit.")
    return infos, by_name


def read_plp(path: str | Path) -> dict[str, Any]:
    """Read a PLP archive without discarding unknown JSON keys or resources."""
    source = Path(path)
    with zipfile.ZipFile(source, "r") as zf:
        infos, by_name = _inspect_entries(zf)
        data_info = by_name["data.plab"]
        raw_data = zf.read(data_info)
        try:
            document = json.loads(raw_data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"data.plab is not valid UTF-8 JSON: {exc}") from exc
        if not isinstance(document, dict):
            raise ValueError("data.plab root must be a JSON object.")
        ids = document.get("objectsIds", [])
        bundle = document.get("objectsBundle", {})
        if not isinstance(ids, list) or not isinstance(bundle, dict):
            raise ValueError("objectsIds must be an array and objectsBundle must be an object.")
        if len(ids) > 500:
            raise ValueError("PLP contains too many objects.")
        missing = [str(item) for item in ids if item not in bundle]
        if missing:
            raise ValueError("objectsIds references missing objectsBundle entries: " + ", ".join(missing[:10]))
        entries = []
        for info in infos:
            entries.append({
                "name": info.filename,
                "canonical_name": _canonical_name(info.filename),
                "bytes": zf.read(info),
                "info": info,
            })
    resources = [
        {"name": item["canonical_name"], "bytes": len(item["bytes"]),
         "sha256": hashlib.sha256(item["bytes"]).hexdigest()}
        for item in entries if item["canonical_name"].startswith("res/")
    ]
    return {
        "path": str(source.resolve()),
        "document": document,
        "raw_data_plab": raw_data,
        "entries": entries,
        "resources": resources,
        "object_count": len(ids),
        "canvas": {"width": document.get("bgWidth"), "height": document.get("bgHeight")},
    }


def write_plp_archive(archive: dict[str, Any], output_path: str | Path) -> Path:
    """Write an archive previously returned by read_plp, preserving entry bytes."""
    target = Path(output_path)
    if target.suffix.lower() != ".plp":
        raise ValueError("Output filename must end in .plp.")
    target.parent.mkdir(parents=True, exist_ok=True)
    entries = archive.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Archive has no entries to write.")
    if target.resolve() == Path(archive.get("path", "")).resolve():
        raise ValueError("Input and output paths must be different.")

    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=str(target.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w") as out:
            for entry in entries:
                info = entry["info"]
                payload = entry["bytes"]
                out.writestr(info, payload)
        # Verify every uncompressed entry before publishing the output.
        with zipfile.ZipFile(temp_path, "r") as check:
            _, check_names = _inspect_entries(check)
            expected = {entry["canonical_name"]: hashlib.sha256(entry["bytes"]).hexdigest() for entry in entries}
            actual = {name: hashlib.sha256(check.read(info)).hexdigest() for name, info in check_names.items()}
            if expected != actual:
                raise ValueError("PLP archive verification failed after writing.")
        os.replace(temp_path, target)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return target


def roundtrip_plp(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Read and rewrite a PLP while preserving all JSON properties and resources."""
    archive = read_plp(input_path)
    target = write_plp_archive(archive, output_path)
    return {
        "success": True,
        "input": archive["path"],
        "output": str(target.resolve()),
        "canvas": archive["canvas"],
        "objects": archive["object_count"],
        "entries": len(archive["entries"]),
        "resources": archive["resources"],
        "preservation": "All uncompressed entry payloads were SHA-256 verified after rewrite.",
        "pixel_lab_compatibility": "Archive payload preservation is verified; opening in PixelLab still requires an app-level test.",
    }
