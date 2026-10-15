"""Compile exact source restaurant water recipes from qualified native methods."""
import copy
import hashlib
import zipfile

from scripts.common import ROOT
from scripts.schedule_generator_build import _receipt
from scripts.schedule_generator_reference import load_restaurant_water_reference
from atlas_schedules.resources import strict_json
from atlas_schedules.errors import GeneratorError
from atlas_schedules.canonical import canonical


def fixed_native_operand_projection(captured):
    """Literal fixed-profile operands; the complete captured arrays ship once."""
    cases=[]
    for i,source in enumerate(captured['native']['cases']):
        fixtures=[]
        for j,fixture in enumerate(source['fixtures']):
            controls={}
            for name,control in fixture['controls'].items():
                values=control['values']
                if len(values)!=8760 or any(v!=values[0] for v in values):
                    raise GeneratorError('source_integrity','restaurant-water-fixed-native-operands',
                        'Actual source fixed-control array is not constant/annual')
                controls[name]={k:copy.deepcopy(v) for k,v in control.items() if k!='values'}
                controls[name].update(hourly_value=values[0],hourly_count=len(values),
                    hourly_array_sha256=hashlib.sha256(canonical(values)).hexdigest(),
                    source_native_pointer='/cases/'+str(i)+'/fixtures/'+str(j)+'/controls/'+name)
            fixtures.append({'source_service_id':fixture['source_service_id'],'controls':controls})
        cases.append({'case_id':source['case_id'],'source_hoo_configuration_id':source['source_hoo_configuration_id'],
            'fixtures':fixtures})
    return {'schema_version':'1.0.0','method':'literal_native_fixed_operand_projection',
        'source_capture':dict(copy.deepcopy(captured['lock']['vectors']),
            canonical_decoded_native_sha256=hashlib.sha256(canonical(captured['native'])).hexdigest()),
        'interpretation':'Literal profiles, specials and one constant hourly operand; full original native arrays remain in the separately locked capture and must be compared by the current source checker',
        'cases':cases}


def validate_fixed_native_operands(projection,captured):
    """Compare actual captured controls/arrays, never accept receipts alone."""
    if projection!=fixed_native_operand_projection(captured):
        raise GeneratorError('source_integrity','restaurant-water-fixed-native-operands',
            'Missing/mispointed/altered literal operand or actual native source array')


def restaurant_program_cases():
    """46 actual identities; native room-method qualification still separate."""
    capture=load_restaurant_water_reference();given=capture['inputs']['cases']
    definitions=strict_json((ROOT/'data/definition-releases/v0.1.1/programs.json').read_bytes(),'programs')
    cases=[]
    for index,program in enumerate(definitions):
        if program['building_type'] not in {'FullServiceRestaurant','QuickServiceRestaurant'}:continue
        configuration=next(c for c in given if c['family']==program['building_type'] and
                           c['template']==program['template'] and c['evidence_view']==program['evidence_view'])
        config=configuration['source_hoo_configuration_id'];selector=config.split('__')[0]
        cases.append({'case_id':'C5-'+program['id'],'program_id':program['id'],'building_type':program['building_type'],
            'name':program['name'],'template':program['template'],'vintage':None,'evidence_view':program['evidence_view'],
            'climate':program['climate'],'configuration_id':config,
            'program_definition':_receipt('data/definition-releases/v0.1.1/programs.json','/'+str(index),'Exact original restaurant identity'),
            'configuration':{'sampling_configuration_id':selector+'_90_1_2013','conditioning_inputs':{'building_type':selector},
                'source_hoo_configuration_id':config,'program_definition_pointer':'/'+str(index),
                'interpretation':'Exact source/view reference People/geometry model; caller physical fixture extent remains separate'},
            'weather':{'mode':'not_used','interpretation':'Selected native interior/water methods and audited ten-table closure have no weather operands'},
            'source_gate_status':'requires_native_programme_certification'})
    if len(cases)!=46:raise GeneratorError('source_integrity','restaurant-cases','Exact46 programme identities required')
    return cases


def program_source_context(case):
    captured=load_restaurant_water_reference();config=case['configuration']['source_hoo_configuration_id']
    given=next(c for c in captured['inputs']['cases'] if c['source_hoo_configuration_id']==config)
    native=next(c for c in captured['native']['cases'] if c['case_id']==given['case_id'])
    context=source_model_context(given,native,captured['lock']['vectors']['payload_sha256'])
    context.update(case_id=case['case_id'],slot_sources={},slot_modes={})
    bound={'configuration_id':config,'source_hoo_configuration_id':config,'carrier_policy':'explicit_source_model_nonresidential_people'}
    return bound,context


def compile_program_records():
    """Development qualification fixture; no shipment or certified resource ID."""
    from atlas_schedules.resources import ResourceSet
    from scripts.schedule_generator_build import compile_recipes
    manifest=strict_json((ROOT/'atlas_schedules/data/manifest.json').read_bytes(),'base-manifest')
    base=ResourceSet(ROOT/'atlas_schedules/data',manifest['resource_set_id'])
    records={(e['kind'],e['key']):base.get(e['kind'],e['key']) for e in manifest['resources']}
    records.update(compile_service_records());records.update(compile_sampling_records())
    ruby=strict_json((ROOT/'sources/schedule-generator-ruby-float-lock.json').read_bytes(),'ruby-lock')['sources'][0]
    content=(ROOT/ruby['source_path']).read_bytes()
    if hashlib.sha256(content).hexdigest()!=ruby['sha256']:raise GeneratorError('source_integrity','ruby-float','Pinned rounding source differs')
    records['reference','ruby-float-numeric-c']={'text':content.decode('utf-8'),'provenance':ruby}
    definitions=strict_json((ROOT/'data/definition-releases/v0.1.1/programs.json').read_bytes(),'programs')
    by_id={p['id']:p for p in definitions};cases=restaurant_program_cases()
    for case in cases:
        pid=case['program_id'];record={'definition':copy.deepcopy(by_id[pid]),'case':case,
            'provenance':copy.deepcopy(case['program_definition'])}
        records['program',pid]=record
    scope={'milestone_id':'C5-programme-qualification-test','scope_version':'1.0.0','calendar':{'year':2007},'cases':cases}
    compile_recipes(records,scope)
    records['reference','m1-scope']=scope
    return records


def service_cases(records):
    """Exact26 SID/configuration identities; not programme catalogue additions."""
    return [{'case_id':'C5-'+record['definition']['id']+'__'+config,
        'source_service_id':record['definition']['id'],'source_hoo_configuration_id':config,
        'building_type':record['definition']['building_type'],'template':record['definition']['template'],
        'hoo_evidence_view':config.rsplit('__',1)[1],'source_definition_view':'source',
        'resource_key':key,'native_reference_case_ids':copy.deepcopy(variant['native_reference_case_ids']),
        'source_gate_status':'requires_public_family_certification'}
        for (kind,key),record in records.items() if kind=='reference' and key.startswith('physical-service__')
        for config,variant in record['recipe']['configurations'].items()]


def compile_cumulative_records(prior_resources):
    """Development assembly from a verified immutable predecessor, never runtime IO.

    This preserves prior operand/recipe records. The expanded scope has no inherited
    certification: a fresh source/native certificate and own-artifact gates follow.
    """
    from atlas_schedules.canonical import canonical
    previous=prior_resources.get('reference','m1-scope')
    authoritative=strict_json((ROOT/'sources/schedule-generator-warehouse-scope.json').read_bytes(),'warehouse-scope')
    if previous!=authoritative:
        raise GeneratorError('scope_mismatch','/prior_resources','Exact approved Warehouse predecessor required')
    records={(e['kind'],e['key']):prior_resources.get(e['kind'],e['key'])
             for e in prior_resources.manifest['resources']}
    for key in ('family-certification','family-native-lock','family-native-join'):
        record=records.pop(('reference',key),None)
        if record is not None and key!='family-certification':records['reference','prior-'+key]=record
    additions=compile_program_records()
    new_cases=additions['reference','m1-scope']['cases']
    new_ids={c['program_id'] for c in new_cases}
    for pair,record in additions.items():
        kind,key=pair
        if (kind=='program' and key in new_ids or kind=='commercial' and
                key.startswith(('full_service_restaurant__','quick_service_restaurant__')) or
                kind=='reference' and key.startswith('physical-service__') or pair not in records and
                key not in {'m1-scope','recipe-coverage','catalogue-index'}):
            records[pair]=record
    # Close the new original-definition operands and their per-field provenance.
    definitions=[records['program',pid]['definition'] for pid in new_ids]
    definitions.extend(r['definition'] for (k,key),r in records.items() if key.startswith('physical-service__'))
    def identifiers(value):
        if isinstance(value,dict):return set().union(*(identifiers(v) for v in value.values())) if value else set()
        if isinstance(value,list):return set().union(*(identifiers(v) for v in value)) if value else set()
        return {value} if isinstance(value,str) and value.startswith(('schedule-','evidence-','sourcefile-')) else set()
    required=identifiers(definitions)
    for filename in ('schedules.json','provenance.json','source_files.json'):
        path='data/definition-releases/v0.1.1/'+filename
        for index,value in enumerate(strict_json((ROOT/path).read_bytes(),path)):
            if value['id'] not in required:continue
            records.setdefault(('reference',value['id']),{'definition':value,
                'provenance':_receipt(path,'/'+str(index),'Exact appended source operand and original field evidence')})
            required.update(identifiers(value))
    new_index={p['id']:p for p in additions['reference','catalogue-index']['programs'] if p['id'] in new_ids}
    index=records['reference','catalogue-index']
    index['programs']=[new_index.get(p['id'],p) for p in index['programs']]
    scope=dict(copy.deepcopy(previous),milestone_id='C5-candidate',
        cases=copy.deepcopy(previous['cases'])+copy.deepcopy(new_cases),
        service_cases=service_cases(records),
        source_order_policy='Preserve exact prior119 cases and recipes; append46 restaurant definitions in source order, then26 explicit physical service/configuration cases. Different ordered requests have distinct RNG receipts.',
        predecessor={'resource_set_id':prior_resources.resource_set_id,
            'scope_sha256':hashlib.sha256(canonical(previous)).hexdigest()},
        qualification_status='requires_current_family_certification')
    records['reference','m1-scope']=scope
    coverage=records['reference','recipe-coverage']
    coverage.update(milestone=scope['milestone_id'],
        cases=coverage['cases']+copy.deepcopy(additions['reference','recipe-coverage']['cases']),
        service_cases=copy.deepcopy(scope['service_cases']),
        physical_resource_scope='165 programme recipes and26 explicitly bound physical service/configuration cases; required programme links are separate from local channels')
    water=load_restaurant_water_reference()
    records['reference','restaurant-water-fixed-native-operands']=fixed_native_operand_projection(water)
    return records


def qualification_request(records):
    """Explicit labelled source-reference extents, not external geometry defaults."""
    instances=[];scope=records['reference','m1-scope'];cases=scope['cases']
    declared=scope.get('service_cases',service_cases(records))
    for case in cases:
        recipe=records['program',case['program_id']]['recipe'];config=case['configuration_id']
        instance={'key':case['case_id'],'owner_kind':'program','program_id':case['program_id'],
            'inputs':copy.deepcopy(recipe['bound_inputs']),
            'operating_group':None if 'residents' in recipe['bound_inputs'] else config,'basis_bindings':{}}
        if 'source_composition' in recipe:instance['inputs']['composition_basis_mode']='source_reference_area_normalized'
        if recipe.get('required_service_links'):
            instance['service_links']={r['source_service_id']:'C5-'+r['source_service_id']+'__'+config for r in recipe['required_service_links']}
        instances.append(instance)
    for case in declared:
        record=records['reference',case['resource_key']];variant=record['recipe']['configurations'][case['source_hoo_configuration_id']]
        basis=record['definition']['load']['basis'];extent=1;unit='1'
        operands={'source_hoo_configuration_id':case['source_hoo_configuration_id'],
            'physical_fixture_evidence':{'scenario':'Caller explicitly selects one original source-reference physical fixture for each alternative source/view context; no population or stock realization'}}
        if basis=='floor_area':
            reference=variant['native_source_physical_reference'];area=reference['floor_area_m2'];multiplier=reference['multiplier']
            extent=area*multiplier;unit='m2'
            operands.update(fixture_floor_area_m2=area,fixture_space_multiplier=multiplier,
                fixture_extent_evidence={'area':{'value':area,'unit':'m2','scenario':'Explicit labelled source-reference fixture area'},
                                        'multiplier':{'value':multiplier,'unit':'1','scenario':'Explicit labelled source-reference fixture multiplier'}})
        instances.append({'key':case['case_id'],'owner_kind':'physical_service','source_service_id':case['source_service_id'],
            'physical_id':'caller-reference-'+case['source_service_id']+'__'+case['hoo_evidence_view'],
            'inputs':operands,'operating_group':case['source_hoo_configuration_id'],
            'basis_bindings':{'multiplicity':1,'extents':{basis:{'value':extent,'unit':unit,
                'evidence':{'scenario':'Explicit source-reference whole fixture extent applied once; alternative contexts have separate physical identities'}}}}})
    return {'schema_version':'1.1.0','calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},'instances':instances}


def mixed_qualification_request(records,resource_set_id):
    """Complete explicit source-reference experiment across completed families."""
    from scripts.schedule_generator_release import _mixed_request
    scope=records['reference','m1-scope']
    class Resources:
        def get(self,kind,key):return copy.deepcopy(records[kind,key])
    resources=Resources();resources.resource_set_id=resource_set_id
    prior=dict(copy.deepcopy(scope),milestone_id='C4',cases=copy.deepcopy(scope['cases'][:119]))
    request=_mixed_request(prior,resources);params=request['params']
    request['schema_version']='1.1.0';params['schema_version']='1.1.0'
    for instance in params['instances']:instance['owner_kind']='program'
    complete=qualification_request(records)
    full=next(c for c in scope['cases'] if c['program_id']=='program-76fabb7b85c683f4f7d8c873')
    quick=next(c for c in scope['cases'] if c['building_type']=='QuickServiceRestaurant' and
        c['template']=='90.1-2013' and c['evidence_view']=='reviewed' and 'Dining' in c['name'])
    services=[]
    for case in (full,quick):
        instance=next(i for i in complete['instances'] if i.get('program_id')==case['program_id'])
        instance['basis_bindings']={'extents':{'floor_area':{'value':100,'unit':'m2',
            'evidence':{'caller':'Explicit experiment programme area, separate from source HOO and whole fixture extent'}}}}
        params['instances'].append(instance)
        services.extend(i for i in complete['instances'] if i['owner_kind']=='physical_service' and
            i['operating_group']==case['configuration_id'])
    if len(services)!=3:raise GeneratorError('scope_mismatch','/mixed-example','Exact Fullmain/booster and Quickmain required')
    params['instances'].extend(services)
    params['mixture'].update(program_id='cumulative-residential-offices-warehouse-restaurants',
        members=[{'instance_key':i['key'],'weight':w} for i,w in zip(params['instances'][:6],[.1,.15,.2,.1,.25,.2])],
        service_members=[{'instance_key':i['key']} for i in services],
        denominator={'value':500,'unit':'m2','evidence':{'caller':'Explicit experiment result area; dwelling area/population and physical-service area shares are not inferred'}})
    return request


def compile_sampling_records():
    """Recover only each exact audited restaurant selector's actual v33 rows."""
    from scripts.schedule_generator_families import recover_commercial_closure
    from scripts.schedule_generator_sources import compile_member, _verify
    lock=strict_json((ROOT/'sources/schedule-generator-warehouse-lock.json').read_bytes(),'warehouse-lock')
    records={}
    for selector in ('full_service_restaurant','quick_service_restaurant'):
        audit=recover_commercial_closure(lock,selector)
        records['commercial',selector+'__sampling-audit']=audit
    source=next(a for a in lock['archives'] if a['source_id']=='comstock' and a['format']=='zip')
    content=(ROOT/'data/raw'/source['cache_path']).read_bytes();_verify(content,source)
    with zipfile.ZipFile(ROOT/'data/raw'/source['cache_path']) as archive:
        for entry in source['members']:
            if entry['kind']!='commercial' or entry.get('fixed_selectors',{}).get('building_type') not in {'full_service_restaurant','quick_service_restaurant'}:continue
            blob=archive.read(entry['path']);_verify(blob,entry)
            records['commercial',entry['key']]=compile_member(blob,entry,source)
    if len(records)!=22:raise GeneratorError('source_integrity','sampling','Exactly two audits and twenty conditional tables required')
    return records


def source_model_context(given,native,output_sha256):
    """Exact source/view model operands; caller physical extent is separate."""
    schedule=given['people_schedule']
    parts=[dict(schedule=copy.deepcopy(schedule),nominal_people=p['nominal_people'],residential=p['residential'],
        source_space_name=p['space_name'],program_id=p['program_id'],source_program_id=p['source_program_id'],
        source_floor_area_m2=p['floor_area_m2'],source_multiplier=p['multiplier'],source_density_person_m2=p['source_density_person_m2'],
        evidence={'source_geometry':given['geometry_receipt'],'source_people_definition':given['people'][i]['source_definition'],
            'native_nominal_people':p['nominal_people'],'source_method':'space.rb:423-518 People.getNumberOfPeople(space.floorArea); same schedule weights added before round6',
            'native_capture_output_sha256':output_sha256}) for i,p in enumerate(native['people'])]
    return {'year':2007,'holidays':[],'steps_per_hour':6,'standards_version':'0.8.6',
        'configuration_id':given['source_hoo_configuration_id'],'source_hoo_configuration_id':given['source_hoo_configuration_id'],
        'slot_sources':{'hot_water_volume':copy.deepcopy(given['water_schedule'])},'slot_modes':{'hot_water_volume':'hours'},
        'occupancy_aggregation':{'policy':'explicit_source_model_nonresidential_people','source_hoo_configuration_id':given['source_hoo_configuration_id'],
            'evidence_view':given['evidence_view'],'constituents':parts,'source_model_scope':copy.deepcopy(given['adaptation']),
            'interpretation':'Exact native source/view model reference; physical fixture extent separately caller-bound'},
        'occupancy_adjustment':{'peak_occ_frac':.231,'source_key':'comstock__resources__options_lookup_tsv',
            'source_options':['baseline_hvac_sizing=autosize','baseline_hvac_sizing=hardsize']},
        'source_clock':{'TZ':'UTC','variant':'controlled_no_DST_local_standard_calendar'},
        'parametric_apply':copy.deepcopy(given['parametric_apply']),
        'configuration_association':{'conditioning_inputs':{'building_type':given['source_hoo_configuration_id'].split('__')[0]},
            'source_hoo_configuration_id':given['source_hoo_configuration_id'],'evidence_view':given['evidence_view'],
            'interpretation':'Explicit source/view prototype HOO adaptation; no population/whole-prototype equivalence'},
        'method':'prototype_budget_preserving_commercial_hybrid'}


def compile_service_records():
    """13 source definitions, each with exactly two qualified view configurations."""
    capture=load_restaurant_water_reference();lock=capture['lock']
    path='data/definition-releases/v0.1.1/services.json';blob=(ROOT/path).read_bytes()
    frozen=capture['inputs']['provenance']['frozen_definitions']['services.json']
    if hashlib.sha256(blob).hexdigest()!=frozen['sha256']:
        raise GeneratorError('source_integrity',path,'Original normalized services changed')
    services=strict_json(blob,path);inputs={c['case_id']:c for c in capture['inputs']['cases']}
    records={}
    for index,definition in enumerate(services):
        if definition['id'] not in lock['source_service_ids']:continue
        sid=definition['id'];load=definition['load'];configurations={}
        provenance=_receipt(path,'/'+str(index),'Exact original source service definition; physical identity/extent separately caller-bound')
        evidence={'definition':provenance,'original_service':copy.deepcopy(definition),
            'native_output_sha256':lock['vectors']['payload_sha256'],
            'source_fixture_methods':copy.deepcopy(capture['inputs']['provenance']['fixture_methods']),
            'interpretation':'Original source volume budget and unresolved thermal assignment; fixed fraction controls do not assign zone heat'}
        slots=[{'slot':'hot_water_volume','source_schedule_id':load['schedule_id'],'unit':'fraction','kind':'load'}]
        controls=[]
        for slot,quantity,unit in [('water_target_temperature','temperature','C'),('water_sensible_fraction','sensible_fraction','fraction'),
                                   ('water_latent_fraction','latent_fraction','fraction')]:
            slots.append({'slot':slot,'source_schedule_id':sid+'-'+slot,'unit':unit,'kind':'control'})
            controls.append({'slot':slot,'quantity':quantity,'unit':unit,'evidence':copy.deepcopy(evidence)})
        for native_index,native in enumerate(capture['native']['cases']):
            fixtures=[f for f in native['fixtures'] if f['source_service_id']==sid]
            if not fixtures:continue
            given=inputs[native['case_id']];config=given['source_hoo_configuration_id']
            if config in configurations:continue
            fixture=fixtures[0];fixture_index=native['fixtures'].index(fixture);companions={}
            for slot,native_slot,original in [('water_target_temperature','target_temperature',load['target_temperature_degC']),
                                              ('water_sensible_fraction','sensible_fraction',.2),('water_latent_fraction','latent_fraction',.05)]:
                profile=fixture['controls'][native_slot]['profiles']['default']
                specials=fixture['controls'][native_slot]['special_profiles']
                if (len(profile)!=1 or profile[0][0]!=24 or len(set(fixture['controls'][native_slot]['values']))!=1 or
                        set(fixture['controls'][native_slot]['profiles'])!={'default'} or
                        set(specials)!={'WntrDsn','SmrDsn'} or any(points!=profile for points in specials.values())):
                    raise GeneratorError('source_integrity',sid+'/'+slot,'Actual fixed native Ruleset is not constant')
                companions[slot]={'method':'native_constant_ruleset','original_value':original,'stored_value':profile[0][1],
                    'native_hourly_value':fixture['controls'][native_slot]['values'][0],
                    'native_source_profile':copy.deepcopy(profile),
                    'native_special_profiles':copy.deepcopy(specials),
                    'source_profile_creation':{'method':'create_constant_schedule_ruleset',
                        'source_locator':'Standards0.8.6 create.rb:113-150','original_rule_order':[],
                        'original_special_state':'not_explicitly_set','getter_alias':'Native getter returns actual constant default'},
                    'source_operand':{'value':(given['kitchen_row']['service_water_heating_target_temperature']
                        if load['basis']=='floor_area' else given['prototype_row']['booster_water_use_temperature'])
                        if native_slot=='target_temperature' else original,
                        'unit':'F' if native_slot=='target_temperature' else 'fraction',
                        'method':'OpenStudio.convert(F,C) then native constant ScheduleDay storage'
                        if native_slot=='target_temperature' else 'create_water_use source fixed fraction'},
                    'evidence':dict(copy.deepcopy(evidence),source_method='create_water_use.rb:39-62; Standards0.8.6 information.rb:338-382',
                        native_control_reference={'resource_kind':'reference','resource_key':'restaurant-water-fixed-native-operands',
                            'json_pointer':'/cases/'+str(native_index)+'/fixtures/'+str(fixture_index)+'/controls/'+native_slot,
                            'source_native_pointer':'/cases/'+str(native_index)+'/fixtures/'+str(fixture_index)+'/controls/'+native_slot,
                            'source_path':lock['vectors']['source_path'],'payload_sha256':lock['vectors']['payload_sha256'],
                            'source_gzip_sha256':lock['vectors']['sha256'],
                            'transformation':'Literal fixed-operand projection, independently closed against original native arrays by current checker'},
                        canonical_source_conversion='scripts/commercial_water_paths.py:78,83 (F-32)/1.8; original normalized definition unchanged',
                        interpretation='Actual source-created fixed Ruleset: native double storage then selected round5 getter; no annual scaling or zone heat inference')}
            configurations[config]={'source_context':source_model_context(given,native,lock['vectors']['payload_sha256']),
                'reference_source':copy.deepcopy(given['water_schedule']),'companion_rules':companions,
                'adaptation':dict(copy.deepcopy(given['adaptation']),original_source_service_id=sid,
                    original_source_path=definition['path_id'],original_source_beneficiary_program_ids=definition['beneficiary_program_ids']),
                'native_reference_case_ids':[c['case_id'] for c in capture['native']['cases']
                    if c['source_hoo_configuration_id']==config and any(f['source_service_id']==sid for f in c['fixtures'])],
                'native_source_physical_reference':copy.deepcopy(fixture['source_physical_reference']) if load['basis']=='floor_area' else
                    {'basis':'absolute','extent':1,'interpretation':'Booster has no area/Kitchen beneficiary or attachment'}}
        if len(configurations)!=2:raise GeneratorError('source_integrity',sid,'Exactly source/reviewed native configurations required')
        source={'building_type':definition['building_type'],'template':definition['template'],'vintage':None,'weather':None,
            'climate':None,'evidence_view':'source','source_id':sid,'source_family':'source_physical_service'}
        demand={'demand_id':sid,'slot':'hot_water_volume','quantity':'hot_water_volume','value':load['value'],'unit':load['unit'],
            'basis':load['basis'],'fuel':'water','host':'building_service','heat_fractions':None,'evidence':copy.deepcopy(evidence)}
        resolved={'source_service_id':sid,'owner_kind':'physical_service','recipe_id':'physical-service__'+sid,
            'source_family':'source_physical_service','source':source,'slots':slots,'demands':[demand],'controls':controls,
            'shared_services':[],'evidence':[evidence],'source_service_definition':copy.deepcopy(definition)}
        records['reference','physical-service__'+sid]={'schema_version':'1.0.0','definition':copy.deepcopy(definition),'provenance':provenance,
            'recipe':{'schema_version':'1.0.0','resolved':resolved,'reference_year':2007,'configurations':configurations,
                'ownership':'instantiate_once','allocation_mode':'whole','required_contract_version':'1.1.0',
                'qualification_boundary':'Actual water/HOO/source fixture methods; programme family/release certificate separately required'}}
    if len(records)!=13:raise GeneratorError('source_integrity','services','Exact source definition count differs')
    return records
