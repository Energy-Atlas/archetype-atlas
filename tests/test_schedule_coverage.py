"""Coverage counts track applied variants and distinguish exclusions from gaps."""
import copy
import importlib
import unittest

from scripts.common import ROOT, load_atlas, load_json


class ScheduleCoverageTests(unittest.TestCase):
    def inputs(self):
        data = load_atlas(ROOT/'data/releases/v0.2.0')
        supplement = ROOT/'data/resolution-releases/v0.3.0'
        resolutions = load_json(supplement/'resolutions.json')
        return data, resolutions

    def test_source_and_resolved_schedules_have_clear_denominators(self):
        data, resolutions = self.inputs()
        report = importlib.import_module('scripts.schedule_coverage').build(data, resolutions)
        self.assertEqual(report['commercial']['active_program_records'], 734)
        self.assertEqual(report['commercial']['required_schedule_fields'], 5138)
        self.assertEqual(report['commercial']['missing_schedule_fields'], 523)
        self.assertEqual(report['commercial']['missing_by_field'], {
            'service_water_heating_schedule_id':485,
            'heating_setpoint_schedule_id':19, 'cooling_setpoint_schedule_id':19})
        self.assertEqual(report['residential']['missing_by_column']['refrigerator'], 38)
        self.assertEqual(report['residential']['missing_by_column']['lighting_interior'], 3)
        self.assertFalse(report['scope']['apply_hvac_unavailability'])
        self.assertFalse(report['near_full_coverage_claim'])

    def test_an_explicit_resolution_reduces_gap_once_without_touching_source(self):
        data, resolutions = self.inputs()
        original = copy.deepcopy(data)
        module = importlib.import_module('scripts.schedule_coverage')
        before = module.build(data, resolutions)
        missing = before['commercial']['missing_records'][0]
        resolutions['resolutions'].append({'record_table':'programs','record_id':missing['record_id'],
            'field':missing['field'], 'resolved_value':{'constant_value':0}, 'rule':'test_only'})
        after = module.build(data, resolutions)
        self.assertEqual(after['commercial']['missing_schedule_fields'],522)
        self.assertEqual(data,original)

    def test_historical_and_unresolved_views_use_their_selected_supplement(self):
        data, _ = self.inputs()
        module = importlib.import_module('scripts.schedule_coverage')
        historical = module.build(data,load_json(ROOT/'data/resolution-releases/v0.1.0/resolutions.json'),
                                  supplement_version='v0.1.0')
        self.assertEqual(historical['resolution_supplement'],'v0.1.0')
        self.assertEqual(historical['commercial']['missing_schedule_fields'],1208)
        self.assertEqual(historical['residential']['missing_profile_fields'],107)
        original = module.build(data,{'resolutions':[]},supplement_version=None)
        self.assertIsNone(original['resolution_supplement'])
        self.assertEqual(original['residential']['missing_profile_fields'],574)


if __name__ == '__main__':
    unittest.main()
