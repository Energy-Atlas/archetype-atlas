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

