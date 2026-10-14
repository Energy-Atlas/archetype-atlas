"""Strict request and emitted bundle validation for hourly local-standard schedules."""
import calendar
import copy
from datetime import date
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator

from .canonical import schedule_id
from .errors import GeneratorError

_ROOT = Path(__file__).resolve().parents[1]


def _schema_errors(value, name):
    schema = json.loads((_ROOT/f'schemas/schedule-generator-{name}-v1.schema.json').read_text(encoding='utf-8'))
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: list(map(str, e.path)))
    if errors:
        error = errors[0]
        path = '/' + '/'.join(map(str, error.absolute_path))
        raise GeneratorError('invalid_contract', path, error.message)


def _finite(value, path=''):
    if isinstance(value, float) and not math.isfinite(value):
        raise GeneratorError('invalid_json', path or '/', 'Nonfinite number')
    if isinstance(value, dict):
        for key, child in value.items():
            _finite(child, f'{path}/{key}')
    elif isinstance(value, list):
        for i, child in enumerate(value):
            _finite(child, f'{path}/{i}')


def validate_request(params: dict, seed: int) -> None:
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**64:
        raise GeneratorError('invalid_seed', '/seed', 'Explicit unsigned 64-bit integer required')
    _finite(params)
    _schema_errors(params, 'request')
    year = params['calendar']['year']
    if calendar.isleap(year):
        raise GeneratorError('leap_year', '/calendar/year', 'Hourly generator requires a non-leap Gregorian year')
    for i, holiday in enumerate(params['calendar'].get('holidays', [])):
        try:
            parsed = date.fromisoformat(holiday)
        except ValueError as error:
            raise GeneratorError('invalid_calendar', f'/calendar/holidays/{i}', 'Invalid Gregorian date') from error
        if parsed.year != year:
            raise GeneratorError('invalid_calendar', f'/calendar/holidays/{i}', 'Holiday outside calendar year')
    keys = [item['key'] for item in params['instances']]
    if len(keys) != len(set(keys)):
        raise GeneratorError('duplicate_instance', '/instances', 'Instance keys must be unique')
    mixture = params.get('mixture')
    if mixture:
        members = mixture['members']
        if not members or any(m['instance_key'] not in keys for m in members):
            raise GeneratorError('invalid_mixture', '/mixture/members', 'Members must reference instances')
        if len({m['instance_key'] for m in members}) != len(members):
            raise GeneratorError('invalid_mixture', '/mixture/members', 'Duplicate member allocation')
        if not math.isclose(math.fsum(m['weight'] for m in members), 1, rel_tol=0, abs_tol=1e-12):
            raise GeneratorError('invalid_mixture', '/mixture/members', 'Normalized area weights must sum to one')


def validate_bundle(bundle: dict) -> None:
    _finite(bundle)
    _schema_errors(bundle, 'bundle')
    schedules = bundle['schedules']
    cal = bundle['metadata']['calendar']
    if calendar.isleap(cal['year']):
        raise GeneratorError('leap_year', '/metadata/calendar/year', 'Leap year cannot have 8760 local hours')
    for sid, schedule in schedules.items():
        if sid != schedule['id']:
            raise GeneratorError('invalid_reference', f'/schedules/{sid}/id', 'Schedule key and id differ')
        if schedule['year'] != cal['year'] or schedule['clock'] != cal['clock']:
            raise GeneratorError('invalid_calendar', f'/schedules/{sid}', 'Schedule calendar differs from bundle')
        if schedule['unit'] == 'fraction' and any(v < 0 or v > 1 for v in schedule['values']):
            raise GeneratorError('invalid_schedule', f'/schedules/{sid}/values', 'Fractions must be in [0, 1]')
    for i, binding in enumerate(bundle['bindings']):
        sid = binding['schedule_id']
        path = f'/bindings/{i}'
        if sid not in schedules or sid != schedule_id(binding['instance_key'], binding['slot']):
            raise GeneratorError('invalid_reference', f'{path}/schedule_id', 'Missing or unscoped schedule')
        if binding['kind'] == 'load':
            if schedules[sid]['unit'] != 'fraction':
                raise GeneratorError('invalid_schedule', path, 'Load schedules must be fractions')
            target = binding['reference_target']
            magnitude = binding['effective_magnitude']
            receipt = binding['scaling_receipt']
            if (target['fuel'] != binding['fuel'] or target['host'] != binding['host'] or
                    target['basis'] != magnitude['basis'] or target['magnitude_unit'] != magnitude['unit'] or
                    target['method'] != binding['budget_method'] or receipt['unit'] != target['unit']):
                raise GeneratorError('invalid_binding', path, 'Load target semantics differ from binding')
            multiplier = 3600 if magnitude['unit'].startswith('m3/s') else 1
            emitted_integral = math.fsum(schedules[sid]['values'])
            if not math.isclose(receipt['generated_integral'], emitted_integral,
                                rel_tol=1e-12, abs_tol=1e-12):
                raise GeneratorError('budget_mismatch', f'{path}/scaling_receipt/generated_integral',
                                     'Receipt integral differs from emitted schedule')
            achieved = emitted_integral * magnitude['value'] * multiplier
            abs_tol = 1e-12 if target['unit'].startswith('m3') else 1e-8
            if not math.isclose(achieved, target['total'], rel_tol=1e-8, abs_tol=abs_tol):
                raise GeneratorError('budget_mismatch', path, 'Emitted load does not conserve annual target')
            if not math.isclose(receipt['achieved_total'], achieved, rel_tol=1e-8, abs_tol=abs_tol):
                raise GeneratorError('budget_mismatch', f'{path}/scaling_receipt', 'Scaling receipt differs from emitted integral')
        elif schedules[sid]['unit'] == 'fraction' and binding['control_quantity'] == 'temperature':
            raise GeneratorError('invalid_binding', path, 'Temperature control cannot use fraction units')
    owned = set()
    referenced = {binding['schedule_id'] for binding in bundle['bindings']}
    for i, constituent in enumerate(bundle['constituents']):
        path = f'/constituents/{i}'
        for slot, sid in constituent['schedule_ids'].items():
            if slot not in constituent['slots'] or sid not in schedules or sid != schedule_id(constituent['instance_key'], slot):
                raise GeneratorError('invalid_reference', f'{path}/schedule_ids/{slot}', 'Invalid constituent schedule reference')
            referenced.add(sid)
        for index in constituent['binding_indices']:
            if index >= len(bundle['bindings']):
                raise GeneratorError('invalid_reference', f'{path}/binding_indices', 'Binding index missing')
            binding = bundle['bindings'][index]
            if binding['instance_key'] != constituent['instance_key'] or binding['program_id'] != constituent['program_id']:
                raise GeneratorError('invalid_reference', f'{path}/binding_indices', 'Binding belongs to another constituent')
            if index in owned:
                raise GeneratorError('invalid_reference', f'{path}/binding_indices', 'Binding has multiple owners')
            owned.add(index)
    if owned != set(range(len(bundle['bindings']))):
        raise GeneratorError('invalid_reference', '/constituents', 'Every binding must be owned')
    if referenced != set(schedules):
        raise GeneratorError('invalid_reference', '/schedules', 'Every schedule must be referenced')


def finalize_channels(generated: dict) -> dict:
    """Copy and validate source output, applying only an explicitly recorded export precision."""
    if not isinstance(generated, dict) or set(generated) != {'channels', 'source_context'}:
        raise GeneratorError('invalid_channels', '/', 'Expected channels and source_context')
    _finite(generated)
    channels, context = generated['channels'], generated['source_context']
    if not isinstance(channels, dict) or not isinstance(context, dict):
        raise GeneratorError('invalid_channels', '/', 'Malformed generated channels')
    result = copy.deepcopy(generated)
    digits = context.get('export_significant_digits')
    if digits is not None and (isinstance(digits, bool) or not isinstance(digits, int) or not 1 <= digits <= 17):
        raise GeneratorError('invalid_channels', '/source_context/export_significant_digits', 'Invalid precision')
    for slot, values in channels.items():
        if not isinstance(slot, str) or not slot or not isinstance(values, list) or len(values) != 8760:
            raise GeneratorError('invalid_channels', f'/channels/{slot}', 'Expected 8760 hourly values')
        for i, value in enumerate(values):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise GeneratorError('invalid_channels', f'/channels/{slot}/{i}', 'Nonfinite or nonnumeric value')
            result['channels'][slot][i] = float(f'{value:.{digits}g}') if digits is not None else value
    return result
