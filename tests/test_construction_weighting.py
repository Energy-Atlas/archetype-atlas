import importlib.util
import tempfile
from pathlib import Path
import unittest


class ConstructionWeightingTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_weighting'))
        from scripts import construction_weighting
        return construction_weighting

    def record(self):
        program = {'template': 'test', 'building_type': 'Office', 'space_type': 'Room'}
        return {'id': 'test/Office', 'template': 'test', 'building_type': 'Office', 'geometry_file': 'model.osm',
                'spaces': [{'name': 'A', 'floor_area_m2': 100, 'volume_m3': 300, 'multiplier': 3,
                            'counted_floor_area': True, 'story': 'One', 'native_program': program,
                            'surfaces': [{'id': 'wall', 'type': 'Wall', 'boundary': 'Outdoors',
                                          'gross_area_m2': 40, 'net_area_m2': 30,
                                          'adjacent_id': None,
                                          'openings': [{'id': 'window', 'type': 'FixedWindow', 'area_m2': 10, 'multiplier': 1}]}],
                            'internal_mass': []}]}

    def test_multiplies_source_once_and_preserves_zero_component_exposure(self):
        p = self.module().build_commercial_profile(self.record(), {})
        self.assertEqual(p['counted_floor_area_m2'], 300)
        s = p['spaces'][0]
        self.assertEqual(s['exposure_m2']['ExteriorWall'], 90)
        self.assertEqual(s['exposure_m2']['ExteriorWindow'], 30)
        self.assertEqual(s['exposure_m2']['ExteriorRoof'], 0)
        self.assertEqual(s['floor_share'], 1)
        self.assertEqual(s['volume_m3'], 900)

    def test_noncounted_scope_gets_no_fabricated_floor_share(self):
        record = self.record()
        extra = dict(record['spaces'][0], name='Plenum', counted_floor_area=False, multiplier=1)
        record['spaces'].append(extra)
        p = self.module().build_commercial_profile(record, {})
        self.assertEqual(p['counted_floor_area_m2'], 300)
        self.assertIsNone(p['spaces'][1]['floor_share'])
        self.assertEqual(p['spaces'][1]['exposure_m2']['ExteriorWall'], 30)

    def test_native_source_key_resolves_cross_context_without_typology_alias(self):
        record = self.record()
        record['id'], record['building_type'] = 'test/DetailedOffice', 'DetailedOffice'
        index = {('test', 'Office', 'Room'): ['published-native-program']}
        p = self.module().build_commercial_profile(record, index)
        self.assertEqual(p['spaces'][0]['program']['definition_ids'], ['published-native-program'])
        self.assertEqual(p['spaces'][0]['program']['native_building_type'], 'Office')
        self.assertEqual(p['building_type'], 'DetailedOffice')

    def test_floor_and_ceiling_pair_is_one_mass_ledger_item(self):
        record = self.record()
        record['spaces'][0]['surfaces'] = [
            {'id': 'floor', 'adjacent_id': 'ceiling', 'type': 'Floor', 'boundary': 'Surface',
             'net_area_m2': 50, 'gross_area_m2': 50, 'openings': []},
            {'id': 'ceiling', 'adjacent_id': 'floor', 'type': 'RoofCeiling', 'boundary': 'Surface',
             'net_area_m2': 50, 'gross_area_m2': 50, 'openings': []}]
        ledger = self.module().build_commercial_profile(record, {})['floor_inventory']
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger[0]['area_m2'], 150)
        self.assertEqual(set(ledger[0]['source_surface_ids']), {'floor', 'ceiling'})

    def test_unequal_pair_multipliers_are_order_independent_and_explicit(self):
        record = self.record()
        a = dict(record['spaces'][0], name='Corridor', multiplier=1)
        b = dict(record['spaces'][0], name='Room', multiplier=4)
        a['surfaces'] = [{'id':'wall-a','adjacent_id':'wall-b','type':'Wall','boundary':'Surface',
                          'gross_area_m2':20,'net_area_m2':20,'openings':[]}]
        b['surfaces'] = [{'id':'wall-b','adjacent_id':'wall-a','type':'Wall','boundary':'Surface',
                          'gross_area_m2':20,'net_area_m2':20,'openings':[]}]
        record['spaces'] = [a,b]
        first = self.module().build_commercial_profile(record,{},paired_area_policy='require_equal')['wall_inventory']
        record['spaces'].reverse()
        second = self.module().build_commercial_profile(record,{},paired_area_policy='require_equal')['wall_inventory']
        self.assertEqual(first,second)
        self.assertEqual(first[0]['status'],'ambiguous_pair_multipliers')
        self.assertIsNone(first[0]['area_m2'])
        self.assertEqual([f['weighted_area_m2'] for f in first[0]['faces']],[20,80])

    def test_accepted_default_averages_unequal_faces_and_flags_approximation(self):
        record = self.record()
        a = dict(record['spaces'][0], name='Corridor', multiplier=1)
        b = dict(record['spaces'][0], name='Room', multiplier=4)
        a['surfaces'] = [{'id':'a','adjacent_id':'b','type':'Wall','boundary':'Surface',
                          'gross_area_m2':20,'net_area_m2':20,'openings':[]}]
        b['surfaces'] = [{'id':'b','adjacent_id':'a','type':'Wall','boundary':'Surface',
                          'gross_area_m2':20,'net_area_m2':20,'openings':[]}]
        record['spaces'] = [a,b]
        first = self.module().build_commercial_profile(record,{})['wall_inventory']
        self.assertEqual(first[0]['area_m2'],50)
        self.assertEqual(first[0]['approximation'],'mean_of_unequal_zone_weighted_faces')
        self.assertEqual([f['weighted_area_m2'] for f in first[0]['faces']],[20,80])
        record['spaces'].reverse()
        self.assertEqual(first,self.module().build_commercial_profile(record,{})['wall_inventory'])

    def test_support_profile_checksum_is_verified_before_loading(self):
        m = self.module()
        self.assertTrue(hasattr(m,'load_profiles'))
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            for name in ('manifest.json','profiles.json','README.md'):
                (folder/name).write_bytes((m.OUTPUT/name).read_bytes())
            self.assertEqual(len(m.load_profiles(folder)['profiles']),170)
            with (folder/'profiles.json').open('ab') as f:
                f.write(b' ')
            with self.assertRaisesRegex(ValueError,'checksum'):
                m.load_profiles(folder)


if __name__ == '__main__':
    unittest.main()
