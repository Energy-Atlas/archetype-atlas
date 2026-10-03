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
from scripts.residential_profiles import validate_profiles

BASE = ROOT/'data/releases/v0.2.0'
DEFAULT = ROOT/'data/resolution-releases/v0.1.0'
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


def resolve_records(data, policy, profiles):
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
        resolutions.append({'id':stable_id('resolution',table,row['id'],field,rule),
            'record_table':table,'record_id':row['id'],'field':field,'original_value':row.get(field),
            'resolved_value':value,'unit':unit,'rule':rule,'basis':basis,
            'note':note,'evidence':[evidence(row,f,note) for f in fields]})
    constant = {'constant_value':0,'calendar_independent':True}
    for row in data['programs']:
        for schedule,magnitude in LOADS.items():
            if source_zero(row,magnitude,schedule):
                add('programs',row,schedule,constant,'dimensionless','explicit_zero_magnitude','source_zero',
                    'Missing fractional schedule resolved to always zero because reported load magnitude is exactly zero.',[magnitude,schedule])
        if row['id'] in policy['no_occupancy_program_ids'] and row['occupancy_schedule_id'] is None and row['people_per_m2'] is None:
            add('programs',row,'occupancy_schedule_id',constant,'dimensionless','reviewed_no_occupancy','research_assumption',
                'Reviewed attic/plenum cavity: no routine modeled occupancy; transient maintenance visits excluded from this experimental variant.',
                ['source_attributes','occupancy_schedule_id'])
        if unconditioned(row,data['mappings'],policy['unconditioned_program_ids']):
            matched=[m for m in data['mappings'] if m['program_id']==row['id']]
            add('programs',row,'conditioning',{'heating_enabled':False,'cooling_enabled':False},'state',
                'reviewed_unconditioned','research_assumption',
                'Reviewed attic/plenum with no thermostat, no mapped HVAC and excluded floor area. Explicitly disable heating/cooling; no temperature sentinel.',
                ['source_attributes','heating_setpoint_schedule_id','cooling_setpoint_schedule_id'])
            resolutions[-1]['evidence'] += [evidence(m,'system_id','No mapped HVAC; absence alone is not sufficient') for m in matched]
            resolutions[-1]['evidence'] += [evidence(m,'part_of_total_floor_area','Excluded from source total floor area') for m in matched]
        attrs=row['source_attributes']
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
    return {'schema_version':'0.1.0','base_release':'v0.2.0','resolutions':resolutions,'unresolved':unresolved,
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
    expected=resolve_records(data,load_json(path/'sources/resolution-policy.json'),index)
    if result!=expected:
        raise ValueError('Resolution evidence/rules do not reproduce')
    if manifest['schema_version']!='0.1.0' or manifest['release_version']!='0.1.0' or manifest['base_release']!='v0.2.0' or manifest['summary']!=result['summary']:
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
            if r['record_id']==row['id'] and r['rule']=='selected_absent_end_use':
                col=r['field'].split(':')[1]
                if col in series and any(series[col]):
                    raise ValueError('Absent end use conflicts with executed positive profile')
    return result


def freeze(profiles, target, base=BASE):
    target,profiles=Path(target),Path(profiles)
    if target.exists():
        raise ValueError('Never overwrite a frozen resolution release')
    if verify_release(base):
        raise ValueError('Base release validation failed')
    index=load_json(profiles/'profile-index.json')
    for p in index:
        for field in ['profile_file','csv_file']:
            profile_name(p[field])
    target.mkdir(parents=True)
    for p in index:
        for field in ['profile_file','csv_file']:
            dst=target/'profiles'/p[field];dst.parent.mkdir(exist_ok=True)
            shutil.copyfile(profiles/p[field],dst)
    dump_json(target/'profile-index.json',index)
    result=resolve_records(load_atlas(base),load_json(ROOT/'sources/resolution-policy.json'),index)
    dump_json(target/'resolutions.json',result)
    paths=['schemas/resolution.schema.json','sources/runtime-lock.json','sources/weather-lock.json',
           'sources/resolution-policy.json','sources/licenses/weather.txt','sources/licenses/resstock.txt',
           'sources/licenses/openstudio-hpxml.txt','sources/licenses/openstudio-standards.txt',
           'scripts/runtime.py','scripts/residential_profiles.py','scripts/run_residential_profiles.rb',
           'scripts/resolve.py','docs/residential-generation.md','docs/adr/0004-selective-resolution.md','LICENSE']
    for name in paths:
        dst=target/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dst)
    dump_json(target/'manifest.json',{'release_version':'0.1.0','schema_version':'0.1.0',
        'base_release':'v0.2.0','base_manifest_sha256':sha(base/'manifest.json'),
        'generation_date':'2026-10-03','summary':result['summary'],
        'files':{p.relative_to(target).as_posix():{'sha256':sha(p),'size_bytes':p.stat().st_size}
                 for p in sorted(target.rglob('*')) if p.is_file()}})
    validate_bundle(target,base)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    parser.add_argument('--target',type=Path,default=DEFAULT)
    parser.add_argument('--profiles',type=Path,default=ROOT/'build/residential/output')
    args=parser.parse_args()
    result=validate_bundle(args.target) if args.verify else freeze(args.profiles,args.target)
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':
    main()
