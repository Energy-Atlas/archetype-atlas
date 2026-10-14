"""Bounded allocation of exact packaged source members; no geometry inference."""
import copy
import math
from urllib.parse import quote

from .errors import GeneratorError
from .mixtures import normalize_basis_bindings


def _fail(path,message):
    raise GeneratorError('incompatible_source_composition','/source_composition/'+path,message)


def source_factors(recipe):
    members=recipe['definition']['members']
    if not members or len({m['program_id'] for m in members})!=len(members):
        _fail('members','Exact nonempty ordered unique source members required')
    areas=[m.get('represented_area_m2') for m in members]
    if any(type(a) not in (int,float) or not math.isfinite(a) or a<=0 for a in areas):
        _fail('members','Positive finite original represented areas required')
    total=math.fsum(areas)
    factors=[a/total for a in areas]
    if any(type(m.get('weight')) not in (int,float) or not math.isclose(m['weight'],f,rel_tol=1e-12,abs_tol=1e-12)
           for m,f in zip(members,factors)):
        _fail('members','Original source weights must close against represented-area ratios')
    return areas,total,factors


def prepare_allocation(instance,recipe):
    """Expand a requested known parent into ordered real physical members."""
    if instance['program_id']!=recipe['parent_program_id']:
        _fail('program_id','Requested parent differs from exact source allocation')
    if instance['inputs'].get('composition_id',recipe['composition_id'])!=recipe['composition_id']:
        _fail('composition_id','Conflicting public composition ID')
    mode=instance['inputs'].get('composition_basis_mode')
    if mode not in {'source_reference_area_normalized','caller_parent_floor_area'}:
        _fail('composition_basis_mode','Explicit supported source allocation mode required')
    physical,aliases=normalize_basis_bindings(instance['basis_bindings'],instance['key'])
    if type(physical.get('multiplicity',1)) not in (int,float) or physical.get('multiplicity',1)!=1 or set(physical.get('extents',{}))-{'floor_area'}:
        _fail('basis_bindings','Known source allocation uses one physical parent and floor area only')
    area=physical.get('extents',{}).get('floor_area')
    areas,total,factors=source_factors(recipe)
    if mode=='source_reference_area_normalized':
        if area is not None:_fail('basis_bindings','Reference-area mode cannot also bind caller geometry')
        denominator={'value':total,'unit':'m2','evidence':{'source':copy.deepcopy(recipe['provenance']),
            'interpretation':'Explicit source_reference_area_normalized prototype allocation; no caller geometry'}}
    else:
        if area is None or area['unit']!='m2' or area['value']<=0:
            _fail('basis_bindings','Caller-parent-area mode requires a positive explicit floor-area extent')
        denominator=copy.deepcopy(area)
    children=[]
    for i,(member,factor) in enumerate(zip(recipe['definition']['members'],factors)):
        key='source-member/'+quote(instance['key'],safe='')+'/'+str(i)+'/'+member['program_id']
        extent={'value':areas[i] if mode=='source_reference_area_normalized' else denominator['value']*factor,
                'unit':'m2','evidence':{'source':copy.deepcopy(recipe['provenance']),
                'original_member':copy.deepcopy(member),'composition_basis_mode':mode,
                'transformation':'Original represented area, scaled once by explicitly bound parent area when requested'}}
        children.append({'key':key,'program_id':member['program_id'],'inputs':{},
            'basis_bindings':{'extents':{'floor_area':extent}},
            'operating_group':instance['operating_group'] if instance['operating_group'] is not None else instance['key']})
    mixture={'program_id':instance['program_id'],'composition_id':recipe['composition_id'],
             'members':[{'instance_key':c['key'],'weight':1} for c in children],
             'result_basis':'floor_area','denominator':denominator}
    receipt={'composition_id':recipe['composition_id'],'composition_basis_mode':mode,
             'original_members':copy.deepcopy(recipe['definition']['members']),
             'source_total_area_m2':total,'physical_factors':factors,'physical_participation':[1]*len(children),
             'control_method':'source_represented_area_pointwise_eligible_average',
             'source':copy.deepcopy(recipe['provenance']),'basis_alias_receipts':aliases,
             'interpretation':'Constituent-first original targets; actual generated member trajectories; source weights are not population weights'}
    return {'parent_instance_key':instance['key'],'children':children,'mixture':mixture,'receipt':receipt}


def validate_allocation(mixture,members,resources):
    """Validate public known-composition calls against actual packaged members."""
    identifier=mixture['composition_id']
    index=resources.get('reference','catalogue-index')['compositions']
    if not any(c['id']==identifier and c['status']=='compiled' for c in index):
        _fail('composition_id','No declared supported physical source allocation')
    record=resources.get('composition',identifier)
    recipe=record.get('source_allocation')
    if recipe is None:_fail('composition_id','Missing source allocation method')
    recipe=dict(recipe,definition=record['definition'],provenance=record['provenance'])
    areas,total,factors=source_factors(recipe)
    definition=recipe['definition']
    if mixture['program_id']!=recipe['parent_program_id'] or len(members)!=len(areas):
        _fail('members','Parent and ordered member count must match exact composition')
    if mixture.get('result_basis')!='floor_area' or 'denominator' not in mixture:
        _fail('denominator','Known physical source allocation requires a floor-area denominator')
    denominator=mixture['denominator']
    operating=None
    for i,((member,weight),expected,factor) in enumerate(zip(members,definition['members'],factors)):
        if (member['program_id']!=expected['program_id'] or weight!=1 or
                any(member['source'].get(k)!=definition[k] for k in ('template','evidence_view'))):
            _fail('members/'+str(i),'Exact member ID, source view/template and unit physical participation required')
        physical,_=normalize_basis_bindings(member.get('basis_bindings',{}),member['instance_key'])
        extents=physical.get('extents',{})
        if physical.get('multiplicity',1)!=1 or set(extents)!={'floor_area'}:
            _fail('members/'+str(i),'Exact single floor-area allocation required')
        extent=extents['floor_area']
        if extent['unit']!='m2' or not math.isclose(extent['value'],denominator['value']*factor,rel_tol=1e-12,abs_tol=1e-10):
            _fail('members/'+str(i),'Bound areas must close against original source area ratios and denominator')
        receipt=copy.deepcopy(member['generation'].get('source_context',{}).get('operating_receipt'))
        if receipt is None:_fail('members/'+str(i),'Actual coordinated source operating receipt required')
        receipt.get('rng',{}).pop('python_version',None)
        if operating is not None and receipt!=operating:
            _fail('members/'+str(i),'Source physical members have conflicting actual operating group draws')
        operating=receipt
    return recipe,{'composition_id':identifier,'original_members':copy.deepcopy(definition['members']),
        'physical_factors':factors,'source_total_area_m2':total,'source':copy.deepcopy(recipe['provenance']),
        'control_method':'source_represented_area_pointwise_eligible_average'}


def bind_parent_identity(bundle,allocation):
    """Keep requested source parent ownership and actual derived references."""
    from .canonical import schedule_id
    instance=allocation['parent_instance'];resolved=allocation['parent_resolved']
    parent=bundle['constituents'][-1];key=instance['key']
    aliases={sid:schedule_id(key,slot) for slot,sid in parent['schedule_ids'].items()}
    for before,after in aliases.items():
        if after in bundle['schedules']:_fail('instance_key','Parent generated schedule key overlaps an existing owner')
        schedule=bundle['schedules'].pop(before);schedule['id']=after;bundle['schedules'][after]=schedule
    parent['schedule_ids']={slot:aliases[sid] for slot,sid in parent['schedule_ids'].items()}
    parent.update(instance_key=key,recipe_id=resolved['recipe_id'],source=copy.deepcopy(resolved['source']),
                  inputs=copy.deepcopy(instance['inputs']),basis_bindings=copy.deepcopy(instance['basis_bindings']))
    parent['source']['source_family']=resolved['source_family']
    parent['evidence'].extend(copy.deepcopy(resolved['evidence']))
    parent['generation'].update(case_id=allocation['parent_case_id'],source_allocation=copy.deepcopy(allocation['receipt']),
        parent_requested_instance_key=key,member_instance_keys=[c['key'] for c in allocation['children']])
    for index in parent['binding_indices']:
        binding=bundle['bindings'][index];binding['instance_key']=key;binding['schedule_id']=aliases[binding['schedule_id']]
        if binding['kind']=='load':
            target=resolved['inputs']['reference_budgets'][binding['demand_id']]
            if not math.isclose(target['total'],binding['reference_target']['total'],rel_tol=1e-12,abs_tol=1e-8):
                _fail('reference_target','Generated parent target differs from original member target established before RNG')
    bundle['generation'].pop('mixture',None)
    bundle['generation'].setdefault('source_compositions',[]).append({'parent_instance_key':key,'program_id':instance['program_id'],
        'composition_id':allocation['receipt']['composition_id'],'member_instance_keys':[c['key'] for c in allocation['children']],
        'receipt':copy.deepcopy(allocation['receipt'])})


def remap_binding_references(value,mapping):
    """Rebase every explicit generated binding reference, retaining all other data."""
    seen=set()
    def index(number):
        if type(number) is not int or number not in mapping:
            _fail('binding_index','Generated reference has no exact local/global binding map')
        return mapping[number]
    def walk(current):
        if not isinstance(current,(dict,list)) or id(current) in seen:return
        seen.add(id(current))
        if isinstance(current,list):
            for child in current:walk(child)
        else:
            for key,child in current.items():
                if key=='binding_index':current[key]=index(child)
                elif key=='binding_indices':
                    if not isinstance(child,list):_fail('binding_indices','Explicit binding list required')
                    current[key]=[index(i) for i in child]
                else:walk(child)
    walk(value)


def project_source_members(bundle,keys):
    """Select complete actual child owners, with unchanged IDs and inverse indices."""
    if not keys or len(set(keys))!=len(keys):_fail('members','Unique actual source member keys required')
    owners={c['instance_key']:c for c in bundle['constituents']}
    if len(owners)!=len(bundle['constituents']) or any(k not in owners for k in keys):
        _fail('members','Actual source member owner is missing or repeated')
    selected=[];bindings=[];schedules={};inverse={};forward={}
    for key in keys:
        child=copy.deepcopy(owners[key])
        if child['generation'].get('method') in {'conserved_source_composition','conserved_constituent_mixture'}:
            _fail('members','Nested source allocation requires separately audited physical expansion')
        demand_ids={d['demand_id'] for d in child['demands']}
        if any(s.get('demand_id') not in demand_ids for s in child['shared_services']):
            _fail('shared_services','Every selected service descriptor needs its actual owned demand binding')
        for sid in child['schedule_ids'].values():
            if sid not in bundle['schedules']:_fail('schedule_id','Selected source member schedule is missing')
            schedules[sid]=bundle['schedules'][sid]
        for original in child['binding_indices']:
            if type(original) is not int or not 0<=original<len(bundle['bindings']) or original in forward:
                _fail('binding_indices','Actual owned binding is missing or repeated')
            binding=bundle['bindings'][original]
            if (binding['instance_key']!=key or binding['program_id']!=child['program_id'] or
                    binding['schedule_id']!=child['schedule_ids'].get(binding['slot'])):
                _fail('binding_indices','Selected binding belongs to another owner or schedule')
            local=len(bindings);forward[original]=local;inverse[local]=original
            bindings.append(copy.deepcopy(binding))
        selected.append(child)
    for child in selected:remap_binding_references(child,forward)
    for binding in bindings:remap_binding_references(binding,forward)
    local={'schema_version':bundle['schema_version'],'algorithm_version':bundle['algorithm_version'],
        'metadata':copy.deepcopy(bundle['metadata']),'constituents':selected,'bindings':bindings,'schedules':schedules,
        'generation':{'method':'private_actual_source_member_projection'}}
    return local,inverse


def compose_source_parent(bundle,allocation):
    """Use the public composer locally, then append only its parent to global data."""
    from .mixtures import compose_constituents
    local,inverse=project_source_members(bundle,[c['key'] for c in allocation['children']])
    physical_count=len(local['bindings'])
    derived=compose_constituents([local],allocation['mixture'],bundle['metadata']['calendar'])
    parent=copy.deepcopy(derived['constituents'][-1])
    parent_bindings=copy.deepcopy(derived['bindings'][physical_count:])
    if parent['binding_indices']!=list(range(physical_count,len(derived['bindings']))):
        _fail('binding_indices','Local parent must own every newly appended binding exactly once')
    inverse.update({physical_count+i:len(bundle['bindings'])+i for i in range(len(parent_bindings))})
    remap_binding_references(parent,inverse)
    for binding in parent_bindings:remap_binding_references(binding,inverse)
    for sid in parent['schedule_ids'].values():
        if sid in bundle['schedules']:_fail('schedule_id','Derived source parent overlaps a global schedule')
        bundle['schedules'][sid]=derived['schedules'][sid]
    bundle['bindings'].extend(parent_bindings);bundle['constituents'].append(parent)
    bind_parent_identity(bundle,allocation)
    return bundle
