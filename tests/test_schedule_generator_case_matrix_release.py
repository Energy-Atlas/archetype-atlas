"""Layout-3 manifest/verifier contract on small synthetic releases.

The real builder's layout3_manifest describes a tiny synthetic member set, and
the standalone reproducer's verify_v3_release must accept exactly that and
reject transport, version, inventory and provenance tampering. No generation
or reference decoding runs here; the full release is profiled separately.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from atlas_schedules.canonical import canonical
from scripts import schedule_generator_case_matrix_release as builder
from scripts import schedule_generator_case_matrix_reproduction as reproduction
from scripts.schedule_generator_release import _archive

ROOT = Path(__file__).resolve().parents[1]
CASES = ('unit-case', 'commercial-case')


def synthetic():
    scope = {'milestone_id': 'A1', 'scope_version': 'synthetic-1', 'cases': [{'case_id': 'p1'}], 'service_cases': []}
    scope_bytes = canonical(scope)
    policy_bytes = canonical({'ignored_administrative_fields': ['rng.python_version']})
    resources = {'schema_version': '1.0.0', 'service_cases': [], 'resources': [
        {'kind': 'reference', 'key': 'm1-scope', 'path': 'reference/m1-scope.json',
         'sha256': hashlib.sha256(scope_bytes).hexdigest(), 'size_bytes': len(scope_bytes)},
        {'kind': 'reference', 'key': 'comparison-policy', 'path': 'reference/comparison-policy.json',
         'sha256': hashlib.sha256(policy_bytes).hexdigest(), 'size_bytes': len(policy_bytes)}]}
    resources['resource_set_id'] = 'resources-'+hashlib.sha256(canonical(resources)).hexdigest()
    def wrapper(owners): return {'schema_version': '1.2.0', 'seed': 42, 'params': {
        'schema_version': '1.2.0', 'resource_set_id': resources['resource_set_id'], 'instances': [{'key': f'o{n}'} for n in range(owners)]}}
    request = wrapper(5)
    mapping = {'cases': [{'case_id': CASES[0], 'request': wrapper(2)}, {'case_id': CASES[1], 'request': wrapper(3)}],
               'full_constituent_order': ['a', 'b', 'c', 'd', 'e', 'f'],
               'typed_slot_obligations': [{'demands': [1], 'controls': [1, 2]}, {'demands': [], 'controls': [3]}]}
    runner = (ROOT/'scripts/schedule_generator_case_matrix_reproduction.py').read_bytes()
    files = {'sources/schedule-generator-m1-scope.json': scope_bytes, 'atlas_schedules/data/reference/m1-scope.json': scope_bytes,
             'atlas_schedules/data/reference/comparison-policy.json': policy_bytes,
             'atlas_schedules/data/manifest.json': canonical(resources),
             'data/schedule-generator/comstock-sampling-audit.json': b'{"gate_status":"passed"}\n',
             'references/all-cases-request.json': canonical(request), '__main__.py': builder.BOOTSTRAP_V3}
    for name in ('atlas_schedules/__main__.py', 'atlas_schedules/generator.py', 'atlas_schedules/contract.py', 'atlas_schedules/resources.py'):
        files[name] = b'# synthetic\n'
    for case in mapping['cases']: files['references/case-matrix/'+case['case_id']+'.request.json'] = canonical(case['request'])
    for name in builder.INPUT_FILES: files['case_matrix/inputs/'+name] = name.encode()
    for name in builder.CODE: files['case_matrix/'+name] = b'# packaged code\n'
    for name in reproduction.PRODUCERS: files['provenance/implementation/'+name] = b'# producer\n'
    files['provenance/implementation/'+reproduction.RUNNER] = runner
    return files, scope, request, mapping, runner


def write_release(target, files, scope, request, mapping, runner, *, reference=b'synthetic reference', mutate=None):
    archive = _archive(files)
    manifest = builder.layout3_manifest('9.9.9', files, scope, request, mapping, archive, runner, reference)
    if mutate: mutate(manifest)
    target.mkdir(parents=True); (target/'references').mkdir()
    (target/'generator.zip').write_bytes(archive); (target/'reproduce.py').write_bytes(runner)
    (target/'references/all-cases-bundle.json.gz').write_bytes(reference)
    (target/'manifest.json').write_bytes(canonical(manifest))
    return manifest


class Layout3VerifierTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='layout3-'); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.parts = synthetic(); self.count = 0

    def release(self, files=None, mutate=None, **kwargs):
        self.count += 1; target = self.root/f'r{self.count}'
        parts = list(copy.deepcopy(self.parts))
        if files is not None: parts[0] = files
        write_release(target, *parts, mutate=mutate, **kwargs)
        return target

    def assertRejected(self, target, text=''):
        with self.assertRaises(ValueError) as caught: reproduction.verify_v3_release(target)
        self.assertIn(text, str(caught.exception))

    def test_builder_manifest_verifies(self):
        verified = reproduction.verify_v3_release(self.release())
        manifest = verified['manifest']
        self.assertEqual(manifest['schema_version'], '3.0.0')
        self.assertEqual(manifest['case_matrix']['case_order'], list(CASES))
        self.assertEqual([c['requested_owners'] for c in manifest['case_matrix']['cases']], [2, 3])
        self.assertEqual(manifest['public_counts'], {'requested_owners': 5, 'constituents': 6, 'schedules': 2, 'bindings': 4})
        self.assertEqual(manifest['reference']['producer_python_version'], '3.11.9')
        self.assertEqual(set(manifest['implementation_sources']), reproduction.PRODUCERS)

    def test_version_and_layout_are_explicit_both_ways(self):
        self.assertRejected(self.release(mutate=lambda m: m.update(schema_version='2.0.0')), 'Unsupported release layout')
        from scripts.schedule_generator_release_reproduction import verify_v2_release
        with self.assertRaises(ValueError): verify_v2_release(self.release())

    def test_transport_and_inventory_tampering_fail(self):
        target = self.release(); (target/'extra.txt').write_bytes(b'x')
        self.assertRejected(target, 'Release file inventory differs')
        target = self.release(); (target/'reproduce.py').write_bytes(b'# changed\n')
        self.assertRejected(target, 'Release file hash/size differs')
        target = self.release(); (target/'references/all-cases-bundle.json.gz').write_bytes(b'other reference')
        self.assertRejected(target, 'Release file hash/size differs')
        target = self.release()
        with zipfile.ZipFile(target/'generator.zip') as archive:
            members = {n: archive.read(n) for n in archive.namelist()}
        members['case_matrix/schedule_generator_case_matrix.py'] = b'# swapped\n'
        (target/'generator.zip').write_bytes(_archive(members))
        self.assertRejected(target, 'Release file hash/size differs')

    def test_case_matrix_descriptor_tampering_fails(self):
        def drop_case(m): m['case_matrix']['cases'].pop(); m['case_matrix']['case_order'].pop()
        self.assertRejected(self.release(mutate=drop_case), 'Case owners do not partition')
        def reorder(m): m['case_matrix']['case_order'].reverse()
        self.assertRejected(self.release(mutate=reorder), 'Case descriptors differ')
        def bad_owner_count(m): m['case_matrix']['cases'][0]['requested_owners'] = 3; m['case_matrix']['cases'][1]['requested_owners'] = 2
        self.assertRejected(self.release(mutate=bad_owner_count), 'Case owner count differs')
        def drop_input(m): m['case_matrix']['inputs'].pop('full-request.json.gz')
        self.assertRejected(self.release(mutate=drop_input), 'Invalid case-matrix inputs')
        def version(m): m['reference']['producer_python_version'] = '3.11'
        self.assertRejected(self.release(mutate=version), 'Invalid producer version')

    def test_layout2_shaped_manifest_is_rejected(self):
        def as_layout2(m):
            m.pop('case_matrix'); m['schema_version'] = '2.0.0'; m['reference'].pop('producer_python_version')
        self.assertRejected(self.release(mutate=as_layout2), 'Invalid layout-3 manifest fields')

    def test_zip_internal_tampering_fails_even_with_matching_file_identity(self):
        target = self.root/'inner'; files, scope, request, mapping, runner = copy.deepcopy(self.parts)
        original = builder.layout3_manifest('9.9.9', files, scope, request, mapping, _archive(files), runner, b'ref')
        tampered = dict(files); tampered['case_matrix/schedule_generator_case_matrix.py'] = b'# packaged CODE\n'  # same size
        archive = _archive(tampered)
        original['files']['generator.zip'] = {'sha256': hashlib.sha256(archive).hexdigest(), 'size_bytes': len(archive)}
        target.mkdir(); (target/'references').mkdir()
        (target/'generator.zip').write_bytes(archive); (target/'reproduce.py').write_bytes(runner)
        (target/'references/all-cases-bundle.json.gz').write_bytes(b'ref'); (target/'manifest.json').write_bytes(canonical(original))
        self.assertRejected(target, 'ZIP member identity differs')

    def test_scope_policy_and_resource_inventory_checks(self):
        def label(m): m['scope']['scope_version'] = 'other'
        self.assertRejected(self.release(mutate=label), 'Scope label differs')
        def services(m): m['scope']['service_case_ids'] = ['extra']; m['scope']['service_case_count'] = 1
        self.assertRejected(self.release(mutate=services), 'Physical service/configuration inventory differs')
        files = dict(self.parts[0]); resources = json.loads(files['atlas_schedules/data/manifest.json'])
        resources['resources'] = resources['resources'][:1]; resources.pop('resource_set_id')
        resources['resource_set_id'] = 'resources-'+hashlib.sha256(canonical(resources)).hexdigest()
        files['atlas_schedules/data/manifest.json'] = canonical(resources); files.pop('atlas_schedules/data/reference/comparison-policy.json')
        for name in ('references/all-cases-request.json',) + tuple('references/case-matrix/'+c+'.request.json' for c in CASES):
            value = json.loads(files[name]); value['params']['resource_set_id'] = resources['resource_set_id']; files[name] = canonical(value)
        parts = list(copy.deepcopy(self.parts)); parts[0] = files
        for case in parts[3]['cases']: case['request']['params']['resource_set_id'] = resources['resource_set_id']
        self.count += 1; target = self.root/f'r{self.count}'; write_release(target, *parts)
        self.assertRejected(target, 'Exact packaged comparison policy required')

    def test_runner_must_equal_its_provenance(self):
        files = dict(self.parts[0]); files['provenance/implementation/'+reproduction.RUNNER] = b'# other runner\n'
        self.assertRejected(self.release(files=files), 'Shipped runner differs from producer provenance')

    def test_bootstrap_refuses_zip_only_reproduction(self):
        target = self.release()
        result = subprocess.run([sys.executable, '-I', '-S', str(target/'generator.zip'), '--reproduce'],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 2); self.assertIn('layout 3', result.stderr)


class BuilderAndProfilerTests(unittest.TestCase):
    def test_reference_authentication_rejects_foreign_truncated_and_trailing_gzip(self):
        import gzip
        from unittest.mock import patch
        decoded = b'{"a":1}\n' * 1000; good = gzip.compress(decoded, mtime=0)
        declared = {'sha256': hashlib.sha256(good).hexdigest(), 'size_bytes': len(good),
                    'decoded_sha256': hashlib.sha256(decoded).hexdigest(), 'decoded_size_bytes': len(decoded),
                    'producer_python_version': '3.11.9'}
        with tempfile.TemporaryDirectory(prefix='reference-') as folder, patch.dict(builder.REFERENCE, declared):
            path = Path(folder)/'r.gz'; path.write_bytes(good)
            self.assertEqual(builder.authenticate_reference(path), good)
            for raw in (gzip.compress(b'other', mtime=0), good[:-8], good+b'\0'):
                path.write_bytes(raw)
                with self.subTest(size=len(raw)), self.assertRaises(ValueError): builder.authenticate_reference(path)
            # Same compressed identity declared for a trailing-byte file still fails on the stream itself.
            trailing = good+b'\0'; path.write_bytes(trailing)
            with patch.dict(builder.REFERENCE, {'sha256': hashlib.sha256(trailing).hexdigest(), 'size_bytes': len(trailing)}):
                with self.assertRaises(ValueError): builder.authenticate_reference(path)

    def test_run_guarded_reports_exit_timeout_and_output(self):
        with tempfile.TemporaryDirectory(prefix='guarded-') as folder:
            ok = builder.run_guarded([sys.executable, '-c', 'print("hello")'], folder, 60)
            self.assertTrue(ok['passed']); self.assertIn('hello', ok['stdout_tail'])
            failed = builder.run_guarded([sys.executable, '-c', 'import sys;sys.exit(4)'], folder, 60)
            self.assertEqual((failed['passed'], failed['exit_code'], failed['stop']), (False, 4, None))
            slow = builder.run_guarded([sys.executable, '-c', 'import time;time.sleep(30)'], folder, 1)
            self.assertEqual((slow['passed'], slow['stop']), (False, 'TIMEOUT'))
            if sys.platform == 'win32':
                self.assertGreater(ok['child_peak_memory']['peak_working_set_bytes'], 4*1024*1024)


if __name__ == '__main__': unittest.main()
