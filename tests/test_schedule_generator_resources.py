"""Resource boundary tests: corruption, incomplete evidence and scope mismatches fail closed."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('atlas_schedules'),
                             'schedule resource implementation is missing')
        from atlas_schedules.errors import GeneratorError
        from scripts.schedule_generator_sources import extract_sources
        self.error = GeneratorError
        self.extract = extract_sources

    def fixture(self, root, content=b'Dependency=building_type\tOption=early\tOption=late\nmedium_office\t0.25\t0.75\n', member='tables/start.tsv'):
        archive = root/'source.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr(member, content)
        return {'schema_version': '1.0.0', 'archives': [{
            'cache_path': 'source.zip', 'format': 'zip', 'source_id': 'fixture',
            'source_revision': 'test-1', 'url': 'https://example.invalid/source.zip',
            'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'size_bytes': archive.stat().st_size,
            'members': [{'path': member, 'sha256': hashlib.sha256(content).hexdigest(),
                         'size_bytes': len(content), 'kind': 'commercial', 'key': 'start',
                         'format': 'conditional_tsv', 'required': True,
                         'original_unit': 'probability', 'extraction_date': '2026-10-14'}]}],
                'files': [], 'external_selectors': ['building_type'],
                'required_resources': [{'kind': 'commercial', 'key': 'start'}]}

    def test_resource_hash_and_inventory_rejection(self):
        from atlas_schedules.resources import ResourceSet
        for mutation in ('changed', 'deleted', 'extra'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                manifest = self.extract(self.fixture(root), root, root/'out')
                resource = root/'out/commercial/start.json'
                if mutation == 'changed':
                    resource.write_bytes(b'{}')
                elif mutation == 'deleted':
                    resource.unlink()
                else:
                    (root/'out/extra.json').write_bytes(b'{}')
                with self.assertRaises(self.error) as e:
                    ResourceSet(root/'out', manifest['resource_set_id'])
                self.assertEqual(e.exception.code, 'resource_integrity')

    def test_unsafe_archive_member_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lock = self.fixture(root, member='../escape.tsv')
            with self.assertRaises(self.error) as e:
                self.extract(lock, root, root/'out')
            self.assertEqual(e.exception.code, 'unsafe_resource_path')
            self.assertFalse((root/'escape.tsv').exists())

    def test_archive_names_cannot_alias_windows_or_posix_paths(self):
        for member in ('tables/NUL.tsv', 'tables//start.tsv', 'tables/name./start.tsv'):
            with self.subTest(member=member), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                with self.assertRaises(self.error) as e:
                    self.extract(self.fixture(root, member=member), root, root/'out')
                self.assertEqual(e.exception.code, 'unsafe_resource_path')

    def test_conditional_dependency_cycle_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lock = self.fixture(root, b'Dependency=start\tOption=x\nanything\t1\n')
            with self.assertRaises(self.error) as e:
                self.extract(lock, root, root/'out')
            self.assertEqual(e.exception.code, 'dependency_cycle')

    def test_incomplete_probability_axis_has_structured_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lock = self.fixture(root, b'0.25,0.75\n0.5\n')
            entry = lock['archives'][0]['members'][0]
            entry['format'] = 'probability_csv'
            entry['probability_axis'] = {'mode': 'columns', 'columns': [0, 1]}
            with self.assertRaises(self.error) as e:
                self.extract(lock, root, root/'out')
            self.assertEqual(e.exception.code, 'invalid_probability')

    def test_nonfinite_calibration_value_is_not_reinterpreted_as_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lock = self.fixture(root, b'NaN\n')
            lock['archives'][0]['members'][0]['format'] = 'csv'
            with self.assertRaises(self.error) as e:
                self.extract(lock, root, root/'out')
            self.assertEqual(e.exception.code, 'invalid_probability')

    def test_probability_resource_is_required(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lock = self.fixture(root)
            lock['archives'][0]['members'] = []
            with self.assertRaises(self.error) as e:
                self.extract(lock, root, root/'out')
            self.assertEqual(e.exception.code, 'missing_resource')

    def test_resource_identity_ignores_destination(self):
        from atlas_schedules.resources import ResourceSet
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lock = self.fixture(root)
            a = self.extract(lock, root, root/'a')
            b = self.extract(lock, root, root/'b')
            self.assertEqual(a, b)
            table = ResourceSet(root/'a', a['resource_set_id']).get('commercial', 'start')
            self.assertEqual(table['options'], ['early', 'late'])
            self.assertEqual(table['rows'][0]['probabilities'], [0.25, 0.75])
            self.assertEqual(table['rows'][0]['selectors'], {'building_type': 'medium_office'})
            self.assertEqual(table['rows'][0]['original_values'], ['0.25', '0.75'])

    def test_malformed_probability_rows_rejected(self):
        for values in ('-0.1\t1.1', 'NaN\t1', '0.1\t0.1', '\t1'):
            with self.subTest(values=values), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                content = ('Dependency=building_type\tOption=early\tOption=late\nmedium_office\t'+values+'\n').encode()
                with self.assertRaises(self.error) as e:
                    self.extract(self.fixture(root, content), root, root/'out')
                self.assertEqual(e.exception.code, 'invalid_probability')

    def test_explicit_scope_selector_excludes_unselected_invalid_rows(self):
        from atlas_schedules.resources import ResourceSet
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lock = self.fixture(root, b'Dependency=building_type\tOption=early\tOption=late\nmedium_office\t0.25\t0.75\nhospital\t0\t0\n')
            lock['archives'][0]['members'][0]['fixed_selectors'] = {'building_type': 'medium_office'}
            manifest = self.extract(lock, root, root/'out')
            table = ResourceSet(root/'out', manifest['resource_set_id']).get('commercial', 'start')
            self.assertEqual(len(table['rows']), 1)
            self.assertEqual(table['rows'][0]['source_row'], 2)

    def test_canonical_json_and_scoped_ids(self):
        from atlas_schedules.canonical import canonical, schedule_id
        self.assertEqual(canonical({'z': 2, 'a': 1}), b'{"a":1,"z":2}\n')
        self.assertEqual(schedule_id('a/b', 'c:d'), 'schedule:a%2Fb:c%3Ad')
        self.assertNotEqual(schedule_id('a:b', 'c'), schedule_id('a', 'b:c'))
        with self.assertRaises(self.error):
            canonical({'a': float('nan')})

    def test_source_hours_are_normalized_to_si_with_original_options(self):
        from atlas_schedules.resources import ResourceSet
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lock = self.fixture(root, b'Dependency=building_type\tOption=3.5\tOption=4.0\nmedium_office\t0.25\t0.75\n')
            lock['archives'][0]['members'][0]['option_quantity'] = {'original_unit': 'h', 'unit': 's', 'multiplier': 3600}
            manifest = self.extract(lock, root, root/'out')
            table = ResourceSet(root/'out', manifest['resource_set_id']).get('commercial', 'start')
            self.assertEqual(table['option_values'], [12600.0, 14400.0])
            self.assertEqual(table['options'], ['3.5', '4.0'])
            self.assertEqual(table['option_unit'], 's')

    def test_packaged_real_source_closure_is_exact_and_portable(self):
        from atlas_schedules.resources import ResourceSet
        manifest = json.loads((ROOT/'atlas_schedules/data/manifest.json').read_text())
        resources = ResourceSet.load(manifest['resource_set_id'])
        table = resources.get('commercial', 'weekday_start_time')
        self.assertEqual(table['rows'][0]['source_row'], 13)
        self.assertEqual(table['rows'][0]['probabilities'][0], 0.003)
        self.assertEqual(table['options'][0], '3.5')
        durations = resources.get('commercial', 'weekday_duration')
        self.assertEqual(len(durations['rows']), 36)
        self.assertTrue(all(r['selectors']['building_type'] == 'medium_office' for r in durations['rows']))
        self.assertEqual(resources.get('commercial', 'sampling-audit')['conditioning_inputs'], {'building_type': 'medium_office'})
        self.assertEqual(len(resources.manifest['cases']), 10)
        for case in resources.manifest['cases']:
            resources.get('program', case['program_id'])
        self.assertNotIn(b'C:\\Users', canonical_bytes := (ROOT/'atlas_schedules/data/program/program-03fe19ed8968e605f4be3b8d.json').read_bytes())
        self.assertNotIn(b'D:\\archetype', canonical_bytes)
        program = resources.get('program', 'program-0e670d8dc556f7f5bdd7f1a9')['definition']
        evidence = resources.get('reference', program['loads'][0]['evidence_id'])['definition']
        self.assertEqual(evidence['original_unit'], 'people/1000 ft2')
        source = resources.get('reference', evidence['source_file_id'])['definition']
        self.assertEqual(len(source['sha256']), 64)

    def test_ragged_source_duration_samples_have_si_receipts(self):
        from atlas_schedules.resources import ResourceSet
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lock = self.fixture(root, b'1,2,3\n4,5\n')
            entry = lock['archives'][0]['members'][0]
            entry['format'] = 'csv'
            entry['column_quantities'] = {'*': {'original_unit': '15-minute interval', 'unit': 's', 'multiplier': 900}}
            manifest = self.extract(lock, root, root/'out')
            table = ResourceSet(root/'out', manifest['resource_set_id']).get('commercial', 'start')
            self.assertEqual(table['normalized_values'], [[900, 1800, 2700], [3600, 4500]])
            self.assertEqual(table['original_values'], [['1', '2', '3'], ['4', '5']])

    def test_m1_exact_case_set(self):
        from scripts.schedule_generator_build import validate_scope
        scope = json.loads((ROOT/'sources/schedule-generator-m1-scope.json').read_text())
        validate_scope(scope)
        self.assertEqual(len(scope['cases']), 10)
        reduced = copy.deepcopy(scope)
        reduced['cases'].pop()
        with self.assertRaises(self.error) as e:
            validate_scope(reduced)
        self.assertEqual(e.exception.code, 'scope_mismatch')

    def test_m1_wrong_configuration_weather_or_template_rejected(self):
        from scripts.schedule_generator_build import validate_scope
        scope = json.loads((ROOT/'sources/schedule-generator-m1-scope.json').read_text())
        for field in ('configuration_id', 'template', 'weather'):
            with self.subTest(field=field):
                bad = copy.deepcopy(scope)
                bad['cases'][0][field] = 'wrong'
                with self.assertRaises(self.error) as e:
                    validate_scope(bad)
                self.assertEqual(e.exception.code, 'scope_mismatch')

    def test_commercial_sampling_gate_blocks_unresolved_port(self):
        from scripts.schedule_generator_build import validate_sampling_audit
        audit = json.loads((ROOT/'data/schedule-generator/comstock-sampling-audit.json').read_text())
        validate_sampling_audit(audit)
        for mutation in ('status', 'field', 'selector'):
            bad = copy.deepcopy(audit)
            if mutation == 'status':
                bad['gate_status'] = 'pending'
            elif mutation == 'field':
                bad['parameters'][0]['decision'] = 'unresolved'
            else:
                bad['conditioning_inputs']['building_type'] = '*'
            with self.assertRaises(self.error) as e:
                validate_sampling_audit(bad)
            self.assertEqual(e.exception.code, 'sampling_gate')


if __name__ == '__main__':
    unittest.main()
