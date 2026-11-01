"""Generation blocks of the IECC commercial and detailed office folders, from their zones (ADR 0055).

python -m scripts.build_zone_recipes --check           # derive from the newest release; every block assembles
python -m scripts.build_zone_recipes --out <folder>    # also write <family>/<template>/<type>/generation.json there

Release 2.2.0 gave blocks to the 90.1, DOE Ref and ResStock folders (ADR 0051). Two folder classes
of the same ComStock building types had none:
- the IECC commercial prototypes (ADR 0040): 14 sampled types x 6 editions;
- the detailed small, medium and large offices of the 90.1 and DOE Ref templates (ADR 0039): the office
  prototypes with their space types, 3 types x 5 templates.
Each folder's `generation.json` is written as `scripts.build_reference_recipes` writes the DOE Ref ones:
a `comstock_hours` block per source program (its building configuration), a `composition` block per
mix, the shared hot-water services under the folder's configurations, and one configuration per view:
the ComStock sampling building type (`programmes.SAMPLING`), the People that ComStock infers the hours
of operation from, and the rule-day inversion when residential spaces hold most design people.

People per zone are the zone's floor area x its program's occupancy density, on the program's
occupancy schedule, in zone-name order (`build_reference_recipes.occupancy_carrier`). The zones are:
- IECC: each program's `source_zones` (the PNNL IDF zones it was extracted from, ADR 0040 item 3);
- detailed offices: the spaces of the pinned openstudio-standards geometry
  (`data/construction-inputs/geometry-v1.json`), each with the program of its standards space type,
  the rule that reproduces every 90.1 configuration from the same file
  (`tests/test_zone_recipes.py`).
A view is written where it generates: `source` always, `filled` only where the filled program
generates differently (none here: IECC programs are source only, ADR 0040 item 20, and the
detailed offices' fillings set zero loads and unconditioned plenums, which carry no slot).
"""
import argparse
from pathlib import Path

from atlas_schedules import programmes
from atlas_schedules.programmes import SAMPLING, TEMPLATES, view_record
from atlas_schedules.release import Release
from scripts import atlas_delta
from scripts.build_apartment_units import geometries
from scripts.build_reference_recipes import occupancy_carrier, water_service
from scripts.common import ROOT

SCHEMA = atlas_delta.GENERATION_SCHEMA
DETAILED = ('SmallOfficeDetailed', 'MediumOfficeDetailed', 'LargeOfficeDetailed')
DETAILED_TEMPLATES = ('90.1-2007', '90.1-2013', '90.1-2019', 'DOE Ref Pre-1980', 'DOE Ref 1980-2004')
VIEWS = programmes.VIEWS


def folder_programs(release, folder):
    """{program ID: record} of one release folder."""
    template, building_type = folder.split('/')[1:]
    prefix = f'{template}.{building_type}.'
    return {pid: release.program(pid)[1] for pid in sorted(release.program_paths) if pid.startswith(prefix)}


def source_programs(programs):
    return {pid: r for pid, r in programs.items() if r['derivation'] != 'composed'}


def iecc_zones(programs, view):
    """[(zone, multiplier, floor m2, [(program, 1.0)])] from the programs' source zones, in zone-name order."""
    zones = []
    for record in source_programs(programs).values():
        data = view_record(record, view)
        for zone in record.get('source_zones') or []:
            zones.append((zone['name'], zone['multiplier'], zone['floor_area_m2'], [(data, 1.0)]))
    names = [z[0] for z in zones]
    if len(names) != len(set(names)):
        raise ValueError('A zone is a source zone of several programs')
    return sorted(zones, key=lambda z: z[0])


def geometry_zones(programs, geometry, building_type, view):
    """[(space, multiplier, floor m2, [(program, 1.0)])] of the prototype geometry's spaces whose standards
    space type has a program, in space-name order."""
    by_name = {r['name']: view_record(r, view) for r in source_programs(programs).values()}
    zones = []
    for space in sorted(geometry['spaces'], key=lambda s: s['name']):
        program = by_name.get(f"{space['standards_space_type']}_{building_type}")
        if program is not None:
            zones.append((space['name'], space['multiplier'], space['floor_area_m2'], [(program, 1.0)]))
    return zones


def configuration_name(building_type, template, view):
    """`<sampling type>[_detailed]__<template slug>__<view>`: unique in the release, as configuration IDs must be."""
    sampled = SAMPLING[building_type] + ('_detailed' if building_type in DETAILED else '')
    return f'{sampled}__{TEMPLATES[template]}__{view}'


def body(record, view):
    return programmes.commercial_body(view_record(record, view))


def program_views(programs):
    """{program ID: views it generates}: source, and filled where the filled record generates differently;
    a mix has the views of its members."""
    views = {}
    for pid, record in source_programs(programs).items():
        views[pid] = ['source'] + (['filled'] if body(record, 'filled') != body(record, 'source') else [])
    for pid, record in programs.items():
        if record['derivation'] == 'composed':
            members = [m['program_id'] for m in record['composition']['members']]
            views[pid] = [v for v in VIEWS if any(v in views[m] for m in members)]
    return views


def folder_document(release, folder, zones_of):
    """The generation.json document of one folder; `zones_of(programs, view)` gives its People topology."""
    programs = folder_programs(release, folder)
    records = list(programs.values())
    building_type, template = records[0]['building_type'], records[0]['template']
    views = program_views(programs)
    used = sorted({v for vs in views.values() for v in vs}, key=VIEWS.index)
    configurations = {}
    for view in used:
        people, invert = occupancy_carrier(zones_of(programs, view))
        configurations[configuration_name(building_type, template, view)] = {
            'building_type': SAMPLING[building_type], 'people': people, 'invert_rule_days': invert}
    blocks = {}
    for pid, record in programs.items():
        composed = record['derivation'] == 'composed'
        blocks[pid] = {'schema_version': SCHEMA, 'method': 'composition' if composed else 'comstock_hours',
                       'views': {v: {} if composed else {'configuration_id': configuration_name(building_type, template, v)}
                                 for v in views[pid]}}
    services = {sid: {'schema_version': SCHEMA, 'method': 'comstock_hours', 'configurations': sorted(configurations)}
                for sid, service in sorted(release.services(folder).items()) if water_service(service)}
    return {'schema_version': SCHEMA, 'configurations': configurations, 'programs': blocks,
            **({'services': services} if services else {})}


def iecc_folders(release):
    """The IECC commercial folders of a sampled building type (ADR 0055: the apartments stay without blocks)."""
    out = []
    for folder in sorted(set(release.folders.values())):
        family, template, _ = folder.split('/')
        if family != 'commercial' or not template.startswith('iecc-'):
            continue
        records = folder_programs(release, folder)
        if records and next(iter(records.values()))['building_type'] in SAMPLING:
            out.append(folder)
    return out


def detailed_folders(release):
    return sorted(f for f in set(release.folders.values())
                  if f.split('/')[0] == 'commercial' and f.split('/')[2].endswith('-office-detailed'))


def build(release):
    """{release folder: generation.json document} of the IECC commercial and detailed office folders."""
    shapes = geometries()
    docs = {folder: folder_document(release, folder, iecc_zones) for folder in iecc_folders(release)}
    for folder in detailed_folders(release):
        record = next(iter(folder_programs(release, folder).values()))
        template, building_type = record['template'], record['building_type']
        if template not in DETAILED_TEMPLATES or building_type not in DETAILED:
            raise ValueError(f'{folder}: unexpected detailed office {template} {building_type}')
        geometry = shapes[(template, building_type)]
        docs[folder] = folder_document(release, folder,
                                       lambda programs, view, g=geometry, b=building_type: geometry_zones(programs, g, b, view))
    return docs


def with_documents(release, docs):
    """The release read with `docs` laid over its own generation.json files."""
    generation = {f: release.generation(f) for f in release.generation_folders()}
    overlap = sorted(set(generation) & set(docs))
    if overlap:
        raise ValueError(f'Folders that already have generation.json: {overlap[:3]}')
    return Release(release.store, generation={**generation, **docs})


def gate(release, docs):
    """Every new block assembles in every view, every service a recipe requires has a block, and every People
    schedule is a schedule of its folder. Returns the number of program views."""
    reader = with_documents(release, docs)
    views = 0
    for folder, doc in docs.items():
        table = reader.schedules(folder)
        for cid, configuration in doc['configurations'].items():
            missing = [s for s, _ in configuration['people'] if s not in table]
            if missing or not configuration['people']:
                raise ValueError(f'{cid}: People schedules outside {folder} or no People: {missing[:3]}')
        for pid, block in doc['programs'].items():
            for view in block['views']:
                recipe = programmes.assemble(reader, pid, view)
                for sid in recipe['required_services']:
                    programmes.assemble_service(reader, sid)
                views += 1
        for sid in doc.get('services', {}):
            programmes.assemble_service(reader, sid)
    return views


def encode(doc):
    return atlas_delta.layered_bytes(doc)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='derive and gate without writing')
    parser.add_argument('--out', type=Path, help='folder to write <family>/<template>/<type>/generation.json into')
    parser.add_argument('--release', default=atlas_delta.RELEASE, help='release the blocks are derived from')
    args = parser.parse_args()
    release = Release(atlas_delta.folder_of(args.release))
    docs = build(release)
    views = gate(release, docs)
    configurations = sum(len(d['configurations']) for d in docs.values())
    services = sum(len(d.get('services', {})) for d in docs.values())
    print(f'{len(docs)} folders ({len(iecc_folders(release))} IECC, {len(detailed_folders(release))} detailed offices): '
          f'{sum(len(d["programs"]) for d in docs.values())} programs, {views} program views, {services} services, '
          f'{configurations} configurations assemble over release {release.version}')
    if args.out and not args.check:
        for folder, doc in docs.items():
            path = args.out/folder/'generation.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encode(doc))
        print(f'{len(docs)} generation.json written under {args.out}')


if __name__ == '__main__':
    main()
