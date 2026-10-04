"""Finite source defaults and operational vacancy rules must remain scoped."""
import copy
import unittest
from scripts.common import ROOT,load_json,load_atlas
from scripts.fixed_background import build
from scripts.resolve import resolve_records

class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.data=load_atlas(ROOT/'data/releases/v0.2.0')
        self.policy=load_json(ROOT/'sources/resolution-policy.json')
        self.policy['fixed_background_record_ids']=[r['id'] for r in self.data['residential_archetypes']]
        self.policy['fixed_background_all_records']=True
        self.policy['fixed_default_names']=['refrigerator','freezer','lighting_exterior']

    def test_occupied_refrigeration_and_exterior_use_fixed_source_fractions(self):
        fixed=build(names=self.policy['fixed_default_names'])
        self.assertAlmostEqual(fixed['schedules']['lighting_exterior']['peak_divisor'],.084)
        result=resolve_records(self.data,self.policy,[],fixed)
        rows=result['resolutions']
        self.assertEqual(sum(r['field']=='profile:refrigerator' for r in rows),41)
        self.assertEqual(sum(r['field']=='profile:freezer' for r in rows),41)
        self.assertEqual(sum(r['field']=='profile:lighting_exterior' for r in rows),41)
        self.assertEqual(sum(r['field']=='profile:lighting_exterior' and r['rule']=='fixed_background_default' for r in rows),38)
        self.assertFalse(any('electric_vehicle' in r['field'] for r in rows))

    def test_unknown_refrigeration_binding_cannot_be_interpreted_as_absence(self):
        self.data['residential_archetypes'][0]['selected_options']['Refrigerator']=None
        with self.assertRaisesRegex(ValueError,'Unknown selected background'):
            resolve_records(self.data,self.policy,[],build())

    def test_vacancy_rules_reject_an_occupied_record(self):
        row=self.data['residential_archetypes'][0]
        row['occupants']=2
        review=copy.deepcopy(self.policy['vacancy_zero_reviews'][0]);review['record_id']=row['id']
        self.policy['vacancy_zero_reviews']=[review]
        with self.assertRaisesRegex(ValueError,'vacancy'):
            resolve_records(self.data,self.policy,[],build())

    def test_historical_defaults_still_reproduce(self):
        fixed=build()
        self.assertEqual(fixed,load_json(ROOT/'data/resolution-releases/v0.3.0/fixed-background-schedules.json'))

if __name__=='__main__':unittest.main()
