"""Scope and channel completeness receipts."""
import json
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


if __name__ == '__main__':
    unittest.main()
