"""Focused draw-only DHW checks, without site/full program generation."""
import copy
import unittest

from scripts.common import ROOT, load_json
from scripts.definition_release import read_bundle
from scripts.program_water_heating import ProgramExporter, draw_heating_power, evaluate_recipe


class DrawPhysicsTests(unittest.TestCase):
    def test_main_booster_split_conserves_heat_and_fuel(self):
        stages = [{'fuel': 'natural gas', 'conversion_efficiency': .8, 'outlet_temperature_degC': 60},
                  {'fuel': 'electricity', 'conversion_efficiency': 1, 'outlet_temperature_degC': 82}]
        result = draw_heating_power(.001, 82, 10, stages, density_kg_m3=1000, specific_heat_J_kg_K=4180)
        self.assertAlmostEqual(result['delivered_heat_W'], 300960)
        self.assertAlmostEqual(result['fuel_input_W']['natural gas'], 261250)
        self.assertAlmostEqual(result['fuel_input_W']['electricity'], 91960)

    def test_mixed_cooler_draw_does_not_heat_to_tank_setpoint(self):
        stages = [{'fuel': 'electricity', 'conversion_efficiency': 1, 'outlet_temperature_degC': 60}]
        a = draw_heating_power(.001, 40, 10, stages, density_kg_m3=1000, specific_heat_J_kg_K=4180)
        b = draw_heating_power(.001, 40, 20, stages, density_kg_m3=1000, specific_heat_J_kg_K=4180)
        self.assertAlmostEqual(a['delivered_heat_W'], 125400)
        self.assertLess(b['delivered_heat_W'], a['delivered_heat_W'])
        self.assertEqual(draw_heating_power(.001, 40, 45, stages, density_kg_m3=1000,
                                          specific_heat_J_kg_K=4180)['delivered_heat_W'], 0)

    def test_unknown_performance_or_impossible_target_is_rejected(self):
        for efficiency in (None, 0, 1.1, float('nan')):
            with self.assertRaises(ValueError):
                draw_heating_power(.001, 60, 10, [{'fuel': 'electricity',
                    'conversion_efficiency': efficiency, 'outlet_temperature_degC': 60}],
                    density_kg_m3=1000, specific_heat_J_kg_K=4180)
        with self.assertRaises(ValueError):
            draw_heating_power(.001, 80, 10, [{'fuel': 'electricity',
                'conversion_efficiency': 1, 'outlet_temperature_degC': 60}],
                density_kg_m3=1000, specific_heat_J_kg_K=4180)

    def test_scaling_is_applied_once_and_fluid_inputs_are_required(self):
        recipe = {'draw': {'value': .00001, 'basis': 'floor_area'}, 'stages': [
            {'fuel': 'electricity', 'conversion_efficiency': 1, 'outlet_temperature_degC': 60}]}
        bindings = {'floor_area_m2': 200, 'water_density_kg_m3': 1000, 'water_specific_heat_J_kg_K': 4180}
        power = evaluate_recipe(recipe, .5, 40, 10, bindings)
        self.assertAlmostEqual(power['delivered_heat_W'], 125400)
        with self.assertRaises(KeyError):
            evaluate_recipe(recipe, .5, 40, 10, {'floor_area_m2': 200})

    def test_approved_cap_reports_unmet_heat_without_charging_it_to_fuel(self):
        recipe = {'draw': {'value': .00001, 'basis': 'floor_area'}, 'stages': [
            {'fuel': 'natural gas', 'conversion_efficiency': .8, 'outlet_temperature_degC': 60}],
            'delivery_policy': {'method': 'cap_at_source_outlet', 'report_unmet_target': True}}
        bindings = {'floor_area_m2': 200, 'water_density_kg_m3': 1000, 'water_specific_heat_J_kg_K': 4180}
        result = evaluate_recipe(recipe, .5, 82, 10, bindings)
        self.assertAlmostEqual(result['delivered_heat_W'], 209000)
        self.assertAlmostEqual(result['fuel_input_W']['natural gas'], 261250)
        self.assertEqual(result['requested_temperature_degC'], 82)
        self.assertEqual(result['delivered_temperature_degC'], 60)
        self.assertEqual(result['unmet_target_K'], 22)
        self.assertAlmostEqual(result['unmet_heat_W'], 91960)
        idle = evaluate_recipe(recipe, 0, 82, 10, bindings)
        self.assertEqual(idle['unmet_heat_W'], 0)
        warm = evaluate_recipe(recipe, .5, 82, 70, bindings)
        self.assertEqual(warm['delivered_heat_W'], 0)
        self.assertEqual(warm['delivered_temperature_degC'], 70)
        self.assertEqual(warm['unmet_target_K'], 12)


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = read_bundle(ROOT/'data/definition-releases/v0.1.1')
        cls.exporter = ProgramExporter(cls.bundle)

    def test_medium_office_has_source_conversion_and_no_active_water_duplicate(self):
        out = self.exporter.export('program-8c35a40eb0181596e0bfcac4')
        self.assertEqual(out['schema_version'], '4.0.0')
        self.assertEqual(len(out['water_heating']), 1)
        self.assertFalse(any(l['type']=='hot_water' for l in out['loads']))
        self.assertEqual(out['water_heating'][0]['stages'][0]['fuel'], 'natural gas')
        self.assertEqual(out['water_heating'][0]['stages'][0]['conversion_efficiency'], .82)
        self.assertEqual(self.exporter.validate(out), [])

    def test_v4_schema_is_valid_json_schema(self):
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(load_json(ROOT/'schemas/program-json-v4.schema.json'))

    def test_residential_and_solar_skip(self):
        out = self.exporter.export('program-0079ce7b163bdb1bd0154dbe')
        self.assertTrue(out['water_heating'])
        self.assertEqual(self.exporter.validate(out), [])
        with self.assertRaisesRegex(ValueError, 'solar.*out of scope'):
            self.exporter.export('program-1a9bafb870d938bc1ff6a0ee')

    def test_contract_rejects_duplicate_draw_and_scope_expansion(self):
        out = self.exporter.export('program-8c35a40eb0181596e0bfcac4')
        duplicate = copy.deepcopy(out)
        duplicate['loads'].append(copy.deepcopy(out['water_heating'][0]['draw']))
        self.assertTrue(self.exporter.validate(duplicate))
        out['water_heating'][0]['standby_loss_W'] = 1
        self.assertTrue(self.exporter.validate(out))

    def test_all_commercial_channels_are_numeric_and_source_traceable(self):
        records = self.exporter.conversions
        self.assertEqual(len(records), 154)
        self.assertEqual(sum(r['source_context']['channel']=='booster' for r in records.values()),23)
        for r in records.values():
            self.assertEqual(r['status'], 'known')
            self.assertTrue(0 < r['conversion_efficiency'] <= 1)
            self.assertIsInstance(r['conversion_efficiency'], (float, int))
            self.assertEqual(len(r['evidence']['source_file_sha256']),64)
            self.assertIsNotNone(r['source_execution']['requirement_index'])

    def test_shared_service_survives_migration_once(self):
        out = self.exporter.export('program-0c7698c80e7049e6280f5373')
        shared = [r for r in out['water_heating'] if r['ownership']=='instantiate_once']
        self.assertEqual(len(shared),1)
        self.assertEqual(shared[0]['service_id'],'service-a38508389268657fcf7c6256')
        self.assertIn('shared_service_host',out['required_bindings'])
        self.assertEqual(self.exporter.validate(out),[])
        out['water_heating'].append(copy.deepcopy(shared[0]))
        self.assertTrue(self.exporter.validate(out))

    def test_shared_service_cannot_duplicate_under_invented_demand_identity(self):
        out = self.exporter.export('program-0c7698c80e7049e6280f5373')
        duplicate = copy.deepcopy(out['water_heating'][0])
        duplicate['demand_id'] = duplicate['draw']['demand_id'] = 'invented-water-demand'
        out['water_heating'].append(duplicate)
        self.assertTrue(self.exporter.validate(out))

    def test_local_demand_cannot_be_reassigned_to_unrelated_shared_service(self):
        out = self.exporter.export('program-8c35a40eb0181596e0bfcac4')
        recipe = out['water_heating'][0]
        recipe['ownership'] = 'instantiate_once'
        recipe['service_id'] = 'service-a38508389268657fcf7c6256'
        recipe['stages'] = self.exporter.recipe({'id':'unused'}, recipe['draw'], recipe['service_id'])['stages']
        self.assertTrue(self.exporter.validate(out))

    def test_active_source_water_demand_cannot_be_silently_omitted(self):
        out = self.exporter.export('program-8c35a40eb0181596e0bfcac4')
        out['water_heating'] = []
        self.assertTrue(self.exporter.validate(out))

    def test_source_booster_channel_is_coupled_to_main(self):
        service = self.exporter.base.services['service-1b99baf832d76dd44370166e']
        recipe = self.exporter.recipe({'id':'unused'}, service['load'], service['id'])
        self.assertEqual(len(recipe['stages']),2)
        self.assertEqual([s['fuel'] for s in recipe['stages']],['natural gas','electricity'])
        self.assertEqual(recipe['stages'][0]['outlet_temperature_degC'],60)
        self.assertAlmostEqual(recipe['stages'][1]['outlet_temperature_degC'],82.2222222222)

    def test_valid_heater_from_wrong_template_is_rejected(self):
        out = self.exporter.export('program-8c35a40eb0181596e0bfcac4')
        other = self.exporter.commercial[('MediumOffice','90.1-2007','main')]
        out['water_heating'][0]['stages'] = [self.exporter.stage(other)]
        self.assertTrue(self.exporter.validate(out))

    def test_mixture_keeps_v3_draw_magnitudes_and_schedules(self):
        pid = 'program-2497c6a2f0f3d35066d45e8c'
        original = self.exporter.base.export(pid, 'defaulted')
        out = self.exporter.export(pid)
        water = [l for l in original['loads'] if l['type']=='hot_water']
        migrated = [r['draw'] for r in out['water_heating'] if r['service_id'] is None]
        self.assertTrue(water)
        self.assertEqual(migrated, water)
        self.assertEqual(out['schedules'], original['schedules'])

    def test_small_hotel_caps_only_delivery_and_preserves_requested_schedule(self):
        for pid in ('program-48033f4bc7ec6fc7b024e233', 'program-ddd1850c0fa5cbf5282f50c0',
                    'program-4693cf50f9561a3d33c1823a'):
            with self.subTest(program=pid):
                original = self.exporter.base.export(pid, 'defaulted')
                out = self.exporter.export(pid)
                self.assertEqual(out['schedules'], original['schedules'])
                recipe = out['water_heating'][0]
                self.assertEqual(recipe['draw'], next(l for l in original['loads'] if l['type']=='hot_water'))
                target = out['schedules'][recipe['draw']['target_temperature_schedule_id']]
                self.assertAlmostEqual(target['rules'][0]['values'][0], 82.2222222222)
                self.assertEqual(recipe['stages'][0]['outlet_temperature_degC'], 60)
                self.assertEqual(recipe['delivery_policy']['method'], 'cap_at_source_outlet')
                self.assertTrue(recipe['delivery_policy']['report_unmet_target'])
                self.assertEqual(self.exporter.validate(out), [])
                del recipe['delivery_policy']
                self.assertTrue(self.exporter.validate(out))

    def test_cap_propagates_to_all_affected_mixtures_without_altering_demands(self):
        affected = ('program-131bcfba407138256934455a', 'program-25c0b29ba11b1aa1f5681fc4',
                    'program-41d7c15eaedaab29da77780b', 'program-54aa9da996ad549d27b0cedf',
                    'program-54cc947ee16edbf6cc2b3189', 'program-56262a9ad7552e5284079e8a',
                    'program-5ad7a80a15053e984f994307', 'program-5ed5d77d02f128cf1040c54c',
                    'program-92bc7cb9951207d81f1b39be', 'program-9511dbb57cd4ad40c05401a4',
                    'program-a8a311d4d13e95676f12d3bc', 'program-d055cdde78efc12f8cbb1e38')
        for pid in affected:
            with self.subTest(program=pid):
                original = self.exporter.base.export(pid, 'defaulted')
                out = self.exporter.export(pid)
                self.assertEqual(out['schedules'], original['schedules'])
                self.assertEqual([r['draw'] for r in out['water_heating'] if r['service_id'] is None],
                                 [l for l in original['loads'] if l['type']=='hot_water'])
                capped = [r for r in out['water_heating'] if r.get('delivery_policy')]
                self.assertEqual(len(capped), 1)
                target = out['schedules'][capped[0]['draw']['target_temperature_schedule_id']]
                self.assertAlmostEqual(target['rules'][0]['values'][0], 82.2222222222)
                self.assertEqual(capped[0]['stages'][0]['outlet_temperature_degC'], 60)
                self.assertEqual(self.exporter.validate(out), [])

    def test_delivery_cap_cannot_be_assigned_to_an_unapproved_demand(self):
        capped = self.exporter.export('program-4693cf50f9561a3d33c1823a')['water_heating'][0]
        out = self.exporter.export('program-8c35a40eb0181596e0bfcac4')
        self.assertNotIn('delivery_policy', out['water_heating'][0])
        out['water_heating'][0]['delivery_policy'] = copy.deepcopy(capped['delivery_policy'])
        self.assertTrue(self.exporter.validate(out))

    def test_census_resolves_approved_temperature_conflicts(self):
        from scripts.validate_program_water_heating import census
        report = census(self.exporter)
        self.assertEqual(report['unexpected_unresolved'], [])
        self.assertEqual(report['known_blocked_temperature_cases'], [])
        self.assertEqual(report['commercial_service_recipes_checked'],217)
        self.assertEqual(len(report['capped_temperature_cases']),6)
        self.assertEqual(len(report['validated_capped_programs']),15)


if __name__ == '__main__':
    unittest.main()
