"""Explicit, checksum-locked native foundation recovery; never run during export.

python -m scripts.recover_construction_foundations --recover
python -m scripts.recover_construction_foundations --check
"""
import argparse
import copy
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scripts.common import ROOT,load_json,dump_json
from scripts.construction_foundation_recovery import DATE,sha,build_census
from scripts.construction_foundation_native import (group_commercial_cases,normalize_foundation_execution,
    validate_achieved_factors,initial_temperature_C,validate_execution)
from scripts.recover_construction_geometry import prepare_sources,canonical_derived
from scripts.recover_program_inputs import RUNTIME,SOURCE

WORK=ROOT/'build/foundation-recovery'
OUTPUT=ROOT/'data/construction-inputs/foundation-execution-v1.json'
LOCK=ROOT/'sources/foundation-ground-source-lock.json'


def invoke(script,args,name):
    paths=[ROOT/'scripts'/script,*args]
    input_digest={str(p.relative_to(ROOT)):sha(p) for p in [paths[0],*args[:2],*args[3:]] if p.is_file()}
    input_digest['runtime']=sha(RUNTIME)
    marker=WORK/(name+'.receipt.json')
    output=WORK/(name+'.json')
    if marker.exists() and output.exists():
        receipt=load_json(marker)
        if receipt['input_sha256']==input_digest and receipt['output_sha256']==sha(output):
            return load_json(output)
    with (WORK/(name+'.log')).open('w',encoding='utf-8') as stream:
        subprocess.run([str(RUNTIME),str(paths[0]),*[str(p) for p in args]],
            cwd=ROOT,check=True,timeout=1800,stdout=stream,stderr=subprocess.STDOUT)
    dump_json(marker,{'input_sha256':input_digest,'output_sha256':sha(output)})
    return load_json(output)


def recover():
    WORK.mkdir(parents=True,exist_ok=True)
    source,receipts,runtime=prepare_sources()
    census=build_census()
    geometry=load_json(ROOT/'data/construction-inputs/geometry-v1.json')
    references={r['id']:r for r in geometry['commercial']}
    cases=sorted({(v['reference_id'],v['climate_zone']) for v in census['contexts'].values() if v['candidate_elements']})
    queries=[]
    rows=[{'template':ref.split('/')[0],'building_type':ref.split('/')[1],
           'climate_zone':climate,'recovery_mode':'query_inventory',
           'source_queries':[q['query'] for q in references[ref]['queries']]} for ref,climate in cases]
    # Bounded batches avoid quadratic JSON writes and provide recovery checkpoints.
    for i in range(0,len(rows),100):
        name=f'queries-{i//100:03}'
        input_file=WORK/(name+'-input.json');dump_json(input_file,rows[i:i+100])
        data=invoke('recover_commercial_foundations.rb',[source,input_file,WORK/(name+'.json')],name)
        for row in data['results']:
            if 'geometry_caller' in row:
                row['geometry_caller'][0]=Path(row['geometry_caller'][0]).relative_to(source).as_posix()
            queries.append(row)
        print(f'Source ground queries {min(i+100,len(rows))}/{len(rows)}',flush=True)
    groups=group_commercial_cases(queries)
    representatives=[]
    for identity,g in sorted(groups.items()):
        r=g['representative'];ref=r['template']+'/'+r['building_type']
        representatives.append({'case_id':identity,'template':r['template'],'building_type':r['building_type'],
            'climate_zone':r['climate_zone'],'recovery_mode':'ground_phases',
            'source_queries':[q['query'] for q in references[ref]['queries']]})
    commercial={}
    def recover_batch(i):
        name=f'native-{i//20:03}'
        input_file=WORK/(name+'-input.json');dump_json(input_file,representatives[i:i+20])
        data=invoke('recover_commercial_foundations.rb',[source,input_file,WORK/(name+'.json')],name)
        for row in data['results']:
            if row['status']!='recovered':raise ValueError('Source recovery blocker: '+json.dumps(row))
        return data['results']
    # Independent process/model state and distinct checkpoint files per batch.
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(recover_batch,i) for i in range(0,len(representatives),20)]
        for future in as_completed(futures):
            for row in future.result():commercial[row['case_id']]=row
            print(f'Native ground cases {len(commercial)}/{len(representatives)}',flush=True)
    source_rows=load_json(ROOT/'data/releases/v0.2.0/residential_archetypes.json')
    options={r['id']:r for r in load_json(ROOT/'data/releases/v0.2.0/residential_options.json')}
    res_inputs=[{'record_id':r['id'],'arguments':{k:v for oid in r['option_ids'] for k,v in options[oid]['arguments'].items()}} for r in source_rows]
    res_input=WORK/'residential-input.json';dump_json(res_input,res_inputs)
    residential=invoke('recover_residential_foundations.rb',[SOURCE,res_input,WORK/'residential-native.json',
        ROOT/'build/geometry-recovery/register-value.rb',ROOT/'build/geometry-recovery/post-hpxml.rb',
        ROOT/'scripts/recover_construction_geometry.rb',ROOT/'scripts/recover_residential_assemblies.rb'],'residential-native')
    # Source archive hashes pin omitted dependencies; retain explicit code/geometry receipts.
    used_geometry={r['geometry_file'] for r in commercial.values()}
    selected={k:v for k,v in receipts.items() if k.endswith(('.rb','.json')) or k.removeprefix('standards/') in used_geometry}
    lock={'schema_version':'1.0.0','extraction_date':DATE,'runtime':runtime,'source_files':selected}
    dump_json(LOCK,lock)
    context_cases={}
    for identity,g in groups.items():
        r=g['representative']
        for climate in g['contexts']:context_cases[r['template']+'/'+r['building_type']+'/'+climate]=identity
    # Normalize paths and computed geometry only, retaining literal material/factor precision.
    normalized={}
    for identity,row in sorted(commercial.items()):
        row=copy.deepcopy(row)
        row['caller'][0]=Path(row['caller'][0]).relative_to(source).as_posix()
        row['source_context_climates']=groups[identity]['contexts']
        for face in row['surfaces']:
            face['vertices']=canonical_derived(face['vertices'])
            face['area_m2']=canonical_derived(face['area_m2'])
        normalized[identity]=normalize_foundation_execution(row,{'lock':LOCK.relative_to(ROOT).as_posix(),
            'source_project':'OpenStudio Standards','source_revision':'c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907','source_locator':row['geometry_file']})
        validate_achieved_factors(normalized[identity],groups[identity]['representative']['physics_signature'])
    res={}
    for row in residential['results']:
        for kiva in row['kiva']:
            spec=kiva['initialization']
            for p in spec['numerical_verification']:
                result=initial_temperature_C(spec,p['outdoor_C'],p['ground_C'],p['heat_C'],p['cool_C'],p['controls'])
                if not abs(result-p['result_C'])<1e-10:raise ValueError('Kiva initialization source verification failed')
        for capture in row['captures']:
            for caller in capture['recipe']['caller_locations']:
                caller['path']=Path(caller['path']).relative_to(SOURCE).as_posix()
        res[row['record_id']]=normalize_foundation_execution(row,{'lock':LOCK.relative_to(ROOT).as_posix(),
            'source_project':'ResStock','source_revision':'dd25369f41a83a0767aefeeac0b6f8a0b0edd649','source_locator':'HPXML/source_fixture/'+row['record_id']})
    paths=[ROOT/'scripts'/p for p in ('recover_commercial_foundations.rb','recover_residential_foundations.rb',
        'recover_construction_foundations.py','construction_foundation_native.py')]
    paths += [ROOT/'data/construction-inputs/foundation-source-v1.json',LOCK]
    return {'schema_version':'1.0.0','kind':'internal_foundation_execution','extraction_date':DATE,
        'consumer_selectable':False,'commercial':normalized,'commercial_context_cases':context_cases,
        'commercial_query_groups':groups,'residential':res,
        'input_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in paths},
        'coverage':{'source_query_contexts':len(queries),'native_commercial_cases':len(normalized),'residential_fixtures':len(res)}}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recover',action='store_true');p.add_argument('--check',action='store_true')
    args=p.parse_args()
    if args.check:
        data=load_json(OUTPUT)
        for name,h in data['input_sha256'].items():
            if sha(ROOT/name)!=h:raise ValueError('Changed foundation recovery input: '+name)
        validate_execution(data,load_json(ROOT/'data/construction-inputs/foundation-source-v1.json'))
        print(data['coverage']);return
    if not args.recover:p.error('Native recovery is opt-in: --recover; frozen input verification: --check')
    data=recover();dump_json(OUTPUT,data);print(data['coverage'])


if __name__=='__main__':main()
