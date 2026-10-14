import copy
import importlib.util
import math
import unittest

from atlas_schedules.errors import GeneratorError
from tests import test_schedule_generator_residential_activity as activity_tests


class ResidentialShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        activity_tests.ResidentialActivityTests.setUpClass()
        cls.resources=activity_tests.ResidentialActivityTests.resources
        cls.cases=activity_tests.ResidentialActivityTests.cases;cls.activities={}

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('atlas_schedules.residential.shapes'),
                             'Coordinated residential shapes are missing')
        from atlas_schedules.residential.activity import simulate_activities
        from atlas_schedules.residential.shapes import occupancy_shapes
        self.shape=occupancy_shapes
        if not self.activities:
            self.activities.update({key:simulate_activities(case['inputs'],case['unit_seed'],self.resources)
                                    for key,case in self.cases.items()})

    def test_all_emitted_shapes_match_independent_raw_source(self):
        for key,case in self.cases.items():
            with self.subTest(case=key):
                actual=self.shape(self.activities[key],case['inputs'],self.resources)
                self.assertEqual(set(actual['channels']),set(case['channels']))
                for slot,expected in case['channels'].items():
                    values=actual['channels'][slot]
                    self.assertEqual(len(expected),8760);self.assertEqual(len(values),8760)
                    for hour,(x,y) in enumerate(zip(values,expected)):
                        self.assertTrue(math.isclose(x,y,rel_tol=1e-6,abs_tol=1e-8),(key,slot,hour,x,y))
                        self.assertGreaterEqual(x,0);self.assertLessEqual(x,1)
                if key!='zero':self.assertEqual(actual['source_context']['fan_months'],case['fan_months'])

    def test_weather_changes_only_dependent_shapes(self):
        base=self.shape(self.activities['one'],self.cases['one']['inputs'],self.resources)
        changed=self.shape(self.activities['weather'],self.cases['weather']['inputs'],self.resources)
        for key in ('resident_states','decisions','main_state','unit_offset_minutes','enduse_states'):
            self.assertEqual(self.activities['one'][key],self.activities['weather'][key])
        for slot in base['channels']:
            if slot=='ceiling_fan':self.assertNotEqual(base['channels'][slot],changed['channels'][slot])
            else:self.assertEqual(base['channels'][slot],changed['channels'][slot])

    def test_location_changes_lighting_only_and_state_changes_emission_not_traces(self):
        base=self.shape(self.activities['one'],self.cases['one']['inputs'],self.resources)
        location=self.shape(self.activities['location'],self.cases['location']['inputs'],self.resources)
        state=self.shape(self.activities['state'],self.cases['state']['inputs'],self.resources)
        for key in ('location','state'):
            self.assertEqual(self.activities[key]['resident_states'],self.activities['one']['resident_states'])
        for slot,values in base['channels'].items():
            if slot.startswith('lighting'):self.assertNotEqual(values,location['channels'][slot])
            else:self.assertEqual(values,location['channels'][slot])
        self.assertNotEqual(base['channels']['occupants'],state['channels']['occupants'])
        self.assertNotEqual(base['source_context']['monthly_shifts'],state['source_context']['monthly_shifts'])

    def test_presence_and_zero_skip_boundaries(self):
        sparse=self.shape(self.activities['sparse'],self.cases['sparse']['inputs'],self.resources)
        self.assertEqual(set(sparse['channels']),{'occupants','lighting_interior'})
        zero=self.shape(self.activities['zero'],self.cases['zero']['inputs'],self.resources)
        self.assertEqual(zero['channels'],{'occupants':[0.0]*8760})
        self.assertFalse(zero['source_context']['rng_consumed'])
        one=self.shape(self.activities['one'],self.cases['one']['inputs'],self.resources)
        self.assertEqual(one['channels']['lighting_interior'],one['channels']['lighting_garage'])
        for slot in sparse['channels']:self.assertEqual(sparse['channels'][slot],one['channels'][slot])

    def test_missing_or_invalid_dependencies_are_not_borrowed(self):
        for key in ('state','latitude','longitude','time_zone_utc_offset','weather_id','installed'):
            inputs=copy.deepcopy(self.cases['one']['inputs']);del inputs[key]
            with self.subTest(missing=key),self.assertRaises(GeneratorError):
                self.shape(self.activities['one'],inputs,self.resources)
        for changes in ({'state':'XX'},{'latitude':float('nan')},{'installed':{}},{'weather_id':'unknown'},{'year':2009}):
            with self.subTest(changes=changes),self.assertRaises(GeneratorError):
                self.shape(self.activities['one'],dict(self.cases['one']['inputs'],**changes),self.resources)
