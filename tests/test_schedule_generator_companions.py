"""Nominal controls and selected fixed backgrounds stay outside energy fitting."""
import importlib.util

from tests.test_schedule_generator_programs import RecipeResourceCase, OCCUPIED, VACANT


class CompanionTests(RecipeResourceCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('atlas_schedules.companions'),
                             'companion implementation is missing')
        super().setUp()
        from atlas_schedules.companions import generate_companions
        self.companions = generate_companions

    def test_companion_controls_and_backgrounds(self):
        result = self.resolve(OCCUPIED, self.inputs(OCCUPIED), self.resources)
        generated = self.companions(result, self.resources)
        self.assertEqual(generated['channels']['activity'], [117.22842806888889]*8760)
        self.assertEqual(generated['channels']['hot_water_fixtures_target_temperature'], [40.55555555555556]*8760)
        self.assertTrue(all(h <= c for h, c in zip(generated['channels']['heating_setpoint'], generated['channels']['cooling_setpoint'])))
        self.assertEqual(set(generated['source_context']['companion_receipts']), set(generated['channels']))
        self.assertTrue(all(len(v) == 8760 for v in generated['channels'].values()))

    def test_zero_resident_preserves_installed_refrigeration(self):
        result = self.resolve(VACANT, self.inputs(VACANT), self.resources)
        demand = next(d for d in result['demands'] if d['quantity'] == 'refrigerator')
        self.assertAlmostEqual(demand['annual_target']['total'], 455700)
        generated = self.companions(result, self.resources)
        values = generated['channels']['refrigerator']
        self.assertGreater(sum(values), 0)
        fixed = self.resources.get('residential', 'fixed-background-schedules')['definition']['schedules']['refrigerator']
        self.assertAlmostEqual(values[0], fixed['weekday_fractions'][0]*fixed['monthly_multipliers'][0]/fixed['peak_divisor'])
        self.assertNotIn('activity', generated['channels'])
        self.assertTrue(all(len(v) == 8760 for v in generated['channels'].values()))

    def test_translated_thermostats_match_all_frozen_references(self):
        for case in self.resources.get('reference', 'm1-scope')['cases']:
            if not case['configuration_id'].startswith('residential_'):
                continue
            resolved = self.resolve(case['program_id'], self.inputs(case['program_id']), self.resources)
            generated = self.companions(resolved, self.resources)
            profile = self.resources.get('reference', case['configuration_id']+'-profile')
            for slot in ('heating_setpoint', 'cooling_setpoint'):
                self.assertLess(max(abs(a-b) for a,b in zip(generated['channels'][slot], profile['series'][slot])), 1e-8)
            if case['program_id'] == 'program-68719c3fb04c28ca96c72c5c':
                self.assertGreater(len(generated['source_context']['companion_receipts']['heating_setpoint']['corrected_hours']), 0)

    def test_kernel_and_companions_close_every_declared_demand(self):
        from atlas_schedules.residential import generate_residential
        from atlas_schedules.budgets import bind_budget
        resolved = self.resolve(OCCUPIED, self.inputs(OCCUPIED), self.resources)
        generated = generate_residential(resolved['inputs'], 42, self.resources)
        generated['channels'].update(self.companions(resolved, self.resources)['channels'])
        for slot in resolved['slots']:
            self.assertIn(slot['slot'], generated['channels'])
            self.assertEqual(len(generated['channels'][slot['slot']]), 8760)
        for demand in resolved['demands']:
            target = resolved['inputs']['reference_budgets'][demand['demand_id']]
            receipt = bind_budget(target, generated['channels'][demand['slot']])
            self.assertAlmostEqual(receipt['scaling_receipt']['achieved_total'], target['total'], places=8)
