"""Explicit contract versions and source-owner identity; no implicit type inference."""
from .errors import GeneratorError


def request_version(params):
    if not isinstance(params,dict):
        raise GeneratorError('invalid_contract','/','Request params must be an object')
    version=params.get('schema_version','1.0.0')
    if type(version) is not str or version not in {'1.0.0','1.1.0'}:
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
        return kind,source,physical
    raise GeneratorError('invalid_contract','/owner_kind','Unknown explicit owner kind')


def identity_fields(record,version):
    kind,*identifiers=owner_identity(record)
    if version=='1.0.0':
        if kind=='physical_service':
            raise GeneratorError('unsupported_schema','/schema_version','Physical ownership cannot be downgraded to programme-only v1.0')
        return {'program_id':identifiers[0]}
    if version!='1.1.0':
        raise GeneratorError('unsupported_schema','/schema_version','Unknown ownership contract version')
    if kind=='physical_service':
        return {'owner_kind':kind,'source_service_id':identifiers[0],'physical_id':identifiers[1]}
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
