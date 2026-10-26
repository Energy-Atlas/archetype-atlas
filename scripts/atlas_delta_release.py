"""Assemble, write and verify the ADR 0036 delta release data/atlas-releases/v1.1.0.

Release 1.1.0 is release 1.0.0's writers run on the DOE reference reconciliation's
overlaid sources (ADR 0037, scripts.reconciliation_overlay). The writers and release
1.0.0 stay as they are: the overlay reaches them through their source loaders and the
construction document export for the duration of one build. The folder holds only
the files that differ from 1.0.0; its manifest names the base release with the base
manifest's SHA-256, lists deletions and counts the resolved release. A reader
resolves one base with `files()`.

python -m scripts.atlas_delta_release            # write the folder
python -m scripts.atlas_delta_release --verify   # every file against the manifest, and the base
python -m scripts.atlas_delta_release --check    # rebuild and compare byte for byte
"""
import argparse
import contextlib
import copy
import json
from pathlib import Path

from scripts import (atlas_constructions, atlas_programs, atlas_release, atlas_systems,
                     construction_foundation_release, reconciliation_overlay)
from scripts.atlas_format import suite_bytes
from scripts.common import ROOT

RELEASE = '1.1.0'
TARGET = ROOT/'data/atlas-releases/v1.1.0'
BASE = atlas_release.TARGET
INPUTS = (*atlas_release.INPUTS, 'scripts/program_composition.py',
          'data/reconciliation/doe-reference-v1.json', 'data/reconciliation/doe-reference-values-v1.json',
          'scripts/reconciliation_overlay.py', 'scripts/atlas_delta_release.py')

README = '''# Energy Archetype Atlas release 1.1.0 (commercial, delta)

A delta on release 1.0.0 (ADR 0036): this folder holds only the files that differ
from `data/atlas-releases/v1.0.0`, and `manifest.json` names that base with its
manifest's SHA-256 and lists deleted files. Resolve it by reading the base and
replacing or removing the files listed here (`scripts.atlas_delta_release.files`).

It applies the DOE reference reconciliation to the DOE Ref templates
(docs/adr/0037-doe-reference-reconciliation.md): the DOE v1.4_7.2 post-1980 and
pre-1980 models are the authority for their schedules and loads. The register in
`data/reconciliation/doe-reference-v1.json` records every difference and its
decision; `data/reconciliation/doe-reference-values-v1.json` holds the extracted
values. The 90.1 templates are unchanged.

Verify with `python -m scripts.atlas_delta_release --verify`; rebuild and compare
with `--check`. Upstream notices are in `notices/` of either folder; original Atlas
work remains unlicensed (see `LICENSE`).
'''


@contextlib.contextmanager
def overlaid():
    """The writers' source loaders return the overlaid sources, and construction documents pass the overlay."""
    programs, systems = atlas_programs.load_sources(), atlas_systems.load_sources()
    _, service_schedules = reconciliation_overlay.apply_programs(programs)
    reconciliation_overlay.apply_systems(systems, programs, service_schedules)
    constructions = atlas_constructions.load_sources()
    sets = {row['detailed_context_id']: (constructions.sets[sid], row)
            for sid, rows in constructions.contexts.items() for row in rows}
    overlay = reconciliation_overlay.Constructions()
    export_pair = construction_foundation_release.export_pair

    def overlaid_pair(context_id, *, release=None):
        detailed, unified = copy.deepcopy(export_pair(context_id, release=release))
        if context_id in sets:
            overlay(*sets[context_id], detailed, unified)
        return detailed, unified

    saved = (atlas_programs.load_sources, atlas_systems.load_sources, atlas_constructions.load_sources)
    atlas_programs.load_sources = lambda: programs
    atlas_systems.load_sources = lambda: systems
    atlas_constructions.load_sources = lambda: constructions
    construction_foundation_release.export_pair = overlaid_pair
    try:
        yield
    finally:
        atlas_programs.load_sources, atlas_systems.load_sources, atlas_constructions.load_sources = saved
        construction_foundation_release.export_pair = export_pair


def base_files():
    listed = atlas_release.verify(BASE)
    return {path: (BASE/path).read_bytes() for path in [*listed['files'], 'manifest.json']}


def assemble():
    """The delta files, manifest included, against the written base."""
    with overlaid():
        full = atlas_release.assemble()
    full.pop('manifest.json')
    full['README.md'] = README.encode('utf-8')
    base = base_files()
    changed = {path: data for path, data in full.items() if base.get(path) != data}
    deleted = sorted(set(base) - set(full) - {'manifest.json'})
    resolved = atlas_release.manifest(full)
    manifest = {
        'schema_version': '1.0.0', 'kind': 'atlas_release', 'release': RELEASE, 'status': 'candidate', 'scope': 'commercial',
        'base_release': {'release': '1.0.0', 'path': BASE.relative_to(ROOT).as_posix(),
                         'manifest_sha256': atlas_release.sha(base['manifest.json'])},
        'decision': ['docs/adr/0036-suite-based-release-storage.md', 'docs/adr/0037-doe-reference-reconciliation.md'],
        'deferred': resolved['deferred'], 'generated_by': 'python -m scripts.atlas_delta_release',
        'input_sha256': {path: atlas_release.sha((ROOT/path).read_bytes()) for path in INPUTS},
        'counts': resolved['counts'],
        'files': {path: {'sha256': atlas_release.sha(data), 'bytes': len(data)} for path, data in sorted(changed.items())},
        'deleted': deleted}
    return {**changed, 'manifest.json': suite_bytes(manifest)}


def verify(target=TARGET):
    """The base release, then every delta file with its checksum and size, and nothing else."""
    target = Path(target)
    listed = json.loads((target/'manifest.json').read_text(encoding='utf-8'))
    if listed.get('kind') != 'atlas_release' or listed.get('release') != RELEASE:
        raise ValueError('Not an atlas release 1.1.0 manifest: '+str(target))
    base = ROOT/listed['base_release']['path']
    if atlas_release.sha((base/'manifest.json').read_bytes()) != listed['base_release']['manifest_sha256']:
        raise ValueError('Base release manifest differs from the one this delta names')
    base_listed = atlas_release.verify(base)
    for path, entry in listed['files'].items():
        data = (target/path).read_bytes() if (target/path).is_file() else None
        if data is None:
            raise ValueError('Release file missing: '+path)
        if len(data) != entry['bytes'] or atlas_release.sha(data) != entry['sha256']:
            raise ValueError('Release file checksum or bytes differ: '+path)
    extra = sorted({p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
                   - set(listed['files']) - {'manifest.json'})
    if extra:
        raise ValueError('Release files not in the manifest: '+', '.join(extra[:5]))
    if set(listed['deleted']) - set(base_listed['files']) or set(listed['deleted']) & set(listed['files']):
        raise ValueError('Deleted files must be base files and not delta files')
    stale = sorted(path for path, digest in listed['input_sha256'].items() if atlas_release.sha((ROOT/path).read_bytes()) != digest)
    if stale:
        raise ValueError('Release inputs changed since it was written; rerun python -m scripts.atlas_delta_release: '+', '.join(stale))
    return listed


def files(target=TARGET):
    """The resolved release 1.1.0: base files, replaced and removed as the delta lists."""
    listed = verify(target)
    base = ROOT/listed['base_release']['path']
    out = {path: (base/path).read_bytes() for path in json.loads((base/'manifest.json').read_text(encoding='utf-8'))['files']}
    for path in listed['deleted']:
        del out[path]
    out.update({path: (Path(target)/path).read_bytes() for path in listed['files']})
    return out


def check(target=TARGET):
    """Rebuild the delta and compare it with the written folder byte for byte."""
    verify(target)
    built = assemble()
    written = {p.relative_to(target).as_posix() for p in Path(target).rglob('*') if p.is_file()}
    differ = sorted(p for p in set(built) | written if p not in built or p not in written or (Path(target)/p).read_bytes() != built[p])
    if differ:
        raise ValueError(f'{len(differ)} release files do not reproduce, e.g. '+', '.join(differ[:5]))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        check()
    elif not args.verify:
        atlas_release.write(assemble(), TARGET)
    listed = verify()
    print(f'Atlas release {RELEASE} (commercial, delta on 1.0.0): {len(listed["files"])} files, '
          f'{len(listed["deleted"])} deleted; resolved: '+', '.join(f'{v} {k}' for k, v in listed['counts'].items()))


if __name__ == '__main__':
    main()
