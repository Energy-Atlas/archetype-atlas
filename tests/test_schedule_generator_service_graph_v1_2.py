"""Labelled contract graphs; no native capture or production qualification."""
import copy
import hashlib
import unittest
from unittest.mock import patch

from atlas_schedules.canonical import schedule_id, canonical
from atlas_schedules.contract import validate_bundle
from atlas_schedules.errors import GeneratorError
from atlas_schedules.service_graph import (required_graph_closure,
    select_physical_services, validate_physical_graph)
from tests import test_schedule_generator_physical_binding_v1_2 as binding_fixtures
CALENDAR=binding_fixtures.CALENDAR


def exact_bundle(parent=False, zero=False, original_context=False, mode='hotel'):
    helper=binding_fixtures.PhysicalBindingTests()
    try:
        def normalize(value,field=None):
            if isinstance(value,dict):
                for k,v in value.items():value[k]=normalize(v,k)
            elif isinstance(value,list):value[:]=[normalize(v) for v in value]
            elif field!='fuel' and value in ('water','water-two'):return 'service-'+('1' if value=='water' else '2')*24
            return value
        def source(value,locator='/0',path='contract-fixture.json'):
            value=normalize(copy.deepcopy(value))
            digest=hashlib.sha256(canonical(value)).hexdigest()
            return {'path':'contract-fixture/'+digest+'.json','sha256':digest,'locator':locator,'value':copy.deepcopy(value)}
        def refresh(value):
            if isinstance(value,dict):
                for child in value.values():refresh(child)
                if set(value)=={'path','sha256','locator','value'}:
                    digest=hashlib.sha256(canonical(value['value'])).hexdigest()
                    value.update(path='contract-fixture/'+digest+'.json',sha256=digest)
            elif isinstance(value,list):
                for child in value:refresh(child)
            return value
        from scripts import schedule_generator_physical_sets as compiler
        compile_inventory=compiler.compile_exact_inventory
        original_fixture=binding_fixtures.fixture
        with patch.object(binding_fixtures,'source',side_effect=source), patch(
                'tests.test_schedule_generator_physical_authority_v1_2.source',side_effect=source), patch.object(
                binding_fixtures,'fixture',side_effect=lambda:normalize(original_fixture())), patch.object(
                compiler,'compile_exact_inventory',side_effect=lambda records:compile_inventory(refresh(normalize(records)))):
            _,params,resources,plan=helper.prepare(mode=mode,parent=parent,zero=zero,original_context=original_context)
        result=helper.emit(plan,[0.0 if zero else .1]*8760)
        result['algorithm_version']='contract-fixture'
        result['metadata'].update(resource_set_id='contract-fixture',scope_id='contract-fixture',
            scope_version='1.2.0',population_realization_equivalent=False,comparison_policy={})
        result['generation']={'master_seed':42,'physical_unit_seed_sequence':[],
            'residential_unit_order':[],'unit_seeds':{}}
        for r in result['metadata']['building_realizations']:r['inventory_resource']['resource_set_id']='contract-fixture'
        instances={i['key']:i for i in params['instances']}
        for allocation in plan['source_allocations']:
            instances.update({i['key']:i for i in allocation['children']})
        keep={'instance_key','program_id','owner_kind','physical_binding_kind',
              'building_realization_id','source_fixture_role_id','source_service_id','physical_id',
              'recipe_id','source','slots','demands','controls','shared_services','evidence','inputs',
              'basis_bindings','schedule_ids','binding_indices','generation','required_service_links',
              'required_service_sets','service_set_projections'}
        for c in result['constituents']:
            from atlas_schedules.owners import identity_fields
            c.update(identity_fields(instances[c['instance_key']],'1.2.0'))
            family=c.pop('source_family'); c['source']['source_family']=family
            c['source'].setdefault('vintage',None);c['source'].setdefault('weather',None)
            context=c['inputs']['source_context']
            c['generation'].update(source_inputs=copy.deepcopy(context),operating_group='g')
            c['inputs']={k:v for k,v in c['inputs'].items() if k not in {
                'reference_channels','reference_budgets','source_context','companion_rules','source_composition'}}
            c['basis_bindings']=copy.deepcopy(instances[c['instance_key']]['basis_bindings'])
            if not c['slots']:c['evidence'].append({'accepted_absence':True})
            for key in set(c)-keep:c.pop(key)
            for d in c['demands']:d['heat_fractions']=None
        for b in result['bindings']:
            b.update(fuel=b['reference_target']['fuel'],host=b['reference_target']['host'],
                     budget_method=b['reference_target']['method'])
        for s in result['schedules'].values():
            s.update(unit='fraction',year=2007,clock='local_standard_time',timestep_minutes=60)
        return result
    finally:helper.doCleanups()


def mixture(members=None, services=None):
    return {'program_id':'result','composition_id':None,'members':members or [],
            **({'service_members':services} if services else {}),'result_basis':'floor_area',
            'denominator':{'value':1000,'unit':'m2','evidence':{'caller':'contract fixture'}}}


def rename_graph(bundle,suffix):
    result=copy.deepcopy(bundle)
    keys={c['instance_key']:c['instance_key']+suffix for c in result['constituents']}
    schedules={s:schedule_id(keys[b['instance_key']],b['slot']) for b in result['bindings'] for s in [b['schedule_id']]}
    def walk(value):
        if isinstance(value,dict):
            if set(value)=={'path','sha256','locator','value'}:return value
            return {(schedules.get(k,k) if k in schedules else k):
                    v+suffix if k=='building_realization_id' and v is not None else walk(v) for k,v in value.items()}
        if isinstance(value,list):return [walk(v) for v in value]
        if isinstance(value,str):return schedules.get(value,keys.get(value,value))
        return value
    return walk(result)


def caller_bundle(alternatives=True):
    from tests import test_schedule_generator_caller_water_v1_2 as fixtures
    from atlas_schedules import caller_unit_water as caller
    from atlas_schedules.budgets import bind_budget
    from atlas_schedules.calendar import evaluate_rules
    from atlas_schedules.owners import identity_fields
    requirements=[fixtures.compiled(index=0),fixtures.compiled(index=1)]
    real=fixtures.realization([fixtures.unit('u','draw',requirements if alternatives else requirements[:1])])
    temporary,resources,_=fixtures.resource_fixture(requirements)
    try:
        pairs=fixtures.pairs(real,{r['programme']['value']['id']:r for r in requirements})
        with patch.object(caller,'_qualified_caller_water_method',return_value=True):
            plan=caller.prepare_caller_water({'calendar':CALENDAR,'building_realizations':[real]},pairs,resources)
    finally:temporary.cleanup()
    result={'schema_version':'1.2.0','algorithm_version':'contract-fixture',
        'metadata':{'resource_set_id':'contract-fixture','calendar':CALENDAR,'building_realizations':[]},
        'generation':{'master_seed':42,'physical_unit_seed_sequence':[],'residential_unit_order':[],'unit_seeds':{}},
        'bindings':[],'constituents':[],'schedules':{}}
    for instance,resolved in plan['resolved_instances']:
        physical=instance['owner_kind']=='physical_service'
        c={k:copy.deepcopy(resolved.get(k,[])) for k in ('slots','demands','controls','shared_services','evidence')}
        c.update(instance_key=instance['key'],**identity_fields(instance,'1.2.0'),
            recipe_id=resolved.get('recipe_id','contract-programme'),source=copy.deepcopy(resolved['source']),
            inputs={k:v for k,v in resolved['inputs'].items() if k not in {'reference_channels','reference_budgets','companion_rules','source_context'}},
            basis_bindings=instance['basis_bindings'],schedule_ids={},binding_indices=[],
            generation={'source_inputs':copy.deepcopy(resolved['inputs'].get('source_context',{'method':'fixed_programme'})),
                'operating_group':None})
        req=(resolved['shared_services'][0]['caller_unit_adaptation']['source_requirement'] if physical else resolved['required_service_sets'][0])
        c['source'].update(source_family=req['programme']['value']['source_family'],vintage=None,weather=None)
        if not physical:c.update(required_service_links=[],required_service_sets=[req],service_set_projections=[])
        if not c['slots']:c['evidence'].append({'accepted_absence':True})
        for d in c['demands']:
            d['heat_fractions']=None;slot=d['slot'];sid=schedule_id(instance['key'],slot)
            values=evaluate_rules(req['source_ruleset']['value'],2007,[])['values']
            c['schedule_ids'][slot]=sid;c['binding_indices'].append(len(result['bindings']))
            result['schedules'][sid]={'id':sid,'values':values,'unit':'fraction','year':2007,
                'clock':'local_standard_time','timestep_minutes':60}
            result['bindings'].append(dict(bind_budget(resolved['inputs']['reference_budgets'][d['demand_id']],values),
                kind='load',instance_key=instance['key'],**identity_fields(instance,'1.2.0'),
                demand_id=d['demand_id'],slot=slot,schedule_id=sid,fuel=d['fuel'],host=d['host'],budget_method='reference_schedule'))
        result['constituents'].append(c)
    caller.bind_caller_water(result,plan)
    return result


def legacy_bundle(sid='service-'+ '3'*24):
    from tests.test_schedule_generator_contract import bundle
    from atlas_schedules.budgets import reference_budget,bind_budget
    result=bundle();result['schema_version']='1.1.0';result['algorithm_version']='contract-fixture'
    result['metadata']['resource_set_id']='contract-fixture';owner=result['constituents'][0]
    key='legacy-water';slot='hot_water_volume';schedule=schedule_id(key,slot);values=[.1]*8760
    demand={'demand_id':sid,'slot':slot,'quantity':slot,'value':1e-8,'unit':'m3/s/m2',
        'basis':'floor_area','fuel':'water','host':'building_service','evidence':{'contract':'labelled'}}
    extent={'value':25,'unit':'m2','evidence':{'caller':'labelled actual whole fixture'}}
    identity={'owner_kind':'physical_service','source_service_id':sid,'physical_id':'legacy-draw'}
    owner.pop('program_id');owner.update(identity,instance_key=key,demands=[demand],controls=[],
        slots=[{'slot':slot,'source_schedule_id':'labelled-rule','unit':'fraction','kind':'load'}],
        basis_bindings={'multiplicity':1,'extents':{'floor_area':extent}},
        schedule_ids={slot:schedule},binding_indices=[0],
        shared_services=[{'demand_id':sid,**{k:identity[k] for k in ('physical_id','source_service_id')},
            'mode':'whole','ownership':'instantiate_once','extent':extent}])
    result['bindings']=[dict(bind_budget(reference_budget(demand,values),values),kind='load',instance_key=key,
        **identity,demand_id=sid,slot=slot,schedule_id=schedule,fuel='water',host='building_service',budget_method='reference_schedule')]
    result['schedules']={schedule:{'id':schedule,'values':values,'unit':'fraction','year':2007,'clock':'local_standard_time','timestep_minutes':60}}
    result['generation']={'master_seed':42,'residential_unit_order':[],'unit_seeds':{}}
    validate_bundle(result)
    return result


class PhysicalGraphTests(unittest.TestCase):
    @staticmethod
    def rewrite_retained_programmes(bundle,change,physical=False):
        def walk(value):
            if isinstance(value,dict):
                if set(value)=={'path','sha256','locator','value'}:
                    record=value['value']
                    if isinstance(record,dict) and isinstance(record.get('definition'),dict) and ('loads' in record['definition'] or physical) and 'recipe' in record:
                        change(record)
                    for child in record.values() if isinstance(record,dict) else []:walk(child)
                    if isinstance(record,dict) and ('recipe' in record or set(record)=={'selected_method_context','physical_service_records','child_program_records','evidence'}):
                        value['sha256']=hashlib.sha256(canonical(record)).hexdigest()
                    return
                for child in value.values():walk(child)
            elif isinstance(value,list):
                for child in value:walk(child)
        walk(bundle)

    def test_original_water_obligations_cannot_be_erased_from_recipes(self):
        for mode,parent in (('hotel',False),('office',False),('hotel',True)):
            with self.subTest(mode=mode,parent=parent):
                bundle=exact_bundle(mode=mode,parent=parent)
                originals=copy.deepcopy([r['value']['definition'] for r in bundle['metadata']['building_realizations'][0]['native_context']['execution_authority']['canonical_program_records']])
                self.rewrite_retained_programmes(bundle,lambda r:r['recipe'].update(required_service_sets=[]))
                for owner in bundle['constituents']:
                    if owner['owner_kind']=='program':owner.update(required_service_sets=[],service_set_projections=[])
                self.assertEqual(originals,[r['value']['definition'] for r in bundle['metadata']['building_realizations'][0]['native_context']['execution_authority']['canonical_program_records']])
                with self.assertRaises(GeneratorError):validate_bundle(bundle)

    def test_retained_caller_operands_groups_and_exact_calendars_are_actual(self):
        caller=caller_bundle(alternatives=False)
        changes={
            'method':lambda b:b['constituents'][0]['inputs'].update(water_method='invented'),
            'resident':lambda b:b['constituents'][0]['inputs'].update(residents=5),
            'owner_calendar':lambda b:b['constituents'][0]['inputs'].update(year=2009),
            'missing_programme_group':lambda b:b['constituents'][1]['generation'].pop('operating_group'),
            'programme_group':lambda b:b['constituents'][1]['generation'].update(operating_group='commercial-g')}
        for label,change in changes.items():
            invalid=copy.deepcopy(caller);change(invalid)
            with self.subTest(label=label),self.assertRaises(GeneratorError):validate_bundle(invalid)
        exact=exact_bundle()
        for owner_index in (0,1):
            for field,value in (('year',2009),('holidays',['01-01'])):
                invalid=copy.deepcopy(exact);invalid['constituents'][owner_index]['inputs'][field]=value
                with self.subTest(owner=owner_index,field=field),self.assertRaises(GeneratorError):validate_bundle(invalid)

    def test_caller_source_family_cannot_reclassify_original_prototype(self):
        bundle=caller_bundle(alternatives=False);owner=bundle['constituents'][1]
        original=copy.deepcopy(owner['required_service_sets'][0]['programme'])
        owner['source']['source_family']='existing_stock_benchmark'
        self.assertEqual(owner['required_service_sets'][0]['programme'],original)
        with patch('atlas_schedules.service_graph._actors',side_effect=AssertionError('classification before original authority')):
            with self.assertRaises(GeneratorError):validate_bundle(bundle)

    def test_unused_pool_parent_and_child_must_match_selected_context(self):
        for branch in ('parent','child','physical'):
            bundle=exact_bundle(parent=True)
            bundle['constituents']=[c for c in bundle['constituents'] if c['owner_kind']=='physical_service']
            bundle['metadata']['building_realizations'][0]['native_context']['execution_authority']['canonical_program_records']=[]
            if branch=='physical':
                chosen=bundle['bindings'][0]['source_service_id']
                bundle['constituents']=[c for c in bundle['constituents'] if c['source_service_id']==chosen]
                bundle['bindings']=[b for b in bundle['bindings'] if b['source_service_id']==chosen]
                bundle['schedules']={k:v for k,v in bundle['schedules'].items() if k in {b['schedule_id'] for b in bundle['bindings']}}
                authority=bundle['metadata']['building_realizations'][0]['native_context']['execution_authority']
                authority['canonical_physical_records']=[r for r in authority['canonical_physical_records'] if r['value']['definition']['id']==chosen]
            validate_bundle(bundle)
            def foreign(record):
                if branch=='physical':
                    if 'load' in record['definition'] and record['definition']['id']!=chosen:
                        record['recipe']['configurations']['selected-context']['source_context']['source_hoo_configuration_id']='foreign-context'
                elif 'loads' in record['definition'] and (record['definition']['id']=='parent')==(branch=='parent'):
                    record['recipe']['source_context']['source_hoo_configuration_id']='foreign-context'
            self.rewrite_retained_programmes(bundle,foreign,physical=branch=='physical')
            with self.subTest(branch=branch),self.assertRaises(GeneratorError):validate_bundle(bundle)

    def test_legacy_identical_alias_proof_survives_v12_and_conflict_rejects(self):
        from atlas_schedules.mixtures import compose_constituents
        first=legacy_bundle();alias=rename_graph(first,'-alias')
        request=mixture(services=[{'instance_key':'legacy-water'},{'instance_key':'legacy-water-alias'}])
        baseline=compose_constituents([first,alias],request,CALENDAR)
        self.assertEqual(len(baseline['constituents'][-1]['generation']['service_selection']['effective_service_members']),1)
        mixed=compose_constituents([first,alias,exact_bundle()],request,CALENDAR)
        receipt=mixed['constituents'][-1]['generation']['service_set_selection']
        self.assertEqual(len(receipt['effective_physical_members']),1)
        self.assertEqual([r['deduplicated'] for r in receipt['reasons']],[False,True])
        validate_bundle(mixed)
        conflict=copy.deepcopy(alias);conflict['constituents'][0]['evidence'].append({'different':'whole physical proof'})
        validate_bundle(conflict)
        with self.assertRaises(GeneratorError) as caught:compose_constituents([first,conflict,exact_bundle()],request,CALENDAR)
        self.assertEqual(caught.exception.code,'shared_service_conflict')

    def test_absolute_source_reference_conserves_input_components_without_local_demand(self):
        bundle=exact_bundle(mode='office');validate_bundle(bundle)
        programme=bundle['constituents'][0];self.assertEqual(programme['demands'],[])
        projection=programme['service_set_projections'][0]
        self.assertEqual(projection['projection_kind'],'source_reference_inputs')
        self.assertAlmostEqual(projection['whole_input_target']['total'],584.1801909869588)
        selected,receipt=select_physical_services(bundle,mixture(),[(programme,.2)])
        self.assertEqual(len(selected),3)
        self.assertTrue(all(c['shared_services'][0]['extent']['value']==1 for c,w in selected))
    def test_seed_order_and_valid_in_range_seed_are_scientifically_exact(self):
        from tests.test_schedule_generator_contract import bundle
        from atlas_schedules.service_graph import _upgrade_bundle
        from atlas_schedules.seeds import assign_physical_unit_sequence
        from atlas_schedules.comparison import compare_bundles
        from atlas_schedules.source_compositions import remap_binding_references
        base=bundle();key=base['constituents'][0]['instance_key']
        base['constituents'][0]['source']['source_family']='existing_stock_source_fixture'
        base['constituents'][0]['generation']['source_inputs']={'method':'resstock_time_allocation_with_selected_source_companions'}
        base['generation'].update(master_seed=42,residential_unit_order=[key],unit_seeds={key:42})
        result=_upgrade_bundle(base)
        for i in (1,2):
            other=rename_graph(_upgrade_bundle(base),'-'+str(i));remap_binding_references(other,{0:i})
            result['constituents']+=other['constituents'];result['bindings']+=other['bindings'];result['schedules'].update(other['schedules'])
        actors=[{'actor_kind':'stock','instance_key':c['instance_key'],'building_realization_id':None,
            'unit_id':None,'stochastic_action':'generate'} for c in result['constituents']]
        seq=assign_physical_unit_sequence(42,actors);result['generation'].update(physical_unit_seed_sequence=seq,
            residential_unit_order=[a['instance_key'] for a in seq],unit_seeds={a['instance_key']:a['unit_seed'] for a in seq})
        validate_bundle(result);self.assertEqual([a['unit_seed'] for a in seq],[42,84,252])
        policy={'tolerances':{k:{'abs_tol':1e-9,'rel_tol':1e-9} for k in (
            'annual_volume_m3','annual_energy_integral','fraction','source_arithmetic','temperature_C','activity_W_person')}}
        for label in ('seed','swap'):
            changed=copy.deepcopy(result)
            if label=='seed':changed['generation']['physical_unit_seed_sequence'][1]['unit_seed']=85
            else:
                sequence=assign_physical_unit_sequence(42,[actors[1],actors[0],actors[2]])
                changed['generation'].update(physical_unit_seed_sequence=sequence,
                    residential_unit_order=[a['instance_key'] for a in sequence],unit_seeds={a['instance_key']:a['unit_seed'] for a in sequence})
            self.assertTrue(compare_bundles(changed,result,policy))
            with self.subTest(label=label),self.assertRaises(GeneratorError):validate_bundle(changed)

    def test_incoming_consistency_does_not_open_production_qualification(self):
        from atlas_schedules import physical_sets as exact
        parent=exact_bundle(parent=True);variant=parent['constituents'][0]['generation']['method_variant']
        q=variant['qualification']['value'];member={k:copy.deepcopy(q[k]) for k in (
            'canonical_member','original_method_reference','conserved_source_authority','evidence')}
        member.update(parent_inventory_id=variant['key']['parent_inventory_id'],
                      parent_inventory_sha256=variant['key']['parent_inventory_sha256'])
        with self.assertRaises(GeneratorError) as raised:
            exact._variant_record(member,variant['selected_method_context'],variant['qualification'])
        self.assertEqual(raised.exception.code,'requires_binding')
        validate_bundle(parent)
        changed=copy.deepcopy(parent)
        changed['constituents'][0]['generation']['method_variant']['adaptation']['original_source_hoo_configuration_id']='invented'
        with self.assertRaises(GeneratorError):validate_bundle(changed)
        from tests.test_schedule_generator_physical_authority_v1_2 import fixture,evidence,source
        from scripts.schedule_generator_physical_sets import compile_exact_inventory
        records=fixture();role=records['ordered_fixture_roles'][0]
        role['service_definition']['value']['load']['schedule_id']=None
        role['schedule_authority']={'kind':'recovered_source_ruleset','frozen_schedule_id':None,
            'service_definition':copy.deepcopy(role['service_definition']),'source_rows':[source({'row':1})],
            'compiled_ruleset':{'rules':[]},'bridge_evidence':evidence()}
        with self.assertRaises(GeneratorError) as raised:compile_exact_inventory(records)
        self.assertEqual(raised.exception.code,'requires_binding')

    def test_physical_only_keeps_unchanged_eligible_pool_without_programme_output(self):
        for parent in (False,True):
            bundle=exact_bundle(parent=parent);original_pool=copy.deepcopy(bundle['metadata']['building_realizations'][0]['native_context']['execution_qualification'])
            bundle['constituents']=[c for c in bundle['constituents'] if c['owner_kind']=='physical_service']
            bundle['metadata']['building_realizations'][0]['native_context']['execution_authority']['canonical_program_records']=[]
            validate_bundle(bundle)
            self.assertEqual(bundle['metadata']['building_realizations'][0]['native_context']['execution_qualification'],original_pool)
            self.assertTrue(all(c['owner_kind']=='physical_service' for c in bundle['constituents']))

    def test_all_legacy_and_combined_three_mode_selection(self):
        from atlas_schedules.mixtures import compose_constituents
        from atlas_schedules.service_graph import _upgrade_bundle
        legacy=_upgrade_bundle(legacy_bundle());exact=exact_bundle();caller=caller_bundle(alternatives=False)
        only=compose_constituents([legacy],mixture(services=[{'instance_key':'legacy-water'}]),CALENDAR)
        ref=only['constituents'][-1]['generation']['service_set_selection']['effective_physical_members'][0]
        self.assertEqual(ref['binding_ref_kind'],'legacy_whole')
        self.assertFalse(set(ref)&{'building_realization_id','source_fixture_role_id','unit_id','requirement_id'})
        p=exact['constituents'][0];view=caller['constituents'][1]
        combined=compose_constituents([legacy,exact,caller],mixture([
            {'instance_key':p['instance_key'],'weight':.2},{'instance_key':view['instance_key'],'weight':.8}],
            [{'instance_key':'legacy-water'}]),CALENDAR)
        receipt=combined['constituents'][-1]['generation']['service_set_selection']
        self.assertEqual([r['binding_ref_kind'] for r in receipt['effective_physical_members']],
            ['legacy_whole']+['exact_source_role']*4+[caller['constituents'][0]['physical_binding_kind']])
        validate_bundle(combined)
        # Whole source target × extent, once; programme weights do not enter water.
        expected=sum(b['reference_target']['total']*c['shared_services'][0]['extent']['value'] for c in combined['constituents']
            if c['owner_kind']=='physical_service' for b in [combined['bindings'][c['binding_indices'][0]]])/1000
        water=next(b for b in combined['bindings'] if b['instance_key']==combined['constituents'][-1]['instance_key'])
        self.assertAlmostEqual(water['reference_target']['total'],expected)
        for label in ('factor','omitted','duplicate','fraction','reason','missing_receipt'):
            bad=copy.deepcopy(combined);result=bad['constituents'][-1]
            components=result['demands'][0]['evidence']['components']
            if label=='factor':components[0]['factor']*=2
            if label=='omitted':components.pop()
            if label=='duplicate':components.append(copy.deepcopy(components[0]))
            if label=='fraction':
                schedule=bad['schedules'][water['schedule_id']]['values']
                schedule[0],schedule[1]=schedule[0]+.01,schedule[1]-.01
            if label=='reason':result['generation']['service_set_selection']['reasons'][0]['deduplicated']=True
            if label=='missing_receipt':result['generation'].pop('service_set_selection')
            with self.subTest(label=label),self.assertRaises(GeneratorError):validate_bundle(bad)
        with self.assertRaises(GeneratorError) as raised:
            compose_constituents([combined],mixture([{'instance_key':combined['constituents'][-1]['instance_key'],'weight':1}]),CALENDAR)
        self.assertEqual(raised.exception.code,'incompatible_source_composition')

    def test_cross_mode_ambiguity_and_required_denominator(self):
        from atlas_schedules.mixtures import compose_constituents
        exact=exact_bundle();p=exact['constituents'][0]
        for request in ({'members':[]},{'members':[],'result_basis':'floor_area'},
                        {'members':[],'result_basis':'floor_area','denominator':{'value':0,'unit':'m2'}}):
            with self.subTest(request=request),self.assertRaises(GeneratorError) as raised:
                select_physical_services(exact,request,[(p,1)])
            self.assertEqual(raised.exception.code,'incompatible_basis')
        with self.assertRaises(GeneratorError) as raised:
            compose_constituents([legacy_bundle(exact['bindings'][0]['source_service_id']),exact],
                mixture([{'instance_key':p['instance_key'],'weight':1}],[{'instance_key':'legacy-water'}]),CALENDAR)
        self.assertEqual(raised.exception.code,'shared_service_conflict')

    def test_caller_static_pool_original_proof_and_alternative_views(self):
        bundle=caller_bundle();validate_bundle(bundle)
        programme=bundle['constituents'][1];other=bundle['constituents'][2]
        selected,receipt=select_physical_services(bundle,mixture(),[(programme,.2),(other,0)])
        self.assertEqual(len(selected),1);self.assertEqual(receipt['reasons'][0]['reason_kind'],'caller_unit_requirement')
        with self.assertRaises(GeneratorError) as raised:select_physical_services(bundle,mixture(),[(programme,.2),(other,.8)])
        self.assertEqual(raised.exception.code,'incompatible_source_composition')
        for label in ('evidence','method','unused_pool','area','owner','host'):
            bad=copy.deepcopy(bundle);r=bad['metadata']['building_realizations'][0]
            if label=='evidence':r['unit_inventory']['units'][0]['area_evidence'][0]['original_value']=0
            if label=='method':bad['constituents'][0]['generation']['water_method_receipt']['consumed_input_fields']=[]
            if label=='unused_pool':r['method_qualification']['value']['qualifications'][1]['value']['association']['value']['reference_calendar']['year']=2009
            if label=='area':bad['constituents'][0]['shared_services'][0]['whole_input_target']['total']*=2
            if label=='owner':bad['constituents'].append(copy.deepcopy(bad['constituents'][0]))
            if label=='host':bad['constituents'][0]['shared_services'][0]['source_basis_target']['host']='unresolved_zone_heat'
            with self.subTest(label=label),self.assertRaises(GeneratorError):validate_bundle(bad)
        # A stable two-ID eligible pool supports one actual declared view.
        single=caller_bundle(alternatives=False);validate_bundle(single)
        self.assertEqual(len(single['metadata']['building_realizations'][0]['source_requirements']),1)
        self.assertEqual(len(single['metadata']['building_realizations'][0]['method_qualification']['value']['qualifications']),2)
        original=single['constituents'][0]['shared_services'][0]['caller_unit_adaptation']['source_requirement']['original_demand']['value']
        self.assertEqual(original['zone_heat_assignment'],'unresolved')

    def test_actor_reconstruction_rejects_self_asserted_receipts_and_keeps_n0(self):
        from atlas_schedules.seeds import assign_physical_unit_sequence
        bundle=caller_bundle(alternatives=False);owner=bundle['constituents'][1]
        owner['inputs']['residents']=0;owner['generation']['source_inputs']={'method':'unit_occupancy_interior_lighting'}
        actor={'actor_kind':'apartment_adapter','instance_key':owner['instance_key'],
            'building_realization_id':owner['building_realization_id'],'unit_id':owner['unit_id'],'stochastic_action':'skip_n0'}
        sequence=assign_physical_unit_sequence(42,[actor]);bundle['generation'].update(
            physical_unit_seed_sequence=sequence,residential_unit_order=[owner['instance_key']],unit_seeds={owner['instance_key']:42})
        validate_bundle(bundle)
        for label in ('seed','position','removed','invented','cohort'):
            changed=copy.deepcopy(bundle)
            if label=='seed':changed['generation']['physical_unit_seed_sequence'][0]['unit_seed']=43
            if label=='position':changed['generation']['physical_unit_seed_sequence'][0]['position']=1
            if label=='removed':changed['generation'].update(physical_unit_seed_sequence=[],residential_unit_order=[],unit_seeds={})
            if label=='invented':changed['generation']['physical_unit_seed_sequence'][0]['actor_kind']='stock'
            if label=='cohort':changed['constituents'][1]['inputs']['residents']=1
            with self.subTest(label=label),self.assertRaises(GeneratorError):validate_bundle(changed)
    def test_two_incoming_bundle_graph_remap(self):
        from atlas_schedules.mixtures import compose_constituents
        from atlas_schedules.source_compositions import project_source_members
        first=exact_bundle(parent=True);second=rename_graph(first,'-two')
        validate_bundle(first);validate_bundle(second)
        root=first['constituents'][-1]['instance_key'];other=second['constituents'][-1]['instance_key']
        with patch('atlas_schedules.resources.ResourceSet.load',side_effect=AssertionError('offline')):
            combined=compose_constituents([first,second],mixture([
                {'instance_key':root,'weight':.2},{'instance_key':other,'weight':.8}]),CALENDAR)
        validate_bundle(combined)
        self.assertEqual(combined['schema_version'],'1.2.0')
        self.assertEqual(len(combined['constituents'][-1]['generation']['service_set_selection']['effective_physical_members']),12)
        # The second valid local binding 0 is globally rebased to 6.
        owner=next(c for c in combined['constituents'] if c['instance_key']==other)
        self.assertEqual(owner['service_set_projections'][0]['members'][0]['physical']['binding_index'],6)
        projected,inverse=project_source_members(combined,[other])
        self.assertEqual(set(projected['constituents'][0]['service_set_projections'][0]['role_ids']),
                         set(owner['service_set_projections'][0]['role_ids']))
        self.assertEqual(inverse[0],6)
        validate_bundle(projected)

    def test_comparison_resolves_legal_binding_rebase_but_keeps_seed_exact(self):
        from atlas_schedules.comparison import compare_bundles
        from atlas_schedules.source_compositions import remap_binding_references
        original=exact_bundle(parent=True);changed=copy.deepcopy(original)
        mapping={i:len(changed['bindings'])-i-1 for i in range(len(changed['bindings']))}
        remap_binding_references(changed,mapping);changed['bindings'].reverse()
        policy={'tolerances':{k:{'abs_tol':1e-9,'rel_tol':1e-9} for k in (
            'annual_volume_m3','annual_energy_integral','fraction','source_arithmetic','temperature_C','activity_W_person')}}
        validate_bundle(changed)
        self.assertEqual(compare_bundles(changed,original,policy),[])
        changed['generation']['physical_unit_seed_sequence']=[{'actor_kind':'stock','instance_key':'invented',
            'building_realization_id':None,'unit_id':None,'stochastic_action':'generate','position':0,'unit_seed':42}]
        self.assertTrue(compare_bundles(changed,original,policy))
        with self.assertRaises(GeneratorError):validate_bundle(changed)
        changed=copy.deepcopy(original)
        changed['metadata']['building_realizations'][0]['inventory']['roles'][0]['geometry_operands']['zone_multiplier']+=1
        self.assertTrue(compare_bundles(changed,original,policy))
    def test_explicit_first_positive_requirement_order_and_whole_participation(self):
        bundle=exact_bundle();programme=bundle['constituents'][0]
        first=programme['service_set_projections'][0]['members'][0]['physical']['instance_key']
        request=mixture([{'instance_key':programme['instance_key'],'weight':.2}],
                        [{'instance_key':first}])
        selected,receipt=select_physical_services(bundle,request,[(programme,.2)])
        self.assertEqual([w for c,w in selected],[1]*4)
        self.assertEqual([r['reason_kind'] for r in receipt['reasons']],
                         ['explicit_service_selection']+['exact_required_set']*4)
        self.assertEqual([r['deduplicated'] for r in receipt['reasons']],
                         [False,True,False,False,False])
        selected,receipt=select_physical_services(bundle,mixture(),[(programme,0)])
        self.assertEqual(selected,[])
        zero=exact_bundle(zero=True);programme=zero['constituents'][0]
        selected,receipt=select_physical_services(zero,mixture(),[(programme,1)])
        self.assertEqual(len(selected),4)
        self.assertTrue(all(c['shared_services'][0]['whole_input_target']['total']==0 for c,w in selected))

    def test_retained_exact_graph_is_publicly_valid_without_resource_lookup(self):
        for parent,original in ((False,False),(True,False),(True,True)):
            with self.subTest(parent=parent,original=original):
                bundle=exact_bundle(parent=parent,original_context=original)
                with patch('atlas_schedules.resources.ResourceSet.load',side_effect=AssertionError('offline')):
                    validate_bundle(bundle)
                    validate_physical_graph(bundle)
                root=bundle['constituents'][-1] if parent else bundle['constituents'][0]
                closure=required_graph_closure(bundle,[root['instance_key']])
                self.assertEqual(set(closure),{c['instance_key'] for c in bundle['constituents']})

    def test_in_range_reference_and_missing_owner_are_rejected(self):
        bundle=exact_bundle()
        for label in ('index','schedule','owner','field','target','authority','pool'):
            bad=copy.deepcopy(bundle);p=bad['constituents'][0]['service_set_projections'][0]
            if label=='index':p['members'][0]['physical']['binding_index']=1
            if label=='schedule':p['members'][0]['physical']['schedule_id']=bad['bindings'][1]['schedule_id']
            if label=='owner':bad['constituents'].pop()
            if label=='field':p['members'][0]['physical']['unknown_reference']=0
            if label=='target':p['projected_target']['total']*=2
            if label=='authority':bad['metadata']['building_realizations'][0]['native_context']['execution_authority']['canonical_physical_records'][0]['value']['definition']['load']['value']*=2
            if label=='pool':bad['metadata']['building_realizations'][0]['native_context']['execution_qualification']['value']['standalone_program_records']*=2
            with self.subTest(label=label),self.assertRaises(GeneratorError):validate_bundle(bad)

    def test_source_parent_additive_overlap_even_zero_child(self):
        bundle=exact_bundle(parent=True);parent=bundle['constituents'][-1]
        child=parent['service_set_projections'][0]['components'][0]['member_instance_key']
        owners={c['instance_key']:c for c in bundle['constituents']}
        with self.assertRaises(GeneratorError) as raised:
            select_physical_services(bundle,mixture(),[(parent,1),(owners[child],0)])
        self.assertEqual(raised.exception.code,'incompatible_source_composition')


if __name__=='__main__':unittest.main()
