"""Contract handoff checks; no site exporter or connector implementation required."""
import calendar
import copy
import datetime
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from scripts.semantics import profile

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


class ProgramJSONContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.program_schema = read('schemas/program-json-v2.schema.json')
        cls.schedule_schema = read('schemas/schedule-json-v2.schema.json')
        cls.validator = Draft202012Validator(cls.program_schema, format_checker=FormatChecker())
        cls.schedule_validator = Draft202012Validator(cls.schedule_schema, format_checker=FormatChecker())
        cls.raw = read('docs/examples/program-json-v2/medium-office.raw.json')
        cls.ready = read('docs/examples/program-json-v2/medium-office.defaulted.json')

    def test_schemas_and_examples(self):
        Draft202012Validator.check_schema(self.program_schema)
        Draft202012Validator.check_schema(self.schedule_schema)
        for row in (self.raw, self.ready):
            self.validator.validate(row)
            for sid, schedule in row['schedules'].items():
                self.assertEqual(sid, schedule['id'])
                self.schedule_validator.validate(schedule)

    def test_rejects_invalid_consumer_inputs(self):
        cases = [
            lambda x: x['loads'][0].update(value=None),
            lambda x: x['loads'][0].update(unit='W/m2'),
            lambda x: x['loads'][0].update(basis='absolute'),
            lambda x: x['loads'][1]['heat_fractions'].update(radiant=2),
            lambda x: x['controls'].update(activity_schedule_id=None),
        ]
        for mutate in cases:
            row = copy.deepcopy(self.ready)
            mutate(row)
            self.assertTrue(list(self.validator.iter_errors(row)))

    def test_reference_closure_and_units(self):
        for row in (self.raw, self.ready):
            for load in row['loads']:
                if load['schedule_id'] is not None:
                    self.assertEqual(row['schedules'][load['schedule_id']]['unit'], '1')
                for key in ('target_temperature_schedule_id', 'inlet_temperature_schedule_id'):
                    if load.get(key):
                        self.assertEqual(row['schedules'][load[key]]['unit'], 'degC')
                fractions = load.get('heat_fractions', {})
                self.assertLessEqual(sum(v for v in fractions.values() if v is not None), 1 + 1e-12)
            for key, unit in [('heating_setpoint_schedule_id', 'degC'),
                              ('cooling_setpoint_schedule_id', 'degC'),
                              ('activity_schedule_id', 'W/person')]:
                if row['controls'][key] is not None:
                    self.assertEqual(row['schedules'][row['controls'][key]]['unit'], unit)

    @staticmethod
    def values(schedule, day, month_day):
        rules = [{'start_date': '2000-' + r['start_date'], 'end_date': '2000-' + r['end_date'],
                  'day_types': '|'.join(r['day_types']), 'values': r['values']}
                 for r in schedule['rules']]
        return profile(rules, day, month_day)

    def test_full_defaulted_coverage_and_temperature_order(self):
        row = self.ready
        for offset in range(366):
            month_day = (datetime.date(2000, 1, 1) + datetime.timedelta(days=offset)).strftime('%m-%d')
            for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Hol', 'WntrDsn', 'SmrDsn']:
                selected = {sid: self.values(s, day, month_day) for sid, s in row['schedules'].items()}
                heating = selected[row['controls']['heating_setpoint_schedule_id']]
                cooling = selected[row['controls']['cooling_setpoint_schedule_id']]
                self.assertTrue(all(h <= c for h, c in zip(heating, cooling)))
                for load in row['loads']:
                    if load['type'] == 'hot_water':
                        target = selected[load['target_temperature_schedule_id']]
                        inlet = selected[load['inlet_temperature_schedule_id']]
                        self.assertTrue(all(t >= i for t, i in zip(target, inlet)))

    def test_known_source_values_and_rule_order_preserved(self):
        source = next(x for x in read('data/definition-releases/v0.1.1/programs.json')
                      if x['id'] == self.ready['source']['program_id'])
        for before, after in zip(source['loads'], self.ready['loads']):
            if before['value'] is not None:
                self.assertEqual(before['value'], after['value'])
        for sid, raw_schedule in self.raw['schedules'].items():
            variants = [s for s in self.ready['schedules'].values()
                        if s['id'] == sid or s.get('source_context', {}).get('id') == sid]
            self.assertEqual(len(variants), 1)
            variant = variants[0]
            source_rules = variant['rules'][1:] if variant['id'] != sid else variant['rules']
            self.assertEqual(source_rules, raw_schedule['rules'])

    def test_raw_unknowns_and_explicit_assumptions(self):
        self.assertIsNone(self.raw['loads'][2]['value'])
        self.assertEqual(self.ready['loads'][2]['value'], 0)
        self.assertEqual(self.raw['assumptions'], [])
        self.assertEqual(len(self.ready['assumptions']), 22)
        self.assertNotEqual(self.raw['id'], self.ready['id'])
        policy = read('sources/program-json-defaults.json')
        rules = {r['id'] for r in policy['rules']}
        self.assertEqual(self.ready['default_policy_id'], policy['id'])
        self.assertTrue(all(a['rule_id'] in rules for a in self.ready['assumptions']))
        self.assertEqual(self.raw['source'], self.ready['source'])

    def test_actual_annual_realization(self):
        row = read('docs/examples/program-json-v2/residential-annual.schedule.json')
        self.schedule_validator.validate(row)
        self.assertEqual(len(row['values']), 24 * (366 if calendar.isleap(row['year']) else 365))
        self.assertEqual(row['source_context']['calendar']['year'], row['year'])
        row['values'].append(0)
        self.assertTrue(list(self.schedule_validator.iter_errors(row)))


if __name__ == '__main__':
    unittest.main()
