import importlib.util
import copy
import json
import math
from pathlib import Path
import unittest

from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet
from atlas_schedules.budgets import reference_budget, bind_budget
from atlas_schedules.calendar import evaluate_rules
from scripts.schedule_generator_reference import load_commercial_reference

ROOT = Path(__file__).resolve().parents[1]


class CommercialParametricTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('atlas_schedules.commercial.parametric'), 'Commercial transform kernel is missing')
        from atlas_schedules.commercial.parametric import transform_commercial
        self.transform = transform_commercial
        self.cases = {case['case_id']: case for case in load_commercial_reference()['cases']}

    def run_case(self, case):
        context = dict(case['source_context'], slot_sources=case['schedules'])
        return self.transform(case['original_channels'], case['operating'], context)

    def compare_case(self, case):
        actual = self.run_case(case)
        self.assertEqual(set(actual['channels']), set(case['channels']))
        for slot, expected in case['channels'].items():
            values = actual['channels'][slot]
            self.assertEqual(len(values), 8760); self.assertEqual(len(expected), 8760)
            for i, (value, want) in enumerate(zip(values, expected)):
                self.assertTrue(math.isclose(value, want, rel_tol=0 if 'setpoint' in slot else 1e-6,
                                            abs_tol=1e-4 if 'setpoint' in slot else 1e-6 if slot=='activity' else 1e-8),
                                (case['case_id'], slot, i, value, want))
            # Native rule selection and time points are discrete decisions;
            # compare each day's actual final rule, not only annual values.
            for day,profile in enumerate(actual['source_context']['transforms'][slot]['daily_profiles'],1):
                key=next(key for key,days in case['final'][slot]['days_used'].items() if day in days)
                native=case['final'][slot]['profiles']['default' if key=='-1' else key]
                self.assertEqual([round(t*60) for t,v in profile],[round(t*60) for t,v in native],(case['case_id'],slot,day))
                for (_,value),(_,want) in zip(profile,native):
                    self.assertTrue(math.isclose(value,want,rel_tol=1e-6,abs_tol=1e-8))
        return actual

    def test_overnight_zero_and_full_day_transforms(self):
        # Replacing source zero/full-day decisions with intuitive special cases fails.
        for name in ('overnight','zero','full_day','weekday_weekend'):
            with self.subTest(case=name): self.compare_case(self.cases[name])

    def test_constants_ramps_and_design_days_match_source(self):
        for name in ('native','short','long','constant_ramp_design','sampled_42'):
            with self.subTest(case=name):
                case = self.cases[name]; actual = self.compare_case(case)
                self.assertEqual(actual['source_context']['special_profiles'], case['special_profiles'])

    def test_inference_requires_explicit_carrier_and_preserves_quantization(self):
        for name in ('native','carrier_weight_0.1','carrier_weight_100'):
            case = self.cases[name]; actual = self.run_case(case)
            self.assertEqual(actual['source_context']['inference']['daily_hoo'],
                             [next(value for value in case['inference']['hoo'].values() if day in value['days_used'])
                              for day in range(1,366)])
        case = self.cases['native']; context = dict(case['source_context'],slot_sources=case['schedules'])
        for field in ('occupancy_aggregation','occupancy_adjustment','slot_sources','slot_modes'):
            bad = copy.deepcopy(context); del bad[field]
            with self.assertRaises(GeneratorError): self.transform(case['original_channels'],case['operating'],bad)

    def test_short_and_long_conserve_original_energy_and_volume_budgets(self):
        # A budget reconstructed after sampling would change these totals.
        manifest = json.loads((ROOT/'atlas_schedules/data/manifest.json').read_text())
        resources = ResourceSet.load(manifest['resource_set_id'])
        program = resources.get('program','program-0e670d8dc556f7f5bdd7f1a9')['definition']
        for slot in ('lighting','electric_equipment','hot_water_volume'):
            load = next(load for load in program['loads'] if load['quantity']==slot)
            demand = dict(load, evidence=[load['evidence_id']], fuel='electricity' if slot!='hot_water_volume' else 'water',host='program')
            target = reference_budget(demand,evaluate_rules(self.cases['native']['schedules'][slot],2007,[])['values'])
            bindings = [bind_budget(target,self.run_case(self.cases[name])['channels'][slot]) for name in ('short','long')]
            self.assertNotEqual(bindings[0]['effective_magnitude']['value'],bindings[1]['effective_magnitude']['value'])
            for binding in bindings:
                self.assertEqual(binding['reference_target'],target)
                self.assertTrue(math.isclose(binding['scaling_receipt']['achieved_total'],target['total'],rel_tol=1e-8))

    def test_missing_or_mismatched_source_channels_fail(self):
        case=self.cases['native'];context=dict(case['source_context'],slot_sources=case['schedules'])
        for channels in ({'occupancy': [0]*8760},dict(case['original_channels'],lighting=[0]*8759)):
            with self.assertRaises(GeneratorError): self.transform(channels,case['operating'],context)
        for changes in ({'slot_sources':None},{'slot_modes':None},{'occupancy_aggregation':None},
                        {'source_clock':{'TZ':'America/New_York'}},{'steps_per_hour':True}):
            with self.assertRaises(GeneratorError):
                self.transform(case['original_channels'],case['operating'],dict(context,**changes))
