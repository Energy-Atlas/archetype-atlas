"""Native capture normalization must not disguise failed source execution."""
import importlib.util
import unittest
import copy
from scripts.common import ROOT,load_json


class NativeFoundationTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_foundation_native'))
        from scripts import construction_foundation_native
        return construction_foundation_native

    def test_preserve_native_factor_and_move_reference_geometry_to_internal_evidence(self):
        native={'status':'recovered','surfaces':[{'name':'slab','surface_type':'Floor','boundary':'GroundFCfactorMethod',
            'construction':{'model':'FFactorGroundFloorConstruction','f_W_m_K':0.8,'reference_area_m2':100,'reference_exposed_perimeter_m':40}}]}
        result=self.module().normalize_foundation_execution(native,{'source_revision':'test-pinned','sha256':'a'*64})
        face=result['surfaces'][0]
        self.assertEqual(face['recipe'],{'model':'FFactorGroundFloorConstruction','f_W_m_K':0.8})
        self.assertEqual(face['reference_geometry'],{'area_m2':100,'exposed_perimeter_m':40})
        self.assertEqual(result['status'],'recovered')

    def test_finite_resistance_named_adiabatic_retains_ground_boundary(self):
        native={'status':'recovered','surfaces':[{'name':'slab','surface_type':'Floor','boundary':'Ground',
            'construction':{'model':'Construction','layers':[{'name':'Adiabatic Material','model':'MasslessOpaqueMaterial','resistance_m2_K_W':1760.9257}]}}]}
        result=self.module().normalize_foundation_execution(native,{'sha256':'a'*64})
        self.assertEqual(result['surfaces'][0]['boundary'],'Ground')
        self.assertEqual(result['surfaces'][0]['recipe']['layers'][0]['resistance_m2_K_W'],1760.9257)

    def test_recovery_failure_and_invalid_method_boundary_are_not_ready(self):
        for native in ({'status':'blocked','error':'source setter failed'},
            {'status':'recovered','surfaces':[{'boundary':'Ground','construction':{'model':'FFactorGroundFloorConstruction','f_W_m_K':0.8}}]}):
            with self.subTest(native=native):
                with self.assertRaises(ValueError):self.module().normalize_foundation_execution(native,{})

    def test_group_only_equal_source_physics_with_same_reference_geometry(self):
        rows=[{'template':'90.1-2019','building_type':'MediumOffice','climate_zone':cz,
               'physics_signature':{'f_W_m_K':f},'status':'source_queries_recovered'}
              for cz,f in [('1A',1.0),('1B',1.0),('6A',0.7)]]
        groups=self.module().group_commercial_cases(rows)
        self.assertEqual(sorted(len(v['contexts']) for v in groups.values()),[1,2])
        self.assertEqual(sorted({v['representative']['physics_signature']['f_W_m_K'] for v in groups.values()}),[0.7,1.0])
        rows[1]['physics_signature']['geometry_climate_context']='1B'
        self.assertEqual(len(self.module().group_commercial_cases(rows)),3)
        rows[1]['status']='blocked'
        with self.assertRaisesRegex(ValueError,'query'):self.module().group_commercial_cases(rows)

    def test_initialization_preserves_source_host_and_controls_cases(self):
        m=self.module()
        cases=[({'host':'conditioned space','ceiling_insulated':False,'walls_insulated':False},12.5,23.0),
               ({'host':'basement - unconditioned','ceiling_insulated':True,'walls_insulated':False},-5,6.25),
               ({'host':'crawlspace - vented','ceiling_insulated':True,'walls_insulated':False},-5,-2.5),
               ({'host':'crawlspace - unvented','ceiling_insulated':True,'walls_insulated':False},-5,-1.25),
               ({'host':'garage','ceiling_insulated':False,'walls_insulated':False},-5,1.1111111111111112)]
        for spec,out,want in cases:
            with self.subTest(host=spec['host']):
                self.assertAlmostEqual(m.initial_temperature_C(spec,out,10,20,26,True),want)
        spec={'host':'conditioned space','ceiling_insulated':False,'walls_insulated':False}
        self.assertEqual(m.initial_temperature_C(spec,30,10,None,None,False),30)
        with self.assertRaisesRegex(ValueError,'setpoint'):m.initial_temperature_C(spec,12,10,None,26,True)
        with self.assertRaisesRegex(ValueError,'host'):m.initial_temperature_C(dict(spec,host='unknown'),12,10,20,26,True)

    def test_native_factor_must_match_executed_source_lookup(self):
        m=self.module()
        row={'surfaces':[{'recipe':{'model':'FFactorGroundFloorConstruction','f_W_m_K':1.26343630645112}}]}
        signature={'explicit_floor':{'assembly_maximum_f_factor':.73}}
        m.validate_achieved_factors(row,signature)
        row['surfaces'][0]['recipe']['f_W_m_K']=.1
        with self.assertRaisesRegex(ValueError,'source.*factor'):m.validate_achieved_factors(row,signature)

    def test_frozen_execution_retains_every_context_and_deferred_source_object(self):
        m=self.module()
        data=load_json(ROOT/'data/construction-inputs/foundation-execution-v1.json')
        census=load_json(ROOT/'data/construction-inputs/foundation-source-v1.json')
        m.validate_execution(data,census)
        broken=copy.deepcopy(data)
        broken['commercial_context_cases'].pop(next(iter(broken['commercial_context_cases'])))
        with self.assertRaisesRegex(ValueError,'context'):m.validate_execution(broken,census)
        broken=copy.deepcopy(data)
        row=next(r for r in broken['residential'].values() if r['source_elements'])
        row['source_elements'].pop()
        with self.assertRaisesRegex(ValueError,'source object'):m.validate_execution(broken,census)


if __name__=='__main__':unittest.main()
