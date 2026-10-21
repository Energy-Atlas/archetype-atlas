"""Frozen combined delivery must reject altered bytes and retain the full denominator."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


class FoundationReleaseTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_foundation_release'))
        from scripts import construction_foundation_release
        return construction_foundation_release

    def test_reproduction_and_tamper_detection(self):
        m=self.module();ids=['construction-set-beb5e983644344ce44d4a299']
        first=m.artifacts(context_ids=ids);self.assertEqual(first,m.artifacts(context_ids=ids))
        manifest=json.loads(first['manifest.json'])
        self.assertEqual(manifest['coverage']['denominator'],{'suites':177,'contexts':3320})
        self.assertFalse(manifest['coverage']['complete'])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,data in first.items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'partial'):m.load_release(root)
            r=m.load_release(root,require_full=False)
            self.assertEqual(set(r['contexts']),set(ids))
            p=root/'assemblies.json';data=json.loads(p.read_bytes());data[next(iter(data))]['f_W_m_K']=99
            p.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'checksum'):m.load_release(root,require_full=False)


if __name__=='__main__':unittest.main()
