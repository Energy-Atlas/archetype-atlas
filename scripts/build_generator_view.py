"""Build the generator view of the newest atlas release, the data the atlas-schedules wheel bundles (ADR 0051).

python -m scripts.build_generator_view            # write atlas_schedules/data/atlas-release/ from data/atlas-releases
python -m scripts.build_generator_view --check    # rebuild and fail unless the folder already equals it
python -m scripts.build_generator_view --out DIR  # write the view elsewhere

The generator assembles its recipes from a release (atlas_schedules.release). Outside a checkout it has
no release tree, so the wheel bundles a view of the newest release in the tree: for each building folder
with generation blocks, exactly the files the assembler reads (`generation.json`, `schedules.json`,
`services.json`, the program records with blocks and their composition members, each record cut to the
fields the assembler reads: `KEEP`), packed one JSON file per folder as {release path: document}, plus
`definition-map.json` and an `index.json` naming the release, its manifest hash and the base chain. A
bundle generated from the view equals one generated from the release tree: every program view assembles
to the same recipe (checked here on every build) and the provenance is the same hash. The view is not
committed; `python -m build` and the release workflows build it first (tests/test_package.py).
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from atlas_schedules import __version__
from atlas_schedules.release import Release, TreeStore, VIEW, VIEW_INDEX
from scripts import atlas_delta
from scripts.common import ROOT

ROOT_FILES = ('definition-map.json',)
FOLDER_FILES = ('generation.json', 'schedules.json', 'services.json')
# The program record fields atlas_schedules.programmes reads (view_record, commercial_body, fixed_body, caller_water,
# assemble); evidence, calendars, lighting controls and the dwellings' top-level fillings stay in the release.
KEEP = ('id', 'name', 'mode', 'derivation', 'template', 'building_type', 'source_family', 'source_id', 'climate',
        'loads', 'parameters', 'composition')


def compact(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def programs_of(release, folder) -> list:
    """Release paths of the folder's programs with blocks and, recursively, their composition members."""
    wanted, queue = set(), list(release.generation(folder).get('programs', {}))
    while queue:
        program_id = queue.pop()
        if program_id in wanted:
            continue
        wanted.add(program_id)
        _, record = release.program(program_id)
        for member in (record.get('composition') or {}).get('members', []):
            queue.append(member['program_id'])
    return sorted(release.program_paths[p] for p in wanted)


def prune(path: str, document):
    return {k: v for k, v in document.items() if k in KEEP} if '/programs/' in path else document


def build(release) -> dict:
    """{file name: bytes} of the view."""
    chain, base = [], release.base
    while base is not None:
        chain.append(base.version)
        base = base.base
    folders, files = {}, {}
    for folder in release.generation_folders():
        paths = [f'{folder}/{name}' for name in FOLDER_FILES if f'{folder}/{name}' in release.paths] + programs_of(release, folder)
        name = folder.replace('/', '__') + '.json'
        files[name] = compact({path: prune(path, release.json(path)) for path in paths})
        folders[folder] = {'file': name, 'paths': paths}
    index = {
        'kind': 'atlas_release_generator_view', 'schema_version': '1.0.0', 'release': release.version,
        'manifest_sha256': release.manifest_sha256, 'base_releases': chain,
        'generation': {'schema_version': release.generation_schema_version},
        'generator': {'version': __version__, 'package': 'atlas-schedules'},
        'generated_by': 'python -m scripts.build_generator_view', 'source': f'data/atlas-releases/v{release.version}',
        'program_fields': list(KEEP),
        'root': {path: release.json(path) for path in ROOT_FILES},
        'folders': folders,
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    files[VIEW_INDEX] = compact(index)
    return files


def check_assembly(release, files: dict) -> int:
    """Every program view, service and configuration assembles from the view as from the release; the view count."""
    from atlas_schedules import programmes
    from atlas_schedules.release import ViewStore
    with tempfile.TemporaryDirectory() as temporary:
        write(files, Path(temporary))
        view = Release(ViewStore(Path(temporary)))
        count = 0
        for folder in release.generation_folders():
            doc = release.generation(folder)
            for rid, block in doc.get('programs', {}).items():
                for values in block['views']:
                    if programmes.assemble(view, rid, values) != programmes.assemble(release, rid, values):
                        raise SystemExit(f'{rid} ({values}) assembles differently from the view')
                    count += 1
            for sid in doc.get('services', {}):
                if programmes.assemble_service(view, sid) != programmes.assemble_service(release, sid):
                    raise SystemExit(f'{sid} assembles differently from the view')
            for cid in doc.get('configurations', {}):
                if programmes.assemble_configuration(view, cid) != programmes.assemble_configuration(release, cid):
                    raise SystemExit(f'{cid} assembles differently from the view')
    return count


def write(files: dict, out: Path) -> None:
    if out.is_dir():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for name, data in files.items():
        (out/name).write_bytes(data)


def stale(files: dict, out: Path) -> list:
    present = {p.name for p in out.iterdir() if p.is_file()} if out.is_dir() else set()
    return sorted({n for n, d in files.items() if not (out/n).is_file() or (out/n).read_bytes() != d} | (present - set(files)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--out', type=Path, default=VIEW)
    parser.add_argument('--release', default=atlas_delta.RELEASE, help='release number under data/atlas-releases')
    args = parser.parse_args(argv)
    release = Release(TreeStore(atlas_delta.RELEASES/f'v{args.release}'))
    files = build(release)
    size = sum(len(d) for d in files.values())
    views = check_assembly(release, files)
    if args.check:
        differ = stale(files, args.out)
        if differ:
            raise SystemExit(f'Generator view of release {release.version} differs in {len(differ)} files, e.g. {differ[:3]}; '
                             f'run python -m scripts.build_generator_view')
        print(f'Generator view of release {release.version} matches: {len(files)} files, {size / 1e6:.1f} MB, {views} views assemble')
        return
    write(files, args.out)
    print(f'Generator view of release {release.version} written to {args.out}: {len(files)} files, {size / 1e6:.1f} MB, '
          f'{views} views assemble')


if __name__ == '__main__':
    main()
