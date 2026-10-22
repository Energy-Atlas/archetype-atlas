"""Assemble, write and verify the ADR 0036 release folder data/atlas-releases/v1.0.0.

The folder holds the commercial program, construction and systems files from the
three writers, merged; the upstream notices they cite; the repository LICENSE; and
a manifest listing every file with its SHA-256 and size, the inputs it was built
from and record counts. Residential (ResStock) storage is deferred.

python -m scripts.atlas_release            # write the folder
python -m scripts.atlas_release --verify   # every file against the manifest
python -m scripts.atlas_release --check    # rebuild and compare byte for byte
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts import atlas_constructions, atlas_programs, atlas_systems
from scripts.atlas_format import merge, suite_bytes
from scripts.common import ROOT

TARGET = ROOT/'data/atlas-releases/v1.0.0'
NOTICES = ROOT/'sources/licenses'
# Construction documents come from the combined suite, so its notices travel with them.
INHERITED_NOTICES = ROOT/'data/construction-foundation-releases/v1.0.0/notices'
INPUTS = (
    'data/definition-releases/v0.1.1/manifest.json',
    'data/resolution-releases/v0.4.0/manifest.json',
    'data/water-reporting-releases/v0.1.0/manifest.json',
    'data/completion-releases/v0.1.0/manifest.json',
    'data/construction-releases/v2.0.0/manifest.json',
    'data/construction-equivalent-releases/v1.1.0/manifest.json',
    'data/construction-foundation-releases/v1.0.0/manifest.json',
    'scripts/atlas_format.py', 'scripts/atlas_programs.py', 'scripts/atlas_constructions.py',
    'scripts/atlas_systems.py', 'scripts/atlas_release.py',
    'scripts/construction_foundation_release.py', 'scripts/construction_foundation_export.py',
)

README = '''# Energy Archetype Atlas release 1.0.0 (commercial)

Suite-based storage under ADR 0036 (docs/adr/0036-suite-based-release-storage.md).
This release covers the commercial templates; residential (ResStock) storage is
deferred and remains in the frozen earlier releases.

- `commercial/<template>/<building-type>/`: one file per program under
  `programs/{source,department,general}/` and per construction set under
  `constructions/`; the folder's `schedules.json`, `systems.json`,
  `components.json`, `services.json` and `water.json` tables.
- `commercial/<template>/library/`: assemblies, materials, HVAC performance curves
  and rules shared between that template's building types.
- `evidence/`: evidence per folder and per template library, and `glossary.json`
  for texts, source files, filling-rule notes and unresolved reasons.
- `manifest.json`: every file with its SHA-256 and size, the pinned inputs and
  record counts.

Verify with `python -m scripts.atlas_release --verify`; rebuild and compare with
`--check`. Programs store fillings inline: the source-backed reading ignores them,
the filled reading applies them. Upstream notices are in `notices/`; original
Atlas work remains unlicensed (see `LICENSE`).
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def commercial_folders():
    """Program, systems and construction folders of the commercial templates."""
    programs = atlas_programs.load_sources()
    systems = atlas_systems.load_sources()
    constructions = atlas_constructions.load_sources()
    here = lambda r: (r['template'], r['building_type'])
    return (programs, systems, constructions,
            sorted({here(p) for p in programs.programs.values() if p['source_family'] != atlas_systems.RESIDENTIAL}),
            sorted({here(h) for h in systems.hvac.values() if h['source_family'] != atlas_systems.RESIDENTIAL}
                   | {here(s) for s in systems.services.values()}),
            sorted({(s['source']['template'], s['source']['building_type']) for s in constructions.sets.values()
                    if s['source']['template'] != atlas_constructions.RESIDENTIAL}))


def assemble(folders=None):
    """Every release file as {path: bytes}, limited to `folders` when given."""
    psrc, ssrc, csrc, pfolders, sfolders, cfolders = commercial_folders()
    keep = (lambda f: True) if folders is None else (lambda f: f in set(folders))
    programs = {f: atlas_programs.build_folder(psrc, *f) for f in pfolders if keep(f)}
    missing = [f for f in sfolders if keep(f) and f not in programs]
    if missing:
        raise ValueError(f'Systems need their folder programs first: {missing}')
    systems = [atlas_systems.build_folder(ssrc, *f, programs[f]) for f in sfolders if keep(f)]
    chosen = [f for f in cfolders if keep(f)]
    constructions = [atlas_constructions.build_folders(csrc, chosen)] if chosen else []
    files = merge(*[b.files for b in programs.values()], *[b.files for b in systems], *[b.files for b in constructions])
    glossary = json.loads(files['evidence/glossary.json'])
    cited = {Path(s['license_path']).name for s in glossary['source_files'].values() if s.get('license_path')}
    for name in sorted(cited | {p.name for p in INHERITED_NOTICES.iterdir()}):
        files['notices/'+name] = (NOTICES/name).read_bytes()
    files['LICENSE'] = (ROOT/'LICENSE').read_bytes()
    files['README.md'] = README.encode('utf-8')
    files['manifest.json'] = suite_bytes(manifest(files))
    return files


def manifest(files):
    sets = [json.loads(d) for p, d in files.items() if '/constructions/' in p]
    tables = lambda name: [json.loads(d) for p, d in files.items() if p.startswith('commercial/') and p.endswith('/'+name)]
    folders = {'/'.join(p.split('/')[:3]) for p in files if p.startswith('commercial/') and p.split('/')[2] != 'library'}
    return {
        'schema_version': '1.0.0', 'kind': 'atlas_release', 'release': '1.0.0', 'status': 'candidate',
        'scope': 'commercial', 'base_release': None, 'decision': 'docs/adr/0036-suite-based-release-storage.md',
        'deferred': ['residential (ResStock) storage', 'generator recipes in program files',
                     'consumer contract exports (Program 5.0.0, construction 4.0.0 / 3.0.0)'],
        'generated_by': 'python -m scripts.atlas_release',
        'input_sha256': {path: sha((ROOT/path).read_bytes()) for path in INPUTS},
        'counts': {
            'folders': len(folders),
            'programs': sum('/programs/' in p for p in files),
            'construction_sets': len(sets),
            'construction_contexts': sum(len(s['contexts']) for s in sets),
            'hvac_systems': sum(len(t) for t in tables('systems.json')),
            'services': sum(len(t) for t in tables('services.json')),
            'water_programs': sum(len(t['programs']) for t in tables('water.json')),
        },
        'files': {path: {'sha256': sha(data), 'bytes': len(data)} for path, data in sorted(files.items())},
    }


def write(files, target=TARGET):
    """Write the folder so it holds exactly these files."""
    target = Path(target)
    for path in [p for p in target.rglob('*') if p.is_file()] if target.exists() else []:
        if path.relative_to(target).as_posix() not in files:
            path.unlink()
    for path, data in files.items():
        out = target/path
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.exists() or out.read_bytes() != data:
            out.write_bytes(data)
    for directory in sorted((d for d in target.rglob('*') if d.is_dir()), key=lambda d: -len(d.parts)):
        if not any(directory.iterdir()):
            directory.rmdir()


def verify(target=TARGET):
    """Every file the manifest lists, with its checksum and size, and nothing else."""
    target = Path(target)
    listed = json.loads((target/'manifest.json').read_text(encoding='utf-8'))
    if listed.get('kind') != 'atlas_release':
        raise ValueError('Not an atlas release manifest: '+str(target))
    for path, entry in listed['files'].items():
        file = target/path
        if not file.is_file():
            raise ValueError('Release file missing: '+path)
        data = file.read_bytes()
        if len(data) != entry['bytes'] or sha(data) != entry['sha256']:
            raise ValueError('Release file checksum or bytes differ: '+path)
    extra = sorted({p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
                   - set(listed['files']) - {'manifest.json'})
    if extra:
        raise ValueError('Release files not in the manifest: '+', '.join(extra[:5]))
    return listed


def check(target=TARGET):
    """Rebuild the release and compare it with the written folder byte for byte."""
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
    if args.verify:
        counts = verify()['counts']
    elif args.check:
        check()
        counts = verify()['counts']
    else:
        files = assemble()
        write(files)
        counts = verify()['counts']
    print('Atlas release 1.0.0 (commercial): '+', '.join(f'{v} {k}' for k, v in counts.items()))


if __name__ == '__main__':
    main()
