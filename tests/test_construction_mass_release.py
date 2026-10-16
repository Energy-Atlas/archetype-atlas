import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from scripts.construction_distribution import load_current_release
from scripts.construction_weighting import load_profiles


class MassReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_current_release()
        cls.profiles = load_profiles()
        cls.ids = [c['id'] for c in cls.source['contexts'].values()
                   if c['reference_id'] == '90.1-2019/MediumOffice' and c['climate_zone'] in {'3B','4A'}
                   and cls.source['construction_sets'][c['construction_set_id']]['source']['building_type']=='MediumOffice']

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_mass_release'))
        from scripts import construction_mass_release
        return construction_mass_release

    def test_freeze_deduplicates_contracts_and_locks_every_payload(self):
        m = self.module()
        files = m.artifacts(self.source, self.profiles, self.ids)
        contexts = json.loads(files['contexts.json'])
        contracts = json.loads(files['contracts.json'])
        self.assertEqual(set(contexts), set(self.ids))
        self.assertEqual(len(contracts), 1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name,data in files.items():
                (root/name).parent.mkdir(parents=True, exist_ok=True)
                (root/name).write_bytes(data)
            loaded = m.load_release(root)
            self.assertEqual(loaded['contexts'], contexts)
            path = root/'contracts.json'
            path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                m.load_release(root)

    def test_new_pair_uses_same_pinned_contract_and_keeps_source_recipes(self):
        m = self.module()
        files = m.artifacts(self.source, self.profiles, self.ids)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name,data in files.items():
                (root/name).parent.mkdir(parents=True, exist_ok=True)
                (root/name).write_bytes(data)
            d,u = m.export_pair(self.ids[0], self.source, m.load_release(root))
        self.assertEqual(d['mass_accounting'], u['mass_accounting'])
        self.assertEqual(d['schema_version'], '2.1.0')
        self.assertEqual(u['schema_version'], '1.2.0')
        self.assertEqual(d['infiltration'], u['infiltration'])


if __name__ == '__main__':
    unittest.main()
