"""Private, default-closed caller-unit fixed water authority and binding.

All source artifacts are explicit operands or verified ResourceSet records. This
module never loads repository files or creates an apartment stochastic actor.
"""
import copy
import hashlib
import math
import re

from .budgets import bind_budget, reference_budget
from .calendar import evaluate_rules
from .canonical import canonical
from .contract import _check_schema, _finite, _load_schema
from .errors import GeneratorError
from .physical_sets import _evidence, _source, _typed
from .programs import verify_caller_water_programme
from .resources import ResourceSet


MODE = 'caller_unit_prototype_density_fixed_dhw'
METHOD = 'source_fixed_apartment_dhw'
CALENDAR = {'year':2007,'clock':'local_standard_time','holidays':[]}
HELPERS = (
    ('lib/openstudio-standards/standards/Standards.ServiceWaterHeating.rb',
     '50f6c89f3e1371b198d33eb5acd6b25b81c0c4319fa261efc067ea511f6b1156'),
    ('lib/openstudio-standards/service_water_heating/create_water_use.rb',
     '6c506aeecc764d019ccc2d2bb1524560ab8130605b790f41bc9506f843d14e18'),
)


def _fail(path, message, code='source_integrity'):
    raise GeneratorError(code,path,message)


def _exact(value, keys, path):
    if not isinstance(value,dict) or set(value)!=set(keys):
        _fail(path,'Missing or unknown caller-water authority field')


def _same(a,b):
    return canonical(a)==canonical(b)


def _positive(value,path):
    if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
        _fail(path,'Positive finite caller-water operand required','requires_binding')


def _original_load(programme):
    loads=programme['value'].get('loads')
    if not isinstance(loads,list):_fail('/programme/loads','Entire original loads required')
    if any(not isinstance(load,dict) for load in loads):
        _fail('/programme/loads','Every original load must be an object')
    matches=[(i,load) for i,load in enumerate(loads) if load.get('quantity')=='hot_water_volume']
    if len(matches)!=1:_fail('/programme/loads','One original apartment water load required','requires_binding')
    index,load=matches[0]
    return dict(copy.deepcopy(programme),locator=programme['locator'].rstrip('/')+'/loads/'+str(index),value=copy.deepcopy(load))


def _validate_source(programme,service,ruleset,evidence):
    for name,obj in (('programme',programme),('service',service),('ruleset',ruleset)):
        _source(obj,'/'+name)
    _exact(evidence,('field_evidence','source_system_type','fixed_controls','association'),'/evidence')
    _evidence(evidence['field_evidence'],'/evidence/field_evidence')
    space=_source(evidence['source_system_type'],'/evidence/source_system_type')
    controls=_source(evidence['fixed_controls'],'/evidence/fixed_controls')
    association=_source(evidence['association'],'/evidence/association')
    p=programme['value'];s=service['value'];r=ruleset['value'];row=space['value']
    if any(not isinstance(v,dict) for v in (p,s,r,row)):_fail('/source','Whole original objects required')
    sid=s.get('id');load=_original_load(programme);d=load['value'];sd=s.get('load')
    if (not isinstance(p.get('service_ids'),list) or not isinstance(s.get('evidence_ids'),list) or
            not isinstance(s.get('beneficiary_program_ids'),list) or
            p.get('building_type') not in ('HighriseApartment','MidriseApartment') or
            p.get('evidence_view') not in ('source','reviewed') or
            type(p.get('id')) is not str or not p['id'] or type(p.get('source_id')) is not str or
            p.get('template')!=s.get('template') or p.get('building_type')!=s.get('building_type') or
            sid not in p.get('service_ids',[]) or s.get('beneficiary_program_ids') != [p['source_id']] or
            s.get('ownership')!='instantiate_once' or s.get('assignment')!='consumer_host_when_applicable' or
            s.get('end_use')!='main' or not isinstance(s.get('path_id'),str) or
            s['path_id']!=p['building_type']+'|'+p['template']+'|main|'+p['source_id'] or
            d.get('service_id')!=sid or d.get('demand_id')!=sid or d.get('scope')!='program_service' or
            sd!=dict(d,scope='building_service') or d.get('quantity')!='hot_water_volume' or
            d.get('basis')!='floor_area' or d.get('unit')!='m3/s/m2' or
            d.get('required_inputs')!=['floor_area'] or d.get('status')!='known' or
            d.get('thermal_effects')!={} or d.get('zone_heat_assignment')!='unresolved' or
            d.get('target_temperature_degC')!=60 or d.get('evidence_id') not in s.get('evidence_ids',[]) or
            d.get('schedule_id')!=r.get('id') or r.get('schedule_type')!='fraction' or
            r.get('time_resolution_minutes')!=60 or not isinstance(r.get('rules'),list) or
            not r['rules'] or any(not isinstance(rule,dict) for rule in r['rules'])):
        _fail('/original_demand','Original programme/service/SID/Ruleset authority differs')
    _positive(d.get('value'),'/original_demand/value')
    if (not isinstance(row.get('space_type'),str) or
            row['space_type']+'_'+p.get('building_type')!=p.get('name') or
            any(row.get(k)!=p.get(v) for k,v in (
            ('building_type','building_type'),('template','template')))):
        _fail('/source_system_type','Original source row family/template differs')
    if row.get('service_water_heating_system_type') not in ('Shared','One Per Unit'):
        _fail('/source_system_type','Original system type missing','requires_binding')
    if (row.get('service_water_heating_schedule')!=r.get('source_name') or
            row.get('service_water_heating_peak_flow_per_area') is None or
            row.get('service_water_heating_target_temperature') is None or
            row.get('service_water_heating_fraction_sensible') is None or
            row.get('service_water_heating_fraction_latent') is None):
        _fail('/source_system_type','Original row water path/control association incomplete','requires_binding')
    c=controls['value']
    _exact(c,('source_space_type','source_helpers','selected_branch','original_density',
              'target_temperature','sensible_fraction','latent_fraction','source_system_type','evidence'),'/fixed_controls/value')
    _evidence(c['evidence'],'/fixed_controls/evidence')
    if not _same(c['source_space_type'],space) or c['source_system_type']!=row['service_water_heating_system_type']:
        _fail('/fixed_controls/source_space_type','Original whole row differs')
    helpers=c['source_helpers']
    if not isinstance(helpers,list) or len(helpers)!=2:_fail('/fixed_controls/source_helpers','Both whole original helper files required','requires_binding')
    for i,(helper,(path,sha)) in enumerate(zip(helpers,HELPERS)):
        _source(helper,'/fixed_controls/source_helpers/'+str(i))
        if (not helper['path'].endswith(path) or helper['sha256']!=sha or helper['locator']!='/' or
                type(helper['value']) is not str or
                hashlib.sha256(helper['value'].encode('utf-8')).hexdigest()!=sha):
            _fail('/fixed_controls/source_helpers/'+str(i),'Pinned whole original helper differs','requires_binding')
    expected=[(space['path'],space['sha256'],space['locator']+'/'+name,row.get(name),unit)
              for name,unit in (('service_water_heating_peak_flow_per_area','US gal/h/ft2'),
                                ('service_water_heating_target_temperature','F'),
                                ('service_water_heating_fraction_sensible','1'),
                                ('service_water_heating_fraction_latent','1'),
                                ('service_water_heating_system_type',None))]
    expected.extend((helper['path'],helper['sha256'],helper['locator'],helper['value'],'Ruby source')
                    for helper in helpers)
    for path,sha,locator,value,unit in expected:
        if not any(e['source_path']==path and e['source_sha256']==sha and e['locator']==locator and
                   _same(e['original_value'],value) and e['original_unit']==unit
                   for e in evidence['field_evidence']):
            _fail('/evidence/field_evidence','Original control/source-branch field evidence incomplete','requires_binding')
        if not any(e['source_path']==path and e['source_sha256']==sha and e['locator']==locator and
                   _same(e['original_value'],value) and e['original_unit']==unit for e in c['evidence']):
            _fail('/fixed_controls/evidence','Derived controls omit original field proof','requires_binding')
    density=c['original_density'];temperature=c['target_temperature']
    _exact(density,('value','unit','canonical_value','canonical_unit'),'/fixed_controls/original_density')
    _exact(temperature,('original_value','original_unit','canonical_value','canonical_unit'),'/fixed_controls/target_temperature')
    for name in ('sensible_fraction','latent_fraction'):_exact(c[name],('value','unit'),'/fixed_controls/'+name)
    for field,value in (('original_density/value',density['value']),
                        ('original_density/canonical_value',density['canonical_value']),
                        ('target_temperature/original_value',temperature['original_value']),
                        ('target_temperature/canonical_value',temperature['canonical_value']),
                        ('sensible_fraction/value',c['sensible_fraction']['value']),
                        ('latent_fraction/value',c['latent_fraction']['value'])):
        if type(value) not in (int,float) or not math.isfinite(value):
            _fail('/fixed_controls/'+field,'Finite numeric original control required')
    for field in ('service_water_heating_peak_flow_per_area','service_water_heating_target_temperature',
                  'service_water_heating_fraction_sensible','service_water_heating_fraction_latent'):
        value=row[field]
        if type(value) not in (int,float) or not math.isfinite(value):
            _fail('/source_system_type/'+field,'Finite numeric original source field required')
    conversion=0.003785411784/3600/0.09290304
    if (c['selected_branch']!='is_flow_per_area_true' or density['unit']!='US gal/h/ft2' or
            density['canonical_unit']!='m3/s/m2' or type(density['value']) not in (int,float) or
            density['value']!=row['service_water_heating_peak_flow_per_area'] or
            not math.isclose(density['value']*conversion,density['canonical_value'],rel_tol=1e-12) or
            not math.isclose(density['canonical_value'],d['value'],rel_tol=1e-12) or
            temperature['original_unit']!='F' or temperature['canonical_unit']!='C' or
            temperature['original_value']!=row['service_water_heating_target_temperature'] or
            (temperature['original_value']-32)/1.8!=temperature['canonical_value'] or
            temperature['canonical_value']!=d['target_temperature_degC'] or
            c['sensible_fraction']!={'value':row['service_water_heating_fraction_sensible'],'unit':'1'} or
            c['latent_fraction']!={'value':row['service_water_heating_fraction_latent'],'unit':'1'}):
        _fail('/fixed_controls','Original selected density/temperature/control fields differ')
    # Pinned file SHA and whole text are provenance; these branch checks cannot
    # qualify a method. The independent closed selector remains mandatory.
    if ('is_flow_per_area: true' not in helpers[0]['value'] or
            "data['service_water_heating_peak_flow_per_area']" not in helpers[0]['value'] or
            'space.multiplier' not in helpers[0]['value'] or
            'water_use_temperature: mixed_water_temp_c' not in helpers[0]['value'] or
            'sensible_fraction: 0.2' not in helpers[1]['value'] or
            'latent_fraction: 0.05' not in helpers[1]['value']):
        _fail('/fixed_controls/source_helpers','Pinned source branch/default controls not retained','requires_binding')
    selected=re.search(r'water_fixture = OpenstudioStandards::ServiceWaterHeating\.create_water_use\(model,(.*?)service_water_loop: swh_loop\)',
                       helpers[0]['value'],re.S)
    constructor=re.search(r'def self\.create_water_use\(model,(.*?)space: nil\)',helpers[1]['value'],re.S)
    if (selected is None or constructor is None or
            re.search(r'\b(?:sensible|latent)_fraction\s*:',selected.group(1)) or
            not re.search(r'\bsensible_fraction:\s*0\.2\s*,',constructor.group(1)) or
            not re.search(r'\blatent_fraction:\s*0\.05\s*,',constructor.group(1)) or
            c['sensible_fraction']!={'value':0.2,'unit':'1'} or
            c['latent_fraction']!={'value':0.05,'unit':'1'}):
        _fail('/fixed_controls/source_helpers','Selected call must inherit pinned constructor fractions','requires_binding')
    a=association['value']
    _exact(a,('programme','original_demand','service_definition','source_ruleset','fixed_controls',
              'source_system_type','reference_calendar','evidence'),'/association/value')
    _evidence(a['evidence'],'/association/evidence')
    for name,want in (('programme',programme),('original_demand',load),('service_definition',service),
                      ('source_ruleset',ruleset),('fixed_controls',controls),('source_system_type',space)):
        if not _same(a[name],want):_fail('/association/'+name,'Entire independent source object differs')
    if not _same(a['reference_calendar'],CALENDAR):_fail('/association/reference_calendar','Fixed source calendar association required','requires_binding')
    return load,row


def compile_requirement(programme: dict, service: dict, ruleset: dict, evidence: dict) -> dict:
    """Compile immutable original water authority independently of caller units."""
    for name,value in (('programme',programme),('service',service),('ruleset',ruleset),('evidence',evidence)):
        try:_finite(value,'/'+name)
        except GeneratorError as error:
            if error.code!='invalid_json':raise
            raise GeneratorError('source_integrity',error.path,error.message) from error
    load,row=_validate_source(programme,service,ruleset,evidence)
    p=programme['value'];sid=service['value']['id']
    identity=[p['id'],p['evidence_view'],load['value']['demand_id']]
    requirement={'requirement_id':'caller-requirement-'+hashlib.sha256(canonical(identity)).hexdigest(),
        'kind':'original_apartment_unit_demand','required':True,'source_channel':'hot_water_volume',
        'ownership_mode':MODE,'water_method':METHOD,'programme':copy.deepcopy(programme),
        'original_demand':load,'service_definition':copy.deepcopy(service),
        'source_ruleset':copy.deepcopy(ruleset),'source_service_id':sid,
        'source_beneficiary_id':p['source_id'],'family':p['building_type'],'template':p['template'],
        'programme_evidence_view':p['evidence_view'],
        'source_system_type':row['service_water_heating_system_type'],
        'reference_calendar':copy.deepcopy(CALENDAR),
        'interpretation':'caller_unit_area_adaptation_of_original_fixed_dhw_density',
        'evidence':copy.deepcopy(evidence['field_evidence'])}
    _typed(requirement,'caller_requirement','/caller_requirement')
    return requirement


def _qualified_caller_water_method(qualification):
    """Production remains closed until each exact source method is reviewed."""
    return False


def validate_caller_unit_evidence(realization: dict) -> None:
    """Bind retained FieldEvidence to a separate fact-only caller declaration.

    Source paths and file hashes are caller provenance; this offline check does
    not fetch or authenticate the separately sourced fact record.
    """
    inventory=realization['unit_inventory'];units=inventory['units']
    fields=('unit_id','physical_id','source_service_id','source_beneficiary_id',
            'programme_ids','water_authority_programme_id')
    mandatory={'/building_realization_id','/unit_inventory_id'}
    for i in range(len(units)):
        mandatory.add('/units/'+str(i)+'/floor_area_m2')
        mandatory.update('/units/'+str(i)+'/'+field for field in fields)
    primary=None
    for i,u in enumerate(units):
        path='/unit_inventory/units/'+str(i)
        base='/units/'+str(i)
        area={base+'/floor_area_m2':(u['floor_area_m2'],'m2')}
        identity={'/building_realization_id':(realization['building_realization_id'],None),
                  '/unit_inventory_id':(realization['unit_inventory_id'],None)}
        identity.update({base+'/'+field:(u[field],None) for field in fields})
        seen=set()
        for name,expected in (('area_evidence',area),('identity_evidence',identity)):
            records=u[name]
            _evidence(records,path+'/'+name)
            for j,record in enumerate(records):
                locator=record['locator'];where=path+'/'+name+'/'+str(j)
                if locator in mandatory:
                    if locator not in expected or locator in seen:
                        _fail(where,'Caller fact locator is misplaced or duplicated')
                    value,unit=expected[locator]
                    if not _same(record['original_value'],value) or record['original_unit']!=unit:
                        _fail(where,'Original caller fact differs from declared unit')
                    if locator==base+'/floor_area_m2':
                        _positive(record['original_value'],where+'/original_value')
                    provenance=(record['source_path'],record['source_sha256'])
                    if primary is None:primary=provenance
                    elif provenance!=primary:
                        _fail(where,'Mandatory caller facts require one primary source file')
                    seen.add(locator)
        if seen!=set(area)|set(identity):
            _fail(path,'Complete original caller area and identity facts required','requires_binding')


def resolve_caller_unit_inventory(realization: dict, requirements: dict[str,dict]) -> dict:
    """Resolve the complete caller declaration independently of owner aliases."""
    schema=_load_schema('request','1.2.0')
    _finite(realization,'/building_realizations')
    try:_check_schema(realization,schema['$defs']['caller_realization'],schema,'/building_realizations')
    except GeneratorError as error:
        raise GeneratorError('source_integrity',error.path,error.message) from error
    inventory=realization['unit_inventory'];units=inventory['units']
    if realization['unit_inventory_sha256']!=hashlib.sha256(canonical(inventory)).hexdigest():
        _fail('/unit_inventory_sha256','Caller declaration checksum differs')
    if not units:_fail('/unit_inventory/units','At least one explicit actual unit required','requires_binding')
    validate_caller_unit_evidence(realization)
    answer={}
    for u in units:
        path='/unit_inventory/units/'+u['unit_id'];key=(realization['building_realization_id'],u['unit_id'])
        if key in answer:_fail(path,'Duplicate actual caller unit','shared_service_conflict')
        _positive(u['floor_area_m2'],path+'/floor_area_m2')
        if type(u['multiplicity']) not in (int,float) or u['multiplicity']!=1:
            _fail(path+'/multiplicity','One draw represents one actual unit','incompatible_basis')
        _evidence(u['area_evidence'],path+'/area_evidence');_evidence(u['identity_evidence'],path+'/identity_evidence')
        if not u['programme_ids'] or len(set(u['programme_ids']))!=len(u['programme_ids']):
            _fail(path+'/programme_ids','Complete unique alternative choices required','shared_service_conflict')
        if u['water_authority_programme_id'] not in u['programme_ids']:
            _fail(path+'/water_authority_programme_id','Explicit chosen water authority missing','requires_binding')
        ordered=[];views=set()
        for pid in u['programme_ids']:
            req=requirements.get(pid)
            if req is None:_fail(path+'/programme_ids','Independent exact source requirement missing','requires_binding')
            _typed(req,'caller_requirement',path+'/programme_ids/'+pid)
            view=req['programme_evidence_view']
            if view in views:_fail(path+'/programme_ids','At most one independently compiled ID per view','shared_service_conflict')
            views.add(view)
            if (req['programme']['value'].get('id')!=pid or req['family']!=realization['building_type'] or
                    req['template']!=realization['template'] or req['source_service_id']!=u['source_service_id'] or
                    req['source_beneficiary_id']!=u['source_beneficiary_id'] or
                    req['programme']['value'].get('evidence_view')!=view):
                _fail(path+'/programme_ids','Unit programme/SID/beneficiary/template/view differs','shared_service_conflict')
            ordered.append(req)
        chosen=requirements[u['water_authority_programme_id']]
        for req in ordered:
            if (any(not _same(req[name],chosen[name]) for name in ('service_definition','source_ruleset')) or
                    not _same(req['original_demand']['value'],chosen['original_demand']['value'])):
                _fail(path+'/programme_ids','Alternative view changes original water source','shared_service_conflict')
        answer[key]={'unit':copy.deepcopy(u),'requirements':copy.deepcopy(ordered),
                     'water_authority_programme_id':u['water_authority_programme_id'],
                     'chosen_requirement':copy.deepcopy(chosen),
                     'building_realization_id':realization['building_realization_id'],
                     'unit_inventory_id':realization['unit_inventory_id'],
                     'unit_inventory_sha256':realization['unit_inventory_sha256']}
    return answer


def _resource(resources, key):
    try:return resources.get('reference',key)
    except GeneratorError as error:
        raise GeneratorError('requires_binding','/reference/'+key,
                             'Independently locked caller water authority is missing') from error


def _qualified_pool(resources,realization):
    context={'family':realization['building_type'],'template':realization['template'],
             'reference_calendar':copy.deepcopy(CALENDAR)}
    key='caller-water-qualification-set__'+hashlib.sha256(canonical(context)).hexdigest()
    group=_source(_resource(resources,key),'/method_qualification')
    value=group['value']
    _exact(value,('qualification_scope','family','template','reference_calendar','qualifications','evidence'),
           '/method_qualification/value')
    _evidence(value['evidence'],'/method_qualification/evidence')
    if (value['qualification_scope']!='caller_unit_fixed_water_programme_coverage' or
            any(not _same(value[name],expected) for name,expected in context.items()) or
            not isinstance(value['qualifications'],list) or not value['qualifications']):
        _fail('/method_qualification','Exact static family/template/calendar coverage required','requires_binding')
    pool={};source_order=[]
    for i,qualification in enumerate(value['qualifications']):
        path='/method_qualification/qualifications/'+str(i)
        _source(qualification,path);q=qualification['value']
        _exact(q,('qualification_id','qualification_scope','programme_id','requirement',
                  'association','fixed_controls','evidence'),path+'/value')
        _evidence(q['evidence'],path+'/evidence')
        pid=q['programme_id'];req=q['requirement']
        if (type(pid) is not str or not pid or pid in pool or
                q['qualification_scope']!='exact_apartment_programme_fixed_rule_calendar_controls' or
                req.get('programme',{}).get('value',{}).get('id')!=pid or
                req.get('family')!=context['family'] or req.get('template')!=context['template'] or
                not _same(req.get('reference_calendar'),context['reference_calendar'])):
            _fail(path,'Unique exact per-ID fixed context proof required')
        controls=_source(q['fixed_controls'],path+'/fixed_controls')
        association=_source(q['association'],path+'/association')
        for name,actual in (('requirement',req),('controls',controls),
                            ('association',association),('qualification',qualification)):
            if not _same(actual,_resource(resources,'caller-water-'+name+'__'+pid)):
                _fail(path+'/'+name,'Whole independently locked resource differs')
        a=association['value']
        _exact(a,('programme','original_demand','service_definition','source_ruleset',
                  'fixed_controls','source_system_type','reference_calendar','evidence'),path+'/association/value')
        if not _same(a['fixed_controls'],controls):_fail(path+'/fixed_controls','Whole controls differ')
        evidence={'field_evidence':req['evidence'],'source_system_type':a['source_system_type'],
                  'fixed_controls':controls,'association':association}
        original=compile_requirement(a['programme'],a['service_definition'],a['source_ruleset'],evidence)
        if not _same(original,req) or not _same(a['original_demand'],req['original_demand']):
            _fail(path+'/requirement','Complete original source requirement differs')
        locator=req['programme']['locator']
        if not locator.startswith('/') or not locator[1:].isdigit():
            _fail(path+'/requirement/programme','Original record order locator required')
        order=(req['programme']['path'],int(locator[1:]))
        if source_order and order<=source_order[-1]:_fail(path,'Eligible proof pool source order/uniqueness differs')
        source_order.append(order);pool[pid]=qualification
    return group,pool


def _physical_result(instance,entry,clock):
    req=entry['chosen_requirement'];u=entry['unit'];sid=req['source_service_id']
    original=req['original_demand']['value']
    values=evaluate_rules(req['source_ruleset']['value'],clock['year'],clock['holidays'])['values']
    demand={'demand_id':sid,'slot':'hot_water_volume','quantity':'hot_water_volume',
            'value':original['value'],'unit':'m3/s/m2','basis':'floor_area',
            'fuel':'water','host':'building_service',
            'evidence':{'original_demand':copy.deepcopy(req['original_demand']),
                        'service_definition':copy.deepcopy(req['service_definition']),
                        'source_ruleset':copy.deepcopy(req['source_ruleset'])}}
    target=reference_budget(demand,values)
    _positive(target['total'],'/source_basis_target/total')
    whole=target['total']*u['floor_area_m2']
    _positive(whole,'/whole_input_target/total')
    extent={'value':u['floor_area_m2'],'unit':'m2','evidence':copy.deepcopy(u['area_evidence'])}
    whole_target={'quantity':'hot_water_volume','total':whole,'unit':'m3','basis':'absolute',
                  'derivation':'source_basis_target_times_extent'}
    descriptor={'demand_id':sid,'source_service_id':sid,'physical_id':u['physical_id'],
                'mode':'whole','ownership':'instantiate_once','extent':copy.deepcopy(extent),
                'source_basis_target':copy.deepcopy(target),'whole_input_target':copy.deepcopy(whole_target),
                'caller_unit_adaptation':{'kind':MODE,'source_geometry_departure':'caller_unit_area',
                    'building_realization_id':entry['building_realization_id'],'unit_id':u['unit_id'],
                    'unit_inventory_id':entry['unit_inventory_id'],
                    'unit_inventory_sha256':entry['unit_inventory_sha256'],
                    'water_authority_programme_id':u['water_authority_programme_id'],
                    'source_requirement':copy.deepcopy(req),
                    'source_system_type':req['source_system_type'],
                    'interpretation':'conserved_original_density_on_one_caller_unit'}}
    p=req['programme']['value']
    resolved={'recipe_id':'caller-water-'+req['requirement_id'],
        'source_family':p['source_family'],
        'source':{'source_id':sid,'building_type':req['family'],'template':req['template'],
                  'vintage':None,'evidence_view':req['programme_evidence_view'],'weather':None},
        'owner_kind':'physical_service','source_service_id':sid,'physical_id':u['physical_id'],
        'physical_binding_kind':MODE,'building_realization_id':entry['building_realization_id'],
        'unit_id':u['unit_id'],
        'slots':[{'slot':'hot_water_volume','source_schedule_id':req['source_ruleset']['value']['id'],
                  'unit':'fraction','kind':'load'}],
        'demands':[demand],'controls':[],'shared_services':[descriptor],
        'evidence':[{'source_requirement':copy.deepcopy(req),
                     'method':'source_fixed_apartment_dhw','source_controls':copy.deepcopy(entry['fixed_controls'])}],
        'inputs':dict(copy.deepcopy(instance['inputs']),year=clock['year'],holidays=copy.deepcopy(clock['holidays']),
                      reference_channels={'hot_water_volume':values},reference_budgets={sid:target},
                      companion_rules={},source_context={'case_id':'caller-water-'+req['requirement_id'],
                          'method':METHOD,'calendar':copy.deepcopy(clock),
                          'compiled_requirement':copy.deepcopy(req),
                          'fixed_controls':copy.deepcopy(entry['fixed_controls'])})}
    plan={'instance_key':instance['key'],'building_realization_id':entry['building_realization_id'],
          'unit_id':u['unit_id'],'physical_id':u['physical_id'],'source_service_id':sid,
          'source_basis_target':target,'extent':extent,'whole_input_target':whole_target,
          'chosen_requirement':copy.deepcopy(req)}
    return resolved,plan


def prepare_caller_water(params: dict, resolved_instances: list[tuple[dict,dict]],
                         resources: ResourceSet) -> dict:
    """Close source, static method pool, declaration and explicit owners before RNG."""
    if type(resources) is not ResourceSet:_fail('/resource_set_id','Verified ResourceSet required','requires_binding')
    clock=params.get('calendar')
    if not _same(clock,CALENDAR):_fail('/calendar','Only the qualified fixed 2007 source calendar is admitted','requires_binding')
    realizations={};used=set();units={};groups={};requirements={}
    for realization in params.get('building_realizations',[]):
        if realization.get('mode')!=MODE:continue
        building=realization['building_realization_id']
        if building in realizations:_fail('/building_realizations','Duplicate caller realization','shared_service_conflict')
        group,pool=_qualified_pool(resources,realization)
        available={pid:copy.deepcopy(q['value']['requirement']) for pid,q in pool.items()}
        inventory=resolve_caller_unit_inventory(realization,available)
        for entry in inventory.values():
            for pid in entry['unit']['programme_ids']:
                if not _qualified_caller_water_method(pool[pid]):
                    _fail('/method_qualification/'+pid,'Exact per-ID fixed method remains unqualified','requires_binding')
        realizations[building]=realization;groups[building]=group;requirements[building]=available
        units.update(inventory)
    caller_owner_keys={};program_claims={};claim_keys=set();legacy_sids=set();caller_sids=set()
    for instance,resolved in resolved_instances:
        kind=instance.get('physical_binding_kind')
        building=instance.get('building_realization_id');unit_id=instance.get('unit_id')
        if kind!=MODE and unit_id is None:
            if instance.get('owner_kind')=='physical_service':legacy_sids.add(instance.get('source_service_id'))
            continue
        if building not in realizations or (building,unit_id) not in units:
            _fail('/instances/'+instance['key'],'Caller owner/claim has no declared unit','requires_binding')
        used.add(building);entry=units[building,unit_id];u=entry['unit']
        if instance.get('operating_group') is not None:
            _fail('/instances/'+instance['key']+'/operating_group','Fixed water has null group','operating_group_conflict')
        bound=instance.get('basis_bindings',{})
        if (set(bound)!={'multiplicity','extents'} or type(bound['multiplicity']) not in (int,float) or
                bound['multiplicity']!=1 or set(bound['extents'])!={'floor_area'} or
                not _same(bound['extents']['floor_area'],{'value':u['floor_area_m2'],'unit':'m2','evidence':u['area_evidence']})):
            _fail('/instances/'+instance['key']+'/basis_bindings','Caller A/evidence/multiplicity differs','incompatible_basis')
        if instance.get('owner_kind')=='physical_service':
            if (kind!=MODE or instance.get('inputs')!={'water_method':METHOD,'source_geometry_departure':'caller_unit_area'} or
                    instance.get('physical_id')!=u['physical_id'] or instance.get('source_service_id')!=u['source_service_id']):
                _fail('/instances/'+instance['key'],'Physical caller owner differs from declaration','shared_service_conflict')
            if (building,unit_id) in caller_owner_keys:_fail('/instances/'+instance['key'],'Duplicate caller physical owner','shared_service_conflict')
            caller_owner_keys[building,unit_id]=instance['key'];caller_sids.add(u['source_service_id'])
        elif instance.get('owner_kind')=='program':
            pid=instance.get('program_id');req=requirements[building].get(pid)
            if pid not in u['programme_ids'] or req is None:
                _fail('/instances/'+instance['key'],'Programme independent water authority differs','source_integrity')
            claim=(building,unit_id,pid)
            if claim in claim_keys:
                _fail('/instances/'+instance['key'],'Duplicate same-unit programme water projection','shared_service_conflict')
            claim_keys.add(claim)
            verify_caller_water_programme(instance,resolved,req)
            program_claims[instance['key']]=(entry,req)
        else:_fail('/instances/'+instance['key'],'Caller unit owner kind unsupported','shared_service_conflict')
    if legacy_sids & caller_sids:
        _fail('/instances','Same SID across caller and other physical mode is ambiguous','shared_service_conflict')
    if set(realizations)!=used:_fail('/building_realizations','Unused caller realization','requires_binding')
    if set(caller_owner_keys)!=set(units):_fail('/instances','One explicit owner per independently declared unit required','requires_binding')
    owners=[];replaced=[]
    for instance,resolved in resolved_instances:
        if instance.get('physical_binding_kind')==MODE:
            entry=units[instance['building_realization_id'],instance['unit_id']]
            chosen=entry['water_authority_programme_id'];q=groups[instance['building_realization_id']]['value']['qualifications']
            entry['fixed_controls']=next(record['value']['fixed_controls'] for record in q if record['value']['programme_id']==chosen)
            actual,plan=_physical_result(instance,entry,clock);replaced.append((instance,actual));owners.append(plan)
        else:replaced.append((instance,resolved))
    projections=[{'instance_key':instance['key'],'building_realization_id':instance['building_realization_id'],
                  'unit_id':instance['unit_id'],'requirement':copy.deepcopy(program_claims[instance['key']][1])}
                 for instance,resolved in resolved_instances if instance['key'] in program_claims]
    receipts=[]
    for building,realization in realizations.items():
        selected=[];seen=set()
        for u in realization['unit_inventory']['units']:
            for pid in u['programme_ids']:
                if pid not in seen:selected.append(copy.deepcopy(requirements[building][pid]));seen.add(pid)
        receipts.append(dict(copy.deepcopy(realization),source_requirements=selected,
                             method_qualification=copy.deepcopy(groups[building])))
    return {'resolved_instances':replaced,'owners':owners,'projections':projections,
            'building_realizations':receipts}


def bind_caller_water(bundle: dict, plan: dict) -> None:
    """Close each emitted fixed source rule against one B, A and B×A owner."""
    owners={c['instance_key']:c for c in bundle['constituents']}
    if len(owners)!=len(bundle['constituents']):_fail('/constituents','Duplicate actual owner key','invalid_reference')
    bindings=bundle['bindings'];physical={}
    for entry in plan['owners']:
        key=entry['instance_key'];owner=owners.get(key);where='/constituents/'+key
        if owner is None:_fail(where,'Actual caller physical owner missing','invalid_reference')
        for field in ('building_realization_id','unit_id','physical_id','source_service_id'):
            if owner.get(field)!=entry[field]:_fail(where+'/'+field,'Physical owner identity differs','invalid_reference')
        if owner.get('physical_binding_kind')!=MODE or owner.get('owner_kind')!='physical_service':
            _fail(where,'Caller physical binding kind differs','invalid_reference')
        candidates=[i for i in owner['binding_indices'] if type(i) is int and 0<=i<len(bindings) and
                    bindings[i].get('kind')=='load' and bindings[i].get('slot')=='hot_water_volume']
        if len(candidates)!=1:_fail(where+'/binding_indices','Exactly one owned water binding required','invalid_reference')
        index=candidates[0];binding=bindings[index]
        for field in ('instance_key','building_realization_id','unit_id','physical_id',
                      'source_service_id','physical_binding_kind'):
            if binding.get(field)!=owner.get(field):_fail(where+'/binding_indices','Wrong owned water reference','invalid_reference')
        sid=binding['schedule_id'];req=entry['chosen_requirement']
        if (binding.get('demand_id')!=req['source_service_id'] or
                owner['schedule_ids'].get('hot_water_volume')!=sid or
                not _same(binding.get('reference_target'),entry['source_basis_target'])):
            _fail(where+'/binding_indices','Owned demand/target/schedule differs','invalid_reference')
        values=bundle['schedules'].get(sid,{}).get('values')
        source_values=evaluate_rules(req['source_ruleset']['value'],
                                     bundle['metadata']['calendar']['year'],
                                     bundle['metadata']['calendar'].get('holidays',[]))['values']
        if not _same(values,source_values):_fail(where+'/schedule_ids','Emitted water fraction differs from original fixed rule')
        expected=bind_budget(entry['source_basis_target'],values)
        if (not _same(expected['effective_magnitude'],binding.get('effective_magnitude')) or
                not _same(expected['scaling_receipt'],binding.get('scaling_receipt'))):
            _fail(where+'/binding_indices','Emitted effective density differs')
        descriptor=owner.get('shared_services')
        if not isinstance(descriptor,list) or len(descriptor)!=1:
            _fail(where+'/shared_services','One physical descriptor required')
        wanted={'demand_id':req['source_service_id'],'source_service_id':req['source_service_id'],
                'physical_id':entry['physical_id'],'mode':'whole','ownership':'instantiate_once',
                'extent':entry['extent'],'source_basis_target':entry['source_basis_target'],
                'whole_input_target':entry['whole_input_target']}
        if any(not _same(descriptor[0].get(k),v) for k,v in wanted.items()):
            _fail(where+'/shared_services','One B/A/W owner descriptor differs')
        adaptation=descriptor[0].get('caller_unit_adaptation')
        if (not isinstance(adaptation,dict) or adaptation.get('source_requirement')!=req or
                adaptation.get('water_authority_programme_id')!=req['programme']['value']['id'] or
                adaptation.get('source_system_type')!=req['source_system_type']):
            _fail(where+'/caller_unit_adaptation','Chosen original water authority differs')
        owner['generation']['water_method_receipt']={
            'method':METHOD,'random_draw_count':0,'operating_group':None,
            'consumed_input_fields':['compiled_requirement.original_demand','calendar',
                                     'resolved_caller_unit.floor_area_m2','compiled_requirement.source_ruleset'],
            'source_geometry_departure':'caller_unit_area'}
        reference={'binding_ref_kind':MODE,'instance_key':key,
                   'building_realization_id':entry['building_realization_id'],
                   'unit_id':entry['unit_id'],'physical_id':entry['physical_id'],
                   'source_service_id':entry['source_service_id'],'binding_index':index,
                   'demand_id':binding['demand_id'],'slot':'hot_water_volume','schedule_id':sid}
        physical[entry['building_realization_id'],entry['unit_id']]={'entry':entry,'reference':reference}
    for item in plan['projections']:
        key=item['instance_key'];owner=owners.get(key);where='/constituents/'+key
        if owner is None:_fail(where,'Actual programme view missing','invalid_reference')
        req=item['requirement'];physical_key=(item['building_realization_id'],item['unit_id'])
        parent=physical.get(physical_key)
        if parent is None:_fail(where+'/service_set_projections','Caller physical owner missing','invalid_reference')
        if (owner.get('owner_kind')!='program' or owner.get('program_id')!=req['programme']['value']['id'] or
                owner.get('building_realization_id')!=item['building_realization_id'] or
                owner.get('unit_id')!=item['unit_id'] or
                req not in owner.get('required_service_sets',[]) or
                any(d.get('slot')=='hot_water_volume' for d in owner.get('demands',[])) or
                'hot_water_volume' in owner.get('schedule_ids',{})):
            _fail(where,'Alternative programme owns or changes fixed water','shared_service_conflict')
        if owner.get('service_set_projections'):
            _fail(where+'/service_set_projections','Duplicate non-owning water projection','shared_service_conflict')
        source=parent['entry'];actual=source['source_basis_target'];original=req['original_demand']['value']
        values=evaluate_rules(req['source_ruleset']['value'],bundle['metadata']['calendar']['year'],
                              bundle['metadata']['calendar'].get('holidays',[]))['values']
        demand={'quantity':'hot_water_volume','value':original['value'],'unit':original['unit'],
                'basis':original['basis'],'fuel':'water','host':'building_service',
                'evidence':{'original_demand':req['original_demand']}}
        independent=reference_budget(demand,values)
        if (independent['total']!=actual['total'] or
                not math.isclose(source['whole_input_target']['total'],
                                 independent['total']*source['extent']['value'],rel_tol=1e-12)):
            _fail(where+'/service_set_projections','Original alternative B/A/W differs')
        owner['service_set_projections']=[{
            'projection_kind':'caller_unit_density','programme_instance_key':key,
            'requirement_id':req['requirement_id'],
            'building_realization_id':item['building_realization_id'],'unit_id':item['unit_id'],
            'unit_inventory_id':owners[source['instance_key']]['shared_services'][0]['caller_unit_adaptation']['unit_inventory_id'],
            'unit_inventory_sha256':owners[source['instance_key']]['shared_services'][0]['caller_unit_adaptation']['unit_inventory_sha256'],
            'physical':copy.deepcopy(parent['reference']),'denominator':copy.deepcopy(source['extent']),
            'projected_target':{'target_kind':'canonical_programme_density','quantity':'hot_water_volume',
                                'total':independent['total'],'unit':'m3/m2','basis':'floor_area'},
            'whole_input_target':{'quantity':'hot_water_volume','total':source['whole_input_target']['total'],
                                  'unit':'m3','basis':'absolute',
                                  'derivation':'sum_unique_physical_whole_input_targets'},
            'interpretation':'caller_unit_area_adaptation_of_original_fixed_dhw_density'}]
    bundle['metadata'].setdefault('building_realizations',[]).extend(copy.deepcopy(plan['building_realizations']))
