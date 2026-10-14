"""Public offline orchestration: resolve, seed, emit, bind, then compose."""
import copy

from .budgets import bind_budget
from .canonical import schedule_id
from .commercial.parametric import transform_commercial
from .commercial.sampling import sample_operating_parameters
from .companions import generate_companions
from .contract import finalize_channels, validate_bundle, validate_request
from .errors import GeneratorError
from .mixtures import normalize_basis_bindings
from .programs import resolve_program
from .residential import generate_residential
from .resources import ResourceSet
from .seeds import assign_unit_seeds, commercial_group_seed

_PREPARED = {'reference_channels', 'reference_budgets', 'source_context', 'companion_rules'}


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
    result['conditioning'] = {k:v for k,v in context['configuration_association'].items()
                              if k not in {'program_definition_pointer'}}
    result['source'] = {k:resolved['source'][k] for k in ('building_type','template','vintage','weather')}
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


def generate(params: dict, seed: int) -> dict:
    """Generate the packaged declared cases with an explicit uint64 realization.

    Caller inputs are source recipe operands, excluding calendar (owned by the
    request) and internal preparation buffers. The returned bundle indexes every
    emitted constituent/mixed schedule once and retains physical source receipts.
    """
    validate_request(params,seed)
    params = copy.deepcopy(params)
    calendar = params['calendar']
    calendar.setdefault('holidays',[])
    resources = ResourceSet.load(params['resource_set_id'])
    scope = resources.get('reference','m1-scope')
    if (calendar['year'] != scope['calendar']['year'] or calendar['holidays']):
        raise GeneratorError('unsupported_binding','/calendar','Outside the declared '+scope['milestone_id']+' calendar')
    resolved_instances = []
    basis_receipts={}
    declared_programs={case['program_id'] for case in scope['cases']}
    for instance in params['instances']:
        try:
            physical,receipts=normalize_basis_bindings(instance['basis_bindings'],instance['key'])
            instance['basis_bindings']=physical; basis_receipts[instance['key']]=receipts
            if instance['program_id'] not in declared_programs:
                raise GeneratorError('unsupported_binding','/program_id','Program is outside the declared '+scope['milestone_id']+' case set')
            if set(instance['inputs']) & ({'year','holidays'} | _PREPARED):
                raise GeneratorError('unknown_input','/inputs','Calendar and preparation buffers are request/internal operands')
            inputs = dict(instance['inputs'],year=calendar['year'],holidays=calendar['holidays'])
            resolved = resolve_program(instance['program_id'],inputs,resources)
            resolved_instances.append((instance,resolved))
        except GeneratorError as error:
            raise GeneratorError(error.code,'/instances/'+instance['key']+error.path,error.message) from error
    # All original annual targets and inputs exist before any RNG is sampled.
    residential_keys = [i['key'] for i,r in resolved_instances if 'residents' in r['inputs']]
    unit_seeds = assign_unit_seeds(seed,residential_keys)
    groups = {}
    for instance,resolved in resolved_instances:
        if 'residents' in resolved['inputs']:
            if instance['operating_group'] is not None:
                raise GeneratorError('operating_group_conflict','/instances/'+instance['key']+'/operating_group',
                                     'Residential source units do not use commercial operating groups')
            continue
        # Missing coordination means an independent group named by the instance.
        group = instance['operating_group'] if instance['operating_group'] is not None else instance['key']
        fingerprint = _group_context(resolved)
        if group in groups and groups[group]['context'] != fingerprint:
            raise GeneratorError('operating_group_conflict','/instances/'+instance['key']+'/operating_group',
                                 'Group has conflicting source/configuration/carrier/calendar context')
        groups.setdefault(group,{'context':fingerprint})
    for group,entry in groups.items():
        group_seed = commercial_group_seed(seed,group)
        entry['operating'] = sample_operating_parameters(entry['context']['conditioning']['conditioning_inputs'],
                                                       group_seed,resources)
    policy = resources.get('reference','comparison-policy')
    bundle = {'schema_version':'1.0.0','algorithm_version':policy['algorithm_version'],
              'schedules':{},'bindings':[],'constituents':[],
              'generation':{'master_seed':seed,'residential_unit_order':residential_keys,'unit_seeds':unit_seeds,
                            'operating_groups':groups,'source_seed_policy':'native_unit_order_and_atlas_conditional_seeded_v1'},
              'metadata':{'resource_set_id':resources.resource_set_id,'calendar':calendar,
                          'scope_id':scope['milestone_id'],'scope_version':scope['scope_version'],
                          'population_realization_equivalent':False,'comparison_policy':policy}}
    for instance,resolved in resolved_instances:
        key = instance['key']
        inputs = resolved['inputs']
        context = inputs['source_context']
        try:
            if key in unit_seeds:
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
                           ('program_id','recipe_id','source','slots','demands','controls','shared_services','evidence')}
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
                binding = dict(bound,kind='load',instance_key=key,program_id=resolved['program_id'],
                               demand_id=demand['demand_id'],slot=demand['slot'],schedule_id=constituent['schedule_ids'][demand['slot']],
                               fuel=demand['fuel'],host=demand['host'],budget_method=bound['reference_target']['method'])
                constituent['binding_indices'].append(len(bundle['bindings'])); bundle['bindings'].append(binding)
            for control in constituent['controls']:
                constituent['binding_indices'].append(len(bundle['bindings']))
                bundle['bindings'].append({'kind':'control','instance_key':key,'program_id':resolved['program_id'],
                                          'slot':control['slot'],'schedule_id':constituent['schedule_ids'][control['slot']],
                                          'control_quantity':control['quantity']})
            bundle['constituents'].append(constituent)
        except GeneratorError as error:
            raise GeneratorError(error.code,'/instances/'+key+error.path,error.message) from error
    validate_bundle(bundle)
    if params.get('mixture') is not None:
        from .mixtures import compose_constituents
        return compose_constituents([bundle],params['mixture'],calendar)
    return bundle
