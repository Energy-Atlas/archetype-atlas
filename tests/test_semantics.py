import unittest
from scripts import semantics


class SemanticsTests(unittest.TestCase):
    def test_si_conversion_and_null_preservation(self):
        self.assertAlmostEqual(semantics.convert(1, 'W/ft2'), 10.76391041671)
        self.assertAlmostEqual(semantics.convert(5, 'people/1000 ft2'), 0.0538195520835)
        self.assertAlmostEqual(semantics.convert(68, 'F'), 20)
        self.assertAlmostEqual(semantics.convert(1, 'cfm/person'), 0.0004719474432)
        self.assertIsNone(semantics.convert(None, 'W/ft2'))
        with self.assertRaises(ValueError):
            semantics.convert(1, 'guess')

    def test_schedule_default_weekday_design_and_seasonal_rules(self):
        rules = [
            {'day_types': 'Default', 'start_date': '2014-01-01', 'end_date': '2014-12-31', 'values': [0]*24},
            {'day_types': 'Wkdy', 'start_date': '2014-01-01', 'end_date': '2014-12-31', 'values': [1]*24},
            {'day_types': 'Wkdy', 'start_date': '2014-06-01', 'end_date': '2014-08-31', 'values': [0.5]*24},
            {'day_types': 'SmrDsn', 'start_date': '2014-01-01', 'end_date': '2014-12-31', 'values': [0.8]*24},
        ]
        self.assertEqual(semantics.profile(rules, 'Wkdy', '02-01'), [1]*24)
        self.assertEqual(semantics.profile(rules, 'Wkdy', '07-01'), [0.5]*24)
        self.assertEqual(semantics.profile(rules, 'Sat', '02-01'), [0]*24)
        self.assertEqual(semantics.profile(rules, 'SmrDsn', '07-01'), [0.8]*24)
        with self.assertRaises(ValueError):
            semantics.profile(rules, 'Bogus', '02-01')

    def test_osm_semantics_without_reconstructing_geometry(self):
        text = '''OS:SpaceType,
{type}, !- Handle
Office, !- Name
Office, !- Standards Building Type
WholeBuilding - Md Office; !- Standards Space Type
OS:Space,
{space}, !- Handle
Core, !- Name
{type}, !- Space Type Name
{zone}, !- Thermal Zone Name
Yes; !- Part of Total Floor Area
OS:ThermalZone,
{zone}, !- Handle
Core Zone, !- Name
3; !- Multiplier
'''
        spaces = semantics.spaces(text)
        self.assertEqual(spaces[0]['source_space_type'], 'WholeBuilding - Md Office')
        self.assertEqual(spaces[0]['source_building_type'], 'Office')
        self.assertEqual(spaces[0]['multiplier'], 3)

    def test_ambiguous_program_lookup_is_rejected(self):
        r = {'building_type': 'Office', 'space_type': 'WholeBuilding - Md Office'}
        with self.assertRaises(ValueError):
            semantics.unique_match([r, r], 'Office', 'WholeBuilding - Md Office')

    def test_options_lookup_continuations_retain_all_measures(self):
        text = 'System\tOption A\tMeasureOne\tx=1\n\t\tMeasureTwo\ty=2\nSystem\tOption B\tMeasureOne\tx=3\n'
        rows = list(semantics.option_rows(text))
        self.assertEqual(rows[1], (2, ['System', 'Option A', 'MeasureTwo', 'y=2'], 1))
        self.assertEqual(rows[2][1][1], 'Option B')


if __name__ == '__main__':
    unittest.main()
