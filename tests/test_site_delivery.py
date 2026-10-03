"""Delivery checks exercise artifacts rather than matching workflow source text."""
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest


class DeliveryTests(unittest.TestCase):
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
