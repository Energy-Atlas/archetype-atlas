"""Freeze a complete, explicitly derived commercial water reporting variant."""
import argparse
import copy
import datetime as dt
import hashlib
import math
from pathlib import Path
import re
import shutil
from collections import Counter, defaultdict

import jsonschema

from scripts.common import ROOT, dump_json, load_atlas, load_json, stable_id
from scripts.fetch import verify_file
from scripts.release import verify_release
from scripts.semantics import osm_objects, profile

BASE = ROOT/'data/releases/v0.2.0'
COMPLETION = ROOT/'data/completion-releases/v0.1.0'
RESOLUTION = ROOT/'data/resolution-releases/v0.4.0'
DEFAULT = ROOT/'data/water-reporting-releases/v0.1.0'
SCHEMA = ROOT/'schemas/water-reporting.schema.json'
DATE = '2026-10-05'
DAYS = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun','Hol','SmrDsn','WntrDsn']
SUPPORT = {'Attic','Basement','Plenum','Corridor','Corridor2','Corridor4','Corridor_topfloor',
           'Mechanical','Elec/MechRoom','ElevatorCore','ElevatorCore4','Stair','Stair4',
           'Storage','Storage4Front','Storage4Rear','DryStorage','Bulk','Fine','Vestibule',
           'Entry','Restroom','PublicRestroom'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def floor_geometry(text):
    """Read full SI floor vertex tuples; the generic tagged parser keeps only X."""
    result=[]
    for block in re.findall(r'OS:Surface,.*?;[^\n]*',text,re.DOTALL):
        o=osm_objects(block)[0]['fields']
        if o.get('Surface Type')!='Floor':continue
        vertices=[]
        for line in block.splitlines():
            body,_,comment=line.partition('!')
            if re.search(r'X\s*,\s*Y\s*,\s*Z\s+Vertex',comment):
                values=[float(v.strip()) for v in body.rstrip(' ,;').split(',')]
                if len(values)!=3 or any(not math.isfinite(v) for v in values):
                    raise ValueError('Invalid floor vertex tuple')
                vertices.append(values)
        if len(vertices)<3:raise ValueError('Missing floor vertices')
        normal=[math.fsum(a[(i+1)%3]*b[(i+2)%3]-a[(i+2)%3]*b[(i+1)%3]
                    for a,b in zip(vertices,vertices[1:]+vertices[:1])) for i in range(3)]
        norm=math.sqrt(math.fsum(v*v for v in normal));area=norm/2
        if not math.isfinite(area) or area<=0:raise ValueError('Invalid floor area')
        origin=vertices[0]
        if any(abs(math.fsum((v[i]-origin[i])*normal[i]/norm for i in range(3)))>1e-5 for v in vertices):
            raise ValueError('Nonplanar floor polygon')
        result.append({'handle':o['Handle'],'space_handle':o['Space Name'],
                       'vertices_m':vertices,'area_m2':area})
    return result


def floor_areas(text):
    result=defaultdict(float)
    for f in floor_geometry(text):result[f['space_handle']]+=f['area_m2']
    return dict(result)


def reference_context(data, cache_root=ROOT/'data/raw'):
    """Benchmark-only weights, deduplicated across overlapping HVAC mappings."""
    provenance={r['id']:r for r in data['provenance']}
    sources={r['id']:r for r in data['source_files']}
    programs={r['id']:r for r in data['programs']}
    refs=defaultdict(dict);geometries={}
    for m in data['mappings']:
        p=programs[m['program_id']]
        if p['source_space_type'] in {'Attic','Basement','Plenum'}:continue
        prov=provenance[m['provenance_id']];source=sources[prov['source_file_id']]
        path=source['path']
        if path not in geometries:
            text=verify_file(source,cache_root).read_text(encoding='utf-8-sig')
            objects=osm_objects(text)
            spaces={o['fields']['Handle']:o['fields'] for o in objects if o['kind']=='OS:Space'}
            zones={o['fields']['Handle']:o['fields'] for o in objects if o['kind']=='OS:ThermalZone'}
            floors=defaultdict(list)
            for f in floor_geometry(text):floors[f['space_handle']].append(f)
            geometries[path]=(spaces,zones,floors)
        spaces,zones,floors=geometries[path]
        originals=prov['fields']['source_space_names']['original_value']
        for original in originals:
            h=original['handle'];space=spaces[h]
            if space['Name']!=original['name'] or not floors[h]:raise ValueError('Reference space/floor mismatch')
            multiplier=float(zones[space['Thermal Zone Name']].get('Multiplier') or 1)
            if multiplier!=original['multiplier'] or multiplier<=0 or not math.isfinite(multiplier):
                raise ValueError('Reference multiplier mismatch')
            area=math.fsum(f['area_m2'] for f in floors[h])
            item={'space_handle':h,'space_name':space['Name'],'floor_area_m2':area,
                  'zone_multiplier':multiplier,'represented_area_m2':area*multiplier,
                  'source_locator':path+'#OS:Space/'+h,'source_revision':source['version'],
                  'source_file_sha256':source['sha256'],'original_value':{'floor_polygons':[
                  {k:v for k,v in f.items() if k!='area_m2'} for f in floors[h]],
                  'zone_multiplier':zones[space['Thermal Zone Name']].get('Multiplier')},
                  'original_unit':'m coordinates; dimensionless zone multiplier',
                  'transformation':'Sum planar floor polygon cross-product areas; multiply zone multiplier once; deduplicate space handle across HVAC mappings',
                  'extraction_date':DATE,'interpretation_note':'Reference benchmark weighting context only, not downstream geometry or an atlas area_fraction'}
            if h in refs[p['id']] and refs[p['id']][h]!=item:raise ValueError('Conflicting duplicate source space')
            refs[p['id']][h]=item
    result={}
    for pid,spaces in refs.items():
        p=programs[pid];density=p['people_per_m2'];area=math.fsum(v['represented_area_m2'] for v in spaces.values())
        if density is not None and (not math.isfinite(density) or density<0):raise ValueError('Invalid source people density')
        prov=provenance[p['provenance_id']];source=sources[prov['source_file_id']]
        result[pid]={'represented_area_m2':area,'design_occupants':None if density is None else area*density,
                     'space_evidence':sorted(spaces.values(),key=lambda s:s['space_handle']),
                     'density_evidence':{'source_locator':source['path']+'#'+prov['locator']+'/occupancy_per_area',
                      'source_revision':source['version'],'source_file_sha256':source['sha256'],
                      'original_value':p['source_attributes']['occupancy_per_area'],
                      'original_unit':'people/1000 ft2','transformation':'Divide by 1000 * 0.09290304 for people/m2; multiply deduplicated represented area',
                      'extraction_date':DATE,'interpretation_note':'Design counts provide derived reporting weights, not sanitary fixture evidence'}}
    return result


def allocation(draw, candidates, references):
    """Assign a reporting beneficiary or retain the full shared service."""
    if draw['allocation_weights']:
        return 'source_assignment',dict(draw['allocation_weights'])
    if draw['end_use'] in {'booster','laundry'}:
        space_type='Kitchen' if draw['end_use']=='booster' else 'Laundry'
        selected=[p for p in candidates if p['source_space_type']==space_type]
        if len(selected)==1:
            return 'derived_dedicated_kitchen_process' if space_type=='Kitchen' else 'derived_dedicated_laundry_process',{selected[0]['id']:1.0}
        return 'retained_shared_service',{}
    if draw['building_type']=='Hospital':return 'retained_shared_service',{}
    selected=[p for p in candidates if p['source_space_type'] not in SUPPORT]
    # Null density/area in an otherwise eligible program blocks a complete inferred split.
    if any(p['id'] not in references or references[p['id']]['design_occupants'] is None for p in selected):
        return 'retained_shared_service',{}
    counts={p['id']:references[p['id']]['design_occupants'] for p in selected
            if references[p['id']]['design_occupants']>0}
    total=math.fsum(counts.values())
    if total<=0:return 'retained_shared_service',{}
    return 'derived_design_occupant_allocation',{k:v/total for k,v in sorted(counts.items())}


def inspection_rules(components, services, schedules):
    """Combine mixed volume at reference scale; temperatures stay on components."""
    start=dt.date(2000,1,1);dates=[start+dt.timedelta(days=i) for i in range(366)]
    output=[];peak=0.0
    for day in DAYS:
        previous=None
        for date in dates:
            values=[0.0]*24
            for c in components:
                s=services[c['path_id']]
                curve=profile(schedules[s['source_schedule_name']]['source_schedule']['rules'],day,date.strftime('%m-%d'))
                scale=s['reference_rated_flow_m3_s']*c['allocation_weight']
                values=[a+scale*b for a,b in zip(values,curve)]
            peak=max(peak,max(values))
            if previous is not None and previous['values']==values:
                previous['end_date']=date.isoformat()
            else:
                previous={'day_types':day,'start_date':date.isoformat(),'end_date':date.isoformat(),
                          'type':'Hourly','values':values}
                output.append(previous)
    for i,r in enumerate(output):
        r['values']=[v/peak if peak else 0.0 for v in r['values']];r['source_index']=i
    return output,peak


def build(data=None, completion=None):
    data=data or load_atlas(BASE)
    completion=completion or load_json(COMPLETION/'commercial-completion.json')
    excluded=set(load_json(ROOT/'sources/schedule-release-scope.json')['excluded_commercial_space_types'])
    programs=[p for p in data['programs'] if p['source_space_type'] not in excluded]
    groups=defaultdict(list)
    for p in programs:groups[p['building_type'],p['template']].append(p)
    references=reference_context(data)
    schedules={s['source_name']:s for s in completion['schedules']}
    services=[]
    for d in completion['draw_paths']:
        status,weights=allocation(d,groups[d['building_type'],d['template']],references)
        area=None
        if d['rated_flow_per_area_m3_s_m2'] is not None:
            if len(d['beneficiary_program_ids'])!=1:raise ValueError('Ambiguous per-area draw')
            area=references[d['beneficiary_program_ids'][0]]['represented_area_m2']
            q=d['rated_flow_per_area_m3_s_m2']*area
        else:
            q=d['rated_flow_m3_s']
            if d.get('fixture_instances'):
                q*=math.fsum(x['multiplier'] for x in d['fixture_instances'])
        if q is None or not math.isfinite(q) or q<0:raise ValueError('Missing or invalid reference draw')
        services.append({'path_id':d['path_id'],'building_type':d['building_type'],'template':d['template'],
                         'end_use':d['end_use'],'source_schedule_name':d['source_schedule_name'],
                         'source_schedule_id':schedules[d['source_schedule_name']]['source_schedule']['id'],
                         'equivalent_schedule_id':schedules[d['source_schedule_name']]['equivalent_schedule']['id'],
                         'source_allocation_status':d['allocation_status'],'allocation_status':status,
                         'allocation_weights':weights,'reference_rated_flow_m3_s':q,
                         'reference_area_m2':area,'target_temperature_degC':d['target_temperature_degC'],
                         'physical_fixture_locations':d['physical_fixture_locations'],
                         'source_evidence_ids':d['evidence_ids'],
                         'field_provenance':{'source_fields':'completion path '+d['path_id']+' with its source_evidence_ids',
                         'allocation':'ADR 0009; source_assignment unchanged, all derived statuses are reporting assumptions',
                         'reference_flow':'Source rated flow times reference represented area or explicit fixture multipliers once; not downstream model magnitude'},
                         'interpretation_note':'Reporting attribution never places physical fixtures or zone gains. Retained services are applied once per building. Booster is not duplicated as another main draw.'})
    indexed={s['path_id']:s for s in services}
    gaps={g['program_id']:g for g in completion['missing_program_evidence']}
    by_program=defaultdict(list);by_building=defaultdict(list)
    for s in services:
        by_building[s['building_type'],s['template']].append(s['path_id'])
        for pid,w in s['allocation_weights'].items():
            by_program[pid].append({'path_id':s['path_id'],'allocation_weight':w})
    branches={(a['building_type'],a['template']):a for a in completion['branch_analyses']}
    reported=[];shapes={};memo={}
    for p in programs:
        components=sorted(by_program[p['id']],key=lambda c:c['path_id'])
        # Identical component mixtures share the same inspection schedule.
        signature=tuple((indexed[c['path_id']]['source_schedule_name'],indexed[c['path_id']]['reference_rated_flow_m3_s']*c['allocation_weight']) for c in components)
        if signature not in memo:
            rules,peak=inspection_rules(components,indexed,schedules)
            sid=stable_id('water_reporting_schedule',rules)
            shapes[sid]={'id':sid,'source_name':'Attributed mixed fixture draw (reporting equivalent)' if peak else 'No attributed fixture draw (reporting equivalent)',
                         'schedule_type':'fraction','units':'dimensionless','time_resolution_minutes':60,
                         'interpolation':'none','rules':rules,'interpretation_note':'Derived month/day profiles on leap-capable inspection calendar 2000, including holidays/design days; component source rules/order remain frozen. Zero means no attributed draw, not proof of no real water use.'}
            memo[signature]=(sid,peak)
        sid,peak=memo[signature];gap=gaps.get(p['id'])
        branch=branches[p['building_type'],p['template']]
        no_source_draw=(branch['main_branch'] in {'no_main_loop','stripmall_reference_returns_true'}
                        and not branch['booster_enabled'] and not branch['laundry_enabled'])
        if gap and gap['classification'].startswith('source_no_') or no_source_draw:
            local='source_no_local_draw'
        elif any(indexed[c['path_id']]['source_allocation_status']!='building_service_unallocated' for c in components):
            local='source_assigned_draw'
        else:
            local='source_local_assignment_unknown'
        if components:
            status='source_assigned_draw' if all(indexed[c['path_id']]['allocation_status']=='source_assignment' for c in components) else 'derived_reporting_allocation'
        elif local=='source_no_local_draw':
            status='zero_local_draw'
        else:
            status='shared_service_reference' if any(indexed[path]['allocation_status']=='retained_shared_service'
                        for path in by_building[p['building_type'],p['template']]) else 'zero_attribution_only'
        reported.append({'program_id':p['id'],'building_type':p['building_type'],'template':p['template'],
                         'program':p['program'],'source_space_type':p['source_space_type'],
                         'source_water_schedule_id':p['service_water_heating_schedule_id'],
                         'local_draw_status':local,'reporting_status':status,
                         'reporting_schedule_id':sid,'reference_reporting_peak_flow_m3_s':peak,
                         'components':components,'building_service_path_ids':by_building[p['building_type'],p['template']],
                         'source_gap_evidence_ids':gap['evidence_ids'] if gap else [],
                         'source_branch_evidence_ids':branch['evidence_ids'],
                         'source_water_branch':branch['main_branch'],
                         'field_provenance':{'identity':'base program '+p['id']+' and its field provenance',
                         'local_draw_status':'completion missing_program_evidence when present; otherwise source assignments or explicit unknown',
                         'reporting_fields':'ADR 0009; components reference exact completion paths and rule evidence; shared references do not establish local fixtures'},
                         'interpretation_note':'Reference reporting shape only. Apply components or retained shared services once, never both a program allocation and the original shared copy. Preserve component temperatures; this is not heater energy.'})
    packet={'schema_version':'0.1.0','release_version':'0.1.0','extraction_date':DATE,
            'variant':'complete_deterministic_water_reporting','dependencies':{
            'atlas':{'path':'data/releases/v0.2.0','manifest_sha256':sha(BASE/'manifest.json')},
            'completion':{'path':'data/completion-releases/v0.1.0','manifest_sha256':sha(COMPLETION/'manifest.json')},
            'resolution':{'path':'data/resolution-releases/v0.4.0','manifest_sha256':sha(RESOLUTION/'manifest.json')}},
            'policy':{'support_space_exclusions':sorted(SUPPORT),'institutional_shared_main':['Hospital'],
                      'allocation_basis':'Fixed source design occupants; dedicated Kitchen/Laundry process program when unique; otherwise retained shared service',
                      'zone_gain_assignment':'unchanged; reporting does not place fixtures or gains',
                      'original_unknowns':'preserved in dependency releases'},
            'summary':{'active_program_records':len(programs),'source_only_water_gaps':sum(g['coverage_resolution_status']=='allocation_unknown' for g in gaps.values()),
                       'operational_water_gaps':0,'source_demand_paths':len(services),
                       'allocation_statuses':dict(sorted(Counter(s['allocation_status'] for s in services).items())),
                       'program_reporting_statuses':dict(sorted(Counter(r['reporting_status'] for r in reported).items())),
                       'reporting_schedule_shapes':len(shapes),'complete_simulation_readiness':False},
            'services':services,'programs':reported,'schedules':list(shapes.values()),
            'reference_programs':references}
    validate_packet(packet,data,completion)
    return packet


def validate_packet(packet, data, completion):
    excluded=set(load_json(ROOT/'sources/schedule-release-scope.json')['excluded_commercial_space_types'])
    expected={p['id'] for p in data['programs'] if p['source_space_type'] not in excluded}
    ids=[p['program_id'] for p in packet['programs']]
    if len(ids)!=len(set(ids)) or set(ids)!=expected:raise ValueError('Program inventory mismatch')
    original={d['path_id']:d for d in completion['draw_paths']}
    ids=[s['path_id'] for s in packet['services']]
    if len(ids)!=len(set(ids)) or set(ids)!=set(original):raise ValueError('Service inventory mismatch')
    schedules={s['id']:s for s in packet['schedules']}
    source_schedules={s['source_name']:s for s in completion['schedules']}
    services={s['path_id']:s for s in packet['services']}
    programs={p['id']:p for p in data['programs']}
    relationships=defaultdict(list)
    for s in services.values():
        weights=s['allocation_weights']
        if any(pid not in expected or not math.isfinite(w) or w<=0 for pid,w in weights.items()):raise ValueError('Invalid allocation weight')
        if weights and not math.isclose(math.fsum(weights.values()),1,rel_tol=1e-12):raise ValueError('Nonconserving allocation')
        if (s['allocation_status']=='retained_shared_service') != (not weights):raise ValueError('Shared allocation mismatch')
        d=original[s['path_id']]
        for field in ['building_type','template','end_use','source_schedule_name','target_temperature_degC']:
            if s[field]!=d[field]:raise ValueError('Source service field mismatch: '+field)
        recipe=source_schedules[d['source_schedule_name']]
        if (s['source_schedule_id']!=recipe['source_schedule']['id'] or
                s['equivalent_schedule_id']!=recipe['equivalent_schedule']['id'] or
                s['source_allocation_status']!=d['allocation_status'] or
                s['source_evidence_ids']!=d['evidence_ids']):raise ValueError('Source schedule/evidence mismatch')
        if d['rated_flow_per_area_m3_s_m2'] is not None:
            area=packet['reference_programs'][d['beneficiary_program_ids'][0]]['represented_area_m2']
            wanted=d['rated_flow_per_area_m3_s_m2']*area
        else:
            area=None;wanted=d['rated_flow_m3_s']
            if d.get('fixture_instances'):wanted*=math.fsum(x['multiplier'] for x in d['fixture_instances'])
        if s['reference_area_m2']!=area or not math.isclose(s['reference_rated_flow_m3_s'],wanted,rel_tol=1e-12,abs_tol=1e-16):
            raise ValueError('Source reference flow mismatch')
        if s['physical_fixture_locations']!=d['physical_fixture_locations']:raise ValueError('Physical fixture assignment changed')
        if s['allocation_status']=='source_assignment' and weights!=d['allocation_weights']:raise ValueError('Source allocation changed')
        if any(e not in completion['evidence'] for e in s['source_evidence_ids']):raise ValueError('Orphan source evidence')
        if any((programs[pid]['building_type'],programs[pid]['template'])!=(s['building_type'],s['template']) for pid in weights):raise ValueError('Cross-building allocation')
        relationships[s['building_type'],s['template']].append(s['path_id'])
    component_uses=defaultdict(dict)
    dates=[(dt.date(2000,1,1)+dt.timedelta(days=i)).strftime('%m-%d') for i in range(366)]
    validated_shapes=set()
    for p in packet['programs']:
        if p['building_service_path_ids']!=relationships[p['building_type'],p['template']]:raise ValueError('Building service relationship mismatch')
        original_program=programs[p['program_id']]
        if any(p[k]!=original_program[k] for k in ['building_type','template','program','source_space_type']):raise ValueError('Source program identity mismatch')
        if p['source_water_schedule_id']!=original_program['service_water_heating_schedule_id']:raise ValueError('Source program schedule mismatch')
        if p['reporting_schedule_id'] not in schedules:raise ValueError('Orphan reporting schedule')
        for c in p['components']:
            s=services.get(c['path_id'])
            if not s or s['allocation_weights'].get(p['program_id'])!=c['allocation_weight']:raise ValueError('Component allocation mismatch')
            if p['program_id'] in component_uses[c['path_id']]:raise ValueError('Duplicate component')
            component_uses[c['path_id']][p['program_id']]=c['allocation_weight']
        peak=p['reference_reporting_peak_flow_m3_s']
        if not math.isfinite(peak) or peak<0:raise ValueError('Invalid reporting peak flow')
        if not peak and any(services[c['path_id']]['reference_rated_flow_m3_s']*c['allocation_weight']*
                           source_schedules[services[c['path_id']]['source_schedule_name']]['peak_divisor']>0 for c in p['components']):
            raise ValueError('Reporting flow conservation failed: zero peak with positive draw')
        # Scale-independent cache still checks every program's compatible peak.
        signature=(p['reporting_schedule_id'],tuple((services[c['path_id']]['source_schedule_name'],
                   round(services[c['path_id']]['reference_rated_flow_m3_s']*c['allocation_weight']/peak,12) if peak else 0)
                   for c in p['components']))
        if signature in validated_shapes:continue
        normalized=schedules[p['reporting_schedule_id']]['rules'];peak=p['reference_reporting_peak_flow_m3_s']
        for day in DAYS:
            for date in dates:
                wanted=[0.0]*24
                for c in p['components']:
                    s=services[c['path_id']]
                    curve=profile(source_schedules[s['source_schedule_name']]['source_schedule']['rules'],day,date)
                    wanted=[a+s['reference_rated_flow_m3_s']*c['allocation_weight']*b for a,b in zip(wanted,curve)]
                actual=profile(normalized,day,date)
                if any(not math.isfinite(v) or not 0<=v<=1 for v in actual):raise ValueError('Invalid reporting schedule')
                if any(not math.isclose(a,peak*b,rel_tol=1e-11,abs_tol=1e-15) for a,b in zip(wanted,actual)):raise ValueError('Reporting flow conservation failed')
        validated_shapes.add(signature)
    for s in services.values():
        if component_uses[s['path_id']]!=s['allocation_weights']:raise ValueError('Incomplete service attribution')
    summary={'active_program_records':len(packet['programs']),
             'source_only_water_gaps':sum(g['coverage_resolution_status']=='allocation_unknown' for g in completion['missing_program_evidence']),
             'operational_water_gaps':sum(not p['reporting_schedule_id'] for p in packet['programs']),
             'source_demand_paths':len(services),
             'allocation_statuses':dict(sorted(Counter(s['allocation_status'] for s in services.values()).items())),
             'program_reporting_statuses':dict(sorted(Counter(r['reporting_status'] for r in packet['programs']).items())),
             'reporting_schedule_shapes':len(schedules),'complete_simulation_readiness':False}
    if summary!=packet['summary']:raise ValueError('Water reporting summary mismatch')


def validate_bundle(path=DEFAULT):
    path=Path(path);manifest=load_json(path/'manifest.json')
    actual={p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()}
    if actual!=set(manifest['files'])|{'manifest.json'}:raise ValueError('Water reporting inventory mismatch')
    for name,entry in manifest['files'].items():
        p=(path/name).resolve()
        if not p.is_relative_to(path.resolve()) or sha(p)!=entry['sha256'] or p.stat().st_size!=entry['size_bytes']:raise ValueError('Water reporting checksum/path mismatch')
    packet=load_json(path/'water-reporting.json')
    jsonschema.validate(packet,load_json(path/'schemas/water-reporting.schema.json'))
    for dependency in packet['dependencies'].values():
        if sha(ROOT/dependency['path']/'manifest.json')!=dependency['manifest_sha256']:raise ValueError('Water reporting dependency mismatch')
        dependency_root=ROOT/dependency['path']
        frozen=load_json(dependency_root/'manifest.json')
        for name,entry in frozen['files'].items():
            file=(dependency_root/name).resolve()
            if not file.is_relative_to(dependency_root.resolve()) or sha(file)!=entry['sha256']:
                raise ValueError('Water reporting dependency file checksum mismatch')
    if packet!=build():raise ValueError('Water reporting reproduction mismatch')
    if (manifest['summary']!=packet['summary'] or manifest['dependencies']!=packet['dependencies']
            or manifest['release_version']!=packet['release_version'] or manifest['schema_version']!=packet['schema_version']):
        raise ValueError('Water reporting manifest metadata mismatch')
    return packet


def freeze(target=DEFAULT):
    target=Path(target)
    if target.exists():raise ValueError('Never overwrite a frozen water reporting release')
    if verify_release(BASE):raise ValueError('Base integrity mismatch')
    packet=build();jsonschema.validate(packet,load_json(SCHEMA))
    dump_json(target/'water-reporting.json',packet)
    for name in ['schemas/water-reporting.schema.json','scripts/water_reporting.py',
                 'docs/adr/0009-complete-water-reporting-variant.md','sources/schedule-release-scope.json',
                 'sources/lock.json','sources/completion-evidence-lock.json',
                 'sources/licenses/openstudio-standards.txt','LICENSE']:
        dst=target/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dst)
    dump_json(target/'manifest.json',{'release_version':'0.1.0','schema_version':'0.1.0','generation_date':DATE,
              'dependencies':packet['dependencies'],'summary':packet['summary'],
              'files':{p.relative_to(target).as_posix():{'sha256':sha(p),'size_bytes':p.stat().st_size}
                       for p in sorted(target.rglob('*')) if p.is_file()}})
    return validate_bundle(target)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true');parser.add_argument('--target',type=Path,default=DEFAULT)
    args=parser.parse_args();packet=validate_bundle(args.target) if args.verify else freeze(args.target)
    print(packet['summary'])


if __name__=='__main__':main()
