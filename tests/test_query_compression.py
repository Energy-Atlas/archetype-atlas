"""Compression is a transport encoding; consumers still receive exact JSON."""
import gzip
from pathlib import Path
import tempfile
import unittest

from scripts.common import load_json
from scripts.query_client import QueryClient
from tests import test_query_delivery as fixtures


class QueryCompressionTests(unittest.TestCase):
    def test_large_resources_use_declared_gzip_and_client_reads_identical_values(self):
        fixtures.QueryDeliveryTests.setUpClass(); fixture = fixtures.QueryDeliveryTests()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest = fixture.generate(root)
            client = QueryClient(root)
            index = client.fetch(manifest['record_types']['program']['index'])
            ref = index['routes'][0]['packets'][0]
            self.assertEqual(ref.get('encoding'), 'gzip', 'Generated large JSON must fit static publication')
            self.assertEqual(len(gzip.decompress((root/ref['href']).read_bytes())), ref['decoded_size_bytes'])
            result = client.query({'record_type': 'program', 'fields': ['lighting_W_m2'],
                                   'where': {'id': fixture.office['id']}})
            self.assertEqual(result['records'][0]['fields']['lighting_W_m2']['value'], 8.82640654170197)


if __name__ == '__main__':
    unittest.main()
