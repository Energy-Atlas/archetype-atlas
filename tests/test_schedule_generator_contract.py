"""Runtime and JSON Schema contracts for the pure Python schedule boundary."""
import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from atlas_schedules.canonical import schedule_id
from atlas_schedules.errors import GeneratorError
from atlas_schedules.contract import validate_request, validate_bundle, finalize_channels
from atlas_schedules.comparison import compare_bundles

ROOT = Path(__file__).resolve().parents[1]


def request():
    return {'resource_set_id': 'resources-fixture',
            'calendar': {'year': 2007, 'clock': 'local_standard_time', 'holidays': []},
            'instances': [{'key': 'a/b', 'program_id': 'program-fixture',
                           'inputs': {'residents': 2, 'bedrooms': 1},
                           'basis_bindings': {'floor_area_m2': 100}, 'operating_group': None}]}


def bundle():
    sid = schedule_id('a/b', 'lighting')
    values = [1.0] * 1600 + [0.0] * 7160
    target = {'quantity': 'lighting', 'total': 20000, 'unit': 'Wh/m2',
              'basis': 'floor_area', 'method': 'reference_schedule',
              'magnitude_unit': 'W/m2', 'fuel': 'electricity', 'host': 'space',
              'evidence': {'locator': 'fixture cell', 'original_value': 10, 'original_unit': 'W/m2'}}
    binding = {'kind': 'load', 'instance_key': 'a/b', 'program_id': 'program-fixture',
               'demand_id': 'demand-lighting', 'slot': 'lighting', 'schedule_id': sid,
               'fuel': 'electricity', 'host': 'space', 'budget_method': 'reference_schedule',
               'reference_target': target,
               'effective_magnitude': {'value': 12.5, 'unit': 'W/m2', 'basis': 'floor_area'},
               'scaling_receipt': {'generated_integral': 1600, 'seconds_per_sample': 3600,
                                   'achieved_total': 20000, 'unit': 'Wh/m2'}}
    return {'schema_version': '1.0.0', 'algorithm_version': 'fixture-v1',
            'schedules': {sid: {'id': sid, 'unit': 'fraction', 'year': 2007,
                                'clock': 'local_standard_time', 'timestep_minutes': 60,
                                'values': values}}, 'bindings': [binding],
            'constituents': [{'instance_key': 'a/b', 'program_id': 'program-fixture',
                              'recipe_id': 'recipe-fixture', 'inputs': {'residents': 2},
                              'source': {'source_family': 'code_prototype_rules',
                                         'source_id': 'program-fixture', 'template': 'fixture',
                                         'vintage': None, 'evidence_view': 'reviewed',
                                         'weather': None},
                              'slots': ['lighting'], 'demands': ['demand-lighting'],
                              'controls': [], 'shared_services': [], 'evidence': [],
                              'schedule_ids': {'lighting': sid}, 'binding_indices': [0],
                              'generation': {'seed': 1, 'decisions': {'day': 'weekday'}}}],
            'generation': {'master_seed': 1, 'source_order': ['a/b']},
            'metadata': {'resource_set_id': 'resources-fixture', 'calendar': request()['calendar']}}


class ContractTests(unittest.TestCase):
    def test_strict_8760_contract(self):
        valid = request(); validate_request(valid, 0); validate_request(valid, 2**64 - 1)
        for invalid_seed in (True, -1, 2**64, 1.0, None):
            with self.subTest(seed=invalid_seed), self.assertRaises(GeneratorError):
                validate_request(valid, invalid_seed)
        for year in (2008, 2000):
            invalid = copy.deepcopy(valid); invalid['calendar']['year'] = year
            with self.subTest(year=year), self.assertRaises(GeneratorError):
                validate_request(invalid, 1)
        invalid = copy.deepcopy(valid); invalid['instances'][0]['unsupported'] = True
        with self.assertRaises(GeneratorError): validate_request(invalid, 1)
        complete = bundle(); validate_bundle(complete)
        for mutation in ('length', 'nan', 'fraction', 'id', 'reference'):
            invalid = copy.deepcopy(complete); sid = next(iter(invalid['schedules']))
            if mutation == 'length': invalid['schedules'][sid]['values'].pop()
            elif mutation == 'nan': invalid['schedules'][sid]['values'][0] = float('nan')
            elif mutation == 'fraction': invalid['schedules'][sid]['values'][0] = 1.01
            elif mutation == 'id': invalid['schedules'][sid]['id'] = 'wrong'
            else: invalid['bindings'][0]['schedule_id'] = 'missing'
            with self.subTest(mutation=mutation), self.assertRaises(GeneratorError):
                validate_bundle(invalid)

    def test_controls_are_not_energy_scaled(self):
        b = bundle(); sid = schedule_id('a/b', 'heating_setpoint')
        b['schedules'][sid] = {'id': sid, 'unit': 'C', 'year': 2007,
                               'clock': 'local_standard_time', 'timestep_minutes': 60,
                               'values': [20.0] * 8760}
        b['bindings'].append({'kind': 'control', 'instance_key': 'a/b',
                              'program_id': 'program-fixture', 'slot': 'heating_setpoint',
                              'schedule_id': sid, 'control_quantity': 'temperature'})
        b['constituents'][0]['slots'].append('heating_setpoint')
        b['constituents'][0]['controls'].append('heating_setpoint')
        b['constituents'][0]['schedule_ids']['heating_setpoint'] = sid
        b['constituents'][0]['binding_indices'].append(1)
        validate_bundle(b)
        b['bindings'][1]['effective_magnitude'] = {'value': 1, 'unit': 'W', 'basis': 'unit'}
        with self.assertRaises(GeneratorError): validate_bundle(b)

    def test_finalize_preserves_emitted_integral_and_input(self):
        generated = {'channels': {'lighting': [0.123456789123] * 8760}, 'source_context': {}}
        original = copy.deepcopy(generated)
        self.assertEqual(finalize_channels(generated)['channels']['lighting'][0], 0.123456789123)
        self.assertEqual(generated, original)
        rounded = copy.deepcopy(generated); rounded['source_context']['export_significant_digits'] = 3
        self.assertEqual(finalize_channels(rounded)['channels']['lighting'][0], 0.123)
        invalid = copy.deepcopy(generated); invalid['source_context']['draw'] = float('nan')
        with self.assertRaises(GeneratorError): finalize_channels(invalid)

    def test_scaling_receipt_reports_the_emitted_integral(self):
        b = bundle(); b['bindings'][0]['scaling_receipt']['generated_integral'] = 1599
        with self.assertRaises(GeneratorError): validate_bundle(b)

    def test_calendar_rejects_impossible_holiday_and_allows_empty_default(self):
        omitted = request(); omitted['calendar'].pop('holidays')
        validate_request(omitted, 1)
        impossible = request(); impossible['calendar']['holidays'] = ['2007-02-29']
        with self.assertRaises(GeneratorError): validate_request(impossible, 1)

    def test_unowned_schedule_and_duplicate_binding_owner_rejected(self):
        b = bundle(); extra_id = schedule_id('a/b', 'extra')
        b['schedules'][extra_id] = {**copy.deepcopy(next(iter(b['schedules'].values()))), 'id': extra_id}
        with self.assertRaises(GeneratorError): validate_bundle(b)
        b = bundle(); b['constituents'].append(copy.deepcopy(b['constituents'][0]))
        with self.assertRaises(GeneratorError): validate_bundle(b)

    def test_equivalent_values_ignore_serialization_and_ids(self):
        expected = bundle(); actual = copy.deepcopy(expected)
        old = next(iter(actual['schedules'])); new = 'opaque-other-id'
        actual['schedules'][new] = actual['schedules'].pop(old)
        actual['schedules'][new]['id'] = new
        actual['bindings'][0]['schedule_id'] = new
        actual['constituents'][0]['schedule_ids']['lighting'] = new
        actual['schedules'][new]['values'][0] += 1e-9
        actual['metadata']['destination'] = 'elsewhere'
        policy = json.loads((ROOT/'sources/schedule-generator-policy.json').read_text())
        self.assertEqual(compare_bundles(actual, expected, policy), [])

    def test_discrete_decision_and_large_numeric_changes_fail(self):
        policy = json.loads((ROOT/'sources/schedule-generator-policy.json').read_text())
        expected = bundle(); actual = copy.deepcopy(expected)
        actual['constituents'][0]['generation']['decisions']['day'] = 'weekend'
        self.assertTrue(compare_bundles(actual, expected, policy))
        actual = copy.deepcopy(expected)
        actual['schedules'][next(iter(actual['schedules']))]['values'][0] = 0.5
        self.assertTrue(compare_bundles(actual, expected, policy))

    def test_comparison_detects_changed_source_magnitude_and_capacity_condition(self):
        policy = json.loads((ROOT/'sources/schedule-generator-policy.json').read_text())
        expected = bundle(); actual = copy.deepcopy(expected)
        actual['bindings'][0]['reference_target']['original_magnitude'] = {
            'value': 11, 'unit': 'W/m2', 'evidence': {'locator': 'different source'}}
        self.assertTrue(compare_bundles(actual, expected, policy))
        actual = copy.deepcopy(expected)
        actual['bindings'][0]['reference_target']['capacity_constraint'] = {
            'maximum': 12.5, 'unit': 'W/m2', 'evidence': {'locator': 'condition'}}
        self.assertTrue(compare_bundles(actual, expected, policy))

    def test_comparison_covers_constituent_schedule_without_load_binding(self):
        policy = json.loads((ROOT/'sources/schedule-generator-policy.json').read_text())
        expected = bundle(); sid = schedule_id('a/b', 'resident_count')
        expected['schedules'][sid] = {'id': sid, 'unit': 'person', 'year': 2007,
                                      'clock': 'local_standard_time', 'timestep_minutes': 60,
                                      'values': [2] * 8760}
        expected['constituents'][0]['slots'].append('resident_count')
        expected['constituents'][0]['schedule_ids']['resident_count'] = sid
        actual = copy.deepcopy(expected)
        actual['schedules'][sid]['values'][0] = 3
        self.assertTrue(compare_bundles(actual, expected, policy))

    def test_schemas_accept_examples(self):
        for stem in ('request', 'program', 'bundle'):
            schema = json.loads((ROOT/f'schemas/schedule-generator-{stem}-v1.schema.json').read_text())
            example = json.loads((ROOT/f'docs/examples/schedule-generator/{stem}.json').read_text())
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(example)
        bundle_schema = json.loads((ROOT/'schemas/schedule-generator-bundle-v1.schema.json').read_text())
        binding = json.loads((ROOT/'docs/examples/schedule-generator/binding.json').read_text())
        Draft202012Validator({'$schema': bundle_schema['$schema'],
                              '$defs': bundle_schema['$defs'],
                              '$ref': '#/$defs/binding'}).validate(binding)

    def test_program_schema_requires_source_interpretation(self):
        schema = json.loads((ROOT/'schemas/schedule-generator-program-v1.schema.json').read_text())
        example = json.loads((ROOT/'docs/examples/schedule-generator/program.json').read_text())
        absent = copy.deepcopy(example); absent.pop('source')
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(absent)))

    def test_bundle_schema_requires_constituent_source_receipt(self):
        schema = json.loads((ROOT/'schemas/schedule-generator-bundle-v1.schema.json').read_text())
        example = bundle(); example['constituents'][0].pop('source')
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(example)))


if __name__ == '__main__':
    unittest.main()
