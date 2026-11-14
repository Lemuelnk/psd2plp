import argparse
import json
from pathlib import Path

from psd2plp.psd.reader import inspect_psd
from psd2plp.convert import convert


def main():
    parser = argparse.ArgumentParser(
        prog="psd2plp",
        description="PSD to PixelLab PLP converter",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="Inspect a PSD document")
    p_inspect.add_argument("input", help="Path to PSD file")

    p_convert = sub.add_parser("convert", help="Convert a PSD to a PLP")
    p_convert.add_argument("input", help="Path to PSD file")
    p_convert.add_argument("-o", "--output", required=True, help="Path to output .plp")
    p_convert.add_argument("--name", default=None,
                           help="Internal PLP preset name (default: output stem)")

    args = parser.parse_args()

    if args.command == "inspect":
        result = inspect_psd(args.input)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.command == "convert":
        out = convert(args.input, args.output, plp_name=args.name)
        print(f"OK: {out}")


if __name__ == "__main__":
    main()
