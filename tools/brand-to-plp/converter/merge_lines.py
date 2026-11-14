"""Regroupe les segments <g data-plp-text> d'une meme ligne en un seul texte.

Une ligne = segments avec le meme baseline (y0 proche) ET contigus
horizontalement (x1 du precedent ~ x0 du suivant).
"""
from __future__ import annotations


def merge_segments_into_lines(segments: list[dict],
                                y_tol: float = 3.0,
                                x_tol: float = 8.0) -> list[dict]:
    """segments : [{'bbox', 'text', 'color', 'font_size_canvas',
                    'size_px', 'font_name', 'font_res', 'em_top_canvas'}]

    Retour : liste fusionnee, chaque item = {
        'bbox' (x0,y0,x1,y1 etendu),
        'text' (concatene),
        'runs': [(length, color), ...],
        'font_size_canvas', 'em_top_canvas', 'font_name', 'font_res',
    }
    """
    if not segments:
        return []

    # Tri par baseline puis x
    def _key(s):
        b = s.get("baseline_canvas")
        if b is None:
            b = s["bbox"][1]
        return (round(b / y_tol), s["bbox"][0])

    srt = sorted(segments, key=_key)

    def _baseline(s):
        return s.get("baseline_canvas", s["bbox"][1])

    lines = []
    current = [srt[0]]
    for seg in srt[1:]:
        prev = current[-1]
        same_y = abs(_baseline(seg) - _baseline(prev)) <= y_tol
        if same_y:
            current.append(seg)
        else:
            lines.append(_merge_line(current))
            current = [seg]
    lines.append(_merge_line(current))

    return [l for l in lines if l is not None]


def _merge_line(segments: list[dict]) -> dict | None:
    if not segments:
        return None
    if len(segments) == 1:
        s = segments[0]
        return {
            "bbox": s["bbox"],
            "text": s["text"],
            "runs": [(len(s["text"]), s["color"])],
            "font_size_canvas": s["font_size_canvas"],
            "em_top_canvas": s["em_top_canvas"],
            "baseline_canvas": s.get("baseline_canvas"),
            "font_name": s.get("font_name", ""),
            "font_res": s.get("font_res"),
        }

    # Fusion
    text = "".join(s["text"] for s in segments)
    runs = [(len(s["text"]), s["color"]) for s in segments]
    # bbox etendu
    x0 = min(s["bbox"][0] for s in segments)
    y0 = min(s["bbox"][1] for s in segments)
    x1 = max(s["bbox"][2] for s in segments)
    y1 = max(s["bbox"][3] for s in segments)
    first = segments[0]
    return {
        "bbox": (x0, y0, x1, y1),
        "text": text,
        "runs": runs,
        "font_size_canvas": first["font_size_canvas"],
        "em_top_canvas": first["em_top_canvas"],
        "baseline_canvas": first.get("baseline_canvas"),
        "font_name": first.get("font_name", ""),
        "font_res": first.get("font_res"),
    }
