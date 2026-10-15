"""Literal source-native fixed-water operands with explicit temperature provenance."""
import copy
import hashlib

from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError

CONTROL_SLOTS=(('water_target_temperature','target_temperature','temperature','C'),
    ('water_sensible_fraction','sensible_fraction','sensible_fraction','fraction'),
    ('water_latent_fraction','latent_fraction','latent_fraction','fraction'))


def fixed_control_projection(control,pointer):
    values=control['values'];profile=control['profiles'].get('default')
    if (len(values)!=8760 or len(set(values))!=1 or set(control['profiles'])!={'default'} or
            not isinstance(profile,list) or len(profile)!=1 or profile[0][0]!=24 or
            set(control['special_profiles'])!={'SmrDsn','WntrDsn'} or
            any(points!=profile for points in control['special_profiles'].values())):
        raise GeneratorError('source_integrity',pointer,'Actual native fixed-control Ruleset is not constant/annual')
    return dict({k:copy.deepcopy(v) for k,v in control.items() if k!='values'},
        hourly_value=values[0],hourly_count=8760,hourly_array_sha256=hashlib.sha256(canonical(values)).hexdigest(),
        source_native_pointer=pointer)


def native_water_companions(definition,controls,source_temperature_operand,evidence,native_reference):
    """No family/basis inference: caller supplies exact original temperature field."""
    if (not isinstance(source_temperature_operand,dict) or source_temperature_operand.get('unit')!='F' or
            not source_temperature_operand.get('source_field') or not source_temperature_operand.get('source_receipt')):
        raise GeneratorError('source_integrity',definition['id'],'Explicit original source temperature field/value/unit/receipt required')
    companions={}
    for slot,name,quantity,unit in CONTROL_SLOTS:
        pointer=native_reference['source_native_prefix']+'/'+name
        projected=fixed_control_projection(controls[name],pointer)
        original=definition['load']['target_temperature_degC'] if name=='target_temperature' else {'sensible_fraction':.2,'latent_fraction':.05}[name]
        operand=(dict(copy.deepcopy(source_temperature_operand),method='OpenStudio.convert(F,C) then native constant ScheduleDay storage')
            if name=='target_temperature' else {'value':original,'unit':'fraction',
                'source_field':'create_water_use default '+name,
                'method':'Exact source fixed create_water_use constructor argument'})
        companions[slot]={'method':'native_constant_ruleset','original_value':original,
            'stored_value':projected['profiles']['default'][0][1],'native_hourly_value':projected['hourly_value'],
            'native_source_profile':copy.deepcopy(projected['profiles']['default']),
            'native_special_profiles':copy.deepcopy(projected['special_profiles']),
            'source_profile_creation':{'method':'create_constant_schedule_ruleset',
                'source_locator':'Standards0.8.6 create.rb:113-150','original_rule_order':[],
                'original_special_state':'not_explicitly_set','getter_alias':'Actual native getter returns fixed default'},
            'source_operand':operand,
            'evidence':dict(copy.deepcopy(evidence),source_method='create_water_use.rb:39-62; Standards0.8.6 information.rb:338-382',
                native_control_reference={'resource_kind':'reference','resource_key':native_reference['projection_resource_key'],
                    'json_pointer':native_reference['projection_prefix']+'/'+name,'source_native_pointer':pointer,
                    'source_path':native_reference['vectors']['source_path'],
                    'payload_sha256':native_reference['vectors']['payload_sha256'],
                    'source_gzip_sha256':native_reference['vectors']['sha256'],
                    'transformation':'Literal fixed-native operand projection; actual original arrays retained and independently compared'},
                interpretation='Original canonical source value versus actual native stored double and round5 getter; fixed fractions do not assign zone heat')}
    return companions
