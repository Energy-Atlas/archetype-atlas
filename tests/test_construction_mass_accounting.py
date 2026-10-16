"""Standalone mass quantities must not depend on the chosen representation."""
import copy
import importlib.util
import unittest

from scripts.construction_distribution import load_current_release
from scripts.construction_set_release import hydrate_context
from scripts.construction_weighting import load_profiles


class SharedMassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_current_release()
        cls.profiles = load_profiles()

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_mass_accounting'),
                             'Shared source mass contract is missing')
        from scripts import construction_mass_accounting
        return construction_mass_accounting

    def context(self, reference):
        candidates = [c for c in self.source['contexts'].values() if c['reference_id'] == reference]
        return next((c for c in candidates if c['climate_zone']=='3B' and
                     self.source['construction_sets'][c['construction_set_id']]['source']['building_type'] == reference.split('/')[-1]), candidates[0])

    def test_office_additional_mass_has_original_physics_and_plenum_quantities(self):
        c = self.context('90.1-2019/MediumOffice')
        mass = self.module().build_mass_contract(self.source, c['id'], self.profiles)
        additional = mass['additional_mass']
        self.assertEqual(additional['status'], 'provided')
        self.assertAlmostEqual(sum(e['area_per_counted_floor_area'] for e in additional['entries']), 4, places=7)
        self.assertTrue(any(not e['scope']['counted_floor_area'] for e in additional['entries']))
        self.assertTrue(all(e['source_operands']['area_per_floor_area'] == 2 for e in additional['entries']))
        recipes = mass['recipes']
        self.assertEqual(len(recipes), 1)
        recipe = next(iter(recipes.values()))
        self.assertAlmostEqual(recipe['capacity_J_m2_K'], 98010)
        self.assertEqual(recipe['layers'][0]['properties']['thickness_m'], .15)
        self.assertEqual(recipe['layers'][0]['properties']['density_kg_m3'], 540)

    def test_office_budgets_preserve_source_physical_capacity(self):
        c = self.context('90.1-2019/MediumOffice')
        mass = self.module().build_mass_contract(self.source, c['id'], self.profiles)
        b = mass['physical_capacity_budgets']
        self.assertAlmostEqual(sum(x['capacity_per_counted_floor_area_J_m2_K'] for x in b['InteriorWall']), 5698.484913357512)
        self.assertAlmostEqual(sum(x['capacity_per_counted_floor_area_J_m2_K'] for x in b['InteriorFloor']), 133854.8988754543)
        self.assertEqual(mass['reference']['profile_id'], '90.1-2019/MediumOffice')
        self.assertGreater(mass['reference']['counted_floor_area_m2'], 0)
        self.module().validate_mass_contract(mass)

    def test_mass_source_locators_resolve_to_frozen_profile_fields(self):
        c = self.context('90.1-2019/MediumOffice')
        mass = self.module().build_mass_contract(self.source, c['id'], self.profiles)
        for rows in mass['physical_capacity_budgets'].values():
            for row in rows:
                value = self.profiles
                for part in row['source_locator'].split('#',1)[1].strip('/').split('/'):
                    key = part.replace('~1','/').replace('~0','~')
                    self.assertIn(key, value)
                    value = value[key]

    def test_both_documents_carry_identical_self_contained_mass_data(self):
        from scripts.construction_equivalent_release import export_frozen, OUTPUT
        c = self.context('90.1-2019/MediumOffice')
        module = self.module()
        d0 = hydrate_context(self.source, c['id'])
        u0 = export_frozen(OUTPUT, c['id'])
        before_d, before_u = copy.deepcopy(d0), copy.deepcopy(u0)
        mass = module.build_mass_contract(self.source, c['id'], self.profiles)
        d = module.upgrade_detailed(d0, mass)
        u = module.upgrade_unified(u0, mass)
        self.assertEqual(d['mass_accounting'], u['mass_accounting'])
        self.assertEqual(d['schema_version'], '2.1.0')
        self.assertEqual(u['schema_version'], '1.2.0')
        self.assertEqual(d0, before_d)
        self.assertEqual(u0, before_u)
        self.assertEqual(d['materials'], d0['materials'])
        self.assertEqual(u['assemblies'], u0['assemblies'])
        module.validate_export(d)
        module.validate_export(u)

    def test_sparse_residential_retains_absence_and_partition_scaling(self):
        c = self.context('residential_archetype-b782a597642c3b89c217')
        mass = self.module().build_mass_contract(self.source, c['id'], self.profiles)
        self.assertEqual(mass['physical_capacity_budgets'], {'InteriorWall': [], 'InteriorFloor': []})
        self.assertAlmostEqual(sum(e['area_per_counted_floor_area'] for e in mass['additional_mass']['entries']), 1)
        self.assertEqual(mass['additional_mass']['entries'][0]['area_convention'], 'source exposed partition area, both sides')

    def test_known_zero_additional_mass_has_no_invented_recipe(self):
        c = self.context('90.1-2019/SmallHotel')
        mass = self.module().build_mass_contract(self.source, c['id'], self.profiles)
        self.assertEqual(mass['additional_mass']['status'], 'known_zero')
        self.assertEqual(mass['additional_mass']['entries'], [])
        self.assertEqual(mass['recipes'], {})

    def test_missing_profile_does_not_become_zero_mass(self):
        c = self.context('90.1-2019/MediumOffice')
        with self.assertRaisesRegex(ValueError, 'profile'):
            self.module().build_mass_contract(self.source, c['id'], {'profiles': {}, 'mass_recipes': {}})

    def test_unknown_quantity_does_not_become_zero_mass(self):
        c = self.context('90.1-2019/MediumOffice')
        packet = copy.deepcopy(self.profiles)
        packet['profiles'][c['reference_id']]['spaces'][0]['added_mass'][0]['area_m2'] = None
        with self.assertRaisesRegex(ValueError, 'quantity|operand'):
            self.module().build_mass_contract(self.source, c['id'], packet)

    def test_quantity_must_agree_with_original_scaling_and_multiplier(self):
        c = self.context('90.1-2019/MediumOffice')
        packet = copy.deepcopy(self.profiles)
        packet['profiles'][c['reference_id']]['spaces'][0]['added_mass'][0]['area_m2'] *= 2
        with self.assertRaisesRegex(ValueError, 'scaling|multiplier'):
            self.module().build_mass_contract(self.source, c['id'], packet)

    def test_invalid_native_material_is_rejected(self):
        c = self.context('90.1-2019/MediumOffice')
        module = self.module()
        mass = module.build_mass_contract(self.source, c['id'], self.profiles)
        next(iter(mass['recipes'].values()))['layers'][0]['properties']['solar_absorptance'] = 2
        with self.assertRaises(ValueError):
            module.validate_mass_contract(mass)

    def test_recipe_source_locators_resolve_to_original_material_layers(self):
        from scripts.common import load_json, ROOT
        for reference in ['90.1-2019/MediumOffice','residential_archetype-b782a597642c3b89c217']:
            c = self.context(reference)
            mass = self.module().build_mass_contract(self.source, c['id'], self.profiles)
            for recipe in mass['recipes'].values():
                path, fragment = recipe['source_locator'].split('#', 1)
                value = load_json(ROOT/path)
                for part in fragment.strip('/').split('/'):
                    key = part.replace('~1','/').replace('~0','~')
                    value = value[int(key)] if isinstance(value,list) else value[key]
                self.assertIsInstance(value, list)
                self.assertTrue(all('thickness_m' in x or 'properties' in x for x in value))

    def test_standalone_scaling_operands_cannot_contradict_reported_quantities(self):
        module = self.module()
        for reference,key in [('90.1-2019/MediumOffice','source_multiplier'),
                              ('residential_archetype-b782a597642c3b89c217','source_area_per_conditioned_floor_area')]:
            c = self.context(reference)
            mass = module.build_mass_contract(self.source, c['id'], self.profiles)
            mass['additional_mass']['entries'][0]['source_operands'][key] = 999
            with self.assertRaisesRegex(ValueError, 'scaling|multiplier'):
                module.validate_mass_contract(mass)

    def test_standalone_capacity_reconciliation_is_enforced_in_both_modes(self):
        from scripts.construction_equivalent_release import export_frozen, OUTPUT
        module = self.module()
        c = self.context('90.1-2019/MediumOffice')
        mass = module.build_mass_contract(self.source, c['id'], self.profiles)
        d = module.upgrade_detailed(hydrate_context(self.source, c['id']),mass)
        u = module.upgrade_unified(export_frozen(OUTPUT,c['id']),mass)
        for cache in [None, module.BatchMassValidationCache()]:
            invalid = copy.deepcopy(d)
            row = invalid['mass_accounting']['physical_capacity_budgets']['InteriorWall'][0]
            row['source_areal_capacity_J_m2_K'] *= 2
            row['capacity_per_counted_floor_area_J_m2_K'] *= 2
            with self.assertRaisesRegex(ValueError, 'capacity'):
                module.validate_export(invalid, cache=cache)
            invalid = copy.deepcopy(u)
            invalid['components']['InternalMass']['quantity']['area_per_counted_floor_area'] *= 2
            with self.assertRaisesRegex(ValueError, 'quantity|capacity'):
                module.validate_export(invalid, cache=cache)
            for role in ['InternalMass','FloorDistributedMass']:
                invalid = copy.deepcopy(u)
                recipe = invalid['assemblies'][invalid['components'][role]['assembly_id']]
                for layer in recipe['layers']:
                    layer['C'] *= 2
                    if layer['model']=='Material':layer['density_kg_m3'] *= 2
                recipe['targets']['capacity_J_m2_K'] *= 2
                with self.assertRaisesRegex(ValueError, 'capacity'):
                    module.validate_export(invalid, cache=cache)

    def test_forged_capacity_and_missing_recipe_are_rejected(self):
        c = self.context('90.1-2019/MediumOffice')
        module = self.module()
        mass = module.build_mass_contract(self.source, c['id'], self.profiles)
        mass['additional_mass']['entries'][0]['capacity_per_counted_floor_area_J_m2_K'] += 1
        with self.assertRaisesRegex(ValueError, 'capacity'):
            module.validate_mass_contract(mass)
        mass = module.build_mass_contract(self.source, c['id'], self.profiles)
        mass['recipes'] = {}
        with self.assertRaisesRegex(ValueError, 'recipe'):
            module.validate_mass_contract(mass)

    def test_negative_residual_reports_excess_without_subtracting_mass(self):
        module = self.module()
        result = module.capacity_residual(100, 120)
        self.assertEqual(result, {'signed_residual_J_K': -20, 'restoration_capacity_J_K': 0,
                                  'excess_capacity_J_K': 20})
        with self.assertRaises(ValueError):
            module.capacity_residual(100, float('nan'))

    def test_batch_validation_rechecks_changed_mass_and_material_content(self):
        module = self.module()
        self.assertTrue(hasattr(module, 'BatchMassValidationCache'))
        c = self.context('90.1-2019/MediumOffice')
        d = module.upgrade_detailed(hydrate_context(self.source, c['id']),
            module.build_mass_contract(self.source, c['id'], self.profiles))
        cache = module.BatchMassValidationCache()
        module.validate_export(d, cache=cache)
        invalid = copy.deepcopy(d)
        next(iter(invalid['mass_accounting']['recipes'].values()))['capacity_J_m2_K'] += 1
        with self.assertRaisesRegex(ValueError, 'capacity'):
            module.validate_export(invalid, cache=cache)
        invalid = copy.deepcopy(d)
        next(iter(invalid['materials'].values()))['properties']['conductivity_W_m_K'] = -1
        with self.assertRaises(Exception):
            module.validate_export(invalid, cache=cache)


if __name__ == '__main__':
    unittest.main()
