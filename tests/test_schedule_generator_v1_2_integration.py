"""Public qualified legacy integration; new-mode contract fixtures are labelled."""
import copy
import json
import shutil
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from atlas_schedules import generate, compose_constituents
from atlas_schedules.__main__ import main
from atlas_schedules.comparison import compare_bundles
from atlas_schedules.contract import validate_bundle, validate_request
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet
from tests import test_schedule_generator_physical_binding_v1_2 as exact
from tests import test_schedule_generator_caller_water_v1_2 as caller
from tests import test_schedule_generator_service_graph_v1_2 as graph


class PublicV12IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Actual locked C5 inputs and existing offline build; no qualification patch.
        cls.temporary=tempfile.TemporaryDirectory()
        root=Path(cls.temporary.name)
        archive=Path(__file__).resolve().parents[1]/'data/generator-releases/v0.7.0/generator.zip'
        with zipfile.ZipFile(archive) as package:
            for name in package.namelist():
                if name.startswith('atlas_schedules/data/'):
                    target=root/name.removeprefix('atlas_schedules/data/')
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(package.read(name))
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        cls.resources=ResourceSet(root,manifest['resource_set_id'])

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def request(self, instances, version='1.2.0'):
        params={'schema_version':version,'resource_set_id':self.resources.resource_set_id,
                'calendar':copy.deepcopy(exact.CALENDAR),'instances':copy.deepcopy(instances)}
        if version=='1.2.0':params['building_realizations']=[]
        return params

    def generate(self, params, seed=42):
        with patch('atlas_schedules.generator.ResourceSet.load',return_value=self.resources):
            return generate(params,seed)

    def stock(self,key):
        pid='program-e0993499165be6c7b5bf9efa'
        return {'owner_kind':'program','key':key,'program_id':pid,'operating_group':None,
                'inputs':self.resources.get('program',pid)['recipe']['bound_inputs'],
                'basis_bindings':{}}

    def test_public_v12_legacy_api_cli(self):
        kitchen,physical=self.restaurant()
        params=self.request([kitchen,*physical])
        for i in params['instances']:
            if i['owner_kind']=='physical_service':i['physical_binding_kind']='legacy_whole'
        before=copy.deepcopy(params)
        actual=self.generate(params)
        self.assertEqual(params,before)
        self.assertEqual(actual['metadata']['building_realizations'],[])
        self.assertEqual(actual['generation']['physical_unit_seed_sequence'],[])
        programme=next(c for c in actual['constituents'] if c['owner_kind']=='program')
        self.assertEqual(programme['required_service_sets'],[])
        self.assertEqual(programme['service_set_projections'],[])
        self.assertTrue(programme['service_links'])
        self.assertTrue(all(len(g['operating']['draw_receipts'])==10 for g in actual['generation']['operating_groups'].values()))
        # Incoming validation and comparison must not load any default resources.
        with patch('atlas_schedules.resources.ResourceSet.load',side_effect=AssertionError('incoming lookup')):
            validate_bundle(actual)
            self.assertEqual(compare_bundles(actual,copy.deepcopy(actual),actual['metadata']['comparison_policy']),[])
        with tempfile.TemporaryDirectory() as directory:
            request=Path(directory)/'request.json';output=Path(directory)/'bundle.json'
            request.write_text(json.dumps({'schema_version':'1.2.0','params':params,'seed':42}),encoding='utf-8')
            with patch('atlas_schedules.generator.ResourceSet.load',return_value=self.resources):
                self.assertEqual(main(['--request',str(request),'--output',str(output)]),0)
            self.assertEqual(json.loads(output.read_text(encoding='utf-8')),actual)
        legacy=copy.deepcopy(params);legacy.pop('building_realizations');legacy['schema_version']='1.1.0'
        for i in legacy['instances']:
            if i['owner_kind']=='physical_service':i.pop('physical_binding_kind')
        old=self.generate(legacy)
        self.assertEqual(actual['schedules'],old['schedules'])
        self.assertEqual([b['reference_target'] for b in actual['bindings'] if b['kind']=='load'],
                         [b['reference_target'] for b in old['bindings'] if b['kind']=='load'])

    def test_public_legacy_source_parent_and_stock_mixed_preparation(self):
        scope=self.resources.get('reference','m1-scope')
        selected=next(c for c in scope['cases'] if 'source_composition' in self.resources.get('program',c['program_id'])['recipe'])
        recipe=self.resources.get('program',selected['program_id'])['recipe']
        parent={'owner_kind':'program','key':'source-parent','program_id':selected['program_id'],
                'inputs':dict(recipe['bound_inputs'],composition_basis_mode='source_reference_area_normalized'),
                'operating_group':'parent-group','basis_bindings':{}}
        actual=self.generate(self.request([self.stock('stock'),parent]))
        validate_bundle(actual)
        self.assertEqual(actual['generation']['request_instance_order'],['stock','source-parent'])
        self.assertEqual(actual['generation']['source_parent_derivation_order'],['source-parent'])
        self.assertEqual(actual['generation']['physical_unit_seed_sequence'][0]['instance_key'],'stock')
        old=self.generate(self.request([self.stock('stock'),parent],'1.1.0'))
        self.assertEqual(actual['schedules'],old['schedules'])
        self.assertEqual([b['reference_target'] for b in actual['bindings'] if b['kind']=='load'],
                         [b['reference_target'] for b in old['bindings'] if b['kind']=='load'])

    def restaurant(self):
        pid='program-76fabb7b85c683f4f7d8c873'
        recipe=self.resources.get('program',pid)['recipe'];config=recipe['source_context']['source_hoo_configuration_id']
        kitchen={'owner_kind':'program','key':'kitchen','program_id':pid,'inputs':recipe['bound_inputs'],
                 'operating_group':config,'basis_bindings':{},'service_links':{}}
        physical=[]
        for req in recipe['required_service_links']:
            sid=req['source_service_id'];key='owner-'+sid;kitchen['service_links'][sid]=key
            record=self.resources.get('reference','physical-service__'+sid)
            variant=record['recipe']['configurations'][config];basis=record['definition']['load']['basis']
            inputs={'source_hoo_configuration_id':config,'physical_fixture_evidence':{'caller':'explicit source fixture'}}
            extent=1;unit='1'
            if basis=='floor_area':
                ref=variant['native_source_physical_reference'];area=ref['floor_area_m2'];multiplier=ref['multiplier']
                extent=area*multiplier;unit='m2'
                inputs.update(fixture_floor_area_m2=area,fixture_space_multiplier=multiplier,
                    fixture_extent_evidence={'area':{'value':area,'unit':'m2','caller':'explicit source area'},
                                            'multiplier':{'value':multiplier,'unit':'1','caller':'explicit source multiplier'}})
            physical.append({'owner_kind':'physical_service','physical_binding_kind':'legacy_whole',
                'key':key,'source_service_id':sid,'physical_id':'fixture-'+sid,'inputs':inputs,
                'operating_group':config,'basis_bindings':{'multiplicity':1,'extents':{
                    basis:{'value':extent,'unit':unit,'evidence':{'caller':'explicit source extent'}}}}})
        return kitchen,physical

    def test_public_stock_receipt_preserves_actual_legacy_seed_order(self):
        instances=[self.stock(k) for k in ('third','first','second')]
        actual=self.generate(self.request(instances))
        sequence=actual['generation']['physical_unit_seed_sequence']
        self.assertEqual(sequence,[{'actor_kind':'stock','instance_key':key,
            'building_realization_id':None,'unit_id':None,'stochastic_action':'generate',
            'position':n,'unit_seed':seed} for n,(key,seed) in
            enumerate(zip(('third','first','second'),(42,84,252)))])
        for version in ('1.0.0','1.1.0'):
            old_instances=copy.deepcopy(instances)
            if version=='1.0.0':
                for i in old_instances:i.pop('owner_kind')
            old=self.generate(self.request(old_instances,version))
            for field in ('residential_unit_order','unit_seeds'):
                self.assertEqual(actual['generation'][field],old['generation'][field])
            self.assertEqual(actual['schedules'],old['schedules'])
            self.assertNotIn('physical_unit_seed_sequence',old['generation'])
        validate_bundle(actual)

    def assert_no_rng_error(self, params, code, path):
        sentry=AssertionError('failure reached RNG allocation')
        with (patch('atlas_schedules.generator.assign_physical_unit_sequence',side_effect=sentry),
              patch('atlas_schedules.generator.commercial_group_seed',side_effect=sentry),
              patch('atlas_schedules.generator.sample_operating_parameters',side_effect=sentry),
              patch('atlas_schedules.generator.generate_residential',side_effect=sentry)):
            with self.assertRaises(GeneratorError) as caught:self.generate(params)
        self.assertEqual(caught.exception.code,code)
        self.assertIn(path,caught.exception.path)

    def test_public_new_modes_stay_closed(self):
        _,owners=self.restaurant();owner=owners[0]
        owner.update(physical_binding_kind='exact_source_role',building_realization_id='source-building',
                     source_fixture_role_id='source-main-role')
        candidate=self.request([owner]);candidate['building_realizations']=[{
            'mode':'exact_source_fixture_extents','building_realization_id':'source-building',
            'inventory_id':'unqualified-restaurant-source-inventory','inventory_sha256':'a'*64,
            'source_hoo_configuration_id':owner['inputs']['source_hoo_configuration_id'],
            'selected_method_context_id':'unqualified-original-source-method','operating_group':owner['operating_group']}]
        validate_request(candidate,42)
        self.assert_no_rng_error(candidate,'requires_binding','reference')
        req=caller.compiled();real=caller.realization([caller.unit('u','draw',[req])])
        physical=[i for i,r in caller.pairs(real,{req['programme']['value']['id']:req},False)]
        params=self.request(physical);params['building_realizations']=[real]
        validate_request(params,42)
        self.assert_no_rng_error(params,'requires_binding','reference')

    def test_phase_one_and_foreign_buildings_fail_before_rng(self):
        params=self.request([self.stock('stock')])
        invalid=copy.deepcopy(params);invalid['schema_version']='9.0.0'
        self.assert_no_rng_error(invalid,'unsupported_schema','schema_version')
        invalid=copy.deepcopy(params);invalid['instances'][0]['inputs']['year']=2007
        self.assert_no_rng_error(invalid,'unknown_input','inputs')
        invalid=copy.deepcopy(params);invalid['instances'][0]['building_realization_id']='missing'
        self.assert_no_rng_error(invalid,'shared_service_conflict','building_realization_id')
        invalid=copy.deepcopy(params);invalid['building_realizations']=[{
            'mode':'exact_source_fixture_extents','building_realization_id':'duplicate',
            'inventory_id':'unqualified','inventory_sha256':'a'*64,'source_hoo_configuration_id':'source',
            'selected_method_context_id':'method','operating_group':'group'}]*2
        self.assert_no_rng_error(invalid,'invalid_request','building_realizations')

    def test_actual_locked_resource_integrity_precedes_rng(self):
        params=self.request([self.stock('stock')])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'resources';shutil.copytree(self.resources.root,root)
            record=self.resources.manifest['resources'][0]
            with (root/record['path']).open('ab') as stream:stream.write(b' ')
            with (patch('atlas_schedules.generator.ResourceSet.load',side_effect=lambda rid:ResourceSet(root,rid)),
                  patch('atlas_schedules.generator.assign_physical_unit_sequence',side_effect=AssertionError('resource RNG'))):
                with self.assertRaises(GeneratorError) as caught:generate(params,42)
            self.assertEqual((caught.exception.code,caught.exception.path),('resource_integrity',record['path']))

    def test_public_c5_pre_rng_group_and_automatic_denominator(self):
        kitchen,physical=self.restaurant()
        params=self.request([kitchen,*physical])
        invalid=copy.deepcopy(params);invalid['instances'][-1]['operating_group']='foreign'
        self.assert_no_rng_error(invalid,'operating_group_conflict','service_links')
        invalid=copy.deepcopy(params);invalid['mixture']={'program_id':'result','composition_id':None,
            'members':[{'instance_key':'kitchen','weight':1}]}
        self.assert_no_rng_error(invalid,'requires_binding','/mixture/denominator')
        invalid['mixture'].update(result_basis='dwelling_unit',denominator={
            'value':1,'unit':'dwelling','evidence':{'caller':'incompatible water root basis'}})
        self.assert_no_rng_error(invalid,'incompatible_basis','/mixture/denominator')

    def test_actual_legacy_control_graph_keeps_all_owned_references_strict(self):
        kitchen,physical=self.restaurant();bundle=self.generate(self.request([kitchen,*physical]))
        owner=next(c for c in bundle['constituents'] if c['owner_kind']=='physical_service')
        controls=[i for i in owner['binding_indices'] if bundle['bindings'][i]['kind']=='control']
        self.assertTrue(controls)
        for mutation in ('foreign_owner','wrong_schedule','second_water','duplicate_index'):
            changed=copy.deepcopy(bundle);actual=next(c for c in changed['constituents'] if c['instance_key']==owner['instance_key'])
            b=changed['bindings'][controls[0]]
            if mutation=='foreign_owner':b['instance_key']='kitchen'
            elif mutation=='wrong_schedule':b['schedule_id']=owner['schedule_ids']['hot_water_volume']
            elif mutation=='duplicate_index':actual['binding_indices'].append(controls[0])
            else:
                index=next(i for i in actual['binding_indices'] if changed['bindings'][i]['kind']=='load')
                actual['binding_indices'].append(len(changed['bindings']));changed['bindings'].append(copy.deepcopy(changed['bindings'][index]))
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):validate_bundle(changed)


class ContractStructureOnlyIntegrationTests(unittest.TestCase):
    def test_contract_structure_only_prepared_exact_parent_final_graph_and_negatives(self):
        from atlas_schedules.source_compositions import _derive_prepared_source_parent,compose_source_parent
        from atlas_schedules.physical_sets import bind_exact_projections
        from atlas_schedules.resources import write_resources
        captured={};prepare=exact.PhysicalBindingTests.prepare
        def capture(helper,*args,**kwargs):
            result=prepare(helper,*args,**kwargs)
            captured['data']=copy.deepcopy(result[0]);captured['plan']=copy.deepcopy(result[3])
            return result
        with patch.object(exact.PhysicalBindingTests,'prepare',new=capture):complete=graph.exact_bundle(parent=True)
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        manifest=write_resources(Path(directory.name),captured['data'],{})
        resources=ResourceSet(Path(directory.name),manifest['resource_set_id'])
        plan=captured['plan'];allocation=plan['source_allocations'][0];key=allocation['parent_instance_key']
        complete['metadata']['resource_set_id']=resources.resource_set_id
        for real in complete['metadata']['building_realizations']:real['inventory_resource']['resource_set_id']=resources.resource_set_id
        validate_bundle(complete)
        staged=copy.deepcopy(complete);staged['constituents']=[c for c in staged['constituents'] if c['instance_key']!=key]
        # Incoming partial graphs still reject; the private producer never calls
        # the incoming composer and consumes actual source-prepared children.
        with self.assertRaises(GeneratorError):compose_source_parent(copy.deepcopy(staged),allocation,resources)
        for mutation in ('wrong_type','wrong_rid','foreign_child','foreign_reference','wrong_variant'):
            changed=copy.deepcopy(staged);resource=resources
            if mutation=='wrong_type':resource=object()
            elif mutation=='wrong_rid':changed['metadata']['resource_set_id']='foreign'
            elif mutation=='foreign_child':changed['constituents'][0]['program_id']='foreign'
            elif mutation=='foreign_reference':changed['constituents'][0]['binding_indices']=[999]
            else:changed['constituents'][0]['generation']['method_variant']['key']['member_evidence_view']='foreign'
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):
                _derive_prepared_source_parent(changed,allocation,resource)
        # Return to actual pre-bind emission, without trimming original proof.
        staged['metadata']['building_realizations']=[]
        for c in staged['constituents']:
            if c['owner_kind']=='program':c['service_set_projections']=[]
        result=_derive_prepared_source_parent(staged,allocation,resources)
        bind_exact_projections(result,plan)
        validate_bundle(result)
        self.assertEqual(result['metadata']['building_realizations'][0]['native_context']['execution_authority'],
                         complete['metadata']['building_realizations'][0]['native_context']['execution_authority'])
        parent=next(c for c in result['constituents'] if c['instance_key']==key)
        self.assertEqual(parent['schedule_ids'],{})
        self.assertTrue(parent['service_set_projections'])
        self.assertEqual(parent['inputs']['year'],2007)
        self.assertEqual(parent['generation']['source_inputs'],allocation['parent_resolved']['inputs']['source_context'])

    def test_stock_uses_original_numeric_cohort_without_apartment_widening(self):
        from atlas_schedules.generator import collect_physical_unit_actors
        from atlas_schedules.residential.activity import simulate_activities
        from atlas_schedules.service_graph import _actors
        root=Path(__file__).resolve().parents[1]/'atlas_schedules/data'
        resource=ResourceSet(root,json.loads((root/'manifest.json').read_text())['resource_set_id'])
        for n in (0.0,2.9,2,1.0):
            instance={'key':'stock','owner_kind':'program'}
            resolved={'source_family':'existing_stock_source_fixture','inputs':{'residents':n,
                'source_context':{'method':'resstock_time_allocation_with_selected_source_companions'}}}
            actors=collect_physical_unit_actors([(instance,resolved)],'1.2.0')
            self.assertEqual(actors[0]['stochastic_action'],'generate')
            retained={'instance_key':'stock','owner_kind':'program','source':{'source_family':resolved['source_family']},
                      'inputs':{'residents':n},'generation':{'source_inputs':resolved['inputs']['source_context']}}
            self.assertEqual(_actors({'constituents':[retained]}),actors)
            self.assertIs(resolved['inputs']['residents'],n)
            if n==0:
                with patch('atlas_schedules.residential.activity.source_streams',side_effect=AssertionError('N0 streams')):
                    receipt=simulate_activities({'year':2007,'residents':n},42,resource)
                self.assertEqual(receipt['status'],'upstream_zero_residents_skip')
                self.assertEqual(receipt['residents_input'],n)
            if n==2.9:
                # Existing source to_i behavior is retained by the real kernel.
                receipt=simulate_activities({'year':2007,'residents':n},42,resource)
                self.assertEqual(receipt['simulated_residents'],2)
                self.assertEqual(receipt['residents_input'],2.9)
        for n in (True,float('inf'),float('nan'),-1,.5):
            instance={'key':'stock','owner_kind':'program'}
            resolved={'source_family':'existing_stock_source_fixture','inputs':{'residents':n,
                'source_context':{'method':'resstock_time_allocation_with_selected_source_companions'}}}
            with self.subTest(n=n),self.assertRaises(GeneratorError):collect_physical_unit_actors([(instance,resolved)],'1.2.0')

    def test_contract_structure_only_mixed_request_preparation_keeps_real_engines(self):
        from atlas_schedules import physical_sets,caller_unit_water,generator
        from atlas_schedules.resources import write_resources
        data,params=exact.records_fixture(parent=True)
        req=caller.compiled();real=caller.realization([caller.unit('u','caller-draw',[req])])
        temporary,caller_resources,_=caller.resource_fixture([req]);self.addCleanup(temporary.cleanup)
        data.update(copy.deepcopy(caller_resources._records))
        caller_instance=caller.pairs(real,{req['programme']['value']['id']:req},False)[0][0]
        original=copy.deepcopy(params['instances'])
        # Interleave a caller physical owner among an actual exact source parent
        # and its original physical owners; declarations deliberately caller-first.
        params['instances'].insert(1,caller_instance)
        params['building_realizations'].insert(0,real)
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        manifest=write_resources(Path(directory.name),data,{})
        resources=ResourceSet(Path(directory.name),manifest['resource_set_id'])
        with (patch.object(physical_sets,'_qualified_exact_context',return_value=True),
              patch.object(physical_sets,'_qualified_execution_association',return_value=True),
              patch.object(caller_unit_water,'_qualified_caller_water_method',return_value=True),
              patch('atlas_schedules.generator.sample_operating_parameters',side_effect=AssertionError('preparation RNG'))):
            modes,exact_params,actual,caller_params=generator._prepare_v12_request(params,resources)
            pairs=[(i,actual.get(i['key'],{})) for i in params['instances']]
            caller_plan=caller_unit_water.prepare_caller_water(params,pairs,resources)
            exact_plan=physical_sets.prepare_exact_bindings(exact_params,
                [(i,r) for i,r in caller_plan['resolved_instances'] if i['key'] in actual],resources)
            merged=generator._merge_exact_preparation(caller_plan['resolved_instances'],exact_plan,
                                                     {i['key'] for i in params['instances']})
        children=[i['key'] for i in exact_plan['source_allocations'][0]['children']]
        self.assertEqual([i['key'] for i,r in merged],children+[caller_instance['key']]+[i['key'] for i in original[1:]])
        self.assertEqual(modes[caller_instance['key']],caller_unit_water.MODE)
        physical=next(r for i,r in merged if i['key']==caller_instance['key'])
        self.assertEqual(physical['inputs']['source_context']['method'],caller_unit_water.METHOD)
        self.assertEqual(physical['demands'][0]['host'],'building_service')
        self.assertEqual(exact_plan['source_allocations'][0]['parent_instance_key'],original[0]['key'])
        self.assertEqual(len(caller_plan['owners']),1)
        self.assertEqual(len(exact_plan['owners']),len(original)-1)
        # No parent/child canonical view or original reference was rewritten.
        for i,r in merged:
            if i['key'] in children:self.assertIn('method_variant',r)
        with self.assertRaises(GeneratorError) as collision:
            generator._merge_exact_preparation(pairs,exact_plan,{children[0]})
        self.assertEqual(collision.exception.code,'duplicate_instance')

    def test_contract_structure_only_authority_coverage_context_target_phases(self):
        helper=exact.PhysicalBindingTests();self.addCleanup(helper.doCleanups)
        # Run real independently verified ResourceSets and actual source engines;
        # only the production policy predicate is qualified locally by helper.
        cases=[('coverage','requires_binding',lambda d,p:p['instances'].pop()),
               ('identity','shared_service_conflict',lambda d,p:p['instances'][1].update(source_fixture_role_id='foreign')),
               ('group','operating_group_conflict',lambda d,p:p['instances'][1].update(operating_group='foreign'))]
        for label,code,mutation in cases:
            with self.subTest(phase=label),patch('atlas_schedules.generator.assign_physical_unit_sequence',side_effect=AssertionError('RNG')):
                with self.assertRaises(GeneratorError) as caught:helper.prepare(mutate=mutation)
                self.assertEqual(caught.exception.code,code)
                self.assertTrue(caught.exception.path)
        with self.assertRaises(GeneratorError) as integrity:
            helper.prepare(mutate=lambda d,p:d['reference','physical-service__water']['recipe']['resolved']['source'].update(building_type='foreign'))
        self.assertEqual(integrity.exception.code,'source_integrity')
        with self.assertRaises(GeneratorError) as caught:
            helper.prepare(parent=True,mutate=lambda d,p:p['instances'][0]['inputs'].update(composition_basis_mode='caller_parent_floor_area'))
        self.assertEqual(caught.exception.code,'incompatible_source_composition')
        from atlas_schedules.budgets import reference_budget,bind_budget
        demand={'quantity':'hot_water_volume','value':None,'basis':'floor_area','unit':'m3/s/m2',
                'fuel':'water','host':'building_service','evidence':{'label':'contract_structure_only'}}
        with self.assertRaises(GeneratorError) as target:reference_budget(demand,[.1]*8760)
        self.assertEqual((target.exception.code,target.exception.path),('unresolved_annual_target','/demand/value'))
        demand['value']=1e-8
        target=reference_budget(demand,[.1]*8760)
        with self.assertRaises(GeneratorError) as generated:bind_budget(target,[0.0]*8760)
        self.assertEqual((generated.exception.code,generated.exception.path),('zero_generated_integral','/values'))

    def test_contract_structure_only_incoming_two_modes_composition(self):
        # Pure retained graphs built with unittest-local qualification only.
        first=graph.exact_bundle();second=graph.caller_bundle(alternatives=False)
        before=[copy.deepcopy(first),copy.deepcopy(second)]
        with patch('atlas_schedules.resources.ResourceSet.load',side_effect=AssertionError('incoming lookup')):
            result=compose_constituents([first,second],graph.mixture(
                members=[{'instance_key':first['constituents'][0]['instance_key'],'weight':.5},
                         {'instance_key':second['constituents'][1]['instance_key'],'weight':.5}]),exact.CALENDAR)
            validate_bundle(result)
        self.assertEqual([first,second],before)
        self.assertEqual(len(result['metadata']['building_realizations']),2)
        invalid=copy.deepcopy(result);invalid['bindings'][0]['schedule_id']='missing'
        with self.assertRaises(GeneratorError) as reference:validate_bundle(invalid)
        self.assertEqual(reference.exception.code,'invalid_reference')
        self.assertEqual(reference.exception.path,'/bindings/0/schedule_id')


if __name__=='__main__':unittest.main()
