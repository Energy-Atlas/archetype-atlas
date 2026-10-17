"""Retail/Office S1 authority transition: exact delta, retained predecessor, nothing else moved."""
import copy
import unittest

from atlas_schedules.errors import GeneratorError
from scripts import schedule_generator_runtime_cut_ro_s1 as transition


class RetailOfficeS1Transition(unittest.TestCase):
    def setUp(self):
        self.lock = transition._read(transition.ROOT, transition.LOCK)
        self.record = transition._read(transition.ROOT, transition.TRANSITION)

    def test_complete_transition(self):
        result = transition.verify_ro_s1_transition()
        self.assertTrue(result['passed'])
        self.assertEqual(result['changed'], list(transition.CHANGED))

    def test_unapproved_stale_missing_or_foreign_rows_reject(self):
        then = transition._read(transition.ROOT, transition.THEN_LOCK)
        def unapproved(lock):
            row = next(r for r in lock['current_dependencies'] if r['source_path'] == 'atlas_schedules/service_graph.py')
            row['sha256'] = '0' * 64
        def stale(lock):
            old = next(r for r in then['current_dependencies'] if r['source_path'] == 'atlas_schedules/commercial/parametric.py')
            index = next(i for i, r in enumerate(lock['current_dependencies']) if r['source_path'] == old['source_path'])
            lock['current_dependencies'][index] = copy.deepcopy(old)
        def missing(lock): lock['current_dependencies'] = [r for r in lock['current_dependencies'] if r['source_path'] != transition.ADDED[0]]
        def foreign(lock): lock['current_dependencies'].append({'source_path': 'tests/foreign.py', 'sha256': '0' * 64, 'size_bytes': 1})
        def evidence(lock): lock['verification_evidence'] = [r for r in lock['verification_evidence'] if r['source_path'] != transition.COVERING]
        def history(lock): lock['timing_evidence'] = None
        def extra_key(lock): lock['later_authority'] = {}
        for change in (unapproved, stale, missing, foreign, evidence, history, extra_key):
            lock = copy.deepcopy(self.lock); change(lock)
            with self.subTest(change=change.__name__), self.assertRaises(GeneratorError):
                transition.verify_ro_s1_transition(lock=lock)

    def test_transition_record_must_match_retained_and_current_bytes(self):
        for field in ('predecessor', 'changed', 'added', 'relocated'):
            record = copy.deepcopy(self.record)
            if field == 'predecessor': record['predecessor']['sha256'] = '0' * 64
            elif field == 'changed': record['changed'][0]['historical_path'] = 'data/foreign.py'
            elif field == 'relocated': record['relocated']['size_bytes'] = 1
            else: record['added'] = []
            with self.subTest(field=field), self.assertRaises(GeneratorError):
                transition.verify_ro_s1_transition(transition=record)


if __name__ == '__main__': unittest.main()
