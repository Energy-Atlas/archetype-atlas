"""Focused source recovery tests; no site build or program regeneration."""
import copy
import unittest

from scripts.energy_source_recovery import physical_assembly, operand, normalize_hpxml, readiness, ground_target, assembly_u
from scripts.recover_energy_inputs import residential_execution, material_execution, locked_sources, BASE
from scripts.definition_release import read_bundle
from scripts.recover_program_inputs import RUNTIME


class EnergyRecoveryTests(unittest.TestCase):
    @unittest.skipUnless(RUNTIME.exists(), 'Pinned runtime execution')
    def test_null_absorptance_follows_source_nil_to_f(self):
        sources, descriptors = locked_sources()
        result = material_execution(read_bundle(BASE), sources, descriptors)
        self.assertEqual(len(result),166)
        adiabatic = next(r for r in result.values() if 'roughness' in r['fields'])
        self.assertEqual(adiabatic['fields']['solar_absorptance']['value'],0)
        self.assertIsNone(adiabatic['fields']['solar_absorptance']['evidence']['original_value'])
        self.assertEqual(adiabatic['fields']['roughness']['origin'],'source_default')
        self.assertEqual(adiabatic['fields']['thermal_absorptance']['value'],.9)
        self.assertFalse(adiabatic['fields']['thermal_absorptance']['evidence']['source_setter_accepted'])

    @unittest.skipUnless(RUNTIME.exists(), 'Pinned OpenStudio runtime is only required for recovery execution')
    def test_residential_runtime_bridge_uses_actual_source_api(self):
        execution, files, runtime = residential_execution()
        self.assertEqual(len(execution['results']), 41)
        self.assertTrue(all(r['equipment'] for r in execution['results']))
        self.assertTrue(any(i['role']=='solar_thermal' for r in execution['results'] for i in r['equipment']))
        self.assertIn('resources/hpxml-measures/BuildResidentialHPXML/measure.rb', files)
        self.assertEqual(len(runtime['runtime_executable_sha256']),64)

    def test_selector_duplicates_preserve_identical_physics(self):
        rows = [{'name': 'Window', 'materials': ['Glass'], 'intended_surface_type': 'ExteriorWindow',
                 'standards_construction_type': 'Metal'},
                {'name': 'Window', 'materials': ['Glass'], 'intended_surface_type': 'ExteriorWindow',
                 'standards_construction_type': None}]
        result = physical_assembly(rows, 'Window')
        self.assertEqual(result['materials'], ['Glass'])
        self.assertEqual(len(result['source_candidates']), 2)
        self.assertEqual(rows[1]['standards_construction_type'], None)

    def test_different_layers_remain_ambiguous(self):
        rows = [{'name': 'Window', 'materials': ['Glass']}, {'name': 'Window', 'materials': ['Other']}]
        with self.assertRaisesRegex(ValueError, 'Ambiguous physical assembly'):
            physical_assembly(rows, 'Window')

    def test_ground_u_target_is_not_relabelled_c_factor(self):
        result = ground_target({'assembly_maximum_u_value':.1,'assembly_maximum_c_factor':None,
                                'assembly_maximum_f_factor':None})
        self.assertEqual(result['model'],'layered_U_ground_construction')
        self.assertEqual(result['field'],'u_W_m2_K')
        self.assertAlmostEqual(result['value'],.5678263337)

    def test_zero_source_target_is_not_zero_physical_transmittance(self):
        layers=[{'model':'StandardOpaqueMaterial','thickness_m':.01,'conductivity_W_m_K':.2}]
        self.assertAlmostEqual(assembly_u(layers,.1),1/.15)
        self.assertIsNone(assembly_u([{'model':'StandardOpaqueMaterial'}],.1))

    def test_si_conversion_retains_original_and_default_status(self):
        result = operand(140, 'degF', 'degC', lambda x: (x-32)*5/9, {'source_locator': 'file#method'}, True)
        self.assertEqual(result['value'], 60)
        self.assertEqual(result['evidence']['original_value'], 140)
        self.assertEqual(result['origin'], 'source_default')
        self.assertIsNone(operand(None, 'W', 'W', lambda x: x, {})['value'])

    def test_seasonal_rating_is_not_operating_cop(self):
        obj = {'cooling_efficiency_seer2': 12.4, 'cooling_capacity': None,
               'cooling_system_type': 'central air conditioner', 'cooling_system_fuel': 'electricity'}
        result = normalize_hpxml(obj, 'cooling', {'source_locator': 'measure.rb#set_cooling_systems'})
        self.assertEqual(result['fields']['cooling_efficiency_seer2']['unit'], 'W/W')
        self.assertAlmostEqual(result['fields']['cooling_efficiency_seer2']['value'], 12.4*.2930710701722222)
        self.assertNotIn('cop', result['fields'])
        self.assertIn('sizing.cooling_capacity', result['required_bindings'])

    def test_heater_units_and_loss_host(self):
        result = normalize_hpxml({'tank_volume': 50, 'temperature': 125, 'heating_capacity': 40000,
                                  'location': 'conditioned space', 'uniform_energy_factor': .64,
                                  'temperature_isdefaulted': True}, 'water_heater', {'source_locator': 'defaults.rb'})
        self.assertAlmostEqual(result['fields']['tank_volume']['value'], .1892705892)
        self.assertEqual(result['fields']['temperature']['origin'], 'source_default')
        self.assertIn('loss_host', result['required_bindings'])
        self.assertNotIn('hot_water_volume', result['fields'])

    def test_absent_heat_pump_backup_does_not_require_backup_sizing(self):
        obj={'heat_pump_type':'mini-split','backup_type':None,'backup_heating_capacity':None,
             'heating_capacity':None,'cooling_capacity':None}
        result=normalize_hpxml(obj,'heat_pump',{'source_locator':'measure.rb#set_heat_pumps'})
        self.assertNotIn('sizing.backup_heating_capacity',result['required_bindings'])

    def test_readiness_does_not_promote_missing_physics_to_consumer_binding(self):
        row = {'unresolved': ['performance_curves'], 'required_bindings': ['serving_assignment']}
        self.assertEqual(readiness(row), 'blocked')
        row['unresolved'] = []
        self.assertEqual(readiness(row), 'requires_bindings')
        row['required_bindings'] = []
        self.assertEqual(readiness(row), 'resolved')


if __name__ == '__main__':
    unittest.main()
