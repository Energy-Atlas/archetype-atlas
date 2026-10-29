"""Release 2.1.0: a delta on the 2.0.0 snapshot (ADR 0046 section 12) carrying the open licence and the generator 3.0.0 recipes."""
import json
import re
import unittest

from jsonschema import Draft202012Validator

import atlas_schedules
from scripts import atlas_delta, atlas_snapshot
from scripts.common import ROOT, load_json

APARTMENT_FOLDERS = ('90-1-2007/highrise-apartment', '90-1-2007/midrise-apartment', '90-1-2013/highrise-apartment',
                     '90-1-2013/midrise-apartment', '90-1-2019/highrise-apartment', '90-1-2019/midrise-apartment',
                     'doe-ref-1980-2004/midrise-apartment', 'doe-ref-pre-1980/midrise-apartment')


class DeltaTests(unittest.TestCase):
    """The folder alone: cheap checks that need no resolved release."""

    @classmethod
    def setUpClass(cls):
        cls.listed = atlas_delta.verify()

    def test_delta_on_2_0_0_released_with_its_generator_named(self):
        listed = self.listed
        self.assertEqual((listed['release'], listed['status'], listed['base_release']['release']), ('2.1.0', 'released', '2.0.0'))
        self.assertEqual(listed['base_release']['manifest_sha256'], atlas_delta.sha((atlas_snapshot.TARGET/'manifest.json').read_bytes()))
        self.assertEqual(listed['removed'], [])
        self.assertEqual(sorted(listed['files']), sorted(['LICENSE', 'README.md', *(f'commercial/{f}/generator.json' for f in APARTMENT_FOLDERS)]))
        generator = listed['generator']
        self.assertEqual(generator['version'], atlas_schedules.__version__)
        self.assertEqual(generator['package'], 'atlas-schedules')
        self.assertEqual(generator['wheel'], f'atlas_schedules-{atlas_schedules.__version__}-py3-none-any.whl')
        self.assertEqual(generator['release_tag'], f'atlas-schedules-v{atlas_schedules.__version__}')
        self.assertEqual(generator['recipes_sha256'], atlas_delta.tree_sha(atlas_delta.RECIPES))
        self.assertIn('docs/adr/0049-atlas-schedules-packaging.md', listed['decision'])
        self.assertEqual(listed['counts'], json.loads((atlas_snapshot.TARGET/'manifest.json').read_bytes())['counts'])

    def test_pinned_inputs_verify(self):
        for path, digest in self.listed['input_sha256'].items():
            with self.subTest(input=path):
                p = ROOT/path
                self.assertEqual(atlas_delta.tree_sha(p) if p.is_dir() else atlas_delta.sha(p.read_bytes()), digest)

    def test_license_is_the_open_licence_text(self):
        text = (atlas_delta.TARGET/'LICENSE').read_bytes()
        self.assertEqual(text, (ROOT/'LICENSE').read_bytes())
        self.assertIn(b'MIT', text)
        self.assertIn(b'CC BY 4.0', text)
        self.assertNotEqual(text, (atlas_snapshot.TARGET/'LICENSE').read_bytes())

    def test_apartment_units_are_the_packaged_resstock_recipes(self):
        for folder in APARTMENT_FOLDERS:
            delta = load_json(atlas_delta.TARGET/f'commercial/{folder}/generator.json')
            base = load_json(atlas_snapshot.TARGET/f'commercial/{folder}/generator.json')
            self.assertEqual(sorted(delta), sorted(base), folder)
            units = 0
            for key, views in delta.items():
                self.assertEqual(sorted(views), sorted(base[key]))
                for view, recipe in views.items():
                    if recipe['kind'] == 'apartment_unit':
                        units += 1
                        self.assertIn('resstock_unit', recipe)
                        self.assertNotIn('slots', recipe)
                        self.assertEqual(recipe, load_json(atlas_delta.RECIPES/f"{recipe['program_id']}.json"))
                        self.assertEqual(base[key][view]['kind'], 'apartment_unit')
                    else:
                        self.assertEqual(recipe, base[key][view])
            self.assertEqual(units, 1 if folder.startswith('doe-ref') else 6, folder)

    def test_schemas_admit_the_release(self):
        for name in ('program-json-v5.1.schema.json', 'program-json-v5.2.schema.json', 'program-json-v5.4.schema.json',
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
        listed = atlas_delta.verify()
        self.assertEqual(set(self.files), set(self.base))
        changed = {p for p in self.files if self.files[p] != self.base[p]}
        self.assertEqual(changed, set(listed['files']))

    def test_exports_name_the_release_and_validate(self):
        from scripts.atlas_exports import LIGHTING, Release, ALTERNATES
        release = Release(files=self.files, release='2.1.0')
        program_id = next(p for p in release.program_ids() if p.startswith('90-1-2019.midrise-apartment.source.'))
        document = release.program(program_id, 'filled')
        self.assertEqual((document['schema_version'], document['source']['release']), ('5.4.0', 'atlas-release-2.1.0'))
        Draft202012Validator(load_json(ROOT/'schemas'/LIGHTING['program'][0])).validate(document)
        sid = next(s for s in sorted(release.constructions.sets) if s.startswith('90-1-2019.midrise-apartment.'))
        key = sorted(release.constructions.sets[sid]['contexts'])[0]
        construction = release.construction(sid, key, 'detailed')
        self.assertEqual(construction['schema_version'], ALTERNATES['detailed'][1])
        Draft202012Validator(load_json(ROOT/'schemas'/ALTERNATES['detailed'][0])).validate(construction)

    def test_default_release_is_the_newest_in_the_tree(self):
        from scripts import site_release
        from scripts.atlas_exports import IN_TREE, Release
        self.assertEqual(site_release.newest(), '2.1.0')
        self.assertEqual(IN_TREE[-1], '2.1.0')
        self.assertEqual(Release.__init__.__defaults__[-1], '2.1.0')
        self.assertRegex(self.files['README.md'].decode('utf-8'), re.compile(r'release 2\.1\.0'))


if __name__ == '__main__':
    unittest.main()
