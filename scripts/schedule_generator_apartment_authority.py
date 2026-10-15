"""Build-only apartment original/recipe/timing/fixed association producer."""
import copy
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from atlas_schedules.apartment_authority import (AUTH,BASE,CALENDAR,SELECTED,artifact,field,
    qualification_value,validate_apartment_authority,validate_fixed_resource,_ids)
from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import ResourceSet,safe_path,write_resources
from scripts.common import ROOT
from scripts.schedule_generator_apartments import compile_apartment_sources,compile_apartment_recipes,CONTROL_SLOTS
from scripts.schedule_generator_apartment_reference import load_apartment_fixed_reference,verify_apartment_qualifications


def _read(path):return json.loads((ROOT/path).read_bytes())


def _source(path):
    blob=(ROOT/path).read_bytes()
    return {'path':path,'sha256':hashlib.sha256(blob).hexdigest(),'locator':'/','value':json.loads(blob)}


def curate_apartment_timing_evidence(destination: Path, *, reviewed_receipt: Path) -> dict:
    """Verify approved durable curation; never recapture or replace originals."""
    expected='f42e38766bfc8b100104bf5ab87a197e6513cf9a0b57afec1017b50976b33b9e'
    blob=Path(reviewed_receipt).read_bytes()
    if hashlib.sha256(blob).hexdigest()!=expected:
        raise GeneratorError('source_integrity','/parity_receipt','Actual reviewed A1 receipt bytes required')
    if Path(destination).resolve()!=(ROOT/(BASE+'evidence')).resolve():
        raise GeneratorError('unsafe_resource_path',str(destination),'Exact independently retained evidence destination required')
    if (Path(destination)/'a1-fix1-native-comparison.json').read_bytes()!=blob:
        raise GeneratorError('source_integrity','/parity_receipt','Durable A1 receipt differs')
    files={'domain':BASE+'timing-domain.json','parity_receipt':BASE+'evidence/a1-fix1-native-comparison.json',
        'source_lock':'sources/schedule-generator-lock.json','timing_lock':'sources/schedule-generator-apartment-timing-lock.json',
        'dependency_cut':BASE+'evidence/a1-scientific-cut.json'}
    value={'method':SELECTED,'reference_calendar':copy.deepcopy(CALENDAR),**{k:_source(p) for k,p in files.items()}}
    value['residential_resources']=copy.deepcopy(value['timing_lock']['value']['residential_resources'])
    value['evidence']=[field(value[k],'Reviewed selected-method scientific evidence;55ordinary+3controlled, not per-ID authority') for k in files]
    return artifact('apartment-selected-timing',value)


def fixed_resources():
    manifest=_read(BASE+'fixed-qualification-manifest.json');result={}
    for key,entry in manifest['proof_files'].items():
        blob=(ROOT/entry['source_path']).read_bytes()
        if len(blob)!=entry['size_bytes'] or hashlib.sha256(blob).hexdigest()!=entry['sha256']:
            raise GeneratorError('source_integrity','/fixed_proofs/'+key,'Actual immutable A3 preimage differs')
        value=json.loads(blob)
        if key.startswith('caller-water-requirement__'):resource=value
        else:
            locator='/native_control_schedules' if key.startswith('caller-water-native-controls__') else '/'
            resource={'path':entry['source_path'],'sha256':entry['sha256'],'locator':locator,
                'value':value if locator=='/' else value['native_control_schedules']}
        validate_fixed_resource(key,resource);result['reference',key]=resource
    return result


def _originals(pid,sources):
    p=sources['programmes'][pid];original=sources['source_objects'];v=p['value']
    sids=list(dict.fromkeys([l['schedule_id'] for l in v['loads'] if l['schedule_id']]+[
        x['value'] for k,x in v['parameters'].items() if k in CONTROL_SLOTS and x['status']=='known']))
    schedules=[original['schedules'][sid] for sid in sids]
    eids=set(v['evidence_ids'])|_ids(v)
    for obj in schedules:
        rule=obj['value'];eids.update([rule['provenance_id']] if 'provenance_id' in rule else rule['evidence_ids'])
    evidence=sorted((original['field_evidence'][eid] for eid in eids),key=lambda o:int(o['locator'][1:]))
    fids={e['value']['source_file_id'] for e in evidence if e['value']['source_file_id'] is not None}
    files=sorted((original['raw_source_files'][fid] for fid in fids),key=lambda o:int(o['locator'][1:]))
    dwelling=pid in sources['requirements']
    return artifact('apartment-originals__'+pid,{'programme':p,'source_row':original['raw_rows'][pid],
        'schedules':schedules,'field_evidence':evidence,'source_files':files,
        'service_definition':sources['requirements'][pid]['service_definition'] if dwelling else None,
        'water_helpers':original['water_helpers'] if dwelling else []})


def compile_apartment_authority(sources: dict,recipes: dict,timing: dict,fixed_resources: dict) -> dict:
    records={('reference','apartment-selected-timing'):copy.deepcopy(timing)}
    for pid in sources['programmes']:
        original=_originals(pid,sources);recipe=artifact('apartment-programme-recipe__'+pid,recipes['program',pid])
        fixed=fixed_resources['reference','apartment-fixed-programme__'+pid]
        q=artifact('apartment-programme-qualification__'+pid,qualification_value(pid,original,recipe,fixed,
            timing if pid in sources['requirements'] else None))
        validate_apartment_authority(pid,recipes['program',pid],q)
        for key,value in (('apartment-originals__'+pid,original),('apartment-programme-recipe__'+pid,recipe),
                          ('apartment-programme-qualification__'+pid,q)):
            records['reference',key]=value
    return records


def verify_apartment_authority(sources: dict,recipes: dict,timing: dict,fixed_resources: dict,resources: dict) -> None:
    expected=compile_apartment_authority(sources,recipes,timing,fixed_resources)
    if set(expected)!=set(resources):
        raise GeneratorError('source_integrity','/authority','Complete authority resource inventory differs')
    for key,value in expected.items():
        if canonical(value)!=canonical(resources[key]):
            raise GeneratorError('source_integrity','/authority/'+key[1],'Whole independent association differs')
        if (ROOT/value['path']).read_bytes()!=canonical(value['value']):
            raise GeneratorError('source_integrity',value['path'],'Actual independent canonical preimage differs')


def build_apartment_resources(destination: Path,tables_destination: Path | None = None) -> dict:
    """Explicit development scope; no writes to installed resources or releases."""
    verify_current_code()
    scope=_read('sources/schedule-generator-apartment-scope.json')
    sources=compile_apartment_sources(scope);recipes=compile_apartment_recipes(sources,scope)
    fixed=fixed_resources()
    timing=curate_apartment_timing_evidence(ROOT/(BASE+'evidence'),
        reviewed_receipt=ROOT/(BASE+'evidence/a1-fix1-native-comparison.json'))
    authority=compile_apartment_authority(sources,recipes,timing,fixed)
    # Retain actual canonical authority preimages; immutable originals are separate.
    for value in authority.values():
        path=ROOT/value['path'];blob=canonical(value['value'])
        if path.exists() and path.read_bytes()!=blob:
            raise GeneratorError('source_integrity',value['path'],'Existing independent authority preimage changed')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
    records={}
    predecessor=ROOT/'data/generator-releases/v0.7.0/generator.zip'
    if hashlib.sha256(predecessor.read_bytes()).hexdigest()!='366b2f1596cb1f29173d5541e7074b0dababa7430327f9108650d98d602462cf':
        raise GeneratorError('source_integrity',str(predecessor),'Exact independently frozen229-programme predecessor required')
    with zipfile.ZipFile(predecessor) as package:
        for name in package.namelist():
            if name.startswith('atlas_schedules/data/') and name.endswith('.json') and not name.endswith('/manifest.json'):
                relative=str(safe_path(name.removeprefix('atlas_schedules/data/')))
                kind,key=relative.split('/',1);records[kind,key.removesuffix('.json')]=json.loads(package.read(name))
    # Exact selected32 source records use A1's independently locked archive path.
    from scripts.schedule_generator_apartment_timing import build_apartment_timing_test_resources
    parent=ROOT/'build/task-10/apartment-a1';parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent,prefix='a4-source-') as temporary:
        selected=build_apartment_timing_test_resources(Path(temporary)/'resources',timing['value']['domain']['value'],
            timing['value']['timing_lock']['value'],ROOT/'data/raw')
        records.update(copy.deepcopy(selected._records))
    records.update(recipes);records.update(fixed);records.update(authority)
    index=records['reference','catalogue-index'];by_id={x['id']:x for x in index['programs']}
    for pid in sources['programmes']:
        by_id[pid].update(status='compiled',reason='Reviewed A1/A3 per-ID apartment method association; A5 release certification separate')
    current=records['reference','m1-scope']
    current['cases'].extend({'program_id':pid,'case_id':'apartment-'+pid} for pid in sources['programmes'])
    current.update(milestone_id='A4',qualification_status='reviewed_apartment_method_integration_A5_release_pending')
    manifest=write_resources(destination,records,{'scope':'apartments','scope_version':'1.0.0',
        'interpretation':'229previous programme IDs plus84 candidate apartment methods; no A5/full-family release claim'})
    if tables_destination is not None:
        target=Path(tables_destination);target.mkdir(parents=True,exist_ok=True)
        (target/'apartment-scope.json').write_bytes(canonical(scope))
    return manifest


def verify_current_code(lock: dict | None = None) -> dict:
    """Build-only exact current cut; historical proof identities remain separate."""
    path='sources/schedule-generator-apartment-authority-lock.json'
    actual=_read(path)
    if lock is not None and canonical(lock)!=canonical(actual):
        raise GeneratorError('source_integrity','/authority_lock','Supplied current lock differs from retained lock')
    if actual['historical_fixed_lock']['sha256']!='6165bfbfbec59caa59d09e2c754c3d7a7e29e305f7053331165cc32c5bd51f87':
        raise GeneratorError('source_integrity','/authority_lock/historical_fixed_lock','Original reviewed A3 lock required')
    for entry in [actual['historical_fixed_lock'],actual['current_producer'],*actual['current_dependencies'],*actual['verification_evidence']]:
        blob=(ROOT/str(safe_path(entry['source_path']))).read_bytes()
        if hashlib.sha256(blob).hexdigest()!=entry['sha256'] or len(blob)!=entry['size_bytes']:
            raise GeneratorError('source_integrity',entry['source_path'],'Exact retained current/historical code/evidence cut differs')
    if actual['historical_dependency_relocations']!=_read(BASE+'evidence/authority-retention.json')['historical_dependency_relocations']:
        raise GeneratorError('source_integrity','/authority_lock/historical_dependencies','Complete historical relocation table differs')
    return actual


def verify_current_authority() -> dict:
    verify_current_code()
    scope=_read('sources/schedule-generator-apartment-scope.json')
    sources=compile_apartment_sources(scope);recipes=compile_apartment_recipes(sources,scope)
    fixed=fixed_resources();native=load_apartment_fixed_reference()
    verify_apartment_qualifications(sources,native,fixed)
    timing=curate_apartment_timing_evidence(ROOT/(BASE+'evidence'),
        reviewed_receipt=ROOT/(BASE+'evidence/a1-fix1-native-comparison.json'))
    actual={}
    for path in (ROOT/AUTH).glob('*.json'):
        actual['reference',path.stem]=_source(path.relative_to(ROOT).as_posix())
    verify_apartment_authority(sources,recipes,timing,fixed,actual)
    return {'passed':True,'programmes':len(recipes),'fixed_resources':len(fixed),'authority_resources':len(actual),
            'fixed_rule_ids':90,'water_requirements':40,'static_pools':8,'current_code_verified':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only',action='store_true',required=True)
    parser.parse_args()
    print(json.dumps(verify_current_authority()))


if __name__=='__main__':main()
