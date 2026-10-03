import copy
import json
import pathlib
import tempfile
import unittest

from scripts import audit, release
from scripts.build import build_atlas, write_atlas


class SecurityReleaseTests(unittest.TestCase):
    def test_scan_rejects_credentials_without_echoing_them(self):
        token = 'ghp_' + 'a'*32
        findings = audit.scan_blob('settings.txt', ('key=' + token).encode())
        self.assertTrue(findings)
        self.assertNotIn(token, str(findings))
        self.assertTrue(audit.scan_blob('.env', b'anything'))
        self.assertTrue(audit.scan_blob('settings.txt', b'https://' + b'name:password' + b'@example.com'))
        self.assertFalse(audit.scan_blob('.env.example', b'# No credentials needed.\n'))

    def test_adjacent_empty_key_examples_are_not_credentials(self):
        self.assertEqual(audit.scan_blob('brief.md', b'OPENAI_API_KEY=\nANTHROPIC_API_KEY=\n'), [])
        self.assertTrue(audit.scan_blob('config.txt', b'API_KEY=' + b'a'*32))

    def test_release_rejects_plausible_drift_and_missing_semantic_tables(self):
        data = build_atlas()
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            processed = root/'processed'
            wrong = copy.deepcopy(data)
            next(p for p in wrong['programs'] if p['program'] == 'office')['lighting_W_m2'] += 0.1
            write_atlas(wrong, processed)
            with self.assertRaises(ValueError):
                release.freeze_release(processed, root/'wrong')
            incomplete = copy.deepcopy(data)
            removed = {'envelope_components', 'systems', 'mappings', 'efficiency_rules', 'residential_options', 'commercial_options'}
            for table in removed:
                incomplete[table] = []
            incomplete['provenance'] = [p for p in incomplete['provenance'] if p['table'] not in removed]
            write_atlas(incomplete, processed)
            with self.assertRaises(ValueError):
                release.freeze_release(processed, root/'incomplete')

    def test_release_immutable_manifest_and_hash_verification(self):
        data = build_atlas()
        with tempfile.TemporaryDirectory() as d:
            processed, target = pathlib.Path(d)/'processed', pathlib.Path(d)/'v0.1.0'
            write_atlas(data, processed)
            release.freeze_release(processed, target)
            self.assertEqual(release.verify_release(target), [])
            manifest_path = target/'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            original = manifest_path.read_bytes()
            manifest['counts']['programs'] += 1
            manifest_path.write_text(json.dumps(manifest))
            self.assertTrue(release.verify_release(target))
            manifest_path.write_bytes(original)
            with self.assertRaises(FileExistsError):
                release.freeze_release(processed, target)
            with (target/'programs.json').open('a') as f:
                f.write(' ')
            self.assertTrue(release.verify_release(target))


if __name__ == '__main__':
    unittest.main()
