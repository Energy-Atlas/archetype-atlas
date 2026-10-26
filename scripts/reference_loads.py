"""Compare DOE reference zone loads with the atlas release and openstudio-standards rows.

python -m scripts.reference_loads --idf-root <extracted doe-reference/v1.4_7.2> --standards-root <ashrae_90_1 dir>
    [--vintage post1980|pre1980] [--out build/reconciliation/loads-<vintage>.json]

Per conditioned zone of the 15 non-residential types (Chicago 5A file): occupancy
(person/m2), lighting, plug and gas (W/m2), the heat fractions, infiltration and
internal mass. A zone maps to its geometry-v1 spaces by name (aliases where the
names differ); a zone spanning several spaces is compared with their area-weighted
mean. Plug loads exclude elevator and exhaust-fan objects, which openstudio-standards
adds outside the space-type table. Matches: 'exact' (1e-3 relative), 'rounding'
(1e-2, the IDFs print SI values at 2-4 significant figures) or 'differ'.
"""
import argparse
import json
from pathlib import Path

from scripts import idf_reader
from scripts.common import ROOT

RELEASE = ROOT/'data/atlas-releases/v1.0.0/commercial'
EXACT, ROUNDING = 1e-3, 1e-2
FT2 = 0.09290304
BTUH = 0.29307107
NON_SPACE_TYPE_PLUG = {'elevators', 'kitchenexhfan', 'exhaustfans', 'laundryexhfan', 'zone exhaust fans'}
QUANTITIES = ('occupancy', 'lighting', 'electric_equipment', 'gas_equipment')
VINTAGES = {'post1980': ('doe-ref-1980-2004', 'doe_ref_1980_2004', 'DOE Ref 1980-2004'),
            'pre1980': ('doe-ref-pre-1980', 'doe_ref_pre_1980', 'DOE Ref Pre-1980')}
TYPES = {'fullservicerestaurant': ('FullServiceRestaurant', 'full-service-restaurant'),
         'hospital': ('Hospital', 'hospital'), 'largehotel': ('LargeHotel', 'large-hotel'),
         'largeoffice': ('LargeOffice', 'large-office'), 'mediumoffice': ('MediumOffice', 'medium-office'),
         'outpatient': ('Outpatient', 'outpatient'), 'primaryschool': ('PrimarySchool', 'primary-school'),
         'quickservicerestaurant': ('QuickServiceRestaurant', 'quick-service-restaurant'),
         'secondaryschool': ('SecondarySchool', 'secondary-school'), 'smallhotel': ('SmallHotel', 'small-hotel'),
         'smalloffice': ('SmallOffice', 'small-office'), 'stand-aloneretail': ('RetailStandalone', 'retail-standalone'),
         'stripmall': ('RetailStripmall', 'retail-stripmall'), 'supermarket': ('SuperMarket', 'super-market'),
         'warehouse': ('Warehouse', 'warehouse')}
ALIASES = {
    'Warehouse': {'BulkStorage': ['Zone3 Bulk Storage'], 'FineStorage': ['Zone2 Fine Storage'], 'Office': ['Zone1 Office']},
    'SuperMarket': {'DryStorage': ['Active Storage'], 'Office': ['Enclosed Office'],
                    'Sales': ['Main Sales', 'East Perimeter Sales', 'West Perimeter Sales', 'Corridor', 'Dining Room',
                              'Mechanical Room', 'Meeting Room', 'Restroom', 'Vestibule']},
}


def match(a, b):
    if a is None or b is None:
        return None
    if a == b == 0:
        return 'exact'
    relative = abs(a - b) / max(abs(a), abs(b))
    return 'exact' if relative <= EXACT else 'rounding' if relative <= ROUNDING else 'differ'


def zone_loads(model):
    """{zone (lower case): floor area, exterior areas and load densities} for one IDF."""
    zones = {k: {'name': z['name'], 'multiplier': z['multiplier'], 'floor_m2': 0.0, 'exterior_m2': 0.0,
                 'exterior_wall_m2': 0.0, 'loads': {q: 0.0 for q in QUANTITIES}, 'objects': [],
                 'unconditioned': any(w in k for w in ('plenum', 'attic'))}
             for k, z in model.zones.items()}
    for s in model.surfaces():
        z = zones[s['zone'].lower()]
        a = idf_reader.area(s['vertices'])
        if s['type'] == 'floor':
            z['floor_m2'] += a
        if s['boundary'] == 'outdoors' and s['type'] in ('wall', 'roof', 'ceiling'):
            z['exterior_m2'] += a
            if s['type'] == 'wall':
                z['exterior_wall_m2'] += a
    people = {}
    for item in model.loads('people'):
        for key in item['zones']:
            z = zones[key]
            number, per_area, area_per = item['values']
            value = {'people': (number or 0) / z['floor_m2'], 'people/area': per_area,
                     'area/person': 1 / area_per if area_per else None}[item['method']]
            people[key] = people.get(key, 0.0) + value
            z['objects'].append({'class': 'People', 'name': item['name'], 'value': value, 'schedule': item['schedule'],
                                 'fraction_radiant': item['fraction_radiant']})
    for key, value in people.items():
        zones[key]['loads']['occupancy'] = value
    for cls, quantity in (('lights', 'lighting'), ('electricequipment', 'electric_equipment'),
                          ('gasequipment', 'gas_equipment')):
        for item in model.loads(cls):
            for key in item['zones']:
                z = zones[key]
                level, per_area, per_person = item['values']
                value = {'lightinglevel': None, 'equipmentlevel': None, 'watts/area': per_area,
                         'watts/person': (per_person or 0) * people.get(key, 0.0)}.get(item['method'])
                if value is None:
                    value = (level or 0) / z['floor_m2']
                outside_table = cls == 'electricequipment' and item['subcategory'].lower() in NON_SPACE_TYPE_PLUG
                if not outside_table:
                    z['loads'][quantity] += value
                z['objects'].append({'class': cls, 'name': item['name'], 'value': value, 'schedule': item['schedule'],
                                     'fractions': item['fractions'], 'subcategory': item['subcategory'],
                                     'outside_space_type_table': outside_table})
    for item in model.infiltration():
        for key in item['zones']:
            zones[key].setdefault('infiltration', []).append(item)
    for item in model.internal_mass():
        for key in item['zones']:
            zones[key].setdefault('internal_mass', []).append(item)
    return zones


def standards_values(row):
    """openstudio-standards spc_typ row in SI: person/m2 and W/m2."""
    def si(key, factor):
        value = row.get(key)
        return None if value is None else value * factor
    lighting = si('lighting_per_area', 1 / FT2)
    extra = si('additional_lighting_per_area', 1 / FT2)
    return {'occupancy': si('occupancy_per_area', 1 / (1000 * FT2)),
            'lighting': None if lighting is None else lighting + (extra or 0.0),
            'electric_equipment': si('electric_equipment_per_area', 1 / FT2),
            'gas_equipment': si('gas_equipment_per_area', BTUH / FT2)}


def atlas_programs(template, folder):
    result = {}
    for path in (RELEASE/template/folder/'programs/source').glob('*.json'):
        program = json.loads(path.read_text(encoding='utf-8'))
        loads = {}
        for load in program['loads']:
            value, status = load['value'], load['status']
            if value is None and 'filling' in load:
                value, status = load['filling']['set'].get('value'), 'filled'
            loads[load['quantity']] = {'value': value, 'status': status}
        result[program['name']] = {'id': program['id'], 'loads': loads}
    return result


def weighted(values, weights):
    if all(v is None for v in values):
        return None
    return sum((v or 0.0) * w for v, w in zip(values, weights)) / sum(weights)


def compare_type(model, building_type, folder, template, standards, geometry):
    zones = zone_loads(model)
    spaces = {s['name'].lower().replace(' ', '_'): s for s in geometry['spaces']}
    programs = atlas_programs(template, folder)
    rows = []
    for key, z in zones.items():
        if z['unconditioned']:
            continue
        names = ALIASES.get(building_type, {}).get(z['name'], [z['name']])
        mapped = [spaces.get(n.lower().replace(' ', '_')) for n in names]
        row = {'zone': z['name'], 'floor_m2': round(z['floor_m2'], 3), 'idf': {q: round(v, 6) for q, v in z['loads'].items()},
               'objects': z['objects'], 'infiltration': z.get('infiltration', []), 'internal_mass': z.get('internal_mass', [])}
        if any(s is None for s in mapped):
            row['mapping'] = None
            rows.append(row)
            continue
        weights = [s['floor_area_m2'] * s['multiplier'] for s in mapped]
        space_types = [s['standards_space_type'] for s in mapped]
        row['mapping'] = {'space_types': sorted(set(space_types)), 'mixed': len(set(space_types)) > 1}
        std = [standards.get((s['standards_building_type'], s['standards_space_type'])) for s in mapped]
        atl = [programs.get(f"{s['standards_space_type']}_{building_type}") for s in mapped]
        refs = {}
        if all(std):
            values = [standards_values(r) for r in std]
            refs['standards'] = {q: weighted([v[q] for v in values], weights) for q in QUANTITIES}
        if all(atl):
            refs['atlas'] = {q: weighted([p['loads'].get(q, {}).get('value') for p in atl], weights) for q in QUANTITIES}
            refs['atlas_programs'] = sorted({p['id'] for p in atl})
        row['refs'] = refs
        row['match'] = {label: {q: match(z['loads'][q], refs[label][q]) for q in QUANTITIES}
                        for label in ('standards', 'atlas') if label in refs}
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--idf-root', type=Path, required=True)
    parser.add_argument('--standards-root', type=Path, required=True)
    parser.add_argument('--vintage', choices=sorted(VINTAGES), default='post1980')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    template, standards_template, geometry_template = VINTAGES[args.vintage]
    rows = json.loads((args.standards_root/standards_template/'data'/f'{standards_template}.spc_typ.json').read_text())
    standards = {(r['building_type'], r['space_type']): r for r in rows['space_types']}
    geometry = {(e['template'], e['building_type']): e
                for e in json.loads((ROOT/'data/construction-inputs/geometry-v1.json').read_text())['commercial']}
    result = {}
    for key, (building_type, folder) in TYPES.items():
        path = next((args.idf_root/f'refbldg_{key}_{args.vintage}_v1-4_7-2').glob('*5A_USA_IL_CHICAGO-OHARE.idf'))
        result[building_type] = compare_type(idf_reader.Model(path), building_type, folder, template, standards,
                                             geometry[(geometry_template, building_type)])
    totals = {q: {} for q in QUANTITIES}
    for rows_ in result.values():
        for row in rows_:
            for q in QUANTITIES:
                m = row.get('match', {}).get('atlas', {}).get(q)
                totals[q][str(m)] = totals[q].get(str(m), 0) + 1
    out = args.out or ROOT/f'build/reconciliation/loads-{args.vintage}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'vintage': args.vintage, 'template': template, 'types': result, 'totals': totals},
                              indent=1, default=str))
    for q, counts in totals.items():
        print(f'{q:20} {counts}')


if __name__ == '__main__':
    main()
