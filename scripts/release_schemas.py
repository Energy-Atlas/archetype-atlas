"""Validate data release files against their JSON Schemas (Draft 2020-12, ADR 0056).

python -m scripts.release_schemas [--release 2.2.0] [--all]

Each release path is matched to its schema by name (`SCHEMAS`): the manifest, `definition-map.json`,
every folder's `generation.json` (the generator validates it too, when it reads it), `schedules.json`,
`services.json` and the program records. `scripts.atlas_delta --check` validates the files a delta
holds and its manifest; `--all` validates every file of the resolved release (the published 2.x
releases validate as they are; their manifests are pinned and never edited). Files of other kinds
(construction packages, systems, water, components, evidence, id-map) are the writers' internal
records, whose consumer contracts are the export schemas; they have no release-record schema yet.
"""
import argparse
from functools import lru_cache
import json
import re

import jsonschema

from scripts.common import ROOT

GENERATION = ROOT/'atlas_schedules/schemas/generation-v1.schema.json'
SCHEMAS = (
    (re.compile(r'^manifest\.json$'), ROOT/'schemas/atlas-release-manifest-v1.schema.json'),
    (re.compile(r'^definition-map\.json$'), ROOT/'schemas/atlas-definition-map-v1.schema.json'),
    (re.compile(r'^(commercial|residential)/[^/]+/[^/]+/generation\.json$'), GENERATION),
    (re.compile(r'^(commercial|residential)/[^/]+/[^/]+/schedules\.json$'), ROOT/'schemas/atlas-release-schedules-v1.schema.json'),
    (re.compile(r'^commercial/[^/]+/[^/]+/services\.json$'), ROOT/'schemas/atlas-release-services-v1.schema.json'),
    (re.compile(r'^(commercial|residential)/[^/]+/[^/]+/programs/(.+/)?[^/]+\.json$'), ROOT/'schemas/atlas-release-program-v1.schema.json'),
)


@lru_cache(maxsize=None)
def validator(path):
    schema = json.loads(path.read_text(encoding='utf-8'))
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def schema_for(path):
    """The schema file of a release path, or None for a kind without a release-record schema."""
    return next((schema for pattern, schema in SCHEMAS if pattern.match(path)), None)


def errors(files):
    """[(release path, schema name, message)] of every file in {path: bytes or document} that fails its schema."""
    found = []
    for path, data in sorted(files.items()):
        schema = schema_for(path)
        if schema is None:
            continue
        document = json.loads(data) if isinstance(data, (bytes, str)) else data
        check = validator(schema)
        if not check.is_valid(document):
            error = jsonschema.exceptions.best_match(check.iter_errors(document))
            where = '/'.join(str(p) for p in error.absolute_path)
            found.append((path, schema.name, f'{where}: {error.message[:300]}'))
    return found


def check(files, label):
    """Raise SystemExit naming the first failures; return the number of files validated."""
    failed = errors(files)
    if failed:
        lines = '\n'.join(f'  {p} ({s}) {m}' for p, s, m in failed[:10])
        raise SystemExit(f'{len(failed)} {label} files fail their schemas:\n{lines}')
    return sum(1 for p in files if schema_for(p))


def main():
    from scripts import atlas_delta
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--release', default=atlas_delta.RELEASE)
    parser.add_argument('--all', action='store_true', help='every file of the resolved release, not only the delta and manifest')
    args = parser.parse_args()
    folder = atlas_delta.folder_of(args.release)
    if args.all:
        files = atlas_delta.files(args.release)
        files['manifest.json'] = (folder/'manifest.json').read_bytes()
    else:
        files = {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    print(f'Release {args.release}: {check(files, args.release)} files valid against their schemas')


if __name__ == '__main__':
    main()
