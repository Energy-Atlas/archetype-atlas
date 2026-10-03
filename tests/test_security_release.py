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
