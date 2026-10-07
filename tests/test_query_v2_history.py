import tempfile
import unittest
from pathlib import Path
from scripts.definition_contract import DefinitionBundle
from scripts.query_v2 import generate_delivery,QueryClient,validate_delivery
from scripts.query_history import export_history,restore_history


class V2HistoryTests(unittest.TestCase):
    def test_major_two_retains_prior_manifest_and_detects_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'one';target=Path(temp)/'two'
            first=generate_delivery(DefinitionBundle(),root)
            export_history(root,major=2)
            self.assertTrue(restore_history(root,target,major=2))
            second=generate_delivery(DefinitionBundle(dependencies={'variant':'two'}),target)
            export_history(target,major=2)
            self.assertNotEqual(first['snapshot_id'],second['snapshot_id'])
            self.assertTrue((target/'snapshots'/first['snapshot_id']/'manifest.json').exists())
            self.assertEqual(validate_delivery(target),[])
            resource=next((target/'resources').iterdir());resource.write_bytes(b'bad')
            self.assertTrue(validate_delivery(target))

    def test_only_explicit_first_publication_allows_absent_history(self):
        with tempfile.TemporaryDirectory() as temp:
            missing=Path(temp)/'absent';target=Path(temp)/'target'
            with self.assertRaises(FileNotFoundError):restore_history(missing,target,major=2)
            self.assertFalse(restore_history(missing,target,allow_missing=True,major=2))


if __name__=='__main__':unittest.main()
