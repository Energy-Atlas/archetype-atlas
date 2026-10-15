"""Precomputed source-archetype support profiles, separate from program loads.

No population weighting or consumer geometry. --recover runs pinned geometry and
internal-mass source methods only; default freezes already recovered evidence.
"""
import argparse
import hashlib
import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path

from scripts.common import ROOT, load_json
from scripts.definition_contract import stable_id

OUTPUT = ROOT/'data/program-support/construction-weighting-v1'
WORK = ROOT/'build/equivalent-work'
DATE = '2026-10-15'
README = '''# Construction weighting support profiles 1.0.0

Program-library supporting data, separate from program loads and schedules.
129 commercial source references and 41 residential source fixtures; 1,158 native
commercial program keys. Existing program definition links are exact source-key
joins, not assertions that every recovered key has a published load contract.

Default weighting uses precomputed source geometry only. Counted source floor
shares, conditional native-building/program group shares, net component exposure,
volume, story scopes and physical mass inventories retain their denominators.
Non-counted scopes use direct exposure. Apply source multipliers once.
Window-operation areas are separated by exterior/interior semantic.

Surface-pair inventories preserve both original face operands. A pair with unequal
multipliers has unknown physical area under the default require_equal policy;
it is not resolved by whichever face is encountered first. The proposed symmetric
mean policy requires an explicit user decision. Profiles retain evidence while
corresponding derived mass semantics are blocked.

python -m scripts.construction_weighting --check compares normalized cached source
recovery and manifest bytes. Add --recover to rerun the pinned geometry/mass
methods, using the existing locked source/runtime retrieval described by the
construction recovery tooling. No HVAC, annual schedules or site build is run.
load_profiles() validates checksums before use. Native source revisions, archive
and executable checksums are retained in manifest.json; field source locators
and original operands/units are in profiles.json and linked immutable inputs.

Preserve LICENSE and sources/licenses upstream notices. Original Atlas work
remains unlicensed by user choice. No production publication is implied.
'''
ROLES = ('ExteriorWall', 'ExteriorRoof', 'ExteriorFloor', 'ExteriorWindow', 'ExteriorDoor',
         'GlassDoor', 'OverheadDoor', 'Skylight', 'InteriorWall', 'InteriorFloor',
         'InteriorCeiling', 'InteriorDoor', 'InteriorWindow', 'TubularDaylightDome', 'TubularDaylightDiffuser')
OPENINGS = {'FixedWindow': 'ExteriorWindow', 'OperableWindow': 'ExteriorWindow',
            'Door': 'ExteriorDoor', 'GlassDoor': 'GlassDoor', 'OverheadDoor': 'OverheadDoor',
            'Skylight': 'Skylight', 'TubularDaylightDome': 'TubularDaylightDome',
            'TubularDaylightDiffuser': 'TubularDaylightDiffuser'}


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)+'\n').encode('utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def program_index(rows, definitions):
    index = defaultdict(list)
    definition_ids = defaultdict(list)
    for d in definitions:
        if d.get('detail') == 'SourcePrograms' and d.get('evidence_view') == 'source':
            definition_ids[d.get('source_id')].append(d['id'])
    for p in rows:
        index[p['template'], p.get('source_building_type'), p.get('source_space_type')].extend(definition_ids[p['id']])
    return {k: sorted(set(v)) for k, v in index.items()}


def build_commercial_profile(record, programs, paired_area_policy='require_equal'):
    if paired_area_policy not in ('require_equal','mean_zone_weighted_faces'):
        raise ValueError('Unknown paired-face area policy')
    total = sum(s['floor_area_m2']*s['multiplier'] for s in record['spaces'] if s['counted_floor_area'])
    if total <= 0:
        raise ValueError('Unknown or zero counted floor area')
    spaces, floors, walls, seen_pairs, seen_walls = [], [], [], set(), set()
    all_faces = {f['id']: (s,f) for s in record['spaces'] for f in s['surfaces']}
    def inventory_item(pair, kind):
        faces = []
        for identity in pair:
            owner, face = all_faces[identity]
            faces.append({'id': identity, 'source_space_name': owner['name'],
                          'multiplier': owner['multiplier'], 'net_area_m2': face['net_area_m2'],
                          'weighted_area_m2': face['net_area_m2']*owner['multiplier']})
        # Canonical owner is the floor face for a floor/ceiling pair; wall owner
        # is stable by source name, never iteration order.
        owner_id = next((i for i in pair if all_faces[i][1]['type']=='Floor'), pair[0])
        owner, _ = all_faces[owner_id]
        multipliers = {f['multiplier'] for f in faces}
        ambiguous = len(multipliers) > 1
        area = None if ambiguous and paired_area_policy=='require_equal' else sum(f['weighted_area_m2'] for f in faces)/len(faces)
        return {'source_surface_ids': list(pair), 'source_space_name': owner['name'], 'faces': faces,
                'area_m2': area, 'area_per_counted_floor_area': None if area is None else area/total,
                'status': 'ambiguous_pair_multipliers' if area is None else 'ready',
                'paired_area_policy': paired_area_policy,
                'rule': 'one physical '+kind+'; preserve both original face operands'}
    for s in record['spaces']:
        mult = s['multiplier']
        if not math.isfinite(mult) or mult <= 0:
            raise ValueError('Invalid source multiplier')
        native = s.get('native_program') or {}
        key = record['template'], native.get('building_type'), native.get('space_type')
        native_id = stable_id('native-program', dict(zip(('template', 'building_type', 'space_type'), key))) if native else None
        scope = {'name': s['name'], 'story': s['story'], 'counted_floor_area': s['counted_floor_area'],
                 'source_space_type': s.get('source_identifiers', {}).get('space_type', native.get('space_type')),
                 'floor_area_m2': s['floor_area_m2']*mult, 'volume_m3': s['volume_m3']*mult,
                 'floor_share': s['floor_area_m2']*mult/total if s['counted_floor_area'] else None,
                 'source_multiplier': mult, 'source_floor_area_m2': s['floor_area_m2'],
                 'program': {'native_id': native_id, 'native_building_type': key[1],
                             'native_space_type': key[2], 'definition_ids': programs.get(key, []),
                             'status': 'native_source_key_recovered' if native else 'source_untyped_scope'},
                 'exposure_m2': {role: 0. for role in ROLES},
                 'operation_area_m2': {k:{'FixedWindow':0.,'OperableWindow':0.} for k in ('ExteriorWindow','InteriorWindow')},
                 'added_mass': [], 'source_locator': record['geometry_file']+'#OS:Space/name='+s['name']}
        for sf in s['surfaces']:
            exterior = sf['boundary'] == 'Outdoors'
            interior = sf['boundary'] in ('Surface', 'Adiabatic')
            role = ({'Wall': 'ExteriorWall', 'Floor': 'ExteriorFloor', 'RoofCeiling': 'ExteriorRoof'} if exterior else
                    {'Wall': 'InteriorWall', 'Floor': 'InteriorFloor', 'RoofCeiling': 'InteriorCeiling'} if interior else {}).get(sf['type'])
            if role:
                scope['exposure_m2'][role] += sf['net_area_m2']*mult
            for opening in sf['openings']:
                op = OPENINGS.get(opening['type'])
                if interior:
                    op = 'InteriorWindow' if opening['type'] in ('FixedWindow', 'OperableWindow') else 'InteriorDoor'
                if op and (exterior or interior):
                    area = opening['area_m2']*opening['multiplier']*mult
                    scope['exposure_m2'][op] += area
                    if op in ('ExteriorWindow','InteriorWindow'):
                        scope['operation_area_m2'][op][opening['type']] += area
            if interior and sf['type'] == 'Floor':
                pair = tuple(sorted({sf['id'], sf['adjacent_id']} - {None}))
                if pair not in seen_pairs:
                    floors.append(inventory_item(pair, 'floor/slab'))
                    seen_pairs.add(pair)
            if interior and sf['type'] == 'Wall':
                pair = tuple(sorted({sf['id'], sf['adjacent_id']} - {None}))
                if pair not in seen_walls:
                    walls.append(inventory_item(pair, 'wall'))
                    seen_walls.add(pair)
        for mass in s['internal_mass']:
            area = (mass.get('direct_area_m2') or 0)+(mass.get('area_per_floor_area') or 0)*s['floor_area_m2']
            # Per-person mass cannot be evaluated without its actual source person count.
            status = 'unknown_person_count' if mass.get('area_per_person_m2') else 'ready'
            scope['added_mass'].append({'id': mass['id'], 'area_m2': area*mult if status == 'ready' else None,
                                        'status': status, 'layers': mass['layers'],
                                        'source_operands': {k: v for k, v in mass.items() if k != 'layers'}})
        spaces.append(scope)
    grouped = defaultdict(lambda: defaultdict(float))
    for s in spaces:
        if s['counted_floor_area']:
            grouped[s['program']['native_building_type']][s['program']['native_id']] += s['floor_area_m2']
    groups = []
    for building,programs_in_group in sorted(grouped.items(),key=lambda row:str(row[0])):
        group_area=sum(programs_in_group.values())
        groups.append({'native_building_type':building,'floor_share':group_area/total,
                       'programs':[{'native_program_id':pid,'conditional_floor_share':area/group_area,
                                    'global_floor_share':area/total,'floor_area_m2':area}
                                   for pid,area in sorted(programs_in_group.items(),key=lambda row:str(row[0]))]})
    return {'id': record['id'], 'building_type': record['building_type'], 'template': record['template'],
            'counted_floor_area_m2': total, 'spaces': spaces,
            'floor_inventory': sorted(floors,key=lambda f:f['source_surface_ids']),
            'wall_inventory': sorted(walls,key=lambda f:f['source_surface_ids']),
            'program_groups': groups,
            'program_share_basis': 'counted source floor area; non-counted scopes use direct exposure',
            'weighting_policy': 'precomputed_source_archetype',
            'units': {'areas': 'm2', 'volumes': 'm3', 'shares_and_multipliers': '1'},
            'interpretation': 'Native source keys do not alias construction typologies or imply publication of missing load contracts.'}


def build_residential_profile(record, geometry, programs):
    cfa = geometry['fields']['cfa_m2']['value']
    attrs = record['source_context']['source_surface_attributes']
    source_areas = {sid: row['attributes'].get('area') for sid, row in attrs.items()}
    areas = {sid: None if v is None else v*.09290304 for sid, v in source_areas.items()}
    net = dict(areas)
    for sid, row in attrs.items():
        a = row['attributes']
        parent = a.get('attached_to_wall_idref') or a.get('attached_to_roof_idref')
        if parent in net and areas[sid] is not None:
            net[parent] -= areas[sid]
    assembly_areas = {}
    for a in record['assemblies']:
        app = a['applicability']
        if a['role'] == 'InteriorPartition':
            area = app.get('area_per_conditioned_floor_area')
            area = None if area is None else area*cfa
        elif a['role'] == 'OrdinaryInteriorFloor':
            area = app.get('source_reference_area_per_cfa')
            area = None if area is None else area*cfa
        else:
            vals = [net.get(sid) for sid in a['source_surface_ids']]
            area = sum(vals) if vals and all(v is not None for v in vals) else None
        if area is not None and area < -1e-6:
            raise ValueError('Negative residential net area')
        assembly_areas[a['id']] = {'area_m2': area, 'area_per_counted_floor_area': None if area is None else area/cfa,
                                   'source_surface_ids': a['source_surface_ids'], 'role': a['role']}
    matches = [p for p in programs if p.get('source_id') == record['id']]
    return {'id': record['id'], 'building_type': matches[0]['building_type'] if len(matches) == 1 else None,
            'template': 'ResStock SDR source fixture',
            'program_definition_ids': sorted(p['id'] for p in matches),
            'counted_floor_area_m2': cfa, 'volume_m3': geometry['fields']['conditioned_volume_m3']['value'],
            'program_share': 1., 'assembly_areas': assembly_areas,
            'source_area_ft2': source_areas, 'weighting_policy': 'precomputed_source_archetype',
            'units': {'areas': 'm2 except source_area_ft2', 'volumes': 'm3', 'shares': '1'},
            'interpretation': 'Preserve fixture identity; sum attached openings once; ordinary interstory quantity is the pinned source rule.'}


def recover():
    from scripts.recover_construction_geometry import prepare_sources
    from scripts.recover_program_inputs import RUNTIME
    source, receipts, runtime = prepare_sources()
    WORK.mkdir(parents=True, exist_ok=True)
    refs = load_json(ROOT/'data/construction-inputs/geometry-v1.json')['commercial']
    ordered = sorted(refs, key=lambda r: (r['id'] != '90.1-2019/MediumOffice', r['id']))
    (WORK/'weight-inputs.json').write_bytes(encoded([{k: r[k] for k in ('template','building_type')} for r in ordered]))
    subprocess.run([str(RUNTIME), str(ROOT/'scripts/recover_construction_weights.rb'), str(source),
                    str(WORK/'weight-inputs.json'), str(WORK/'commercial-weights.json')], cwd=ROOT, check=True, timeout=600)
    (WORK/'source-receipts.json').write_bytes(encoded({'source': str(source), 'receipts': receipts, 'runtime': runtime}))


def build_profiles():
    raw = load_json(WORK/'commercial-weights.json')
    geometry = load_json(ROOT/'data/construction-inputs/geometry-v1.json')
    source_rows = load_json(ROOT/'data/releases/v0.2.0/programs.json')
    defs = load_json(ROOT/'data/definition-releases/v0.1.1/programs.json')
    index = program_index(source_rows, defs)
    refs = {g['id']: g for g in geometry['commercial']}
    if {r['id'] for r in raw['results']} != set(refs):
        raise ValueError('Incomplete source recovery')
    profiles, native, mass_recipes = {}, {}, {}
    for record in raw['results']:
        # Stabilize SDK-derived geometry only, never literal source program data
        # or material constants. The recovery follows the existing 9-digit policy.
        from scripts.recover_construction_geometry import canonical_derived
        original_scopes = {s['name']: s for s in refs[record['id']]['spaces']}
        for s in record['spaces']:
            original = original_scopes[s['name']]
            s['source_identifiers'] = {'building_type': original['standards_building_type'],
                                       'space_type': original['standards_space_type']}
            for key in ('floor_area_m2', 'volume_m3'):
                s[key] = canonical_derived(s[key])
            s['surfaces'] = canonical_derived(s['surfaces'])
        p = build_commercial_profile(record, index)
        ref = refs[record['id']]
        p['provenance'] = {'source_project': 'OpenStudio Standards', 'source_revision': 'c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907',
                           'source_locator': ref['geometry_file'], 'source_file_sha256': ref['geometry_file_sha256'],
                           'extraction_date': DATE, 'original_unit': 'm2, m3 and dimensionless',
                           'transformation': 'Pinned SDK netArea/grossArea, 9 significant digits for derived geometry only; source geometry tweaks; source multipliers exactly once; no consumer BEM.',
                           'interpretation_note': 'Source thermostat rules evaluate only furnishing applicability; no HVAC or annual energy model.'}
        profiles[p['id']] = p
        for s, scope in zip(record['spaces'], p['spaces']):
            scope['original_value'] = {'floor_area_m2': s['floor_area_m2'], 'volume_m3': s['volume_m3'],
                                       'multiplier': s['multiplier'],
                                       'component_areas_m2': {k: v/s['multiplier'] for k,v in scope['exposure_m2'].items()}}
            for mass in scope['added_mass']:
                layers = mass.pop('layers')
                mid = stable_id('reference-mass-recipe', layers) if layers else None
                if mid:
                    mass_recipes[mid] = layers
                mass['recipe_id'] = mid
            row = s.get('native_program')
            if row:
                identity = scope['program']['native_id']
                native[identity] = {'id': identity, 'template': record['template'],
                                    'building_type': row.get('building_type'), 'space_type': row.get('space_type'),
                                    'definition_ids': scope['program']['definition_ids'],
                                    'source_row_sha256': hashlib.sha256(encoded(row)).hexdigest(),
                                    'source_locator': 'lib/openstudio-standards/standards/Standards.SpaceType.rb#space_type_get_standards_data',
                                    'original_value': {k: row.get(k) for k in ('template','building_type','space_type')},
                                    'original_unit': 'native source identifiers', 'transformation': 'Exact pinned source lookup; no typology alias',
                                    'extraction_date': DATE,
                                    'interpretation_note': 'Supporting share key, not an additional simulation-ready program load definition.'}
    residential = load_json(ROOT/'data/construction-inputs/residential-assemblies-v1.json')['records']
    res_geom = {g['id']: g for g in geometry['residential']}
    for identity, record in residential.items():
        p = build_residential_profile(record, res_geom[identity], defs)
        p['provenance'] = record['source_context']['context_provenance']
        profiles[identity] = p
    return {'schema_version': '1.0.0', 'kind': 'program_library_construction_weighting_profiles',
            'profiles': profiles, 'native_programs': native, 'mass_recipes': mass_recipes}


def load_profiles(directory=OUTPUT):
    directory=Path(directory)
    manifest=load_json(directory/'manifest.json')
    if manifest.get('kind')!='program_support_profile_release' or manifest.get('release')!='1.0.0':
        raise ValueError('Invalid support profile release')
    for name,row in manifest['files'].items():
        if sha(directory/name)!=row['sha256']:
            raise ValueError('Support profile checksum mismatch: '+name)
    for path,digest in manifest['input_sha256'].items():
        if sha(ROOT/path)!=digest:
            raise ValueError('Support profile input checksum mismatch: '+path)
    return load_json(directory/'profiles.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recover', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.recover:
        recover()
    packet = build_profiles()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT/'profiles.json'
    data = encoded(packet)
    if args.check:
        if path.read_bytes() != data:
            raise ValueError('Weighting profiles are not reproducible')
    else:
        path.write_bytes(data)
    inputs = ['data/construction-inputs/geometry-v1.json', 'data/construction-inputs/residential-assemblies-v1.json',
              'data/releases/v0.2.0/programs.json', 'data/definition-releases/v0.1.1/programs.json',
              'scripts/construction_weighting.py', 'scripts/recover_construction_weights.rb',
              'scripts/recover_construction_geometry.py']
    geometry = load_json(ROOT/inputs[0])
    manifest = {'schema_version': '1.0.0', 'kind': 'program_support_profile_release', 'release': '1.0.0',
                'input_sha256': {p: sha(ROOT/p) for p in inputs},
                'source_runtime': geometry['runtime'],
                'source_files': {p: q for p,q in geometry['source_files'].items()
                                 if any(s in p for s in ('Standards.SpaceType.rb', 'Prototype.Model.rb', '/space/space.rb', '/thermal_zone/thermal_zone.rb'))},
                'files': {'profiles.json': {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)},
                          'README.md': {'sha256': hashlib.sha256(README.encode('utf-8')).hexdigest(), 'bytes':len(README.encode('utf-8'))}},
                'coverage': {'commercial_references': 129, 'residential_fixtures': 41,
                             'native_program_keys': len(packet['native_programs'])}}
    mpath = OUTPUT/'manifest.json'
    if args.check:
        if mpath.read_bytes() != encoded(manifest):
            raise ValueError('Weighting profile manifest is not reproducible')
    else:
        mpath.write_bytes(encoded(manifest))
    readme=OUTPUT/'README.md'
    if args.check:
        if readme.read_bytes()!=README.encode('utf-8'):
            raise ValueError('Weighting profile README is not reproducible')
    else:
        readme.write_bytes(README.encode('utf-8'))
    print(f"Profiles: {len(packet['profiles'])}; native source program keys: {len(packet['native_programs'])}")


if __name__ == '__main__':
    main()
