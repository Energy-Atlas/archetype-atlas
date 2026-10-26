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

Research assumptions in the new folders (user decisions, ADR 0039):
- Fillings follow the resolution policy's rules for no gas, no occupancy, no
  lighting, unconditioned spaces and no hot water. In the filled export,
  Courthouse schedules without design days take the Wednesday profile on design
  days, and Courthouse BLDG_EQUIP_SCH takes the Sunday profile on holidays.
- Values still null after those rules are borrowed in the filled export:
  densities from the same or an analogous space type elsewhere, schedules and
  setpoints from the building's most common ones. The source export keeps them
  null.
- The generic office has no prototype. Its hot water is the large detailed
  office's lumped main draw divided by that building's counted floor area, as a
  building draw per floor area.

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
    frozen_addressed = atlas_programs.addressed
    if 'construction_only' in overlays:
        atlas_programs.addressed = lambda field: construction_only_overlay.addressed(field, frozen_addressed)
    atlas_programs.load_sources = lambda: programs
    atlas_systems.load_sources = lambda: systems
    atlas_constructions.load_sources = lambda: constructions
    construction_foundation_release.export_pair = overlaid_pair
    try:
        yield
    finally:
        atlas_programs.load_sources, atlas_systems.load_sources, atlas_constructions.load_sources = saved
        atlas_programs.addressed = frozen_addressed
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


# >>> release 1.3.0
# Release 1.2.0 pins this file by SHA-256. Later releases are therefore added as tagged
# blocks like this one, before the main guard; when a release that pins an earlier form of
# the file is verified, the blocks of later releases are stripped first, which restores the
# exact bytes that built it (ADR 0040, agent decisions). Nothing above this block changes.
import re  # noqa: E402

from scripts import iecc_commercial_overlay  # noqa: E402

IECC_COMMERCIAL = (*iecc_commercial_overlay.INPUTS, *iecc_commercial_overlay.SCRIPTS)
RELEASES['1.3.0'] = {
    'overlays': ('reconciliation', 'construction_only', 'iecc_commercial'),
    'inputs': (*atlas_release.INPUTS, *RECONCILIATION, *CONSTRUCTION_ONLY, *IECC_COMMERCIAL, 'scripts/atlas_minor_release.py'),
    'decisions': ('docs/adr/0036-suite-based-release-storage.md', 'docs/adr/0037-doe-reference-reconciliation.md',
                  'docs/adr/0039-construction-only-programs.md', 'docs/adr/0040-iecc-commercial-family.md'),
    'readme': '''# Energy Archetype Atlas release 1.3.0 (commercial, delta)

A delta on release 1.0.0 (ADR 0036): this folder holds only the files that differ
from `data/atlas-releases/v1.0.0`, and `manifest.json` names that base with its
manifest's SHA-256 and lists deleted files. Resolve it by reading the base and
replacing or removing the files listed here (`scripts.atlas_minor_release.files`).

It holds everything releases 1.1.0 and 1.2.0 changed (the DOE reference
reconciliation, ADR 0037, and the construction-only programs, ADR 0039), and adds
the IECC commercial prototype family (docs/adr/0040-iecc-commercial-family.md):
16 building types in the IECC 2006, 2009, 2012, 2015, 2018 and 2021 editions,
96 folders under `commercial/iecc-<year>/`, extracted from the pinned PNNL IDFs
into data/program-inputs/iecc-commercial-<year>.json.
- Programs per standards space type, area-weighted over the IDF zones; absence of an
  object in the complete model is a source zero. A load that differs by location
  keeps the most common value and lists the others in `value_by_climate`.
- One construction set per folder with 19 contexts, one per climate zone (zones 7
  and 8 keyed `7-a` and `8-a`). The IDF design-flow infiltration is the source
  method. The unified representation is deferred.
- Building services and hot-water draws with their zone gains. HVAC is deferred.

Verify with `python -m scripts.atlas_minor_release --release 1.3.0 --verify`; rebuild
and compare with `--check`. Upstream notices are in `notices/` of either folder;
original Atlas work remains unlicensed (see `LICENSE`).
'''}
BUILDER = 'scripts/atlas_minor_release.py'
BLOCK = re.compile(r'# >>> release (\d+\.\d+\.\d+)\n.*?# <<< release \1\n\n\n', re.S)


def pinned_bytes(path, release):
    """A release input as that release pinned it: this builder without the blocks of later releases."""
    data = (ROOT/path).read_bytes()
    if path != BUILDER:
        return data
    later = lambda m: tuple(map(int, m[1].split('.'))) > tuple(map(int, release.split('.')))
    return BLOCK.sub(lambda m: '' if later(m) else m[0], data.decode('utf-8')).encode('utf-8')


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
    stale = sorted(path for path, digest in listed['input_sha256'].items() if atlas_release.sha(pinned_bytes(path, release)) != digest)
    if stale:
        raise ValueError(f'Release inputs changed since it was written; rerun python -m scripts.atlas_minor_release '
                         f'--release {release}: '+', '.join(stale))
    return listed


_overlaid_before_1_3_0 = overlaid


@contextlib.contextmanager
def overlaid(overlays):
    """The earlier overlays, then the IECC commercial family (ADR 0040): its programs and services join
    the overlaid sources, its construction sets the construction sources, and the construction export
    hook serves its documents."""
    if 'iecc_commercial' not in overlays:
        with _overlaid_before_1_3_0(overlays):
            yield
        return
    iecc = iecc_commercial_overlay.constructions()
    with _overlaid_before_1_3_0(tuple(o for o in overlays if o != 'iecc_commercial')):
        iecc_commercial_overlay.apply(atlas_programs.load_sources(), atlas_systems.load_sources(), iecc.inputs)
        iecc.add_to(atlas_constructions.load_sources())
        inner = construction_foundation_release.export_pair

        def pair(context_id, *, release=None):
            return iecc.pair(context_id) if context_id in iecc.where else inner(context_id, release=release)
        construction_foundation_release.export_pair = pair
        try:
            yield
        finally:
            construction_foundation_release.export_pair = inner


_assemble_unpinned = assemble


def assemble(release):
    """The delta files, the builder's digest taken as verify reads it: without the blocks of later releases,
    so --check of an earlier release still reproduces its manifest after later blocks are added."""
    out = _assemble_unpinned(release)
    manifest = json.loads(out['manifest.json'])
    if BUILDER in manifest['input_sha256']:
        manifest['input_sha256'][BUILDER] = atlas_release.sha(pinned_bytes(BUILDER, release))
    return {**out, 'manifest.json': suite_bytes(manifest)}
# <<< release 1.3.0


# >>> release 1.4.0
# Release 1.4.0 adds the residential tree (ADR 0038, 0041, 0042) beside everything of
# release 1.3.0: the `residential` overlay merges the files of scripts.residential_release
# into the assembled release. Added as a tagged block for the reason the 1.3.0 block gives.
from scripts.atlas_format import merge  # noqa: E402


def residential_inputs():
    from scripts import residential_release
    return residential_release.inputs()


RELEASES['1.4.0'] = {
    'overlays': ('reconciliation', 'construction_only', 'iecc_commercial', 'residential'),
    'inputs': (*atlas_release.INPUTS, *RECONCILIATION, *CONSTRUCTION_ONLY, *IECC_COMMERCIAL, *residential_inputs(),
               'scripts/atlas_minor_release.py'),
    'decisions': ('docs/adr/0036-suite-based-release-storage.md', 'docs/adr/0037-doe-reference-reconciliation.md',
                  'docs/adr/0039-construction-only-programs.md', 'docs/adr/0040-iecc-commercial-family.md',
                  'docs/adr/0038-residential-release-storage.md', 'docs/adr/0041-iecc-residential-family.md',
                  'docs/adr/0042-manufactured-housing-family.md'),
    'scope': 'commercial and residential',
    'readme': '''# Energy Archetype Atlas release 1.4.0 (commercial and residential, delta)

A delta on release 1.0.0 (ADR 0036): this folder holds only the files that differ
from `data/atlas-releases/v1.0.0`, and `manifest.json` names that base with its
manifest's SHA-256 and lists deleted files. Resolve it by reading the base and
replacing or removing the files listed here (`scripts.atlas_minor_release.files`).

Commercial: everything of release 1.3.0 (the DOE reference reconciliation, ADR 0037,
the programs of the construction-only folders, ADR 0039, and the IECC commercial
family, ADR 0040), unchanged.

Residential (new, docs/adr/0038-residential-release-storage.md):
- `residential/resstock-sdr/<building-type>/`: the 41 ResStock SDR fixture dwellings,
  one program per dwelling with its fillings, its annual series in
  `schedules/<program-id>.json` and one construction set of one context. Values are
  those of the frozen definition, resolution and construction releases.
- `residential/iecc-<edition>/{single-family,multifamily}/`: the IECC residential
  prototypes, editions 2006 to 2024 (docs/adr/0041-iecc-residential-family.md).
  Programs per type and appliance fuel, whose entries carry `applies_with` where they
  hold only for some climate codes, foundations or heating systems; one construction
  set per type with a context per climate code and foundation.
- `residential/{hud-code,doe-final-rule}/{single-section,multi-section}/`: the
  manufactured-housing prototypes (docs/adr/0042-manufactured-housing-family.md).
- Loads keep the source basis, per dwelling unit where the source gives one. Systems
  are not stored for residential families (ADR 0038 section 7).

Exports: dwelling programs as Program JSON 5.3.0 (`python -m scripts.atlas_exports
--release 1.4.0 --program ID`), ResStock construction sets as constructions 4.2.0 /
3.1.0, and the IDF-derived sets as source model constructions 1.0.0.

Verify with `python -m scripts.atlas_minor_release --release 1.4.0 --verify`; rebuild
and compare with `--check`. Upstream notices are in `notices/` of either folder;
original Atlas work remains unlicensed (see `LICENSE`).
'''}


# What release 1.4.0 still leaves out. The base list named residential storage and the consumer exports,
# which releases 1.1.0 and 1.4.0 now hold.
DEFERRED_1_4_0 = ('generator recipes in program files',
                  'systems, water heaters and the unified construction representation of the IECC commercial '
                  'family (ADR 0040)',
                  'systems and water heaters of the residential families (ADR 0038 section 7)')


def assemble(release):
    """The delta files, manifest included, against the written base; residential files join the commercial ones.
    Input digests are taken as verify reads them (the builder without the blocks of later releases)."""
    spec = RELEASES[release]
    with overlaid(spec['overlays']):
        full = atlas_release.assemble()
    full.pop('manifest.json')
    residential_counts = {}
    if 'residential' in spec['overlays']:
        from scripts import residential_release, residential_storage
        full = merge(full, residential_release.files())
        residential_counts = residential_storage.counts(full)
    full['README.md'] = spec['readme'].encode('utf-8')
    base = base_files()
    changed = {path: data for path, data in full.items() if base.get(path) != data}
    deleted = sorted(set(base) - set(full) - {'manifest.json'})
    resolved = atlas_release.manifest({p: d for p, d in full.items() if not p.startswith('residential/')})
    resolved['counts'].update(residential_counts)
    if 'residential' in spec['overlays']:
        resolved['deferred'] = list(DEFERRED_1_4_0)
    manifest = {
        'schema_version': '1.0.0', 'kind': 'atlas_release', 'release': release, 'status': 'candidate',
        'scope': spec.get('scope', 'commercial'),
        'base_release': {'release': '1.0.0', 'path': BASE.relative_to(ROOT).as_posix(),
                         'manifest_sha256': atlas_release.sha(base['manifest.json'])},
        'decision': list(spec['decisions']), 'deferred': resolved['deferred'],
        'generated_by': f'python -m scripts.atlas_minor_release --release {release}',
        'input_sha256': {path: atlas_release.sha(pinned_bytes(path, release)) for path in spec['inputs']},
        'counts': resolved['counts'],
        'files': {path: {'sha256': atlas_release.sha(data), 'bytes': len(data)} for path, data in sorted(changed.items())},
        'deleted': deleted}
    return {**changed, 'manifest.json': suite_bytes(manifest)}


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
    print(f'Atlas release {args.release} ({listed.get("scope", "commercial")}, delta on 1.0.0): {len(listed["files"])} files, '
          f'{len(listed["deleted"])} deleted; resolved: '+', '.join(f'{v} {k}' for k, v in listed['counts'].items()))
# <<< release 1.4.0


if __name__ == '__main__':
    main()
