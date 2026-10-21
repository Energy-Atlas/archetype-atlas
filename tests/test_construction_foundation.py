"""Foundation contract ownership, reference closure and absence semantics."""
import copy
import importlib.util
import unittest


def factor_document():
    return {'components':{'GroundFloor':{'disposition':'provided','target':{'surface_type':'Floor'},
        'assignments':[{'assembly_id':'floor','ground_method_id':'fc'}]}},
        'assemblies':{'floor':{'id':'floor','model':'FFactorGroundFloorConstruction','status':'ready','f_W_m_K':.8,'evidence_ids':['proof']}},
        'materials':{},'evidence':{'proof':{'source_locator':'pinned/input#floor'}},
        'foundation_ground':{'configuration':{'type':'source_native_commercial'},
            'methods':{'fc':{'model':'FFactor','model_parameters_id':'boundary','parameters':{},
                'required_geometry':['surface_area_m2','exposed_perimeter_m']}},
            'model_parameters':{'boundary':{'model':'FCBoundary','monthly_temperature_input':'fc_monthly_ground_temperature_C'}},
            'required_geometry':{'surface_area_m2':{'unit':'m2','exclusive_minimum':0},'exposed_perimeter_m':{'unit':'m','minimum':0}}}}


class FoundationContractTests(unittest.TestCase):
    def test_method_execution_operands_cannot_be_omitted_or_cross_wired(self):
        from scripts.common import ROOT,load_json
        for mutation in ('wrong_boundary_input','empty_geometry','wrong_geometry_unit','empty_kiva','empty_airflow'):
            d=factor_document()
            if mutation=='wrong_boundary_input':d['foundation_ground']['model_parameters']['boundary']['monthly_temperature_input']='surface_monthly_ground_temperature_C'
            elif mutation=='empty_geometry':
                d['foundation_ground']['required_geometry']={};d['foundation_ground']['methods']['fc']['required_geometry']=[]
            elif mutation=='wrong_geometry_unit':d['foundation_ground']['required_geometry']['exposed_perimeter_m']['unit']='m3'
            else:
                d=load_json(ROOT/'docs/examples/construction-foundation-v1/residential-vented-crawlspace.detailed.json')
                if mutation=='empty_kiva':next(iter(d['foundation_ground']['methods'].values()))['parameters']={}
                else:
                    exchange=next(iter(d['foundation_ground']['configuration']['air_exchange'].values()))
                    model=exchange['model'];exchange.clear();exchange['model']=model
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):self.module().validate_foundation_extension(d)

    def test_both_full_schemas_reject_incomplete_native_execution(self):
        from scripts.common import ROOT,load_json
        from scripts.validate_construction_foundation import schema,validate_document
        for representation in ('detailed','unified'):
            for mutation in ('wrong_boundary_input','empty_geometry','empty_kiva'):
                name='residential-vented-crawlspace' if mutation=='empty_kiva' else 'medium-office-2019-3B'
                d=load_json(ROOT/'docs/examples/construction-foundation-v1'/f'{name}.{representation}.json')
                ground=d['foundation_ground']
                if mutation=='wrong_boundary_input':next(iter(ground['model_parameters'].values()))['monthly_temperature_input']='surface_monthly_ground_temperature_C'
                elif mutation=='empty_geometry':
                    ground['required_geometry']={}
                    for method in ground['methods'].values():method['required_geometry']=[]
                else:next(iter(ground['methods'].values()))['parameters']={}
                with self.subTest(representation=representation,mutation=mutation):
                    self.assertTrue(list(schema(representation).iter_errors(d)))
                    with self.assertRaises(ValueError):validate_document(d,representation)

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.construction_foundation'))
        from scripts import construction_foundation
        return construction_foundation

    def test_factor_owned_by_assembly_and_no_shadow_parameter_or_registry(self):
        m=self.module();d=factor_document();m.validate_foundation_extension(d)
        for mutation in ('factor','material','registry'):
            bad=copy.deepcopy(d)
            if mutation=='factor':bad['foundation_ground']['methods']['fc']['parameters']['f_W_m_K']=.8
            elif mutation=='material':bad['foundation_ground']['methods']['fc']['parameters']['density_kg_m3']=2000
            else:bad['foundation_ground']['components']={}
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):m.validate_foundation_extension(bad)

    def test_missing_method_recipe_or_geometry_reference_fails(self):
        m=self.module()
        for mutation in ('method','assembly','geometry'):
            d=factor_document()
            if mutation=='method':d['foundation_ground']['methods'].clear()
            elif mutation=='assembly':d['assemblies'].clear()
            else:d['foundation_ground']['required_geometry'].pop('exposed_perimeter_m')
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):m.validate_foundation_extension(d)

    def test_no_contact_uses_existing_absence_disposition(self):
        m=self.module();d=factor_document()
        d['components']['GroundFloor'].update(disposition='source_absent',assignments=[])
        d['assemblies'].clear()
        d['foundation_ground']={'configuration':{'type':'no_direct_ground_contact','reason':'Source unit is above another apartment'},
            'methods':{},'model_parameters':{},'required_geometry':{}}
        m.validate_foundation_extension(d)
        d['components']['GroundFloor']['disposition']='provided'
        with self.assertRaises(ValueError):m.validate_foundation_extension(d)

    def test_native_unified_exception_requires_reason_and_ordinary_components_stay_simple(self):
        m=self.module();d=factor_document();d['kind']='building_level_equivalent'
        rule=d['components']['GroundFloor']['assignments'][0]
        d['components']['GroundFloor']={'status':'ready','assembly_id':None,'assignments':[rule,dict(rule,assembly_id='floor2')],
            'native_exception_reason':'Distinct native methods cannot be physically homogenized'}
        d['assemblies']['floor2']=dict(d['assemblies']['floor'],id='floor2',f_W_m_K=.7)
        m.validate_foundation_extension(d)
        del d['components']['GroundFloor']['native_exception_reason']
        with self.assertRaisesRegex(ValueError,'exception'):m.validate_foundation_extension(d)
        d=factor_document();d['kind']='building_level_equivalent'
        d['components']['ExteriorWall']={'status':'ready','assembly_id':None,'assignments':[rule]}
        with self.assertRaisesRegex(ValueError,'ordinary'):m.validate_foundation_extension(d)

    def test_native_layer_recipe_cannot_shadow_kiva_parameters(self):
        d=factor_document()
        d['assemblies']['floor']={'id':'floor','model':'native_opaque_layers','status':'ready',
            'layers':[],'evidence_ids':['proof'],'kiva_parameters':{'wall_depth_below_slab_m':.2032}}
        with self.assertRaisesRegex(ValueError,'shadow|native assembly'):
            self.module().validate_foundation_extension(d)


if __name__=='__main__':unittest.main()
