"""Release 2.1.0: a delta on the 2.0.0 snapshot (ADR 0046 section 12) carrying the open licence and the generator 3.0.0 recipes.

Since ADR 0051 the delta is verify-only: the packaged recipes it pinned left the tree with generator 4.0.0, and
release 2.2.0 carries the same apartment units as `resstock_unit` generation blocks."""
import json
import unittest

from jsonschema import Draft202012Validator

from atlas_schedules.release import Release
from scripts import atlas_delta, atlas_snapshot
from scripts.common import ROOT, load_json

FOLDER = atlas_delta.folder_of('2.1.0')
APARTMENT_FOLDERS = ('90-1-2007/highrise-apartment', '90-1-2007/midrise-apartment', '90-1-2013/highrise-apartment',
                     '90-1-2013/midrise-apartment', '90-1-2019/highrise-apartment', '90-1-2019/midrise-apartment',
                     'doe-ref-1980-2004/midrise-apartment', 'doe-ref-pre-1980/midrise-apartment')
VIEW = {'source': 'source', 'reviewed': 'filled'}


class DeltaTests(unittest.TestCase):
    """The folder alone: cheap checks that need no resolved release."""

    @classmethod
    def setUpClass(cls):
        cls.listed = atlas_delta.verify('2.1.0')

    def test_delta_on_2_0_0_released_with_its_generator_named(self):
        listed = self.listed
        self.assertEqual((listed['release'], listed['status'], listed['base_release']['release']), ('2.1.0', 'released', '2.0.0'))
        self.assertEqual(listed['base_release']['manifest_sha256'], atlas_delta.sha((atlas_snapshot.TARGET/'manifest.json').read_bytes()))
        self.assertEqual(listed['removed'], [])
        self.assertEqual(sorted(listed['files']), sorted(['LICENSE', 'README.md', *(f'commercial/{f}/generator.json' for f in APARTMENT_FOLDERS)]))
        generator = listed['generator']
        self.assertEqual(generator, atlas_delta.GENERATOR['2.1.0'])
        self.assertEqual((generator['version'], generator['wheel'], generator['release_tag']),
                         ('3.0.0', 'atlas_schedules-3.0.0-py3-none-any.whl', 'atlas-schedules-v3.0.0'))
        self.assertIn('docs/adr/0049-atlas-schedules-packaging.md', listed['decision'])
        self.assertEqual(listed['counts'], json.loads((atlas_snapshot.TARGET/'manifest.json').read_bytes())['counts'])
        self.assertTrue(any('ADR 0051' in note for note in listed['edited_by']))

    def test_pinned_inputs_verify(self):
        self.assertEqual(sorted(self.listed['input_sha256']), ['LICENSE', 'data/atlas-releases/v2.0.0/manifest.json'])
        for path, digest in self.listed['input_sha256'].items():
            with self.subTest(input=path):
                self.assertEqual(atlas_delta.sha((ROOT/path).read_bytes()), digest)

    def test_license_is_the_open_licence_text(self):
        text = (FOLDER/'LICENSE').read_bytes()
        self.assertEqual(text, (ROOT/'LICENSE').read_bytes())
        self.assertIn(b'MIT', text)
        self.assertIn(b'CC BY 4.0', text)
        self.assertNotEqual(text, (atlas_snapshot.TARGET/'LICENSE').read_bytes())

    def test_apartment_units_are_the_resstock_units_release_2_2_0_carries(self):
        later = Release(atlas_delta.folder_of('2.2.0'))
        units = 0
        for folder in APARTMENT_FOLDERS:
            delta = load_json(FOLDER/f'commercial/{folder}/generator.json')
            base = load_json(atlas_snapshot.TARGET/f'commercial/{folder}/generator.json')
            self.assertEqual(sorted(delta), sorted(base), folder)
            blocks = later.generation(f'commercial/{folder}')['programs']
            for key, views in delta.items():
                self.assertEqual(sorted(views), sorted(base[key]))
                for view, recipe in views.items():
                    if recipe['kind'] == 'apartment_unit':
                        units += 1
                        self.assertIn('resstock_unit', recipe)
                        self.assertNotIn('slots', recipe)
                        self.assertEqual(base[key][view]['kind'], 'apartment_unit')
                        block = blocks[key]['views'][VIEW[view]]['resstock_unit']
                        strip = lambda unit: {k: v for k, v in unit.items() if k != 'source'}
                        self.assertEqual(strip(recipe['resstock_unit']), strip(block), (key, view))
                        self.assertEqual(recipe['resstock_unit']['source']['hot_water']['density'], block['source']['hot_water']['density'])
                    else:
                        self.assertEqual(recipe, base[key][view])
        self.assertEqual(units, 38)

    def test_schemas_admit_the_release(self):
        for name in ('program-json-v5.1.schema.json', 'program-json-v5.2.schema.json',
                     'building-services-v1.schema.json', 'construction-source-model-v1.schema.json'):
            self.assertIn('atlas-release-2.1.0', (ROOT/'schemas'/name).read_text(encoding='utf-8'), name)


class ResolvedTests(unittest.TestCase):
    """The resolved release: 2.0.0 with the delta laid over, exported for consumers."""

    @classmethod
    def setUpClass(cls):
        cls.base = atlas_snapshot.files()
        cls.files = atlas_delta.files('2.1.0')

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.base, cls.files

    def test_every_other_file_is_2_0_0(self):
        listed = atlas_delta.verify('2.1.0')
        self.assertEqual(set(self.files), set(self.base))
        changed = {p for p in self.files if self.files[p] != self.base[p]}
        self.assertEqual(changed, set(listed['files']))

    def test_exports_name_the_release_and_validate(self):
        from scripts.atlas_exports import IN_TREE, LIGHTING, Release as Exports
        self.assertIn('2.1.0', IN_TREE)
        release = Exports(files=self.files, release='2.1.0')
        program_id = next(p for p in release.program_ids() if p.startswith('90-1-2019.midrise-apartment.source.'))
        document = release.program(program_id, 'filled')
        self.assertEqual((document['schema_version'], document['source']['release']), ('5.4.0', 'atlas-release-2.1.0'))
        Draft202012Validator(load_json(ROOT/'schemas'/LIGHTING['program'][0])).validate(document)


if __name__ == '__main__':
    unittest.main()
