"""Extract the pinned DOE reference and PNNL prototype archives for local comparison.

python -m scripts.reference_models --cache-root <dir> --extract-root <dir> [--source doe-reference|pnnl-prototypes]

Archives come from sources/reference-models-lock.json and are verified with
scripts.fetch before extraction. Each archive extracts to
<extract-root>/<source_id>/<archive path without .zip>/. Directory entries are
skipped (the DOE archives carry "./" and "../" entries); a file entry that would
land outside its folder is refused. Existing files must already hold the same bytes.
"""
import argparse
import zipfile
from pathlib import Path

from scripts import fetch
from scripts.common import ROOT, load_json

LOCK = ROOT/'sources/reference-models-lock.json'


def members(archive, dest):
    base = dest.resolve()
    for info in archive.infolist():
        if info.is_dir():
            continue
        target = (base/info.filename).resolve()
        if base not in target.parents:
            raise ValueError(f'Unsafe archive entry: {info.filename}')
        yield info, target


def extract(entry, cache_root, extract_root):
    archive_path = fetch.verify_file(entry, cache_root)
    dest = Path(extract_root)/entry['source_id']/entry['path'].removesuffix('.zip')
    count = 0
    with zipfile.ZipFile(archive_path) as archive:
        for info, target in members(archive, dest):
            content = archive.read(info)
            if target.exists():
                if target.read_bytes() != content:
                    raise ValueError(f'Extracted file differs from its archive: {target}')
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            count += 1
    return dest, count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-root', type=Path, required=True)
    parser.add_argument('--extract-root', type=Path, required=True)
    parser.add_argument('--source', choices=['doe-reference', 'pnnl-prototypes'])
    args = parser.parse_args()
    entries = [e for e in load_json(LOCK)['files'] if args.source in (None, e['source_id'])]
    total = 0
    for entry in entries:
        _, count = extract(entry, args.cache_root, args.extract_root)
        total += count
    print(f'Extracted {total} files from {len(entries)} verified archives')


if __name__ == '__main__':
    main()
