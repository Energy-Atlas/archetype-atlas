"""Write the generation blocks of the DOE Ref programs from release 2.0.0 (ADR 0046 stage X1.2, ADR 0049).

python -m scripts.build_reference_recipes --idf-root "<extracted doe-reference/v1.4_7.2>"           # write
python -m scripts.build_reference_recipes --idf-root "<extracted doe-reference/v1.4_7.2>" --check   # compare

Release 1.1.0 reconciled the DOE Ref programs with the DOE v1.4_7.2 files (ADR 0037), so their
generator parameters come from the release itself, written to each DOE Ref folder's
`generation.json` in release 2.1.0:
- programs, schedules and shared services of `data/atlas-releases/v2.0.0/commercial/
  doe-ref-*/<folder>/`, source values only. The release fills of the generated types set only
  zero loads and unconditioned attics and plenums, which carry no slot, so no filled view is written;
- People topology for inferring hours of operation from the DOE file zones (Chicago 5A
  IDF, checked against the reconciliation register): each zone maps to its release
  program by name, as the reconciliation compared them (openstudio-standards geometry
  space names, aliases, the zones moved to programs of their own), and contributes
  zone floor area x the program's occupancy density on the program's occupancy
  schedule, in zone-name order; the dominant group follows openstudio-standards
  (residential space types by name, design people x zone multiplier);
- a `comstock_hours` block per source program of the 15 sampled types (its configuration), a
  `composition` block per department or general mix, the shared hot-water services with their one
  configuration, and the Midrise Apartment programs as a ResStock apartment unit
  (scripts/build_apartment_units.py) or `fixed` source rule sets (office, corridor).
The recipes are assembled from these blocks by atlas_schedules.programmes.
"""
import argparse
import hashlib
import re
from collections import defaultdict
from pathlib import Path

from atlas_schedules.programmes import SAMPLING, TEMPLATES, known_positive, load_of
from atlas_schedules.release import Release
from scripts import idf_reader, release_2_1_0
from scripts.build_apartment_units import geometries, unit_block
from scripts.common import ROOT, load_json
from scripts.reconciliation_register import NEW_PROGRAMS
from scripts.reference_extras import zone_floors
from scripts.reference_loads import ALIASES, TYPES, VINTAGES

RELEASE = ROOT/'data/atlas-releases/v2.0.0'
REGISTER = ROOT/'data/reconciliation/doe-reference-v1.json'
APARTMENT = 'MidriseApartment'
VIEW = 'source'
SCHEMA = '1.0.0'
RESIDENTIAL_SPACE_TYPES = re.compile(r"\sApartment|GuestRoom|PatRoom|ResBedroom|ResLiving")


def release_folder(template, folder):
    return RELEASE/'commercial'/template/folder


def release_path(path):
    return Path(path).relative_to(ROOT).as_posix()


def read_folder(template, folder):
    root = release_folder(template, folder)
    programs = {}
    for path in sorted((root/'programs').glob('*/*.json')):
        record = load_json(path)
        programs[record['id']] = (release_path(path), record)
    return programs, load_json(root/'schedules.json'), load_json(root/'services.json')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def zone_programs(model, building_type, geometry, by_name):
    """[(zone name, multiplier, floor m2, [(program, share)])] in zone-name order; zones without a release program
    are left out."""
    floors = zone_floors(model)
    spaces = {s['name'].lower().replace(' ', '_'): s for s in geometry['spaces']}
    moved = {z.lower(): space_type for (bt, space_type), group in NEW_PROGRAMS.items() if bt == building_type
             for z in group['zones']}
    out = []
    for key, zone in sorted(model.zones.items(), key=lambda item: item[1]['name']):
        if key in moved:
            shares = {moved[key]: 1.0}
        else:
            names = ALIASES.get(building_type, {}).get(zone['name'], [zone['name']])
            mapped = [spaces.get(n.lower().replace(' ', '_')) for n in names]
            if any(s is None for s in mapped):
                continue
            total = sum(s['floor_area_m2'] for s in mapped)
            shares = defaultdict(float)
            for s in mapped:
                shares[s['standards_space_type']] += s['floor_area_m2']/total
        programs = [(by_name[f'{t}_{building_type}'], share) for t, share in sorted(shares.items())
                    if f'{t}_{building_type}' in by_name]
        if programs:
            out.append((zone['name'], zone['multiplier'], floors[key], programs))
    return out


def residential(space_type):
    """openstudio-standards space.rb `space_residential?`: by space type name."""
    return bool(space_type and RESIDENTIAL_SPACE_TYPES.search(space_type))


def occupancy_carrier(zones):
    """(people [(schedule id, design people)] of the dominant group, residential dominant?)."""
    groups, totals = {True: [], False: []}, {True: 0.0, False: 0.0}
    for _, multiplier, floor, programs in zones:
        for program, share in programs:
            occupancy = load_of(program, 'occupancy')
            if not known_positive(occupancy):
                continue
            count = floor*share*occupancy['value']
            group = residential(program['name'].rsplit('_', 1)[0])
            groups[group].append([occupancy['schedule_id'], count])
            totals[group] += count*multiplier
    dominant = totals[True] > totals[False]
    return groups[dominant], dominant


def block(method, parameters=None):
    return {'schema_version': SCHEMA, 'method': method, 'views': {VIEW: parameters or {}}}


def commercial_folder(template, building_type, programs, folder_services, people, invert):
    """The generation.json document of one sampled DOE Ref folder."""
    configuration = f'{SAMPLING[building_type]}__{TEMPLATES[template][0]}__{VIEW}'
    blocks = {pid: block('composition') if record['derivation'] == 'composed'
              else block('comstock_hours', {'configuration_id': configuration})
              for pid, (_, record) in sorted(programs.items())}
    services = {sid: {'schema_version': SCHEMA, 'method': 'comstock_hours', 'configurations': [configuration]}
                for sid, service in sorted(folder_services.items()) if water_service(service)}
    configurations = {configuration: {'building_type': SAMPLING[building_type], 'people': people, 'invert_rule_days': invert}}
    return {'configurations': configurations, 'programs': blocks, **({'services': services} if services else {})}


def water_service(service):
    """A shared service the generator draws: a known hot-water volume on a schedule."""
    load = service['load']
    return load['quantity'] == 'hot_water_volume' and bool(load['value']) and isinstance(load['schedule_id'], str)


def apartment_folder(release, folder, programs, geometry):
    """The DOE Midrise Apartment programs: apartments as ResStock units, the others as fixed source rule sets."""
    blocks = {}
    for pid, (_, record) in sorted(programs.items()):
        if record['name'] == f'Apartment_{APARTMENT}':
            blocks[pid] = block('resstock_unit', {'resstock_unit': unit_block(release, pid, VIEW, geometry)})
        else:
            blocks[pid] = block('fixed')
    return {'programs': blocks}


def build(idf_root):
    """{release folder: generation.json document} of every DOE Ref folder with a generator kind."""
    register = load_json(REGISTER)
    geometry = geometries()
    release = Release(release_2_1_0.TARGET)
    docs = {}
    for vintage, (folder_template, _, template) in VINTAGES.items():
        for key, (building_type, folder) in [*TYPES.items(), (None, (APARTMENT, 'midrise-apartment'))]:
            programs, _, folder_services = read_folder(folder_template, folder)
            name = f'commercial/{folder_template}/{folder}'
            if building_type == APARTMENT:
                # Apartments are ResStock units (scripts/build_apartment_units.py, plan section 8, B7).
                docs[name] = apartment_folder(release, name, programs, geometry[(template, APARTMENT)])
                continue
            path = next((Path(idf_root)/f'refbldg_{key}_{vintage}_v1-4_7-2').glob('*5A_USA_IL_CHICAGO-OHARE.idf'))
            if register['input_sha256'][path.name] != sha256(path):
                raise ValueError('IDF differs from the reconciliation register input: '+path.name)
            by_name = {r['name']: r for _, r in programs.values() if r['derivation'] != 'composed'}
            zones = zone_programs(idf_reader.Model(path), building_type, geometry[(template, building_type)], by_name)
            people, invert = occupancy_carrier(zones)
            docs[name] = commercial_folder(template, building_type, programs, folder_services, people, invert)
    return docs


def stale(docs):
    release = Release(release_2_1_0.TARGET)
    return sorted(f for f, doc in docs.items() if {k: v for k, v in release.generation(f).items() if k != 'schema_version'} != doc)


def write(idf_root):
    docs = build(idf_root)
    changed = stale(docs)
    release_2_1_0.write_generation({f: docs[f] for f in changed})
    counts = defaultdict(int)
    for doc in docs.values():
        for b in doc['programs'].values():
            counts[b['method']] += 1
    print(f'Rewrote {len(changed)} of {len(docs)} DOE Ref folders: {dict(counts)} blocks, '
          f'{sum(len(d.get("services", {})) for d in docs.values())} services, '
          f'{sum(len(d.get("configurations", {})) for d in docs.values())} configurations')


def check(idf_root):
    docs = build(idf_root)
    changed = stale(docs)
    if changed:
        raise SystemExit(f'{len(changed)} DOE Ref generation.json files differ, e.g. {changed[:3]}')
    print(f'DOE Ref generation blocks reproduce: {len(docs)} folders, '
          f'{sum(len(d["programs"]) for d in docs.values())} programs')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--idf-root', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    (check if args.check else write)(args.idf_root)


if __name__ == '__main__':
    main()
