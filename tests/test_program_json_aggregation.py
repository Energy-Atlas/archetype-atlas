"""Equipment trajectories and heat partitions use different weighting rules."""
import copy
import importlib
import unittest

from jsonschema import Draft202012Validator
from scripts.common import ROOT, load_json
from scripts.semantics import profile


def ruleset(identity, values, extra=()):
    return {'id': identity, 'name': identity, 'type': 'ruleset', 'unit': '1',
            'timestep_minutes': 60,
            'rule_selection': 'last_specific_match_else_last_default',
            'rules': [{'start_date': '01-01', 'end_date': '12-31',
                       'day_types': ['Default'], 'values': values}] + list(extra)}


def annual(identity, values):
    return {'id': identity, 'name': identity, 'type': 'annual', 'unit': '1',
            'year': 2007, 'clock': 'local_standard_time', 'timestep_minutes': 60,
            'values': values + [0] * (8760 - len(values))}


def equipment(identity, schedule_id, fraction=.2, **kwargs):
    return dict({'demand_id': identity, 'type': 'electric_equipment',
                 'end_use': identity, 'value': 1000, 'unit': 'W', 'basis': 'dwelling_unit',
                 'schedule_id': schedule_id,
                 'heat_fractions': {'radiant': fraction, 'latent': 0, 'lost': 0}}, **kwargs)


def inspect(schedule, day, date):
    rules = [dict(r, day_types='|'.join(r['day_types']),
                  start_date='2000-' + r['start_date'], end_date='2000-' + r['end_date'])
             for r in schedule['rules']]
    return profile(rules, day, date)


class EquipmentAggregationTests(unittest.TestCase):
    def aggregate(self, *args, **kwargs):
        self.assertIsNotNone(importlib.util.find_spec('scripts.program_json_aggregation'),
                             'Equipment aggregation helper is missing')
        return importlib.import_module('scripts.program_json_aggregation').aggregate_loads(*args, **kwargs)

    def test_power_sum_and_annual_heat_weight_have_distinct_weights(self):
        schedules = {'one': annual('one', [1]), 'three': annual('three', [1, 1, 1])}
        original = [equipment('a', 'one'), equipment('b', 'three', .6)]
        before = copy.deepcopy((original, schedules))
        loads, result, metadata = self.aggregate(original, schedules)
        self.assertEqual(len(loads), 1)
        self.assertEqual(loads[0]['value'], 2000)
        combined = result[loads[0]['schedule_id']]
        self.assertEqual(combined['values'][:4], [1, .5, .5, 0])
        self.assertEqual(sum(combined['values']) * loads[0]['value'], 4000)
        self.assertAlmostEqual(loads[0]['heat_fractions']['radiant'], .5)
        self.assertEqual(combined['year'], 2007)
        components = metadata['groups'][0]['components']
        self.assertEqual([c['annual_energy_weight'] for c in components], [.25, .75])
        self.assertEqual([c['load'] for c in components], original)
        self.assertEqual(metadata['calendar']['year'], 2007)
        self.assertEqual(metadata['calendar']['holidays'], [])
        self.assertEqual((original, schedules), before)
        self.assertEqual(result['one'], schedules['one'])
        self.assertEqual(result['three'], schedules['three'])

    def test_fuel_host_and_basis_stay_separate_and_other_loads_unchanged(self):
        loads = [equipment('a', 's', type='gas_equipment', fuel='natural gas'),
                 equipment('b', 's', type='gas_equipment', fuel='propane'),
                 equipment('c', 's', host='exterior'), equipment('d', 's'),
                 equipment('e', 's', basis='floor_area', unit='W/m2'),
                 equipment('f', 's', type='lighting'),
                 equipment('g', 's', type='occupancy'),
                 equipment('h', 's', type='hot_water')]
        out, _, _ = self.aggregate(loads, {'s': ruleset('s', [1])})
        self.assertEqual(out, loads)

    def test_rules_preserve_specific_precedence_seasons_and_design_days(self):
        extra = [{'start_date': '11-01', 'end_date': '03-01', 'day_types': ['Wkdy'], 'values': [.6]},
                 {'start_date': '01-01', 'end_date': '12-31', 'day_types': ['Mon'], 'values': [1]},
                 {'start_date': '01-01', 'end_date': '12-31', 'day_types': ['Hol'], 'values': [.1]},
                 {'start_date': '02-01', 'end_date': '02-29', 'day_types': ['SmrDsn'], 'values': [.8]},
                 {'start_date': '01-01', 'end_date': '12-31', 'day_types': ['WntrDsn'], 'values': [.7]}]
        a, b = ruleset('a', [.2], extra), ruleset('b', [.4])
        out, schedules, _ = self.aggregate([equipment('a', 'a'), equipment('b', 'b')], {'a': a, 'b': b})
        mixed = schedules[out[0]['schedule_id']]
        self.assertEqual(mixed['type'], 'ruleset')
        self.assertEqual(mixed['rule_selection'], 'last_specific_match_else_last_default')
        for day, date, expected in [('Mon', '01-01', .7), ('Tue', '01-01', .5),
                                    ('Tue', '06-01', .3), ('Hol', '01-01', .25),
                                    ('SmrDsn', '02-29', .6), ('WntrDsn', '06-01', .55),
                                    ('Default', '02-29', .3), ('Wkdy', '01-01', .5),
                                    ('Wknd', '01-01', .3), ('Tue', '10-31', .3),
                                    ('Tue', '11-01', .5), ('Tue', '03-01', .5),
                                    ('Tue', '03-02', .3)]:
            with self.subTest(day=day, date=date):
                self.assertAlmostEqual(inspect(mixed, day, date)[0], expected)
        self.assertEqual(schedules['a'], a)

    def test_holiday_calendar_controls_annual_energy_weight(self):
        holiday = {'start_date': '01-01', 'end_date': '12-31', 'day_types': ['Hol'], 'values': [0]}
        schedules = {'a': ruleset('a', [1], [holiday]), 'b': ruleset('b', [1])}
        _, _, metadata = self.aggregate([equipment('a', 'a'), equipment('b', 'b', .6)], schedules,
                                        holidays=('2007-01-01',))
        components = metadata['groups'][0]['components']
        self.assertEqual(components[0]['annual_energy'], 8736000)
        self.assertEqual(components[1]['annual_energy'], 8760000)
        self.assertEqual(metadata['calendar']['holidays'], ['2007-01-01'])

    def test_zero_annual_energy_is_omitted_without_division(self):
        out, _, metadata = self.aggregate([equipment('a', 's'), equipment('b', 's')],
                                           {'s': ruleset('s', [0])})
        self.assertEqual(out, [])
        self.assertEqual(metadata['groups'][0]['status'], 'omitted_zero_energy')
        self.assertIsNone(metadata['groups'][0]['components'][0]['annual_energy_weight'])

    def test_annual_calendar_mismatch_and_mixed_schedule_kinds_are_errors(self):
        schedules = {'a': annual('a', [1]), 'b': ruleset('b', [1])}
        with self.assertRaisesRegex(ValueError, 'year|calendar'):
            self.aggregate([equipment('a', 'a')], schedules, calendar_year=2008)
        with self.assertRaisesRegex(ValueError, 'annual.*ruleset|ruleset.*annual'):
            self.aggregate([equipment('a', 'a'), equipment('b', 'b')], schedules)

    def test_ids_and_output_are_deterministic_under_component_reordering(self):
        schedules = {'s': ruleset('s', [1])}
        a, b = equipment('a', 's'), equipment('b', 's', .6)
        self.assertEqual(self.aggregate([a, b], schedules), self.aggregate([b, a], schedules))

    def test_design_day_only_load_is_not_silently_omitted(self):
        design = {'start_date': '01-01', 'end_date': '12-31', 'day_types': ['SmrDsn'], 'values': [1]}
        with self.assertRaisesRegex(ValueError, 'zero annual energy.*design|nonzero.*calendar'):
            self.aggregate([equipment('a', 's')], {'s': ruleset('s', [0], [design])})

    def test_incomplete_fractions_and_nonfinite_power_are_rejected(self):
        for updates in [{'value': float('nan')}, {'value': -1},
                        {'heat_fractions': {'radiant': None, 'latent': 0, 'lost': 0}},
                        {'heat_fractions': {'radiant': -.1, 'latent': 0, 'lost': 0}},
                        {'heat_fractions': {'radiant': .8, 'latent': .3, 'lost': 0}}]:
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                self.aggregate([equipment('a', 's', **updates), equipment('b', 's')],
                               {'s': ruleset('s', [1])})

    def test_later_weekday_rule_wins_even_over_earlier_monday_selector(self):
        later = [{'start_date': '01-01', 'end_date': '12-31', 'day_types': ['Mon'], 'values': [.9]},
                 {'start_date': '01-01', 'end_date': '12-31', 'day_types': ['Wkdy'], 'values': [.2]},
                 {'start_date': '01-01', 'end_date': '12-31', 'day_types': ['Default'], 'values': [.8]}]
        schedules = {'a': ruleset('a', [.1], later), 'b': ruleset('b', [.4])}
        out, result, _ = self.aggregate([equipment('a', 'a'), equipment('b', 'b')], schedules)
        mixed = result[out[0]['schedule_id']]
        self.assertAlmostEqual(inspect(mixed, 'Mon', '01-01')[0], .3)
        self.assertAlmostEqual(inspect(mixed, 'Tue', '01-01')[0], .3)
        self.assertAlmostEqual(inspect(mixed, 'Sun', '01-01')[0], .6)

    def test_explicit_day_coverage_without_default_can_still_compose(self):
        a = ruleset('a', [.2])
        a['rules'][0]['day_types'] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat',
                                    'Sun', 'Hol', 'SmrDsn', 'WntrDsn']
        schedules = {'a': a, 'b': ruleset('b', [.4])}
        out, result, _ = self.aggregate([equipment('a', 'a'), equipment('b', 'b')], schedules)
        mixed = result[out[0]['schedule_id']]
        self.assertEqual(mixed['type'], 'ruleset')
        for day in a['rules'][0]['day_types']:
            self.assertAlmostEqual(inspect(mixed, day, '02-29')[0], .3)

    def test_composed_schedules_conform_to_embedded_dto_schema(self):
        schema = load_json(ROOT / 'schemas/program-json-v2.schema.json')
        validator = Draft202012Validator({'$defs': schema['$defs'], '$ref': '#/$defs/schedule'})
        for source in [ruleset('s', [.5]), annual('s', [1])]:
            out, result, _ = self.aggregate([equipment('a', 's'), equipment('b', 's')], {'s': source})
            self.assertEqual([e.message for e in validator.iter_errors(result[out[0]['schedule_id']])], [])
