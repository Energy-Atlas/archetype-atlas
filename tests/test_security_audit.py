import unittest

from scripts import audit


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


if __name__ == '__main__':
    unittest.main()
