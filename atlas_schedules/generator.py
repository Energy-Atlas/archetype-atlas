"""Public offline orchestration: resolve, seed, emit, bind, then compose."""
import copy
import math

from .budgets import bind_budget
from .canonical import schedule_id
from .commercial.parametric import transform_commercial,_RESTAURANT_CONFIGURATIONS
from .commercial.sampling import sample_operating_parameters
from .commercial.source_models import RETAIL_CONFIGURATIONS
from .companions import generate_companions
from .contract import finalize_channels, validate_bundle, validate_request
from .errors import GeneratorError
from .mixtures import normalize_basis_bindings
from .programs import resolve_program
from .residential import generate_residential
from .resources import ResourceSet
from .seeds import assign_unit_seeds, assign_physical_unit_sequence, commercial_group_seed
from .owners import request_version,identity_fields
from .services import resolve_physical_service,prepare_required_service_links,bind_required_service_links

_PREPARED = {'reference_channels', 'reference_budgets', 'source_context', 'companion_rules','source_composition'}


def _qualified_apartment_actor(instance: dict, resolved: dict) -> bool:
    """Independently recheck the retained per-ID source/executable association."""
    from .apartment_authority import reconstruct_apartment_programme,bind_apartment_unit_context
    from .canonical import canonical
    try:
        q=resolved['inputs']['source_context']['apartment_qualification']
        raw={k:v for k,v in resolved['inputs'].items() if k not in _PREPARED}
        expected=reconstruct_apartment_programme(raw,q['value']['compiled_recipe']['value'],q)
        bind_apartment_unit_context(instance,expected)
        if instance.get('program_id')!=expected['program_id']:return False
        return all(canonical(resolved.get(k))==canonical(expected.get(k)) for k in
            ('program_id','source','source_family','slots','demands','controls','evidence','inputs','required_service_sets'))
    except (GeneratorError,KeyError,TypeError):return False


def collect_physical_unit_actors(resolved_instances: list[tuple[dict,dict]],
                                 version: str) -> list[dict]:
    """Collect only selected physical stochastic units in resolved request order."""
    if version != '1.2.0':
        raise GeneratorError('unsupported_schema', '/schema_version',
                             'Physical unit actor collection requires 1.2.0')
    actors = []
    seen_units = set()
    for instance, resolved in resolved_instances:
        inputs = resolved.get('inputs', {})
        context = inputs.get('source_context', {})
        method = context.get('method') if isinstance(context, dict) else None
        key = instance.get('key')
        if (resolved.get('source_family') == 'existing_stock_source_fixture' and
                method == 'resstock_time_allocation_with_selected_source_companions'):
            n=inputs.get('residents')
            if (instance.get('owner_kind', 'program') != 'program' or
                    instance.get('building_realization_id') is not None or
                    instance.get('unit_id') is not None or
                    type(n) not in (int,float) or not math.isfinite(n) or n < 0):
                raise GeneratorError('requires_binding', '/instances/'+str(key),
                                     'Stock actor requires a programme owner and resident cohort')
            if n!=0 and int(n)==0:
                raise GeneratorError('unsupported_input','/instances/'+str(key)+'/inputs/residents',
                                     'Positive count truncating to zero is undefined upstream')
            actors.append({'actor_kind': 'stock', 'instance_key': key,
                           'building_realization_id': None, 'unit_id': None,
                           'stochastic_action': 'generate'})
            continue
        if method != 'unit_occupancy_interior_lighting':
            continue
        source = resolved.get('source', {})
        building = instance.get('building_realization_id')
        unit = instance.get('unit_id')
        n = inputs.get('N')
        if (instance.get('owner_kind') != 'program' or
                resolved.get('source_family') not in {'code_prototype_rules',
                                                      'existing_stock_benchmark'} or
                not isinstance(source, dict) or
                source.get('building_type') not in {'HighriseApartment', 'MidriseApartment'} or
                not isinstance(building, str) or not building or
                not isinstance(unit, str) or not unit or
                type(n) is not int or n < 0):
            raise GeneratorError('requires_binding', '/instances/'+str(key),
                                 'Selected apartment actor lacks exact source, unit or cohort')
        if not _qualified_apartment_actor(instance, resolved):
            raise GeneratorError('requires_binding', '/instances/'+str(key),
                                 'Apartment occupancy/lighting method is not independently qualified')
        actual_unit = (building, unit)
        if actual_unit in seen_units:
            raise GeneratorError('shared_service_conflict', '/instances/'+str(key),
                                 'Duplicate selected apartment actor for one physical unit')
        seen_units.add(actual_unit)
        actors.append({'actor_kind': 'apartment_adapter', 'instance_key': key,
                       'building_realization_id': building, 'unit_id': unit,
                       'stochastic_action': 'skip_n0' if n == 0 else 'generate'})
    return actors


def build_physical_unit_generation(master: int,
                                   resolved_instances: list[tuple[dict,dict]]) -> dict:
    """Assemble the exact 1.2 generation receipt from resolved source actors."""
    sequence = assign_physical_unit_sequence(
        master, collect_physical_unit_actors(resolved_instances, '1.2.0'))
    return {'physical_unit_seed_sequence': sequence,
            'residential_unit_order': [actor['instance_key'] for actor in sequence],
            'unit_seeds': {actor['instance_key']: actor['unit_seed'] for actor in sequence}}


def _apartment_fixed_channels(inputs):
    record=inputs['source_context']['apartment_qualification']['value']['compiled_recipe']['value']
    selected={s['slot'] for s in record['recipe']['resolved']['slots']}
    return {k:copy.deepcopy(v) for k,v in inputs['reference_channels'].items()
            if k in selected and k not in inputs['companion_rules']}


def _run_physical_unit_actor(actor: dict, inputs: dict, resources) -> dict:
    """Keep the qualified stock kernel and closed apartment adapter at one boundary."""
    if actor['actor_kind'] == 'stock' and actor['stochastic_action'] == 'generate':
        return generate_residential(inputs, actor['unit_seed'], resources)
    if actor['actor_kind']=='apartment_adapter':
        if not inputs.get('source_context',{}).get('apartment_qualification'):
            raise GeneratorError('requires_binding','/source_context','Complete qualified apartment inputs required')
        if actor['stochastic_action']=='skip_n0':
            return {'channels':_apartment_fixed_channels(inputs),
                    'source_context':{'method':'source_measure_skip_and_original_fixed_rule_retention',
                                      'N':0,'unit_seed':actor['unit_seed'],'random_draw_count':0}}
        from .residential.selected import generate_unit_occupancy_interior_lighting
        consumed={k:inputs[k] for k in ('year','holidays','state','latitude','longitude','time_zone_utc_offset')}
        consumed['residents']=inputs['N']
        selected=generate_unit_occupancy_interior_lighting(consumed,actor['unit_seed'],resources)
        channels=_apartment_fixed_channels(inputs)
        for slot in ('occupants','lighting_interior','additional_lighting'):
            if slot in channels:channels[slot]=copy.deepcopy(selected['channels']['occupants' if slot=='occupants' else 'lighting_interior'])
        return {'channels':channels,'source_context':selected['source_context']}
    # An N0 adapter position never initializes streams, HMM, events or lighting.
    # Positive adapter execution also awaits separate native/source qualification.
    raise GeneratorError('requires_binding', '/source_context/method',
                         'Apartment occupancy/lighting execution awaits qualification')


def _group_context(resolved):
    """Compare source science shared by the group, allowing distinct room slots.

    Program/case/carrier catalogue IDs and definition pointers vary between the
    source/reviewed Office/Plenum views. The actual carrier rules and evidence,
    sampling configuration, dependencies and calendar must still agree.
    """
    context = resolved['inputs']['source_context']
    keys = ('year','holidays','configuration_id','method','standards_version','steps_per_hour',
            'source_clock','occupancy_adjustment','occupancy_aggregation')
    result = {key:copy.deepcopy(context[key]) for key in keys}
    for key in ('source_hoo_configuration_id','parametric_apply'):
        if key in context:result[key]=copy.deepcopy(context[key])
    result['conditioning'] = {k:v for k,v in context['configuration_association'].items()
                              if k not in {'program_definition_pointer'}}
    result['source'] = {k:resolved['source'][k] for k in ('building_type','template','vintage','weather')}
    if context['occupancy_aggregation'].get('policy')=='explicit_source_model_nonresidential_people':
        configuration=context.get('source_hoo_configuration_id')
        if (configuration not in _RESTAURANT_CONFIGURATIONS|RETAIL_CONFIGURATIONS or configuration!=context['configuration_id'] or
                context['configuration_association'].get('conditioning_inputs')!={'building_type':configuration.split('__')[0]}):
            raise GeneratorError('operating_group_conflict','/source_hoo_configuration_id','Exact qualified source-model dependency scope required')
        weather=resolved['source']['weather']
        if weather is not None and (not isinstance(weather,dict) or weather.get('mode')!='not_used' or
                set(weather)-{'mode','interpretation','independence_certified_by'}):
            raise GeneratorError('operating_group_conflict','/weather','Qualified source-model methods have no weather operand; used/foreign weather context cannot be ignored')
        # Only method-unused metadata representation is projected away. All
        # consumed cfg/view/People/calendar/caller operands above remain exact.
        result['source']['weather']=None
        result['unused_weather_dependency']={'mode':'not_used',
            'scope':('Exact qualified RetailStandalone source/view model methods and ten-table selector closure'
                     if configuration in RETAIL_CONFIGURATIONS else
                     'Exact qualified restaurant source/view model methods and ten-table selector closure'),
            'original_owner_weather_records':'Retained in owners and explicit group receipt'}
    return result


def _heat_fractions(demand, resolved):
    original = demand['evidence'].get('original_value')
    if isinstance(original,dict) and 'heat_fractions' in original:
        return copy.deepcopy(original['heat_fractions'])
    for receipt in resolved['evidence']:
        for group in receipt.get('aggregation',{}).get('groups',[]):
            for component in group.get('components',[]):
                load = component['load']
                if (load['demand_id'] == demand['demand_id'] or
                        (load.get('end_use') == demand['quantity'] and load.get('fuel') == demand['fuel']
                         and load.get('host') == demand['host'])):
                    return copy.deepcopy(load.get('heat_fractions'))
    return None


def _prepare_v12_request(params, resources):
    """Prepare independent source modes; never route foreign identities as legacy."""
    from .physical_sets import _prepare_exact_instances
    from .caller_unit_water import prepare_caller_water
    realizations={r['building_realization_id']:r for r in params['building_realizations']}
    if len(realizations)!=len(params['building_realizations']):
        raise GeneratorError('shared_service_conflict','/building_realizations','Duplicate realization')
    modes={};sids={};physical_ids={}
    for instance in params['instances']:
        key=instance['key'];building=instance.get('building_realization_id')
        if building is not None and building not in realizations:
            raise GeneratorError('shared_service_conflict','/instances/'+key+'/building_realization_id','Unknown realization')
        mode=realizations[building]['mode'] if building is not None else None
        kind=instance.get('physical_binding_kind')
        if ((kind=='exact_source_role' and mode!='exact_source_fixture_extents') or
                (kind=='caller_unit_prototype_density_fixed_dhw' and mode!=kind) or
                (instance.get('unit_id') is not None and mode!='caller_unit_prototype_density_fixed_dhw')):
            raise GeneratorError('shared_service_conflict','/instances/'+key+'/building_realization_id','Owner and realization modes differ')
        if set(instance['inputs']) & ({'year','holidays'} | _PREPARED):
            raise GeneratorError('unknown_input','/instances/'+key+'/inputs','Calendar and preparation buffers are request/internal operands')
        modes[key]=mode
        if instance['owner_kind']=='physical_service':
            for field,index in (('source_service_id',sids),('physical_id',physical_ids)):
                value=instance[field]
                if value in index and index[value]!=kind:
                    raise GeneratorError('shared_service_conflict','/instances/'+key+'/'+field,'Cross-mode physical identity is ambiguous')
                index[value]=kind
    exact_params=dict(params,instances=[i for i in params['instances'] if modes[i['key']]=='exact_source_fixture_extents'],
                      building_realizations=[r for r in params['building_realizations'] if r['mode']=='exact_source_fixture_extents'])
    exact_pairs=_prepare_exact_instances(exact_params,resources) if exact_params['building_realizations'] else []
    caller_params=dict(params,instances=[i for i in params['instances'] if modes[i['key']]=='caller_unit_prototype_density_fixed_dhw'],
                       building_realizations=[r for r in params['building_realizations'] if r['mode']=='caller_unit_prototype_density_fixed_dhw'])
    # Core4 explicitly accepts unresolved physical pairs: it derives actual water
    # from independent locked per-ID authority, never from this empty operand.
    caller_pairs=[(i,{}) for i in caller_params['instances'] if i['owner_kind']=='physical_service']
    if caller_params['building_realizations']:
        prepare_caller_water(caller_params,caller_pairs,resources)
    return modes,exact_params,{i['key']:r for i,r in exact_pairs},caller_params


def _merge_exact_preparation(pairs, plan, occupied):
    """Splice selected exact children where their requested parent occurred."""
    replacements={i['key']:(i,r) for i,r in plan['resolved_instances']}
    children={a['parent_instance_key']:[c['key'] for c in a['children']] for a in plan['source_allocations']}
    for keys in children.values():
        for key in keys:
            if key in occupied:
                raise GeneratorError('duplicate_instance','/instances/'+key,'Generated source-member key overlaps another instance')
            occupied.add(key)
    result=[]
    for instance,resolved in pairs:
        key=instance['key']
        if key in children:result.extend(replacements[c] for c in children[key])
        else:result.append(replacements.get(key,(instance,resolved)))
    return result


def _preflight_v12_mixture(params, pairs, service_links, exact_plan, caller_plan):
    """Close requested whole participation and alternative overlap before RNG."""
    mixture=params.get('mixture')
    if mixture is None:return
    positive={m['instance_key'] for m in mixture['members'] if m['weight']>0}
    required={p['programme_instance_key'] for p in service_links}
    for plan in (exact_plan,caller_plan):
        if plan is not None:required.update(p['instance_key'] for p in plan['projections'])
    if mixture.get('service_members') or positive & required:
        if 'result_basis' not in mixture or 'denominator' not in mixture:
            raise GeneratorError('requires_binding','/mixture/denominator','Whole services require explicit result basis and denominator')
        basis=mixture['result_basis'];denominator=mixture['denominator']
        if (basis not in {'floor_area','absolute'} or
                denominator['unit']!={'floor_area':'m2','absolute':'1'}.get(basis) or denominator['value']<=0):
            raise GeneratorError('incompatible_basis','/mixture/denominator','Physical participation requires positive matching root denominator')
    claims=set()
    for instance,resolved in pairs:
        if instance['key'] not in positive or instance.get('unit_id') is None:continue
        identity=(instance.get('building_realization_id'),instance['unit_id'])
        if identity in claims:
            raise GeneratorError('incompatible_source_composition','/mixture/members','Positive alternative views overlap one actual unit')
        claims.add(identity)


def generate(params: dict, seed: int) -> dict:
    """Generate the packaged declared cases with an explicit uint64 realization.

    Caller inputs are source recipe operands, excluding calendar (owned by the
    request) and internal preparation buffers. The returned bundle indexes every
    emitted constituent/mixed schedule once and retains physical source receipts.
    """
    validate_request(params,seed)
    version=request_version(params)
    params = copy.deepcopy(params)
    if version!='1.2.0':params.pop('schema_version',None)
    calendar = params['calendar']
    calendar.setdefault('holidays',[])
    resources = ResourceSet.load(params['resource_set_id'])
    scope = resources.get('reference','m1-scope')
    if (calendar['year'] != scope['calendar']['year'] or calendar['holidays']):
        raise GeneratorError('unsupported_binding','/calendar','Outside the declared '+scope['milestone_id']+' calendar')
    resolved_instances = []
    basis_receipts={}
    source_allocations=[]
    occupied_keys={i['key'] for i in params['instances']}
    declared_programs={case['program_id'] for case in scope['cases']}
    declared_services={(case['source_service_id'],case['source_hoo_configuration_id']):case
                       for case in scope.get('service_cases',[])}
    exact_plan=None;caller_plan=None
    if version=='1.2.0':
        for instance in params['instances']:
            physical,receipts=normalize_basis_bindings(instance['basis_bindings'],instance['key'])
            instance['basis_bindings']=physical;basis_receipts[instance['key']]=receipts
        modes,exact_params,exact_resolved,caller_params=_prepare_v12_request(params,resources)
    for instance in params['instances']:
        try:
            if version!='1.2.0':
                physical,receipts=normalize_basis_bindings(instance['basis_bindings'],instance['key'])
                instance['basis_bindings']=physical; basis_receipts[instance['key']]=receipts
            elif instance['key'] in exact_resolved:
                resolved_instances.append((instance,exact_resolved[instance['key']]))
                continue
            elif instance.get('physical_binding_kind')=='caller_unit_prototype_density_fixed_dhw':
                resolved_instances.append((instance,{}))
                continue
            if instance.get('owner_kind')=='physical_service':
                service_case=declared_services.get((instance['source_service_id'],instance['inputs'].get('source_hoo_configuration_id')))
                if service_case is None:
                    raise GeneratorError('unsupported_binding','/source_service_id',
                                         'Physical service/configuration is outside the declared '+scope['milestone_id']+' service set')
                resolved=resolve_physical_service(instance,calendar,resources)
                resolved['inputs']['source_context']['case_id']=service_case['case_id']
                resolved_instances.append((instance,resolved))
                continue
            if instance['program_id'] not in declared_programs and not (version=='1.2.0' and modes[instance['key']]=='caller_unit_prototype_density_fixed_dhw'):
                raise GeneratorError('unsupported_binding','/program_id','Program is outside the declared '+scope['milestone_id']+' case set')
            if set(instance['inputs']) & ({'year','holidays'} | _PREPARED):
                raise GeneratorError('unknown_input','/inputs','Calendar and preparation buffers are request/internal operands')
            inputs = dict(instance['inputs'],year=calendar['year'],holidays=calendar['holidays'])
            resolved = resolve_program(instance['program_id'],inputs,resources)
            from .apartment_authority import candidate,bind_apartment_unit_context
            if candidate(resources.get('program',instance['program_id'])):
                if version!='1.2.0':raise GeneratorError('unsupported_schema','/schema_version','Apartment methods require explicit1.2.0')
                bind_apartment_unit_context(instance,resolved)
            if version=='1.2.0' and resolved.get('required_service_sets') and (
                    modes[instance['key']] is None or modes[instance['key']]=='caller_unit_prototype_density_fixed_dhw' and
                    instance.get('unit_id') is None):
                raise GeneratorError('requires_binding','/building_realization_id','Independent service sets require actual declared scope')
            if 'source_composition' in resolved['inputs']:
                from .source_compositions import prepare_allocation
                allocation=prepare_allocation(instance,resolved['inputs']['source_composition'])
                allocation['parent_instance']=copy.deepcopy(instance)
                allocation['parent_resolved']=resolved
                allocation['parent_case_id']=resources.get('program',instance['program_id'])['case']['case_id']
                for child in allocation['children']:
                    if child['key'] in occupied_keys:
                        raise GeneratorError('duplicate_instance','/key','Generated source-member key overlaps another instance')
                    occupied_keys.add(child['key'])
                    recipe=resources.get('program',child['program_id'])['recipe']
                    if 'source_composition' in recipe:
                        raise GeneratorError('unsupported_binding','/source_composition','Nested source parent needs its own audited physical expansion')
                    child['inputs']=copy.deepcopy(recipe['bound_inputs'])
                    child_resolved=resolve_program(child['program_id'],dict(child['inputs'],year=calendar['year'],holidays=calendar['holidays']),resources)
                    basis_receipts[child['key']]={}
                    resolved_instances.append((child,child_resolved))
                source_allocations.append(allocation)
            else:resolved_instances.append((instance,resolved))
        except GeneratorError as error:
            raise GeneratorError(error.code,'/instances/'+instance['key']+error.path,error.message) from error
    if version=='1.2.0':
        if caller_params['building_realizations']:
            from .caller_unit_water import prepare_caller_water
            caller_plan=prepare_caller_water(params,resolved_instances,resources)
            resolved_instances=caller_plan['resolved_instances']
        if exact_params['building_realizations']:
            from .physical_sets import prepare_exact_bindings
            exact_plan=prepare_exact_bindings(exact_params,
                [(i,r) for i,r in resolved_instances if i['key'] in exact_resolved],resources)
            resolved_instances=_merge_exact_preparation(resolved_instances,exact_plan,occupied_keys)
            source_allocations.extend(exact_plan['source_allocations'])
            for child,_ in resolved_instances:basis_receipts.setdefault(child['key'],{})
        request_order={i['key']:n for n,i in enumerate(params['instances'])}
        source_allocations.sort(key=lambda a:request_order[a['parent_instance_key']])
    # All original annual targets and inputs exist before any RNG is sampled.
    if version=='1.2.0':
        # Reuse the unchanged C5 contract on a private legacy-scope view, as the
        # incoming graph validator does. Exact/caller ownership is never erased.
        link_pairs=copy.deepcopy(resolved_instances)
        for instance,resolved in link_pairs:
            if instance.get('physical_binding_kind')=='legacy_whole':
                instance.pop('physical_binding_kind');resolved.pop('physical_binding_kind')
        service_link_plans=prepare_required_service_links(link_pairs,'1.1.0')
    else:service_link_plans=prepare_required_service_links(resolved_instances,version)
    if version == '1.2.0':
        _preflight_v12_mixture(params,resolved_instances,service_link_plans,exact_plan,caller_plan)
        actors=collect_physical_unit_actors(resolved_instances,version)
        residential_keys=[a['instance_key'] for a in actors]
    else:
        residential_keys = [i['key'] for i,r in resolved_instances if 'residents' in r['inputs']]
        unit_seeds = assign_unit_seeds(seed,residential_keys)
    groups = {}
    for instance,resolved in resolved_instances:
        if (instance['key'] in residential_keys if version == '1.2.0'
                else 'residents' in resolved['inputs']):
            if instance['operating_group'] is not None:
                raise GeneratorError('operating_group_conflict','/instances/'+instance['key']+'/operating_group',
                                     'Residential source units do not use commercial operating groups')
            continue
        if instance.get('physical_binding_kind')=='caller_unit_prototype_density_fixed_dhw':
            continue
        if resolved['inputs']['source_context'].get('method')=='source_fixed_apartment_programme':
            if instance['operating_group'] is not None:
                raise GeneratorError('operating_group_conflict','/instances/'+instance['key'],'Fixed apartment programme has no commercial group')
            continue
        # Missing coordination means an independent group named by the instance.
        group = instance['operating_group'] if instance['operating_group'] is not None else instance['key']
        fingerprint = _group_context(resolved)
        if group in groups and groups[group]['context'] != fingerprint:
            raise GeneratorError('operating_group_conflict','/instances/'+instance['key']+'/operating_group',
                                 'Group has conflicting source/configuration/carrier/calendar context')
        groups.setdefault(group,{'context':fingerprint})
        if 'unused_weather_dependency' in fingerprint:
            groups[group].setdefault('original_owner_weather_records',[]).append({
                'instance_key':instance['key'],**identity_fields(resolved,version),
                'weather':copy.deepcopy(resolved['source']['weather'])})
    if version=='1.2.0':
        physical_generation=build_physical_unit_generation(seed,resolved_instances)
        unit_seeds=physical_generation['unit_seeds']
        physical_actors_by_key={a['instance_key']:a for a in physical_generation['physical_unit_seed_sequence']}
    for group,entry in groups.items():
        group_seed = commercial_group_seed(seed,group)
        entry['operating'] = sample_operating_parameters(entry['context']['conditioning']['conditioning_inputs'],
                                                       group_seed,resources)
    policy = resources.get('reference','comparison-policy')
    bundle = {'schema_version':version,'algorithm_version':policy['algorithm_version'],
              'schedules':{},'bindings':[],'constituents':[],
              'generation':{'master_seed':seed,'residential_unit_order':residential_keys,'unit_seeds':unit_seeds,
                            'operating_groups':groups,'source_seed_policy':'native_unit_order_and_atlas_conditional_seeded_v1'},
              'metadata':{'resource_set_id':resources.resource_set_id,'calendar':calendar,
                          'scope_id':scope['milestone_id'],'scope_version':scope['scope_version'],
                          'population_realization_equivalent':False,'comparison_policy':policy}}
    if version == '1.2.0':
        bundle['generation'].update(physical_generation)
        bundle['metadata']['building_realizations']=[]
    if source_allocations:
        bundle['generation']['request_instance_order']=[i['key'] for i in params['instances']]
        bundle['generation']['physical_member_generation_order']=[i['key'] for i,r in resolved_instances]
        bundle['generation']['source_parent_derivation_order']=[a['parent_instance_key'] for a in source_allocations]
    for instance,resolved in resolved_instances:
        key = instance['key']
        inputs = resolved['inputs']
        context = inputs['source_context']
        try:
            if instance.get('physical_binding_kind')=='caller_unit_prototype_density_fixed_dhw':
                generated={'channels':copy.deepcopy(inputs['reference_channels']),
                           'source_context':{'method':'source_fixed_apartment_dhw',
                                             'random_draw_count':0}}
                kernel_context=generated['source_context']
            elif version == '1.2.0' and key in physical_actors_by_key:
                generated = _run_physical_unit_actor(physical_actors_by_key[key], inputs, resources)
                kernel_context = {'residential':generated['source_context']}
            elif context.get('method')=='source_fixed_apartment_programme':
                generated={'channels':_apartment_fixed_channels(inputs),
                           'source_context':{'method':'source_fixed_apartment_programme','random_draw_count':0}}
                kernel_context=generated['source_context']
            elif key in unit_seeds:
                generated = generate_residential(inputs,unit_seeds[key],resources)
                kernel_context = {'residential':generated['source_context']}
            else:
                group = instance['operating_group'] if instance['operating_group'] is not None else key
                generated = transform_commercial(inputs['reference_channels'],groups[group]['operating'],context)
                kernel_context = generated['source_context']
            companion = generate_companions(resolved,resources)
            overlap = set(generated['channels']) & set(companion['channels'])
            if overlap:
                raise GeneratorError('invalid_channels','/channels','Duplicate kernel/companion slots: '+str(sorted(overlap)))
            finalized = finalize_channels({'channels':dict(generated['channels'],**companion['channels']),
                                           'source_context':{'export_precision':'raw_source_float'}})
            channels = finalized['channels']
            selected = {s['slot'] for s in resolved['slots']}
            missing = selected-set(channels)
            if missing:
                raise GeneratorError('invalid_channels','/channels/'+sorted(missing)[0],'Active source slot was not generated')
            unselected={}
            for slot in sorted(set(channels)-selected):
                receipts=[d for e in resolved['evidence'] for d in e.get('absent_demands',[])
                          if d.get('end_use')==slot and type(d.get('value')) in (int,float) and d['value']==0]
                if not receipts:
                    raise GeneratorError('invalid_channels','/channels/'+slot,'Unknown source channel cannot be silently omitted')
                unselected[slot]={'status':'accepted_absent_demand','source_receipts':copy.deepcopy(receipts),
                                  'interpretation':'Kernel shape has no selected physical demand; explicit source/reviewed absence retained'}
            generation = {'case_id':context['case_id'],'status':'generated' if selected else 'accepted_inactive',
                          'source_context':kernel_context,'companions':companion['source_context'],
                          'unselected_kernel_channels':unselected,
                          'source_inputs':copy.deepcopy(context)}
            if basis_receipts[key]:generation['basis_alias_receipts']=basis_receipts[key]
            constituent = {k:copy.deepcopy(resolved[k]) for k in
                           ('recipe_id','source','slots','demands','controls','shared_services','evidence')}
            constituent.update(identity_fields(resolved,version))
            if version in {'1.1.0','1.2.0'} and resolved.get('owner_kind','program')!='physical_service':
                constituent['required_service_links']=copy.deepcopy(resolved.get('required_service_links',[]))
                if version=='1.2.0':
                    constituent['required_service_sets']=copy.deepcopy(resolved.get('required_service_sets',[]))
                    constituent['service_set_projections']=[]
            if 'method_variant' in resolved:
                generation['method_variant']=copy.deepcopy(resolved['method_variant'])
            constituent['source']['source_family'] = resolved['source_family']
            constituent.update(instance_key=key,inputs={k:v for k,v in inputs.items() if k not in _PREPARED},
                               basis_bindings=copy.deepcopy(instance['basis_bindings']),schedule_ids={},binding_indices=[],generation=generation)
            for slot in resolved['slots']:
                name=slot['slot']; sid=schedule_id(key,name)
                bundle['schedules'][sid]={'id':sid,'unit':slot['unit'],'year':calendar['year'],
                                          'clock':calendar['clock'],'timestep_minutes':60,'values':channels[name]}
                constituent['schedule_ids'][name]=sid
            for demand in constituent['demands']:
                demand['heat_fractions'] = _heat_fractions(demand,resolved)
                bound = bind_budget(inputs['reference_budgets'][demand['demand_id']],channels[demand['slot']])
                binding = dict(bound,kind='load',instance_key=key,**identity_fields(resolved,version),
                               demand_id=demand['demand_id'],slot=demand['slot'],schedule_id=constituent['schedule_ids'][demand['slot']],
                               fuel=demand['fuel'],host=demand['host'],budget_method=bound['reference_target']['method'])
                constituent['binding_indices'].append(len(bundle['bindings'])); bundle['bindings'].append(binding)
            for control in constituent['controls']:
                constituent['binding_indices'].append(len(bundle['bindings']))
                bundle['bindings'].append({'kind':'control','instance_key':key,**identity_fields(resolved,version),
                                          'slot':control['slot'],'schedule_id':constituent['schedule_ids'][control['slot']],
                                          'control_quantity':control['quantity']})
            bundle['constituents'].append(constituent)
            if version in {'1.1.0','1.2.0'}:
                constituent['generation']['operating_group']=(None if instance.get('physical_binding_kind')=='caller_unit_prototype_density_fixed_dhw' or context.get('method') in {'unit_occupancy_interior_lighting','source_fixed_apartment_programme'}
                    else instance['operating_group'] if instance['operating_group'] is not None else key)
        except GeneratorError as error:
            raise GeneratorError(error.code,'/instances/'+key+error.path,error.message) from error
    bind_required_service_links(bundle,service_link_plans)
    for allocation in source_allocations:
        from .source_compositions import compose_source_parent,_derive_prepared_source_parent
        if version=='1.2.0':
            allocation['receipt']['basis_alias_receipts'].update(basis_receipts.get(allocation['parent_instance_key'],{}))
        bundle=(_derive_prepared_source_parent(bundle,allocation,resources) if version=='1.2.0'
                else compose_source_parent(bundle,allocation,resources))
    if exact_plan is not None:
        from .physical_sets import bind_exact_projections
        bind_exact_projections(bundle,exact_plan)
    if caller_plan is not None:
        from .caller_unit_water import bind_caller_water
        bind_caller_water(bundle,caller_plan)
    if version=='1.2.0':
        realization_order={r['building_realization_id']:n for n,r in enumerate(params['building_realizations'])}
        bundle['metadata']['building_realizations'].sort(key=lambda r:realization_order[r['building_realization_id']])
    validate_bundle(bundle)
    if params.get('mixture') is not None:
        from .mixtures import compose_constituents
        return compose_constituents([bundle],params['mixture'],calendar)
    return bundle
