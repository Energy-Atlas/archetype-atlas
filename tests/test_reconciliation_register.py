"""Reconciliation register rules (ADR 0037) on synthetic zone rows, and the committed register's integrity."""
import json
import unittest
from collections import Counter

from scripts import reconciliation_register as rr
from scripts.common import ROOT

REGISTER = ROOT/'data/reconciliation/doe-reference-v1.json'


def zone(name, value, atlas, quantity='electric_equipment', objects=()):
    loads = {q: 0.0 for q in rr.reference_loads.QUANTITIES}
    loads[quantity] = value
    stored = dict(loads, **{quantity: atlas})
    return {'zone': name, 'floor_m2': 100.0, 'idf': loads, 'objects': list(objects),
            'mapping': {'space_types': ['T'], 'mixed': False},
            'refs': {'atlas': stored, 'atlas_programs': ['program-t']}}


def rows_for(*zones, building_type='X'):
    register = rr.Register()
    rr.program_load_rows(register, 'f.idf', 'doe-ref-1980-2004', building_type, list(zones))
    return [r for r in register.rows if r['field'] == 'electric_equipment']


class RuleTests(unittest.TestCase):
    def test_keep_leave_and_omit_require_a_reason(self):
        with self.assertRaises(AssertionError):
            rr.Register().add(decision='keep', klass='x')

    def test_rounding_is_kept(self):
        [row] = rows_for(zone('a', 10.0, 10.05))
        self.assertEqual((row['klass'], row['decision'], row['reason_id']), ('A7-rounding', 'keep', 'R-ROUNDING'))

    def test_a_printed_factor_of_ten_is_explicitly_wrong(self):
        [row] = rows_for(zone('a', 5.38, 0.5382))
        self.assertEqual((row['klass'], row['decision']), ('A5-explicitly-wrong', 'replace'))

    def test_existing_density_is_kept_with_an_alternate_beyond_half(self):
        [row] = rows_for(zone('a', 10.0, 4.0))
        self.assertEqual((row['klass'], row['decision']), ('A5-existing-density', 'keep'))
        self.assertEqual(row['alternate']['value'], 10.0)
        [row] = rows_for(zone('a', 10.0, 8.0))
        self.assertIsNone(row['alternate'])

    def test_a_nonzero_atlas_density_against_a_doe_zero_is_kept(self):
        [row] = rows_for(zone('a', 0.0, 0.5))
        self.assertEqual(row['decision'], 'keep')

    def test_a_service_folded_into_the_space_type_is_replaced(self):
        elevator = {'class': 'electricequipment', 'outside_space_type_table': True}
        [row] = rows_for(zone('a', 0.0, 2133.0, objects=[elevator]))
        self.assertEqual((row['klass'], row['decision']), ('A5-folded-service', 'replace'))

    def test_absence_in_the_doe_model_fills_zero(self):
        [row] = rows_for(zone('a', 0.0, None))
        self.assertEqual((row['klass'], row['decision'], row['source_value']['value']), ('B5-missing-density', 'fill', 0.0))

    def test_retagged_zones_are_left_to_the_retag_row(self):
        self.assertEqual(rows_for(zone('Storage_Flr1', 5.0, 0.4), building_type='Outpatient'), [])


@unittest.skipUnless(REGISTER.exists(), 'register not generated')
class RegisterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(REGISTER.read_text())

    def test_ids_are_unique_and_summary_matches(self):
        rows = self.document['rows']
        self.assertEqual(len({r['id'] for r in rows}), len(rows))
        self.assertEqual(self.document['summary']['by_decision'], dict(Counter(r['decision'] for r in rows)))

    def test_every_keep_leave_and_omit_cites_a_known_reason(self):
        for r in self.document['rows']:
            if r['decision'] in ('keep', 'leave', 'omit'):
                self.assertIn(r['reason_id'], self.document['reasons'], r['id'])

    def test_no_row_awaits_review(self):
        self.assertEqual([r['id'] for r in self.document['rows'] if r['decision'] not in
                          ('add', 'replace', 'keep', 'fill', 'leave', 'omit')], [])

    def test_inputs_are_pinned(self):
        self.assertEqual(len(self.document['input_sha256']), 30)


if __name__ == '__main__':
    unittest.main()
