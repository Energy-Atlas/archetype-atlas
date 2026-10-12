import copy
import importlib.util
import unittest

from scripts.common import ROOT
from scripts.definition_release import read_bundle
from scripts.schedule_json import has_full_coverage


class CompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = read_bundle(ROOT / 'data/definition-releases/v0.1.1')
        cls.office = next(p for p in cls.bundle['programs'] if p['building_type'] == 'MediumOffice'
                          and p['template'] == '90.1-2019' and p['evidence_view'] == 'reviewed'
                          and p.get('detail') == 'SourcePrograms' and 'plenum' not in p['name'].lower())

    def exporter(self, bundle=None):
        self.assertIsNotNone(importlib.util.find_spec('scripts.program_json_v3'))
        from scripts.program_json_v3 import ProgramExporter
        return ProgramExporter(bundle or self.bundle)

    def test_medium_office_ready_contract(self):
        e = self.exporter()
        out = e.export(self.office['id'], 'defaulted')
        self.assertEqual(out['schema_version'], '3.0.0')
        self.assertEqual(e.validate(out), [])
        self.assertTrue(all(l['value'] > 0 for l in out['loads']))
        lights = next(l for l in out['loads'] if l['type'] == 'lighting')
        self.assertEqual(set(lights['heat_fractions']), {'radiant', 'visible', 'return_air'})
        water = next(l for l in out['loads'] if l['type'] == 'hot_water')
        self.assertEqual(water['inlet_temperature']['method'], 'CorrelationFromWeatherFile')
        self.assertNotIn('inlet_temperature_schedule_id', water)
        self.assertIn('weather_file', out['required_bindings'])
        for s in out['schedules'].values():
            self.assertTrue(has_full_coverage(s))
        schedule = out['schedules'][lights['schedule_id']]
        holiday = next(r for r in schedule['rules'] if r['day_types'] == ['Hol'])
        sunday = next(r for r in schedule['rules'] if r['day_types'] == ['Sun'])
        self.assertEqual(holiday['values'], sunday['values'])

    def test_attic_has_no_fake_loads_or_thermostats(self):
        p = next(p for p in self.bundle['programs'] if 'attic' in p['name'].lower())
        out = self.exporter().export(p['id'], 'defaulted')
        self.assertEqual(out['controls']['conditioning_state'], 'unconditioned')
        self.assertNotIn('heating_setpoint_schedule_id', out['controls'])
        self.assertNotIn('activity_schedule_id', out['controls'])
        self.assertEqual(out['loads'], [])
        self.assertTrue(out['metadata']['absent_demands'])

    def test_unapproved_occupied_load_unknown_is_rejected(self):
        p = copy.deepcopy(self.office)
        p['id'] = 'unknown-active-equipment'
        next(l for l in p['loads'] if l['quantity'] == 'electric_equipment')['value'] = None
        b = dict(self.bundle, programs=self.bundle['programs'] + [p])
        with self.assertRaisesRegex(ValueError, 'unresolved.*electric_equipment'):
            self.exporter(b).export(p['id'], 'defaulted')

    def test_data_center_leap_day_uses_february(self):
        e = self.exporter()
        out = e.export('program-0d0d5461f1cee89d04d148eb', 'defaulted')
        l = next(l for l in out['loads'] if l['type'] == 'electric_equipment')
        s = out['schedules'][l['schedule_id']]
        self.assertTrue(has_full_coverage(s))
        feb = [r for r in s['rules'] if r['start_date'] == '02-01']
        self.assertTrue(feb)
        self.assertTrue(all(r['end_date'] == '02-29' for r in feb))
        self.assertFalse(any(r['day_types'] == ['Default'] for r in s['rules']))

    def test_mixture_closes_controls_and_recovers_triage(self):
        e = self.exporter()
        out = e.export('program-00781e0b526174a15665721b', 'defaulted')
        self.assertEqual(e.validate(out), [])
        triage = next(p for p in self.bundle['programs'] if p.get('source_id') == 'program-a4ffe6755aa603f0cfcd')
        out = e.export(triage['id'], 'defaulted')
        self.assertAlmostEqual(next(l['value'] for l in out['loads'] if l['type'] == 'electric_equipment'), 21.5278)

    def test_residential_components_remain_self_contained_and_scope_explicit(self):
        out = self.exporter().export('program-0079ce7b163bdb1bd0154dbe', 'defaulted')
        aggregation = out['metadata']['aggregation']
        for group in aggregation['groups']:
            for component in group['components']:
                self.assertIn(component['load']['schedule_id'], aggregation['component_schedules'])
        self.assertIn('general_water_use_heat_gains', out['metadata']['excluded_scope'])
        self.assertEqual(out['metadata']['scope_status'], 'complete_within_agreed_program_scope')
        self.assertEqual(out['metadata']['pending_decisions'], [])

    def test_mixture_recovers_occupied_leaf_activity_before_fallback(self):
        out = self.exporter().export('program-131bcfba407138256934455a', 'defaulted')
        occupancy = [l for l in out['loads'] if l['type'] == 'occupancy']
        self.assertTrue(occupancy)
        for load in occupancy:
            sid = load.get('activity_schedule_id', out['controls'].get('activity_schedule_id'))
            values = [v for r in out['schedules'][sid]['rules'] for v in r['values']]
            self.assertEqual(set(values), {132.0})


if __name__ == '__main__':
    unittest.main()
