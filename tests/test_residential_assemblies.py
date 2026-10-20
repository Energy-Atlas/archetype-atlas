"""Source construction parity and the above-ground boundary."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/construction-inputs/residential-assemblies-v1.json'


class ResidentialAssemblyTests(unittest.TestCase):
    def test_recovery_implementation_exists(self):
        self.assertTrue(importlib.util.find_spec('scripts.recover_residential_assemblies'),
                        'Pinned residential assembly recovery is absent')

    def test_all_fixtures_and_source_physics(self):
        self.assertTrue(OUTPUT.exists(), 'All residential assemblies need recovery')
        from scripts.recover_residential_assemblies import validate
        packet = json.loads(OUTPUT.read_text())
        validate(packet)
        source = json.loads((ROOT / 'data/releases/v0.2.0/residential_archetypes.json').read_text())
        self.assertEqual(set(packet['records']), {r['id'] for r in source})
        self.assertEqual(len(packet['records']), 41)
        self.assertTrue(all(r['assemblies'] and not r['unresolved'] for r in packet['records'].values()))

    def test_validator_rejects_reversed_order_and_missing_mass(self):
        self.assertTrue(OUTPUT.exists(), 'Source layers are absent')
        from scripts.recover_residential_assemblies import validate
        packet = json.loads(OUTPUT.read_text())
        target = next(a for r in packet['records'].values() for a in r['assemblies']
                      if a['model'] == 'opaque_layers' and len(a['layers']) > 2)
        target['layers'].reverse()
        with self.assertRaisesRegex(ValueError, 'order'):
            validate(packet)
        target['layers'].reverse()
        target['layers'][0]['properties']['density_kg_m3'] = None
        with self.assertRaisesRegex(ValueError, 'density'):
            validate(packet)

    def test_pilot_parallel_mass_and_u_match_source(self):
        self.assertTrue(OUTPUT.exists(), 'Pilot recovery is absent')
        from scripts.recover_residential_assemblies import parallel_r, validate
        packet = json.loads(OUTPUT.read_text())
        pilot = next(iter(packet['records'].values()))
        for a in pilot['assemblies']:
            if a['model'] != 'opaque_layers':
                continue
            p = a['parameters']
            layers = a['layers']
            self.assertAlmostEqual(p['mass_per_area_kg_m2'], sum(l['properties']['thickness_m'] *
                l['properties']['density_kg_m3'] for l in layers), places=8)
            self.assertAlmostEqual(p['heat_capacity_per_area_J_m2_K'], sum(l['properties']['thickness_m'] *
                l['properties']['density_kg_m3'] * l['properties']['specific_heat_J_kg_K'] for l in layers), places=7)
            proof = a['evidence']['parallel_recipe']
            self.assertAlmostEqual(parallel_r(proof), proof['assembly_r_m2_K_W'], places=9)
        validate(packet)

    def test_ground_and_native_optional_vt_boundary(self):
        self.assertTrue(OUTPUT.exists(), 'Boundary recovery is absent')
        packet = json.loads(OUTPUT.read_text())
        roles = {a['role'] for r in packet['records'].values() for a in r['assemblies']}
        self.assertFalse(roles & {'FoundationWall', 'Slab', 'RimJoist', 'FloorOverFoundation'})
        glazing = [a for r in packet['records'].values() for a in r['assemblies'] if a['model'] == 'simple_glazing']
        self.assertTrue(glazing)
        for a in glazing:
            p = a['layers'][0]['properties']
            self.assertGreater(p['u_W_m2_K'], 0)
            self.assertTrue(0 < p['shgc'] < 1)
            if p['visible_transmittance'] is None:
                self.assertEqual(p['visible_transmittance_mode'], 'energyplus_autocalculate_from_shgc')
                self.assertIn('Energy+.idd', a['layers'][0]['evidence']['source_locator'])

    def test_active_curtains_survive_bare_glazing_recovery(self):
        packet = json.loads(OUTPUT.read_text())
        for r in packet['records'].values():
            for a in r['assemblies']:
                if a['role'] != 'Window':
                    continue
                self.assertIn('solar_modifiers', a, 'Source curtains must survive glazing recovery')
                shade = a['solar_modifiers']['incident_solar_multiplier']
                self.assertEqual(shade['model'], 'constant')
                self.assertTrue(0 < shade['value'] < 1)
                self.assertEqual(shade['value'], shade['evidence']['original_value']['summer'])
                self.assertEqual(shade['value'], shade['evidence']['original_value']['winter'])

    def test_density_cannot_be_guessed_from_r_value(self):
        from scripts.recover_residential_assemblies import validate
        packet = json.loads(OUTPUT.read_text())
        layer = next(a['layers'][0] for r in packet['records'].values()
                     for a in r['assemblies'] if a['model'] == 'opaque_layers')
        layer['properties']['density_kg_m3'] *= 1.1
        with self.assertRaisesRegex(ValueError, 'source.*density'):
            validate(packet)

    def test_source_parallel_thermal_mass_operands(self):
        packet = json.loads(OUTPUT.read_text())
        found = 0
        for r in packet['records'].values():
            for a in r['assemblies']:
                if a['model'] != 'opaque_layers':
                    continue
                source = a['evidence']['parallel_recipe']
                fractions = source['path_fractions']
                physical = [ms for ms in source['layers'] if ms[0]['name'] != 'AirFilm']
                self.assertEqual(len(physical), len(a['layers']))
                for native_paths, layer in zip(physical, a['layers']):
                    if len(native_paths) == 1:
                        continue
                    found += 1
                    rho = sum(m['density_lb_ft3']*f for m, f in zip(native_paths, fractions))
                    cp = sum(m['density_lb_ft3']*m['specific_heat_Btu_lb_F']*f
                             for m, f in zip(native_paths, fractions))/rho
                    self.assertAlmostEqual(layer['properties']['density_kg_m3'], rho*16.02, places=7)
                    self.assertAlmostEqual(layer['properties']['specific_heat_J_kg_K'], cp*4187, places=7)
        self.assertGreater(found, 100)

    def test_mislabeling_foundation_floor_cannot_cross_boundary(self):
        from scripts.recover_residential_assemblies import validate
        packet = json.loads(OUTPUT.read_text())
        floor = next(a for r in packet['records'].values() for a in r['assemblies'] if a['role'] == 'Floor')
        floor['source_adjacency'][0]['exterior'] = 'basement - unconditioned'
        with self.assertRaisesRegex(ValueError, 'Ground boundary'):
            validate(packet)

    def test_source_curtain_factor_cannot_be_overwritten(self):
        from scripts.recover_residential_assemblies import validate
        packet = json.loads(OUTPUT.read_text())
        window = next(a for r in packet['records'].values() for a in r['assemblies'] if a['role'] == 'Window')
        window['solar_modifiers']['incident_solar_multiplier']['value'] = 1.0
        with self.assertRaisesRegex(ValueError, 'source shading'):
            validate(packet)


if __name__ == '__main__':
    unittest.main()
