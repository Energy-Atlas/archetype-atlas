"""Exact source allocation is distinct from arbitrary mixture participation."""
import copy
import unittest

from atlas_schedules.errors import GeneratorError
from tests.test_schedule_generator_pilot import GeneratorCase, OFFICE


class SourceAllocationTests(unittest.TestCase):
    def setUp(self):
        self.definition={'id':'composition-exact','template':'90.1-2013','evidence_view':'source',
            'members':[{'program_id':'fine','represented_area_m2':300,'weight':.75},
                       {'program_id':'bulk','represented_area_m2':100,'weight':.25}]}
        self.recipe={'parent_program_id':'storage','composition_id':'composition-exact',
            'definition':self.definition,'provenance':{'source_locator':'exact#/members'}}
        self.instance={'key':'parent/one','program_id':'storage','inputs':{'composition_basis_mode':'source_reference_area_normalized'},
                       'basis_bindings':{},'operating_group':None}

    def prepare(self,instance=None,recipe=None):
        from atlas_schedules.source_compositions import prepare_allocation
        return prepare_allocation(instance or self.instance,recipe or self.recipe)

    def test_reference_area_mode_is_explicit_and_constituent_first(self):
        allocation=self.prepare()
        self.assertEqual(allocation['parent_instance_key'],'parent/one')
        self.assertEqual([c['program_id'] for c in allocation['children']],['fine','bulk'])
        self.assertEqual([c['basis_bindings']['extents']['floor_area']['value'] for c in allocation['children']],[300,100])
        self.assertEqual([m['weight'] for m in allocation['mixture']['members']],[1,1])
        self.assertEqual(allocation['mixture']['denominator']['value'],400)
        self.assertEqual([c['operating_group'] for c in allocation['children']],['parent/one']*2)
        self.assertEqual(len({c['key'] for c in allocation['children']}),2)
        self.assertEqual(allocation['receipt']['physical_factors'],[.75,.25])
        self.assertEqual(allocation['receipt']['control_method'],'source_represented_area_pointwise_eligible_average')

    def test_explicit_caller_area_scales_all_members_once(self):
        instance=copy.deepcopy(self.instance)
        instance['inputs']['composition_basis_mode']='caller_parent_floor_area'
        instance['basis_bindings']={'extents':{'floor_area':{'value':1000,'unit':'m2','evidence':{'caller':'bound'}}}}
        allocation=self.prepare(instance)
        self.assertEqual([c['basis_bindings']['extents']['floor_area']['value'] for c in allocation['children']],[750,250])
        self.assertEqual(allocation['mixture']['denominator']['value'],1000)
        self.assertEqual(allocation['receipt']['physical_factors'],[.75,.25])

    def test_missing_or_conflicting_operands_fail(self):
        for mutation in ('missing_mode','unknown_mode','missing_area','reference_with_area','multiplicity','bool_multiplicity','wrong_composition'):
            instance=copy.deepcopy(self.instance)
            if mutation=='missing_mode':instance['inputs'].pop('composition_basis_mode')
            if mutation=='unknown_mode':instance['inputs']['composition_basis_mode']='guessed_geometry'
            if mutation=='missing_area':instance['inputs']['composition_basis_mode']='caller_parent_floor_area'
            if mutation=='reference_with_area':instance['basis_bindings']={'floor_area_m2':100}
            if mutation=='multiplicity':instance['basis_bindings']={'multiplicity':2}
            if mutation=='bool_multiplicity':instance['basis_bindings']={'multiplicity':True}
            if mutation=='wrong_composition':instance['inputs']['composition_id']='foreign'
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):self.prepare(instance)

    def test_source_weights_must_match_original_area_ratios(self):
        recipe=copy.deepcopy(self.recipe)
        recipe['definition']['members'][0]['weight']=.5
        with self.assertRaises(GeneratorError):self.prepare(recipe=recipe)


class SourceComposerTests(GeneratorCase):
    def source_fixture(self,unrelated=False):
        import math
        from atlas_schedules.contract import validate_bundle
        instances=[self.instance('fine',OFFICE,group='source-building',basis={'floor_area_m2':300}),
                   self.instance('bulk',OFFICE,group='source-building',basis={'floor_area_m2':100})]
        if unrelated:instances.insert(0,self.instance('unrelated',OFFICE,group='unrelated-building'))
        bundle=self.generate(self.params(instances),42)
        for i,c in enumerate(bundle['constituents']):
            c['program_id']=c['instance_key']
            c['source'].update(template='90.1-2013',evidence_view='source')
            for index in c['binding_indices']:
                binding=bundle['bindings'][index];binding['program_id']=c['program_id']
                if binding['kind']=='load' and c['instance_key']=='bulk':
                    binding['reference_target']['total']*=3
                    binding['effective_magnitude']['value']*=3
                    binding['scaling_receipt']['achieved_total']*=3
                    next(d for d in c['demands'] if d['demand_id']==binding['demand_id'])['value']*=3
            bundle['schedules'][c['schedule_ids']['heating_setpoint']]['values']=[20+8*i]*8760
        validate_bundle(bundle)
        definition={'id':'composition-exact','template':'90.1-2013','evidence_view':'source',
                    'members':[{'program_id':'fine','represented_area_m2':300,'weight':.75},
                               {'program_id':'bulk','represented_area_m2':100,'weight':.25}]}
        record={'definition':definition,'source_allocation':{'parent_program_id':'storage','composition_id':'composition-exact'},
                'provenance':{'source_locator':'exact#/members'}}
        original=self.resources
        class Evidence:
            def get(self,kind,key):
                if (kind,key)==('reference','catalogue-index'):return {'compositions':[{'id':'composition-exact','status':'compiled'}]}
                if (kind,key)==('composition','composition-exact'):return record
                return original.get(kind,key)
        mixture={'program_id':'storage','composition_id':'composition-exact',
                 'members':[{'instance_key':'fine','weight':1},{'instance_key':'bulk','weight':1}],
                 'result_basis':'floor_area','denominator':{'value':400,'unit':'m2','evidence':{'source':'explicit reference area'}}}
        return bundle,mixture,Evidence()

    def test_known_source_composition_uses_unequal_areas_and_bound_targets(self):
        import math
        from unittest.mock import patch
        from atlas_schedules import compose_constituents
        bundle,mixture,resources=self.source_fixture()
        with patch('atlas_schedules.mixtures.ResourceSet.load',return_value=resources):
            actual=compose_constituents([bundle],mixture,bundle['metadata']['calendar'])
        parent=actual['constituents'][-1]
        self.assertEqual(parent['generation']['method'],'conserved_source_composition')
        self.assertEqual(parent['generation']['source_allocation']['physical_factors'],[.75,.25])
        self.assertEqual(actual['schedules'][parent['schedule_ids']['heating_setpoint']]['values'],[22]*8760)
        for index in parent['binding_indices']:
            binding=actual['bindings'][index]
            if binding['kind']!='load':continue
            parts=binding['reference_target']['evidence']['components']
            self.assertEqual([p['factor'] for p in parts],[.75,.25])
            expected=math.fsum(p['factor']*actual['bindings'][p['binding_index']]['reference_target']['total'] for p in parts)
            self.assertEqual(binding['reference_target']['total'],expected)
            for h in (0,25,3000,8759):
                power=binding['effective_magnitude']['value']*actual['schedules'][binding['schedule_id']]['values'][h]
                want=math.fsum(p['factor']*actual['bindings'][p['binding_index']]['effective_magnitude']['value']*actual['schedules'][p['schedule_id']]['values'][h] for p in parts)
                self.assertTrue(math.isclose(power,want,rel_tol=1e-12,abs_tol=1e-12))

    def test_foreign_order_weights_views_and_areas_reject(self):
        from unittest.mock import patch
        from atlas_schedules import compose_constituents
        for mutation in ('order','weight','view','extent','denominator','parent','group'):
            bundle,mixture,resources=self.source_fixture()
            if mutation=='order':mixture['members'].reverse()
            if mutation=='weight':mixture['members'][0]['weight']=.75
            if mutation=='view':bundle['constituents'][0]['source']['evidence_view']='reviewed'
            if mutation=='extent':bundle['constituents'][0]['basis_bindings']['floor_area_m2']=200
            if mutation=='denominator':mixture['denominator']['value']=800
            if mutation=='parent':mixture['program_id']='foreign'
            if mutation=='group':bundle['constituents'][0]['generation']['source_context']['operating_receipt']['group_seed']+=1
            with self.subTest(mutation=mutation),patch('atlas_schedules.mixtures.ResourceSet.load',return_value=resources),self.assertRaises(GeneratorError):
                compose_constituents([bundle],mixture,bundle['metadata']['calendar'])


class SourceProjectionTests(GeneratorCase):
    source_fixture=SourceComposerTests.source_fixture
    def test_projection_contains_only_complete_actual_children_and_inverse_indices(self):
        from atlas_schedules.source_compositions import project_source_members
        bundle,mixture,_=self.source_fixture(unrelated=True)
        before=copy.deepcopy(bundle)
        local,inverse=project_source_members(bundle,['fine','bulk'])
        self.assertEqual([c['instance_key'] for c in local['constituents']],['fine','bulk'])
        expected=[i for c in bundle['constituents'][1:] for i in c['binding_indices']]
        self.assertEqual(inverse,dict(enumerate(expected)))
        self.assertEqual(set(local['schedules']),{sid for c in bundle['constituents'][1:] for sid in c['schedule_ids'].values()})
        self.assertEqual([i for c in local['constituents'] for i in c['binding_indices']],list(range(len(expected))))
        self.assertEqual(bundle,before)
        from atlas_schedules.contract import validate_bundle
        validate_bundle(local)

    def test_parent_only_merge_matches_existing_composer_and_global_references(self):
        from unittest.mock import patch
        from atlas_schedules import compose_constituents
        from atlas_schedules.source_compositions import compose_source_parent,bind_parent_identity
        from atlas_schedules.comparison import compare_bundles
        from atlas_schedules.contract import validate_bundle
        bundle,mixture,resources=self.source_fixture(unrelated=True)
        with patch('atlas_schedules.mixtures.ResourceSet.load',return_value=resources):
            expected=compose_constituents([bundle],mixture,bundle['metadata']['calendar'])
        parent=expected['constituents'][-1]
        allocation={'parent_instance_key':'requested-parent','parent_case_id':'C4-parent',
            'children':[{'key':'fine'},{'key':'bulk'}],'mixture':mixture,
            'receipt':parent['generation']['source_allocation'],
            'parent_instance':{'key':'requested-parent','program_id':'storage','inputs':{},'basis_bindings':{}},
            'parent_resolved':{'recipe_id':'recipe-storage','source':copy.deepcopy(parent['source']),
                'source_family':'source_composition','evidence':[],
                'inputs':{'reference_budgets':{expected['bindings'][i]['demand_id']:expected['bindings'][i]['reference_target']
                    for i in parent['binding_indices'] if expected['bindings'][i]['kind']=='load'}}}}
        bind_parent_identity(expected,allocation)
        original_owners=copy.deepcopy(bundle['constituents'])
        original_generation=copy.deepcopy(bundle['generation'])
        with patch('atlas_schedules.mixtures.ResourceSet.load',return_value=resources):
            actual=compose_source_parent(bundle,allocation)
        self.assertIs(actual,bundle)
        self.assertEqual(actual['constituents'][:-1],original_owners)
        for key,value in original_generation.items():self.assertEqual(actual['generation'][key],value)
        self.assertEqual(compare_bundles(actual,expected,actual['metadata']['comparison_policy']),[])
        validate_bundle(actual)
        for index in actual['constituents'][-1]['binding_indices']:
            binding=actual['bindings'][index]
            if binding['kind']=='load':
                for part in binding['reference_target']['evidence']['components']:
                    self.assertEqual(actual['bindings'][part['binding_index']]['schedule_id'],part['schedule_id'])

    def test_nested_binding_references_remap_and_unknown_refs_reject(self):
        from atlas_schedules.source_compositions import remap_binding_references
        original={'binding_indices':[0,3],'outer':{'reference_target':{'evidence':{'components':[{'binding_index':3}]}}}}
        remap_binding_references(original,{0:10,3:13})
        self.assertEqual(original,{'binding_indices':[10,13],'outer':{'reference_target':{'evidence':{'components':[{'binding_index':13}]}}}})
        for malformed in ({'binding_index':4},{'binding_index':True},{'binding_indices':[0,4]}):
            with self.subTest(malformed=malformed),self.assertRaises(GeneratorError):
                remap_binding_references(malformed,{0:10})

    def test_projection_rejects_missing_duplicate_cross_owner_and_dangling_refs(self):
        from atlas_schedules.source_compositions import project_source_members
        original,_,_=self.source_fixture(unrelated=True)
        for mutation in ('missing','duplicate','owner','schedule','binding','service'):
            bundle=copy.deepcopy(original);keys=['fine','bulk']
            if mutation=='missing':keys[0]='absent'
            if mutation=='duplicate':keys[1]='fine'
            child=bundle['constituents'][1]
            if mutation=='owner':child['binding_indices'][0]=bundle['constituents'][0]['binding_indices'][0]
            if mutation=='schedule':child['schedule_ids']['lighting']='missing'
            if mutation=='binding':child['binding_indices'][0]=len(bundle['bindings'])
            if mutation=='service':child['shared_services']=[{'id':'cross-owner-service','demand':{'demand_id':'unowned','schedule_id':'missing'}}]
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):project_source_members(bundle,keys)

    def test_projection_retains_owned_service_descriptor_and_nested_binding_ref(self):
        from atlas_schedules.source_compositions import project_source_members
        bundle,_,_=self.source_fixture(unrelated=True)
        child=bundle['constituents'][1]
        index=next(i for i in child['binding_indices'] if bundle['bindings'][i]['kind']=='load')
        child['shared_services']=[{'source_service_id':'synthetic-reference-closure-fixture',
            'demand_id':bundle['bindings'][index]['demand_id'],'physical_id':'one-explicit-service',
            'mode':'whole','extent':{'value':1,'unit':'m2','evidence':{'caller':'explicit fixture'}},
            'bound_reference':{'binding_index':index,'schedule_id':bundle['bindings'][index]['schedule_id']}}]
        local,inverse=project_source_members(bundle,['fine','bulk'])
        descriptor=copy.deepcopy(child['shared_services'][0])
        descriptor['bound_reference']['binding_index']=next(i for i,g in inverse.items() if g==index)
        self.assertEqual(local['constituents'][0]['shared_services'],[descriptor])
        self.assertEqual(local['bindings'][descriptor['bound_reference']['binding_index']]['demand_id'],descriptor['demand_id'])


if __name__=='__main__':unittest.main()
