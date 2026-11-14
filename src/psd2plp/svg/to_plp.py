"""SVG -> PlpProject : un objet par element (natif si possible, raster sinon)."""
from __future__ import annotations
import io
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image

from psd2plp.pixellab.model import PlpProject, PlpObject, PlpResource
from psd2plp.svg.reader import read_svg
from psd2plp.svg.native_shape import try_native_shape


REF_WIDTH = 708
MAX_RASTER = 2048
SVG_NS = "http://www.w3.org/2000/svg"


def _tag(elem) -> str:
    return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag


def _element_to_svg(elem, vb_w, vb_h) -> bytes:
    wrapper = ET.Element(
        f"{{{SVG_NS}}}svg",
        {"viewBox": f"0 0 {vb_w} {vb_h}", "width": str(vb_w), "height": str(vb_h)},
    )
    wrapper.append(elem)
    return ET.tostring(wrapper, encoding="utf-8")


def _rasterize_element(elem, vb_w, vb_h, px_w, px_h):
    import cairosvg
    try:
        return cairosvg.svg2png(
            bytestring=_element_to_svg(elem, vb_w, vb_h),
            output_width=px_w, output_height=px_h,
        )
    except Exception:
        return None


def _crop_to_content(png_bytes):
    try:
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        bbox = img.getbbox()
        if bbox is None:
            return None
        cropped = img.crop(bbox)
        buf = io.BytesIO()
        cropped.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), bbox
    except Exception:
        return None


def _element_to_plp(elem, doc, px_w, px_h, container_w, container_h,
                    add_resource, ref_counter):
    """Retourne un PlpObject (natif ou raster) ou None."""
    # 1) Essaie forme native
    native = try_native_shape(elem, doc.width, doc.height, container_w, container_h)
    if native is not None:
        x0, y0, x1, y1 = [float(v) for v in native["vCScn1x"]]
        cx0 = x0 / 100.0 * container_w
        cy0 = y0 / 100.0 * container_h
        cx1 = x1 / 100.0 * container_w
        cy1 = y1 / 100.0 * container_h

        # Rasterise AUSSI pour avoir un PNG de secours
        raw = _rasterize_element(elem, doc.width, doc.height, px_w, px_h)
        res_name = None
        if raw:
            cropped = _crop_to_content(raw)
            if cropped:
                res_name = add_resource(cropped[0])

        ref_counter[0] += 1
        obj = PlpObject(
            kind="shape",
            x=cx0, y=cy0,
            width=cx1 - cx0, height=cy1 - cy0,
            opacity=100,
            image_shape_type=5,
            resource_name=res_name,
            reference=f"n{ref_counter[0]:04d}",
        )
        obj.qUDmYrz = native
        return obj

    # 2) Fallback : raster
    raw = _rasterize_element(elem, doc.width, doc.height, px_w, px_h)
    if not raw:
        return None
    cropped = _crop_to_content(raw)
    if not cropped:
        return None
    png_bytes, bbox = cropped
    x0, y0, x1, y1 = bbox
    res_name = add_resource(png_bytes)
    ref_counter[0] += 1
    return PlpObject(
        kind="shape",
        x=x0 * container_w / px_w,
        y=y0 * container_h / px_h,
        width=(x1 - x0) * container_w / px_w,
        height=(y1 - y0) * container_h / px_h,
        opacity=100,
        image_shape_type=2,
        resource_name=res_name,
        reference=f"r{ref_counter[0]:04d}",
    )


def svg_to_plp(svg_path, bg_color: int = 0) -> PlpProject:
    svg_path = Path(svg_path)
    doc = read_svg(svg_path)

    container_w = REF_WIDTH
    container_h = round(REF_WIDTH * doc.height / doc.width)

    proj = PlpProject(
        width=int(round(doc.width)),
        height=int(round(doc.height)),
        bg_color=bg_color,
    )
    proj.raw_template["_container_w"] = container_w
    proj.raw_template["_container_h"] = int(container_h)

    scale = min(MAX_RASTER / doc.width, MAX_RASTER / doc.height)
    px_w = max(1, int(round(doc.width * scale)))
    px_h = max(1, int(round(doc.height * scale)))

    used = set()
    def add_resource(png):
        name = f"r{len(used):04d}"
        used.add(name)
        proj.resources.append(PlpResource(name=name, kind="png", data=png))
        return name

    ref_counter = [0]
    children = list(doc.root) if doc.root is not None else []
    for elem in children:
        obj = _element_to_plp(elem, doc, px_w, px_h,
                              container_w, container_h,
                              add_resource, ref_counter)
        if obj is not None:
            proj.objects.append(obj)

    # Thumb
    try:
        import cairosvg
        full = cairosvg.svg2png(url=str(svg_path), output_width=px_w, output_height=px_h)
        thumb = Image.open(io.BytesIO(full)).convert("RGBA")
        thumb.thumbnail((512, 512))
        has_alpha = False
        try:
            has_alpha = thumb.getchannel("A").getextrema()[0] < 255
        except Exception:
            pass
        buf = io.BytesIO()
        if has_alpha:
            thumb.save(buf, format="PNG", optimize=True)
        else:
            thumb.convert("RGB").save(buf, format="JPEG", quality=80)
        proj.raw_template["_thumb_bytes"] = buf.getvalue()
    except Exception:
        pass

    return proj
