"""Write, check and read the delta releases on the 2.0.0 snapshot (ADR 0036 section 2, ADR 0046).

python -m scripts.atlas_delta --write     # write data/atlas-releases/v2.1.0 from its pinned inputs
python -m scripts.atlas_delta --check     # rebuild the delta and fail unless the folder already equals it
python -m scripts.atlas_delta --verify    # every file against the manifest, and the base manifest unchanged

A delta holds only the files that differ from its base, with `manifest.json` naming the
base and that base manifest's SHA-256; a reader resolves one base (`files()`). The base
of every delta is the full snapshot 2.0.0 (`scripts.atlas_snapshot`); no file is removed.

Release 2.1.0 (CHANGELOG 2026-10-29; ADR 0046 section 12):
- `LICENSE`: the root open-licence text (ADR 0048 item 4), in place of the unlicensed
  text 2.0.0 packaged;
- `README.md`: the delta's own description;
- `generator.json` of the eight apartment folders (90.1-2007, 2013 and 2019 Midrise and
  Highrise, DOE Ref Midrise): every `apartment_unit` recipe is the generator 3.0.0 ResStock
  unit recipe of the same program ID (`atlas_schedules/data/recipes/`, written by
  `scripts.build_apartment_units` and `build_reference_recipes` from 2.0.0; ADR 0047),
  in place of the 2.x prototype recipe; the other entries are unchanged;
- `manifest.json`: `generator` names the generator version, package, wheel and tag the
  recipes ship in (ADR 0049), and `input_sha256` pins the inputs above.
Every other file of 2.1.0 is 2.0.0's. Apartment recipes still read 2.0.0's prototype recipes
as their input, so `build_apartment_units --check` keeps reading 2.0.0.
"""
import argparse
import hashlib
import json
from pathlib import Path

import atlas_schedules
from scripts import atlas_snapshot
from scripts.atlas_format import canonical
from scripts.common import ROOT

RELEASE = '2.1.0'
BASE = atlas_snapshot.RELEASE
RELEASES = ROOT/'data/atlas-releases'
TARGET = RELEASES/f'v{RELEASE}'
RECIPES = ROOT/'atlas_schedules/data/recipes'
PACKAGE = 'atlas-schedules'
STATUS = 'released'
DECISIONS = ('docs/adr/0046-release-2-0-0.md', 'docs/adr/0047-resstock-apartment-units-and-source-magnitudes.md',
             'docs/adr/0048-open-licences.md', 'docs/adr/0049-atlas-schedules-packaging.md')
README = """# Energy Archetype Atlas release 2.1.0 (commercial and residential, delta on 2.0.0)

A delta release (ADR 0036 section 2, ADR 0046 section 12): this folder holds only the
files that differ from release 2.0.0, which `manifest.json` names as `base_release` with
its manifest's SHA-256. Every other file is 2.0.0's; nothing is removed. Resolve it with
`python -m scripts.atlas_delta` (`scripts.atlas_delta.files('2.1.0')`), or copy the 2.0.0
folder and overlay this one.

What differs from 2.0.0:

- `LICENSE`: original code MIT, original data and documentation CC BY 4.0 (ADR 0048);
- `generator.json` of the eight apartment folders: every apartment-unit recipe is the
  generator 3.0.0 ResStock multifamily unit recipe (ADR 0047), which the `atlas-schedules`
  3.0.0 package ships (ADR 0049; `manifest.json` `generator`).

Verify with `python -m scripts.atlas_delta --verify`; rebuild and compare with `--check`.
Upstream notices are in 2.0.0's `notices/`.
"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tree_sha(folder):
    """SHA-256 over the sorted relative paths and contents of a folder."""
    digest = hashlib.sha256()
    for path in sorted(p for p in Path(folder).rglob('*') if p.is_file()):
        digest.update(path.relative_to(folder).as_posix().encode()+b'\0'+hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def nested(value, levels=3):
    """One record per line down to `levels` levels, as 2.0.0 stores its indented files (keys sorted)."""
    def encode(value, depth):
        if depth == levels or not isinstance(value, dict) or not value:
            return canonical(value)
        pad = ' '*depth
        rows = [f'{pad}{json.dumps(k, ensure_ascii=False)}:{encode(v, depth+1)}' for k, v in sorted(value.items())]
        return '{\n'+',\n'.join(rows)+'\n'+' '*(depth-1)+'}'
    return (encode(value, 1)+'\n').encode('utf-8')


def unit_recipes(base):
    """{path: bytes} of every base generator.json whose apartment-unit recipes the packaged ones replace."""
    out = {}
    for path, data in sorted(base.items()):
        if not path.endswith('/generator.json'):
            continue
        table = json.loads(data)
        changed = False
        for views in table.values():
            for view, recipe in views.items():
                if recipe['kind'] == 'apartment_unit':
                    packaged = json.loads((RECIPES/f"{recipe['program_id']}.json").read_text(encoding='utf-8'))
                    if packaged['kind'] != 'apartment_unit' or 'resstock_unit' not in packaged:
                        raise ValueError('Packaged recipe is not a ResStock unit: '+recipe['program_id'])
                    views[view] = packaged
                    changed = True
        if changed:
            out[path] = nested(table)
    return out


def build(base):
    """{path: bytes} of the delta's files, manifest excluded."""
    return {'LICENSE': (ROOT/'LICENSE').read_bytes(), 'README.md': README.encode('utf-8'), **unit_recipes(base)}


def manifest(delta, base_manifest):
    version = atlas_schedules.__version__
    return {
        'kind': 'atlas_release', 'schema_version': base_manifest['schema_version'], 'release': RELEASE,
        'scope': base_manifest['scope'], 'status': STATUS,
        'base_release': {'release': BASE, 'path': atlas_snapshot.TARGET.relative_to(ROOT).as_posix(),
                         'manifest_sha256': sha((atlas_snapshot.TARGET/'manifest.json').read_bytes())},
        'generated_by': 'python -m scripts.atlas_delta --write',
        'decision': list(DECISIONS),
        'generator': {'version': version, 'package': PACKAGE, 'wheel': f'atlas_schedules-{version}-py3-none-any.whl',
                      'release_tag': f'{PACKAGE}-v{version}', 'request_schema_version': '3.0.0',
                      'recipes_sha256': tree_sha(RECIPES)},
        'input_sha256': {'LICENSE': sha((ROOT/'LICENSE').read_bytes()),
                         'atlas_schedules/__init__.py': sha((ROOT/'atlas_schedules/__init__.py').read_bytes()),
                         'atlas_schedules/data/recipes': tree_sha(RECIPES),
                         f'data/atlas-releases/v{BASE}/manifest.json': sha((atlas_snapshot.TARGET/'manifest.json').read_bytes()),
                         'scripts/atlas_delta.py': sha(Path(__file__).read_bytes())},
        'counts': base_manifest['counts'],
        'deferred': [d for d in base_manifest['deferred'] if not d.startswith('ADR 0046 phase 2')],
        'files': {p: {'sha256': sha(d), 'bytes': len(d)} for p, d in sorted(delta.items())},
        'removed': [],
    }


def manifest_bytes(listed):
    return (json.dumps(listed, indent=2, sort_keys=True, ensure_ascii=False)+'\n').encode('utf-8')


def verify(folder=TARGET):
    """The manifest, after checking every file against it, no other file present, and the base manifest unchanged."""
    listed = json.loads((Path(folder)/'manifest.json').read_text(encoding='utf-8'))
    base = listed.get('base_release') or {}
    if listed.get('kind') != 'atlas_release' or base.get('release') != BASE:
        raise ValueError(f'Not a delta atlas release on {BASE}: {folder}')
    if sha((ROOT/base['path']/'manifest.json').read_bytes()) != base['manifest_sha256']:
        raise ValueError(f'Base release {BASE} manifest differs from the one the delta was written on')
    for path, entry in listed['files'].items():
        p = Path(folder)/path
        data = p.read_bytes() if p.is_file() else None
        if data is None or len(data) != entry['bytes'] or sha(data) != entry['sha256']:
            raise ValueError('Release file missing or differs: '+path)
    extra = sorted({p.relative_to(folder).as_posix() for p in Path(folder).rglob('*') if p.is_file()} - set(listed['files']) - {'manifest.json'})
    if extra:
        raise ValueError('Release files not in the manifest: '+', '.join(extra[:5]))
    return listed


def files(release=RELEASE):
    """Every file of a release in the tree, resolved: the base's files with the delta's laid over."""
    if release == BASE:
        return atlas_snapshot.files()
    if release != RELEASE:
        raise ValueError(f'Release {release} is not in the tree')
    listed = verify()
    resolved = atlas_snapshot.files()
    for path in listed['removed']:
        del resolved[path]
    for path in listed['files']:
        resolved[path] = (TARGET/path).read_bytes()
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', action='store_true')
    group.add_argument('--check', action='store_true')
    group.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        listed = verify()
        print(f'Atlas release {RELEASE} (delta on {BASE}): {len(listed["files"])} files differ, generator '
              f'{listed["generator"]["version"]} ({listed["generator"]["wheel"]})')
        return
    base_manifest = atlas_snapshot.verify()
    delta = build(atlas_snapshot.files())
    delta['manifest.json'] = manifest_bytes(manifest(delta, base_manifest))
    if args.check:
        stale = [p for p, d in delta.items() if not (TARGET/p).is_file() or (TARGET/p).read_bytes() != d]
        extra = sorted({p.relative_to(TARGET).as_posix() for p in TARGET.rglob('*') if p.is_file()} - set(delta)) if TARGET.is_dir() else ['(missing)']
        if stale or extra:
            raise SystemExit(f'Release {RELEASE} differs from its inputs: {len(stale)} stale, {len(extra)} extra, '
                             f'e.g. {(stale + extra)[:3]}; run python -m scripts.atlas_delta --write')
        print(f'Release {RELEASE} reproduces from its inputs: {len(delta) - 1} files and the manifest')
        return
    for path in sorted(p for p in TARGET.rglob('*') if p.is_file()) if TARGET.is_dir() else []:
        if path.relative_to(TARGET).as_posix() not in delta:
            path.unlink()
    for path, data in sorted(delta.items()):
        out = TARGET/path
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.is_file() or out.read_bytes() != data:
            out.write_bytes(data)
    verify()
    print(f'Release {RELEASE} written: {len(delta) - 1} files and the manifest')


if __name__ == '__main__':
    main()
