"""Rebuild offline and compare every canonical table byte-for-byte."""
import argparse
import tempfile
from pathlib import Path

from scripts.build import build_atlas, write_atlas
from scripts.common import ROOT, TABLES


def check_rebuild(target, pilot=False):
    target = Path(target)
    with tempfile.TemporaryDirectory() as d:
        rebuilt = Path(d)
        write_atlas(build_atlas(pilot=pilot), rebuilt)
        names = ['metadata.json'] + [t+'.json' for t in TABLES]
        return [name for name in names if not (target/name).is_file() or
                (target/name).read_bytes() != (rebuilt/name).read_bytes()]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('target', nargs='?', type=Path, default=ROOT/'data/processed')
    p.add_argument('--pilot', action='store_true')
    args = p.parse_args()
    mismatches = check_rebuild(args.target, args.pilot)
    if mismatches:
        raise SystemExit('Canonical rebuild mismatch: ' + ', '.join(mismatches))
    print('Offline rebuild matches all canonical JSON tables byte-for-byte')


if __name__ == '__main__':
    main()
