"""Regression requirements for source-executed dwelling program recovery."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ResidentialRecoveryTests(unittest.TestCase):
    def test_selected_miscellaneous_end_uses_are_included(self):
        data = json.loads((ROOT / 'data/program-inputs/residential-v1.json').read_text())
        for row in data['records'].values():
            options = row['metadata']['original_selected_options']
            present = {x['end_use'] for x in row['loads']}
            for option, end_use in [('Misc Well Pump', 'plug_loads_well_pump'), ('Misc Gas Grill', 'fuel_loads_grill'), ('Misc Gas Fireplace', 'fuel_loads_fireplace'), ('Misc Gas Lighting', 'fuel_loads_lighting'), ('Misc Pool', 'pool_pump'), ('Misc Hot Tub Spa', 'permanent_spa_pump')]:
                if options[option] != 'None' and not (option == 'Misc Hot Tub Spa' and row['metadata']['expanded_source_arguments']['misc_permanent_spa'] == 'None'):
                    self.assertIn(end_use, present, (option, options[option]))
            self.assertEqual(row['metadata']['excluded_channels'], ['electric_vehicle'])

    def test_magnitudes_conserve_annual_energy_and_water(self):
        from scripts.definition_contract import stable_id
        data = json.loads((ROOT / 'data/program-inputs/residential-v1.json').read_text())
        root = ROOT / 'data/resolution-releases/v0.4.0'
        descriptors = {x['record_id']: x for x in json.loads((root / 'profile-index.json').read_text())}
        for rid, row in data['records'].items():
            profile = json.loads((root / 'profiles' / (rid + '.json')).read_text())
            schedules = {stable_id('residential-schedule', {'source': rid, 'channel': k, 'profile_sha256': descriptors[rid]['profile_sha256']}): v for k, v in profile['series'].items()}
            schedules.update({k: v['values'] for k, v in data['schedules'].items()})
            for load in row['loads']:
                if load['value'] == 0:
                    continue
                shape = schedules[load['schedule_id']]
                self.assertEqual(len(shape), 8760)
                self.assertGreaterEqual(min(shape), 0)
                self.assertLessEqual(max(shape), 1.000000001)
                original = load['evidence']['original_value']
                actual = load['value'] * sum(shape)
                expected = original['annual_kwh'] * 1000 if load['unit'] == 'W' else original['daily_gallons'] * 365 * 0.003785411784 / 3600
                self.assertAlmostEqual(actual / expected, 1, places=12)
                fractions = load.get('heat_fractions', {})
                self.assertTrue(all(0 <= v <= 1 for v in fractions.values()))
                self.assertLessEqual(sum(fractions.values()), 1.000000000001)

    def test_stock_refrigeration_usage_calibration_is_preserved(self):
        data = json.loads((ROOT / 'data/program-inputs/residential-v1.json').read_text())
        for row in data['records'].values():
            args = row['metadata']['expanded_source_arguments']
            for load in row['loads']:
                if load['end_use'] not in ['refrigerator', 'extra_refrigerator', 'freezer']:
                    continue
                key = load['end_use']
                expected = args['appliance_' + key + '_rated_annual_consumption'] * (args['appliance_' + key + '_usage_multiplier'] or 1) * float(args[key + '_usage_multiplier'])
                self.assertAlmostEqual(load['evidence']['original_value']['annual_kwh'], expected)

    def test_recovered_inventory_and_physical_operands(self):
        path = ROOT / 'data/program-inputs/residential-v1.json'
        self.assertTrue(path.exists(), 'Source-executed residential input recovery is missing')
        data = json.loads(path.read_text())
        source = json.loads((ROOT / 'data/releases/v0.2.0/residential_archetypes.json').read_text())
        self.assertEqual(set(data['records']), {r['id'] for r in source})
        for row in source:
            recovered = data['records'][row['id']]
            self.assertEqual(recovered['unresolved'], [])
            for load in recovered['loads']:
                self.assertGreaterEqual(load['value'], 0)
                self.assertIn(load['unit'], ['W', 'm3/s'])
                self.assertEqual(load['basis'], 'dwelling_unit')
                self.assertIn('source_locator', load['evidence'])
                if load['value']:
                    self.assertTrue(load.get('schedule_id') or load.get('schedule'))
            if row['occupants'] == 0:
                fridge = [x for x in recovered['loads'] if x['end_use'] == 'refrigerator']
                self.assertTrue(fridge)
                self.assertGreater(fridge[0]['value'], 0)
            for end_use in ['cooking_range', 'clothes_dryer']:
                fuels = [x for x in recovered['loads'] if x['end_use'] == end_use and x.get('fuel') in ['natural gas', 'propane'] and x['value'] > 0]
                if fuels:
                    self.assertTrue(any(x['end_use'] == end_use and x.get('fuel') == 'electricity' and x['value'] > 0 for x in recovered['loads']))


if __name__ == '__main__':
    unittest.main()
