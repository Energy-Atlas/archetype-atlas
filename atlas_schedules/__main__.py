"""Command line.

atlas-schedules request.json [-o bundle.json] [--release-dir DIR]   # generate a bundle (request schema 4.0.0)
atlas-schedules translate request.json [-o request-4.json]          # rewrite a 3.0.0 request's definition IDs as release IDs
atlas-schedules --version                                           # generator, request schema and the release it reads

`python -m atlas_schedules` runs the same commands. The release read is, in order, `--release-dir`,
`ATLAS_RELEASES`, the source tree's `data/atlas-releases` and the generator view the wheel bundles
(atlas_schedules.release, ADR 0051).
"""
import argparse
import json
from pathlib import Path
import sys

from . import REQUEST_SCHEMA_VERSION, __version__
from .errors import GeneratorError
from .generator import generate
from .release import current, set_releases, translate


def version_line() -> str:
    try:
        release = current()
        read = f"atlas release {release.version} from {release.store.describe()}"
    except GeneratorError as error:
        read = f"no atlas release ({error.message})"
    return f"atlas-schedules {__version__} (request schema {REQUEST_SCHEMA_VERSION}); reads {read}"


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: cannot read {path}: {error}", file=sys.stderr)
        return None


def _write(document: dict, output: Path | None, compact: bool) -> None:
    text = json.dumps(document, separators=(",", ":")) if compact else json.dumps(document, indent=2)
    if output:
        output.write_text(text + "\n", encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text + "\n")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="atlas-schedules", description="Generate a schedule bundle from a request.")
    parser.add_argument("--version", action="store_true", help="print the generator version and the atlas release it reads")
    parser.add_argument("--release-dir", type=Path, metavar="DIR",
                        help="read the atlas release here (a releases folder, one release folder or a generator view) "
                             "instead of ATLAS_RELEASES or the bundled view")
    commands = parser.add_subparsers(dest="command")
    generate_parser = commands.add_parser("generate", help="generate a bundle (the default command)")
    generate_parser.add_argument("request", type=Path, help=f"request JSON (schema {REQUEST_SCHEMA_VERSION})")
    generate_parser.add_argument("-o", "--output", type=Path, help="write the bundle here instead of standard output")
    translate_parser = commands.add_parser("translate", help="rewrite a 3.0.0 request's definition IDs as release IDs and views")
    translate_parser.add_argument("request", type=Path, help="request JSON with program-… or service-… IDs")
    translate_parser.add_argument("-o", "--output", type=Path, help="write the 4.0.0 request here instead of standard output")
    # The request path alone still generates, as it did before 4.0.0: the first positional that is not an
    # option's value names the command, else it is the request.
    positional, skip = [], False
    for index, token in enumerate(argv):
        if skip:
            skip = False
        elif token in ("--release-dir", "-o", "--output"):
            skip = True
        elif not token.startswith("-"):
            positional.append(index)
    if positional and argv[positional[0]] not in ("generate", "translate"):
        argv.insert(positional[0], "generate")
    args = parser.parse_args(argv)
    if args.release_dir:
        set_releases(args.release_dir)
    if args.version:
        print(version_line())
        return 0
    if args.command is None:
        parser.print_usage(sys.stderr)
        return 2
    document = _read(args.request)
    if document is None:
        return 2
    try:
        if args.command == "translate":
            _write(translate(document), args.output, compact=False)
            return 0
        bundle = generate(document)
    except GeneratorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    _write(bundle, args.output, compact=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
