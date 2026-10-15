import copy
import importlib.util
import unittest

from scripts.common import load_json, ROOT
from scripts.construction_distribution import load_current_release


class EquivalentExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = load_current_release()
        from scripts.construction_weighting import load_profiles
        cls.profiles = load_profiles()

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_equivalent_export'))
        from scripts import construction_equivalent_export
        return construction_equivalent_export

    def context(self, building):
        return next(c for c in self.release['contexts'].values()
                    if c['reference_id'] == '90.1-2019/'+building and c['climate_zone'] == '3B'
                    and self.release['construction_sets'][c['construction_set_id']]['source']['building_type'] == building)

    def test_medium_office_is_additive_one_recipe_per_semantic(self):
        c = self.context('MediumOffice')
        original = copy.deepcopy(self.release['component_configurations'][c['configuration_id']])
        d = self.module().export_equivalent(self.release, c['id'], self.profiles)
        self.assertEqual(d['kind'], 'building_level_equivalent')
        self.assertEqual(d['infiltration'], c['infiltration'])
        self.assertEqual(d['source'], self.release['construction_sets'][c['construction_set_id']]['source'])
        self.assertEqual(self.release['component_configurations'][c['configuration_id']], original)
        self.assertEqual(d['components']['ExteriorWall']['status'], 'ready')
        self.assertIsInstance(d['components']['ExteriorWall']['assembly_id'], str)
        for component in d['components'].values():
            self.assertNotIn('assignments', component)
            self.assertNotIn('when', component)
        self.assertGreater(d['components']['InternalMass']['quantity']['area_per_counted_floor_area'], 0)

    def test_warehouse_overrides_resolve_before_weighting(self):
        c = self.context('Warehouse')
        d = self.module().export_equivalent(self.release, c['id'], self.profiles)
        receipt = d['components']['ExteriorWall']['derivation']
        rows = receipt['contributors']
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(sum(r['weight'] for r in rows), 1.)
        # Office and Fine use the same assembly; source default is not a third contributor.
        self.assertEqual(d['components']['ExteriorWall']['status'], 'ready')
        self.assertEqual(receipt['weight_basis'], 'source_archetype_net_component_area')

    def test_residential_source_fixture_and_zero_quantity_stay_explicit(self):
        c = next(c for c in self.release['contexts'].values()
                 if self.release['construction_sets'][c['construction_set_id']]['scope'] == 'whole_dwelling')
        d = self.module().export_equivalent(self.release, c['id'], self.profiles)
        self.assertEqual(d['source']['source_fixture_id'], self.release['construction_sets'][c['construction_set_id']]['source']['source_fixture_id'])
        self.assertAlmostEqual(d['components']['InternalMass']['quantity']['area_per_counted_floor_area'], 1)
        self.assertEqual(d['components']['InternalMass']['status'], 'ready')

    def test_residential_overhangs_are_evidence_and_common_solar_modifier_is_active(self):
        c = next(c for c in self.release['contexts'].values()
                 if self.release['construction_sets'][c['construction_set_id']]['scope']=='whole_dwelling')
        original = copy.deepcopy(self.release['assemblies'])
        d = self.module().export_equivalent(self.release,c['id'],self.profiles)
        window = d['components']['ExteriorWindow']
        self.assertEqual(window['status'],'ready')
        recipe = d['assemblies'][window['assembly_id']]
        self.assertNotIn('overhang_geometry',recipe['solar_modifiers'])
        self.assertAlmostEqual(recipe['solar_modifiers']['incident_solar_multiplier']['value'],.8276)
        evidence = window['derivation']['geometry_evidence']
        self.assertEqual(len(evidence),2)
        self.assertEqual({v['overhang_geometry']['distance_to_top_of_window_m'] for v in evidence},{.3048})
        self.assertEqual(window['derivation']['geometry_policy'],'consumer_overhang_geometry_by_BEMGen')
        self.assertEqual(original,self.release['assemblies'])

    def test_missing_profile_blocks_instead_of_using_equal_shares(self):
        c = self.context('Warehouse')
        profiles = dict(self.profiles, profiles={})
        d = self.module().export_equivalent(self.release, c['id'], profiles)
        self.assertEqual(d['status'], 'blocked')
        self.assertEqual(d['components']['ExteriorWall']['status'], 'blocked')
        self.assertIsNone(d['components']['ExteriorWall']['assembly_id'])

    def test_known_zero_exposure_does_not_invent_weights_for_unused_alternatives(self):
        module = self.module()
        component = {'assignments': [{'assembly_id': 'a', 'when': {'scope': 'building_default'}},
                                     {'assembly_id': 'b', 'when': {'scope': 'space_type', 'space_type': 'Room'}}]}
        profile = {'spaces': [{'source_space_type': 'Room', 'story': 'One',
                              'exposure_m2': {'ExteriorFloor': 0}, 'operation_area_m2': {}}]}
        rows, area, basis = module.contributors_for(component, 'ExteriorFloor', profile)
        self.assertEqual(rows, [])
        self.assertEqual(area, 0)
        self.assertEqual(basis, 'source_reference_zero_exposure')

    def test_identical_glazing_does_not_hide_different_source_shading(self):
        module = self.module()
        release = {'materials': {'m': {'model': 'SimpleGlazing', 'properties': {'u_W_m2_K': 2, 'shgc': .4, 'visible_transmittance': .6}}},
                   'assemblies': {a: {'model': 'simple_glazing', 'layers': [{'material_id': 'm'}],
                                       'solar_modifiers': {'depth_m': d}} for a,d in (('a',1),('b',2))}}
        with self.assertRaisesRegex(ValueError, 'solar'):
            module._opening(release, [{'assembly_id': 'a', 'weight': .5}, {'assembly_id': 'b', 'weight': .5}])

    def test_standalone_output_satisfies_additional_schema(self):
        from jsonschema import Draft202012Validator
        path = ROOT/'schemas/construction-equivalent-v1.1.schema.json'
        self.assertTrue(path.exists(), 'Additive equivalent schema is missing')
        c = self.context('MediumOffice')
        schema = load_json(path)
        d = self.module().export_equivalent(self.release, c['id'], self.profiles)
        Draft202012Validator(schema).validate(d)
        invalid = copy.deepcopy(d)
        invalid['components']['ExteriorWall']['assembly_id'] = None
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(invalid)))

    def test_repeated_floor_inventory_normalizes_after_grouping(self):
        c = next(c for c in self.release['contexts'].values()
                 if c['reference_id']=='90.1-2013/HighriseApartment' and c['climate_zone']=='5B')
        d = self.module().export_equivalent(self.release, c['id'], self.profiles)
        rows = d['components']['FloorDistributedMass']['derivation']['contributors']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['weight'], 1.)

    def test_missing_negative_or_nonfinite_exposure_is_not_zero(self):
        module = self.module()
        component = {'assignments': [{'assembly_id':'a','when':{'scope':'building_default'}}]}
        for exposure in ({}, {'ExteriorWall':-1}, {'ExteriorWall':float('nan')}):
            profile = {'spaces':[{'source_space_type':'Room','story':'One','exposure_m2':exposure,'operation_area_m2':{}}]}
            with self.assertRaisesRegex(ValueError,'exposure'):
                module.contributors_for(component,'ExteriorWall',profile)

    def test_invalid_native_material_properties_block_before_conversion(self):
        module = self.module()
        for thickness,conductivity,density in ((-.1,-1,-1000),(.1,0,1000)):
            release = {'materials':{'m':{'model':'StandardOpaqueMaterial','properties':{
                'thickness_m':thickness,'conductivity_W_m_K':conductivity,'density_kg_m3':density,'specific_heat_J_kg_K':1000}}}}
            with self.assertRaises(ValueError):
                module.source_layers(release,{'layers':[{'material_id':'m'}]})

    def test_window_operations_are_separate_for_each_boundary_semantic(self):
        m = self.module()
        component = {'assignments':[{'assembly_id':'a','when':{'scope':'building_default','window_operation':'fixed'}},
                                    {'assembly_id':'b','when':{'scope':'building_default','window_operation':'operable'}}]}
        profile = {'spaces':[{'source_space_type':'Room','story':'One',
                   'exposure_m2':{'ExteriorWindow':10,'InteriorWindow':0},
                   'operation_area_m2':{'ExteriorWindow':{'FixedWindow':8,'OperableWindow':2},
                                        'InteriorWindow':{'FixedWindow':0,'OperableWindow':0}}}]}
        rows,area,_ = m.contributors_for(component,'InteriorWindow',profile)
        self.assertEqual((rows,area),([],0))
        profile['spaces'][0]['exposure_m2']['InteriorWindow'] = 5
        profile['spaces'][0]['operation_area_m2']['InteriorWindow']['FixedWindow'] = 5
        rows,area,_ = m.contributors_for(component,'InteriorWindow',profile)
        self.assertEqual(area,5)
        self.assertEqual(rows[0]['assembly_id'],'a')
        ext,ext_area,_ = m.contributors_for(component,'ExteriorWindow',profile)
        self.assertEqual(ext_area,10)
        self.assertEqual([r['weight'] for r in ext],[.8,.2])

    def test_ambiguous_mass_has_closed_resource_graph_and_explicit_pair_policy(self):
        from scripts.construction_equivalent_release import validate_document
        c = self.context('MediumOffice')
        profiles = copy.deepcopy(self.profiles)
        p = profiles['profiles'][c['reference_id']]
        p['wall_inventory'][0]['area_m2'] = None
        d = self.module().export_equivalent(self.release,c['id'],profiles)
        self.assertEqual(d['components']['InternalMass']['status'],'blocked')
        self.assertEqual(d['mass_accounting']['paired_surface_policy']['canonical_side'],'InteriorFloor')
        self.assertIn('reverse',d['mass_accounting']['paired_surface_policy']['adjacent_ceiling'])
        validate_document(d,self.release,profiles)

    def test_accepted_hospital_mass_budget_is_ready_with_visible_approximation(self):
        from scripts.construction_equivalent_release import validate_document
        c = self.context('Hospital')
        d = self.module().export_equivalent(self.release,c['id'],self.profiles)
        self.assertEqual(d['status'],'ready')
        self.assertEqual(d['components']['InternalMass']['status'],'ready')
        policy = d['mass_accounting']['reference_area_approximation']
        self.assertGreater(policy['unequal_multiplier_pair_counts']['wall_pairs'],0)
        self.assertEqual(policy['evidence_profile_id'],'90.1-2019/Hospital')
        validate_document(d,self.release,self.profiles)


if __name__ == '__main__':
    unittest.main()
