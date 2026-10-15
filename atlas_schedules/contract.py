"""Strict request and emitted bundle validation for hourly local-standard schedules."""
import calendar
import copy
from datetime import date
import json
import math
from pathlib import Path
import re
from functools import lru_cache

from .budgets import ANNUAL_UNITS
from .canonical import schedule_id
from .errors import GeneratorError
from .owners import request_version,owner_identity

_ROOT = Path(__file__).resolve().parent
_SCHEMA_KEYWORDS = {'$schema', '$id', '$defs', '$ref', 'type', 'const', 'enum', 'oneOf',
                   'properties', 'required', 'additionalProperties', 'items', 'uniqueItems',
                   'minProperties', 'minItems', 'maxItems', 'minLength', 'pattern', 'minimum', 'maximum'}


def _schema_errors(value, name, version='1.0.0'):
    schema = _load_schema(name,version)
    _check_schema(value, schema, schema, '')


@lru_cache(maxsize=6)
def _load_schema(name,version='1.0.0'):
    if version not in {'1.0.0','1.1.0'}:
        raise GeneratorError('unsupported_schema','/schema_version','Unsupported schema version')
    suffix='v1' if version=='1.0.0' else 'v1_1'
    schema = json.loads((_ROOT/f'schemas/schedule-generator-{name}-{suffix}.schema.json').read_text(encoding='utf-8'))
    def vocabulary(node):
        # Check every schema branch, including unselected/optional fields.
        unknown=set(node)-_SCHEMA_KEYWORDS
        if unknown:
            raise GeneratorError('unsupported_schema','/','Unsupported keyword: '+sorted(unknown)[0])
        for key in ('properties','$defs'):
            for child in node.get(key,{}).values(): vocabulary(child)
        for key in ('items','additionalProperties'):
            if isinstance(node.get(key),dict): vocabulary(node[key])
        for branch in node.get('oneOf',[]): vocabulary(branch)
    vocabulary(schema)
    return schema


def _check_schema(value, schema, root, path):
    """Only the explicitly enumerated local v1 schema vocabulary, offline stdlib.

    New schema keywords fail closed rather than silently weaken the contract.
    Development tests compare this bounded checker with the JSON Schema oracle.
    """
    unknown = set(schema)-_SCHEMA_KEYWORDS
    if unknown:
        raise GeneratorError('unsupported_schema', path or '/', 'Unsupported keyword: '+sorted(unknown)[0])
    def fail(message):
        raise GeneratorError('invalid_contract', path or '/', message)
    if '$ref' in schema:
        ref = schema['$ref']
        if not ref.startswith('#/$defs/') or ref.count('/') != 2:
            raise GeneratorError('unsupported_schema', path or '/', 'Only local named definitions supported')
        _check_schema(value, root['$defs'][ref.rsplit('/',1)[1]], root, path)
    if 'oneOf' in schema:
        matches = 0
        for branch in schema['oneOf']:
            try: _check_schema(value, branch, root, path)
            except GeneratorError as error:
                if error.code != 'invalid_contract': raise
            else: matches += 1
        if matches != 1: fail('Expected exactly one contract alternative')
    types = schema.get('type', [])
    types = [types] if isinstance(types,str) else types
    def finite_number():
        if type(value) not in (int,float): return False
        try: return math.isfinite(value)
        except OverflowError: return False
    predicates = {'object':lambda: isinstance(value,dict), 'array':lambda: isinstance(value,list),
                  'string':lambda: isinstance(value,str), 'null':lambda: value is None,
                  'number':finite_number,
                  'integer':lambda: finite_number() and value == int(value),
                  'boolean':lambda: type(value) is bool}
    if any(t not in predicates for t in types):
        raise GeneratorError('unsupported_schema',path or '/','Unknown schema type')
    if types and not any(predicates[t]() for t in types): fail('Incorrect value type')
    def equal(a,b):
        return type(a) is type(b) and a == b if isinstance(a,bool) or isinstance(b,bool) else a == b
    if 'const' in schema and not equal(value,schema['const']): fail('Incorrect constant')
    if 'enum' in schema and not any(equal(value,v) for v in schema['enum']): fail('Unknown enumeration value')
    if isinstance(value,dict):
        missing = set(schema.get('required',[]))-set(value)
        if missing: fail('Missing required field: '+sorted(missing)[0])
        if len(value)<schema.get('minProperties',0): fail('Too few object properties')
        for key,child in value.items():
            if not isinstance(key,str): fail('JSON object keys must be strings')
            definition = schema.get('properties',{}).get(key,schema.get('additionalProperties',True))
            if definition is False: fail('Unknown field: '+key)
            if isinstance(definition,dict): _check_schema(child,definition,root,path+'/'+key)
    elif isinstance(value,list):
        if not schema.get('minItems',0)<=len(value)<=schema.get('maxItems',math.inf): fail('Incorrect array length')
        if schema.get('uniqueItems') and any(value[i] in value[:i] for i in range(len(value))): fail('Duplicate array item')
        for i,child in enumerate(value):
            if 'items' in schema: _check_schema(child,schema['items'],root,path+'/'+str(i))
    elif isinstance(value,str):
        if len(value)<schema.get('minLength',0): fail('String too short')
        if 'pattern' in schema and re.search(schema['pattern'],value) is None: fail('String pattern mismatch')
    elif type(value) in (int,float):
        if not schema.get('minimum',-math.inf)<=value<=schema.get('maximum',math.inf): fail('Number outside contract bounds')


def _finite(value, path=''):
    if value is not None and type(value) not in (str,bool,int,float,dict,list):
        raise GeneratorError('invalid_json',path or '/','Value is not a JSON primitive/object/array')
    if isinstance(value, float) and not math.isfinite(value):
        raise GeneratorError('invalid_json', path or '/', 'Nonfinite number')
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key,str):
                raise GeneratorError('invalid_json',path or '/','JSON object keys must be strings')
            _finite(child, f'{path}/{key}')
    elif isinstance(value, list):
        for i, child in enumerate(value):
            _finite(child, f'{path}/{i}')


def validate_request(params: dict, seed: int) -> None:
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**64:
        raise GeneratorError('invalid_seed', '/seed', 'Explicit unsigned 64-bit integer required')
    _finite(params)
    version=request_version(params)
    checked=params
    if version=='1.0.0' and 'schema_version' in params:
        checked={k:v for k,v in params.items() if k!='schema_version'}
    _schema_errors(checked, 'request',version)
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
        service_members=mixture.get('service_members',[]) if version=='1.1.0' else []
        if (not members and not service_members) or any(m['instance_key'] not in keys for m in members):
            raise GeneratorError('invalid_mixture', '/mixture/members', 'Members must reference instances')
        if len({m['instance_key'] for m in members}) != len(members):
            raise GeneratorError('invalid_mixture', '/mixture/members', 'Duplicate member allocation')
        if members and mixture['composition_id'] is None and not math.isclose(math.fsum(m['weight'] for m in members), 1, rel_tol=0, abs_tol=1e-12):
            raise GeneratorError('invalid_mixture', '/mixture/members', 'Normalized area weights must sum to one')
        if version=='1.1.0':
            owners={item['key']:item for item in params['instances']}
            if any(owners[m['instance_key']]['owner_kind']=='physical_service' for m in members):
                raise GeneratorError('invalid_mixture','/mixture/members','Whole physical services use separate unweighted service_members')
            if (len({m['instance_key'] for m in service_members})!=len(service_members) or
                    any(m['instance_key'] not in owners or owners[m['instance_key']]['owner_kind']!='physical_service' for m in service_members)):
                raise GeneratorError('invalid_mixture','/mixture/service_members','Unique physical-service owner keys required')
            if service_members and ('result_basis' not in mixture or 'denominator' not in mixture):
                raise GeneratorError('requires_binding','/mixture/denominator','Whole services require explicit physical result basis and denominator')
            if service_members and mixture['composition_id'] is not None:
                raise GeneratorError('invalid_mixture','/mixture/service_members','Explicit service selection cannot alter an authoritative source composition')


def validate_bundle(bundle: dict) -> None:
    _finite(bundle)
    _schema_errors(bundle, 'bundle',bundle.get('schema_version'))
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
            unit_pair = ANNUAL_UNITS.get(magnitude['unit'])
            if unit_pair is None or unit_pair[0] != target['unit']:
                raise GeneratorError('invalid_binding', path, 'Magnitude unit cannot produce annual target unit')
            multiplier = unit_pair[1]
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
        if not constituent['slots'] and (constituent['demands'] or constituent['controls'] or
                not any(e.get('accepted_absence') is True for e in constituent['evidence'])):
            raise GeneratorError('invalid_reference',path,'Empty recipe requires explicit accepted-inactive source receipts')
        slots = {item['slot']: item for item in constituent['slots']}
        demands = {item['demand_id']: item for item in constituent['demands']}
        controls = {item['slot']: item for item in constituent['controls']}
        if (len(slots) != len(constituent['slots']) or
                len(demands) != len(constituent['demands']) or
                len(controls) != len(constituent['controls'])):
            raise GeneratorError('invalid_reference', path, 'Duplicate resolved slot, demand or control')
        for slot, descriptor in slots.items():
            sid = constituent['schedule_ids'].get(slot)
            if sid != schedule_id(constituent['instance_key'], slot) or sid not in schedules:
                raise GeneratorError('invalid_reference', f'{path}/schedule_ids/{slot}', 'Declared slot has no scoped schedule')
            if schedules[sid]['unit'] != descriptor['unit']:
                raise GeneratorError('invalid_binding', f'{path}/slots/{slot}', 'Resolved slot unit differs from schedule')
        for slot, sid in constituent['schedule_ids'].items():
            if slot not in slots or sid not in schedules or sid != schedule_id(constituent['instance_key'], slot):
                raise GeneratorError('invalid_reference', f'{path}/schedule_ids/{slot}', 'Invalid constituent schedule reference')
            referenced.add(sid)
        for index in constituent['binding_indices']:
            if index >= len(bundle['bindings']):
                raise GeneratorError('invalid_reference', f'{path}/binding_indices', 'Binding index missing')
            binding = bundle['bindings'][index]
            if binding['instance_key'] != constituent['instance_key'] or owner_identity(binding)!=owner_identity(constituent):
                raise GeneratorError('invalid_reference', f'{path}/binding_indices', 'Binding belongs to another constituent')
            slot = binding['slot']
            if slot not in slots or constituent['schedule_ids'].get(slot) != binding['schedule_id']:
                raise GeneratorError('invalid_reference', f'{path}/binding_indices/{index}', 'Binding slot or schedule not declared by owner')
            if binding['kind'] == 'load':
                demand = demands.get(binding['demand_id'])
                if demand is None or demand['slot'] != slot or slots[slot]['kind'] != 'load':
                    raise GeneratorError('invalid_reference', f'{path}/binding_indices/{index}', 'Load demand not declared by owner')
                target = binding['reference_target']
                if any(target[field] != demand[field] for field in ('quantity', 'basis', 'fuel', 'host')) or target['magnitude_unit'] != demand['unit']:
                    raise GeneratorError('invalid_binding', f'{path}/binding_indices/{index}', 'Bound load differs from resolved source demand')
            else:
                control = controls.get(slot)
                if (control is None or slots[slot]['kind'] not in {'control', 'resident_count'} or
                        binding['control_quantity'] != control['quantity'] or
                        schedules[binding['schedule_id']]['unit'] != control['unit']):
                    raise GeneratorError('invalid_reference', f'{path}/binding_indices/{index}', 'Control not declared by owner')
            if index in owned:
                raise GeneratorError('invalid_reference', f'{path}/binding_indices', 'Binding has multiple owners')
            owned.add(index)
        owner_bindings = [bundle['bindings'][index] for index in constituent['binding_indices']]
        if (len(owner_bindings) != len(demands)+len(controls) or
                {b['demand_id'] for b in owner_bindings if b['kind']=='load'} != set(demands) or
                {b['slot'] for b in owner_bindings if b['kind']=='control'} != set(controls)):
            raise GeneratorError('invalid_reference',path,'Every active demand/control needs exactly one owned binding')
    if owned != set(range(len(bundle['bindings']))):
        raise GeneratorError('invalid_reference', '/constituents', 'Every binding must be owned')
    if referenced != set(schedules):
        raise GeneratorError('invalid_reference', '/schedules', 'Every schedule must be referenced')
    _validate_generated_binding_references(bundle)
    if bundle['schema_version']=='1.1.0':
        from .services import validate_service_links
        validate_service_links(bundle)


def _validate_generated_binding_references(bundle):
    """Close explicit generated component/service references against actual owners.

    An in-range integer alone does not prove ownership after bundle merging.
    Original source fields without a generated binding index are unaffected.
    """
    bindings=bundle['bindings']
    def binding(index,path):
        if type(index) is not int or not 0<=index<len(bindings):
            raise GeneratorError('invalid_reference',path,'Generated binding reference has no actual binding')
        return bindings[index]
    def walk(value,path):
        if isinstance(value,dict):
            if value.get('method')=='actual_generated_bound_trajectory_sum':
                components=value.get('components')
                required={'binding_index','instance_key','schedule_id','demand_id'}
                if (not isinstance(components,list) or not components or
                        any(not isinstance(c,dict) or not required<=set(c) for c in components)):
                    raise GeneratorError('invalid_reference',path+'/components',
                                         'Actual generated trajectory components require complete binding ownership')
                if bundle['schema_version']=='1.1.0':
                    for component in components:
                        if 'owner_kind' not in component:
                            raise GeneratorError('invalid_reference',path+'/components',
                                                 'Typed trajectory components require an explicit owner kind')
                        owner_identity(component)
            if 'binding_index' in value:
                actual=binding(value['binding_index'],path+'/binding_index')
                for field in ('instance_key','schedule_id','demand_id','source_service_id','physical_id'):
                    if field in value and value[field]!=actual.get(field):
                        raise GeneratorError('invalid_reference',path+'/'+field,
                                             'Generated component reference belongs to another owner, schedule or demand')
                if 'owner_kind' in value and owner_identity(value)!=owner_identity(actual):
                    raise GeneratorError('invalid_reference',path+'/owner_kind','Generated reference has a different typed source owner')
            if 'binding_indices' in value:
                indices=value['binding_indices']
                if not isinstance(indices,list):
                    raise GeneratorError('invalid_reference',path+'/binding_indices','Generated binding list required')
                for i,index in enumerate(indices):binding(index,path+'/binding_indices/'+str(i))
            for key,child in value.items():walk(child,path+'/'+key)
        elif isinstance(value,list):
            for i,child in enumerate(value):walk(child,path+'/'+str(i))
    for field in ('bindings','constituents','generation'):walk(bundle[field],'/'+field)


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
