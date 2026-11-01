"""Write, check and read the delta releases on the 2.0.0 snapshot (ADR 0036 section 2, ADR 0046, ADR 0051).

python -m scripts.atlas_delta --write  [--release 2.2.0]   # write the delta folder from its inputs
python -m scripts.atlas_delta --check  [--release 2.2.0]   # rebuild the delta and fail unless the folder already equals it
python -m scripts.atlas_delta --verify [--release 2.2.0]   # every file against the manifest, and the base manifest unchanged

A delta holds only the files that differ from its base, with `manifest.json` naming the base and
that base manifest's SHA-256, and listing the base files it removes (`removed`). A reader resolves
the chain (`files()`): the 2.0.0 snapshot (`scripts.atlas_snapshot`), then each delta laid over the
one before. The default release is the newest.

Release 2.1.0 (CHANGELOG 2026-10-29; ADR 0046 section 12), a delta on 2.0.0:
- `LICENSE`: the root open-licence text (ADR 0048 item 4), in place of the unlicensed text 2.0.0 packaged;
- `README.md`: the delta's own description;
- `generator.json` of the eight apartment folders: every `apartment_unit` recipe is the generator 3.0.0
  ResStock unit recipe of the same program ID (ADR 0047), in place of the 2.x prototype recipe.
  Their input, the packaged recipes of generator 3.0.0, left the tree with ADR 0051 (stage P3), so
  these files are kept as written at commit 77ebad7e and verified by checksum; `--check` rebuilds only
  the licence, the README and the manifest around them.

Release 2.2.0 (ADR 0051), a delta on 2.1.0:
- `<family>/<template>/<building type>/generation.json` of the 90 generated folders: the folder's program
  `generation` blocks (method and, per view, the parameters the record cannot give), its services'
  blocks and its building configurations. A program reads with its block as `generation`;
- `definition-map.json`: each definition program ID generator 3.0.0 took, with its release program and
  view (`values`), and each definition service ID with its release service;
- `removed`: every folder's `generator.json` (83 paths; the eight 2.1.0 rewrote are the same paths).
  The blocks were derived from the generator 3.0.0 packaged copies by `scripts.derive_generation_blocks`
  at the commit ADR 0051 section 7 names, where the equivalence gate ran; `scripts.build_reference_recipes`
  and `scripts.build_apartment_units` rewrite the DOE Ref and apartment blocks from their sources. The
  90.1 commercial blocks and the dwellings' inputs have no source builder, as their packaged recipes had
  none, and are kept as written. `--check` rebuilds the licence, the README and the manifest around the
  files, requires every block to assemble (`atlas_schedules.programmes`), and `scripts.release_editor
  --check` requires every program to keep its ID with its block.
No program, schedule, service or construction value changes in either delta, and no ID moves.
"""
import argparse
import hashlib
import json
from pathlib import Path

from atlas_schedules.release import Release
from scripts import atlas_snapshot
from scripts.atlas_format import canonical
from scripts.common import ROOT

BASE = atlas_snapshot.RELEASE
CHAIN = ('2.1.0', '2.2.0')              # the deltas, each on the one before
RELEASE = CHAIN[-1]
RELEASES = ROOT/'data/atlas-releases'
PACKAGE = 'atlas-schedules'
STATUS = 'released'
GENERATION_SCHEMA = '1.0.0'
DECISIONS = {
    '2.1.0': ('docs/adr/0046-release-2-0-0.md', 'docs/adr/0047-resstock-apartment-units-and-source-magnitudes.md',
              'docs/adr/0048-open-licences.md', 'docs/adr/0049-atlas-schedules-packaging.md'),
    '2.2.0': ('docs/adr/0051-generation-parameters-in-the-release.md', 'docs/adr/0046-release-2-0-0.md',
              'docs/adr/0047-resstock-apartment-units-and-source-magnitudes.md', 'docs/adr/0049-atlas-schedules-packaging.md'),
}
# The generator each delta was written for: 2.1.0 carries generator 3.0.0's recipes; 2.2.0 is read by 4.0.0 on.
GENERATOR = {
    '2.1.0': {'version': '3.0.0', 'package': PACKAGE, 'wheel': 'atlas_schedules-3.0.0-py3-none-any.whl',
              'release_tag': 'atlas-schedules-v3.0.0', 'request_schema_version': '3.0.0',
              'recipes_sha256': 'bda69907c8782cad1fd6d155da34aa9682764fdd37e39d0c4796815b36b42c49'},
    '2.2.0': {'version': '4.0.0', 'package': PACKAGE, 'wheel': 'atlas_schedules-4.0.0-py3-none-any.whl',
              'release_tag': 'atlas-schedules-v4.0.0', 'request_schema_version': '4.0.0', 'reads': 'release 2.x, generation 1.x'},
}
README = {'2.1.0': """# Energy Archetype Atlas release 2.1.0 (commercial and residential, delta on 2.0.0)

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
""", '2.2.0': """# Energy Archetype Atlas release 2.2.0 (generation parameters, delta on 2.1.0)

A delta release (ADR 0036 section 2, ADR 0051): this folder holds only its own files, and a
reader resolves every other path in `../v2.1.0/` and then `../v2.0.0/`, whose manifest hashes
the chain of `manifest.json` files records. It publishes the stochastic schedule generator's
parameters with the programs and removes each folder's `generator.json`; no program,
schedule, service or construction value changes, and no ID moves (the program ID rule leaves
`generation` out).

- `<family>/<template>/<building type>/generation.json`: the folder's program `generation`
  blocks (method and, per view, the parameters the record cannot give), its services'
  blocks and its building configurations. A program reads with its block as `generation`.
- `definition-map.json`: each definition program ID generator 3.0.0 took, with its release
  program and view (`values`), and each definition service ID with its release service.

The generator (`atlas-schedules` 4.0.0 on, ADR 0051) assembles its recipes from this release;
Program JSON 5.4.0 exports name `atlas-release-2.2.0`. Resolve the chain with
`python -m scripts.atlas_delta` (`scripts.atlas_delta.files('2.2.0')`); verify with `--verify`,
rebuild and compare with `--check`. Upstream notices are in 2.0.0's `notices/`; original Atlas
data is CC BY 4.0 (see `LICENSE`).
"""}


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


def folder_of(release):
    return RELEASES/f'v{release}'


def base_of(release):
    if release not in CHAIN:
        raise ValueError(f'Release {release} is not a delta in the tree; the deltas are {CHAIN}')
    index = CHAIN.index(release)
    return BASE if index == 0 else CHAIN[index - 1]


def kept(release, suffix):
    """{path: bytes} of the delta's files ending in `suffix`, as they sit in the folder (kept as written)."""
    folder = folder_of(release)
    if not folder.is_dir():
        raise SystemExit(f'Release {release} has no folder to keep its files from: {folder}')
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob('*'))
            if p.is_file() and p.name.endswith(suffix)}


def build(release):
    """{path: bytes} of the delta's files, manifest excluded."""
    files = {'LICENSE': (ROOT/'LICENSE').read_bytes(), 'README.md': README[release].encode('utf-8')}
    if release == '2.1.0':
        files.update(kept(release, 'generator.json'))
    else:
        files.update(kept(release, 'generation.json'))
        files.update(kept(release, 'definition-map.json'))
    return files


def generation_counts(release, delta):
    """Counts of the generation blocks a delta carries, read through atlas_schedules over the base (before the manifest exists)."""
    from atlas_schedules.release import TreeStore
    docs = {p.rsplit('/', 1)[0]: json.loads(d) for p, d in delta.items() if p.endswith('/generation.json')}
    reader = Release(TreeStore(folder_of(base_of(release))), generation=docs)
    methods, services, configurations, views = {}, 0, 0, 0
    for folder in reader.generation_folders():
        doc = reader.generation(folder)
        for block in doc.get('programs', {}).values():
            methods[block['method']] = methods.get(block['method'], 0) + 1
            views += len(block['views'])
        services += len(doc.get('services', {}))
        configurations += len(doc.get('configurations', {}))
    mapped = json.loads(delta['definition-map.json'])
    return {'generation_folders': len(reader.generation_folders()), 'programs_with_generation': sum(methods.values()),
            'program_views': views, 'methods': dict(sorted(methods.items())), 'services_with_generation': services,
            'configurations': configurations, 'definition_programs': len(mapped['programs']),
            'definition_services': len(mapped['services']), 'retired_definition_programs': len(mapped.get('retired', {}))}


def manifest(release, delta, base_manifest):
    base = base_of(release)
    base_folder = folder_of(base)
    out = {
        'kind': 'atlas_release', 'schema_version': base_manifest['schema_version'], 'release': release,
        'scope': base_manifest['scope'], 'status': STATUS,
        'base_release': {'release': base, 'path': base_folder.relative_to(ROOT).as_posix(),
                         'manifest_sha256': sha((base_folder/'manifest.json').read_bytes())},
        'generated_by': f'python -m scripts.atlas_delta --write --release {release}',
        'decision': list(DECISIONS[release]),
        'generator': dict(GENERATOR[release]),
        'input_sha256': {'LICENSE': sha((ROOT/'LICENSE').read_bytes()),
                         f'data/atlas-releases/v{base}/manifest.json': sha((base_folder/'manifest.json').read_bytes())},
        'counts': dict(base_manifest['counts']),
        'deferred': [d for d in base_manifest['deferred'] if not d.startswith('ADR 0046 phase 2')],
        'files': {p: {'sha256': sha(d), 'bytes': len(d)} for p, d in sorted(delta.items())},
        'removed': [],
    }
    if release == '2.1.0':
        # Verify-only (ADR 0046 section 7's rule for releases whose inputs left): no input digests beyond the base.
        out['edited_by'] = ['ADR 0051 (2026-10-29): manifest only; the packaged recipes this delta pinned left the tree '
                            'with generator 4.0.0, so the generator.json files are verified by checksum']
    else:
        out['input_sha256']['scripts/atlas_delta.py'] = sha(Path(__file__).read_bytes())
        resolved = Release(base_folder)
        out['removed'] = sorted(p for p in resolved.paths if p.endswith('/generator.json'))
        out['generation'] = {'schema_version': GENERATION_SCHEMA}
        counts = out['counts']
        counts.pop('programs_with_recipes', None)
        counts.pop('programs_without_recipes', None)
        out['counts'] = {**counts, 'generation': generation_counts(release, delta)}
        out['deferred'] = [d.replace('generator recipes', 'generation blocks') for d in out['deferred']]
    return out


def manifest_bytes(listed):
    return (json.dumps(listed, indent=2, sort_keys=True, ensure_ascii=False)+'\n').encode('utf-8')


def verify(release=RELEASE):
    """The manifest, after checking every file against it, no other file present, and the base manifest unchanged."""
    folder = folder_of(release)
    base = base_of(release)
    listed = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    recorded = listed.get('base_release') or {}
    if listed.get('kind') != 'atlas_release' or recorded.get('release') != base:
        raise ValueError(f'Not a delta atlas release on {base}: {folder}')
    if sha((ROOT/recorded['path']/'manifest.json').read_bytes()) != recorded['manifest_sha256']:
        raise ValueError(f'Base release {base} manifest differs from the one the delta was written on')
    for path, entry in listed['files'].items():
        p = folder/path
        data = p.read_bytes() if p.is_file() else None
        if data is None or len(data) != entry['bytes'] or sha(data) != entry['sha256']:
            raise ValueError('Release file missing or differs: '+path)
    extra = sorted({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()} - set(listed['files']) - {'manifest.json'})
    if extra:
        raise ValueError('Release files not in the manifest: '+', '.join(extra[:5]))
    return listed


def files(release=RELEASE):
    """Every file of a release in the tree, resolved: the base's files with each delta laid over, removals applied."""
    if release == BASE:
        return atlas_snapshot.files()
    listed = verify(release)
    resolved = files(base_of(release))
    for path in listed['removed']:
        del resolved[path]
    folder = folder_of(release)
    for path in listed['files']:
        resolved[path] = (folder/path).read_bytes()
    return resolved


def assembles(release):
    """Every block of a release assembles in every view, and every service and configuration; the view count."""
    from atlas_schedules import programmes
    reader = Release(folder_of(release))
    count = 0
    for folder in reader.generation_folders():
        doc = reader.generation(folder)
        for rid, block in doc.get('programs', {}).items():
            for view in block['views']:
                programmes.assemble(reader, rid, view)
                count += 1
        for sid in doc.get('services', {}):
            programmes.assemble_service(reader, sid)
        for cid in doc.get('configurations', {}):
            programmes.assemble_configuration(reader, cid)
    return count


def layered_bytes(value, depth=3):
    """Compact storage (ADR 0046 P9): one record per line down to `depth` levels."""
    from scripts.iecc_commercial_values import layered
    return (layered(value, depth)+"\n").encode('utf-8')


def write(release):
    """Write the delta folder from its inputs and verify it; the manifest is rewritten last."""
    target = folder_of(release)
    base = base_of(release)
    base_manifest = atlas_snapshot.verify() if base == BASE else verify(base)
    delta = build(release)
    delta['manifest.json'] = manifest_bytes(manifest(release, delta, base_manifest))
    for path in sorted(p for p in target.rglob('*') if p.is_file()) if target.is_dir() else []:
        if path.relative_to(target).as_posix() not in delta:
            path.unlink()
    for path, data in sorted(delta.items()):
        out = target/path
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.is_file() or out.read_bytes() != data:
            out.write_bytes(data)
    verify(release)
    return delta


def write_generation(docs, release=RELEASE):
    """Write {release folder: generation.json document} into the delta and rewrite its manifest
    (scripts.build_reference_recipes and scripts.build_apartment_units)."""
    for name, doc in docs.items():
        out = folder_of(release)/name/'generation.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(layered_bytes({**doc, 'schema_version': GENERATION_SCHEMA}))
    write(release)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', action='store_true')
    group.add_argument('--check', action='store_true')
    group.add_argument('--verify', action='store_true')
    parser.add_argument('--release', choices=CHAIN, default=RELEASE)
    args = parser.parse_args()
    release = args.release
    target = folder_of(release)
    if args.verify:
        listed = verify(release)
        print(f'Atlas release {release} (delta on {base_of(release)}): {len(listed["files"])} files differ, '
              f'{len(listed["removed"])} removed, generator {listed["generator"]["version"]}')
        return
    base = base_of(release)
    base_manifest = atlas_snapshot.verify() if base == BASE else verify(base)
    delta = build(release)
    delta['manifest.json'] = manifest_bytes(manifest(release, delta, base_manifest))
    if args.check:
        stale = [p for p, d in delta.items() if not (target/p).is_file() or (target/p).read_bytes() != d]
        extra = sorted({p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()} - set(delta)) if target.is_dir() else ['(missing)']
        if stale or extra:
            raise SystemExit(f'Release {release} differs from its inputs: {len(stale)} stale, {len(extra)} extra, '
                             f'e.g. {(stale + extra)[:3]}; run python -m scripts.atlas_delta --write --release {release}')
        views = assembles(release) if release != '2.1.0' else 0
        print(f'Release {release} reproduces from its inputs: {len(delta) - 1} files and the manifest'
              + (f'; {views} program views assemble' if views else ''))
        return
    delta = write(release)
    print(f'Release {release} written: {len(delta) - 1} files and the manifest')


# >>> release 2.3.0
# Release 2.2.0 pins this file by SHA-256 (`input_sha256`). Later releases are therefore added as tagged
# blocks like this one, before the main guard, as ADR 0040 (agent decision 17) did for the minor-release
# builder: a manifest pins the file without the blocks of later releases (`pinned_writer`), which restores
# the exact bytes that wrote it. Nothing above this block changes. This block (ADR 0055, ADR 0056):
# - validates every delta file and the manifest against the release-record schemas (scripts.release_schemas)
#   whenever a delta is built, so `--check` and `--write` fail on a file that breaks its schema;
# - counts generation blocks over the resolved release (base and delta), as a delta from 2.3.0 carries only
#   its new and changed generation.json files;
# - states the generation coverage of releases after 2.2.0 by folder class (scripts.generation_coverage), in
#   place of 2.2.0's entry, which named "plenum" programs as a class and an empty DOE Ref class.
import re  # noqa: E402

from scripts import generation_coverage, release_schemas  # noqa: E402

WRITER = 'scripts/atlas_delta.py'
BLOCK = re.compile(r'# >>> release (\d+\.\d+\.\d+)\n.*?# <<< release \1\n\n\n', re.S)
GENERATION_BY_CLASS_FROM = (2, 3, 0)


def _version(release):
    return tuple(int(part) for part in release.split('.'))


def pinned_writer(release):
    """This file as `release` pinned it: without the blocks of later releases."""
    text = (ROOT/WRITER).read_text(encoding='utf-8')
    return BLOCK.sub(lambda m: '' if _version(m[1]) > _version(release) else m[0], text).encode('utf-8')


def generation_reader(release, delta):
    """The release with its generation.json files resolved over the base: the base's, then the delta's."""
    from atlas_schedules.release import TreeStore
    base = Release(TreeStore(folder_of(base_of(release))))
    docs = {f: base.generation(f) for f in base.generation_folders()}
    docs.update({p.rsplit('/', 1)[0]: json.loads(d) for p, d in delta.items() if p.endswith('/generation.json')})
    return Release(base.store, generation=docs)


_build_before_2_3_0 = build
_manifest_before_2_3_0 = manifest


def generation_counts(release, delta):
    """Counts of the generation blocks of the resolved release (base and delta; release 2.2.0's base has none)."""
    reader = generation_reader(release, delta)
    methods, services, configurations, views = {}, 0, 0, 0
    for folder in reader.generation_folders():
        doc = reader.generation(folder)
        for block in doc.get('programs', {}).values():
            methods[block['method']] = methods.get(block['method'], 0) + 1
            views += len(block['views'])
        services += len(doc.get('services', {}))
        configurations += len(doc.get('configurations', {}))
    mapped = json.loads(delta['definition-map.json']) if 'definition-map.json' in delta else reader.json('definition-map.json')
    return {'generation_folders': len(reader.generation_folders()), 'programs_with_generation': sum(methods.values()),
            'program_views': views, 'methods': dict(sorted(methods.items())), 'services_with_generation': services,
            'configurations': configurations, 'definition_programs': len(mapped['programs']),
            'definition_services': len(mapped['services']), 'retired_definition_programs': len(mapped.get('retired', {}))}


def manifest(release, delta, base_manifest):
    """The manifest as before, with the writer pinned as this release wrote it and, after 2.2.0, the generation
    coverage by folder class; valid against the manifest schema."""
    out = _manifest_before_2_3_0(release, delta, base_manifest)
    if WRITER in out['input_sha256']:
        out['input_sha256'][WRITER] = sha(pinned_writer(release))
    if _version(release) < SPLIT_LICENCE_FROM:
        out['input_sha256']['LICENSE'] = sha(delta['LICENSE'])
    else:
        edited = edits_2_3_0()
        out['input_sha256'].update({path: sha((ROOT/path).read_bytes()) for path in EDIT_INPUTS})
        out['input_sha256']['LICENSE-DATA'] = sha(delta['LICENSE-DATA'])
        out['removed'] = list(edited.removed)
        kinds = {'programs': sum('.construction-' not in i for i in edited.ids),
                 'construction_sets': sum('.construction-' in i for i in edited.ids)}
        out['counts']['moved_ids'] = {**kinds, 'id_map': ID_MAP}
    if _version(release) >= GENERATION_BY_CLASS_FROM:
        kept = [d for d in out['deferred'] if not d.startswith('generation blocks')]
        out['deferred'] = generation_coverage.deferred(generation_reader(release, delta)) + kept
    release_schemas.check({'manifest.json': out}, f'release {release}')
    return out


# Release 2.3.0 (ADR 0059), a delta on 2.2.0:
# - `LICENSE` is the MIT text alone and `LICENSE-DATA` the CC BY 4.0 legal code (issue #44); releases 2.1.0 and
#   2.2.0 keep the one two-part `LICENSE` they packaged, verified by checksum as their licence input;
# - the record edits of ADR 0053 (`scripts.atlas_edits.edit` over the resolved 2.2.0): the files they change or
#   add, the paths they remove (`removed`, the old names of moved IDs) and `id-map-2.3.0.json`, the map from 2.2.0
#   to 2.3.0 IDs (1,550 programs, 12 construction sets);
# - `generation.json` of the 84 IECC commercial and 15 detailed office folders (ADR 0055), derived by
#   `scripts.build_zone_recipes` over the edited release, as their IDs are 2.3.0's.
import functools  # noqa: E402

CHAIN = ('2.1.0', '2.2.0', '2.3.0')
RELEASE = CHAIN[-1]
SPLIT_LICENCE_FROM = (2, 3, 0)
ID_MAP = 'id-map-2.3.0.json'
EDIT_INPUTS = ('scripts/atlas_edits.py', 'data/program-inputs/pnnl-point-load-exceptions-v1.json',
               'data/program-inputs/distinguishing-names-v1.json')
DECISIONS['2.3.0'] = ('docs/adr/0059-release-2-3-0.md', 'docs/adr/0053-release-2-3-0-data-corrections.md',
                      'docs/adr/0054-release-2-3-0-export-contracts.md',
                      'docs/adr/0055-generation-for-iecc-and-detailed-offices.md',
                      'docs/adr/0056-release-record-schemas-and-versioning.md', 'docs/adr/0048-open-licences.md')
GENERATOR['2.3.0'] = {'version': '4.1.0', 'package': PACKAGE, 'wheel': 'atlas_schedules-4.1.0-py3-none-any.whl',
                      'release_tag': 'atlas-schedules-v4.1.0', 'request_schema_version': '4.0.0',
                      'reads': 'release 2.x, generation 1.x'}
README['2.3.0'] = """# Energy Archetype Atlas release 2.3.0 (data corrections and generation coverage, delta on 2.2.0)

A delta release (ADR 0036 section 2, ADR 0059): this folder holds only its own files, and a
reader resolves every other path in `../v2.2.0/`, `../v2.1.0/` and then `../v2.0.0/`, whose
manifest hashes the chain of `manifest.json` files records. `removed` lists the 2.2.0 paths
this release drops: the old names of the records whose IDs move.

- Record corrections (ADR 0053): the unified `InternalMass` of eight DOE Ref building-scope
  construction sets counts their whole additional-mass inventory; the 90.1 small-hotel
  elevator takes the PNNL prototype value, and its support mixes follow; every unknown
  commercial load carries its reason, and the ADR 0016 accepted absence is a stored filling;
  same-named records take the name of their source distinction. Program and set IDs follow
  their rules: 1,550 programs and 12 construction sets have new IDs, and every citing file
  follows, `generation.json` and `definition-map.json` included.
- `id-map-2.3.0.json`: every 2.2.0 ID that moves, mapped to its 2.3.0 ID (`ids`). The
  2.0.0 `id-map.json` keeps the map into 2.0.0.
- `<family>/<template>/<building type>/generation.json` of the IECC commercial and detailed
  office folders (ADR 0055), new, and of the 2.2.0 folders whose programs moved.
- `LICENSE` is the MIT License for code and `LICENSE-DATA` the CC BY 4.0 legal code for data
  and documentation; attribute as "Archetype Atlas, Energy-Atlas" with the release number.

Exports of this release follow new contracts (ADR 0054): Program JSON 6.0.0, detailed
constructions 5.0.0, unified constructions 4.0.0, source-model constructions 2.0.0 and
building services 1.0.1, naming `atlas-release-2.3.0`. The generator (`atlas-schedules`
4.1.0) reads it. Resolve the chain with `python -m scripts.atlas_delta`
(`scripts.atlas_delta.files('2.3.0')`); verify with `--verify`, rebuild and compare with
`--check`. Upstream notices are in 2.0.0's `notices/`.
"""


@functools.lru_cache(maxsize=1)
def edits_2_3_0():
    """The ADR 0053 edits over the resolved release 2.2.0 (scripts.atlas_edits)."""
    from scripts import atlas_edits
    return atlas_edits.edit(files('2.2.0'))


def zone_generation(resolved):
    """{path: bytes} of the IECC commercial and detailed office generation.json over a resolved release (ADR 0055)."""
    from atlas_schedules.release import TreeStore
    from scripts import build_zone_recipes

    class Store(TreeStore):
        def __init__(self):
            self.folder, self.base, self.removed = None, None, set()
            self.manifest = {'release': RELEASE, 'generation': {'schema_version': GENERATION_SCHEMA}}
            self.manifest_sha256, self.version = None, RELEASE

        @property
        def paths(self):
            return {p: p for p in resolved}

        def json(self, path):
            return json.loads(resolved[path])

        def describe(self):
            return f'release {RELEASE} as built'

    reader = Release(Store())
    docs = build_zone_recipes.build(reader)
    build_zone_recipes.gate(reader, docs)
    return {f'{folder}/generation.json': build_zone_recipes.encode(doc) for folder, doc in docs.items()}


def _build_2_3_0():
    from scripts import atlas_edits
    edited = edits_2_3_0()
    out = {'LICENSE': (ROOT/'LICENSE').read_bytes(), 'LICENSE-DATA': (ROOT/'LICENSE-DATA').read_bytes(),
           'README.md': README['2.3.0'].encode('utf-8')}
    out.update(edited.files)
    out[ID_MAP] = atlas_edits.id_map_bytes(edited.ids)
    generation = zone_generation(edited.resolved(files('2.2.0')))
    clash = sorted(set(generation) & set(out))
    if clash:
        raise ValueError(f'Zone generation.json over files the edits write: {clash[:3]}')
    out.update(generation)
    return out


def build(release):
    """The delta's files, each valid against its release-record schema; before 2.3.0 the licence each release
    packaged is kept as written (ADR 0059), since the root LICENSE split."""
    if _version(release) >= SPLIT_LICENCE_FROM:
        out = _build_2_3_0()
    else:
        out = _build_before_2_3_0(release)
        out['LICENSE'] = (folder_of(release)/'LICENSE').read_bytes()
    release_schemas.check(out, f'release {release}')
    return out


_verify_before_2_3_0 = verify
_files_before_2_3_0 = files


def verify(release=None):
    return _verify_before_2_3_0(release or RELEASE)


def files(release=None):
    return _files_before_2_3_0(release or RELEASE)
# <<< release 2.3.0


if __name__ == '__main__':
    main()
