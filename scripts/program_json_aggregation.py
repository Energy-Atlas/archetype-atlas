"""Conserve ready DTO equipment trajectories and annual heat partitions (ADR 0016).

Design magnitudes must already share a physical host and scaling basis. Annual
energy is in ``load.unit * hour`` (for example Wh/m2), not an inferred zone area.
Original descriptors and schedules remain available for provenance inspection.
"""
import calendar
import copy
import datetime as dt
import functools
import json
import math

from scripts.definition_contract import canonical, stable_id
from scripts.semantics import DAY_TYPES, profile


RULE_SELECTION = 'last_specific_match_else_last_default'
WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
# Source DummySmrDsn is already normalized to SmrDsn in schedule_json DTOs.
SELECTORS = ['Default', 'Wkdy', 'Wknd'] + sorted(
    DAY_TYPES - {'Default', 'Wkdy', 'Wknd', 'DummySmrDsn'})


def _finite_nonnegative(value, description):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(description + ' must be finite and nonnegative')
    return value


def _rules(schedule):
    if schedule.get('rule_selection') != RULE_SELECTION:
        raise ValueError('Unsupported schedule rule selection')
    result = []
    for rule in schedule['rules']:
        if not set(rule['day_types']) <= DAY_TYPES:
            raise ValueError('Unsupported schedule day selectors')
        if len(rule['values']) not in (1, 24):
            raise ValueError('Expected constant or hourly day profile')
        result.append(dict(rule, day_types='|'.join(rule['day_types']),
                           start_date='2000-' + rule['start_date'],
                           end_date='2000-' + rule['end_date']))
    return result


@functools.lru_cache(maxsize=256)
def _schedule_hours(encoded, year, holidays):
    """Integrate on a stated local-standard-time calendar, with no DST shifts."""
    schedule = json.loads(encoded)
    if schedule['unit'] != '1' or schedule['timestep_minutes'] != 60:
        raise ValueError('Equipment schedules must be dimensionless hourly profiles')
    if schedule['type'] == 'annual':
        if schedule['year'] != year:
            raise ValueError('Annual schedule year differs from aggregation calendar year')
        if schedule.get('clock') != 'local_standard_time':
            raise ValueError('Annual schedule must use local_standard_time')
        values = schedule['values']
        if len(values) != (366 if calendar.isleap(year) else 365) * 24:
            raise ValueError('Annual schedule length differs from calendar year')
        for value in values:
            _finite_nonnegative(value, 'Schedule value')
        return math.fsum(values)
    if schedule['type'] != 'ruleset':
        raise ValueError('Unsupported equipment schedule type')
    rules = _rules(schedule)
    for rule in rules:
        for value in rule['values']:
            _finite_nonnegative(value, 'Schedule value')
    holiday_set = set(holidays)
    first = dt.date(year, 1, 1)
    return math.fsum(math.fsum(profile(rules, 'Hol' if date.isoformat() in holiday_set
                                     else WEEKDAYS[date.weekday()], date.strftime('%m-%d')))
                     for date in (first + dt.timedelta(days=i)
                                  for i in range(366 if calendar.isleap(year) else 365)))


def _compose_rules(schedules, magnitudes, total):
    sources = [_rules(s) for s in schedules]
    boundaries = {dt.date(2000, 1, 1), dt.date(2001, 1, 1)}
    for rules in sources:
        for rule in rules:
            boundaries.add(dt.date.fromisoformat(rule['start_date']))
            boundaries.add(dt.date.fromisoformat(rule['end_date']) + dt.timedelta(days=1))
    rules = []
    bounds = sorted(boundaries)
    for start, end in zip(bounds, bounds[1:]):
        for selector in SELECTORS:
            try:
                series = [profile(source, selector, start.strftime('%m-%d')) for source in sources]
            except ValueError:
                # Abstract Default/Wkdy/Wknd need not exist if explicit days do.
                # Actual simulation selectors must have full source coverage.
                if selector in WEEKDAYS + ('Hol', 'SmrDsn', 'WntrDsn'):
                    raise ValueError('Incomplete equipment ruleset coverage: ' + selector) from None
                continue
            values = [math.fsum(magnitude * row[h] for magnitude, row in zip(magnitudes, series)) / total
                      for h in range(24)]
            rules.append({'start_date': start.strftime('%m-%d'),
                          'end_date': (end - dt.timedelta(days=1)).strftime('%m-%d'),
                          'day_types': [selector],
                          'values': values[:1] if len(set(values)) == 1 else values})
    return {'type': 'ruleset', 'rule_selection': RULE_SELECTION, 'rules': rules}


def _compose_schedule(schedules, magnitudes, total):
    kinds = {s['type'] for s in schedules}
    if len(kinds) != 1:
        raise ValueError('Cannot combine annual and ruleset schedules without explicit compatible design-day profiles')
    if kinds == {'annual'}:
        result = {'type': 'annual', 'year': schedules[0]['year'], 'clock': 'local_standard_time',
                  'values': [math.fsum(m * value for m, value in zip(magnitudes, row)) / total
                             for row in zip(*(s['values'] for s in schedules))]}
    else:
        result = _compose_rules(schedules, magnitudes, total)
    result.update(unit='1', timestep_minutes=60, name='Summed equipment power trajectory')
    result['id'] = stable_id('equipment-schedule', result)
    return result


def aggregate_loads(loads, schedules, calendar_year=2007, holidays=()):
    """Return copied loads, all input plus derived schedules, and audit metadata.

    Only compatible electric/fuel equipment is combined. Constant heat fractions
    conserve annual partition; hourly partition can differ and source components
    are retained. Mixed annual/ruleset groups fail rather than lose design days.
    Zero-energy groups are omitted only if their other calendar/design profiles
    are also zero. Calendar-only assumptions are explicit in returned metadata.
    """
    dt.date(calendar_year, 1, 1)
    holiday_dates = sorted({h.isoformat() if isinstance(h, dt.date) else h for h in holidays})
    if any(dt.date.fromisoformat(h).year != calendar_year for h in holiday_dates):
        raise ValueError('Holiday date differs from aggregation calendar year')
    result_schedules = copy.deepcopy(schedules)
    metadata = {'calendar': {'year': calendar_year, 'holidays': holiday_dates,
                             'clock': 'local_standard_time', 'timestep_minutes': 60,
                             'annual_samples': 'Retained as recorded; holidays select ruleset profiles only.'},
                'method': 'Sum design-power trajectories; annual-energy-weighted constant heat fractions.',
                'heat_partition': 'Annual heat partition conserved; hourly partition is an approximation.',
                'groups': []}
    groups, positions = {}, []
    for load in loads:
        if load['type'] not in {'electric_equipment', 'gas_equipment'}:
            positions.append(('load', copy.deepcopy(load)))
            continue
        fuel = load.get('fuel', 'electricity' if load['type'] == 'electric_equipment' else 'natural gas')
        key = canonical([load['type'], fuel, load.get('host'), load['basis'], load['unit']])
        if key not in groups:
            groups[key] = []
            positions.append(('group', key))
        groups[key].append(copy.deepcopy(load))
    output = []
    for kind, item in positions:
        if kind == 'load':
            output.append(item)
            continue
        components = sorted(groups[item], key=canonical)
        magnitudes = [_finite_nonnegative(c['value'], 'Equipment magnitude') for c in components]
        profiles = [schedules[c['schedule_id']] for c in components]
        hours = [_schedule_hours(canonical(s), calendar_year, tuple(holiday_dates)) for s in profiles]
        energy = [m * h for m, h in zip(magnitudes, hours)]
        total_energy, total = math.fsum(energy), math.fsum(magnitudes)
        descriptor = {'components': [{'load': c, 'annual_energy': e,
                                      'annual_energy_weight': e / total_energy if total_energy else None}
                                     for c, e in zip(components, energy)],
                      'annual_energy': total_energy, 'annual_energy_unit': components[0]['unit'] + '*h'}
        metadata['groups'].append(descriptor)
        if not total_energy:
            if any(m and any(v for r in s.get('rules', []) for v in r['values'])
                   for m, s in zip(magnitudes, profiles)):
                raise ValueError('Equipment has zero annual energy but nonzero design or other calendar profiles')
            descriptor.update(status='omitted_zero_energy', demand_id=None)
            continue
        fraction_keys = set(components[0].get('heat_fractions', {}))
        for component in components:
            fractions = component.get('heat_fractions', {})
            if set(fractions) != fraction_keys:
                raise ValueError('Equipment heat fractions must have identical resolved keys')
            if not fraction_keys <= {'radiant', 'latent', 'lost'}:
                raise ValueError('Unsupported native equipment heat fraction')
            if any(_finite_nonnegative(v, 'Heat fraction') > 1 for v in fractions.values()) or math.fsum(fractions.values()) > 1 + 1e-12:
                raise ValueError('Equipment heat fractions exceed unity')
        if len(components) == 1:
            merged = copy.deepcopy(components[0])
        else:
            schedule = _compose_schedule(profiles, magnitudes, total)
            result_schedules[schedule['id']] = schedule
            merged = {k: copy.deepcopy(components[0][k]) for k in ('type', 'unit', 'basis', 'fuel', 'host')
                      if k in components[0]}
            merged.update(value=total, end_use=merged['type'], schedule_id=schedule['id'])
            if fraction_keys:
                merged['heat_fractions'] = {key: math.fsum(e * c['heat_fractions'][key]
                                                          for e, c in zip(energy, components)) / total_energy
                                            for key in sorted(fraction_keys)}
            merged['demand_id'] = stable_id('equipment-demand', {'load': merged,
                                                                'components': components,
                                                                'calendar': metadata['calendar']})
        descriptor.update(status='retained' if len(components) == 1 else 'aggregated', demand_id=merged['demand_id'])
        output.append(merged)
    return output, result_schedules, metadata
