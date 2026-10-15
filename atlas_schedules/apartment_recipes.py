"""Pure assembly of exact apartment recipes from already verified originals."""
import copy
import hashlib

from .canonical import canonical
from .errors import GeneratorError

CALENDAR = {'year': 2007, 'clock': 'local_standard_time', 'holidays': []}
ORDERED_PROGRAMME_IDS_SHA256 = '3c0d169db7dd01f6cf0ebd5ce1c5a77d991d5a1cf16891b36178d6167c6794f0'
SLOTS = {'occupancy': 'occupants', 'lighting': 'lighting_interior',
         'additional_lighting': 'additional_lighting',
         'electric_equipment': 'electric_equipment', 'gas_equipment': 'gas_equipment'}
CONTROL_SLOTS = {'activity_schedule_id': ('activity', 'W/person', 'activity'),
                 'heating_setpoint_schedule_id': ('heating_setpoint', 'C', 'temperature'),
                 'cooling_setpoint_schedule_id': ('cooling_setpoint', 'C', 'temperature')}
HELPERS = ('lib/openstudio-standards/standards/Standards.ServiceWaterHeating.rb',
           'lib/openstudio-standards/service_water_heating/create_water_use.rb')


def _fail(path,message,code='source_integrity'):
    raise GeneratorError(code,path,message)

def _object(path, sha, locator, value):
    return {'path': path, 'sha256': sha, 'locator': locator, 'value': copy.deepcopy(value)}


def _derived(name, value):
    # The canonical value is regenerated from verified originals. It is not a
    # qualification certificate or a claim that a generated file ships today.
    return _object('derived/apartment-a2/' + name + '.json',
                   hashlib.sha256(canonical(value)).hexdigest(), '/', value)


def _field(path, sha, locator, value, unit, transformation):
    return {'source_revision': 'c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907',
            'source_path': path, 'source_sha256': sha, 'locator': locator,
            'original_value': copy.deepcopy(value), 'original_unit': unit,
            'transformation': transformation, 'extraction_date': '2026-10-15',
            'interpretation_note': 'Original selected source field; source-only, no native fixture qualification'}


def _water_evidence(programme, service, schedule, row, helpers):
    raw = row['value']; path = row['path']; sha = row['sha256']; locator = row['locator']
    fields = (('service_water_heating_peak_flow_per_area', 'US gal/h/ft2'),
              ('service_water_heating_target_temperature', 'F'),
              ('service_water_heating_fraction_sensible', '1'),
              ('service_water_heating_fraction_latent', '1'),
              ('service_water_heating_system_type', None))
    evidence = [_field(path, sha, locator + '/' + key, raw[key], unit,
                       'Retain original source field; SI conversion where required')
                for key, unit in fields]
    evidence += [_field(h['path'], h['sha256'], '/', h['value'], 'Ruby source',
                        'Retain complete pinned helper source') for h in helpers]
    conversion = 0.003785411784 / 3600 / 0.09290304
    density = raw['service_water_heating_peak_flow_per_area']
    temperature = raw['service_water_heating_target_temperature']
    controls = _derived('controls-' + programme['value']['id'], {
        'source_space_type': row, 'source_helpers': helpers,
        'selected_branch': 'is_flow_per_area_true',
        'original_density': {'value': density, 'unit': 'US gal/h/ft2',
                             'canonical_value': density * conversion, 'canonical_unit': 'm3/s/m2'},
        'target_temperature': {'original_value': temperature, 'original_unit': 'F',
                               'canonical_value': (temperature - 32) / 1.8, 'canonical_unit': 'C'},
        'sensible_fraction': {'value': raw['service_water_heating_fraction_sensible'], 'unit': '1'},
        'latent_fraction': {'value': raw['service_water_heating_fraction_latent'], 'unit': '1'},
        'source_system_type': raw['service_water_heating_system_type'], 'evidence': evidence})
    matches = [(i, load) for i, load in enumerate(programme['value']['loads'])
               if load['quantity'] == 'hot_water_volume']
    if len(matches) != 1:
        _fail('/programme/loads', 'One independently bound source water load required', 'requires_binding')
    i, load = matches[0]
    original = _object(programme['path'], programme['sha256'],
                       programme['locator'] + '/loads/' + str(i), load)
    association = _derived('association-' + programme['value']['id'], {
        'programme': programme, 'original_demand': original,
        'service_definition': service, 'source_ruleset': schedule,
        'fixed_controls': controls, 'source_system_type': row,
        'reference_calendar': CALENDAR, 'evidence': evidence})
    return {'field_evidence': evidence, 'source_system_type': row,
            'fixed_controls': controls, 'association': association}


def compile_recipes(records: dict, scope: dict) -> dict:
    rules = records['source_objects']['schedules']
    proof = records['source_objects']['field_evidence']
    result = {}
    for item in scope['programmes']:
        pid = item['id']; obj = records['programmes'][pid]; p = obj['value']
        slots = []; demands = []; controls = []; sources = {}; companions = {}
        unresolved = []; explicit_zero = []
        for load in p['loads']:
            q = load['quantity']; state = load['status']; sid = load['schedule_id']
            if q == 'hot_water_volume':
                continue  # Independent physical service: never a local programme owner.
            if state == 'unknown':
                unresolved.append({'quantity': q, 'original_load': copy.deepcopy(load),
                                   'field_evidence': copy.deepcopy(proof[load['evidence_id']]),
                                   'state': 'requires_binding'})
                continue
            if state != 'known' or (sid is not None and sid not in rules):
                _fail('/programmes/' + pid + '/loads/' + q, 'Known load has invalid original rule', 'requires_binding')
            slot = SLOTS[q]
            if load['value'] == 0:
                explicit_zero.append({'quantity': q, 'original_load': copy.deepcopy(load),
                                      'field_evidence': copy.deepcopy(proof[load['evidence_id']])})
            if sid is None:
                if load['value'] != 0:
                    _fail('/programmes/' + pid + '/loads/' + q, 'Positive load lacks source rule', 'requires_binding')
                continue
            source = rules[sid]['value']
            sources[slot] = copy.deepcopy(source)
            if q == 'occupancy':
                slots.append({'slot': slot, 'source_schedule_id': sid,
                              'unit': 'fraction', 'kind': 'control'})
                controls.append({'slot': slot, 'quantity': 'occupancy_fraction', 'unit': 'fraction',
                                 'evidence': {'original_load': copy.deepcopy(load),
                                              'field_evidence': copy.deepcopy(proof[load['evidence_id']]),
                                              'nominal_density': {'value': load['value'],
                                                                  'unit': load['unit'], 'basis': load['basis']}}})
                continue
            if load['value'] == 0:
                continue
            ev = proof[load['evidence_id']]['value']
            source_field = ev['locator'].rsplit('/', 1)[-1]
            expected = {'lighting': 'lighting_per_area', 'additional_lighting': 'additional_lighting_per_area',
                        'electric_equipment': 'electric_equipment_per_area',
                        'gas_equipment': 'gas_equipment_per_area'}[q]
            if source_field != expected:
                _fail('/programmes/' + pid + '/loads/' + q, 'Fuel/slot source field differs')
            if load['scope'] != 'program' or load['basis'] != 'floor_area':
                _fail('/programmes/' + pid + '/loads/' + q, 'Assigned-zone host lacks programme scope')
            fuel = 'natural_gas' if q == 'gas_equipment' else 'electricity'
            slots.append({'slot': slot, 'source_schedule_id': sid,
                          'unit': 'fraction', 'kind': 'load'})
            demands.append({'demand_id': load['demand_id'], 'slot': slot, 'quantity': q,
                            'value': load['value'], 'unit': load['unit'], 'basis': load['basis'],
                            'fuel': fuel, 'host': 'assigned_zone',
                            'evidence': {'original_load': copy.deepcopy(load),
                                         'field_evidence': copy.deepcopy(proof[load['evidence_id']]),
                                         'source_field': source_field,
                                         'source_scope': load['scope'],
                                         'host_interpretation': 'Original programme-scoped space-type load'}})
        for name, (slot, unit, kind) in CONTROL_SLOTS.items():
            param = p['parameters'][name]
            if param['status'] == 'unknown':
                unresolved.append({'quantity': name, 'original_parameter': copy.deepcopy(param),
                                   'field_evidence': copy.deepcopy(proof[param['evidence_id']]),
                                   'state': 'requires_binding'})
                continue
            sid = param['value']
            if sid not in rules:
                _fail('/programmes/' + pid + '/parameters/' + name, 'Known control rule missing')
            source = rules[sid]['value']; sources[slot] = copy.deepcopy(source)
            slots.append({'slot': slot, 'source_schedule_id': sid, 'unit': unit, 'kind': 'control'})
            controls.append({'slot': slot, 'quantity': kind, 'unit': unit,
                             'evidence': {'original_parameter': copy.deepcopy(param),
                                          'field_evidence': copy.deepcopy(proof[param['evidence_id']])}})
            companions[slot] = {'method': 'source_rules', 'source': copy.deepcopy(source),
                                'evidence': copy.deepcopy(proof[param['evidence_id']])}
        dwelling = item['role'] == 'dwelling'
        method = 'unit_occupancy_interior_lighting' if dwelling else 'source_fixed_apartment_programme'
        bound = {'apartment_method': method}
        required = ['year', 'apartment_method'] + (['N'] if dwelling else [])
        recipe = {'schema_version': '1.0.0', 'bound_inputs': bound,
                  'variable_inputs': {}, 'required_inputs': required,
                  'reference_year': 2007, 'calendar_year_locked': True,
                  'reference_sources': sources, 'companion_rules': companions,
                  'aggregate_binding_policy': 'original_definition_demands',
                  'source_context': {'method': method, 'qualification_state': 'closed',
                                     'calendar': CALENDAR, 'original_programme': copy.deepcopy(obj),
                                     'original_source_row': copy.deepcopy(records['source_objects']['raw_rows'][pid]),
                                     'unresolved_exclusions': unresolved,
                                     'explicit_zero': explicit_zero,
                                     'selected_N0_policy': ('source_measure_skip_and_original_fixed_rule_retention'
                                                            if dwelling else None),
                                     'timing_domain': copy.deepcopy(scope['timing_domain'])},
                  'resolved': {'recipe_id': 'apartment-' + pid,
                               'source_family': p['source_family'],
                               'source': {'source_id': p['source_id'], 'building_type': p['building_type'],
                                          'template': p['template'], 'vintage': None,
                                          'evidence_view': p['evidence_view'], 'weather': None},
                               'slots': slots, 'demands': demands, 'controls': controls,
                               'shared_services': [],
                               'evidence': [{'original_programme': copy.deepcopy(obj),
                                             'candidate_state': 'closed'}]}}
        if dwelling:
            recipe['required_service_sets'] = [copy.deepcopy(records['requirements'][pid])]
            recipe['required_service_links'] = []
            recipe['required_contract_version'] = '1.2.0'
            recipe['source_context']['nominal_density'] = next(
                copy.deepcopy(x['evidence']['nominal_density']) for x in controls
                if x['slot'] == 'occupants')
            recipe['source_context']['N_domain'] = 'integer >= 0; boolean rejected'
            recipe['source_context']['master_seed_domain'] = 'top-level generate seed: unsigned 64-bit integer; boolean rejected'
            recipe['source_context']['rho_times_A'] = 'control receipt only; caller supplies independently evidenced A'
        result['program', pid] = {'definition': copy.deepcopy(p), 'recipe': recipe,
                                  'provenance': {'source_object': copy.deepcopy(obj),
                                                 'interpretation': 'Closed A2 source recipe; no native or runtime qualification'}}
    return result
