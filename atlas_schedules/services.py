"""Close already generated whole-service ownership; no source or random inference."""
import copy
import math

from .errors import GeneratorError
from .owners import owner_identity
from .budgets import reference_budget
from .calendar import evaluate_rules


def _fail(path,message,code='requires_binding'):
    raise GeneratorError(code,path,message)


def prepare_required_service_links(resolved_instances,version):
    """Validate exact original programme aliases before any group RNG draw."""
    owners={instance['key']:(instance,resolved) for instance,resolved in resolved_instances}
    if len(owners)!=len(resolved_instances):_fail('/instances','Duplicate generated owner key','invalid_reference')
    plans=[]
    for instance,resolved in resolved_instances:
        if owner_identity(resolved)[0]!='program':continue
        path='/instances/'+instance['key']+'/service_links'
        if resolved.get('required_contract_version','1.0.0')=='1.1.0' and version!='1.1.0':
            _fail(path,'This exact source programme requires explicit typed ownership contract1.1.0','unsupported_schema')
        required=resolved.get('required_service_links',[])
        expected={r['source_service_id'] for r in required}
        supplied=instance.get('service_links',{})
        if not isinstance(supplied,dict) or set(supplied)!=expected:
            _fail(path,'Exact required hot_water_volume links for programme '+resolved['program_id']+' are '+str(sorted(expected)))
        for requirement in required:
            sid=requirement['source_service_id'];service_key=supplied[sid];where=path+'/'+sid
            if service_key not in owners:_fail(where,'Required active programme hot_water_volume has no selected physical owner '+str(service_key))
            service_instance,service=owners[service_key]
            if owner_identity(service)!=('physical_service',sid,service_instance.get('physical_id')):
                _fail(where,'Required active programme channel refers to another physical/source service','shared_service_conflict')
            if requirement.get('required') is not True or requirement.get('source_channel')!='hot_water_volume':
                _fail(where,'Invalid original active service requirement','source_integrity')
            group=instance['operating_group'] if instance['operating_group'] is not None else instance['key']
            other=service_instance['operating_group'] if service_instance['operating_group'] is not None else service_key
            if group!=other:_fail(where,'Programme and physical fixture require the same explicit operating group','operating_group_conflict')
            programme_context=resolved['inputs']['source_context'];service_context=service['inputs']['source_context']
            config=programme_context.get('source_hoo_configuration_id')
            if not config or config!=service_context.get('source_hoo_configuration_id'):
                _fail(where,'Programme and physical fixture require the same exact source/view HOO context','operating_group_conflict')
            if any(resolved['source'][k]!=service['source'][k] for k in ('building_type','template')):
                _fail(where,'Programme and physical fixture source family/template differ','shared_service_conflict')
            definition=service['source_service_definition'];original=requirement['original_demand']
            if (definition['id']!=sid or resolved['source']['source_id'] not in definition['beneficiary_program_ids'] or
                    original.get('service_id')!=sid or original.get('demand_id')!=sid or
                    original.get('quantity')!='hot_water_volume' or
                    any(original.get(k)!=definition['load'].get(k) for k in ('value','unit','basis','schedule_id'))):
                _fail(where,'Original programme/service beneficiary, value, unit, basis or schedule differs','source_integrity')
            demand=service['demands'][0]
            expected_target=reference_budget(demand,service['inputs']['reference_channels']['hot_water_volume'])
            if expected_target!=service['inputs']['reference_budgets'].get(sid):
                _fail(where,'Physical service original annual target differs before RNG','source_integrity')
            plans.append({'programme_instance_key':instance['key'],'service_instance_key':service_key,
                'source_service_id':sid,'physical_id':service['physical_id'],'operating_group':group,
                'original_programme_load':copy.deepcopy(original),'source_reference_target':copy.deepcopy(expected_target),
                'source_requirement_evidence':copy.deepcopy(requirement['evidence'])})
    return plans


def bind_required_service_links(bundle,plans):
    """Attach aliases to the actual generated owner/binding without new draws."""
    owners=_owners(bundle)
    for plan in plans:
        programme=owners[plan['programme_instance_key']];service=owners[plan['service_instance_key']]
        indices=[i for i in service['binding_indices'] if bundle['bindings'][i]['kind']=='load' and
                 bundle['bindings'][i].get('demand_id')==plan['source_service_id']]
        if len(indices)!=1:_fail('/service_links/'+plan['source_service_id'],'No unique actual generated physical volume binding','invalid_reference')
        index=indices[0];binding=bundle['bindings'][index]
        if binding['reference_target']!=plan['source_reference_target']:
            _fail('/service_links/'+plan['source_service_id'],'Generated physical binding changed original source target','source_integrity')
        programme.setdefault('service_links',[]).append({'required':True,'source_channel':'hot_water_volume',
            'owner_kind':'physical_service','source_service_id':plan['source_service_id'],'physical_id':plan['physical_id'],
            'instance_key':service['instance_key'],'operating_group':plan['operating_group'],'binding_index':index,
            'demand_id':binding['demand_id'],'slot':binding['slot'],'schedule_id':binding['schedule_id'],
            'evidence':{'original_programme_load':copy.deepcopy(plan['original_programme_load']),
                'source_reference_target':copy.deepcopy(plan['source_reference_target']),
                'source_requirement':copy.deepcopy(plan['source_requirement_evidence']),
                'interpretation':'Required original programme water alias points to one actual generated whole physical fixture; no local duplicate demand or schedule'}})


def resolve_physical_service(instance,calendar,resources):
    """Resolve original volume/controls before RNG, with exact physical operands."""
    identity=owner_identity(instance)
    if identity[0]!='physical_service':_fail('/owner_kind','Exact physical-service identity required')
    _,sid,physical_id=identity
    try:record=resources.get('reference','physical-service__'+sid)
    except GeneratorError as error:
        raise GeneratorError('requires_binding','/source_service_id','No qualified source recipe for physical service '+sid) from error
    definition=record.get('definition');recipe=record.get('recipe');provenance=record.get('provenance',{})
    if (not isinstance(definition,dict) or definition.get('id')!=sid or not isinstance(recipe,dict) or
            recipe.get('required_contract_version')!='1.1.0' or recipe.get('ownership')!='instantiate_once' or
            recipe.get('allocation_mode')!='whole' or provenance.get('source_path')!='data/definition-releases/v0.1.1/services.json' or
            not provenance.get('source_locator') or not provenance.get('source_sha256')):
        _fail('/source_service_id','Exact source service recipe/identity/pointer/hash proof is missing','source_integrity')
    if (calendar.get('year')!=recipe['reference_year'] or calendar.get('clock')!='local_standard_time' or calendar.get('holidays',[])!=[]):
        _fail('/calendar','Outside exact native-qualified physical service reference calendar')
    inputs=instance.get('inputs',{})
    if not isinstance(inputs,dict):_fail('/inputs','Explicit physical fixture inputs required')
    basis=definition['load']['basis']
    required={'source_hoo_configuration_id','physical_fixture_evidence'}
    if basis=='floor_area':required|={'fixture_floor_area_m2','fixture_space_multiplier','fixture_extent_evidence'}
    missing=required-set(inputs)
    if missing:_fail('/inputs/'+sorted(missing)[0],'Required source/physical fixture operand missing for '+sid)
    if inputs.get('allocation_mode','whole')!='whole':
        _fail('/inputs/allocation_mode','Components/already-allocated fixtures require source total/allocation/upstream proof unavailable for '+sid)
    unknown=set(inputs)-required-{'allocation_mode'}
    if unknown:_fail('/inputs/'+sorted(unknown)[0],'Unknown physical source fixture operand','unknown_input')
    config=inputs['source_hoo_configuration_id']
    variant=recipe['configurations'].get(config) if isinstance(config,str) else None
    if variant is None:_fail('/inputs/source_hoo_configuration_id','Exact source SID/family/template/view configuration required for '+sid)
    if not isinstance(inputs['physical_fixture_evidence'],dict) or not inputs['physical_fixture_evidence']:
        _fail('/inputs/physical_fixture_evidence','Caller physical fixture identity/source role evidence required')
    physical=copy.deepcopy(instance.get('basis_bindings',{}))
    multiplicity=physical.get('multiplicity',1)
    if set(physical)-{'extents','multiplicity'} or type(multiplicity) not in (int,float) or multiplicity!=1:
        _fail('/basis_bindings','Whole fixture has one explicit source extent and unit multiplicity')
    operands={}
    if basis=='floor_area':
        for name in ('fixture_floor_area_m2','fixture_space_multiplier'):
            value=inputs[name]
            if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
                _fail('/inputs/'+name,'Explicit positive finite actual fixture operand required')
            operands[name]=value
        receipt=inputs['fixture_extent_evidence']
        if (not isinstance(receipt,dict) or set(receipt)!={'area','multiplier'} or
                not isinstance(receipt['area'],dict) or not isinstance(receipt['multiplier'],dict) or
                receipt['area'].get('value')!=operands['fixture_floor_area_m2'] or receipt['area'].get('unit')!='m2' or
                receipt['multiplier'].get('value')!=operands['fixture_space_multiplier'] or receipt['multiplier'].get('unit')!='1'):
            _fail('/inputs/fixture_extent_evidence','Separate actual area/multiplier original values/units/evidence required')
        extent_value=operands['fixture_floor_area_m2']*operands['fixture_space_multiplier'];unit='m2'
        if not math.isfinite(extent_value):_fail('/inputs/fixture_floor_area_m2','Physical extent product is nonfinite')
    elif basis=='absolute':extent_value=1;unit='1'
    else:_fail('/source_service_id','Unqualified source physical service basis','source_integrity')
    extent=physical.get('extents',{}).get(basis)
    if (set(physical.get('extents',{}))!={basis} or not isinstance(extent,dict) or set(extent)!={'value','unit','evidence'} or
            type(extent['value']) not in (int,float) or extent['value']!=extent_value or extent['unit']!=unit or
            not isinstance(extent['evidence'],dict) or not extent['evidence']):
        _fail('/basis_bindings/extents/'+basis,'Whole source extent must equal actual area×multiplier once, or absolute unit extent')
    resolved=copy.deepcopy(recipe['resolved'])
    if resolved.get('source_service_id')!=sid or resolved.get('owner_kind')!='physical_service' or 'program_id' in resolved:
        _fail('/source_service_id','Resolved physical source identity differs','source_integrity')
    channels={'hot_water_volume':evaluate_rules(variant['reference_source'],calendar['year'],[])['values']}
    resolved['inputs']=dict(copy.deepcopy(inputs),year=calendar['year'],holidays=[],reference_channels=channels,
        reference_budgets={d['demand_id']:reference_budget(d,channels[d['slot']]) for d in resolved['demands']},
        companion_rules=copy.deepcopy(variant['companion_rules']),source_context=copy.deepcopy(variant['source_context']))
    resolved['physical_id']=physical_id
    resolved['shared_services']=[{'source_service_id':sid,'physical_id':physical_id,'demand_id':sid,
        'mode':'whole','ownership':'instantiate_once','extent':extent,'physical_operands':operands,
        'physical_operand_evidence':copy.deepcopy(inputs.get('fixture_extent_evidence',inputs['physical_fixture_evidence'])),
        'source_service_definition':copy.deepcopy(definition),'adaptation':copy.deepcopy(variant['adaptation']),
        'interpretation':'Original source target remains unscaled; actual whole extent converts once during physical composition'}]
    return resolved


def _owners(bundle):
    owners={c['instance_key']:c for c in bundle['constituents']}
    if len(owners)!=len(bundle['constituents']):
        _fail('/constituents','Generated owner keys must be unique','invalid_reference')
    return owners


def _whole_proof(bundle,owner):
    identity=owner_identity(owner)
    if identity[0]!='physical_service':_fail('/shared_services','A typed physical-service owner is required')
    path='/shared_services/'+identity[2]
    demands=[d for d in owner['demands'] if d['quantity']=='hot_water_volume']
    descriptors=owner['shared_services']
    if len(demands)!=1 or len(owner['demands'])!=1 or len(descriptors)!=1:
        _fail(path,'Whole physical fixture requires exactly one source volume demand and ownership descriptor')
    demand=demands[0];descriptor=descriptors[0]
    if (descriptor.get('mode')!='whole' or descriptor.get('ownership')!='instantiate_once' or
            descriptor.get('source_service_id')!=identity[1] or descriptor.get('physical_id')!=identity[2] or
            descriptor.get('demand_id')!=demand['demand_id']):
        _fail(path,'Whole source/physical/demand ownership proof differs','shared_service_conflict')
    multiplicity=owner.get('basis_bindings',{}).get('multiplicity',1)
    if type(multiplicity) not in (int,float) or multiplicity!=1:
        _fail(path,'Whole physical fixture multiplicity is one; select actual distinct physical IDs')
    extent=descriptor.get('extent')
    if (not isinstance(extent,dict) or set(extent)!={'value','unit','evidence'} or not extent['evidence'] or
            type(extent['value']) not in (int,float) or not math.isfinite(extent['value']) or extent['value']<=0 or
            extent['unit']!={'floor_area':'m2','dwelling_unit':'dwelling','person':'person','absolute':'1'}.get(demand['basis']) or
            owner.get('basis_bindings',{}).get('extents',{}).get(demand['basis'])!=extent):
        _fail(path,'Whole source extent must match the actual physical owner binding')
    physical=owner.get('basis_bindings',{})
    if (set(physical.get('extents',{}))!={demand['basis']} or
            demand['basis']=='absolute' and (extent['value']!=1 or 'floor_area_m2' in physical)):
        _fail(path,'Whole absolute fixture uses unit extent; unrelated physical bases/area scaling are not selections')
    bindings=[bundle['bindings'][i] for i in owner['binding_indices']]
    volume=[b for b in bindings if b.get('demand_id')==demand['demand_id']]
    if len(volume)!=1:_fail(path,'Whole fixture has no unique generated source-volume binding')
    # Exact complete physical semantics and trajectories. Scoped owner/schedule
    # identifiers alone are declaration differences, never physical proof.
    return {'source_service_id':identity[1],'physical_id':identity[2],
        'source':copy.deepcopy(owner['source']),'inputs':copy.deepcopy(owner['inputs']),
        'basis_bindings':copy.deepcopy(owner.get('basis_bindings',{})),
        'demands':copy.deepcopy(owner['demands']),'controls':copy.deepcopy(owner['controls']),
        'shared_services':copy.deepcopy(descriptors),'evidence':copy.deepcopy(owner['evidence']),
        'generation':copy.deepcopy(owner['generation']),
        'bindings':[{k:copy.deepcopy(v) for k,v in b.items() if k not in {'instance_key','schedule_id'}} for b in bindings],
        'trajectories':{slot:bundle['schedules'][sid]['values'] for slot,sid in owner['schedule_ids'].items()}}


def _validate_original_service_requirement(bundle,programme,requirement,link,service,binding):
    """Close an alias against independently retained original source operands."""
    path='/constituents/'+programme['instance_key']+'/service_links/'+requirement['source_service_id']
    sid=requirement['source_service_id'];original=requirement['original_demand']
    evidence=link.get('evidence',{})
    if (evidence.get('original_programme_load')!=original or
            evidence.get('source_requirement')!=requirement['evidence']):
        _fail(path,'Alias differs from the independent original programme requirement','source_integrity')
    _whole_proof(bundle,service)
    definition=service['shared_services'][0].get('source_service_definition')
    physical_load=copy.deepcopy(original);physical_load['scope']='building_service'
    if (original.get('scope')!='program_service' or not isinstance(definition,dict) or
            definition.get('id')!=sid or original.get('service_id')!=sid or original.get('demand_id')!=sid or
            original.get('quantity')!='hot_water_volume' or definition.get('load')!=physical_load or
            definition.get('ownership')!='instantiate_once' or definition.get('assignment')!='consumer_host_when_applicable' or
            programme['source']['source_id'] not in definition.get('beneficiary_program_ids',[]) or
            original.get('evidence_id') not in definition.get('evidence_ids',[]) or
            requirement['evidence'].get('id')!=original.get('evidence_id') or
            any(definition.get(k)!=programme['source'].get(k) or definition.get(k)!=service['source'].get(k)
                for k in ('building_type','template')) or service['source'].get('source_id')!=sid):
        _fail(path,'Original programme load, beneficiary, assignment or physical source definition differs','source_integrity')
    locator=requirement['evidence'].get('locator')
    if not isinstance(locator,str) or not definition.get('path_id') or not locator.endswith('/'+definition['path_id']):
        _fail(path,'Original requirement locator and physical source path differ','source_integrity')
    demand=service['demands'][0]
    if (any(demand.get(k)!=physical_load.get(k) for k in ('demand_id','quantity','value','unit','basis')) or
            demand.get('slot')!='hot_water_volume' or demand.get('fuel')!='water' or demand.get('host')!='building_service' or
            demand.get('heat_fractions') is not None or physical_load.get('thermal_effects')!={} or
            physical_load.get('zone_heat_assignment')!='unresolved' or
            demand.get('evidence',{}).get('original_service')!=definition):
        _fail(path,'Generated physical volume differs from the original demand or unresolved heat semantics','source_integrity')
    from .generator import _group_context
    contexts=[]
    for owner in (programme,service):
        source=owner['generation'].get('source_inputs')
        config=owner['inputs'].get('source_hoo_configuration_id')
        if (not isinstance(source,dict) or not config or config!=source.get('source_hoo_configuration_id') or
                not isinstance(source.get('occupancy_aggregation'),dict) or
                source.get('year')!=bundle['metadata']['calendar']['year'] or
                source.get('holidays')!=bundle['metadata']['calendar'].get('holidays',[]) or
                source.get('occupancy_aggregation',{}).get('evidence_view')!=owner['source'].get('evidence_view')):
            _fail(path,'Original programme/physical configuration, view or calendar differs','operating_group_conflict')
        try:contexts.append(_group_context({'inputs':{'source_context':source},'source':owner['source']}))
        except (KeyError,TypeError) as error:
            raise GeneratorError('source_integrity',path,'Incomplete retained original group context') from error
    group=link['operating_group'];groups=bundle['generation'].get('operating_groups',{})
    if not isinstance(groups,dict) or ('operating_groups' in bundle['generation'] and group not in groups):
        _fail(path,'Original operating-group receipt is missing or malformed','operating_group_conflict')
    root=groups.get(group)
    if group in groups and (not isinstance(root,dict) or not isinstance(root.get('operating'),dict)):
        _fail(path,'Original operating-group receipt is malformed','operating_group_conflict')
    if contexts[0]!=contexts[1] or root is not None and contexts[0]!=root.get('context'):
        _fail(path,'Original consumed programme/physical/root group context differs','operating_group_conflict')
    operating=[]
    for owner in (programme,service):
        receipt=owner['generation'].get('source_context',{}).get('operating_receipt')
        if receipt is not None:
            receipt=copy.deepcopy(receipt);receipt.get('rng',{}).pop('python_version',None);operating.append(receipt)
    if root is not None:
        receipt=copy.deepcopy(root.get('operating'));receipt.get('rng',{}).pop('python_version',None);operating.append(receipt)
    if operating and any(receipt!=operating[0] for receipt in operating):
        _fail(path,'Actual programme/physical/root operating draws differ','operating_group_conflict')
    try:
        rules=service['generation']['source_inputs']['slot_sources']['hot_water_volume']
        calendar=bundle['metadata']['calendar']
        target=reference_budget(demand,evaluate_rules(rules,calendar['year'],calendar.get('holidays',[]))['values'])
    except (KeyError,TypeError) as error:
        raise GeneratorError('source_integrity',path,'Original physical water Ruleset/calendar target proof is missing') from error
    if binding['reference_target']!=target or evidence.get('source_reference_target')!=target:
        _fail(path,'Original Ruleset-derived physical/alias annual target differs','source_integrity')


def validate_service_links(bundle):
    owners=_owners(bundle)
    for programme in owners.values():
        if programme.get('owner_kind')=='physical_service':continue
        path='/constituents/'+programme['instance_key']+'/required_service_links'
        required=programme.get('required_service_links')
        if (not isinstance(required,list) or any(not isinstance(r,dict) or r.get('required') is not True or
                r.get('source_channel')!='hot_water_volume' or not isinstance(r.get('original_demand'),dict) or
                not isinstance(r.get('evidence'),dict) or not isinstance(r.get('source_service_id'),str) for r in required)):
            _fail(path,'Independent original required-service inventory is missing or malformed','source_integrity')
        links=programme.get('service_links',[])
        expected=[r['source_service_id'] for r in required]
        if (len(set(expected))!=len(expected) or len(links)!=len(required) or
                {link['source_service_id'] for link in links}!=set(expected) or
                programme.get('owner_kind')=='derived_result' and required):
            _fail(path,'Bound aliases do not cover the exact original required programme services','requires_binding')
        requirements={r['source_service_id']:r for r in required}
        for link in links:
            path='/constituents/'+programme['instance_key']+'/service_links/'+link['source_service_id']
            service=owners.get(link['instance_key'])
            if service is None:_fail(path,'Required programme channel has no generated physical-service owner')
            if owner_identity(service)!=('physical_service',link['source_service_id'],link['physical_id']):
                _fail(path,'Required programme channel points to another source/physical fixture','shared_service_conflict')
            group=link['operating_group']
            if group!=programme['generation'].get('operating_group') or group!=service['generation'].get('operating_group'):
                _fail(path,'Required programme/service operating groups differ','operating_group_conflict')
            if link['binding_index'] not in service['binding_indices']:
                _fail(path,'Required programme channel points to another owner binding','invalid_reference')
            binding=bundle['bindings'][link['binding_index']]
            if (binding['kind']!='load' or binding['reference_target']['quantity']!=link['source_channel'] or
                    binding['slot']!=link['slot'] or binding['demand_id']!=link['demand_id'] or
                    binding['schedule_id']!=link['schedule_id']):
                _fail(path,'Required programme channel does not identify the physical source volume binding','invalid_reference')
            _validate_original_service_requirement(bundle,programme,requirements[link['source_service_id']],link,service,binding)


def select_whole_services(bundle,mixture,members):
    """Ruling18 explicit-first then positive-required-link closure, data only."""
    owners=_owners(bundle);selected=[];physical={};links=[]
    def select(key):
        service=owners.get(key)
        if service is None:_fail('/mixture/service_members/'+key,'Selected whole physical owner is missing')
        proof=_whole_proof(bundle,service);physical_id=service['physical_id']
        if physical_id in physical:
            if physical[physical_id]!=proof:
                _fail('/shared_services/'+physical_id,'Repeated physical fixture has conflicting complete source/budget/extent/trajectory/metadata','shared_service_conflict')
            return True
        physical[physical_id]=proof;selected.append((service,1));return False
    explicit=mixture.get('service_members',[])
    for selector in explicit:select(selector['instance_key'])
    for programme,weight in members:
        if weight<=0:continue
        for link in programme.get('service_links',[]):
            deduplicated=select(link['instance_key'])
            links.append({'programme_instance_key':programme['instance_key'],'reason':'positive_programme_required_active_source_channel',
                'source_channel':link['source_channel'],'source_service_id':link['source_service_id'],
                'physical_id':link['physical_id'],'service_instance_key':link['instance_key'],'deduplicated':deduplicated})
    receipt={'method':'already_generated_required_whole_service_closure',
        'original_programme_members':copy.deepcopy(mixture['members']),
        'explicit_service_members':copy.deepcopy(explicit),
        'effective_service_members':[{'instance_key':c['instance_key']} for c,w in selected],
        'required_links':links,'interpretation':'Whole participation one outside programme normalization; no new owners/schedules/RNG or guessed allocations'}
    return selected,receipt
