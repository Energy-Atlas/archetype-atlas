"""IDF reading and full-year schedule evaluation on small synthetic inputs."""
import tempfile
import unittest
from pathlib import Path

from scripts import idf_reader, idf_schedules

OLD_LAYOUT = """
Version,7.2;
Building,b,0.0,City,0.04,0.2,FullExterior,25,6;
GlobalGeometryRules,UpperLeftCorner,Counterclockwise,Relative;
Zone,Z1,0,10,0,0,1,2,,;
BuildingSurface:Detailed,Z1_Wall,Wall,C,Z1,Outdoors,,SunExposed,WindExposed,AutoCalculate,4,
  0,0,3, 0,0,0, 4,0,0, 4,0,3;
FenestrationSurface:Detailed,Z1_Win,Window,G,Z1_Wall,,AutoCalculate,,,1,4,
  1,0,2, 1,0,1, 3,0,1, 3,0,2;
Lights,Z1_L,Z1,SCH,Watts/Area,,10.0,,0.0,0.7,0.2,1.0,General;
"""

NEW_LAYOUT = """
Version,22.1;
Building,b,0.0,City,0.04,0.2,FullExterior,25,6;
GlobalGeometryRules,UpperLeftCorner,Counterclockwise,Relative;
Zone,Z1,0,0,0,0,1,1,,;
BuildingSurface:Detailed,Z1_Wall,Wall,C,Z1,,Outdoors,,SunExposed,WindExposed,AutoCalculate,4,
  0,0,3, 0,0,0, 4,0,0, 4,0,3;
FenestrationSurface:Detailed,Z1_Win,Window,G,Z1_Wall,,AutoCalculate,,1,4,
  1,0,2, 1,0,1, 3,0,1, 3,0,2;
"""


def model(text):
    directory = tempfile.TemporaryDirectory()
    path = Path(directory.name)/'m.idf'
    path.write_text(text)
    return directory, idf_reader.Model(path)


class ReaderTests(unittest.TestCase):
    def test_old_layout_reads_relative_vertices_and_window_multiplier(self):
        directory, m = model(OLD_LAYOUT)
        with directory:
            wall = m.surfaces()[0]
            self.assertEqual(wall['boundary'], 'outdoors')
            self.assertEqual(wall['vertices'][0], (10.0, 0.0, 3.0))
            self.assertAlmostEqual(idf_reader.area(wall['vertices']), 12.0)
            window = m.fenestration()[0]
            self.assertEqual((window['multiplier'], window['host_type']), (1.0, 'wall'))
            self.assertAlmostEqual(idf_reader.area(window['vertices']), 2.0)
            self.assertEqual(m.zones['z1']['multiplier'], 2)
            self.assertEqual(m.loads('lights')[0]['fractions']['radiant'], 0.7)

    def test_new_layout_skips_the_space_field(self):
        directory, m = model(NEW_LAYOUT)
        with directory:
            self.assertEqual(m.version, (22, 1))
            self.assertEqual(m.surfaces()[0]['boundary'], 'outdoors')
            self.assertAlmostEqual(idf_reader.area(m.fenestration()[0]['vertices']), 2.0)

    def test_orientation_follows_the_outward_normal(self):
        south = [(0, 0, 3), (0, 0, 0), (4, 0, 0), (4, 0, 3)]
        self.assertEqual(idf_reader.orientation(south), 'S')


class ScheduleTests(unittest.TestCase):
    FIELDS = ['OCC', 'Fraction', 'Through: 12/31', 'For: Weekdays SummerDesignDay', 'Until: 08:30', '0.0',
              'Until: 24:00', '1.0', 'For: AllOtherDays', 'Until: 24:00', '0.0']

    def test_holidays_and_design_days_follow_the_compact_rules(self):
        days = idf_schedules.calendar_days([('New Years Day', 'January 1'), ('Labor Day', '1st Monday in September')])
        values, subhour = idf_schedules.evaluate_compact(self.FIELDS, days)
        self.assertTrue(subhour)
        self.assertEqual(days['2006-09-04'][1], 'Hol')
        self.assertEqual(values['2006-09-04'], [0.0] * 24)
        self.assertEqual(values['SmrDsn'][8], 0.5)
        self.assertEqual(values['2006-01-03'][9], 1.0)

    def test_ruleset_holidays_take_default_without_a_hol_rule(self):
        days = idf_schedules.calendar_days([('New Years Day', 'January 1')])
        rules = [{'day_types': 'Default|Wkdy', 'start_date': '2014-01-01', 'end_date': '2014-12-31', 'v': 1.0},
                 {'day_types': 'Sat|Sun', 'start_date': '2014-01-01', 'end_date': '2014-12-31', 'v': 0.0}]
        values = idf_schedules.evaluate_ruleset(rules, lambda r: [r['v']] * 24, days)
        self.assertEqual(values['2006-01-01'], [1.0] * 24)
        compact, _ = idf_schedules.evaluate_compact(
            ['S', 'F', 'Through: 12/31', 'For: Weekdays', 'Until: 24:00', '1', 'For: AllOtherDays', 'Until: 24:00', '0'],
            days)
        keys = idf_schedules.differing_days(compact, values)
        self.assertEqual(idf_schedules.classify(keys, days), 'holidays and design days only')


YEAR_SCHEDULES = """
Version,23.1;
Schedule:Day:Hourly,Wkday,Fraction,0,0,0,0,0,0,0.5,1,1,1,1,1,1,1,1,1,1,0.5,0,0,0,0,0,0;
Schedule:Day:Hourly,Wkend,Fraction,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2;
Schedule:Day:Interval,Summer,Fraction,No,Until: 06:30,0.1,Until: 24:00,0.9;
Schedule:Week:Compact,Normal,For: Weekdays,Wkday,For: CustomDay1,Wkend,For: AllOtherDays,Wkend;
Schedule:Week:Compact,Flat,AllDays,Summer;
Schedule:Week:Daily,Daily,Wkend,Wkday,Wkday,Wkday,Wkday,Wkday,Wkend,Wkend,Summer,Wkend,Wkend,Wkend;
Schedule:Year,Occ,Fraction,Normal,1,1,5,31,Flat,6,1,8,31,Daily,9,1,12,31;
Schedule:Constant,Setpoint,Temperature,22.2;
Schedule:Compact,NoColon,Temperature,Through: 12/31,For: AllDays,Until 6:00,20,Until 24:00,22;
"""


class YearScheduleTests(unittest.TestCase):
    """Schedule:Year, Week and Day objects convert to atlas rules that match them on every day."""

    def schedules(self):
        return idf_schedules.Schedules(idf_reader.parse(YEAR_SCHEDULES))

    def test_year_schedule_converts_and_checks_over_the_full_year(self):
        s = self.schedules()
        days = idf_schedules.calendar_days([])
        rules = s.checked_ruleset('Occ', days)
        self.assertEqual([(r['day_types'], r['start_date'], r['end_date']) for r in rules],
                         [('Default', '2000-01-01', '2000-05-31'), ('Wknd|Hol|SmrDsn|WntrDsn', '2000-01-01', '2000-05-31'),
                          ('Default', '2000-06-01', '2000-08-31'),
                          ('Default', '2000-09-01', '2000-12-31'), ('Wknd|Hol|WntrDsn', '2000-09-01', '2000-12-31'),
                          ('SmrDsn', '2000-09-01', '2000-12-31')])
        self.assertAlmostEqual(rules[2]['values'][6], 0.5)  # 06:30 inside the hour: energy-conserving mean
        values = s.evaluate('Occ', days)
        self.assertAlmostEqual(values['2006-07-04'][7], 0.9, places=12)
        self.assertAlmostEqual(values['2006-01-02'][8], 1.0, places=12)  # a Monday
        self.assertAlmostEqual(values['2006-01-01'][8], 0.2, places=12)  # a Sunday

    def test_constant_and_colonless_compact_schedules(self):
        s = self.schedules()
        self.assertEqual(s.checked_ruleset('Setpoint'),
                         [{'day_types': 'Default', 'start_date': '2000-01-01', 'end_date': '2000-12-31',
                           'type': 'Constant', 'values': [22.2]}])
        rules = s.checked_ruleset('NoColon')
        self.assertEqual(rules[0]['values'][:7], [20.0] * 6 + [22.0])

    def test_a_wrong_conversion_is_caught(self):
        s = self.schedules()
        s.ruleset = lambda name: [idf_schedules.rule('Default', (1, 1), (12, 31), [0.2])]
        with self.assertRaises(ValueError):
            s.checked_ruleset('Occ')


if __name__ == '__main__':
    unittest.main()


class ReferenceLoadTests(unittest.TestCase):
    def test_match_grades_relative_differences(self):
        from scripts.reference_loads import match
        self.assertEqual(match(10.0, 10.005), 'exact')
        self.assertEqual(match(10.0, 10.05), 'rounding')
        self.assertEqual(match(10.0, 11.0), 'differ')
        self.assertEqual(match(0.0, 0.0), 'exact')
        self.assertIsNone(match(None, 1.0))

    def test_standards_rows_convert_to_si(self):
        from scripts.reference_loads import standards_values
        values = standards_values({'occupancy_per_area': 5.0, 'lighting_per_area': 1.0,
                                   'additional_lighting_per_area': None, 'electric_equipment_per_area': 0.5,
                                   'gas_equipment_per_area': None})
        self.assertAlmostEqual(values['occupancy'], 0.0538196, places=6)
        self.assertAlmostEqual(values['lighting'], 10.7639, places=3)
        self.assertIsNone(values['gas_equipment'])
