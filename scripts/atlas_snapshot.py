"""Write and verify release 2.0.0, a full snapshot that ends the 1.x delta chain (ADR 0046, phase 1).

python -m scripts.atlas_snapshot            # write data/atlas-releases/v2.0.0
python -m scripts.atlas_snapshot --verify   # every file against the manifest, and the inputs
python -m scripts.atlas_snapshot --check    # rebuild and compare byte for byte

Release 2.0.0 is the resolved release 1.6.0 (scripts.atlas_minor_release.files), stored whole:
- no base release: a reader opens this folder alone, and later minors are deltas on it;
- every indented JSON file re-encoded one record per line down to three levels
  (scripts.iecc_commercial_values.layered); line tables stay as they are;
- the generator recipes of atlas_schedules/data/recipes beside the programs they belong to,
  one `generator.json` per folder keyed by release program ID with the source and reviewed
  recipe, for the programs whose definition values are unchanged since release 1.0.0 (the
  90.1 templates). The DOE Ref programs changed in release 1.1.0 and the later families have
  no recipes; the manifest lists both as deferred.
Values do not change: every resolved 1.6.0 file decodes to the same JSON in 2.0.0.

The release reads no frozen folder (ADR 0046 phase 2): `exporter-inputs.json` holds what the
exporters took from them (the capped-delivery services and programs under release IDs, and the
source programs with neither setpoint schedule), and readers verify the files alone; only
`--verify` and `--check` compare the inputs.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from scripts import atlas_minor_release, atlas_release
from scripts.atlas_exports import EXPORTER_INPUTS, Release
from scripts.atlas_format import suite_bytes
from scripts.common import ROOT, load_json
from scripts.iecc_commercial_values import layered

RELEASE, SOURCE = '2.0.0', '1.6.0'
TARGET = ROOT/f'data/atlas-releases/v{RELEASE}'
RECIPES = ROOT/'atlas_schedules/data/recipes'
DEFINITIONS = ROOT/'data/definition-releases/v0.1.1/programs.json'
CURRENT = ('90.1-2007', '90.1-2013', '90.1-2019')  # templates whose definition values are those of release 1.0.0
LEGACY = ROOT/'data/releases/v0.2.0/programs.json'
INPUTS = ('scripts/atlas_snapshot.py', f'data/atlas-releases/v{SOURCE}/manifest.json', 'data/definition-releases/v0.1.1/programs.json',
          'data/releases/v0.2.0/programs.json')
DEFERRED = ('generator recipes of the DOE Ref programs (values changed in release 1.1.0) and of the construction-only, '
            'IECC, plenum and residential programs (none exist)',
            'systems and water heaters of the IECC commercial family (ADR 0040)',
            'systems and water heaters of the residential families (ADR 0038 section 7)',
            'ADR 0046 phase 2: rewritten writers, selection decisions in the evidence tree, frozen folders retired')
README = '''# Energy Archetype Atlas release 2.0.0 (commercial and residential, full snapshot)

A full snapshot (ADR 0036 section 2, ADR 0046): this folder holds every file of the
release and names no base. It is release 1.6.0 resolved (the DOE reference
reconciliation, the construction-only programs, the IECC commercial family, the
residential tree, the lighting controls and plenum programs, and the IECC unified
constructions; ADR 0037 to 0045), with the same values, stored more compactly, and
the generator recipes of the 90.1 programs in each folder's `generator.json`.

Releases 1.1.0 to 1.6.0 are deltas on 1.0.0; later minors are deltas on this release.

Verify with `python -m scripts.atlas_snapshot --verify`; rebuild and compare with
`--check`. Upstream notices are in `notices/`; original Atlas work remains unlicensed
(see `LICENSE`).
'''


def digest(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def recipes_digest():
    h = hashlib.sha256()
    for path in sorted(RECIPES.glob('*.json')):
        h.update(path.name.encode()+b'\0'+hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


def encode(path, data):
    """Indented JSON one record per line down to three levels; anything else unchanged."""
    if path.endswith('.json') and (data.startswith(b'{\n  "') or data.startswith(b'[\n  ')):
        return (layered(json.loads(data), 3)+'\n').encode('utf-8')
    return data


def generator_files(files):
    """{folder/generator.json: bytes} for the release programs of the current templates, and the counts."""
    definitions = load_json(DEFINITIONS)
    by_key = defaultdict(dict)
    for d in definitions:
        source = d if d.get('evidence_view') == 'source' else next((x for x in definitions if x['id'] == d.get('source_definition_id')), d)
        by_key[(source.get('source_id'), d['name'], d.get('template'))][d.get('evidence_view')] = d['id']
        if d.get('derivation') == 'composed':  # release mixes keep no source ID; name and template identify them
            by_key[('composed', d['name'], d.get('template'))][d.get('evidence_view')] = d['id']
    out, counts = defaultdict(dict), defaultdict(int)
    for path, data in sorted(files.items()):
        if not (path.startswith('commercial/') and '/programs/' in path):
            continue
        program = json.loads(data)
        if program.get('template') not in CURRENT:
            counts['programs_without_recipes'] += 1
            continue
        key = 'composed' if program.get('derivation') == 'composed' else program.get('source_id')
        found = by_key.get((key, program['name'], program['template']))
        if not found:
            counts['programs_without_recipes'] += 1
            continue
        entry = {}
        for view, definition_id in sorted(found.items()):
            recipe = RECIPES/f'{definition_id}.json'
            if recipe.exists():
                entry['reviewed' if view == 'reviewed' else 'source'] = load_json(recipe)
        if entry:
            out[path.split('/programs/')[0]+'/generator.json'][program['id']] = entry
            counts['programs_with_recipes'] += 1
    return {p: (layered(v, 2)+'\n').encode('utf-8') for p, v in out.items()}, dict(counts)


def exporter_inputs(source):
    """The frozen-folder values the exporters of the source release read, under release IDs."""
    release = Release(source, release=SOURCE)
    services, programs = release.capped()
    sources = {p.get('source_id') for _, p in release.programs.values()}
    commercial = load_json(LEGACY)
    inactive = sorted(r['id'] for r in commercial if r['id'] in sources and r['heating_setpoint_schedule_id'] is None
                      and r['cooling_setpoint_schedule_id'] is None)
    return {'schema_version': '1.0.0', 'decision': 'docs/adr/0046-release-2-0-0.md',
            'capped_services': sorted(services), 'capped_programs': sorted(programs), 'inactive_controls': inactive}


def assemble():
    source = atlas_minor_release.files(SOURCE)
    files = {p: encode(p, d) for p, d in source.items() if p not in ('manifest.json', 'README.md')}
    generators, generator_counts = generator_files(source)
    files.update(generators)
    files[EXPORTER_INPUTS] = (layered(exporter_inputs(source), 1)+'\n').encode('utf-8')
    files['README.md'] = README.encode('utf-8')
    listed = json.loads((ROOT/f'data/atlas-releases/v{SOURCE}/manifest.json').read_text(encoding='utf-8'))
    manifest = {
        'schema_version': '1.0.0', 'kind': 'atlas_release', 'release': RELEASE, 'status': 'candidate', 'scope': listed['scope'],
        'base_release': None, 'snapshot_of': {'release': SOURCE, 'manifest_sha256': digest(f'data/atlas-releases/v{SOURCE}/manifest.json')},
        'decision': [*listed['decision'], 'docs/adr/0046-release-2-0-0.md'], 'deferred': list(DEFERRED),
        'generated_by': 'python -m scripts.atlas_snapshot',
        'input_sha256': {**{p: digest(p) for p in INPUTS}, 'atlas_schedules/data/recipes': recipes_digest()},
        'counts': {**listed['counts'], **generator_counts},
        'files': {p: {'sha256': atlas_release.sha(d), 'bytes': len(d)} for p, d in sorted(files.items())}}
    return {**files, 'manifest.json': suite_bytes(manifest)}


def verify(folder=TARGET, inputs=True):
    listed = json.loads((Path(folder)/'manifest.json').read_text(encoding='utf-8'))
    if listed.get('kind') != 'atlas_release' or listed.get('release') != RELEASE or listed.get('base_release') is not None:
        raise ValueError(f'Not a full atlas release {RELEASE} manifest: {folder}')
    for path, entry in listed['files'].items():
        p = Path(folder)/path
        data = p.read_bytes() if p.is_file() else None
        if data is None or len(data) != entry['bytes'] or atlas_release.sha(data) != entry['sha256']:
            raise ValueError('Release file missing or differs: '+path)
    extra = sorted({p.relative_to(folder).as_posix() for p in Path(folder).rglob('*') if p.is_file()} - set(listed['files']) - {'manifest.json'})
    if extra:
        raise ValueError('Release files not in the manifest: '+', '.join(extra[:5]))
    stale = inputs and [p for p, d in listed['input_sha256'].items()
                        if (recipes_digest() if p == 'atlas_schedules/data/recipes' else digest(p)) != d]
    if stale:
        raise ValueError('Release inputs changed since it was written; rerun python -m scripts.atlas_snapshot: '+', '.join(stale))
    return listed


def files(folder=TARGET):
    """Every file, checked against the manifest; the writer's inputs need not be present."""
    listed = verify(folder, inputs=False)
    return {path: (Path(folder)/path).read_bytes() for path in listed['files']}


def check():
    verify()
    built = assemble()
    written = {p.relative_to(TARGET).as_posix() for p in TARGET.rglob('*') if p.is_file()}
    differ = sorted(p for p in set(built) | written if p not in built or p not in written or (TARGET/p).read_bytes() != built[p])
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
    size = sum(e['bytes'] for e in listed['files'].values())
    print(f'Atlas release {RELEASE} (full snapshot of {SOURCE}): {len(listed["files"])} files, {size/1e6:.0f} MB; '
          + ', '.join(f'{v} {k}' for k, v in listed['counts'].items()))


if __name__ == '__main__':
    main()
