"""Combined exports preserve frozen above-ground semantics and compact native physics."""
import importlib.util
import unittest
from scripts.common import ROOT,load_json


class FoundationExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_d=load_json(ROOT/'docs/examples/construction-mass-v1/medium-office-2019-3B.detailed.json')
        cls.base_u=load_json(ROOT/'docs/examples/construction-mass-v1/medium-office-2019-3B.unified.json')

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_foundation_export'))
        from scripts import construction_foundation_export
        return construction_foundation_export

    def test_office_native_factor_and_unchanged_ordinary_content(self):
        m=self.module();d,u=m.export_pair('construction-set-beb5e983644344ce44d4a299')
        self.assertEqual(d['schema_version'],'3.0.0');self.assertEqual(u['schema_version'],'2.0.0')
        for old,new in ((self.base_d,d),(self.base_u,u)):
            self.assertEqual(new['infiltration'],old['infiltration'])
            self.assertEqual(new['mass_accounting'],old['mass_accounting'])
            for role,c in old['components'].items():self.assertEqual(c,new['components'][role])
            for aid,a in old['assemblies'].items():self.assertEqual(a,new['assemblies'][aid])
        c=d['components']['GroundFloor'];a=d['assemblies'][c['assignments'][0]['assembly_id']]
        self.assertEqual(c['assignments'][0]['when']['boundary_condition'],'Ground')
        self.assertEqual(a['model'],'FFactorGroundFloorConstruction')
        self.assertAlmostEqual(a['f_W_m_K'],1.26343630645112)
        self.assertLess(len(d['metadata']['source_files']),100)
        self.assertEqual(len(u['components']['GroundFloor'].get('assignments',[])),0)
        self.assertNotIn('source_inventory',str(d['foundation_ground']))

    def test_residential_native_kiva_and_simplified_ordinary_interfaces(self):
        m=self.module()
        from scripts.construction_distribution import load_current_release
        r=load_current_release()
        sid=next(s['id'] for s in r['construction_sets'].values() if s['source']['source_fixture_id']=='residential_archetype-0157cd8578ba44bf8a77')
        cid=next(c['id'] for c in r['contexts'].values() if c['construction_set_id']==sid)
        d,u=m.export_pair(cid)
        self.assertTrue(any(x['model']=='Kiva' for x in d['foundation_ground']['methods'].values()))
        for role in ('RimJoist','FloorOverFoundation'):
            self.assertTrue(u['components'][role]['assembly_id'])
            self.assertNotIn('assignments',u['components'][role])
            self.assertLessEqual(len(u['assemblies'][u['components'][role]['assembly_id']]['layers']),3)
            self.assertEqual(u['assemblies'][u['components'][role]['assembly_id']]['surface_properties']['exterior']['roughness'],'Rough')
        self.assertIn('crawlspace - vented',d['foundation_ground']['configuration']['air_exchange'])

    def test_missing_contact_physics_cannot_become_source_absence(self):
        with self.assertRaisesRegex(ValueError,'Missing.*physics'):
            self.module().prepare_foundation_extension({'configuration_type':'Slab-on-Grade'}, {}, {'faces':[]})


if __name__=='__main__':unittest.main()
