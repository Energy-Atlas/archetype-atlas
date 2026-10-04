"""Conservation and scope guards for the finite Medium Office draw pilot."""
import copy
import importlib
import math
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.common import ROOT, load_atlas, load_json, dump_json
from scripts.semantics import profile


class WaterEquivalentTests(unittest.TestCase):
    def module(self):
        return importlib.import_module('scripts.water_equivalent')

    def test_normalization_preserves_draw_for_all_days_and_source_rules(self):
        data = load_atlas(ROOT/'data/releases/v0.2.0')
        packet = self.module().build(data)
        source = next(s for s in data['schedules'] if s['id'] == packet['source_schedule_id'])
        equivalent = packet['equivalent_schedule']
        self.assertEqual(packet['program_id'], 'program-29f8fa7a1d5e5afcf1f0')
        self.assertEqual(packet['allocation_weight'], 1)
        self.assertEqual(packet['peak_divisor'], 0.57)
        for original, derived in zip(source['rules'], equivalent['rules']):
            self.assertEqual({k:v for k,v in original.items() if k != 'values'},
                             {k:v for k,v in derived.items() if k != 'values'})
        for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Hol', 'SmrDsn', 'WntrDsn']:
            for date in ['01-01', '06-15', '12-31']:
                for original, normalized in zip(profile(source['rules'], day, date),
                                                profile(equivalent['rules'], day, date)):
                    self.assertTrue(0 <= normalized <= 1)
                    self.assertTrue(math.isclose(original * packet['rated_flow_m3_s_m2'],
                                                 normalized * packet['equivalent_peak_flow_m3_s_m2'],
                                                 rel_tol=1e-12, abs_tol=1e-16))
        self.assertEqual(len(packet['source_space_names']), 15)
        self.assertEqual(len(set(packet['source_space_names'])), 15)
        self.assertNotIn('Core_bottom', packet['physical_fixture_locations'])

    def test_conflicting_schedule_or_unreviewed_program_fails(self):
        original = load_atlas(ROOT/'data/releases/v0.2.0')
        for field, value in [('service_water_heating_schedule_id', 'other'),
                             ('source_space_type', 'Other'), ('template', '90.1-2019')]:
            data = copy.deepcopy(original)
            row = next(p for p in data['programs'] if p['id'] == 'program-29f8fa7a1d5e5afcf1f0')
            row[field] = value
            with self.assertRaises(ValueError):
                self.module().build(data)

    def test_missing_or_negative_flow_is_not_invented(self):
        original = load_atlas(ROOT/'data/releases/v0.2.0')
        for value in [None, -1, float('nan')]:
            data = copy.deepcopy(original)
            row = next(p for p in data['programs'] if p['id'] == 'program-29f8fa7a1d5e5afcf1f0')
            row['source_attributes']['service_water_heating_peak_flow_per_area'] = value
            with self.assertRaises(ValueError):
                self.module().build(data)

    def test_source_releases_are_not_mutated(self):
        data = load_atlas(ROOT/'data/releases/v0.2.0')
        original = copy.deepcopy(data)
        self.module().build(data)
        self.assertEqual(data, original)

    def test_frozen_pilot_schema_checksums_and_reproduction(self):
        packet = self.module().validate_bundle()
        self.assertEqual(packet['newly_resolved_missing_schedules'],0)
        self.assertEqual(packet['target_temperature_degC'],60)
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)/'pilot'
            shutil.copytree(self.module().DEFAULT,target)
            changed = load_json(target/'water-equivalent.json')
            changed['allocation_weight'] = 0.5
            dump_json(target/'water-equivalent.json',changed)
            with self.assertRaisesRegex(ValueError,'checksum'):
                self.module().validate_bundle(target)
        with self.assertRaisesRegex(ValueError,'overwrite'):
            self.module().freeze(self.module().DEFAULT)


if __name__ == '__main__':
    unittest.main()
