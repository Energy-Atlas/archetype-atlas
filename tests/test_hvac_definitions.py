import unittest
from scripts.definition_contract import BuildContext
from scripts.hvac_definitions import build_hvac, normalize_rule
from scripts.definition_compare import compare_elements


class HVACTests(unittest.TestCase):
    def test_capacity_band_is_not_a_selected_cop(self):
        row = {'id':'rule', 'template':'90.1-2019', 'equipment_table':'unitary_acs',
               'metrics':{'minimum_energy_efficiency_ratio':12}, 'source_attributes':{
               'minimum_capacity':0, 'maximum_capacity':65000, 'start_date':'2000-01-01',
               'end_date':'2999-09-09'}}
        result = normalize_rule(row, '2026-10-07')
        self.assertAlmostEqual(result['predicates']['maximum_capacity_W'],19049.6195612, places=5)
        self.assertEqual(result['rating_date'],'2026-10-07')
        self.assertNotIn('cop', result)
        self.assertEqual(result['status'],'conditional_unassigned')

    def test_source_descriptor_does_not_invent_fuel_or_performance(self):
        source={'id':'s','building_type':'MediumOffice','template':'90.1-2019',
                'source_family':'code_prototype_rules','system_type':'PSZ-AC',
                'source_attributes':{'heating_type':'Gas','fan_type':'ConstantVolume'}}
        result=build_hvac(BuildContext(atlas={'systems':[source]}))
        row=result['hvac_systems'][0]
        self.assertIsNone(row['parameters']['heating_fuel']['value'])
        self.assertIsNone(row['parameters']['efficiency_or_cop']['value'])
        self.assertTrue(result['components'])

    def test_different_fan_properties_prevent_identity(self):
        result=compare_elements('component',{'fan_pressure_Pa':500},{'fan_pressure_Pa':600})
        self.assertFalse(result['identity'])


if __name__=='__main__': unittest.main()
