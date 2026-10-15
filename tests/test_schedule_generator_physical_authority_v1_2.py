"""Labelled source-structure fixtures, never production/native qualification."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet, write_resources


ROOT = Path(__file__).resolve().parents[1]


def source(value, locator='/0', path='contract-fixture.json'):
    return {'path': path, 'sha256': 'a'*64, 'locator': locator, 'value': copy.deepcopy(value)}


def evidence():
    return [{'source_revision': 'labelled-contract-fixture', 'source_path': 'contract-fixture.json',
             'source_sha256': 'a'*64, 'locator': '/0', 'original_value': 'retained',
             'original_unit': None, 'transformation': 'none', 'extraction_date': '2026-10-15',
             'interpretation_note': 'Structural fixture only; no native or ready-family certificate'}]


CENSUS_FIELDS = ('role_id', 'source_order', 'source_service_id', 'source_path_id', 'role_kind',
                 'source_space', 'geometry_operands')


def census(records):
    """Test extraction artifact; independent of aliases or generated owners."""
    records['geometry'] = source({'source_geometry': source({'original_geometry': 'whole'}, path='source-geometry.osm'),
        'fixture_role_census': [{k: copy.deepcopy(r[k]) for k in CENSUS_FIELDS}
                                for r in records['ordered_fixture_roles']], 'evidence': evidence()},
        path='labelled-census-extraction.json')


def consumed():
    return source({'calendar': {'year': 2007, 'clock': 'local_standard_time', 'holidays': []},
        'source_resources': [source({'resource': 'locked'})], 'caller_policy': source({'error_on_out_of_order': False}),
        'object_order': ['A'], 'people': source({'all_people': []}),
        'registration': source({'all_programme_and_water_slots': []}), 'fixed_companions': source({'all_companions': []})})


def fixture():
    load = {'demand_id': 'water', 'service_id': 'water', 'quantity': 'hot_water_volume',
            'scope': 'program_service', 'basis': 'floor_area', 'unit': 'm3/s/m2',
            'value': 2e-8, 'schedule_id': 'rules', 'status': 'known', 'evidence_id': 'ev',
            'thermal_effects': {}, 'zone_heat_assignment': 'unresolved', 'required_inputs': ['floor_area']}
    service = {'id': 'water', 'path_id': 'Fixture|2013|main', 'building_type': 'Fixture',
               'template': '2013', 'beneficiary_program_ids': ['source-leaf'],
               'ownership': 'instantiate_once', 'assignment': 'consumer_host_when_applicable',
               'evidence_ids': ['ev'], 'load': dict(load, scope='building_service')}
    programme = {'id': 'leaf', 'source_id': 'source-leaf', 'building_type': 'Fixture',
                 'template': '2013', 'evidence_view': 'source', 'loads': [load], 'service_ids': ['water']}
    role = {'role_id': 'role-a', 'source_order': 0, 'source_service_id': 'water',
            'source_path_id': service['path_id'], 'role_kind': 'source_space_fixture',
            'service_definition': source(service, '/services/0'), 'source_space': {'name': 'A', 'handle': 'locked-A'},
            'geometry_operands': {'floor_area_m2': 10, 'space_multiplier': 2, 'zone_multiplier': 7,
                                  'evidence': evidence()}, 'source_basis': 'floor_area',
            'schedule_authority': {'kind': 'canonical_ruleset', 'canonical_schedule': source({'id': 'rules', 'rules': []})},
            'evidence': evidence()}
    records = {'inventory_id': 'labelled', 'family': 'Fixture', 'template': '2013', 'evidence_view': 'source',
            'geometry': source({'original_geometry_receipt': 'locked'}), 'ordered_fixture_roles': [role],
            'programmes': [source(programme, '/programmes/0')], 'compositions': [],
            'method_references': [source({'program_id': 'leaf', 'source_hoo_configuration_id': 'source-context',
                                          'context_evidence_view': 'source', 'method_consumed_context': consumed(),
                                          'original_method': source({'whole_original_method': 'retained'}), 'evidence': evidence()})],
            'evidence': evidence()}
    census(records)
    return records


def compilers():
    from scripts.schedule_generator_physical_sets import compile_exact_inventory, compile_exact_requirements
    return compile_exact_inventory, compile_exact_requirements


def component_fixture():
    records = fixture(); leaf = records['programmes'][0]['value']
    component = {'program_id': 'leaf', 'weight': 0, 'load': copy.deepcopy(leaf['loads'][0])}
    parent = {'id': 'parent', 'source_id': 'source-parent', 'building_type': 'Fixture', 'template': '2013',
              'evidence_view': 'reviewed', 'composition_id': 'mix', 'service_ids': [],
              'loads': [{'quantity': 'hot_water_volume', 'source_components': [component], 'value': 999}]}
    records['programmes'].append(source(parent, '/programmes/1'))
    records['compositions'] = [source({'id': 'mix', 'building_type': 'Fixture', 'template': '2013',
        'evidence_view': 'reviewed', 'members': [{'program_id': 'leaf', 'source_program_id': 'source-leaf',
                                               'represented_area_m2': 20, 'weight': 0}]})]
    records['method_references'].append(source({'program_id': 'parent', 'source_hoo_configuration_id': 'reviewed-context',
        'context_evidence_view': 'reviewed', 'method_consumed_context': consumed(),
        'original_method': source({'whole_original_method': 'parent'}), 'evidence': evidence()}))
    return records


class PhysicalAuthorityTests(unittest.TestCase):
    def test_compilers_and_runtime_resolvers_exist(self):
        from scripts.schedule_generator_physical_sets import compile_child_variant
        from atlas_schedules.physical_sets import resolve_exact_authority, resolve_child_variant
        self.assertTrue(all(callable(f) for f in (*compilers(), compile_child_variant,
                                                 resolve_exact_authority, resolve_child_variant)))

    def test_build_join_preserves_independent_c5_inventory_and_reproducible_authority(self):
        from scripts.schedule_generator_build import compile_exact_authority_resources
        records = fixture()
        packaged = {('program', 'leaf'): {'recipe': {'required_service_links': [
            {'required': True, 'source_channel': 'hot_water_volume', 'source_service_id': 'unrelated-c5',
             'original_demand': {'complete_original': 'retained'}, 'evidence': {'original': 'retained'}}]}}}
        original_links = copy.deepcopy(packaged['program', 'leaf']['recipe']['required_service_links'])
        compile_exact_authority_resources(packaged, records)
        recipe = packaged['program', 'leaf']['recipe']
        self.assertEqual(recipe['required_service_links'], original_links)
        self.assertEqual(recipe['required_service_sets'][0]['source_service_id'], 'water')
        self.assertIn(('reference', 'physical-fixture-inventory__labelled'), packaged)
        self.assertIn(('reference', recipe['exact_source_authority']['requirements_key']), packaged)
        self.assertNotIn(('reference', recipe['exact_source_authority']['qualification_key']), packaged)
        before = canonical({str(k): v for k, v in packaged.items()})
        compile_exact_authority_resources(packaged, records)
        self.assertEqual(canonical({str(k): v for k, v in packaged.items()}), before)
        changed = copy.deepcopy(packaged)
        changed['program', 'leaf']['recipe']['required_service_links'][0]['source_service_id'] = 'water'
        with self.assertRaises(GeneratorError): compile_exact_authority_resources(changed, records)

    def test_complete_order_includes_zero_and_unallocated_absolute_and_distinct_hashes(self):
        compile_inventory, compile_requirements = compilers()
        records = fixture(); second = copy.deepcopy(records['ordered_fixture_roles'][0])
        second.update(role_id='zero-role', source_order=1)
        second['source_space'] = {'name': 'B', 'handle': 'locked-B'}
        # A true zero schedule remains a positive-magnitude role.
        second['schedule_authority']['canonical_schedule']['value']['rules'] = [{'value': 0}]
        # Same SID must carry the exact same schedule authority, even for zero.
        records['ordered_fixture_roles'][0]['schedule_authority'] = copy.deepcopy(second['schedule_authority'])
        third = copy.deepcopy(second); third.update(role_id='unallocated', source_order=2,
            source_service_id='absolute', source_path_id='Fixture|2013|absolute', role_kind='absolute_fixture',
            source_space=None, source_basis='absolute')
        third['service_definition']['value'].update(id='absolute', path_id=third['source_path_id'], beneficiary_program_ids=[])
        third['service_definition']['value']['load'].update(demand_id='absolute', service_id='absolute',
            basis='absolute', unit='m3/s')
        third['geometry_operands'].update(floor_area_m2=None, space_multiplier=None, zone_multiplier=None)
        records['ordered_fixture_roles'] += [second, third]
        census(records)
        inventory = compile_inventory(records); requirements = compile_requirements(records, inventory)
        self.assertEqual([r['role_id'] for r in inventory['payload']['roles']], ['role-a', 'zero-role', 'unallocated'])
        self.assertEqual([r['consumed_extent']['value'] for r in inventory['payload']['roles']], [20, 20, 1])
        self.assertEqual(requirements[0]['expected_role_ids'], ['role-a', 'zero-role'])
        self.assertEqual(inventory['inventory_sha256'], hashlib.sha256(canonical(inventory['payload'])).hexdigest())
        self.assertNotEqual(inventory['inventory_sha256'], inventory['payload']['geometry']['sha256'])
        self.assertNotEqual(inventory['inventory_sha256'], hashlib.sha256(canonical(inventory)).hexdigest())
        self.assertEqual(records['ordered_fixture_roles'][0]['geometry_operands']['zone_multiplier'], 7)
        omitted = copy.deepcopy(records)
        omitted['ordered_fixture_roles'].pop(1)
        omitted['ordered_fixture_roles'][1]['source_order'] = 1
        with self.assertRaises(GeneratorError): compile_inventory(omitted)

    def test_source_order_identity_cardinality_and_unknown_input_reject(self):
        compile_inventory, _ = compilers()
        for mutation in ('order', 'duplicate', 'sid', 'basis', 'null_area', 'bool_multiplier', 'extra', 'unknown', 'missing_census'):
            records = fixture(); role = records['ordered_fixture_roles'][0]
            if mutation == 'order': role['source_order'] = 1
            if mutation == 'duplicate': records['ordered_fixture_roles'].append(copy.deepcopy(role))
            if mutation == 'sid': role['source_service_id'] = 'wrong'
            if mutation == 'basis': role['source_basis'] = 'absolute'
            if mutation == 'null_area': role['geometry_operands']['floor_area_m2'] = None
            if mutation == 'bool_multiplier': role['geometry_operands']['space_multiplier'] = True
            if mutation == 'extra': role['caller_alias'] = 'not-authority'
            if mutation == 'unknown': records['aliases'] = ['role-a']
            if mutation == 'missing_census': records['geometry']['value'].pop('fixture_role_census')
            with self.subTest(mutation=mutation), self.assertRaises(GeneratorError): compile_inventory(records)

    def test_malformed_entire_source_objects_fail_with_structured_error(self):
        compile_inventory, compile_requirements = compilers()
        for mutation in ('schedule_array', 'programme_array', 'method_array', 'composition_array',
                         'loads_scalar', 'load_array', 'relation_scalar', 'composition_id_array', 'method_id_array'):
            records = fixture(); inv = compile_inventory(records)
            if mutation == 'schedule_array': records['ordered_fixture_roles'][0]['schedule_authority']['canonical_schedule']['value'] = []
            if mutation == 'programme_array': records['programmes'][0]['value'] = []
            if mutation == 'method_array': records['method_references'][0]['value'] = []
            if mutation == 'composition_array': records['compositions'] = [source([])]
            if mutation == 'loads_scalar': records['programmes'][0]['value']['loads'] = True
            if mutation == 'load_array': records['programmes'][0]['value']['loads'] = [[]]
            if mutation == 'relation_scalar': records['programmes'][0]['value']['service_ids'] = True
            if mutation == 'composition_id_array': records['compositions'] = [source({'id': []})]
            if mutation == 'method_id_array': records['method_references'][0]['value']['program_id'] = []
            with self.subTest(mutation=mutation), self.assertRaises(GeneratorError): compile_requirements(records, inv)
        for malformed in (None, False, 1, 'leaf', {}, [], [None], [False], [1], ['leaf'], [[]]):
            records = component_fixture(); inv = compile_inventory(records)
            records['programmes'][1]['value']['loads'][0]['source_components'] = malformed
            original = copy.deepcopy(records)
            with self.subTest(source_components=malformed):
                with self.assertRaises(GeneratorError) as caught: compile_requirements(records, inv)
                self.assertEqual(caught.exception.code, 'source_integrity')
                self.assertIn('/source_components', caught.exception.path)
                self.assertEqual(records, original)
        for field in ('program_id', 'load', 'weight'):
            for malformed in (None, [], {}, True, ''):
                records = component_fixture(); inv = compile_inventory(records)
                records['programmes'][1]['value']['loads'][0]['source_components'][0][field] = malformed
                original = copy.deepcopy(records)
                with self.subTest(component_field=field, value=malformed):
                    with self.assertRaises(GeneratorError) as caught: compile_requirements(records, inv)
                    self.assertEqual(caught.exception.code, 'source_integrity')
                    self.assertIn('/source_components/0/'+field, caught.exception.path)
                    self.assertEqual(records, original)
        for field in ('demand_id', 'service_id', 'schedule_id'):
            records = component_fixture(); inv = compile_inventory(records)
            records['programmes'][1]['value']['loads'][0]['source_components'][0]['load'][field] = ['not-an-id']
            with self.subTest(load_id=field):
                with self.assertRaises(GeneratorError) as caught: compile_requirements(records, inv)
                self.assertEqual(caught.exception.code, 'source_integrity')
                self.assertIn('/source_components/0/load/'+field, caught.exception.path)
        for malformed in (None, False, 1, 'leaf', {}, [], [None], [False], [1], ['leaf'], [[]]):
            records = component_fixture(); inv = compile_inventory(records)
            records['compositions'][0]['value']['members'] = malformed
            original = copy.deepcopy(records)
            with self.subTest(composition_members=malformed):
                with self.assertRaises(GeneratorError) as caught: compile_requirements(records, inv)
                self.assertEqual(caught.exception.code, 'source_integrity')
                self.assertIn('/members', caught.exception.path)
                self.assertEqual(records, original)
        for field in ('program_id', 'source_program_id', 'represented_area_m2', 'weight'):
            for malformed in (None, [], {}, True, ''):
                records = component_fixture(); inv = compile_inventory(records)
                records['compositions'][0]['value']['members'][0][field] = malformed
                with self.subTest(member_field=field, value=malformed):
                    with self.assertRaises(GeneratorError) as caught: compile_requirements(records, inv)
                    self.assertEqual(caught.exception.code, 'source_integrity')
                    self.assertIn('/members/0/'+field, caught.exception.path)
        for malformed in (None, [], {}, True, ''):
            records = component_fixture(); inv = compile_inventory(records)
            records['programmes'][1]['value']['composition_id'] = malformed
            with self.subTest(composition_id=malformed):
                with self.assertRaises(GeneratorError) as caught: compile_requirements(records, inv)
                self.assertEqual(caught.exception.code, 'source_integrity')
                self.assertIn('/composition_id', caught.exception.path)

    def test_entire_original_load_and_entire_service_relation_are_separate_branches(self):
        compile_inventory, compile_requirements = compilers()
        records = fixture(); inv = compile_inventory(records); req = compile_requirements(records, inv)[0]
        self.assertEqual(req['original_demand']['value'], records['programmes'][0]['value']['loads'][0])
        self.assertEqual(req['kind'], 'original_programme_demand')
        for mutation in ('equal_value_forged_load', 'beneficiary', 'schedule'):
            changed = copy.deepcopy(records)
            if mutation == 'equal_value_forged_load': changed['programmes'][0]['value']['loads'][0]['status'] = 'invented'
            if mutation == 'beneficiary': changed['programmes'][0]['value']['source_id'] = 'foreign'
            if mutation == 'schedule': changed['ordered_fixture_roles'][0]['schedule_authority']['canonical_schedule']['value']['id'] = 'wrong'
            with self.subTest(mutation=mutation), self.assertRaises(GeneratorError):
                compile_requirements(changed, inv)
        records['programmes'][0]['value']['loads'] = []
        role = records['ordered_fixture_roles'][0]; role['source_basis'] = 'absolute'
        role['service_definition']['value']['load'].update(basis='absolute', unit='m3/s')
        census(records)
        req = compile_requirements(records, compile_inventory(records))[0]
        self.assertEqual(req['kind'], 'original_service_reference')
        self.assertEqual(req['original_service_relation']['value'], ['water'])
        self.assertNotIn('original_demand', req)

    def test_original_components_keep_member_own_view_method_order_area_and_zero_weight(self):
        compile_inventory, compile_requirements = compilers()
        records = component_fixture()
        component = records['programmes'][1]['value']['loads'][0]['source_components'][0]
        inv = compile_inventory(records); reqs = compile_requirements(records, inv)
        parent_req = reqs[1]; c = parent_req['components'][0]
        self.assertEqual((c['component_index'], c['member_evidence_view'], c['represented_area_m2'], c['original_weight']),
                         (0, 'source', 20, 0))
        self.assertEqual(c['original_component']['value'], component)
        self.assertEqual(c['original_method_reference'], records['method_references'][0])
        self.assertEqual(parent_req['original_mixed_demand']['value']['value'], 999)
        for mutation in ('component_load', 'member_source', 'area', 'weight', 'duplicate'):
            changed = copy.deepcopy(records)
            if mutation == 'component_load': changed['programmes'][1]['value']['loads'][0]['source_components'][0]['load']['status'] = 'forged'
            if mutation == 'member_source': changed['compositions'][0]['value']['members'][0]['source_program_id'] = 'foreign'
            if mutation == 'area': changed['compositions'][0]['value']['members'][0]['represented_area_m2'] = None
            if mutation == 'weight': changed['compositions'][0]['value']['members'][0]['weight'] = 1
            if mutation == 'duplicate': changed['programmes'][1]['value']['loads'][0]['source_components'] *= 2
            with self.subTest(mutation=mutation), self.assertRaises(GeneratorError): compile_requirements(changed, inv)

    def test_recovered_null_requires_independent_packaged_bridge(self):
        compile_inventory, _ = compilers(); records = fixture(); role = records['ordered_fixture_roles'][0]
        role['service_definition']['value']['load']['schedule_id'] = None
        role['schedule_authority'] = {'kind': 'recovered_source_ruleset', 'frozen_schedule_id': None,
            'service_definition': copy.deepcopy(role['service_definition']), 'source_rows': [source({'row': 1})],
            'compiled_ruleset': {'rules': []}, 'bridge_evidence': evidence()}
        with self.assertRaises(GeneratorError) as caught: compile_inventory(records)
        self.assertEqual(caught.exception.code, 'requires_binding')

    def test_qualified_programme_with_independently_empty_obligations_resolves(self):
        from scripts.schedule_generator_build import compile_exact_authority_resources
        from atlas_schedules.physical_sets import resolve_exact_authority
        records = fixture(); records['programmes'][0]['value'].update(loads=[], service_ids=[])
        packaged = {('program', 'leaf'): {'recipe': {'required_service_links': []}}}
        reference = compile_exact_authority_resources(packaged, records)
        recipe = packaged['program', 'leaf']['recipe']
        self.assertEqual(recipe['required_service_sets'], [])
        self.assertEqual(packaged['reference', reference['requirements_key']], [])
        realization = {'mode': 'exact_source_fixture_extents', 'inventory_id': 'labelled',
            'inventory_sha256': reference['inventory_sha256'], 'building_realization_id': 'building',
            'source_hoo_configuration_id': 'source-context', 'selected_method_context_id': 'selected', 'operating_group': 'g'}
        instance = {'owner_kind': 'program', 'key': 'p', 'program_id': 'leaf',
                    'building_realization_id': 'building', 'operating_group': 'g', 'inputs': {}}
        context = source({'selected_method_context_id': 'selected', 'source_hoo_configuration_id': 'source-context',
            'context_evidence_view': 'source', 'qualification_scope': 'full_selected_programme_and_water_registration',
            'qualification_id': 'q', 'method_consumed_context': consumed()})
        for covered in (['leaf'], ['another-programme'], []):
            qualification = source({'qualification_id': 'q',
                'qualification_scope': 'full_selected_programme_and_water_registration',
                'inventory_id': 'labelled', 'inventory_sha256': reference['inventory_sha256'],
                'program_ids': covered, 'selected_method_context': context, 'evidence': evidence()})
            resources_data = dict(packaged)
            resources_data['reference', reference['qualification_key']] = qualification
            with self.subTest(covered=covered), tempfile.TemporaryDirectory() as directory:
                manifest = write_resources(Path(directory), resources_data, {})
                resources = ResourceSet(Path(directory), manifest['resource_set_id'])
                with self.assertRaises(GeneratorError) as caught:
                    resolve_exact_authority(instance, realization, recipe, resources)
                self.assertEqual(caught.exception.code, 'requires_binding')
                with patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True):
                    if covered == ['leaf']:
                        resolved = resolve_exact_authority(instance, realization, recipe, resources)
                        self.assertEqual(resolved['source_requirements'], [])
                        self.assertEqual(resolved['method_qualification'], qualification)
                    else:
                        with self.assertRaises(GeneratorError) as caught:
                            resolve_exact_authority(instance, realization, recipe, resources)
                        self.assertEqual((caught.exception.code, caught.exception.path),
                                         ('requires_binding', '/method_qualification/program_ids'))

    def test_runtime_inventory_is_first_and_complete_aliases_cannot_omit_zero_role(self):
        from atlas_schedules.physical_sets import resolve_exact_authority
        compile_inventory, compile_requirements = compilers(); records = fixture()
        records['ordered_fixture_roles'][0]['schedule_authority']['canonical_schedule']['value']['rules'] = [{'value': 0}]
        zero = copy.deepcopy(records['ordered_fixture_roles'][0]); zero.update(role_id='zero-role', source_order=1)
        zero['source_space'] = {'name': 'B', 'handle': 'locked-B'}
        records['ordered_fixture_roles'].append(zero); census(records)
        inv = compile_inventory(records); reqs = compile_requirements(records, inv)
        realization = {'mode': 'exact_source_fixture_extents', 'inventory_id': 'labelled',
            'inventory_sha256': inv['inventory_sha256'], 'building_realization_id': 'building',
            'source_hoo_configuration_id': 'source-context', 'selected_method_context_id': 'selected', 'operating_group': 'g'}
        instance = {'owner_kind': 'program', 'key': 'p', 'program_id': 'leaf', 'building_realization_id': 'building',
                    'operating_group': 'g', 'inputs': {}}
        recipe = {'exact_source_authority': {'inventory_id': 'labelled', 'inventory_sha256': inv['inventory_sha256'],
            'requirements_key': 'requirements-fixture', 'qualification_key': 'full-fixture'},
            'required_service_links': [], 'required_service_sets': reqs}
        context = {'selected_method_context_id': 'selected', 'source_hoo_configuration_id': 'source-context',
            'context_evidence_view': 'source', 'qualification_scope': 'full_selected_programme_and_water_registration',
            'qualification_id': 'q', 'method_consumed_context': consumed()}
        qualification = source({'qualification_id': 'q', 'qualification_scope': 'full_selected_programme_and_water_registration',
            'inventory_id': 'labelled', 'inventory_sha256': inv['inventory_sha256'],
            'program_ids': ['leaf'], 'selected_method_context': source(context), 'evidence': evidence()})
        with tempfile.TemporaryDirectory() as directory:
            manifest = write_resources(Path(directory), {('reference', 'physical-fixture-inventory__labelled'): inv,
                ('reference', 'requirements-fixture'): reqs, ('reference', 'full-fixture'): qualification}, {})
            resources = ResourceSet(Path(directory), manifest['resource_set_id'])
            entry = next(e for e in manifest['resources'] if e['key']=='physical-fixture-inventory__labelled')
            self.assertNotEqual(entry['sha256'], inv['inventory_sha256'])
            self.assertNotEqual(entry['sha256'], records['geometry']['value']['source_geometry']['sha256'])
            with self.assertRaises(GeneratorError) as caught: resolve_exact_authority(instance, realization, recipe, resources)
            self.assertEqual(caught.exception.code, 'requires_binding')
            with patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True):
                resolved = resolve_exact_authority(instance, realization, recipe, resources)
            self.assertEqual(resolved['source_requirements'], reqs)
            self.assertEqual(resolved['inventory'], inv)
            self.assertEqual(resolved['method_qualification'], qualification)
            with patch.object(resources, 'get', wraps=resources.get) as lookups, patch(
                    'atlas_schedules.physical_sets._qualified_exact_context', return_value=True):
                resolve_exact_authority(instance, realization, recipe, resources)
                self.assertEqual(lookups.call_args_list[0].args, ('reference', 'physical-fixture-inventory__labelled'))
            changed = copy.deepcopy(recipe); changed['required_service_sets'][0]['expected_role_ids'].pop()
            with patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True), self.assertRaises(GeneratorError):
                resolve_exact_authority(instance, realization, changed, resources)
            changed = copy.deepcopy(recipe); changed.pop('required_service_links')
            with patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True), self.assertRaises(GeneratorError):
                resolve_exact_authority(instance, realization, changed, resources)
            changed = copy.deepcopy(recipe); changed['required_service_sets'] = []
            with patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True), self.assertRaises(GeneratorError):
                resolve_exact_authority(instance, realization, changed, resources)
            changed = copy.deepcopy(recipe); changed['required_service_links'] = [{'source_channel': 'hot_water_volume', 'source_service_id': 'water'}]
            with patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True), self.assertRaises(GeneratorError):
                resolve_exact_authority(instance, realization, changed, resources)
            changed = copy.deepcopy(realization); changed['inventory_sha256'] = 'b'*64
            with self.assertRaises(GeneratorError): resolve_exact_authority(instance, changed, recipe, resources)
            changed = copy.deepcopy(recipe); changed['exact_source_authority']['qualification_key'] = 'missing'
            with self.assertRaises(GeneratorError) as caught: resolve_exact_authority(instance, realization, changed, resources)
            self.assertEqual(caught.exception.code, 'requires_binding')
            changed = copy.deepcopy(recipe); changed['exact_source_authority']['requirements_key'] = ['not-an-id']
            with self.assertRaises(GeneratorError): resolve_exact_authority(instance, realization, changed, resources)
        malformed = copy.deepcopy(qualification); malformed['value']['program_ids'] = [['not-an-id']]
        with tempfile.TemporaryDirectory() as directory:
            manifest = write_resources(Path(directory), {('reference', 'physical-fixture-inventory__labelled'): inv,
                ('reference', 'requirements-fixture'): reqs, ('reference', 'full-fixture'): malformed}, {})
            resources = ResourceSet(Path(directory), manifest['resource_set_id'])
            with self.assertRaises(GeneratorError): resolve_exact_authority(instance, realization, recipe, resources)

    def test_child_variant_exact_tuple_and_crossview(self):
        from scripts.schedule_generator_physical_sets import compile_child_variant
        from atlas_schedules.physical_sets import resolve_child_variant
        compile_inventory, _ = compilers(); records = fixture(); inv = compile_inventory(records)
        member = {'parent_inventory_id': 'labelled', 'parent_inventory_sha256': inv['inventory_sha256'],
            'canonical_member': records['programmes'][0], 'original_method_reference': records['method_references'][0],
            'conserved_source_authority': [source(records['programmes'][0]['value']['loads'][0]),
                                           records['ordered_fixture_roles'][0]['schedule_authority']['canonical_schedule']],
            'evidence': evidence()}
        context = source({'selected_method_context_id': 'reviewed-selected', 'source_hoo_configuration_id': 'reviewed-context',
            'context_evidence_view': 'reviewed', 'qualification_scope': 'full_selected_programme_and_water_registration',
            'qualification_id': 'full-fixture', 'method_consumed_context': consumed()})
        key = {'parent_inventory_id': 'labelled', 'parent_inventory_sha256': inv['inventory_sha256'],
            'member_program_id': 'leaf', 'member_evidence_view': 'source', 'selected_method_context_id': 'reviewed-selected'}
        qualification = source({'qualification_id': 'full-fixture',
            'qualification_scope': 'full_selected_programme_and_water_registration', 'key': key, 'selected_method_context': context,
            'canonical_member': member['canonical_member'], 'original_method_reference': member['original_method_reference'],
            'conserved_source_authority': member['conserved_source_authority'], 'evidence': evidence()})
        with self.assertRaises(GeneratorError) as caught: compile_child_variant(member, context, qualification)
        self.assertEqual(caught.exception.code, 'requires_binding')
        with patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True):
            variant = compile_child_variant(member, context, qualification)
        self.assertEqual(variant['context_relation'], 'qualified_crossview_context')
        self.assertEqual(variant['canonical_member'], records['programmes'][0])
        self.assertEqual(variant['adaptation']['conserved_source_authority'], member['conserved_source_authority'])
        with tempfile.TemporaryDirectory() as directory:
            manifest = write_resources(Path(directory), {('reference', 'physical-child-variant__'+variant['variant_id']): variant}, {})
            resources = ResourceSet(Path(directory), manifest['resource_set_id'])
            recipe = {'permitted_child_variants': [{'variant_id': variant['variant_id'], 'key': key}]}
            with patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True):
                self.assertEqual(resolve_child_variant(inv, member, 'reviewed-selected', recipe, resources), variant)
            for mutation in ('absent', 'ambiguous', 'view', 'hash', 'context', 'variant_id'):
                changed = copy.deepcopy(recipe)
                if mutation == 'absent': changed['permitted_child_variants'] = []
                if mutation == 'ambiguous': changed['permitted_child_variants'] *= 2
                if mutation == 'variant_id': changed['permitted_child_variants'][0]['variant_id'] = ['not-an-id']
                if mutation in ('view', 'hash', 'context'):
                    field = {'view': 'member_evidence_view', 'hash': 'parent_inventory_sha256', 'context': 'selected_method_context_id'}[mutation]
                    changed['permitted_child_variants'][0]['key'][field] = 'wrong'
                with self.subTest(mutation=mutation), patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True), self.assertRaises(GeneratorError):
                    resolve_child_variant(inv, member, 'reviewed-selected', changed, resources)
            changed_member = copy.deepcopy(member); changed_member['canonical_member']['value']['loads'][0]['value'] = 42
            with patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True), self.assertRaises(GeneratorError):
                resolve_child_variant(inv, changed_member, 'reviewed-selected', recipe, resources)
        # Even a coherently rebuilt contract variant cannot replace an original
        # Ruleset retained independently in the source fixture inventory.
        forged_member = copy.deepcopy(member)
        forged_member['conserved_source_authority'][1]['value']['rules'] = [{'value': 999}]
        forged_qualification = copy.deepcopy(qualification)
        forged_qualification['value']['conserved_source_authority'] = forged_member['conserved_source_authority']
        with patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True):
            forged_variant = compile_child_variant(forged_member, context, forged_qualification)
            with tempfile.TemporaryDirectory() as directory:
                manifest = write_resources(Path(directory), {('reference', 'physical-child-variant__'+forged_variant['variant_id']): forged_variant}, {})
                resources = ResourceSet(Path(directory), manifest['resource_set_id'])
                recipe = {'permitted_child_variants': [{'variant_id': forged_variant['variant_id'], 'key': key}]}
                with self.assertRaises(GeneratorError) as caught:
                    resolve_child_variant(inv, forged_member, 'reviewed-selected', recipe, resources)
                self.assertEqual(caught.exception.code, 'source_integrity')
        for mutation in ('unqualified', 'pilot', 'original_load'):
            changed = copy.deepcopy(qualification)
            if mutation == 'unqualified': changed['value']['qualification_scope'] = 'unqualified'
            if mutation == 'pilot': changed['value']['selected_method_context']['value']['qualification_scope'] = 'people_water_pilot'
            if mutation == 'original_load': changed['value']['conserved_source_authority'][0]['value']['value'] = 9
            with self.subTest(mutation=mutation), patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True), self.assertRaises(GeneratorError):
                compile_child_variant(member, context, changed)
        original_context = copy.deepcopy(context)
        original_context['value'].update(context_evidence_view='source', source_hoo_configuration_id='source-context')
        original_qualification = copy.deepcopy(qualification)
        original_qualification['value']['selected_method_context'] = original_context
        with patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True):
            original_variant = compile_child_variant(member, original_context, original_qualification)
        self.assertEqual(original_variant['context_relation'], 'original_context')
        self.assertIsNone(original_variant['adaptation'])
        original_context['value']['source_hoo_configuration_id'] = 'unsupported-same-view-context'
        original_qualification['value']['selected_method_context'] = original_context
        with patch('atlas_schedules.physical_sets._qualified_exact_context', return_value=True), self.assertRaises(GeneratorError):
            compile_child_variant(member, original_context, original_qualification)

    def test_frozen_sourced_examples_are_not_ready_qualifications(self):
        completion = json.loads((ROOT/'data/completion-releases/v0.1.0/commercial-completion.json').read_text())
        services = json.loads((ROOT/'data/definition-releases/v0.1.1/services.json').read_text())
        paths = {p['path_id']: p for p in completion['draw_paths']}
        office = paths[services[118]['path_id']]; hotel = paths[services[174]['path_id']]
        self.assertEqual(office['physical_fixture_locations'], ['Core_bottom', 'Core_mid', 'Core_top'])
        self.assertEqual(hotel['source_space_names'], ['Room_1_Flr_3', 'Room_2_Flr_3', 'Room_5_Flr_3', 'Room_6_Flr_3'])
        programmes = json.loads((ROOT/'data/definition-releases/v0.1.1/programs.json').read_text())
        vac_ids = {p['source_id'] for p in programmes if p['building_type']=='SmallHotel' and
                   p['template']=='90.1-2013' and 'Vac' in p['name']}
        vac = [p for p in completion['draw_paths'] if p['building_type']=='SmallHotel' and
               p['template']=='90.1-2013' and set(p['beneficiary_program_ids']) & vac_ids]
        self.assertEqual(sum(len(p['source_space_names']) for p in vac), 14)
        self.assertTrue(all(p['rated_flow_per_area_m3_s_m2'] > 0 for p in vac))
        schedules = json.loads((ROOT/'data/definition-releases/v0.1.1/schedules.json').read_text())
        off = next(s for s in schedules if s['id']=='schedule-ad297eb5529e99cd81fb')
        self.assertEqual([r['values'] for r in off['rules']], [[0.0]])
        self.assertTrue(all(p['matching_atlas_schedule_ids']==[off['id']] for p in vac))
        self.assertNotIn('qualification_scope', completion)

    def test_c5_original_authority_negatives_remain_enforced(self):
        from atlas_schedules.services import validate_service_links
        from tests.test_schedule_generator_service_owners import WholeServiceClosureTests
        valid = WholeServiceClosureTests().fixtures()
        validate_service_links(valid)
        for mutation in ('equal_valued_forged_load', 'wrong_beneficiary', 'ruleset_target'):
            changed = copy.deepcopy(valid); programme, service = changed['constituents']
            if mutation == 'equal_valued_forged_load':
                programme['required_service_links'][0]['original_demand']['required_inputs'] = []
                programme['service_links'][0]['evidence']['original_programme_load']['required_inputs'] = []
            if mutation == 'wrong_beneficiary':
                service['shared_services'][0]['source_service_definition']['beneficiary_program_ids'] = ['foreign']
            if mutation == 'ruleset_target':
                service['generation']['source_inputs']['slot_sources']['hot_water_volume']['rules'][0]['values'] = [0]
            with self.subTest(mutation=mutation), self.assertRaises(GeneratorError): validate_service_links(changed)


if __name__ == '__main__':
    unittest.main()
