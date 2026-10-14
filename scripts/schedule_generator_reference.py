"""Opt-in independent Ruby/OpenStudio capture; ordinary generation remains offline Python."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tarfile
from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import strict_json, ResourceSet
from scripts.common import ROOT
from scripts.runtime import extract_verified

_LOCK=ROOT/'sources/schedule-generator-reference-lock.json'
_VECTORS=ROOT/'data/schedule-generator/reference-vectors.json'

def _read(path):
    return strict_json(Path(path).read_bytes(),str(path))

def _verify(path,receipt):
    path=Path(path)
    if not path.is_file():raise GeneratorError('source_integrity',str(path),'Locked file missing')
    data=path.read_bytes()
    if len(data)!=receipt['size_bytes'] or hashlib.sha256(data).hexdigest()!=receipt['sha256']:
        raise GeneratorError('source_integrity',str(path),'Locked byte size or SHA-256 mismatch')
    return data

def load_reference_vectors(path: Path = _VECTORS) -> dict:
    lock=_read(_LOCK)
    data=_verify(path,lock['vectors'])
    vectors=strict_json(data,str(path))
    if vectors.get('provenance')!=lock['capture_provenance']:
        raise GeneratorError('source_integrity',str(path),'Independent capture provenance mismatch')
    return vectors

def capture_reference(runtime_archive: Path, resstock_archive: Path, standards_archive: Path,
                      ruby_source_cache: Path, destination: Path) -> dict:
    """Verify archives before extracting to a fresh task-local directory and executing."""
    lock=_read(_LOCK);destination=Path(destination)
    if destination.exists():raise GeneratorError('source_integrity',str(destination),'Capture destination must be new')
    runtime_lock=_read(ROOT/'sources/runtime-lock.json')['archives']
    standards_lock=_read(ROOT/'sources/commercial-runtime-lock.json')['archives'][0]
    for file,receipt in [(runtime_archive,runtime_lock[0]),(resstock_archive,runtime_lock[1]),(standards_archive,standards_lock)]:
        _verify(file,receipt)
    for source in lock['algorithm_sources']:
        if source['source_id']=='ruby':
            _verify(Path(ruby_source_cache)/source['source_path'].replace('/','__'),source)
    destination.mkdir(parents=True)
    # Execution uses a fresh extraction of the verified runtime, never another worktree.
    runtime_destination=(destination/'runtime').resolve()
    runtime_root=runtime_lock[0]['root']
    selected=[runtime_root+'/'+part for part in ('bin/','Ruby/','lib/','LICENSE.md','copyright.txt')]
    extracted=extract_verified(runtime_archive,runtime_lock[0]['sha256'],runtime_destination,include=selected)
    executable=extracted/runtime_lock[0]['root']/'bin/openstudio.exe'
    standards_source=next(s for s in lock['algorithm_sources'] if s['source_id']=='openstudio-standards')
    with tarfile.open(standards_archive) as archive:
        method_bytes=archive.extractfile(standards_source['source_path']).read()
    method=destination/'Standards.Model.rb';method.write_bytes(method_bytes);_verify(method,standards_source)
    # Independent source seed-allocation evidence is copied from the verified ResStock archive.
    resstock_sources=[]
    with tarfile.open(resstock_archive) as archive:
        for member in lock['resstock_methods']:
            data=archive.extractfile(runtime_lock[1]['root']+'/'+member['source_path']).read()
            if hashlib.sha256(data).hexdigest()!=member['sha256']:raise GeneratorError('source_integrity',member['source_path'],'ResStock method mismatch')
            resstock_sources.append(member)
    manifest=_read(ROOT/'atlas_schedules/data/manifest.json')
    resources=ResourceSet.load(manifest['resource_set_id'])
    schedules=[resources.get('reference',e['key'])['definition'] for e in manifest['resources']
               if e['kind']=='reference' and e['key'].startswith('schedule-')]
    schedules=[s for s in schedules if all('type' in r for r in s.get('rules',[]))]
    input_path=destination/'input.json'
    input_path.write_bytes(canonical({'seeds':lock['capture_seeds'],'schedules':schedules}))
    harness=ROOT/'scripts/reference_schedule_generator.rb'
    output=destination/'ruby-output.json'
    completed=subprocess.run([str(executable),str(harness),str(input_path.resolve()),str(method.resolve()),str(output.resolve())],
                             cwd=ROOT,capture_output=True,text=True,check=True)
    (destination/'execution.log').write_text(completed.stdout+completed.stderr,encoding='utf-8')
    capture=_read(output)
    if not capture['ruby_description'].startswith('ruby 3.2.2 '):raise GeneratorError('source_integrity','/runtime','Wrong Ruby version')
    provenance={'algorithm_sources':lock['algorithm_sources'],'resstock_methods':resstock_sources,
                'runtime_archive_sha256':runtime_lock[0]['sha256'],'runtime_version':runtime_lock[0]['version'],
                'executed_openstudio_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
                'harness_sha256':hashlib.sha256(harness.read_bytes()).hexdigest(),
                'input_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),
                'runtime_extraction_selection':selected,
                'source_locator':'reference_schedule_generator.rb: Random#rand probes; random.c:rand_init,genrand_real,limited_rand,limited_big_rand; Standards.Model.rb:model_add_schedule/model_add_vals_to_sch',
                'field_locator':'random_vectors[i].draws[j].value retains the original Ruby operation result; rule_vectors[i].values[h] retains the source ScheduleDay.getValue at h+0.5',
                'extraction_date':'2026-10-14','original_unit':'Ruby Random uniforms/integers and source hourly values',
                'original_value':'Independent runtime captures retained exactly',
                'transformation':'Ruby packed state converted to 624 least-significant-word-first uint32 values; index=625-left; OpenStudio profiles sampled at half hour',
                'interpretation_note':'Source RNG order/native initialization; selected frozen rules use Standards method. Explicit holiday selects default day; no Hol profile is created by upstream.'}
    result={'schema_version':'1.0.0','runtime':{'ruby_version':'3.2.2','ruby_description':capture['ruby_description'],
            'openstudio_version':runtime_lock[0]['version']},'provenance':provenance,
            'random_vectors':capture['random_vectors'],'enduse_vectors':capture['enduse_vectors'],'rule_vectors':capture['rule_vectors']}
    for vector in result['rule_vectors']:
        vector['source_record']=resources.get('reference',vector['schedule_id'])['provenance']
    (destination/'reference-vectors.json').write_bytes(canonical(result))
    candidate=dict(lock,capture_provenance=provenance,vectors={'source_path':'data/schedule-generator/reference-vectors.json',
                 'sha256':hashlib.sha256(canonical(result)).hexdigest(),'size_bytes':len(canonical(result))})
    (destination/'reference-lock.json').write_bytes(canonical(candidate))
    print(completed.stdout.strip())
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only',action='store_true')
    parser.add_argument('--runtime-archive',type=Path)
    parser.add_argument('--resstock-archive',type=Path)
    parser.add_argument('--standards-archive',type=Path)
    parser.add_argument('--ruby-source-cache',type=Path)
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args()
    if args.verify_only:
        result=load_reference_vectors();print('Verified independently captured vectors:',len(result['random_vectors']),len(result['rule_vectors']))
    else:
        operands=[args.runtime_archive,args.resstock_archive,args.standards_archive,args.ruby_source_cache,args.destination]
        if any(p is None for p in operands):parser.error('Capture requires every archive, source cache and new destination explicitly')
        capture_reference(*operands)

if __name__=='__main__':main()
