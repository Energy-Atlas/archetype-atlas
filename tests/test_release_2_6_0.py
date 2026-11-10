"""Release 2.6.0: the unconditioned-attic repair of ADR 0065, a delta on 2.5.0 (ADR 0066), whose unified exports take
unified constructions 4.1.0."""
import json
import unittest

import atlas_schedules
from atlas_schedules.release import Release, current
from scripts import atlas_contracts, atlas_delta, attic_boundary
from scripts.common import ROOT, load_json

FOLDER = atlas_delta.folder_of('2.6.0')
BASE = atlas_delta.folder_of('2.5.0')
ID_MAP = 'id-map-2.6.0.json'
# The four small office eras of the LOD study: 2.5.0 set ID, 2.6.0 set ID.
SMALL_OFFICE = {'90-1-2007.small-office-detailed.construction-package.b1ba8a': '90-1-2007.small-office-detailed.construction-package.7fae32',
                '90-1-2019.small-office-detailed.construction-package.7eee9d': '90-1-2019.small-office-detailed.construction-package.ff7fc8',
                'doe-ref-1980-2004.small-office-detailed.construction-package.8575fa': 'doe-ref-1980-2004.small-office-detailed.construction-package.bdc90e',
                'doe-ref-pre-1980.small-office-detailed.construction-package.db34c2': 'doe-ref-pre-1980.small-office-detailed.construction-package.14f979'}
BULK = '90-1-2019.warehouse.source.bulk.b043c0'   # a 2.5.0 program, which keeps its ID


class DeltaTests(unittest.TestCase):
    """The folder and its manifest: checks that need no resolved release."""

    @classmethod
    def setUpClass(cls):
        cls.listed = atlas_delta.verify('2.6.0')
        cls.release = Release(FOLDER)
        cls.ids = load_json(FOLDER/ID_MAP)

    @classmethod
    def tearDownClass(cls):
        del cls.listed, cls.release, cls.ids

    def test_newest_release_on_the_recorded_2_5_0(self):
        listed = self.listed
        self.assertEqual((listed['release'], listed['status'], listed['base_release']['release']), ('2.6.0', 'released', '2.5.0'))
        self.assertEqual(listed['base_release']['manifest_sha256'], atlas_delta.sha((BASE/'manifest.json').read_bytes()))
        self.assertEqual(atlas_delta.RELEASE, '2.6.0')
        self.assertEqual(atlas_delta.CHAIN, ('2.1.0', '2.2.0', '2.3.0', '2.4.0', '2.5.0', '2.6.0'))
        self.assertEqual(listed['decision'][:2], ['docs/adr/0066-release-2-6-0.md', 'docs/adr/0065-unconditioned-attic-boundaries.md'])
        for decision in listed['decision']:
            self.assertTrue((ROOT/decision).is_file(), decision)

    def test_generator_and_pinned_inputs(self):
        generator = self.listed['generator']
        # No generator release (ADR 0066 section 4): the recipes are 2.5.0's, which 4.1.2 carries.
        self.assertEqual(generator, atlas_delta.GENERATOR['2.5.0'])
        self.assertEqual((generator['version'], generator['release_tag']), (atlas_schedules.__version__, 'atlas-schedules-v4.1.2'))
        self.assertEqual(sorted(self.listed['input_sha256']),
                         sorted(['LICENSE', 'LICENSE-DATA', 'data/atlas-releases/v2.5.0/manifest.json', 'scripts/atlas_delta.py',
                                 *atlas_delta.EDIT_INPUTS_2_6_0]))
        for path, digest in self.listed['input_sha256'].items():
            with self.subTest(input=path):
                data = atlas_delta.pinned_writer('2.6.0') if path == 'scripts/atlas_delta.py' else (ROOT/path).read_bytes()
                self.assertEqual(atlas_delta.sha(data), digest)

    def test_earlier_releases_pin_the_writer_without_this_block(self):
        self.assertNotIn(b'release 2.6.0', atlas_delta.pinned_writer('2.5.0'))
        self.assertEqual(atlas_delta.sha(atlas_delta.pinned_writer('2.5.0')),
                         load_json(BASE/'manifest.json')['input_sha256']['scripts/atlas_delta.py'])

    def test_licences_and_readme(self):
        self.assertEqual((FOLDER/'LICENSE').read_bytes(), (ROOT/'LICENSE').read_bytes())
        self.assertEqual((FOLDER/'LICENSE-DATA').read_bytes(), (ROOT/'LICENSE-DATA').read_bytes())
        self.assertIn('release 2.6.0', (FOLDER/'README.md').read_text(encoding='utf-8'))

    def test_id_map_and_removed_paths(self):
        ids = self.ids['ids']
        self.assertEqual((self.ids['base_release'], self.ids['release']), ('2.5.0', '2.6.0'))
        self.assertEqual(len(ids), 24)
        self.assertTrue(all('.construction-package.' in old and '.construction-package.' in new for old, new in ids.items()))
        self.assertEqual(self.listed['counts']['moved_ids'], {'programs': 0, 'construction_sets': 24, 'id_map': ID_MAP})
        removed = set(self.listed['removed'])
        self.assertEqual({p.rsplit('/', 1)[1][:-5] for p in removed}, set(ids))
        self.assertTrue(all('/constructions/' in p for p in removed))
        for old, new in SMALL_OFFICE.items():
            self.assertEqual(ids[old], new)

    def test_no_program_schedule_service_or_generation_file(self):
        kinds = ('/programs/', '/schedules.json', '/services.json', '/generation.json', 'definition-map.json', 'exporter-inputs.json')
        self.assertEqual([p for p in self.listed['files'] if any(k in p for k in kinds)], [])

    def test_release_assets_publish_the_manifest_and_id_map(self):
        from scripts import build_release_assets
        self.assertEqual(build_release_assets.published_files('2.6.0'),
                         {'manifest.json': 'atlas-release-2.6.0.manifest.json', ID_MAP: ID_MAP})

    def test_counts(self):
        counts = self.listed['counts']
        base = load_json(BASE/'manifest.json')['counts']
        self.assertEqual(counts['interior_ceiling_corrections'], {'construction_sets': 24, 'contexts': 568, 'unresolved': 0})
        self.assertEqual(counts['unified_attics'], {'contexts': 926, 'by_family': {'openstudio_standards_rules': 568,
                                                                                 'pnnl_idf': 342, 'resstock': 16}})
        for key in set(base) - {'moved_ids'}:
            self.assertEqual(counts[key], base[key], key)

    def test_the_generator_and_the_site_read_it_from_the_tree(self):
        from scripts import site_release
        from scripts.atlas_exports import IN_TREE, Release as Exports
        reader = current()
        self.assertEqual(reader.provenance(), {'version': '2.6.0', 'manifest_sha256': self.release.manifest_sha256,
                                               'generation_schema_version': '1.0.0'})
        self.assertEqual(site_release.newest(), '2.6.0')
        self.assertEqual(IN_TREE[-1], '2.6.0')
        self.assertEqual(Exports.__init__.__defaults__[-1], '2.6.0')


class ExportTests(unittest.TestCase):
    """The resolved release exported in its contracts: unified 4.1.0 (ADR 0066 section 2)."""

    @classmethod
    def setUpClass(cls):
        from scripts.atlas_exports import Release as Exports
        cls.exports = Exports(release='2.6.0')
        cls.before = Exports(release='2.5.0')
        cls.ids = load_json(FOLDER/ID_MAP)['ids']
        cls.corrected = {sid: sorted(k for k in rec['contexts'] if 'unified' in rec['contexts'][k]
                                     and attic_boundary.CARRIED in (cls.exports.constructions.export(sid, k, 'unified').get('provenance') or {}))
                         for sid, rec in cls.exports.constructions.sets.items() if sid in cls.ids.values()}

    @classmethod
    def tearDownClass(cls):
        del cls.exports, cls.before, cls.ids, cls.corrected

    def test_the_corrected_contexts(self):
        self.assertEqual(set(self.corrected), set(self.ids.values()))
        self.assertEqual(sum(map(len, self.corrected.values())), 568)

    def test_every_corrected_context_equals_the_2_5_0_export_with_the_rule_applied(self):
        """The 2.6.0 unified 4.1.0 document is the 4.1.0 document ADR 0065 exported from release 2.5.0 (the correction applied
        at export), except for the release label and the moved set ID."""
        back = {new: old for old, new in self.ids.items()}
        for new, keys in sorted(self.corrected.items()):
            old = back[new]
            for key in keys:
                with self.subTest(set=new, context=key):
                    document = self.exports.construction(new, key, 'unified')
                    expected, _ = attic_boundary.export(self.before, old, key)
                    expected = json.loads(json.dumps(expected).replace(old, new))
                    expected['release'] = 'atlas-release-2.6.0'
                    self.assertEqual(document, expected)

    def test_small_office_4_a(self):
        document = self.exports.construction(SMALL_OFFICE['90-1-2019.small-office-detailed.construction-package.7eee9d'], '4-a', 'unified')
        self.assertEqual((document['schema_version'], document['release']), ('4.1.0', 'atlas-release-2.6.0'))
        self.assertEqual(atlas_contracts.UNIFIED_BY_RELEASE['2.6.0'], atlas_contracts.UNIFIED_ATTICS)
        correction, = document['export_corrections']
        self.assertEqual(correction['status'], 'corrected')
        self.assertEqual(correction['corrected'], document['components']['InteriorCeiling']['derivation'])
        self.assertEqual(document['components']['InteriorCeiling']['derivation']['source_reference_area_m2'], 0.0)
        self.assertAlmostEqual(correction['stored']['source_reference_area_m2'], 511.15624589999993, places=9)
        self.assertNotIn(attic_boundary.CARRIED, document['provenance'])
        attic, = document['attics']
        self.assertAlmostEqual(attic['attic_omitted_roof']['u_bounds_W_m2_K']['equivalent_sealed_roof_only'], 0.1138394978, places=9)

    def test_a_context_without_an_attic_is_4_0_0_with_the_version_raised(self):
        sid = next(s for s in self.exports.constructions.sets if s.startswith('90-1-2019.medium-office-detailed.'))
        document = self.exports.construction(sid, '4-a', 'unified')
        stored = self.before.construction(sid, '4-a', 'unified')
        self.assertEqual(document, {**stored, 'schema_version': '4.1.0', 'release': 'atlas-release-2.6.0'})
        self.assertNotIn('attics', document)

    def test_iecc_and_detailed_documents(self):
        sid = next(s for s in self.exports.constructions.sets if s.startswith('iecc-2021.small-office.'))
        document = self.exports.construction(sid, '4-a', 'unified')
        self.assertEqual((document['schema_version'], document['attics'][0]['source']['family']), ('4.1.0', 'pnnl_idf'))
        self.assertNotIn('export_corrections', document)
        detailed = self.exports.construction(sid, '4-a', 'detailed')
        self.assertEqual(detailed, {**self.before.construction(sid, '4-a', 'detailed'), 'release': 'atlas-release-2.6.0'})

    def test_programs_keep_their_ids_and_values(self):
        for version in ('source', 'filled'):
            document = self.exports.program(BULK, version)
            earlier = self.before.program(BULK, version)
            self.assertEqual(document['source']['release'], 'atlas-release-2.6.0')
            # The release label is the only difference (it also names the release in the atlas evidence rows).
            self.assertEqual(json.loads(json.dumps(document).replace('atlas-release-2.6.0', 'atlas-release-2.5.0')), earlier)

    def test_every_view_assembles(self):
        self.assertEqual(atlas_delta.assembles('2.6.0'), 2847)


if __name__ == '__main__':
    unittest.main()
