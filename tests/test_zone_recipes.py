"""Generation blocks of the IECC commercial and detailed office folders (ADR 0055, scripts.build_zone_recipes).

The People of a building configuration (what ComStock infers the hours of operation from) are checked
against answer keys at the ADR 0035 tolerance:
- the rule the detailed offices use (prototype geometry spaces x program density) reproduces every
  90.1 source configuration of the plain types from the same geometry file; those configurations carry
  the native openstudio-standards People (tests/schedules/test_residential_dominance_native.py);
- the IECC configurations agree with the People objects of the PNNL IDFs
  (tests/answer_keys/commercial/iecc-people.json, scripts/capture/iecc_people.py): total design people
  with multipliers per group within 1e-6, and the rule-day inversion exactly.
Every block validates, assembles and, for a sample, generates a bundle that validates.
"""
from collections import defaultdict
import json
from pathlib import Path
import unittest

import jsonschema

from atlas_schedules import generator, programmes
from atlas_schedules.programmes import SAMPLING, known_positive, load_of
from atlas_schedules.release import Release
from scripts import atlas_delta, build_zone_recipes as z, generation_coverage
from scripts.build_apartment_units import geometries
from scripts.build_reference_recipes import residential
from tests.schedules.helpers import bundle_errors

ROOT = Path(__file__).resolve().parents[1]
KEY = ROOT/'tests/answer_keys/commercial/iecc-people.json'
TOLERANCE = 1e-6
SLUGS = {'90.1-2007': '90-1-2007', '90.1-2013': '90-1-2013', '90.1-2019': '90-1-2019'}
SAMPLE = ('iecc-2021.medium-office.source.whole-building-md-office.986e31',
          '90-1-2019.large-office-detailed.source.open-office.458da9')


def schema(name):
    return jsonschema.Draft202012Validator(json.loads((ROOT/'atlas_schedules/schemas'/name).read_text(encoding='utf-8')))


class ZoneRecipes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = Release(atlas_delta.folder_of('2.2.0'))
        cls.docs = z.build(cls.release)
        cls.reader = z.with_documents(cls.release, cls.docs)

    @classmethod
    def tearDownClass(cls):
        del cls.release, cls.docs, cls.reader

    def test_folders_and_blocks(self):
        iecc = [f for f in self.docs if '/iecc-' in f]
        detailed = [f for f in self.docs if f.endswith('-office-detailed')]
        self.assertEqual((len(iecc), len(detailed)), (84, 15))   # 14 sampled types x 6 editions; 3 offices x 5 templates
        for folder, doc in self.docs.items():
            with self.subTest(folder=folder):
                self.assertEqual(set(doc['programs']), set(z.folder_programs(self.release, folder)))
                for block in doc['programs'].values():
                    self.assertEqual(list(block['views']), ['source'])   # IECC is source only; the fillings add no slot
                self.assertEqual(len(doc['configurations']), 1)

    def test_documents_validate_and_configurations_are_unique(self):
        check = schema('generation-v1.schema.json')
        for folder, doc in self.docs.items():
            self.assertEqual(list(check.iter_errors(doc)), [], folder)
        ids = [cid for doc in self.docs.values() for cid in doc['configurations']]
        ids += [cid for f in self.release.generation_folders() for cid in self.release.generation(f).get('configurations', {})]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_block_assembles(self):
        self.assertEqual(z.gate(self.release, self.docs), 1262)

    def test_detailed_offices_sample_their_plain_type(self):
        for folder, doc in self.docs.items():
            if folder.endswith('-office-detailed'):
                (cid, configuration), = doc['configurations'].items()
                plain = folder.split('/')[2].removesuffix('-detailed').replace('-', '_')
                self.assertEqual(configuration['building_type'], plain)
                self.assertTrue(cid.startswith(plain + '_detailed__'))

    def test_geometry_rule_reproduces_the_native_90_1_configurations(self):
        folders = {(f.split('/')[1], b): f for f, (_, _, b) in generation_coverage.folders(self.release).items()}
        checked = 0
        for (template, building_type), geometry in sorted(geometries().items()):
            if template not in SLUGS or building_type not in SAMPLING or building_type in z.DETAILED:
                continue
            programs = z.folder_programs(self.release, folders[(SLUGS[template], building_type)])
            people, invert = z.occupancy_carrier(z.geometry_zones(programs, geometry, building_type, 'source'))
            cid = z.configuration_name(building_type, template, 'source')
            native = self.release.configurations[cid][1]
            with self.subTest(configuration=cid):
                self.assertEqual(invert, native['invert_rule_days'])
                self.assertEqual([s for s, _ in people], [s for s, _ in native['people']])
                for (_, mine), (_, theirs) in zip(people, native['people']):
                    self.assertAlmostEqual(mine, theirs, delta=TOLERANCE * max(1.0, theirs))
            checked += 1
        self.assertEqual(checked, 45)   # 15 types x 3 editions

    def test_iecc_people_match_the_pnnl_idfs(self):
        key = json.loads(KEY.read_text(encoding='utf-8'))['cases']
        self.assertEqual(len(key), 84)
        for folder in z.iecc_folders(self.release):
            programs = z.folder_programs(self.release, folder)
            first = next(iter(programs.values()))
            case = key[f"{first['template']}/{first['building_type']}"]
            mine, theirs = defaultdict(float), defaultdict(float)
            for _, multiplier, floor, [(program, _)] in z.iecc_zones(programs, 'source'):
                occupancy = load_of(program, 'occupancy')
                if known_positive(occupancy):
                    mine[residential(program['name'].rsplit('_', 1)[0])] += floor * occupancy['value'] * multiplier
            for row in case['zones']:
                theirs[row['residential']] += row['design_people'] * row['multiplier']
            (configuration,) = self.docs[folder]['configurations'].values()
            with self.subTest(folder=folder):
                for group in (True, False):
                    self.assertAlmostEqual(mine[group], theirs[group], delta=TOLERANCE * max(1.0, theirs[group]))
                self.assertEqual(configuration['invert_rule_days'], theirs[True] > theirs[False])
                areas = {row['zone']: row['floor_area_m2'] for row in case['zones']}
                for zone, _, floor, _ in z.iecc_zones(programs, 'source'):
                    self.assertAlmostEqual(floor, areas[zone], delta=1e-6 * max(1.0, floor))

    def test_sample_bundles_generate_and_validate(self):
        current = programmes.current, generator.current
        programmes.current = generator.current = lambda: self.reader
        try:
            for program_id in SAMPLE:
                recipe = programmes.load_recipe(program_id)
                instances = [{'key': 'zone', 'program_id': program_id, 'extent': {'floor_area': 100}, 'operating_group': 'building',
                              'service_links': {sid: f'water-{n}' for n, sid in enumerate(recipe['required_services'])}}]
                instances += [{'key': f'water-{n}', 'service_id': sid, 'physical_id': f'heater-{n}', 'extent': {'floor_area': 100},
                               'configuration_id': recipe['commercial']['configuration_id'], 'operating_group': 'building'}
                              for n, sid in enumerate(recipe['required_services'])]
                bundle = generator.generate({'schema_version': '4.0.0', 'seed': 7, 'instances': instances})
                with self.subTest(program=program_id):
                    self.assertEqual(bundle_errors(bundle), [])
                    owner = bundle['owners'][0]
                    self.assertEqual(owner['values'], 'source')
                    for load in owner['loads']:
                        values = bundle['schedules'][owner['schedules'][load['slot']]]['values']
                        self.assertAlmostEqual(load['amplitude'] * sum(values), load['annual_total'],
                                               delta=1e-4 * max(1.0, load['annual_total']))
        finally:
            programmes.current, generator.current = current

    def test_coverage_by_folder_class(self):
        groups = generation_coverage.coverage(self.reader)
        self.assertNotIn('unexplained', groups)
        self.assertEqual({k: len(v) for k, v in groups.items()},
                         {'generated': 189, 'no_sampling_type': 36, 'iecc_apartments': 12, 'residential_prototypes': 18})
        self.assertEqual(generation_coverage.unexplained(self.release), sorted(self.docs))   # 2.2.0 lacks exactly these


class KnownAbsence(unittest.TestCase):
    """A known null schedule parameter is a known absence (an IECC plenum's thermostat, ADR 0040 item 9): no slot."""

    def record(self, setpoint):
        known = {'status': 'known', 'value': setpoint, 'unit': 'schedule reference', 'evidence_id': None, 'required_inputs': []}
        return {'id': 'x', 'loads': [{'quantity': 'occupancy', 'status': 'known', 'value': 0.0, 'unit': 'person/m2',
                                      'basis': 'floor_area', 'schedule_id': None}],
                'parameters': {'heating_setpoint_schedule_id': known, 'cooling_setpoint_schedule_id': known}}

    def test_known_null_setpoint_adds_no_slot(self):
        self.assertEqual(programmes.commercial_body(self.record(None))['slots'], [])
        self.assertEqual(programmes.fixed_body(self.record(None))['slots'], [])

    def test_known_schedule_adds_a_thermostat_slot(self):
        body = programmes.commercial_body(self.record('s.htg.000000'))
        self.assertEqual([s['slot'] for s in body['slots']], ['heating_setpoint', 'cooling_setpoint'])
        self.assertEqual(body['modes'], {'cooling_setpoint': 'tstat', 'heating_setpoint': 'tstat'})


if __name__ == '__main__':
    unittest.main()
