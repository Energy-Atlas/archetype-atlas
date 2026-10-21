"""Ground census must retain source absence, unresolved physics and climate scope."""
import copy
import importlib.util
import unittest
from scripts.common import ROOT, load_json
from scripts.construction_distribution import load_current_release


class FoundationRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.definitions = load_json(ROOT/'data/definition-releases/v0.1.1/constructions.json')
        cls.release = load_current_release()
        cls.geometry = load_json(ROOT/'data/construction-inputs/geometry-v1.json')
        cls.residential = load_json(ROOT/'data/construction-inputs/residential-assemblies-v1.json')

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_foundation_recovery'), 'Missing foundation census implementation')
        from scripts import construction_foundation_recovery
        return construction_foundation_recovery

    def census(self):
        return self.module().inventory_foundation_sources(self.definitions, self.release, self.geometry, self.residential)

    def test_full_denominator_and_no_false_executable_claim(self):
        c=self.census()
        self.assertEqual(len(c['suites']),177)
        self.assertEqual(len(c['contexts']),3320)
        self.assertEqual(c['coverage']['commercial_floor_suites'],136)
        self.assertEqual(c['coverage']['commercial_wall_suites'],124)
        self.assertEqual(self.module().build_census()['coverage']['source_evidence_contexts'],8)
        self.assertEqual(c['coverage']['residential_effective_configurations'],{
            'Slab-on-Grade':14,'Basement, Conditioned':7,'Crawlspace, Vented':5,'Basement, Unconditioned':3,
            'Crawlspace, Unvented':1,'Above Apartment':7,'Ambient':4})
        counts=c['coverage']['context_dispositions']
        self.assertEqual(sum(counts.values()),3320)
        self.assertEqual(counts['executable_contact'],0)
        self.assertGreater(counts['source_supported_no_contact'],0)
        self.assertGreater(counts['missing_executable_physics'],3273)
        self.assertEqual(c['coverage']['deferred_residential_objects'],{
            'Slab':45,'FoundationWall':78,'RimJoist':78,'FloorOverFoundation':9})

    def test_climate_candidates_are_selected_and_not_called_final_assignments(self):
        c=self.census()
        office=next(s for s in c['suites'].values() if s['building_type']=='MediumOffice' and s['template']=='90.1-2019')
        contexts=[v for v in c['contexts'].values() if v['suite_id']==office['id']]
        for v in contexts:
            self.assertEqual(len(v['candidate_elements']['GroundFloor']),1)
            self.assertFalse(v['native_execution_recovered'])
        warm=next(v for v in contexts if v['climate_zone']=='1A')
        cold=next(v for v in contexts if v['climate_zone']=='6A')
        self.assertNotEqual(warm['candidate_elements']['GroundFloor'],cold['candidate_elements']['GroundFloor'])

    def test_missing_floor_dependency_fails_instead_of_becoming_absence(self):
        definitions=copy.deepcopy(self.definitions)
        package=next(d for d in definitions if d['id']=='construction-93cb2afe2fe44c8e084b9b99')
        package['elements']['ground_contact_floor']=[]
        with self.assertRaisesRegex(ValueError,'ground.floor|GroundFloor'):
            self.module().inventory_foundation_sources(definitions,self.release,self.geometry,self.residential)

    def test_no_contact_with_deferred_physics_is_rejected(self):
        residential=copy.deepcopy(self.residential)
        geometry=copy.deepcopy(self.geometry)
        row=next(r for r in geometry['residential'] if r['source_context']['foundation_adjacency']=='Above Apartment')
        residential['records'][row['id']]['deferred_elements']=[{'id':'SlabUnexpected','role':'Slab'}]
        with self.assertRaisesRegex(ValueError,'no.contact|absence'):
            self.module().inventory_foundation_sources(self.definitions,self.release,geometry,residential)


if __name__=='__main__':unittest.main()
