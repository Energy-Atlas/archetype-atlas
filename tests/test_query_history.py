"""Clean static builds retain previous pinned snapshot URLs."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

from scripts.common import load_json
from scripts.query_delivery import generate_delivery, validate_delivery
from tests import test_query_delivery as fixtures


class QueryHistoryTests(unittest.TestCase):
    def test_corrupt_previous_snapshot_is_rejected_even_when_latest_is_valid(self):
        from scripts.query_history import export_history
        fixture = fixtures.QueryDeliveryTests(); fixtures.QueryDeliveryTests.setUpClass()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); old = fixture.generate(root)
            data = fixture.pilot(); data['programs'][0] = dict(data['programs'][0], lighting_W_m2=9)
            fixture.generate(root, data)
            (root/'snapshots'/old['snapshot_id']/'manifest.json').write_text('{}')
            self.assertTrue(validate_delivery(root), 'Retention must verify every pinned snapshot')
            with self.assertRaises(ValueError):
                export_history(root)

    def test_clean_publisher_restores_previous_snapshot_without_changing_its_bytes(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.query_history'), 'Snapshot retention is not implemented')
        from scripts.query_history import export_history, restore_history
        fixture = fixtures.QueryDeliveryTests(); fixtures.QueryDeliveryTests.setUpClass()
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            old, clean = Path(a), Path(b)
            manifest = fixture.generate(old)
            export_history(old)
            latest = load_json(old/'latest.json')
            self.assertIn('history', latest)
            restore_history(old, clean)
            old_manifest = 'snapshots/' + manifest['snapshot_id'] + '/manifest.json'
            self.assertEqual((clean/old_manifest).read_bytes(), (old/old_manifest).read_bytes())
            data = fixture.pilot(); data['programs'][0] = dict(data['programs'][0], lighting_W_m2=9)
            fixture.generate(clean, data)
            self.assertTrue((clean/old_manifest).exists())
            self.assertEqual(validate_delivery(clean), [])


if __name__ == '__main__':
    unittest.main()
