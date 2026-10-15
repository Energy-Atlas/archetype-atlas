"""Build the explicit cumulative C5 resources from immutable source evidence."""
import copy
import hashlib
from pathlib import Path
import tempfile
import zipfile

from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet,safe_path,strict_json,write_resources
from scripts.common import ROOT
from scripts.schedule_generator_restaurants import compile_cumulative_records
from scripts.schedule_generator_restaurant_certification import build_native_join,validate_native_associations


def build_cumulative_resources(destination,tables_destination=None):
    """Development builder only; the standalone artifact needs no predecessor."""
    from scripts.schedule_generator_release import verify_generator
    from scripts.schedule_generator_families import recover_commercial_closure
    predecessor=ROOT/'data/generator-releases/v0.5.1'
    errors=verify_generator(predecessor)
    if errors:raise GeneratorError('source_integrity',str(predecessor),'; '.join(errors))
    release=strict_json((predecessor/'manifest.json').read_bytes(),'predecessor-manifest')
    archive_path=predecessor/'generator.zip'
    build_root=ROOT/'build';build_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=build_root,prefix='c5-predecessor-') as temporary:
        root=Path(temporary)
        with zipfile.ZipFile(archive_path) as archive:
            for name in archive.namelist():
                if not name.startswith('atlas_schedules/data/'):continue
                relative=str(safe_path(name.removeprefix('atlas_schedules/data/')))
                target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(archive.read(name))
        previous=ResourceSet(root,release['resource_set_id'])
        records=compile_cumulative_records(previous)
        predecessor_metadata=copy.deepcopy(previous.manifest)
    join=build_native_join(records)
    class Records:
        def get(self,kind,key):return copy.deepcopy(records[kind,key])
    association=validate_native_associations(Records(),join)
    scope=records['reference','m1-scope']
    scope.update(milestone_id='C5',qualification_status='source_native_methods_passed_current_family_certificate_required')
    for case in scope['cases'][119:]:
        case['source_gate_status']='passed'
        records['program',case['program_id']]['case']=copy.deepcopy(case)
    for case in scope['service_cases']:case['source_gate_status']='passed'
    records['reference','recipe-coverage']['milestone']='C5'
    for programme in records['reference','catalogue-index']['programs']:
        if programme['status']=='requires_binding':
            programme['reason']='outside_C5; exact source carriers/services/annual decomposition and family-specific native qualification remain'
    records['reference','restaurant-source-association']=association
    join_path='data/schedule-generator/restaurant-cumulative-native.json'
    scope_path='sources/schedule-generator-restaurant-scope.json'
    lock_path='sources/schedule-generator-restaurant-lock.json'
    native_lock_path='sources/schedule-generator-restaurant-cumulative-reference-lock.json'
    join_blob=canonical(join)
    native_lock={'schema_version':'1.0.0','source_gate_status':'passed',
        'fixture_order':[c['configuration_id'] for c in scope['cases']],
        'service_case_order':[c['case_id'] for c in scope['service_cases']],
        'vectors':{'source_path':join_path,'sha256':hashlib.sha256(join_blob).hexdigest(),'size_bytes':len(join_blob)},
        'interpretation':'Exact seven immutable component captures;165programme plus26separate physical service/configuration associations; numerical/current certificate separately required'}
    records['reference','family-native-lock']=native_lock
    lock=strict_json((ROOT/'sources/schedule-generator-warehouse-lock.json').read_bytes(),'warehouse-lock')
    for selector in ('full_service_restaurant','quick_service_restaurant'):recover_commercial_closure(lock,selector)
    blocked=[{'family':'outside_C5','status':'requires_binding',
        'reason':'1735programmes/368compositions outside this exact milestone; actual source/caller operands and native branch qualification remain; full extraction open'}]
    lock.update(milestone_id='C5',scope_cases=scope['cases'],service_cases=scope['service_cases'],blocked_families=blocked,
        frozen_predecessor={'source_path':'data/generator-releases/v0.5.1/generator.zip',
            **release['files']['generator.zip'],'resource_set_id':release['resource_set_id'],
            'interpretation':'Development extraction input only; all consumed records/captures are independently packaged in the new artifact, with no runtime dependency on this archive'})
    generated={scope_path:canonical(scope),join_path:join_blob,native_lock_path:canonical(native_lock)}
    for name,blob in generated.items():
        (ROOT/name).parent.mkdir(parents=True,exist_ok=True);(ROOT/name).write_bytes(blob)
        lock['frozen_files'][name]={'sha256':hashlib.sha256(blob).hexdigest(),'size_bytes':len(blob)}
    (ROOT/lock_path).write_bytes(canonical(lock))
    certificate=ROOT/'data/schedule-generator/families/restaurants/certification.json'
    if certificate.exists():records['reference','family-certification']=strict_json(certificate.read_bytes(),'C5-certificate')
    metadata={k:v for k,v in predecessor_metadata.items() if k not in {'resources','resource_set_id'}}
    metadata.update(scope='restaurants',milestone_id='C5',scope_version=scope['scope_version'],
        source_gate_status='passed',generator_support_status='not_shipped',cases=scope['cases'],
        service_cases=scope['service_cases'],complete_scope_request_contract_version='1.1.0',
        dependency_inventory=lock['required_resources'],blocked_families=blocked)
    manifest=write_resources(destination,records,metadata)
    if tables_destination is not None:
        tables_destination=Path(tables_destination);tables_destination.mkdir(parents=True,exist_ok=True)
        for name,value in {'catalogue-index':records['reference','catalogue-index'],
            'coverage':records['reference','recipe-coverage'],'scope':scope,'native-association':association,
            'physical-service-cases':{'schema_version':'1.0.0','cases':scope['service_cases']}}.items():
            (tables_destination/(name+'.json')).write_bytes(canonical(value))
    return manifest
