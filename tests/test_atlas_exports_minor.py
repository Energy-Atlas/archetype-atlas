"""Release 1.1.0 exports: Program JSON 5.1.0, constructions 4.1.0 / 3.1.0 and building services 1.0.0."""
import json
import unittest

from scripts import atlas_delta_release
from scripts.atlas_exports import Release


@unittest.skipUnless((atlas_delta_release.TARGET/'manifest.json').exists(), 'release 1.1.0 not written')
class MinorExportTests(unittest.TestCase):
    """Program JSON 5.1.0, constructions 4.1.0 / 3.1.0 and building services 1.0.0 validate and carry the new fields."""

    @classmethod
    def setUpClass(cls):
        cls.release = Release(release='1.1.0')

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.release

    def program(self, prefix):
        return next(p for p in self.release.program_ids() if p.startswith(prefix))

    def test_programs(self):
        er = self.release.program(self.program('doe-ref-1980-2004.hospital.source.er-exam'), 'filled')
        self.assertEqual(er['schema_version'], '5.1.0')
        self.assertEqual(len(er['source_calendar']['holidays']), 10)
        self.assertIn(er['controls']['humidifying_setpoint_schedule_id'], er['schedules'])
        self.assertEqual(er['schedules'][er['controls']['humidifying_setpoint_schedule_id']]['unit'], '%')
        kitchen = self.release.program(self.program('doe-ref-1980-2004.full-service-restaurant.source.kitchen'), 'filled')
        self.assertEqual({g['sensible_fraction'] for g in kitchen['water_use_gains']}, {0.2})
        self.assertTrue(kitchen['building_service_ids'])
        library = self.release.program(self.program('doe-ref-1980-2004.primary-school.source.library'), 'source')
        self.assertEqual([s['name'] for s in library['source_spaces']], ['Library_Media_Center_ZN_1_FLR_1'])
        warehouse = self.release.program(self.program('doe-ref-1980-2004.warehouse.source.office'), 'source')
        self.assertTrue(any('schedule_id' in a for a in warehouse['alternates']))
        for prefix in ('90-1-2019.hospital.source.', 'doe-ref-pre-1980.small-hotel.general.'):
            self.release.program(self.program(prefix), 'filled')

    def test_constructions_and_building_services(self):
        [path] = [p for p in self.release.files if p.startswith('commercial/doe-ref-pre-1980/super-market/constructions/')]
        set_id = json.loads(self.release.files[path])['id']
        detailed = self.release.construction(set_id, '5-a', 'detailed')
        unified = self.release.construction(set_id, '5-a', 'unified')
        self.assertEqual((detailed['schema_version'], unified['schema_version']), ('4.1.0', '3.1.0'))
        self.assertEqual(detailed['infiltration']['default_method'], 'fixed_source_reference_natural_ach')
        services = self.release.building_services('doe-ref-pre-1980/super-market')
        self.assertEqual({s['end_use'] for s in services['services']} >= {'refrigeration_case', 'refrigeration_rack'}, True)
        self.assertTrue(all(s['load']['schedule_id'] in services['schedules'] for s in services['services'] if s['load'].get('schedule_id')))


if __name__ == '__main__':
    unittest.main()
