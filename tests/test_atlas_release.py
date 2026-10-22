"""ADR 0036 release folder: the three writers' files, notices and a manifest of every file."""
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts.common import ROOT

FOLDERS = (('90.1-2019', 'MediumOffice'),)


class AtlasReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts import atlas_release
        cls.module = atlas_release
        cls.files = atlas_release.assemble(FOLDERS)
        cls.manifest = json.loads(cls.files['manifest.json'])

    def test_contains_every_writer_and_the_notices(self):
        files = self.files
        self.assertTrue(any('/programs/source/' in p for p in files))
        self.assertTrue(any('/constructions/' in p for p in files))
        for table in ('systems', 'components', 'services', 'water', 'schedules'):
            self.assertIn(f'commercial/90-1-2019/medium-office/{table}.json', files)
        self.assertIn('evidence/glossary.json', files)
        self.assertEqual(files['LICENSE'], (ROOT/'LICENSE').read_bytes())
        self.assertIn('README.md', files)
        glossary = json.loads(files['evidence/glossary.json'])
        cited = {Path(s['license_path']).name for s in glossary['source_files'].values() if s.get('license_path')}
        shipped = {Path(p).name for p in files if p.startswith('notices/')}
        self.assertTrue(cited <= shipped, cited - shipped)
        self.assertTrue({p.name for p in (ROOT/'data/construction-foundation-releases/v1.0.0/notices').iterdir()} <= shipped)
        for path in files:
            if path.startswith('notices/'):
                self.assertEqual(files[path], (ROOT/'sources/licenses'/Path(path).name).read_bytes())

    def test_manifest_lists_every_file_with_its_checksum(self):
        listed = self.manifest['files']
        self.assertEqual(set(listed), set(self.files) - {'manifest.json'})
        for path, entry in listed.items():
            data = self.files[path]
            self.assertEqual(entry, {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}, path)
        self.assertEqual(self.manifest['release'], '1.0.0')
        self.assertEqual(self.manifest['scope'], 'commercial')
        self.assertIsNone(self.manifest['base_release'])
        self.assertIn('residential', ' '.join(self.manifest['deferred']))

    def test_manifest_pins_inputs_and_counts_records(self):
        inputs = self.manifest['input_sha256']
        for path in ('data/definition-releases/v0.1.1/manifest.json', 'data/resolution-releases/v0.4.0/manifest.json',
                     'data/construction-foundation-releases/v1.0.0/manifest.json', 'scripts/atlas_programs.py',
                     'scripts/atlas_constructions.py', 'scripts/atlas_systems.py', 'scripts/atlas_release.py'):
            self.assertEqual(inputs[path], hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), path)
        counts = self.manifest['counts']
        self.assertEqual(counts['programs'], sum('/programs/' in p for p in self.files))
        self.assertEqual(counts['construction_sets'], sum('/constructions/' in p for p in self.files))
        systems = json.loads(self.files['commercial/90-1-2019/medium-office/systems.json'])
        self.assertEqual(counts['hvac_systems'], len(systems))
        self.assertEqual(counts['folders'], 1)

    def test_files_are_canonical_and_commercial_only(self):
        for path, data in self.files.items():
            self.assertLess(len(data), 25_000_000, path)
            self.assertNotIn(b'\r', data, path)
            self.assertFalse(re.search(r'resstock|residential', path, re.I) and not path.startswith('notices/'), path)

    def test_assembly_is_deterministic(self):
        self.assertEqual(self.files, self.module.assemble(FOLDERS))

    def test_verify_accepts_the_written_folder_and_rejects_changes(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)/'v1.0.0'
            self.module.write(self.files, target)
            self.module.verify(target)
            program = next(target.glob('commercial/*/*/programs/source/*.json'))
            original = program.read_bytes()
            program.write_bytes(original.replace(b'"', b"'", 1))
            with self.assertRaisesRegex(ValueError, 'checksum|bytes'):
                self.module.verify(target)
            program.write_bytes(original)
            (target/'stray.json').write_text('{}\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'not in the manifest'):
                self.module.verify(target)
            (target/'stray.json').unlink()
            program.unlink()
            with self.assertRaisesRegex(ValueError, 'missing'):
                self.module.verify(target)

    def test_write_replaces_a_previous_folder_exactly(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)/'v1.0.0'
            target.mkdir()
            (target/'old.json').write_text('{}\n', encoding='utf-8')
            self.module.write(self.files, target)
            self.assertFalse((target/'old.json').exists())
            self.module.verify(target)

    def test_committed_release_verifies(self):
        target = ROOT/'data/atlas-releases/v1.0.0'
        if not target.exists():
            self.skipTest('Release folder not written yet')
        self.module.verify(target)


if __name__ == '__main__':
    unittest.main()
