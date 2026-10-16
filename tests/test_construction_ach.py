"""Focused fixed-ACH physics and evidence tests; no catalogue/site build."""
import copy
import importlib
import math
import tempfile
from pathlib import Path
import unittest


class FixedACHTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ach = importlib.import_module('scripts.derive_construction_ach')

    def test_residential_exposure_is_not_applied_twice(self):
        fields = {'annual_ach_per_unit_wsf_per_s': {'value': .2 / 3600},
                  'a_ext': {'value': .2}}
        self.assertAlmostEqual(self.ach.residential_ach(fields, .5), .1 / 3600)
        fields['annual_ach_per_unit_wsf_per_s']['value'] = None
        with self.assertRaises(ValueError):
            self.ach.residential_ach(fields, .5)

    def test_surface_centroid_matches_source_polygon_rules(self):
        # Unequal triangles catch a bounding-box or vertex mean shortcut.
        v = [[0,0,0], [2,0,0], [1,0,3], [0,0,1]]
        area = 3.5
        self.assertAlmostEqual(self.ach.surface_centroid_z(v, area), 22/21)
        five = [[0,0,0], [1,0,0], [1,0,1], [.5,0,2], [0,0,1]]
        self.assertEqual(self.ach.surface_centroid_z(five, 1.5), .8)

    def test_wind_height_temperature_and_nonpositive_height(self):
        self.assertAlmostEqual(self.ach.wind_factor(10, 'Country'), 1)
        self.assertLess(self.ach.wind_factor(10, 'City'), 1)
        self.assertEqual(self.ach.wind_factor(0, 'City'), 0)
        self.assertEqual(self.ach.wind_factor(-2, 'City'), 0)
        self.assertAlmostEqual(self.ach.temperature_offset(1.5), 0)
        self.assertGreater(self.ach.temperature_offset(-2), 0)

    def test_commercial_flow_averages_clipped_hourly_factors_and_uses_multipliers(self):
        spaces = [{'volume_m3':100, 'multiplier':2, 'exterior_area_m2':10,
                   'centroid_z_m':10},
                  {'volume_m3':100, 'multiplier':1, 'exterior_area_m2':0,
                   'centroid_z_m':10}]
        # Temperature coefficient zero isolates velocity-squared scaling.
        coefficients = {'a':-.5, 'b':0, 'd':1}
        weather = [(22,0), (22,2)]
        result = self.ach.commercial_ach(spaces, weather, 'Country', .01, coefficients)
        self.assertAlmostEqual(result['mean_flow_m3_s'], .01*10*2*3.5/2)
        self.assertAlmostEqual(result['ach_per_s'], (.01*10*2*3.5/2)/300)
        self.assertEqual(result['reference_volume_m3'], 300)

    def test_coefficients_preserve_source_off_to_on_and_climate_zero_fallback(self):
        rows = [{'building_type':'SmallOffice', 'climate_zone':1, 'air_barrier':False,
                 'hvac_status':'on', 'a':1, 'b':2, 'd':3},
                {'building_type':'SmallOffice', 'climate_zone':1, 'air_barrier':False,
                 'hvac_status':'off', 'a':None, 'b':4, 'd':None}]
        result = self.ach.select_coefficients(rows, 'SmallOffice', '0A')
        self.assertEqual(result['coefficients'], {'a':1, 'b':4, 'd':3})
        self.assertEqual(result['fallback_fields'], ['a','d'])
        self.assertEqual(result['correlation_climate_zone'], 1)
        with self.assertRaises(ValueError):
            self.ach.select_coefficients(rows, 'Unknown', '4A')

    def test_smallhotel_reference_overlay_retains_uninstantiated_scope(self):
        mapping = {'package_id':'construction-1d0774872c8801caa0afdd44',
                   'reference_ids':[], 'candidate_reference_ids':['90.1-2019/SmallHotel'],
                   'status':'source_scope_not_instantiated'}
        result = self.ach.adopt_mapping(mapping)
        self.assertEqual(result['reference_ids'], ['90.1-2019/SmallHotel'])
        self.assertEqual(result['source_mapping_status'], 'source_scope_not_instantiated')
        self.assertEqual(mapping['reference_ids'], [])
        bad = copy.deepcopy(mapping); bad['package_id'] = 'other'
        with self.assertRaises(ValueError):
            self.ach.adopt_mapping(bad)

    def test_invalid_operands_fail_instead_of_becoming_zero(self):
        for wsf in (None, math.nan, -1):
            with self.assertRaises(ValueError):
                self.ach.residential_ach({'annual_ach_per_unit_wsf_per_s':{'value':.1}}, wsf)
        with self.assertRaises(ValueError):
            self.ach.commercial_ach([], [(22,1)], 'City', .1, {'a':0,'b':1,'d':1})

    def test_source_alaska_label_preserves_group_without_inventing_moisture_class(self):
        climates = {'7A':{'wsf':.65,'weather_file_sha256':'same'},
                    '7B':{'wsf':.65,'weather_file_sha256':'same'}}
        row,aliases = self.ach.residential_forcing('7AK',climates)
        self.assertEqual(aliases,['7A','7B'])
        self.assertEqual(row['wsf'],.65)
        climates['7B']['wsf'] = .7
        with self.assertRaises(ValueError):
            self.ach.residential_forcing('7AK',climates)

    def test_changed_weather_is_rejected_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'forcing.epw'
            path.write_text('modified forcing')
            with self.assertRaisesRegex(ValueError,'weather checksum'):
                self.ach.read_weather(path,'0'*64)

    def test_pinned_source_volume_is_retained_under_bounded_sdk_variability(self):
        self.assertEqual(self.ach.reference_volume(1911.3873768131405,1911.36583),1911.36583)
        with self.assertRaisesRegex(ValueError,'volume drift'):
            self.ach.reference_volume(1912,1911.36583)

    def test_stale_python_native_dependency_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Stale native'):
            self.ach.verify_native_dependencies({'input_sha256':{'scripts/derive_construction_ach.py':'0'*64}})


if __name__ == '__main__':
    unittest.main()
