"""Explicit contract versions and source-owner identity; no implicit type inference."""
from .errors import GeneratorError


def request_version(params):
    if not isinstance(params,dict):
        raise GeneratorError('invalid_contract','/','Request params must be an object')
    version=params.get('schema_version','1.0.0')
    if type(version) is not str or version not in {'1.0.0','1.1.0','1.2.0'}:
        raise GeneratorError('unsupported_schema','/schema_version','Explicit supported request version required')
    return version


def owner_identity(record):
    """Exact typed source identity; legacy records have only programme identity."""
    kind=record.get('owner_kind','program')
    if kind in {'program','derived_result'}:
        identifier=record.get('program_id')
        if (type(identifier) is not str or not identifier or
                set(record)&{'source_service_id','physical_id'}):
            raise GeneratorError('invalid_contract','/owner_kind','Programme/derived owner requires only its programme/result ID')
        return kind,identifier
    if kind=='physical_service':
        source=record.get('source_service_id');physical=record.get('physical_id')
        if (type(source) is not str or not source or type(physical) is not str or not physical or
                'program_id' in record):
            raise GeneratorError('invalid_contract','/owner_kind','Physical service requires source and physical IDs without a programme ID')
        if 'physical_binding_kind' in record:
            return kind,source,*physical_identity(record)
        return kind,source,physical
    raise GeneratorError('invalid_contract','/owner_kind','Unknown explicit owner kind')


def physical_identity(record):
    """Physical scope excludes the source SID, which remains a separate authority."""
    if record.get('owner_kind') != 'physical_service':
        raise GeneratorError('invalid_contract', '/owner_kind', 'Physical service owner required')
    physical = record.get('physical_id')
    kind = record.get('physical_binding_kind')
    if type(physical) is not str or not physical:
        raise GeneratorError('invalid_contract', '/physical_id', 'Physical ID required')
    if kind == 'legacy_whole':
        if 'building_realization_id' in record or 'unit_id' in record or 'source_fixture_role_id' in record:
            raise GeneratorError('invalid_contract', '/physical_binding_kind', 'Legacy physical scope is global')
        return kind, physical
    building = record.get('building_realization_id')
    if type(building) is not str or not building:
        raise GeneratorError('invalid_contract', '/building_realization_id', 'Building realization required')
    if kind == 'exact_source_role':
        if 'unit_id' in record or type(record.get('source_fixture_role_id')) is not str or not record['source_fixture_role_id']:
            raise GeneratorError('invalid_contract', '/source_fixture_role_id', 'Exact source role required')
        return kind, building, physical
    if kind == 'caller_unit_prototype_density_fixed_dhw':
        unit = record.get('unit_id')
        if type(unit) is not str or not unit or 'source_fixture_role_id' in record:
            raise GeneratorError('invalid_contract', '/unit_id', 'Caller unit required')
        return kind, building, unit, physical
    raise GeneratorError('invalid_contract', '/physical_binding_kind', 'Unknown physical binding kind')


def identity_fields(record,version):
    kind,*identifiers=owner_identity(record)
    if version=='1.0.0':
        if kind=='physical_service':
            raise GeneratorError('unsupported_schema','/schema_version','Physical ownership cannot be downgraded to programme-only v1.0')
        return {'program_id':identifiers[0]}
    if version not in {'1.1.0','1.2.0'}:
        raise GeneratorError('unsupported_schema','/schema_version','Unknown ownership contract version')
    if kind=='physical_service':
        fields = {'owner_kind':kind,'source_service_id':identifiers[0],
                  'physical_id':record['physical_id'] if version=='1.2.0' else identifiers[1]}
        if version == '1.2.0':
            scope = physical_identity(record)
            fields['physical_binding_kind'] = scope[0]
            if len(scope) > 2: fields['building_realization_id'] = scope[1]
            if scope[0] == 'exact_source_role': fields['source_fixture_role_id'] = record['source_fixture_role_id']
            if scope[0] == 'caller_unit_prototype_density_fixed_dhw': fields['unit_id'] = scope[2]
        return fields
    if version == '1.2.0':
        fields = {'owner_kind': kind, 'program_id': identifiers[0]}
        for name in ('building_realization_id', 'unit_id'):
            if name in record: fields[name] = record[name]
        return fields
    return {'owner_kind':kind,'program_id':identifiers[0]}


def upgrade_generated_reference_identities(bundle):
    """Tag already validated legacy generated references for a v1.1 merge."""
    # Called only after validation of the exact v1.0 input, whose contract has
    # no external service aliases. Never repair a missing v1.1 inventory.
    for owner in bundle['constituents']:
        owner['required_service_links']=[]
    bindings=bundle['bindings']
    def walk(value):
        if isinstance(value,dict):
            if 'binding_index' in value:
                index=value['binding_index']
                if type(index) is not int or not 0<=index<len(bindings):
                    raise GeneratorError('invalid_reference','/binding_index','No actual legacy binding for typed upgrade')
                value.update(identity_fields(bindings[index],'1.1.0'))
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    for field in ('bindings','constituents','generation'):walk(bundle[field])
