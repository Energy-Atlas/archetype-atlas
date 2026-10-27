"""Release 1.1.0 against its answer key, the extracted DOE reference values (ADR 0037).

The values file is the answer key: every applied schedule, value, window ratio, service,
infiltration rule and mass fill must appear in the resolved release, schedules compared
over the full year, holidays and design days at the ADR 0035 tolerance. With
ATLAS_DOE_IDF_ROOT set to the extracted doe-reference/v1.4_7.2 folder, every program slot
is also compared with the DOE Schedule:Compact objects themselves.
"""
import json
import math
import os
import unittest
from pathlib import Path

from scripts import atlas_delta_release, idf_schedules, reference_extras
from scripts.atlas_exports import Release
from scripts.common import ROOT, load_json
from scripts.reconciliation_overlay import TEMPLATES

VALUES = ROOT/'data/reconciliation/doe-reference-values-v1.json'
REGISTER = ROOT/'data/reconciliation/doe-reference-v1.json'
HOLIDAYS = [('New Years Day', 'January 1'), ('Independence Day', 'July 4'), ('Christmas', 'December 25'),
            ('Memorial Day', 'Last Monday in May'), ('Labor Day', '1st Monday in September')]


def profile(rule):
    return rule['values'] * (24 // len(rule['values']))


def same_year(a, b, days):
    x, y = idf_schedules.evaluate_ruleset(a, profile, days), idf_schedules.evaluate_ruleset(b, profile, days)
    return [k for k in days if not (x[k] is None and y[k] is None) and not idf_schedules.same(x[k], y[k])]


@unittest.skipUnless((atlas_delta_release.TARGET/'manifest.json').exists(), 'release 1.1.0 not written')
class ReleaseAnswerKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = atlas_delta_release.files()
        cls.release = Release(cls.files)
        cls.values = load_json(VALUES)
        cls.base = {}
        for path in (atlas_delta_release.BASE/'commercial').glob('doe-ref-*/*/programs/*/*.json'):
            p = json.loads(path.read_text(encoding='utf-8'))
            cls.base[p['id']] = p
        cls.current = {}
        for pid, (_, p) in cls.release.programs.items():
            cls.current[(p['template'], p['building_type'], p.get('source_id') or p['name'])] = pid

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.files, cls.release, cls.values, cls.base, cls.current

    def now(self, base_id):
        p = self.base[base_id]
        return self.release.stored_program(self.current[(p['template'], p['building_type'], p.get('source_id') or p['name'])])

    def suite(self, program):
        return self.release.suite(self.release.programs[program['id']][0])

    def slot(self, program, slot):
        kind, field, _ = reference_extras.SLOTS[slot]
        if kind == 'load':
            entry = next((l for l in program['loads'] if l['quantity'] == field), None)
            return entry and entry.get('schedule_id')
        return program['parameters'].get(field, {}).get('value')

    def test_only_the_doe_ref_folders_change(self):
        listed = json.loads((atlas_delta_release.TARGET/'manifest.json').read_text())
        changed = [*listed['files'], *listed['deleted']]
        self.assertEqual([p for p in changed if p.startswith('commercial/') and not p.startswith('commercial/doe-ref-')], [])
        self.assertEqual([p for p in changed if '/midrise-apartment/' in p], [])

    def test_program_slots_take_the_doe_schedules(self):
        days = idf_schedules.calendar_days(HOLIDAYS)
        checked = 0
        for folder in self.values['folders'].values():
            for base_id, slots in folder['program_schedules'].items():
                program = self.now(base_id)
                for slot, schedule_id in slots.items():
                    stored = self.slot(program, slot)
                    if slot == 'hot_water' and stored is None:
                        continue  # served by a building service, checked below
                    with self.subTest(program=program['id'], slot=slot):
                        got = self.suite(program).schedule(stored)['rules']
                        self.assertEqual(same_year(got, self.values['schedules'][schedule_id]['rules'], days), [])
                        checked += 1
        self.assertGreater(checked, 300)

    def test_program_values_and_fractions(self):
        for folder in self.values['folders'].values():
            for item in folder['program_values']:
                program = self.now(item['program'])
                load = next(l for l in program['loads'] if l['quantity'] == item['path'][1])
                with self.subTest(program=program['id'], path=item['path']):
                    if item['path'][2] in ('value', 'zero'):
                        self.assertTrue(math.isclose(load['value'], item['value'] or 0.0, abs_tol=1e-12))
                    else:
                        self.assertEqual(load['thermal_effects'][item['path'][3]]['value'], item['value'])

    def test_hot_water_zeros_calendar_and_window_ratios(self):
        for folder in self.values['folders'].values():
            for item in folder['hot_water']['zero_programs']:
                program = self.now(item['program'])
                load = next(l for l in program['loads'] if l['quantity'] == 'hot_water_volume')
                self.assertEqual(load['value'], 0.0)
                self.assertNotIn('service_water_heating_schedule_id', program.get('unresolved', {}))
            for base_id, item in folder['fenestration']['programs'].items():
                self.assertEqual(self.now(base_id)['fenestration']['wwr'], {d: item['value'][d] for d in 'NESW'})
            for base_id in folder['program_schedules']:
                self.assertEqual(len(self.now(base_id)['source_calendar']['holidays']), 10)

    def test_new_programs_take_their_zone_groups(self):
        days = idf_schedules.calendar_days(HOLIDAYS)
        by_name = {(p['template'], p['name']): p for _, p in self.release.programs.values()}
        for key, folder in self.values['folders'].items():
            for item in folder['new_programs']:
                program = by_name[(TEMPLATES[key.split('/')[0]], item['name'])]
                parent = self.now(item['parent'])
                with self.subTest(program=item['name'], template=key):
                    self.assertEqual([s['name'] for s in program['source_spaces']], item['zones'])
                    self.assertLessEqual(set(item['zones']), set(parent['excluded_source_spaces']))
                    for quantity, value in item['loads'].items():
                        load = next(l for l in program['loads'] if l['quantity'] == quantity)
                        self.assertTrue(math.isclose(load['value'], value, abs_tol=1e-12))
                    for slot, schedule_id in item['slots'].items():
                        got = self.suite(program).schedule(self.slot(program, slot))['rules']
                        self.assertEqual(same_year(got, self.values['schedules'][schedule_id]['rules'], days), [])
        names = {p['name'] for _, p in self.release.programs.values() if p['template'] == 'DOE Ref 1980-2004'}
        self.assertIn('Activity_Mixed_PrimarySchool', names)

    def test_mixes_conserve_member_loads(self):
        for pid, (_, program) in self.release.programs.items():
            if program['template'] not in TEMPLATES.values() or 'composition' not in program:
                continue
            members = {m['program_id']: m['weight'] for m in program['composition']['members']}
            for load in program['loads']:
                if load.get('value') is None:
                    continue
                parts = [next(l for l in self.release.stored_program(m)['loads'] if l['quantity'] == load['quantity'])['value']
                         for m in members]
                with self.subTest(program=pid, quantity=load['quantity']):
                    self.assertTrue(math.isclose(load['value'], math.fsum(w*v for w, v in zip(members.values(), parts)), rel_tol=1e-12))

    def test_services(self):
        services = [json.loads(self.files[f'commercial/{key}/services.json']) for key in self.values['folders']]
        added = sum(len(f['services']) for f in self.values['folders'].values())
        names = {(s['template'], s['building_type'], s['end_use'], s.get('name')) for t in services for s in t.values()}
        expected = {(TEMPLATES[k.split('/')[0]], f['building_type'], s['end_use'], s['value']['name'])
                    for k, f in self.values['folders'].items() for s in f['services']}
        self.assertEqual(expected - names, set())
        self.assertGreaterEqual(added, 150)
        for table in services:
            for service in table.values():
                if service['load'].get('quantity') == 'hot_water_volume':
                    self.assertEqual(service['load']['thermal_effects']['sensible_fraction']['value'], 0.2)

    def test_constructions(self):
        for key, folder in self.values['folders'].items():
            template = key.split('/')[0]
            [path] = [p for p in self.files if p.startswith(f'commercial/{key}/constructions/')]
            set_id = json.loads(self.files[path])['id']
            for representation in ('detailed', 'unified'):
                document = self.release.constructions.export(set_id, '5-a', representation)
                with self.subTest(folder=key, representation=representation):
                    self.assertEqual({k: v for k, v in document['fenestration_defaults'].items() if k in ('conditioned', 'unconditioned', 'all')},
                                     folder['fenestration']['building']['value'])
                    rules = document['infiltration']['methods']['doe_design_flow']['zone_rules']
                    self.assertEqual(len(rules), len(folder['infiltration']['zone_rules']))
                    self.assertEqual(document['infiltration']['default_method'], 'fixed_source_reference_natural_ach')
                    spaces = {e['scope'].get('source_space_name') for e in document['mass_accounting']['additional_mass']['entries']}
                    self.assertEqual({f['space'] for f in folder['mass_fills']} - spaces, set())
            self.assertIn(template, TEMPLATES)


@unittest.skipUnless(os.environ.get('ATLAS_DOE_IDF_ROOT') and (atlas_delta_release.TARGET/'manifest.json').exists(),
                     'set ATLAS_DOE_IDF_ROOT to the extracted doe-reference/v1.4_7.2 folder')
class DoeFileTests(unittest.TestCase):
    def test_every_program_slot_follows_its_doe_schedule_or_a_register_row(self):
        from scripts import idf_reader, reference_loads
        from scripts.reconciliation_register import zone_program_map
        root = Path(os.environ['ATLAS_DOE_IDF_ROOT'])
        release = Release(atlas_delta_release.files())
        register = load_json(REGISTER)
        kept = {(r['template'], r['building_type'], (r.get('target') or [None])[0]) for r in register['rows']
                if r['decision'] in ('keep', 'leave') and str(r.get('field', '')).count('schedule')}
        base = ReleaseAnswerKeyTests
        base.setUpClass()
        case = base()
        geometry = {(e['template'], e['building_type']): e for e in load_json(ROOT/'data/construction-inputs/geometry-v1.json')['commercial']}
        values = load_json(VALUES)
        for key, folder in values['folders'].items():
            template = key.split('/')[0]
            vintage = 'post1980' if template == 'doe-ref-1980-2004' else 'pre1980'
            idf = next(k for k, v in reference_loads.TYPES.items() if v[1] == key.split('/')[1])
            model = idf_reader.Model(next((root/f'refbldg_{idf}_{vintage}_v1-4_7-2').glob('*5A_USA_IL_CHICAGO-OHARE.idf')))
            days = idf_schedules.calendar_days(model.holidays())
            _, standards_template, geometry_template = reference_loads.VINTAGES[vintage]
            rows = reference_loads.compare_type(model, folder['building_type'], key.split('/')[1], template, {},
                                                geometry[(geometry_template, folder['building_type'])])
            choices, _ = reference_extras.slot_choices(model, zone_program_map(rows, folder['building_type']),
                                                       reference_extras.zone_floors(model))
            for base_id, slots in choices.items():
                program = case.now(base_id)
                for slot, name in slots.items():
                    stored = case.slot(program, slot)
                    if not isinstance(stored, str) or (template, folder['building_type'], base_id) in kept:
                        continue
                    expected, _ = idf_schedules.evaluate_compact(model.schedules()[name.lower()], days)
                    got = idf_schedules.evaluate_ruleset(release.suite(release.programs[program['id']][0]).schedule(stored)['rules'], profile, days)
                    with self.subTest(program=program['id'], slot=slot):
                        self.assertEqual([k for k in days if not idf_schedules.same(expected[k], got[k])], [])


if __name__ == '__main__':
    unittest.main()
