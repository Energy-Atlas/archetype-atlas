"""Protect the stock identity, units, and literal source value of triage recovery."""
import copy
import unittest

from scripts.investigate_er_triage import recover_scorecard, verified_bytes


class TriageRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.cells = {
            'BuildingSummary!C4': 'Hospital post-1980 construction',
            'ZoneSummary!A8': 'ER_Triage_Mult4_Flr_1',
            'ZoneSummary!L2': 'Elec Plug and Process (W/m2)',
            'ZoneSummary!L8': 21.5278,
        }

    def test_preserves_literal_si_without_multiplying_zone_multiplier(self):
        self.assertEqual(recover_scorecard(self.cells), 21.5278)

    def test_rejects_another_stock_variant_or_units(self):
        for key, value in [('BuildingSummary!C4', 'Hospital pre-1980 construction'),
                           ('ZoneSummary!L2', 'Elec Plug and Process (W/ft2)'),
                           ('ZoneSummary!A8', 'ER_Trauma1_Flr_1')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                cells = copy.deepcopy(self.cells)
                cells[key] = value
                recover_scorecard(cells)

    def test_missing_or_nonpositive_equipment_is_not_recovered_as_zero(self):
        for value in (None, 0, -1, '21.5278', float('nan')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                recover_scorecard({**self.cells, 'ZoneSummary!L8': value})

    def test_checksum_mismatch_fails_before_parsing(self):
        with self.assertRaisesRegex(ValueError, 'checksum'):
            verified_bytes(b'changed workbook', '0' * 64)


if __name__ == '__main__':
    unittest.main()
