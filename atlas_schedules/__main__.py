"""Command line: python -m atlas_schedules request.json [-o bundle.json]."""
import argparse
import json
from pathlib import Path
import sys

from .errors import GeneratorError
from .generator import generate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="atlas_schedules", description="Generate a schedule bundle from a request.")
    parser.add_argument("request", type=Path, help="request JSON (schema 3.0.0)")
    parser.add_argument("-o", "--output", type=Path, help="write the bundle here instead of standard output")
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.request.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: cannot read {args.request}: {error}", file=sys.stderr)
        return 2
    try:
        bundle = generate(document)
    except GeneratorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    text = json.dumps(bundle, separators=(",", ":"))
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
