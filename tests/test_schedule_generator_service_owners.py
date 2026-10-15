"""Explicit version selection and truthful typed service ownership contracts."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from atlas_schedules.comparison import compare_bundles
from atlas_schedules.contract import validate_request,validate_bundle
from atlas_schedules.errors import GeneratorError
from tests.test_schedule_generator_pilot import GeneratorCase,OFFICE,ROOT


class ServiceRequestContractTests(unittest.TestCase):
    def params(self):
        return {'schema_version':'1.1.0','resource_set_id':'explicit-contract-resource',
            'calendar':{'year':2007,'clock':'local_standard_time'},'instances':[
                {'owner_kind':'physical_service','key':'actual-booster','source_service_id':'service-26df36d04c21572b9838d63f',
                 'physical_id':'caller-declared-fixture','inputs':{},'operating_group':'restaurant',
                 'basis_bindings':{'extents':{'absolute':{'value':1,'unit':'1','evidence':{'caller':'explicit whole fixture'}}}}}]}

    def test_explicit_11_service_only_request_has_no_invented_programme(self):
        params=self.params();error=None
        try:validate_request(params,42)
        except GeneratorError as caught:error=caught
        self.assertIsNone(error,'Explicit typed service contract is not implemented: '+str(error))
        self.assertNotIn('program_id',params['instances'][0])

    def test_explicit_11_program_and_service_union_accepts_truthful_links(self):
        params=self.params()
        params['instances'].insert(0,{'owner_kind':'program','key':'kitchen','program_id':'program-76fabb7b85c683f4f7d8c873',
            'inputs':{},'basis_bindings':{},'operating_group':'restaurant',
            'service_links':{'service-24ad7408506ea3d448dc35d0':'actual-main'}})
        # Contract shape is separate from the later exact source recipe/link resolver.
        params['instances'][1]['key']='actual-main'
        params['instances'][1]['source_service_id']='service-24ad7408506ea3d448dc35d0'
        error=None
        try:validate_request(params,42)
        except GeneratorError as caught:error=caught
        self.assertIsNone(error,'Typed programme/service union is not implemented: '+str(error))

    def test_version_and_foreign_identity_reject_instead_of_implicit_inference(self):
        for mutation in ('absent_version','old_version','unknown_version','null_version','foreign_program',
                         'missing_physical_id','missing_service_id','missing_kind','derived_request'):
            params=self.params();owner=params['instances'][0]
            if mutation=='absent_version':params.pop('schema_version')
            if mutation=='old_version':params['schema_version']='1.0.0'
            if mutation=='unknown_version':params['schema_version']='1.2.0'
            if mutation=='null_version':params['schema_version']=None
            if mutation=='foreign_program':owner['program_id']='not-a-service-programme'
            if mutation=='missing_physical_id':owner.pop('physical_id')
            if mutation=='missing_service_id':owner.pop('source_service_id')
            if mutation=='missing_kind':owner.pop('owner_kind')
            if mutation=='derived_request':owner['owner_kind']='derived_result'
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):validate_request(params,42)

    def test_cli_envelope_must_match_effective_params_version(self):
        from atlas_schedules.__main__ import main
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for envelope,marker in [('1.1.0',None),('1.0.0','1.1.0'),('1.2.0','1.2.0')]:
                params=self.params()
                if marker is None:params.pop('schema_version')
                else:params['schema_version']=marker
                (root/'request.json').write_text(json.dumps({'schema_version':envelope,'params':params,'seed':42}))
                with self.subTest(envelope=envelope,marker=marker),self.assertRaises(GeneratorError):
                    main(['--request',str(root/'request.json'),'--output',str(root/'bundle.json')])


class ServiceVersionApiTests(GeneratorCase):
    def test_absent_and_explicit_10_preserve_existing_science(self):
        params=self.params([self.instance('office',OFFICE)])
        expected=self.generate(params,42);explicit=copy.deepcopy(params);explicit['schema_version']='1.0.0'
        error=None
        try:actual=self.generate(explicit,42)
        except GeneratorError as caught:error=caught
        self.assertIsNone(error,'Explicit legacy version marker is not dispatched: '+str(error))
        self.assertEqual(compare_bundles(actual,expected,expected['metadata']['comparison_policy']),[])
        self.assertEqual(actual['schema_version'],'1.0.0')

    def test_programme_only_11_api_cli_equivalence_and_original_targets(self):
        params=self.params([self.instance('office',OFFICE)])
        old=self.generate(params,42)
        params['schema_version']='1.1.0';params['instances'][0]['owner_kind']='program'
        error=None
        try:actual=self.generate(params,42)
        except GeneratorError as caught:error=caught
        self.assertIsNone(error,'Explicit new programme API is not implemented: '+str(error))
        self.assertEqual(actual['schema_version'],'1.1.0')
        self.assertTrue(all(c['owner_kind']=='program' for c in actual['constituents']))
        self.assertTrue(all(b['owner_kind']=='program' for b in actual['bindings']))
        legacy=copy.deepcopy(actual);legacy['schema_version']='1.0.0'
        for record in legacy['constituents']+legacy['bindings']:record.pop('owner_kind')
        for owner in legacy['constituents']:
            owner['generation'].pop('operating_group');owner.pop('required_service_links')
        self.assertEqual(compare_bundles(legacy,old,old['metadata']['comparison_policy']),[])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);request=root/'request.json';output=root/'bundle.json'
            request.write_text(json.dumps({'schema_version':'1.1.0','params':params,'seed':42}))
            result=subprocess.run([sys.executable,'-m','atlas_schedules','--request',str(request),'--output',str(output)],
                                  cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(compare_bundles(json.loads(output.read_text()),actual,actual['metadata']['comparison_policy']),[])

    def service_fixture(self):
        """Labelled contract fixture, not an actual restaurant recipe/native claim."""
        bundle=self.generate(self.params([self.instance('synthetic-service-contract',OFFICE)]),42)
        owner=bundle['constituents'][0]
        demand=next(d for d in owner['demands'] if d['quantity']=='hot_water_volume')
        binding=next(b for b in bundle['bindings'] if b.get('demand_id')==demand['demand_id'])
        slot=demand['slot'];sid=owner['schedule_ids'][slot]
        owner.update(demands=[demand],controls=[],slots=[s for s in owner['slots'] if s['slot']==slot],
                     schedule_ids={slot:sid},binding_indices=[0])
        owner['source']['source_family']='synthetic_contract_fixture'
        owner['evidence'].append({'interpretation':'Synthetic identity/composition contract fixture only; no source service or native certification'})
        bundle.update(schema_version='1.1.0',bindings=[binding],schedules={sid:bundle['schedules'][sid]})
        for record in (owner,binding):
            record.pop('program_id')
            record.update(owner_kind='physical_service',source_service_id='service-000000000000000000000000',
                          physical_id='explicit-synthetic-physical-fixture')
        extent={'value':100,'unit':'m2','evidence':{'caller':'Synthetic explicit whole fixture extent'}}
        owner['basis_bindings']={'extents':{'floor_area':copy.deepcopy(extent)},'multiplicity':1}
        owner['shared_services']=[{'demand_id':demand['demand_id'],'source_service_id':owner['source_service_id'],
            'physical_id':owner['physical_id'],'mode':'whole','ownership':'instantiate_once','extent':extent}]
        owner['generation']['operating_group']='synthetic-contract-context'
        return bundle

    def test_typed_physical_bundle_and_scientific_identity_need_no_program_id(self):
        bundle=self.service_fixture();error=None
        try:
            validate_bundle(bundle)
            differences=compare_bundles(bundle,copy.deepcopy(bundle),bundle['metadata']['comparison_policy'])
        except (GeneratorError,KeyError) as caught:error=caught
        self.assertIsNone(error,'Bundle/comparison remains programme-only: '+str(error))
        self.assertEqual(differences,[])
        self.assertNotIn('program_id',bundle['constituents'][0])
        changed=copy.deepcopy(bundle)
        for record in changed['constituents']+changed['bindings']:record['physical_id']='a-distinct-actual-fixture'
        self.assertTrue(compare_bundles(changed,bundle,bundle['metadata']['comparison_policy']))

    def test_programme_only_11_generic_mixture_has_explicit_derived_identity(self):
        instances=[self.instance('office-a',OFFICE),self.instance('office-b',OFFICE)]
        for owner in instances:owner['owner_kind']='program'
        params=self.params(instances,{'program_id':'caller-result-label','composition_id':None,
            'members':[{'instance_key':i['key'],'weight':.5} for i in instances]})
        params['schema_version']='1.1.0';error=None
        try:bundle=self.generate(params,42)
        except (GeneratorError,KeyError) as caught:error=caught
        self.assertIsNone(error,'Generic composer did not propagate versioned derived identity: '+str(error))
        self.assertEqual(bundle['schema_version'],'1.1.0')
        self.assertEqual(bundle['constituents'][-1]['owner_kind'],'derived_result')
        self.assertTrue(all(bundle['bindings'][i]['owner_kind']=='derived_result' for i in bundle['constituents'][-1]['binding_indices']))
        validate_bundle(bundle)

    def test_generic_composer_reconstructs_service_owner_without_fabricated_programme(self):
        from atlas_schedules import compose_constituents
        service=self.service_fixture()
        params=self.params([self.instance('office',OFFICE,basis={'floor_area_m2':1000})])
        params['schema_version']='1.1.0';params['instances'][0]['owner_kind']='program'
        programme=self.generate(params,42)
        mixture={'program_id':'water-and-office','composition_id':None,'members':[{'instance_key':'office','weight':1}],
            'service_members':[{'instance_key':'synthetic-service-contract'}],
            'result_basis':'floor_area','denominator':{'value':1000,'unit':'m2','evidence':{'caller':'explicit physical result'}}}
        error=None
        try:actual=compose_constituents([programme,service],mixture,programme['metadata']['calendar'])
        except (GeneratorError,KeyError) as caught:error=caught
        self.assertIsNone(error,'Composer invented/demanded a programme identity for the service: '+str(error))
        validate_bundle(actual)
        retained=next(c for c in actual['constituents'] if c.get('owner_kind')=='physical_service')
        self.assertNotIn('program_id',retained)
        self.assertEqual(retained['physical_id'],'explicit-synthetic-physical-fixture')


class TypedReferenceContractTests(unittest.TestCase):
    def fixture(self):
        from tests.test_schedule_generator_contract import bundle
        value=bundle();value['schema_version']='1.1.0'
        for record in value['constituents']+value['bindings']:
            record.pop('program_id')
            record.update(owner_kind='physical_service',source_service_id='service-000000000000000000000000',
                          physical_id='synthetic-reference-contract-only')
        binding=value['bindings'][0]
        value['constituents'][0]['generation']['contract_component']={
            'method':'actual_generated_bound_trajectory_sum','components':[{
                **{k:binding[k] for k in ('instance_key','schedule_id','demand_id','owner_kind','source_service_id','physical_id')},
                'binding_index':0}]}
        return value

    def test_actual_11_component_requires_complete_typed_source_identity(self):
        value=self.fixture();validate_bundle(value)
        for field in ('owner_kind','source_service_id','physical_id'):
            changed=copy.deepcopy(value)
            changed['constituents'][0]['generation']['contract_component']['components'][0].pop(field)
            with self.subTest(field=field),self.assertRaises(GeneratorError):validate_bundle(changed)

    def test_mispointed_typed_owner_and_component_references_reject(self):
        value=self.fixture()
        for location,field in (('binding','physical_id'),('binding','source_service_id'),
                               ('component','physical_id'),('component','source_service_id'),('component','owner_kind')):
            changed=copy.deepcopy(value)
            record=changed['bindings'][0] if location=='binding' else changed['constituents'][0]['generation']['contract_component']['components'][0]
            record[field]='program' if field=='owner_kind' else ('service-'+'1'*24 if field=='source_service_id' else 'wrong-physical-fixture')
            with self.subTest(location=location,field=field),self.assertRaises(GeneratorError):validate_bundle(changed)

    def test_static_11_schemas_match_bounded_checker_and_oracle(self):
        from jsonschema import Draft202012Validator
        from atlas_schedules.contract import _schema_errors
        values={'request':ServiceRequestContractTests().params(),'bundle':self.fixture()}
        for name,valid in values.items():
            schema=json.loads((ROOT/'schemas'/f'schedule-generator-{name}-v1_1.schema.json').read_text(encoding='utf-8'))
            self.assertEqual(schema,json.loads((ROOT/'atlas_schedules/schemas'/f'schedule-generator-{name}-v1_1.schema.json').read_text(encoding='utf-8')))
            Draft202012Validator.check_schema(schema);oracle=Draft202012Validator(schema)
            oracle.validate(valid);_schema_errors(valid,name,'1.1.0')
            for mutation in ('missing_kind','foreign_program','missing_physical','wrong_version'):
                changed=copy.deepcopy(valid)
                record=changed['instances'][0] if name=='request' else changed['constituents'][0]
                if mutation=='missing_kind':record.pop('owner_kind')
                elif mutation=='foreign_program':record['program_id']='not-a-service-programme'
                elif mutation=='missing_physical':record.pop('physical_id')
                else:changed['schema_version']='1.0.0'
                with self.subTest(name=name,mutation=mutation):
                    self.assertTrue(list(oracle.iter_errors(changed)))
                    with self.assertRaises(GeneratorError):_schema_errors(changed,name,'1.1.0')


class ServiceSelectionContractTests(unittest.TestCase):
    def params(self):
        value=ServiceRequestContractTests().params()
        value['instances'].insert(0,{'owner_kind':'program','key':'kitchen','program_id':'source-programme',
                                   'inputs':{},'basis_bindings':{},'operating_group':'restaurant'})
        value['mixture']={'program_id':'caller-result','composition_id':None,
            'members':[{'instance_key':'kitchen','weight':1}],
            'service_members':[{'instance_key':'actual-booster'}],
            'result_basis':'floor_area','denominator':{'value':1000,'unit':'m2','evidence':{'caller':'explicit'}}}
        return value

    def test_separate_whole_services_preserve_programme_normalization_and_service_only(self):
        value=self.params();validate_request(value,42)
        value['mixture']['members']=[];validate_request(value,42)

    def test_invalid_service_weight_disable_and_weighted_service_selection_reject(self):
        for mutation in ('weighted_service','weight','disable','duplicate','programme_service_key',
                         'missing_owner','empty_selections','service_without_denominator','legacy'):
            value=self.params();mixture=value['mixture']
            if mutation=='weighted_service':mixture['members']=[{'instance_key':'actual-booster','weight':1}]
            elif mutation=='weight':mixture['service_members'][0]['weight']=0
            elif mutation=='disable':mixture['service_members'][0]['enabled']=False
            elif mutation=='duplicate':mixture['service_members']*=2
            elif mutation=='programme_service_key':mixture['service_members'][0]['instance_key']='kitchen'
            elif mutation=='missing_owner':mixture['service_members'][0]['instance_key']='missing'
            elif mutation=='empty_selections':mixture['members']=[];mixture.pop('service_members')
            elif mutation=='service_without_denominator':mixture.pop('denominator');mixture.pop('result_basis')
            else:
                value.pop('schema_version')
                for instance in value['instances']:instance.pop('owner_kind')
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):validate_request(value,42)


class WholeServiceClosureTests(unittest.TestCase):
    def fixtures(self,linked=True):
        """Small labelled contract data; no restaurant method qualification claim."""
        from tests.test_schedule_generator_contract import bundle
        from atlas_schedules.canonical import schedule_id
        base=bundle();base['schema_version']='1.1.0'
        owner=base['constituents'][0];owner['owner_kind']='program'
        base['bindings'][0]['owner_kind']='program'
        owner['generation']['operating_group']='contract-building'
        owner['basis_bindings']={'floor_area_m2':1000}
        physical=copy.deepcopy(base);service=physical['constituents'][0];binding=physical['bindings'][0]
        old_sid=binding['schedule_id'];new_sid=schedule_id('main-fixture','hot_water_volume')
        physical['schedules']={new_sid:{**physical['schedules'][old_sid],'id':new_sid}}
        for record in (service,binding):
            record.pop('program_id');record.update(owner_kind='physical_service',source_service_id='service-'+'0'*24,
                                                 physical_id='contract-whole-main',instance_key='main-fixture')
        binding.update(slot='hot_water_volume',schedule_id=new_sid,demand_id='contract-water',host='building_service',fuel='none')
        binding['reference_target'].update(quantity='hot_water_volume',total=5.76,unit='m3/m2',magnitude_unit='m3/s/m2',
                                          host='building_service',fuel='none')
        binding['effective_magnitude'].update(value=1e-6,unit='m3/s/m2')
        binding['scaling_receipt'].update(achieved_total=5.76,unit='m3/m2')
        demand=service['demands'][0];demand.update(demand_id='contract-water',slot='hot_water_volume',quantity='hot_water_volume',
            value=1e-6,unit='m3/s/m2',host='building_service',fuel='none',heat_fractions=None)
        service['slots']=[{'slot':'hot_water_volume','unit':'fraction','kind':'load','source_schedule_id':'synthetic-water-only'}]
        service['schedule_ids']={'hot_water_volume':new_sid}
        extent={'value':100,'unit':'m2','evidence':{'caller':'explicit synthetic whole source extent'}}
        service['basis_bindings']={'extents':{'floor_area':copy.deepcopy(extent)},'multiplicity':1}
        service['shared_services']=[{'demand_id':'contract-water','source_service_id':service['source_service_id'],
            'physical_id':service['physical_id'],'mode':'whole','ownership':'instantiate_once','extent':extent,
            'source_note':'Synthetic wire/closure fixture only, not native source certification'}]
        # Complete labelled source operands for the strict required-link wire test.
        # These are synthetic contract data, not restaurant/native certification.
        from atlas_schedules.budgets import reference_budget
        from atlas_schedules.calendar import evaluate_rules
        sid=service['source_service_id'];eid='synthetic-original-service-evidence'
        owner['required_service_links']=[]
        for item in (owner,service):
            item['source']['building_type']='SyntheticContractFixture'
            item['inputs']['source_hoo_configuration_id']='synthetic-contract-context'
            item['generation']['source_inputs']={'year':2007,'holidays':[],
                'configuration_id':'synthetic-contract-context','source_hoo_configuration_id':'synthetic-contract-context',
                'method':'synthetic_contract_only','standards_version':'synthetic','steps_per_hour':1,
                'source_clock':{'interpretation':'Explicit synthetic local-standard clock'},'occupancy_adjustment':None,
                'occupancy_aggregation':{'policy':'synthetic_contract_only','evidence_view':'reviewed'},
                'configuration_association':{'conditioning_inputs':{'synthetic':'contract only'}}}
        service['source']['source_id']=sid
        load={'demand_id':sid,'service_id':sid,'scope':'building_service','quantity':'hot_water_volume',
            'value':1e-6,'unit':'m3/s/m2','basis':'floor_area','schedule_id':'synthetic-water-only',
            'status':'known','required_inputs':['floor_area'],'evidence_id':eid,
            'target_temperature_degC':60,'zone_heat_assignment':'unresolved','thermal_effects':{}}
        path='SyntheticContractFixture|fixture|main|program-fixture'
        definition={'id':sid,'building_type':'SyntheticContractFixture','template':'fixture','end_use':'main',
            'path_id':path,'beneficiary_program_ids':['program-fixture'],'load':copy.deepcopy(load),
            'evidence_ids':[eid],'source_evidence_ids':[],'ownership':'instantiate_once',
            'assignment':'consumer_host_when_applicable'}
        service['shared_services'][0].update(demand_id=sid,source_service_definition=copy.deepcopy(definition))
        demand.update(demand_id=sid,fuel='water',evidence={'original_service':copy.deepcopy(definition),
            'interpretation':'Synthetic wire fixture only, no native/source certification'})
        reference={'time_resolution_minutes':60,'rules':[{'type':'Constant','day_types':['Default'],
            'start_date':'01-01','end_date':'12-31','values':[1600/8760]}]}
        service['generation']['source_inputs']['slot_sources']={'hot_water_volume':reference}
        target=reference_budget(demand,evaluate_rules(reference,2007,[])['values'])
        binding.update(demand_id=sid,fuel='water',reference_target=copy.deepcopy(target))
        original=copy.deepcopy(load);original['scope']='program_service'
        requirement={'source_service_id':sid,'source_channel':'hot_water_volume','required':True,
            'original_demand':original,'evidence':{'id':eid,'locator':'synthetic/draw_paths/'+path,
                'interpretation':'Synthetic contract original requirement, not an atlas programme/source claim'}}
        if linked:owner['required_service_links']=[copy.deepcopy(requirement)]
        if linked:
            owner['service_links']=[{'required':True,'source_channel':'hot_water_volume','owner_kind':'physical_service',
                'source_service_id':service['source_service_id'],'physical_id':service['physical_id'],
                'instance_key':service['instance_key'],'operating_group':'contract-building','binding_index':0,
                'demand_id':binding['demand_id'],'slot':binding['slot'],'schedule_id':new_sid,
                'evidence':{'original_programme_load':copy.deepcopy(original),'source_reference_target':copy.deepcopy(target),
                    'source_requirement':copy.deepcopy(requirement['evidence']),
                    'interpretation':'Synthetic required-link contract fixture only'}}]
            # This outgoing generated reference is global in the joined input bundle.
            owner['service_links'][0]['binding_index']=1
        base['constituents'].append(service);base['bindings'].append(binding);base['schedules'].update(physical['schedules'])
        service['binding_indices']=[1]
        return base

    def mixture(self,programme_weight=1,explicit=False,service_only=False):
        return {'program_id':'contract-result','composition_id':None,
            'members':[] if service_only else [{'instance_key':'a/b','weight':programme_weight}],
            **({'service_members':[{'instance_key':'main-fixture'}]} if explicit or service_only else {}),
            'result_basis':'floor_area','denominator':{'value':1000,'unit':'m2','evidence':{'caller':'explicit result basis'}}}

    def compose(self,value,mixture):
        from atlas_schedules import compose_constituents
        return compose_constituents([value],mixture,value['metadata']['calendar'])

    def test_positive_programme_link_closes_once_and_explicit_selector_deduplicates(self):
        value=self.fixtures()
        for explicit in (False,True):
            actual=self.compose(value,self.mixture(explicit=explicit));parent=actual['constituents'][-1]
            load=[actual['bindings'][i] for i in parent['binding_indices'] if actual['bindings'][i]['kind']=='load']
            self.assertEqual(next(b for b in load if b['reference_target']['quantity']=='lighting')['reference_target']['total'],20000)
            water=next(b for b in load if b['reference_target']['quantity']=='hot_water_volume')
            self.assertAlmostEqual(water['reference_target']['total'],.576)
            self.assertEqual(len(water['reference_target']['evidence']['components']),1)
            closure=parent['generation']['service_selection']
            self.assertEqual(closure['original_programme_members'],self.mixture()['members'])
            self.assertEqual(closure['effective_service_members'],[{'instance_key':'main-fixture'}])
            self.assertEqual(closure['required_links'][0]['deduplicated'],explicit)
            validate_bundle(actual)

    def test_service_only_selects_whole_fixture_without_programme_weight(self):
        actual=self.compose(self.fixtures(linked=False),self.mixture(service_only=True))
        parent=actual['constituents'][-1]
        self.assertEqual(len(parent['demands']),1)
        self.assertAlmostEqual(actual['bindings'][parent['binding_indices'][0]]['reference_target']['total'],.576)

    def test_link_identity_group_owner_and_extent_conflicts_fail(self):
        for mutation in ('missing_owner','wrong_sid','wrong_physical','wrong_group','wrong_binding','missing_extent'):
            value=self.fixtures();link=value['constituents'][0]['service_links'][0]
            if mutation=='missing_owner':link['instance_key']='missing'
            elif mutation=='wrong_sid':link['source_service_id']='service-'+'1'*24
            elif mutation=='wrong_physical':link['physical_id']='wrong'
            elif mutation=='wrong_group':link['operating_group']='foreign-context'
            elif mutation=='wrong_binding':link['binding_index']=0
            else:value['constituents'][1]['shared_services'][0].pop('extent')
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):self.compose(value,self.mixture())

    def second_programme(self,value,linked=True):
        from atlas_schedules.canonical import schedule_id
        owner=copy.deepcopy(value['constituents'][0]);binding=copy.deepcopy(value['bindings'][0])
        old_sid=binding['schedule_id'];sid=schedule_id('second-programme',binding['slot'])
        owner['instance_key']='second-programme';owner['schedule_ids']={binding['slot']:sid}
        owner['binding_indices']=[len(value['bindings'])]
        if not linked:
            owner.pop('service_links',None);owner['required_service_links']=[]
        binding.update(instance_key=owner['instance_key'],schedule_id=sid)
        binding['reference_target']['total']*=3;binding['effective_magnitude']['value']*=3
        binding['scaling_receipt']['achieved_total']*=3;owner['demands'][0]['value']*=3
        value['bindings'].append(binding);value['constituents'].append(owner)
        value['schedules'][sid]={**copy.deepcopy(value['schedules'][old_sid]),'id':sid}

    def test_shared_programme_aliases_keep_unequal_energy_weights_and_one_volume(self):
        value=self.fixtures();self.second_programme(value)
        for explicit in (False,True):
            mixture=self.mixture(explicit=explicit)
            mixture['members']=[{'instance_key':'a/b','weight':.25},{'instance_key':'second-programme','weight':.75}]
            actual=self.compose(value,mixture);parent=actual['constituents'][-1]
            targets={d['quantity']:d['annual_target']['total'] for d in parent['demands']}
            self.assertEqual(targets['lighting'],50000)
            self.assertAlmostEqual(targets['hot_water_volume'],.576)
            receipt=parent['generation']['service_selection']
            self.assertEqual(receipt['original_programme_members'],mixture['members'])
            self.assertEqual([r['deduplicated'] for r in receipt['required_links']],[explicit,True])
            self.assertEqual(receipt['effective_service_members'],[{'instance_key':'main-fixture'}])

    def test_zero_programme_has_no_closure_and_unallocated_booster_is_explicit_only(self):
        from atlas_schedules.canonical import schedule_id
        value=self.fixtures();self.second_programme(value,linked=False)
        booster=copy.deepcopy(value['constituents'][1]);binding=copy.deepcopy(value['bindings'][1])
        old_sid=binding['schedule_id'];sid=schedule_id('unallocated-booster',binding['slot'])
        booster.update(instance_key='unallocated-booster',physical_id='unallocated-physical-booster',
                       source_service_id='service-'+'1'*24,binding_indices=[len(value['bindings'])],schedule_ids={binding['slot']:sid})
        booster['shared_services'][0].update(physical_id=booster['physical_id'],source_service_id=booster['source_service_id'])
        binding.update(instance_key=booster['instance_key'],physical_id=booster['physical_id'],source_service_id=booster['source_service_id'],schedule_id=sid)
        value['constituents'].append(booster);value['bindings'].append(binding)
        value['schedules'][sid]={**copy.deepcopy(value['schedules'][old_sid]),'id':sid}
        mixture=self.mixture();mixture['members']=[{'instance_key':'a/b','weight':0},{'instance_key':'second-programme','weight':1}]
        actual=self.compose(value,mixture);parent=actual['constituents'][-1]
        self.assertEqual(parent['generation']['service_selection']['effective_service_members'],[])
        self.assertFalse(any(d['quantity']=='hot_water_volume' for d in parent['demands']))
        mixture['members'][0]['weight']=.25;mixture['members'][1]['weight']=.75
        parent=self.compose(value,mixture)['constituents'][-1]
        self.assertEqual(parent['generation']['service_selection']['effective_service_members'],[{'instance_key':'main-fixture'}])
        mixture['service_members']=[{'instance_key':'unallocated-booster'}]
        parent=self.compose(value,mixture)['constituents'][-1]
        self.assertEqual(parent['generation']['service_selection']['effective_service_members'],
                         [{'instance_key':'unallocated-booster'},{'instance_key':'main-fixture'}])
        self.assertAlmostEqual(next(d for d in parent['demands'] if d['quantity']=='hot_water_volume')['annual_target']['total'],1.152)

    def test_private_projection_retains_required_physical_owner_and_inverse_reference_map(self):
        from atlas_schedules.source_compositions import project_source_members
        value=self.fixtures();self.second_programme(value,linked=False)
        local,inverse=project_source_members(value,['a/b'])
        self.assertEqual([c['instance_key'] for c in local['constituents']],['a/b','main-fixture'])
        self.assertEqual(inverse,{0:0,1:1})
        self.assertEqual(local['constituents'][0]['service_links'][0]['binding_index'],1)
        validate_bundle(local)

    def test_public_merge_rebases_all_required_service_and_component_references(self):
        from atlas_schedules import compose_constituents
        from tests.test_schedule_generator_contract import bundle
        from atlas_schedules.canonical import schedule_id
        prefix=bundle();owner=prefix['constituents'][0];binding=prefix['bindings'][0]
        sid=schedule_id('prefix-owner',binding['slot']);old=binding['schedule_id']
        owner.update(instance_key='prefix-owner',schedule_ids={binding['slot']:sid})
        binding.update(instance_key='prefix-owner',schedule_id=sid)
        prefix['schedules']={sid:{**prefix['schedules'][old],'id':sid}}
        actual=compose_constituents([prefix,self.fixtures()],self.mixture(),prefix['metadata']['calendar'])
        programme=next(c for c in actual['constituents'] if c['instance_key']=='a/b')
        self.assertEqual(programme['service_links'][0]['binding_index'],2)
        self.assertEqual(actual['bindings'][2]['owner_kind'],'physical_service')
        self.assertTrue(all('owner_kind' in record for record in actual['constituents']+actual['bindings']))
        parent=actual['constituents'][-1]
        components=[p for d in parent['demands'] for p in d['evidence']['components']]
        for component in components:
            binding=actual['bindings'][component['binding_index']]
            self.assertEqual(component['owner_kind'],binding['owner_kind'])
            self.assertEqual(component['schedule_id'],binding['schedule_id'])
        validate_bundle(actual)

    def test_absolute_fixture_has_unit_extent_and_cannot_apply_area_or_extra_multiplicity(self):
        value=self.fixtures(linked=False);owner=value['constituents'][1];binding=value['bindings'][1]
        extent={'value':1,'unit':'1','evidence':{'caller':'Synthetic absolute whole fixture only'}}
        owner['basis_bindings']={'extents':{'absolute':copy.deepcopy(extent)},'multiplicity':1}
        owner['shared_services'][0]['extent']=copy.deepcopy(extent)
        owner['demands'][0].update(basis='absolute',unit='m3/s')
        binding['reference_target'].update(basis='absolute',unit='m3',magnitude_unit='m3/s')
        binding['effective_magnitude'].update(basis='absolute',unit='m3/s');binding['scaling_receipt']['unit']='m3'
        actual=self.compose(value,self.mixture(service_only=True))
        self.assertAlmostEqual(actual['constituents'][-1]['demands'][0]['annual_target']['total'],.00576)
        for mutation in ('extent','multiplicity','area'):
            changed=copy.deepcopy(value);service=changed['constituents'][1]
            if mutation=='extent':
                service['shared_services'][0]['extent']['value']=2
                service['basis_bindings']['extents']['absolute']['value']=2
            elif mutation=='multiplicity':service['basis_bindings']['multiplicity']=2
            else:service['basis_bindings']['floor_area_m2']=100
            with self.subTest(mutation=mutation),self.assertRaises(GeneratorError):self.compose(changed,self.mixture(service_only=True))


if __name__=='__main__':unittest.main()
