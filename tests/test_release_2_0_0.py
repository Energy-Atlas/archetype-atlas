"""Release 2.0.0: the full snapshot of release 1.6.0 (ADR 0046, phase 1)."""
import json
import os
import unittest

from scripts import atlas_minor_release, atlas_snapshot


class EncodingTests(unittest.TestCase):
    def test_indented_json_keeps_its_value(self):
        data = b'{\n  "a": {\n    "b": [1, 2, {"c": null}]\n  }\n}\n'
        out = atlas_snapshot.encode('x.json', data)
        self.assertEqual(json.loads(out), json.loads(data))
        table = b'{\n"k":{"v":1}\n}\n'
        self.assertEqual(atlas_snapshot.encode('t.json', table), table)
        self.assertEqual(atlas_snapshot.encode('README.md', data), data)


@unittest.skipUnless((atlas_snapshot.TARGET/'manifest.json').exists(), 'release 2.0.0 not written')
class Release200Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.listed = atlas_snapshot.verify()
        cls.files = atlas_snapshot.files()

    def test_full_snapshot_with_the_values_of_1_6_0(self):
        self.assertIsNone(self.listed['base_release'])
        self.assertEqual(self.listed['snapshot_of']['release'], '1.6.0')
        source = atlas_minor_release.files('1.6.0')
        for path, data in source.items():
            if path in ('manifest.json', 'README.md'):
                continue
            with self.subTest(path=path):
                self.assertIn(path, self.files)
                if path.endswith('.json'):
                    self.assertEqual(json.loads(self.files[path]), json.loads(data))
                else:
                    self.assertEqual(self.files[path], data)
        extra = set(self.files) - set(source)
        self.assertTrue(all(p.endswith('/generator.json') for p in extra))

    def test_generator_recipes_for_the_90_1_programs(self):
        counts = self.listed['counts']
        self.assertEqual(counts['programs_with_recipes'] + counts['programs_without_recipes'], counts['programs'])
        generators = [p for p in self.files if p.endswith('/generator.json')]
        self.assertTrue(generators)
        self.assertTrue(all(p.split('/')[1].startswith('90-1-') for p in generators))
        recipes = json.loads(self.files[next(p for p in generators if '/90-1-2019/medium-office/' in p)])
        entry = next(iter(recipes.values()))
        self.assertLessEqual(set(entry), {'source', 'reviewed'})
        self.assertIn('slots', entry.get('source') or entry['reviewed'])

    def test_exports(self):
        from scripts.atlas_exports import Release
        release = Release(files=self.files, release='2.0.0')
        program_id = next(p for p in release.program_ids() if p.startswith('90-1-2019.medium-office.source.whole'))
        document = release.program(program_id, 'filled')
        self.assertEqual((document['schema_version'], document['source']['release']), ('5.4.0', 'atlas-release-2.0.0'))


@unittest.skipUnless((atlas_snapshot.TARGET/'manifest.json').exists() and os.environ.get('ATLAS_RELEASE_CHECK'),
                     'set ATLAS_RELEASE_CHECK=1 to rebuild release 2.0.0')
class Release200CheckTests(unittest.TestCase):
    def test_release_reproduces_byte_for_byte(self):
        atlas_snapshot.check()


if __name__ == '__main__':
    unittest.main()
