"""Test whether the atlas 90.1 templates equal the PNNL prototypes in geometry and construction.

python -m scripts.prototype_equivalence --prototype-root <extracted pnnl-prototypes/commercial-ashrae901>
    [--standards-raw <cache of the pinned openstudio-standards files>]
    [--editions 2007 2013 2019] [--out build/reconciliation/prototype-equivalence.json]

For each edition (atlas template 90-1-<edition>) and each of the 16 prototype types:
- geometry: every prototype zone against the source geometry the atlas recovered
  (data/construction-inputs/geometry-v1.json, from the pinned openstudio-standards
  geometry files): zone set, multiplier, floor area, height range and exterior
  wall and roof areas;
- fenestration: window-to-wall ratio per orientation and skylight-to-roof ratio,
  against the windows of the same openstudio-standards geometry file;
- construction, for each of the 19 prototype climates against the atlas context of
  the IDF's AnalysisClimateZone: layer resistance of the dominant exterior wall, roof
  and exposed-floor constructions, U-factor and SHGC of the dominant window and
  skylight glazing, and the ground-floor F-factor;
- infiltration: the prototype method and rate next to the atlas method;
- internal mass: area per floor area, prototype against the atlas inventory.
Values agree within TOLERANCE (relative). Loads and schedules are not compared:
by decision they are recorded as evidence only.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from scripts import idf_reader
from scripts.common import ROOT

TOLERANCE = 0.01
TYPES = {'ApartmentHighRise': ('HighriseApartment', 'highrise-apartment'),
         'ApartmentMidRise': ('MidriseApartment', 'midrise-apartment'),
         'Hospital': ('Hospital', 'hospital'), 'HotelLarge': ('LargeHotel', 'large-hotel'),
         'HotelSmall': ('SmallHotel', 'small-hotel'), 'OfficeLarge': ('LargeOffice', 'large-office'),
         'OfficeMedium': ('MediumOffice', 'medium-office'), 'OfficeSmall': ('SmallOffice', 'small-office'),
         'OutPatientHealthCare': ('Outpatient', 'outpatient'),
         'RestaurantFastFood': ('QuickServiceRestaurant', 'quick-service-restaurant'),
         'RestaurantSitDown': ('FullServiceRestaurant', 'full-service-restaurant'),
         'RetailStandalone': ('RetailStandalone', 'retail-standalone'),
         'RetailStripmall': ('RetailStripmall', 'retail-stripmall'),
         'SchoolPrimary': ('PrimarySchool', 'primary-school'), 'SchoolSecondary': ('SecondarySchool', 'secondary-school'),
         'Warehouse': ('Warehouse', 'warehouse')}


def agree(a, b):
    if a is None or b is None:
        return None
    if a == b == 0:
        return True
    return abs(a - b) / max(abs(a), abs(b)) <= TOLERANCE


def ratio(window, wall):
    return round(window / wall, 4) if wall > 0.01 else None


# ------------------------------------------------------------------ geometry side
def osm_windows(path):
    """Window-to-wall ratio per orientation and skylight-to-roof ratio of an OSM geometry file."""
    objects = idf_reader.parse(path.read_text(errors='replace'))
    building = next((f for k, f in objects if k == 'os:building'), None)
    north = idf_reader.number(building[3], 0.0) if building else 0.0
    spaces = {f[0]: tuple(idf_reader.number(v, 0.0) for v in f[6:9]) for k, f in objects if k == 'os:space'}
    zones = {f[0]: idf_reader.number(f[2], 1) or 1 for k, f in objects if k == 'os:thermalzone'}
    space_zone = {f[0]: f[10] for k, f in objects if k == 'os:space'}
    walls, windows, roof, sky = defaultdict(float), defaultdict(float), 0.0, 0.0
    surfaces = {}
    for k, f in objects:
        if k != 'os:surface':
            continue
        ox, oy, oz = spaces.get(f[4], (0, 0, 0))
        points = [(x + ox, y + oy, z + oz) for x, y, z in idf_reader.vertices(f, 11)]
        multiplier = zones.get(space_zone.get(f[4]), 1)
        surfaces[f[0]] = (f[2].lower(), points, multiplier, f[4])
        if f[5].lower() == 'outdoors' and f[2].lower() == 'wall':
            walls[idf_reader.orientation(points, north)] += idf_reader.area(points) * multiplier
        if f[5].lower() == 'outdoors' and f[2].lower() == 'roofceiling':
            roof += idf_reader.area(points) * multiplier
    for k, f in objects:
        if k != 'os:subsurface' or f[2].lower() not in ('fixedwindow', 'operablewindow', 'skylight', 'glassdoor'):
            continue
        host = surfaces.get(f[4])
        if not host:
            continue
        kind, host_points, multiplier, space = host
        ox, oy, oz = spaces.get(space, (0, 0, 0))
        points = [(x + ox, y + oy, z + oz) for x, y, z in idf_reader.vertices(f, 11)]
        a = idf_reader.area(points) * (idf_reader.number(f[9], 1) or 1) * multiplier
        if kind == 'wall':
            windows[idf_reader.orientation(host_points, north)] += a
        else:
            sky += a
    return {'wwr': {o: ratio(windows[o], walls[o]) for o in idf_reader.ORIENTATIONS},
            'wwr_total': ratio(sum(windows.values()), sum(walls.values())), 'srr': ratio(sky, roof)}


def prototype_windows(model):
    walls, windows, roof, sky = defaultdict(float), defaultdict(float), 0.0, 0.0
    for s in model.surfaces():
        m = model.zones[s['zone'].lower()]['multiplier']
        if s['boundary'] == 'outdoors' and s['type'] == 'wall':
            walls[idf_reader.orientation(s['vertices'], model.north_axis)] += idf_reader.area(s['vertices']) * m
        if s['boundary'] == 'outdoors' and s['type'] == 'roof':
            roof += idf_reader.area(s['vertices']) * m
    hosts = {s['name'].lower(): s for s in model.surfaces()}
    for w in model.fenestration():
        if w['type'] not in ('window', 'glassdoor'):
            continue
        host = hosts.get(w['host'].lower())
        m = model.zones[host['zone'].lower()]['multiplier']
        a = idf_reader.area(w['vertices']) * w['multiplier'] * m
        if host['type'] == 'wall':
            windows[idf_reader.orientation(host['vertices'], model.north_axis)] += a
        else:
            sky += a
    return {'wwr': {o: ratio(windows[o], walls[o]) for o in idf_reader.ORIENTATIONS},
            'wwr_total': ratio(sum(windows.values()), sum(walls.values())), 'srr': ratio(sky, roof)}


def zone_geometry(model):
    zones = {k: {'floor_m2': 0.0, 'wall_m2': 0.0, 'roof_m2': 0.0, 'z': [float('inf'), float('-inf')],
                 'multiplier': z['multiplier']} for k, z in model.zones.items()}
    for s in model.surfaces():
        z = zones[s['zone'].lower()]
        a = idf_reader.area(s['vertices'])
        zs = [p[2] for p in s['vertices']]
        z['z'] = [min(z['z'][0], *zs), max(z['z'][1], *zs)]
        if s['type'] == 'floor':
            z['floor_m2'] += a
        if s['boundary'] == 'outdoors' and s['type'] == 'wall':
            z['wall_m2'] += a
        if s['boundary'] == 'outdoors' and s['type'] == 'roof':
            z['roof_m2'] += a
    return zones


def prototype_totals(model):
    zones = zone_geometry(model)
    totals = defaultdict(float)
    for key, z in zones.items():
        unconditioned = any(w in key for w in ('plenum', 'attic'))
        if not unconditioned:
            totals['conditioned_floor_m2'] += z['floor_m2'] * z['multiplier']
        totals['exterior_wall_m2'] += z['wall_m2'] * z['multiplier']
        totals['exterior_roof_m2'] += z['roof_m2'] * z['multiplier']
    return dict(totals)


def atlas_totals(entry):
    totals = defaultdict(float)
    for s in entry['spaces']:
        unconditioned = any(w in s['name'].lower() for w in ('plenum', 'attic'))
        if not unconditioned:
            totals['conditioned_floor_m2'] += s['floor_area_m2'] * s['multiplier']
        totals['exterior_wall_m2'] += s['outdoor_wall_area_m2'] * s['multiplier']
        totals['exterior_roof_m2'] += s['outdoor_roof_area_m2'] * s['multiplier']
    return dict(totals)


def compare_geometry(model, entry):
    """Building totals decide; zone-level differences are listed as representation detail."""
    zones = zone_geometry(model)
    spaces = {s['name'].lower(): s for s in entry['spaces']}
    p, a = prototype_totals(model), atlas_totals(entry)
    totals = {k: {'prototype': round(p.get(k, 0.0), 2), 'atlas': round(a.get(k, 0.0), 2), 'equal': agree(p.get(k, 0.0), a.get(k, 0.0))}
              for k in sorted(set(p) | set(a))}
    zone_differences = []
    for name in sorted(set(zones) & set(spaces)):
        z, s = zones[name], spaces[name]
        if any(w in name for w in ('plenum', 'attic')):
            continue  # prototypes leave plenum floors to one-sided "Zone" boundaries
        pairs = {'multiplier': (z['multiplier'], s['multiplier']), 'floor_m2': (z['floor_m2'], s['floor_area_m2']),
                 'height_m': (z['z'][1] - z['z'][0], s['z_max_m'] - s['z_min_m'])}
        for field, (x, y) in pairs.items():
            if not agree(float(x), float(y)):
                zone_differences.append({'zone': name, 'field': field, 'prototype': round(x, 4), 'atlas': round(y, 4)})
    return {'totals': totals, 'equal': all(t['equal'] for t in totals.values()),
            'prototype_zones': len(zones), 'atlas_spaces': len(spaces),
            'only_prototype': sorted(set(zones) - set(spaces)), 'only_atlas': sorted(set(spaces) - set(zones)),
            'zone_differences': zone_differences}


# -------------------------------------------------------------- construction side
def dominant(items):
    return max(items.items(), key=lambda kv: kv[1])[0] if items else None


def prototype_constructions(model):
    """Dominant construction values per component role."""
    constructions, materials = model.constructions(), model.materials()
    areas = defaultdict(lambda: defaultdict(float))
    for s in model.surfaces():
        a = idf_reader.area(s['vertices']) * model.zones[s['zone'].lower()]['multiplier']
        role = {('wall', 'outdoors'): 'ExteriorWall', ('roof', 'outdoors'): 'ExteriorRoof',
                ('floor', 'outdoors'): 'ExteriorFloor', ('floor', 'ground'): 'GroundFloor',
                ('floor', 'groundfcfactormethod'): 'GroundFloor'}.get((s['type'], s['boundary']))
        if role:
            areas[role][s['construction'].lower()] += a
    for w in model.fenestration():
        role = {'window': 'ExteriorWindow' if w['host_type'] == 'wall' else 'Skylight',
                'glassdoor': 'GlassDoor', 'door': 'ExteriorDoor'}.get(w['type'])
        if role:
            areas[role][w['construction'].lower()] += idf_reader.area(w['vertices']) * w['multiplier']
    result = {}
    for role, by_construction in areas.items():
        total = sum(by_construction.values())
        variants = []
        for name, a in sorted(by_construction.items(), key=lambda kv: -kv[1]):
            item = constructions.get(name, {})
            value = {'construction': name, 'share': round(a / total, 3)}
            if item.get('kind') == 'ffactor':
                value['f_factor'] = item['f_factor']
            elif item.get('kind') == 'layers':
                glazing = [materials.get(layer) for layer in item['layers']]
                if len(glazing) == 1 and glazing[0] and glazing[0]['kind'] == 'simple_glazing':
                    value.update(u_factor=glazing[0]['u_factor'], shgc=glazing[0]['shgc'])
                else:
                    value['layer_resistance'] = model.layer_resistance(name)
            variants.append(value)
        result[role] = variants
    return result


def atlas_constructions(document):
    result = {}
    for role in ('ExteriorWall', 'ExteriorRoof', 'ExteriorFloor', 'GroundFloor', 'ExteriorWindow', 'Skylight',
                 'ExteriorDoor', 'GlassDoor'):
        component = document['components'].get(role, {})
        assignments = [a for a in component.get('assignments', []) if a.get('when', {}).get('scope') == 'building_default']
        fixed = [a for a in assignments if a.get('when', {}).get('window_operation') in (None, 'fixed')]
        if not (fixed or assignments):
            continue
        assembly = document['assemblies'][(fixed or assignments)[0]['assembly_id']]
        value = {'assembly': assembly['id']}
        if 'f_W_m_K' in assembly:
            value['f_factor'] = assembly['f_W_m_K']
        elif assembly.get('model') == 'simple_glazing':
            props = document['materials'][assembly['layers'][0]['material_id']]['properties']
            value.update(u_factor=props.get('u_W_m2_K'), shgc=props.get('shgc'))
        else:
            value['layer_resistance'] = assembly.get('metrics', {}).get('layer_resistance_m2_K_W')
        result[role] = value
    return result


def compare_constructions(prototype, atlas):
    """Each prototype construction variant of a role against the atlas building default."""
    result = {}
    for role, variants in prototype.items():
        a = atlas.get(role)
        if a is None:
            result[role] = {'prototype': variants, 'atlas': None, 'equal': None}
            continue
        fields = [f for f in ('layer_resistance', 'u_factor', 'shgc', 'f_factor') if f in a]
        checks = [all(agree(v.get(f), a.get(f)) for f in fields) for v in variants]
        result[role] = {'prototype': variants, 'atlas': a, 'equal': all(checks),
                        'equal_area_share': round(sum(v['share'] for v, ok in zip(variants, checks) if ok), 3)}
    return result


def compare_mass(model, document):
    """Internal-mass area per counted floor area, in counted (occupied) and uncounted (plenum, attic) spaces."""
    zones = zone_geometry(model)
    counted_floor = sum(z['floor_m2'] * z['multiplier'] for k, z in zones.items()
                        if not any(w in k for w in ('plenum', 'attic')))
    prototype = {'counted': 0.0, 'uncounted': 0.0}
    for m in model.internal_mass():
        for zone in m['zones']:
            side = 'uncounted' if any(w in zone for w in ('plenum', 'attic')) else 'counted'
            prototype[side] += (m['area'] or 0.0) * zones[zone]['multiplier'] / len(m['zones'])
    prototype = {k: round(v / counted_floor, 4) for k, v in prototype.items()}
    atlas = {'counted': 0.0, 'uncounted': 0.0}
    for entry in document['mass_accounting']['additional_mass'].get('entries', []):
        atlas['counted' if entry['scope'].get('counted_floor_area') else 'uncounted'] += entry['area_per_counted_floor_area']
    atlas = {k: round(v, 4) for k, v in atlas.items()}
    return {'prototype': prototype, 'atlas': atlas, 'counted_equal': agree(prototype['counted'], atlas['counted']),
            'uncounted_equal': agree(prototype['uncounted'], atlas['uncounted'])}


def context_key(climate):
    return f'{climate[0]}-{(climate[1:] or "a").lower()}'


def main():
    from scripts.atlas_exports import Release
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prototype-root', type=Path, required=True)
    parser.add_argument('--standards-raw', type=Path, default=ROOT/'data/raw/openstudio-standards',
                        help='the scripts.fetch cache of the pinned openstudio-standards files')
    parser.add_argument('--editions', nargs='+', default=['2007', '2013', '2019'])
    parser.add_argument('--out', type=Path, default=ROOT/'build/reconciliation/prototype-equivalence.json')
    args = parser.parse_args()
    geometry = {(e['template'], e['building_type']): e
                for e in json.loads((ROOT/'data/construction-inputs/geometry-v1.json').read_text())['commercial']}
    release = Release()
    sets = {}
    for path in (ROOT/'data/atlas-releases/v1.0.0/commercial').glob('*/*/constructions/*.json'):
        sets[(path.parts[-4], path.parts[-3])] = json.loads(path.read_text(encoding='utf-8'))['id']
    result = {}
    for edition in args.editions:
        template = f'90-1-{edition}'
        for pnnl, (building_type, folder) in TYPES.items():
            files = sorted((args.prototype_root/f'ASHRAE901_{pnnl}').glob(f'ASHRAE901_{pnnl}_STD{edition}_*.idf'))
            entry = geometry[(f'90.1-{edition}', building_type)]
            record = {'geometry_file': entry['geometry_file']}
            reference = idf_reader.Model(next(f for f in files if f.stem.endswith('_Denver')))
            record['geometry'] = compare_geometry(reference, entry)
            osm = osm_windows(args.standards_raw/entry['geometry_file'])
            record['fenestration'] = {'prototype': prototype_windows(reference), 'atlas_source_geometry': osm}
            climates = {}
            for f in files:
                model = idf_reader.Model(f)
                climate = re.search(r'AnalysisClimateZone = (\w+)', f.read_text(errors='replace')).group(1)
                document = release.constructions.export(sets[(template, folder)], context_key(climate), 'detailed')
                climates[f.stem.rsplit('_', 1)[1]] = {
                    'climate': climate, 'srr': prototype_windows(model)['srr'],
                    'constructions': compare_constructions(prototype_constructions(model), atlas_constructions(document)),
                    'infiltration': {'prototype': sorted({(i['method'], i['values'][2] or i['values'][3] or i['values'][1])
                                                          for i in model.infiltration()}, key=str)[:6],
                                     'atlas': document['infiltration']['method']}}
            record['climates'] = climates
            record['internal_mass'] = compare_mass(reference, release.constructions.export(
                sets[(template, folder)], '5-b', 'detailed'))
            result[f'{template}/{folder}'] = record
            equal = sum(1 for c in climates.values() for v in c['constructions'].values() if v['equal'])
            total = sum(1 for c in climates.values() for v in c['constructions'].values() if v['equal'] is not None)
            bad = [k for k, t in record['geometry']['totals'].items() if not t['equal']]
            print(f"{template} {folder:24} geometry {'equal' if not bad else 'DIFFERS ' + ','.join(bad)} "
                  f"(zone diffs {len(record['geometry']['zone_differences'])}) WWR proto {record['fenestration']['prototype']['wwr_total']} "
                  f"src {osm['wwr_total']} constructions {equal}/{total}", flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1, default=str))


if __name__ == '__main__':
    main()
