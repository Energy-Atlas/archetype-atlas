"""Evaluate selected source controls and backgrounds on the explicit clock."""
import copy
from datetime import date, timedelta
import math

from .calendar import evaluate_rules
from .errors import GeneratorError


def _native_constant(slot,rule):
    """Selected source-created water Ruleset, native storage then round5 getter."""
    from .commercial.parametric import _stored, _hourly
    path='/companions/'+slot
    evidence=rule.get('evidence',{})
    fields=('original_value','stored_value','native_hourly_value')
    if (slot not in {'water_target_temperature','water_sensible_fraction','water_latent_fraction'} or
            any(type(rule.get(k)) not in (int,float) or not math.isfinite(rule[k]) for k in fields) or
            not isinstance(evidence,dict) or not evidence.get('native_output_sha256') or
            evidence.get('source_method')!='create_water_use.rb:39-62; Standards0.8.6 information.rb:338-382'):
        raise GeneratorError('source_integrity',path,'Exact finite source fixed-control/native method evidence required')
    operand=rule.get('source_operand',{})
    profile=rule.get('native_source_profile')
    specials=rule.get('native_special_profiles',{});creation=rule.get('source_profile_creation',{})
    if (not isinstance(operand,dict) or type(operand.get('value')) not in (int,float) or not math.isfinite(operand['value']) or
            not isinstance(profile,list) or len(profile)!=1 or profile[0]!=[24.0,rule['stored_value']] or
            not isinstance(specials,dict) or set(specials)!={'WntrDsn','SmrDsn'} or any(points!=profile for points in specials.values()) or
            creation.get('method')!='create_constant_schedule_ruleset' or creation.get('original_rule_order')!=[] or
            creation.get('original_special_state')!='not_explicitly_set'):
        raise GeneratorError('source_integrity',path,'Actual source operand and native constant profile required')
    if slot=='water_target_temperature':
        if (operand.get('unit')!='F' or operand.get('method')!='OpenStudio.convert(F,C) then native constant ScheduleDay storage' or
                (operand['value']-32)/1.8!=rule['original_value']):
            raise GeneratorError('source_integrity',path,'Original Fahrenheit and canonical Celsius source operands differ')
        # The compiled profile is an actual locked native fixed operand, not an
        # emulation of OpenStudio's unit-library floating-point conversion.
        stored=_stored(profile[0][1])
    else:
        if operand.get('unit')!='fraction' or operand['value']!=rule['original_value']:
            raise GeneratorError('source_integrity',path,'Original source fixed fraction operand differs')
        stored=_stored(rule['original_value'])
    hourly=_hourly([[24.0,stored]],6)[0]
    if stored!=rule['stored_value'] or hourly!=rule['native_hourly_value']:
        raise GeneratorError('source_integrity',path,'Native fixed-control storage/getter receipt differs from source calculation')
    return [hourly]*8760


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
        elif method == 'native_constant_ruleset':
            values = _native_constant(slot,rule)
        else:
            raise GeneratorError('unsupported_binding', '/companions/'+slot, 'No compiled source method')
        channels[slot] = values
        receipts[slot] = dict(copy.deepcopy(rule['evidence']), method=method)
        if method=='native_constant_ruleset':
            receipts[slot]['native_getter_precision']={
                'original_canonical_value':rule['original_value'],'source_operand':copy.deepcopy(rule['source_operand']),
                'actual_native_stored_value':rule['stored_value'],'actual_native_source_profile':copy.deepcopy(rule['native_source_profile']),
                'native_special_profiles':copy.deepcopy(rule['native_special_profiles']),
                'source_profile_creation':copy.deepcopy(rule['source_profile_creation']),
                'hourly_value':values[0],'method':'Pinned native ScheduleDay getter then Ruby3.2.2 round5',
                'canonical_value_is_native_stored_value':rule['original_value']==rule['stored_value'],
                'annual_normalization':'none; fixed control retains source semantics'}
    for slot, values in channels.items():
        if len(values) != 8760 or any(isinstance(v, bool) or not isinstance(v, (int,float)) or not math.isfinite(v) for v in values):
            raise GeneratorError('invalid_schedule', '/companions/'+slot, '8760 finite hourly source values required')
    return {'channels': channels, 'source_context': {'resource_set_id': resources.resource_set_id,
            'year': year, 'clock': 'local_standard_time', 'export_precision': 'raw_source_float',
            'companion_receipts': receipts, 'energy_normalization': 'none; controls retain source semantics'}}
