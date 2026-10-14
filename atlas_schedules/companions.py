"""Evaluate selected source controls and backgrounds on the explicit clock."""
import copy
from datetime import date, timedelta
import math

from .calendar import evaluate_rules
from .errors import GeneratorError


def _thermostats(arguments, year):
    profiles = {}
    for mode in ('heating', 'cooling'):
        if arguments.get('hvac_control_'+mode+'_season_period') != 'Jan 1 - Dec 31':
            raise GeneratorError('unsupported_binding', '/thermostat/'+mode, 'Only declared full-year source season supported')
        for day in ('weekday', 'weekend'):
            prefix = 'hvac_control_'+mode+'_'+day+'_setpoint'
            try:
                base = float(arguments[prefix+'_temp'])
                magnitude = float(arguments[prefix+'_offset_magnitude'])
                direction = [float(v) for v in arguments[prefix+'_schedule'].split(',')]
            except (ValueError, KeyError, TypeError) as error:
                raise GeneratorError('missing_input', '/thermostat/'+prefix, 'Actual bound thermostat operands required') from error
            if len(direction) != 24 or not all(math.isfinite(v) for v in [base, magnitude, *direction]):
                raise GeneratorError('invalid_input', '/thermostat/'+prefix, '24 finite offset directions required')
            # ResStockArguments.modify_setpoint_schedule then HVAC.get_hvac_setpoints.
            profiles[mode, day] = [(base + magnitude*v - 32)*5/9 for v in direction]
    channels = {'heating_setpoint': [], 'cooling_setpoint': []}
    corrected = []
    for d in range(365):
        day = 'weekend' if (date(year, 1, 1)+timedelta(days=d)).weekday() > 4 else 'weekday'
        for hour, (heating, cooling) in enumerate(zip(profiles['heating', day], profiles['cooling', day])):
            # Full-year equal season selectors: correct both to their midpoint.
            if cooling < heating:
                corrected.append(d*24+hour)
                heating = cooling = (heating+cooling)/2
            channels['heating_setpoint'].append(heating)
            channels['cooling_setpoint'].append(cooling)
    return channels, corrected


def generate_companions(resolved: dict, resources) -> dict:
    """Return only companions selected by the compiled recipe, with source receipts."""
    inputs = resolved['inputs']
    year = inputs['year']
    channels, receipts = {}, {}
    for slot, rule in inputs['companion_rules'].items():
        method = rule['method']
        if method == 'translated_thermostat':
            if slot in channels:
                continue
            temperatures, corrected = _thermostats(inputs['thermostat_arguments'], year)
            for name, values in temperatures.items():
                channels[name] = values
                receipts[name] = dict(copy.deepcopy(rule['evidence']), method=method,
                                     correction='equal_seasons_midpoint', corrected_hours=corrected,
                                     equipment_unavailability='excluded', fan_setpoint_offset='not_selected_in_source_schedule_variant')
            continue
        if method == 'fixed_background':
            fixed = resources.get('residential', 'fixed-background-schedules')['definition']
            if fixed['variant'] != rule['variant']:
                raise GeneratorError('unsupported_binding', '/companions/'+slot, 'Selected background variant changed')
            shape = fixed['schedules'][rule['source_slot']]
            if shape['temperature_dependent']:
                raise GeneratorError('missing_input', '/companions/'+slot, 'Selected temperature-dependent rule requires its actual temperature binding')
            values = []
            for d in range(365):
                day = date(year, 1, 1)+timedelta(days=d)
                profile = shape['weekend_fractions' if day.weekday() > 4 else 'weekday_fractions']
                values.extend(v*shape['monthly_multipliers'][day.month-1]/shape['peak_divisor'] for v in profile)
        elif method == 'constant':
            values = [rule['value']]*8760
        elif method == 'source_rules':
            values = evaluate_rules(rule['source'], year, inputs['holidays'])['values']
        else:
            raise GeneratorError('unsupported_binding', '/companions/'+slot, 'No compiled source method')
        channels[slot] = values
        receipts[slot] = dict(copy.deepcopy(rule['evidence']), method=method)
    for slot, values in channels.items():
        if len(values) != 8760 or any(isinstance(v, bool) or not isinstance(v, (int,float)) or not math.isfinite(v) for v in values):
            raise GeneratorError('invalid_schedule', '/companions/'+slot, '8760 finite hourly source values required')
    return {'channels': channels, 'source_context': {'resource_set_id': resources.resource_set_id,
            'year': year, 'clock': 'local_standard_time', 'export_precision': 'raw_source_float',
            'companion_receipts': receipts, 'energy_normalization': 'none; controls retain source semantics'}}
