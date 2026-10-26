"""DOE schedule conversion and the reconciliation overlay on the writer sources."""
import unittest

from scripts import idf_schedules, reconciliation_values

COMPACT = ['S', 'Fraction', 'Through: 6/30', 'For: Weekdays SummerDesignDay', 'Until: 07:30', '0.1', 'Until: 24:00', '0.9',
           'For: Saturday', 'Until: 24:00', '0.5', 'For: AllOtherDays', 'Until: 24:00', '0.0',
           'Through: 12/31', 'For: Weekdays', 'Until: 24:00', '0.7', 'For: Holiday', 'Until: 24:00', '0.2',
           'For: AllDays', 'Until: 24:00', '0.3']


class ConversionTests(unittest.TestCase):
    def test_compact_rules_convert_to_the_same_year(self):
        days = idf_schedules.calendar_days([('Independence Day', 'July 4'), ('New Years Day', 'January 1')])
        rules = reconciliation_values.ruleset(COMPACT)
        expected, subhour = idf_schedules.evaluate_compact(COMPACT, days)
        got = idf_schedules.evaluate_ruleset(rules, lambda r: r['values'] * (24 // len(r['values'])), days)
        self.assertTrue(subhour)
        self.assertEqual([k for k in days if not idf_schedules.same(expected[k], got[k])], [])
        self.assertEqual(rules[0]['day_types'], 'Default')
        self.assertEqual(rules[-1]['end_date'][:10], '2014-12-31')


if __name__ == '__main__':
    unittest.main()
