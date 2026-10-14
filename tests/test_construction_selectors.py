"""Source selector closure rejects ambiguous physics and silent climate substitution."""
import importlib.util
import unittest


class SelectorTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.recover_construction_selectors'),
                             'Missing source selector closure implementation')
        from scripts import recover_construction_selectors
        return recover_construction_selectors

    def test_exact_context_and_physical_ambiguity(self):
        m = self.module()
        row = {'template': 'T', 'climate_zone_set': 'ClimateZone 3A',
               'intended_surface_type': 'ExteriorDoor', 'standards_construction_type': 'Swinging',
               'building_category': 'Nonresidential', 'construction': 'door',
               'assembly_maximum_u_value': .5}
        matches = m.match_properties([row], 'T', 'ExteriorDoor', 'Swinging', 'Nonresidential')
        self.assertEqual(matches, [(0, row)])
        self.assertEqual(m.match_properties([row], 'T', 'ExteriorDoor', 'Swinging', 'Residential'), [])
        bad = dict(row, assembly_maximum_u_value=.3)
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            m.match_properties([row, bad], 'T', 'ExteriorDoor', 'Swinging', 'Nonresidential')

    def test_reproducibility_serialization_includes_final_lf(self):
        m = self.module()
        self.assertTrue(hasattr(m, 'artifact_bytes'), 'Missing byte-for-byte artifact reproducibility check')
        self.assertEqual(m.artifact_bytes({'a':1}), b'{\n  "a": 1\n}\n')

    def test_percentage_branches_remain_separate(self):
        m = self.module()
        row = {'template': 'T', 'climate_zone_set': 'ClimateZone 3',
               'intended_surface_type': 'Skylight', 'standards_construction_type': 'Glass with Curb',
               'building_category': 'Nonresidential', 'construction': 'glass',
               'minimum_percent_of_surface': 0, 'maximum_percent_of_surface': 2}
        other = dict(row, minimum_percent_of_surface=2.001, maximum_percent_of_surface=5)
        self.assertEqual(len(m.match_properties([row, other], 'T', 'Skylight',
                                               'Glass with Curb', 'Nonresidential')), 2)

    def test_climate_rule_rejects_unknown_and_preserves_legacy_groups(self):
        m = self.module()
        groups = [{'name': 'ClimateZone 3', 'climate_zones': ['ASHRAE 169-2013-3A']},
                  {'name': 'ClimateZone 3A', 'climate_zones': ['ASHRAE 169-2013-3A']},
                  {'name': 'ClimateZone 1', 'climate_zones': ['ASHRAE 169-2013-1A']},
                  {'name': 'ClimateZone 1A', 'climate_zones': ['ASHRAE 169-2013-1A']}]
        self.assertEqual(m.source_climate_group('DOE Ref Pre-1980', '1A', groups), 'ClimateZone 1')
        self.assertEqual(m.source_climate_group('DOE Ref Pre-1980', '3A', groups), 'ClimateZone 3A')
        self.assertEqual(m.source_climate_group('90.1-2019', '3A', groups), 'ClimateZone 3A')
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            m.source_climate_group('90.1-2019', '9Z', groups)

    def test_missing_physics_cannot_be_geometry_binding(self):
        m = self.module()
        with self.assertRaisesRegex(ValueError, 'conductivity'):
            m.validate_layer({'model': 'StandardGlazing', 'thickness_m': .003})
        m.validate_layer({'model': 'Gas', 'thickness_m': .01, 'gas_type': 'Air'})

    def test_simple_glazing_requires_positive_u_and_bounded_optics(self):
        m = self.module()
        with self.assertRaisesRegex(ValueError, 'Nonpositive'):
            m.validate_layer({'model':'SimpleGlazing', 'u_W_m2_K':0, 'shgc':.4, 'visible_transmittance':.6})
        with self.assertRaisesRegex(ValueError, 'optical'):
            m.validate_layer({'model':'SimpleGlazing', 'u_W_m2_K':2, 'shgc':1.1, 'visible_transmittance':.6})

    def test_duplicate_glazing_names_keep_candidates_without_merging_different_physics(self):
        m = self.module()
        a = {'name':'window', 'intended_surface_type':None, 'standards_construction_type':None,
             'insulation_layer':None, 'skylight_framing':None, 'materials':['U 0.5 SHGC 0.4 Simple Glazing']}
        b = dict(a, intended_surface_type='Skylight', materials=['U 0.5 SHGC 0.4 Simple Glazing Window'])
        recipe = m.construction_recipe([a,b], 'window', [])
        self.assertEqual([r['index'] for r in recipe['source_candidates']], [0,1])
        self.assertEqual(recipe['materials'], a['materials'])
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            m.construction_recipe([a,dict(b, materials=['U 0.7 SHGC 0.4 Simple Glazing'])], 'window', [])

    def test_source_default_uses_recorded_order_without_invented_percentage_rule(self):
        m = self.module()
        self.assertTrue(hasattr(m, 'resolve_source_selector'), 'Missing source-native ordered selector resolution')
        groups = [{'name':'ClimateZone 3', 'climate_zones':['ASHRAE 169-2013-3A']},
                  {'name':'ClimateZone 3A', 'climate_zones':['ASHRAE 169-2013-3A']},
                  {'name':'ClimateZone 4', 'climate_zones':['ASHRAE 169-2013-4A']}]
        selector = {'elements':['high','low'], 'selection_policy':{'default':'source_first_match',
            'source_order':[{'source_index':0, 'element_ids':['low'], 'predicate':{'climate_zone_set':'ClimateZone 3',
                'minimum_percent_of_surface':0, 'maximum_percent_of_surface':2}},
                {'source_index':1, 'element_ids':['high'], 'predicate':{'climate_zone_set':'ClimateZone 3',
                'minimum_percent_of_surface':2.001, 'maximum_percent_of_surface':5}}]}}
        packet = {'records':{'package':{'template':'90.1-2007','selectors':{'skylight':selector}}},
                  'elements':{}, 'climate_zone_sets':groups}
        self.assertEqual(m.resolve_source_selector(packet, 'package','skylight','3A')['element_ids'], ['low'])
        self.assertEqual(m.resolve_source_selector(packet, 'package','skylight','3A', 'high')['element_ids'], ['high'])
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            m.resolve_source_selector(packet, 'package','skylight','4A')


class FrozenClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import recover_construction_selectors as m
        cls.m = m
        cls.packet = m.load_json(m.OUTPUT)

    def test_complete_source_slots_and_baseline_ids(self):
        m, p = self.m, self.packet
        m.validate(p)
        self.assertEqual(len(p['records']), 183)
        self.assertEqual(len(p['baseline_element_ids']), 2982)
        inventory = p['inventory']['selector_occurrences']
        for slot in ('exterior_door', 'exterior_overhead_door', 'exterior_operable_window',
                     'interior_doors', 'interior_fixed_windows', 'interior_operable_windows',
                     'interior_partitions', 'tubular_daylight_domes', 'tubular_daylight_diffusers'):
            self.assertEqual(inventory[slot], 161, slot)
        self.assertEqual(inventory['exterior_glass_door'], 143)
        self.assertEqual(inventory['exterior_skylight'], 109)
        self.assertTrue(all(r['selectors']['site_shading']['disposition'] == 'source_absent_at_this_scope'
                            for r in p['records'].values()))

    def test_attic_constructor_overrides_are_complete(self):
        p = self.packet
        for record in p['records'].values():
            if record['space_type'] != 'Attic':
                continue
            floor = record['selectors']['exterior_floor']
            roof = record['selectors']['exterior_roof']
            self.assertEqual(floor['construction_name'], 'Typical Attic Soffit')
            self.assertEqual(roof['construction_name'], 'Typical Uninsulated Wood Joist Attic Roof')
            self.assertTrue(record['selectors']['interior_floors']['elements'])

    def test_zero_target_has_positive_attained_u_and_removed_insulation(self):
        p = self.packet
        zero = [r for r in p['elements'].values() if r['source_attributes'].get('assembly_maximum_u_value') == 0]
        self.assertTrue(zero)
        for row in zero:
            self.assertGreater(row['target_adjustment']['attained_u_W_m2_K'], 0)
            name = p['evidence'][row['evidence']['evidence_id']]['original_value']['insulation_layer']
            self.assertFalse(any(l['properties']['name'] == name for l in row['layers']))

    def test_detailed_glazing_has_physics_without_fabricated_scalar_summary(self):
        detailed = [r for r in self.packet['elements'].values() if r['model'] == 'detailed_glazing']
        self.assertTrue(detailed)
        for row in detailed:
            self.assertIsNone(row['parameters']['u_W_m2_K']['value'])
            self.assertFalse(row['unresolved'])
            self.assertTrue(all('conductivity_W_m_K' in l['properties'] for l in row['layers']
                                if l['properties']['model'] == 'StandardGlazing'))

    def test_every_native_material_default_has_source_and_runtime_evidence(self):
        for row in self.packet['elements'].values():
            for layer in row['layers']:
                evidence = self.packet['evidence'][layer['evidence']['evidence_id']]
                self.assertTrue(evidence['source_sha256'])
                self.assertTrue(evidence['runtime_executable_sha256'])
                self.assertEqual(set(layer['field_evidence']), set(layer['properties']))
                self.assertFalse(row['required_bindings'])


if __name__ == '__main__':
    unittest.main()
