"""Freeze and verify the immutable standalone shipment."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class GeneratorReleaseTests(unittest.TestCase):
    def test_frozen_integrity_and_numerical_reproduction(self):
        from scripts.schedule_generator_release import freeze_generator, verify_generator, reproduce_generator
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'v0.1.1'
            manifest = freeze_generator(target, '0.1.1')
            self.assertEqual(verify_generator(target), [])
            self.assertEqual(reproduce_generator(target), [])
            self.assertIn('generator.zip', manifest['files'])
            with zipfile.ZipFile(target / 'generator.zip') as archive:
                self.assertIn('atlas_schedules/schemas/schedule-generator-bundle-v1.schema.json', archive.namelist())
                self.assertIn('sources/schedule-generator-m1-scope.json', archive.namelist())
                self.assertIn('sources/licenses/resstock.txt', archive.namelist())
            with self.assertRaises(ValueError):
                freeze_generator(target, '0.1.1')
            blob = target / 'generator.zip'
            content = bytearray(blob.read_bytes())
            content[-40] ^= 1
            blob.write_bytes(content)
            self.assertTrue(verify_generator(target))

    def test_partial_scope_can_ship(self):
        from scripts.schedule_generator_release import freeze_generator, verify_generator
        with tempfile.TemporaryDirectory() as directory:
            scope = json.loads((ROOT / 'sources/schedule-generator-m1-scope.json').read_text())
            scope['milestone_id'] = 'M1-office-pilot'
            scope['cases'] = [case for case in scope['cases'] if case['program_id'] == 'program-0e670d8dc556f7f5bdd7f1a9']
            target = Path(directory) / 'pilot'
            manifest = freeze_generator(target, '0.0.1', scope=scope)
            self.assertEqual(manifest['scope']['case_count'], 1)
            self.assertEqual(verify_generator(target), [])
            with zipfile.ZipFile(target / 'generator.zip') as archive:
                packaged_coverage = json.loads(archive.read('docs/validation/schedule-generator-coverage.json'))
                self.assertEqual(packaged_coverage['scope']['case_count'], 1)
                self.assertEqual(packaged_coverage['resource_set_id'], manifest['resource_set_id'])
                from atlas_schedules.resources import ResourceSet
                from scripts.schedule_generator_coverage import coverage_errors
                with tempfile.TemporaryDirectory() as extracted:
                    for name in archive.namelist():
                        if name.startswith('atlas_schedules/data/'):
                            archive.extract(name, extracted)
                    packaged_resources = ResourceSet(Path(extracted) / 'atlas_schedules/data',
                                                     manifest['resource_set_id'])
                    self.assertEqual(coverage_errors(packaged_coverage, packaged_resources), [])
                example = json.loads(archive.read('references/all-cases-request.json'))
                self.assertEqual(example['params']['resource_set_id'], manifest['resource_set_id'])
                self.assertNotIn('docs/examples/schedule-generator-v1/medium-office-request.json', archive.namelist())
                self.assertNotIn('docs/examples/schedule-generator-v1/two-apartments-request.json', archive.namelist())

    def test_m1_scope_manifest_cannot_silently_shrink(self):
        from scripts.schedule_generator_release import freeze_generator
        with tempfile.TemporaryDirectory() as directory:
            scope = json.loads((ROOT / 'sources/schedule-generator-m1-scope.json').read_text())
            scope['cases'].pop()
            with self.assertRaises(ValueError):
                freeze_generator(Path(directory) / 'bad', '0.1.0', scope=scope)

    def test_unknown_resource_family_cannot_bypass_source_certification(self):
        from atlas_schedules.resources import ResourceSet, write_resources
        from scripts.schedule_generator_release import freeze_generator
        manifest = json.loads((ROOT/'atlas_schedules/data/manifest.json').read_text())
        resources = ResourceSet.load(manifest['resource_set_id'])
        scope = resources.get('reference','m1-scope')
        scope['milestone_id'] = 'uncharacterized-family'
        scope['cases'] = [c for c in scope['cases'] if c['program_id']=='program-0e670d8dc556f7f5bdd7f1a9']
        records = {('reference','m1-scope'):scope,
                   ('reference','catalogue-index'):resources.get('reference','catalogue-index'),
                   ('program',scope['cases'][0]['program_id']):resources.get('program',scope['cases'][0]['program_id'])}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'resources'
            write_resources(root,records,{})
            with self.assertRaisesRegex(ValueError,'approved source family'):
                freeze_generator(Path(directory)/'bad','0.0.1',resources_root=root)


if __name__ == '__main__':
    unittest.main()
