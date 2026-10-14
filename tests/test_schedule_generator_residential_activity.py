import copy
import importlib.util
import json
from pathlib import Path
import unittest

from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet
from atlas_schedules.ruby_random import SourceRandom
from scripts.schedule_generator_reference import load_residential_reference

ROOT=Path(__file__).resolve().parents[1]


class ResidentialActivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest=json.loads((ROOT/'atlas_schedules/data/manifest.json').read_text())
        cls.resources=ResourceSet.load(manifest['resource_set_id'])
        cls.cases={v['case_id']:v for v in load_residential_reference()['cases']}

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('atlas_schedules.residential.activity'),
                             'Residential activity kernel is missing')
        from atlas_schedules.residential.activity import simulate_activities
        self.simulate=simulate_activities

    def test_activity_trace_matches_source_fixture(self):
        # Wrong initial/duration/transition row, rotation, or draw breaks these traces.
        for case in self.cases.values():
            with self.subTest(case=case['case_id']):
                actual=self.simulate(case['inputs'],case['unit_seed'],self.resources)
                self.assertEqual(len(actual['resident_states']),int(case['inputs']['residents']))
                for trace in actual['resident_states']:self.assertEqual(len(trace),35040)
                for key in ('resident_states','occupant_types','decisions','unit_offset_minutes','main_state','enduse_states'):
                    self.assertEqual(actual[key],case[key],key)

    def test_multiple_residents_and_offset(self):
        for key in ('one','multiple','different_seed'):
            case=self.cases[key];actual=self.simulate(case['inputs'],case['unit_seed'],self.resources)
            self.assertEqual(actual['occupant_types'],case['occupant_types'])
            self.assertEqual(actual['unit_offset_minutes'],case['unit_offset_minutes'])
            self.assertGreaterEqual(actual['unit_offset_minutes'],-30)
            self.assertLess(actual['unit_offset_minutes'],30)
            for stream,state in dict(main=actual['main_state'],**actual['enduse_states']).items():
                rng=SourceRandom(0);rng.setstate(json.loads(json.dumps(state)))
                expected=SourceRandom(0);expected.setstate(case['main_state'] if stream=='main' else case['enduse_states'][stream])
                self.assertEqual([rng.random() for _ in range(4)],[expected.random() for _ in range(4)])

    def test_zero_residents_skip_before_rng_allocation(self):
        case=self.cases['zero'];actual=self.simulate(case['inputs'],case['unit_seed'],self.resources)
        self.assertEqual(actual['status'],'upstream_zero_residents_skip')
        self.assertIsNone(actual['main_state']);self.assertIsNone(actual['unit_offset_minutes'])
        self.assertEqual(actual['enduse_seeds'],{});self.assertEqual(actual['enduse_states'],{})
        self.assertEqual(actual['resident_states'],[])

    def test_preserve_source_resident_truncation_without_count_scaling(self):
        inputs=copy.deepcopy(self.cases['one']['inputs']);inputs['residents']=1.9
        actual=self.simulate(inputs,42,self.resources)
        self.assertEqual(actual['residents_input'],1.9)
        self.assertEqual(actual['simulated_residents'],1)
        self.assertEqual(actual['resident_states'],self.cases['one']['resident_states'])

    def test_invalid_activity_inputs_fail_explicitly(self):
        for changes in ({'residents':True},{'residents':-.5},{'residents':float('nan')},{'residents':.5},{'year':2008}):
            with self.subTest(changes=changes):
                inputs=dict(self.cases['one']['inputs'],**changes)
                with self.assertRaises(GeneratorError):self.simulate(inputs,42,self.resources)
        for seed in (True,-1,1.2):
            with self.subTest(seed=seed),self.assertRaises(GeneratorError):
                self.simulate(self.cases['zero']['inputs'],seed,self.resources)
