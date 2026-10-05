"""Build and verify an additive, evidence-gated schedule resolution supplement."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import re
from pathlib import Path
import shutil

import jsonschema

from scripts.common import ROOT, dump_json, load_atlas, load_json, stable_id
from scripts.release import verify_release
from scripts.residential_profiles import validate_profiles, completed_output

BASE = ROOT/'data/releases/v0.2.0'
DEFAULT = ROOT/'data/resolution-releases/v0.3.0'
LOADS = {'occupancy_schedule_id':'people_per_m2', 'lighting_schedule_id':'lighting_W_m2',
         'electric_equipment_schedule_id':'electric_equipment_W_m2',
         'gas_equipment_schedule_id':'gas_equipment_W_m2'}
ELECTRIC = {'Heating Fuel':{'Electricity','None'}, 'HVAC Secondary Heating Fuel':{'Electricity','None'},
            'Clothes Dryer':{'Electric','None'}, 'Cooking Range':{'Electric Resistance','Electric Induction','None'},
            'Water Heater Efficiency':{'Electric Standard','Electric Premium','Electric Tankless',
                                     'Solar Thermal, 40 sqft, South, Roof Pitch, Electric Standard Backup'},
            'Misc Gas Fireplace':{'None'}, 'Misc Gas Grill':{'None'}, 'Misc Gas Lighting':{'None'},
            'Misc Pool Heater':{'None','Electric Heat Pump','Electricity'},
            'Misc Hot Tub Spa':{'None','Electricity'}}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_completion(policy):
    version=policy.get('commercial_completion_release')
    if version is None:return None
    if version!='v0.1.0':raise ValueError('Unreviewed commercial completion release')
    from scripts.commercial_completion import validate_bundle
    path=ROOT/'data/completion-releases'/version
    if sha(path/'manifest.json')!=policy['commercial_completion_manifest_sha256']:
        raise ValueError('Commercial completion binding mismatch')
    return validate_bundle(path)


def verify_completion_reviews(policy, lock_path):
    """Check quoted vacancy source fragments against immutable official blobs."""
    from scripts.fetch import verify_file
    entries={e['sha256']:e for e in load_json(lock_path)['files']}
    for review in policy.get('vacancy_zero_reviews',[]):
        for proof in review['evidence']:
            entry=entries.get(proof['source_file_sha256'])
            if entry is None or proof['source_revision']!=entry['source_revision']:
                raise ValueError('Unbound completion evidence')
            raw=verify_file(entry).read_text(encoding='utf-8')
            if proof['original_value'].strip() not in raw:
                raise ValueError('Completion source fragment mismatch')


def profile_name(name):
    if not re.fullmatch(r'residential_archetype-[a-f0-9]{20}\.(json|csv)',name):
        raise ValueError('Unsafe profile path')
    return name


def source_zero(row, magnitude, schedule):
    value = row.get(magnitude)
    return type(value) in (int,float) and value == 0 and row.get(schedule) is None


def all_electric(options):
    return all(options.get(key) in allowed for key, allowed in ELECTRIC.items())


def unconditioned(row, mappings, reviewed_ids):
    matched = [m for m in mappings if m['program_id'] == row['id']]
    return (row['id'] in reviewed_ids and row['source_space_type'] in {'Attic','Plenum'}
            and row['heating_setpoint_schedule_id'] is None and row['cooling_setpoint_schedule_id'] is None
            and bool(matched) and all(m['system_id'] is None and m['part_of_total_floor_area']==['No'] for m in matched))


def resolve_records(data, policy, profiles, fixed_background=None, completion=None):
    resolutions, unresolved = [], []
    provenance = {p['id']:p for p in data['provenance']}
    sources = {s['id']:s for s in data['source_files']}
    def evidence(row, field, note):
        p = provenance[row['provenance_id']]; s = sources[p['source_file_id']]
        f = p['fields'].get(field, {'original_value':row.get(field), 'original_units':'source descriptors',
                                   'transformation':'Retain source context; original null means unknown'})
        return {'source_locator':s['path']+'#'+p['locator']+'/'+field,
                'source_revision':s['version'],'source_file_sha256':s['sha256'],
                'provenance_id':p['id'],'original_value':f['original_value'],
                'original_unit':f['original_units'],'transformation':f['transformation']+'; '+note,
                'extraction_date':policy['date'],'interpretation_note':note}
    def add(table, row, field, value, unit, rule, basis, note, fields):
        proofs=[evidence(row,f,note) for f in fields]
        for proof in policy.get('rule_evidence',{}).get(rule,[]):
            proofs.append({**proof,'provenance_id':row['provenance_id'],
                           'extraction_date':policy['date'],'interpretation_note':note})
        resolutions.append({'id':stable_id('resolution',table,row['id'],field,rule),
            'record_table':table,'record_id':row['id'],'field':field,'original_value':row.get(field),
            'resolved_value':value,'unit':unit,'rule':rule,'basis':basis,
            'note':note,'evidence':proofs})
    constant = {'constant_value':0,'calendar_independent':True}
    supported_vacancy={'lighting_interior','lighting_exterior','plug_loads_other','plug_loads_tv','cooking_range','clothes_washer','clothes_dryer','dishwasher','hot_water_fixtures','hot_water_dishwasher','hot_water_clothes_washer'}
    for review in policy.get('vacancy_zero_reviews',[]):
        if review['column'] not in supported_vacancy or not review['evidence']:
            raise ValueError('Invalid vacancy end-use evidence')
    for row in data['programs']:
        if completion:
            from scripts.commercial_completion import evidence_for,inactive_control
            control=next((c for c in completion['controls'] if c['record_id']==row['id']),None)
            if control:
                if (row['heating_setpoint_schedule_id'] is not None or row['cooling_setpoint_schedule_id'] is not None
                        or any(m['system_id'] is not None for m in data['mappings'] if m['program_id']==row['id']) or not inactive_control(control)):
                    raise ValueError('Inactive conditioning conflicts with source')
                add('programs',row,'conditioning',{'heating_enabled':False,'cooling_enabled':False},'state','inspected_inactive_controls','executed_upstream',
                    'Dedicated source zone has empty thermostat schedules and no direct HVAC through loads, zone recreation, HVAC, custom tweaks and transfer-air phases at 4A. Passive thermal coupling remains possible; no complete simulation claimed.',
                    ['heating_setpoint_schedule_id','cooling_setpoint_schedule_id'])
                resolutions[-1]['evidence'] += [{**e,'provenance_id':row['provenance_id']} for e in evidence_for(completion,control)]
            gap=next((g for g in completion['missing_program_evidence'] if g['program_id']==row['id']),None)
            if gap and gap['zero_schedule_eligible']:
                if row['service_water_heating_schedule_id'] is not None or any(type(row['source_attributes'].get(k)) in (int,float) and row['source_attributes'][k]>0 for k in ['service_water_heating_peak_flow_rate','service_water_heating_peak_flow_per_area']):
                    raise ValueError('Complete water zero conflicts with positive source')
                add('programs',row,'service_water_heating_schedule_id',constant,'dimensionless','source_complete_no_water_draw','source_zero',
                    'Pinned complete main/booster/laundry source path creates no modeled program fixture draw and no unallocated service remains for this building/template. Zero applies to fixture demand, not central heater energy or circulation.',
                    ['service_water_heating_schedule_id','source_attributes'])
                resolutions[-1]['evidence'] += [{**e,'provenance_id':row['provenance_id']} for e in evidence_for(completion,gap)]
        for schedule,magnitude in LOADS.items():
            if source_zero(row,magnitude,schedule):
                add('programs',row,schedule,constant,'dimensionless','explicit_zero_magnitude','source_zero',
                    'Missing fractional schedule resolved to always zero because reported load magnitude is exactly zero.',[magnitude,schedule])
        if row['id'] in policy['no_occupancy_program_ids'] and row['occupancy_schedule_id'] is None and row['people_per_m2'] is None:
            add('programs',row,'occupancy_schedule_id',constant,'dimensionless','reviewed_no_occupancy','research_assumption',
                policy.get('occupancy_notes',{}).get(row['id'],
                    'Reviewed attic/plenum cavity: no routine modeled occupancy; transient maintenance visits excluded from this experimental variant.'),
                ['source_attributes','occupancy_schedule_id'])
        if (row['id'] in policy.get('no_lighting_program_ids',[]) and row['source_space_type']=='Plenum'
                and row['lighting_schedule_id'] is None and row['lighting_W_m2'] is None
                and all(row['source_attributes'].get(k) in (None,'',0) for k in
                        ['lighting_per_area','lighting_per_person','additional_lighting_per_area'])):
            add('programs',row,'lighting_schedule_id',constant,'dimensionless','reviewed_no_lighting','research_assumption',
                'User-reviewed ceiling plenum: standards load routine skips plenum loads; no modeled lighting. Occupied offices retain their lighting.',
                ['source_attributes','lighting_schedule_id','lighting_W_m2'])
        if unconditioned(row,data['mappings'],policy['unconditioned_program_ids']):
            matched=[m for m in data['mappings'] if m['program_id']==row['id']]
            add('programs',row,'conditioning',{'heating_enabled':False,'cooling_enabled':False},'state',
                'reviewed_unconditioned','research_assumption',
                'Reviewed attic/plenum with no thermostat, no mapped HVAC and excluded floor area. Explicitly disable heating/cooling; no temperature sentinel.',
                ['source_attributes','heating_setpoint_schedule_id','cooling_setpoint_schedule_id'])
            resolutions[-1]['evidence'] += [evidence(m,'system_id','No mapped HVAC; absence alone is not sufficient') for m in matched]
            resolutions[-1]['evidence'] += [evidence(m,'part_of_total_floor_area','Excluded from source total floor area') for m in matched]
        attrs=row['source_attributes']
        if (row['id'] in policy.get('no_gas_equipment_program_ids',[])
                and row['gas_equipment_schedule_id'] is None and row['gas_equipment_W_m2'] is None
                and all(attrs.get(k) in (None,'',0) for k in
                        ['gas_equipment_per_area','gas_equipment_schedule','additional_gas_equipment_schedule'])):
            note='User-approved program gas-equipment absence in the clean standards space-type recipe; constant zero schedule and density. Does not classify the building as all-electric or zero gas heating/water heating; direct/custom loads require a separate variant.'
            for field,value,unit in [('gas_equipment_schedule_id',constant,'dimensionless'),
                                     ('gas_equipment_W_m2',0,'W/m2')]:
                add('programs',row,field,value,unit,'reviewed_no_gas_equipment','research_assumption',note,
                    ['source_attributes','gas_equipment_W_m2','gas_equipment_schedule_id'])
        water_keys=['service_water_heating_peak_flow_rate','service_water_heating_peak_flow_per_area']
        water_values=[attrs.get(k) for k in water_keys]
        if (row['id'] in policy['no_hot_water_program_ids'] and row['service_water_heating_schedule_id'] is None
                and all(v in (None,'',0) for v in water_values)):
            add('programs',row,'service_water_heating_schedule_id',constant,'dimensionless',
                'reviewed_no_hot_water','research_assumption',
                'Reviewed cavity/elevator-core program has no modeled plumbing demand in this experimental variant. Does not disable a whole-building water system or circulation pump.',
                ['source_attributes','service_water_heating_schedule_id'])
    for row in data.get('residential_archetypes',[]):
        opts=row['selected_options']
        if fixed_background and row['id'] in policy.get('fixed_background_record_ids',[]) and (row['occupants']==0 or policy.get('fixed_background_all_records')):
            for parameter,column in [('Refrigerator','refrigerator'),('Misc Freezer','freezer')]:
                if opts.get(parameter) in (None,''):
                    raise ValueError('Unknown selected background appliance')
                if opts[parameter]=='None':
                    add('residential_archetypes',row,'profile:'+column,constant,'dimensionless',
                        'selected_absent_end_use','source_zero',parameter+' is explicitly absent; fixed background use is zero.',['selected_options'])
                    continue
                schedule=fixed_background['schedules'][column]
                note=('User-selected fixed normalized refrigeration default for a dwelling; separate appliance load, not miscellaneous plugs; source fractions retained without temperature feedback or load magnitude.' if policy.get('fixed_background_all_records') else 'User-selected fixed normalized refrigeration default for a zero-occupant dwelling; source weekday/weekend fractions and monthly multipliers retained; no temperature feedback, load magnitude or stochastic execution claimed.')
                add('residential_archetypes',row,'profile:'+column,
                    {'fixed_schedule_id':column,'schedule_file':'fixed-background-schedules.json'},'dimensionless',
                    'fixed_background_default','research_assumption',note,['selected_options'])
                for e in schedule['evidence']:
                    resolutions[-1]['evidence'].append({k:v for k,v in {
                        **e,'provenance_id':row['provenance_id'],'interpretation_note':note+' '+e['interpretation_note']
                        }.items() if k!='original_field'})
        for review in policy.get('vacancy_zero_reviews',[]):
            if review['record_id']!=row['id']:continue
            if row['occupants']!=0 or review.get('eri_version')!='latest' or review.get('apply_ashrae140_assumptions') is not False:
                raise ValueError('Invalid vacancy zero applicability')
            add('residential_archetypes',row,'profile:'+review['column'],constant,'dimensionless',
                'reviewed_vacancy_zero','executed_upstream',
                'Pinned upstream operational zero-occupant rule; refrigeration continues separately. No shared/common-area load inferred.', ['occupants','selected_options'])
            resolutions[-1]['evidence'] += [{k:v for k,v in {**e,'provenance_id':row['provenance_id']}.items() if k!='original_field'} for e in review['evidence']]
        if fixed_background and 'lighting_exterior' in fixed_background['schedules'] and row['occupants']!=0 and row['id'] in policy.get('exterior_record_ids',[]):
            if opts.get('Lighting') in (None,'','None') or opts.get('Lighting Other Use')!='100% Usage':
                raise ValueError('Unknown exterior lighting applicability')
            schedule=fixed_background['schedules']['lighting_exterior']
            note='Fixed source dwelling exterior lighting default; weekday/weekend and monthly product peak-normalized. Multifamily common-area lighting is separately unreported.'
            add('residential_archetypes',row,'profile:lighting_exterior',{'fixed_schedule_id':'lighting_exterior','schedule_file':'fixed-background-schedules.json'},'dimensionless',
                'fixed_background_default','research_assumption',note,['selected_options'])
            resolutions[-1]['evidence'] += [{k:v for k,v in {**e,'provenance_id':row['provenance_id']}.items() if k!='original_field'} for e in schedule['evidence']]
        if all_electric(opts):
            add('residential_archetypes',row,'gas_equipment_W',0,'W','demonstrated_all_electric','source_zero',
                'All selected fuel-using end uses are electricity/absent, including secondary heat, water heating, dryer, cooking and miscellaneous gas/pool/spa loads; dwelling gas equipment is zero.',
                ['selected_options'])
        for parameter,columns in {'Dishwasher':['dishwasher','hot_water_dishwasher'],
                                 'Clothes Washer':['clothes_washer','hot_water_clothes_washer'],
                                 'Clothes Dryer':['clothes_dryer'], 'Cooking Range':['cooking_range'],
                                 'Ceiling Fan':['ceiling_fan']}.items():
            if opts.get(parameter)=='None' or (parameter=='Ceiling Fan' and opts.get(parameter)=='Standard Efficiency, No usage'):
                for column in columns:
                    add('residential_archetypes',row,'profile:'+column,constant,'dimensionless','selected_absent_end_use','source_zero',
                        parameter+' is explicitly absent/inactive in source selection; potential-use profile is always zero.',['selected_options'])
    for p in profiles:
        row=next(r for r in data['residential_archetypes'] if r['id']==p['record_id'])
        for column,unit in p['columns'].items():
            add('residential_archetypes',row,'profile:'+column,{'profile_file':'profiles/'+p['profile_file'],'column':column},unit,
                'executed_residential_profile','executed_upstream' if p['status']=='executed_stochastic' or column.endswith('_setpoint') else 'source_zero',
                'Executed upstream schedule-only station-proxy variant; nominal setpoints precede HVAC unavailable-day overrides; see profile provenance and unresolved list.',['selected_options'])
    resolved={(r['record_id'],r['field']) for r in resolutions}
    for row in data['programs']:
        for field in list(LOADS)+['heating_setpoint_schedule_id','cooling_setpoint_schedule_id','service_water_heating_schedule_id']:
            if row[field] is None and (row['id'],field) not in resolved:
                if field.endswith('setpoint_schedule_id') and (row['id'],'conditioning') in resolved:
                    continue
                unresolved.append({'record_table':'programs','record_id':row['id'],'field':field,
                    'reason':'Source null; no explicit zero magnitude or applicable reviewed evidence. Support-space names/electric HVAC alone do not justify resolution.'})
    counts=Counter(r['rule'] for r in resolutions)
    return {'schema_version':policy.get('schema_version','0.1.0'),'base_release':'v0.2.0','resolutions':resolutions,'unresolved':unresolved,
            'summary':{'resolution_rows':len(resolutions),'records_with_resolutions':len({r['record_id'] for r in resolutions}),
                       'unresolved_program_fields':len(unresolved),'by_rule':dict(sorted(counts.items()))}}


def validate_bundle(path, base=BASE):
    path=Path(path); manifest=load_json(path/'manifest.json')
    if verify_release(base) or manifest['base_manifest_sha256'] != sha(base/'manifest.json'):
        raise ValueError('Base release integrity mismatch')
    actual={p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()}
    if actual != set(manifest['files'])|{'manifest.json'}:
        raise ValueError('Supplement inventory mismatch')
    for name,entry in manifest['files'].items():
        p=(path/name).resolve()
        if not p.is_relative_to(path.resolve()) or not p.is_file() or sha(p)!=entry['sha256'] or p.stat().st_size!=entry['size_bytes']:
            raise ValueError('Supplement checksum/path mismatch')
    data=load_atlas(base); result=load_json(path/'resolutions.json')
    jsonschema.validate(result,load_json(path/'schemas/resolution.schema.json'))
    index=load_json(path/'profile-index.json')
    policy=load_json(path/'sources/resolution-policy.json')
    if policy.get('vacancy_zero_reviews'):
        verify_completion_reviews(policy,path/'sources/completion-evidence-lock.json')
    fixed=load_json(path/'fixed-background-schedules.json') if policy.get('fixed_background_record_ids') else None
    if fixed is not None:
        from scripts.fixed_background import build
        if fixed!=build(evidence_lock=path/'sources/schedule-evidence-lock.json',names=policy.get('fixed_default_names')):
            raise ValueError('Fixed background defaults do not reproduce pinned source')
    expected=resolve_records(data,policy,index,fixed,load_completion(policy))
    if result!=expected:
        raise ValueError('Resolution evidence/rules do not reproduce')
    if (manifest['schema_version']!=result['schema_version'] or manifest['release_version']!=policy['policy_version']
            or manifest['base_release']!='v0.2.0' or manifest['summary']!=result['summary']):
        raise ValueError('Supplement manifest metadata mismatch')
    rows={r['id']:r for r in data['residential_archetypes']}
    if len(index)!=len(rows) or {p['record_id'] for p in index} != set(rows):
        raise ValueError('Profile record inventory mismatch')
    for p in index:
        jpath=path/'profiles'/profile_name(p['profile_file']); cpath=path/'profiles'/profile_name(p['csv_file'])
        if sha(jpath)!=p['profile_sha256'] or sha(cpath)!=p['csv_sha256']:
            raise ValueError('Profile index checksum mismatch')
        profile=load_json(jpath); meta=profile['metadata']; series=profile['series']; row=rows[p['record_id']]
        if (meta['record_id']!=row['id'] or meta['seed']!=int(row['source_building_id'])
                or meta['selected_options']!=row['selected_options'] or meta['columns']!=p['columns']
                or meta['year']!=2007 or meta['timestep_minutes']!=60 or meta['occupants']!=row['occupants']
                or not meta['provenance'] or not meta['unresolved']):
            raise ValueError('Profile source context/provenance mismatch')
        validation=validate_profiles(cpath,meta)
        if validation['rows']!=8760 or set(series)!=set(p['columns']):
            raise ValueError('Profile shape mismatch')
        with cpath.open(encoding='utf-8',newline='') as stream:
            csv_rows=list(csv.DictReader(stream))
        for col,unit in p['columns'].items():
            if unit not in {'dimensionless','degC'} or len(series[col])!=8760:
                raise ValueError('Profile units/dimensions mismatch')
            if series[col] != [float(r[col]) for r in csv_rows]:
                raise ValueError('Canonical profile differs from execution CSV')
        if any(h>c+1e-8 for h,c in zip(series['heating_setpoint'],series['cooling_setpoint'])):
            raise ValueError('Profile thermostat overlap')
        for r in result['resolutions']:
            if r['record_id']==row['id'] and r['rule'] in {'selected_absent_end_use','reviewed_vacancy_zero'}:
                col=r['field'].split(':')[1]
                if col in series and any(series[col]):
                    raise ValueError('Absent end use conflicts with executed positive profile')
    return result


def freeze(profiles, target, base=BASE):
    target,profiles=Path(target),Path(profiles)
    if target.exists():
        raise ValueError('Never overwrite a frozen resolution release')
    profiles=completed_output(profiles)
    if verify_release(base):
        raise ValueError('Base release validation failed')
    index=load_json(profiles/'profile-index.json')
    for p in index:
        for field in ['profile_file','csv_file']:
            profile_name(p[field])
    policy=load_json(ROOT/'sources/resolution-policy.json')
    fixed=None
    if policy.get('fixed_background_record_ids'):
        from scripts.fixed_background import build
        fixed=build(names=policy.get('fixed_default_names'))
    result=resolve_records(load_atlas(base),policy,index,fixed,load_completion(policy))
    target.mkdir(parents=True)
    for p in index:
        for field in ['profile_file','csv_file']:
            dst=target/'profiles'/p[field];dst.parent.mkdir(exist_ok=True)
            shutil.copyfile(profiles/p[field],dst)
    dump_json(target/'profile-index.json',index)
    if fixed is not None:
        dump_json(target/'fixed-background-schedules.json',fixed)
    dump_json(target/'resolutions.json',result)
    paths=['schemas/resolution.schema.json','sources/runtime-lock.json','sources/weather-lock.json',
           'sources/resolution-policy.json','sources/licenses/weather.txt','sources/licenses/resstock.txt',
           'sources/licenses/openstudio-hpxml.txt','sources/licenses/openstudio-standards.txt',
           'scripts/runtime.py','scripts/residential_profiles.py','scripts/run_residential_profiles.rb',
           'scripts/resolve.py','docs/residential-generation.md','docs/adr/0004-selective-resolution.md','LICENSE']
    if fixed is not None:
        paths+=['scripts/fixed_background.py','docs/adr/0006-deterministic-coverage-release.md']
    for name in paths:
        dst=target/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dst)
    for name in policy.get('supporting_files',[]):
        src=(ROOT/name).resolve()
        if not src.is_relative_to(ROOT.resolve()) or name not in {
                'docs/adr/0005-parametric-schedule-generators.md','docs/schedule-source-review.md',
                'sources/schedule-evidence-lock.json','sources/licenses/comstock.txt',
                'sources/completion-evidence-lock.json','sources/schedule-release-scope.json',
                'docs/adr/0008-reviewed-schedule-completion.md','sources/residential-completion-inputs.json',
                'scripts/inspect_residential_zero.rb','scripts/inspect_exterior_defaults.rb',
                'sources/residential-completion-receipt.json'}:
            raise ValueError('Unrecognized supplement supporting file')
        dst=target/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    dump_json(target/'manifest.json',{'release_version':policy['policy_version'],'schema_version':result['schema_version'],
        'base_release':'v0.2.0','base_manifest_sha256':sha(base/'manifest.json'),
        'generation_date':policy['date'],'summary':result['summary'],
        'files':{p.relative_to(target).as_posix():{'sha256':sha(p),'size_bytes':p.stat().st_size}
                 for p in sorted(target.rglob('*')) if p.is_file()}})
    validate_bundle(target,base)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--target',type=Path,default=DEFAULT)
    parser.add_argument('--profiles',type=Path,default=ROOT/'build/residential',help='Generation directory with a completed latest-run.json receipt')
    args=parser.parse_args()
    result=validate_bundle(args.target) if args.verify else freeze(args.profiles,args.target)
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':
    main()
