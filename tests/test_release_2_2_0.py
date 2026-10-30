"""Release 2.2.0: the generation parameters with the programs, a delta on 2.1.0 (ADR 0051)."""
import json
import re
import unittest

from jsonschema import Draft202012Validator

import atlas_schedules
from atlas_schedules import programmes
from atlas_schedules.release import Release, current
from scripts import atlas_delta
from scripts.common import ROOT, load_json

FOLDER = atlas_delta.folder_of('2.2.0')
BASE = atlas_delta.folder_of('2.1.0')
CLASSROOM = '90-1-2019.primary-school.source.classroom.6fac9d'


class DeltaTests(unittest.TestCase):
    """The folder alone: cheap checks that need no resolved release."""

    @classmethod
    def setUpClass(cls):
        cls.listed = atlas_delta.verify('2.2.0')
        cls.release = Release(FOLDER)

    @classmethod
    def tearDownClass(cls):
        del cls.listed, cls.release

    def test_delta_on_the_recorded_2_1_0(self):
        listed = self.listed
        self.assertEqual((listed['release'], listed['status'], listed['base_release']['release']), ('2.2.0', 'released', '2.1.0'))
        self.assertEqual(listed['base_release']['manifest_sha256'], atlas_delta.sha((BASE/'manifest.json').read_bytes()))
        self.assertEqual(self.release.base.manifest_sha256, listed['base_release']['manifest_sha256'])
        self.assertEqual(listed['generation'], {'schema_version': '1.0.0'})
        self.assertIn('docs/adr/0051-generation-parameters-in-the-release.md', listed['decision'])
        self.assertEqual(atlas_delta.RELEASE, '2.2.0')

    def test_generator_json_removed_and_only_generation_files_added(self):
        base = self.release.base
        generator_json = sorted(p for p in base.paths if p.endswith('/generator.json'))
        self.assertEqual(self.listed['removed'], generator_json)
        self.assertEqual(len(generator_json), 83)
        self.assertEqual(set(self.listed['files']) & set(base.paths), {'README.md', 'LICENSE'})
        self.assertTrue(all(p.endswith(('/generation.json', 'definition-map.json', 'README.md', 'LICENSE')) for p in self.listed['files']))
        self.assertEqual(sum(p.endswith('/generation.json') for p in self.listed['files']), 90)
        self.assertFalse(any(p.endswith('/generator.json') for p in self.release.paths))

    def test_generator_named_and_pinned_inputs_verify(self):
        generator = self.listed['generator']
        self.assertEqual(generator['version'], atlas_schedules.__version__)
        self.assertEqual((generator['package'], generator['request_schema_version']), ('atlas-schedules', atlas_schedules.REQUEST_SCHEMA_VERSION))
        self.assertEqual(generator['release_tag'], f'atlas-schedules-v{atlas_schedules.__version__}')
        for path, digest in self.listed['input_sha256'].items():
            with self.subTest(input=path):
                self.assertEqual(atlas_delta.sha((ROOT/path).read_bytes()), digest)
        self.assertIn('scripts/atlas_delta.py', self.listed['input_sha256'])

    def test_counts(self):
        counts = self.listed['counts']['generation']
        self.assertEqual(counts['methods'], {'composition': 191, 'comstock_hours': 734, 'fixed': 22,
                                             'resstock_dwelling': 41, 'resstock_unit': 20})
        self.assertEqual((counts['generation_folders'], counts['programs_with_generation'], counts['program_views'],
                          counts['services_with_generation'], counts['configurations']), (90, 1008, 1585, 186, 120))
        self.assertEqual((counts['definition_programs'], counts['definition_services'], counts['retired_definition_programs']), (1216, 150, 12))
        self.assertNotIn('programs_with_recipes', self.listed['counts'])
        self.assertEqual(self.listed['counts']['programs'], 2978)

    def test_programs_read_with_their_blocks_and_keep_their_records(self):
        folder, record = self.release.program(CLASSROOM)
        self.assertEqual(folder, 'commercial/90-1-2019/primary-school')
        self.assertEqual(record['generation']['method'], 'comstock_hours')
        self.assertEqual(record['generation']['views']['filled'], {'configuration_id': 'primary_school__90_1_2019__reviewed'})
        _, base = self.release.base.program(CLASSROOM)
        self.assertEqual({k: v for k, v in record.items() if k != 'generation'}, base)

    def test_definition_map(self):
        mapped = self.release.json('definition-map.json')
        self.assertEqual((len(mapped['programs']), len(mapped['services']), len(mapped['retired'])), (1216, 150, 12))
        entry = mapped['programs']['program-098127c144bbfd68cea77c6b']
        self.assertEqual(entry, {'program_id': CLASSROOM, 'values': 'filled'})
        recipe = programmes.assemble(self.release, entry['program_id'], entry['values'])
        self.assertEqual(recipe['commercial']['configuration_id'], 'primary_school__90_1_2019__reviewed')
        self.assertEqual(mapped['services']['service-7430007e80203f78a1297cc6'], '90-1-2013.medium-office.main.87f1fd')

    def test_every_view_assembles(self):
        self.assertEqual(atlas_delta.assembles('2.2.0'), 1585)

    def test_the_generator_reads_it_from_the_tree(self):
        reader = current()
        self.assertEqual((reader.version, reader.manifest_sha256), ('2.2.0', self.release.manifest_sha256))
        self.assertEqual(reader.provenance(), {'version': '2.2.0', 'manifest_sha256': self.release.manifest_sha256,
                                               'generation_schema_version': '1.0.0'})

    def test_schemas_admit_the_release(self):
        for name in ('program-json-v5.1.schema.json', 'program-json-v5.2.schema.json', 'building-services-v1.schema.json',
                     'construction-source-model-v1.schema.json'):
            self.assertIn('atlas-release-2.2.0', (ROOT/'schemas'/name).read_text(encoding='utf-8'), name)
        schema = load_json(ROOT/'schemas/program-json-v5.4.schema.json')
        for version in ('source', 'filled'):
            label = schema['$defs'][version]['properties']['source']['properties']['release']
            self.assertEqual(label, {'type': 'string', 'pattern': r'^atlas-release-\d+\.\d+\.\d+$'})
            for release in ('1.5.0', '1.6.0', '2.0.0', '2.1.0', '2.2.0', '2.3.0'):
                self.assertRegex(f'atlas-release-{release}', label['pattern'])
            self.assertNotRegex('atlas-release-2.2', label['pattern'])


class ResolvedTests(unittest.TestCase):
    """The resolved release: 2.0.0 with both deltas laid over, exported for consumers."""

    @classmethod
    def setUpClass(cls):
        cls.base = atlas_delta.files('2.1.0')
        cls.files = atlas_delta.files('2.2.0')

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.base, cls.files

    def test_every_other_file_is_2_1_0(self):
        listed = atlas_delta.verify('2.2.0')
        self.assertEqual(set(self.base) - set(self.files), set(listed['removed']))
        self.assertEqual(set(self.files) - set(self.base), set(listed['files']) - {'README.md', 'LICENSE'})
        changed = {p for p in self.files if p in self.base and self.files[p] != self.base[p]}
        self.assertEqual(changed, {'README.md'})
        self.assertEqual(self.files['LICENSE'], (ROOT/'LICENSE').read_bytes())

    def test_exports_name_the_release_and_validate(self):
        from scripts.atlas_exports import LIGHTING, Release as Exports, ALTERNATES
        release = Exports(files=self.files, release='2.2.0')
        program_id = next(p for p in release.program_ids() if p.startswith('90-1-2019.midrise-apartment.source.'))
        document = release.program(program_id, 'filled')
        self.assertEqual((document['schema_version'], document['source']['release']), ('5.4.0', 'atlas-release-2.2.0'))
        self.assertNotIn('generation', document)
        Draft202012Validator(load_json(ROOT/'schemas'/LIGHTING['program'][0])).validate(document)
        sid = next(s for s in sorted(release.constructions.sets) if s.startswith('90-1-2019.midrise-apartment.'))
        key = sorted(release.constructions.sets[sid]['contexts'])[0]
        construction = release.construction(sid, key, 'detailed')
        self.assertEqual(construction['schema_version'], ALTERNATES['detailed'][1])
        Draft202012Validator(load_json(ROOT/'schemas'/ALTERNATES['detailed'][0])).validate(construction)

    def test_default_release_is_the_newest_in_the_tree(self):
        from scripts import site_release
        from scripts.atlas_exports import IN_TREE, Release as Exports
        self.assertEqual(site_release.newest(), '2.2.0')
        self.assertEqual(IN_TREE[-1], '2.2.0')
        self.assertEqual(Exports.__init__.__defaults__[-1], '2.2.0')
        self.assertRegex(self.files['README.md'].decode('utf-8'), re.compile(r'release 2\.2\.0'))
        self.assertEqual(json.loads(self.files['definition-map.json'])['schema_version'], '1.0.0')


if __name__ == '__main__':
    unittest.main()
