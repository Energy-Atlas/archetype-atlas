"""Consumer conformance: exact query semantics over local and HTTP resources."""
import importlib.util
import json
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import tempfile
import threading
import unittest

from scripts.common import ROOT, load_atlas, load_json
from scripts.query_delivery import generate_delivery, json_bytes, descriptor


class QueryClientTests(unittest.TestCase):
    def test_strict_json_rejects_duplicate_members_and_overflow_numbers(self):
        for content in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
                        b'{"x":1e9999}', b'{"x":-1e9999}'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.module().strict_json(content)

    def test_verified_malformed_json_has_artifact_error_not_encoding_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'invalid.json'; content = b'{bad'; path.write_bytes(content)
            client = self.module().QueryClient(self.root)
            client.root = Path(d)
            with self.assertRaises(self.module().QueryError) as cm:
                client.fetch(descriptor('invalid.json', content))
            self.assertEqual(cm.exception.code, 'invalid_artifact')

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        data = load_atlas(ROOT/'data/releases/v0.2.0')
        cls.office = next(r for r in data['programs'] if
                          (r['building_type'], r['program'], r['template']) == ('MediumOffice', 'office', '90.1-2013'))
        data['programs'] = [r for r in data['programs'] if r['building_type'] in {'MediumOffice', 'HighriseApartment'}]
        for table in list(data):
            if isinstance(data[table], list) and table not in {'programs', 'schedules', 'provenance', 'source_files'}:
                data[table] = []
        supplement = load_json(ROOT/'data/resolution-releases/v0.4.0/resolutions.json')
        cls.manifest = generate_delivery(cls.root, data, {'atlas': {'version': '0.2.0', 'manifest_sha256': 'a'*64}},
                                         supplement=supplement)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.query_client'), 'Query client is not implemented')
        return __import__('scripts.query_client', fromlist=['query_client'])

    def request(self, **kwargs):
        return dict(record_type='program', fields=['people_per_m2', 'lighting_W_m2', 'gas_equipment_W_m2'],
                    where={'building_type': 'MediumOffice', 'program': 'office', 'template': '90.1-2013'}, **kwargs)

    def test_exact_projection_and_lazy_reads(self):
        client = self.module().QueryClient(self.root)
        result = client.query(self.request())
        self.assertEqual(result['match_count'], 1)
        self.assertEqual(result['records'][0]['id'], self.office['id'])
        self.assertEqual(set(result['records'][0]['fields']), set(self.request()['fields']))
        self.assertAlmostEqual(result['records'][0]['fields']['people_per_m2']['value'], 0.05381955208354861)
        self.assertIsNone(result['records'][0]['fields']['gas_equipment_W_m2']['value'])
        self.assertEqual(client.download_stats['requests'], 4)  # latest, manifest, type index, one natural packet
        before = dict(client.download_stats)
        self.assertEqual(client.query(self.request()), result)
        self.assertEqual(client.download_stats, before)
        client.fetch(result['records'][0]['evidence'])
        self.assertEqual(client.download_stats['requests'], 5)

    def test_reviewed_view_is_explicit_and_filters_its_values(self):
        client = self.module().QueryClient(self.root)
        result = client.query(self.request(view='reviewed'))
        self.assertEqual(result['records'][0]['fields']['gas_equipment_W_m2']['value'], 0)
        self.assertEqual(result['records'][0]['fields']['gas_equipment_W_m2']['status'], 'reviewed')
        request = self.request(view='reviewed'); request['where']['gas_equipment_W_m2'] = 0
        self.assertEqual(client.query(request)['match_count'], 1)
        request['view'] = 'source'
        self.assertEqual(client.query(request)['match_count'], 0)

    def test_ambiguous_variants_and_no_match_are_preserved(self):
        client = self.module().QueryClient(self.root)
        req = {'record_type': 'program', 'fields': ['lighting_W_m2'],
               'where': {'building_type': 'HighriseApartment', 'program': 'apartment_unit', 'template': '90.1-2013'}}
        result = client.query(req)
        self.assertEqual(result['match_count'], 3)
        self.assertEqual(len({r['id'] for r in result['records']}), 3)
        req['where']['variant'] = 'not-a-source-variant'
        self.assertEqual(client.query(req)['records'], [])

    def test_invalid_requests_never_ignore_fields_or_context(self):
        mod = self.module(); client = mod.QueryClient(self.root)
        for req, code in [({'record_type': 'program', 'fields': []}, 'invalid_request'),
                          ({'record_type': 'no-such-table', 'fields': ['x']}, 'unknown_record_type'),
                          ({'record_type': 'program', 'fields': ['typo']}, 'unknown_field'),
                          ({'record_type': 'program', 'fields': ['lighting_W_m2'], 'where': {'climate_zone': '5A'}}, 'unknown_filter'),
                          ({'record_type': 'program', 'fields': ['lighting_W_m2'], 'where': {'source_context': {}}}, 'invalid_request'),
                          ({'record_type': 'program', 'fields': ['lighting_W_m2'], 'limit': 1}, 'invalid_request')]:
            with self.subTest(req=req), self.assertRaises(mod.QueryError) as cm:
                client.query(req)
            self.assertEqual(cm.exception.code, code)

    def test_pin_snapshot_without_latest_and_reject_tampered_resources(self):
        mod = self.module()
        latest = load_json(self.root/'latest.json')
        client = mod.QueryClient(self.root, manifest_ref=latest['manifest'])
        self.assertEqual(client.query(self.request())['snapshot_id'], latest['snapshot_id'])
        self.assertEqual(client.download_stats['requests'], 3)
        bad = dict(latest['manifest'], sha256='0'*64)
        with self.assertRaises(mod.QueryError) as cm:
            mod.QueryClient(self.root, manifest_ref=bad)
        self.assertEqual(cm.exception.code, 'integrity_error')
        with self.assertRaises(mod.QueryError) as cm:
            client.fetch(dict(latest['manifest'], href='../escape.json'))
        self.assertEqual(cm.exception.code, 'unsafe_reference')

    def test_id_only_lookup_does_not_fetch_other_context_packets(self):
        client = self.module().QueryClient(self.root)
        result = client.query({'record_type': 'program', 'fields': ['lighting_W_m2'],
                               'where': {'id': self.office['id']}})
        self.assertEqual(result['match_count'], 1)
        self.assertEqual(client.download_stats['requests'], 4)

    def test_boolean_does_not_equal_numeric_and_absent_is_not_null(self):
        client = self.module().QueryClient(self.root)
        req = self.request(); req['where']['lighting_W_m2'] = True
        self.assertEqual(client.query(req)['match_count'], 0)
        req['where'] = {'gas_equipment_W_m2': None, 'id': self.office['id']}
        self.assertEqual(client.query(req)['match_count'], 1)

    def test_local_http_parity_under_subdirectory(self):
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(self.root.parent)))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/{self.root.name}/'
            local = self.module().QueryClient(self.root).query(self.request())
            remote = self.module().QueryClient(url).query(self.request())
            self.assertEqual(remote, local)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_incompatible_major_rejected_before_manifest_fetch(self):
        mod = self.module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            latest = load_json(self.root/'latest.json'); latest['schema_version'] = '2.0.0'
            (root/'latest.json').write_bytes(json_bytes(latest))
            with self.assertRaises(mod.QueryError) as cm:
                mod.QueryClient(root)
            self.assertEqual(cm.exception.code, 'unsupported_schema')


if __name__ == '__main__':
    unittest.main()
