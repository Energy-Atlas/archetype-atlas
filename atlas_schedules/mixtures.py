"""Conserve actual emitted constituent trajectories with explicit physical scales."""
import copy
import math
from urllib.parse import quote

from .budgets import bind_budget, reference_budget
from .canonical import schedule_id
from .contract import validate_bundle, validate_request
from .errors import GeneratorError
from .resources import ResourceSet
from .owners import identity_fields,upgrade_generated_reference_identities

BASIS_UNITS = {'floor_area':'m2','dwelling_unit':'dwelling','person':'person','absolute':'1'}
SUFFIXES = {'floor_area':'/m2','dwelling_unit':'/dwelling','person':'/person','absolute':''}


def _fail(path,message):
    raise GeneratorError('incompatible_scale',path,message)


def normalize_basis_bindings(bindings, instance_key):
    """Interpret only explicit physical operands, including the v1 area alias."""
    if set(bindings)-{'extents','multiplicity','floor_area_m2'}:
        _fail('/basis_bindings','Unknown physical binding field')
    result=copy.deepcopy(bindings); receipts={}
    if 'floor_area_m2' in result:
        value=result['floor_area_m2']
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:
            _fail('/basis_bindings/floor_area_m2','Finite nonnegative caller area required')
        receipt={'source_locator':'/instances/'+instance_key+'/basis_bindings/floor_area_m2',
                 'original_value':value,'original_unit':'m2','transformation':'Explicit compatibility alias to extents.floor_area',
                 'interpretation_note':'Caller-declared area, no geometry or dwelling area inferred'}
        receipts['floor_area_m2']=receipt
        extents=result.setdefault('extents',{})
        if 'floor_area' in extents:
            extent=extents['floor_area']
            if extent['value']!=value or extent['unit']!='m2':
                _fail('/basis_bindings/floor_area_m2','Area alias conflicts with canonical floor-area extent')
        else:
            extents['floor_area']={'value':value,'unit':'m2','evidence':copy.deepcopy(receipt)}
    return result,receipts


def _basis_scale(constituent, basis, mixture):
    bindings = constituent.get('basis_bindings',{})
    multiplicity = bindings.get('multiplicity',1)
    if type(multiplicity) not in (int,float) or not math.isfinite(multiplicity) or multiplicity<0:
        _fail('/basis_bindings/multiplicity','Explicit finite nonnegative multiplicity required')
    extent = bindings.get('extents',{}).get(basis)
    if 'denominator' not in mixture:
        if extent is not None:
            _fail('/mixture/denominator','Physical extents require an explicit result denominator')
        return multiplicity
    if extent is None or basis not in BASIS_UNITS:
        _fail('/basis_bindings/extents/'+basis,'Explicit source-basis physical extent required')
    if extent['unit'] != BASIS_UNITS[basis]:
        _fail('/basis_bindings/extents/'+basis+'/unit','Extent does not cancel the source basis')
    return extent['value']*multiplicity/mixture['denominator']['value']


def _people_basis(constituent):
    occupancy = next((c for c in constituent['controls'] if c['quantity']=='occupancy_fraction'),None)
    if occupancy is None: return None
    evidence = occupancy['evidence']
    if 'residents' in evidence:
        return occupancy, 'dwelling_unit', evidence['residents']
    density = evidence.get('nominal_density')
    if density is None:
        _fail('/controls/'+occupancy['slot'],'Occupancy requires its source nominal density')
    if density['unit'] != 'person'+SUFFIXES.get(density['basis'],'?'):
        _fail('/controls/'+occupancy['slot'],'Incompatible source nominal density unit')
    return occupancy,density['basis'],density['value']


def _qualified_group_weather_records(bundle,group,receipt,version):
    """Validate disclosure owners separately from unchanged consumed science."""
    from .commercial.parametric import _RESTAURANT_CONFIGURATIONS
    from .commercial.source_models import RETAIL_CONFIGURATIONS
    context=receipt.get('context',{})
    owners=[c for c in bundle['constituents'] if c['generation'].get('operating_group')==group]
    def qualified(value):
        return (isinstance(value,dict) and value.get('source_hoo_configuration_id') in _RESTAURANT_CONFIGURATIONS|RETAIL_CONFIGURATIONS and
            isinstance(value.get('occupancy_aggregation'),dict) and
            value['occupancy_aggregation'].get('policy')=='explicit_source_model_nonresidential_people')
    actual_qualified=any(qualified(c['generation'].get('source_inputs')) for c in owners)
    if not actual_qualified and not qualified(context):
        return None
    if not actual_qualified or not qualified(context):
        raise GeneratorError('operating_group_conflict','/operating_groups/'+group+'/context',
            'Actual qualified owner and root configuration/context differ')
    from .generator import _group_context
    path='/operating_groups/'+group+'/original_owner_weather_records'
    records=receipt.get('original_owner_weather_records')
    if (not isinstance(records,list) or not owners or len(records)!=len(owners) or
            any(not isinstance(r,dict) or not isinstance(r.get('instance_key'),str) for r in records) or
            len({r.get('instance_key') for r in records})!=len(records)):
        raise GeneratorError('invalid_reference',path,'Exact retained input owner weather disclosures required')
    for record,owner in zip(records,owners):
        expected={'instance_key':owner['instance_key'],**identity_fields(owner,version),
                  'weather':owner['source']['weather']}
        if record!=expected:
            raise GeneratorError('invalid_reference',path,'Weather disclosure points to another source/physical owner or original weather')
        source=owner['generation'].get('source_inputs')
        if not isinstance(source,dict) or _group_context({'inputs':{'source_context':source},'source':owner['source']})!=context:
            raise GeneratorError('operating_group_conflict',path,'Actual consumed owner configuration/People/calendar/caller context differs')
        operating=owner['generation'].get('source_context',{}).get('operating_receipt')
        if operating is not None:
            actual=copy.deepcopy(operating);root=copy.deepcopy(receipt['operating'])
            for value in (actual,root):value.get('rng',{}).pop('python_version',None)
            if actual!=root:
                raise GeneratorError('operating_group_conflict',path,'Actual consumed owner group seed/operating draws differ')
    return copy.deepcopy(records)


def compose_constituents(constituents: list[dict], mixture: dict, calendar: dict) -> dict:
    """Compose complete generated bundles, retaining their indexed schedules.

    The input list contains one or more bundles returned by generate without a
    mixture, not stored source profiles or private preparation buffers. Members
    identify their actual constituent keys. Output is another complete bundle,
    with original constituents plus a scoped mixed result owner.
    """
    return _compose_constituents(constituents,mixture,calendar)


def _compose_constituents(constituents,mixture,calendar,*,verified_resources=None):
    """Share composition checks with private same-request source-parent assembly."""
    if verified_resources is not None and type(verified_resources) is not ResourceSet:
        raise GeneratorError('resource_integrity','/resource_set_id','Exact verified ResourceSet required')
    if not isinstance(constituents,list) or not constituents:
        raise GeneratorError('invalid_mixture','/constituents','At least one generated bundle required')
    bundle = None
    version=max((b.get('schema_version','1.0.0') for b in constituents))
    input_receipts=[]; operating_groups={}; qualified_weather_groups=set()
    for incoming in constituents:
        validate_bundle(incoming)
        if verified_resources is not None and verified_resources.resource_set_id!=incoming['metadata']['resource_set_id']:
            raise GeneratorError('resource_integrity','/resource_set_id','Verified request snapshot identity differs')
        if incoming['metadata']['calendar'] != calendar:
            raise GeneratorError('invalid_calendar','/calendar','Constituent calendar differs from mixture')
        if version!='1.2.0' and any(c['generation'].get('method')=='conserved_constituent_mixture' for c in incoming['constituents']):
            raise GeneratorError('invalid_mixture','/constituents','Nested mixed results need an explicit new physical allocation')
        if version=='1.2.0' and any(c['generation'].get('method')=='conserved_constituent_mixture' and
                not c['generation'].get('service_set_selection',{}).get('effective_physical_members') for c in incoming['constituents']):
            raise GeneratorError('invalid_mixture','/constituents','Nested nonwater mixed results retain their existing explicit-allocation boundary')
        # Complete source-parent bundles contain references below demands,
        # targets, magnitudes, services and generation receipts as well as owners.
        from .source_compositions import remap_binding_references
        incoming=copy.deepcopy(incoming)
        if version=='1.2.0' and incoming['schema_version']!='1.2.0':
            from .service_graph import _upgrade_bundle
            incoming=_upgrade_bundle(incoming)
        if version=='1.1.0':
            legacy=incoming['schema_version']=='1.0.0'
            incoming['schema_version']=version
            for record in incoming['constituents']+incoming['bindings']:record.update(identity_fields(record,version))
            if legacy:upgrade_generated_reference_identities(incoming)
        offset=len(bundle['bindings']) if bundle is not None else 0
        remap_binding_references(incoming,{i:i+offset for i in range(len(incoming['bindings']))})
        input_receipts.append(copy.deepcopy(incoming['generation']))
        for group,receipt in incoming['generation'].get('operating_groups',{}).items():
            normalized=copy.deepcopy(receipt)
            normalized.get('operating',{}).get('rng',{}).pop('python_version',None)
            disclosed=_qualified_group_weather_records(incoming,group,receipt,version)
            if disclosed is not None:
                qualified_weather_groups.add(group)
                normalized.pop('original_owner_weather_records')
            previous=copy.deepcopy(operating_groups.get(group))
            prior_disclosed=(previous.pop('original_owner_weather_records',None) if previous is not None else None)
            if group in operating_groups and previous!=normalized:
                raise GeneratorError('operating_group_conflict','/operating_groups/'+group,
                                     'Precomputed group names have conflicting actual source/sample receipts')
            if disclosed is not None:
                combined=(prior_disclosed or [])+disclosed
                if len({r['instance_key'] for r in combined})!=len(combined):
                    raise GeneratorError('invalid_reference','/operating_groups/'+group,'Duplicate retained weather owner identity')
                normalized['original_owner_weather_records']=combined
            elif prior_disclosed is not None:
                # Only the exact qualified source-model policy above may
                # separate this disclosure from its consumed group receipt.
                raise GeneratorError('operating_group_conflict','/operating_groups/'+group,'Conflicting group disclosure policy')
            operating_groups[group]=normalized
        if bundle is None:
            bundle = incoming
            continue
        if (bundle['metadata']['resource_set_id'] != incoming['metadata']['resource_set_id'] or
                bundle['algorithm_version'] != incoming['algorithm_version']):
            raise GeneratorError('invalid_mixture','/constituents','Conflicting source resource/algorithm identities')
        if set(bundle['schedules']) & set(incoming['schedules']):
            raise GeneratorError('duplicate_instance','/constituents','Constituent schedule identities overlap')
        bundle['schedules'].update(copy.deepcopy(incoming['schedules']))
        bundle['bindings'].extend(copy.deepcopy(incoming['bindings']))
        if version=='1.2.0':
            retained={r['building_realization_id']:r for r in bundle['metadata']['building_realizations']}
            for realization in incoming['metadata']['building_realizations']:
                key=realization['building_realization_id']
                if key in retained and retained[key]!=realization:
                    raise GeneratorError('shared_service_conflict','/metadata/building_realizations','Conflicting retained realization authority')
                if key not in retained:
                    bundle['metadata']['building_realizations'].append(copy.deepcopy(realization));retained[key]=realization
        for c in copy.deepcopy(incoming['constituents']):
            bundle['constituents'].append(c)
    if len(input_receipts)>1:
        bundle['generation']={'method':'precomputed_bundle_composition_v1',
                              'input_generation_receipts':input_receipts,
                              'seed_interpretation':'Preserve actual input allocations; no multifamily reallocation or reseeding'}
        if version=='1.2.0':
            bundle['generation'].update(physical_unit_seed_sequence=[],residential_unit_order=[],unit_seeds={})
        if qualified_weather_groups:
            bundle['generation']['operating_groups']=copy.deepcopy(operating_groups)
            bundle['generation']['operating_group_disclosure_scope']='All retained generated input owners in input order; mixture participation is separately disclosed'
    instances = [{'key':c['instance_key'],**identity_fields(c,version),'inputs':{},
                  'basis_bindings':c.get('basis_bindings',{}),'operating_group':None} for c in bundle['constituents']]
    reconstructed={'resource_set_id':bundle['metadata']['resource_set_id'],'calendar':calendar,
                   'instances':instances,'mixture':mixture}
    if version=='1.1.0':reconstructed['schema_version']=version
    if version=='1.2.0':
        from .contract import _check_schema,_load_schema
        schema=_load_schema('request',version)
        _check_schema(mixture,schema['properties']['mixture'],schema,'/mixture')
        keys={i['key']:i for i in instances};weighted=mixture['members'];explicit=mixture.get('service_members',[])
        if (not weighted and not explicit or len({m['instance_key'] for m in weighted})!=len(weighted) or
                len({m['instance_key'] for m in explicit})!=len(explicit) or
                any(m['instance_key'] not in keys or keys[m['instance_key']]['owner_kind']=='physical_service' for m in weighted) or
                any(m['instance_key'] not in keys or keys[m['instance_key']]['owner_kind']!='physical_service' for m in explicit) or
                weighted and mixture['composition_id'] is None and not math.isclose(math.fsum(m['weight'] for m in weighted),1,rel_tol=0,abs_tol=1e-12)):
            raise GeneratorError('invalid_mixture','/mixture','Unique actual members and normalized programme participation required')
    else:validate_request(reconstructed,0)
    if ('denominator' in mixture) != ('result_basis' in mixture):
        _fail('/mixture','Result basis and physical denominator must be supplied together')
    if 'denominator' in mixture:
        denominator=mixture['denominator']
        if denominator['value']<=0 or denominator['unit']!=BASIS_UNITS[mixture['result_basis']]:
            _fail('/mixture/denominator','Positive denominator with matching result-basis unit required')
    owners={c['instance_key']:c for c in bundle['constituents']}
    members=[(owners[m['instance_key']],m['weight']) for m in mixture['members']]
    source_recipe=None;source_receipt=None
    if mixture['composition_id'] is not None:
        from .source_compositions import validate_allocation
        resources=verified_resources if verified_resources is not None else ResourceSet.load(bundle['metadata']['resource_set_id'])
        source_recipe,source_receipt=validate_allocation(mixture,members,resources)
    service_members=[];service_receipt=None
    if version=='1.1.0':
        from .services import select_whole_services
        service_members,service_receipt=select_whole_services(bundle,mixture,members)
    elif version=='1.2.0':
        from .service_graph import select_physical_services
        service_members,service_receipt=select_physical_services(bundle,mixture,members)
    load_members=members+service_members
    for c,w in load_members:
        physical,receipts=normalize_basis_bindings(c.get('basis_bindings',{}),c['instance_key'])
        c['basis_bindings']=physical
        if receipts:c['generation']['basis_alias_receipts']=receipts
    all_bases={d['basis'] for c,w in load_members for d in c['demands']}
    all_bases.update(p[1] for c,w in members if (p:=_people_basis(c)) is not None)
    if 'result_basis' not in mixture and len(all_bases)>1:
        _fail('/mixture/denominator','Mixed source bases require explicit physical conversion and denominator')
    result_basis=mixture.get('result_basis',next(iter(all_bases),'absolute'))
    if result_basis not in BASIS_UNITS: _fail('/mixture/result_basis','Unknown physical basis')
    bundle=_derive_constituent(bundle,mixture,members,load_members,result_basis,
                               source_recipe,source_receipt,service_receipt)
    validate_bundle(bundle)
    return bundle


def _derive_constituent(bundle,mixture,members,load_members,result_basis,
                        source_recipe,source_receipt,service_receipt):
    """Shared arithmetic for validated incoming or privately prepared source data."""
    version=bundle['schema_version'];calendar=bundle['metadata']['calendar']
    owners={c['instance_key']:c for c in bundle['constituents']}
    key='mixture/'+mixture['program_id']
    if key in owners: raise GeneratorError('duplicate_instance','/mixture/program_id','Mixed result key overlaps an instance')
    mixed={'instance_key':key,'program_id':mixture['program_id'],'recipe_id':'conserved-mixture-v1',
           'source':{'source_family':'derived_mixture','source_id':'actual_generated_constituents',
                     'template':None,'vintage':None,'weather':None,'evidence_view':'derived'},
           'inputs':copy.deepcopy(mixture),'basis_bindings':{},'slots':[],'demands':[],'controls':[],
           'shared_services':[],'evidence':[{'method':'sum_weighted_original_annual_targets',
                                           'interpretation':'Explicit experimental allocation; no population weights or inferred geometry'}],
           'schedule_ids':{},'binding_indices':[],
           'generation':{'method':'conserved_constituent_mixture','result_basis':result_basis,
                         'weight_interpretation':'participation_multipliers_with_explicit_extents' if 'denominator' in mixture else 'normalized_source_basis_weights',
                         'denominator':copy.deepcopy(mixture.get('denominator',{'value':1,'unit':BASIS_UNITS[result_basis],
                            'evidence':{'interpretation':'One declared source basis unit; homogeneous weighted source-basis average, no inferred geometry'}})),
                         'members':copy.deepcopy(mixture['members']),'people_pairs':[],'control_policy':
                         'Active-member weight-normalized representative thermostats; water/activity/occupancy stay paired with actual members'}}
    if source_recipe is not None:
        definition=source_recipe['definition']
        mixed['source'].update(template=definition['template'],evidence_view=definition['evidence_view'],
                              source_id=definition['id'],source_family='source_composition')
        mixed['generation'].update(method='conserved_source_composition',source_allocation=source_receipt,
            control_policy='ADR0012 source represented-area pointwise eligible control average; no thermal conservation claim')
        mixed['evidence'].append({'source_composition':copy.deepcopy(source_receipt)})
    if version in {'1.1.0','1.2.0'}:
        mixed['owner_kind']='program' if source_recipe is not None else 'derived_result'
        mixed['required_service_links']=[]
        if version=='1.2.0':mixed.update(required_service_sets=[],service_set_projections=[])
    if service_receipt is not None:mixed['generation']['service_set_selection' if version=='1.2.0' else 'service_selection']=service_receipt
    def emit(slot,unit,kind,values):
        sid=schedule_id(key,slot)
        bundle['schedules'][sid]={'id':sid,'unit':unit,'year':calendar['year'],'clock':calendar['clock'],
                                  'timestep_minutes':60,'values':values}
        mixed['slots'].append({'slot':slot,'source_schedule_id':'generated-member-trajectories',
                               'unit':unit,'kind':kind})
        mixed['schedule_ids'][slot]=sid
        return sid
    def control(slot,unit,quantity,values,evidence):
        sid=emit(slot,unit,'control',values)
        mixed['controls'].append({'slot':slot,'quantity':quantity,'unit':unit,'evidence':evidence})
        mixed['binding_indices'].append(len(bundle['bindings']))
        bundle['bindings'].append({'kind':'control','instance_key':key,**identity_fields(mixed,version),
                                  'slot':slot,'schedule_id':sid,'control_quantity':quantity})
    groups={}; services={}
    for c,weight in load_members:
        for index in c['binding_indices']:
            binding=bundle['bindings'][index]
            if binding['kind']!='load': continue
            demand=next(d for d in c['demands'] if d['demand_id']==binding['demand_id'])
            basis=demand['basis']; factor=weight*_basis_scale(c,basis,mixture)
            carrier='m3/s' if demand['unit'].startswith('m3/s') else 'W' if demand['unit'].startswith('W') else None
            if carrier is None or demand['unit']!=carrier+SUFFIXES.get(basis,'?'):
                _fail('/demands/'+demand['demand_id'],'Demand unit does not match its declared source basis')
            group=(demand['quantity'],carrier,demand['fuel'],demand['host'])
            descriptor=next((s for s in c['shared_services'] if s.get('demand_id')==demand['demand_id'] and s.get('physical_id')),None)
            if descriptor is not None:
                if descriptor.get('mode') != 'whole':
                    raise GeneratorError('requires_binding','/shared_services/'+descriptor['physical_id'],
                                         'Allocated components require audited source-total/already-allocated semantics; unavailable in M1')
                extent=descriptor.get('extent')
                if ('denominator' not in mixture or not isinstance(extent,dict) or
                        set(extent)!={'value','unit','evidence'} or extent['unit']!=BASIS_UNITS[basis] or
                        type(extent['value']) not in (int,float) or not math.isfinite(extent['value']) or extent['value']<0 or not extent['evidence']):
                    raise GeneratorError('requires_binding','/shared_services/'+descriptor['physical_id'],
                                         'Whole physical service needs explicit source extent and result denominator')
                identity={'source_service_id':descriptor.get('source_service_id'),'demand':demand,
                          'reference_target':binding['reference_target'],'extent':extent,
                          'values':bundle['schedules'][binding['schedule_id']]['values']}
                physical_id=descriptor['physical_id']
                service_key=physical_id
                if version=='1.2.0':
                    from .owners import physical_identity
                    service_key=physical_identity(c)
                if service_key in services:
                    previous=services[service_key]
                    if previous['identity']!=identity:
                        raise GeneratorError('shared_service_conflict','/shared_services/'+physical_id,
                                             'Repeated whole physical service differs in source/budget/extent/trajectory')
                    previous['receipt']['links'].append({'instance_key':c['instance_key'],
                                                         'descriptor':copy.deepcopy(descriptor)})
                    continue
                receipt={'physical_id':physical_id,'ownership':'instantiate_once','mode':'whole',
                         'links':[{'instance_key':c['instance_key'],'descriptor':copy.deepcopy(descriptor)}],
                         'interpretation':'Whole source service emitted once; informational allocation/program weights do not rescale it'}
                services[service_key]={'identity':identity,'receipt':receipt}
                mixed['shared_services'].append(receipt)
                factor=extent['value']/mixture['denominator']['value']
            groups.setdefault(group,[]).append({'binding_index':index,'schedule_id':binding['schedule_id'],
                                               'instance_key':c['instance_key'],'demand_id':demand['demand_id'],
                                               'factor':factor,'heat_fractions':demand.get('heat_fractions'),
                                               **(identity_fields(c,version) if version in {'1.1.0','1.2.0'} else {})})
    for (quantity,carrier,fuel,host),components in groups.items():
        slot='load/'+ '/'.join(quote(part,safe='') for part in (quantity,carrier,fuel,host))
        unit=carrier+SUFFIXES[result_basis]
        target_total=math.fsum(c['factor']*bundle['bindings'][c['binding_index']]['reference_target']['total'] for c in components)
        if len(components)==1:
            component=components[0]; binding=bundle['bindings'][component['binding_index']]
            values=list(bundle['schedules'][component['schedule_id']]['values'])
            amplitude=binding['effective_magnitude']['value']*component['factor']
        else:
            powers=[math.fsum(c['factor']*bundle['bindings'][c['binding_index']]['effective_magnitude']['value']*
                              bundle['schedules'][c['schedule_id']]['values'][h] for c in components) for h in range(8760)]
            amplitude=math.fsum(c['factor']*bundle['bindings'][c['binding_index']]['effective_magnitude']['value'] for c in components)
            values=[p/amplitude if amplitude else 0.0 for p in powers]
        evidence={'method':'actual_generated_bound_trajectory_sum','components':components,
                  'normalization':'Divide hourly trajectory by sum of scaled bound magnitudes; bind actual emitted integral to summed original target',
                  'denominator':copy.deepcopy(mixture.get('denominator')),
                  'heat_partition':'Annual energy weighted constant fractions; hourly partition is an approximation'}
        annual_weights=[c['factor']*bundle['bindings'][c['binding_index']]['reference_target']['total'] for c in components]
        fractions=None
        active=[(c,e) for c,e in zip(components,annual_weights) if e>0]
        if carrier=='W' and active and all(c['heat_fractions'] is not None for c,e in active):
            names=set(active[0][0]['heat_fractions'])
            if any(set(c['heat_fractions'])!=names for c,e in active):
                _fail('/demands/'+slot,'Incompatible heat fraction decomposition')
            fractions={n:math.fsum(e*c['heat_fractions'][n] for c,e in active)/target_total for n in names}
        demand={'demand_id':slot,'slot':slot,'quantity':quantity,'value':None,'unit':unit,
                'basis':result_basis,'fuel':fuel,'host':host,'evidence':evidence,'heat_fractions':fractions,
                'annual_target':{'total':target_total,'unit':('m3' if carrier=='m3/s' else 'Wh')+SUFFIXES[result_basis],
                                 'evidence':evidence}}
        bound=bind_budget(reference_budget(demand,[]),values)
        sid=emit(slot,'fraction','load',values)
        mixed['demands'].append(demand); mixed['binding_indices'].append(len(bundle['bindings']))
        bundle['bindings'].append(dict(bound,kind='load',instance_key=key,**identity_fields(mixed,version),
                                       demand_id=slot,slot=slot,schedule_id=sid,fuel=fuel,host=host,budget_method='direct_annual'))
    for c,weight in members:
        if c['generation'].get('method')=='conserved_source_composition':
            for pair in c['generation']['people_pairs']:
                pair=copy.deepcopy(pair)
                pair['factor']*=weight*_basis_scale(c,c['generation']['result_basis'],mixture)
                mixed['generation']['people_pairs'].append(pair)
            continue
        people=_people_basis(c)
        if people is None: continue
        occupancy,basis,density=people
        activity=next((x for x in c['controls'] if x['quantity']=='activity'),None)
        if density==0 and activity is None: continue  # actual zero-resident source skip
        if activity is None: _fail('/controls/activity','Active occupancy lacks its paired source activity')
        mixed['generation']['people_pairs'].append({'instance_key':c['instance_key'],'density':density,
             'source_basis':basis,'factor':weight*_basis_scale(c,basis,mixture),
             'occupancy_schedule_id':c['schedule_ids'][occupancy['slot']],
             'activity_schedule_id':c['schedule_ids'][activity['slot']],
             'evidence':{'occupancy':copy.deepcopy(occupancy['evidence']),'activity':copy.deepcopy(activity['evidence'])}})
    pairs=mixed['generation']['people_pairs']
    if pairs:
        heat=[math.fsum(p['density']*p['factor']*bundle['schedules'][p['occupancy_schedule_id']]['values'][h]*
                         bundle['schedules'][p['activity_schedule_id']]['values'][h] for p in pairs) for h in range(8760)]
        control('people_heat','W'+SUFFIXES[result_basis],'people_heat',heat,
                {'method':'sum_each_load_density_occupancy_activity','pairs':copy.deepcopy(pairs)})
    for slot in ('heating_setpoint','cooling_setpoint'):
        control_members=[(c,w*_basis_scale(c,'floor_area',mixture)) for c,w in members] if source_recipe is not None else members
        active=[(c,w) for c,w in control_members if w>0 and slot in c['schedule_ids'] and
                c.get('basis_bindings',{}).get('multiplicity',1)>0 and
                all(e['value']>0 for e in c.get('basis_bindings',{}).get('extents',{}).values())]
        total=math.fsum(w for c,w in active)
        if total:
            values=[math.fsum(w*bundle['schedules'][c['schedule_ids'][slot]]['values'][h] for c,w in active)/total for h in range(8760)]
            control(slot,'C','temperature',values,{'interpretation':'Representative control, not thermal-load conservation',
                    'method':'source_represented_area_pointwise_eligible_average' if source_recipe is not None else 'active_member_weight_normalized_average',
                    'active_members':[c['instance_key'] for c,w in active],
                    **({'active_factors':[w for c,w in active],'source_allocation':copy.deepcopy(source_receipt)} if source_recipe is not None else {})})
    if not mixed['slots']:
        mixed['evidence'][0]['accepted_absence']=all(c['evidence'][0].get('accepted_absence') for c,w in members)
    bundle['constituents'].append(mixed)
    bundle['generation']['mixture']=copy.deepcopy(mixture)
    return bundle
