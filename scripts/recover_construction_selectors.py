"""Freeze complete pinned commercial above-ground construction-set closure.

No source/frozen release mutation, geometry generation, systems or site build.
Native construction methods execute in isolated models; raw targets are evidence,
not asserted attained performance. python -m scripts.recover_construction_selectors
"""
import argparse
import copy
import hashlib
import json
import math
import re
import subprocess
from collections import Counter
from pathlib import Path

from scripts.common import ROOT, load_json, dump_json
from scripts.definition_contract import canonical, stable_id
from scripts.energy_source_recovery import physical_assembly, assembly_u
from scripts.construction_definitions import normalize_material
from scripts.recover_program_inputs import RUNTIME

REVISION = 'c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907'
DATE = '2026-10-14'
SOURCE = ROOT / ('build/geometry-recovery/standards/openstudio-standards-' + REVISION)
WORK = ROOT / 'build/construction-selectors'
OUTPUT = ROOT / 'data/construction-inputs/selector-closure-v1.json'
FROZEN = ROOT / 'data/definition-releases/v0.1.1'
BASE = 'lib/openstudio-standards/standards/ashrae_90_1/'
CONSTRUCTIONS = BASE + 'data/ashrae_90_1.constructions.json'
MATERIALS = BASE + 'data/ashrae_90_1.materials.json'
CLIMATES = BASE + 'data/ashrae_90_1.climate_zone_sets.json'
MODEL = 'lib/openstudio-standards/standards/Standards.Model.rb'
MODIFY = 'lib/openstudio-standards/constructions/modify.rb'
FILMS = 'lib/openstudio-standards/constructions/information.rb'
U_FACTOR = 5.678263337
TEMPLATES = {'DOE Ref Pre-1980': 'doe_ref_pre_1980',
             'DOE Ref 1980-2004': 'doe_ref_1980_2004',
             '90.1-2007': 'ashrae_90_1_2007', '90.1-2013': 'ashrae_90_1_2013',
             '90.1-2019': 'ashrae_90_1_2019'}
TARGET_SLOTS = {'exterior_floor': 'ExteriorFloor', 'exterior_wall': 'ExteriorWall',
    'exterior_roof': 'ExteriorRoof', 'exterior_fixed_window': 'ExteriorWindow',
    'exterior_operable_window': 'ExteriorWindow', 'exterior_door': 'ExteriorDoor',
    'exterior_glass_door': 'GlassDoor', 'exterior_overhead_door': 'ExteriorDoor',
    'exterior_skylight': 'Skylight'}
DIRECT_SLOTS = {'interior_floors': 'InteriorFloor', 'interior_walls': 'InteriorWall',
    'interior_ceilings': 'InteriorCeiling', 'interior_doors': 'InteriorDoor',
    'interior_fixed_windows': 'InteriorWindow', 'interior_operable_windows': 'InteriorWindow',
    'interior_partitions': 'InteriorPartition', 'tubular_daylight_domes': 'TubularDaylightDome',
    'tubular_daylight_diffusers': 'TubularDaylightDiffuser', 'space_shading': 'SpaceShading',
    'building_shading': 'BuildingShading', 'site_shading': 'SiteShading'}
GROUND_SLOTS = ['ground_contact_floor', 'ground_contact_wall', 'ground_contact_ceiling']
GLASS_FIELDS = ['thickness_m', 'conductivity_W_m_K', 'optical_data_type',
    'solar_transmittance_at_normal_incidence', 'front_side_solar_reflectance_at_normal_incidence',
    'back_side_solar_reflectance_at_normal_incidence', 'visible_transmittance_at_normal_incidence',
    'front_side_visible_reflectance_at_normal_incidence', 'back_side_visible_reflectance_at_normal_incidence',
    'infrared_transmittance_at_normal_incidence', 'front_side_infrared_hemispherical_emissivity',
    'back_side_infrared_hemispherical_emissivity', 'dirt_correction_factor_for_solar_and_visible_transmittance',
    'solar_diffusing']
MATERIAL_FIELDS = {'thickness_m':('thickness','in','m'),
    'conductivity_W_m_K':('conductivity','Btu*in/(h*ft2*degF)','W/m/K'),
    'density_kg_m3':('density','lb/ft3','kg/m3'),
    'specific_heat_J_kg_K':('specific_heat','Btu/(lb*degF)','J/kg/K'),
    'resistance_m2_K_W':('resistance','h*ft2*degF/Btu','m2*K/W'),
    'u_W_m2_K':('u_factor','Btu/(h*ft2*degF)','W/m2/K'),
    'shgc':('solar_heat_gain_coefficient','1','1')}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact_bytes(packet):
    return (json.dumps(packet, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def match_properties(rows, template, role, construction_type, category):
    matches = [(i, r) for i, r in enumerate(rows) if
        (r.get('template'), r.get('intended_surface_type'),
         r.get('standards_construction_type'), r.get('building_category')) ==
        (template, role, construction_type, category)]
    contexts = {}
    for _, row in matches:
        key = tuple(row.get(k) for k in ('climate_zone_set', 'minimum_percent_of_surface',
            'maximum_percent_of_surface', 'operation_type', 'orientation'))
        physics = canonical({k:v for k,v in row.items() if k != 'notes'})
        if key in contexts and contexts[key] != physics:
            raise ValueError('Ambiguous construction property context: ' + str(key))
        contexts[key] = physics
    return matches


def source_climate_group(template, climate, groups):
    if climate.startswith('ClimateZone '):
        if any(g['name'] == climate for g in groups):
            return climate
        raise ValueError('Unsupported climate group: ' + climate)
    label = climate if climate.startswith('ASHRAE 169-') else 'ASHRAE 169-2013-' + climate
    candidates = [g['name'] for g in groups if label in g['climate_zones']]
    if not candidates:
        raise ValueError('Unsupported climate: ' + climate)
    if template.startswith('DOE Ref') and any(g in candidates for g in
                                              ('ClimateZone 1', 'ClimateZone 7', 'ClimateZone 8')):
        return min(candidates)
    return max(candidates)


def resolve_source_selector(packet, package_id, source_selector, climate, element_id=None):
    """Follow pinned prototype first-match policy, or select an explicit variant.

    Coverage/orientation operands are retained evidence. This method does not
    invent a dynamic consumer WWR selection rule absent from the pinned caller.
    """
    record = packet['records'][package_id]
    selector = record['selectors'][source_selector]
    source_group = source_climate_group(record['template'], climate, packet['climate_zone_sets'])
    policy = selector.get('selection_policy')
    if not policy:
        ids = selector['elements']
        if element_id is not None:
            if element_id not in ids:
                raise ValueError('Unsupported explicit source variant')
            ids = [element_id]
        return {'element_ids':ids, 'source_climate_group':source_group,
                'property_climate_group':None, 'selection_rule':'direct_source_recipe_or_absent'}
    ordered = policy['source_order']
    matching = [c for c in ordered if c['predicate']['climate_zone_set'] == source_group]
    property_group = source_group
    if not matching and re.fullmatch(r'ClimateZone [0-8][ABC]', source_group):
        property_group = source_group[:-1]
        matching = [c for c in ordered if c['predicate']['climate_zone_set'] == property_group]
    if not matching:
        raise ValueError('Unsupported source selector climate: ' + climate)
    if element_id is not None:
        if not any(element_id in c['element_ids'] for c in matching):
            raise ValueError('Unsupported explicit source variant for climate: ' + climate)
        ids = [element_id]
        rule = 'explicit_source_variant_id'
    else:
        if policy['default'] != 'source_first_match':
            raise ValueError('Ambiguous selector without declared source first-match policy')
        ids = matching[0]['element_ids']
        rule = 'source_first_match'
    return {'element_ids':ids, 'source_climate_group':source_group,
            'property_climate_group':property_group, 'selection_rule':rule}


def validate_layer(layer):
    model = layer['model']
    fields = {
        'StandardOpaqueMaterial': ['thickness_m', 'conductivity_W_m_K', 'density_kg_m3',
            'specific_heat_J_kg_K', 'roughness', 'thermal_absorptance', 'solar_absorptance', 'visible_absorptance'],
        'MasslessOpaqueMaterial': ['resistance_m2_K_W', 'roughness', 'thermal_absorptance',
            'solar_absorptance', 'visible_absorptance'],
        'AirGap': ['resistance_m2_K_W'],
        'Gas': ['thickness_m', 'gas_type'],
        'SimpleGlazing': ['u_W_m2_K', 'shgc', 'visible_transmittance'],
        'StandardGlazing': ['conductivity_W_m_K'] + [k for k in GLASS_FIELDS if k != 'conductivity_W_m_K'],
    }
    if model not in fields:
        raise ValueError('Unsupported material model: ' + model)
    for field in fields[model]:
        if layer.get(field) is None:
            raise ValueError('Missing source material physics: ' + field)
        value = layer[field]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if not math.isfinite(value) or value < 0:
                raise ValueError('Invalid source material physics: ' + field)
            if field.endswith(('_m', '_W_m_K', '_kg_m3', '_J_kg_K', '_m2_K_W')) and value <= 0:
                raise ValueError('Nonpositive source material physics: ' + field)
            if field == 'u_W_m2_K' and value <= 0:
                raise ValueError('Nonpositive source glazing U')
            if (field in {'shgc','visible_transmittance','thermal_absorptance','solar_absorptance',
                    'visible_absorptance','dirt_correction_factor_for_solar_and_visible_transmittance'} or
                    field.endswith(('_at_normal_incidence','_hemispherical_emissivity'))) and value > 1:
                raise ValueError('Invalid optical fraction: ' + field)
    if model == 'StandardGlazing' and not isinstance(layer['solar_diffusing'], bool):
        raise ValueError('solar_diffusing must be source-converted boolean')
    if model == 'StandardGlazing' and layer['optical_data_type'] != 'SpectralAverage':
        raise ValueError('Unsupported detailed glazing spectral dataset dependency')


def proof(path, fragment, original, unit, transformation, note, receipts):
    return {'source_locator': path + '#/' + fragment, 'source_revision': REVISION,
        'source_sha256': receipts[path]['sha256'], 'extraction_date': DATE,
        'original_value': copy.deepcopy(original), 'original_unit': unit,
        'transformation': transformation, 'interpretation_note': note}


def intern_evidence(packet):
    """Preserve complete provenance once; references never replace original data."""
    table = {}
    def visit(value):
        if isinstance(value, list):
            return [visit(v) for v in value]
        if not isinstance(value, dict):
            return value
        if 'source_locator' in value and 'original_value' in value:
            identity = stable_id('selector-evidence', value)
            table[identity] = value
            return {'evidence_id':identity}
        return {k:visit(v) for k,v in value.items()}
    result = visit(packet)
    result['evidence'] = dict(sorted(table.items()))
    return result


def field_evidence(layer, original, recipe, receipts, runtime):
    result = {}
    attrs = recipe['properties'] or {}
    for field, value in layer.items():
        native, unit, normalized = MATERIAL_FIELDS.get(field, (field,
            'boolean' if field == 'solar_diffusing' else 'category' if field in
            {'name','model','roughness','gas_type','optical_data_type'} else '1',
            'boolean' if field == 'solar_diffusing' else 'category' if field in
            {'name','model','roughness','gas_type','optical_data_type'} else '1'))
        if field == 'model':
            native = 'material_type'
        base_value = original.get(native)
        derivation = 'Pinned model_add_material constructor/setter SI getter; original null retained; actual SDK default is recovered by execution.'
        originals = base_value
        if 'simple glazing' in original['name'].lower():
            originals = {'material_name':original['name'], 'property_token':{'u_W_m2_K':'U',
                'shgc':'SHGC','visible_transmittance':'VT'}.get(field, field)}
            unit = 'generated source material name; U Btu/h/ft2/degF, SHGC/VT 1'
            derivation = 'Pinned model_add_material name-token parser, last token wins; explicit source code defaults when absent; actual native getter.'
        if field in {'thickness_m','resistance_m2_K_W','u_W_m2_K','name'} and attrs:
            originals = {'material_original':originals,
                'target_u_Btu_h_ft2_degF':attrs.get('assembly_maximum_u_value'),
                'insulation_layer':recipe['assembly'].get('insulation_layer'),
                'source_intended_surface_type':recipe['assembly'].get('intended_surface_type'),
                'interior_film':attrs.get('u_value_includes_interior_film_coefficient'),
                'exterior_film':attrs.get('u_value_includes_exterior_film_coefficient')}
            derivation += ' Then pinned model_add_construction/modify.rb target adjustment, clamping, insulation removal, and setter acceptance. Detailed glazing adjustment is skipped by source.'
        if field == 'solar_diffusing':
            derivation = 'Pinned model_add_material /true/i =~ raw.to_s; false for numeric 0/1; preserve actual native Boolean getter.'
        path = MATERIALS if original.get('material_type') else MODEL
        e = proof(path, ('materials/name='+original['name']+'/'+native if path == MATERIALS else
                         'model_add_material/'+original['name']+'/'+field), originals, unit, derivation,
                  'Executable '+normalized+' operand comes from exact source-native getter; no inferred constant.', receipts)
        e['runtime_executable_sha256'] = runtime['executable_sha256']
        e['normalized_unit'] = normalized
        e['supporting_source_locators'] = [MODEL+'#model_add_material', MODEL+'#model_add_construction', MODIFY+'#construction_set_u_value']
        result[field] = e
    return result


def locked_sources():
    geometry = load_json(ROOT / 'data/construction-inputs/geometry-v1.json')
    receipts = {}
    for name, receipt in geometry['source_files'].items():
        if not name.startswith('standards/lib/'):
            continue
        path = name[len('standards/'):]
        if sha(SOURCE / path) != receipt['sha256'] or receipt['source_revision'] != REVISION:
            raise ValueError('Modified pinned Standards dependency: ' + path)
        receipts[path] = dict(receipt, source_id='openstudio-standards', path=path,
            url='https://raw.githubusercontent.com/NatLabRockies/openstudio-standards/' + REVISION + '/' + path)
    if not receipts or any(p not in receipts for p in (CONSTRUCTIONS, MATERIALS, CLIMATES, MODEL, MODIFY, FILMS)):
        raise ValueError('Incomplete Standards source lock')
    runtime_root = ROOT / 'build/runtime/openstudio-windows'
    runtime = load_json(runtime_root / '.atlas-extraction.json')
    if sha(RUNTIME) != runtime['files'][RUNTIME.relative_to(runtime_root).as_posix()]:
        raise ValueError('Modified native runtime')
    return receipts, {'executable_sha256': sha(RUNTIME),
        'archive_sha256': runtime['archive_sha256']}


def table_path(template, table):
    slug = TEMPLATES[template]
    return BASE + slug + '/data/' + slug + '.' + table + '.json'


def recipe_identity(template, assembly, attributes):
    return stable_id('native-construction', {'template':template,
        'assembly': {k:v for k,v in assembly.items() if k != 'source_candidates'},
        'properties': attributes})


def construction_recipe(rows, name, material_rows):
    candidates = [(i,r) for i,r in enumerate(rows) if r['name'] == name]
    if not candidates:
        raise ValueError('Missing source construction: ' + name)
    def physics(row):
        p = {k:v for k,v in row.items() if k not in {'name','standards_construction_type'}}
        glazing = all('simple glazing' in n.lower() or any(m['name'] == n and
            m.get('material_type') in {'Gas','StandardGlazing','SimpleGlazing'} for m in material_rows)
            for n in row['materials'])
        # Fenestration U helper determines model from actual layers, and skips
        # detailed panes. An absent intended-surface metadata label does not
        # change these physical recipes; keep first-row native source behavior.
        if glazing:
            p.pop('intended_surface_type', None)
            p['materials'] = [{k:v for k,v in normalize_material(
                {'name':n} if 'simple glazing' in n.lower() else physical_assembly(material_rows,n)).items()
                if k != 'name'} for n in row['materials']]
        return canonical(p)
    if len({physics(r) for _,r in candidates}) != 1:
        raise ValueError('Ambiguous physical assembly: ' + name)
    result = copy.deepcopy(candidates[0][1])
    result['source_candidates'] = [{'index':i, 'row':r} for i,r in candidates]
    return result


def create_plan(receipts):
    frozen = load_json(FROZEN / 'constructions.json')
    provenance = {r['id']: r for r in load_json(FROZEN / 'provenance.json')}
    raw = load_json(SOURCE / CONSTRUCTIONS)['constructions']
    materials = load_json(SOURCE / MATERIALS)['materials']
    groups = load_json(SOURCE / CLIMATES)['climate_zone_sets']
    raw_properties = {t: load_json(SOURCE / table_path(t,'construction_properties'))['construction_properties']
                      for t in TEMPLATES}
    properties = {t: [dict(r, template=t) for r in rows] for t,rows in raw_properties.items()}
    elements, recipes, records = {}, {}, {}
    baseline = [r for r in frozen if r.get('representation') == 'element' and
                not r['role'].startswith('GroundContact')]
    baseline_by_context = {}

    def add(template, name, role, attrs, identity=None, source_context=None, original=None):
        assembly = construction_recipe(raw, name, materials)
        recipe = recipe_identity(template, assembly, attrs)
        if recipe not in recipes:
            originals = [physical_assembly(materials, n) if 'simple glazing' not in n.lower()
                         else {'name':n} for n in assembly['materials']]
            recipes[recipe] = {'id':recipe, 'template':template, 'assembly':assembly,
                'properties':attrs, 'materials':originals}
        eid = identity or stable_id('construction-selector', source_context)
        if eid not in elements:
            e = proof(CONSTRUCTIONS, 'constructions/name=' + name, assembly,
                'ordered source construction recipe', 'Execute pinned model_add_construction; preserve source row candidates.',
                'Target performance remains distinct from attained native layers; no source repair.', receipts)
            elements[eid] = {'id':eid, 'name':name, 'role':role, 'template':template,
                'climate':attrs.get('climate_zone_set') if attrs else None,
                'source_family': ('experimental_assumption' if original and original.get('derivation') == 'assumed'
                    else 'existing_stock_benchmark' if template.startswith('DOE') else 'code_prototype_rules'),
                'source_attributes':attrs or {}, 'recipe_id':recipe, 'evidence':e,
                'required_bindings':[], 'unresolved':[], 'source_context':source_context}
            if attrs:
                located = [(i,r) for i,r in enumerate(properties[template]) if r == attrs]
                if not located:
                    raise ValueError('Missing exact property source row: ' + eid)
                elements[eid]['property_evidence'] = proof(table_path(template, 'construction_properties'),
                    'construction_properties/' + str(located[0][0]),
                    raw_properties[template][located[0][0]],
                    'U Btu/h/ft2/degF; SHGC 1; surface coverage percent; film flags boolean',
                    'Exact selector context; template is the pinned source class/file binding; native source units enter pinned construction method.',
                    'Climate group, type, conditioning category and coverage branch remain explicit.', receipts)
                elements[eid]['property_source_candidates'] = [i for i,_ in located]
            if original:
                elements[eid]['original_source_id'] = original['source_id']
        return eid

    for row in baseline:
        original = provenance[row['evidence_ids'][0]]['original_value']
        attrs = original if isinstance(original, dict) and 'construction' in original else None
        template = row['template'] if row['template'] in TEMPLATES else '90.1-2019'
        if attrs:
            exact = [r for r in properties[template] if all(r.get(k) == v for k,v in attrs.items())]
            if not exact or len({canonical(r) for r in exact}) != 1:
                raise ValueError('Unresolved exact baseline property context: ' + row['id'])
            attrs = exact[0]
        add(template, row['name'], row['role'], attrs, row['id'],
            {'source_id':row['source_id'], 'baseline':True}, row)
        # Keep original public identity/template for accepted generic interior defaults.
        elements[row['id']]['template'] = row['template']
        if attrs:
            baseline_by_context.setdefault(canonical(attrs), []).append(row['id'])

    for package in [r for r in frozen if r.get('representation') == 'package']:
        template = package['template']
        source = package['source_set']
        source_path = table_path(template, 'construction_sets')
        sets = [dict(r, template=template) for r in load_json(SOURCE / source_path)['construction_sets']]
        comparable = {k:v for k,v in source.items() if k not in {'id','source_family','source_building_type'}}
        comparable['building_type'] = source.get('source_building_type', source['building_type'])
        locations = [i for i,r in enumerate(sets) if r == comparable]
        if len(locations) != 1:
            raise ValueError('Package source selector not uniquely located: ' + package['id'])
        pe = proof(source_path, 'construction_sets/' + str(locations[0]), comparable,
            'native construction-set selectors', 'Exact source set and complete pinned model_add_construction_set slot census.',
            'Null selector means upstream supplies no construction at this scope; inherit consumer/source parent context explicitly.', receipts)
        record = {'id':package['id'], 'template':template, 'building_type':package['building_type'],
            'space_type':source.get('space_type'), 'selectors':{}, 'deferred_selectors':{}, 'evidence':pe}
        for slot in GROUND_SLOTS:
            record['deferred_selectors'][slot] = {'role': {'ground_contact_floor':'GroundContactFloor',
                'ground_contact_wall':'GroundContactWall', 'ground_contact_ceiling':'GroundContactRoof'}[slot],
                'source_selector':slot, 'source_attributes':{k:source.get(slot+k) for k in
                    ('_standards_construction_type','_building_category')}, 'disposition':'deferred_ground_axis', 'evidence':pe}
        known = set(DIRECT_SLOTS) | {s + suffix for s in [*TARGET_SLOTS, *GROUND_SLOTS]
            for suffix in ('_standards_construction_type','_building_category')} | {
            'building_type','space_type','template','is_residential','climate_zone_set','notes'}
        if set(comparable) - known:
            raise ValueError('Uncensused source construction-set fields: ' + str(set(comparable)-known))
        for slot, role in {**TARGET_SLOTS, **DIRECT_SLOTS}.items():
            entry = {'role':role, 'source_selector':slot, 'elements':[], 'evidence':pe,
                     'disposition':'source_absent_at_this_scope'}
            direct = source.get(slot) if slot in DIRECT_SLOTS else None
            if source.get('space_type') == 'Attic':
                if slot == 'exterior_floor':
                    direct = 'Typical Attic Soffit'
                elif slot == 'exterior_roof' and source.get('exterior_roof_standards_construction_type'):
                    direct = 'Typical Uninsulated Wood Joist Attic Roof'
                elif slot == 'interior_floors':
                    direct = None
                    target_slot = 'exterior_roof'
                    role = 'ExteriorRoof'
                else:
                    target_slot = slot
            else:
                target_slot = slot
            if direct:
                old = [eid for eid in package['elements'].get(slot, [])
                       if eid in elements and elements[eid]['name'] == direct and not elements[eid]['source_attributes']]
                eid = old[0] if old else add(template, direct, role, None,
                    source_context={'package_id':package['id'], 'source_selector':slot, 'construction':direct})
                entry.update(elements=[eid], disposition='resolved_direct_recipe', construction_name=direct)
                if source.get('space_type') == 'Attic':
                    entry['source_method_override'] = MODEL + '#model_add_construction_set/Attic/' + slot
            elif slot in TARGET_SLOTS or (source.get('space_type') == 'Attic' and slot == 'interior_floors'):
                typ = source.get(target_slot + '_standards_construction_type')
                category = source.get(target_slot + '_building_category')
                entry['source_attributes'] = {'standards_construction_type':typ, 'building_category':category}
                if typ is not None and category is not None:
                    matches = match_properties(properties[template], template, role, typ, category)
                    if not matches:
                        raise ValueError('Missing required target selector: ' + package['id'] + '/' + slot)
                    for index, attr in matches:
                        existing = baseline_by_context.get(canonical(attr), [])
                        if existing:
                            ids = existing
                        else:
                            if not attr.get('construction'):
                                raise ValueError('Source target selector has no construction: ' + str(attr))
                            ids = [add(template, attr['construction'], role, attr, source_context={
                                'source_path':table_path(template, 'construction_properties'), 'source_index':index,
                                'template':template, 'role':role, 'construction_type':typ, 'category':category})]
                        entry['elements'].extend(ids)
                    entry.update(disposition='resolved_source_context', elements=sorted(set(entry['elements'])),
                        climate_selection={'method':'pinned_source_climate_group_then_exact_property_group_or_documented_parent_group',
                            'source_method':MODEL + '#model_find_and_add_construction',
                            'template_climate_method':(table_path(template,'Model').replace('/data/','/').replace('.Model.json','.Model.rb')
                                if template.startswith('DOE Ref') else MODEL) + '#model_get_climate_zone_set_from_list',
                            'groups':sorted({elements[i]['climate'] for i in entry['elements']})})
                    entry['selection_policy'] = {'default':'source_first_match',
                        'percent_caller_policy':'Pinned model_get_percent_of_surface_range returns both criteria null; no dynamic percentage branch is applied by prototype source caller.',
                        'source_order':[{'source_index':index, 'element_ids':(
                            baseline_by_context.get(canonical(attr)) or [stable_id('construction-selector', {
                                'source_path':table_path(template,'construction_properties'), 'source_index':index,
                                'template':template,'role':role,'construction_type':typ,'category':category})]),
                            'predicate':{k:attr.get(k) for k in ('climate_zone_set','minimum_percent_of_surface',
                                'maximum_percent_of_surface','operation_type','orientation')}} for index,attr in matches],
                        'explicit_variant_selection':'Retained alternative recipe may be selected by element ID; do not invent a WWR rule.'}
            record['selectors'][slot] = entry
        records[package['id']] = record
    return {'records':records, 'elements':elements, 'recipes':recipes, 'baseline_element_ids':sorted(r['id'] for r in baseline),
            'climate_zone_sets':groups}


def native_execute(plan, runtime, pilot_only=False):
    WORK.mkdir(parents=True, exist_ok=True)
    recipes = plan['recipes']
    pilot_ids = {eid for r in plan['records'].values() if r['building_type'] in {'MediumOffice','Office'}
                 for s in r['selectors'].values() for eid in s['elements']}
    pilot_recipes = {plan['elements'][i]['recipe_id'] for i in pilot_ids}
    pilot = [recipes[i] for i in sorted(pilot_recipes)]
    dump_json(WORK/'pilot-input.json', pilot)
    subprocess.run([str(RUNTIME), str(ROOT/'scripts/recover_construction_selectors.rb'),
        str(SOURCE), str(WORK/'pilot-input.json'), str(WORK/'pilot-output.json')],
        cwd=ROOT, check=True, timeout=240)
    native = load_json(WORK/'pilot-output.json')
    results = {r['id']:r for r in native['results']}
    for r in results.values():
        for layer in r['layers']:
            validate_layer(layer)
    print('Validated native Medium Office pilot:', len(pilot), 'unique recipes', flush=True)
    if pilot_only:
        return results, native['runtime_version']
    other = [r for i,r in sorted(recipes.items()) if i not in results]
    dump_json(WORK/'all-input.json', other)
    subprocess.run([str(RUNTIME), str(ROOT/'scripts/recover_construction_selectors.rb'),
        str(SOURCE), str(WORK/'all-input.json'), str(WORK/'all-output.json')],
        cwd=ROOT, check=True, timeout=600)
    rest = load_json(WORK/'all-output.json')
    if rest['runtime_version'] != native['runtime_version']:
        raise ValueError('Native runtime changed between pilot and expansion')
    results.update({r['id']:r for r in rest['results']})
    if set(results) != set(recipes):
        raise ValueError('Incomplete native recipe execution')
    return results, native['runtime_version']


def recover(pilot_only=False):
    receipts, runtime = locked_sources()
    plan = create_plan(receipts)
    print('Planned:', len(plan['elements']), 'elements,', len(plan['recipes']), 'unique native recipes', flush=True)
    native, version = native_execute(plan, runtime, pilot_only)
    if pilot_only:
        return {'native_pilot':len(native), 'runtime_version':version}
    for eid, element in plan['elements'].items():
        recipe = plan['recipes'][element['recipe_id']]
        result = native[element['recipe_id']]
        props = recipe['properties'] or {}
        layer_models = {l['model'] for l in result['layers']}
        element['model'] = ('simple_glazing' if layer_models == {'SimpleGlazing'} else
                            'detailed_glazing' if layer_models & {'StandardGlazing','Gas'} else 'opaque_layers')
        original_materials = recipe['materials']
        layers = []
        for i, layer in enumerate(result['layers']):
            validate_layer(layer)
            matching = [m for m in original_materials if layer['name'] == m['name'] or
                        layer['name'].startswith(m['name'] + ' R-')]
            matching = list({canonical(m):m for m in matching}.values())
            if len(matching) != 1:
                raise ValueError('Unresolved native layer source: ' + layer['name'])
            e = proof(MATERIALS if matching[0].get('material_type') else MODEL,
                ('materials/name=' + matching[0]['name'] if matching[0].get('material_type') else
                 'model_add_material/' + matching[0]['name']), matching[0],
                'source IP material columns; generated simple glazing U Btu/h/ft2/degF and SHGC/VT 1',
                'Execute pinned constructors/setters and target adjustment; getters report SI. solar_diffusing uses source /true/i boolean conversion.',
                'Retain actual SDK outcome including rejected nil.to_f setters; no fabricated material defaults.', receipts)
            e['supporting_source_locators'] = [MODEL + '#model_add_material', MODEL + '#model_add_construction',
                                             MODIFY + '#construction_set_u_value']
            e['runtime_executable_sha256'] = runtime['executable_sha256']
            layers.append({'order':i, 'properties':layer, 'evidence':e,
                           'field_evidence':field_evidence(layer, matching[0], recipe, receipts, runtime)})
        element['layers'] = layers
        films = result['films_m2_K_W']
        target = props.get('assembly_maximum_u_value')
        target_si = None if target is None else target * U_FACTOR
        achieved = assembly_u(result['layers'], films) if element['model'] == 'opaque_layers' else (
            result['layers'][0]['u_W_m2_K'] if element['model'] == 'simple_glazing' else None)
        if achieved is not None and not math.isclose(achieved, result['native_attained_u_W_m2_K'], rel_tol=1e-12):
            raise ValueError('Normalized assembly resistance differs from pinned source calculation: ' + eid)
        adjustment = ('base_source_layers' if target is None else
            'detailed_glazing_target_not_adjusted_by_source' if element['model'] == 'detailed_glazing' else
            'source_zero_target_insulation_removed' if abs(target) < .01 else 'source_native_target_method')
        element['target_adjustment'] = {'status':adjustment, 'target_u_W_m2_K':target_si,
            'attained_u_W_m2_K':achieved, 'films_m2_K_W':films,
            'includes_interior_film': result['includes_interior_film'],
            'includes_exterior_film': result['includes_exterior_film'],
            'evidence':proof(FILMS, 'film_coefficients_r_value/' + (recipe['assembly']['intended_surface_type'] or 'source_null'),
                {'role':recipe['assembly']['intended_surface_type'], 'interior':result['includes_interior_film'],
                 'exterior':result['includes_exterior_film']}, 'boolean',
                'Pinned native film method; attained U = 1 / (sum native layer resistance + included films) for opaque materials.',
                'Direct base recipes report physical U with both source standard films; simple glazing U already includes rating films; detailed optical summary remains optional.', receipts)}
        u_evidence = copy.deepcopy(element['target_adjustment']['evidence'])
        u_evidence['original_value'] = {'target_u_Btu_h_ft2_degF':target,
            'native_layer_resistances_m2_K_W':result['native_layer_resistances_m2_K_W'],
            'native_included_films_m2_K_W':films,
            'native_simple_glazing_rated_u_W_m2_K':achieved if element['model'] == 'simple_glazing' else None,
            'source_layer_evidence_ids':[stable_id('selector-evidence', l['evidence']) for l in layers]}
        u_evidence['original_unit'] = 'native getter resistances m2*K/W, SimpleGlazing rated U W/m2/K; source target Btu/(h*ft2*degF)'
        u_evidence['transformation'] = ('Execute pinned source material and construction methods; '
            'opaque attained U = 1/(sum native layer R + included pinned films); simple glazing uses native rated U getter; '
            'detailed glazing scalar U is unreported, not required for ordered pane/gas model execution.')
        u_evidence['supporting_source_locators'] = [MODEL+'#model_add_construction', MATERIALS+'#/materials', MODIFY+'#construction_set_u_value']
        u_evidence['runtime_executable_sha256'] = runtime['executable_sha256']
        element['parameters'] = {'u_W_m2_K': {'value':achieved, 'unit':'W/m2/K',
            'origin':'source_native_calculation', 'evidence':u_evidence}}
        if element['model'] == 'simple_glazing':
            for field in ('shgc','visible_transmittance'):
                element['parameters'][field] = {'value':result['layers'][0][field], 'unit':'1',
                    'origin':'source_native_getter', 'evidence':layers[0]['evidence']}
            element['target_adjustment']['target_shgc'] = props.get('assembly_maximum_solar_heat_gain_coefficient')
            element['target_adjustment']['source_shgc_behavior'] = 'Preserve pinned model_add_construction conditional setter; target is not automatically applied.'
        element['native_name'] = result['name']
        element['source_skylight_framing'] = recipe['assembly'].get('skylight_framing')
        if element['source_skylight_framing']:
            raise ValueError('Unexported source skylight framing dependency: ' + eid)
    del plan['recipes']
    counts = Counter(s['disposition'] for r in plan['records'].values() for s in r['selectors'].values())
    plan['inventory'] = {'package_count':len(plan['records']), 'baseline_element_count':len(plan['baseline_element_ids']),
        'additional_element_ids':sorted(set(plan['elements']) - set(plan['baseline_element_ids'])),
        'element_count':len(plan['elements']), 'selector_dispositions':dict(sorted(counts.items())),
        'selector_occurrences':dict(sorted(Counter(k for r in plan['records'].values() for k,s in
            r['selectors'].items() if s['elements']).items()))}
    inputs = [FROZEN/'constructions.json', FROZEN/'provenance.json',
              ROOT/'data/construction-inputs/geometry-v1.json', ROOT/'scripts/recover_construction_selectors.py',
              ROOT/'scripts/recover_construction_selectors.rb', ROOT/'scripts/energy_source_recovery.py',
              ROOT/'scripts/construction_definitions.py', ROOT/'scripts/definition_contract.py',
              ROOT/'scripts/recover_program_inputs.py', ROOT/'scripts/common.py']
    packet = {'schema_version':'1.0.0', 'kind':'commercial_above_ground_selector_closure',
        'extraction_date':DATE, 'input_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in inputs},
        'source_files':receipts, 'runtime':dict(runtime, version=version),
        'boundary':'Complete source construction-set above-ground slots; ground/foundation and systems deferred.', **plan}
    packet = intern_evidence(packet)
    validate(packet)
    return packet


def validate(packet):
    elements = packet['elements']
    if not set(packet['baseline_element_ids']) <= set(elements):
        raise ValueError('Dropped baseline above-ground identities')
    for record in packet['records'].values():
        if set(record['selectors']) != set(TARGET_SLOTS) | set(DIRECT_SLOTS):
            raise ValueError('Incomplete selector census')
        for selector in record['selectors'].values():
            if not set(selector['elements']) <= set(elements):
                raise ValueError('Orphan source selector dependency')
    for element in elements.values():
        if not element.get('layers') or element['unresolved']:
            raise ValueError('Unresolved above-ground source physics: ' + element['id'])
        for layer in element['layers']:
            validate_layer(layer['properties'])
        if element['model'] == 'opaque_layers' and element['parameters']['u_W_m2_K']['value'] is None:
            raise ValueError('Unresolved attained opaque U: ' + element['id'])
    if 'evidence' in packet:
        for evidence in packet['evidence'].values():
            path = evidence['source_locator'].split('#')[0]
            if packet['source_files'].get(path, {}).get('sha256') != evidence['source_sha256']:
                raise ValueError('Unverified selector source evidence')
            original = evidence['original_value']
            if isinstance(original, dict) and not set(original.get('source_layer_evidence_ids',[])) <= set(packet['evidence']):
                raise ValueError('Orphan attained-U material provenance')
        def references(value):
            if isinstance(value, list):
                for child in value:
                    references(child)
            elif isinstance(value, dict):
                if 'evidence_id' in value and value['evidence_id'] not in packet['evidence']:
                    raise ValueError('Orphan selector provenance')
                for child in value.values():
                    references(child)
        references({k:v for k,v in packet.items() if k != 'evidence'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--pilot', action='store_true')
    args = parser.parse_args()
    packet = recover(args.pilot)
    if args.pilot:
        print('Native pilot passed')
    elif args.check:
        if artifact_bytes(packet) != OUTPUT.read_bytes():
            raise ValueError('Construction selector closure is not reproducible')
        print('Verified deterministic selector closure')
    else:
        dump_json(OUTPUT, packet)
        print('Frozen selector closure:', {k:v for k,v in packet['inventory'].items() if k != 'additional_element_ids'})


if __name__ == '__main__':
    main()
