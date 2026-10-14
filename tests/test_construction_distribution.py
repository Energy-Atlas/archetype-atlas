"""Current complete-set delivery preserves embedded source rules and archives."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from scripts.construction_hotel_applicability import load_current_release


class ConstructionDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.source=load_current_release()

    def implementation(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_distribution'))
        from scripts import construction_distribution
        return construction_distribution

    def test_exact_complete_set_census_and_unchanged_consumer_content(self):
        module=self.implementation();current,selection,evidence=module.build_distribution(self.source)
        self.assertEqual(len(current['construction_sets']),177)
        self.assertEqual(len(current['contexts']),3320)
        self.assertEqual({p['scope'] for p in current['construction_sets'].values()},{'building','whole_dwelling'})
        for table in ('component_configurations','selector_receipts','assemblies','materials','evidence','metadata'):
            self.assertEqual(current[table],self.source[table])
        for identity,c in current['contexts'].items():self.assertEqual(c,self.source['contexts'][identity])
        self.assertEqual(selection['coverage']['embedded_space_contexts'],1470)
        self.assertEqual(len(selection['retired_space_type_ids']),47)
        self.assertFalse(evidence['consumer_selectable']);self.assertEqual(len(evidence['contexts']),8)
        for identity,c in evidence['contexts'].items():
            self.assertEqual(c,self.source['contexts'][identity])
            self.assertIn(c['climate_zone'],('0A','0B'))
            self.assertIn(c['reference_id'].split('/')[1],('MediumOffice','LargeOffice'))

    def test_missing_embedded_rule_is_rejected(self):
        module=self.implementation();source=copy.deepcopy(self.source)
        c=next(c for c in source['contexts'].values() if c['construction_set_id']=='construction-c6985aaff2845cac856a73ab' and c['climate_zone']=='4A')
        config=source['component_configurations'][c['configuration_id']]
        for component in config['components'].values():
            component['assignments']=[a for a in component['assignments'] if a['when'].get('space_type')!='GuestRoom']
        with self.assertRaisesRegex(ValueError,'embedded'):module.build_distribution(source)

    def test_source_selector_alternative_cannot_be_dropped(self):
        module=self.implementation();source=copy.deepcopy(self.source)
        c=next(c for c in source['contexts'].values() if c['construction_set_id']=='construction-c6985aaff2845cac856a73ab' and c['climate_zone']=='4A')
        rows=source['selector_receipts'][c['selector_receipt_id']]
        target=next(d for d in rows if d['source_definition_id']=='construction-1d0774872c8801caa0afdd44')
        target['candidate_element_ids']=[]
        with self.assertRaisesRegex(ValueError,'embedded'):module.build_distribution(source)

    def test_archive_tampering_is_rejected(self):
        module=self.implementation()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,data in module.artifacts(self.source).items():(root/name).write_bytes(data)
            self.assertEqual(len(module.load_current_release(root)['construction_sets']),177)
            archive=json.loads((root/'source-evidence.json').read_bytes());archive['contexts'].pop(next(iter(archive['contexts'])))
            (root/'source-evidence.json').write_text(json.dumps(archive),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'checksum|reproducibility'):module.load_current_release(root)


if __name__=='__main__':unittest.main()
