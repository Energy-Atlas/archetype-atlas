"""Test-only pre-Ruling23 scalar validation oracle, preserved before optimization."""
import math,re
from atlas_schedules.errors import GeneratorError

_SCHEMA_KEYWORDS = {'$schema', '$id', '$defs', '$ref', 'type', 'const', 'enum', 'oneOf',
                   'properties', 'required', 'additionalProperties', 'items', 'uniqueItems',
                   'minProperties', 'minItems', 'maxItems', 'minLength', 'pattern', 'minimum', 'maximum'}

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
