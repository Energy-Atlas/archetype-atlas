"""Labelled contract fixtures for unpublished caller-unit fixed apartment water.

These tests establish source and arithmetic boundaries, not a native caller
fixture certificate or an enabled production programme ID.
"""
import unittest
import importlib.util
import copy
import csv
import hashlib
import json
import math
import tempfile
from pathlib import Path
from unittest.mock import patch

from atlas_schedules.budgets import bind_budget
from atlas_schedules.calendar import evaluate_rules
from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet, write_resources

from scripts import schedule_generator_build


ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS = ROOT/'data/definition-releases/v0.1.1'
RAW = ROOT/'data/raw/openstudio-standards'
HIGH = ('program-23458a6e125b4cee7f62bb42',
        'program-c448bb72c3506ad91ce6a8ea',
        'service-4d91c74f772e74926e2ecebb',
        'schedule-b390cc186dc47849e5d9',
        'lib/openstudio-standards/standards/ashrae_90_1/ashrae_90_1_2013/data/ashrae_90_1_2013.spc_typ.json', 41)
MID = ('program-1bff8c83069c349972223cbf',
       'program-02a965069a6a68c83d2d4695',
       'service-2d40bf7a2924ea1b3bd735d7',
       'schedule-91ecb5143fd1beddfead',
       'lib/openstudio-standards/standards/ashrae_90_1/ashrae_90_1_2007/data/ashrae_90_1_2007.spc_typ.json', 93)
HELPERS = ('lib/openstudio-standards/standards/Standards.ServiceWaterHeating.rb',
           'lib/openstudio-standards/service_water_heating/create_water_use.rb')


def source(path, locator, value):
    content = (ROOT/path).read_bytes()
    return {'path':path, 'sha256':hashlib.sha256(content).hexdigest(),
            'locator':locator, 'value':copy.deepcopy(value)}


def derived(name, value):
    # A labelled structural fixture: no upstream or native certificate claim.
    return {'path':'contract-fixture/'+name+'.json',
            'sha256':hashlib.sha256(canonical(value)).hexdigest(),
            'locator':'/', 'value':copy.deepcopy(value)}


def field_evidence(path, locator, value, unit):
    return {'source_revision':'labelled-contract-fixture', 'source_path':path,
            'source_sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
            'locator':locator, 'original_value':copy.deepcopy(value),
            'original_unit':unit, 'transformation':'Retain original source field and SI conversion',
            'extraction_date':'2026-10-15',
            'interpretation_note':'Structural fixture, not native qualification'}


def source_case(case=HIGH, index=0):
    programme_ids, sid, schedule_id, row_path, row_index = case[:2], case[2], case[3], case[4], case[5]
    def record(filename, identifier):
        rows=json.loads((DEFINITIONS/filename).read_text(encoding='utf-8'))
        i,row=next((i,row) for i,row in enumerate(rows) if row['id']==identifier)
        return source('data/definition-releases/v0.1.1/'+filename, '/'+str(i), row)
    programme=record('programs.json',programme_ids[index]);service=record('services.json',sid)
    ruleset=record('schedules.json',schedule_id)
    row=json.loads((RAW/row_path).read_text(encoding='utf-8'))['space_types'][row_index]
    space=source('data/raw/openstudio-standards/'+row_path,'/space_types/'+str(row_index),row)
    helpers=[source('data/raw/openstudio-standards/'+p,'/',(RAW/p).read_text(encoding='utf-8')) for p in HELPERS]
    rootloc=space['locator']; rawpath=space['path']
    evidence=[field_evidence(rawpath,rootloc+'/'+field,row[field],unit) for field,unit in (
        ('service_water_heating_peak_flow_per_area','US gal/h/ft2'),
        ('service_water_heating_target_temperature','F'),
        ('service_water_heating_fraction_sensible','1'),
        ('service_water_heating_fraction_latent','1'),
        ('service_water_heating_system_type',None))]
    evidence.extend(field_evidence(helper['path'],helper['locator'],helper['value'],'Ruby source')
                    for helper in helpers)
    controls=derived('controls-'+programme_ids[index],{
        'source_space_type':space,'source_helpers':helpers,
        'selected_branch':'is_flow_per_area_true',
        'original_density':{'value':0.003663157895,'unit':'US gal/h/ft2',
                            'canonical_value':4.146067251759837e-8,'canonical_unit':'m3/s/m2'},
        'target_temperature':{'original_value':140,'original_unit':'F','canonical_value':60,'canonical_unit':'C'},
        'sensible_fraction':{'value':0.2,'unit':'1'},'latent_fraction':{'value':0.05,'unit':'1'},
        'source_system_type':row['service_water_heating_system_type'],'evidence':evidence})
    load_index,load=next((i,v) for i,v in enumerate(programme['value']['loads']) if v['quantity']=='hot_water_volume')
    original=dict(programme,locator=programme['locator']+'/loads/'+str(load_index),value=copy.deepcopy(load))
    association=derived('association-'+programme_ids[index],{
        'programme':programme,'original_demand':original,'service_definition':service,
        'source_ruleset':ruleset,'fixed_controls':controls,'source_system_type':space,
        'reference_calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},'evidence':evidence})
    return programme,service,ruleset,{'field_evidence':evidence,'source_system_type':space,
                                      'fixed_controls':controls,'association':association}


def compiled(case=HIGH,index=0):
    return schedule_generator_build.compile_apartment_water_requirement(*source_case(case,index))


def area_evidence(area):
    return [{'source_revision':'caller-contract-fixture','source_path':'contract-fixture/caller-area.json',
             'source_sha256':'a'*64,'locator':'/floor_area_m2','original_value':area,
             'original_unit':'m2','transformation':'Caller declared SI area',
             'extraction_date':'2026-10-15','interpretation_note':'Caller authority, not source geometry'}]


def unit(unit_id,physical_id,programmes,area=80.0,chosen=None):
    first=programmes[0]
    return {'unit_id':unit_id,'physical_id':physical_id,
            'source_service_id':first['source_service_id'],
            'source_beneficiary_id':first['source_beneficiary_id'],
            'programme_ids':[r['programme']['value']['id'] for r in programmes],
            'water_authority_programme_id':chosen or first['programme']['value']['id'],
            'floor_area_m2':area,'area_evidence':area_evidence(area),
            'multiplicity':1,'identity_evidence':area_evidence(unit_id)}


def realization(units,family='HighriseApartment',template='90.1-2013'):
    inventory={'authority':'caller_declared_units','units':copy.deepcopy(units)}
    fields=('unit_id','physical_id','source_service_id','source_beneficiary_id',
            'programme_ids','water_authority_programme_id','floor_area_m2')
    facts={'building_realization_id':'building-1','unit_inventory_id':'caller-inventory-1',
           'units':[{k:copy.deepcopy(u[k]) for k in fields} for u in inventory['units']]}
    fact_path='contract-fixture/caller-facts.json';fact_sha=hashlib.sha256(canonical(facts)).hexdigest()
    def claim(locator,value,unit=None):
        return {'source_revision':'labelled-caller-contract-fixture','source_path':fact_path,
                'source_sha256':fact_sha,'locator':locator,'original_value':copy.deepcopy(value),
                'original_unit':unit,'transformation':'Caller fact retained in normalized m2',
                'extraction_date':'2026-10-15',
                'interpretation_note':'Fact-only caller authority, not source geometry or native certificate'}
    for i,u in enumerate(inventory['units']):
        base='/units/'+str(i)
        u['area_evidence']=[claim(base+'/floor_area_m2',u['floor_area_m2'],'m2')]
        u['identity_evidence']=[claim('/building_realization_id',facts['building_realization_id']),
                                claim('/unit_inventory_id',facts['unit_inventory_id'])]
        u['identity_evidence'].extend(claim(base+'/'+field,u[field]) for field in fields
                                      if field!='floor_area_m2')
    return {'mode':'caller_unit_prototype_density_fixed_dhw','building_realization_id':'building-1',
            'building_type':family,'template':template,'unit_inventory_id':'caller-inventory-1',
            'unit_inventory':inventory,'unit_inventory_sha256':hashlib.sha256(canonical(inventory)).hexdigest()}


def resource_fixture(requirements):
    records={}
    proofs=[]
    for req in requirements:
        pid=req['programme']['value']['id']
        case=HIGH if req['family']=='HighriseApartment' else MID
        index=case[:2].index(pid)
        _,_,_,evidence=source_case(case,index)
        controls=evidence['fixed_controls'];association=evidence['association']
        qualification=derived('qualification-'+pid,{
            'qualification_id':'contract-fixture-'+pid,
            'qualification_scope':'exact_apartment_programme_fixed_rule_calendar_controls',
            'programme_id':pid,'requirement':req,'association':association,
            'fixed_controls':controls,'evidence':evidence['field_evidence']})
        records['reference','caller-water-requirement__'+pid]=copy.deepcopy(req)
        records['reference','caller-water-controls__'+pid]=copy.deepcopy(controls)
        records['reference','caller-water-association__'+pid]=copy.deepcopy(association)
        records['reference','caller-water-qualification__'+pid]=copy.deepcopy(qualification)
        proofs.append(qualification)
    first=requirements[0];calendar={'year':2007,'clock':'local_standard_time','holidays':[]}
    context={'family':first['family'],'template':first['template'],'reference_calendar':calendar}
    key='caller-water-qualification-set__'+hashlib.sha256(canonical(context)).hexdigest()
    group=derived('fixed-qualified-pool',{
        'qualification_scope':'caller_unit_fixed_water_programme_coverage',
        **context,'qualifications':proofs,'evidence':source_case()[3]['field_evidence']})
    records['reference',key]=group
    temporary=tempfile.TemporaryDirectory()
    manifest=write_resources(Path(temporary.name),records,{'purpose':'labelled contract fixture'})
    resources=ResourceSet(Path(temporary.name),manifest['resource_set_id'])
    return temporary,resources,group


def pairs(real,requirements,programme_claims=True):
    result=[]
    for u in real['unit_inventory']['units']:
        p={'key':'owner-'+u['unit_id'],'owner_kind':'physical_service','physical_binding_kind':
           'caller_unit_prototype_density_fixed_dhw','building_realization_id':real['building_realization_id'],
           'unit_id':u['unit_id'],'physical_id':u['physical_id'],'source_service_id':u['source_service_id'],
           'operating_group':None,'inputs':{'water_method':'source_fixed_apartment_dhw',
                                          'source_geometry_departure':'caller_unit_area'},
           'basis_bindings':{'multiplicity':1,'extents':{'floor_area':{
               'value':u['floor_area_m2'],'unit':'m2','evidence':copy.deepcopy(u['area_evidence'])}}}}
        result.append((p,{}))
        if programme_claims:
            for pid in u['programme_ids']:
                req=requirements[pid]
                i={'key':'view-'+u['unit_id']+'-'+pid,'owner_kind':'program','program_id':pid,
                   'building_realization_id':real['building_realization_id'],'unit_id':u['unit_id'],
                   'operating_group':None,'inputs':{},'basis_bindings':copy.deepcopy(p['basis_bindings'])}
                r={'program_id':pid,'owner_kind':'program','required_service_sets':[req],
                   'required_service_links':[],'source':{
                       'source_id':req['source_beneficiary_id'],'building_type':req['family'],
                       'template':req['template'],'evidence_view':req['programme_evidence_view']},
                   'slots':[],'demands':[],'controls':[],'shared_services':[], 'inputs':{}}
                result.append((i,r))
    return result


class CallerWaterContractTests(unittest.TestCase):
    def test_compiler_entry_exists_for_independent_original_demand(self):
        self.assertTrue(callable(getattr(schedule_generator_build,
                                         'compile_apartment_water_requirement', None)))

    def test_binder_entry_exists_for_one_physical_water_owner(self):
        self.assertIsNotNone(importlib.util.find_spec('atlas_schedules.caller_unit_water'))

    def test_source_and_reviewed_original_loads_compile_independently(self):
        source_req=compiled(HIGH,0);reviewed_req=compiled(HIGH,1)
        self.assertEqual(source_req['source_service_id'],HIGH[2])
        self.assertEqual(reviewed_req['source_service_id'],HIGH[2])
        self.assertNotEqual(source_req['requirement_id'],reviewed_req['requirement_id'])
        self.assertEqual([source_req['programme_evidence_view'],reviewed_req['programme_evidence_view']],
                         ['source','reviewed'])
        self.assertEqual(source_req['original_demand']['value']['value'],4.146067251759837e-8)
        self.assertEqual(source_req['original_demand']['value']['unit'],'m3/s/m2')
        self.assertEqual(source_req['source_ruleset']['value']['id'],HIGH[3])
        self.assertEqual(compiled(MID,0)['source_ruleset']['value']['id'],MID[3])
        self.assertNotEqual(HIGH[3],MID[3])
        self.assertEqual(source_req['source_system_type'],'Shared')
        self.assertEqual(compiled(MID,0)['source_system_type'],'One Per Unit')

    def test_compiler_rejects_changed_original_q_rule_scope_or_control(self):
        for label in ('q','scope','rule','control','system','missing_q'):
            with self.subTest(label=label):
                args=list(source_case())
                if label=='q':args[0]['value']['loads'][-1]['value']*=2
                if label=='scope':args[1]['value']['load']['scope']='program_service'
                if label=='rule':args[2]['value']['id']=MID[3]
                if label=='control':args[3]['fixed_controls']['value']['sensible_fraction']['value']=0
                if label=='system':args[3]['source_system_type']['value']['service_water_heating_system_type']='One Per Unit'
                if label=='missing_q':args[0]['value']['loads'][-1]['value']=None
                with self.assertRaises(GeneratorError) as raised:
                    schedule_generator_build.compile_apartment_water_requirement(*args)
                self.assertIn(raised.exception.code,{'source_integrity','requires_binding'})

    def test_source_evidence_is_complete_and_original_helpers_are_immutable(self):
        args=list(source_case())
        args[3]['field_evidence']=args[3]['field_evidence'][:1]
        with self.assertRaises(GeneratorError):schedule_generator_build.compile_apartment_water_requirement(*args)
        args=list(source_case())
        args[3]['fixed_controls']['value']['source_helpers'][1]['value']+='\n# changed after locking'
        with self.assertRaises(GeneratorError):schedule_generator_build.compile_apartment_water_requirement(*args)

    def test_coherently_relabelled_top_floor_source_row_cannot_bind_ordinary_view(self):
        from atlas_schedules.caller_unit_water import compile_requirement
        args=list(source_case());evidence=args[3]
        evidence['source_system_type']['value']['space_type']='Apartment_topfloor_NS'
        evidence['fixed_controls']['value']['source_space_type']=copy.deepcopy(evidence['source_system_type'])
        evidence['association']['value']['source_system_type']=copy.deepcopy(evidence['source_system_type'])
        evidence['association']['value']['fixed_controls']=copy.deepcopy(evidence['fixed_controls'])
        with self.assertRaises(GeneratorError) as raised:compile_requirement(*args)
        self.assertEqual(raised.exception.path,'/source_system_type')

    def test_coherently_changed_row_fractions_cannot_override_selected_helper_defaults(self):
        from atlas_schedules.caller_unit_water import compile_requirement
        args=list(source_case());evidence=args[3]
        row=evidence['source_system_type']['value']
        for field,value in (('service_water_heating_fraction_sensible',0.3),
                            ('service_water_heating_fraction_latent',0.04)):
            row[field]=value
            for record in evidence['field_evidence']:
                if record['locator'].endswith('/'+field):record['original_value']=value
        controls=evidence['fixed_controls']['value']
        controls['source_space_type']=copy.deepcopy(evidence['source_system_type'])
        controls['sensible_fraction']['value']=0.3;controls['latent_fraction']['value']=0.04
        controls['evidence']=copy.deepcopy(evidence['field_evidence'])
        association=evidence['association']['value']
        association['source_system_type']=copy.deepcopy(evidence['source_system_type'])
        association['fixed_controls']=copy.deepcopy(evidence['fixed_controls'])
        with self.assertRaises(GeneratorError) as raised:compile_requirement(*args)
        self.assertEqual(raised.exception.path,'/fixed_controls/source_helpers')

    def test_malformed_nested_source_proof_raises_contextual_generator_error(self):
        from atlas_schedules.caller_unit_water import compile_requirement
        mutations={
            'canonical_string':lambda a:a[3]['fixed_controls']['value']['original_density'].__setitem__('canonical_value','bad'),
            'canonical_null':lambda a:a[3]['fixed_controls']['value']['original_density'].__setitem__('canonical_value',None),
            'canonical_list':lambda a:a[3]['fixed_controls']['value']['original_density'].__setitem__('canonical_value',[]),
            'canonical_bool':lambda a:a[3]['fixed_controls']['value']['original_density'].__setitem__('canonical_value',True),
            'canonical_nonfinite':lambda a:a[3]['fixed_controls']['value']['original_density'].__setitem__('canonical_value',float('inf')),
            'temperature_string':lambda a:a[3]['fixed_controls']['value']['target_temperature'].__setitem__('original_value','bad'),
            'load_null':lambda a:a[0]['value'].__setitem__('loads',[None]),
            'load_list':lambda a:a[0]['value'].__setitem__('loads',[[]]),
            'service_ids_null':lambda a:a[0]['value'].__setitem__('service_ids',None),
            'evidence_ids_null':lambda a:a[1]['value'].__setitem__('evidence_ids',None),
        }
        for label,change in mutations.items():
            with self.subTest(label=label):
                args=list(source_case());change(args)
                with self.assertRaises(GeneratorError) as raised:compile_requirement(*args)
                self.assertIn(raised.exception.code,{'source_integrity','requires_binding'})

    def test_bounded_source_inventory_is_candidate_only(self):
        path=ROOT/'.superpowers/sdd/2026-10-13-schedule-generator/apartment-water-ownership-source-paths.tsv'
        with path.open(encoding='utf-8',newline='') as stream:rows=list(csv.DictReader(stream,delimiter='\t'))
        self.assertEqual(len(rows),20)
        self.assertEqual(len({r['source_program_id'] for r in rows}|
                             {r['reviewed_program_id'] for r in rows}),40)
        self.assertEqual({r['native_fixture_count'] for r in rows},{'not_native_executed'})

    def test_caller_inventory_requires_complete_evidenced_unit_and_same_water_authority(self):
        from atlas_schedules.caller_unit_water import resolve_caller_unit_inventory
        a,b=compiled(HIGH,0),compiled(HIGH,1)
        lookup={r['programme']['value']['id']:r for r in (a,b)}
        original=realization([unit('unit-1','draw-1',[a,b],chosen=b['programme']['value']['id'])])
        resolved=resolve_caller_unit_inventory(original,lookup)
        self.assertEqual(resolved[('building-1','unit-1')]['water_authority_programme_id'],
                         b['programme']['value']['id'])
        for label in ('hash','zero_area','multiplicity','wrong_sid','wrong_choice','duplicate_view','foreign_top_floor'):
            with self.subTest(label=label):
                broken=copy.deepcopy(original);u=broken['unit_inventory']['units'][0]
                if label=='hash':broken['unit_inventory_sha256']='0'*64
                if label=='zero_area':u['floor_area_m2']=0
                if label=='multiplicity':u['multiplicity']=2
                if label=='wrong_sid':u['source_service_id']=MID[2]
                if label=='wrong_choice':u['water_authority_programme_id']='program-missing'
                if label=='duplicate_view':u['programme_ids'].append(u['programme_ids'][0])
                if label=='foreign_top_floor':u['programme_ids'][1]=MID[0]
                if label!='hash':broken['unit_inventory_sha256']=hashlib.sha256(canonical(broken['unit_inventory'])).hexdigest()
                with self.assertRaises(GeneratorError):resolve_caller_unit_inventory(broken,lookup)

    def test_caller_evidence_must_bind_area_identity_views_and_primary_provenance(self):
        from atlas_schedules.caller_unit_water import resolve_caller_unit_inventory
        a,b=compiled(HIGH,0),compiled(HIGH,1)
        lookup={r['programme']['value']['id']:r for r in (a,b)}
        original=realization([unit('unit-1','draw-1',[a,b],area=80),
                              unit('unit-2','draw-2',[a],area=95)])
        self.assertEqual(len(resolve_caller_unit_inventory(original,lookup)),2)
        supported=copy.deepcopy(original)
        extra=copy.deepcopy(supported['unit_inventory']['units'][0]['area_evidence'][0])
        extra.update(locator='/supporting/original-drawing-area',source_path='contract-fixture/other-drawing.json',
                     source_sha256='c'*64,original_value=861.113,original_unit='ft2')
        supported['unit_inventory']['units'][0]['area_evidence'].append(extra)
        supported['unit_inventory_sha256']=hashlib.sha256(canonical(supported['unit_inventory'])).hexdigest()
        self.assertEqual(len(resolve_caller_unit_inventory(supported,lookup)),2)
        for label in ('zero_original_area','wrong_unit','wrong_draw','reordered_views',
                      'wrong_locator','wrong_unit_of_area','boolean_area','duplicate_claim',
                      'cross_unit_provenance','missing_building_claim'):
            with self.subTest(label=label):
                broken=copy.deepcopy(original);units=broken['unit_inventory']['units'];u=units[0]
                area=u['area_evidence'][0];claims=u['identity_evidence']
                byloc={entry['locator']:entry for entry in claims}
                if label=='zero_original_area':area['original_value']=0
                if label=='wrong_unit':byloc['/units/0/unit_id']['original_value']='unit-2'
                if label=='wrong_draw':byloc['/units/0/physical_id']['original_value']='draw-2'
                if label=='reordered_views':byloc['/units/0/programme_ids']['original_value'].reverse()
                if label=='wrong_locator':area['locator']='/units/1/floor_area_m2'
                if label=='wrong_unit_of_area':area['original_unit']='ft2'
                if label=='boolean_area':area['original_value']=True
                if label=='duplicate_claim':claims.append(copy.deepcopy(byloc['/units/0/unit_id']))
                if label=='cross_unit_provenance':units[1]['identity_evidence'][0]['source_sha256']='b'*64
                if label=='missing_building_claim':claims.remove(byloc['/building_realization_id'])
                broken['unit_inventory_sha256']=hashlib.sha256(canonical(broken['unit_inventory'])).hexdigest()
                with self.assertRaises(GeneratorError):resolve_caller_unit_inventory(broken,lookup)

    def test_default_closed_and_fixture_qualified_same_unit_views_distinct_units(self):
        from atlas_schedules import caller_unit_water as water
        a,b=compiled(HIGH,0),compiled(HIGH,1)
        requirements={r['programme']['value']['id']:r for r in (a,b)}
        real=realization([unit('unit-1','same-local-id',[a,b],area=80),
                          unit('unit-2','same-local-id',[a],area=95)])
        temporary,resources,group=resource_fixture([a,b])
        self.addCleanup(temporary.cleanup)
        request={'schema_version':'1.2.0','calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},
                 'building_realizations':[real],'instances':[]}
        resolved=pairs(real,requirements)
        with self.assertRaises(GeneratorError) as raised:
            water.prepare_caller_water(request,resolved,resources)
        self.assertEqual(raised.exception.code,'requires_binding')
        with patch.object(water,'_qualified_caller_water_method',return_value=True):
            plan=water.prepare_caller_water(request,resolved,resources)
        self.assertEqual(len(plan['owners']),2)
        self.assertEqual(len(plan['projections']),3)
        self.assertEqual(plan['building_realizations'][0]['method_qualification'],group)
        self.assertEqual([v['source_basis_target']['total'] for v in plan['owners']],
                         [0.6853498919966031]*2)
        self.assertEqual([v['whole_input_target']['total'] for v in plan['owners']],
                         [0.6853498919966031*80,0.6853498919966031*95])
        self.assertEqual(len(plan['building_realizations'][0]['source_requirements']),2)

    def test_static_qualification_pool_supports_subsets_orders_and_physical_only(self):
        from atlas_schedules import caller_unit_water as water
        a,b=compiled(HIGH,0),compiled(HIGH,1)
        lookup={r['programme']['value']['id']:r for r in (a,b)}
        temporary,resources,group=resource_fixture([a,b]);self.addCleanup(temporary.cleanup)
        cases=[([unit('u1','p1',[a],80)],True,[a['programme']['value']['id']]),
               ([unit('u1','p1',[b],95)],True,[b['programme']['value']['id']]),
               ([unit('u1','p1',[b,a],80)],False,[b['programme']['value']['id'],a['programme']['value']['id']])]
        with patch.object(water,'_qualified_caller_water_method',return_value=True):
            for units,claims,order in cases:
                with self.subTest(order=order,claims=claims):
                    real=realization(units)
                    params={'calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},
                            'building_realizations':[real]}
                    plan=water.prepare_caller_water(params,pairs(real,lookup,claims),resources)
                    self.assertEqual(plan['building_realizations'][0]['method_qualification'],group)
                    self.assertEqual([r['programme']['value']['id'] for r in
                                      plan['building_realizations'][0]['source_requirements']],order)
                    self.assertEqual(len(plan['owners']),1)
                    self.assertEqual(len(plan['projections']),len(order) if claims else 0)

    def test_owner_conflicts_and_foreign_method_operands_reject_before_rng(self):
        from atlas_schedules import caller_unit_water as water
        a=compiled();pid=a['programme']['value']['id'];temporary,resources,_=resource_fixture([a])
        self.addCleanup(temporary.cleanup)
        real=realization([unit('u1','p1',[a],80)])
        request={'calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},
                 'building_realizations':[real]}
        original=pairs(real,{pid:a})
        for label in ('missing_owner','duplicate_owner','duplicate_claim','wrong_area','wrong_physical','non_null_group',
                      'residents','cross_mode_sid','changed_requirement'):
            with self.subTest(label=label):
                items=copy.deepcopy(original)
                if label=='missing_owner':items=items[1:]
                if label=='duplicate_owner':items.append(copy.deepcopy(items[0]))
                if label=='duplicate_claim':
                    extra=copy.deepcopy(items[1]);extra[0]['key']='duplicate-programme-claim';items.append(extra)
                if label=='wrong_area':items[0][0]['basis_bindings']['extents']['floor_area']['value']=90
                if label=='wrong_physical':items[0][0]['physical_id']='different'
                if label=='non_null_group':items[0][0]['operating_group']='group'
                if label=='residents':items[0][0]['inputs']['residents']=0
                if label=='cross_mode_sid':items.append(({'key':'legacy','owner_kind':'physical_service',
                    'source_service_id':a['source_service_id'],'physical_id':'legacy','physical_binding_kind':'legacy_whole'},{}))
                if label=='changed_requirement':items[1][1]['required_service_sets'][0]['original_demand']['value']['value']*=2
                with patch.object(water,'_qualified_caller_water_method',return_value=True):
                    with self.assertRaises(GeneratorError):water.prepare_caller_water(request,items,resources)

    def test_fixed_rule_binding_uses_original_density_and_area_once(self):
        from atlas_schedules import caller_unit_water as water
        req=compiled();pid=req['programme']['value']['id'];real=realization([unit('unit-1','draw-1',[req],area=95)])
        temporary,resources,_=resource_fixture([req]);self.addCleanup(temporary.cleanup)
        request={'schema_version':'1.2.0','calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},
                 'building_realizations':[real],'instances':[]}
        with patch.object(water,'_qualified_caller_water_method',return_value=True):
            plan=water.prepare_caller_water(request,pairs(real,{pid:req}),resources)
        owner_plan=plan['owners'][0];owner_pair=next((i,r) for i,r in plan['resolved_instances'] if i['owner_kind']=='physical_service')
        owner_instance,owner_resolved=owner_pair
        values=evaluate_rules(req['source_ruleset']['value'],2007,[])['values']
        self.assertEqual(len(values),8760)
        self.assertEqual(math.fsum(values),4591.7)
        bound=bind_budget(owner_plan['source_basis_target'],values)
        self.assertAlmostEqual(bound['effective_magnitude']['value'],4.146067251759837e-8,places=19)
        self.assertEqual(owner_resolved['inputs']['reference_channels']['hot_water_volume'],values)
        bundle={'metadata':{'calendar':request['calendar']},'schedules':{'water-schedule':{'values':values}},
                'bindings':[dict(bound,kind='load',instance_key=owner_instance['key'],
                                 owner_kind='physical_service',physical_binding_kind='caller_unit_prototype_density_fixed_dhw',
                                 building_realization_id='building-1',unit_id='unit-1',physical_id='draw-1',
                                 source_service_id=req['source_service_id'],demand_id=req['source_service_id'],
                                 slot='hot_water_volume',schedule_id='water-schedule')],
                'constituents':[{'instance_key':owner_instance['key'],'owner_kind':'physical_service',
                                 'physical_binding_kind':'caller_unit_prototype_density_fixed_dhw',
                                 'building_realization_id':'building-1','unit_id':'unit-1','physical_id':'draw-1',
                                 'source_service_id':req['source_service_id'],'binding_indices':[0],
                                 'schedule_ids':{'hot_water_volume':'water-schedule'},
                                 'shared_services':copy.deepcopy(owner_resolved['shared_services']),
                                 'generation':{},'demands':copy.deepcopy(owner_resolved['demands'])},
                                {'instance_key':'view-unit-1-'+pid,'owner_kind':'program','program_id':pid,
                                 'building_realization_id':'building-1','unit_id':'unit-1',
                                 'demands':[],'slots':[],'schedule_ids':{},'binding_indices':[],
                                 'required_service_sets':[req],'service_set_projections':[]}]}
        water.bind_caller_water(bundle,plan)
        descriptor=bundle['constituents'][0]['shared_services'][0]
        self.assertEqual(descriptor['source_basis_target']['unit'],'m3/m2')
        self.assertEqual(descriptor['extent']['value'],95)
        self.assertEqual(descriptor['whole_input_target']['total'],0.6853498919966031*95)
        self.assertEqual(bundle['constituents'][1]['service_set_projections'][0]['projection_kind'],'caller_unit_density')
        receipt=bundle['constituents'][0]['generation']['water_method_receipt']
        self.assertEqual(receipt['random_draw_count'],0)
        self.assertIn('compiled_requirement.original_demand',receipt['consumed_input_fields'])


if __name__ == '__main__':
    unittest.main()
