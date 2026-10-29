"""Build the generator recipes of the DOE Ref programs from release 2.0.0 (ADR 0046, stage X1.2).

python -m scripts.build_reference_recipes --idf-root "<extracted doe-reference/v1.4_7.2>"           # write
python -m scripts.build_reference_recipes --idf-root "<extracted doe-reference/v1.4_7.2>" --check   # compare

The packaged DOE Ref recipes were built from the frozen definitions (release 1.0.0
values); release 1.1.0 reconciled the DOE Ref programs with the DOE v1.4_7.2 files
(ADR 0037), so they are rebuilt here from the release itself:
- programs, schedules and shared services of `data/atlas-releases/v2.0.0/commercial/
  doe-ref-*/<folder>/`, source records under their release IDs. The release fills of
  the generated types set only zero loads and unconditioned attics and plenums, which
  carry no slot, so no filled recipe is written;
- People topology for inferring hours of operation from the DOE file zones (Chicago 5A
  IDF, checked against the reconciliation register): each zone maps to its release
  program by name, as the reconciliation compared them (openstudio-standards geometry
  space names, aliases, the zones moved to programs of their own), and contributes
  zone floor area x the program's occupancy density on the program's occupancy
  schedule, in zone-name order; the dominant group follows openstudio-standards
  (residential space types by name, design people x zone multiplier);
- one commercial recipe per source program of the 15 sampled types, one composition
  recipe per department or general mix, the shared hot-water services with one
  configuration each, and the Midrise Apartment programs as a ResStock apartment unit
  (the apartments, through scripts/build_apartment_units.py) or fixed source rule sets
  (office, corridor);
- the schedules the recipes use, added to `atlas_schedules/data/schedules.json` under
  their release IDs (days expanded into rules); entries only the replaced recipes used
  are removed.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from atlas_schedules.commercial.profiles import round_half_up, stored_value
from scripts import idf_reader
from scripts.build_apartment_units import unit_recipe
from scripts.recipe_shapes import (LOAD_SLOTS, SAMPLING, SETPOINTS, TEMPLATES, WATER_CONTROLS, WATER_FRACTIONS,
                                   _known_positive, _load, _residential, heat_fractions, programme_recipe)
from scripts.common import ROOT, load_json
from scripts.reconciliation_register import NEW_PROGRAMS
from scripts.reference_extras import zone_floors
from scripts.reference_loads import ALIASES, TYPES, VINTAGES

RELEASE = ROOT/'data/atlas-releases/v2.0.0'
DATA = ROOT/'atlas_schedules/data'
REGISTER = ROOT/'data/reconciliation/doe-reference-v1.json'
GEOMETRY = ROOT/'data/construction-inputs/geometry-v1.json'
APARTMENT = 'MidriseApartment'
VIEW = 'source'


class Space:
    """A DOE zone in the shape `_residential` reads."""
    def __init__(self, space_type):
        self.space_type = space_type


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


def occupancy_carrier(zones):
    """(people [(schedule id, design people)] of the dominant group, residential dominant?)."""
    groups, totals = {True: [], False: []}, {True: 0.0, False: 0.0}
    for _, multiplier, floor, programs in zones:
        for program, share in programs:
            occupancy = _load(program, 'occupancy')
            if not _known_positive(occupancy):
                continue
            count = floor*share*occupancy['value']
            residential = _residential(Space(program['name'].rsplit('_', 1)[0]))
            groups[residential].append([occupancy['schedule_id'], count])
            totals[residential] += count*multiplier
    dominant = totals[True] > totals[False]
    return groups[dominant], dominant


def adapted(record):
    """A release source record in the shape `programme_recipe` reads (descriptive text in the thermal effects of
    water loads is not a fraction)."""
    loads = [{**l, 'thermal_effects': {k: v for k, v in (l.get('thermal_effects') or {}).items() if isinstance(v, dict)}}
             for l in record['loads']]
    return {**record, 'loads': loads, 'evidence_view': record['mode']}


def commercial_recipes(template, building_type, programs, people, invert):
    configuration = f'{SAMPLING[building_type]}__{TEMPLATES[template][0]}__{VIEW}'
    recipes = []
    for path, record in programs.values():
        if record['derivation'] == 'composed':
            members = [[m['program_id'], m['represented_area_m2']] for m in record['composition']['members']]
            recipes.append({
                'schema_version': '2.0.0', 'program_id': record['id'], 'name': record['name'], 'kind': 'composition',
                'source': {'family': record['source_family'], 'building_type': building_type, 'template': template,
                           'view': record['mode'], 'definition': path},
                'slots': [], 'demands': [], 'controls': [], 'companions': {}, 'required_services': [],
                'composition': {'composition_id': record['id'], 'members': members}})
        else:
            recipe = programme_recipe(adapted(record), people, configuration, SAMPLING[building_type], invert, path)
            recipes.append(recipe)
    record = {'configuration_id': configuration, 'building_type': SAMPLING[building_type], 'people': people,
              'invert_rule_days': invert}
    return recipes, record


def water_fractions(effects):
    """Sensible and latent fractions of a water draw: the release's, else openstudio-standards' constants."""
    return {slot: (effects.get(key) or {}).get('value', default)
            for (slot, default), key in zip(WATER_FRACTIONS.items(), ('sensible_fraction', 'latent_fraction'))}


def water_services(services, configuration):
    out = []
    for service in services.values():
        load = service['load']
        if load['quantity'] != 'hot_water_volume' or not load['value'] or not isinstance(load['schedule_id'], str):
            continue
        effects = load.get('thermal_effects') or {}
        companions = {'water_target_temperature': {'method': 'constant',
                                                   'value': round_half_up(stored_value(load['target_temperature_degC']), 5)},
                      **{slot: {'method': 'constant', 'value': value} for slot, value in water_fractions(effects).items()}}
        out.append({
            'schema_version': '2.0.0', 'service_id': service['id'], 'kind': 'physical_service',
            'source': {'definition': f"data/atlas-releases/v2.0.0/commercial/{service['template'].lower().replace(' ', '-')}/"
                                     f"{TYPE_FOLDERS[service['building_type']]}/services.json#{service['id']}"},
            'demand': {'quantity': load['quantity'], 'unit': load['unit'], 'value': load['value'], 'basis': load['basis'],
                       'fuel': 'water', 'host': 'building_service'},
            'controls': WATER_CONTROLS,
            'configurations': {configuration: {'schedule': load['schedule_id'], 'companions': companions}}})
    return out


TYPE_FOLDERS = {**{bt: folder for bt, folder in TYPES.values()}, APARTMENT: 'midrise-apartment'}


def apartment_recipes(template, programs, services):
    """The DOE Midrise Apartment programs: apartments as an apartment unit, the others as fixed source rule sets."""
    recipes = []
    for path, record in programs.values():
        slots, demands, controls, companions = [], [], [], {}
        occupancy = _load(record, 'occupancy')
        if _known_positive(occupancy):
            slots.append({'slot': 'occupants', 'kind': 'control', 'unit': 'fraction', 'schedule': occupancy['schedule_id']})
            controls.append({'slot': 'occupants', 'quantity': 'occupancy_fraction', 'unit': 'fraction',
                             'people': {'basis': 'floor_area', 'density': occupancy['value'], 'unit': 'person/m2'}})
        for quantity, slot in (('lighting', 'lighting_interior'), ('electric_equipment', 'electric_equipment')):
            load = _load(record, quantity)
            if _known_positive(load):
                slots.append({'slot': slot, 'kind': 'load', 'unit': 'fraction', 'schedule': load['schedule_id']})
                demands.append({'slot': slot, 'quantity': quantity, 'unit': load['unit'], 'value': load['value'],
                                'basis': load['basis'], 'fuel': LOAD_SLOTS[quantity], 'host': 'assigned_zone',
                                'heat_fractions': heat_fractions(adapted(record)['loads'][record['loads'].index(load)])})
        parameters = record['parameters']
        activity = parameters.get('activity_schedule_id') or {}
        named = [('activity', activity)] if _known_positive(occupancy) and activity.get('status') == 'known' else []
        named += [(slot, parameters.get(key) or {}) for slot, key in SETPOINTS]
        for slot, parameter in named:
            if parameter.get('status') != 'known':
                continue
            unit = 'W/person' if slot == 'activity' else 'C'
            slots.append({'slot': slot, 'kind': 'control', 'unit': unit, 'schedule': parameter['value']})
            controls.append({'slot': slot, 'quantity': 'activity' if slot == 'activity' else 'temperature', 'unit': unit})
            companions[slot] = {'method': 'source_rules', 'schedule': parameter['value']}
        recipe = {'schema_version': '2.0.0', 'program_id': record['id'], 'name': record['name'],
                  'kind': 'apartment_unit' if record['name'] == f'Apartment_{APARTMENT}' else 'fixed',
                  'source': {'family': record['source_family'], 'building_type': APARTMENT, 'template': template,
                             'view': record['mode'], 'climate': record['climate'], 'vintage': None,
                             'source_id': record.get('source_id'), 'definition': path},
                  'slots': slots, 'demands': demands, 'controls': controls, 'companions': companions,
                  'required_services': []}
        water = _load(record, 'hot_water_volume')
        if recipe['kind'] == 'apartment_unit':
            recipe['unit_timing'] = {'additional_lighting': 'lighting_interior', 'lighting_interior': 'lighting_interior',
                                     'occupants': 'occupants'}
            if _known_positive(water):
                service = services[water['service_id']]
                fractions = water_fractions(service['load']['thermal_effects'])
                index = record['loads'].index(water)
                recipe['caller_water'] = {
                    'service_id': water['service_id'], 'density': water['value'], 'density_unit': water['unit'],
                    'schedule': water['schedule_id'],
                    'controls': {'water_target_temperature': ['temperature', 'C', service['load']['target_temperature_degC']],
                                 'water_sensible_fraction': ['sensible_fraction', 'fraction', fractions['water_sensible_fraction']],
                                 'water_latent_fraction': ['latent_fraction', 'fraction', fractions['water_latent_fraction']]},
                    'source': {'demand': f'{path}#/loads/{index}',
                               'service': f"{path.split('/programs/')[0]}/services.json#{water['service_id']}"}}
        elif _known_positive(water):
            raise ValueError(f"{record['id']}: hot water outside an apartment has no fixed-recipe form")
        recipes.append(recipe)
    return recipes


def build(idf_root):
    """(recipes, configurations, services, {schedule id: rules}) of every DOE Ref folder with a generator kind."""
    register = load_json(REGISTER)
    geometry = {(e['template'], e['building_type']): e for e in load_json(GEOMETRY)['commercial']}
    recipes, configurations, services, schedules = [], [], [], {}
    for vintage, (folder_template, _, template) in VINTAGES.items():
        for key, (building_type, folder) in [*TYPES.items(), (None, (APARTMENT, 'midrise-apartment'))]:
            programs, table, folder_services = read_folder(folder_template, folder)
            for schedule_id, schedule in table['schedules'].items():
                schedules[schedule_id] = {'rules': [{'day_types': r['day_types'], 'start_date': r['start_date'],
                                                     'end_date': r['end_date'], 'values': table['days'][r['day']]}
                                                    for r in schedule['rules']]}
            if building_type == APARTMENT:
                # Apartments are ResStock units (scripts/build_apartment_units.py, plan section 8, B7).
                recipes += [unit_recipe(r, release_folder(folder_template, folder), r['program_id'], VIEW,
                                        geometry[(template, APARTMENT)]) if r['kind'] == 'apartment_unit' else r
                            for r in apartment_recipes(template, programs, folder_services)]
                continue
            path = next((Path(idf_root)/f'refbldg_{key}_{vintage}_v1-4_7-2').glob('*5A_USA_IL_CHICAGO-OHARE.idf'))
            if register['input_sha256'][path.name] != sha256(path):
                raise ValueError('IDF differs from the reconciliation register input: '+path.name)
            by_name = {r['name']: r for _, r in programs.values() if r['derivation'] != 'composed'}
            zones = zone_programs(idf_reader.Model(path), building_type, geometry[(template, building_type)], by_name)
            people, invert = occupancy_carrier(zones)
            built, configuration = commercial_recipes(template, building_type, programs, people, invert)
            recipes += built
            configurations.append(configuration)
            services += water_services(folder_services, configuration['configuration_id'])
    return recipes, configurations, services, schedules


def packaged_files(recipes, configurations, services):
    """{path under atlas_schedules/data: JSON text} in the packaged layout (people in the configuration)."""
    files = {}
    for record in configurations:
        files[f"configurations/{record['configuration_id']}.json"] = record
    for recipe in recipes:
        spec = recipe.get('commercial')
        if spec:
            recipe = {**recipe, 'commercial': {'configuration_id': spec['configuration_id'], 'modes': spec['modes']}}
        files[f"recipes/{recipe['program_id']}.json"] = recipe
    for record in services:
        files[f"services/{record['service_id']}.json"] = record
    return {p: json.dumps(v, indent=1, sort_keys=True)+'\n' for p, v in files.items()}


def replaced():
    """Packaged files of the DOE Ref templates: recipes, their configurations and services."""
    out = []
    for path in sorted((DATA/'recipes').glob('*.json')):
        if (load_json(path)['source'].get('template') or '').startswith('DOE Ref'):
            out.append(path)
    out += sorted(p for p in (DATA/'configurations').glob('*__doe_ref_*.json'))
    for path in sorted((DATA/'services').glob('*.json')):
        if any('__doe_ref_' in k for k in load_json(path)['configurations']):
            out.append(path)
    return out


def references(value, table):
    found = set()
    if isinstance(value, str):
        if value in table:
            found.add(value)
    elif isinstance(value, dict):
        for item in value.values():
            found |= references(item, table)
    elif isinstance(value, list):
        for item in value:
            found |= references(item, table)
    return found


def write(idf_root):
    recipes, configurations, services, schedules = build(idf_root)
    files = packaged_files(recipes, configurations, services)
    table_path = DATA/'schedules.json'
    table = load_json(table_path)
    old = replaced()
    kept_refs = set()
    for folder in ('recipes', 'configurations', 'services'):
        for path in (DATA/folder).glob('*.json'):
            if path not in old:
                kept_refs |= references(load_json(path), table)
    old_refs = set().union(*(references(load_json(p), table) for p in old))
    for path in old:
        path.unlink()
    used = set().union(*(references(json.loads(text), schedules) for text in files.values()))
    for schedule_id in old_refs - kept_refs - used:
        table.pop(schedule_id, None)
    for schedule_id in sorted(used):
        table[schedule_id] = schedules[schedule_id]
    for relative, text in files.items():
        (DATA/relative).write_bytes(text.encode('utf-8'))
    table_path.write_bytes((json.dumps(table, separators=(',', ':'), sort_keys=True)+'\n').encode('utf-8'))
    counts = defaultdict(int)
    for recipe in recipes:
        counts[recipe['kind']] += 1
    print(f'Replaced {len(old)} packaged files; wrote {dict(counts)} recipes, {len(configurations)} configurations, '
          f'{len(services)} services, {len(used)} schedules ({len(old_refs - kept_refs - used)} unused removed)')


def check(idf_root):
    recipes, configurations, services, schedules = build(idf_root)
    files = packaged_files(recipes, configurations, services)
    differ = [p for p, text in files.items() if not (DATA/p).is_file() or (DATA/p).read_text(encoding='utf-8') != text]
    table = load_json(DATA/'schedules.json')
    used = set().union(*(references(json.loads(text), schedules) for text in files.values()))
    differ += [f'schedules.json#{s}' for s in sorted(used) if table.get(s) != schedules[s]]
    stale = [p.relative_to(DATA).as_posix() for p in replaced() if p.relative_to(DATA).as_posix() not in files]
    if differ or stale:
        raise SystemExit(f'{len(differ)} packaged files differ, {len(stale)} not rebuilt, e.g. {(differ + stale)[:5]}')
    print(f'DOE Ref recipes reproduce: {len(files)} files, {len(used)} schedules')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--idf-root', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    (check if args.check else write)(args.idf_root)


if __name__ == '__main__':
    main()
