from __future__ import annotations
from pathlib import Path


def convert(src_path: str, out_path: str, plp_name: str | None = None) -> Path:
    src = Path(src_path)
    out = Path(out_path)
    if not src.is_file():
        raise FileNotFoundError(f"introuvable : {src}")

    suffix = src.suffix.lower()
    if suffix == ".psd":
        from psd2plp.mapping.psd_to_plp import convert_psd
        proj = convert_psd(str(src))
    elif suffix == ".svg":
        from psd2plp.svg.to_plp import svg_to_plp
        proj = svg_to_plp(src)
    else:
        raise ValueError(f"extension non supportee : {suffix}")

    from psd2plp.pixellab.writer import write_plp
    return write_plp(proj, out, plp_name=plp_name or out.stem)
