"""Closed, build-only exact apartment source recipe checks."""
import copy
import hashlib
import json
import math
import unittest
from collections import Counter

from atlas_schedules.budgets import reference_budget
from atlas_schedules.calendar import evaluate_rules
from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from scripts.common import ROOT
from scripts.schedule_generator_apartments import compile_apartment_sources, compile_apartment_recipes


SCOPE = ROOT / 'sources/schedule-generator-apartment-scope.json'
IDS_SHA = '3c0d169db7dd01f6cf0ebd5ce1c5a77d991d5a1cf16891b36178d6167c6794f0'


class ApartmentRecipes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = json.loads(SCOPE.read_text(encoding='utf-8'))
        cls.source = compile_apartment_sources(cls.scope)
        cls.records = compile_apartment_recipes(cls.source, cls.scope)

    def test_exact_84_identity_and_90_rules(self):
        ids = [p['id'] for p in self.scope['programmes']]
        self.assertEqual(hashlib.sha256(canonical(ids)).hexdigest(), IDS_SHA)
        self.assertEqual(set(self.source['programmes']), set(ids))
        self.assertEqual(len(self.source['programmes']), 84)
        self.assertEqual(len(self.source['requirements']), 40)
        self.assertEqual(len(self.source['locations']), 37)
        self.assertEqual(len(self.source['source_objects']['schedules']), 90)
        self.assertEqual(len(self.source['source_objects']['raw_rows']), 84)
        self.assertEqual({p['view'] for p in self.scope['programmes']}, {'source', 'reviewed'})
        self.assertEqual({p['family'] for p in self.scope['programmes']}, {'HighriseApartment', 'MidriseApartment'})
        self.assertEqual(len({(p['family'], p['template']) for p in self.scope['programmes']}), 8)
        self.assertEqual({(p['role'], sum(x['role'] == p['role'] for x in self.scope['programmes']))
                          for p in self.scope['programmes']}, {('dwelling', 40), ('corridor', 28), ('support_office', 16)})
        self.assertEqual(len({q['source_beneficiary_id'] for q in self.source['requirements'].values()}), 20)
        self.assertEqual(len(self.records), 84)
        original_rules = json.loads((ROOT / 'data/definition-releases/v0.1.1/schedules.json').read_text())
        for sid, obj in self.source['source_objects']['schedules'].items():
            self.assertEqual(obj['value'], original_rules[int(obj['locator'][1:])])
            self.assertEqual(obj['value']['id'], sid)
            self.assertEqual(obj['value']['rules'], original_rules[int(obj['locator'][1:])]['rules'])
        for pid, row in self.source['source_objects']['raw_rows'].items():
            original = json.loads((ROOT / row['path']).read_text(encoding='utf-8'))
            self.assertEqual(row['value'], original['space_types'][int(row['locator'].split('/')[-1])], pid)
        for key, record in self.records.items():
            self.assertEqual(key, ('program', record['definition']['id']))
            self.assertNotIn('source_composition', record['recipe'])
            self.assertEqual(record['recipe']['source_context']['qualification_state'], 'closed')
        for mutate in (
            lambda s: s['programmes'][0].__setitem__('id', 'program-foreign'),
            lambda s: s['programmes'][0].__setitem__('view', 'reviewed'),
            lambda s: s['programmes'][0].__setitem__('template', '90.1-2019'),
            lambda s: s['programmes'][0].__setitem__('role', 'corridor'),
            lambda s: s['source_files']['programs.json'].__setitem__('sha256', '0'*64),
        ):
            bad = copy.deepcopy(self.scope); mutate(bad)
            with self.assertRaises(GeneratorError): compile_apartment_sources(bad)
        bad = copy.deepcopy(self.source)
        bad['source_objects']['schedules'][next(iter(bad['source_objects']['schedules']))]['value']['rules'][0]['values'][0] = -1
        with self.assertRaises(GeneratorError): compile_apartment_recipes(bad, self.scope)

    def test_all_original_targets_and_people_controls(self):
        for (kind, pid), record in self.records.items():
            recipe = record['recipe']; p = record['definition']
            load_by_id = {x['demand_id']: x for x in p['loads']}
            self.assertEqual(len(recipe['resolved']['demands']), sum(x['status'] == 'known' and x['quantity'] not in ('occupancy', 'hot_water_volume') and x['value'] > 0 for x in p['loads']))
            for demand in recipe['resolved']['demands']:
                original = load_by_id[demand['demand_id']]
                self.assertEqual(demand['value'], original['value'])
                self.assertEqual(demand['unit'], original['unit'])
                self.assertEqual(demand['host'], 'assigned_zone')
                self.assertEqual(demand['evidence']['source_scope'], original['scope'])
                self.assertEqual(demand['fuel'], 'natural_gas' if original['quantity'] == 'gas_equipment' else 'electricity')
                values = evaluate_rules(recipe['reference_sources'][demand['slot']], 2007, [])['values']
                target = reference_budget(demand, values)
                self.assertTrue(math.isclose(target['total'], original['value'] * math.fsum(values)))
            self.assertFalse(any(x['quantity'] == 'occupancy' for x in recipe['resolved']['demands']))
            self.assertEqual({x['slot'] for x in recipe['resolved']['controls']},
                             {x['slot'] for x in recipe['resolved']['slots'] if x['kind'] == 'control'})
            self.assertEqual(len(recipe['source_context']['unresolved_exclusions']),
                             sum(x['status'] == 'unknown' for x in p['loads'] if x['quantity'] != 'hot_water_volume') +
                             sum(p['parameters'][name]['status'] == 'unknown' for name in
                                 ('activity_schedule_id', 'heating_setpoint_schedule_id',
                                  'cooling_setpoint_schedule_id')))
            if pid in self.source['requirements']:
                self.assertEqual(recipe['required_service_sets'], [self.source['requirements'][pid]])
                self.assertIn('N', recipe['required_inputs'])
                self.assertNotIn('seed', recipe['required_inputs'])
                self.assertNotIn('N', recipe['variable_inputs'])
                self.assertEqual(recipe['source_context']['nominal_density']['value'],
                                 next(x['value'] for x in p['loads'] if x['quantity'] == 'occupancy'))
                expected_activity = 120.0 if p['template'].startswith('DOE Ref') else 95.0
                self.assertEqual({v for rule in recipe['reference_sources']['activity']['rules']
                                  for v in rule['values']}, {expected_activity})
            else:
                self.assertNotIn('N', recipe['required_inputs'])
        sentinel = self.records['program', 'program-23458a6e125b4cee7f62bb42']['recipe']
        targets = {d['slot']: reference_budget(d, evaluate_rules(sentinel['reference_sources'][d['slot']], 2007, [])['values'])['total'] for d in sentinel['resolved']['demands']}
        self.assertAlmostEqual(targets['lighting_interior'], 6065.282301680871)
        self.assertAlmostEqual(targets['additional_lighting'], 1530.4917957512478)
        self.assertAlmostEqual(targets['electric_equipment'], 38441.5445)
        req = self.source['requirements']['program-23458a6e125b4cee7f62bb42']
        self.assertAlmostEqual(req['original_demand']['value']['value'] * 4591.7 * 3600, 0.6853498919966031)

    def test_unknown_zero_and_absent_partition(self):
        counts = Counter()
        for obj in self.source['programmes'].values():
            p = obj['value']
            for q in ('occupancy', 'lighting', 'additional_lighting', 'electric_equipment',
                      'gas_equipment', 'hot_water_volume'):
                matches = [x for x in p['loads'] if x['quantity'] == q]
                state = ('absent' if not matches else 'unknown' if matches[0]['status'] == 'unknown'
                         else 'zero' if matches[0]['value'] == 0 else 'known')
                counts[q, state] += 1
        self.assertEqual(counts['additional_lighting', 'unknown'], 48)
        self.assertEqual(counts['gas_equipment', 'unknown'], 42)
        self.assertEqual(counts['gas_equipment', 'zero'], 42)
        self.assertEqual(counts['hot_water_volume', 'known'], 40)
        self.assertEqual(counts['hot_water_volume', 'absent'], 44)
        self.assertEqual(counts['occupancy', 'zero'], 28)
        self.assertEqual(counts['electric_equipment', 'zero'], 28)


if __name__ == '__main__': unittest.main()
