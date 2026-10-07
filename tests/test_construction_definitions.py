import unittest
from scripts.definition_contract import DefinitionError
from scripts.construction_definitions import normalize_material, unique_named, adjust_layers, film_resistance
from scripts.definition_contract import load_context
from scripts.program_definitions import build_programs
from scripts.construction_definitions import build_constructions


class ConstructionTests(unittest.TestCase):
    def test_near_zero_target_removes_named_insulation_as_source_does(self):
        layers=[{'name':'board','thickness_m':.1,'conductivity_W_m_K':1},
                {'name':'insulation','thickness_m':.05,'conductivity_W_m_K':.05}]
        result,status=adjust_layers(layers,.01,'insulation',.15)
        self.assertEqual(len(result),1)
        self.assertEqual(status,'source_zero_target_insulation_removed')
    def test_material_conversion_preserves_mass(self):
        result = normalize_material({'name': 'Board', 'material_type': 'StandardOpaqueMaterial',
                 'thickness': 1, 'conductivity': 1, 'density': 1, 'specific_heat': 1})
        self.assertAlmostEqual(result['thickness_m'], 0.0254)
        self.assertAlmostEqual(result['density_kg_m3'], 16.01846337396)
        self.assertAlmostEqual(result['specific_heat_J_kg_K'], 4186.8)

    def test_ambiguous_names_are_not_last_wins(self):
        with self.assertRaises(DefinitionError):
            unique_named([{'name': 'x', 'materials': ['a']}, {'name': 'x', 'materials': ['b']}], 'x')

    def test_target_adjustment_conserves_noninsulation(self):
        layers = [{'name': 'board', 'thickness_m': .1, 'conductivity_W_m_K': 1},
                  {'name': 'insulation', 'thickness_m': .05, 'conductivity_W_m_K': .05}]
        result, status = adjust_layers(layers, .5, 'insulation', .15)
        self.assertEqual(status, 'adjusted')
        self.assertEqual(result[0]['thickness_m'], .1)
        self.assertAlmostEqual(result[1]['thickness_m'], .0875)
        self.assertEqual(layers[1]['thickness_m'], .05)

    def test_generated_glazing_retains_source_defaults(self):
        row = normalize_material({'name': 'U 0.5 SHGC 0.4 Simple Glazing'})
        self.assertAlmostEqual(row['u_W_m2_K'], 2.8391316685, places=8)
        self.assertEqual(row['visible_transmittance'], .81)
        self.assertIn('visible_transmittance', row['source_code_defaults'])

    def test_wall_film_resistance_is_source_specific(self):
        self.assertAlmostEqual(film_resistance('ExteriorWall', True, True), .15, places=2)

    def test_pilot_can_reuse_material_across_multiple_assemblies(self):
        context = load_context()
        result = build_constructions(context, build_programs(context))
        self.assertGreater(len(result['materials']), 0)
        fallbacks = [r for r in result['constructions'] if r['derivation']=='assumed']
        self.assertTrue(all(r['layers'] for r in fallbacks))


if __name__ == '__main__': unittest.main()
