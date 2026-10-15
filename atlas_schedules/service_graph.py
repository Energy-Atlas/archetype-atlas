"""Offline physical ownership, retained authority and transitive reference closure.

Incoming consistency never attests production qualification. All operands come
from the bundle; no ResourceSet, file, default recipe, RNG or owner repair occurs.
"""
import copy
import hashlib
import math

from .canonical import canonical
from .errors import GeneratorError
from .owners import physical_identity
from . import physical_sets as exact

CALLER='caller_unit_prototype_density_fixed_dhw'


def _fail(path, message, code='source_integrity'):
    raise GeneratorError(code,path,message)


def _same(a,b):
    return canonical(a)==canonical(b)


def _owners(bundle):
    result={c['instance_key']:c for c in bundle['constituents']}
    if len(result)!=len(bundle['constituents']):
        _fail('/constituents','Duplicate retained owner key','invalid_reference')
    return result


def _unique(records, identifier, path):
    result={}
    for record in records:
        exact._source(record,path)
        value=record['value']
        if not isinstance(value,dict):_fail(path,'Whole source object required')
        key=identifier(value)
        if not isinstance(key,str) or not key or key in result:
            _fail(path,'Missing or duplicate source identity')
        result[key]=record
    return result


def _canonical_record(record,path):
    exact._source(record,path)
    if record['locator']!='/' or record['sha256']!=hashlib.sha256(canonical(record['value'])).hexdigest():
        _fail(path,'Retained canonical resource bytes/hash/whole locator differ')


def _source_consistency(value):
    """All retained uses of one immutable object agree, including unused proof."""
    objects={};files={}
    def walk(current,path):
        if isinstance(current,dict):
            if set(current)=={'path','sha256','locator','value'}:
                exact._source(current,path)
                key=(current['path'],current['sha256'],current['locator'])
                if key in objects and not _same(objects[key],current['value']):
                    _fail(path,'One immutable source object has conflicting retained values')
                objects[key]=current['value']
                if current['path'] in files and files[current['path']]!=current['sha256']:
                    _fail(path,'One retained source file has conflicting revisions')
                files[current['path']]=current['sha256']
            for k,v in current.items():walk(v,path+'/'+k)
        elif isinstance(current,list):
            for i,v in enumerate(current):walk(v,path+'/'+str(i))
    walk(value,'')


def _binding(bundle,owner):
    indices=owner['binding_indices']
    if (not indices or any(type(i) is not int or not 0<=i<len(bundle['bindings']) for i in indices) or
            len(set(indices))!=len(indices)):
        _fail('/constituents/'+owner['instance_key'],'Physical owned binding indices differ','invalid_reference')
    if owner['physical_binding_kind']=='legacy_whole':
        # C5 retains fixed companion controls in addition to its one owned load.
        # Every reference still belongs to this exact owner; new modes remain
        # restricted to their separately qualified water-only binding contract.
        for i in indices:
            b=bundle['bindings'][i]
            if (b.get('instance_key')!=owner['instance_key'] or b.get('owner_kind')!='physical_service' or
                    any(b.get(k)!=owner.get(k) for k in ('source_service_id','physical_id','physical_binding_kind',
                        'building_realization_id','unit_id','source_fixture_role_id')) or
                    b.get('schedule_id')!=owner['schedule_ids'].get(b.get('slot')) or
                    b.get('schedule_id') not in bundle['schedules'] or
                    b.get('kind') not in {'load','control'} or
                    b.get('kind')=='load' and b.get('slot')!='hot_water_volume'):
                _fail('/bindings/'+str(i),'Legacy physical owned load/control reference differs','invalid_reference')
        indices=[i for i in indices if bundle['bindings'][i].get('kind')=='load']
    if len(indices)!=1:
        _fail('/constituents/'+owner['instance_key'],'One physical owned water binding required','invalid_reference')
    index=indices[0];binding=bundle['bindings'][index]
    if (binding.get('instance_key')!=owner['instance_key'] or binding.get('kind')!='load' or
            binding.get('slot')!='hot_water_volume' or
            any(binding.get(k)!=owner.get(k) for k in ('source_service_id','physical_id',
                'physical_binding_kind','building_realization_id','unit_id','source_fixture_role_id')) or
            owner['schedule_ids'].get('hot_water_volume')!=binding.get('schedule_id')):
        _fail('/bindings/'+str(index),'Physical binding identity/schedule differs','invalid_reference')
    return index,binding


def _reference(bundle,owner):
    index,binding=_binding(bundle,owner)
    fields=('instance_key','physical_id','source_service_id','demand_id','slot','schedule_id')
    result={k:binding[k] for k in fields}
    kind=owner['physical_binding_kind']
    result.update(binding_ref_kind=kind,binding_index=index)
    if kind!='legacy_whole':result['building_realization_id']=owner['building_realization_id']
    if kind=='exact_source_role':result['source_fixture_role_id']=owner['source_fixture_role_id']
    if kind==CALLER:result['unit_id']=owner['unit_id']
    return result


def _check_resolved(owner,resolved,group):
    """Check the actual retained executable, independently of owner receipts."""
    path='/constituents/'+owner['instance_key']
    source=dict(copy.deepcopy(resolved['source']),source_family=resolved['source_family'])
    source.setdefault('vintage',None);source.setdefault('weather',None)
    for field,wanted in (('recipe_id',resolved['recipe_id']),('source',source),
                         ('slots',resolved['slots']),('controls',resolved['controls'])):
        if not _same(owner.get(field),wanted):_fail(path+'/'+field,'Retained owner differs from entire source executable')
    actual=copy.deepcopy(owner['demands'])
    for d in actual:d.pop('heat_fractions',None)
    wanted=copy.deepcopy(resolved['demands'])
    for d in wanted:d.pop('heat_fractions',None)
    if not _same(actual,wanted):_fail(path+'/demands','Original executable demand changed')
    prepared={'reference_channels','reference_budgets','source_context','companion_rules','source_composition'}
    inputs={k:v for k,v in resolved['inputs'].items() if k not in prepared}
    if not _same(owner['inputs'],inputs):
        _fail(path+'/inputs','Actual retained operands/calendar differ from reconstructed executable')
    if owner['owner_kind']!='physical_service' and not _same(owner['required_service_links'],resolved.get('required_service_links',[])):
        _fail(path+'/required_service_links','Actual C5 inventory differs from original executable')
    if (not _same(owner['generation'].get('source_inputs'),resolved['inputs']['source_context']) or
            owner['generation'].get('operating_group')!=group):
        _fail(path+'/generation','Actual executable method/group context differs','operating_group_conflict')


def _original_obligations(programme,recipe,path):
    """Count obligations from whole originals before inspecting supplied entries."""
    expected=[];occupied=set()
    for load in programme['loads']:
        if load.get('quantity')!='hot_water_volume' or 'source_components' in load:continue
        sid=load.get('service_id')
        if sid in occupied:_fail(path,'Duplicate original water obligation')
        occupied.add(sid)
        expected.append(('original_programme_demand',load))
    for sid in programme['service_ids']:
        if sid not in occupied:
            expected.append(('original_service_reference',sid));occupied.add(sid)
    expected.extend(('original_source_components',load) for load in programme['loads']
        if load.get('quantity')=='hot_water_volume' and 'source_components' in load)
    actual=[]
    for requirement in recipe['required_service_sets']:
        kind=requirement['kind']
        if kind=='original_programme_demand':value=requirement['original_demand']['value']
        elif kind=='original_service_reference':value=requirement['source_service_id']
        elif kind=='original_source_components':value=requirement['original_mixed_demand']['value']
        else:_fail(path,'Foreign requirement branch in exact source original')
        actual.append((kind,value))
    if not _same(actual,expected):
        _fail(path,'Required inventory does not cover complete original water demand/reference/components in source order')


def _exact_realization(bundle,realization,owners):
    """Reconstruct selected closure against independent canonical originals/pool."""
    clock=bundle['metadata']['calendar'];building=realization['building_realization_id']
    inventory=exact.validate_inventory({'payload':realization['inventory'],
        'inventory_sha256':realization['inventory_sha256']},_incoming=True)
    payload=inventory['payload'];native=realization['native_context'];authority=native['execution_authority']
    path='/metadata/building_realizations/'+building
    if (payload['inventory_id']!=realization['inventory_id'] or
            realization['inventory_resource']['resource_set_id']!=bundle['metadata']['resource_set_id'] or
            realization['inventory_resource']['kind']!='reference' or
            realization['inventory_resource']['key']!='physical-fixture-inventory__'+payload['inventory_id'] or
            realization['inventory_resource']['sha256']!=hashlib.sha256(canonical(inventory)).hexdigest()):
        _fail(path,'Original inventory/resource identity differs')
    qualification=authority['method_qualification'];exact._source(qualification,path+'/method_qualification')
    q=qualification['value']
    exact._exact(q,('qualification_id','qualification_scope','inventory_id','inventory_sha256',
        'program_ids','selected_method_context','evidence'),path+'/method_qualification/value')
    exact._evidence(q['evidence'],path+'/method_qualification/evidence')
    selected=q['selected_method_context'];context=exact._selected_context(selected)
    if (q['qualification_scope']!=exact.FULL_SCOPE or q['qualification_id']!=context['qualification_id'] or
            q['inventory_id']!=payload['inventory_id'] or q['inventory_sha256']!=inventory['inventory_sha256'] or
            not isinstance(q['program_ids'],list) or len(set(q['program_ids']))!=len(q['program_ids'])):
        _fail(path,'Independent native inventory/coverage identity differs')
    for pid in q['program_ids']:exact._typed(pid,'id',path+'/program_ids')
    if (context['method_consumed_context']['value']['calendar']!=clock or
            any(context[k]!=realization[k] or native[k]!=realization[k] for k in
                ('source_hoo_configuration_id','selected_method_context_id')) or
            native['qualification_id']!=context['qualification_id']):
        _fail(path+'/native_context','Qualified selected context/calendar differs','operating_group_conflict')
    association=authority['execution_association']
    exact._exact(association,('selected_method_context','physical_service_records','child_program_records','evidence'),path+'/execution_association')
    exact._evidence(association['evidence'],path+'/execution_association/evidence')
    if not _same(association['selected_method_context'],selected):_fail(path,'Native/executable selected context differs')
    executable=native['execution_qualification'];exact._source(executable,path+'/execution_qualification')
    eq=executable['value']
    exact._exact(eq,('qualification_id','qualification_scope','selected_method_context','execution_association',
                    'standalone_program_records','evidence'),path+'/execution_qualification/value')
    exact._typed(eq['qualification_id'],'id',path+'/execution_qualification/qualification_id')
    exact._evidence(eq['evidence'],path+'/execution_qualification/evidence')
    retained_association=eq['execution_association'];_canonical_record(retained_association,path+'/execution_association')
    if (eq['qualification_scope']!=exact.FULL_SCOPE or not _same(eq['selected_method_context'],selected) or
            not _same(retained_association['value'],association) or
            retained_association['path']!='reference/physical-execution-association__'+realization['selected_method_context_id']+'.json'):
        _fail(path,'Independent executable association differs')
    canonical_programs=_unique(authority['canonical_program_records'],lambda v:v.get('definition',{}).get('id'),path+'/canonical_program_records')
    canonical_physical=_unique(authority['canonical_physical_records'],lambda v:v.get('definition',{}).get('id'),path+'/canonical_physical_records')
    pool=_unique(eq['standalone_program_records'],lambda v:v.get('definition',{}).get('id'),path+'/standalone_program_records')
    for pid,record in {**canonical_programs,**pool}.items():
        _canonical_record(record,path+'/program/'+pid)
        if record['path']!='program/'+pid+'.json' or pid not in q['program_ids']:
            _fail(path,'Whole canonical programme is outside qualified eligible context')
        if pid in pool and pid in canonical_programs and not _same(pool[pid],canonical_programs[pid]):
            _fail(path,'Selected programme differs from eligible source pool')
    for record in pool.values():
        exact._executable_context(record['value']['recipe']['source_context'],realization,clock,path+'/eligible/source_context')
    selected_owners=[c for c in owners.values() if c.get('building_realization_id')==building]
    programmes=[c for c in selected_owners if c['owner_kind']=='program']
    physical=[c for c in selected_owners if c.get('physical_binding_kind')=='exact_source_role']
    if set(canonical_programs)!={c['program_id'] for c in programmes} or set(canonical_physical)!={c['source_service_id'] for c in physical}:
        _fail(path,'Canonical retained records must close exactly selected direct/parent/child originals')
    child_records={}
    for item in association['child_program_records']:
        exact._exact(item,('variant_id','key','program_record'),path+'/child_program_records')
        exact._typed(item['variant_id'],'id',path+'/child_program_records/variant_id')
        schema=exact._load_schema('bundle','1.2.0')
        exact._check_schema(item['key'],schema['$defs']['child_variant']['properties']['key'],schema,path+'/child_program_records/key')
        exact._source(item['program_record'],path+'/child_program_records/program_record')
        key=item['key'];definition=item['program_record']['value'].get('definition',{})
        if (item['variant_id'] in child_records or key['parent_inventory_id']!=payload['inventory_id'] or
                key['parent_inventory_sha256']!=inventory['inventory_sha256'] or
                key['selected_method_context_id']!=realization['selected_method_context_id'] or
                key['member_program_id']!=definition.get('id') or
                key['member_evidence_view']!=definition.get('evidence_view') or key['member_program_id'] not in q['program_ids']):
            _fail(path,'Child executable full tuple/original view/qualified coverage differs')
        exact._executable_context(item['program_record']['value']['recipe']['source_context'],realization,clock,path+'/associated_child/source_context')
        child_records[item['variant_id']]=item
    requirements={}
    # An unused eligible parent still has independently retained component leaves
    # in its qualified association. They supply proof, never selected outputs.
    for record in list(pool.values())+list(canonical_programs.values())+[item['program_record'] for item in child_records.values()]:
        original=record['value'];programme=exact._programme(original['definition'],path+'/programme')
        recipe=original.get('recipe',{});resolved=recipe.get('resolved',{})
        exact._exact(recipe.get('exact_source_authority'),('inventory_id','inventory_sha256','requirements_key','qualification_key'),path+'/exact_source_authority')
        ref=recipe['exact_source_authority']
        if (ref['inventory_id']!=payload['inventory_id'] or ref['inventory_sha256']!=inventory['inventory_sha256'] or
                not isinstance(recipe.get('required_service_links'),list) or not isinstance(recipe.get('required_service_sets'),list) or
                resolved.get('program_id')!=programme['id'] or any(resolved.get('source',{}).get(k)!=programme[v] for k,v in (
                    ('source_id','source_id'),('building_type','building_type'),('template','template'),('evidence_view','evidence_view')))):
            _fail(path,'Eligible whole programme original/source/inventory differs')
        exact._method(recipe.get('original_method_reference'),programme)
        exact._no_double_listing(recipe['required_service_links'],recipe['required_service_sets'])
        _original_obligations(programme,recipe,path+'/programme/'+programme['id']+'/required_service_sets')
        for req in recipe['required_service_sets']:
            if not _same(exact._programme_requirement(req)['value'],programme):_fail(path,'Eligible requirement changed original whole programme')
            rid=req['requirement_id']
            if rid in requirements and not _same(requirements[rid],req):_fail(path,'Conflicting independent source requirements')
            requirements[rid]=req
    exact.validate_requirements(list(requirements.values()),inventory)
    by_role={r['role_id']:r for r in payload['roles']}
    associated=_unique(association['physical_service_records'],lambda v:v.get('definition',{}).get('id'),path+'/physical_service_records')
    if set(associated)!={r['source_service_id'] for r in payload['roles']}:
        _fail(path,'Executable physical coverage differs from complete source inventory')
    for sid,record in associated.items():
        roles=[r for r in payload['roles'] if r['source_service_id']==sid]
        if not _same(record['value'].get('definition'),roles[0]['service_definition']['value']):_fail(path,'Executable original service authority differs')
        configurations=record['value']['recipe'].get('configurations',{})
        variant=configurations.get(realization['source_hoo_configuration_id'])
        if not isinstance(variant,dict):_fail(path,'Associated physical executable lacks selected configuration')
        exact._executable_context(variant.get('source_context'),realization,clock,path+'/associated_physical/source_context')
        schedule=roles[0]['schedule_authority']
        rules=schedule.get('canonical_schedule',{}).get('value',schedule.get('compiled_ruleset'))
        if not _same(variant.get('reference_source'),rules):_fail(path,'Associated physical executable changed original Ruleset')
        if sid in canonical_physical:
            original=canonical_physical[sid];_canonical_record(original,path+'/physical/'+sid)
            if original['path']!='reference/physical-service__'+sid+'.json':_fail(path,'Canonical service resource path differs')
            exact._original_executable(record['value'],original['value'],{'configurations'},path+'/physical/'+sid)
    owner_plans=[];claimed=set()
    for owner in physical:
        role=by_role.get(owner['source_fixture_role_id']);where='/constituents/'+owner['instance_key']
        if role is None or role['source_service_id']!=owner['source_service_id']:_fail(where,'Foreign physical role/SID','shared_service_conflict')
        if role['role_id'] in claimed:_fail(where,'Duplicate actual role owner','shared_service_conflict')
        claimed.add(role['role_id'])
        instance=dict(key=owner['instance_key'],**{k:copy.deepcopy(owner[k]) for k in (
            'owner_kind','physical_binding_kind','source_service_id','physical_id','building_realization_id','source_fixture_role_id','basis_bindings')},
            inputs={k:v for k,v in owner['inputs'].items() if k not in {'year','holidays'}},operating_group=realization['operating_group'])
        from .services import _resolve_physical_service_record
        resolved=_resolve_physical_service_record(instance,clock,associated[owner['source_service_id']]['value'])
        _check_resolved(owner,resolved,realization['operating_group'])
        exact._executable_context(resolved['inputs']['source_context'],realization,clock,where+'/source_context')
        variant=associated[owner['source_service_id']]['value']['recipe']['configurations'][realization['source_hoo_configuration_id']]
        schedule=role['schedule_authority'];rules=schedule.get('canonical_schedule',{}).get('value',schedule.get('compiled_ruleset'))
        if not _same(variant['reference_source'],rules):_fail(where,'Selected executable changed original Ruleset')
        if role['source_basis']=='floor_area' and any(owner['inputs'].get(a)!=role['geometry_operands'][b] for a,b in (
            ('fixture_floor_area_m2','floor_area_m2'),('fixture_space_multiplier','space_multiplier'))):_fail(where,'Original geometry operands differ')
        target=resolved['inputs']['reference_budgets'][owner['source_service_id']]
        independent=exact._original_target(None,[role],clock)
        if any(not _same(target[k],independent[k]) for k in ('total','basis','unit','magnitude_unit','quantity','method','fuel','host')):
            _fail(where,'Canonical source B differs')
        extent=role['consumed_extent']
        if any(resolved['shared_services'][0]['extent'][k]!=extent[k] for k in ('value','unit')):_fail(where,'Original extent differs')
        owner_plans.append({'instance_key':owner['instance_key'],'building_realization_id':building,
            'role':role,'extent':extent,'source_basis_target':target,
            'whole_input_target':{'quantity':'hot_water_volume','total':target['total']*extent['value'],
                'unit':'m3','basis':'absolute','derivation':'source_basis_target_times_extent'}})
        expected=copy.deepcopy(resolved['shared_services']);expected[0].update(source_basis_target=target,
            extent=extent,whole_input_target=owner_plans[-1]['whole_input_target'])
        if not _same(owner['shared_services'],expected):_fail(where+'/shared_services','Full source/extent/whole authority differs')
    projections=[];children_by_key={};used_variants=set()
    if len({o['program_id'] for o in programmes})!=len(programmes):
        _fail(path,'Duplicate exact selected programme claim','shared_service_conflict')
    for owner in programmes:
        record=canonical_programs[owner['program_id']]['value'];recipe=record['recipe'];selected_record=record
        variant=owner['generation'].get('method_variant')
        if variant is not None:
            exact._typed(variant,'child_variant',path+'/method_variant')
            member={k:copy.deepcopy(variant['adaptation'][k] if variant['adaptation'] is not None else variant['qualification']['value'][k])
                for k in ('canonical_member','original_method_reference','conserved_source_authority','evidence')}
            member.update(parent_inventory_id=payload['inventory_id'],parent_inventory_sha256=inventory['inventory_sha256'])
            expected=exact._variant_record(member,selected,variant['qualification'],_incoming=True)
            if not _same(expected,variant):_fail(path,'Full qualified variant tuple/original/adaptation differs')
            item=child_records.get(variant['variant_id'])
            if item is None or not _same(item['key'],variant['key']):_fail(path,'Missing exact child executable','invalid_reference')
            selected_record=item['program_record']['value'];used_variants.add(variant['variant_id'])
            exact._original_executable(selected_record,record,{'bound_inputs','required_inputs','variable_inputs','source_context','companion_rules'},path+'/child')
            if not _same(selected_record['definition'],variant['canonical_member']['value']):_fail(path,'Child changed canonical member')
        elif owner['program_id'] not in pool:_fail(path,'Selected direct programme absent from eligible pool')
        from .programs import _resolve_program_record
        resolved=_resolve_program_record(owner['program_id'],dict(owner['inputs'],year=clock['year'],holidays=clock['holidays']),
            selected_record,'compiled' if selected_record['recipe']['resolved']['slots'] else 'accepted_inactive')
        resolved=exact._without_owned_water(resolved)
        _check_resolved(owner,resolved,realization['operating_group'])
        exact._executable_context(resolved['inputs']['source_context'],realization,clock,path+'/programme/source_context')
        own=recipe['required_service_sets']
        if not _same(owner['required_service_sets'],own):_fail(path,'Actual selected requirements differ from original executable')
        if len(own)!=len(owner['service_set_projections']):_fail(path,'Incomplete projection inventory','invalid_reference')
        for req in own:
            if not _same(exact._programme_requirement(req)['value'],record['definition']):_fail(path,'Whole original programme differs')
            item={'instance_key':owner['instance_key'],'building_realization_id':building,'requirement':req,'children':[]}
            projections.append(item);children_by_key[owner['instance_key'],req['requirement_id']]=(owner,variant)
    # Source order: child projections precede their parent's component projection.
    projections.sort(key=lambda p:p['requirement']['kind']=='original_source_components')
    for item in projections:
        req=item['requirement']
        if req['kind']!='original_source_components':continue
        parent=owners[item['instance_key']];recipe=canonical_programs[parent['program_id']]['value']['recipe']
        if parent['inputs'].get('composition_basis_mode')!='source_reference_area_normalized':
            _fail(path,'Source parent uses unsupported caller area','incompatible_source_composition')
        for component in req['components']:
            matches=[(o,v) for (key,rid),(o,v) in children_by_key.items() if rid==component['child_requirement_id'] and
                o['program_id']==component['member_program_id']]
            if len(matches)!=1:_fail(path,'Missing or ambiguous actual component projection','invalid_reference')
            child,variant=matches[0]
            if variant is None or {'variant_id':variant['variant_id'],'key':variant['key']} not in recipe.get('permitted_child_variants',[]):
                _fail(path,'Parent did not permit full child tuple')
            if (not _same(variant['original_method_reference'],component['original_method_reference']) or
                    variant['key']['member_evidence_view']!=component['member_evidence_view']):_fail(path,'Immutable original child method/view differs')
            item['children'].append({'instance':{'key':child['instance_key'],'operating_group':realization['operating_group']},
                'requirement':requirements[component['child_requirement_id']],'variant':variant})
    closure={rid for item in projections for rid in exact._requirement_roles(item['requirement'],requirements)}
    if closure and any(rid not in closure and by_role[rid]['source_space'] is not None for rid in claimed):
        _fail(path,'Extra source-space physical role outside independently selected requirement closure','shared_service_conflict')
    if not used_variants<=set(child_records):_fail(path,'Unclosed child executable')
    expected=copy.deepcopy(bundle)
    plan={'owners':owner_plans,'projections':projections,'authorities':{building:{'source_requirements':list(requirements.values())}},'building_realizations':[realization]}
    exact.bind_exact_projections(expected,plan)
    expected_owners=_owners(expected)
    for owner in programmes:
        if not _same(owner['service_set_projections'],expected_owners[owner['instance_key']]['service_set_projections']):
            _fail('/constituents/'+owner['instance_key']+'/service_set_projections','Original component/role projection differs','invalid_reference')
    if selected_owners and not any(_same(native['source_context'],c['generation']['source_inputs']) for c in selected_owners):
        _fail(path+'/native_context/source_context','Retained selected executable context has no actual owner')


def _caller_realization(bundle,realization,owners):
    from . import caller_unit_water as caller
    building=realization['building_realization_id'];path='/metadata/building_realizations/'+building
    group=realization['method_qualification'];exact._source(group,path+'/method_qualification');value=group['value']
    exact._exact(value,('qualification_scope','family','template','reference_calendar','qualifications','evidence'),path+'/method_qualification/value')
    exact._evidence(value['evidence'],path+'/method_qualification/evidence')
    if (value['qualification_scope']!='caller_unit_fixed_water_programme_coverage' or value['family']!=realization['building_type'] or
            value['template']!=realization['template'] or not _same(value['reference_calendar'],bundle['metadata']['calendar']) or
            not _same(value['reference_calendar'],caller.CALENDAR) or not isinstance(value['qualifications'],list) or not value['qualifications']):
        _fail(path,'Static qualified family/template/calendar pool differs')
    pool={};last=None
    for qualification in value['qualifications']:
        exact._source(qualification,path+'/qualifications');q=qualification['value']
        exact._exact(q,('qualification_id','qualification_scope','programme_id','requirement','association','fixed_controls','evidence'),path+'/qualifications/value')
        exact._typed(q['qualification_id'],'id',path+'/qualification_id');exact._evidence(q['evidence'],path+'/evidence')
        pid=q['programme_id'];req=q['requirement'];association=q['association'];controls=q['fixed_controls']
        exact._source(association,path+'/association');exact._source(controls,path+'/fixed_controls');a=association['value']
        exact._exact(a,('programme','original_demand','service_definition','source_ruleset','fixed_controls','source_system_type','reference_calendar','evidence'),path+'/association/value')
        if not _same(a['fixed_controls'],controls):_fail(path,'Whole fixed controls/association differ')
        compiled=caller.compile_requirement(a['programme'],a['service_definition'],a['source_ruleset'],{
            'field_evidence':req['evidence'],'source_system_type':a['source_system_type'],'fixed_controls':controls,'association':association})
        if (q['qualification_scope']!='exact_apartment_programme_fixed_rule_calendar_controls' or pid in pool or
                compiled['programme']['value']['id']!=pid or not _same(compiled,req) or
                not _same(a['original_demand'],req['original_demand']) or req['family']!=value['family'] or
                req['template']!=value['template'] or not _same(req['reference_calendar'],value['reference_calendar'])):
            _fail(path,'Whole independent per-ID fixed source association differs')
        locator=req['programme']['locator']
        if not locator.startswith('/') or not locator[1:].isdigit():_fail(path,'Original source record order missing')
        order=(req['programme']['path'],int(locator[1:]))
        if last is not None and order<=last:_fail(path,'Static proof pool source order differs')
        last=order;pool[pid]=q
    declaration={k:v for k,v in realization.items() if k not in {'source_requirements','method_qualification'}}
    entries=caller.resolve_caller_unit_inventory(declaration,{pid:q['requirement'] for pid,q in pool.items()})
    selected=[]
    for u in declaration['unit_inventory']['units']:
        for pid in u['programme_ids']:
            if pid not in selected:selected.append(pid)
    if not _same(realization['source_requirements'],[pool[pid]['requirement'] for pid in selected]):
        _fail(path,'Actual declared requirement order/coverage differs from static pool')
    retained=[c for c in owners.values() if c.get('building_realization_id')==building]
    owner_plans=[];projections=[];covered=set();claims=set();expected=copy.deepcopy(bundle)
    expected_owners=_owners(expected)
    for owner in retained:
        key=(building,owner.get('unit_id'));entry=entries.get(key)
        if entry is None:_fail(path,'Foreign caller unit owner/claim','shared_service_conflict')
        unit=entry['unit'];where='/constituents/'+owner['instance_key']
        if 'operating_group' not in owner['generation'] or owner['generation']['operating_group'] is not None:
            _fail(where+'/generation/operating_group','Caller physical/programme water uses a null group','operating_group_conflict')
        extent={'value':unit['floor_area_m2'],'unit':'m2','evidence':unit['area_evidence']}
        if not _same(owner['basis_bindings'],{'multiplicity':1,'extents':{'floor_area':extent}}):
            _fail(where,'Actual caller A/evidence/multiplicity differs','incompatible_basis')
        if owner['owner_kind']=='physical_service':
            if (owner['physical_binding_kind']!=CALLER or key in covered or owner['physical_id']!=unit['physical_id'] or
                    owner['source_service_id']!=unit['source_service_id']):_fail(where,'Caller one-owner identity differs','shared_service_conflict')
            covered.add(key);entry=copy.deepcopy(entry);entry['fixed_controls']=pool[entry['water_authority_programme_id']]['fixed_controls']
            inputs=owner['inputs'];clock=bundle['metadata']['calendar']
            if (set(inputs)!={'water_method','source_geometry_departure','year','holidays'} or
                    inputs['water_method']!=caller.METHOD or inputs['source_geometry_departure']!='caller_unit_area' or
                    not _same(inputs['year'],clock['year']) or not _same(inputs['holidays'],clock['holidays'])):
                _fail(where+'/inputs','Exact retained fixed-water method/departure/calendar operands required')
            instance={'key':owner['instance_key'],'inputs':{k:v for k,v in inputs.items() if k not in {'year','holidays'}}}
            resolved,plan=caller._physical_result(instance,entry,bundle['metadata']['calendar'])
            _check_resolved(owner,resolved,None)
            if not _same(owner['shared_services'],resolved['shared_services']):_fail(where,'Whole caller source/control/A/B/W authority differs')
            owner_plans.append(plan)
        else:
            pid=owner['program_id'];claim=(key,pid)
            if pid not in unit['programme_ids'] or claim in claims:_fail(where,'Duplicate or foreign alternative view','shared_service_conflict')
            claims.add(claim);req=pool[pid]['requirement'];programme=req['programme']['value']
            if (owner['required_service_sets']!=[req] or owner['required_service_links'] or
                    any(owner['source'].get(k)!=programme[v] for k,v in (
                        ('source_id','source_id'),('building_type','building_type'),('template','template'),('evidence_view','evidence_view'),
                        ('source_family','source_family'))) or
                    any(d['slot']=='hot_water_volume' for d in owner['demands']) or 'hot_water_volume' in owner['schedule_ids']):
                _fail(where,'Alternative programme changed or owns original water')
            projections.append({'instance_key':owner['instance_key'],'building_realization_id':building,'unit_id':unit['unit_id'],'requirement':req})
            expected_owners[owner['instance_key']]['service_set_projections']=[]
    if covered!=set(entries):_fail(path,'Exactly one physical owner for every declared caller unit required','invalid_reference')
    caller.bind_caller_water(expected,{'owners':owner_plans,'projections':projections,'building_realizations':[]})
    for owner in retained:
        wanted=expected_owners[owner['instance_key']]
        field='generation' if owner['owner_kind']=='physical_service' else 'service_set_projections'
        if field=='generation':
            if owner['generation'].get('water_method_receipt')!=wanted['generation']['water_method_receipt']:_fail(path,'Fixed method operand/zero draw receipt differs')
        elif not _same(owner[field],wanted[field]):_fail(path,'Caller projection/reference/target differs','invalid_reference')


def _actors(bundle):
    """Reconstruct actors from selected method/source, never from seed receipts."""
    actors=[];seen=set()
    for owner in bundle['constituents']:
        inputs=owner['inputs'];context=owner['generation'].get('source_inputs',{})
        method=context.get('method');family=owner['source']['source_family'];kind=owner['owner_kind']
        key=owner['instance_key'];building=owner.get('building_realization_id');unit=owner.get('unit_id')
        stock=family=='existing_stock_source_fixture' and method=='resstock_time_allocation_with_selected_source_companions'
        apartment=method=='unit_occupancy_interior_lighting'
        if not stock and not apartment:continue
        n=inputs.get('residents')
        if kind!='program':_fail('/constituents/'+key,'Retained actor lacks programme authority')
        if stock:
            if (type(n) not in (int,float) or not math.isfinite(n) or n<0 or n!=0 and int(n)==0):
                _fail('/constituents/'+key,'Retained stock actor lacks original resident operand authority')
            if building is not None or unit is not None:_fail('/constituents/'+key,'Stock actor has caller unit identity')
            actor='stock';action='generate'
        else:
            if type(n) is not int or n<0:_fail('/constituents/'+key,'Retained apartment actor requires integer cohort')
            if (family not in {'code_prototype_rules','existing_stock_benchmark'} or
                    owner['source'].get('building_type') not in {'HighriseApartment','MidriseApartment'} or
                    not isinstance(building,str) or not building or not isinstance(unit,str) or not unit):
                _fail('/constituents/'+key,'Retained apartment actor source/actual identity differs')
            if (building,unit) in seen:_fail('/constituents/'+key,'Duplicate actual apartment actor','shared_service_conflict')
            seen.add((building,unit));actor='apartment_adapter';action='skip_n0' if n==0 else 'generate'
        actors.append({'actor_kind':actor,'instance_key':key,'building_realization_id':building,'unit_id':unit,'stochastic_action':action})
    return actors


def _seed_closure(bundle):
    from .seeds import assign_physical_unit_sequence,validate_physical_unit_sequence
    generation=bundle['generation']
    # Independently generated input bundles keep their original allocations.
    if generation.get('method')=='precomputed_bundle_composition_v1':
        all_actors=_actors(bundle);seen=set()
        for receipt in generation.get('input_generation_receipts',[]):
            keys=receipt.get('physical_unit_seed_sequence',[])
            selected={r.get('instance_key') for r in keys}
            actors=[a for a in all_actors if a['instance_key'] in selected]
            expected=assign_physical_unit_sequence(receipt.get('master_seed'),actors)
            if receipt.get('physical_unit_seed_sequence')!=expected:_fail('/generation','Input actor closure/order/seed differs','invalid_reference')
            if seen&selected:_fail('/generation','Repeated retained actor allocation','invalid_reference')
            seen.update(selected)
            validate_physical_unit_sequence(dict(bundle,generation=receipt))
        if seen!={a['instance_key'] for a in all_actors}:_fail('/generation','Input allocation dropped a retained source actor','invalid_reference')
        # Required top-level empty chain denotes preservation, not reseeding.
        if any(generation.get(k) for k in ('physical_unit_seed_sequence','residential_unit_order','unit_seeds')):
            _fail('/generation','Precomputed composition cannot reallocate source actors','invalid_reference')
        return
    expected=assign_physical_unit_sequence(generation.get('master_seed'),_actors(bundle))
    if generation.get('physical_unit_seed_sequence')!=expected:
        _fail('/generation/physical_unit_seed_sequence','Retained sequence differs from independent selected source actors','invalid_reference')
    validate_physical_unit_sequence(bundle)


def _upgrade_bundle(bundle):
    """Upgrade only previously validated old inputs; never fill missing 1.2 data."""
    from .contract import validate_bundle
    from .owners import identity_fields,upgrade_generated_reference_identities
    from .seeds import assign_physical_unit_sequence
    validate_bundle(bundle)
    previous=bundle['schema_version']
    if previous not in {'1.0.0','1.1.0'}:_fail('/schema_version','Only explicit old versions may upgrade')
    result=copy.deepcopy(bundle)
    for record in result['constituents']+result['bindings']:
        record.update(identity_fields(record,'1.1.0'))
        if record['owner_kind']=='physical_service':record['physical_binding_kind']='legacy_whole'
    if previous=='1.0.0':upgrade_generated_reference_identities(result)
    for owner in result['constituents']:
        if owner['owner_kind']!='physical_service':owner.update(required_service_sets=[],service_set_projections=[])
    result['schema_version']='1.2.0';result['metadata']['building_realizations']=[]
    generation=result['generation'];generation['upgraded_from']=previous
    sequence=assign_physical_unit_sequence(generation.get('master_seed'),_actors(result))
    if generation.get('residential_unit_order',[])!=[a['instance_key'] for a in sequence] and sequence:
        _fail('/generation','Legacy retained actor order differs from source method')
    generation.update(physical_unit_seed_sequence=sequence,
        residential_unit_order=[a['instance_key'] for a in sequence],
        unit_seeds={a['instance_key']:a['unit_seed'] for a in sequence})
    return result


def _composed_water(bundle,owner,mixture,members,physical):
    """Recompute whole water from actual source-basis trajectories exactly once."""
    from .mixtures import _basis_scale
    from .comparison import _close
    groups={};path='/constituents/'+owner['instance_key']
    for source,weight in members+physical:
        for index in source['binding_indices']:
            binding=bundle['bindings'][index]
            if binding['kind']!='load' or binding['reference_target']['quantity']!='hot_water_volume':continue
            demand=next(d for d in source['demands'] if d['demand_id']==binding['demand_id'])
            group=(demand['quantity'],'m3/s',demand['fuel'],demand['host'])
            factor=weight*_basis_scale(source,demand['basis'],mixture)
            if source['owner_kind']=='physical_service':
                factor=source['shared_services'][0]['extent']['value']/mixture['denominator']['value']
            groups.setdefault(group,[]).append((index,factor))
    actual={}
    for index in owner['binding_indices']:
        binding=bundle['bindings'][index]
        if binding['kind']!='load' or binding['reference_target']['quantity']!='hot_water_volume':continue
        demand=next(d for d in owner['demands'] if d['demand_id']==binding['demand_id'])
        carrier='m3/s' if demand['unit'].startswith('m3/s') else None
        group=(demand['quantity'],carrier,demand['fuel'],demand['host'])
        if group in actual:_fail(path,'Duplicate composed water channel')
        actual[group]=(binding,demand)
    if set(actual)!=set(groups):_fail(path,'Composed water channel coverage differs from actual selected source owners')
    # These are the unchanged named comparison-policy tolerances. Validation
    # never trusts caller-supplied metadata to widen its scientific checks.
    volume={'abs_tol':1e-12,'rel_tol':1e-8};fraction={'abs_tol':1e-8,'rel_tol':1e-6}
    for group,terms in groups.items():
        binding,demand=actual[group];evidence=demand['evidence']
        if evidence.get('method')!='actual_generated_bound_trajectory_sum':_fail(path,'Composed water lacks source trajectory authority')
        components=evidence.get('components',[])
        if (len(components)!=len(terms) or any(c.get('binding_index')!=i or not _same(c.get('factor'),factor)
                for c,(i,factor) in zip(components,terms)) or
                not _same(binding['reference_target']['evidence'],evidence)):
            _fail(path,'Composed water component identity/count/order or extent factor differs')
        total=math.fsum(factor*bundle['bindings'][i]['reference_target']['total'] for i,factor in terms)
        if (not _close(binding['reference_target']['total'],total,volume) or
                not _close(demand['annual_target']['total'],total,volume)):
            _fail(path,'Composed target differs from unique physical whole targets/root denominator')
        amplitude=math.fsum(factor*bundle['bindings'][i]['effective_magnitude']['value'] for i,factor in terms)
        values=bundle['schedules'][binding['schedule_id']]['values']
        for hour,actual_value in enumerate(values):
            power=math.fsum(factor*bundle['bindings'][i]['effective_magnitude']['value']*
                bundle['schedules'][bundle['bindings'][i]['schedule_id']]['values'][hour] for i,factor in terms)
            expected=(bundle['schedules'][bundle['bindings'][terms[0][0]]['schedule_id']]['values'][hour]
                if len(terms)==1 else power/amplitude if amplitude else 0.0)
            if not _close(actual_value,expected,fraction):
                _fail(path+'/schedule_ids/'+binding['slot'],'Composed hourly water differs from actual selected trajectories')


def validate_physical_graph(bundle: dict) -> None:
    """Strict offline entry point; malformed retained proof is always contextual."""
    from .contract import _finite,_schema_errors,_validate_generated_binding_references
    _finite(bundle)
    if bundle.get('schema_version')!='1.2.0':_fail('/schema_version','Physical graph requires 1.2.0','unsupported_schema')
    _schema_errors(bundle,'bundle','1.2.0')
    _validate_generated_binding_references(bundle)
    try:_validate_physical_graph(bundle)
    except GeneratorError:raise
    except (KeyError,TypeError,AttributeError,ValueError,IndexError) as error:
        raise GeneratorError('source_integrity','/','Incomplete retained physical source proof') from error


def _validate_physical_graph(bundle):
    """Validate retained original proofs, actual owners, projections and selection."""
    if bundle.get('schema_version')!='1.2.0':_fail('/schema_version','Physical graph requires 1.2.0','unsupported_schema')
    owners=_owners(bundle);_source_consistency(bundle)
    # Normalize only the 1.2 legacy discriminator for the unchanged C5 proof.
    from .services import validate_service_links,_whole_proof
    legacy=copy.deepcopy(bundle)
    for owner in legacy['constituents']+legacy['bindings']:
        if owner.get('physical_binding_kind')=='legacy_whole':owner.pop('physical_binding_kind')
    legacy_owners=_owners(legacy);legacy_proofs={}
    physical={};roles=set();units=set();sids={};raw={}
    for owner in owners.values():
        if owner['owner_kind']!='physical_service':
            exact._no_double_listing(owner['required_service_links'],owner['required_service_sets'])
            continue
        identity=physical_identity(owner);_binding(bundle,owner)
        if identity in physical:
            if identity[0]!='legacy_whole':_fail('/constituents','Duplicate scoped physical owner','shared_service_conflict')
            proof=_whole_proof(legacy,legacy_owners[owner['instance_key']])
            if proof!=legacy_proofs[identity]:
                _fail('/constituents','Legacy aliases have conflicting complete physical proof','shared_service_conflict')
        elif identity[0]=='legacy_whole':
            legacy_proofs[identity]=_whole_proof(legacy,legacy_owners[owner['instance_key']])
        physical[identity]=owner
        kind=identity[0];sid=owner['source_service_id'];local=owner['physical_id']
        if sid in sids and sids[sid]!=kind or local in raw and raw[local]!=kind:
            _fail('/constituents','Cross-mode SID or raw physical ID is ambiguous','shared_service_conflict')
        sids[sid]=kind;raw[local]=kind
        if kind=='exact_source_role':
            key=(owner['building_realization_id'],owner['source_fixture_role_id'])
            if key in roles:_fail('/constituents','Duplicate role owner','shared_service_conflict')
            roles.add(key)
        if kind==CALLER:
            key=(owner['building_realization_id'],owner['unit_id'])
            if key in units:_fail('/constituents','Duplicate caller unit owner','shared_service_conflict')
            units.add(key)
    validate_service_links(legacy)
    realizations={}
    for realization in bundle['metadata']['building_realizations']:
        building=realization['building_realization_id']
        if building in realizations:_fail('/metadata/building_realizations','Duplicate realization','shared_service_conflict')
        realizations[building]=realization
        if not any(c.get('building_realization_id')==building for c in owners.values()):_fail('/metadata/building_realizations','Unused realization')
        if realization['mode']=='exact_source_fixture_extents':_exact_realization(bundle,realization,owners)
        else:_caller_realization(bundle,realization,owners)
    for owner in owners.values():
        building=owner.get('building_realization_id')
        if building is not None and building not in realizations:_fail('/constituents/'+owner['instance_key'],'Unknown realization','invalid_reference')
        if owner['owner_kind']!='physical_service' and building is None and (owner['required_service_sets'] or owner['service_set_projections']):
            _fail('/constituents/'+owner['instance_key'],'Set owner has no actual realization')
    _seed_closure(bundle)
    for owner in owners.values():
        receipt=owner['generation'].get('service_set_selection')
        if owner['owner_kind']=='derived_result' and owner['generation'].get('method')=='conserved_constituent_mixture' and receipt is None:
            _fail('/constituents/'+owner['instance_key']+'/service_set_selection','Derived 1.2 composition requires its combined participation receipt')
        if receipt is not None:
            mixture=owner['inputs'];members=[(owners[m['instance_key']],m['weight']) for m in mixture['members']]
            physical,expected=_select_physical_services(bundle,mixture,members)
            if not _same(receipt,expected):_fail('/constituents/'+owner['instance_key']+'/service_set_selection','Combined selection reasons/order/authority differ')
            if owner['generation'].get('method')=='conserved_constituent_mixture':
                _composed_water(bundle,owner,mixture,members,physical)


def _overlap(members):
    for owner,weight in members:
        if (owner['owner_kind']=='derived_result' and owner['generation'].get('service_set_selection',{}).get('effective_physical_members')):
            _fail('/mixture/members','Weighted nesting of composed physical water is unresolved','incompatible_source_composition')
    for i,(left,lw) in enumerate(members):
        lp=left.get('service_set_projections',[])
        for right,rw in members[i+1:]:
            rp=right.get('service_set_projections',[])
            if left.get('building_realization_id')!=right.get('building_realization_id'):continue
            left_roles={r for p in lp for r in p.get('role_ids',[])}
            right_roles={r for p in rp for r in p.get('role_ids',[])}
            parents=any(p.get('projection_kind')=='source_components_density' for p in lp+rp)
            same_unit=(left.get('unit_id') is not None and left.get('unit_id')==right.get('unit_id'))
            if parents and left_roles&right_roles or same_unit and lw>0 and rw>0:
                _fail('/mixture/members','Additive source parent/child or alternative-view overlap','incompatible_source_composition')


def select_physical_services(bundle: dict, mixture: dict, members: list[tuple[dict,float]]) -> tuple[list[tuple[dict,int]],dict]:
    """Explicit-first ordered whole participation; validate zero-weight coverage."""
    from .contract import validate_bundle
    validate_bundle(bundle)
    return _select_physical_services(bundle,mixture,members)


def _select_physical_services(bundle,mixture,members):
    owners=_owners(bundle);_overlap(members);selected=[];seen=set();reasons=[]
    for owner,weight in members:
        if (owner.get('instance_key') not in owners or not _same(owner,owners[owner['instance_key']]) or
                owner.get('owner_kind')=='physical_service' or type(weight) not in (int,float) or
                not math.isfinite(weight) or weight<0):
            _fail('/mixture/members','Participation must identify actual retained programme/result owners','invalid_reference')
    def select(key,reason):
        owner=owners.get(key)
        if owner is None or owner['owner_kind']!='physical_service':_fail('/mixture/service_members','Actual physical owner missing','invalid_reference')
        identity=physical_identity(owner);deduplicated=identity in seen
        reference=_reference(bundle,owner)
        if not deduplicated:seen.add(identity);selected.append((owner,1))
        reasons.append(dict(reason,physical=reference,deduplicated=deduplicated))
    explicit=mixture.get('service_members',[])
    for i,selector in enumerate(explicit):select(selector['instance_key'],{'reason_kind':'explicit_service_selection','selector_index':i})
    positive=[]
    for owner,weight in members:
        if weight<=0:continue
        positive.append(owner['instance_key'])
        links={r['source_service_id']:r for r in owner.get('service_links',[])}
        for requirement in owner['required_service_links']:
            link=links[requirement['source_service_id']]
            select(link['instance_key'],{'reason_kind':'legacy_required_link','programme_instance_key':owner['instance_key'],
                'source_channel':'hot_water_volume','source_service_id':requirement['source_service_id'],'original_requirement':copy.deepcopy(requirement)})
        projections={p['requirement_id']:p for p in owner['service_set_projections']}
        for requirement in owner['required_service_sets']:
            projection=projections[requirement['requirement_id']]
            if requirement['kind']=='original_apartment_unit_demand':
                select(projection['physical']['instance_key'],{'reason_kind':'caller_unit_requirement',
                    'programme_instance_key':owner['instance_key'],'requirement_id':requirement['requirement_id'],'unit_id':owner['unit_id']})
            else:
                for item in projection['members']:
                    select(item['physical']['instance_key'],{'reason_kind':'exact_required_set','programme_instance_key':owner['instance_key'],
                        'requirement_id':requirement['requirement_id'],'role_id':item['role_id']})
    if selected:
        basis=mixture.get('result_basis');denominator=mixture.get('denominator',{})
        if (basis not in {'floor_area','absolute'} or denominator.get('unit')!={'floor_area':'m2','absolute':'1'}.get(basis) or
                type(denominator.get('value')) not in (int,float) or not math.isfinite(denominator['value']) or denominator['value']<=0):
            _fail('/mixture/denominator','Physical participation requires positive explicit matching denominator','incompatible_basis')
    return selected,{'explicit_service_members':copy.deepcopy(explicit),'positive_programme_keys':positive,
        'effective_physical_members':[_reference(bundle,c) for c,w in selected],'reasons':reasons}


def required_graph_closure(bundle: dict, keys: list[str]) -> list[str]:
    """Close child projections and every generated owner reference before mapping."""
    from .contract import validate_bundle
    validate_bundle(bundle);owners=_owners(bundle);result=[];seen=set()
    def visit(key):
        if key in seen:return
        if key not in owners:_fail('/constituents/'+key,'Required retained owner missing','invalid_reference')
        seen.add(key);result.append(key)
        # SourceObjects retain immutable upstream identifiers, never graph keys.
        def graph_walk(value):
            if isinstance(value,dict) and set(value)=={'path','sha256','locator','value'}:return
            if isinstance(value,dict):
                for name in ('instance_key','member_instance_key'):
                    if name in value:visit(value[name])
                for name in ('member_instance_keys','active_members'):
                    for target in value.get(name,[]):visit(target)
                for child in value.values():graph_walk(child)
            elif isinstance(value,list):
                for child in value:graph_walk(child)
        graph_walk(owners[key])
    for key in keys:visit(key)
    # Retained whole-original realization proofs close their actual programmes;
    # projection never rewrites that immutable selected-source association.
    buildings={owners[key].get('building_realization_id') for key in result}
    for owner in owners.values():
        if owner.get('building_realization_id') in buildings and owner.get('building_realization_id') is not None:
            visit(owner['instance_key'])
    # Original seed chains are source-significant dependencies of retained actors.
    def seed_owners(generation):
        for actor in generation.get('physical_unit_seed_sequence',[]):visit(actor['instance_key'])
        for child in generation.get('input_generation_receipts',[]):seed_owners(child)
    seed_owners(bundle['generation'])
    return result
