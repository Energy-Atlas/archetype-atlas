"""Delivery checks exercise artifacts rather than matching workflow source text."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class DeliveryTests(unittest.TestCase):
    def test_repeated_original_arrays_share_one_source_value_with_working_anchor(self):
        site = self.module('site')
        original = [{'quoted': '<unsafe>', 'hours': list(range(24))}]
        field = {'status': 'known', 'original_field': 'source row', 'original_units': None,
                 'original_value': original, 'transformation': 'Retain original'}
        prov = {'locator': '/record/0', 'extraction_date': '2026-10-05', 'notes': 'note',
                'fields': {'a': field, 'b': dict(field)}}
        source = {'version': 'abc', 'url': 'https://example.org/source', 'project': 'project',
                  'path': 'source.json', 'sha256': '0'*64, 'license_path': 'LICENSE'}
        rendered = site.provenance_html(prov, source, 'records/record.md', 'v0.2.0')
        self.assertEqual(rendered.count('&lt;unsafe&gt;'), 1)
        self.assertIn('id="original-a"', rendered)
        self.assertIn('href="#original-a"', rendered)
        self.assertIn('id="evidence-b"', rendered)

    def test_publication_size_rejects_a_site_above_the_selected_ceiling(self):
        checker=self.module('site_check')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'asset').write_bytes(b'123456')
            self.assertEqual(checker.check_size(root,6),[])
            self.assertTrue(checker.check_size(root,5))

    def test_compact_presentation_json_preserves_values_and_rejects_nonfinite_data(self):
        site=self.module('site')
        packet={'record':{'original':None,'zero':0,'SI_value':0.82/0.09290304,
                         'note':'Literal <tag>, unicode °C and newline\ntext'},
                'evidence':[{'value':list(range(24))} for _ in range(3)]}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'packet.json'
            site.write_site_json(path,packet)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')),packet)
            self.assertLess(path.stat().st_size,len(json.dumps(packet,indent=2).encode()))
            with self.assertRaises(ValueError):
                site.write_site_json(path,{'invalid':float('nan')})

    def test_generated_directory_rename_retries_transient_windows_lock(self):
        site=self.module('site')
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'stage';target=Path(d)/'output';source.mkdir()
            (source/'result.txt').write_text('verified artifact')
            original=Path.rename; calls=[]
            def temporarily_locked(path,destination):
                calls.append(path)
                if len(calls)==1:
                    raise PermissionError('Temporary Windows file lock')
                return original(path,destination)
            with patch.object(Path,'rename',temporarily_locked):
                site.rename_generated(source,target)
            self.assertEqual((target/'result.txt').read_text(),'verified artifact')
            self.assertEqual(len(calls),2)

    def module(self, name):
        self.assertIsNotNone(importlib.util.find_spec('scripts.' + name), name + ' is not implemented')
        return __import__('scripts.' + name, fromlist=[name])

    def test_asset_tampering_and_path_escape_fail_closed(self):
        assets = self.module('site_assets')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'plot.js').write_text('wrong')
            entry = {'path': 'plot.js', 'size_bytes': 5, 'sha256': '0'*64}
            with self.assertRaisesRegex(ValueError, 'checksum'):
                assets.verify_asset(root, entry)
            with self.assertRaisesRegex(ValueError, 'escape'):
                assets.verify_asset(root, {**entry, 'path': '../escape.js'})

    def test_link_checker_rejects_an_empty_or_incomplete_build(self):
        checker = self.module('site_check')
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(checker.check_links(Path(d)), 'An empty build must not pass verification')

    def test_link_checker_under_project_subpath_detects_broken_fragments_and_assets(self):
        checker = self.module('site_check')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'index.html').write_text('<a href="entry/#value">entry</a><script src="asset.js"></script>')
            (root/'entry').mkdir()
            (root/'entry/index.html').write_text('<p id="value">0</p><a href="/archetype-atlas/">Home</a>')
            (root/'asset.js').write_text('/* ok */')
            self.assertEqual(checker.check_links(root, '/archetype-atlas/'), [])
            (root/'entry/index.html').write_text('<p id="different">0</p>')
            self.assertTrue(any('fragment' in e for e in checker.check_links(root, '/archetype-atlas/')))
            (root/'asset.js').unlink()
            self.assertTrue(any('asset.js' in e for e in checker.check_links(root, '/archetype-atlas/')))

    def test_link_checker_rejects_an_origin_root_link_that_drops_project_prefix(self):
        checker = self.module('site_check')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'index.html').write_text('<a href="/releases/v0.2.0/">Broken project URL</a>')
            errors = checker.check_links(root, '/archetype-atlas/')
            self.assertTrue(any('prefix' in e for e in errors), errors)

    def test_preview_transfer_handles_a_disconnecting_browser(self):
        smoke = self.module('site_smoke')
        class DisconnectedClient:
            def write(self, data):
                raise ConnectionAbortedError('Peer closed the response during navigation')
        handler = object.__new__(smoke.Handler)
        handler.copyfile(io.BytesIO(b'profile'), DisconnectedClient())


if __name__ == '__main__':
    unittest.main()
