"""Freeze source-bound commercial fixture paths and inspected direct controls."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import jsonschema
from scripts.common import ROOT,load_json,dump_json,load_atlas,stable_id
from scripts.commercial_water_paths import build as water_paths
from scripts.release import verify_release

BASE=ROOT/'data/releases/v0.2.0'
DEFAULT=ROOT/'data/completion-releases/v0.1.0'
LOCK=ROOT/'sources/completion-evidence-lock.json'
POLICY=ROOT/'sources/commercial-completion-policy.json'
PHASES=['loads','thermal_zones','hvac','custom_hvac_tweaks','transfer_air']

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def inactive_control(c):
    return (c['runtime_phases']==PHASES and bool(c['runtime_evidence']) and all(
        s['thermostat'] and s['heating_schedule'] is None and s['cooling_schedule'] is None
        and not s['equipment'] and not s['air_loops'] and not s['ideal_loads'] and not s['zone_mixing']
        and s['zone_spaces']==[s['space']] for s in c['runtime_evidence']))

def evidence_for(packet,row):
    return [packet['evidence'][i] for i in row['evidence_ids']]

def build(data=None,lock_path=LOCK,cache_root=ROOT/'data/raw',policy_path=POLICY):
    data=data or load_atlas(BASE)
    packet=water_paths(data,lock_path,cache_root)
    packet.pop('source_receipts');packet.pop('required_additional_sources')
    policy=load_json(policy_path)
    controls=copy.deepcopy(policy['controls'])
    rows={r['id']:r for r in data['programs']}
    files={e['path']:e for e in load_json(lock_path)['files'] if e['source_id']=='openstudio-standards'}
    for c in controls:
        row=rows[c['record_id']]
        if (row['building_type'],row['template'],row['source_space_type'])!=(c['building_type'],c['template'],c['source_space_type']):
            raise ValueError('Control source record mismatch')
        if row['heating_setpoint_schedule_id'] is not None or row['cooling_setpoint_schedule_id'] is not None or not inactive_control(c):
            raise ValueError('Inactive control contradicted by source or generated phases')
        mapped={n for m in data['mappings'] if m['program_id']==row['id'] for n in m['source_space_names']}
        if mapped!={s['space'] for s in c['runtime_evidence']}:
            raise ValueError('Control space mapping mismatch')
        if any(m['system_id'] is not None for m in data['mappings'] if m['program_id']==row['id']):
            raise ValueError('Control HVAC assignment mismatch')
        path=c['source_locator'].split('#')[0];entry=files[path]
        c['evidence']=[dict(source_locator=c['source_locator'],source_revision=policy['source_revision'],source_file_sha256=entry['sha256'],original_value=c['source_values'],original_unit=c['original_unit'],transformation=c['transformation'],extraction_date=c['extraction_date'],interpretation_note=c['interpretation'])]
        c['execution_receipt_sha256']=policy['execution_receipt_sha256']
    packet['controls']=controls
    packet['interpretation']='Water fixture paths are static extractions from pinned official Ruby/JSON; direct controls are executed pre-sizing source-phase observations at climate 4A. Geometry, represented areas and full-model sizing/simulation remain downstream.'
    packet['release_version']='0.1.0'
    packet['summary']['inactive_direct_control_records']=len(controls)
    for s in packet['schedules']:
        s['normalized_source_rows']=copy.deepcopy(s['source_rows'])
        s['normalization_status']='always_zero' if s['peak_divisor']==0 else 'peak_normalized'
        for r in s['normalized_source_rows']:r['values']=[v/s['peak_divisor'] if s['peak_divisor'] else 0.0 for v in r['values']]
        def schedule(variant,source_rows):
            return dict(id=stable_id('completion_schedule',s['source_name'],variant),source_name=s['source_name']+' ('+variant+')',schedule_type='fraction',units='dimensionless',time_resolution_minutes=60,interpolation='none',rules=[{**{k:r[k] for k in ['day_types','start_date','end_date','type','values']},'source_index':i,'source_units':r['units'],'source_category':r['category']} for i,r in zip(s['source_order'],source_rows)])
        s['source_schedule']=schedule('source draw fractions',s['source_rows'])
        s['equivalent_schedule']=schedule('peak normalized draw',s['normalized_source_rows'])
    schedules={s['source_name']:s for s in packet['schedules']}
    for d in packet['draw_paths']:
        s=schedules[d['source_schedule_name']]
        d['equivalent_schedule_id']=s['equivalent_schedule']['id']
        d['equivalent_peak_flow_m3_s']=None if d['rated_flow_m3_s'] is None else d['rated_flow_m3_s']*s['peak_divisor']
        d['equivalent_peak_flow_per_area_m3_s_m2']=None if d['rated_flow_per_area_m3_s_m2'] is None else d['rated_flow_per_area_m3_s_m2']*s['peak_divisor']
        d['evidence'] += s['evidence']
        d['interpretation_note']=d.get('interpretation_note','')+' Mixed fixture draw, not heater energy/circulation. Apply each source fixture once; represented area and multiplier once. Unallocated services are not copied to programs.'
    # Normalized evidence table prevents replicating prototype inputs into every draw/gap.
    evidence={}
    def compact(value):
        if isinstance(value,dict):
            for key in list(value):
                if key=='evidence':
                    ids=[]
                    for e in value.pop(key):
                        i=stable_id('completion_evidence',e);evidence[i]=e;ids.append(i)
                    value['evidence_ids']=ids
                else:compact(value[key])
        elif isinstance(value,list):
            for v in value:compact(v)
    compact(packet);packet['evidence']=dict(sorted(evidence.items()))
    validate_packet(packet)
    return packet

def validate_packet(packet):
    def references(value):
        if isinstance(value,dict):
            for key,v in value.items():
                if key=='evidence_ids':
                    if not v or any(i not in packet['evidence'] for i in v):raise ValueError('Orphan field evidence')
                elif key!='evidence':references(v)
        elif isinstance(value,list):
            for v in value:references(v)
    references(packet)
    ids=[d['path_id'] for d in packet['draw_paths']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate fixture path')
    schedules={s['source_name']:s for s in packet['schedules']}
    for d in packet['draw_paths']:
        weights=d['allocation_weights']
        if (set(weights)!=set(d['beneficiary_program_ids']) or (weights and not math.isclose(sum(weights.values()),1))
                or any(w<0 or not math.isfinite(w) for w in weights.values())):
            raise ValueError('Invalid or nonconserving allocation')
        if d['allocation_status']=='building_service_unallocated' and weights:raise ValueError('Unallocated service assigned')
        s=schedules[d['source_schedule_name']]
        for a,b in zip(s['source_rows'],s['normalized_source_rows']):
            if len(a['values'])!=len(b['values']) or len(a['values']) not in {1,24}:raise ValueError('Invalid draw schedule dimensions')
            if {k:v for k,v in a.items() if k!='values'}!={k:v for k,v in b.items() if k!='values'}:raise ValueError('Schedule selectors changed')
            for x,y in zip(a['values'],b['values']):
                if not math.isfinite(y) or not 0<=y<=1 or not math.isclose(x,y*s['peak_divisor'],abs_tol=1e-12):raise ValueError('Draw conservation failed')
        for source,equivalent in [('rated_flow_m3_s','equivalent_peak_flow_m3_s'),('rated_flow_per_area_m3_s_m2','equivalent_peak_flow_per_area_m3_s_m2')]:
            q=d[source]
            if q is not None and (not math.isfinite(q) or q<0 or not math.isclose(q*s['peak_divisor'],d[equivalent],abs_tol=1e-16)):raise ValueError('Flow conservation failed')
    for g in packet['missing_program_evidence']:
        if g['zero_schedule_eligible'] and g.get('building_service_paths'):raise ValueError('Shared service blocks complete water zero')
    for c in packet['controls']:
        if not inactive_control(c):raise ValueError('Control evidence is active/incomplete')

def validate_bundle(path=DEFAULT):
    path=Path(path);m=load_json(path/'manifest.json')
    if verify_release(BASE) or sha(BASE/'manifest.json')!=m['base_manifest_sha256']:raise ValueError('Completion base mismatch')
    if {p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()}!=set(m['files'])|{'manifest.json'}:raise ValueError('Completion inventory mismatch')
    for n,e in m['files'].items():
        p=(path/n).resolve()
        if not p.is_relative_to(path.resolve()) or sha(p)!=e['sha256'] or p.stat().st_size!=e['size_bytes']:raise ValueError('Completion checksum/path mismatch')
    packet=load_json(path/'commercial-completion.json')
    jsonschema.validate(packet,load_json(path/'schemas/commercial-completion.schema.json'))
    policy=load_json(path/'sources/commercial-completion-policy.json')
    if policy['execution_receipt_sha256']!=sha(path/'sources/commercial-control-receipt.json'):raise ValueError('Control receipt mismatch')
    receipt=load_json(path/'sources/commercial-control-receipt.json')
    if receipt['inspection_script_sha256']!=sha(path/'scripts/inspect_commercial_controls.rb'):raise ValueError('Inspection script mismatch')
    for c in policy['controls']:
        case=next(r for r in receipt['cases'] if (r['building_type'],r['template'])==(c['building_type'],c['template']))
        if case['errors'] or case['phases']!=c['runtime_phases'] or c['runtime_evidence']!=[s for s in case['spaces'] if s['source_space_type']==c['source_space_type']]:raise ValueError('Control witness mismatch')
    if packet!=build(lock_path=path/'sources/completion-evidence-lock.json',policy_path=path/'sources/commercial-completion-policy.json'):raise ValueError('Completion source reproduction mismatch')
    if m['summary']!=packet['summary']:raise ValueError('Completion summary mismatch')
    return packet

def freeze(target=DEFAULT):
    target=Path(target)
    if target.exists():raise ValueError('Never overwrite a frozen completion release')
    packet=build();jsonschema.validate(packet,load_json(ROOT/'schemas/commercial-completion.schema.json'))
    dump_json(target/'commercial-completion.json',packet)
    for n in ['schemas/commercial-completion.schema.json','sources/completion-evidence-lock.json','sources/commercial-completion-policy.json','sources/commercial-control-receipt.json','sources/commercial-runtime-lock.json','sources/licenses/openstudio-standards.txt','scripts/commercial_completion.py','scripts/commercial_water_paths.py','scripts/inspect_commercial_controls.rb','docs/adr/0008-reviewed-schedule-completion.md','LICENSE']:
        p=target/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,p)
    dump_json(target/'manifest.json',dict(release_version='0.1.0',schema_version='0.1.0',base_release='v0.2.0',base_manifest_sha256=sha(BASE/'manifest.json'),generation_date='2026-10-04',summary=packet['summary'],files={p.relative_to(target).as_posix():dict(sha256=sha(p),size_bytes=p.stat().st_size) for p in sorted(target.rglob('*')) if p.is_file()}))
    validate_bundle(target)
    return packet

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true');p.add_argument('--target',type=Path,default=DEFAULT)
    p.add_argument('--inspect-controls',action='store_true');p.add_argument('--openstudio',type=Path);a=p.parse_args()
    if a.inspect_controls:
        from scripts.runtime import fetch_runtime
        expected='46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361'
        if not a.openstudio or sha(a.openstudio)!=expected:raise ValueError('Use the locked OpenStudio 3.10.0 Windows executable')
        source=fetch_runtime(load_json(ROOT/'sources/commercial-runtime-lock.json'),ROOT/'build/commercial-runtime')['standards-controls']
        out=ROOT/'build/reproduced-commercial-controls.json'
        subprocess.run([str(a.openstudio.resolve()),'execute_ruby_script',str(ROOT/'scripts/inspect_commercial_controls.rb'),str(source),str(out)],check=True)
        if load_json(out)!=load_json(ROOT/'sources/commercial-control-receipt.json')['cases']:raise ValueError('Generated control phases do not reproduce')
        print('Eight locked source-phase cases reproduced');return
    packet=validate_bundle(a.target) if a.verify else freeze(a.target)
    print(json.dumps(packet['summary'],indent=2))
if __name__=='__main__':main()
