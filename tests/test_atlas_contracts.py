"""The 2.3.0 export contracts' tables and schemas (ADR 0054): the null meanings, the vocabulary mapping, the versions."""
import json
import re
import unittest

from scripts import atlas_contracts, atlas_delta
from scripts.atlas_exports import derived_schemas
from scripts.common import ROOT, load_json

GUIDE = ROOT/'website/content/guides/program-json.md'
VOCABULARY = ROOT/'schemas/vocabulary-v1.json'


class NullTableTests(unittest.TestCase):
    def test_the_guide_prints_the_exporter_table(self):
        text = GUIDE.read_text(encoding='utf-8')
        table = text.split('<!-- nulls-table:start -->\n', 1)[1].split('\n<!-- nulls-table:end -->', 1)[0]
        self.assertEqual(table, atlas_contracts.guide_table())

    def test_rows_are_well_formed(self):
        for pattern, status, source, text in atlas_contracts.NULLS:
            self.assertTrue(pattern.startswith('/'), pattern)
            self.assertIn(status, ('unknown', 'none', 'not_applicable'))
            self.assertIn(source, (None, 'record'))
            self.assertTrue(text.endswith('.'), text)

    def test_meanings_match_by_segment(self):
        self.assertEqual(atlas_contracts.meaning('/loads/3/value')[0], 'unknown')
        self.assertEqual(atlas_contracts.meaning('/loads/3/host_zone')[0], 'none')
        self.assertEqual(atlas_contracts.meaning('/fenestration/wwr/N')[0], 'not_applicable')
        self.assertEqual(atlas_contracts.meaning('/lighting_controls/daylighting')[0], 'none')
        self.assertIsNone(atlas_contracts.meaning('/name'))


class VersionTests(unittest.TestCase):
    def test_new_majors_are_derived_and_committed(self):
        derived = derived_schemas()
        for name, version, identity in (atlas_contracts.PROGRAM, atlas_contracts.DETAILED, atlas_contracts.UNIFIED,
                                        atlas_contracts.SOURCE_MODEL):
            with self.subTest(schema=name):
                schema = load_json(ROOT/'schemas'/name)
                self.assertEqual(schema, derived[name])
                self.assertEqual(schema['$id'], identity)
                text = json.dumps(schema)
                self.assertIn(f'"const": "{version}"', text)

    def test_program_6_requires_status_nulls_and_shared_evidence(self):
        schema = load_json(ROOT/'schemas'/atlas_contracts.PROGRAM[0])
        for version in ('source', 'filled'):
            variant = schema['$defs'][version]
            self.assertIn('nulls', variant['required'])
            self.assertIn('status', variant['$defs']['load']['required'])
            self.assertEqual(variant['$defs']['evidence']['required'][:2], ['id', 'source_project'])
            self.assertEqual(variant['properties']['source']['properties']['release'], atlas_contracts.RELEASE_LABEL)

    def test_construction_majors_name_the_release(self):
        detailed = load_json(ROOT/'schemas'/atlas_contracts.DETAILED[0])
        unified = load_json(ROOT/'schemas'/atlas_contracts.UNIFIED[0])
        for schema in (detailed, unified):
            self.assertIn('release', schema['required'])
            self.assertNotIn('export_mode', schema['properties'])
        self.assertIn('construction_definition_release', detailed['$defs']['source']['properties'])
        self.assertNotIn('definition_release', detailed['$defs']['source']['properties'])
        self.assertEqual(unified['properties']['provenance']['required'], ['construction_delivery_release'])


class VocabularyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = load_json(VOCABULARY)
        cls.files = atlas_delta.files(atlas_delta.RELEASE)

    @classmethod
    def tearDownClass(cls):
        del cls.files

    def spellings(self, layer):
        return {s for row in self.table['units'] for s in row[layer]}

    def test_every_record_unit_is_mapped(self):
        seen = set()
        for path, data in self.files.items():
            if path.endswith('/schedules.json'):
                seen |= {s.get('units') for s in json.loads(data)['schedules'].values()}
            elif '/programs/' in path and path.startswith('commercial/'):
                record = json.loads(data)
                for load in record['loads']:
                    seen.add(load.get('unit'))
                    seen |= {e.get('unit') for e in (load.get('thermal_effects') or {}).values() if isinstance(e, dict)}
                seen |= {p.get('unit') for p in record['parameters'].values() if isinstance(p, dict) and 'unit' in p}
        self.assertEqual(seen - {None} - self.spellings('records'), set())

    def test_every_generation_unit_is_mapped(self):
        seen = set()
        for path, data in self.files.items():
            if path.endswith('/generation.json'):
                seen |= set(re.findall(r'"\w*unit":"([^"]*)"', data.decode('utf-8')))
        self.assertTrue(seen)
        self.assertEqual(seen - self.spellings('generation'), set())

    def test_every_export_schedule_unit_is_mapped(self):
        schema = load_json(ROOT/'schemas'/atlas_contracts.PROGRAM[0])
        units = set()
        for variant in schema['$defs'].values():
            for definition in variant['$defs'].values():
                unit = definition.get('properties', {}).get('unit', {})
                units |= set(unit.get('enum', []))
        self.assertTrue(units)
        self.assertEqual(units - self.spellings('exports'), set())

    def test_climate_zone_forms_and_conversions(self):
        forms = {f['example']: re.compile(f['pattern']) for f in self.table['climate_zones']['forms']}
        for example, pattern in forms.items():
            self.assertRegex(example, pattern)
        self.assertRegex('8B', forms['4A'])
        self.assertNotRegex('4-a', forms['4A'])
        for row in self.table['climate_zones']['conversions']:
            self.assertTrue(row['rule'])


if __name__ == '__main__':
    unittest.main()
