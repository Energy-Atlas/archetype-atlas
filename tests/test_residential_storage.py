"""ADR 0038 residential storage: the 41 ResStock fixture dwellings migrate unchanged (S12a)."""
import copy
import json
import re
import unittest

from scripts.atlas_format import h6, translate
from scripts.common import ROOT, load_json

ID = re.compile(r'^(?:[a-z_]+(?:-[a-z_]+)*-[0-9a-f]{20,64}|[a-z0-9-]+(?:\.[a-z0-9-]+)+\.[0-9a-f]{6})(?::.*)?$')
LIMIT = 25_000_000


def anonymous(value):
    """A value with every identifier replaced by '#', ID-keyed tables as sorted lists of their records."""
    if isinstance(value, dict):
        if value and all(isinstance(k, str) and ID.match(k) for k in value):
            return sorted((anonymous(v) for v in value.values()), key=lambda v: json.dumps(v, sort_keys=True))
        return {k: anonymous(v) for k, v in value.items()}
    if isinstance(value, list):
        return [anonymous(v) for v in value]
    if isinstance(value, str) and ID.match(value):
        return '#'
    return value


def unlabelled(document):
    """A construction document without its identifiers and climate label."""
    out = anonymous(copy.deepcopy(document))
    if 'climate_zone' in out:
        out['climate_zone'] = None
    if isinstance(out.get('source', {}).get('climate'), dict):
        out['source']['climate']['value'] = None
    return out


class ResStockMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import resstock_dwellings
        from scripts.residential_storage import program_files
        cls.module = resstock_dwellings
        cls.sources = resstock_dwellings.load_sources()
        cls.ids = {}
        cls.files = resstock_dwellings.build(cls.sources, cls.ids)
        cls.programs = program_files(cls.files)
        cls.records = {r['id']: r for r in cls.sources.records}

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.module, cls.sources, cls.ids, cls.files, cls.programs, cls.records

    def stored(self, record):
        return self.programs[self.ids[record['id']]]

    def test_every_dwelling_migrates_once_into_its_building_type_folder(self):
        self.assertEqual(len(self.records), 41)
        self.assertEqual(len(self.programs), 41)
        for record in self.records.values():
            folder, program = self.stored(record)
            self.assertEqual(folder, f'residential/resstock-sdr/{self.module.FOLDERS[record["building_type"]]}/')
            self.assertEqual(program['source_id'], record['source_id'])
            self.assertTrue(program['id'].startswith(folder.split('/')[1]+'.'+folder.split('/')[2]+'.'), program['id'])
            building = re.search(r'source_building_(\d+)', record['name'])[1]
            self.assertTrue(program['id'].split('.')[2].endswith('-b'+building), program['id'])

    def test_definition_values_and_annual_series_are_unchanged(self):
        from scripts.residential_storage import read_annual
        for record in self.records.values():
            folder, program = self.stored(record)
            local = self.ids[record['id']+':schedules']
            expected = {k: v for k, v in record.items() if k not in self.module.RESERVED}
            got = {k: v for k, v in program.items() if k in expected}
            self.assertEqual(got, translate(expected, local), record['id'])
            annual = read_annual(self.files, folder)
            for old, new in local.items():
                source = self.sources.definitions.schedules.get(old) or self.sources.recovery['schedules'][old]
                self.assertEqual(annual[new], {k: v for k, v in source.items() if k != 'id'}, old)

    def test_fillings_move_unchanged(self):
        resolutions = json.loads(self.files['evidence/residential/resstock-sdr/resolutions.json'])
        frozen = {r['id']: r for r in load_json(ROOT/'data/resolution-releases/v0.4.0/resolutions.json')['resolutions']}
        for record in self.records.values():
            _, program = self.stored(record)
            recovered = self.sources.recovery['records'][record['source_id']]
            local = self.ids[record['id']+':schedules']
            filling = program['filling']
            loads = [{k: v for k, v in l.items() if k != 'resolutions'} for l in filling['loads']]
            self.assertEqual(loads, translate(recovered['loads'], local), record['id'])
            for key in ('controls', 'climate', 'vintage', 'unresolved', 'metadata'):
                self.assertEqual(filling[key], recovered[key], key)
            rows = [r for r in frozen.values() if r['record_id'] == record['source_id']]
            self.assertEqual(filling['resolutions'], sorted(r['id'] for r in rows))
            for row in rows:
                self.assertEqual(resolutions[row['id']], {k: v for k, v in row.items() if k != 'id'})
            bases = {r['basis'] for r in rows}
            self.assertEqual(filling['basis'], 'research_assumption' if 'research_assumption' in bases else 'executed_upstream')

    def test_construction_sets_reproduce_the_frozen_documents(self):
        from scripts.atlas_constructions import read_files
        from scripts.construction_foundation_release import export_pair
        suite = read_files(self.files)
        checked = 0
        for record in self.records.values():
            _, program = self.stored(record)
            sid, rows = self.module.construction_rows(self.sources, record)
            stored = suite.sets[program['construction_set_id']]
            self.assertEqual(len(stored['contexts']), 1)
            [key] = stored['contexts']
            frozen = sorted(self.sources.constructions.contexts[sid], key=lambda c: (c['climate_zone'], c['reference_id']))
            pairs = [export_pair(c['detailed_context_id'], release=self.sources.constructions.release) for c in frozen]
            for representation, index in (('detailed', 0), ('unified', 1)):
                document = suite.export(program['construction_set_id'], key, representation)
                self.assertEqual(document, translate(pairs[0][index], self.ids), record['id'])
                for other in pairs[1:]:  # labels 7 and 8: the B context equals the A context but for its label
                    self.assertEqual(unlabelled(other[index]), unlabelled(pairs[0][index]))
                checked += 1
        self.assertEqual(checked, 82)

    def test_files_stay_under_25_mb_and_ids_follow_content(self):
        for path, data in self.files.items():
            self.assertLess(len(data), LIMIT, path)
        for pid, (_, program) in self.programs.items():
            self.assertEqual(pid.rsplit('.', 1)[1], h6({k: v for k, v in program.items() if k != 'id'}), pid)

    def test_rebuild_is_byte_identical(self):
        again = self.module.build(self.sources)
        self.assertEqual(again, self.files)


class ResStockExportTests(unittest.TestCase):
    """Program JSON 5.3.0 of a dwelling equals the frozen exporters' document of its definition record."""

    @classmethod
    def setUpClass(cls):
        from scripts import resstock_dwellings
        from scripts.definition_release import read_bundle
        from scripts.program_json_v3 import ProgramExporter as V3
        from scripts.program_water_heating import ProgramExporter as V4
        from scripts.residential_exports import Dwellings
        cls.ids = {}
        files = resstock_dwellings.build(ids=cls.ids)
        cls.dwellings = Dwellings(files, '1.4.0')
        cls.bundle = read_bundle(ROOT/'data/definition-releases/v0.1.1')
        cls.v3, cls.v4 = V3(cls.bundle), V4(cls.bundle)
        cls.old_schedules = {s['id']: s for s in cls.bundle['schedules']}
        records = [p for p in cls.bundle['programs'] if p['source_family'] == 'existing_stock_source_fixture']
        first = {}
        for record in sorted(records, key=lambda r: r['id']):
            first.setdefault(record['building_type'], record)
        cls.sample = list(first.values())

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.ids, cls.dwellings, cls.bundle, cls.v3, cls.v4, cls.old_schedules, cls.sample

    def normal(self, document):
        out = anonymous({k: v for k, v in document.items() if k not in ('schema_version', 'export_mode', 'version', 'id', 'dwelling')})
        out['source'] = {k: v for k, v in out['source'].items() if k not in ('definition_release', 'evidence_view', 'release')}
        out['source']['evidence'] = sorted(out['source']['evidence'], key=lambda e: json.dumps(e, sort_keys=True))
        out['loads'] = sorted(out['loads'], key=lambda e: json.dumps(e, sort_keys=True))
        aggregation = out.get('metadata', {}).get('aggregation')
        if aggregation:
            for group in aggregation.get('groups', []):
                group['components'] = sorted(group.get('components', []), key=lambda v: json.dumps(v, sort_keys=True))
            aggregation['groups'] = sorted(aggregation.get('groups', []), key=lambda v: json.dumps(v, sort_keys=True))
        for key in ('water_heating',):
            if key in out:
                out[key] = sorted(out[key], key=lambda v: json.dumps(v, sort_keys=True))
        return out

    def test_one_dwelling_per_building_type_exports_as_the_frozen_exporters_do(self):
        from scripts import atlas_exports
        from jsonschema import Draft202012Validator
        validator = Draft202012Validator(load_json(ROOT/'schemas/program-json-v5.3.schema.json'))
        self.assertEqual(len(self.sample), 7)
        for record in self.sample:
            pid = self.ids[record['id']]
            for version in atlas_exports.VERSIONS:
                document = self.dwellings.program(pid, version)
                self.assertEqual(list(validator.iter_errors(document)), [], pid)
                self.assertEqual((document['schema_version'], document['version'], document['id']), ('5.3.0', version, pid))
                self.assertEqual(document['dwelling']['construction_set_id'], self.dwellings.stored(pid)['construction_set_id'])
                expected = self.v3.export(record['id'], 'raw') if version == 'source' else self.v4.export(record['id'])
                self.assertEqual(self.normal(document), self.normal(expected), f'{pid} {version}')
                values = sorted(json.dumps(s.get('values')) for s in document['schedules'].values())
                frozen = sorted(json.dumps(s.get('values')) for s in expected['schedules'].values())
                self.assertEqual(values, frozen, f'{pid} {version} schedule values')


if __name__ == '__main__':
    unittest.main()
