"""Release 2.0.0: the full snapshot of release 1.6.0 (ADR 0046), the only release in the tree."""
import io
import json
import unittest
from unittest import mock

from jsonschema import Draft202012Validator

from scripts import atlas_snapshot
from scripts.atlas_exports import EXPORTER_INPUTS
from scripts.common import ROOT, load_json

FROZEN = ('releases', 'definition-releases', 'resolution-releases', 'water-reporting-releases', 'completion-releases',
          'construction-releases', 'construction-equivalent-releases', 'construction-mass-releases',
          'construction-foundation-releases', 'water-releases')


class Release200Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.listed = atlas_snapshot.verify()
        cls.files = atlas_snapshot.files()

    @classmethod
    def tearDownClass(cls):
        # unittest keeps every test class until the run ends; free the release state.
        del cls.listed, cls.files

    def test_full_snapshot_of_1_6_0_and_the_only_release(self):
        self.assertIsNone(self.listed['base_release'])
        self.assertEqual((self.listed['snapshot_of']['release'], self.listed['status']), ('1.6.0', 'candidate'))
        self.assertEqual(sorted(p.name for p in (ROOT/'data/atlas-releases').iterdir()), ['v2.0.0'])
        self.assertIn(EXPORTER_INPUTS, self.files)

    def test_generator_recipes_for_the_90_1_and_doe_ref_programs(self):
        counts = self.listed['counts']
        self.assertEqual(counts['programs_with_recipes'] + counts['programs_without_recipes'], counts['programs'])
        generators = [p for p in self.files if p.endswith('/generator.json')]
        self.assertTrue(all(p.split('/')[1].startswith(('90-1-', 'doe-ref-')) for p in generators))
        recipes = json.loads(self.files[next(p for p in generators if '/90-1-2019/medium-office/' in p)])
        entry = next(iter(recipes.values()))
        self.assertLessEqual(set(entry), {'source', 'reviewed'})
        self.assertIn('slots', entry.get('source') or entry['reviewed'])
        # DOE Ref recipes are written from the release, under release IDs (stage X1.2)
        doe = json.loads(self.files['commercial/doe-ref-1980-2004/medium-office/generator.json'])
        self.assertTrue(all(set(e) == {'source'} and e['source']['program_id'] == pid for pid, e in doe.items()))

    def test_daylighting_fractions_are_plain_values(self):
        programs = [json.loads(d) for p, d in self.files.items() if p.startswith('commercial/') and '/programs/' in p]
        controls = [p['lighting_controls'] for p in programs if 'lighting_controls' in p]
        self.assertTrue(any(c.get('daylighting') for c in controls))
        self.assertFalse(any('geometry_dependent' in c for c in controls))
        self.assertEqual(self.listed['counts']['plain_daylighting_programs'],
                         sum(1 for c in controls if c['source'] == 'pnnl_prototype' and c['status'] == 'known'))

    def test_exporter_inputs(self):
        carried = json.loads(self.files[EXPORTER_INPUTS])
        self.assertEqual((len(carried['capped_services']), len(carried['capped_programs']), len(carried['inactive_controls'])),
                         (3, 3, 43))

    def test_exports_open_no_frozen_folder(self):
        from scripts.atlas_exports import Release
        release = Release(files=self.files, release='2.0.0')
        opened = []
        real = io.open

        def guarded(file, *args, **kwargs):
            path = str(file).replace('\\', '/')
            if any('/data/'+name+'/' in path for name in FROZEN) or '/data/atlas-releases/v1.' in path:
                opened.append(path)
            return real(file, *args, **kwargs)
        programs = sorted(release.program_ids())
        dwellings = sorted(release.dwellings.program_ids())
        with mock.patch('io.open', guarded), mock.patch('builtins.open', guarded):
            for pid in [*programs[::150], *dwellings[::8]]:
                for version in ('source', 'filled'):
                    try:
                        release.program(pid, version)
                    except ValueError as error:
                        self.assertRegex(str(error), 'source only|water heaters', pid)
            for sid in sorted(release.constructions.sets)[::20]:
                key = sorted(release.constructions.sets[sid]['contexts'])[0]
                release.construction(sid, key, 'unified')
        self.assertEqual(opened, [])

    def test_exports(self):
        from scripts.atlas_exports import Release
        release = Release(files=self.files, release='2.0.0')
        program_id = next(p for p in release.program_ids() if p.startswith('90-1-2019.medium-office.source.whole'))
        document = release.program(program_id, 'filled')
        self.assertEqual((document['schema_version'], document['source']['release']), ('5.4.0', 'atlas-release-2.0.0'))
        self.assertNotIn('geometry_dependent', document.get('lighting_controls', {}))


class ExportSchemaTests(unittest.TestCase):
    def test_schemas_are_derived_from_the_previous_majors(self):
        from scripts import atlas_exports
        for name, schema in atlas_exports.derived_schemas().items():
            self.assertEqual(load_json(ROOT/'schemas'/name), schema, name)
            Draft202012Validator.check_schema(schema)

    def test_only_release_2_0_0_reads_from_the_tree(self):
        from scripts.atlas_exports import Release
        with self.assertRaisesRegex(ValueError, 'frozen-data-2026-10-27'):
            Release(release='1.6.0')


if __name__ == '__main__':
    unittest.main()
