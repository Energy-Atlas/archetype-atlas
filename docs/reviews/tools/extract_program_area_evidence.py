import json, math
from pathlib import Path
from collections import defaultdict, Counter
from scripts.fetch import verify_file, fetch_file
from scripts.semantics import spaces, osm_objects
from scripts.water_reporting import floor_areas
root=Path(__file__).resolve().parents[3]; base=root/'data/releases/v0.2.0'
(root/'build/reviews').mkdir(parents=True, exist_ok=True)
for rule in json.loads((root/'docs/reviews/source-default-lock.json').read_text() )['files']:
 fetch_file(rule, root/'data/raw')
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
programs=load(base/'programs.json'); selection=load(root/'sources/selection.json')
sources={r['path']:r for r in load(base/'source_files.json') if r['source_id']=='openstudio-standards'}
by_context=defaultdict(list)
for p in programs:by_context[p['building_type'],p['template']].append(p)
out=[]; cache={}; unmatched=[]
for t in selection['templates']:
 for model in t['models']:
  path=model['geometry']; source=sources[path]
  if path not in cache:
   text=verify_file(source,root/'data/raw').read_text(encoding='utf-8-sig')
   ss=spaces(text)
   if any(s['part_of_total_floor_area']=='' for s in ss):
    objs=osm_objects(text)
    assert next(o['fields']['Version Identifier'] for o in objs if o['kind']=='OS:Version')=='2.2.1'
    assert not any(o['kind'] in {'OS:AirLoopHVAC:ReturnPlenum','OS:AirLoopHVAC:SupplyPlenum'} for o in objs)
    for s in ss:
     s['part_of_total_floor_area_original']=s['part_of_total_floor_area']
     if s['part_of_total_floor_area']=='':s['part_of_total_floor_area']='Yes'
   cache[path]=(ss,floor_areas(text))
  ss,areas=cache[path]; counted=[s for s in ss if s['part_of_total_floor_area']=='Yes']
  assert all(s['handle'] in areas and s['multiplier']>0 for s in counted)
  complete_flags=all(s['part_of_total_floor_area'] in {'Yes','No'} for s in ss)
  denominator=math.fsum(areas[s['handle']]*s['multiplier'] for s in counted) if complete_flags else None
  if denominator is not None:assert denominator>0
  prs=by_context[model['building_type'],t['template']]
  lookup={(p['source_building_type'],p['source_space_type']):p for p in prs}
  groups=defaultdict(list)
  for s in ss:
   sb=s['source_building_type'] or ('Any' if s['source_space_type']=='Plenum' else '')
   p=lookup.get((sb,s['source_space_type']))
   if not p:
    if s in counted:unmatched.append((model['building_type'],t['template'],s['name']))
    continue
   groups[p['id']].append(s)
  rows=[]
  for p in sorted(prs,key=lambda p:p['source_space_type']):
   matches=groups[p['id']]; assert matches
   counted_matches=[s for s in matches if s['part_of_total_floor_area']=='Yes']
   area=math.fsum(areas[s['handle']]*s['multiplier'] for s in counted_matches)
   rows.append({'program_id':p['id'],'source_building_type':p['source_building_type'],
     'source_space_type':p['source_space_type'],'share_percent':100*area/denominator if denominator is not None and counted_matches else None,
     'area_status':'derived' if denominator is not None and counted_matches else ('not_counted' if denominator is not None else 'unresolved_floor_flags'),
     'represented_counted_area_m2':area,'counted_space_handles':[s['handle'] for s in counted_matches],
     'uncounted_space_handles':[s['handle'] for s in matches if s['part_of_total_floor_area']!='Yes']})
  if denominator is not None:assert math.isclose(math.fsum(r['represented_counted_area_m2'] for r in rows),denominator,rel_tol=1e-10), (model['building_type'],t['template'])
  out.append({'building_type':model['building_type'],'template':t['template'],'source_family':t['family'],
   'geometry':path,'sha256':source['sha256'],'source_revision':source['version'],
   'denominator_m2':denominator,'rows':rows})
assert not unmatched,unmatched
(root/'build/reviews/program-area-evidence.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('Verified model contexts:',len(out),'unique geometry files:',len(cache),'program rows:',sum(len(m['rows']) for m in out),'unmatched counted spaces:',len(unmatched))
for m in out:
 if m['template']=='90.1-2013' and m['building_type'] in ['MediumOffice','Outpatient','FullServiceRestaurant','RetailStandalone','MidriseApartment','LargeOffice']:
  print(m['building_type'],round(m['denominator_m2'],3) if m['denominator_m2'] is not None else 'U',[(r['source_space_type'],round(r['share_percent'],3) if r['share_percent'] is not None else r['area_status']) for r in m['rows']])
