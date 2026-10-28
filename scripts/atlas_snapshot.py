"""Verify and read release 2.0.0, the full snapshot that ends the 1.x delta chain (ADR 0046).

python -m scripts.atlas_snapshot --verify   # every file against the manifest

Release 2.0.0 is release 1.6.0 resolved and stored whole (ADR 0046 sections 2 and 6):
- no base release: a reader opens this folder alone, and later minors are deltas on it;
- every indented JSON file one record per line down to three levels; line tables as they were;
- the generator recipes beside the programs they belong to, one `generator.json` per folder keyed
  by release program ID: the source and reviewed recipes of the 90.1 programs and the source
  recipes of the DOE Ref programs (scripts.build_reference_recipes);
- daylighting fractions as plain values (`lighting_controls.geometry_dependent` dropped, user
  decision L-1); program IDs those of 1.6.0;
- `exporter-inputs.json`: what the exporters took from the frozen folders, so the release reads
  no other folder.

The writer read release 1.6.0 and the frozen definitions, which left the tree in stage X1.3
(ADR 0046 section 7); it is readable at the tag `frozen-data-2026-10-27`, together with
`--check`. The manifest keeps the writer's input digests as provenance. Readers verify the files
alone; milestone B's writers write the next release.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.common import ROOT

RELEASE = '2.0.0'
TARGET = ROOT/f'data/atlas-releases/v{RELEASE}'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(folder=TARGET):
    """The manifest, after checking every file against it and that no other file is present."""
    listed = json.loads((Path(folder)/'manifest.json').read_text(encoding='utf-8'))
    if listed.get('kind') != 'atlas_release' or listed.get('release') != RELEASE or listed.get('base_release') is not None:
        raise ValueError(f'Not a full atlas release {RELEASE} manifest: {folder}')
    for path, entry in listed['files'].items():
        p = Path(folder)/path
        data = p.read_bytes() if p.is_file() else None
        if data is None or len(data) != entry['bytes'] or sha(data) != entry['sha256']:
            raise ValueError('Release file missing or differs: '+path)
    extra = sorted({p.relative_to(folder).as_posix() for p in Path(folder).rglob('*') if p.is_file()} - set(listed['files']) - {'manifest.json'})
    if extra:
        raise ValueError('Release files not in the manifest: '+', '.join(extra[:5]))
    return listed


def files(folder=TARGET):
    """Every file, checked against the manifest."""
    listed = verify(folder)
    return {path: (Path(folder)/path).read_bytes() for path in listed['files']}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--verify', action='store_true', help='the default, kept for the earlier command line')
    parser.parse_args()
    listed = verify()
    size = sum(e['bytes'] for e in listed['files'].values())
    print(f'Atlas release {RELEASE} (full snapshot of {listed["snapshot_of"]["release"]}): {len(listed["files"])} files, '
          f'{size/1e6:.0f} MB; '+', '.join(f'{v} {k}' for k, v in listed['counts'].items()))


if __name__ == '__main__':
    main()
