"""The DOE Ref generator recipes carry the release 2.0.0 values (ADR 0046 stage X1.2, ADR 0051)."""
import json
import os
import unittest
from pathlib import Path

from atlas_schedules import programmes
from atlas_schedules.release import Release
from scripts import atlas_delta, build_reference_recipes as m
from scripts.common import load_json


@unittest.skipUnless((atlas_delta.folder_of('2.2.0')/'manifest.json').exists(), 'release 2.2.0 not written')
class ReleaseValueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = Release(atlas_delta.folder_of('2.2.0'))
        cls.folders = [f for f in cls.release.generation_folders() if f.split('/')[1].startswith('doe-ref-')]
        cls.recipes = [programmes.assemble(cls.release, pid, view) for f in cls.folders
                       for pid, block in cls.release.generation(f)['programs'].items() for view in block['views']]
        cls.programs = {}
        for path in sorted((m.RELEASE/'commercial').glob('doe-ref-*/*/programs/*/*.json')):
            record = load_json(path)
            cls.programs[record['id']] = (m.release_path(path), record)

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.release, cls.recipes, cls.programs

    def test_every_generated_program_has_a_source_block(self):
        generated = {bt for bt in programmes.SAMPLING} | {m.APARTMENT}
        expected = {pid for pid, (_, r) in self.programs.items() if r['building_type'] in generated}
        self.assertEqual({r['program_id'] for r in self.recipes}, expected)
        self.assertEqual(len(self.recipes), 357)
        for recipe in self.recipes:
            path, record = self.programs[recipe['program_id']]
            self.assertEqual(recipe['values'], 'source')
            self.assertEqual(('data/atlas-releases/v2.0.0/'+recipe['source']['program'], recipe['name']), (path, record['name']))

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

    def test_schedules_and_people_are_release_schedules_of_the_folder(self):
        for folder in self.folders:
            table = self.release.schedules(folder)
            for configuration in self.release.generation(folder).get('configurations', {}).values():
                for schedule_id, count in configuration['people']:
                    self.assertIn(schedule_id, table)
                    self.assertGreater(count, 0)

    def test_services_carry_the_release_water_demand(self):
        services = 0
        for folder in self.folders:
            for service_id in self.release.generation(folder).get('services', {}):
                record = programmes.assemble_service(self.release, service_id)
                load = self.release.services(folder)[service_id]['load']
                self.assertEqual((record['demand']['value'], record['demand']['unit']), (load['value'], load['unit']))
                for variant in record['configurations'].values():
                    self.assertEqual(variant['schedule'], load['schedule_id'])
                services += 1
        self.assertEqual(services, 54)

    def test_no_block_names_the_frozen_definitions(self):
        for folder in self.folders:
            self.assertNotIn('definition-releases', json.dumps(self.release.generation(folder)))


@unittest.skipUnless(os.environ.get('ATLAS_DOE_REFERENCE_ROOT'), 'set ATLAS_DOE_REFERENCE_ROOT to the extracted v1.4_7.2 files')
class ReproductionTests(unittest.TestCase):
    def test_generation_blocks_reproduce(self):
        m.check(Path(os.environ['ATLAS_DOE_REFERENCE_ROOT']))


if __name__ == '__main__':
    unittest.main()
