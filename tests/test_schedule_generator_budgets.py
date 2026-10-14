"""Conservation tests use hand-computed annual integrals."""
import copy
import math
import unittest

from atlas_schedules.errors import GeneratorError
from atlas_schedules.budgets import reference_budget, bind_budget


def demand(family='resstock'):
    return {'quantity': 'lighting', 'value': 10.0, 'unit': 'W/m2',
            'basis': 'floor_area', 'fuel': 'electricity', 'host': 'space',
            'evidence': {'source_family': family, 'locator': 'test source cell',
                         'original_value': 10, 'original_unit': 'W/m2'}}


class BudgetTests(unittest.TestCase):
    def test_res_and_com_reference_budget_conservation(self):
        for family in ('resstock', 'comstock'):
            with self.subTest(family=family):
                target = reference_budget(demand(family), [1.0] * 2000 + [0.0] * 6760)
                self.assertEqual(target['total'], 20000)
                self.assertEqual(target['unit'], 'Wh/m2')
                self.assertEqual(target['basis'], 'floor_area')
                for hours, expected in ((1600, 12.5), (2400, 20000 / 2400)):
                    samples = [1.0] * hours + [0.0] * (8760 - hours)
                    bound = bind_budget(target, samples)
                    self.assertEqual(bound['effective_magnitude']['value'], expected)
                    self.assertAlmostEqual(math.fsum(samples) * bound['effective_magnitude']['value'], 20000)
                    self.assertEqual(bound['reference_target'], target)
                    self.assertEqual(bound['scaling_receipt']['generated_integral'], hours)

    def test_direct_annual_definition_precedes_rounded_power(self):
        item = demand()
        item['annual_target'] = {'total': 4321, 'unit': 'Wh/m2',
                                 'evidence': {'locator': 'annual source', 'original_value': 4321,
                                              'original_unit': 'Wh/m2'}}
        target = reference_budget(item, [1.0] * 8760)
        self.assertEqual(target['total'], 4321)
        self.assertEqual(target['method'], 'direct_annual')
        self.assertEqual(target['evidence']['locator'], 'annual source')
        self.assertEqual(bind_budget(target, [1.0] * 1000)['effective_magnitude']['value'], 4.321)

    def test_volume_seconds_conversion(self):
        item = demand()
        item.update(quantity='hot_water', value=0.001, unit='m3/s/dwelling', basis='dwelling_unit', fuel='water')
        target = reference_budget(item, [1.0] * 2000)
        self.assertEqual((target['total'], target['unit']), (7200, 'm3/dwelling'))
        bound = bind_budget(target, [1.0] * 1000)
        self.assertEqual(bound['effective_magnitude']['value'], 0.002)
        self.assertEqual(bound['scaling_receipt']['seconds_per_sample'], 3600)

    def test_volume_budget_rejects_material_rounding_drift(self):
        from atlas_schedules.contract import validate_bundle
        from tests.test_schedule_generator_contract import bundle
        b = bundle(); binding = b['bindings'][0]
        target = reference_budget({**demand(), 'quantity': 'hot_water', 'value': 1e-10,
                                   'unit': 'm3/s/dwelling', 'basis': 'dwelling_unit',
                                   'fuel': 'water'}, [1.0] * 2000)
        bound = bind_budget(target, b['schedules'][binding['schedule_id']]['values'])
        binding.update(fuel='water', budget_method=target['method'], **bound)
        validate_bundle(b)
        binding['reference_target']['total'] += 1e-9
        with self.assertRaises(GeneratorError): validate_bundle(b)

    def test_zero_unknown_and_unrealized_targets(self):
        zero = demand(); zero['value'] = 0
        target = reference_budget(zero, [1.0] * 8760)
        self.assertEqual(bind_budget(target, [0.0] * 8760)['effective_magnitude']['value'], 0)
        unknown = demand(); unknown['value'] = None
        with self.assertRaises(GeneratorError) as caught:
            reference_budget(unknown, [1.0] * 8760)
        self.assertEqual(caught.exception.code, 'unresolved_annual_target')
        with self.assertRaises(GeneratorError) as caught:
            bind_budget(reference_budget(demand(), [1.0] * 8760), [0.0] * 8760)
        self.assertEqual(caught.exception.code, 'zero_generated_integral')

    def test_normalization_amplitude_is_not_nameplate(self):
        item = demand(); item['installed_rating'] = {'value': 10, 'unit': 'W/m2'}
        target = reference_budget(item, [1.0] * 2000)
        self.assertEqual(bind_budget(target, [1.0] * 1600)['effective_magnitude']['value'], 12.5)
        constrained = copy.deepcopy(target)
        constrained['capacity_constraint'] = {'maximum': 10, 'unit': 'W/m2',
                                              'evidence': {'locator': 'requested constraint'}}
        with self.assertRaises(GeneratorError) as caught:
            bind_budget(constrained, [1.0] * 1600)
        self.assertEqual(caught.exception.code, 'infeasible_intensity')


if __name__ == '__main__':
    unittest.main()
