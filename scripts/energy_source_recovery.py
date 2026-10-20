"""Independent, source-traceable construction/system recovery primitives."""
import copy
import math

from scripts.definition_contract import canonical

BTUH_TO_W = .2930710701722222
GAL_TO_M3 = .003785411784


def physical_assembly(rows, name):
    """Allow selector-only duplicates, never different physical recipes."""
    matches = [(i, r) for i, r in enumerate(rows) if r['name'] == name]
    physics = {canonical({k:v for k,v in r.items() if k not in
                {'name','standards_construction_type','source_candidates'}}) for _, r in matches}
    if len(physics) != 1:
        raise ValueError('Ambiguous physical assembly: ' + name)
    result = copy.deepcopy(matches[0][1])
    result['source_candidates'] = [{'index': i, 'row': copy.deepcopy(r)} for i, r in matches]
    return result


def operand(value, original_unit, unit, conversion, evidence, defaulted=False):
    normalized = conversion(value) if value is not None else None
    if isinstance(normalized, float) and not math.isfinite(normalized):
        raise ValueError('Nonfinite recovered value')
    return {'value': normalized, 'unit': unit, 'status': 'unknown' if value is None else 'known',
            'origin': 'source_default' if defaulted else 'source',
            'evidence': {**copy.deepcopy(evidence), 'original_value': copy.deepcopy(value),
                         'original_unit': original_unit,
                         'transformation': TRANSFORMS.get((original_unit,unit),
                             'identity; retain source category' if unit=='category' else 'identity')}}


TRANSFORMS = {('degF','degC'):'(value - 32) * 5/9', ('Btu/h','W'):f'value * {BTUH_TO_W}',
    ('US gal','m3'):f'value * {GAL_TO_M3}', ('ft2','m2'):'value * 0.09290304',
    ('ft2*h*degF/Btu','m2*K/W'):'value / 5.678263337',
    ('Btu/h/ft2/degF','W/m2/K'):'value * 5.678263337',
    ('Btu/h/degF','W/K'):f'value * {BTUH_TO_W} * 1.8',
    ('degree','rad'):'value * pi / 180', ('W/cfm','W/(m3/s)'):'value / 0.00047194745',
    ('Btu/Wh','W/W'):f'value * {BTUH_TO_W}; retain rating metric',
    ('1/h','1/s'):'value / 3600'}


def ground_target(attributes):
    for source, field, model, factor in [
        ('assembly_maximum_f_factor','f_W_m_K','F-factor ground floor',1.730734667),
        ('assembly_maximum_c_factor','c_W_m2_K','C-factor underground wall',5.678263337),
        ('assembly_maximum_u_value','u_W_m2_K','layered_U_ground_construction',5.678263337)]:
        value = attributes.get(source)
        if value is not None:
            return {'field':field,'model':model,'value':value*factor,'source_field':source}
    return {'field':None,'model':'unresolved_ground_target','value':None,'source_field':None}


def assembly_u(layers, films):
    resistance=films
    for layer in layers:
        if layer.get('model') in {'MasslessOpaqueMaterial','AirGap'}:
            r=layer.get('resistance_m2_K_W')
        else:
            t,k=layer.get('thickness_m'),layer.get('conductivity_W_m_K')
            r=t/k if t is not None and k is not None and k>0 else None
        if r is None or r<0:
            return None
        resistance+=r
    return 1/resistance if resistance>0 else None


# Explicit source HPXML units. Unmapped native fields remain original evidence,
# not undocumented numbers in the normalized executable fields.
CONVERSIONS = {
    'heating_capacity': ('Btu/h', 'W', lambda x: x*BTUH_TO_W),
    'cooling_capacity': ('Btu/h', 'W', lambda x: x*BTUH_TO_W),
    'backup_heating_capacity': ('Btu/h', 'W', lambda x: x*BTUH_TO_W),
    'heating_capacity_17F': ('Btu/h', 'W', lambda x: x*BTUH_TO_W),
    'tank_volume': ('US gal', 'm3', lambda x: x*GAL_TO_M3),
    'storage_volume': ('US gal', 'm3', lambda x: x*GAL_TO_M3),
    'actual_tank_volume': ('US gal', 'm3', lambda x: x*GAL_TO_M3),
    'temperature': ('degF', 'degC', lambda x: (x-32)*5/9),
    'compressor_lockout_temp': ('degF', 'degC', lambda x: (x-32)*5/9),
    'backup_heating_lockout_temp': ('degF', 'degC', lambda x: (x-32)*5/9),
    'backup_heating_switchover_temp': ('degF', 'degC', lambda x: (x-32)*5/9),
    'collector_area': ('ft2', 'm2', lambda x: x*.09290304),
    'collector_rated_thermal_losses': ('Btu/h/ft2/degF', 'W/m2/K', lambda x: x*5.678263337),
    'tank_loss_coefficient': ('Btu/h/degF', 'W/K', lambda x: x*BTUH_TO_W*1.8),
    'heating_input_conversion_efficiency': ('1', '1', lambda x: x),
    'collector_tilt': ('degree', 'rad', lambda x: math.radians(x)),
    'collector_azimuth': ('degree', 'rad', lambda x: math.radians(x)),
    'fan_watts_per_cfm': ('W/cfm', 'W/(m3/s)', lambda x: x/.00047194745),
    'fan_watts': ('W', 'W', lambda x: x),
    'airflow_defect_ratio': ('1', '1', lambda x: x),
    'charge_defect_ratio': ('1', '1', lambda x: x),
    'pilot_light_btuh': ('Btu/h', 'W', lambda x: x*BTUH_TO_W),
}
RATINGS = {'cooling_efficiency_seer', 'cooling_efficiency_seer2', 'cooling_efficiency_eer',
           'cooling_efficiency_eer2', 'cooling_efficiency_ceer', 'heating_efficiency_hspf',
           'heating_efficiency_hspf2'}
FRACTIONS = {'heating_efficiency_afue', 'heating_efficiency_percent', 'heating_efficiency_cop',
             'backup_heating_efficiency_afue', 'backup_heating_efficiency_percent', 'energy_factor',
             'uniform_energy_factor', 'recovery_efficiency', 'fraction_heat_load_served',
             'fraction_cool_load_served', 'fraction_dhw_load_served', 'performance_adjustment',
             'collector_rated_optical_efficiency', 'solar_fraction', 'heating_autosizing_factor',
             'cooling_autosizing_factor', 'cop'}
CATEGORIES = {'heating_system_type', 'heating_system_fuel', 'cooling_system_type', 'cooling_system_fuel',
              'heat_pump_type', 'heat_pump_fuel', 'backup_type', 'backup_heating_fuel', 'compressor_type',
              'equipment_type', 'water_heater_type', 'fuel_type', 'location', 'usage_bin', 'tank_model_type',
              'operating_mode', 'collector_type', 'collector_loop_type', 'collector_orientation', 'system_type',
              'distribution_system_idref', 'related_hvac_idref', 'water_heating_system_idref'}


def normalize_hpxml(source, role, evidence):
    fields = {}
    for name, value in source.items():
        if name.endswith('_isdefaulted'):
            continue
        if name in CONVERSIONS:
            native, unit, convert = CONVERSIONS[name]
        elif name in RATINGS:
            native, unit, convert = 'Btu/Wh', 'W/W', lambda x: x*BTUH_TO_W
        elif name in FRACTIONS:
            native, unit, convert = '1', '1', lambda x: x
        elif name in CATEGORIES:
            native, unit, convert = 'source category', 'category', lambda x: x
        else:
            continue
        selected=evidence.get('field_evidence',{}).get(name,evidence.get('default_evidence')
            if source.get(name+'_isdefaulted',False) else None) or evidence
        proof = {k:v for k,v in selected.items() if k not in {'field_evidence','default_evidence'}}
        proof['source_locator']=selected['source_locator']+'/'+name
        fields[name] = operand(value, native, unit, convert, proof, source.get(name+'_isdefaulted', False))
        if name in evidence.get('field_evidence',{}):
            fields[name]['origin']='source_calculation'
    bindings = []
    for name in ('heating_capacity', 'cooling_capacity', 'backup_heating_capacity'):
        if name=='backup_heating_capacity' and not source.get('backup_type'):
            continue
        if name in fields and fields[name]['value'] is None:
            bindings.append('sizing.'+name)
    if role in {'water_heater', 'solar_thermal'}:
        bindings += ['loss_host', 'water_demand_assignment', 'water_mains_temperature']
    elif 'location' in fields and fields['location']['value'] is None:
        bindings.append('equipment_host')
    return {'role': role, 'fields': fields, 'required_bindings': sorted(set(bindings)),
            'native_source_fields': copy.deepcopy(source),
            'interpretation': 'Seasonal/integrated ratings retain their metric names; source defaults are not Atlas assumptions.'}


def readiness(row):
    if row.get('unresolved'):
        return 'blocked'
    return 'requires_bindings' if row.get('required_bindings') else 'resolved'
