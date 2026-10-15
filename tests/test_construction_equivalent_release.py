import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

from scripts.common import ROOT, load_json
from scripts.construction_distribution import load_current_release
from scripts.construction_equivalent_export import export_equivalent


class EquivalentReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_current_release()
        from scripts.construction_weighting import load_profiles
        cls.profiles = load_profiles()
        cls.context = next(c['id'] for c in cls.source['contexts'].values()
                           if c['reference_id']=='90.1-2019/MediumOffice' and c['climate_zone']=='3B'
                           and cls.source['construction_sets'][c['construction_set_id']]['source']['building_type']=='MediumOffice')

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_equivalent_release'))
        from scripts import construction_equivalent_release
        return construction_equivalent_release

    def test_pilot_freeze_hydration_and_tamper_rejection(self):
        m = self.module()
        first = m.artifacts(self.source, self.profiles, [self.context])
        self.assertEqual(first, m.artifacts(self.source, self.profiles, [self.context]))
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name, value in first.items():
                path = folder/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(value)
            d = m.export_frozen(folder, self.context)
            self.assertEqual(d, export_equivalent(self.source, self.context, self.profiles))
            with (folder/'assemblies.json').open('ab') as f:
                f.write(b' ')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                m.export_frozen(folder, self.context)

    def test_physical_references_and_conservation_are_enforced(self):
        m = self.module()
        d = export_equivalent(self.source, self.context, self.profiles)
        m.validate_document(d, self.source, self.profiles)
        invalid = copy.deepcopy(d)
        aid = invalid['components']['ExteriorWall']['assembly_id']
        invalid['assemblies'][aid]['layers'][0]['C'] *= 2
        with self.assertRaisesRegex(ValueError, 'capacity'):
            m.validate_document(invalid, self.source, self.profiles)
        invalid = copy.deepcopy(d)
        del invalid['assemblies'][aid]
        with self.assertRaisesRegex(ValueError, 'reference'):
            m.validate_document(invalid, self.source, self.profiles)

    def test_original_frozen_release_remains_hydratable(self):
        document = self.module().export_frozen(ROOT/'data/construction-equivalent-releases/v1.0.0',self.context)
        self.assertEqual(document['schema_version'],'1.0.0')
        self.assertEqual(document['detailed_context_id'],self.context)


if __name__ == '__main__':
    unittest.main()
