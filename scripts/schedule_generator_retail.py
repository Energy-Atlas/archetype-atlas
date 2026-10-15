"""Development extraction for the exact source-qualified RetailStandalone family."""
import copy
import gzip
import hashlib
import zipfile

from atlas_schedules.errors import GeneratorError
from atlas_schedules.canonical import canonical
from atlas_schedules.resources import strict_json
from scripts.common import ROOT
from scripts.schedule_generator_families import recover_commercial_closure
from scripts.schedule_generator_sources import compile_member,_verify


def validate_programme_observation(given,observed):
    """Tie native People topology/geometry and actual source schedules to inputs."""
    def fail():raise GeneratorError('source_integrity','retail-programme/'+given['case_id'],
        'Actual native People topology/geometry/source/operating association differs')
    if (any(given[field]!=observed[field] for field in ('case_id','operating','source_context','schedules')) or
            observed['source_reference_geometry']!=given['geometry_receipt']):fail()
    scope=given['source_context']['occupancy_aggregation']['source_model_scope']
    original=scope['original_people_inventory'];actual=observed['actual_people']
    if (len(actual)!=len(original) or observed['native_people_object_count']!=scope['native_people_object_count'] or
            observed['source_space_order']!=scope['native_sorted_space_order']):fail()
    handle='native_people_object_handle'
    for i,(a,b) in enumerate(zip(actual,original)):
        if any(a.get(k)!=v for k,v in b.items() if k!=handle) or (a[handle] is None)!=(b[handle] is None):fail()
        for j in range(i):
            if (a[handle]==actual[j][handle])!=(b[handle]==original[j][handle]):fail()


def load_programme_reference():
    """Actual 336-case native evidence with explicit compressed/raw byte closure."""
    from scripts.schedule_generator_native_codec import decode_native_component
    lock=strict_json((ROOT/'sources/schedule-generator-retail-programme-reference-lock.json').read_bytes(),'retail-programme-lock')
    if lock.get('source_gate_status')!='native_programme_capture_complete_public_family_certification_pending':
        raise GeneratorError('source_integrity','retail-programme','Exact native qualification boundary required')
    component={'reference_resource_key':'retail-programme-native-lock','lock':lock,
        'reference_resource_sha256':hashlib.sha256(canonical(lock)).hexdigest()}
    result={'lock':lock}
    for kind in ('inputs','vectors'):
        entry=lock[kind]
        payload=decode_native_component((ROOT/entry['source_path']).read_bytes(),component,kind)
        result[kind]=strict_json(payload,'retail-programme-'+kind)
    given=result['inputs'];native=result['vectors']['cases']
    keys=[c['case_id'] for c in given];actual=[c['case_id'] for c in native]
    if len(keys)!=336 or len(set(keys))!=336 or actual!=keys:
        raise GeneratorError('source_integrity','retail-programme','Exact ordered 336 native/input associations required')
    if (len({c['source_case']['program_id'] for c in given})!=64 or
            len({c['source_case']['configuration_id'] for c in given})!=10 or
            sum(bool(c['source_member_receipt']) for c in given)!=116):
        raise GeneratorError('source_integrity','retail-programme','Exact programme/configuration/parent-member scope required')
    for expected,observed in zip(given,native):
        validate_programme_observation(expected,observed)
    return result


def compile_sampling_records():
    """Exact eleven source records: one retail audit and ten raw conditional tables."""
    lock=strict_json((ROOT/'sources/schedule-generator-warehouse-lock.json').read_bytes(),'prior-source-lock')
    audit=recover_commercial_closure(lock,'retail')
    records={('commercial','retail__sampling-audit'):audit}
    source=next(a for a in lock['archives'] if a['source_id']=='comstock' and a['format']=='zip')
    archive_path=ROOT/'data/raw'/source['cache_path'];_verify(archive_path.read_bytes(),source)
    with zipfile.ZipFile(archive_path) as archive:
        for entry in source['members']:
            if entry['kind']!='commercial' or entry.get('fixed_selectors',{}).get('building_type')!='retail':continue
            blob=archive.read(entry['path']);_verify(blob,entry)
            records['commercial',entry['key']]=compile_member(blob,entry,source)
    if len(records)!=11:raise GeneratorError('source_integrity','retail','Exact ten-table closure and one audit required')
    return records


def load_context_reference():
    """Actual native context evidence; local programme qualification is separate."""
    lock=strict_json((ROOT/'sources/schedule-generator-retail-context-reference-lock.json').read_bytes(),'retail-context-lock')
    if lock.get('source_gate_status')!='native_context_passed_programme_family_pending':
        raise GeneratorError('source_integrity','retail-context','Exact native qualification boundary required')
    result={'lock':lock}
    for kind in ('inputs','vectors'):
        entry=lock[kind];blob=(ROOT/entry['source_path']).read_bytes();_verify(blob,entry)
        payload=gzip.decompress(blob)
        if len(payload)!=entry['payload_size_bytes'] or hashlib.sha256(payload).hexdigest()!=entry['payload_sha256']:
            raise GeneratorError('source_integrity','retail-context','Actual native input/output payload differs')
        result[kind]=strict_json(payload,'retail-context-'+kind)
    given={c['case_id']:c for c in result['inputs']['cases']};native=result['vectors']['cases']
    if len(given)!=20 or len(native)!=20 or len({c['case_id'] for c in native})!=20 or set(given)!={c['case_id'] for c in native}:
        raise GeneratorError('source_integrity','retail-context','Exact twenty native/source input keys required')
    configs=set();fixtures=0
    for actual in native:
        expected=given[actual['case_id']];config=actual['configuration_id'];configs.add(config)
        if (any(actual[f]!=expected[f] for f in ('configuration_id','template','evidence_view','operating','adaptation','parametric_apply')) or
                expected['parametric_apply']!={'error_on_out_of_order':False,'source_method':'create_typical.rb:766'} or
                expected['master_seed'] not in {42,51}):
            raise GeneratorError('source_integrity','retail-context/'+actual['case_id'],'Actual source/view/native operands differ')
        if actual['source_service_id'] is not None:
            fixtures+=1
            if (expected['physical_service']['id']!=actual['source_service_id'] or
                    actual['registration']['count']!=1 or actual['registration']['fixture_count']!=1):
                raise GeneratorError('source_integrity','retail-context/'+actual['case_id'],'Actual physical Main/source registration differs')
    if configs!=set(lock['configuration_ids']) or len(configs)!=10 or fixtures!=12:
        raise GeneratorError('source_integrity','retail-context','Exact ten contexts/twelve physical observations required')
    return result


def program_cases():
    """All64 exact original identities, kept in frozen definition order."""
    from scripts.schedule_generator_build import _receipt
    captured=load_context_reference();contexts=captured['inputs']['cases']
    definitions=strict_json((ROOT/'data/definition-releases/v0.1.1/programs.json').read_bytes(),'programs')
    cases=[]
    for i,p in enumerate(definitions):
        if p['building_type']!='RetailStandalone':continue
        given=next(c for c in contexts if c['template']==p['template'] and c['evidence_view']==p['evidence_view'])
        config=given['configuration_id']
        cases.append({'case_id':'C6-'+p['id'],'program_id':p['id'],'building_type':p['building_type'],
            'name':p['name'],'template':p['template'],'vintage':None,'evidence_view':p['evidence_view'],
            'climate':p['climate'],'configuration_id':config,
            'program_definition':_receipt('data/definition-releases/v0.1.1/programs.json','/'+str(i),'Exact original Retail source/view identity'),
            'configuration':{'sampling_configuration_id':'retail_90_1_2013','conditioning_inputs':{'building_type':'retail'},
                'source_hoo_configuration_id':config,'program_definition_pointer':'/'+str(i),
                'interpretation':'Exact original selected-view source SpaceType People/geometry/native HOO; no inferred caller geometry or population'},
            'weather':{'mode':'not_used','interpretation':'Exact selected native interior/water methods and audited ten-table closure have no weather operand'},
            'source_gate_status':'requires_native_programme_certification'})
    if len(cases)!=64:raise GeneratorError('source_integrity','retail-cases','Exactly64 original programmes required')
    return cases


def program_source_context(case):
    """Literal original native SpaceType People operands in source-space order."""
    captured=load_context_reference();config=case['configuration_id']
    given=next(c for c in captured['inputs']['cases'] if c['configuration_id']==config)
    native=next(c for c in captured['vectors']['cases'] if c['case_id']==given['case_id'])
    inventory=copy.deepcopy(native['native_people']);parts=[]
    for person in inventory:
        if person['nominal_people']==0:continue
        selected=next(p for p in given['source_people'] if p['space_name']==person['space_name'])
        parts.append({'schedule':copy.deepcopy(selected['schedule']),'nominal_people':person['nominal_people'],
            'residential':person['residential'],'source_space_name':person['space_name'],'program_id':person['program_id'],
            'source_program_id':person['source_program_id'],'source_floor_area_m2':person['floor_area_m2'],
            'source_multiplier':person['multiplier'],'source_density_person_m2':person['source_density_person_m2'],
            'evidence':{'source_people_definition':copy.deepcopy(person['source_definition']),
                'source_people_field':copy.deepcopy(person['source_field_evidence']),
                'native_nominal_people':person['nominal_people'],'native_people_object_handle':person['native_people_object_handle'],
                'source_geometry':copy.deepcopy(given['geometry_receipt']),
                'native_context':{'resource_kind':'reference','resource_key':'retail-context-native-lock',
                    'source_path':captured['lock']['vectors']['source_path'],'payload_sha256':captured['lock']['vectors']['payload_sha256'],
                    'case_id':native['case_id'],'interpretation':'Original c8 source SpaceType/inherited-schedule factory; this per-space occurrence retains its shared source People identity'}}})
    scope=dict(copy.deepcopy(given['adaptation']),model_family='RetailStandalone',original_people_inventory=inventory,
        native_people_object_count=native['native_people_object_count'],native_sorted_space_order=copy.deepcopy(native['source_space_order']))
    caller=next(e for e in captured['lock']['source_runtime_primary_dependency_receipts']['files'] if e['path']=='source/create_typical.rb')
    context={'method':'prototype_budget_preserving_commercial_hybrid','case_id':case['case_id'],'year':2007,'holidays':[],
        'steps_per_hour':6,'standards_version':'0.8.6','configuration_id':config,'source_hoo_configuration_id':config,
        'slot_sources':{},'slot_modes':{},
        'occupancy_aggregation':{'policy':'explicit_source_model_nonresidential_people','source_hoo_configuration_id':config,
            'evidence_view':given['evidence_view'],'constituents':parts,'source_model_scope':scope,
            'interpretation':'Actual sorted source-space People occurrences; shared SpaceType objects retained; one shared Ruleset weighted-hour round6, no extra multiplier'},
        'occupancy_adjustment':{'peak_occ_frac':.231,'source_key':'comstock__resources__options_lookup_tsv',
            'source_options':['baseline_hvac_sizing=autosize','baseline_hvac_sizing=hardsize']},
        'source_clock':{'TZ':'UTC','variant':'controlled_no_DST_local_standard_calendar'},
        'parametric_apply':dict(copy.deepcopy(given['parametric_apply']),source_member=copy.deepcopy(caller)),
        'configuration_association':{'conditioning_inputs':{'building_type':'retail'},'source_hoo_configuration_id':config,
            'evidence_view':given['evidence_view'],'interpretation':'Exact selected-view prototype HOO adaptation, not original stock/whole-prototype equivalence'}}
    return {'configuration_id':config,'source_hoo_configuration_id':config,
            'carrier_policy':'explicit_source_model_nonresidential_people'},context


def compile_program_records():
    """Development qualification records; no inherited certificate or runtime support claim."""
    from atlas_schedules.resources import ResourceSet
    from scripts.schedule_generator_build import compile_recipes,_receipt
    manifest=strict_json((ROOT/'atlas_schedules/data/manifest.json').read_bytes(),'base-manifest')
    base=ResourceSet(ROOT/'atlas_schedules/data',manifest['resource_set_id'])
    records={(e['kind'],e['key']):base.get(e['kind'],e['key']) for e in manifest['resources']}
    records.update(compile_sampling_records())
    records.update(compile_service_records())
    captured=load_context_reference();records['reference','retail-context-native-lock']=captured['lock']
    ruby=strict_json((ROOT/'sources/schedule-generator-ruby-float-lock.json').read_bytes(),'ruby-lock')['sources'][0]
    content=(ROOT/ruby['source_path']).read_bytes();_verify(content,ruby)
    records['reference','ruby-float-numeric-c']={'text':content.decode('utf-8'),'provenance':ruby}
    definitions=strict_json((ROOT/'data/definition-releases/v0.1.1/programs.json').read_bytes(),'programs')
    by_id={p['id']:p for p in definitions};cases=program_cases()
    for case in cases:
        definition=by_id[case['program_id']]
        if definition['service_ids'] or any(l['quantity']=='hot_water_volume' for l in definition['loads']):
            raise GeneratorError('source_integrity',case['program_id'],'Unallocated physical Main cannot become a programme alias')
        records['program',case['program_id']]={'definition':copy.deepcopy(definition),'case':copy.deepcopy(case),
            'provenance':copy.deepcopy(case['program_definition'])}
    compositions=strict_json((ROOT/'data/definition-releases/v0.1.1/compositions.json').read_bytes(),'compositions')
    for i,c in enumerate(compositions):
        if c['building_type']=='RetailStandalone':records['composition',c['id']]={'definition':copy.deepcopy(c),
            'provenance':_receipt('data/definition-releases/v0.1.1/compositions.json','/'+str(i),'Exact original ordered Retail members/represented areas; model allocation ratios, not population weights')}
    scope={'milestone_id':'C6-Retail-programme-qualification','scope_version':'1.0.0','calendar':{'year':2007},'cases':cases,
        'service_cases':service_cases(records)}
    compile_recipes(records,scope)
    for case in cases:
        recipe=records['program',case['program_id']]['recipe']
        if 'source_composition' in recipe:
            config=case['configuration_id']
            recipe['bound_inputs']={'configuration_id':config,'source_hoo_configuration_id':config,'carrier_policy':'actual_generated_source_constituents'}
            recipe['required_inputs']=['year',*recipe['bound_inputs'],'composition_basis_mode']
        recipe.update(required_contract_version='1.1.0',required_service_links=[],calendar_year_locked=True)
    records['reference','m1-scope']=scope
    return records


def fixed_native_operands(captured):
    from scripts.schedule_generator_service_build import fixed_control_projection
    cases=[]
    for i,native in enumerate(captured['vectors']['cases']):
        if native['source_service_id'] is None:continue
        cases.append({'case_id':native['case_id'],'source_hoo_configuration_id':native['configuration_id'],
            'source_service_id':native['source_service_id'],
            'controls':{name:fixed_control_projection(control,'/cases/'+str(i)+'/controls/'+name)
                for name,control in native['controls'].items()}})
    return {'schema_version':'1.0.0','method':'literal_native_fixed_operand_projection',
        'source_capture':copy.deepcopy(captured['lock']['vectors']),'cases':cases,
        'interpretation':'Actual constant-profile/getter operands; complete native arrays remain separately packaged once, never a receipt-only numerical oracle'}


def validate_fixed_native_operands(projection,captured):
    if projection!=fixed_native_operands(captured):
        raise GeneratorError('source_integrity','retail-fixed-native-operands','Actual native control/body/pointer/array differs')


def compile_service_records():
    """Three unallocated absolute source Mains, exactly six allowed view cases."""
    from scripts.schedule_generator_build import _receipt
    from scripts.schedule_generator_service_build import native_water_companions,CONTROL_SLOTS
    captured=load_context_reference();given={c['case_id']:c for c in captured['inputs']['cases']}
    definitions=strict_json((ROOT/'data/definition-releases/v0.1.1/services.json').read_bytes(),'services')
    projection=fixed_native_operands(captured);records={('reference','retail-fixed-native-operands'):projection}
    for i,definition in enumerate(definitions):
        if definition['building_type']!='RetailStandalone':continue
        sid=definition['id'];load=definition['load']
        if definition['beneficiary_program_ids'] or load['basis']!='absolute':
            raise GeneratorError('source_integrity',sid,'Exact unallocated absolute source Main required')
        provenance=_receipt('data/definition-releases/v0.1.1/services.json','/'+str(i),'Exact original unallocated Retail Main; one source fixture, no Sales/General allocation')
        evidence={'definition':copy.deepcopy(provenance),'original_service':copy.deepcopy(definition),
            'native_output_sha256':captured['lock']['vectors']['payload_sha256'],
            'source_fixture_method':{'source_revision':'c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907',
                'source_locator':'Standards.ServiceWaterHeating.rb:112-121; create_water_use.rb:38-80',
                'interpretation':'Original absolute main branch passes no space/area/multiplier; volume is not heater energy'}}
        configurations={}
        for native_index,native in enumerate(captured['vectors']['cases']):
            if native['source_service_id']!=sid or native['configuration_id'] in configurations:continue
            g=given[native['case_id']];config=native['configuration_id']
            _,context=program_source_context({'configuration_id':config,'case_id':'C6-'+sid+'__'+config})
            context.update(slot_sources={'hot_water_volume':copy.deepcopy(g['water_schedule'])},slot_modes={'hot_water_volume':'hours'})
            projected_index=next(j for j,c in enumerate(projection['cases']) if c['case_id']==native['case_id'])
            temperature={'value':g['prototype_row']['main_water_use_temperature'],'unit':'F',
                'source_field':'main_water_use_temperature','source_receipt':copy.deepcopy(g['source_prototype_receipt']),
                'interpretation':'Actual absolute Main prototype operand; no absolute-to-booster inference'}
            companion=native_water_companions(definition,native['controls'],temperature,evidence,
                {'source_native_prefix':'/cases/'+str(native_index)+'/controls',
                 'projection_resource_key':'retail-fixed-native-operands',
                 'projection_prefix':'/cases/'+str(projected_index)+'/controls','vectors':captured['lock']['vectors']})
            configurations[config]={'source_context':context,'reference_source':copy.deepcopy(g['water_schedule']),
                'companion_rules':companion,'adaptation':dict(copy.deepcopy(g['adaptation']),
                    original_source_service_id=sid,original_source_path=definition['path_id'],
                    original_source_beneficiary_program_ids=[],
                    interpretation='Original source unallocated fixture using exact selected-view model HOO; reviewed case is an explicit prototype adaptation'),
                'native_reference_case_ids':[c['case_id'] for c in captured['vectors']['cases'] if c['source_service_id']==sid and c['configuration_id']==config],
                'native_source_physical_reference':{'basis':'absolute','extent':1,
                    'interpretation':'One actual unattached unallocated Main; no programme/parent allocation or area scaling'}}
        if len(configurations)!=2:raise GeneratorError('source_integrity',sid,'Exact source/reviewed Main configurations required')
        slots=[{'slot':'hot_water_volume','source_schedule_id':load['schedule_id'],'unit':'fraction','kind':'load'}]
        controls=[]
        for slot,name,quantity,unit in CONTROL_SLOTS:
            slots.append({'slot':slot,'source_schedule_id':sid+'-'+slot,'unit':unit,'kind':'control'})
            controls.append({'slot':slot,'quantity':quantity,'unit':unit,'evidence':copy.deepcopy(evidence)})
        source={'building_type':definition['building_type'],'template':definition['template'],'vintage':None,
            'weather':None,'climate':None,'evidence_view':'source','source_id':sid,'source_family':'source_physical_service'}
        demand={'demand_id':sid,'slot':'hot_water_volume','quantity':'hot_water_volume','value':load['value'],
            'unit':load['unit'],'basis':load['basis'],'fuel':'water','host':'building_service',
            'heat_fractions':None,'evidence':copy.deepcopy(evidence)}
        resolved={'source_service_id':sid,'owner_kind':'physical_service','recipe_id':'physical-service__'+sid,
            'source_family':'source_physical_service','source':source,'slots':slots,'demands':[demand],
            'controls':controls,'shared_services':[],'evidence':[evidence],'source_service_definition':copy.deepcopy(definition)}
        records['reference','physical-service__'+sid]={'schema_version':'1.0.0','definition':copy.deepcopy(definition),
            'provenance':provenance,'recipe':{'schema_version':'1.0.0','resolved':resolved,'reference_year':2007,
                'configurations':configurations,'ownership':'instantiate_once','allocation_mode':'whole',
                'required_contract_version':'1.1.0','qualification_boundary':'Actual original Main/source-model HOO/fixed methods; programme/public/certificate gates remain separate'}}
    if len(records)!=4:raise GeneratorError('source_integrity','retail-services','Exactly three original physical definitions and one fixed projection required')
    return records


def service_cases(records):
    """Exact supported SID/configuration denominator, distinct from definitions."""
    return [{'case_id':'C6-'+record['definition']['id']+'__'+config,
        'owner_kind':'physical_service','source_service_id':record['definition']['id'],
        'resource_key':key,'source_hoo_configuration_id':config,'hoo_evidence_view':config.rsplit('__',1)[1],
        'building_type':'RetailStandalone','template':record['definition']['template'],
        'source_gate_status':'requires_public_family_certification'}
        for (kind,key),record in records.items() if kind=='reference' and key.startswith('physical-service__')
        and record['definition']['building_type']=='RetailStandalone'
        for config in record['recipe']['configurations']]


def qualification_request(records):
    """Exact ordered original programmes followed by explicit unallocated fixtures.

    These fixture selectors carry caller-labelled source-reference extents. They
    do not supply arbitrary building geometry or inferred programme allocations.
    Cumulative assembly must retain its predecessor's entire ordered prefix.
    """
    scope=records['reference','m1-scope']
    if 'qualification_request_order' in scope:
        from scripts.schedule_generator_restaurants import qualification_request as assemble_all
        request=assemble_all(records);indexed={i['key']:i for i in request['instances']};order=scope['qualification_request_order']
        if len(indexed)!=len(request['instances']) or len(order)!=len(set(order)) or set(order)!=set(indexed):
            raise GeneratorError('scope_mismatch','/qualification_request_order','Exact complete ordered case inventory required')
        request['instances']=[indexed[key] for key in order]
        return request
    instances=[]
    for case in scope['cases']:
        recipe=records['program',case['program_id']]['recipe']
        inputs=copy.deepcopy(recipe['bound_inputs'])
        if 'source_composition' in recipe:inputs['composition_basis_mode']='source_reference_area_normalized'
        instances.append({'key':case['case_id'],'owner_kind':'program','program_id':case['program_id'],
            'inputs':inputs,'operating_group':case['configuration_id'],'basis_bindings':{}})
    for case in service_cases(records):
        sid=case['source_service_id'];config=case['source_hoo_configuration_id']
        instances.append({'key':case['case_id'],'owner_kind':'physical_service','source_service_id':sid,
            'physical_id':'caller-reference-'+sid+'__'+case['hoo_evidence_view'],'operating_group':config,
            'inputs':{'source_hoo_configuration_id':config,
                'physical_fixture_evidence':{'caller':'Explicit one original unallocated Main in this alternative model/view context'}},
            'basis_bindings':{'multiplicity':1,'extents':{'absolute':{'value':1,'unit':'1',
                'evidence':{'caller':'Explicit whole absolute fixture once; no programme area or mixture weight'}}}}})
    return {'schema_version':'1.1.0','calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},'instances':instances}


def compile_cumulative_records(prior_resources):
    """Append exact Retail operands to the approved immutable C5 predecessor."""
    from atlas_schedules.canonical import canonical
    from scripts.schedule_generator_build import _receipt
    from scripts.schedule_generator_restaurants import qualification_request as predecessor_request
    previous=prior_resources.get('reference','m1-scope')
    authoritative=strict_json((ROOT/'sources/schedule-generator-restaurant-scope.json').read_bytes(),'restaurant-scope')
    if previous!=authoritative:
        raise GeneratorError('scope_mismatch','/prior_resources','Exact approved C5 predecessor required')
    records={(e['kind'],e['key']):prior_resources.get(e['kind'],e['key']) for e in prior_resources.manifest['resources']}
    old_request=predecessor_request(records)
    records.pop(('reference','family-certification'))
    records['reference','c5-family-native-join']=records.pop(('reference','family-native-join'))
    additions=compile_program_records();new_cases=additions['reference','m1-scope']['cases']
    new_services=service_cases(additions);new_ids={c['program_id'] for c in new_cases}
    for pair,record in additions.items():
        kind,key=pair
        if (kind=='program' and key in new_ids or kind=='commercial' and key.startswith('retail__') or
                kind=='composition' and record['definition']['building_type']=='RetailStandalone' or
                kind=='reference' and key.startswith('physical-service__') and record['definition']['building_type']=='RetailStandalone' or
                pair not in records and key not in {'m1-scope','recipe-coverage','catalogue-index'}):
            records[pair]=record
    def identifiers(value):
        if isinstance(value,dict):return set().union(*(identifiers(v) for v in value.values())) if value else set()
        if isinstance(value,list):return set().union(*(identifiers(v) for v in value)) if value else set()
        return {value} if isinstance(value,str) and value.startswith(('schedule-','evidence-','sourcefile-')) else set()
    definitions=[records['program',pid]['definition'] for pid in new_ids]
    definitions.extend(records['reference',c['resource_key']]['definition'] for c in new_services)
    required=identifiers(definitions)
    for filename in ('schedules.json','provenance.json','source_files.json'):
        path='data/definition-releases/v0.1.1/'+filename
        for index,value in enumerate(strict_json((ROOT/path).read_bytes(),path)):
            if value['id'] not in required:continue
            records.setdefault(('reference',value['id']),{'definition':value,
                'provenance':_receipt(path,'/'+str(index),'Exact appended original Retail operand and field evidence')})
            required.update(identifiers(value))
    new_index={p['id']:p for p in additions['reference','catalogue-index']['programs'] if p['id'] in new_ids}
    records['reference','catalogue-index']['programs']=[new_index.get(p['id'],p) for p in records['reference','catalogue-index']['programs']]
    new_compositions={r['definition']['id'] for (kind,key),r in additions.items() if kind=='composition' and r['definition']['building_type']=='RetailStandalone'}
    compiled_compositions={c['id']:c for c in additions['reference','catalogue-index']['compositions'] if c['id'] in new_compositions}
    records['reference','catalogue-index']['compositions']=[compiled_compositions.get(c['id'],c) for c in records['reference','catalogue-index']['compositions']]
    new_request=qualification_request(additions)
    order=[i['key'] for i in old_request['instances']+new_request['instances']]
    if len(order)!=261 or len(set(order))!=261:
        raise GeneratorError('scope_mismatch','/qualification_request_order','Exact191old plus64programme and6physical new cases required')
    scope=dict(copy.deepcopy(previous),milestone_id='C6-candidate',
        cases=copy.deepcopy(previous['cases'])+copy.deepcopy(new_cases),
        service_cases=copy.deepcopy(previous['service_cases'])+copy.deepcopy(new_services),
        qualification_request_order=order,
        source_order_policy='Preserve all191 approved C5 requested owners as an ordered prefix, then64 exact Retail programmes and6 explicit unallocated fixture/configuration cases; new ordered requests retain distinct RNG receipts',
        predecessor={'resource_set_id':prior_resources.resource_set_id,'scope_sha256':hashlib.sha256(canonical(previous)).hexdigest()},
        qualification_status='requires_current_family_certification')
    records['reference','m1-scope']=scope
    coverage=records['reference','recipe-coverage']
    coverage.update(milestone=scope['milestone_id'],cases=coverage['cases']+copy.deepcopy(additions['reference','recipe-coverage']['cases']),
        service_cases=copy.deepcopy(scope['service_cases']),
        physical_resource_scope='229 programme recipes and32 explicit physical service/configuration cases; required programme aliases remain separate from local channels')
    return records


def mixed_qualification_request(records,resource_set_id):
    """Keep the prior mixed experiment, then add an actual generated Retail parent.

    Explicit whole physical fixtures remain outside programme area weights. All
    extents are labelled caller experiment inputs, separate from native HOO.
    """
    from scripts.schedule_generator_restaurants import mixed_qualification_request as previous_mix
    request=previous_mix(records,resource_set_id);params=request['params']
    complete=qualification_request(records)
    pid='program-757305412c872b2f63b16d64'
    parent=copy.deepcopy(next(i for i in complete['instances'] if i.get('program_id')==pid))
    parent['inputs']['composition_basis_mode']='caller_parent_floor_area'
    parent['basis_bindings']={'extents':{'floor_area':{'value':100,'unit':'m2',
        'evidence':{'caller':'Explicit represented Retail programme area in this experiment, separate from source-reference HOO and fixture extent'}}}}
    fixture=copy.deepcopy(next(i for i in complete['instances'] if i.get('source_service_id')=='service-18de06e6d287f5e459877967'
        and i['inputs']['source_hoo_configuration_id']=='retail__90_1_2013__source'))
    params['instances'].extend([parent,fixture])
    # Explicit normalized coefficients retain old ratios*.8 plus Retail*.2.
    # Separate extents/result denominator determine physical basis factors.
    # Whole physical services remain outside the coefficient normalization.
    for member in params['mixture']['members']:member['weight']*=.8
    params['mixture']['members'].append({'instance_key':parent['key'],'weight':.2})
    params['mixture']['service_members'].append({'instance_key':fixture['key']})
    params['mixture']['program_id']='cumulative-residential-offices-warehouse-restaurants-retail'
    return request
