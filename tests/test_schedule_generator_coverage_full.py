"""Catalogue identity/dependency census must distinguish evidence from shipment."""
import copy
import json
from pathlib import Path
import unittest

from scripts import schedule_generator_coverage as coverage
from atlas_schedules.resources import ResourceSet

ROOT = Path(__file__).resolve().parents[1]


class FullCoverageTests(unittest.TestCase):
    def inventory(self):
        self.assertTrue(callable(getattr(coverage, 'build_catalogue_inventory', None)),
                        'Actual per-channel/dependency catalogue inventory is missing')
        return coverage.build_catalogue_inventory()

    def test_every_current_record_has_channel_coverage(self):
        inventory = self.inventory()
        self.assertEqual(len(inventory['programs']), 1900)
        self.assertEqual(len(inventory['compositions']), 378)
        programs = {p['id']: p for p in inventory['programs']}
        self.assertEqual(sum(p['scope'] == 'whole_dwelling' for p in programs.values()), 41)
        self.assertTrue(all(p['channels'] or p['absence_evidence'] for p in programs.values()))
        for composition in inventory['compositions']:
            self.assertTrue(all(m['program_id'] in programs for m in composition['members']))
        for program in programs.values():
            self.assertTrue(all(c['status'] in {'generated', 'source_fixed', 'absent',
                            'requires_binding', 'unsupported'} and c['source_state'] in
                            {'known', 'unknown', 'absent', 'shared', 'excluded'}
                            for c in program['channels']))

    def test_dependency_normalization_preserves_template_and_region(self):
        inventory = self.inventory()
        programs = inventory['programs']
        self.assertEqual({p['template'] for p in programs if p['scope'] != 'whole_dwelling'},
                         {'90.1-2007', '90.1-2013', '90.1-2019', 'DOE Ref Pre-1980', 'DOE Ref 1980-2004'})
        for program in programs:
            self.assertEqual(program['dependencies']['template'], program['template'])
            if program['scope'] == 'whole_dwelling':
                self.assertTrue(program['dependencies']['weather']['sha256'])
                self.assertTrue(program['dependencies']['state'])
            else:
                self.assertIsNone(program['climate'])
                self.assertEqual(program['dependencies']['climate_policy'], 'shared_source_rules_no_fabricated_climate_records')

    def test_two_3b_locations_remain_distinct(self):
        inventory = self.inventory()
        locations = [v for v in inventory['doe_locations'] if v['climate_zone'] == '3B']
        self.assertEqual({v['location'] for v in locations}, {'Los Angeles', 'Las Vegas'})
        self.assertEqual({v['variant'] for v in locations}, {'coastal', 'inland'})
        self.assertTrue(all(v['weather_binding'] is None and v['program_ids'] == [] for v in locations))
        actual = [p for p in inventory['programs'] if p['scope'] == 'whole_dwelling' and p['climate'] == '3B']
        self.assertEqual(len(actual), 3)
        self.assertTrue(all(p['dependencies']['weather']['station_filename'] not in
                            {'Los Angeles', 'Las Vegas'} for p in actual))

    def test_unsupported_and_excluded_are_not_complete(self):
        inventory = self.inventory()
        self.assertFalse(inventory['full_extraction_complete'])
        states = {c['source_state'] for p in inventory['programs'] for c in p['channels']}
        self.assertTrue({'unknown', 'shared', 'absent', 'excluded'} <= states)
        self.assertTrue(any(c['status'] == 'requires_binding' for p in inventory['programs'] for c in p['channels']))
        self.assertTrue(all(not c['complete'] for p in inventory['programs'] for c in p['channels']
                            if c['source_state'] == 'excluded' or c['status'] in {'unsupported','requires_binding'}))

    def test_compiled_channel_inventory_covers_resolved_slot_semantics(self):
        manifest = json.loads((ROOT/'atlas_schedules/data/manifest.json').read_text())
        resources = ResourceSet.load(manifest['resource_set_id'])
        inventory = {p['id']:p for p in coverage.build_catalogue_inventory(resources)['programs']}
        for case in resources.manifest['cases']:
            recipe = resources.get('program',case['program_id'])['recipe']
            rows = inventory[case['program_id']]['channels']
            actual = {c.get('runtime_slot') for c in rows if c['status'] in {'generated','source_fixed'}}
            self.assertEqual(actual,{s['slot'] for s in recipe['resolved']['slots']})
            for row in rows:
                if row['status'] in {'generated','source_fixed'}:
                    self.assertTrue(row['resolved_source_evidence'])

    def test_original_unknown_zero_fixture_has_explicit_resolved_absence(self):
        programs = {p['id']:p for p in self.inventory()['programs']}
        vacant = programs['program-e0993499165be6c7b5bf9efa']
        original_unknown = [c for c in vacant['channels'] if c['source_state']=='unknown']
        self.assertTrue(original_unknown)
        self.assertTrue(all(c['status']=='absent' and c['resolved_absence_evidence'] for c in original_unknown))

    def test_declared_recipe_is_distinct_from_all_channel_completeness(self):
        inventory=self.inventory()
        for program in inventory['programs']:
            self.assertEqual(program['declared_recipe_complete'],program['runtime_status'] in {'compiled','accepted_inactive'})
            if any(not c['complete'] for c in program['channels']): self.assertFalse(program['full_record_complete'])

    def test_approved_inactive_unknowns_retain_exact_resolution_receipts(self):
        inventory={p['id']:p for p in self.inventory()['programs']}
        plenum=inventory['program-f41ee055c01c510fa42096ae']
        unknown=[c for c in plenum['channels'] if c['source_state']=='unknown' and c['slot'] not in {'heating_setpoint','cooling_setpoint'}]
        self.assertTrue(unknown)
        self.assertTrue(all(c['status']=='absent' and c['original_value'] is None and c['resolved_absence_evidence'] for c in unknown))
        missing=[c for c in plenum['channels'] if c['slot'] in {'heating_setpoint','cooling_setpoint'}]
        self.assertTrue(all(c['status']=='absent' and c['resolved_absence_evidence'] for c in missing))
        for row in unknown+missing:
            proof=row['resolved_absence_evidence']['resolution_receipts']
            self.assertTrue(proof)
            self.assertTrue(all(p['resource_key']==plenum['id'] and p['pointer'].startswith(('/recipe/resolved/evidence/0/','/definition/parameters/conditioning')) and len(p['resource_sha256'])==64 for p in proof))
