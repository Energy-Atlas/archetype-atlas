"""Release 2.1.0: generation parameters as a delta on 2.0.0 (ADR 0049)."""
import json
import unittest

from atlas_schedules import programmes
from atlas_schedules.release import Release, current
from scripts import release_2_1_0, site_release
from scripts.common import ROOT

FOLDER = ROOT/'data/atlas-releases/v2.1.0'


class Release210Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = release_2_1_0.verify(FOLDER)

    def test_delta_on_the_recorded_2_0_0(self):
        listed = self.release.manifest
        self.assertEqual((listed['release'], listed['base_release']['release'], listed['generation']['schema_version']),
                         ('2.1.0', '2.0.0', '1.0.0'))
        self.assertEqual(self.release.base.manifest_sha256, listed['base_release']['manifest_sha256'])
        self.assertEqual(current().version, '2.1.0')

    def test_generator_json_retired_and_nothing_else_replaced(self):
        base = self.release.base
        self.assertEqual(sorted(self.release.retired), sorted(p for p in base.paths if p.endswith('/generator.json')))
        self.assertEqual(set(self.release.manifest['files']) & set(base.paths), {'README.md', 'LICENSE'})
        self.assertTrue(all(p.endswith(('/generation.json', 'definition-map.json', 'README.md', 'LICENSE'))
                            for p in self.release.manifest['files']))

    def test_programs_read_with_their_blocks(self):
        folder, record = self.release.program('90-1-2019.primary-school.source.classroom.6fac9d')
        self.assertEqual(record['generation']['method'], 'comstock_hours')
        self.assertEqual(record['generation']['views']['filled'], {'configuration_id': 'primary_school__90_1_2019__reviewed'})
        _, base = self.release.base.program('90-1-2019.primary-school.source.classroom.6fac9d')
        self.assertEqual({k: v for k, v in record.items() if k != 'generation'}, base)
        counts = self.release.manifest['counts']
        self.assertEqual(counts['methods'], {'composition': 191, 'comstock_hours': 734, 'fixed': 22,
                                             'resstock_dwelling': 41, 'resstock_unit': 20})

    def test_every_view_assembles(self):
        self.assertEqual(release_2_1_0.assembles(self.release), 1585)

    def test_definition_map(self):
        mapped = self.release.json('definition-map.json')
        self.assertEqual((len(mapped['programs']), len(mapped['services']), len(mapped['retired'])), (1216, 150, 12))
        entry = mapped['programs']['program-098127c144bbfd68cea77c6b']
        self.assertEqual(entry, {'program_id': '90-1-2019.primary-school.source.classroom.6fac9d', 'values': 'filled'})
        recipe = programmes.assemble(self.release, entry['program_id'], entry['values'])
        self.assertEqual(recipe['commercial']['configuration_id'], 'primary_school__90_1_2019__reviewed')

    def test_site_and_exports_read_2_0_0(self):
        self.assertEqual(site_release.releases()[-1], '2.1.0')
        self.assertEqual(site_release.newest(), '2.0.0')
        self.assertEqual(json.loads((FOLDER/'manifest.json').read_bytes())['exports']['release'], '2.0.0')

    def test_the_base_resolves_beside_it(self):
        self.assertIsInstance(Release(FOLDER).base, Release)


if __name__ == '__main__':
    unittest.main()
