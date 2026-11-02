"""Release 2.3.0: the ADR 0053 corrections, the IECC and detailed office generation blocks and the licence split,
a delta on 2.2.0 (ADR 0059)."""
import json
import unittest

from jsonschema import Draft202012Validator

from atlas_schedules.release import Release
from scripts import atlas_delta
from scripts.common import ROOT, load_json

FOLDER = atlas_delta.folder_of('2.3.0')
BASE = atlas_delta.folder_of('2.2.0')
ID_MAP = 'id-map-2.3.0.json'
WHOLE_BUILDING = ('90-1-2019.medium-office.source.whole-building-md-office.36f6a8',
                  '90-1-2019.medium-office.source.whole-building-md-office.d597bd')


class DeltaTests(unittest.TestCase):
    """The folder and its manifest: checks that need no resolved release."""

    @classmethod
    def setUpClass(cls):
        cls.listed = atlas_delta.verify('2.3.0')
        cls.release = Release(FOLDER)
        cls.ids = load_json(FOLDER/ID_MAP)

    @classmethod
    def tearDownClass(cls):
        del cls.listed, cls.release, cls.ids

    def test_newest_release_on_the_recorded_2_2_0(self):
        listed = self.listed
        self.assertEqual((listed['release'], listed['status'], listed['base_release']['release']), ('2.3.0', 'released', '2.2.0'))
        self.assertEqual(listed['base_release']['manifest_sha256'], atlas_delta.sha((BASE/'manifest.json').read_bytes()))
        self.assertEqual(atlas_delta.CHAIN[:3], ('2.1.0', '2.2.0', '2.3.0'))
        self.assertEqual(listed['decision'][0], 'docs/adr/0059-release-2-3-0.md')
        for decision in listed['decision']:
            self.assertTrue((ROOT/decision).is_file(), decision)

    def test_generator_and_pinned_inputs(self):
        generator = self.listed['generator']
        self.assertEqual(generator, atlas_delta.GENERATOR['2.3.0'])
        self.assertEqual((generator['version'], generator['release_tag'], generator['wheel']),
                         ('4.1.0', 'atlas-schedules-v4.1.0', 'atlas_schedules-4.1.0-py3-none-any.whl'))
        self.assertEqual(generator['request_schema_version'], '4.0.0')
        self.assertEqual(sorted(self.listed['input_sha256']),
                         sorted(['LICENSE', 'LICENSE-DATA', 'data/atlas-releases/v2.2.0/manifest.json', 'scripts/atlas_delta.py',
                                 *atlas_delta.EDIT_INPUTS]))
        for path, digest in self.listed['input_sha256'].items():
            with self.subTest(input=path):
                data = atlas_delta.pinned_writer('2.3.0') if path == 'scripts/atlas_delta.py' else (ROOT/path).read_bytes()
                self.assertEqual(atlas_delta.sha(data), digest)

    def test_licences_split(self):
        # Issue #44: the root LICENSE is the MIT text alone, LICENSE-DATA the CC BY 4.0 legal code; both ship.
        code, data = (FOLDER/'LICENSE').read_bytes(), (FOLDER/'LICENSE-DATA').read_bytes()
        self.assertEqual(code, (ROOT/'LICENSE').read_bytes())
        self.assertEqual(data, (ROOT/'LICENSE-DATA').read_bytes())
        self.assertTrue(code.startswith(b'MIT License\n'))
        self.assertNotIn(b'CC BY', code)
        self.assertTrue(data.startswith(b'Creative Commons Attribution 4.0 International Public License\n'))
        self.assertIn(b'Section 8 -- Interpretation.', data)
        self.assertNotEqual(code, (BASE/'LICENSE').read_bytes())

    def test_id_map_and_removed_paths(self):
        ids = self.ids['ids']
        self.assertEqual((self.ids['base_release'], self.ids['release']), ('2.2.0', '2.3.0'))
        self.assertEqual(len(ids), 1562)
        moved = self.listed['counts']['moved_ids']
        self.assertEqual(moved, {'programs': 1550, 'construction_sets': 12, 'id_map': ID_MAP})
        self.assertEqual(sum('.construction-' in old for old in ids), 12)
        removed = set(self.listed['removed'])
        self.assertEqual(len(removed), 1562)
        self.assertEqual({p.rsplit('/', 1)[1][:-5] for p in removed}, set(ids))
        paths = self.release.paths
        self.assertFalse(removed & set(paths))
        self.assertEqual(ids[WHOLE_BUILDING[0]], WHOLE_BUILDING[1])
        self.assertIn(WHOLE_BUILDING[1], self.release.program_paths)
        self.assertNotIn(WHOLE_BUILDING[0], self.release.program_paths)

    def test_generation_of_the_iecc_and_detailed_office_folders(self):
        counts = self.listed['counts']['generation']
        self.assertEqual((counts['generation_folders'], counts['programs_with_generation'], counts['program_views'],
                          counts['services_with_generation'], counts['configurations']), (189, 2270, 2847, 507, 219))
        base = set(Release(BASE).generation_folders())
        new = sorted(set(self.release.generation_folders()) - base)
        self.assertEqual(len(new), 99)
        self.assertEqual(sum('/iecc-' in f for f in new), 84)
        self.assertEqual(sum(f.endswith('-office-detailed') for f in new), 15)
        generation = [d for d in self.listed['deferred'] if d.startswith('generation blocks')]
        self.assertIn('189 of 255 folders', generation[0])

    def test_in_the_tree_under_release_2_4_0(self):
        # Release 2.4.0 is the newest since ADR 0062; 2.3.0 stays in the tree as its base and exports by name.
        from scripts.atlas_exports import IN_TREE
        self.assertEqual(IN_TREE[IN_TREE.index('2.3.0') + 1], '2.4.0')
        self.assertEqual(atlas_delta.base_of('2.4.0'), '2.3.0')
        self.assertIn('release 2.3.0', (FOLDER/'README.md').read_text(encoding='utf-8'))


class ExportTests(unittest.TestCase):
    """The resolved release exported in the 2.3.0 contracts (ADR 0054)."""

    @classmethod
    def setUpClass(cls):
        from scripts.atlas_exports import Release as Exports
        cls.exports = Exports(release='2.3.0')

    @classmethod
    def tearDownClass(cls):
        del cls.exports

    def test_program_json_6_names_the_release_and_labels_the_daylighting_origin(self):
        from scripts import atlas_contracts
        document = self.exports.program(WHOLE_BUILDING[1], 'source')
        self.assertEqual((document['schema_version'], document['source']['release']), ('6.0.0', 'atlas-release-2.3.0'))
        Draft202012Validator(load_json(ROOT/'schemas'/atlas_contracts.PROGRAM[0])).validate(document)
        origin = document['lighting_controls']['daylighting_origin']
        # Review F5c: the climate-independent whole building's fractions come from the 0A model, a copy of all 19.
        self.assertEqual((origin['kind'], origin['cited_climate'], len(origin['climates'])), ('prototype_zone_set', '0A', 19))
        self.assertIn('one copy of them', origin['note'])
        self.assertIsNone(document['climate'] if 'climate' in document else None)

    def test_daylighting_origin_of_climate_exceptions_and_reference_models(self):
        ids = self.exports.program_ids()
        retail = next(p for p in ids if p.startswith('90-1-2013.retail-standalone.source.core-retail.'))
        origin = self.exports.program(retail, 'source')['lighting_controls']['daylighting_origin']
        self.assertEqual(len(origin['climates']), 15)
        self.assertFalse({'6A', '6B', '7A', '8A'} & set(origin['climates']))
        reference = next(p for p in ids if p.startswith('doe-ref-pre-1980.warehouse.source.'))
        origin = self.exports.program(reference, 'source')['lighting_controls']['daylighting_origin']
        self.assertEqual(origin['kind'], 'reference_model_scan')
        self.assertNotIn('climates', origin)

    def test_every_view_assembles(self):
        self.assertEqual(atlas_delta.assembles('2.3.0'), 2847)


if __name__ == '__main__':
    unittest.main()
