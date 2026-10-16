"""Source support profiles distinguish real interfaces from generated reverse faces."""
import importlib.util
import unittest
from scripts.common import ROOT,load_json


class FoundationProfileTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_foundation_profiles'))
        from scripts import construction_foundation_profiles
        return construction_foundation_profiles

    def test_split_shared_edges_are_not_external_footprint_perimeter(self):
        # One 2x2 rectangle beside two 1x1 rectangles sharing its long edge.
        polys=[[[0,0,0],[2,0,0],[2,2,0],[0,2,0]],
               [[2,0,0],[3,0,0],[3,1,0],[2,1,0]],
               [[2,1,0],[3,1,0],[3,2,0],[2,2,0]]]
        self.assertAlmostEqual(self.module().footprint_boundary_length(polys),10)
        # These are outline edges; a below-grade F-factor floor can still have zero air-exposed perimeter.
        self.assertAlmostEqual(self.module().footprint_boundary_length([polys[0]]),8)

    def test_residential_profile_excludes_reverse_floor_faces_and_retains_methods(self):
        data=load_json(ROOT/'data/construction-inputs/foundation-execution-v1.json')
        row=data['residential']['residential_archetype-0157cd8578ba44bf8a77']
        p=self.module().build_foundation_profile(row)
        floors=[f for f in p['faces'] if f['role']=='FloorOverFoundation']
        self.assertEqual(len(floors),1)
        self.assertAlmostEqual(floors[0]['area_m2'],101.21786208)
        self.assertEqual(floors[0]['thermal_host'],'conditioned space')
        self.assertEqual({f['role'] for f in p['faces']},{'GroundFloor','FoundationWall','RimJoist','FloorOverFoundation'})
        self.assertTrue(all(f['foundation_id'] in p['kiva'] for f in p['faces'] if f['boundary']=='Foundation'))


if __name__=='__main__':unittest.main()
