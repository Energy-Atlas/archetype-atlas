import copy
import importlib.util
import unittest

from scripts.common import ROOT
from scripts.definition_release import read_bundle


class CompletenessTests(unittest.TestCase):
    def test_report_names_unresolved_program_and_never_calls_it_complete(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.program_completeness'))
        from scripts.program_completeness import validate_programs
        b = read_bundle(ROOT / 'data/definition-releases/v0.1.1')
        office = next(p for p in b['programs'] if p['id'] == 'program-8c35a40eb0181596e0bfcac4')
        broken = copy.deepcopy(office)
        broken['id'] = 'broken-occupied-program'
        next(l for l in broken['loads'] if l['quantity'] == 'lighting')['value'] = None
        b['programs'].append(broken)
        result = validate_programs(b, [office['id'], broken['id']])
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['ready'], 1)
        self.assertEqual(result['failures'][0]['program_id'], broken['id'])
        self.assertIn('lighting', result['failures'][0]['reason'])
        self.assertTrue(result['source_bundle_unchanged'])


if __name__ == '__main__':
    unittest.main()
