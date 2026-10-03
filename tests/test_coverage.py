import copy
import csv
import unittest

from scripts.build import build_atlas
from scripts.common import ROOT, load_json
from scripts.validate import validate_atlas
from scripts.release import verify_release


class FullCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atlas = build_atlas()

    def test_every_commercial_suite_type_has_program_and_mapping(self):
        selection = load_json(ROOT/'sources/selection.json')
        programs = {r['building_type'] for r in self.atlas['programs']}
        mappings = {r['building_type'] for r in self.atlas['mappings']}
        for suite in ['doe_reference', 'pnnl_commercial']:
            self.assertEqual(set(selection['coverage_suites'][suite]) - programs, set())
            self.assertEqual(set(selection['coverage_suites'][suite]) - mappings, set())

    def test_residential_configurations_cover_all_seven_classes(self):
        self.assertTrue('residential_archetypes' in self.atlas, 'residential configurations missing')
        rows = self.atlas['residential_archetypes']
        self.assertEqual(len(rows), 41)
        self.assertEqual({r['building_type'] for r in rows},
                         set(load_json(ROOT/'sources/selection.json')['residential_buildings']))
        options = {r['id']: r for r in self.atlas['residential_options']}
        for row in rows:
            self.assertTrue(row['option_ids'])
            for oid in row['option_ids']:
                option = options[oid]
                self.assertEqual(row['selected_options'][option['parameter']], option['option'])
            self.assertFalse(row['simulation_ready'])
            self.assertIsNone(row['conditioned_floor_area_m2'])

    def test_residential_values_and_context_match_source_fixture(self):
        self.assertTrue('residential_archetypes' in self.atlas, 'residential configurations missing')
        with (ROOT/'data/raw/resstock/project_national/resources/sdr_minimal_buildstock.csv').open(encoding='utf-8') as stream:
            source = {r['Building']: r for r in csv.DictReader(stream)}
        for row in self.atlas['residential_archetypes']:
            raw = source[row['source_building_id']]
            self.assertEqual(row['occupants'], float(raw['Occupants']))
            self.assertAlmostEqual(row['heating_base_C'], (float(raw['Heating Setpoint'][:-1])-32)/1.8)
            self.assertAlmostEqual(row['cooling_base_C'], (float(raw['Cooling Setpoint'][:-1])-32)/1.8)
            self.assertEqual(row['source_context']['Geometry Building Type Height'], raw['Geometry Building Type Height'])
            for key, value in row['selected_options'].items():
                self.assertEqual(value, raw[key])

    def test_residential_wrong_option_reference_rejected(self):
        self.assertTrue('residential_archetypes' in self.atlas, 'residential configurations missing')
        a = copy.deepcopy(self.atlas)
        row = a['residential_archetypes'][0]
        wrong = next(r for r in a['residential_options'] if r['parameter'] in row['selected_options']
                     and r['option'] != row['selected_options'][r['parameter']])
        row['option_ids'].append(wrong['id'])
        self.assertTrue(any('residential option' in e for e in validate_atlas(a)))

    def test_older_frozen_release_remains_verifiable(self):
        self.assertEqual(verify_release(ROOT/'data/releases/v0.1.0'), [])

    def test_full_source_input_atlas_validates_with_documented_overlap(self):
        self.assertEqual(validate_atlas(self.atlas), [])
        overlaps = [r for r in self.atlas['residential_archetypes'] if r['heating_base_C'] > r['cooling_base_C']]
        self.assertEqual(len(overlaps), 6)
        self.assertTrue(all(r['thermostat_base_overlap'] and not r['simulation_ready'] for r in overlaps))

    def test_dummy_summer_design_selector_matches_generator_substring_semantics(self):
        from scripts.semantics import profile
        rules = [{'day_types': 'Default', 'start_date': '2014-01-01', 'end_date': '2014-12-31', 'values': [1]},
                 {'day_types': 'DummySmrDsn', 'start_date': '2014-01-01', 'end_date': '2014-12-31', 'values': [0]}]
        self.assertEqual(profile(rules, 'SmrDsn', '07-01'), [0]*24)
        self.assertEqual(profile(rules, 'WntrDsn', '01-01'), [1]*24)

    def test_specialized_refrigeration_evidence_is_retained(self):
        self.assertTrue('specialized_rules' in self.atlas, 'specialized rules missing')
        rules = self.atlas['specialized_rules']
        self.assertTrue(any(r['rule_type'] == 'refrigeration_walkins' for r in rules))
        self.assertTrue(any(r['source_attributes'].get('building_type') == 'SuperMarket' for r in rules))

    def test_independent_comparison_rejects_residential_value_and_argument_drift(self):
        from scripts.compare import compare_sources
        a = copy.deepcopy(self.atlas)
        a['residential_archetypes'][0]['occupants'] += 1
        self.assertTrue(compare_sources(a)['errors'])
        a = copy.deepcopy(self.atlas)
        a['residential_options'][0]['arguments']['invented_argument'] = 'wrong'
        self.assertTrue(compare_sources(a)['errors'])

    def test_coverage_audit_detects_missing_template_type_and_residential_class(self):
        from scripts import coverage
        self.assertTrue(coverage.coverage_report(self.atlas)['typology_coverage_complete'])
        a = copy.deepcopy(self.atlas)
        a['programs'] = [r for r in a['programs'] if not
                         (r['building_type'] == 'Hospital' and r['template'] == '90.1-2019')]
        self.assertFalse(coverage.coverage_report(a)['typology_coverage_complete'])
        a = copy.deepcopy(self.atlas)
        a['residential_archetypes'] = [r for r in a['residential_archetypes'] if r['building_type'] != 'ManufacturedHome']
        self.assertFalse(coverage.coverage_report(a)['typology_coverage_complete'])


if __name__ == '__main__':
    unittest.main()
