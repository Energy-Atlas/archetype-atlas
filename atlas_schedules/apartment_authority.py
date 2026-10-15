"""Independent apartment scientific roots, pure reconstruction and resource seam."""
import copy
import hashlib

from .authority_types import _exact, _source_object, _field_evidence
from .canonical import canonical
from .errors import GeneratorError
from .resources import ResourceSet
from . import apartment_authority_pins as pins

BASE='data/schedule-generator/apartment/'
AUTH=BASE+'authority/'
CALENDAR={'year':2007,'clock':'local_standard_time','holidays':[]}
SELECTED='unit_occupancy_interior_lighting'
FIXED='source_fixed_apartment_programme'


def _fail(path,message,code='source_integrity'):
    raise GeneratorError(code,path,message)


def _same(a,b):return canonical(a)==canonical(b)


def _hash(value):return hashlib.sha256(canonical(value)).hexdigest()


def artifact(name,value):
    return {'path':AUTH+name+'.json','sha256':_hash(value),'locator':'/','value':copy.deepcopy(value)}


def field(source,note):
    return {'source_revision':'apartment-reviewed-A1-A3', 'source_path':source['path'],
        'source_sha256':source['sha256'],'locator':source['locator'],
        'original_value':copy.deepcopy(source['value']),'original_unit':None,
        'transformation':'Whole independently retained original/derived association; no source operand replacement',
        'extraction_date':'2026-10-15','interpretation_note':note}


def _root(source,path):
    _source_object(source,path)
    if source['locator']!='/' or source['sha256']!=_hash(source['value']):
        _fail(path,'Exact canonical root preimage required')
    return source['value']


def _original(source,path):
    _source_object(source,path)
    key=(source['path'],source['sha256'],source['locator'])
    if pins.ORIGINAL_PINS.get(key)!=_hash(source['value']):
        _fail(path,'Whole original body/path/file revision/locator differs from reviewed scientific root')
    return source['value']


def _scientific(source,path):
    _source_object(source,path)
    expected=pins.SCIENTIFIC_FILES.get(source['path'])
    if (expected is None or source['locator']!='/' or source['sha256']!=expected['sha256'] or
            _hash(source['value'])!=expected['canonical_value_sha256']):
        _fail(path,'Independent reviewed A1 scientific file/body differs')
    return source['value']


def validate_fixed_resource(key,value):
    expected=pins.FIXED_RESOURCES.get(key)
    if expected is None or _hash(value)!=expected['sha256']:
        _fail('/method_qualification/'+key,'Exact independently reviewed A3 whole resource differs','requires_binding')
    if set(value)=={'path','sha256','locator','value'}:
        _source_object(value,'/method_qualification/'+key)
        file=pins.FIXED_FILES[key]
        preimage=value['value'] if value['locator']=='/' else {'native_control_schedules':value['value']}
        if (value['path']!=file['source_path'] or value['sha256']!=file['sha256'] or
                value['sha256']!=_hash(preimage)):
            _fail('/method_qualification/'+key,'Pinned complete derived preimage differs','requires_binding')
    return value


def _ids(value):
    if isinstance(value,dict):
        found={value['evidence_id']} if isinstance(value.get('evidence_id'),str) else set()
        for child in value.values():found.update(_ids(child))
        return found
    if isinstance(value,list):return set().union(*(_ids(x) for x in value)) if value else set()
    return set()


def compile_original_apartment_recipe(originals: dict) -> dict:
    from .apartment_recipes import compile_recipes, _water_evidence, CONTROL_SLOTS
    from .caller_unit_water import _compile_requirement
    value=_root(originals,'/apartment/original_sources')
    _exact(value,('programme','source_row','schedules','field_evidence','source_files',
                  'service_definition','water_helpers'),'/apartment/original_sources/value')
    p=_original(value['programme'],'/apartment/programme');pid=p['id']
    row=next((r for r in pins.SCOPE_ROWS if r['id']==pid),None)
    if row is None:_fail('/program_id','Programme is outside exact reviewed apartment scope')
    _original(value['source_row'],'/apartment/source_row')
    def objects(name):
        sequence=value[name]
        if not isinstance(sequence,list):_fail('/apartment/'+name,'Original source list required')
        result={}
        for obj in sequence:
            v=_original(obj,'/apartment/'+name)
            if v['id'] in result:_fail('/apartment/'+name,'Duplicate original source identity')
            result[v['id']]=obj
        return result
    schedules=objects('schedules');evidence=objects('field_evidence');files=objects('source_files')
    sids=list(dict.fromkeys([l['schedule_id'] for l in p['loads'] if l['schedule_id']]+[
        v['value'] for k,v in p['parameters'].items() if k in CONTROL_SLOTS and v['status']=='known']))
    if list(schedules)!=sids:_fail('/apartment/schedules','Complete original rule order/coverage differs')
    eids=set(p['evidence_ids'])|_ids(p)
    for obj in schedules.values():
        rule=obj['value'];eids.update([rule['provenance_id']] if 'provenance_id' in rule else rule['evidence_ids'])
    if (set(evidence)!=eids or list(evidence.values())!=sorted(evidence.values(),key=lambda o:int(o['locator'][1:]))):
        _fail('/apartment/field_evidence','Complete original provenance order/coverage differs')
    fids={e['value']['source_file_id'] for e in evidence.values() if e['value']['source_file_id'] is not None}
    if set(files)!=fids or list(files.values())!=sorted(files.values(),key=lambda o:int(o['locator'][1:])):
        _fail('/apartment/source_files','Complete original source-file metadata differs')
    first=evidence[p['loads'][0]['evidence_id']]['value'];sourcefile=files[first['source_file_id']]['value']
    raw=value['source_row']
    if (raw['path']!='data/raw/openstudio-standards/'+sourcefile['path'] or raw['sha256']!=sourcefile['sha256'] or
            raw['locator']!=first['locator'].rsplit('/',1)[0]):
        _fail('/apartment/source_row','Exact per-ID original row association differs')
    records={'programmes':{pid:value['programme']},'requirements':{},
             'source_objects':{'schedules':schedules,'field_evidence':evidence,'raw_rows':{pid:value['source_row']}}}
    if row['role']=='dwelling':
        service=value['service_definition'];s=_original(service,'/apartment/service_definition')
        if p['service_ids']!=[s['id']]:_fail('/apartment/service_definition','Original service differs')
        helpers=value['water_helpers']
        if not isinstance(helpers,list) or len(helpers)!=2:_fail('/apartment/water_helpers','Both original helpers required')
        for helper in helpers:_original(helper,'/apartment/water_helpers')
        demand=next(l for l in p['loads'] if l['quantity']=='hot_water_volume')
        proof=_water_evidence(value['programme'],service,schedules[demand['schedule_id']],value['source_row'],helpers)
        records['requirements'][pid]=_compile_requirement(value['programme'],service,schedules[demand['schedule_id']],proof)
    elif value['service_definition'] is not None or value['water_helpers']!=[]:
        _fail('/apartment/service_definition','Common fixed programme has no dwelling water authority')
    return compile_recipes(records,{'programmes':[row],'timing_domain':pins.TIMING_DOMAIN})['program',pid]


def _timing(source):
    value=_root(source,'/apartment/selected_timing')
    if source['path']!=AUTH+'apartment-selected-timing.json':_fail('/apartment/selected_timing','Exact timing artifact required')
    _exact(value,('method','reference_calendar','domain','parity_receipt','source_lock','timing_lock',
                  'residential_resources','dependency_cut','evidence'),'/apartment/selected_timing/value')
    for key in ('domain','parity_receipt','source_lock','timing_lock','dependency_cut'):
        _scientific(value[key],'/apartment/selected_timing/'+key)
    lock=value['timing_lock']['value'];domain=value['domain']['value']
    if (value['method']!=SELECTED or not _same(value['reference_calendar'],CALENDAR) or
            not _same(value['residential_resources'],lock['residential_resources']) or
            not _same([{k:x[k] for k in pins.LOCATIONS[0]} for x in domain['locations']],pins.LOCATIONS)):
        _fail('/apartment/selected_timing','Reviewed complete selected domain/source identities differ')
    _field_evidence(value['evidence'],'/apartment/selected_timing/evidence')
    return value


def qualification_value(pid,originals,recipe,fixed,timing):
    return {'programme_id':pid,'original_sources':copy.deepcopy(originals),'compiled_recipe':copy.deepcopy(recipe),
        'fixed_programme':copy.deepcopy(fixed),'selected_timing':copy.deepcopy(timing),
        'reference_calendar':copy.deepcopy(CALENDAR),
        'evidence':[field(originals,'Whole independently pinned original source closure'),
                    field(recipe,'Entire executable recompiled from original source closure'),
                    field(fixed,'Actual reviewed A3 fixed Ruleset/control proof; selected timing separate')]}


def validate_apartment_authority(program_id: str,record: dict,qualification: dict) -> dict:
    q=_root(qualification,'/apartment/method_qualification')
    _exact(q,('programme_id','original_sources','compiled_recipe','fixed_programme','selected_timing',
              'reference_calendar','evidence'),'/apartment/method_qualification/value')
    if program_id not in pins.PROGRAMME_IDS or q['programme_id']!=program_id:
        _fail('/program_id','Exact reviewed per-ID apartment authority required','requires_binding')
    if qualification['path']!=AUTH+'apartment-programme-qualification__'+program_id+'.json':
        _fail('/apartment/method_qualification','Foreign qualification artifact')
    original=q['original_sources'];expected=compile_original_apartment_recipe(original)
    if original['path']!=AUTH+'apartment-originals__'+program_id+'.json':_fail('/apartment/original_sources','Foreign original closure')
    r=_root(q['compiled_recipe'],'/apartment/compiled_recipe')
    if (q['compiled_recipe']['path']!=AUTH+'apartment-programme-recipe__'+program_id+'.json' or
            not _same(record,expected) or not _same(r,expected)):
        _fail('/apartment/compiled_recipe','Entire executable differs from independently reconstructed originals')
    fixed=validate_fixed_resource('apartment-fixed-programme__'+program_id,q['fixed_programme'])
    if not _same(fixed['value']['programme'],original['value']['programme']):_fail('/apartment/fixed_programme','Whole original programme differs')
    method=expected['recipe']['source_context']['method']
    if method==SELECTED:_timing(q['selected_timing'])
    elif q['selected_timing'] is not None:_fail('/apartment/selected_timing','Common fixed programme has no timing actor')
    wanted=qualification_value(program_id,original,q['compiled_recipe'],fixed,q['selected_timing'])
    if not _same(q,wanted):_fail('/apartment/method_qualification','Complete deterministic authority association differs')
    return q


def resolve_apartment_authority(program_id: str,record: dict,resources: ResourceSet) -> dict:
    if type(resources) is not ResourceSet:_fail('/resource_set_id','Actual verified ResourceSet required','requires_binding')
    try:
        qualification=resources.get('reference','apartment-programme-qualification__'+program_id)
        q=validate_apartment_authority(program_id,record,qualification)
        for name,key in (('original_sources','apartment-originals__'+program_id),
                         ('compiled_recipe','apartment-programme-recipe__'+program_id),
                         ('fixed_programme','apartment-fixed-programme__'+program_id)):
            if not _same(q[name],resources.get('reference',key)):_fail('/apartment/'+name,'Whole independent resource differs')
        if q['selected_timing'] is not None and not _same(q['selected_timing'],resources.get('reference','apartment-selected-timing')):
            _fail('/apartment/selected_timing','Independent timing resource differs')
        if q['selected_timing'] is not None:
            for key,sha in q['selected_timing']['value']['residential_resources'].items():
                if _hash(resources.get('residential',key))!=sha:
                    _fail('/residential/'+key,'Actual selected scientific source record differs')
        if not _same(record,resources.get('program',program_id)):_fail('/apartment/compiled_recipe','Actual executable differs')
        return qualification
    except GeneratorError as error:
        if error.code=='missing_resource':
            raise GeneratorError('requires_binding',error.path,'Independent apartment authority is missing') from error
        raise


def candidate(record):
    if not isinstance(record,dict):_fail('/program_id','Whole executable record required','requires_binding')
    definition=record.get('definition');recipe=record.get('recipe')
    context=recipe.get('source_context') if isinstance(recipe,dict) else None
    return (isinstance(definition,dict) and definition.get('id') in pins.PROGRAMME_IDS or
            isinstance(context,dict) and context.get('method') in {SELECTED,FIXED})


def reconstruct_apartment_programme(inputs: dict,record: dict,qualification: dict) -> dict:
    from .programs import _validate_apartment_recipe_inputs,_prepare_program_record
    pid=record.get('definition',{}).get('id')
    validate_apartment_authority(pid,record,qualification)
    _validate_apartment_recipe_inputs(inputs,record)
    resolved=_prepare_program_record(inputs,record,'compiled')
    resolved['program_id']=pid
    context=resolved['inputs']['source_context']
    context.update(case_id='apartment-'+pid,apartment_qualification=copy.deepcopy(qualification))
    resolved['evidence'].append({'apartment_qualification':copy.deepcopy(qualification)})
    return resolved


def bind_apartment_unit_context(instance: dict,resolved: dict) -> None:
    """Retain prototype design people separately from the caller's chain cohort."""
    context=resolved['inputs']['source_context']
    if context['method']!=SELECTED:return
    if (instance.get('owner_kind')!='program' or not isinstance(instance.get('building_realization_id'),str) or
            not instance['building_realization_id'] or not isinstance(instance.get('unit_id'),str) or not instance['unit_id']):
        _fail('/building_realization_id','Selected method requires actual declared unit identity','requires_binding')
    bound=instance.get('basis_bindings',{});area=bound.get('extents',{}).get('floor_area')
    if (bound.get('multiplicity')!=1 or not isinstance(area,dict) or area.get('unit')!='m2' or
            type(area.get('value')) not in (int,float) or area['value']<=0 or not area.get('evidence')):
        _fail('/basis_bindings','Independent evidenced unit floor area is required','requires_binding')
    envelope=area['evidence']
    _exact(envelope,('field_evidence',),'/basis_bindings/extents/floor_area/evidence')
    _field_evidence(envelope['field_evidence'],'/basis_bindings/extents/floor_area/evidence/field_evidence')
    resolved.update(owner_kind='program',building_realization_id=instance['building_realization_id'],unit_id=instance['unit_id'])
    q=context['apartment_qualification']['value'];p=q['original_sources']['value']['programme']['value']
    load=next(l for l in p['loads'] if l['quantity']=='occupancy')
    proof=next(c['evidence'] for c in resolved['controls'] if c['slot']=='occupants')
    receipt={'method':'prototype_temporal_adaptation','reference_design_people':load['value']*area['value'],
        'chain_residents':resolved['inputs']['N'],'source_density':{
            'original_load':copy.deepcopy(load),'field_evidence':copy.deepcopy(proof['field_evidence'])},
        'area':copy.deepcopy(area)}
    context['prototype_temporal_adaptation']=receipt
    proof['prototype_temporal_adaptation']=copy.deepcopy(receipt)
    resolved['evidence'].append({'prototype_temporal_adaptation':copy.deepcopy(receipt)})


def reconstruct_apartment_owner(owner: dict) -> dict:
    context=owner['generation'].get('source_inputs',{})
    q=context.get('apartment_qualification')
    if q is None:_fail('/constituents/'+owner['instance_key'],'Whole apartment qualification required')
    record=q['value']['compiled_recipe']['value']
    resolved=reconstruct_apartment_programme(owner['inputs'],record,q)
    bind_apartment_unit_context(owner,resolved)
    return resolved
