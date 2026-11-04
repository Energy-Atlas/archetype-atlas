"""Release 2.5.0: the ADR 0063 conditioning sides and per-side mixes, a delta on 2.4.0 (ADR 0064), exported in
Program JSON 6.2.0."""
import unittest

from jsonschema import Draft202012Validator

import atlas_schedules
from atlas_schedules.release import Release, current
from scripts import atlas_delta
from scripts.common import ROOT, load_json

FOLDER = atlas_delta.folder_of('2.5.0')
BASE = atlas_delta.folder_of('2.4.0')
ID_MAP = 'id-map-2.5.0.json'
# 90.1-2019 warehouse: 2.4.0 ID, 2.5.0 ID.
BULK = ('90-1-2019.warehouse.source.bulk.39f8eb', '90-1-2019.warehouse.source.bulk.b043c0')
STORAGE_MIX = ('90-1-2019.warehouse.department.storage-mixed.05aa51', '90-1-2019.warehouse.department.storage-mixed.bfa555')


class DeltaTests(unittest.TestCase):
    """The folder and its manifest: checks that need no resolved release."""

    @classmethod
    def setUpClass(cls):
        cls.listed = atlas_delta.verify('2.5.0')
        cls.release = Release(FOLDER)
        cls.ids = load_json(FOLDER/ID_MAP)

    @classmethod
    def tearDownClass(cls):
        del cls.listed, cls.release, cls.ids

    def test_newest_release_on_the_recorded_2_4_0(self):
        listed = self.listed
        self.assertEqual((listed['release'], listed['status'], listed['base_release']['release']), ('2.5.0', 'released', '2.4.0'))
        self.assertEqual(listed['base_release']['manifest_sha256'], atlas_delta.sha((BASE/'manifest.json').read_bytes()))
        self.assertEqual(atlas_delta.RELEASE, '2.5.0')
        self.assertEqual(atlas_delta.CHAIN, ('2.1.0', '2.2.0', '2.3.0', '2.4.0', '2.5.0'))
        self.assertEqual(listed['decision'][0], 'docs/adr/0064-release-2-5-0.md')
        for decision in listed['decision']:
            self.assertTrue((ROOT/decision).is_file(), decision)

    def test_generator_and_pinned_inputs(self):
        generator = self.listed['generator']
        self.assertEqual(generator, atlas_delta.GENERATOR['2.5.0'])
        # The generator code is 4.1.0's; 4.1.2 is the wheel that bundles this release's view (ADR 0064 section 4).
        self.assertEqual((generator['version'], generator['release_tag'], generator['wheel']),
                         (atlas_schedules.__version__, 'atlas-schedules-v4.1.2', 'atlas_schedules-4.1.2-py3-none-any.whl'))
        self.assertEqual(generator['request_schema_version'], atlas_schedules.REQUEST_SCHEMA_VERSION)
        self.assertEqual(sorted(self.listed['input_sha256']),
                         sorted(['LICENSE', 'LICENSE-DATA', 'data/atlas-releases/v2.4.0/manifest.json', 'scripts/atlas_delta.py',
                                 *atlas_delta.EDIT_INPUTS_2_5_0]))
        for path, digest in self.listed['input_sha256'].items():
            with self.subTest(input=path):
                data = atlas_delta.pinned_writer('2.5.0') if path == 'scripts/atlas_delta.py' else (ROOT/path).read_bytes()
                self.assertEqual(atlas_delta.sha(data), digest)

    def test_earlier_releases_pin_the_writer_without_this_block(self):
        self.assertNotIn(b'release 2.5.0', atlas_delta.pinned_writer('2.4.0'))
        self.assertEqual(atlas_delta.sha(atlas_delta.pinned_writer('2.4.0')),
                         load_json(BASE/'manifest.json')['input_sha256']['scripts/atlas_delta.py'])

    def test_licences_and_readme(self):
        self.assertEqual((FOLDER/'LICENSE').read_bytes(), (ROOT/'LICENSE').read_bytes())
        self.assertEqual((FOLDER/'LICENSE-DATA').read_bytes(), (ROOT/'LICENSE-DATA').read_bytes())
        self.assertIn('release 2.5.0', (FOLDER/'README.md').read_text(encoding='utf-8'))

    def test_id_map_and_removed_paths(self):
        ids = self.ids['ids']
        self.assertEqual((self.ids['base_release'], self.ids['release']), ('2.4.0', '2.5.0'))
        self.assertEqual(len(ids), 518)
        kinds = {kind: sum(old.split('.')[2] == kind for old in ids) for kind in ('source', 'department', 'general')}
        self.assertEqual(kinds, {'source': 72, 'department': 305, 'general': 141})
        self.assertEqual(self.listed['counts']['moved_ids'], {'programs': 518, 'construction_sets': 0, 'id_map': ID_MAP})
        removed = set(self.listed['removed'])
        self.assertEqual({p.rsplit('/', 1)[1][:-5] for p in removed}, set(ids))
        self.assertFalse(removed & set(self.release.paths))
        for old, new in (BULK, STORAGE_MIX):
            self.assertEqual(ids[old], new)
            self.assertIn(new, self.release.program_paths)

    def test_release_assets_publish_the_manifest_and_id_map(self):
        from scripts import build_release_assets
        self.assertEqual(build_release_assets.published_files('2.5.0'),
                         {'manifest.json': 'atlas-release-2.5.0.manifest.json', ID_MAP: ID_MAP})

    def test_counts(self):
        counts = self.listed['counts']
        base = load_json(BASE/'manifest.json')['counts']
        self.assertEqual(counts['conditioning_sides'], {
            'source_programs_not_conditioned': {'heating': 47, 'cooling': 60}, 'source_programs_changed': 72,
            'source_programs_mixed_service': 2, 'mixes': {'full_coverage': 373, 'partial_coverage': 69, 'unknown_side': 4}})
        for key in ('generation', 'programs', 'services', 'unoccupied_lighting_cap'):
            self.assertEqual(counts[key], base[key], key)

    def test_the_records_carry_the_edits(self):
        _, bulk = self.release.program(BULK[1])
        self.assertEqual(bulk['parameters']['cooling_setpoint_schedule_id']['value'], None)
        self.assertEqual(bulk['parameters']['conditioning']['value'], {'heating_enabled': True, 'cooling_enabled': False})
        _, mix = self.release.program(STORAGE_MIX[1])
        self.assertEqual(mix['composition']['setpoint_coverage']['heating'], 1.0)
        self.assertAlmostEqual(mix['composition']['setpoint_coverage']['cooling'], 0.30303030303, places=10)

    def test_the_generator_and_the_site_read_it_from_the_tree(self):
        from scripts import site_release
        from scripts.atlas_exports import IN_TREE, Release as Exports
        reader = current()
        self.assertEqual(reader.provenance(), {'version': '2.5.0', 'manifest_sha256': self.release.manifest_sha256,
                                               'generation_schema_version': '1.0.0'})
        self.assertEqual(site_release.newest(), '2.5.0')
        self.assertEqual(IN_TREE[-1], '2.5.0')
        self.assertEqual(Exports.__init__.__defaults__[-1], '2.5.0')


class SiteTests(unittest.TestCase):
    def test_program_pages_state_the_sides_and_a_mix_coverage(self):
        from scripts.suite_site import conditioning_fact
        release = Release(FOLDER)
        self.assertEqual(conditioning_fact(release.program(BULK[1])[1]),
                         'heating only (cooling <code>not_conditioned</code>: no source equipment serves it)')
        self.assertEqual(conditioning_fact(release.program(STORAGE_MIX[1])[1]),
                         'heating and cooling · setpoint coverage heating 1.000, cooling 0.303 (the represented-area share of '
                         'the members with each side)')
        fine = next(p for p in release.program_paths if p.startswith('90-1-2019.warehouse.source.fine.'))
        self.assertEqual(conditioning_fact(release.program(fine)[1]), '')


class ExportTests(unittest.TestCase):
    """The resolved release exported in its contracts (ADR 0063 section 2.4)."""

    @classmethod
    def setUpClass(cls):
        from scripts.atlas_exports import Release as Exports
        cls.exports = Exports(release='2.5.0')

    @classmethod
    def tearDownClass(cls):
        del cls.exports

    def test_program_json_6_2_carries_the_sides_and_the_coverage(self):
        from scripts import atlas_contracts
        schema = Draft202012Validator(load_json(ROOT/'schemas'/atlas_contracts.PROGRAM_6_2[0]))
        bulk = self.exports.program(BULK[1], 'source')
        schema.validate(bulk)
        self.assertEqual((bulk['schema_version'], bulk['source']['release']), ('6.2.0', 'atlas-release-2.5.0'))
        self.assertEqual(bulk['controls']['conditioning_state'], 'heating_only')
        self.assertEqual(bulk['nulls']['/controls/cooling_setpoint_schedule_id']['status'], 'not_conditioned')
        mix = self.exports.program(STORAGE_MIX[1], 'filled')
        schema.validate(mix)
        self.assertAlmostEqual(mix['controls']['setpoint_coverage']['cooling'], 0.30303030303, places=10)

    def test_every_view_assembles(self):
        self.assertEqual(atlas_delta.assembles('2.5.0'), 2847)


if __name__ == '__main__':
    unittest.main()
