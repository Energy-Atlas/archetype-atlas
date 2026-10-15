"""Structural contract fixtures only; no 1.2 source or generation qualification."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from atlas_schedules.__main__ import main
from atlas_schedules.contract import _schema_errors, validate_bundle, validate_request
from atlas_schedules.errors import GeneratorError
from atlas_schedules.owners import identity_fields, owner_identity, request_version
from tests.test_schedule_generator_contract import bundle as legacy_bundle
from tests.test_schedule_generator_contract import request as legacy_request


class V12WireTests(unittest.TestCase):
    def request(self):
        return {'schema_version': '1.2.0', 'resource_set_id': 'contract_structure_only',
                'calendar': {'year': 2007, 'clock': 'local_standard_time'},
                'building_realizations': [], 'instances': [{
                    'owner_kind': 'physical_service', 'physical_binding_kind': 'legacy_whole',
                    'key': 'water', 'source_service_id': 'service-26df36d04c21572b9838d63f',
                    'physical_id': 'fixture', 'inputs': {}, 'operating_group': 'group',
                    'basis_bindings': {'extents': {'absolute': {
                        'value': 1, 'unit': '1', 'evidence': {'fixture': 'contract_structure_only'}}}}}]}

    def bundle(self):
        result = legacy_bundle()
        result['schema_version'] = '1.2.0'
        result['metadata']['building_realizations'] = []
        result['generation']['physical_unit_seed_sequence'] = []
        result['constituents'][0].update(owner_kind='program', required_service_links=[],
                                         required_service_sets=[], service_set_projections=[])
        result['bindings'][0]['owner_kind'] = 'program'
        return result

    def assert_contract_error(self, callback):
        with self.assertRaises(GeneratorError) as caught:
            callback()
        self.assertIn(caught.exception.code, {'unsupported_schema', 'invalid_contract'})

    def test_explicit_v12_markers_and_old_versions(self):
        self.assertEqual(request_version(legacy_request()), '1.0.0')
        explicit = legacy_request(); explicit['schema_version'] = '1.0.0'
        validate_request(explicit, 42)
        old = copy.deepcopy(self.request()); old['schema_version'] = '1.1.0'
        old.pop('building_realizations'); old['instances'][0].pop('physical_binding_kind')
        validate_request(old, 42)
        validate_bundle(legacy_bundle())
        params = self.request()
        self.assertEqual(request_version(params), '1.2.0')
        validate_request(params, 42)
        _schema_errors(params, 'request', '1.2.0')
        _schema_errors(self.bundle(), 'bundle', '1.2.0')
        for version, old_params in [('1.0.0', explicit), ('1.1.0', old)]:
            changed = copy.deepcopy(old_params); changed['building_realizations'] = []
            self.assert_contract_error(lambda: validate_request(changed, 42))
        old_bundle = legacy_bundle(); old_bundle['generation']['physical_unit_seed_sequence'] = []
        self.assert_contract_error(lambda: validate_bundle(old_bundle))
        with tempfile.TemporaryDirectory() as directory:
            request_file = Path(directory)/'request.json'
            output = Path(directory)/'output.json'
            for envelope in ('1.1.0', '7.0.0'):
                request_file.write_text(json.dumps({'schema_version': envelope, 'params': params, 'seed': 42}))
                with patch('atlas_schedules.__main__.generate', side_effect=AssertionError('must not generate')):
                    self.assert_contract_error(lambda: main(['--request', str(request_file), '--output', str(output)]))
            request_file.write_text(json.dumps({'schema_version': '1.2.0', 'params': params, 'seed': 42}))
            sentinel = {'sentinel': 'matching wire reached generate'}
            with patch('atlas_schedules.__main__.generate', return_value=sentinel):
                self.assertEqual(main(['--request', str(request_file), '--output', str(output)]), 0)
            self.assertEqual(json.loads(output.read_text()), sentinel)

    def test_v12_strict_unions(self):
        params = self.request()
        bad = copy.deepcopy(params); bad.pop('building_realizations')
        self.assert_contract_error(lambda: validate_request(bad, 42))
        for value in (True, float('inf')):
            bad = copy.deepcopy(params); bad['instances'][0]['basis_bindings']['multiplicity'] = value
            self.assert_contract_error(lambda bad=bad: _schema_errors(bad, 'request', '1.2.0'))
        for field, value in [('source_fixture_role_id', 'role'), ('unit_id', 'u'), ('building_realization_id', 'b')]:
            bad = copy.deepcopy(params); bad['instances'][0][field] = value
            self.assert_contract_error(lambda bad=bad: validate_request(bad, 42))
        bad = copy.deepcopy(params); bad['building_realizations'] = [{
            'mode': 'exact_source_fixture_extents', 'building_realization_id': 'b',
            'inventory_id': 'i', 'inventory_sha256': None,
            'source_hoo_configuration_id': 'h', 'selected_method_context_id': 'm',
            'operating_group': 'g'}]
        self.assert_contract_error(lambda: validate_request(bad, 42))
        bad['building_realizations'][0]['inventory_sha256'] = 'A'*64
        self.assert_contract_error(lambda: validate_request(bad, 42))
        result = self.bundle()
        for field in ('building_realizations',):
            bad = copy.deepcopy(result); bad['metadata'].pop(field)
            self.assert_contract_error(lambda bad=bad: _schema_errors(bad, 'bundle', '1.2.0'))
        for field in ('required_service_sets', 'service_set_projections'):
            bad = copy.deepcopy(result); bad['constituents'][0].pop(field)
            self.assert_contract_error(lambda bad=bad: _schema_errors(bad, 'bundle', '1.2.0'))
        for mutation in ('missing_receipts', 'wrong_receipts', 'foreign_graph'):
            bad = copy.deepcopy(result)
            if mutation == 'missing_receipts': bad['generation'].pop('physical_unit_seed_sequence')
            elif mutation == 'wrong_receipts': bad['generation']['physical_unit_seed_sequence'] = {}
            else: bad['constituents'][0]['unknown_graph_field'] = 1
            self.assert_contract_error(lambda bad=bad: _schema_errors(bad, 'bundle', '1.2.0'))
        receipt = {'actor_kind': 'apartment_adapter', 'instance_key': 'a',
                   'building_realization_id': 'b', 'unit_id': 'u',
                   'stochastic_action': 'skip_n0', 'position': 0, 'unit_seed': 2**64}
        good = copy.deepcopy(result); good['generation']['physical_unit_seed_sequence'] = [receipt]
        _schema_errors(good, 'bundle', '1.2.0')
        for field, value in [('actor_kind', 'other'), ('building_realization_id', None),
                             ('position', True), ('position', -1), ('position', 1.0),
                             ('unit_seed', -1), ('unit_seed', True), ('unit_seed', 1.0),
                             ('extra', 1)]:
            bad = copy.deepcopy(good); bad['generation']['physical_unit_seed_sequence'][0][field] = value
            self.assert_contract_error(lambda bad=bad: _schema_errors(bad, 'bundle', '1.2.0'))
        stock = copy.deepcopy(good); stock['generation']['physical_unit_seed_sequence'][0].update(
            actor_kind='stock', building_realization_id=None, unit_id=None, stochastic_action='generate')
        _schema_errors(stock, 'bundle', '1.2.0')
        stock['generation']['physical_unit_seed_sequence'][0]['unit_id'] = 'u'
        self.assert_contract_error(lambda: _schema_errors(stock, 'bundle', '1.2.0'))

    def test_v12_physical_identity_is_scoped_but_retains_sid(self):
        from atlas_schedules.owners import physical_identity
        legacy = {'owner_kind': 'physical_service', 'physical_binding_kind': 'legacy_whole',
                  'source_service_id': 'sid', 'physical_id': 'fixture'}
        exact = dict(legacy, physical_binding_kind='exact_source_role', building_realization_id='b',
                     source_fixture_role_id='r')
        caller = dict(legacy, physical_binding_kind='caller_unit_prototype_density_fixed_dhw',
                      building_realization_id='b', unit_id='u')
        self.assertEqual(physical_identity(legacy), ('legacy_whole', 'fixture'))
        self.assertEqual(physical_identity(exact), ('exact_source_role', 'b', 'fixture'))
        self.assertEqual(physical_identity(caller), ('caller_unit_prototype_density_fixed_dhw', 'b', 'u', 'fixture'))
        self.assertEqual(identity_fields(exact, '1.2.0')['source_service_id'], 'sid')
        self.assertNotEqual(owner_identity(exact), owner_identity(dict(exact, building_realization_id='other')))
        self.assertEqual(owner_identity(exact)[1], 'sid')

    def test_v12_request_realization_alternatives_are_structurally_disjoint(self):
        exact = self.request()
        exact['building_realizations'] = [{
            'mode': 'exact_source_fixture_extents', 'building_realization_id': 'b',
            'inventory_id': 'inventory', 'inventory_sha256': 'a'*64,
            'source_hoo_configuration_id': 'hoo', 'selected_method_context_id': 'method',
            'operating_group': 'group'}]
        exact['instances'][0].update(physical_binding_kind='exact_source_role',
            building_realization_id='b', source_fixture_role_id='role')
        _schema_errors(exact, 'request', '1.2.0')
        bad = copy.deepcopy(exact); bad['instances'][0]['unit_id'] = 'u'
        self.assert_contract_error(lambda: _schema_errors(bad, 'request', '1.2.0'))
        evidence = {'source_revision': 'caller', 'source_path': 'declaration.json',
            'source_sha256': 'b'*64, 'locator': '/units/0', 'original_value': 75,
            'original_unit': 'm2', 'transformation': 'identity',
            'extraction_date': '2026-10-15', 'interpretation_note': 'contract_structure_only'}
        caller = self.request()
        caller['building_realizations'] = [{
            'mode': 'caller_unit_prototype_density_fixed_dhw', 'building_realization_id': 'b',
            'building_type': 'HighriseApartment', 'template': '90.1-2013',
            'unit_inventory_id': 'units', 'unit_inventory_sha256': 'c'*64,
            'unit_inventory': {'authority': 'caller_declared_units', 'units': [{
                'unit_id': 'u', 'physical_id': 'fixture',
                'source_service_id': 'service-26df36d04c21572b9838d63f',
                'source_beneficiary_id': 'programme-source', 'programme_ids': ['programme'],
                'water_authority_programme_id': 'programme', 'floor_area_m2': 75,
                'area_evidence': [evidence], 'multiplicity': 1,
                'identity_evidence': [evidence]}]}}]
        caller['instances'][0].update(physical_binding_kind='caller_unit_prototype_density_fixed_dhw',
            building_realization_id='b', unit_id='u', operating_group=None,
            inputs={'water_method': 'source_fixed_apartment_dhw',
                    'source_geometry_departure': 'caller_unit_area'},
            basis_bindings={'multiplicity': 1, 'extents': {'floor_area': {
                'value': 75, 'unit': 'm2', 'evidence': [evidence]}}})
        _schema_errors(caller, 'request', '1.2.0')
        for path, value in [('inputs', {'source_hoo_configuration_id':'hoo'}),
                            ('source_fixture_role_id', 'role')]:
            bad = copy.deepcopy(caller)
            if path == 'inputs': bad['instances'][0]['inputs'].update(value)
            else: bad['instances'][0][path] = value
            self.assert_contract_error(lambda bad=bad: _schema_errors(bad, 'request', '1.2.0'))


if __name__ == '__main__':
    unittest.main()
