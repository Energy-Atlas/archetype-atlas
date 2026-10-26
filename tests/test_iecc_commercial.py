"""The IECC commercial family (ADR 0040): definition inputs, release 1.3.0 and the PNNL answer keys.

The answer-key tests compare release 1.3.0 with the PNNL IDFs for every type and edition in
Buffalo (5A), Miami (1A) and Fairbanks (8) at the ADR 0035 tolerance (fractions 1e-6). They
read the extracted IDFs from IECC_IDF_ROOT (default: D:/Prototype Building Models/commercial-iecc)
and skip when the IDFs are absent, as in CI.
"""
import json
import math
import os
import unittest
from collections import defaultdict
from pathlib import Path

from scripts import atlas_minor_release, idf_reader, idf_schedules
from scripts.common import ROOT, load_json
from scripts.iecc_commercial_documents import INPUT
from scripts.iecc_commercial_zones import CITIES, EDITIONS, TYPES, Lookup, conflict_candidates, normalize, template

IDF_ROOT = Path(os.environ.get('IECC_IDF_ROOT', 'D:/Prototype Building Models/commercial-iecc'))
SAMPLE = ('Buffalo', 'Miami', 'Fairbanks')
TOLERANCE = 1e-6
RELEASE = atlas_minor_release.target('1.3.0')
QUANTITIES = {'people': 'occupancy', 'lights': 'lighting', 'electricequipment': 'electric_equipment', 'gasequipment': 'gas_equipment'}
SERVICE_SUBCATEGORIES = {'elevatorlift', 'elevatorlightsfan', 'elevators', 'reachinfreezer', 'reachinrefrigerator'}


def close(a, b, tolerance=TOLERANCE):
    return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))


def at(load, climate):
    return load.get('value_by_climate', {}).get(climate, load['value'])


class ZoneTableTests(unittest.TestCase):
    def test_no_zone_name_maps_to_two_space_types(self):
        lookup = Lookup()
        self.assertEqual(len({k for k in lookup.table}), len(lookup.table))
        self.assertEqual({k for k, o in lookup.origin.items() if o == 'alias_conflict'}, set(conflict_candidates()))

    def test_alias_entries_give_reasons(self):
        aliases = load_json(ROOT/'sources/iecc-commercial-zone-aliases.json')
        for entry in [*aliases['conflicts'], *aliases['guesses']]:
            self.assertGreater(len(entry['reason']), 40, entry['zone'])


@unittest.skipUnless(all((ROOT/INPUT.format(e)).exists() for e in EDITIONS), 'IECC definition inputs not generated')
class InputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = {e: load_json(ROOT/INPUT.format(e)) for e in EDITIONS}

    def test_inputs_are_under_25_mb(self):
        for e in EDITIONS:
            self.assertLess((ROOT/INPUT.format(e)).stat().st_size, 25_000_000, e)

    def test_every_type_has_programs_services_and_19_contexts(self):
        for e, d in self.inputs.items():
            types = {p['building_type'] for p in d['programs']}
            self.assertEqual(types, set(TYPES.values()), e)
            for building_type, payload in d['envelope'].items():
                self.assertEqual(sorted(payload['contexts']), sorted(v[1] for v in CITIES.values()), (e, building_type))

    def test_source_values_only(self):
        for e, d in self.inputs.items():
            for p in d['programs']:
                self.assertEqual(p['source_family'], 'iecc_commercial_prototype')
                self.assertNotIn('source_definition_id', p)
                for load in p['loads']:
                    self.assertEqual(load['status'] if 'status' in load else 'known', 'known', (e, p['name']))
                    self.assertIsNotNone(load['value'], (e, p['name'], load['quantity']))

    def test_pnnl_names_are_kept(self):
        names = {v: k for k, v in TYPES.items()}
        for d in self.inputs.values():
            for p in d['programs']:
                if p['derivation'] != 'composed':
                    self.assertEqual(p['pnnl_building_type'], names[p['building_type']])

    def test_climate_variation_is_rare_and_named_by_climate(self):
        labels = {v[1] for v in CITIES.values()}
        for e, d in self.inputs.items():
            for p in d['programs']:
                for load in p['loads']:
                    self.assertLessEqual(set(load.get('value_by_climate', {})), labels)
        varying = {e for e, d in self.inputs.items() for p in d['programs'] for l in p['loads'] if l.get('value_by_climate')}
        self.assertIn('2021', varying)

    def test_every_schedule_conversion_was_checked(self):
        for e, d in self.inputs.items():
            self.assertGreater(d['schedule_checks'], 500, e)


@unittest.skipUnless((RELEASE/'manifest.json').exists(), 'release 1.3.0 not written')
class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.atlas_exports import Release
        cls.release = Release(release='1.3.0')

    def test_release_holds_release_1_2_0(self):
        listed = atlas_minor_release.verify('1.3.0')
        earlier = json.loads((ROOT/'data/atlas-releases/v1.2.0/manifest.json').read_text())
        changed = [p for p, e in earlier['files'].items() if listed['files'].get(p) != e]
        self.assertEqual(sorted(changed), ['README.md', 'evidence/glossary.json'])
        self.assertEqual(listed['deleted'], earlier['deleted'])

    def test_96_folders(self):
        folders = {p.split('/')[1]+'/'+p.split('/')[2] for p in self.release.files if p.startswith('commercial/iecc-')}
        folders = {f for f in folders if not f.endswith('/library')}
        self.assertEqual(len(folders), 96)

    def test_programs_constructions_and_services_export(self):
        for prefix in ('iecc-2021.medium-office.source.', 'iecc-2006.hospital.department.', 'iecc-2015.primary-school.general.'):
            program_id = next(p for p in self.release.program_ids() if p.startswith(prefix))
            document = self.release.program(program_id, 'source')
            self.assertEqual(document['schema_version'], '5.2.0')
            with self.assertRaises(ValueError):
                self.release.program(program_id, 'filled')
        office = self.release.program(next(p for p in self.release.program_ids()
                                           if p.startswith('iecc-2021.medium-office.source.whole-building')), 'source')
        lighting = next(l for l in office['loads'] if l['end_use'] == 'lighting')
        self.assertEqual(set(lighting['value_by_climate']), {'0B', '1B'})
        [path] = [p for p in self.release.files if p.startswith('commercial/iecc-2021/medium-office/constructions/')]
        set_id = json.loads(self.release.files[path])['id']
        detailed = self.release.construction(set_id, '8-a', 'detailed')
        self.assertEqual(detailed['schema_version'], '4.2.0')
        self.assertEqual(detailed['infiltration']['method'], 'source_design_flow')
        self.assertEqual(detailed['source']['source_climate_label'], '8')
        with self.assertRaises(ValueError):
            self.release.construction(set_id, '5-a', 'unified')
        services = self.release.building_services('iecc-2021/medium-office')
        self.assertIn('elevator', {s['end_use'] for s in services['services']})


@unittest.skipUnless(IDF_ROOT.is_dir() and (RELEASE/'manifest.json').exists(), 'PNNL IECC IDFs or release 1.3.0 absent')
class AnswerKeyTests(unittest.TestCase):
    """Release 1.3.0 against the IDFs: program loads and schedules, window ratios, infiltration and envelope."""

    @classmethod
    def setUpClass(cls):
        from scripts.atlas_constructions import read_files
        files = atlas_minor_release.files('1.3.0')
        cls.programs, cls.schedules, cls.constructions = defaultdict(dict), {}, read_files(files)
        cls.sets = {}
        for path, data in files.items():
            if not path.startswith('commercial/iecc-'):
                continue
            folder = '/'.join(path.split('/')[1:3])
            if '/programs/source/' in path:
                p = json.loads(data)
                cls.programs[folder][p['name']] = p
            elif path.endswith('/schedules.json'):
                cls.schedules[folder] = json.loads(data)
            elif '/constructions/' in path:
                cls.sets[folder] = json.loads(data)

    def schedule(self, folder, sid):
        table = self.schedules[folder]
        stored = table['schedules'][sid]
        return [{**{k: v for k, v in r.items() if k != 'day'}, 'values': table['days'][r['day']]} for r in stored['rules']]

    def check_schedule(self, model, name, rules, days):
        compact = model.schedules().get(name.lower())
        if compact is None:
            return
        expected, _ = idf_schedules.evaluate_compact(compact, days)
        got = idf_schedules.evaluate_ruleset(rules, lambda r: r['values'] * (24 // len(r['values'])), days)
        bad = [k for k in days if not idf_schedules.same(expected[k], got[k])]
        self.assertEqual(bad, [], name)

    def test_programs_against_the_idfs(self):
        for pnnl, building_type in TYPES.items():
            for edition in EDITIONS:
                folder = f'iecc-{edition}/' + ''.join('-'+c.lower() if c.isupper() else c for c in building_type).strip('-')
                programs = self.programs[folder]
                for city in SAMPLE:
                    climate = CITIES[city][1]
                    model = idf_reader.Model(IDF_ROOT/f'IECC_{pnnl}'/f'IECC_{pnnl}_STD{edition}_{city}.idf')
                    days = idf_schedules.calendar_days(model.holidays())
                    floors = defaultdict(float)
                    for s in model.surfaces():
                        if s['type'] == 'floor':
                            floors[s['zone'].lower()] += idf_reader.area(s['vertices'])
                    values, names = defaultdict(float), {}
                    for cls, quantity in QUANTITIES.items():
                        for item in model.loads(cls):
                            if item.get('subcategory', '').lower().replace(' ', '') in SERVICE_SUBCATEGORIES:
                                continue
                            a, b, c = item['values']
                            for z in item['zones']:
                                key = quantity
                                if cls == 'lights' and any(t in (item['name']+' '+item['subcategory']).lower() for t in ('plugin', 'allowance', 'display')):
                                    key = 'additional_lighting'
                                v = {'people': (a or 0)/floors[z] if floors[z] else 0, 'people/area': b, 'area/person': 1/c if c else 0,
                                     'lightinglevel': (a or 0)/floors[z], 'equipmentlevel': (a or 0)/floors[z], 'watts/area': b}.get(item['method'])
                                if v is None:
                                    continue  # watts/person: covered by the extractor's own check
                                values[(z, key)] += v
                                names[(z, key)] = item['schedule']
                    for name, program in programs.items():
                        zones = [(z['name'].lower(), z['floor_area_m2']*z['multiplier']) for z in program['source_zones']]
                        area = math.fsum(a for _, a in zones)
                        for load in program['loads']:
                            if load['quantity'] not in ('occupancy', 'lighting', 'additional_lighting', 'electric_equipment', 'gas_equipment'):
                                continue
                            expected = math.fsum(values[(z, load['quantity'])]*a for z, a in zones)/area if area else 0.0
                            expected *= load.get('schedule_peak_scaling', 1.0)  # peak-normalized schedule (agent decision 19)
                            with self.subTest(edition=edition, city=city, program=name, quantity=load['quantity']):
                                self.assertTrue(close(at(load, climate), expected), (at(load, climate), expected))
                            source = next((names[(z, load['quantity'])] for z, _ in zones if (z, load['quantity']) in names), None)
                            if source and at(load, climate) and 'schedule_peak_scaling' not in load and len({names.get((z, load['quantity'])) for z, _ in zones} - {None}) == 1:
                                self.check_schedule(model, source, self.schedule(folder, load['schedule_id']), days)

    def test_window_ratios_infiltration_and_envelope(self):
        from scripts import iecc_commercial_envelope as envelope
        for pnnl, building_type in TYPES.items():
            for edition in EDITIONS:
                folder = f'iecc-{edition}/' + ''.join('-'+c.lower() if c.isupper() else c for c in building_type).strip('-')
                record = self.sets[folder]
                for city in SAMPLE:
                    key = CITIES[city][1][0] + '-' + CITIES[city][1][1].lower()
                    document = self.constructions.export(record['id'], key, 'detailed')
                    model = idf_reader.Model(IDF_ROOT/f'IECC_{pnnl}'/f'IECC_{pnnl}_STD{edition}_{city}.idf')
                    ratios = envelope.window_ratios(model, {}, None)['building']['all']
                    with self.subTest(edition=edition, city=city, type=building_type):
                        self.assertEqual(document['fenestration_defaults']['all'], ratios)
                        rules = document['infiltration']['methods']['source_design_flow']['zone_rules']
                        idf = sorted((i['method'], next(v for v in i['values'] if v is not None and v != 0) if any(i['values']) else 0.0)
                                     for i in model.infiltration())
                        self.assertEqual(sum(len(r['zones']) for r in rules), sum(len(i['zones']) for i in model.infiltration()))
                        rates = sorted({(r['method'], r['value']) for r in rules})
                        self.assertTrue(all(any(m == rm and close(v, rv) for rm, rv in rates) for m, v in idf if v), (idf, rates))
                        walls = {s['construction'].lower() for s in model.surfaces() if s['boundary'] == 'outdoors' and s['type'] == 'wall'}
                        expected = sorted(round(model.layer_resistance(c), 9) for c in walls if model.layer_resistance(c) is not None)
                        got = sorted({round(document['assemblies'][a['assembly_id']]['metrics']['layer_resistance_m2_K_W'], 9)
                                      for a in document['components']['ExteriorWall']['assignments']})
                        self.assertEqual(sorted(set(expected)), got)


if __name__ == '__main__':
    unittest.main()
