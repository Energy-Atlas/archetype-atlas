"""The reference-model lock is well formed, and extraction refuses unsafe entries."""
import hashlib
import io
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import fetch, reference_models
from scripts.common import ROOT, load_json

LOCK = load_json(ROOT/'sources/reference-models-lock.json')


class LockTests(unittest.TestCase):
    def test_every_entry_is_a_safe_pinned_archive(self):
        sources = {s['source_id'] for s in LOCK['sources']}
        paths = set()
        for entry in LOCK['files']:
            self.assertIn(entry['source_id'], sources)
            self.assertRegex(entry['sha256'], r'^[0-9a-f]{64}$')
            self.assertGreater(entry['size_bytes'], 0)
            self.assertTrue(entry['path'].endswith('.zip'), entry['path'])
            fetch.safe_url(entry['url'])
            if 'fallback_url' in entry:
                fetch.safe_url(entry['fallback_url'], fetch.FALLBACK_HOSTS)
            fetch.cache_path(entry, ROOT/'build')
            paths.add((entry['source_id'], entry['path']))
        self.assertEqual(len(paths), len(LOCK['files']))

    def test_lock_covers_both_families_and_cites_their_notices(self):
        counts = {}
        for entry in LOCK['files']:
            counts[entry['source_id']] = counts.get(entry['source_id'], 0) + 1
        self.assertEqual(counts, {'doe-reference': 48, 'pnnl-prototypes': 160})
        for source in LOCK['sources']:
            self.assertTrue((ROOT/source['license_path']).is_file(), source['license_path'])

    def test_doe_archives_cover_three_vintages_of_sixteen_types(self):
        doe = [e for e in LOCK['files'] if e['source_id'] == 'doe-reference']
        vintages = {re.match(r'v1\.4_7\.2/refbldg_[a-z-]+_(\w+?)_v1', e['path']).group(1) for e in doe}
        self.assertEqual(vintages, {'new2004', 'post1980', 'pre1980'})
        self.assertEqual(len({e['building_type'] for e in doe}), 16)


class ExtractTests(unittest.TestCase):
    def archive(self, names):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as z:
            for name in names:
                z.writestr(name, b'' if name.endswith('/') else b'idf text')
        data = buffer.getvalue()
        return data, {'source_id': 'doe-reference', 'path': 'v1.4_7.2/test.zip', 'url': 'https://www.energy.gov/x.zip',
                      'size_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

    def run_extract(self, names):
        data, entry = self.archive(names)
        with tempfile.TemporaryDirectory() as cache, tempfile.TemporaryDirectory() as out:
            path = Path(cache)/entry['source_id']/entry['path']
            path.parent.mkdir(parents=True)
            path.write_bytes(data)
            dest, count = reference_models.extract(entry, cache, out)
            return count, sorted(p.name for p in dest.rglob('*') if p.is_file())

    def test_directory_entries_are_skipped(self):
        self.assertEqual(self.run_extract(['./', '../', 'a.idf']), (1, ['a.idf']))

    def test_traversing_file_entries_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            self.run_extract(['../escape.idf'])


if __name__ == '__main__':
    unittest.main()
