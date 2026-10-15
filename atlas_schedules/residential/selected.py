"""Pure selected ResStock unit occupancy and interior-light timing.

This component is deliberately unrouted. Whole residential wrappers retain
their source weather, installed equipment and event semantics.
"""
import math

from ..errors import GeneratorError
from .activity import dates, required, rows, simulate_activities
from .shapes import MONTHS, _schedules, building_america_lighting, shift_and_normalize

_LOCATION_FIELDS = ('state', 'latitude', 'longitude', 'time_zone_utc_offset')
_POSITIVE_FIELDS = {'year', 'holidays', 'residents', *_LOCATION_FIELDS}
_ZERO_FIELDS = {'year', 'holidays', 'residents'}


def validate_selected_inputs(inputs: dict, locations: list[dict]) -> None:
    """Require a complete, exact native argument tuple for positive cohorts."""
    if not isinstance(inputs, dict):
        raise GeneratorError('invalid_input', '/inputs', 'Selected input object required')
    n = required(inputs, 'residents')
    if type(n) is not int or n < 0:
        raise GeneratorError('invalid_input', '/inputs/residents', 'Explicit nonnegative integer cohort required')
    expected_fields = _ZERO_FIELDS if n == 0 else _POSITIVE_FIELDS
    if set(inputs) != expected_fields:
        raise GeneratorError('invalid_input', '/inputs', 'Exact selected method input fields required')
    if type(inputs['year']) is not int or inputs['year'] != 2007:
        raise GeneratorError('unsupported_input', '/inputs/year', 'Selected domain is 2007 only')
    if inputs['holidays'] != [] or type(inputs['holidays']) is not list:
        raise GeneratorError('unsupported_input', '/inputs/holidays', 'No holiday calendar in selected domain')
    if n == 0:
        return  # The orchestration layer handles source skip before RNG initialization.
    if not isinstance(locations, list) or len(locations) != 37:
        raise GeneratorError('resource_integrity', '/reference/apartment-timing-domain/locations',
                             'Exact native timing domain required')
    state = inputs['state']
    if not isinstance(state, str) or len(state) != 2:
        raise GeneratorError('invalid_input', '/inputs/state', 'Postal state code required')
    for key in _LOCATION_FIELDS[1:]:
        value = inputs[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise GeneratorError('invalid_input', '/inputs/'+key, 'Finite numeric source coordinate/offset required')
    actual = tuple(inputs[key] for key in _LOCATION_FIELDS)
    if not any(actual == tuple(location[key] for key in _LOCATION_FIELDS)
               for location in locations):
        raise GeneratorError('unsupported_input', '/inputs', 'Location tuple is outside locked native domain')


def generate_unit_occupancy_interior_lighting(inputs: dict, unit_seed: int, resources) -> dict:
    """Emit only the two same-argument selected source channels for positive N."""
    domain = resources.get('reference', 'apartment-timing-domain')['value']
    if (domain.get('method') != 'unit_occupancy_interior_lighting' or
            domain.get('calendar') != {'year': 2007, 'clock': 'local_standard_time', 'holidays': []}):
        raise GeneratorError('resource_integrity', '/reference/apartment-timing-domain',
                             'Selected timing calendar/method differs')
    validate_selected_inputs(inputs, domain['locations'])
    if inputs['residents'] == 0:
        raise GeneratorError('unsupported_input', '/inputs/residents',
                             'Orchestration must skip zero resident unit before source streams')
    # This call retains the source main/end-use stream construction and its
    # transient N x 35040 resident-state matrix. The returned receipt excludes it.
    activity = simulate_activities(inputs, unit_seed, resources)
    return _selected_shapes(activity, inputs, resources, domain)


def _selected_shapes(activity: dict, inputs: dict, resources, domain: dict) -> dict:
    """Source arithmetic on a real activity result; also permits capture-protocol proof."""
    days = dates(inputs['year'])
    shifts = {}
    for daytype in ('weekday', 'weekend'):
        table = rows(resources, daytype+'__state_and_monthly_schedule_shift_csv')
        header = table[0]
        shifts[daytype] = {row[header.index('Month')]: int(row[header.index('Lead')])
                           for row in table[1:] if row[header.index('State')] == inputs['state']}
        if set(shifts[daytype]) != set(MONTHS):
            raise GeneratorError('unsupported_input', '/inputs/state',
                                 'State/month shifts not reported by source')
    traces = activity['resident_states']
    count = activity['simulated_residents']
    if len(traces) != count or any(len(trace) != 35040 or any(type(s) is not int or not 0 <= s < 7
                                                            for s in trace) for trace in traces):
        raise GeneratorError('activity_context', '/activities/resident_states',
                             'Complete source state traces required')
    awake = []
    home = []
    for step in range(35040):
        away = sum(trace[step] == 5 for trace in traces)/count
        sleeping = sum(trace[step] == 0 for trace in traces)/count
        awake.append(1-(away+sleeping))
        home.extend([1-away]*15)
    offset = activity['unit_offset_minutes']
    occupants = shift_and_normalize(home, offset, days, shifts, 60)
    custom = _schedules(resources, 'schedules_csv')
    lighting = building_america_lighting(
        inputs['latitude'], inputs['longitude'], inputs['time_zone_utc_offset'],
        custom['lighting_interior', 'LightingInteriorMonthlyMultipliers'])
    minute_values = []
    for step, today in enumerate(days):
        profile = lighting[today.month-1]
        minimum = min(profile)
        for quarter in range(96):
            value = minimum+(profile[quarter//4]-minimum)*awake[step*96+quarter]
            minute_values.extend([value]*15)
    interior = shift_and_normalize(minute_values, offset, days, shifts)
    context = {
        'method': 'unit_occupancy_interior_lighting',
        'method_locator': 'ResStock BuildResidentialScheduleFile/resources/schedules.rb:945-955,1046-1067',
        'activity_locator': 'ResStock BuildResidentialScheduleFile/resources/schedules.rb:119-160,207-245',
        'source_revision': domain['evidence'][0]['source_revision'],
        'consumed_inputs': dict(inputs),
        'resource_set_id': resources.resource_set_id,
        'raw_source_precision': 'raw_source_float',
        'activity_status': activity['status'],
        'residents_input': inputs['residents'],
        'simulated_residents': count,
        'unit_seed': activity['unit_seed'],
        'occupant_types': list(activity['occupant_types']),
        'enduse_seeds': dict(activity['enduse_seeds']),
        'unit_offset_minutes': offset,
        'shift_order': ['annual_unit_minute_rotation', 'daily_state_month_rotation',
                        'hourly_sum', 'source_normalization'],
    }
    return {'channels': {'occupants': occupants, 'lighting_interior': interior},
            'source_context': context}
