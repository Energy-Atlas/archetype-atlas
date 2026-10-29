"""The DOE Ref generator recipes carry the release 2.0.0 values (ADR 0046, stage X1.2)."""
import json
import os
import unittest
from pathlib import Path

from scripts import build_reference_recipes as m
from scripts.recipe_shapes import SAMPLING
from scripts.common import ROOT, load_json

DATA = ROOT/'atlas_schedules/data'


def packaged(folder):
    return [load_json(p) for p in sorted((DATA/folder).glob('*.json'))]


@unittest.skipUnless((m.RELEASE/'manifest.json').exists(), 'release 2.0.0 not written')
class ReleaseValueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = load_json(DATA/'schedules.json')
        cls.recipes = [r for r in packaged('recipes') if (r['source'].get('template') or '').startswith('DOE Ref')]
        cls.programs, cls.schedules = {}, {}
        for path in sorted((m.RELEASE/'commercial').glob('doe-ref-*/*/programs/*/*.json')):
            record = load_json(path)
            cls.programs[record['id']] = (m.release_path(path), record)
        for path in sorted((m.RELEASE/'commercial').glob('doe-ref-*/*/schedules.json')):
            table = load_json(path)
            for schedule_id, schedule in table['schedules'].items():
                cls.schedules[schedule_id] = [[r['day_types'], r['start_date'], r['end_date'], table['days'][r['day']]]
                                              for r in schedule['rules']]

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.table, cls.recipes, cls.programs, cls.schedules

    def test_every_generated_program_has_a_recipe_under_its_release_id(self):
        generated = {bt for bt in SAMPLING} | {m.APARTMENT}
        expected = {pid for pid, (_, r) in self.programs.items() if r['building_type'] in generated}
        self.assertEqual({r['program_id'] for r in self.recipes}, expected)
        for recipe in self.recipes:
            path, record = self.programs[recipe['program_id']]
            self.assertEqual((recipe['source']['definition'], recipe['name']), (path, record['name']))

    def test_demands_and_slots_are_the_release_values(self):
        for recipe in self.recipes:
            if recipe['kind'] in ('composition', 'apartment_unit'):
                continue
            _, record = self.programs[recipe['program_id']]
            loads = {l['quantity']: l for l in record['loads']}
            with self.subTest(program=recipe['program_id']):
                for demand in recipe['demands']:
                    load = loads[demand['quantity']]
                    self.assertEqual((demand['value'], demand['unit'], demand['basis']), (load['value'], load['unit'], load['basis']))
                    slot = next(s for s in recipe['slots'] if s['slot'] == demand['slot'])
                    self.assertEqual(slot['schedule'], load['schedule_id'])
                for control in recipe['controls']:
                    if 'people' in control:
                        self.assertEqual(control['people']['density'], loads['occupancy']['value'])
                setpoints = {s['slot']: s['schedule'] for s in recipe['slots'] if s['slot'].endswith('_setpoint')}
                for slot, schedule in setpoints.items():
                    self.assertEqual(schedule, record['parameters'][slot+'_schedule_id']['value'])
                positive = {q for q, l in loads.items() if l['status'] == 'known' and (l['value'] or 0) > 0
                            and not l.get('service_id') and q in ('lighting', 'electric_equipment', 'gas_equipment')}
                self.assertLessEqual(positive, {d['quantity'] for d in recipe['demands']})

    def test_apartment_units_are_resstock_units_of_their_era(self):
        # ADR 0047: the unit's loads come from ResStock, so it carries no prototype demands or slots.
        eras = {'DOE Ref Pre-1980': ['<1940', '1940s', '1950s', '1960s', '1970s'],
                'DOE Ref 1980-2004': ['1980s', '1990s', '2000s']}
        units = [r for r in self.recipes if r['kind'] == 'apartment_unit']
        self.assertTrue(units)
        for recipe in units:
            with self.subTest(program=recipe['program_id']):
                self.assertNotIn('demands', recipe)
                self.assertNotIn('slots', recipe)
                self.assertEqual(recipe['resstock_unit']['vintages'], eras[recipe['source']['template']])

    def test_compositions_list_the_release_members(self):
        for recipe in (r for r in self.recipes if r['kind'] == 'composition'):
            _, record = self.programs[recipe['program_id']]
            self.assertEqual(recipe['composition']['members'],
                             [[x['program_id'], x['represented_area_m2']] for x in record['composition']['members']])

    def test_schedules_are_the_release_rules(self):
        used = set()
        for record in [*self.recipes, *packaged('configurations'), *packaged('services')]:
            used |= m.references(record, self.schedules)
        self.assertTrue(used)
        for schedule_id in used:
            rules = [[r['day_types'], r['start_date'], r['end_date'], r['values']] for r in self.table[schedule_id]['rules']]
            self.assertEqual(rules, self.schedules[schedule_id], schedule_id)

    def test_services_carry_the_release_water_demand(self):
        services = {}
        for path in sorted((m.RELEASE/'commercial').glob('doe-ref-*/*/services.json')):
            services.update(load_json(path))
        doe = [s for s in packaged('services') if any('__doe_ref_' in k for k in s['configurations'])]
        self.assertTrue(doe)
        for record in doe:
            load = services[record['service_id']]['load']
            self.assertEqual((record['demand']['value'], record['demand']['unit']), (load['value'], load['unit']))
            for variant in record['configurations'].values():
                self.assertEqual(variant['schedule'], load['schedule_id'])

    def test_no_recipe_names_the_frozen_definitions(self):
        for folder in ('recipes', 'services'):
            for record in packaged(folder):
                if 'doe-ref' in json.dumps(record.get('source', {})).lower() or '__doe_ref_' in json.dumps(record):
                    self.assertNotIn('definition-releases', json.dumps(record))


@unittest.skipUnless(os.environ.get('ATLAS_DOE_REFERENCE_ROOT'), 'set ATLAS_DOE_REFERENCE_ROOT to the extracted v1.4_7.2 files')
class ReproductionTests(unittest.TestCase):
    def test_packaged_recipes_reproduce(self):
        m.check(Path(os.environ['ATLAS_DOE_REFERENCE_ROOT']))


if __name__ == '__main__':
    unittest.main()
