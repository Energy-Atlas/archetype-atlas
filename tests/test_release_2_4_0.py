"""Release 2.4.0: the ADR 0060 PNNL prototype corrections (unoccupied lighting cap, office lighting power, elevators and
kitchen reach-ins), a delta on 2.3.0 (ADR 0062), exported in Program JSON 6.1.0 (ADR 0061)."""
import math
import unittest

from jsonschema import Draft202012Validator

from atlas_schedules.release import Release
from scripts import atlas_delta
from scripts.common import ROOT, load_json

FOLDER = atlas_delta.folder_of('2.4.0')
BASE = atlas_delta.folder_of('2.3.0')
ID_MAP = 'id-map-2.4.0.json'
# 90.1-2019 medium office whole building: 2.3.0 ID, 2.4.0 ID (lighting power and the cap moved it).
WHOLE_BUILDING = ('90-1-2019.medium-office.source.whole-building-md-office.d597bd',
                  '90-1-2019.medium-office.source.whole-building-md-office.197348')
CAP_POINTER = '/lighting_controls/unoccupied_lighting_cap/rule'


class DeltaTests(unittest.TestCase):
    """The folder and its manifest: checks that need no resolved release."""

    @classmethod
    def setUpClass(cls):
        cls.listed = atlas_delta.verify('2.4.0')
        cls.release = Release(FOLDER)
        cls.ids = load_json(FOLDER/ID_MAP)

    @classmethod
    def tearDownClass(cls):
        del cls.listed, cls.release, cls.ids

    def test_newest_release_on_the_recorded_2_3_0(self):
        listed = self.listed
        self.assertEqual((listed['release'], listed['status'], listed['base_release']['release']), ('2.4.0', 'released', '2.3.0'))
        self.assertEqual(listed['base_release']['manifest_sha256'], atlas_delta.sha((BASE/'manifest.json').read_bytes()))
        self.assertEqual(atlas_delta.CHAIN[:4], ('2.1.0', '2.2.0', '2.3.0', '2.4.0'))
        self.assertEqual(listed['decision'][0], 'docs/adr/0062-release-2-4-0.md')
        for decision in listed['decision']:
            self.assertTrue((ROOT/decision).is_file(), decision)

    def test_generator_and_pinned_inputs(self):
        generator = self.listed['generator']
        self.assertEqual(generator, atlas_delta.GENERATOR['2.4.0'])
        # The generator code is 4.1.0's; 4.1.1 is the wheel that bundles this release's view (ADR 0062 section 4).
        self.assertEqual((generator['version'], generator['release_tag'], generator['wheel']),
                         ('4.1.1', 'atlas-schedules-v4.1.1', 'atlas_schedules-4.1.1-py3-none-any.whl'))
        self.assertEqual(generator['request_schema_version'], '4.0.0')
        self.assertEqual(sorted(self.listed['input_sha256']),
                         sorted(['LICENSE', 'LICENSE-DATA', 'data/atlas-releases/v2.3.0/manifest.json', 'scripts/atlas_delta.py',
                                 *atlas_delta.EDIT_INPUTS_2_4_0]))
        self.assertIn('scripts/atlas_edits_2_4_0.py', self.listed['input_sha256'])
        self.assertIn('scripts/atlas_edits.py', self.listed['input_sha256'])
        for path, digest in self.listed['input_sha256'].items():
            with self.subTest(input=path):
                data = atlas_delta.pinned_writer('2.4.0') if path == 'scripts/atlas_delta.py' else (ROOT/path).read_bytes()
                self.assertEqual(atlas_delta.sha(data), digest)

    def test_licences_and_readme(self):
        self.assertEqual((FOLDER/'LICENSE').read_bytes(), (ROOT/'LICENSE').read_bytes())
        self.assertEqual((FOLDER/'LICENSE-DATA').read_bytes(), (ROOT/'LICENSE-DATA').read_bytes())
        self.assertIn('release 2.4.0', (FOLDER/'README.md').read_text(encoding='utf-8'))

    def test_id_map_and_removed_paths(self):
        ids = self.ids['ids']
        self.assertEqual((self.ids['base_release'], self.ids['release']), ('2.3.0', '2.4.0'))
        self.assertEqual(len(ids), 2301)
        kinds = {kind: sum(old.split('.')[2] == kind for old in ids) for kind in ('source', 'department', 'general')}
        self.assertEqual(kinds, {'source': 1894, 'department': 296, 'general': 111})
        self.assertFalse(any('.construction-' in old for old in ids))
        self.assertEqual(self.listed['counts']['moved_ids'], {'programs': 2301, 'construction_sets': 0, 'id_map': ID_MAP})
        removed = set(self.listed['removed'])
        self.assertEqual(len(removed), 2301)
        self.assertEqual({p.rsplit('/', 1)[1][:-5] for p in removed}, set(ids))
        self.assertFalse(removed & set(self.release.paths))
        self.assertEqual(ids[WHOLE_BUILDING[0]], WHOLE_BUILDING[1])
        self.assertIn(WHOLE_BUILDING[1], self.release.program_paths)
        self.assertNotIn(WHOLE_BUILDING[0], self.release.program_paths)

    def test_release_assets_publish_the_manifest_and_id_map(self):
        from scripts import build_release_assets
        self.assertEqual(build_release_assets.published_files('2.4.0'),
                         {'manifest.json': 'atlas-release-2.4.0.manifest.json', ID_MAP: ID_MAP})
        self.assertEqual(build_release_assets.published_files('2.3.0'), {})

    def test_counts(self):
        counts = self.listed['counts']
        base = load_json(BASE/'manifest.json')['counts']
        self.assertEqual(counts['services'], base['services'] + 84)
        self.assertEqual(counts['unoccupied_lighting_cap'], {'programs_with_rule': 19, 'programs_with_null_rule': 1875})
        self.assertEqual(counts['generation'], base['generation'])   # the edits follow IDs; no block is added
        self.assertEqual(counts['programs'], base['programs'])

    def test_the_records_carry_the_edits(self):
        _, record = self.release.program(WHOLE_BUILDING[1])
        cap = record['lighting_controls']['unoccupied_lighting_cap']
        self.assertTrue(math.isclose(cap['rule']['cap_W_m2'], 0.02/0.09290304))
        self.assertTrue(math.isclose(cap['rule']['lighting_threshold_W_m2'], 0.02/0.093))
        self.assertEqual(next(l['value'] for l in record['loads'] if l['quantity'] == 'lighting'), 6.66362)
        older = next(p for p in self.release.program_paths if p.startswith('90-1-2013.medium-office.source.whole-building'))
        self.assertIsNone(self.release.program(older)[1]['lighting_controls']['unoccupied_lighting_cap']['rule'])
        services = self.release.json('commercial/90-1-2019/medium-office/services.json')
        lifts = [s for s in services.values() if s['end_use'] == 'elevator']
        self.assertEqual(len(lifts), 2)
        self.assertEqual({tuple(s['beneficiary_program_ids']) for s in lifts}, {(WHOLE_BUILDING[1],)})

    def test_in_the_tree_under_release_2_5_0(self):
        # Release 2.5.0 is the newest since ADR 0064; 2.4.0 stays in the tree as its base and exports by name.
        from scripts.atlas_exports import IN_TREE
        self.assertEqual(IN_TREE[IN_TREE.index('2.4.0') + 1], '2.5.0')
        self.assertEqual(atlas_delta.base_of('2.5.0'), '2.4.0')


class ExportTests(unittest.TestCase):
    """The resolved release exported in its contracts (ADR 0061)."""

    @classmethod
    def setUpClass(cls):
        from scripts.atlas_exports import Release as Exports
        cls.exports = Exports(release='2.4.0')

    @classmethod
    def tearDownClass(cls):
        del cls.exports

    def test_program_json_6_1_carries_the_cap_and_its_null(self):
        from scripts import atlas_contracts
        schema = Draft202012Validator(load_json(ROOT/'schemas'/atlas_contracts.PROGRAM_6_1[0]))
        document = self.exports.program(WHOLE_BUILDING[1], 'filled')
        schema.validate(document)
        self.assertEqual((document['schema_version'], document['source']['release']), ('6.1.0', 'atlas-release-2.4.0'))
        self.assertEqual(document['lighting_controls']['unoccupied_lighting_cap']['rule']['condition'], 'zone_occupant_count_zero')
        self.assertNotIn(CAP_POINTER, document['nulls'])
        self.assertEqual(len(document['building_service_ids']), 2)
        iecc = next(p for p in self.exports.program_ids() if p.startswith('iecc-2018.medium-office.source.whole-building'))
        document = self.exports.program(iecc, 'source')
        schema.validate(document)
        self.assertIsNone(document['lighting_controls']['unoccupied_lighting_cap']['rule'])
        self.assertEqual(document['nulls'][CAP_POINTER]['status'], 'none')

    def test_building_services_of_the_90_1_folders(self):
        services = self.exports.building_services('90-1-2019/hospital')
        self.assertEqual((services['schema_version'], services['release']), ('1.0.1', 'atlas-release-2.4.0'))
        self.assertEqual(sorted(s['name'] for s in services['services'] if s['end_use'] == 'elevator'),
                         ['Elevators', 'Elevators_Lights_Fan'])

    def test_every_view_assembles(self):
        self.assertEqual(atlas_delta.assembles('2.4.0'), 2847)


if __name__ == '__main__':
    unittest.main()
