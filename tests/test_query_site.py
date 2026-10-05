"""The public site is a self-contained consumer handoff."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

from scripts.common import ROOT, load_json
from scripts.query_delivery import validate_delivery
from tests import test_query_delivery as fixtures


class QuerySiteTests(unittest.TestCase):
    def test_machine_docs_publish_verified_schemas_and_conformance_vectors(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.query_site'), 'Query site integration is not implemented')
        from scripts.query_site import publish_query_delivery
        fixture = fixtures.QueryDeliveryTests(); fixtures.QueryDeliveryTests.setUpClass()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            summary = publish_query_delivery(root, inputs=(fixture.pilot(),
                {'atlas': {'version': '0.2.0', 'manifest_sha256': 'a'*64}}, None, None, None, None, None))
            delivery = root/'delivery/v1'
            self.assertEqual(validate_delivery(delivery), [])
            self.assertEqual(summary['program_count'], 1)
            self.assertTrue((delivery/'schemas/query-request.schema.json').is_file())
            vectors = load_json(delivery/'examples/conformance.json')
            office = next(v for v in vectors['cases'] if v['name'] == 'medium-office-source')
            self.assertEqual(office['response']['match_count'], 1)
            self.assertEqual(office['response']['records'][0]['fields']['lighting_W_m2']['value'], 8.82640654170197)
            self.assertEqual(office['response']['records'][0]['fields']['ventilation_m3_s_m2']['unit'], 'm3/s/m2')
            self.assertTrue((delivery/'history.zip').is_file())


if __name__ == '__main__':
    unittest.main()
