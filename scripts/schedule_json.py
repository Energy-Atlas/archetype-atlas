"""Source-faithful hourly schedule DTOs and explicit coverage fallbacks."""
import copy
import datetime as dt
from scripts.definition_contract import stable_id

POLICY = 'atlas-program-defaults-1.0.0'
DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Hol', 'WntrDsn', 'SmrDsn']


def normalize_schedule(record):
    result = {'id': record['id'], 'name': record.get('source_name') or record.get('source_channel') or record.get('name') or record['id'],
              'unit': {'dimensionless': '1', 'C': 'degC'}.get(record['units'], record['units']),
              'timestep_minutes': record.get('time_resolution_minutes', 60),
              'source_context': {k: copy.deepcopy(v) for k, v in record.items() if k not in {'rules', 'annual_values'}}}
    if 'annual_values' in record:
        result.update(type='annual', year=record['calendar']['year'], clock='local_standard_time', values=list(record['annual_values']))
    else:
        result.update(type='ruleset', rule_selection='last_specific_match_else_last_default', rules=[])
        result['source_context']['rule_metadata'] = [{k: copy.deepcopy(v) for k, v in r.items() if k != 'values'} for r in record['rules']]
        for rule in record['rules']:
            tokens = rule['day_types'].split('|') if isinstance(rule['day_types'], str) else rule['day_types']
            result['rules'].append({'start_date': rule['start_date'][-5:] if len(rule['start_date']) == 10 else rule['start_date'][5:10],
                                   'end_date': rule['end_date'][-5:] if len(rule['end_date']) == 10 else rule['end_date'][5:10],
                                   'day_types': list(dict.fromkeys('SmrDsn' if d == 'DummySmrDsn' else d for d in tokens)),
                                   'values': list(rule['values'])})
    return result


def constant_schedule(value, unit, rule_id):
    identity = stable_id('default-schedule', {'policy': POLICY, 'rule': rule_id, 'value': value, 'unit': unit})
    return {'id': identity, 'name': 'Experimental default / ' + rule_id, 'unit': unit,
            'type': 'ruleset', 'timestep_minutes': 60, 'rule_selection': 'last_specific_match_else_last_default',
            'rules': [{'start_date': '01-01', 'end_date': '12-31', 'day_types': ['Default'], 'values': [value]}]}


def date_mask(start, end):
    first = dt.date(2000, 1, 1)
    a = (dt.date.fromisoformat('2000-' + start) - first).days
    b = (dt.date.fromisoformat('2000-' + end) - first).days
    if a <= b:
        return ((1 << (b - a + 1)) - 1) << a
    return (((1 << 366) - 1) ^ ((1 << a) - 1)) | ((1 << (b + 1)) - 1)


def has_full_coverage(schedule):
    if schedule['type'] == 'annual':
        return True
    coverage = {day: 0 for day in DAYS}
    for rule in schedule['rules']:
        mask = date_mask(rule['start_date'], rule['end_date'])
        tokens = set(rule['day_types'])
        for day in DAYS:
            if ('Default' in tokens or day in tokens or
                    day in DAYS[:5] and 'Wkdy' in tokens or day in {'Sat', 'Sun'} and 'Wknd' in tokens):
                coverage[day] |= mask
    return all(value == (1 << 366) - 1 for value in coverage.values())


def complete_schedule(schedule, fallback):
    if has_full_coverage(schedule):
        return schedule, False
    result = copy.deepcopy(schedule)
    result['id'] = stable_id('completed-schedule', {'source': schedule['id'], 'policy': POLICY, 'fallback': fallback})
    result['name'] += ' / explicit coverage fallback'
    result['rules'].insert(0, {'start_date': '01-01', 'end_date': '12-31', 'day_types': ['Default'], 'values': [fallback]})
    return result, True


def extrema(schedule):
    values = schedule['values'] if schedule['type'] == 'annual' else [v for r in schedule['rules'] for v in r['values']]
    return min(values), max(values)
