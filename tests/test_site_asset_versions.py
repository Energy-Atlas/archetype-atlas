"""Asset identity follows bytes, preventing mixed construction UI revisions."""
import importlib.util
import tempfile
import unittest
from pathlib import Path


class AssetVersionTests(unittest.TestCase):
    def test_changed_asset_bytes_change_url_without_touching_external_or_material_assets(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.site_asset_versions'))
        from scripts.site_asset_versions import version_asset_urls
        with tempfile.TemporaryDirectory() as d:
            assets=Path(d);(assets/'construction.js').write_bytes(b'old')
            original='<script src="/archetype-atlas/assets/construction.js"></script><link href="../../assets/site.css"><script src="https://other.example/assets/construction.js"></script><link href="/archetype-atlas/assets/stylesheets/main.hashed.css">'
            before=version_asset_urls(original,assets)
            self.assertIn('/assets/construction.js?v=',before)
            self.assertIn('https://other.example/assets/construction.js',before)
            self.assertIn('href="../../assets/site.css"',before)
            self.assertIn('/assets/stylesheets/main.hashed.css',before)
            self.assertEqual(before,version_asset_urls(before,assets))
            (assets/'construction.js').write_bytes(b'new')
            after=version_asset_urls(before,assets)
            self.assertNotEqual(before,after)
            self.assertEqual(after.count('?v='),1)
