"""Opt-in six-cell native EnergyPlus input/numerical smoke; never run by site/export."""
import argparse
import csv
import hashlib
import io
import math
import re
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from scripts.common import ROOT, load_json
from scripts.construction_set_export import encoded
from scripts.construction_foundation_recovery import sha

LOCK=ROOT/'sources/foundation-engine-runtime-lock.json'
RECEIPT=ROOT/'data/construction-inputs/foundation-smoke-v1.json'
WORK=ROOT/'build/foundation-recovery'
WEATHER=ROOT/'build/geometry-recovery/standards/openstudio-standards-c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907/data/weather/USA_TX_El.Paso.Intl.AP.722700_TMY3.epw'
WEATHER_SHA='6ea31e9e6779cc0295ba3bfe8a72300e3aa05ef2926d1e9f6f68853d425a56ca'
ENGINE_SHA='71278a62c9c3871922b3f7ee28a3c7c9f658caa995a934fccb92e8f8965a3977'


def runtime(fetch=False):
    lock=load_json(LOCK);archive=ROOT/lock['archive_path'];out=ROOT/lock['extract_path']
    if not archive.is_file() and fetch:
        archive.parent.mkdir(parents=True,exist_ok=True)
        temporary=archive.with_suffix('.download')
        with urllib.request.urlopen(lock['url']) as source,temporary.open('wb') as target:
            while chunk:=source.read(1024*1024):target.write(chunk)
        if sha(temporary)!=lock['archive_sha256']:raise ValueError('Engine archive checksum mismatch')
        temporary.replace(archive)
    if not archive.is_file():raise ValueError('Pinned engine cache missing; opt in with --fetch-runtime')
    if sha(archive)!=lock['archive_sha256'] or archive.stat().st_size!=lock['archive_bytes']:raise ValueError('Engine archive checksum mismatch')
    executable=out/'EnergyPlus-26.2.0-4bd7a1f26f-Windows-x86_64/energyplus.exe'
    if not executable.is_file():
        with zipfile.ZipFile(archive) as zipped:
            for name in zipped.namelist():
                if not (out/name).resolve().is_relative_to(out.resolve()):raise ValueError('Unsafe runtime archive path')
            zipped.extractall(out)
    if sha(executable)!=ENGINE_SHA:raise ValueError('Engine executable checksum mismatch')
    return executable


def inputs():
    from scripts.construction_foundation_release import pilot_contexts,export_pair
    pilots=pilot_contexts();documents={k:export_pair(v)[0] for k,v in pilots.items()}
    from scripts.construction_foundation_export import session
    source=session().source
    cid=next(c['id'] for c in source['contexts'].values() if c['climate_zone']=='3B' and
             source['construction_sets'][c['construction_set_id']]['source']['building_type']=='Hospital' and
             source['construction_sets'][c['construction_set_id']]['source']['template']=='90.1-2019')
    documents['hospital-2019']=export_pair(cid)[0]
    if sha(WEATHER)!=WEATHER_SHA:raise ValueError('Changed pinned source weather')
    location=WEATHER.read_text(encoding='utf-8-sig').splitlines()[0].split(',')
    site=dict(zip(('latitude','longitude','time_zone','elevation_m'),map(float,location[6:10])))
    def rule(doc,role,model):
        return next(r for r in doc['components'][role]['assignments'] if r.get('ground_method_id') and
                    doc['foundation_ground']['methods'][r['ground_method_id']]['model']==model)
    specs=[('f-factor','medium-office-2019-3B','GroundFloor','FFactor',{'perimeter_m':40}),
           ('f-factor-core','medium-office-2019-3B','GroundFloor','FFactor',{'perimeter_m':0}),
           ('layered-ground','small-data-centre-2019','GroundFloor','LayeredGround',{}),
           ('c-factor','hospital-2019','FoundationWall','CFactor',{}),
           ('kiva-slab','residential-slab','GroundFloor','Kiva',{'initial_temperature_C':23}),
           ('kiva-wall','residential-vented-crawlspace','GroundFloor','Kiva',{'initial_temperature_C':13.55,'walled_kiva':True})]
    rows=[]
    for label,name,role,model,extra in specs:
        doc=documents[name];r=rule(doc,role,model)
        row={'label':label,'document':doc,'ground_rule':r,'closing_document':documents['medium-office-2019-3B'],'weather_site':site,**extra}
        if extra.get('walled_kiva'):row['wall_rule']=rule(doc,'FoundationWall','Kiva')
        rows.append(row)
    return rows


def run(fetch=False):
    from scripts.recover_program_inputs import RUNTIME
    from scripts.recover_construction_geometry import prepare_sources
    prepare_sources() # Verify locked source/runtime caches; native recovery is not rerun.
    engine=runtime(fetch);WORK.mkdir(parents=True,exist_ok=True)
    path=WORK/'smoke-input.json';path.write_bytes(encoded(inputs()))
    script=ROOT/'scripts/experiments/construction_foundation_smoke.rb';out=WORK/'smoke'
    prepared=subprocess.run([str(RUNTIME),str(script),str(path),str(out)],cwd=ROOT,capture_output=True,text=True,timeout=120)
    (WORK/'smoke-prepare.log').write_text(prepared.stdout+prepared.stderr,encoding='utf-8')
    prepared.check_returncode();results=[]
    for row in load_json(path):
        directory=out/row['label'];result=directory/'results'
        process=subprocess.run([str(engine),'-w',str(WEATHER),'-d',str(result),'-r',str(directory/'in.idf')],cwd=ROOT,capture_output=True,text=True,timeout=180)
        error=(result/'eplusout.err').read_text(encoding='utf-8')
        counts={name:len(re.findall(r'\*\* '+text+r' \*\*',error)) for name,text in [('severe','Severe'),('fatal','Fatal'),('warnings','Warning')]}
        values=list(csv.reader(io.StringIO((result/'eplusout.csv').read_text(encoding='utf-8'))))
        samples=[float(v) for r in values[1:] for v in r[1:] if v.strip()]
        if process.returncode or any(counts.values()) or not samples or not all(math.isfinite(v) for v in samples):
            raise ValueError('Native smoke failed: '+row['label']+' '+str(counts))
        results.append({'label':row['label'],'returncode':process.returncode,**counts,'samples':len(values)-1,
                        'finite':True,'range_W':[min(samples),max(samples)]})
    paths=[LOCK,ROOT/'scripts/construction_foundation_smoke.py',script,ROOT/'sources/runtime-lock.json',
           ROOT/'data/construction-inputs/foundation-execution-v1.json',ROOT/'data/construction-inputs/foundation-airflow-v1.json',
           ROOT/'scripts/construction_foundation_export.py']
    return {'schema_version':'1.0.0','kind':'internal_foundation_native_smoke','engine_version':'26.2.0-4bd7a1f26f',
            'engine_sha256':sha(engine),'weather_sha256':sha(WEATHER),'smoke_input_sha256':sha(path),
            'input_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in paths},
            'test_conditions':{'plan_area_m2':100,'height_m':3,'design_day_maximum_C':32,'design_day_range_K':10,
              'ground_monthly_temperature_C':18,'hours':24,'timestep_per_hour':4,
              'initialization_note':'Explicit synthetic smoke temperatures only. Source initialization independently verified against 588 native probes.',
              'closing_faces':'Explicit MediumOffice test closing construction; no public catalogue fallback.'},
            'results':results,'interpretation_note':'Six synthetic method-input/numerical smoke cells with finite conduction output, no warnings/severe/fatal. Not archetype energy validation or a systematic zoning/construction error experiment. Minimal audited 25.1-to-26.2 object subset, not a general importer.'}


def check():
    receipt=load_json(RECEIPT)
    for path,digest in receipt['input_sha256'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed native smoke input: '+path)
    if len(receipt['results'])!=6 or any(any(r[k] for k in ('returncode','warnings','severe','fatal')) or not r['finite'] for r in receipt['results']):raise ValueError('Invalid native smoke receipt')
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--fetch-runtime',action='store_true');args=p.parse_args()
    if args.fetch_runtime and not args.run:p.error('--fetch-runtime requires --run')
    if args.run:RECEIPT.write_bytes(encoded(run(args.fetch_runtime)))
    print('Verified',len(check()['results']),'native EnergyPlus 26.2 smoke cells')


if __name__=='__main__':main()
