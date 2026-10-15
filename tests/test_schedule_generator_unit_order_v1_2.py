"""Labelled contract fixtures for physical 1.2 unit order, not source captures."""
import copy
import json
import math
import unittest
from unittest.mock import patch
from pathlib import Path

from atlas_schedules.errors import GeneratorError
from atlas_schedules.generator import (collect_physical_unit_actors,
                                       build_physical_unit_generation,
                                       _run_physical_unit_actor)
from atlas_schedules.seeds import (assign_physical_unit_sequence,
                                   source_streams, validate_physical_unit_sequence)


def stock(key):
    return ({'key': key}, {'source_family': 'existing_stock_source_fixture',
            'inputs': {'residents': 2, 'source_context': {
                'method': 'resstock_time_allocation_with_selected_source_companions'}}})


def water(key, building='building-1', unit='unit-1'):
    return ({'key': key, 'physical_binding_kind': 'caller_unit_prototype_density_fixed_dhw',
             'building_realization_id': building, 'unit_id': unit},
            {'source_family': 'code_prototype', 'inputs': {'residents': 2,
             'source_context': {'method': 'source_fixed_apartment_dhw'}}})


def other(key, method='source_fixed_programme'):
    return ({'key': key}, {'source_family': 'code_prototype',
            'inputs': {'residents': 2, 'source_context': {'method': method}}})


def apartment(key, building, unit, residents, *, family='code_prototype_rules',
              building_type='HighriseApartment'):
    return ({'key': key, 'owner_kind': 'program', 'building_realization_id': building,
             'unit_id': unit},
            {'source_family': family, 'source': {'building_type': building_type},
             'inputs': {'residents': residents, 'source_context': {
                 'method': 'unit_occupancy_interior_lighting'}}})


class PhysicalUnitOrderTests(unittest.TestCase):
    def sequence(self, records, master=42):
        return assign_physical_unit_sequence(master,
                                             collect_physical_unit_actors(records, '1.2.0'))

    def test_stock_actor_requires_source_family_method_and_resident(self):
        records = [stock('s1'), other('bare-residents'), water('water'),
                   ({'key': 'wrong-stock'}, {'source_family': 'existing_stock_source_fixture',
                    'inputs': {'residents': 2, 'source_context': {'method': 'other'}}}),
                   stock('s2')]
        self.assertEqual(self.sequence(records), [
            {'actor_kind': 'stock', 'instance_key': 's1', 'building_realization_id': None,
             'unit_id': None, 'stochastic_action': 'generate', 'position': 0, 'unit_seed': 42},
            {'actor_kind': 'stock', 'instance_key': 's2', 'building_realization_id': None,
             'unit_id': None, 'stochastic_action': 'generate', 'position': 1, 'unit_seed': 84}])
        self.assertEqual(self.sequence(records, 0)[-1]['unit_seed'], 0)
        self.assertEqual(self.sequence(records, 51)[-1]['unit_seed'], 102)
        missing = stock('missing')
        del missing[1]['inputs']['residents']
        with self.assertRaises(GeneratorError):
            self.sequence([missing])

    def test_fixed_water_and_alternative_projections_do_not_shift_positions(self):
        baseline = [stock('s1'), stock('s2'), stock('s3')]
        expected = self.sequence(baseline)
        for records in ([water('owner'), *baseline],
                        [baseline[0], water('owner'), other('source-view'),
                         baseline[1], other('reviewed-view'), baseline[2]],
                        [*reversed([water('owner'), other('source-view')]), *baseline]):
            with self.subTest(records=[i['key'] for i, _ in records]):
                self.assertEqual(self.sequence(records), expected)

    def test_cumulative_seed_is_full_width(self):
        records = [stock(f's{i}') for i in range(30)]
        self.assertEqual(self.sequence(records)[-1]['unit_seed'], 42 * math.factorial(30))
        self.assertGreater(self.sequence(records)[-1]['unit_seed'], 2**64)
        self.assertEqual([r['unit_seed'] for r in self.sequence(records, 0)], [0] * 30)

    def test_stock_apartment_stock_and_n0_reserve_global_positions(self):
        with patch('atlas_schedules.generator._qualified_apartment_actor', return_value=True):
            records = [stock('s1'), apartment('a0', 'b1', 'u1', 0), stock('s2')]
            self.assertEqual([(r['instance_key'], r['position'], r['unit_seed'],
                               r['stochastic_action']) for r in self.sequence(records)],
                             [('s1', 0, 42, 'generate'), ('a0', 1, 84, 'skip_n0'),
                              ('s2', 2, 252, 'generate')])
            self.assertEqual([r['unit_seed'] for r in self.sequence(records, 51)], [51, 102, 306])
            positive = [apartment('a1', 'b1', 'u1', 2),
                        apartment('a0', 'b1', 'u2', 0),
                        apartment('a2', 'b2', 'u1', 3)]
            self.assertEqual([(r['position'], r['unit_seed'], r['stochastic_action'])
                              for r in self.sequence(positive)],
                             [(0, 42, 'generate'), (1, 84, 'skip_n0'),
                              (2, 252, 'generate')])
            self.assertEqual([r['unit_seed'] for r in self.sequence(positive, 0)], [0, 0, 0])
            self.assertEqual(list(source_streams(self.sequence(positive)[0]['unit_seed'])),
                             ['main', 'hygiene', 'dishwasher', 'clothes_washer',
                              'clothes_dryer', 'ev', 'cooking'])
            self.assertNotIn('streams', self.sequence(positive)[1])

    def test_water_insertions_and_alternative_views_preserve_mixed_actor_order(self):
        baseline = [stock('s1'), apartment('a1', 'b1', 'u1', 1),
                    apartment('a0', 'b1', 'u2', 0), stock('s2')]
        with patch('atlas_schedules.generator._qualified_apartment_actor', return_value=True):
            expected = self.sequence(baseline)
            variants = [
                [water('w1'), *baseline],
                [baseline[0], water('w1'), other('source-view'), baseline[1],
                 water('w2', unit='u2'), baseline[2], other('reviewed-view'), baseline[3]],
                [baseline[0], baseline[1], other('reviewed-view'), baseline[2],
                 water('w1'), other('source-view'), baseline[3]],
            ]
            for records in variants:
                with self.subTest(records=[i['key'] for i, _ in records]):
                    self.assertEqual(self.sequence(records), expected)

    def test_duplicate_selected_apartment_unit_rejects_positive_and_n0(self):
        with patch('atlas_schedules.generator._qualified_apartment_actor', return_value=True):
            for n in (0, 2):
                records = [apartment('source-view', 'b1', 'u1', n),
                           apartment('reviewed-view', 'b1', 'u1', n)]
                with self.subTest(residents=n), self.assertRaises(GeneratorError):
                    self.sequence(records)
            self.assertEqual(self.sequence([water('w1'), other('source-view'),
                                            other('reviewed-view')]), [])

    def test_unqualified_or_malformed_apartment_actor_rejects_before_allocation(self):
        candidate = apartment('a1', 'b1', 'u1', 1)
        with self.assertRaises(GeneratorError) as caught:
            collect_physical_unit_actors([candidate], '1.2.0')
        self.assertEqual(caught.exception.code, 'requires_binding')
        with patch('atlas_schedules.generator._qualified_apartment_actor', return_value=True):
            for bad in (apartment('a1', 'b1', 'u1', True),
                        apartment('a1', 'b1', 'u1', -1),
                        apartment('a1', 'b1', 'u1', 1, family='other'),
                        apartment('a1', 'b1', 'u1', 1, building_type='Office')):
                with self.subTest(bad=bad), self.assertRaises(GeneratorError):
                    collect_physical_unit_actors([bad], '1.2.0')

    def test_retained_stock_bundle_receipt_and_tampering(self):
        produced = build_physical_unit_generation(42,
                                                  [stock('s1'), water('owner'), stock('s2')])
        self.assertEqual(produced, {
            'physical_unit_seed_sequence': [
                {'actor_kind': 'stock', 'instance_key': 's1',
                 'building_realization_id': None, 'unit_id': None,
                 'stochastic_action': 'generate', 'position': 0, 'unit_seed': 42},
                {'actor_kind': 'stock', 'instance_key': 's2',
                 'building_realization_id': None, 'unit_id': None,
                 'stochastic_action': 'generate', 'position': 1, 'unit_seed': 84}],
            'residential_unit_order': ['s1', 's2'],
            'unit_seeds': {'s1': 42, 's2': 84}})
        self.assertEqual(build_physical_unit_generation(42,
                         [water('owner'), other('source-view'), other('reviewed-view')]), {
            'physical_unit_seed_sequence': [],
            'residential_unit_order': [], 'unit_seeds': {}})
        bundle = {'schema_version': '1.2.0', 'generation': {'master_seed': 42,
                  **produced}}
        validate_physical_unit_sequence(bundle)
        for index, field, value in ((0, 'position', 1), (1, 'unit_seed', 85)):
            mutated = copy.deepcopy(bundle)
            mutated['generation']['physical_unit_seed_sequence'][index][field] = value
            with self.subTest(index=index, field=field), self.assertRaises(GeneratorError):
                validate_physical_unit_sequence(mutated)
        mutated = copy.deepcopy(bundle)
        mutated['generation']['unit_seeds']['s2'] = 85
        with self.assertRaises(GeneratorError):
            validate_physical_unit_sequence(mutated)
        mutated['generation']['unit_seeds']['s2'] = True
        with self.assertRaises(GeneratorError):
            validate_physical_unit_sequence(mutated)

    def test_legacy_stock_generation_receipts_remain_unchanged(self):
        from atlas_schedules import generate
        from atlas_schedules.resources import ResourceSet
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root/'atlas_schedules/data/manifest.json').read_text())
        resources = ResourceSet.load(manifest['resource_set_id'])
        pid = 'program-03fe19ed8968e605f4be3b8d'
        bound = resources.get('program', pid)['recipe']['bound_inputs']
        instances = [{'key': key, 'program_id': pid, 'inputs': copy.deepcopy(bound),
                      'basis_bindings': {}, 'operating_group': None}
                     for key in ('s1', 's2')]
        params = {'resource_set_id': resources.resource_set_id,
                  'calendar': {'year': 2007, 'clock': 'local_standard_time', 'holidays': []},
                  'instances': instances}
        legacy = generate(params, 42)
        params['schema_version'] = '1.1.0'
        for item in instances:
            item['owner_kind'] = 'program'
        typed = generate(params, 42)
        for bundle in (legacy, typed):
            self.assertEqual(bundle['generation']['residential_unit_order'], ['s1', 's2'])
            self.assertEqual(bundle['generation']['unit_seeds'], {'s1': 42, 's2': 84})
            self.assertNotIn('physical_unit_seed_sequence', bundle['generation'])

    def test_positive_streams_reserve_ev_and_water_has_no_stream(self):
        receipts = self.sequence([stock('positive'), water('owner')])
        self.assertEqual([r['instance_key'] for r in receipts], ['positive'])
        self.assertEqual(list(source_streams(receipts[0]['unit_seed'])),
                         ['main', 'hygiene', 'dishwasher', 'clothes_washer',
                          'clothes_dryer', 'ev', 'cooking'])

    def test_selected_n0_skips_actual_kernel_and_stream_boundary(self):
        from atlas_schedules.resources import ResourceSet
        from atlas_schedules.programs import resolve_program
        from atlas_schedules.residential import activity
        from atlas_schedules.residential import events
        from atlas_schedules.generator import generate_residential
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root/'atlas_schedules/data/manifest.json').read_text())
        resources = ResourceSet.load(manifest['resource_set_id'])
        pid = 'program-03fe19ed8968e605f4be3b8d'
        inputs = copy.deepcopy(resources.get('program', pid)['recipe']['bound_inputs'])
        prepared = resolve_program(pid, dict(inputs, year=2007, holidays=[]), resources)
        with patch('atlas_schedules.generator._qualified_apartment_actor', return_value=True):
            skipped, stock_actor = build_physical_unit_generation(42, [
                apartment('a0', 'b1', 'u1', 0), stock('s1')])['physical_unit_seed_sequence']
        self.assertEqual((skipped['position'], skipped['unit_seed'],
                          skipped['stochastic_action']), (0, 42, 'skip_n0'))
        self.assertEqual(stock_actor['unit_seed'], 84)
        with patch('atlas_schedules.generator.generate_residential', wraps=generate_residential) as kernel, \
             patch('atlas_schedules.residential.activity.source_streams',
                   wraps=activity.source_streams) as streams, \
             patch('atlas_schedules.residential.generate_events',
                   wraps=events.generate_events) as event_kernel:
            with self.assertRaises(GeneratorError):
                _run_physical_unit_actor(skipped, {'residents': 0}, resources)
            self.assertEqual((kernel.call_count, streams.call_count,
                              event_kernel.call_count), (0, 0, 0))
            result = _run_physical_unit_actor(stock_actor, prepared['inputs'], resources)
            self.assertIn('channels', result)
            self.assertEqual(kernel.call_count, 1)
            streams.assert_called_once_with(84)
            self.assertEqual(event_kernel.call_count, 1)
            self.assertEqual(list(result['source_context']['activity']['enduse_seeds']),
                             ['hygiene', 'dishwasher', 'clothes_washer',
                              'clothes_dryer', 'ev', 'cooking'])


if __name__ == '__main__':
    unittest.main()
