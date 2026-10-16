"""Representation-independent source mass quantities; no fitting or BEM geometry."""
import copy
import hashlib
import json
import math
from functools import lru_cache

from jsonschema import Draft202012Validator
from scripts.common import ROOT, load_json
from scripts.definition_contract import stable_id
from scripts.construction_equivalent_export import _mass_budgets, source_layers
from scripts.construction_set_validation import validate_set, BatchValidationCache
from scripts.construction_validation import validate_material

PROFILE_PATH = ROOT/'data/program-support/construction-weighting-v1.1.0/profiles.json'
RESIDENTIAL_PATH = ROOT/'data/construction-inputs/residential-assemblies-v1.json'
SCHEMAS = {
    'construction_set': ROOT/'schemas/construction-json-v2.1.schema.json',
    'building_level_equivalent': ROOT/'schemas/construction-equivalent-v1.2.schema.json',
    'mass': ROOT/'schemas/construction-mass-accounting-v1.schema.json',
}
LEGACY_BUDGET_KEYS = ('source_assembly_id', 'area_per_counted_floor_area',
                      'capacity_per_counted_floor_area_J_m2_K')


def number(value, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError('Unknown or invalid mass quantity/material operand')
    return value


@lru_cache(maxsize=None)
def validator(kind):
    schema = load_json(SCHEMAS[kind])
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


class BatchMassValidationCache:
    """Validate each content fingerprint once; validate every selected context."""
    def __init__(self):
        self.legacy = BatchValidationCache()
        self.context, self.blocks, self.checked = {}, {}, set()
        for kind in ('construction_set', 'building_level_equivalent'):
            schema = copy.deepcopy(validator(kind).schema)
            schema['properties']['mass_accounting'] = {'type':'object'}
            if kind == 'construction_set':
                for key in ('assemblies','materials','evidence'):
                    schema['properties'][key] = {'type':'object'}
                schema['$defs']['source']['properties']['evidence']['items'] = {}
                for key in ('source_files','input_sha256'):
                    schema['$defs']['metadata']['properties'][key] = {'type':'object'}
            else:
                schema['properties']['assemblies'] = {'type':'object'}
                self.blocks['equivalent_assembly'] = Draft202012Validator({
                    '$defs':schema['$defs'], '$ref':'#/$defs/assembly'})
            self.context[kind] = Draft202012Validator(schema)

    def check(self, kind, value, check):
        fingerprint = (kind, hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).digest())
        if fingerprint not in self.checked:
            check(value)
            self.checked.add(fingerprint)

    def validate(self, document):
        kind = document['kind']
        self.context[kind].validate(document)
        self.check('mass', document['mass_accounting'], validate_mass_contract)
        if kind == 'building_level_equivalent':
            for assembly in document['assemblies'].values():
                self.check('equivalent_assembly', assembly, self.blocks['equivalent_assembly'].validate)


@lru_cache(maxsize=1)
def profile_hash():
    return hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()


def pointer(value):
    return value.replace('~', '~0').replace('/', '~1')


def original_recipe(release, aid):
    a = release['assemblies'][aid]
    return [{'model': release['materials'][l['material_id']]['model'],
             'properties': copy.deepcopy(release['materials'][l['material_id']]['properties'])}
            for l in a['layers']]


@lru_cache(maxsize=1)
def residential_recipe_locators():
    return {a['id']: RESIDENTIAL_PATH.relative_to(ROOT).as_posix()+'#/records/'+pointer(rid)+f'/assemblies/{i}/layers'
            for rid, row in load_json(RESIDENTIAL_PATH)['records'].items()
            for i,a in enumerate(row['assemblies'])}


def source_quantity(operands, scope):
    """Evaluate pinned optional-coefficient rules, requiring known active operands."""
    try:
        if scope['kind'] == 'whole_dwelling':
            return number(operands.get('source_area_per_conditioned_floor_area'))*number(
                operands.get('source_conditioned_floor_area_m2'), positive=True)
        if operands.get('area_per_person_m2') not in (None, 0):
            raise ValueError('Unknown person-based mass scaling operand')
        result = 0.
        if operands.get('direct_area_m2') is not None:
            result += number(operands['direct_area_m2'])
        if operands.get('area_per_floor_area') is not None:
            result += number(operands['area_per_floor_area'])*number(operands.get('source_space_floor_area_m2'))
        return result*number(operands.get('source_multiplier'), positive=True)
    except ValueError as exc:
        raise ValueError('Invalid mass scaling/multiplier operand: '+str(exc)) from exc


def recipe_capacity(layers):
    fake = {'materials': {str(i): layer for i, layer in enumerate(layers)}}
    return sum(l['C'] for l in source_layers(fake, {'layers': [
        {'material_id': str(i)} for i in range(len(layers))]}))


def build_mass_contract(release, context_id, packet, *, components=None):
    """Use selected detailed rules and frozen native quantities, never unified JSON."""
    c = release['contexts'][context_id]
    profile = packet['profiles'].get(c['reference_id'])
    if profile is None:
        raise ValueError('Missing source mass profile: '+c['reference_id'])
    cfa = number(profile.get('counted_floor_area_m2'), positive=True)
    configuration = release['component_configurations'][c['configuration_id']]
    if components is not None:
        configuration = dict(configuration, components=components)
    location = PROFILE_PATH.relative_to(ROOT).as_posix()+'#/profiles/'+pointer(profile['id'])
    budgets = _mass_budgets(release, configuration, profile)
    for role, rows in budgets.items():
        for b in rows:
            aid = b['source_assembly_id']
            b.update(reference_area_m2=b['area_per_counted_floor_area']*cfa,
                     source_areal_capacity_J_m2_K=sum(l['C'] for l in source_layers(release, release['assemblies'][aid])),
                     source_locator=location+('/assembly_areas/'+pointer(aid) if 'assembly_areas' in profile else
                         '/'+{'InteriorFloor':'floor_inventory','InteriorWall':'wall_inventory'}[role]))
    entries, recipes = [], {}

    def add(aid, area, scope, operands, locator, layers, convention):
        area = number(area)
        if area == 0:
            return
        capacity = recipe_capacity(layers)
        recipe_locator = (PROFILE_PATH.relative_to(ROOT).as_posix()+'#/mass_recipes/'+pointer(aid)
                          if 'spaces' in profile else residential_recipe_locators()[aid])
        recipes[aid] = {'model': 'opaque_layers', 'layers': layers,
                        'capacity_J_m2_K': capacity, 'source_locator': recipe_locator,
                        'interpretation': 'Original source mass material layers; no equivalent fitting or added air films.'}
        entries.append({'id': stable_id('source-mass-quantity', {'profile': profile['id'], 'locator': locator}),
                        'recipe_id': aid, 'scope': scope,
                        'reference_area_m2': area, 'area_per_counted_floor_area': area/cfa,
                        'capacity_per_counted_floor_area_J_m2_K': area/cfa*capacity,
                        'source_operands': copy.deepcopy(operands), 'source_locator': locator,
                        'area_convention': convention})

    if 'spaces' in profile:
        for i, s in enumerate(profile['spaces']):
            for j, mass in enumerate(s['added_mass']):
                if mass['status'] != 'ready' or mass['recipe_id'] is None:
                    raise ValueError('Unknown source additional-mass quantity or recipe')
                aid = mass['recipe_id']
                if aid not in packet['mass_recipes']:
                    raise ValueError('Missing source additional-mass recipe')
                operands = {k: v for k,v in mass['source_operands'].items() if k != 'layers'}
                operands.update(source_space_floor_area_m2=s['source_floor_area_m2'],
                                source_multiplier=s['source_multiplier'])
                # An unset optional native coefficient is inactive by the pinned
                # OpenStudio API rule, not an unknown reported total quantity.
                expected = source_quantity(operands, {'kind':'source_space'})
                if not math.isclose(expected, number(mass['area_m2']), rel_tol=1e-8, abs_tol=1e-6):
                    raise ValueError('Source mass quantity disagrees with scaling/multiplier operands')
                add(aid, mass['area_m2'],
                    {'kind': 'source_space', 'source_space_name': s['name'], 'source_story': s['story'],
                     'native_building_type': s['program']['native_building_type'],
                     'native_space_type': s['program']['native_space_type'],
                     'counted_floor_area': s['counted_floor_area']},
                    operands, location+f'/spaces/{i}/added_mass/{j}',
                    [{'model': 'StandardOpaqueMaterial', 'properties': copy.deepcopy(p)} for p in packet['mass_recipes'][aid]],
                    'source InternalMass object area; source multiplier applied once')
    else:
        for assignment in configuration['components']['InteriorPartition']['assignments']:
            aid = assignment['assembly_id']
            q = profile['assembly_areas'][aid]
            add(aid, q['area_m2'], {'kind': 'whole_dwelling', 'counted_floor_area': True},
                {'source_area_per_conditioned_floor_area': q['area_per_counted_floor_area'],
                 'source_conditioned_floor_area_m2': cfa},
                location+'/assembly_areas/'+pointer(aid), original_recipe(release, aid),
                'source exposed partition area, both sides')

    mass = {
        'schema_version': '1.0.0', 'status': 'ready',
        'reference': {'profile_id': profile['id'], 'counted_floor_area_m2': cfa,
                      'quantity_basis': 'multiply normalized quantities by actual counted building floor area'},
        'floor_pair_policy': 'one physical slab; do not add both floor and ceiling capacity',
        'paired_surface_policy': {'canonical_side': 'InteriorFloor',
                                  'adjacent_ceiling': 'reverse the same canonical floor assembly',
                                  'unpaired_ceiling': 'use InteriorCeiling recipe'},
        'added_mass_policy': 'additional source furnishings/partition objects are separate from explicit surfaces',
        'removed_wall_policy': 'Restore only unrepresented InteriorWall capacity using source or equivalent recipes; exchange equivalence remains approximate',
        'residual_floor_policy': 'Restore only unrepresented InteriorFloor capacity; explicit slabs retain their capacity',
        'residual_policy': 'max(0, reference minus represented); report signed difference and excess; never subtract mass',
        'physical_inventory_profile_id': profile['id'],
        'paired_face_area_policy': 'mean_zone_weighted_faces',
        'reference_area_approximation': {
            'unequal_multiplier_pair_counts': {kind: sum(bool(item.get('approximation')) for item in profile.get(key, []))
                for kind,key in [('floor_pairs','floor_inventory'), ('wall_pairs','wall_inventory')]},
            'evidence_profile_id': profile['id'],
            'interpretation': 'Mean of multiplied face areas where multipliers differ; preserve the frozen source inventory. Residential inferred adiabatic floor/ceiling object quantities retain their source convention.'},
        'physical_capacity_budgets': budgets,
        'additional_mass': {'status': 'provided' if entries else 'known_zero', 'entries': entries,
                            'allocation_policy': 'Precomputed source-scope quantities normalized by building counted floor area; preserve source scopes. If absent in consumer geometry, require an explicit consumer allocation policy.',
                            'legacy_partition_selector_policy': 'InteriorPartition is a retained material selector. Instantiate additional mass from this inventory only; never instantiate both representations of the same source object.'},
        'recipes': dict(sorted(recipes.items())),
        'provenance': {'source_project': profile['provenance']['source_project'],
                       'source_revision': profile['provenance']['source_revision'],
                       'source_locator': location,
                       'source_file_sha256': {PROFILE_PATH.relative_to(ROOT).as_posix(): profile_hash(),
                            **({RESIDENTIAL_PATH.relative_to(ROOT).as_posix(): hashlib.sha256(RESIDENTIAL_PATH.read_bytes()).hexdigest()} if 'assembly_areas' in profile else {})},
                       'extraction_date': '2026-10-16',
                       'original_unit': 'm2, m3, SI material properties, and dimensionless source multipliers/scaling coefficients',
                       'original_value': {'counted_floor_area_m2': cfa, 'profile_provenance': copy.deepcopy(profile['provenance'])},
                       'transformation': 'Copy frozen source quantities; divide area and capacity by counted reference floor area. Use source multiplier once. Select wall/slab recipes with detailed source precedence.',
                       'interpretation_note': 'Quantities describe the selected source archetype, not a population weight or consumer geometry. Additional mass is independent of residual restoration.'},
    }
    validate_mass_contract(mass)
    return mass


def legacy_budgets(mass):
    return {role: [{k: row[k] for k in LEGACY_BUDGET_KEYS} for row in rows]
            for role,rows in mass['physical_capacity_budgets'].items()}


def validate_mass_contract(mass):
    validator('mass').validate(mass)
    cfa = number(mass['reference']['counted_floor_area_m2'], positive=True)
    used = set()
    for aid, recipe in mass['recipes'].items():
        for layer in recipe['layers']:
            validate_material(dict(layer['properties'], model=layer['model']))
        if not math.isclose(recipe_capacity(recipe['layers']), recipe['capacity_J_m2_K'], rel_tol=1e-9, abs_tol=1e-8):
            raise ValueError('Invalid source mass recipe capacity: '+aid)
    for entry in mass['additional_mass']['entries']:
        rid = entry['recipe_id']
        if rid not in mass['recipes']:
            raise ValueError('Orphan additional-mass recipe')
        used.add(rid)
        ratio = number(entry['area_per_counted_floor_area'])
        if not math.isclose(ratio*cfa, number(entry['reference_area_m2']), rel_tol=1e-9, abs_tol=1e-7):
            raise ValueError('Inconsistent additional-mass area normalization')
        if not math.isclose(source_quantity(entry['source_operands'], entry['scope']),
                            entry['reference_area_m2'], rel_tol=1e-8, abs_tol=1e-6):
            raise ValueError('Source mass quantity disagrees with scaling/multiplier operands')
        if not math.isclose(ratio*mass['recipes'][rid]['capacity_J_m2_K'], entry['capacity_per_counted_floor_area_J_m2_K'], rel_tol=1e-9, abs_tol=1e-7):
            raise ValueError('Inconsistent additional-mass capacity')
    if used != set(mass['recipes']):
        raise ValueError('Unused additional-mass recipe')
    expected = 'provided' if used else 'known_zero'
    if mass['additional_mass']['status'] != expected:
        raise ValueError('Inconsistent known-zero additional mass status')
    for rows in mass['physical_capacity_budgets'].values():
        for row in rows:
            ratio = number(row['area_per_counted_floor_area'])
            if not math.isclose(ratio*cfa, row['reference_area_m2'], rel_tol=1e-9, abs_tol=1e-7):
                raise ValueError('Inconsistent physical-mass reference area')
            if not math.isclose(ratio*row['source_areal_capacity_J_m2_K'], row['capacity_per_counted_floor_area_J_m2_K'], rel_tol=1e-9, abs_tol=1e-7):
                raise ValueError('Inconsistent physical-mass capacity')


def upgrade_detailed(document, mass, *, cache=None):
    output = copy.deepcopy(document)
    output['schema_version'] = '2.1.0'
    output['mass_accounting'] = copy.deepcopy(mass)
    validate_export(output, cache=cache)
    return output


def upgrade_unified(document, mass, *, cache=None):
    if document['mass_accounting']['physical_capacity_budgets'] != legacy_budgets(mass):
        raise ValueError('Shared mass budget differs from frozen equivalent source budget')
    q = document['components']['InternalMass'].get('quantity', {}).get('area_per_counted_floor_area', 0)
    total = sum(e['area_per_counted_floor_area'] for e in mass['additional_mass']['entries'])
    if not math.isclose(q, total, rel_tol=1e-9, abs_tol=1e-8):
        raise ValueError('Shared additional mass differs from frozen equivalent quantity')
    output = copy.deepcopy(document)
    output['schema_version'] = '1.2.0'
    output['mass_accounting'] = copy.deepcopy(mass)
    validate_export(output, cache=cache)
    return output


def validate_export(document, *, cache=None):
    if cache is None:
        validator(document['kind']).validate(document)
        validate_mass_contract(document['mass_accounting'])
    else:
        cache.validate(document)
    mass = document['mass_accounting']
    reference = document['source']['reference_variant_id'] if document['kind']=='construction_set' else document['reference_id']
    if reference != mass['reference']['profile_id']:
        raise ValueError('Mismatched source mass reference')
    if document['kind'] == 'construction_set':
        legacy = {k:v for k,v in document.items() if k != 'mass_accounting'}
        legacy['schema_version'] = '2.0.0'
        validate_set(legacy, cache=cache.legacy if cache else None)
        for rows in mass['physical_capacity_budgets'].values():
            for row in rows:
                if row['source_assembly_id'] not in document['assemblies']:
                    raise ValueError('Orphan detailed physical-mass source assembly')
                capacity = sum(l['C'] for l in source_layers(document, document['assemblies'][row['source_assembly_id']]))
                if not math.isclose(capacity, row['source_areal_capacity_J_m2_K'], rel_tol=1e-9, abs_tol=1e-7):
                    raise ValueError('Physical-mass budget capacity contradicts detailed source layers')
        for role, rows in mass['physical_capacity_budgets'].items():
            selected = {a['assembly_id'] for a in document['components'][role]['assignments']}
            if any(row['source_assembly_id'] not in selected for row in rows):
                raise ValueError('Physical mass budget does not use selected detailed assignments')
    else:
        for role, rows in [('InternalMass',mass['additional_mass']['entries']),
                           ('FloorDistributedMass',mass['physical_capacity_budgets']['InteriorFloor'])]:
            area = sum(row['area_per_counted_floor_area'] for row in rows)
            capacity = sum(row['capacity_per_counted_floor_area_J_m2_K'] for row in rows)
            component = document['components'][role]
            quantity = component.get('quantity', {}).get('area_per_counted_floor_area', 0)
            if not math.isclose(area, number(quantity), rel_tol=1e-9, abs_tol=1e-8):
                raise ValueError('Equivalent mass quantity contradicts shared inventory: '+role)
            if component['status'] == 'ready':
                aid = component['assembly_id']
                if aid not in document['assemblies']:
                    raise ValueError('Orphan equivalent mass recipe')
                layers = document['assemblies'][aid]['layers']
                areal = sum(number(l['C']) for l in layers)
                for layer in layers:
                    if layer['model']=='Material' and not math.isclose(layer['C'],
                            number(layer['thickness_m'],True)*number(layer['density_kg_m3'],True)*number(layer['specific_heat_J_kg_K'],True),
                            rel_tol=1e-9, abs_tol=1e-7):
                        raise ValueError('Equivalent material capacity is inconsistent')
                if not math.isclose(quantity*areal, capacity, rel_tol=1e-9, abs_tol=1e-7):
                    raise ValueError('Equivalent mass capacity contradicts shared inventory: '+role)
            elif capacity != 0 or area != 0:
                raise ValueError('Missing equivalent mass recipe for positive source quantity')
    # Encoding checks all numerical metadata as well as material fields.
    from scripts.construction_set_export import encoded
    encoded(document)


def capacity_residual(reference_J_K, represented_J_K):
    signed = number(reference_J_K)-number(represented_J_K)
    return {'signed_residual_J_K': signed, 'restoration_capacity_J_K': max(0, signed),
            'excess_capacity_J_K': max(0, -signed)}
