"""Assemble, write and verify ADR 0036 minor (delta) releases from release 1.2.0 on.

python -m scripts.atlas_minor_release --release 1.2.0            # write the folder
python -m scripts.atlas_minor_release --release 1.2.0 --verify   # every file against the manifest, and the base
python -m scripts.atlas_minor_release --release 1.2.0 --check    # rebuild and compare byte for byte

A minor release is release 1.0.0's writers run on overlaid sources. A reader resolves
one base only, so each minor is a delta on 1.0.0 that holds everything changed
since then: release 1.2.0 applies the DOE reference reconciliation of 1.1.0
(ADR 0037) and then the construction-only programs (ADR 0039). The writers and
release 1.0.0 stay as they are: the overlays reach them through their source
loaders and the construction document export for the length of one build.
Release 1.1.0 keeps its own builder, scripts.atlas_delta_release.
"""
import argparse
import contextlib
import copy
import json
from pathlib import Path

from scripts import (atlas_constructions, atlas_programs, atlas_release, atlas_systems,
                     construction_foundation_release, construction_only_overlay, reconciliation_overlay)
from scripts.atlas_format import suite_bytes
from scripts.common import ROOT

BASE = atlas_release.TARGET
RECONCILIATION = ('scripts/program_composition.py', 'data/reconciliation/doe-reference-v1.json',
                  'data/reconciliation/doe-reference-values-v1.json', 'scripts/reconciliation_overlay.py')
CONSTRUCTION_ONLY = ('data/program-inputs/construction-only-v1.json', 'scripts/construction_only_overlay.py')
RELEASES = {
    '1.2.0': {
        'overlays': ('reconciliation', 'construction_only'),
        'inputs': (*atlas_release.INPUTS, *RECONCILIATION, *CONSTRUCTION_ONLY, 'scripts/atlas_minor_release.py'),
        'decisions': ('docs/adr/0036-suite-based-release-storage.md', 'docs/adr/0037-doe-reference-reconciliation.md',
                      'docs/adr/0039-construction-only-programs.md'),
        'readme': '''# Energy Archetype Atlas release 1.2.0 (commercial, delta)

A delta on release 1.0.0 (ADR 0036): this folder holds only the files that differ
from `data/atlas-releases/v1.0.0`, and `manifest.json` names that base with its
manifest's SHA-256 and lists deleted files. Resolve it by reading the base and
replacing or removing the files listed here (`scripts.atlas_minor_release.files`).

It holds everything release 1.1.0 changed, the DOE reference reconciliation of the
DOE Ref templates (docs/adr/0037-doe-reference-reconciliation.md), and adds programs
to the 51 folders that had construction sets only
(docs/adr/0039-construction-only-programs.md): college, courthouse, laboratory,
data centres, the detailed offices, the generic office and the tall buildings.

Verify with `python -m scripts.atlas_minor_release --release 1.2.0 --verify`; rebuild
and compare with `--check`. Upstream notices are in `notices/` of either folder;
original Atlas work remains unlicensed (see `LICENSE`).
'''},
}


def target(release):
    return ROOT/f'data/atlas-releases/v{release}'


@contextlib.contextmanager
def overlaid(overlays):
    """The writers' source loaders return the overlaid sources, and construction documents pass the overlay."""
    programs, systems = atlas_programs.load_sources(), atlas_systems.load_sources()
    if 'reconciliation' in overlays:
        _, service_schedules = reconciliation_overlay.apply_programs(programs)
        reconciliation_overlay.apply_systems(systems, programs, service_schedules)
    if 'construction_only' in overlays:
        construction_only_overlay.apply(programs, systems)
    constructions = atlas_constructions.load_sources()
    sets = {row['detailed_context_id']: (constructions.sets[sid], row)
            for sid, rows in constructions.contexts.items() for row in rows}
    document_overlay = reconciliation_overlay.Constructions() if 'reconciliation' in overlays else None
    export_pair = construction_foundation_release.export_pair

    def overlaid_pair(context_id, *, release=None):
        detailed, unified = copy.deepcopy(export_pair(context_id, release=release))
        if document_overlay and context_id in sets:
            document_overlay(*sets[context_id], detailed, unified)
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


def assemble(release):
    """The delta files, manifest included, against the written base."""
    spec = RELEASES[release]
    with overlaid(spec['overlays']):
        full = atlas_release.assemble()
    full.pop('manifest.json')
    full['README.md'] = spec['readme'].encode('utf-8')
    base = base_files()
    changed = {path: data for path, data in full.items() if base.get(path) != data}
    deleted = sorted(set(base) - set(full) - {'manifest.json'})
    resolved = atlas_release.manifest(full)
    manifest = {
        'schema_version': '1.0.0', 'kind': 'atlas_release', 'release': release, 'status': 'candidate', 'scope': 'commercial',
        'base_release': {'release': '1.0.0', 'path': BASE.relative_to(ROOT).as_posix(),
                         'manifest_sha256': atlas_release.sha(base['manifest.json'])},
        'decision': list(spec['decisions']), 'deferred': resolved['deferred'],
        'generated_by': f'python -m scripts.atlas_minor_release --release {release}',
        'input_sha256': {path: atlas_release.sha((ROOT/path).read_bytes()) for path in spec['inputs']},
        'counts': resolved['counts'],
        'files': {path: {'sha256': atlas_release.sha(data), 'bytes': len(data)} for path, data in sorted(changed.items())},
        'deleted': deleted}
    return {**changed, 'manifest.json': suite_bytes(manifest)}


def verify(release):
    """The base release, then every delta file with its checksum and size, and nothing else."""
    folder = target(release)
    listed = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    if listed.get('kind') != 'atlas_release' or listed.get('release') != release:
        raise ValueError(f'Not an atlas release {release} manifest: {folder}')
    base = ROOT/listed['base_release']['path']
    if atlas_release.sha((base/'manifest.json').read_bytes()) != listed['base_release']['manifest_sha256']:
        raise ValueError('Base release manifest differs from the one this delta names')
    base_listed = atlas_release.verify(base)
    for path, entry in listed['files'].items():
        data = (folder/path).read_bytes() if (folder/path).is_file() else None
        if data is None:
            raise ValueError('Release file missing: '+path)
        if len(data) != entry['bytes'] or atlas_release.sha(data) != entry['sha256']:
            raise ValueError('Release file checksum or bytes differ: '+path)
    extra = sorted({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
                   - set(listed['files']) - {'manifest.json'})
    if extra:
        raise ValueError('Release files not in the manifest: '+', '.join(extra[:5]))
    if set(listed['deleted']) - set(base_listed['files']) or set(listed['deleted']) & set(listed['files']):
        raise ValueError('Deleted files must be base files and not delta files')
    stale = sorted(path for path, digest in listed['input_sha256'].items() if atlas_release.sha((ROOT/path).read_bytes()) != digest)
    if stale:
        raise ValueError(f'Release inputs changed since it was written; rerun python -m scripts.atlas_minor_release '
                         f'--release {release}: '+', '.join(stale))
    return listed


def files(release):
    """The resolved release: base files, replaced and removed as the delta lists."""
    listed = verify(release)
    base = ROOT/listed['base_release']['path']
    out = {path: (base/path).read_bytes() for path in json.loads((base/'manifest.json').read_text(encoding='utf-8'))['files']}
    for path in listed['deleted']:
        del out[path]
    out.update({path: (target(release)/path).read_bytes() for path in listed['files']})
    return out


def check(release):
    """Rebuild the delta and compare it with the written folder byte for byte."""
    verify(release)
    built, folder = assemble(release), target(release)
    written = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    differ = sorted(p for p in set(built) | written if p not in built or p not in written or (folder/p).read_bytes() != built[p])
    if differ:
        raise ValueError(f'{len(differ)} release files do not reproduce, e.g. '+', '.join(differ[:5]))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--release', choices=sorted(RELEASES), required=True)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        check(args.release)
    elif not args.verify:
        atlas_release.write(assemble(args.release), target(args.release))
    listed = verify(args.release)
    print(f'Atlas release {args.release} (commercial, delta on 1.0.0): {len(listed["files"])} files, '
          f'{len(listed["deleted"])} deleted; resolved: '+', '.join(f'{v} {k}' for k, v in listed['counts'].items()))


if __name__ == '__main__':
    main()
