"""Labelled contract fixtures: no native capture, certificate, or readiness claim."""
import copy
import hashlib
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from atlas_schedules.budgets import bind_budget
from atlas_schedules.canonical import schedule_id, canonical
from atlas_schedules.errors import GeneratorError
from atlas_schedules.owners import identity_fields
from atlas_schedules.resources import ResourceSet, write_resources
from tests.test_schedule_generator_physical_authority_v1_2 import source, evidence, consumed, fixture, census

CALENDAR = {'year': 2007, 'clock': 'local_standard_time', 'holidays': []}


def rules(value):
    return {'id': 'rules', 'time_resolution_minutes': 60, 'rules': [
        {'day_types': 'Default|WntrDsn|SmrDsn', 'type': 'Constant', 'values': [value],
         'start_date': '01-01', 'end_date': '12-31'}]}


def demand(load):
    return {**{k: copy.deepcopy(load[k]) for k in ('demand_id', 'quantity', 'basis', 'value', 'unit')},
        'slot': 'hot_water_volume', 'fuel': 'water', 'host': 'building_service',
        'evidence': {'locator': 'labelled source operand', 'original_value': copy.deepcopy(load), 'original_unit': load['unit']}}


def context(configuration):
    return {'configuration_id': configuration, 'source_hoo_configuration_id': configuration,
            'year': 2007, 'holidays': [], 'case_id': 'labelled-case'}


def artifact(value,path):
    return {'path':path,'sha256':hashlib.sha256(canonical(value)).hexdigest(),'locator':'/','value':copy.deepcopy(value)}


def records_fixture(mode='hotel', parent=False, zero=False, bad_weights=False, bad_area=False, original_context=False):
    from scripts.schedule_generator_physical_sets import compile_exact_inventory, compile_exact_requirements, compile_child_variant
    selected_configuration='source-context' if original_context else 'selected-context'
    records = fixture(); original = records['ordered_fixture_roles'][0]
    original['schedule_authority']['canonical_schedule']['value'] = rules(0 if zero else .2)
    load = original['service_definition']['value']['load']
    if mode == 'office':
        load.update(value=3.6592313912e-5, basis='absolute', unit='m3/s')
        original['source_basis'] = 'absolute'
        original['schedule_authority']['canonical_schedule']['value'] = rules(1478.2 / 8760)
        records['programmes'][0]['value']['loads'] = []
    else:
        load['value'] = .3515783333108323 / (3600 * 1752)
        records['programmes'][0]['value']['loads'] = [dict(copy.deepcopy(load), scope='program_service')]
    count = 3 if mode == 'office' else 4
    records['ordered_fixture_roles'] = []
    for i in range(count):
        role = copy.deepcopy(original); role.update(role_id='role-'+str(i), source_order=i)
        role['source_space'] = {'name': 'Room_'+str(i), 'handle': 'locked-'+str(i)}
        role['geometry_operands'].update(floor_area_m2=39.02202 if i == 0 else (624.3157440000001-156.08808)/12,
                                        space_multiplier=4, zone_multiplier=[1,10,1,1][i])
        records['ordered_fixture_roles'].append(role)
    if parent:
        leaf = records['programmes'][0]['value']
        # Deliberately unequal component areas/densities; parent scalar is unrelated.
        second = copy.deepcopy(leaf); second.update(id='leaf-two', source_id='source-two', service_ids=['water-two'])
        second['loads'][0].update(demand_id='water-two', service_id='water-two', value=2*load['value'])
        records['programmes'].append(source(second, '/programmes/1'))
        for i in range(2):
            role = copy.deepcopy(original); role.update(role_id='second-'+str(i), source_order=count+i,
                source_service_id='water-two', source_path_id='Fixture|2013|second')
            role['source_space'] = {'name': 'Second_'+str(i), 'handle': 'second-'+str(i)}
            role['geometry_operands'].update(floor_area_m2=10, space_multiplier=1, zone_multiplier=20)
            role['service_definition']['value'].update(id='water-two', path_id=role['source_path_id'], beneficiary_program_ids=['source-two'])
            role['service_definition']['value']['load'] = dict(copy.deepcopy(second['loads'][0]), scope='building_service')
            records['ordered_fixture_roles'].append(role)
        records['method_references'].append(source(dict(copy.deepcopy(records['method_references'][0]['value']), program_id='leaf-two')))
        areas = [624.3157440000001, 20]; total = math.fsum(areas)
        components = [{'program_id': p['value']['id'], 'weight': a/total, 'load': copy.deepcopy(p['value']['loads'][0])}
                      for p,a in zip(records['programmes'], areas)]
        p = {'id': 'parent', 'source_id': 'source-parent', 'building_type': 'Fixture', 'template': '2013',
             'evidence_view': 'reviewed', 'composition_id': 'mix', 'service_ids': [],
             'loads': [{'quantity': 'hot_water_volume', 'source_components': components, 'value': 999}]}
        records['programmes'].append(source(p, '/programmes/2'))
        records['compositions'] = [source({'id': 'mix', 'building_type': 'Fixture', 'template': '2013', 'evidence_view': 'reviewed',
            'members': [{'program_id': c['program_id'], 'source_program_id': prog['value']['source_id'],
                         'represented_area_m2': a, 'weight': c['weight']}
                        for c,prog,a in zip(components,records['programmes'],areas)]})]
        records['method_references'].append(source(dict(copy.deepcopy(records['method_references'][0]['value']),
            program_id='parent', context_evidence_view='reviewed', source_hoo_configuration_id='selected-context')))
    if parent:
        records['evidence_view'] = 'reviewed'
        if bad_weights:
            for c in records['programmes'][-1]['value']['loads'][0]['source_components']: c['weight']=0
            for c in records['compositions'][0]['value']['members']: c['weight']=0
        if bad_area:
            records['compositions'][0]['value']['members'][0]['represented_area_m2']+=100
            areas=[m['represented_area_m2'] for m in records['compositions'][0]['value']['members']]
            for c,m,a in zip(records['programmes'][-1]['value']['loads'][0]['source_components'],records['compositions'][0]['value']['members'],areas):
                c['weight']=a/sum(areas);m['weight']=c['weight']
    census(records); inventory = compile_exact_inventory(records); reqs = compile_exact_requirements(records, inventory)
    reference = {'inventory_id': 'labelled', 'inventory_sha256': inventory['inventory_sha256'],
                 'requirements_key': 'requirements', 'qualification_key': 'qualification'}
    data = {('reference','physical-fixture-inventory__labelled'): inventory, ('reference','requirements'): reqs}
    for prog in records['programmes']:
        p = prog['value']; loads = [demand(l) for l in p['loads'] if 'source_components' not in l]
        own = [r for r in reqs if r.get('programme',r.get('parent_programme'))['value']['id'] == p['id']]
        resolved = {'owner_kind': 'program', 'program_id': p['id'], 'recipe_id': 'recipe-'+p['id'],
            'source_family': 'labelled_contract_fixture', 'source': {'source_id': p['source_id'], 'building_type': 'Fixture',
                'template': '2013', 'evidence_view': p['evidence_view'], 'vintage': None, 'weather': None},
            'slots': [{'slot':'hot_water_volume','unit':'fraction','kind':'load','source_schedule_id':'rules'}] if loads else [],
            'demands': loads, 'controls': [], 'shared_services': [{'demand_id':d['demand_id'],'source_service_id':d['demand_id'],'ownership':'instantiate_once'} for d in loads], 'evidence': [{'accepted_absence': True}]}
        recipe = {'resolved': resolved, 'bound_inputs': {}, 'required_inputs': [], 'calendar_year_locked': True,
            'reference_year': 2007, 'reference_sources': {'hot_water_volume': original['schedule_authority']['canonical_schedule']['value']} if loads else {},
            'companion_rules': {}, 'source_context': context('source-context'), 'required_contract_version': '1.1.0',
            'required_service_links': [], 'required_service_sets': own, 'exact_source_authority': reference,
            'original_method_reference': next(m for m in records['method_references'] if m['value']['program_id']==p['id'])}
        if p['id']=='parent':
            recipe['source_context']=context(selected_configuration)
            recipe['source_composition']={'parent_program_id':'parent','composition_id':'mix',
                'definition':records['compositions'][0]['value'],'provenance':{'label':'contract fixture'}}
        data['program',p['id']]={'definition': copy.deepcopy(p), 'recipe': recipe, 'case':{'case_id':'labelled-case'}}
    data['reference','catalogue-index']={'programs':[{'id':p['value']['id'],'status':'compiled' if p['value']['loads'] and p['value']['id']!='parent' else 'accepted_inactive'} for p in records['programmes']]}
    physical_sources=[]; child_sources=[]
    for sid in dict.fromkeys(r['source_service_id'] for r in inventory['payload']['roles']):
        role=next(r for r in inventory['payload']['roles'] if r['source_service_id']==sid); definition=role['service_definition']['value']
        resolved={'owner_kind':'physical_service','source_service_id':sid,'source_service_definition':copy.deepcopy(definition),
            'recipe_id':'physical-'+sid,'source_family':'labelled_contract_fixture',
            'source':{'source_id':sid,'building_type':'Fixture','template':'2013','evidence_view':'source'},
            'slots':[{'slot':'hot_water_volume','unit':'fraction','kind':'load','source_schedule_id':'rules'}],
            'demands':[demand(definition['load'])],'controls':[],'shared_services':[],'evidence':[]}
        variant={'reference_source':role['schedule_authority']['canonical_schedule']['value'], 'companion_rules':{},
                 'source_context':context('source-context'),'adaptation':{}}
        rec={'definition':copy.deepcopy(definition),'provenance':{'source_path':'data/definition-releases/v0.1.1/services.json','source_locator':'/fixture','source_sha256':'a'*64},
             'recipe':{'required_contract_version':'1.1.0','ownership':'instantiate_once','allocation_mode':'whole',
                'reference_year':2007,'resolved':resolved,'configurations':{'source-context':variant},
                'exact_source_authority':reference,'required_service_links':[],'required_service_sets':[]}}
        data['reference','physical-service__'+sid]=copy.deepcopy(rec)
        selected=copy.deepcopy(rec); selected['recipe']['configurations'][selected_configuration]=dict(copy.deepcopy(variant),source_context=context(selected_configuration))
        physical_sources.append(source(selected,path='selected-physical-'+sid+'.json'))
    for p in records['programmes']:
        if p['value']['id']=='parent':continue
        selected=copy.deepcopy(data['program',p['value']['id']]); selected['recipe']['source_context']=context(selected_configuration)
        child_sources.append(source(selected,path='selected-child-'+p['value']['id']+'.json'))
    # Native consumed evidence is unchanged; executable packaging is qualified separately.
    consumed_context=consumed()
    selected_context=source({'selected_method_context_id':'selected','source_hoo_configuration_id':selected_configuration,
        'context_evidence_view':'reviewed' if parent and not original_context else 'source','qualification_scope':'full_selected_programme_and_water_registration',
        'qualification_id':'labelled-q','method_consumed_context':consumed_context})
    association={'selected_method_context':selected_context,'physical_service_records':physical_sources,'child_program_records':[], 'evidence':evidence()}
    if parent:
        parent_req=next(r for r in reqs if r['kind']=='original_source_components')
        for component,selected in zip(parent_req['components'],child_sources):
            req=next(r for r in reqs if r['requirement_id']==component['child_requirement_id'])
            roles=[r for r in inventory['payload']['roles'] if r['role_id'] in req['expected_role_ids']]
            member={'parent_inventory_id':'labelled','parent_inventory_sha256':inventory['inventory_sha256'],
                'canonical_member':req['programme'],'original_method_reference':component['original_method_reference'],
                'conserved_source_authority':[req['original_demand']]+[r['schedule_authority']['canonical_schedule'] for r in roles], 'evidence':evidence()}
            key={'parent_inventory_id':'labelled','parent_inventory_sha256':inventory['inventory_sha256'],
                'member_program_id':component['member_program_id'],'member_evidence_view':'source','selected_method_context_id':'selected'}
            q=source({'qualification_id':'labelled-q','qualification_scope':'full_selected_programme_and_water_registration','key':key,
                'selected_method_context':selected_context,**{k:member[k] for k in ('canonical_member','original_method_reference','conserved_source_authority')},'evidence':evidence()})
            with patch('atlas_schedules.physical_sets._qualified_exact_context',return_value=True): v=compile_child_variant(member,selected_context,q)
            data['reference','physical-child-variant__'+v['variant_id']]=v
            data['program','parent']['recipe'].setdefault('permitted_child_variants',[]).append({'variant_id':v['variant_id'],'key':key})
            association['child_program_records'].append({'variant_id':v['variant_id'],'key':key,'program_record':selected})
    data['reference','physical-execution-association__selected']=association
    data['reference','qualification']=source({'qualification_id':'labelled-q','qualification_scope':'full_selected_programme_and_water_registration',
        'inventory_id':'labelled','inventory_sha256':inventory['inventory_sha256'],'program_ids':[p['value']['id'] for p in records['programmes']],
        'selected_method_context':selected_context,'evidence':evidence()})
    realization={'building_realization_id':'building','mode':'exact_source_fixture_extents','inventory_id':'labelled',
        'inventory_sha256':inventory['inventory_sha256'],'source_hoo_configuration_id':selected_configuration,
        'selected_method_context_id':'selected','operating_group':'g'}
    programme={'key':'p','owner_kind':'program','program_id':'parent' if parent else 'leaf','building_realization_id':'building',
        'inputs':{'composition_basis_mode':'source_reference_area_normalized'} if parent else {}, 'basis_bindings':{},'operating_group':'g'}
    if parent:
        # Existing resolver requires recipe bound operands to declare parent mode.
        data['program','parent']['recipe']['bound_inputs']=copy.deepcopy(programme['inputs'])
        data['program','parent']['recipe']['required_inputs']=list(programme['inputs'])
    else:
        # Standalone programme executes its supplied selected context as well.
        data['program','leaf']['recipe']['source_context']=context(selected_configuration)
    instances=[programme]
    for r in inventory['payload']['roles']:
        inputs={'source_hoo_configuration_id':selected_configuration,'physical_fixture_evidence':{'role':r['source_space']}}
        if r['source_basis']=='floor_area':
            inputs.update(fixture_floor_area_m2=r['geometry_operands']['floor_area_m2'],fixture_space_multiplier=r['geometry_operands']['space_multiplier'],
                fixture_extent_evidence={'area':{'value':r['geometry_operands']['floor_area_m2'],'unit':'m2'},'multiplier':{'value':r['geometry_operands']['space_multiplier'],'unit':'1'}})
        extent=dict(r['consumed_extent'],evidence={'label':'explicit contract fixture'})
        instances.append({'key':'owner-'+r['role_id'],'owner_kind':'physical_service','physical_binding_kind':'exact_source_role',
            'building_realization_id':'building','source_fixture_role_id':r['role_id'],'source_service_id':r['source_service_id'],
            'physical_id':'physical-'+r['role_id'],'inputs':inputs,'operating_group':'g','basis_bindings':{'extents':{r['source_basis']:extent},'multiplicity':1}})
    direct_id=programme['program_id']
    data['reference','physical-execution-qualification__selected']=source({
        'qualification_id':'independent-labelled-execution-q','qualification_scope':'full_selected_programme_and_water_registration',
        'selected_method_context':selected_context,
        'execution_association':artifact(association,'reference/physical-execution-association__selected.json'),
        'standalone_program_records':[artifact(data['program',direct_id],'program/'+direct_id+'.json')], 'evidence':evidence()})
    return data, {'schema_version':'1.2.0','calendar':CALENDAR,'building_realizations':[realization],'instances':instances}


class PhysicalBindingTests(unittest.TestCase):
    def resources(self,data):
        directory=tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        manifest=write_resources(Path(directory.name),data,{})
        return ResourceSet(Path(directory.name),manifest['resource_set_id'])

    def prepare(self,mode='hotel',parent=False,zero=False,mutate=None,bad_weights=False,bad_area=False,original_context=False):
        import atlas_schedules.physical_sets as sets
        data,params=records_fixture(mode,parent,zero,bad_weights,bad_area,original_context)
        if mutate:mutate(data,params)
        resources=self.resources(data)
        with patch.object(sets,'_qualified_exact_context',return_value=True), patch.object(sets,'_qualified_execution_association',return_value=True):
            pairs=sets._prepare_exact_instances(params,resources)
            plan=sets.prepare_exact_bindings(params,pairs,resources)
        return data,params,resources,plan

    def emit(self,plan,values=None):
        result={'schema_version':'1.2.0','constituents':[],'bindings':[],'schedules':{},'metadata':{'calendar':CALENDAR}}
        for instance,resolved in plan['resolved_instances']:
            c=copy.deepcopy(resolved); c.update(instance_key=instance['key'],schedule_ids={},binding_indices=[],generation={})
            for d in c['demands']:
                sid=schedule_id(instance['key'],d['slot']); actual=values if values is not None else [.1]*8760
                result['schedules'][sid]={'id':sid,'values':actual}; c['schedule_ids'][d['slot']]=sid
                c['binding_indices'].append(len(result['bindings']))
                result['bindings'].append(dict(bind_budget(resolved['inputs']['reference_budgets'][d['demand_id']],actual),
                    kind='load',instance_key=instance['key'],demand_id=d['demand_id'],slot=d['slot'],schedule_id=sid,
                    **identity_fields(resolved,'1.2.0')))
            result['constituents'].append(c)
        # A source parent with only projected water has no local owned channels.
        for a in plan['source_allocations']:
            c=copy.deepcopy(a['parent_resolved']); c.update(instance_key=a['parent_instance_key'],schedule_ids={},binding_indices=[],generation={})
            result['constituents'].append(c)
        from atlas_schedules.physical_sets import bind_exact_projections
        bind_exact_projections(result,plan)
        return result

    def test_source_basis_and_parent_components(self):
        for mode,want,count in [('office',194.72673032898626,3),('hotel',.3515783333108323,4)]:
            with self.subTest(mode=mode):
                _,_,_,plan=self.prepare(mode); result=self.emit(plan)
                owners=[c for c in result['constituents'] if c['owner_kind']=='physical_service']
                self.assertEqual(len(result['bindings']),count)
                self.assertAlmostEqual(result['bindings'][0]['reference_target']['total'],want)
                descriptor=owners[0]['shared_services'][0]
                self.assertEqual(descriptor['source_basis_target'],result['bindings'][0]['reference_target'])
                self.assertAlmostEqual(descriptor['extent']['value'],1 if mode=='office' else 156.08808)
                self.assertAlmostEqual(descriptor['whole_input_target']['total'],want if mode=='office' else 54.87718701608786)
                p=result['constituents'][0]; projection=p['service_set_projections'][0]
                self.assertEqual(p['demands'],[]); self.assertEqual(p['shared_services'],[]); self.assertEqual(p['slots'],[]); self.assertEqual(p['schedule_ids'],{}); self.assertEqual(p['binding_indices'],[])
                self.assertEqual(len(projection['members']),count)
                self.assertEqual(projection['interpretation'],'conserved_original_input_components' if mode=='office' else 'canonical_density_partition')
                self.assertAlmostEqual(projection['whole_input_target']['total'],584.1801909869588 if mode=='office' else 219.4958887352323)
        _,_,_,plan=self.prepare(parent=True); result=self.emit(plan)
        parent=result['constituents'][-1]; p=parent['service_set_projections'][0]
        self.assertAlmostEqual(p['denominator']['value'],644.3157440000001)
        self.assertAlmostEqual(p['whole_input_target']['total'],233.5590220676656)
        self.assertAlmostEqual(p['projected_target']['total'],233.5590220676656/644.3157440000001)
        self.assertEqual(len(p['components']),2); self.assertEqual(len(p['members']),6)
        for comp in p['components']:
            child=next(c for c in result['constituents'] if c['instance_key']==comp['member_instance_key'])
            self.assertEqual(child['generation']['method_variant'],comp['selected_child_variant'])
            self.assertEqual(child['source']['evidence_view'],'source')
            self.assertEqual(comp['selected_child_variant']['context_relation'],'qualified_crossview_context')
            self.assertEqual(child['generation']['operating_group'],'g')

    def test_coverage_and_identity_fail_before_sampling(self):
        def wrong_source(data,params,field):
            data['reference','physical-service__water']['recipe']['resolved']['source'][field]='foreign'
            data['reference','physical-execution-association__selected']['physical_service_records'][0]['value']['recipe']['resolved']['source'][field]='foreign'
        mutations={
            'family':lambda d,p:wrong_source(d,p,'building_type'),
            'template':lambda d,p:wrong_source(d,p,'template'),
            'same-scoped-physical':lambda d,p:p['instances'][2].update(physical_id=p['instances'][1]['physical_id']),
            'missing':lambda d,p:p['instances'].pop(),
            'duplicate':lambda d,p:p['instances'].append(dict(copy.deepcopy(p['instances'][1]),key='duplicate',physical_id='another')),
            'wrong-role':lambda d,p:p['instances'][1].update(source_fixture_role_id='foreign'),
            'wrong-sid':lambda d,p:p['instances'][1].update(source_service_id='foreign'),
            'geometry':lambda d,p:p['instances'][1]['inputs'].update(fixture_floor_area_m2=40),
            'extent':lambda d,p:p['instances'][1]['basis_bindings']['extents']['floor_area'].update(value=999),
            'group':lambda d,p:p['instances'][1].update(operating_group='foreign'),
            'context':lambda d,p:p['instances'][1]['inputs'].update(source_hoo_configuration_id='foreign'),
            'overlap':lambda d,p:p['instances'].append(dict(copy.deepcopy(p['instances'][0]),key='another-programme'))}
        for label,mutation in mutations.items():
            with self.subTest(label=label), patch('atlas_schedules.generator.sample_operating_parameters',side_effect=AssertionError('RNG before closure')):
                with self.assertRaises(GeneratorError) as caught:self.prepare(mutate=mutation)
                self.assertIn(caught.exception.code,{'source_integrity'} if label in {'family','template'} else {'requires_binding','shared_service_conflict','operating_group_conflict'})
                self.assertTrue(caught.exception.path)
        with self.assertRaises(GeneratorError) as caught:
            self.prepare(parent=True,mutate=lambda d,p:p['instances'][0]['inputs'].update(composition_basis_mode='caller_parent_floor_area'))
        self.assertEqual(caught.exception.code,'incompatible_source_composition')

    def test_two_realizations_reuse_local_physical_ids_without_merging(self):
        def duplicate(data,params):
            second=copy.deepcopy(params['building_realizations'][0]); second['building_realization_id']='building-two'; second['operating_group']='g-two'
            params['building_realizations'].append(second)
            for instance in copy.deepcopy(params['instances']):
                instance.update(key=instance['key']+'-two',building_realization_id='building-two',operating_group='g-two')
                params['instances'].append(instance)
        _,_,_,plan=self.prepare(mutate=duplicate); result=self.emit(plan)
        self.assertEqual(len(result['bindings']),8)
        self.assertEqual(len({(b['building_realization_id'],b['physical_id']) for b in result['bindings']}),8)

    def test_zero_target_keeps_positive_q_and_zero_roles(self):
        _,_,_,plan=self.prepare(zero=True); result=self.emit(plan,[0.0]*8760)
        self.assertEqual(len(result['bindings']),4)
        self.assertEqual(len(result['constituents'][0]['service_set_projections'][0]['members']),4)
        self.assertEqual(result['bindings'][0]['reference_target']['total'],0)
        self.assertGreater(result['bindings'][0]['reference_target']['original_magnitude']['value'],0)
        self.assertEqual(result['bindings'][0]['effective_magnitude']['value'],0)
        _,_,_,positive=self.prepare()
        with self.assertRaises(GeneratorError) as caught:self.emit(positive,[0.0]*8760)
        self.assertEqual(caught.exception.code,'zero_generated_integral')

    def test_association_is_explicit_strict_and_preserves_whole_original(self):
        def mutate(label):
            def change(data,params):
                association=data['reference','physical-execution-association__selected']
                if label=='missing':data.pop(('reference','physical-execution-association__selected'))
                elif label=='ambiguous':association['physical_service_records']*=2
                elif label=='unknown':association['unknown']=True
                elif label=='unassociated':association['selected_method_context']['value']['method_consumed_context']['value']['source_resources']=[]
                elif label=='context':association['selected_method_context']['value']['source_hoo_configuration_id']='foreign'
                elif label=='definition':association['physical_service_records'][0]['value']['definition']['unreported']='forged'
                elif label=='configuration':association['physical_service_records'][0]['value']['recipe']['configurations']['selected-context']['source_context']['configuration_id']='foreign'
                elif label=='child-original':association['child_program_records'][0]['program_record']['value']['recipe']['resolved']['source']['evidence_view']='reviewed'
                elif label=='child-missing':association['child_program_records']=[]
            return change
        for label in ('missing','ambiguous','unknown','unassociated','context','definition','configuration','child-original','child-missing'):
            with self.subTest(label=label),self.assertRaises(GeneratorError):self.prepare(parent=True,mutate=mutate(label))

    def test_independent_inventory_order_is_not_caller_owner_order(self):
        _,_,_,plan=self.prepare(mutate=lambda d,p:p['instances'].__setitem__(slice(1,None),list(reversed(p['instances'][1:]))))
        self.assertEqual([e['role']['role_id'] for e in plan['owners']],['role-0','role-1','role-2','role-3'])
        result=self.emit(plan)
        self.assertEqual(result['constituents'][0]['service_set_projections'][0]['role_ids'],['role-0','role-1','role-2','role-3'])

    def test_parent_extent_and_weight_closure_precede_sampling(self):
        for kwargs in ({'bad_weights':True},{'bad_area':True}):
            with self.subTest(kwargs=kwargs),self.assertRaises(GeneratorError):
                self.prepare(parent=True,**kwargs)

    def test_execution_authority_wire_is_strict_and_required(self):
        from atlas_schedules.contract import _load_schema,_check_schema
        _,_,_,plan=self.prepare(parent=True)
        receipt=plan['building_realizations'][0]
        schema=_load_schema('bundle','1.2.0')
        branch=schema['properties']['metadata']['properties']['building_realizations']['items']['oneOf'][0]
        _check_schema(receipt,branch,schema,'/receipt')
        for label in ('missing','unknown','malformed_original','unknown_association','missing-execution-q','malformed-execution-q'):
            wrong=copy.deepcopy(receipt);proof=wrong['native_context']['execution_authority']
            if label=='missing':wrong['native_context'].pop('execution_authority')
            if label=='unknown':proof['extra']=True
            if label=='malformed_original':proof['canonical_program_records'][0]['sha256']='wrong'
            if label=='unknown_association':proof['execution_association']['extra']=True
            if label=='missing-execution-q':wrong['native_context'].pop('execution_qualification')
            if label=='malformed-execution-q':wrong['native_context']['execution_qualification']['extra']=True
            with self.subTest(label=label),self.assertRaises(GeneratorError):_check_schema(wrong,branch,schema,'/receipt')
        proof=receipt['native_context']['execution_authority']
        self.assertEqual(len(proof['canonical_physical_records']),2)
        self.assertEqual(len(proof['canonical_program_records']),3)

    def test_original_context_child_executes_without_recursive_native_resources(self):
        _,_,_,plan=self.prepare(parent=True,original_context=True)
        result=self.emit(plan)
        for c in result['constituents']:
            variant=c.get('generation',{}).get('method_variant')
            if variant is None:continue
            self.assertEqual(variant['context_relation'],'original_context')
            self.assertIsNone(variant['adaptation'])
            self.assertEqual(variant['original_method_reference']['value']['method_consumed_context'],
                variant['selected_method_context']['value']['method_consumed_context'])
            self.assertEqual(c['inputs']['source_context']['configuration_id'],'source-context')
        proof=result['metadata']['building_realizations'][0]['native_context']['execution_qualification']
        native=proof['value']['selected_method_context']['value']['method_consumed_context']
        self.assertEqual(native,consumed())
        self.assertNotEqual(proof['value']['qualification_id'],proof['value']['selected_method_context']['value']['qualification_id'])

    def test_native_and_executable_qualifiers_are_independently_closed(self):
        import atlas_schedules.physical_sets as sets
        data,params=records_fixture();resources=self.resources(data)
        for patch_name in (None,'_qualified_exact_context','_qualified_execution_association'):
            with self.subTest(patch_name=patch_name):
                if patch_name is None:
                    with self.assertRaises(GeneratorError):sets._prepare_exact_instances(params,resources)
                else:
                    with patch.object(sets,patch_name,return_value=True),self.assertRaises(GeneratorError):
                        sets._prepare_exact_instances(params,resources)

    def test_executable_qualification_requires_whole_proof_and_direct_closure(self):
        def change(label):
            def mutate(data,params):
                q=data['reference','physical-execution-qualification__selected']['value']
                if label=='missing':data.pop(('reference','physical-execution-qualification__selected'))
                if label=='scope':q['qualification_scope']='pilot'
                if label=='unknown':q['unknown']=True
                if label=='association-value':q['execution_association']['value']['evidence'][0]['interpretation_note']='foreign'
                if label=='association-sha':q['execution_association']['sha256']='b'*64
                if label=='association-locator':q['execution_association']['locator']='/foreign'
                if label=='context':q['selected_method_context']['value']['qualification_id']='foreign'
                if label=='direct-missing':q['standalone_program_records']=[]
                if label=='direct-duplicate':q['standalone_program_records']*=2
                if label=='direct-sha':q['standalone_program_records'][0]['sha256']='b'*64
                if label=='direct-value':q['standalone_program_records'][0]['value']['recipe']['source_context']['case_id']='foreign'
            return mutate
        for label in ('missing','scope','unknown','association-value','association-sha','association-locator','context','direct-missing','direct-duplicate','direct-sha','direct-value'):
            with self.subTest(label=label),self.assertRaises(GeneratorError):self.prepare(mutate=change(label))

    def test_unqualified_standalone_record_rejects_before_shared_executor(self):
        import atlas_schedules.physical_sets as sets
        data,params=records_fixture()
        data['program','leaf']['recipe']['source_context']['case_id']='unqualified-native-case'
        resources=self.resources(data)
        with patch.object(sets,'_qualified_exact_context',return_value=True), patch.object(sets,'_qualified_execution_association',return_value=True), patch(
                'atlas_schedules.programs._resolve_program_record',side_effect=AssertionError('unqualified programme executed')):
            with self.assertRaises(GeneratorError):sets._prepare_exact_instances(params,resources)

    def test_supplied_resolved_pair_rechecks_actual_qualified_context(self):
        import atlas_schedules.physical_sets as sets
        data,params=records_fixture();resources=self.resources(data)
        with patch.object(sets,'_qualified_exact_context',return_value=True), patch.object(sets,'_qualified_execution_association',return_value=True):
            pairs=sets._prepare_exact_instances(params,resources)
            pairs[0][1]['inputs']['source_context']['case_id']='unqualified-native-case'
            with self.assertRaises(GeneratorError):sets.prepare_exact_bindings(params,pairs,resources)

    def test_source_only_execution_needs_no_direct_programme_record(self):
        import atlas_schedules.physical_sets as sets
        data,params=records_fixture();params['instances']=params['instances'][1:2]
        data['reference','physical-execution-qualification__selected']['value']['standalone_program_records']=[]
        resources=self.resources(data)
        with patch.object(sets,'_qualified_exact_context',return_value=True), patch.object(sets,'_qualified_execution_association',return_value=True):
            pairs=sets._prepare_exact_instances(params,resources)
            plan=sets.prepare_exact_bindings(params,pairs,resources)
        self.assertEqual(len(plan['owners']),1)
        self.assertEqual(plan['projections'],[])
        self.assertEqual(plan['building_realizations'][0]['native_context']['execution_authority']['canonical_program_records'],[])

    def test_standalone_programme_whole_executable_is_qualified_before_execution(self):
        def change(data,params):
            data['program','leaf']['recipe']['source_context']['case_id']='unqualified-native-case'
        with self.assertRaises(GeneratorError):self.prepare(mutate=change)

    def test_retained_physical_binding_cannot_be_replaced_by_equal_total(self):
        _,_,_,plan=self.prepare(); result=self.emit(plan)
        wrong=copy.deepcopy(result); wrong['bindings'][0]['physical_id']='foreign'
        from atlas_schedules.physical_sets import bind_exact_projections
        with self.assertRaises(GeneratorError):bind_exact_projections(wrong,plan)


if __name__=='__main__':unittest.main()
