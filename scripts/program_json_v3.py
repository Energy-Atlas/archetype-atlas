"""ADR 0016 ready exports. Frozen definitions and historical v2 stay immutable."""
import calendar
import copy
import math

from jsonschema import Draft202012Validator

from scripts.common import ROOT, load_json
from scripts.definition_contract import stable_id
from scripts.program_json import ProgramExporter as HistoricalExporter, represented_demands
from scripts.schedule_json import normalize_schedule, has_full_coverage, date_mask

POLICY = 'atlas-program-defaults-2.0.0'
NATIVE_FRACTIONS = {'lighting': ('radiant', 'visible', 'return_air'),
                    'electric_equipment': ('radiant', 'latent', 'lost'),
                    'gas_equipment': ('radiant', 'latent', 'lost')}


def constant(value, unit, reason):
    return {'id': stable_id('resolved-schedule', {'policy': POLICY, 'value': value, 'unit': unit, 'reason': reason}),
            'name': reason, 'type': 'ruleset', 'unit': unit, 'timestep_minutes': 60,
            'rule_selection': 'last_specific_match_else_last_default',
            'rules': [{'start_date': '01-01', 'end_date': '12-31', 'day_types': ['Default'], 'values': [value]}]}


def complete_approved_schedule(original):
    if has_full_coverage(original):
        return original, None
    result = copy.deepcopy(original)
    name = original['name']
    if name in {'OfficeMedium BLDG_EQUIP_SCH_2004', 'OfficeMedium BLDG_EQUIP_SCH_2013',
                'OfficeMedium BLDG_LIGHT_SCH_2004', 'OfficeMedium BLDG_LIGHT_SCH_2013'}:
        if any('Hol' in r['day_types'] for r in result['rules']):
            raise ValueError('Unexpected partially covered holiday rules: ' + name)
        sunday = [r for r in result['rules'] if r['day_types'] == ['Sun']]
        if len(sunday) != 1 or sunday[0]['start_date'] != '01-01' or sunday[0]['end_date'] != '12-31':
            raise ValueError('Unexpected Sunday rule: ' + name)
        result['rules'].append(dict(copy.deepcopy(sunday[0]), day_types=['Hol']))
        reason = 'accepted-holiday-sunday'
    elif name == 'DataCenter_EQUIP_SCH':
        for rule in result['rules']:
            if rule['start_date'] == '02-01' and rule['end_date'] == '02-28':
                rule['end_date'] = '02-29'
        reason = 'accepted-leap-day-february'
    else:
        raise ValueError('unresolved schedule coverage: ' + name)
    if not has_full_coverage(result):
        raise ValueError('unresolved schedule coverage after accepted completion: ' + name)
    result['id'] = stable_id('resolved-schedule', {'source': original['id'], 'policy': POLICY, 'rules': result['rules']})
    result['name'] += ' / ' + reason
    return result, reason


class ProgramExporter(HistoricalExporter):
    def __init__(self, bundle, recovery=None):
        super().__init__(bundle)
        self.historical = HistoricalExporter(bundle)
        self.validator = Draft202012Validator(load_json(ROOT / 'schemas/program-json-v3.schema.json'))
        path = ROOT / 'data/program-inputs/residential-v1.json'
        artifact = load_json(path) if path.exists() else {}
        self.recovery = recovery if recovery is not None else artifact.get('records', {})
        self.recovered_schedules = artifact.get('schedules', {})
        self.recovery_provenance = {k: v for k, v in artifact.items() if k not in {'records', 'schedules'}}
        triage = ROOT / 'data/program-inputs/er-triage-v1.json'
        self.triage = load_json(triage) if triage.exists() else {}
        commercial = load_json(ROOT / 'data/releases/v0.2.0/programs.json')
        self.inactive_controls = {r['id'] for r in commercial if r['heating_setpoint_schedule_id'] is None
                                  and r['cooling_setpoint_schedule_id'] is None}
        self._ready_cache = {}

    def export(self, program_id, mode='raw'):
        if mode not in {'raw', 'defaulted'}:
            raise ValueError('Unknown export mode')
        key = program_id, mode
        if key not in self._ready_cache:
            source = self.programs[program_id]
            out = self._raw(source) if mode == 'raw' else self._ready(source)
            errors = self.validate(out)
            if errors:
                raise ValueError(program_id + ': ' + '; '.join(errors[:8]))
            self._ready_cache[key] = out
        return copy.deepcopy(self._ready_cache[key])

    def _raw(self, source):
        out = self.historical.export(source['id'], 'raw')
        out['schema_version'] = '3.0.0'
        out.pop('assumptions')
        out['metadata'] = {'absent_demands': [], 'resolutions': [], 'excluded_scope': ['ventilation', 'infiltration'],
                           'source_operands': copy.deepcopy({'loads': source['loads'], 'parameters': source['parameters']})}
        out['source']['source_family'] = source.get('source_family')
        residential = source.get('scope') == 'whole_dwelling'
        out['source']['climate'] = ({'status': 'exact', 'value': source['climate']} if source.get('climate') else
            {'status': 'unknown'} if residential else {'status': 'shared', 'basis': 'Selected standards program recipe has no climate selector'})
        out['source']['vintage'] = ({'status': 'exact', 'value': source['vintage'], 'kind': 'stock_vintage'} if source.get('vintage') else
            {'status': 'exact', 'value': source['template'], 'kind': 'source_template'} if source.get('template') else {'status': 'unknown'})
        out['controls']['conditioning_state'] = 'unknown'
        for item in self._all_loads(out):
            if item['type'] in NATIVE_FRACTIONS:
                item['heat_fractions'] = {k: item['heat_fractions'][k] for k in NATIVE_FRACTIONS[item['type']]}
            if item['type'] == 'hot_water':
                item.pop('inlet_temperature_schedule_id', None)
                item['inlet_temperature'] = {'method': 'unresolved'}
            item['host'] = 'assigned_zone'
            if item['type'] in {'electric_equipment', 'gas_equipment'}:
                item['fuel'] = 'electricity' if item['type'] == 'electric_equipment' else 'natural gas'
        return out

    @staticmethod
    def _all_loads(out):
        return out['loads'] + [l for s in out['shared_services'] for l in s['loads']]

    def _ready(self, source):
        out = self._raw(source)
        out.update(export_mode='defaulted', default_policy_id=POLICY, id=source['id'] + ':defaulted:' + POLICY)
        composition = self.compositions.get(source.get('composition_id'))
        members = []
        if composition:
            out['loads'], out['shared_services'] = [], []
            out['metadata']['composition'] = copy.deepcopy(composition)
            services = {}
            for member in composition['members']:
                leaf = self.export(member['program_id'], 'defaulted')
                weight = member['weight']
                members.append((weight, leaf))
                out['schedules'].update(leaf['schedules'])
                for load in leaf['loads']:
                    if load['basis'] != 'floor_area':
                        raise ValueError('unresolved mixture scaling basis')
                    item = copy.deepcopy(load)
                    item['value'] *= weight
                    if item['type'] == 'occupancy':
                        item['activity_schedule_id'] = item.get('activity_schedule_id', leaf['controls'].get('activity_schedule_id'))
                    item['demand_id'] = stable_id('mixed-demand', {'parent': source['id'], 'member': member['program_id'], 'demand': item['demand_id']})
                    if item['value'] > 0:
                        out['loads'].append(item)
                for service in leaf['shared_services']:
                    services[service['id']] = service
                out['metadata']['resolutions'].append({'member': member['program_id'], 'weight': weight,
                    'resolutions': leaf['metadata']['resolutions'], 'absent_demands': leaf['metadata']['absent_demands'],
                    'aggregation': leaf['metadata']['aggregation']})
            local_ids = {d for l in source['loads'] for d in represented_demands(l)}
            out['shared_services'] = [s for k, s in sorted(services.items()) if k not in local_ids]
        elif source.get('scope') == 'whole_dwelling':
            recovered = self.recovery.get(source['source_id'])
            if recovered is None:
                raise ValueError('unresolved residential source recovery: ' + source['source_id'])
            if recovered.get('unresolved'):
                raise ValueError('unresolved residential inputs: ' + repr(recovered['unresolved']))
            # Keep occupancy and thermostat realization; replace the schedule-only placeholders.
            out['loads'] = [l for l in out['loads'] if l['type'] == 'occupancy']
            for original in recovered['loads']:
                item = copy.deepcopy(original)
                evidence = item.pop('evidence', {})
                if item['type'] == 'equipment':
                    item['type'] = 'electric_equipment' if item['fuel'] == 'electricity' else 'gas_equipment'
                elif item['type'] == 'water':
                    item['type'] = 'hot_water'
                if item['basis'] == 'dwelling_unit' and item['unit'] in {'W', 'm3/s'}:
                    item['unit'] += '/dwelling'
                if item.get('host') == 'conditioned space':
                    item['host'] = 'assigned_zone'
                if item['type'] == 'lighting' and item.get('host') == 'outside':
                    item['type'] = 'exterior_lighting'
                    item.pop('heat_fractions', None)
                out['metadata']['resolutions'].append({'end_use': item['end_use'], 'evidence': evidence})
                schedule = item.pop('schedule', None)
                if schedule:
                    out['schedules'][schedule['id']] = schedule
                    item['schedule_id'] = schedule['id']
                elif item.get('schedule_id') in self.recovered_schedules:
                    out['schedules'][item['schedule_id']] = copy.deepcopy(self.recovered_schedules[item['schedule_id']])
                elif item.get('schedule_id') in self.schedules:
                    out['schedules'][item['schedule_id']] = normalize_schedule(self.schedules[item['schedule_id']])
                item.setdefault('demand_id', stable_id('recovered-demand', {'program': source['id'], 'end_use': item['end_use'], 'fuel': item.get('fuel'), 'host': item.get('host')}))
                item.setdefault('host', 'assigned_zone')
                target = item.pop('target_temperature_degC', None)
                if item['type'] == 'hot_water' and target is not None:
                    s = constant(target, 'degC', 'recovered-water-target')
                    out['schedules'][s['id']] = s
                    item['target_temperature_schedule_id'] = s['id']
                out['loads'].append(item)
            out['metadata']['residential_recovery'] = {k: copy.deepcopy(v) for k, v in recovered.items() if k != 'loads'}
            out['metadata']['residential_source'] = copy.deepcopy(self.recovery_provenance)
            out['metadata']['excluded_scope'] += ['electric_vehicle', 'general_water_use_heat_gains', 'dhw_distribution_and_system_effects']
            out['metadata']['scope_decision'] = 'User accepted water-use thermal gains and distribution effects outside program scope on 2026-10-11; not assumed zero.'

        name = source['name'].lower()
        # 'shaft' added by user decision (ADR 0039, 2026-10-26) for the construction-only service shafts.
        support = any(k in name for k in ('attic', 'plenum', 'elevator', 'elec/mech', 'electrical', 'mechanical', 'shaft'))
        for group in [out['loads']] + [s['loads'] for s in out['shared_services']]:
            active = []
            for item in group:
                if item['value'] is None:
                    if (source.get('source_id') == self.triage.get('source_program_id') and
                            item['end_use'] == 'electric_equipment' and self.triage.get('status') == 'recovered'):
                        item['value'] = self.triage['value_W_m2']
                        out['metadata']['resolutions'].append(copy.deepcopy(self.triage))
                if item['value'] is None:
                    allowed = item['end_use'] == 'additional_lighting' or item['type'] == 'gas_equipment' or support
                    allowed |= item['type'] == 'occupancy' and 'data' in name and 'center' in name
                    if not allowed:
                        raise ValueError('unresolved ' + item['end_use'] + ' magnitude: ' + source['id'])
                    item['value'] = 0
                    out['metadata']['resolutions'].append({'demand_id': item['demand_id'], 'field': 'value', 'original_value': None,
                        'replacement_value': 0, 'rule': 'accepted-absence', 'decision': 'ADR 0016'})
                if item['value'] == 0:
                    out['metadata']['absent_demands'].append(item)
                    continue
                if item.get('schedule_id') is None:
                    raise ValueError('unresolved active ' + item['end_use'] + ' schedule: ' + source['id'])
                if item['type'] in NATIVE_FRACTIONS:
                    for k in NATIVE_FRACTIONS[item['type']]:
                        item.setdefault('heat_fractions', {})
                        if item['heat_fractions'].get(k) is None:
                            item['heat_fractions'][k] = 0
                            out['metadata']['resolutions'].append({'demand_id': item['demand_id'], 'field': 'heat_fractions.' + k,
                                'original_value': None, 'replacement_value': 0, 'rule': 'EnergyPlus-25.1-native-default'})
                if item['type'] == 'hot_water':
                    item['inlet_temperature'] = {'method': 'CorrelationFromWeatherFile', 'engine': 'EnergyPlus', 'engine_version': '25.1.0'}
                    if item.get('target_temperature_schedule_id') is None:
                        s = constant(60, 'degC', 'accepted-water-target-fallback')
                        out['schedules'][s['id']] = s
                        item['target_temperature_schedule_id'] = s['id']
                        out['metadata']['resolutions'].append({'demand_id': item['demand_id'], 'rule': 'accepted-water-target-60C'})
                active.append(item)
            group[:] = active
        out['shared_services'] = [s for s in out['shared_services'] if s['loads']]
        self._controls(out, source, members)
        self._complete_schedules(out)
        # Aggregation is imported at runtime to keep the resolver usable independently.
        from scripts.program_json_aggregation import aggregate_loads
        out['loads'], out['schedules'], aggregation = aggregate_loads(out['loads'], out['schedules'])
        component_ids = {c['load']['schedule_id'] for g in aggregation['groups'] for c in g['components']}
        aggregation['component_schedules'] = {sid: copy.deepcopy(out['schedules'][sid]) for sid in sorted(component_ids)}
        out['metadata']['aggregation'] = aggregation
        # Record the accepted calendar decision where it changes heat partition.
        calendar_sensitive = any(
            len({tuple(sorted(c['load'].get('heat_fractions', {}).items())) for c in g['components']}) > 1
            and any(out['schedules'][c['load']['schedule_id']]['type'] == 'ruleset' for c in g['components'])
            for g in aggregation['groups'])
        out['metadata']['accepted_decisions'] = ['ruleset_heat_weighting_calendar_2007_no_holidays'] if calendar_sensitive else []
        out['metadata']['pending_decisions'] = []
        out['metadata']['scope_status'] = 'complete_within_agreed_program_scope'
        self._prune(out)
        bases = {l['basis'] for l in self._all_loads(out)}
        out['required_bindings'] = [v for k, v in [('floor_area', 'floor_area_m2'), ('dwelling_unit', 'dwelling_unit_count'), ('person', 'person_count')] if k in bases]
        if out['shared_services']:
            out['required_bindings'].append('shared_service_host')
        if any(l['type'] == 'hot_water' for l in self._all_loads(out)):
            out['required_bindings'].append('weather_file')
        if any(l.get('host', 'assigned_zone') != 'assigned_zone' for l in out['loads']):
            out['required_bindings'].append('load_host')
        out['required_bindings'] += ['calendar_year', 'holiday_calendar']
        return out

    def _controls(self, out, source, members):
        controls = out['controls']
        conditioning = source['parameters'].get('conditioning', {}).get('value') or {}
        for mode in ('heating', 'cooling'):
            key = mode + '_setpoint_schedule_id'
            enabled = conditioning.get(mode + '_enabled')
            if members:
                applicable = [(w, leaf['schedules'][leaf['controls'][key]]) for w, leaf in members if w > 0 and leaf['controls'][mode + '_enabled']]
                enabled = bool(applicable)
                if enabled:
                    from scripts.program_composition import mix_schedule
                    total = math.fsum(w for w, _ in applicable)
                    canonical = [{'units': s['unit'], 'schedule_type': 'temperature',
                        'rules': [{'start_date': '2000-' + r['start_date'], 'end_date': '2000-' + r['end_date'],
                                  'day_types': '|'.join(r['day_types']), 'values': r['values']} for r in s['rules']]} for _, s in applicable]
                    mixed = normalize_schedule(mix_schedule(canonical, [w / total for w, _ in applicable]))
                    out['schedules'][mixed['id']] = mixed
                    controls[key] = mixed['id']
                    out['metadata']['resolutions'].append({'field': key, 'rule': 'area-weighted-active-member-controls', 'active_area_fraction': total})
            if enabled is None:
                if controls.get(key) is not None:
                    enabled = True
                elif source.get('source_id') in self.inactive_controls:
                    enabled = False
                    out['metadata']['resolutions'].append({'field': mode + '_enabled', 'value': False, 'rule': 'accepted-support-space-inactive-conditioning'})
                else:
                    raise ValueError('unresolved ' + mode + ' conditioning: ' + source['id'])
            controls[mode + '_enabled'] = enabled
            if not enabled:
                controls.pop(key, None)
            elif controls.get(key) is None:
                raise ValueError('unresolved active ' + mode + ' setpoint: ' + source['id'])
        h, c = controls['heating_enabled'], controls['cooling_enabled']
        controls['conditioning_state'] = 'heating_and_cooling' if h and c else 'heating_only' if h else 'cooling_only' if c else 'unconditioned'
        if any(l['type'] == 'occupancy' for l in out['loads']):
            recovered = self.recovery.get(source.get('source_id'), {}).get('controls', {})
            if members:
                activities = {l['activity_schedule_id'] for l in out['loads'] if l['type'] == 'occupancy'}
                if None in activities:
                    raise ValueError('unresolved active member activity')
                if len(activities) == 1:
                    controls['activity_schedule_id'] = next(iter(activities))
                else:
                    controls.pop('activity_schedule_id', None)
                out['metadata']['resolutions'].append({'field': 'activity_schedule_id', 'rule': 'preserved-active-member-activity'})
            elif controls.get('activity_schedule_id') is None:
                value = recovered.get('activity_W_person', 120)
                s = constant(value, 'W/person', 'source-residential-activity' if recovered else 'accepted-activity-fallback')
                out['schedules'][s['id']] = s
                controls['activity_schedule_id'] = s['id']
                out['metadata']['resolutions'].append({'field': 'activity_schedule_id', 'value_W_person': value, 'rule': s['name']})
            controls['people_radiant_fraction'] = recovered.get('people_radiant_fraction', .3)
            controls['people_sensible_fraction'] = recovered.get('people_sensible_fraction', 'autocalculate')
        else:
            for k in ('activity_schedule_id', 'people_radiant_fraction', 'people_sensible_fraction'):
                controls.pop(k, None)

    def _complete_schedules(self, out):
        for owner in self._all_loads(out) + [out['controls']]:
            for key, sid in list(owner.items()):
                if not key.endswith('_schedule_id') and key != 'schedule_id':
                    continue
                if sid is None:
                    continue
                result, reason = complete_approved_schedule(out['schedules'][sid])
                if reason:
                    owner[key] = result['id']
                    out['schedules'][result['id']] = result
                    out['metadata']['resolutions'].append({'field': key, 'source_schedule_id': sid, 'resolved_schedule_id': result['id'], 'rule': reason})

    def _prune(self, out):
        ids = {v for owner in self._all_loads(out) + [out['controls']] for k, v in owner.items()
               if k == 'schedule_id' or k.endswith('_schedule_id')}
        out['schedules'] = {k: v for k, v in out['schedules'].items() if k in ids}

    def validate(self, out):
        errors = [e.message for e in self.validator.iter_errors(out)]
        if errors:
            return errors
        ready = out['export_mode'] == 'defaulted'
        schedules = out['schedules']
        def check(sid, unit):
            if sid is None:
                if ready: errors.append('Unresolved active schedule')
            elif sid not in schedules: errors.append('Orphan schedule ' + sid)
            elif schedules[sid]['unit'] != unit: errors.append('Wrong schedule unit ' + sid)
        years = set()
        for sid, s in schedules.items():
            if sid != s['id']: errors.append('Schedule identity mismatch')
            if s['type'] == 'annual':
                years.add(s['year'])
                if len(s['values']) != (8784 if calendar.isleap(s['year']) else 8760): errors.append('Annual calendar mismatch')
            else:
                for r in s['rules']:
                    try: date_mask(r['start_date'], r['end_date'])
                    except ValueError: errors.append('Invalid schedule date')
            if ready and not has_full_coverage(s): errors.append('Incomplete schedule coverage')
            values = s.get('values', []) if s['type'] == 'annual' else [v for r in s['rules'] for v in r['values']]
            if s['unit'] == '1' and any(v < 0 or v > 1 + 1e-10 for v in values): errors.append('Invalid load fraction')
        if len(years) > 1: errors.append('Incompatible annual calendars')
        demands = set()
        for l in self._all_loads(out):
            if l['demand_id'] in demands: errors.append('Duplicated physical demand')
            demands.add(l['demand_id'])
            if ready and (l['value'] is None or l['value'] <= 0): errors.append('Unresolved or inactive load')
            if l['value'] is not None and not math.isfinite(l['value']): errors.append('Nonfinite load')
            check(l['schedule_id'], '1')
            f = l.get('heat_fractions', {})
            if ready and any(v is None for v in f.values()): errors.append('Unresolved heat fraction')
            if sum(v for v in f.values() if v is not None) > 1 + 1e-9: errors.append('Heat fractions exceed one')
            if l['type'] == 'hot_water':
                check(l['target_temperature_schedule_id'], 'degC')
                if ready and l['inlet_temperature']['method'] != 'CorrelationFromWeatherFile': errors.append('Unresolved mains temperature')
            if ready and l['type'] in {'electric_equipment','gas_equipment'} and not l.get('fuel'): errors.append('Unresolved fuel')
        c = out['controls']
        if ready:
            h, cool = c['heating_enabled'], c['cooling_enabled']
            expected = 'heating_and_cooling' if h and cool else 'heating_only' if h else 'cooling_only' if cool else 'unconditioned'
            if c['conditioning_state'] != expected: errors.append('Conditioning state contradicts service flags')
        for mode in ('heating', 'cooling'):
            if c[mode + '_enabled']:
                check(c.get(mode + '_setpoint_schedule_id'), 'degC')
            elif ready and mode + '_setpoint_schedule_id' in c:
                errors.append('Disabled service has setpoint schedule')
        for l in out['loads']:
            if l['type'] != 'occupancy': continue
            check(l.get('activity_schedule_id', c.get('activity_schedule_id')), 'W/person')
            if ready and any(c.get(k) is None for k in ('people_radiant_fraction', 'people_sensible_fraction')): errors.append('Unresolved People fractions')
        if ready and not errors and c['heating_enabled'] and c['cooling_enabled']:
            errors += self._ordered(schedules[c['heating_setpoint_schedule_id']], schedules[c['cooling_setpoint_schedule_id']], 'Heating exceeds cooling')
        return errors
