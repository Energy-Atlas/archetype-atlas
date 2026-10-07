"""Approved source-area mixtures, preserving load trajectories and calendar rules."""
import copy
import datetime as dt
import math
from collections import defaultdict
from scripts.common import load_json
from scripts.definition_contract import DefinitionBundle, DefinitionError, evidence, parameter, record, stable_id
from scripts.fetch import fetch_file
from scripts.semantics import spaces, osm_objects, profile, DAY_TYPES
from scripts.water_reporting import floor_areas


def represented_weights(rows):
    included=[r for r in rows if r['area_status']=='derived' and r['represented_area_m2']>0
              and not any(x in r['source_space_type'].lower() for x in ('basement','attic'))]
    denominator=math.fsum(r['represented_area_m2'] for r in included)
    return {r['program_id']:r['represented_area_m2']/denominator for r in included} if denominator else {}


def extract_areas(context):
    result={};cache={}
    sources={r['path']:r for r in context.atlas['source_files'] if r['source_id']=='openstudio-standards'}
    programs=defaultdict(list)
    for p in context.atlas['programs']:programs[p['building_type'],p['template']].append(p)
    for template in load_json(context.root/'sources/selection.json')['templates']:
        for model in template['models']:
            family=model['building_type'];key=(family,template['template'])
            if context.scope=='pilot' and family!='MediumOffice':continue
            path=model['geometry'];source=sources[path]
            if path not in cache:
                text=fetch_file(source,context.root/'data/raw').read_text(encoding='utf-8-sig')
                ss=spaces(text)
                if any(s['part_of_total_floor_area']=='' for s in ss):
                    # The version-specific default is source evidence, not an atlas guess.
                    default_lock=load_json(context.root/'docs/reviews/source-default-lock.json')
                    for descriptor in default_lock['files']:
                        fetch_file(descriptor,context.root/'data/raw')
                    objs=osm_objects(text)
                    if next(o['fields']['Version Identifier'] for o in objs if o['kind']=='OS:Version')!='2.2.1':
                        raise DefinitionError('Unresolved OSM counted-area default')
                    if any(o['kind'] in {'OS:AirLoopHVAC:ReturnPlenum','OS:AirLoopHVAC:SupplyPlenum'} for o in objs):
                        raise DefinitionError('Implicit area flag with plenum needs source default resolution')
                    for s in ss:
                        if s['part_of_total_floor_area']=='':s['part_of_total_floor_area']='Yes'
                if any(s['part_of_total_floor_area'] not in {'Yes','No'} or s['multiplier']<=0 for s in ss):
                    raise DefinitionError('Invalid source counted-area flag or multiplier')
                cache[path]=(ss,floor_areas(text))
            ss,areas=cache[path];lookup={(p['source_building_type'],p['source_space_type']):p for p in programs[key]}
            grouped=defaultdict(list)
            for s in ss:
                source_building=s['source_building_type'] or ('Any' if s['source_space_type']=='Plenum' else '')
                p=lookup.get((source_building,s['source_space_type']))
                if not p:
                    if s['part_of_total_floor_area']=='Yes':raise DefinitionError('Unmatched counted source space')
                    continue
                grouped[p['id']].append(s)
            rows=[]
            for p in programs[key]:
                matches=grouped[p['id']]
                if not matches:raise DefinitionError('Source program has no geometry evidence')
                counted=[s for s in matches if s['part_of_total_floor_area']=='Yes']
                area=math.fsum(areas[s['handle']]*s['multiplier'] for s in counted)
                rows.append({'program_id':p['id'],'source_space_type':p['source_space_type'],
                    'source_building_type':p['source_building_type'],
                    'represented_area_m2':area,'area_status':'derived' if counted else 'non_counted',
                    'source_file_id':source['id'],'geometry_path':path,
                    'space_handles':[s['handle'] for s in counted],
                    'uncounted_space_handles':[s['handle'] for s in matches if s not in counted]})
            result[key]=rows
    return result


def mix_schedule(schedules,weights,factors=None,normalization=1):
    factors=factors or [1]*len(weights)
    if not schedules or len(schedules)!=len(weights) or len(factors)!=len(weights):
        raise DefinitionError('Mixture vector lengths differ')
    if any(f is None or (s is None and f!=0) for s,f in zip(schedules,factors)):
        return None
    if any(s is not None and 'rules' not in s for s in schedules):
        return None # Annual realizations require an explicitly compatible adapter, not calendar transplantation.
    boundaries={dt.date(2000,1,1),dt.date(2001,1,1)}
    for schedule in schedules:
        for rule in (schedule or {}).get('rules',[]):
            boundaries.add(dt.date.fromisoformat('2000-'+rule['start_date'][5:10]))
            end=dt.date.fromisoformat('2000-'+rule['end_date'][5:10])+dt.timedelta(days=1)
            boundaries.add(end)
    rules=[];bounds=sorted(boundaries)
    for start,end in zip(bounds,bounds[1:]):
        # Aggregate selectors must precede explicit weekdays: source semantics use
        # the last matching specific rule, and Wkdy also matches Mon through Fri.
        for day in ['Default','Wkdy','Wknd']+sorted(DAY_TYPES-{'DummySmrDsn','Default','Wkdy','Wknd'}):
            series=[]
            try:
                for s,f in zip(schedules,factors):
                    series.append(profile(s['rules'],day,start.strftime('%m-%d')) if f else [0]*24)
            except ValueError:return None
            values=[math.fsum(w*f*series[i][h] for i,(w,f) in enumerate(zip(weights,factors)))/normalization
                    if normalization else 0 for h in range(24)]
            rules.append({'day_types':day,'start_date':start.isoformat(),'end_date':(end-dt.timedelta(days=1)).isoformat(),
                          'values':values if len(set(values))>1 else values[:1], 'source_index':len(rules)})
    row={'rules':rules,'units':next((s.get('units','1') for s in schedules if s),'1'),
         'schedule_type':next((s.get('schedule_type','fraction') for s in schedules if s),'fraction'),
         'time_resolution_minutes':60,'derivation':'composed','calendar':'source rule calendar; leap-day inspection supported'}
    row['id']=stable_id('mixed-schedule',row)
    return row


def recipe_groups(family,names):
    from scripts.common import ROOT
    policy=load_json(ROOT/'sources/program-composition-policy.json')
    rule=next((r for r in policy['recipes'] if r['building_type']==family),{})
    available={n for n in names if not any(t in n.lower() for t in ('basement','attic'))}
    departments={key:[n for n in members if n in available] for key,members in rule.get('departments',{}).items()}
    departments={k:v for k,v in departments.items() if len(v)>1}
    exclusions=set(rule.get('general_exclusions',[]))
    general=sorted(available-exclusions) if rule.get('general',False) else []
    return {'departments':departments,'general':general if len(general)>1 else []}


def compose(context,programs):
    bundle=DefinitionBundle();areas=extract_areas(context)
    schedules={s['id']:s for s in programs['schedules']}
    source_map={s['id']:s for s in context.atlas['programs']}
    contexts=defaultdict(list)
    for row in programs['programs']:
        row['available_details']=['SourcePrograms']
        contexts[row['building_type'],row['template'],row['evidence_view']].append(row)
    # A reviewed view substitutes overlays into the entire source context.
    # An unchanged leaf still contributes its area and its source load trajectory.
    for (family,template,view),leaves in list(contexts.items()):
        if view!='reviewed':continue
        overlays={r['source_definition_id']:r for r in leaves}
        contexts[family,template,view]=[overlays.get(r['id'],r)
            for r in contexts[family,template,'source']]
    for (family,template,view),leaves in contexts.items():
        eligible=represented_weights(areas[family,template])
        by_name={source_map[r['source_id']]['source_space_type']:r for r in leaves if r['source_id'] in eligible}
        grouping=recipe_groups(family,list(by_name))
        groups=[('DepartmentMixes',name,names) for name,names in grouping['departments'].items()]
        if grouping['general']:groups.append(('GeneralMix','General_Mixed_'+family,grouping['general']))
        if family in {'LargeHotel','SmallHotel'} and grouping['general']:
            groups.extend(('GeneralMix',name,names) for name,names in grouping['departments'].items()
                          if 'Corridor' in name)
        for mode in ('DepartmentMixes','GeneralMix'):
            mode_groups=[g for g in groups if g[0]==mode]
            if not mode_groups:continue
            covered={n for _,_,names in mode_groups for n in names}
            for name,leaf in by_name.items():
                if name not in covered and mode not in leaf['available_details']:leaf['available_details'].append(mode)
        for mode,name,names in groups:
            members=[by_name[n] for n in names];denominator=math.fsum(eligible[m['source_id']] for m in members)
            weights=[eligible[m['source_id']]/denominator for m in members]
            source={'id':stable_id('composition-source',{'family':family,'template':template,'view':view,'mode':mode,'name':name}),
                    'building_type':family,'template':template,'source_family':members[0]['source_family']}
            row=record('program',source,name,derivation='composed')
            if view=='reviewed':
                original=dict(source,id=stable_id('composition-source',{'family':family,'template':template,
                    'view':'source','mode':mode,'name':name}))
                row['source_definition_id']=record('program',original,name,derivation='composed')['id']
            row.update(evidence_view=view,detail=mode,available_details=[mode],loads=[],
                       service_ids=sorted({sid for m in members for sid in m['service_ids']}),
                       required_inputs=['floor_area'],optional=False)
            area_map={a['program_id']:a for a in areas[family,template]}
            recipe={'id':stable_id('composition',source),'building_type':family,'template':template,
                    'evidence_view':view,'mode':mode,'name':name,
                    'members':[{'program_id':m['id'],'source_program_id':m['source_id'],'weight':w,
                         'represented_area_m2':area_map[m['source_id']]['represented_area_m2'],
                         'source_geometry_file_id':area_map[m['source_id']]['source_file_id']}
                         for m,w in zip(members,weights)],'method':'ADR 0012; unrounded represented area; pointwise setpoints and conserved load trajectories'}
            ev=evidence(context,None,'composition/'+recipe['id'],recipe['members'],'m2; dimensionless weights',
                        'w_i=A_i/sum(A); q=sum(w_i*d_i*s_i(t)); T=sum(w_i*T_i(t))',
                        'Approved experimental approximation; any required unknown propagates.')
            bundle['provenance'].append(ev);row['evidence_ids']=[ev['id']];row['composition_id']=recipe['id']
            quantities=sorted({l['quantity'] for m in members for l in m['loads']})
            for quantity in quantities:
                groups_by_member=[[l for l in m['loads'] if l['quantity']==quantity] for m in members]
                if any(len(items)!=1 for items in groups_by_member):
                    # Keep source components rather than pretending unknown/no draw is zero.
                    row.setdefault('unresolved_loads',[]).append({'quantity':quantity,'reason':'missing or multiple source demands; source member references retained'})
                    continue
                loads=[items[0] for items in groups_by_member]
                compatible=all(l['basis']=='floor_area' and l['unit']==loads[0]['unit'] for l in loads)
                values=[l['value'] for l in loads]
                density=math.fsum(w*d for w,d in zip(weights,values)) if compatible and all(v is not None for v in values) else None
                mixed=mix_schedule([schedules.get(l['schedule_id']) for l in loads],weights,values,density or 1) if density is not None else None
                if mixed:
                    mixed['evidence_ids']=[ev['id']]
                    mixed['id']=stable_id('mixed-schedule',mixed)
                    bundle['schedules'].append(mixed)
                demand=parameter(density,loads[0]['unit'],ev['id'],required_inputs=['floor_area'])
                demand.update(quantity=quantity,basis='floor_area',schedule_id=mixed['id'] if mixed else None,
                              demand_id=stable_id('mixed-demand',{'composition':recipe['id'],'quantity':quantity}),
                              scope='composed_program',source_components=[{'program_id':m['id'],'weight':w,'load':l} for m,w,l in zip(members,weights,loads)],
                              thermal_effects={'method':'evaluate each source component effect on its conserved trajectory; do not independently average fractions'})
                row['loads'].append(demand)
            for field in ('heating_setpoint_schedule_id','cooling_setpoint_schedule_id','activity_schedule_id'):
                refs=[m['parameters'][field]['value'] for m in members]
                mixed=mix_schedule([schedules.get(ref) for ref in refs],weights)
                if mixed:
                    mixed['evidence_ids']=[ev['id']]
                    mixed['id']=stable_id('mixed-schedule',mixed)
                    bundle['schedules'].append(mixed)
                row['parameters'][field]=parameter(mixed['id'] if mixed else None,'schedule reference',ev['id'])
            bundle['programs'].append(row);bundle['compositions'].append(recipe)
    return DefinitionBundle().merge(bundle)
