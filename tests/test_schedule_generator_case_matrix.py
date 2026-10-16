"""Qualified bounded matrix proofs; fixture identities never authorize release.

Each suite assembles fresh resources with the existing stdlib
build_apartment_resources helper, the tracked locked v0.7 predecessor and actual
locked source/qualification inputs. No old prepared directory is read. Exact
production inventories are archived test assets, with distinct raw/canonical
identities; historical source paths are metadata only. No native method or new
qualification capture runs, and existing authority preimages stay byte-exact.
Only ResourceSet.load is redirected for actual public generation; no scientific
predicate, source qualification, seed receipt or strict validator is patched.
"""
import copy
import hashlib
import inspect
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote
import zlib

from atlas_schedules import generate
from atlas_schedules.canonical import canonical
from atlas_schedules.contract import validate_bundle
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet, strict_json
from scripts import schedule_generator_case_matrix as adapter

ROOT = Path(__file__).resolve().parents[1]
UNIT, COM = 'unit-fixture', 'commercial-fixture'
ACTOR_FIELDS = ('actor_kind', 'instance_key', 'building_realization_id', 'unit_id',
                'stochastic_action', 'position', 'unit_seed')
FIXTURES = ROOT/'tests/fixtures/schedule_generator_case_matrix'
FIXTURE_MANIFEST = {'size_bytes': 3055, 'sha256': 'b7781a15cfd04230328def736f61935c3b12f8d4c1f3d6cf997e4ce409fa0c7c'}


def identity(value):
    blob = canonical(value)
    return {'size_bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}


def bytes_identity(blob):
    return {'size_bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}


def production_fixture_inputs():
    """Authenticate durable exact raw archives; never resolve historical paths."""
    raw = (FIXTURES/'manifest.json').read_bytes()
    assert bytes_identity(raw) == FIXTURE_MANIFEST
    manifest = strict_json(raw, 'case-matrix fixture manifest')
    assert manifest['schema_version'] == 'case-matrix-test-fixtures-1.0.0'
    assert [r['file'] for r in manifest['files']] == [
        'full-request.json.gz', 'resource-manifest.json.gz', 'r74-design-mapping.json.gz']
    values = []
    for entry in manifest['files']:
        blob = (FIXTURES/entry['file']).read_bytes()
        assert bytes_identity(blob) == entry['compressed'] and len(blob) <= 104857600
        decoder = zlib.decompressobj(16+zlib.MAX_WBITS)
        decoded = decoder.decompress(blob, entry['decoded_raw']['size_bytes']+1)
        assert decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
        assert bytes_identity(decoded) == entry['decoded_raw']
        value = strict_json(decoded, entry['file'])
        assert identity(value) == entry['canonical_content']
        values.append(value)
    assert {k: values[2][k] for k in ('schema_version', 'status')} == manifest['source_mapping']
    return values


def prepare_fixture_resources(destination):
    """Normal unittest setup, requiring the repository's locked CI source inputs."""
    from scripts.schedule_generator_apartment_authority import build_apartment_resources
    authority = ROOT/'data/schedule-generator/apartment/authority'
    def snapshot():
        return {p.name: bytes_identity(p.read_bytes()) for p in sorted(authority.glob('*.json'))}
    before = snapshot()
    assert len(before) == 253, 'Tracked authority preimages are a required fixture input'
    manifest = build_apartment_resources(destination)
    assert snapshot() == before, 'Fixture assembly changed tracked authority bytes/inventory'
    assert identity(manifest) == {'size_bytes': 925452,
        'sha256': 'b2af62dcda8814878f44df9f4334414a1503eec4343b46d1d9b1b562fbdf30af'}
    return ResourceSet(destination, manifest['resource_set_id'])


def descriptor(request, resources, mapping, expected, *, reference=None, cases=None):
    """Declare static obligations independently of any adapter-produced matrix."""
    result = {'schema_version': 'case-matrix-structure-descriptor-1.0.0',
              'request': identity(request), 'resource_manifest': identity(resources),
              'mapping': identity(mapping),
              'expected': copy.deepcopy(expected)}
    if reference is not None: result['full_reference'] = identity(reference)
    if cases is not None: result['case_bundles'] = {k: identity(v) for k, v in cases.items()}
    return result


def refreshed(desc, *, request=None, resources=None, mapping=None, reference=None, cases=None):
    """Refresh transport identities only; expected scientific obligations stay fixed."""
    result = copy.deepcopy(desc)
    for key, value in [('request', request), ('resource_manifest', resources),
                       ('mapping', mapping), ('full_reference', reference)]:
        if value is not None: result[key] = identity(value)
    if cases is not None: result['case_bundles'] = {k: identity(v) for k, v in cases.items()}
    return result


def source_objects(value):
    if isinstance(value, dict):
        if set(value) == {'path', 'sha256', 'locator', 'value'}: yield value
        for child in value.values(): yield from source_objects(child)
    elif isinstance(value, list):
        for child in value: yield from source_objects(child)


def caller_request(requirement):
    """Fact-only caller declaration following the durable caller-water fixtures.

    No source/native qualification is synthesized here. All water requirements,
    controls, methods and the complete unselected pool come from real resources.
    """
    pid = requirement['programme']['value']['id']
    unit = {'unit_id': 'u0', 'physical_id': 'caller-draw',
            'source_service_id': requirement['source_service_id'],
            'source_beneficiary_id': requirement['source_beneficiary_id'],
            'programme_ids': [pid], 'water_authority_programme_id': pid, 'floor_area_m2': 80.0}
    facts = {'building_realization_id': 'building-1', 'unit_inventory_id': 'caller-inventory-1',
             'units': [copy.deepcopy(unit)]}
    digest = hashlib.sha256(canonical(facts)).hexdigest()
    def claim(locator, value, unit=None):
        return {'source_revision': 'labelled-caller-contract-fixture',
                'source_path': 'contract-fixture/caller-facts.json', 'source_sha256': digest,
                'locator': locator, 'original_value': copy.deepcopy(value), 'original_unit': unit,
                'transformation': 'Caller fact retained in normalized m2', 'extraction_date': '2026-10-15',
                'interpretation_note': 'Fact-only caller authority, not source geometry or native certificate'}
    fields = list(unit)
    unit.update(multiplicity=1, area_evidence=[claim('/units/0/floor_area_m2', 80.0, 'm2')],
                identity_evidence=[claim('/building_realization_id', 'building-1'),
                                  claim('/unit_inventory_id', 'caller-inventory-1')]+
                                 [claim('/units/0/'+k, unit[k]) for k in fields if k != 'floor_area_m2'])
    inventory = {'authority': 'caller_declared_units', 'units': [unit]}
    real = {'mode': 'caller_unit_prototype_density_fixed_dhw', 'building_realization_id': 'building-1',
            'building_type': requirement['family'], 'template': requirement['template'],
            'unit_inventory_id': 'caller-inventory-1', 'unit_inventory': inventory,
            'unit_inventory_sha256': hashlib.sha256(canonical(inventory)).hexdigest()}
    basis = {'multiplicity': 1, 'extents': {'floor_area': {
        'value': 80.0, 'unit': 'm2', 'evidence': copy.deepcopy(unit['area_evidence'])}}}
    water = {'key': 'water-u0', 'owner_kind': 'physical_service',
             'physical_binding_kind': 'caller_unit_prototype_density_fixed_dhw',
             'building_realization_id': 'building-1', 'unit_id': 'u0', 'physical_id': 'caller-draw',
             'source_service_id': requirement['source_service_id'], 'operating_group': None,
             'inputs': {'water_method': 'source_fixed_apartment_dhw', 'source_geometry_departure': 'caller_unit_area'},
             'basis_bindings': copy.deepcopy(basis)}
    basis['extents']['floor_area']['evidence'] = {'field_evidence': copy.deepcopy(unit['area_evidence'])}
    apartment = {'key': 'view-u0-'+pid, 'owner_kind': 'program', 'program_id': pid,
                 'building_realization_id': 'building-1', 'unit_id': 'u0', 'operating_group': None,
                 'inputs': {'apartment_method': 'unit_occupancy_interior_lighting', 'N': 0},
                 'basis_bindings': basis}
    return real, [water, apartment]


def restaurant_request(resources):
    """Explicit physical operands from the durable public-v1.2 fixture pattern."""
    pid = 'program-76fabb7b85c683f4f7d8c873'
    recipe = resources.get('program', pid)['recipe']
    config = recipe['source_context']['source_hoo_configuration_id']
    kitchen = {'owner_kind': 'program', 'key': 'kitchen', 'program_id': pid,
               'inputs': recipe['bound_inputs'], 'operating_group': config,
               'basis_bindings': {}, 'service_links': {}}
    physical = []
    for req in recipe['required_service_links']:
        sid = req['source_service_id']; key = 'owner-'+sid; kitchen['service_links'][sid] = key
        record = resources.get('reference', 'physical-service__'+sid)
        variant = record['recipe']['configurations'][config]; basis = record['definition']['load']['basis']
        inputs = {'source_hoo_configuration_id': config, 'physical_fixture_evidence': {'caller': 'explicit source fixture'}}
        extent = 1; unit = '1'
        if basis == 'floor_area':
            ref = variant['native_source_physical_reference']; area = ref['floor_area_m2']; multiplier = ref['multiplier']
            extent = area*multiplier; unit = 'm2'
            inputs.update(fixture_floor_area_m2=area, fixture_space_multiplier=multiplier,
                          fixture_extent_evidence={'area': {'value': area, 'unit': 'm2', 'caller': 'explicit source area'},
                                                   'multiplier': {'value': multiplier, 'unit': '1', 'caller': 'explicit source multiplier'}})
        physical.append({'owner_kind': 'physical_service', 'physical_binding_kind': 'legacy_whole',
                         'key': key, 'source_service_id': sid, 'physical_id': 'fixture-'+sid,
                         'inputs': inputs, 'operating_group': config, 'basis_bindings': {'multiplicity': 1,
                         'extents': {basis: {'value': extent, 'unit': unit, 'evidence': {'caller': 'explicit source extent'}}}}})
    return kitchen, physical


def fixture(resources):
    manifest = resources.manifest
    stock_a, stock_b = [
        {'owner_kind': 'program', 'key': key, 'program_id': pid, 'operating_group': None,
         'inputs': resources.get('program', pid)['recipe']['bound_inputs'], 'basis_bindings': {}}
        for key, pid in [('stock-before', 'program-03fe19ed8968e605f4be3b8d'),
                         ('stock-after', 'program-e0993499165be6c7b5bf9efa')]]
    assert stock_a['inputs']['residents'] > 0 and stock_b['inputs']['residents'] == 0
    kitchen, physical = restaurant_request(resources)
    absolute_sid = 'service-26df36d04c21572b9838d63f'
    absolute_record = resources.get('reference', 'physical-service__'+absolute_sid)
    absolute_config = 'full_service_restaurant__90_1_2013__source'
    assert absolute_record['definition']['load']['basis'] == 'absolute'
    absolute = {'owner_kind': 'physical_service', 'physical_binding_kind': 'legacy_whole',
                'key': 'absolute-service', 'source_service_id': absolute_sid,
                'physical_id': 'absolute-physical-fixture', 'operating_group': 'absolute-group',
                'inputs': {'source_hoo_configuration_id': absolute_config,
                           'physical_fixture_evidence': {'caller': 'explicit bounded absolute fixture'}},
                'basis_bindings': {'multiplicity': 1, 'extents': {'absolute': {
                    'value': 1, 'unit': '1', 'evidence': {'caller': 'one explicit whole fixture'}}}}}
    req = resources.get('reference', 'caller-water-requirement__program-23458a6e125b4cee7f62bb42')
    real, caller = caller_request(req)
    apartment = caller[1]
    apartment['inputs'] = {'apartment_method': 'unit_occupancy_interior_lighting', 'N': 0}
    # A real Warehouse source parent and its original, non-zero source members.
    scope = resources.get('reference', 'm1-scope')
    zero_pid = 'program-e784bf91b3765d28c5d61368'
    zero_recipe = resources.get('program', zero_pid)['recipe']
    assert zero_recipe['resolved']['slots'] == []
    zero_slot = {'owner_kind': 'program', 'key': 'qualified-zero-slot-owner', 'program_id': zero_pid,
                 'inputs': copy.deepcopy(zero_recipe['bound_inputs']), 'basis_bindings': {},
                 'operating_group': 'zero-slot-group'}
    pid = next(c['program_id'] for c in scope['cases']
               if 'source_composition' in resources.get('program', c['program_id'])['recipe'])
    recipe = resources.get('program', pid)['recipe']
    parent = {'owner_kind': 'program', 'key': 'source-parent', 'program_id': pid,
              'inputs': dict(recipe['bound_inputs'], composition_basis_mode='source_reference_area_normalized'),
              'operating_group': 'parent-group', 'basis_bindings': {}}
    instances = [stock_a, kitchen, *physical, absolute, zero_slot, *caller, stock_b, parent]
    request = {'schema_version': '1.2.0', 'seed': 42, 'params': {
        'schema_version': '1.2.0', 'resource_set_id': resources.resource_set_id,
        'calendar': {'year': 2007, 'clock': 'local_standard_time', 'holidays': []},
        'instances': instances, 'building_realizations': [real]}}
    unit_keys = [stock_a['key'], *[i['key'] for i in caller], stock_b['key']]
    case_for = {i['key']: UNIT if i['key'] in unit_keys else COM for i in instances}
    children = []
    for n, member in enumerate(recipe['source_composition']['definition']['members']):
        key = 'source-member/'+quote(parent['key'], safe='')+'/'+str(n)+'/'+member['program_id']
        children.append({'key': key, 'program_id': member['program_id'], 'member_index': n,
                         'member': copy.deepcopy(member), 'case_id': COM})
        case_for[key] = COM
    expanded = [k for i in instances for k in
                ([c['key'] for c in children] if i is parent else [i['key']])]
    order = expanded + [parent['key']]
    actors = []
    for pos, (instance, kind, action) in enumerate([
            (stock_a, 'stock', 'generate'), (apartment, 'apartment_adapter', 'skip_n0'),
            (stock_b, 'stock', 'generate')]):
        actors.append({'actor_kind': kind, 'instance_key': instance['key'],
                       'building_realization_id': instance.get('building_realization_id'),
                       'unit_id': instance.get('unit_id'), 'stochastic_action': action,
                       'position': pos, 'unit_seed': 42*math.factorial(pos+1), 'case_id': UNIT})
    groups = [{'key': kitchen['operating_group'], 'ordered_members': [kitchen['key'], *[i['key'] for i in physical]], 'case_id': COM},
              {'key': 'absolute-group', 'ordered_members': [absolute['key']], 'case_id': COM},
              {'key': 'zero-slot-group', 'ordered_members': [zero_slot['key']], 'case_id': COM},
              {'key': 'parent-group', 'ordered_members': [c['key'] for c in children], 'case_id': COM}]
    context = {'family': req['family'], 'template': req['template'],
               'reference_calendar': request['params']['calendar']}
    pool = resources.get('reference', 'caller-water-qualification-set__'+hashlib.sha256(canonical(context)).hexdigest())
    pool_ids = [q['value']['programme_id'] for q in pool['value']['qualifications']]
    assert len(pool_ids) > 1  # unselected qualifications are real and retained.
    contexts = [{'case_id': UNIT, 'context_index': 0, 'request_realization': real,
                 'requested_keys': [i['key'] for i in caller],
                 'full_static_pool_programme_ids': pool_ids}]
    slots = []
    record_by_key = {}
    for i in instances:
        if i is parent: continue
        if i is caller[0]:
            definitions = [('hot_water_volume', 'fraction', 'load'),
                           ('water_target_temperature', 'C', 'control'),
                           ('water_sensible_fraction', 'fraction', 'control'),
                           ('water_latent_fraction', 'fraction', 'control')]
            for n, (slot, unit, kind) in enumerate(definitions):
                slots.append({'case_id': UNIT, 'owner_key': i['key'], 'slot_index': n,
                              'slot': slot, 'unit': unit, 'kind': kind,
                              'demands': [{'demand_id': req['source_service_id']}] if kind == 'load' else [],
                              'controls': [{'slot': slot}] if kind == 'control' else []})
        else:
            record_by_key[i['key']] = resources.get('program', i['program_id']) if i['owner_kind'] == 'program' else resources.get('reference', 'physical-service__'+i['source_service_id'])
    record_by_key[parent['key']] = resources.get('program', pid)
    for child in children: record_by_key[child['key']] = resources.get('program', child['program_id'])
    from atlas_schedules.generator import _group_context
    for group in groups:
        key = group['ordered_members'][0]; record = record_by_key[key]
        resolved = copy.deepcopy(record['recipe']['resolved'])
        if key == absolute['key']:
            context = record['recipe']['configurations'][absolute_config]['source_context']
        else: context = record['recipe']['source_context']
        resolved['inputs'] = {'source_context': dict(copy.deepcopy(context), year=2007, holidays=[])}
        group['exact_consumed_context'] = _group_context(resolved)
    for key, record in record_by_key.items():
        resolved = record['recipe']['resolved']
        for n, slot in enumerate(resolved['slots']):
            # Caller selected apartment water is a non-owning projection.
            if key == apartment['key'] and slot['slot'] == 'hot_water_volume': continue
            demands = [d for d in resolved['demands'] if d['slot'] == slot['slot']]
            controls = [c for c in resolved['controls'] if c['slot'] == slot['slot']]
            slots.append({'case_id': case_for[key], 'owner_key': key, 'slot_index': n,
                          **copy.deepcopy(slot), 'demands': copy.deepcopy(demands),
                          'controls': copy.deepcopy(controls)})
    parents = [{'case_id': COM, 'parent_key': parent['key'], 'children': children,
                'composition_id': recipe['source_composition']['composition_id']}]
    mapping = {'schema_version': 'r74-static-case-matrix-design-1.0.0',
               'status': 'DESIGN_ONLY_NOT_RELEASE_AUTHORITY', 'master_seed': 42,
               'resource_set_id': resources.resource_set_id, 'calendar': request['params']['calendar'],
               'requested_owners': [{'request_index': n, 'case_id': case_for[i['key']],
                                     'instance': i, 'generated_children': [c['key'] for c in children] if i is parent else []}
                                    for n, i in enumerate(instances)],
               'source_parents': parents, 'building_contexts': contexts,
               'native_physical_unit_sequence': actors, 'operating_groups': groups,
               'full_physical_member_generation_order': expanded,
               'full_source_parent_derivation_order': [parent['key']], 'full_constituent_order': order,
               'typed_slot_obligations': slots, 'dependency_edges': [],
               'all_resource_entries_retained_in_each_case': manifest['resources'], 'cases': []}
    for cid in (UNIT, COM):
        indices = [n for n, i in enumerate(instances) if case_for[i['key']] == cid]
        cq = copy.deepcopy(request)
        cq['params']['instances'] = [copy.deepcopy(instances[n]) for n in indices]
        cq['params']['building_realizations'] = [copy.deepcopy(real)] if cid == UNIT else []
        mapping['cases'].append({'case_id': cid, 'request_indices': indices, 'request': cq,
                                 'canonical_request_identity': identity(cq),
                                 'full_constituent_order_projection': [k for k in order if case_for[k] == cid]})
    # Independently declared static contract, never derived from adapter output.
    expected = {
        'case_order': [UNIT, COM], 'request_instance_order': [i['key'] for i in instances],
        'full_constituent_order': copy.deepcopy(order),
        'full_physical_member_generation_order': copy.deepcopy(expanded),
        'full_source_parent_derivation_order': [parent['key']],
        'native_physical_unit_sequence': copy.deepcopy(actors),
        'operating_groups': copy.deepcopy(groups), 'building_contexts': copy.deepcopy(contexts),
        'source_parents': copy.deepcopy(parents), 'typed_slot_obligations': copy.deepcopy(slots),
        'physical_owners': [copy.deepcopy(i) for i in instances if i['owner_kind'] == 'physical_service'],
        'resource_entries': copy.deepcopy(manifest['resources'])}
    with patch('atlas_schedules.generator.ResourceSet.load', return_value=resources):
        reference = generate(request['params'], 42)
    validate_bundle(reference)
    return request, manifest, mapping, reference, expected


class CaseMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix='case-matrix-fixture-')
        cls.addClassCleanup(temporary.cleanup)
        resources = prepare_fixture_resources(Path(temporary.name)/'resources')
        cls.request, cls.resources, cls.mapping, cls.reference, expected = fixture(resources)
        cls.desc = descriptor(cls.request, cls.resources, cls.mapping, expected, reference=cls.reference)
        cls.matrix = adapter._compile_structure(cls.request, cls.resources, cls.mapping, cls.desc)
        cls.cases = {cid: adapter._route_reference_structure(cls.reference, cls.matrix, cid, cls.desc)
                     for cid in (UNIT, COM)}
        print(json.dumps({'bounded_fixture': {
            'request': identity(cls.request), 'resource_manifest': identity(cls.resources),
            'mapping': identity(cls.mapping), 'reference': identity(cls.reference),
            'requested_owners': len(cls.request['params']['instances']),
            'output_owners': len(cls.reference['constituents']), 'slots': len(cls.reference['schedules']),
            'bindings': len(cls.reference['bindings']), 'native_actors': len(cls.mapping['native_physical_unit_sequence']),
            'static_pool_entries': len(cls.mapping['building_contexts'][0]['full_static_pool_programme_ids'])}}))

    def assertCode(self, code, fn, *args):
        with self.assertRaises(GeneratorError) as caught: fn(*args)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return caught.exception

    def compile_bad(self, mapping, code, request=None, resources=None):
        request = request or self.request; resources = resources or self.resources
        desc = refreshed(self.desc, mapping=mapping, request=request, resources=resources)
        self.assertCode(code, adapter._compile_structure, request, resources, mapping, desc)

    def test_private_structure_preserves_exact_order_and_all_obligations(self):
        before = canonical([self.request, self.resources, self.mapping])
        matrix = adapter._compile_structure(self.request, self.resources, self.mapping, self.desc)
        self.assertEqual(matrix['case_order'], [UNIT, COM])
        self.assertEqual(matrix['mapping'], self.mapping)
        self.assertEqual(before, canonical([self.request, self.resources, self.mapping]))
        self.assertEqual(matrix['mapping']['native_physical_unit_sequence'][1]['stochastic_action'], 'skip_n0')
        self.assertEqual({next(iter(i['basis_bindings']['extents']))
                          for i in self.request['params']['instances'] if i.get('physical_binding_kind') == 'legacy_whole'},
                         {'floor_area', 'absolute'})

    def test_private_reference_routes_roundtrip_canonically(self):
        before = identity(self.reference)
        before_cases = {k: identity(v) for k, v in self.cases.items()}
        objects = [canonical(o) for o in source_objects(self.reference)]
        for bundle in self.cases.values(): validate_bundle(bundle)
        desc = refreshed(self.desc, cases=self.cases)
        union = adapter._assemble_union_structure(self.cases, self.matrix, desc)
        validate_bundle(union)
        self.assertEqual(canonical(union), canonical(self.reference))
        self.assertEqual(before_cases, {k: identity(v) for k, v in self.cases.items()})
        self.assertEqual(before, identity(self.reference))
        self.assertEqual(objects, [canonical(o) for o in source_objects(self.reference)])
        # Returned mutable operands must have no aliases into callers.
        routed = adapter._route_reference_structure(self.reference, self.matrix, UNIT, self.desc)
        routed['schedules'][next(iter(routed['schedules']))]['values'][0] = -1
        self.assertEqual(before, identity(self.reference))
        parent = next(c for c in union['constituents'] if c['instance_key'] == 'source-parent')
        refs = parent['demands'][0]['evidence']['components']
        self.assertTrue(any(r['binding_index'] != 0 for r in refs))
        next(source_objects(union['constituents']))['value'] = {'caller_edit': True}
        self.assertEqual(before_cases, {k: identity(v) for k, v in self.cases.items()})

    def test_zero_cohort_chain_cannot_split_shift_or_reset(self):
        for field, value in [('position', 0), ('unit_seed', 42), ('stochastic_action', 'generate'), ('case_id', COM)]:
            mapping = copy.deepcopy(self.mapping); mapping['native_physical_unit_sequence'][1][field] = value
            with self.subTest(field=field): self.compile_bad(mapping, 'matrix_native_closure')
        mapping = copy.deepcopy(self.mapping); mapping['native_physical_unit_sequence'].pop(1)
        self.compile_bad(mapping, 'matrix_native_closure')

    def test_group_context_and_complete_static_pool_cannot_split(self):
        for field, code in [('operating_groups', 'matrix_group_closure'), ('building_contexts', 'matrix_context_closure')]:
            mapping = copy.deepcopy(self.mapping)
            if field == 'operating_groups': mapping[field][0]['ordered_members'].pop()
            else: mapping[field][0]['full_static_pool_programme_ids'].pop()
            self.compile_bad(mapping, code)
        mapping = copy.deepcopy(self.mapping); mapping['building_contexts'][0]['case_id'] = COM
        self.compile_bad(mapping, 'matrix_context_closure')
        broken = copy.deepcopy(self.reference)
        first_group = self.mapping['operating_groups'][0]['key']
        broken['generation']['operating_groups'][first_group]['context']['configuration_id'] = 'changed'
        self.assertCode('matrix_group_closure', adapter._route_reference_structure, broken,
                        self.matrix, COM, refreshed(self.desc, reference=broken))
        broken = copy.deepcopy(self.reference)
        broken['metadata']['building_realizations'][0]['method_qualification']['value']['qualifications'].pop()
        self.assertCode('matrix_context_closure', adapter._route_reference_structure, broken,
                        self.matrix, UNIT, refreshed(self.desc, reference=broken))

    def test_unknown_generation_field_fails_closed(self):
        broken = copy.deepcopy(self.reference); broken['generation']['future_rng'] = {}
        self.assertCode('matrix_generation_fields', adapter._route_reference_structure, broken,
                        self.matrix, UNIT, refreshed(self.desc, reference=broken))
        cases = copy.deepcopy(self.cases); cases[COM]['generation']['future_rng'] = {}
        self.assertCode('matrix_generation_fields', adapter._assemble_union_structure, cases,
                        self.matrix, refreshed(self.desc, cases=cases))

    def test_private_engines_need_no_source_io_or_jobs(self):
        denied = AssertionError('pure adapter attempted source I/O or external work')
        with patch('builtins.open', side_effect=denied), patch('pathlib.Path.open', side_effect=denied), \
                patch('socket.socket', side_effect=denied), patch('subprocess.Popen', side_effect=denied), \
                patch('atlas_schedules.resources.ResourceSet.load', side_effect=denied):
            matrix = adapter._compile_structure(self.request, self.resources, self.mapping, self.desc)
            result = adapter._route_reference_structure(self.reference, matrix, UNIT, self.desc)
            # Schema cache is warm from qualified fixture setup; this is a pure
            # adapter guard, not the later fresh-process cold certificate.
            validate_bundle(result)

    def test_sourceobjects_never_remap(self):
        # Real source objects include arbitrary source-owned values, even keys
        # named binding_index. No generated-index operation may interpret them.
        broken = copy.deepcopy(self.reference)
        obj = {'path': 'labelled-routing-sentinel.json', 'sha256': 'b'*64,
               'locator': '/', 'value': {'binding_index': 999999, 'binding_indices': [999999]}}
        broken['constituents'][0]['evidence'].append(obj)
        routed = adapter._route_reference_structure(broken, self.matrix, UNIT,
                                                    refreshed(self.desc, reference=broken))
        self.assertIn(obj, routed['constituents'][0]['evidence'])
        self.assertEqual(broken['constituents'][0]['evidence'][-1], obj)

    def test_crosscase_source_revision_value_and_physical_collision_fail_global(self):
        for mode in ('revision', 'value', 'field_revision', 'physical'):
            cases = copy.deepcopy(self.cases)
            if mode == 'physical':
                a = next(c for c in cases[UNIT]['constituents'] if c['owner_kind'] == 'physical_service')
                b = next(c for c in cases[COM]['constituents'] if c['owner_kind'] == 'physical_service')
                b['physical_id'] = a['physical_id']
                code = 'matrix_physical_collision'
            else:
                obj = next(source_objects(cases[UNIT]['constituents']))
                other = copy.deepcopy(obj)
                if mode == 'revision': other['sha256'] = 'f'*64
                elif mode == 'value': other['value'] = {'altered': True}
                else: other = {'source_path': obj['path'], 'source_sha256': 'f'*64}
                cases[COM]['constituents'][0]['evidence'].append(other)
                code = 'matrix_source_conflict'
            with self.subTest(mode=mode):
                self.assertCode(code, adapter._assemble_union_structure, cases, self.matrix,
                                refreshed(self.desc, cases=cases))

    def test_all_slots_and_members_required_even_when_weight_zero(self):
        mapping = copy.deepcopy(self.mapping); mapping['typed_slot_obligations'].pop()
        self.compile_bad(mapping, 'matrix_slot_closure')
        mapping = copy.deepcopy(self.mapping); mapping['source_parents'][0]['children'].pop()
        self.compile_bad(mapping, 'matrix_parent_closure')
        cases = copy.deepcopy(self.cases)
        owner = cases[COM]['constituents'][-1]; owner['generation']['members'][0]['weight'] = 0
        owner['schedule_ids'].pop(next(iter(owner['schedule_ids'])))
        self.assertCode('matrix_slot_closure', adapter._assemble_union_structure, cases,
                        self.matrix, refreshed(self.desc, cases=cases))
        cases = copy.deepcopy(self.cases)
        owner = cases[COM]['constituents'][-1]; owner['generation']['members'][0]['weight'] = 0
        owner['generation']['members'].pop()
        self.assertCode('matrix_parent_closure', adapter._assemble_union_structure, cases,
                        self.matrix, refreshed(self.desc, cases=cases))

    def streamed(self, cases):
        pieces = adapter._stream_union_structure(cases, self.matrix, refreshed(self.desc, cases=cases))
        return list(pieces)

    def test_streamed_union_pieces_concatenate_to_assembled_union(self):
        before = {k: identity(v) for k, v in self.cases.items()}
        pieces = self.streamed(self.cases)
        assembled = adapter._assemble_union_structure(self.cases, self.matrix, refreshed(self.desc, cases=self.cases))
        joined = b''.join(blob for _, blob in pieces)
        self.assertEqual(joined, canonical(assembled))
        self.assertEqual(joined, canonical(self.reference))
        self.assertEqual(before, {k: identity(v) for k, v in self.cases.items()})
        paths = [path for path, _ in pieces]
        self.assertEqual((paths[0], paths[-1]), ('', ''))
        self.assertEqual([p for p in paths if p.startswith('/constituents/')],
                         ['/constituents/%d' % n for n in range(len(self.reference['constituents']))])
        self.assertEqual([p for p in paths if p.startswith('/bindings/')],
                         ['/bindings/%d' % n for n in range(len(self.reference['bindings']))])
        self.assertEqual([p for p in paths if p.startswith('/schedules/')],
                         ['/schedules/'+s.replace('~', '~0').replace('/', '~1') for s in sorted(self.reference['schedules'])])
        members = ([self.reference[k] for k in ('metadata', 'generation')] + self.reference['constituents'] +
                   self.reference['bindings'] + list(self.reference['schedules'].values()))
        self.assertLessEqual(max(len(blob) for _, blob in pieces), max(len(canonical(m)) for m in members) + 256)

    def test_streamed_union_keeps_sourceobjects_and_never_aliases_cases(self):
        cases = copy.deepcopy(self.cases)
        obj = {'path': 'labelled-routing-sentinel.json', 'sha256': 'b'*64,
               'locator': '/', 'value': {'binding_index': 999999, 'binding_indices': [999999]}}
        cases[COM]['constituents'][-1]['evidence'].append(obj)
        before = {k: identity(v) for k, v in cases.items()}
        joined = b''.join(blob for _, blob in self.streamed(cases))
        assembled = adapter._assemble_union_structure(cases, self.matrix, refreshed(self.desc, cases=cases))
        self.assertEqual(joined, canonical(assembled))
        self.assertIn(canonical(obj)[:-1], joined)
        self.assertEqual(before, {k: identity(v) for k, v in cases.items()})

    def test_streamed_union_runs_every_union_check_before_first_piece(self):
        def mutate(mode):
            cases = copy.deepcopy(self.cases)
            if mode == 'physical':
                a = next(c for c in cases[UNIT]['constituents'] if c['owner_kind'] == 'physical_service')
                b = next(c for c in cases[COM]['constituents'] if c['owner_kind'] == 'physical_service')
                b['physical_id'] = a['physical_id']
            elif mode in ('revision', 'value'):
                obj = next(source_objects(cases[UNIT]['constituents'])); other = copy.deepcopy(obj)
                if mode == 'revision': other['sha256'] = 'f'*64
                else: other['value'] = {'altered': True}
                cases[COM]['constituents'][0]['evidence'].append(other)
            elif mode == 'generation': cases[COM]['generation']['future_rng'] = {}
            elif mode == 'slot':
                owner = cases[COM]['constituents'][-1]; owner['schedule_ids'].pop(next(iter(owner['schedule_ids'])))
            elif mode == 'schedule':
                sid = next(iter(cases[UNIT]['schedules'])); cases[COM]['schedules'][sid] = cases[UNIT]['schedules'][sid]
            elif mode == 'metadata': cases[COM]['metadata']['calendar'] = {'changed': True}
            return cases
        expected = {'physical': 'matrix_physical_collision', 'revision': 'matrix_source_conflict',
                    'value': 'matrix_source_conflict', 'generation': 'matrix_generation_fields',
                    'slot': 'matrix_slot_closure', 'schedule': 'matrix_slot_closure',
                    'metadata': 'matrix_context_closure'}
        for mode, code in expected.items():
            cases = mutate(mode)
            with self.subTest(mode=mode):
                self.assertCode(code, adapter._stream_union_structure, cases, self.matrix,
                                refreshed(self.desc, cases=cases))
                self.assertCode(code, adapter._assemble_union_structure, cases, self.matrix,
                                refreshed(self.desc, cases=cases))

    def test_streamed_union_matches_gzip_reference_and_reports_a_changed_value(self):
        import gzip
        from scripts import schedule_generator_case_matrix_stream as comparer
        with tempfile.TemporaryDirectory(prefix='case-matrix-reference-') as folder:
            path = Path(folder)/'reference.json.gz'
            path.write_bytes(gzip.compress(canonical(self.reference), mtime=0))
            declared = {'compressed': bytes_identity(path.read_bytes()), 'decoded': identity(self.reference)}
            result = comparer.compare_canonical_stream(self.streamed(self.cases), path, **declared)
            self.assertEqual((result['status'], result['first_difference']), ('MATCH', None))
            self.assertEqual(result['reference']['decoded'], identity(self.reference))
            cases = copy.deepcopy(self.cases)
            sid = sorted(cases[COM]['schedules'])[0]; values = cases[COM]['schedules'][sid]['values']
            values[100] = values[100] + 1.0
            result = comparer.compare_canonical_stream(self.streamed(cases), path, **declared)
            self.assertEqual(result['status'], 'MISMATCH')
            self.assertEqual(result['first_difference']['path'], '/schedules/'+sid.replace('~', '~0').replace('/', '~1'))

    def test_public_stream_rejects_non_authoritative_fixture(self):
        self.assertEqual(list(inspect.signature(adapter.stream_original_union).parameters), ['case_bundles', 'matrix'])
        with patch.object(adapter, '_stream_union_structure', side_effect=AssertionError('admission bypass')):
            self.assertCode('matrix_admission', adapter.stream_original_union, self.cases, self.matrix)

    def test_public_compile_rejects_non_authoritative_fixture(self):
        for altered in ('fixture', 'version', 'identity', 'mapping', 'pin'):
            mapping = copy.deepcopy(self.mapping)
            if altered == 'version': mapping['schema_version'] = '9.0.0'
            if altered == 'identity': mapping.pop('resource_set_id')
            if altered == 'mapping': mapping['cases'].reverse()
            if altered == 'pin': mapping['source_pins'] = {'current_code': 'changed'}
            with self.subTest(altered=altered), patch.object(adapter, '_compile_structure', side_effect=AssertionError('admission bypass')):
                self.assertCode('matrix_admission', adapter.compile_case_matrix, self.request, self.resources, mapping)

    def test_public_route_rejects_non_authoritative_fixture(self):
        for change in ({}, {'schema_version': '9.0.0'}, {'production_identity': {}}, {'case_order': []}):
            matrix = copy.deepcopy(self.matrix); matrix.update(change)
            with patch.object(adapter, '_route_reference_structure', side_effect=AssertionError('admission bypass')):
                self.assertCode('matrix_admission', adapter.route_reference_case, self.reference, matrix, UNIT)

    def test_public_union_rejects_non_authoritative_fixture(self):
        with patch.object(adapter, '_assemble_union_structure', side_effect=AssertionError('admission bypass')):
            self.assertCode('matrix_admission', adapter.assemble_original_union, self.cases, self.matrix)

    def test_production_admission_has_no_caller_override(self):
        self.assertEqual(list(inspect.signature(adapter.compile_case_matrix).parameters),
                         ['full_request', 'resource_manifest', 'mapping'])
        self.assertEqual(list(inspect.signature(adapter.route_reference_case).parameters),
                         ['full_reference', 'matrix', 'case_id'])
        self.assertEqual(list(inspect.signature(adapter.assemble_original_union).parameters), ['case_bundles', 'matrix'])
        with patch.dict('os.environ', {'CASE_MATRIX_TEST': '1', 'CASE_MATRIX_SKIP_ADMISSION': '1'}):
            self.assertCode('matrix_admission', adapter.compile_case_matrix, self.request, self.resources, self.mapping)


class ProductionAdmissionTests(unittest.TestCase):
    """Static admitted inventory only; never decode or generate the full graph."""
    @classmethod
    def setUpClass(cls):
        values = production_fixture_inputs()
        cls.request, cls.resources, cls.mapping = values
        cls.matrix = adapter.compile_case_matrix(*values)

    def assertAdmission(self, fn, *args):
        with self.assertRaises(GeneratorError) as caught: fn(*args)
        self.assertEqual(caught.exception.code, 'matrix_admission', str(caught.exception))
        return caught.exception

    def test_exact_static_production_matrix_compiles_without_execution(self):
        self.assertEqual(self.matrix['case_order'], [
            'unit-chain-and-caller-closure', 'commercial-group-and-source-parent-closure'])
        self.assertEqual(len(self.matrix['mapping']['full_constituent_order']), 463)
        self.assertEqual(len(self.matrix['mapping']['typed_slot_obligations']), 2754)

    def test_changed_production_input_content_and_pins_fail_before_engine(self):
        for target in ('request', 'resource_manifest', 'mapping', 'mapping_version', 'code_pin', 'missing_identity'):
            request = copy.deepcopy(self.request); resources = copy.deepcopy(self.resources); mapping = copy.deepcopy(self.mapping)
            expected_path = 'mapping'
            if target == 'request': request['seed'] += 1; expected_path = 'request'
            elif target == 'resource_manifest': resources['resources'].pop(); expected_path = 'resource_manifest'
            elif target == 'mapping': mapping['cases'].reverse()
            elif target == 'mapping_version': mapping['schema_version'] = '9.0.0'
            elif target == 'code_pin': mapping['source_pins']['current_code'] = 'changed'
            else: mapping.pop('request_identity')
            with self.subTest(target=target), patch.object(adapter, '_compile_structure', side_effect=AssertionError('admission bypass')):
                error = self.assertAdmission(adapter.compile_case_matrix, request, resources, mapping)
                self.assertEqual(error.path, '/case_matrix/'+expected_path)

    def test_recompiled_matrix_admission_rejects_changed_provenance_and_inventory(self):
        for field in ('schema_version', 'production_provenance', 'expected', 'case_order', 'input_identities'):
            matrix = copy.deepcopy(self.matrix); matrix[field] = None
            with self.subTest(field=field), patch.object(adapter, '_route_reference_structure', side_effect=AssertionError('route bypass')), patch.object(adapter, '_assemble_union_structure', side_effect=AssertionError('union bypass')), patch.object(adapter, '_stream_union_structure', side_effect=AssertionError('stream bypass')):
                self.assertAdmission(adapter.route_reference_case, {}, matrix, 'unit-chain-and-caller-closure')
                self.assertAdmission(adapter.assemble_original_union, {}, matrix)
                self.assertAdmission(adapter.stream_original_union, {}, matrix)


if __name__ == '__main__': unittest.main()
