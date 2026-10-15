"""Selected ResStock dwelling timing against locked native source captures."""
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet
from scripts.common import ROOT

LOCK = ROOT / 'sources/schedule-generator-apartment-timing-lock.json'
M1 = ROOT / 'data/schedule-generator/residential-vectors.json'
R1 = ROOT / 'data/schedule-generator/residential-family-native.json.gz'
NATIVE4 = ROOT / 'build/task-10/native-apartment-boundary-20261014-01/native-output.json'
DOMAIN = ROOT / 'data/schedule-generator/apartment/timing-domain.json'
POLICY = ROOT / 'atlas_schedules/data/reference/comparison-policy.json'


def source_bytes(path, digest):
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest, path
    return data


def selected_inputs(case):
    source = case['inputs']
    return {name: source[name] for name in
            ('year', 'residents', 'state', 'latitude', 'longitude', 'time_zone_utc_offset')} | {'holidays': []}


class ApartmentSelectedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.schedule_generator_apartment_timing import (
            build_apartment_timing_test_resources, compile_apartment_timing_domain)
        cls.lock = json.loads(LOCK.read_text(encoding='utf-8'))
        cls.domain = compile_apartment_timing_domain(M1, R1, cls.lock)
        assert cls.domain == json.loads(DOMAIN.read_text(encoding='utf-8'))
        build_root = ROOT/'build/task-10/apartment-a1'
        build_root.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(prefix='selected-', dir=build_root)
        cls.resources = build_apartment_timing_test_resources(
            Path(cls.temporary.name)/'resources', cls.domain, cls.lock, ROOT/'data/raw')
        cls.m1 = json.loads(source_bytes(M1, cls.lock['vectors']['M1']['sha256']))['cases']
        cls.r1 = json.loads(gzip.decompress(source_bytes(R1, cls.lock['vectors']['R1']['sha256'])))['cases']
        cls.native4 = json.loads(source_bytes(NATIVE4, cls.lock['vectors']['selected4']['sha256']))['cases']
        cls.tolerance = json.loads(POLICY.read_text(encoding='utf-8'))['tolerances']['fraction']
        cls.receipts = []

    @classmethod
    def tearDownClass(cls):
        if len(cls.receipts) == 58:
            receipt = {'schema_version': '1.0.0',
                       'interpretation': '55 full selected-activity targets; three R1 controlled-component matrix targets',
                       'policy': cls.tolerance,
                       'resource_set_id': cls.resources.resource_set_id,
                       'source_lock_sha256': hashlib.sha256(LOCK.read_bytes()).hexdigest(),
                       'domain_artifact_sha256': hashlib.sha256(DOMAIN.read_bytes()).hexdigest(),
                       'native_vector_sha256': {key: cls.lock['vectors'][key]['sha256']
                                                for key in ('M1', 'R1', 'selected4')},
                       'targets': cls.receipts}
            (ROOT/'build/task-10/apartment-a1/native-comparison.json').write_text(
                json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
        cls.temporary.cleanup()

    def selected(self, inputs, seed, capture=None):
        from atlas_schedules.residential import selected
        if capture is None:
            return selected.generate_unit_occupancy_interior_lighting(inputs, seed, self.resources)
        actual_producer = selected.simulate_activities
        def record(*args):
            result = actual_producer(*args)
            capture.append(result)
            return result
        with patch.object(selected, 'simulate_activities', record):
            return selected.generate_unit_occupancy_interior_lighting(inputs, seed, self.resources)

    def assert_channels(self, result, case, locator):
        self.assertEqual(set(result['channels']), {'occupants', 'lighting_interior'})
        metrics = {}
        for name, actual in result['channels'].items():
            expected = case['channels'][name]
            self.assertEqual(len(actual), 8760, (locator, name))
            self.assertEqual(len(expected), 8760, (locator, name))
            self.assertTrue(all(math.isfinite(x) and 0 <= x <= 1 for x in actual), (locator, name))
            failures = [(hour, x, y) for hour, (x, y) in enumerate(zip(actual, expected))
                        if abs(x-y) > max(self.tolerance['abs_tol'], self.tolerance['rel_tol']*abs(y))]
            self.assertEqual(failures, [], (locator, name, failures[:1]))
            metrics[name] = {'samples': len(actual), 'mismatch_count': len(failures),
                             'first_mismatch_hour': failures[0][0] if failures else None,
                             'maximum_absolute_error': max(abs(x-y) for x, y in zip(actual, expected)),
                             'maximum_relative_error': max((abs(x-y)/abs(y) for x, y in zip(actual, expected)
                                                            if y != 0), default=0.0)}
        return metrics

    def assert_activity(self, activity, case, locator):
        self.assertEqual(activity['occupant_types'], case['occupant_types'], locator)
        self.assertEqual(activity['unit_offset_minutes'], case['unit_offset_minutes'], locator)
        if 'resident_states' in case:
            self.assertEqual(activity['resident_states'], case['resident_states'], locator)
        if 'resident_state_runs' in case:
            expected = [[state for length, state in resident for _ in range(length)]
                        for resident in case['resident_state_runs']]
            self.assertEqual(activity['resident_states'], expected, locator)
        for key in ('decisions', 'main_state', 'enduse_states'):
            if key in case:
                self.assertEqual(activity[key], case[key], (locator, key))
        if 'stream_seeds' in case:
            self.assertEqual(activity['enduse_seeds'],
                             {key: value for key, value in case['stream_seeds'].items() if key != 'main'}, locator)

    def test_archived_same_argument_selected_parity(self):
        targets = [('M1', i, case) for i, case in enumerate(self.m1)
                   if case['inputs']['year'] == 2007 and isinstance(case['inputs']['residents'], int)
                   and case['inputs']['residents'] > 0 and
                   {'occupants', 'lighting_interior'} <= set(case['channels'])]
        targets += [('R1', i, case) for i, case in enumerate(self.r1)
                    if case['inputs']['year'] == 2007 and case['inputs']['residents'] > 0 and
                    {'occupants', 'lighting_interior'} <= set(case['channels'])]
        self.assertEqual((sum(source == 'M1' for source, _, _ in targets),
                          sum(source == 'R1' for source, _, _ in targets)), (6, 48))
        self.assertEqual(len(targets), 54)
        observed_location_n = {
            (case['inputs']['state'], case['inputs']['latitude'], case['inputs']['longitude'],
             case['inputs']['time_zone_utc_offset'], int(case['inputs']['residents']))
            for _, _, case in targets}
        observed_location_n.update(
            (case['inputs']['state'], case['inputs']['latitude'], case['inputs']['longitude'],
             case['inputs']['time_zone_utc_offset'], case['inputs']['residents'])
            for case in self.native4
            if case['status'] == 'executed_source_occupancy_and_lighting_methods')
        self.assertEqual(len(observed_location_n), 41)
        # R1 component harness cases 49-51 replace the native resident-state
        # trajectories with synthetic all-home/all-away controls after the
        # source activity call. Their visible selected arguments are identical
        # to case 0, but selected outputs differ. They are archive inventory,
        # not same-argument pure method comparisons.
        synthetic = [entry for entry in targets if entry[0] == 'R1' and entry[1] in (49, 50, 51)]
        self.assertEqual([entry[2]['case_id'] for entry in synthetic],
                         ['component_no_events', 'component_boundary', 'component_all_absent'])
        self.assertTrue(all(entry[2]['unit_seed'] == self.r1[0]['unit_seed'] and
                            selected_inputs(entry[2]) == selected_inputs(self.r1[0])
                            for entry in synthetic))
        self.assertTrue(all(entry[2]['channels']['occupants'] != self.r1[0]['channels']['occupants']
                            for entry in synthetic))
        receipts = []
        for source, index, case in targets:
            if (source, index) in {('R1', 49), ('R1', 50), ('R1', 51)}:
                continue
            locator = f'{source}#/cases/{index}'
            inputs = selected_inputs(case)
            # The pinned source uses geometry_num_occupants.to_i; public selected inputs are integer.
            raw = inputs['residents']
            inputs['residents'] = int(raw)
            self.assertEqual(inputs['residents'], int(raw), locator)
            captured = []
            result = self.selected(inputs, case['unit_seed'], captured)
            self.assertEqual(len(captured), 1, locator)
            self.assert_activity(captured[0], case, locator)
            metrics = self.assert_channels(result, case, locator)
            self.assertEqual(result['source_context']['residents_input'], inputs['residents'])
            receipts.append((locator, case['unit_seed'], raw, inputs['residents']))
            self.receipts.append({'locator': locator, 'case_id': case['case_id'],
                                  'proof_kind': 'full_selected_activity', 'unit_seed': case['unit_seed'],
                                  'residents_raw': raw, 'residents_effective_integer': inputs['residents'],
                                  'discrete_checkpoint_status': 'all_available_exact',
                                  'channels': metrics})
        self.assertEqual(len(receipts), 51)
        for index, case in enumerate(self.native4):
            if case['status'] != 'executed_source_occupancy_and_lighting_methods':
                continue
            locator = f'selected4#/cases/{index}'
            captured = []
            result = self.selected(selected_inputs(case), case['unit_seed'], captured)
            self.assertEqual(len(captured), 1, locator)
            self.assert_activity(captured[0], case, locator)
            metrics = self.assert_channels(result, case, locator)
            receipts.append((locator, case['unit_seed'], case['inputs']['residents'], case['inputs']['residents']))
            self.receipts.append({'locator': locator, 'case_id': case['case_id'],
                                  'proof_kind': 'full_selected_activity', 'unit_seed': case['unit_seed'],
                                  'residents_raw': case['inputs']['residents'],
                                  'residents_effective_integer': case['inputs']['residents'],
                                  'discrete_checkpoint_status': 'available_states_types_seeds_offset_exact',
                                  'channels': metrics})
        self.assertEqual(len(receipts), 55)
        self.assertEqual(len([r for r in receipts if r[0].startswith('selected4')]), 4)

    def test_location_tuple_not_coordinate_cartesian(self):
        from atlas_schedules.residential import selected
        validate_selected_inputs = selected.validate_selected_inputs
        locations = self.domain['locations']
        self.assertEqual(len(locations), 37)
        for location in locations:
            inputs = {'year': 2007, 'holidays': [], 'residents': 1,
                      **{key: location[key] for key in
                         ('state', 'latitude', 'longitude', 'time_zone_utc_offset')}}
            validate_selected_inputs(inputs, locations)
        base = selected_inputs(self.m1[0])
        foreign = dict(base, state='ZZ')
        recombined = dict(base, state='CA', latitude=locations[1]['latitude'] + 0.001)
        perturbed = dict(base, latitude=base['latitude'] + 0.00001)
        for changed in (foreign, recombined, perturbed):
            with self.subTest(changed=changed), self.assertRaises(GeneratorError):
                validate_selected_inputs(changed, locations)
        for invalid in (0, -1, 2.0, True, '2'):
            with self.subTest(residents=invalid), self.assertRaises(GeneratorError):
                self.selected(dict(base, residents=invalid), 42)
        validate_selected_inputs({'year': 2007, 'holidays': [], 'residents': 0}, locations)
        with patch.object(selected, 'simulate_activities', side_effect=AssertionError('RNG entered')):
            for invalid_inputs in (dict(base, state='ZZ'), dict(base, residents=0),
                                   dict(base, residents=2.0), dict(base, year=2008)):
                with self.subTest(pre_rng=invalid_inputs), self.assertRaises(GeneratorError):
                    self.selected(invalid_inputs, 42)

    def test_controlled_component_capture_protocol(self):
        """Three R1 native vectors replace matrices after real source activity draws."""
        from atlas_schedules.residential.selected import _selected_shapes
        inputs = selected_inputs(self.r1[0])
        captured = []
        baseline = self.selected(inputs, self.r1[0]['unit_seed'], captured)
        self.assert_channels(baseline, self.r1[0], 'R1#/cases/0')
        self.assertEqual(len(captured), 1)
        base_activity = captured[0]
        for index in (49, 50, 51):
            case = self.r1[index]
            locator = f'R1#/cases/{index}'
            self.assertEqual(selected_inputs(case), inputs)
            self.assertEqual(case['unit_seed'], self.r1[0]['unit_seed'])
            self.assertEqual(case['occupant_types'], base_activity['occupant_types'])
            self.assertEqual(case['unit_offset_minutes'], base_activity['unit_offset_minutes'])
            self.assertEqual(case['main_state'], base_activity['main_state'])
            self.assertEqual(case['enduse_states'], base_activity['enduse_states'])
            self.assertEqual(case['component_states'], case['resident_state_runs'])
            activity = dict(base_activity)
            activity['resident_states'] = [[state for length, state in resident for _ in range(length)]
                                           for resident in case['component_states']]
            self.assertEqual([len(trace) for trace in activity['resident_states']],
                             [35040]*inputs['residents'])
            result = _selected_shapes(activity, inputs, self.resources, self.domain)
            metrics = self.assert_channels(result, case, locator)
            self.receipts.append({'locator': locator, 'case_id': case['case_id'],
                                  'proof_kind': 'controlled_component_post_activity_state_override',
                                  'harness_locator': 'scripts/reference_schedule_generator.rb:11-23,52-54,151-155',
                                  'unit_seed': case['unit_seed'], 'residents_raw': inputs['residents'],
                                  'residents_effective_integer': inputs['residents'],
                                  'discrete_checkpoint_status': 'retained_rng_type_offset_exact; controlled_states_exact',
                                  'channels': metrics})

    def test_variable_integer_cohort_source_loop(self):
        self.assertEqual({int(case['inputs']['residents']) for case in self.r1
                          if case['inputs']['residents'] > 0}, {1, 2, 3, 4, 5, 6})
        for n in (1, 2, 3, 6, 7):
            captured = []
            result = self.selected(dict(selected_inputs(self.m1[0]), residents=n), 42, captured)
            self.assertEqual(len(captured[0]['resident_states']), n)
            self.assertEqual(result['source_context']['simulated_residents'], n)
            for values in result['channels'].values():
                self.assertEqual(len(values), 8760)
                self.assertAlmostEqual(max(values), 1.0)

    def test_selected_receipt_omits_raw_trajectories(self):
        result = self.selected(selected_inputs(self.m1[0]), 42)
        receipt = result['source_context']
        for key in ('resident_states', 'decisions', 'main_state', 'enduse_states'):
            self.assertNotIn(key, receipt)
        self.assertEqual(set(receipt['enduse_seeds']),
                         {'hygiene', 'dishwasher', 'clothes_washer', 'clothes_dryer', 'ev', 'cooking'})
        self.assertEqual(receipt['activity_status'], 'simulated_source_activities')
        self.assert_channels(result, self.m1[0], 'M1#/cases/0')

    def test_no_unrequested_operands_and_wrapper_boundary(self):
        from atlas_schedules.residential.activity import simulate_activities
        from atlas_schedules.residential.shapes import occupancy_shapes
        inputs = selected_inputs(self.m1[0])
        forbidden = {'weather_id', 'installed', 'bedrooms', 'appliances', 'events'}
        self.assertTrue(forbidden.isdisjoint(inputs))
        with patch.object(self.resources, 'get', wraps=self.resources.get) as resource_get:
            self.selected(inputs, 42)
        self.assertTrue(all(call.args[0] in {'residential', 'reference'}
                            for call in resource_get.call_args_list))
        self.assertTrue(all(call.args[1] in self.lock['residential_resources']
                            if call.args[0] == 'residential' else call.args[1] == 'apartment-timing-domain'
                            for call in resource_get.call_args_list))
        activity = simulate_activities(inputs, 42, self.resources)
        with self.assertRaises(GeneratorError):
            occupancy_shapes(activity, inputs, self.resources)

    def test_resource_integrity_and_independence(self):
        entries = self.resources.manifest['resources']
        self.assertEqual(len(entries), 33)
        self.assertEqual({(e['kind'], e['key']) for e in entries},
                         {('residential', name) for name in self.lock['residential_resources']} |
                         {('reference', 'apartment-timing-domain')})
        self.assertNotEqual(self.resources.resource_set_id,
                            json.loads((ROOT/'atlas_schedules/data/manifest.json').read_text())['resource_set_id'])
        self.assertEqual({e['key']: e['sha256'] for e in entries if e['kind'] == 'residential'},
                         self.lock['residential_resources'])
        root = self.resources.root
        entry = next(e for e in entries if e['key'] == 'apartment-timing-domain')
        target = root/entry['path']
        original = target.read_bytes()
        try:
            target.write_bytes(original + b' ')
            with self.assertRaises(GeneratorError):
                ResourceSet(root, self.resources.resource_set_id)
        finally:
            target.write_bytes(original)
        extra = root/'reference'/'extra.json'
        try:
            extra.write_text('{}', encoding='utf-8')
            with self.assertRaises(GeneratorError):
                ResourceSet(root, self.resources.resource_set_id)
        finally:
            extra.unlink()
        try:
            target.unlink()
            with self.assertRaises(GeneratorError):
                ResourceSet(root, self.resources.resource_set_id)
        finally:
            target.write_bytes(original)

    def test_source_producer_rejects_modified_lock_and_domain(self):
        from scripts.schedule_generator_apartment_timing import build_apartment_timing_test_resources
        altered = copy.deepcopy(self.lock)
        key = next(iter(altered['residential_resources']))
        altered['residential_resources'][key] = '0'*64
        with self.assertRaises(GeneratorError):
            build_apartment_timing_test_resources(
                Path(self.temporary.name)/'bad-lock', self.domain, altered, ROOT/'data/raw')
        changed_domain = copy.deepcopy(self.domain)
        changed_domain['locations'][0]['state'] = 'ZZ'
        with self.assertRaises(GeneratorError):
            build_apartment_timing_test_resources(
                Path(self.temporary.name)/'bad-domain', changed_domain, self.lock, ROOT/'data/raw')
        with patch.object(ResourceSet, 'load', side_effect=AssertionError('Default M1 read')):
            independent = build_apartment_timing_test_resources(
                Path(self.temporary.name)/'independent', self.domain, self.lock, ROOT/'data/raw')
        self.assertEqual(independent.resource_set_id, self.resources.resource_set_id)


if __name__ == '__main__':
    unittest.main()
