import tempfile
import unittest
from pathlib import Path
from scripts.definition_contract import DefinitionBundle
from scripts.definition_release import freeze, verify


class ReleaseTests(unittest.TestCase):
    def test_release_is_immutable_and_detects_corruption(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'release'
            bundle=DefinitionBundle(schema_version='1.0.0', scope='pilot')
            manifest=freeze(bundle,path)
            self.assertEqual(verify(path).errors,[])
            self.assertEqual(freeze(bundle,path),manifest)
            (path/'programs.json').write_text('[] changed',encoding='utf-8')
            self.assertTrue(verify(path).errors)
            with self.assertRaises(ValueError):freeze(bundle,path)


if __name__=='__main__': unittest.main()
