import argparse
import json
from pathlib import Path

from psd2plp.psd.reader import inspect_psd
from psd2plp.convert import convert


def main():
    parser = argparse.ArgumentParser(
        prog="psd2plp",
        description="PSD/SVG to PixelLab PLP converter",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="Inspect a PSD document")
    p_inspect.add_argument("input", help="Path to PSD file")

    p_convert = sub.add_parser("convert", help="Convert a PSD or SVG to a PLP")
    p_convert.add_argument("input", help="Path to PSD or SVG file")
    p_convert.add_argument("-o", "--output", required=True, help="Path to output .plp")
    p_convert.add_argument("--name", default=None,
                           help="Internal PLP preset name (default: output stem)")

    p_spec = sub.add_parser("from-spec", help="Build a PLP from a JSON spec")
    p_spec.add_argument("input", help="Path to JSON spec")
    p_spec.add_argument("-o", "--output", required=True, help="Path to output .plp")
    p_spec.add_argument("--name", default=None, help="Internal PLP name")

    args = parser.parse_args()

    if args.command == "inspect":
        result = inspect_psd(args.input)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.command == "convert":
        out = convert(args.input, args.output, plp_name=args.name)
        print(f"OK: {out}")
        return

    if args.command == "from-spec":
        from psd2plp.spec import plp_from_spec
        from psd2plp.spec.schema import parse_spec
        from psd2plp.pixellab.writer import write_plp

        with open(args.input) as f:
            data = json.load(f)
        spec = parse_spec(data)
        name = args.name or Path(args.output).stem
        proj = plp_from_spec(spec, plp_name=name)
        out = write_plp(proj, args.output, plp_name=name)
        print(f"OK: {out}")
        return


if __name__ == "__main__":
    main()
