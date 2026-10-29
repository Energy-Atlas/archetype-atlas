"""Release 2.1.0: the generation parameters with the programs, a delta on 2.0.0 (ADR 0049).

python -m scripts.release_2_1_0 --check    # verify the folder against its manifest; assemble every view

The generator packaged 1,585 recipes, 186 services, 120 configurations and a schedule table that
repeated release 2.0.0's values. Stages P1 and P2 wrote, from those copies, what the release does not
already state (this script at commit ca8553c9):
- per program, a `generation` block (method and, per view, the parameters the record cannot give):
  `comstock_hours` (the configuration), `composition` and `fixed` (none), `resstock_unit` (ADR 0047's
  unit characteristics) and `resstock_dwelling` (the dwelling's executed OpenStudio-HPXML inputs);
- per service, the configurations it runs under; per folder, its building configurations, their
  People on the folder's release schedules;
- `definition-map.json`: each packaged definition program ID with its release program and view,
  each definition service ID with its release service.

Its gate held: every packaged recipe, service and configuration, re-keyed by release ID, equalled the
one assembled from the release (atlas_schedules.programmes) as JSON, schedules compared by their rules.
Stated exceptions: the 12 hotel corridor compositions no release program holds, and the 36 90.1
apartment-building fixed recipes, whose legacy form dropped known heat fractions and kept a
zero-density occupancy slot; the release values replace both. Stage P3 deleted the packaged copies.

The DOE Ref blocks, services and configurations are rewritten from the release and the DOE files by
scripts/build_reference_recipes.py, the apartment units' blocks by scripts/build_apartment_units.py,
both through `write_generation`. The 90.1 commercial blocks and configurations and the ResStock
dwellings' inputs have no source builder in this tree, as their packaged recipes had none; they are
kept as written.
"""
import argparse
from collections import defaultdict
import hashlib
import json

from atlas_schedules import programmes
from atlas_schedules.release import Release
from scripts.common import ROOT
from scripts.iecc_commercial_values import layered

RELEASES = ROOT/'data/atlas-releases'
BASE = RELEASES/'v2.0.0'
TARGET = RELEASES/'v2.1.0'
SCHEMA = '1.0.0'


def text(value, depth=3):
    """Compact storage (ADR 0046 P9): one record per line down to `depth` levels."""
    return (layered(value, depth)+'\n').encode('utf-8')


def counts(release):
    methods = defaultdict(int)
    services = configurations = 0
    for folder in release.generation_folders():
        doc = release.generation(folder)
        for block in doc.get('programs', {}).values():
            methods[block['method']] += 1
        services += len(doc.get('services', {}))
        configurations += len(doc.get('configurations', {}))
    mapped = release.json('definition-map.json')
    return {'generation_folders': len(release.generation_folders()), 'programs_with_generation': sum(methods.values()),
            'methods': dict(sorted(methods.items())), 'services_with_generation': services,
            'configurations': configurations, 'definition_programs': len(mapped['programs']),
            'definition_services': len(mapped['services'])}


def write_manifest(folder=TARGET):
    """Rewrite the manifest's file list and counts after a writer changed the folder's files."""
    path = folder/'manifest.json'
    manifest = json.loads(path.read_bytes())
    files = sorted(p for p in folder.rglob('*') if p.is_file() and p != path)
    manifest['files'] = {p.relative_to(folder).as_posix(): {'bytes': p.stat().st_size,
                                                            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                         for p in files}
    path.write_bytes(text(manifest))
    manifest['counts'] = counts(Release(folder))
    path.write_bytes(text(manifest))


def write_generation(docs, folder=TARGET):
    """Write {release folder: generation.json document} and the manifest."""
    for name, doc in docs.items():
        out = folder/name/'generation.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text({**doc, 'schema_version': SCHEMA}))
    write_manifest(folder)


def verify(folder=TARGET):
    """Every listed file has its hash and nothing else is in the folder; the base is the one recorded."""
    release = Release(folder)
    listed = release.manifest['files']
    present = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()} - {'manifest.json'}
    bad = [p for p, entry in listed.items() if hashlib.sha256((folder/p).read_bytes()).hexdigest() != entry['sha256']]
    if bad or present != set(listed):
        raise SystemExit(f'Release 2.1.0: {len(bad)} files differ from the manifest; unlisted {sorted(present - set(listed))[:3]}, '
                         f'missing {sorted(set(listed) - present)[:3]}')
    if release.manifest['counts'] != counts(release):
        raise SystemExit('Release 2.1.0: the manifest counts differ from the folder')
    return release


def assembles(release):
    """Every block assembles in every view, and every service and configuration (the release alone)."""
    count = 0
    for folder in release.generation_folders():
        doc = release.generation(folder)
        for rid, block in doc.get('programs', {}).items():
            for view in block['views']:
                programmes.assemble(release, rid, view)
                count += 1
        for sid in doc.get('services', {}):
            programmes.assemble_service(release, sid)
        for cid in doc.get('configurations', {}):
            programmes.assemble_configuration(release, cid)
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', required=True)
    parser.parse_args()
    release = verify()
    print(f'Release 2.1.0 verified: {assembles(release)} program views assemble')


if __name__ == '__main__':
    main()
