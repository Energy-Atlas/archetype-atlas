"""Locked source retrieval retries transient host failures and nothing else."""
import hashlib
import io
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

from scripts import fetch

CONTENT = b'locked source bytes'
ENTRY = {'source_id': 'example', 'path': 'data/file.json', 'url': 'https://raw.githubusercontent.com/o/r/c/data/file.json',
         'size_bytes': len(CONTENT), 'sha256': hashlib.sha256(CONTENT).hexdigest()}


class Response(io.BytesIO):
    def geturl(self):
        return ENTRY['url']


def http_error(code):
    return urllib.error.HTTPError(ENTRY['url'], code, 'error', {}, None)


class FetchRetryTests(unittest.TestCase):
    def fetch(self, *outcomes):
        calls = []

        def urlopen(request, timeout):
            calls.append(request.full_url)
            outcome = outcomes[len(calls)-1]
            if isinstance(outcome, Exception):
                raise outcome
            return Response(outcome)
        with tempfile.TemporaryDirectory() as root, patch.object(fetch.urllib.request, 'urlopen', urlopen), \
                patch.object(fetch.time, 'sleep'):
            path = fetch.fetch_file(ENTRY, root)
            return path.read_bytes(), len(calls)

    def test_transient_host_errors_are_retried_then_verified(self):
        self.assertEqual(self.fetch(http_error(503), urllib.error.URLError('reset'), CONTENT), (CONTENT, 3))

    def test_client_errors_are_not_retried(self):
        with self.assertRaises(urllib.error.HTTPError):
            self.fetch(http_error(404), CONTENT)

    def test_retries_stop_after_the_last_attempt(self):
        with self.assertRaises(urllib.error.HTTPError):
            self.fetch(*[http_error(503)]*fetch.ATTEMPTS)

    def test_corrupt_bytes_still_fail_integrity(self):
        with self.assertRaisesRegex(ValueError, 'integrity'):
            self.fetch(b'different bytes!!!!')


if __name__ == '__main__':
    unittest.main()
