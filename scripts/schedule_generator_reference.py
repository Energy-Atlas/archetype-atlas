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

def capture_residential(runtime_archive, resstock_archive, destination, events=False, resources=None):
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
    if resources is None:
        manifest=_read(ROOT/'atlas_schedules/data/manifest.json');resources=ResourceSet.load(manifest['resource_set_id'])
    manifest=resources.manifest
    receipts=[dict(e,provenance=resources.get(e['kind'],e['key']).get('provenance')) for e in manifest['resources']
              if e['kind']=='residential' or e['kind']=='weather']
    # Verify executed Ruby resource files against the packaged locked source records.
    for e in receipts:
        if e['kind']!='residential':continue
        receipt=e['provenance'] or {}
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


def load_commercial_reference():
    lock = _read(ROOT/'sources/schedule-generator-commercial-reference-lock.json')
    result = strict_json(_verify(ROOT/lock['vectors']['source_path'], lock['vectors']), 'commercial-reference')
    if result['provenance'] != lock['capture_provenance']:
        raise GeneratorError('source_integrity', 'commercial-reference', 'Capture provenance mismatch')
    return result


def commercial_capture_inputs(resources):
    """Controlled reference probes, never caller defaults or population records."""
    import copy
    from atlas_schedules.commercial.sampling import sample_operating_parameters
    schedules = {slot: resources.get('reference', key)['definition'] for slot, key in {
        'occupancy': 'schedule-db120b43964b8b666cd8', 'lighting': 'schedule-4f028eec18f19916e7d2',
        'electric_equipment': 'schedule-4082e09c5f9727640add', 'activity': 'schedule-904d44133907f0dbfbbe',
        'heating_setpoint': 'schedule-7c3bd1014eed8de1237a', 'cooling_setpoint': 'schedule-e1ba079905225f741119',
        'hot_water_volume': 'schedule-1a7eda5cfd8f681cc7d7'}.items()}
    context = {'year': 2007, 'holidays': [], 'steps_per_hour': 6,
        'configuration_id': 'medium_office_90_1_2013', 'standards_version': '0.8.6',
        'slot_modes': {slot: 'tstat' if slot.endswith('setpoint') else 'hours' for slot in schedules},
        'occupancy_aggregation': {'policy': 'explicit_single_nonresidential_reference_carrier',
            'constituents': [{'schedule': schedules['occupancy'], 'nominal_people': 1.0, 'residential': False,
                              'evidence': resources.get('reference', 'schedule-db120b43964b8b666cd8')['provenance']}],
            'interpretation': 'Normalized inference carrier, no area/geometry or actual building nominal count; weighted inputs rounded to six decimals before threshold'},
        'occupancy_adjustment': {'peak_occ_frac': .231, 'source_key': 'comstock__resources__options_lookup_tsv',
            'source_options': ['baseline_hvac_sizing=autosize', 'baseline_hvac_sizing=hardsize'],
            'interpretation': 'Both inspected sizing options set this schedule multiplier; sizing is not executed or inferred'},
        'source_clock': {'TZ': 'UTC', 'variant': 'controlled_no_DST_local_standard_calendar'}}
    operation = sample_operating_parameters({'building_type': 'medium_office'}, 42, resources)
    result = []
    for key, start, duration, weekend_start, weekend_duration in [
        ('native',8,10,8,4), ('short',9,6,10,2), ('long',5,18,6,14),
        ('overnight',22,8,23,7), ('zero',8,0,8,0), ('full_day',0,24,0,24),
        ('weekday_weekend',7.25,9.75,10.5,3.5)]:
        item = {'case_id': key, 'source_context': copy.deepcopy(context), 'schedules': copy.deepcopy(schedules),
                'operating': copy.deepcopy(operation)}
        for parameter, hours in zip(('weekday_start_time','weekday_duration','weekend_start_time','weekend_duration'),
                                    (start,duration,weekend_start,weekend_duration)):
            item['operating']['effective_values'][parameter] = {'value': hours*3600, 'unit': 's', 'modify': True}
        item['operating']['controlled_probe'] = {'interpretation': 'Explicit reference-only operating cases, not sampled population options',
                                               'start_duration_hours': [start,duration,weekend_start,weekend_duration]}
        result.append(item)
    for weight in (.1,100):
        item = copy.deepcopy(result[0]); item['case_id'] = 'carrier_weight_'+str(weight)
        item['source_context']['occupancy_aggregation']['constituents'][0]['nominal_people'] = weight
        result.append(item)
    item = copy.deepcopy(result[0]); item['case_id'] = 'constant_ramp_design'
    for slot, values in [('activity',[120.0]),('lighting',[.1]*6+[.2,.4,.6,.8,1,.8,.6,.4,.2]+[.1]*9)]:
        source = item['schedules'][slot]
        for rule in source['rules']:
            if rule['day_types'] not in ('WntrDsn','SmrDsn'):
                rule['values'] = values; rule['type'] = 'Constant' if len(values)==1 else 'Hourly'
    result.append(item)
    item = copy.deepcopy(result[0]); item['case_id'] = 'sampled_42'; item['operating'] = operation
    result.append(item)
    return result


def capture_commercial(runtime_archive, destination):
    """Locked native source-method probes, independent of Python transform."""
    import ast
    import copy
    import io
    import pandas as pd
    from warnings import warn
    destination = Path(destination)
    if destination.exists():
        raise GeneratorError('source_integrity', str(destination), 'Capture destination must be new')
    runtime_lock = _read(ROOT/'sources/runtime-lock.json')['archives'][0]
    _verify(runtime_archive, runtime_lock)
    lock = _read(ROOT/'sources/schedule-generator-lock.json')
    gem_receipt = next(a for a in lock['archives'] if a['format']=='gem')
    gem = _verify(ROOT/'data/raw'/gem_receipt['cache_path'], gem_receipt)
    destination.mkdir(parents=True)
    selected = [runtime_lock['root']+'/'+p for p in ('bin/','Ruby/','lib/','LICENSE.md','copyright.txt')]
    runtime = extract_verified(runtime_archive, runtime_lock['sha256'], destination/'runtime', include=selected)
    executable = runtime/runtime_lock['root']/'bin/openstudio.exe'
    source = destination/'source'; source.mkdir()
    with tarfile.open(fileobj=io.BytesIO(gem)) as outer:
        with tarfile.open(fileobj=io.BytesIO(outer.extractfile('data.tar.gz').read())) as archive:
            for receipt in gem_receipt['members']:
                if receipt['format'] != 'text' or not receipt['path'].endswith('.rb'): continue
                data = archive.extractfile(receipt['path']).read()
                if hashlib.sha256(data).hexdigest() != receipt['sha256']:
                    raise GeneratorError('source_integrity',receipt['path'],'Gem member differs')
                name = Path(receipt['path']).name
                target = source/('schedules/'+name if '/schedules/' in receipt['path'] else name)
                target.parent.mkdir(exist_ok=True); target.write_bytes(data)
    manifest = _read(ROOT/'atlas_schedules/data/manifest.json')
    resources = ResourceSet.load(manifest['resource_set_id'])
    receipts = []
    for entry in manifest['resources']:
        if entry['kind'] != 'reference' or not entry['key'].startswith('comstock__resources__measures'): continue
        record = resources.get('reference',entry['key'])
        receipts.append(record['provenance'])
        name = record['provenance']['source_path'].split('/')[-2]+'.rb'
        (source/name).write_text(record['text'],encoding='utf-8',newline='')
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=record['provenance']['source_sha256']:
            raise GeneratorError('source_integrity',entry['key'],'Executed measure differs from locked text')
    old_standard = next(r for r in _read(_LOCK)['algorithm_sources'] if r['source_id']=='openstudio-standards')
    frozen_source = ROOT/'data/raw/openstudio-standards/lib/openstudio-standards/standards/Standards.Model.rb'
    (source/'Standards.Model.rb').write_bytes(_verify(frozen_source,old_standard))
    inputs = commercial_capture_inputs(resources)
    input_path = destination/'input.json'; input_path.write_bytes(canonical(inputs))
    harness = ROOT/'scripts/reference_commercial.rb'; output = destination/'native-output.json'
    completed = subprocess.run([str(executable.resolve()),str(harness),str(source.resolve()),str(input_path.resolve()),str(output.resolve())],
                               cwd=ROOT,capture_output=True,text=True,env=dict(os.environ,TZ='UTC'))
    (destination/'execution.log').write_text(completed.stdout+completed.stderr,encoding='utf-8')
    completed.check_returncode()
    capture = _read(output)
    # Execute only the actual pinned conditional method, with stored uniforms.
    sampler = resources.get('reference','comstock__sampling__tsv_sampling_py')
    tree = ast.parse(sampler['text'])
    method = next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_com_execute_samples')
    method.decorator_list=[]
    module = ast.Module(body=[method],type_ignores=[]); ast.fix_missing_locations(module)
    namespace = {'deepcopy':copy.deepcopy,'warn':warn}
    exec(compile(module,sampler['provenance']['source_path'],'exec'),namespace)
    audit = resources.get('commercial','sampling-audit'); order = audit['selected_parameter_order']
    tables = {}; dependencies = {}
    import zipfile
    tsv_receipt = lock['archives'][0]
    tsv_content=_verify(ROOT/'data/raw'/tsv_receipt['cache_path'],tsv_receipt)
    with zipfile.ZipFile(io.BytesIO(tsv_content)) as archive:
        for parameter in order:
            tables[parameter] = pd.read_csv(io.BytesIO(archive.read('tsvs-v33/'+parameter+'.tsv')),sep='\t',dtype=str,keep_default_na=False)
            dependencies[parameter] = resources.get('commercial',parameter)['dependencies']
    dependencies['building_type'] = []
    draws = [.1,.7,.2,.8,.3,.4,.5,.6,.7,.8]
    native = namespace['_com_execute_samples'](tables,dependencies,['building_type']+order,{0:draws},{0:{'building_type':'medium_office'}})[0]
    rows = []; selectors={'building_type':'medium_office'}
    for parameter,draw in zip(order,draws):
        table=resources.get('commercial',parameter)
        row=next(r for r in table['rows'] if all(r['selectors'][d]==selectors[d] for d in table['dependencies']))
        rows.append({'parameter':parameter,'selectors':{d:selectors[d] for d in table['dependencies']},
                     'uniform':draw,'source_row':row['source_row'],'selected_option':native[parameter]})
        selectors[parameter]=native[parameter]
    provenance = {'runtime_archive_sha256':runtime_lock['sha256'],'runtime_version':runtime_lock['version'],
        'executed_openstudio_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
        'gem_sha256':gem_receipt['sha256'],'gem_version':'0.8.6','gem_members':gem_receipt['members'],
        'measure_receipts':receipts,'frozen_definition_builder':old_standard,
        'harness_sha256':hashlib.sha256(harness.read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),
        'sampler_method_receipt':sampler['provenance'],'pandas_version':pd.__version__,
        'tsv_archive_receipt':{k:tsv_receipt[k] for k in ('source_id','source_revision','url','sha256','size_bytes')},
        'source_locator':'parametric.rb:model_infer_hours_of_operation_building/schedule_ruleset_get_parametric_inputs/schedule_ruleset_apply_parametric_inputs; space.rb:spaces_get_occupancy_schedule/space_hours_of_operation; ComStock:set_sch_bpr/schedule_ruleset_simple_value_adjust; tsv_sampling.py:_com_execute_samples',
        'field_locator':'cases[].inference/setup/pre_adjustment/final/channels/special_profiles; conditional_vectors[]',
        'original_value':'Actual native profiles, formula strings, rule indices, legacy round5 hourly channels and source discrete options',
        'original_unit':'source fractional schedules, degrees C, W/person, source hours and unnormalized probabilities',
        'transformation':'Native output retained before annual-load budget binding; no Python commercial transformation used. Capture-only exact-content daily-getter memoization; native annual/inference/transform callers unchanged; cached vs uncached full8760 occupancy getter equality asserted.',
        'extraction_date':'2026-10-14','calendar_environment':{'TZ':'UTC','variant':'controlled_no_DST_local_standard_calendar',
            'interpretation':'No elapsed Time arithmetic in selected commercial numerical methods; Time.now only administrative properties omitted. Native Date uses explicit Gregorian year.'},
        'interpretation_note':'Single normalized nonresidential occupancy carrier is an explicit experimental adaptation, not actual building geometry/population. Positive weights .1/1/100 tested only; source round6 prevents arbitrary cancellation. All original frozen schedules and annual targets unchanged. Native Standards0.8.6 methods distinct from frozen Standardsdevelop schedule definitions. Source model timestep6; lexical3.10.0<3.8.0 takes legacy minimum-interval queries and round5. getValue snaps queries forward to timestep endpoints; addValue IDF double storage15 significant digits captured independently, including occupancy multiplication and negative values. Original and changed/interpolated complete8760 cached/uncached getter equality asserted.',
        'population_realization_equivalent':False}
    result={'schema_version':'1.0.0','ruby_description':capture['ruby_description'],'provenance':provenance,
            'conditional_vectors':rows,'cases':capture['cases']}
    data=canonical(result); (destination/'commercial-vectors.json').write_bytes(data)
    candidate={'schema_version':'1.0.0','capture_provenance':provenance,'vectors':{
        'source_path':'data/schedule-generator/commercial-vectors.json','sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)}}
    (destination/'commercial-reference-lock.json').write_bytes(canonical(candidate))
    print(completed.stdout.strip()); return result

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
    parser.add_argument('--family',choices=['foundation','residential','events','commercial'],default='foundation')
    parser.add_argument('--runtime-archive',type=Path)
    parser.add_argument('--resstock-archive',type=Path)
    parser.add_argument('--standards-archive',type=Path)
    parser.add_argument('--ruby-source-cache',type=Path)
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--resources-root',type=Path)
    args=parser.parse_args()
    if args.family=='commercial':
        if args.verify_only:
            result=load_commercial_reference();print('Verified commercial cases:',len(result['cases']),len(result['conditional_vectors']))
        else:
            if args.runtime_archive is None or args.destination is None:
                parser.error('Commercial capture requires runtime archive and a new destination')
            capture_commercial(args.runtime_archive,args.destination)
        return
    if args.family in ('residential','events'):
        if args.verify_only:
            print('Verified '+args.family+' cases:',len((load_event_reference() if args.family=='events' else load_residential_reference())['cases']))
        else:
            if any(p is None for p in [args.runtime_archive,args.resstock_archive,args.destination]):
                parser.error('Residential capture requires runtime/resstock archives and a new destination')
            resources = None
            if args.resources_root is not None:
                manifest = _read(args.resources_root/'manifest.json')
                resources = ResourceSet(args.resources_root, manifest['resource_set_id'])
            capture_residential(args.runtime_archive,args.resstock_archive,args.destination,
                                events=args.family=='events',resources=resources)
        return
    if args.verify_only:
        result=load_reference_vectors();print('Verified independently captured vectors:',len(result['random_vectors']),len(result['rule_vectors']))
    else:
        operands=[args.runtime_archive,args.resstock_archive,args.standards_archive,args.ruby_source_cache,args.destination]
        if any(p is None for p in operands):parser.error('Capture requires every archive, source cache and new destination explicitly')
        capture_reference(*operands)

if __name__=='__main__':main()
