"""Scope and channel completeness receipts."""
import json
import copy
from pathlib import Path
import unittest

from atlas_schedules.resources import ResourceSet

ROOT = Path(__file__).resolve().parents[1]


class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads((ROOT / 'atlas_schedules/data/manifest.json').read_text())
        cls.resources = ResourceSet.load(manifest['resource_set_id'])

    def test_m1_missing_case_or_channel_blocks_shipment(self):
        from scripts.schedule_generator_coverage import build_coverage, coverage_errors
        coverage = build_coverage(self.resources)
        self.assertEqual(coverage_errors(coverage), [])
        self.assertEqual(coverage['scope']['case_count'], 10)
        self.assertEqual(sum(len(case['channels']) for case in coverage['cases']), 115)
        self.assertEqual(sum(case['status'] == 'accepted_inactive' for case in coverage['cases']), 2)
        missing = json.loads(json.dumps(coverage))
        missing['cases'].pop()
        self.assertTrue(coverage_errors(missing))
        broken = json.loads(json.dumps(coverage))
        channel = next(c for case in broken['cases'] for c in case['channels'] if c['status'] == 'generated')
        channel['status'] = 'failed_validation'
        self.assertTrue(coverage_errors(broken))

    def test_unsupported_outside_scope_is_visible(self):
        from scripts.schedule_generator_coverage import build_coverage
        coverage = build_coverage(self.resources)
        self.assertEqual(coverage['outside_scope']['program_count'], 1890)
        self.assertEqual(coverage['outside_scope']['composition_count'], 378)
        self.assertEqual(len(coverage['outside_scope']['programs']), 1890)
        self.assertEqual(len(coverage['outside_scope']['compositions']), 378)
        self.assertTrue(all(p['status'] in {'unsupported_binding', 'requires_binding'}
                            for p in coverage['outside_scope']['programs']))

    def test_included_evidence_is_closed_and_required(self):
        from scripts.schedule_generator_coverage import build_coverage, coverage_errors
        coverage = build_coverage(self.resources)
        self.assertEqual(coverage_errors(coverage, self.resources), [])
        channels = [channel for case in coverage['cases'] for channel in case['channels']]
        self.assertEqual(len(channels), 115)
        self.assertTrue(all(channel['source_evidence'] for channel in channels))
        office = [case for case in coverage['cases']
                  if case['program_id'] in {'program-0e670d8dc556f7f5bdd7f1a9',
                                            'program-53754431fd3a91a89a631601'}]
        self.assertEqual(len(office), 2)
        for case in office:
            for channel in case['channels']:
                if channel['slot'] == 'occupancy':
                    self.assertEqual(channel['source_evidence']['resource_key'],
                                     'schedule-db120b43964b8b666cd8')
                    self.assertEqual(channel['source_evidence']['pointer'], '/provenance')
        missing = copy.deepcopy(coverage)
        for case in missing['cases']:
            for channel in case['channels']:
                channel['source_evidence'] = None
        self.assertTrue(coverage_errors(missing))
        dangling = copy.deepcopy(coverage)
        dangling['cases'][0]['channels'][0]['source_evidence']['resource_key'] = 'missing-evidence-record'
        self.assertTrue(coverage_errors(dangling, self.resources))
        misplaced = copy.deepcopy(coverage)
        same_program = [channel for channel in misplaced['cases'][0]['channels']
                        if channel['source_evidence']['resource_kind'] == 'program']
        self.assertGreaterEqual(len(same_program), 2)
        same_program[0]['source_evidence'] = copy.deepcopy(same_program[1]['source_evidence'])
        self.assertTrue(coverage_errors(misplaced, self.resources))
        inactive = copy.deepcopy(coverage)
        next(case for case in inactive['cases'] if case['status'] == 'accepted_inactive')['absence_evidence'] = {}
        self.assertTrue(coverage_errors(inactive, self.resources))


if __name__ == '__main__':
    unittest.main()
