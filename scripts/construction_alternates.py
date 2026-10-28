"""Extract the PNNL prototype constructions that differ from the atlas 90.1 sets (plan stage B3, user decision P1).

python -m scripts.construction_alternates [--prototype-root DIR] [--check]

openstudio-standards stays the construction authority of the 90.1 templates (P1); where the PNNL
prototype of the same edition, type and climate builds a component differently by more than 1%,
its construction is recorded as an alternate. For the ASHRAE 90.1 2007, 2013 and 2019 prototypes
(16 types x 19 locations, pinned in sources/reference-models-lock.json) and each atlas context of
release 2.0.0 that the IDF's AnalysisClimateZone names:
- the prototype constructions of each role, by net area (zone multipliers applied): exterior wall,
  roof and floor, ground floor, window, skylight, door and glass door;
- the atlas building-default assembly of the role (the comparison of review S3,
  docs/reviews/prototype-equivalence-90-1.md): layer resistance without air films for opaque
  assemblies, U-factor and SHGC for simple glazing, F-factor for ground floors;
- where a prototype variant differs by more than 1% in any compared value from the building default of any set of
  the folder (90.1-2007 and 2013 small hotel hold a base set and an overlay), every variant of the role
  with its area share and its full source physics (layers and materials as written in the IDF), each
  assembly and material stored once in the input's tables.
Writes the committed input data/program-inputs/construction-alternates-v1.json, which
scripts.release_editor adds to the release without the IDFs. --check rebuilds and compares it.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from scripts import idf_reader
from scripts.common import ROOT, load_json
from scripts.iecc_commercial_values import encode
from scripts.iecc_commercial_zones import CITIES
from scripts.definition_contract import stable_id
from scripts.lighting_controls import Extract, prototype_root

OUTPUT = ROOT/'data/program-inputs/construction-alternates-v1.json'
FAMILY = 'commercial-ashrae901'
EDITIONS = ('2007', '2013', '2019')
TOLERANCE = 0.01
EXTRACTION_DATE = '2026-10-28'
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
SURFACE_ROLES = {('wall', 'outdoors'): 'ExteriorWall', ('roof', 'outdoors'): 'ExteriorRoof', ('floor', 'outdoors'): 'ExteriorFloor',
                 ('floor', 'ground'): 'GroundFloor', ('floor', 'groundfcfactormethod'): 'GroundFloor'}
ROLES = ('ExteriorWall', 'ExteriorRoof', 'ExteriorFloor', 'GroundFloor', 'ExteriorWindow', 'Skylight', 'ExteriorDoor', 'GlassDoor')


class Sources(Extract):
    """The pinned prototype files, and evidence rows in the construction-document shape."""

    def cite(self, source_file, locator, value, unit, transformation, note):
        source = self.source_files[source_file]
        row = {'source_project': source['project'], 'source_revision': source['version'],
               'source_locator': f"{source['archive_path']}!{source['path']}#{locator}", 'source_file_sha256': source['sha256'],
               'original_value': value, 'original_unit': unit, 'transformation': transformation,
               'extraction_date': EXTRACTION_DATE, 'interpretation_note': note}
        key = stable_id('construction-evidence', row)
        self.evidence[key] = {'id': key, **row}
        return key


def differs(a, b):
    if a is None or b is None:
        return False
    if a == b == 0:
        return False
    return abs(a - b) / max(abs(a), abs(b)) > TOLERANCE


def context_key(climate):
    return f'{climate[0]}-{(climate[1:] or "a").lower()}'


def material(model, name):
    """A material as the release libraries store it, from the IDF fields."""
    key = name.lower()
    for f in model.all('material'):
        if f[0].lower() == key:
            return {'model': 'StandardOpaqueMaterial', 'name': f[0], 'properties': {
                'roughness': f[1], 'thickness_m': float(f[2]), 'conductivity_W_m_K': float(f[3]), 'density_kg_m3': float(f[4]),
                'specific_heat_J_kg_K': float(f[5]), 'thermal_absorptance': float(f[6]) if len(f) > 6 and f[6] else 0.9,
                'solar_absorptance': float(f[7]) if len(f) > 7 and f[7] else 0.7,
                'visible_absorptance': float(f[8]) if len(f) > 8 and f[8] else 0.7}}
    for f in model.all('material:nomass'):
        if f[0].lower() == key:
            return {'model': 'MasslessOpaqueMaterial', 'name': f[0], 'properties': {
                'roughness': f[1], 'resistance_m2_K_W': float(f[2]),
                'thermal_absorptance': float(f[3]) if len(f) > 3 and f[3] else 0.9,
                'solar_absorptance': float(f[4]) if len(f) > 4 and f[4] else 0.7,
                'visible_absorptance': float(f[5]) if len(f) > 5 and f[5] else 0.7}}
    for f in model.all('windowmaterial:simpleglazingsystem'):
        if f[0].lower() == key:
            return {'model': 'SimpleGlazing', 'name': f[0], 'properties': {
                'u_W_m2_K': float(f[1]), 'shgc': float(f[2]), 'visible_transmittance': float(f[3]) if len(f) > 3 and f[3] else None}}
    raise ValueError(f'Unsupported or missing material {name} in {model.path.name}')


def assembly(model, name, role):
    """(assembly as the release libraries store it, {material name: material}, compared values) of one IDF construction."""
    found = model.constructions()[name.lower()]
    if found['kind'] == 'ffactor':
        return ({'model': 'FFactorGroundFloorConstruction', 'name': name, 'role': role, 'f_W_m_K': found['f_factor'],
                 'source_area_m2': found['area'], 'source_exposed_perimeter_m': found['perimeter'], 'status': 'ready'},
                {}, {'f_factor': found['f_factor']})
    if found['kind'] != 'layers':
        raise ValueError(f'Unsupported construction {name} ({found["kind"]}) in {model.path.name}')
    materials = {layer: material(model, layer) for layer in found['layers']}
    glazing = [m for m in materials.values() if m['model'] == 'SimpleGlazing']
    if glazing:
        if len(materials) != 1:
            raise ValueError(f'Simple glazing with other layers in {name} ({model.path.name})')
        props = glazing[0]['properties']
        values = {'u_factor': props['u_W_m2_K'], 'shgc': props['shgc']}
        record = {'model': 'simple_glazing', 'name': name, 'role': role}
    else:
        resistance = model.layer_resistance(name)
        values = {'layer_resistance': resistance}
        record = {'model': 'opaque_layers', 'name': name, 'role': role, 'layer_orientation': 'exterior_to_interior',
                  'metrics': {'layer_resistance_m2_K_W': resistance}}
    record['layers'] = [{'material': layer, 'order': i} for i, layer in enumerate(found['layers'])]
    return record, materials, values


def intern(table, record):
    """The key of a record stored once in a table of the input, keyed by its content."""
    key = stable_id('record', record)
    table.setdefault(key, record)
    return key


def prototype_roles(model):
    """{role: {construction: net area m2}} with zone and window multipliers."""
    areas = defaultdict(lambda: defaultdict(float))
    for s in model.surfaces():
        role = SURFACE_ROLES.get((s['type'], s['boundary']))
        if role:
            areas[role][s['construction']] += idf_reader.area(s['vertices'])*model.zones[s['zone'].lower()]['multiplier']
    for w in model.fenestration():
        role = {'window': 'ExteriorWindow' if w['host_type'] == 'wall' else 'Skylight', 'glassdoor': 'GlassDoor',
                'door': 'ExteriorDoor'}.get(w['type'])
        if role:
            zone = model.zones.get((w['zone'] or '').lower(), {'multiplier': 1})
            areas[role][w['construction']] += idf_reader.area(w['vertices'])*w['multiplier']*zone['multiplier']
    return areas


def atlas_values(document, role):
    """The compared values of the atlas building-default assembly of a role, or None."""
    component = document['components'].get(role, {})
    assignments = [a for a in component.get('assignments', []) if a.get('when', {}).get('scope') == 'building_default']
    fixed = [a for a in assignments if a.get('when', {}).get('window_operation') in (None, 'fixed')]
    if not (fixed or assignments):
        return None
    record = document['assemblies'][(fixed or assignments)[0]['assembly_id']]
    if 'f_W_m_K' in record:
        return {'assembly_id': record['id'], 'f_factor': record['f_W_m_K']}
    if record.get('model') == 'simple_glazing':
        props = document['materials'][record['layers'][0]['material_id']]['properties']
        return {'assembly_id': record['id'], 'u_factor': props.get('u_W_m2_K'), 'shgc': props.get('shgc')}
    return {'assembly_id': record['id'], 'layer_resistance': record.get('metrics', {}).get('layer_resistance_m2_K_W')}


def build(root=None):
    from scripts.atlas_exports import Release
    release = Release()
    root = Path(root or prototype_root())
    extract = Sources(root)
    sets = defaultdict(list)  # two folders hold a base set and an overlay that inherits from it
    for sid in sorted(release.constructions.sets):
        folder = sid.split('.')
        if folder[0].startswith('90-1-'):
            sets[(folder[0], folder[1])].append(sid)
    out = defaultdict(lambda: defaultdict(dict))
    library = {'assemblies': {}, 'materials': {}}
    for edition in EDITIONS:
        template = f'90-1-{edition}'
        for pnnl, (_, folder) in TYPES.items():
            sids = sets[(template, folder)]
            for city in CITIES:
                path = root/FAMILY/f'ASHRAE901_{pnnl}'/f'ASHRAE901_{pnnl}_STD{edition}_{city}.idf'
                text = path.read_text(errors='replace')
                key = context_key(re.search(r'AnalysisClimateZone = (\w+)', text).group(1))
                documents = [release.construction(s, key, 'detailed') for s in sids if key in release.constructions.sets[s]['contexts']]
                if not documents:
                    continue
                model = idf_reader.Model(path)
                source = extract.prototype_file(FAMILY, path)
                roles = {}
                for role, by_construction in sorted(prototype_roles(model).items()):
                    atlas = [a for a in (atlas_values(d, role) for d in documents) if a]
                    if not atlas:
                        continue
                    total = sum(by_construction.values())
                    variants, different = [], False
                    for name, area in sorted(by_construction.items(), key=lambda kv: (-kv[1], kv[0].lower())):
                        record, materials, values = assembly(model, name, role)
                        for layer in record.get('layers', []):
                            layer['material'] = intern(library['materials'], materials[layer['material']])
                        different |= any(differs(values.get(f), a.get(f)) for a in atlas for f in values)
                        evidence = extract.cite(source, f'Construction {name}', values, 'SI (m2K/W, W/m2K, W/mK)',
                                                'layers and materials as written in the IDF; net area with zone and window '
                                                'multipliers', f'PNNL prototype construction of {role} in {path.name} '
                                                '(user decision P1: an alternate to the openstudio-standards assembly).')
                        variants.append({'construction': name, 'area_share': round(area/total, 6), 'values': values,
                                         'assembly': intern(library['assemblies'], record), 'evidence_id': evidence})
                    if different:  # the release editor compares each set of the folder with its own building default
                        roles[role] = {'variants': variants}
                if roles:
                    out[template][folder][key] = roles
    return {'schema_version': '1.0.0', 'kind': 'construction_alternates', 'decision': 'docs/adr/0046-release-2-0-0.md',
            'policy': {'tolerance': TOLERANCE, 'compared': 'layer resistance without films (opaque), U-factor and SHGC '
                       '(simple glazing), F-factor (ground floor), against the atlas building-default assembly',
                       'authority': 'openstudio-standards (user decision P1); the prototype constructions are alternates'},
            'source_files': dict(sorted(extract.source_files.items())), 'evidence': dict(sorted(extract.evidence.items())),
            'assemblies': dict(sorted(library['assemblies'].items())), 'materials': dict(sorted(library['materials'].items())),
            'alternates': {t: {f: dict(sorted(c.items())) for f, c in sorted(folders.items())} for t, folders in sorted(out.items())}}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--prototype-root', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    document = build(args.prototype_root)
    data = encode(document)
    if args.check:
        if OUTPUT.read_bytes() != data:
            raise SystemExit('construction-alternates-v1.json differs from a rebuild')
    else:
        OUTPUT.write_bytes(data)
    count = sum(len(roles) for folders in document['alternates'].values() for contexts in folders.values() for roles in contexts.values())
    print(f'Construction alternates: {count} component contexts; {len(document["source_files"])} IDFs')


if __name__ == '__main__':
    main()
