import unittest

from scripts.energy_json_review import material_requirements, collect, render
from scripts.definition_contract import DefinitionBundle


class EnergyReviewTests(unittest.TestCase):
    def test_massless_does_not_require_mass_or_glazing_properties(self):
        required = material_requirements({'model':'MasslessOpaqueMaterial'})
        self.assertIn('resistance_m2_K_W', required)
        self.assertNotIn('density_kg_m3', required)
        self.assertNotIn('solar_transmittance_at_normal_incidence', required)

    def test_unreported_required_material_operand_is_a_gap(self):
        bundle = DefinitionBundle(materials=[{'id':'m1','model':'StandardOpaqueMaterial','thickness_m':.1,
            'conductivity_W_m_K':.5,'density_kg_m3':None,'specific_heat_J_kg_K':900}])
        fields = collect(bundle, {'records':{}}, {'records':{},'water_heaters':{}})['construction']['fields']
        density = next(f for f in fields if f['field']=='materials.density_kg_m3')
        self.assertEqual(density['unresolved'],1)
        self.assertEqual(density['affected_ids'],['m1'])

    def test_binding_is_not_missing_source_physics(self):
        bundle = DefinitionBundle()
        recovery = {'records':{'c1':{'id':'c1','source_context':{'role':'GroundContactFloor'},
                    'required_bindings':['surface_area'],'unresolved':[],'recovered':{},'readiness':'requires_bindings'}}}
        result = collect(bundle, recovery, {'records':{},'water_heaters':{}})
        field = next(f for f in result['construction']['fields'] if f['field']=='required_bindings.surface_area')
        self.assertEqual(field['consumer_binding'],1)
        self.assertEqual(field['unresolved'],0)

    def test_user_annotations_survive_regeneration(self):
        review={'records':1,'fields':[{'field':'layers','eligible':1,'known':0,'unresolved':1,
            'consumer_binding':0,'affected_ids':['c1'],'patterns':{'Residential':1},'examples':['c1'],
            'proposal':'Recover source layers.'}]}
        old='<!-- annotation:layers:begin -->\nKeep this comment.\n<!-- annotation:layers:end -->'
        text=render('Construction',review,old)
        self.assertIn('Keep this comment.',text)
        self.assertIn('User comments / decision',text)


if __name__ == '__main__':
    unittest.main()
