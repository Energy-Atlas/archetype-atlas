"""Normalize deterministic program demands without duplicating shared services."""
import copy
from scripts.common import load_json
from scripts.definition_contract import (DefinitionBundle, DefinitionError, evidence,
                                         parameter, record, stable_id)

LOADS = {
    'people_per_m2': ('occupancy', 'person/m2', 'occupancy_schedule_id'),
    'lighting_W_m2': ('lighting', 'W/m2', 'lighting_schedule_id'),
    'additional_lighting_W_m2': ('additional_lighting', 'W/m2', 'lighting_schedule_id'),
    'electric_equipment_W_m2': ('electric_equipment', 'W/m2', 'electric_equipment_schedule_id'),
    'gas_equipment_W_m2': ('gas_equipment', 'W/m2', 'gas_equipment_schedule_id'),
}


def evaluate_load(load, bases, schedule_value=1):
    """Scale one physical demand; this is not a model instantiation or unit converter."""
    if load['value'] is None or schedule_value is None:
        return None
    basis = load['basis']
    if basis == 'absolute':
        scale = 1
    elif basis in bases and bases[basis] is not None and bases[basis] >= 0:
        scale = bases[basis]
    else:
        raise DefinitionError('Required load basis: '+basis)
    return load['value']*scale*schedule_value


def unique_services(services):
    result = {}
    for service in services:
        if service['id'] in result and result[service['id']] != service:
            raise DefinitionError('Conflicting shared service')
        result[service['id']] = service
    return list(result.values())


def source_evidence(context, source, field, unit, bundle):
    prov = next((p for p in context.atlas.get('provenance', [])
                 if p['id'] == source.get('provenance_id')), {})
    original = prov.get('fields', {}).get(field, {})
    row = evidence(context, prov.get('source_file_id'),
                   prov.get('locator', source['id'])+'/'+original.get('original_field', field),
                   original.get('original_value', source.get(field)),
                   original.get('original_units', unit),
                   original.get('transformation', 'retain normalized source value'),
                   prov.get('notes') or 'Null remains unknown; no generic replacement.')
    bundle['provenance'].append(row)
    return row['id']


def _completion(context):
    relative = context.policy.get('dependencies', {}).get('completion')
    return load_json(context.root/relative/'commercial-completion.json') if relative else {}


def build_programs(context):
    bundle = DefinitionBundle()
    source_to_record = {}
    for source in context.atlas.get('programs', []):
        if not context.includes(source):
            continue
        row = record('program', source, source.get('source_space_type', source['program'])+'_'+source['building_type'])
        row.update(detail='SourcePrograms', loads=[], service_ids=[],
                   optional=any(token in source.get('source_space_type', '').lower()
                                for token in ('attic', 'basement')))
        for field, (quantity, unit, schedule) in LOADS.items():
            eid = source_evidence(context, source, field, unit, bundle)
            load = parameter(source.get(field), unit, eid, required_inputs=['floor_area'])
            load.update(quantity=quantity, basis='floor_area', schedule_id=source.get(schedule),
                        demand_id=stable_id('demand', {'program': source['id'], 'field': field}),
                        thermal_effects={}, scope='program')
            prefix = 'lighting' if 'lighting' in field else quantity
            for suffix in ('radiant', 'latent', 'lost', 'visible', 'to_return_air'):
                key = prefix+'_fraction_'+suffix
                if key in source.get('source_attributes', {}):
                    a = source['source_attributes'][key]
                    thermal = evidence(context, next(p for p in bundle['provenance'] if p['id']==eid)['source_file_id'],
                                       source['id']+'/source_attributes/'+key, a, 'dimensionless',
                                       'identity', 'Source physical effect; unknown remains unknown.')
                    bundle['provenance'].append(thermal)
                    load['thermal_effects'][suffix] = parameter(a, '1', thermal['id'])
            row['loads'].append(load)
            row['evidence_ids'].append(eid)
        for field in ('heating_setpoint_schedule_id', 'cooling_setpoint_schedule_id', 'activity_schedule_id'):
            eid = source_evidence(context, source, field, 'schedule reference', bundle)
            row['parameters'][field] = parameter(source.get(field), 'schedule reference', eid)
            row['evidence_ids'].append(eid)
        row['required_inputs'] = ['floor_area']
        source_to_record[source['id']] = row
        bundle['programs'].append(row)
    completion = _completion(context)
    for draw in completion.get('draw_paths', []):
        if not context.includes(draw):
            continue
        eid_row = evidence(context, None, 'commercial-completion/draw_paths/'+draw['path_id'],
                           {'value': draw['original_flow'], 'alternate': draw.get('alternate_original_total')},
                           draw['original_flow_unit'], 'source helper default branch, not alternate branch',
                           draw['interpretation_note'])
        bundle['provenance'].append(eid_row)
        area = draw['rated_flow_per_area_m3_s_m2'] is not None
        service_id = stable_id('service', {'path_id': draw['path_id']})
        demand = parameter(draw['rated_flow_per_area_m3_s_m2'] if area else draw['rated_flow_m3_s'],
                           'm3/s/m2' if area else 'm3/s', eid_row['id'],
                           required_inputs=['floor_area'] if area else [])
        demand.update(quantity='hot_water_volume', basis='floor_area' if area else 'absolute',
                      schedule_id=draw.get('matching_atlas_schedule_ids', [None])[0]
                      if draw.get('matching_atlas_schedule_ids') else None,
                      demand_id=service_id, service_id=service_id, scope='building_service',
                      thermal_effects={}, target_temperature_degC=draw.get('target_temperature_degC'),
                      zone_heat_assignment='unresolved')
        service = {'id': service_id, 'path_id': draw['path_id'], 'building_type': draw['building_type'],
                   'template': draw['template'], 'end_use': draw['end_use'], 'load': demand,
                   'ownership': 'instantiate_once', 'assignment': 'consumer_host_when_applicable',
                   'beneficiary_program_ids': draw['beneficiary_program_ids'],
                   'evidence_ids': [eid_row['id']], 'source_evidence_ids': draw['evidence_ids']}
        bundle['services'].append(service)
        for pid in draw['beneficiary_program_ids']:
            if pid in source_to_record:
                source_to_record[pid]['service_ids'].append(service_id)
        # Local area-based fixture demand is part of its source program once.
        # Other/shared service references never copy the service into each program.
        if area and len(draw['beneficiary_program_ids']) == 1:
            pid = draw['beneficiary_program_ids'][0]
            if pid in source_to_record:
                source_to_record[pid]['loads'].append(dict(demand, scope='program_service'))
    schedule_ids = {load['schedule_id'] for row in bundle['programs'] for load in row['loads']}
    schedule_ids |= {p['value'] for row in bundle['programs'] for p in row['parameters'].values()}
    schedule_ids |= {s['load']['schedule_id'] for s in bundle['services']}
    bundle['schedules'] = [copy.deepcopy(s) for s in context.atlas.get('schedules', []) if s['id'] in schedule_ids]
    for item in completion.get('schedules', []):
        for field in ('source_schedule', 'equivalent_schedule'):
            if item[field]['id'] in schedule_ids:
                bundle['schedules'].append(copy.deepcopy(item[field]))
    apply_reviewed(context, bundle)
    return DefinitionBundle().merge(bundle)


def apply_reviewed(context, bundle):
    relative = context.policy.get('dependencies', {}).get('resolution')
    if not relative:
        return
    resolutions = load_json(context.root/relative/'resolutions.json')['resolutions']
    by_source = {}
    for item in resolutions:
        if item['record_table'] == 'programs':
            by_source.setdefault(item['record_id'], []).append(item)
    for source in list(bundle['programs']):
        if source['source_id'] not in by_source:
            continue
        reviewed = copy.deepcopy(source)
        reviewed.update(id=stable_id('program', {'source': source['id'], 'view': 'reviewed'}),
                        evidence_view='reviewed', source_definition_id=source['id'])
        applied = []
        for item in by_source[source['source_id']]:
            field, value = item['field'], item['resolved_value']
            eid = evidence(context, None, 'resolution/'+item['id'], value, item['unit'],
                           'explicit frozen reviewed overlay', item['note'])
            resolved = value
            if isinstance(value, dict) and 'constant_value' in value:
                sid = stable_id('schedule', {'resolution': item['id'], 'value': value})
                bundle['schedules'].append({'id': sid, 'source_name': item['id'],
                    'schedule_type': 'fraction', 'units': item['unit'], 'time_resolution_minutes': 60,
                    'calendar_independent': value['calendar_independent'], 'rules': [
                        {'day_types': 'Default', 'start_date': '2000-01-01', 'end_date': '2000-12-31',
                         'values': [value['constant_value']], 'source_index': 0}],
                    'evidence_ids': [eid['id']]})
                resolved = sid
            elif isinstance(value, dict):
                # Consumer schedule/profile objects are handled by the residential adapter.
                if field.endswith('_schedule_id'):
                    continue
            for load_field, (_, _, schedule_field) in LOADS.items():
                for load in reviewed['loads']:
                    if load['quantity'] == LOADS[load_field][0]:
                        if field == schedule_field:
                            load['schedule_id'] = resolved
                        elif field == load_field:
                            load.update(parameter(resolved, load['unit'], eid['id'],
                                                  required_inputs=load['required_inputs']))
            if field in reviewed['parameters'] or field == 'conditioning':
                reviewed['parameters'][field] = parameter(resolved, item['unit'], eid['id'])
            applied.append(item['id'])
            bundle['provenance'].append(eid)
            reviewed['evidence_ids'].append(eid['id'])
        reviewed['reviewed_resolution_ids'] = applied
        bundle['programs'].append(reviewed)
