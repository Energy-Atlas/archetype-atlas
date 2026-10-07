"""Self-contained connector exports; canonical definitions are never mutated."""
import calendar
import copy
import datetime as dt
import math
from jsonschema import Draft202012Validator

from scripts.common import ROOT, load_json
from scripts.definition_contract import stable_id
from scripts.schedule_json import (POLICY, DAYS, normalize_schedule, constant_schedule,
                                   complete_schedule, date_mask, extrema)
from scripts.semantics import profile

FRACTIONS = ['radiant', 'latent', 'lost', 'visible', 'return_air']
POWER = {'lighting', 'electric_equipment', 'gas_equipment'}


def load_type(quantity):
    if quantity == 'occupancy': return 'occupancy'
    if quantity in {'lighting', 'additional_lighting', 'lighting_interior'}: return 'lighting'
    if quantity == 'gas_equipment': return 'gas_equipment'
    if quantity.startswith('hot_water'): return 'hot_water'
    return 'electric_equipment'


class ProgramExporter:
    def __init__(self, bundle):
        self.bundle = bundle
        self.programs = {r['id']: r for r in bundle['programs']}
        self.schedules = {r['id']: r for r in bundle['schedules']}
        self.services = {r['id']: r for r in bundle['services']}
        self.compositions = {r['id']: r for r in bundle['compositions']}
        self.evidence = {r['id']: r for r in bundle['provenance']}
        self.validator = Draft202012Validator(load_json(ROOT / 'schemas/program-json-v2.schema.json'))
        self._cache, self._normalized, self._completed, self._temperature_cache = {}, {}, {}, {}

    def export(self, program_id, mode='raw'):
        if mode not in {'raw', 'defaulted'}: raise ValueError('Unknown export mode')
        key = program_id, mode
        if key not in self._cache:
            out = self._build(self.programs[program_id], mode)
            errors = self.validate(out)
            if errors: raise ValueError('; '.join(errors[:5]))
            self._cache[key] = out
        return copy.deepcopy(self._cache[key])

    def _build(self, source, mode):
        ready = mode == 'defaulted'
        out = {'schema_version': '2.0.0', 'kind': 'program', 'export_mode': mode,
               'id': source['id'] + (':defaulted:' + POLICY if ready else ''), 'name': source['name'],
               'scope': source.get('scope', 'program'),
               'source': {'program_id': source['id'], 'definition_release': 'v0.1.1',
                          'building_type': source.get('building_type'), 'template': source.get('template'),
                          'evidence_view': source['evidence_view'], 'evidence': []},
               'loads': [], 'controls': {}, 'schedules': {}, 'shared_services': [],
               'default_policy_id': POLICY if ready else None, 'assumptions': [], 'required_bindings': []}
        for eid in source.get('evidence_ids', []):
            e = self.evidence.get(eid)
            if e:
                out['source']['evidence'].append({'source_file_id': e.get('source_file_id'), 'locator': e.get('locator', ''),
                    'original_value': copy.deepcopy(e.get('original_value')), 'original_unit': e.get('original_unit'),
                    'transformation': e.get('transformation', ''), 'extraction_date': e['extraction_date'],
                    'interpretation': e.get('interpretation', '')})

        def assumption(path, before, after, rule, reason=None):
            if ready:
                out['assumptions'].append({'path': path, 'original_value': copy.deepcopy(before),
                    'replacement_value': copy.deepcopy(after), 'rule_id': rule,
                    'reason': reason or 'Explicit experimental policy ' + POLICY})

        def schedule(identity, unit, fallback, path, rule):
            if identity is None:
                if not ready: return None
                result = constant_schedule(fallback, unit, rule)
                assumption(path, None, result['id'], rule)
            else:
                if identity not in self.schedules: raise ValueError('Missing schedule ' + identity)
                if identity not in self._normalized: self._normalized[identity] = normalize_schedule(self.schedules[identity])
                result = self._normalized[identity]
                if result['unit'] != unit: raise ValueError('Unexpected schedule unit for ' + identity)
                if ready:
                    key = identity, fallback
                    if key not in self._completed: self._completed[key] = complete_schedule(result, fallback)
                    completed, changed = self._completed[key]
                    if changed:
                        assumption(path, identity, completed['id'], 'unknown-schedule-coverage')
                        if completed['id'] not in out['schedules']:
                            assumption('/schedules/' + completed['id'] + '/rules/0', None, completed['rules'][0], 'unknown-schedule-coverage')
                    result = completed
            out['schedules'][result['id']] = result
            return result['id']

        def operand(value, fallback, path, rule):
            if value is None and ready:
                assumption(path, None, fallback, rule)
                return fallback
            return value

        def load(original, path):
            kind = load_type(original['quantity'])
            value = operand(original['value'], 0, path + '/value', 'unknown-load')
            result = {'demand_id': original['demand_id'], 'type': kind, 'end_use': original['quantity'],
                      'value': value, 'unit': original['unit'], 'basis': original['basis'],
                      'schedule_id': schedule(original.get('schedule_id'), '1', 0 if not value else 1,
                                              path + '/schedule_id', 'unknown-load-schedule')}
            if kind in POWER:
                fractions = original.get('thermal_effects', {})
                result['heat_fractions'] = {}
                for name in FRACTIONS:
                    v = fractions.get('to_return_air' if name == 'return_air' else name, {})
                    v = v.get('value') if isinstance(v, dict) else None
                    result['heat_fractions'][name] = operand(v, 0, path + '/heat_fractions/' + name, 'unknown-heat-fraction')
            if kind == 'hot_water':
                original_target = original.get('target_temperature_degC')
                target = 60 if original_target is None and ready else original_target
                target_schedule = constant_schedule(target, 'degC', 'unknown-water-target') if target is not None else None
                if target_schedule:
                    if original_target is not None:
                        target_schedule['id'] = stable_id('source-water-target', {'demand': original['demand_id'], 'degC': target})
                        target_schedule['name'] = 'Source fixture target temperature'
                    else:
                        assumption(path + '/target_temperature_schedule_id', None, target_schedule['id'], 'unknown-water-target')
                    out['schedules'][target_schedule['id']] = target_schedule
                result['target_temperature_schedule_id'] = target_schedule['id'] if target_schedule else None
                result['inlet_temperature_schedule_id'] = schedule(None, 'degC', min(10, target) if target is not None else 10,
                    path + '/inlet_temperature_schedule_id', 'unknown-water-inlet')
            return result

        composition = self.compositions.get(source.get('composition_id')) if ready else None
        local_service_ids = set()
        service_ids = set(source.get('service_ids', []))
        member_exports = []
        if composition:
            for member in composition['members']:
                leaf = self.export(member['program_id'], 'defaulted')
                member_exports.append((member['weight'], leaf))
                out['schedules'].update(leaf['schedules'])
                for item in leaf['loads']:
                    result = copy.deepcopy(item)
                    if result['basis'] != 'floor_area': raise ValueError('Mixture has incompatible scaling basis')
                    local_service_ids.add(result['demand_id'])
                    result['demand_id'] = stable_id('mixed-import-demand', {'program': source['id'], 'leaf': member['program_id'], 'demand': result['demand_id']})
                    result['value'] *= member['weight']
                    out['loads'].append(result)
                service_ids.update(s['id'] for s in leaf['shared_services'])
                assumption('/loads', None, {'program_id': member['program_id'], 'weight': member['weight'],
                    'leaf_assumptions': leaf['assumptions']}, 'unknown-load',
                    'Defaults applied to source leaf before weighted trajectory; known positive contributions retained')
        else:
            for original in source.get('loads', []):
                local_service_ids.add(original['demand_id'])
                out['loads'].append(load(original, '/loads/' + str(len(out['loads']))))

        conditioning = source.get('parameters', {}).get('conditioning', {}).get('value') or {}
        for key in ('heating_enabled', 'cooling_enabled'):
            out['controls'][key] = operand(conditioning.get(key), True, '/controls/' + key, 'unknown-conditioning')
        for name, fallback, unit, rule in [('heating_setpoint_schedule_id', 20, 'degC', 'unknown-heating-setpoint'),
                                            ('cooling_setpoint_schedule_id', 26, 'degC', 'unknown-cooling-setpoint'),
                                            ('activity_schedule_id', 120, 'W/person', 'unknown-activity')]:
            original = source.get('parameters', {}).get(name, {}).get('value')
            if ready and original is None and member_exports:
                from scripts.program_composition import mix_schedule
                normalized = [leaf['schedules'][leaf['controls'][name]] for _, leaf in member_exports]
                canonical_schedules = [{'units': s['unit'], 'schedule_type': 'fraction' if s['unit'] == '1' else 'temperature' if s['unit'] == 'degC' else 'activity',
                    'rules': [{'start_date': '2000-' + r['start_date'], 'end_date': '2000-' + r['end_date'],
                               'day_types': '|'.join(r['day_types']), 'values': r['values']} for r in s['rules']]} for s in normalized]
                mixed = mix_schedule(canonical_schedules, [w for w, _ in member_exports])
                if mixed is None: raise ValueError('Unable to compose control schedules')
                result = normalize_schedule(mixed)
                out['schedules'][result['id']] = result
                out['controls'][name] = result['id']
                assumption('/controls/' + name, None, result['id'], rule, 'Pointwise composition after leaf defaults')
                continue
            if ready and original is None and name in {'heating_setpoint_schedule_id', 'cooling_setpoint_schedule_id'}:
                other = 'cooling_setpoint_schedule_id' if name.startswith('heating') else 'heating_setpoint_schedule_id'
                other_id = source.get('parameters', {}).get(other, {}).get('value')
                if other_id in self.schedules:
                    bounds = extrema(normalize_schedule(self.schedules[other_id]))
                    fallback = min(fallback, bounds[0] - 2) if name.startswith('heating') else max(fallback, bounds[1] + 2)
            out['controls'][name] = schedule(original, unit, fallback, '/controls/' + name, rule)
        out['controls']['people_radiant_fraction'] = operand(None, .3, '/controls/people_radiant_fraction', 'unknown-people-radiant')
        out['controls']['people_sensible_fraction'] = operand(None, 'autocalculate', '/controls/people_sensible_fraction', 'unknown-people-sensible')

        for sid in sorted(service_ids - local_service_ids):
            if sid not in self.services: raise ValueError('Unknown service ' + sid)
            original = self.services[sid]
            path = '/shared_services/' + str(len(out['shared_services'])) + '/loads/0'
            out['shared_services'].append({'id': sid, 'ownership': 'instantiate_once',
                'host_assignment': 'consumer_selected_zone', 'loads': [load(original['load'], path)]})
        bases = {l['basis'] for l in out['loads'] + [l for s in out['shared_services'] for l in s['loads']]}
        out['required_bindings'] = [v for k, v in [('floor_area', 'floor_area_m2'), ('dwelling_unit', 'dwelling_unit_count'), ('person', 'person_count')] if k in bases]
        if out['shared_services']: out['required_bindings'].append('shared_service_host')
        out['required_bindings'] += ['calendar_year', 'holiday_calendar']
        # Do not copy unused member schedules into a potentially large mixture payload.
        used = {l['schedule_id'] for l in out['loads']}
        used |= {out['controls'][k] for k in ('heating_setpoint_schedule_id', 'cooling_setpoint_schedule_id', 'activity_schedule_id')}
        for item in out['loads'] + [l for s in out['shared_services'] for l in s['loads']]:
            used |= {item.get(k) for k in ('schedule_id', 'target_temperature_schedule_id', 'inlet_temperature_schedule_id')}
        out['schedules'] = {k: v for k, v in out['schedules'].items() if k in used}
        return out

    def validate(self, out):
        errors = [e.message for e in self.validator.iter_errors(out)]
        if errors: return errors
        schedules = out['schedules']
        years = set()
        for sid, s in schedules.items():
            if sid != s['id']: errors.append('Schedule key differs from identity')
            if s['type'] == 'annual':
                years.add(s['year'])
                if len(s['values']) != (8784 if calendar.isleap(s['year']) else 8760): errors.append('Annual calendar length mismatch')
            else:
                for r in s['rules']:
                    try: date_mask(r['start_date'], r['end_date'])
                    except ValueError: errors.append('Invalid schedule date')
        if len(years) > 1: errors.append('Incompatible recorded calendar years')
        def check(identity, unit):
            if identity is None: return
            if identity not in schedules: errors.append('Orphan schedule reference ' + identity)
            elif schedules[identity]['unit'] != unit: errors.append('Incorrect schedule unit ' + identity)
        demands = set()
        for l in out['loads'] + [l for s in out['shared_services'] for l in s['loads']]:
            if l['demand_id'] in demands: errors.append('Duplicated physical demand')
            demands.add(l['demand_id'])
            check(l['schedule_id'], '1')
            for k in ('target_temperature_schedule_id', 'inlet_temperature_schedule_id'): check(l.get(k), 'degC')
            if sum(v for v in l.get('heat_fractions', {}).values() if v is not None) > 1 + 1e-10: errors.append('Heat fractions exceed one')
        for k, unit in [('heating_setpoint_schedule_id', 'degC'), ('cooling_setpoint_schedule_id', 'degC'), ('activity_schedule_id', 'W/person')]:
            check(out['controls'][k], unit)
        if not errors and out['export_mode'] == 'defaulted':
            heating = out['controls']['heating_setpoint_schedule_id']
            cooling = out['controls']['cooling_setpoint_schedule_id']
            if out['controls']['heating_enabled'] and out['controls']['cooling_enabled']:
                errors += self._ordered(schedules[heating], schedules[cooling], 'Heating exceeds cooling')
            for l in out['loads'] + [l for s in out['shared_services'] for l in s['loads']]:
                if l['type'] == 'hot_water':
                    errors += self._ordered(schedules[l['inlet_temperature_schedule_id']], schedules[l['target_temperature_schedule_id']], 'Water inlet exceeds target')
        return errors

    def _ordered(self, lower, upper, message):
        key = lower['id'], upper['id']
        if key in self._temperature_cache: return self._temperature_cache[key]
        if extrema(lower)[1] <= extrema(upper)[0]:
            result = []
        else:
            annual = next((s for s in (lower, upper) if s['type'] == 'annual'), None)
            dates = {dt.date(2000, 1, 1)}
            for s in (lower, upper):
                if s['type'] == 'ruleset':
                    for r in s['rules']:
                        dates.add(dt.date.fromisoformat('2000-' + r['start_date']))
                        dates.add(dt.date.fromisoformat('2000-' + r['end_date']))
                        dates.add(dt.date.fromisoformat('2000-' + r['end_date']) + dt.timedelta(days=1))
            def values(s, day, date):
                if s['type'] == 'annual':
                    offset = (date - dt.date(s['year'], 1, 1)).days * 24
                    return s['values'][offset:offset + 24]
                rules = [{'start_date': '2000-' + r['start_date'], 'end_date': '2000-' + r['end_date'], 'day_types': '|'.join(r['day_types']), 'values': r['values']} for r in s['rules']]
                return profile(rules, day, date.strftime('%m-%d'))
            if annual:
                year = annual['year'];dates = {dt.date(year, 1, 1) + dt.timedelta(days=i) for i in range(366 if calendar.isleap(year) else 365)}
            result = []
            for date in dates:
                for day in ([DAYS[date.weekday()]] if annual else DAYS):
                    if any(a > b + 1e-9 for a, b in zip(values(lower, day, date), values(upper, day, date))):
                        result = [message];break
                if result: break
        self._temperature_cache[key] = result
        return result
