from __future__ import annotations
import json, zipfile
from pathlib import Path
from .model import PlpProject, PlpObject, PlpResource


def _kind(b):
    if b.startswith(b"\x89PNG"): return "png"
    if b.startswith(b"\xff\xd8\xff"): return "jpg"
    if b.startswith(b"OTTO"): return "otf"
    if b[:4] in (b"\x00\x01\x00\x00", b"true", b"ttcf"): return "ttf"
    return "bin"


def read_plp(path):
    with zipfile.ZipFile(Path(path)) as z:
        data = json.loads(z.read("data.plab"))
        resources = []
        for n in z.namelist():
            if n.lstrip("/").startswith("res/") and not n.endswith("/"):
                raw = z.read(n)
                resources.append(PlpResource(n.split("/")[-1], _kind(raw), raw))

    objects = []
    for key in data.get("objectsIds", []):
        o = data["objectsBundle"].get(key, {})
        if key.startswith("shape"):
            objects.append(PlpObject(
                kind="shape",
                x=o.get("shapeX", 0), y=o.get("shapeY", 0),
                width=float(o.get("shapeWidth", 0)),
                height=float(o.get("shapeHeight", 0)),
                rotation=float(o.get("shapeRotation", 0)),
                opacity=o.get("shapeOpacity", 100),
                reference=o.get("shapeReference", ""),
            ))
        elif key.startswith("text"):
            c = o.get("textTextColor", {}).get("interval1", {}).get("textsIntervalsColor", -1)
            objects.append(PlpObject(
                kind="text",
                x=o.get("shapeX", 0), y=o.get("shapeY", 0),
                text=o.get("textTextString", ""),
                text_size=float(o.get("textTextSize", 32)),
                text_color=c,
                rotation=float(o.get("textRotation", 0)),
                opacity=o.get("textOpacity", 100),
                reference=o.get("textReference", ""),
                max_width=o.get("textMaxWidth", -1),
            ))

    return PlpProject(
        width=data.get("bgWidth", 0),
        height=data.get("bgHeight", 0),
        bg_color=data.get("bgColor", -1),
        objects=objects,
        resources=resources,
        raw_template=data,
    )
