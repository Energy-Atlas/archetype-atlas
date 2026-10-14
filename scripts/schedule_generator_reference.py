"""Opt-in independent Ruby/OpenStudio capture; ordinary generation remains offline Python."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile
from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import strict_json, ResourceSet, safe_path
from scripts.common import ROOT
from scripts.runtime import extract_verified

_LOCK=ROOT/'sources/schedule-generator-reference-lock.json'
_VECTORS=ROOT/'data/schedule-generator/reference-vectors.json'

def _long_path(path):
    path=Path(path).resolve()
    return Path('\\\\?\\'+str(path)) if os.name=='nt' else path

def residential_capture_inputs(resources):
    """Explicit scientific probes; no values inherited by the runtime kernel."""
    installed={key:True for key in ('dishwasher','clothes_washer','clothes_dryer','cooking_range',
                                   'plug_loads_other','plug_loads_tv','ceiling_fan','garage')}
    base={'year':2007,'residents':1,'state':'NC','latitude':35.741,'longitude':-81.389,
          'time_zone_utc_offset':-5,'weather_id':'USA_NC_Hickory.Rgnl.AP.723145_TMY3','installed':installed}
    import copy
    probes=[('one',42,{}),('multiple',84,{'residents':3}),
            ('weather',42,{'weather_id':'USA_AK_Anchorage-Merrill.Field.702735_TMY3'}),
            ('state',42,{'state':'CA'}),('location',42,{'latitude':61.21,'longitude':-149.85,'time_zone_utc_offset':-9}),
            ('sparse',42,{'installed':{k:False for k in installed}}),('zero',42,{'residents':0}),
            ('different_seed',0,{'year':2009,'residents':2})]
    result=[]
    for key,seed,overrides in probes:
        inputs=copy.deepcopy(base);inputs.update(overrides)
        weather=resources.get('weather',inputs['weather_id'])
        result.append({'case_id':key,'unit_seed':seed,'inputs':inputs,'drybulb_C':weather['drybulb_C']})
    return result

def load_residential_reference():
    lock=_read(ROOT/'sources/schedule-generator-residential-reference-lock.json')
    data=_verify(ROOT/lock['vectors']['source_path'],lock['vectors'])
    result=strict_json(data,'residential-reference')
    if result['provenance']!=lock['capture_provenance']:
        raise GeneratorError('source_integrity','residential-reference','Capture provenance mismatch')
    return result


def event_capture_inputs(resources):
    import copy
    probes=residential_capture_inputs(resources)
    result=[item for item in probes if item['case_id'] in ('one','multiple','sparse','zero')]
    for slot in ('dishwasher','clothes_washer','clothes_dryer','cooking_range'):
        item=copy.deepcopy(result[0]);item['case_id']='without_'+slot
        item['inputs']['installed'][slot]=False;result.append(item)
    for case in resources.get('reference','m1-scope')['cases']:
        program=resources.get('program',case['program_id'])
        if 'configuration' not in program:continue
        cfg=program['configuration'];arguments=cfg['arguments']
        # Exact schedule-only HPXML construction in run_residential_profiles.rb.
        # Output omission on a zero-resident skip does not imply appliance absence.
        installed={slot:arguments[argument]!='None' for slot,argument in
                   [('dishwasher','appliance_dishwasher'),('clothes_washer','appliance_clothes_washer'),
                    ('clothes_dryer','appliance_clothes_dryer'),('cooking_range','appliance_cooking_range_oven'),
                    ('ceiling_fan','ceiling_fans')]}
        installed.update({slot:float(arguments[argument])>0 for slot,argument in
                          [('plug_loads_other','misc_plug_loads_other_usage_multiplier'),
                           ('plug_loads_tv','misc_plug_loads_television_usage_multiplier')]})
        installed['garage']=cfg['selected_options']['Geometry Garage']!='None'
        weather_id=cfg['weather']['station_filename'].removesuffix('.epw')
        inputs={'year':2007,'residents':cfg['occupants'],'bedrooms':cfg['bedrooms'],
                'state':cfg['state'],'latitude':cfg['latitude'],'longitude':cfg['longitude'],
                'time_zone_utc_offset':cfg['time_zone_utc_offset'],'weather_id':weather_id,'installed':installed}
        result.append({'case_id':case['configuration_id'],'program_id':case['program_id'],
                       'configuration_provenance':program['configuration_provenance'],
                       'unit_seed':cfg['seed'],'inputs':inputs,
                       'drybulb_C':resources.get('weather',weather_id)['drybulb_C']})
    for key,runs in [('component_no_events',[[35040,6]]),
                     ('component_boundary',[[1,1],[1,2],[1,3],[1,4],[35031,6],[1,1],[1,2],[1,3],[1,4],[1,6]]),
                     ('component_all_absent',[[35040,5]])]:
        item=copy.deepcopy(result[0]);item['case_id']=key;item['component_states']=[runs];result.append(item)
    return result


def load_event_reference():
    lock=_read(ROOT/'sources/schedule-generator-event-reference-lock.json')
    result=strict_json(_verify(ROOT/lock['vectors']['source_path'],lock['vectors']),'event-reference')
    if result['provenance']!=lock['capture_provenance']:
        raise GeneratorError('source_integrity','event-reference','Capture provenance mismatch')
    return result

def capture_residential(runtime_archive, resstock_archive, destination, events=False):
    lock=_read(ROOT/'sources/runtime-lock.json')['archives'];destination=Path(destination)
    if destination.exists():raise GeneratorError('source_integrity',str(destination),'Capture destination must be new')
    _verify(runtime_archive,lock[0]);_verify(resstock_archive,lock[1]);destination.mkdir(parents=True)
    selected=[lock[0]['root']+'/'+part for part in ('bin/','Ruby/','lib/','LICENSE.md','copyright.txt')]
    runtime=extract_verified(runtime_archive,lock[0]['sha256'],destination/'runtime',include=selected)
    source_selected=[lock[1]['root']+'/resources/hpxml-measures/'+part for part in
                     ('BuildResidentialScheduleFile/','HPXMLtoOpenStudio/resources/')]+[lock[1]['root']+'/LICENSE.md']
    # Strip only the archive root in this fresh extraction to stay within Windows paths.
    source=(ROOT/'build'/('rs-'+hashlib.sha256(str(destination.resolve()).encode()).hexdigest()[:12])).resolve()
    if source.exists():raise GeneratorError('source_integrity',str(source),'Source extraction must be new')
    source.mkdir()
    with tarfile.open(resstock_archive) as archive:
        for member in archive.getmembers():
            safe_path(member.name.rstrip('/'))
            if not (member.isfile() or member.isdir()):
                raise GeneratorError('source_integrity',member.name,'Non-regular archive member')
            if not any(member.name==p.rstrip('/') or member.name.startswith(p.rstrip('/')+'/') for p in source_selected):continue
            target=source/member.name.split('/',1)[1]
            if not target.resolve().is_relative_to(source):raise GeneratorError('source_integrity',member.name,'Unsafe source target')
            if member.isdir():_long_path(target).mkdir(parents=True,exist_ok=True)
            else:
                _long_path(target.parent).mkdir(parents=True,exist_ok=True);_long_path(target).write_bytes(archive.extractfile(member).read())
    executable=runtime/lock[0]['root']/'bin/openstudio.exe'
    manifest=_read(ROOT/'atlas_schedules/data/manifest.json');resources=ResourceSet.load(manifest['resource_set_id'])
    receipts=[dict(e,provenance=resources.get(e['kind'],e['key']).get('provenance')) for e in manifest['resources']
              if e['kind']=='residential' or e['kind']=='weather']
    # Verify executed Ruby resource files against the packaged locked source records.
    for e in receipts:
        if e['kind']!='residential':continue
        receipt=e['provenance']
        if receipt.get('source_id')!='resstock':continue
        path=source/receipt['source_path'].split('/',1)[1]
        if hashlib.sha256(_long_path(path).read_bytes()).hexdigest()!=receipt['source_sha256']:
            raise GeneratorError('source_integrity',str(path),'Executed resource mismatch')
    inputs=event_capture_inputs(resources) if events else residential_capture_inputs(resources)
    input_path=(destination/'input.json').resolve()
    input_path.write_bytes(canonical(inputs));harness=ROOT/'scripts/reference_schedule_generator.rb'
    output=(destination/'ruby-output.json').resolve()
    completed=subprocess.run([str(executable.resolve()),str(harness),'--events' if events else '--residential',str(source.resolve()),str(input_path),str(output)],
                             cwd=ROOT,capture_output=True,text=True,check=False,
                             env=dict(os.environ,TZ='UTC') if events else None)
    (destination/'execution.log').write_text(completed.stdout+completed.stderr,encoding='utf-8')
    completed.check_returncode()
    capture=_read(output)
    if not capture['ruby_description'].startswith('ruby 3.2.2 '):raise GeneratorError('source_integrity','/runtime','Wrong Ruby version')
    provenance={'source_revision':lock[1]['version'],'source_archive_sha256':lock[1]['sha256'],
        'runtime_archive_sha256':lock[0]['sha256'],'runtime_version':lock[0]['version'],
        'executed_openstudio_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
        'harness_sha256':hashlib.sha256(harness.read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),
        'resource_set_id':resources.resource_set_id,'resource_receipts':receipts,
        'runtime_extraction_selection':selected,'source_extraction_selection':source_selected,
        'source_locator':'schedules.rb:simulate_occupant_activities/create_stochastic_schedules/fill_plug_loads_schedule/fill_lighting_schedule; measure.rb:zero resident skip',
        'field_locator':'cases[i].resident_states/decisions/main_state/channels; exact upstream method results',
        'original_unit':'state ID; 15-minute duration; minute offset; dimensionless hourly fraction',
        'original_value':'Independent upstream full-year traces and raw continuous channels retained',
        'transformation':'one-hot matrices encoded as state IDs; Ruby MT packed integer encoded as uint32 words; weather monthly mean C converted to F by source UnitConversions',
        'extraction_date':'2026-10-14','interpretation_note':'Source execution stops at first sink event method, after activity/shape generation. The zero-resident source measure skips generation; its fixture explicitly adapts that skip to zero occupancy only, with no source-generated other loads. No sizing or EnergyPlus. No export rounding.',
        'comparison_policy':_read(ROOT/'sources/schedule-generator-policy.json')}
    result={'schema_version':'1.0.0','ruby_description':capture['ruby_description'],'provenance':provenance,'cases':capture['cases']}
    if events:
        provenance.update(source_locator='schedules.rb:1076-1564; actual generate_* event methods and create_stochastic_schedules:171-197',
            field_locator='cases[i].event_segments/event_draws/final_rng_states/channels; source native method results',
            original_unit='minute-indexed calibration draws; dimensionless hourly fractions; native random draws',
            transformation='Nonzero constant minute runs [start,length,value]; activity states RLE [length,state]; native rand limits represented as range size; source nonfinite normalization retained as null with explicit channel receipt',
            calendar_environment={'TZ':'UTC','variant':'controlled_no_DST_local_standard_calendar',
                'affected_source_calculations':['generate_dishwasher_power_schedule.month','generate_clothes_washer_dryer_power_schedules.month','generate_cooking_power_schedule.month'],
                'interpretation':'Child-process computational calendar control only. Physical lighting/weather timezone inputs unchanged. Uncontrolled host-DST Windows arrays can differ near month edges; old frozen profiles/annual targets unchanged.'},
            interpretation_note='Actual native full-year event methods before budget binding in controlled-no-DST environment. Six exact frozen configuration inputs plus explicit component/presence probes. Controlled component traces replace only returned one-hot states after genuine activity draws; no-event normalization is undefined upstream and is explicitly rejected by Python. EV output excluded with native allocator slot retained. Calibration never substitutes annual magnitudes.')
        for item,case in zip(inputs,result['cases']):
            for key in ('program_id','configuration_provenance','component_states'):
                if key in item:case[key]=item[key]
            packed=[]
            for trace in case.pop('resident_states'):
                runs=[]
                for state in trace:
                    if runs and runs[-1][1]==state:runs[-1][0]+=1
                    else:runs.append([1,state])
                packed.append(runs)
            case['resident_state_runs']=packed
            case.pop('decisions') # Full activity decisions are covered by separate Task 4 capture.
        filename='event-vectors.json';lockname='event-reference-lock.json'
    else:
        filename='residential-vectors.json';lockname='residential-reference-lock.json'
    data=canonical(result);(destination/filename).write_bytes(data)
    candidate={'schema_version':'1.0.0','capture_provenance':provenance,'vectors':{
        'source_path':'data/schedule-generator/'+filename,'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)}}
    (destination/lockname).write_bytes(canonical(candidate))
    print(completed.stdout.strip());return result

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
    parser.add_argument('--family',choices=['foundation','residential','events'],default='foundation')
    parser.add_argument('--runtime-archive',type=Path)
    parser.add_argument('--resstock-archive',type=Path)
    parser.add_argument('--standards-archive',type=Path)
    parser.add_argument('--ruby-source-cache',type=Path)
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args()
    if args.family in ('residential','events'):
        if args.verify_only:
            print('Verified '+args.family+' cases:',len((load_event_reference() if args.family=='events' else load_residential_reference())['cases']))
        else:
            if any(p is None for p in [args.runtime_archive,args.resstock_archive,args.destination]):
                parser.error('Residential capture requires runtime/resstock archives and a new destination')
            capture_residential(args.runtime_archive,args.resstock_archive,args.destination,events=args.family=='events')
        return
    if args.verify_only:
        result=load_reference_vectors();print('Verified independently captured vectors:',len(result['random_vectors']),len(result['rule_vectors']))
    else:
        operands=[args.runtime_archive,args.resstock_archive,args.standards_archive,args.ruby_source_cache,args.destination]
        if any(p is None for p in operands):parser.error('Capture requires every archive, source cache and new destination explicitly')
        capture_reference(*operands)

if __name__=='__main__':main()
