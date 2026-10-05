"""Extract every finite source main/booster/laundry fixture branch without guessing beneficiaries."""
from pathlib import Path
import hashlib,collections
from scripts.common import ROOT,load_json as read,load_atlas
from scripts.fetch import verify_file
REV='c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907'

def build(data=None,lock_path=ROOT/'sources/completion-evidence-lock.json',cache_root=ROOT/'data/raw'):
    lock=read(lock_path); receipts=[r for r in lock['files'] if r['source_id']=='openstudio-standards'];receipt={r['path']:r for r in receipts}; CACHE=Path(cache_root)/'openstudio-standards'; DATE=lock['retrieval_date']; [verify_file(r,cache_root) for r in receipts]
    lockpaths={r['path'] for l in ['sources/lock.json','sources/water-evidence-lock.json'] for r in read(ROOT/l)['files'] if r.get('source_id')=='openstudio-standards'}
    data=data or load_atlas(ROOT/'data/releases/v0.2.0'); programs=data['programs']; mappings=data['mappings']; prov={r['id']:r for r in data['provenance']}; sfiles={r['id']:r for r in data['source_files']}
    historical=read(ROOT/'data/resolution-releases/v0.3.0/resolutions.json'); known={r['record_id'] for r in historical['resolutions'] if r['field']=='service_water_heating_schedule_id'}; missing=[dict(record_id=p['id']) for p in programs if p['service_water_heating_schedule_id'] is None and p['id'] not in known and p['source_space_type'] not in {'Attic','Plenum','Basement'}]; missingids={r['record_id'] for r in missing}; buildings=sorted({r['building_type'] for r in programs})
    RECIPE='lib/openstudio-standards/standards/Standards.ServiceWaterHeating.rb'; MODEL='lib/openstudio-standards/prototypes/common/objects/Prototype.Model.rb'; HELPER='lib/openstudio-standards/service_water_heating/create_water_use.rb'; LOOP='lib/openstudio-standards/service_water_heating/create_water_heating_loop.rb'
    def proof(path,locator,value,unit,transformation,note):
     r=receipt[path]
     return dict(source_locator=path+'#'+locator,source_revision=REV,source_file_sha256=r['sha256'],original_value=value,original_unit=unit,transformation=transformation,extraction_date=DATE,interpretation_note=note)
    inputs={}
    for rel in sorted(receipt):
     if not rel.endswith('prototype_inputs.json'):continue
     p=CACHE/rel
     for i,r in enumerate(read(p)['prototype_inputs']):
      if r['building_type'] in buildings:
       inputs[r['building_type'],r['template']]=(rel,i,r)
    space_tables={}
    for rel in sorted(receipt):
     if not rel.endswith('spc_typ.json'):continue
     p=CACHE/rel
     for i,r in enumerate(read(p)['space_types']):
      space_tables[r['template'],r['building_type'],r['space_type']]=(p.relative_to(CACHE).as_posix(),i,r)
    SCHEDULE='lib/openstudio-standards/standards/ashrae_90_1/data/ashrae_90_1.schedules.json'
    schedule_rows=read(CACHE/SCHEDULE)['schedules']; scheds=collections.defaultdict(list)
    for i,r in enumerate(schedule_rows):scheds[r['name']].append((i,r))
    source_schedules=data['schedules']
    fnames={p['id']: sorted({n for m in mappings if m['program_id']==p['id'] for n in m['source_space_names']}) for p in programs}
    def attrproof(p):
     pr=prov[p['provenance_id']];sf=sfiles[pr['source_file_id']]
     return proof(sf['path'],pr['locator'],{k:v for k,v in p['source_attributes'].items() if 'water' in k},'mixed original source units; gal/h, gal/h/ft2, degF', 'Keep null and empty-string fields unchanged; evaluate source branch separately', 'Null and empty source fields are unknown/reporting state; no zero physical water assumption')
    def source_schedule(name):
     if name is None:return None
     rows=scheds[name]
     if not rows:return dict(source_name=name,status='not_found',source_rows=[])
     maxima=[v for _,r in rows for v in r['values']]
     return dict(source_name=name,status='source_rules_extracted',source_order=[i for i,r in rows],source_rows=[r for i,r in rows],peak_divisor=max(maxima),matching_atlas_schedule_ids=[s['id'] for s in source_schedules if s['source_name']==name], evidence=[proof(SCHEDULE,'/schedules/'+str(i),r,'dimensionless draw fraction (source units retained)', 'No rule sorting or date truncation; optional equivalent divides values by max and multiplies rated flow by max', 'Rules, design days, source dates and source order retained') for i,r in rows])
    paths=[]; analyses=[]; gaps=[]; usedschedules=set()
    for (b,t),(ip,ii,r) in sorted(inputs.items()):
     bp='lib/openstudio-standards/prototypes/common/buildings/Prototype.'+({'HighriseApartment':'HighRiseApartment'}.get(b,b))+'.rb'
     lines=(CACHE/bp).read_text().splitlines(); lineno=next(i+1 for i,l in enumerate(lines) if 'def model_custom_swh_tweaks' in l)
     block='\n'.join(lines[lineno-1:next((i for i in range(lineno,len(lines)) if lines[i].startswith('  def ') or lines[i]=='end'),len(lines))])
     assert 'create_water_use(' not in (CACHE/bp).read_text()
     active=[p for p in programs if p['building_type']==b and p['template']==t]
     if r['main_water_heater_volume'] is None: branch='no_main_loop'
     elif b=='LargeOffice': branch='large_office_core_spaces'
     elif b=='RetailStripmall': branch='stripmall_reference_returns_true' if t.startswith('DOE Ref') else 'stripmall_individual_space_draw'
     elif r['main_service_water_peak_flowrate'] is not None: branch='lumped_main_draw'
     else: branch='space_type_main_draw'
     a=dict(building_type=b,template=t,prototype_locator=ip+'#/prototype_inputs/'+str(ii),main_branch=branch,main_condition_original=dict(main_water_heater_volume=r['main_water_heater_volume'],main_service_water_peak_flowrate=r['main_service_water_peak_flowrate']),booster_enabled=r['booster_water_heater_volume'] is not None,laundry_enabled=r['laundry_water_heater_volume'] is not None,prototype_original_water_fields={k:v for k,v in r.items() if 'water' in k},custom_swh_tweaks=dict(source_locator=bp+'#L'+str(lineno),source_text=block,classification='heater_parameters_only' if 'update_waterheater' in block else 'returns_true_without_changes'),evidence=[proof(ip,'/prototype_inputs/'+str(ii),r,'mixed source units', 'Evaluate main then booster then laundry source branches independently', 'Volumes gate loop creation; heater placement does not assign fixture beneficiaries'),proof(bp,'L'+str(lineno),block,'Ruby code','Read custom methods and delegated heater parameter methods; no custom fixture creation', 'Ambient thermal-zone and heater losses are energy semantics, not fixture placement')])
     analyses.append(a)
     if branch=='stripmall_individual_space_draw':
      spaces=['LGstore1','SMstore1','SMstore2','SMstore3','LGstore2','SMstore5','SMstore6']
      schedules=['RetailStripmall Type1_SWH_SCH','RetailStripmall Type1_SWH_SCH','RetailStripmall Type2_SWH_SCH','RetailStripmall Type2_SWH_SCH','RetailStripmall Type3_SWH_SCH','RetailStripmall Type3_SWH_SCH','RetailStripmall Type3_SWH_SCH']
      for n,schedule in sorted(zip(spaces,schedules)):
       usedschedules.add(schedule)
       beneficiaries=sorted(p['id'] for p in active if n in fnames[p['id']])
       assert len(beneficiaries)==1
       paths.append(dict(path_id=b+'|'+t+'|main|'+n,building_type=b,template=t,end_use='main',source_branch=branch,source_schedule_name=schedule,rated_flow_m3_s=0.03*0.003785411784/60,rated_flow_per_area_m3_s_m2=None,original_flow=0.03,original_flow_unit='US gal/min',physical_fixture_locations=[n],beneficiary_program_ids=beneficiaries,allocation_status='exact_source_space_tag',target_temperature_degC=(r['main_water_use_temperature']-32)/1.8,evidence=[proof(RECIPE,'L78-L113',dict(space=n,schedule=schedule,flow=0.03),'US gal/min','Use seven explicit zipped schedule-space fixture calls; multiply by 0.003785411784/60','Do not add other strips or copy Type1 to Type2/Type3')]))
     if branch in ['lumped_main_draw','large_office_core_spaces']:
      physical=['Core_bottom','Core_mid','Core_top'] if branch=='large_office_core_spaces' else []
      beneficiary=sorted({p['id'] for p in active if set(fnames[p['id']])&set(physical)})
      flow=r['main_service_water_peak_flowrate']
      paths.append(dict(path_id=b+'|'+t+'|main',building_type=b,template=t,end_use='main',source_branch=branch,source_schedule_name=r['main_service_water_flowrate_schedule'],rated_flow_m3_s=flow*0.003785411784/60,rated_flow_per_area_m3_s_m2=None,flow_instance_count=len(physical) if physical else 1,physical_fixture_locations=physical,beneficiary_program_ids=beneficiary,allocation_status='exact_source_space_tag' if beneficiary else 'building_service_unallocated',target_temperature_degC=(r['main_water_use_temperature']-32)/1.8,original_flow=flow,original_flow_unit='US gal/min',evidence=[proof(ip,'/prototype_inputs/'+str(ii)+'/main_service_water_peak_flowrate',flow,'US gal/min','Multiply by 0.003785411784/60 to obtain m3/s per fixture; preserve distinct three-core instances', 'No area scaling in this branch; main heater location ignored for beneficiaries'),proof(RECIPE,'L52-L65' if physical else 'L119-L130','create_water_use(...space: core)' if physical else 'create_water_use(...without space)','Ruby code','Use explicit fixture-space argument only', 'LargeOffice repeated source core draws map to office; a lump has no beneficiary allocation')]))
      usedschedules.add(r['main_service_water_flowrate_schedule'])
     if branch=='space_type_main_draw':
      for p in active:
       attrs=p['source_attributes'];q=attrs.get('service_water_heating_peak_flow_per_area');total=attrs.get('service_water_heating_peak_flow_rate')
       qnum=q if type(q) in (float,int) else 0;totalnum=total if type(total) in (float,int) else 0
       if qnum<0.00001 and totalnum<0.00001: continue
       note='Default is_flow_per_area=true; source computes area times space multiplier once. Explicit table gal/h is alternate helper branch and not simultaneously added. Fixture helper call omits physical space.'
       paths.append(dict(path_id=b+'|'+t+'|main|'+p['id'],building_type=b,template=t,end_use='main',source_branch=branch,source_schedule_name=attrs.get('service_water_heating_schedule'),rated_flow_m3_s=None,rated_flow_per_area_m3_s_m2=qnum*0.003785411784/3600/0.09290304 if type(q) in (int,float) else None,original_flow=q,original_flow_unit='US gal/h/ft2',alternate_original_total=total,alternate_original_total_unit='US gal/h (unused default path)',source_space_names=fnames[p['id']],physical_fixture_locations=[],beneficiary_program_ids=[p['id']],allocation_status='exact_source_space_type_tag',target_temperature_degC=(attrs['service_water_heating_target_temperature']-32)/1.8 if type(attrs.get('service_water_heating_target_temperature')) in (int,float) else None,evidence=[attrproof(p),proof(RECIPE,'L133-L186 and L287-L341','default is_flow_per_area=true; if both .to_f < 0.00001 return nil; create_water_use(name: space.name,...without space)','Ruby code','Convert flow with factor 0.003785411784/3600/0.09290304; no geometry assumed',note)],interpretation_note=note))
       usedschedules.add(attrs.get('service_water_heating_schedule'))
     for use,prefix in [('booster','booster'),('laundry','laundry')]:
      if r[prefix+'_water_heater_volume'] is None:continue
      flow=r[prefix+'_service_water_peak_flowrate'];temp=r[prefix+'_water_use_temperature'];schedule=r[prefix+'_service_water_flowrate_schedule'];usedschedules.add(schedule)
      paths.append(dict(path_id=b+'|'+t+'|'+use,building_type=b,template=t,end_use=use,source_branch='volume_not_null',source_schedule_name=schedule,rated_flow_m3_s=flow*0.003785411784/60 if type(flow) in (int,float) else None,rated_flow_per_area_m3_s_m2=None,original_flow=flow,original_flow_unit='US gal/min',target_temperature_degC=(temp-32)/1.8 if type(temp) in (int,float) else None,physical_fixture_locations=[],beneficiary_program_ids=[],allocation_status='building_service_unallocated',reported_heater_space_name=r.get(prefix+'_water_heater_space_name'),evidence=[proof(ip,'/prototype_inputs/'+str(ii)+'/'+prefix+'_service_water_peak_flowrate',flow,'US gal/min','Multiply by 0.003785411784/60; preserve original null','Loop volume enables draw. Heater location or laundry name alone cannot establish beneficiary allocation'),proof(RECIPE,'L193-L217' if use=='booster' else 'L222-L246','create_water_use(name: '+use+',...without space)','Ruby code','Keep source draw separate pending supported program allocation','Booster heat exchanger couples energy to main; do not duplicate this fixture draw as another main draw')]))
     for p in active:
      if p['id'] not in missingids:continue
      attrs=p['source_attributes'];status=''
      if branch=='no_main_loop' and not a['booster_enabled'] and not a['laundry_enabled']:status='source_no_swh_end_use_for_building_template'
      elif branch=='space_type_main_draw':status='source_no_local_main_fixture_draw'
      elif branch=='large_office_core_spaces' and not set(fnames[p['id']])&set(['Core_bottom','Core_mid','Core_top']):status='source_no_local_main_fixture_outside_core'
      else:status='unallocated_building_main_draw'
      gaps.append(dict(program_id=p['id'],building_type=b,template=t,source_space_type=p['source_space_type'],source_space_names=fnames[p['id']],classification=status,source_schedule_name=None,normalized_physical_flow=None,building_service_paths=[d['path_id'] for d in paths if d['building_type']==b and d['template']==t and d['allocation_status']=='building_service_unallocated'],evidence=[attrproof(p),a['evidence'][0],proof(RECIPE,'L12; L144-L157; L287-L289' if branch=='space_type_main_draw' else 'L12; L52-L130','branch '+branch,'Ruby code','Interpret source control flow separately from null physical inputs','Source no local demand means no model fixture created for this source program; it does not mean real plumbing or all beneficiary demand is absent')],interpretation_note='No occupancy schedule copy. Preserve original unknown fields. Separate any unallocated main/booster/laundry demand; review beneficiary allocation before treating a local no-draw proof as complete program-level sanitary service coverage.'))
    # Highrise DOE is unsupported by prototype constructor and not present in inputs; classify only if active missing includes it.
    for m in missing:
     if m['record_id'] not in {g['program_id'] for g in gaps}:
      p=next(p for p in programs if p['id']==m['record_id'])
      gaps.append(dict(program_id=p['id'],building_type=p['building_type'],template=p['template'],source_space_type=p['source_space_type'],classification='unsupported_source_prototype_pair',source_schedule_name=None,normalized_physical_flow=None,evidence=[proof(MODEL,'L17-L25','HighriseApartment DOE reference returns false','Ruby code','Preserve unsupported source pair as unknown','No HighriseApartment DOE reference source; do not extrapolate code-vintage template')]))
    assert len(gaps)==485,(len(gaps),len(missing))
    for g in gaps:
     g['coverage_resolution_status']='allocation_unknown' if g.get('building_service_paths') or g['classification']=='unsupported_source_prototype_pair' else 'source_proved_no_modeled_program_draw'
     g['zero_schedule_eligible']=g['coverage_resolution_status']=='source_proved_no_modeled_program_draw'
    for d in paths:
     d['matching_atlas_schedule_ids']=[s['id'] for s in source_schedules if s['source_name']==d['source_schedule_name']]
     d['allocation_weights']={pid:1 for pid in d['beneficiary_program_ids']} if len(d['beneficiary_program_ids'])==1 else {}
     if d['source_branch']=='large_office_core_spaces':
      instances={}
      for m in mappings:
       if m['building_type']==d['building_type'] and m['template']==d['template']:
        original=prov[m['provenance_id']]['fields']['source_space_names']['original_value']
        for sp in original:
         if sp['name'] in d['physical_fixture_locations']:
          if sp['name'] in instances: assert instances[sp['name']]==sp
          instances[sp['name']]=sp
      d['fixture_instances']=[instances[n] for n in sorted(instances)]
      assert len(d['fixture_instances'])==3
    # Correct source ranges to exact pinned line numbers rather than imprecise method spans.
    replacements={'L52-L65':'L51-L63','L119-L130':'L112-L121','L78-L113':'L76-L110','L133-L186 and L287-L341':'L122-L171 and L236-L307','L193-L217':'L177-L193','L222-L246':'L197-L217','L12; L144-L157; L287-L289':'L13; L136-L148; L276-L278','L12; L52-L130':'L13; L51-L121'}
    for container in analyses+paths+gaps:
     for e in container.get('evidence',[]):
      for before,after in replacements.items():
       if e['source_locator']==RECIPE+'#'+before:e['source_locator']=RECIPE+'#'+after

    geometry_audits={}
    for m in mappings:
     if m['building_type'] not in buildings:continue
     sf=sfiles[prov[m['provenance_id']]['source_file_id']]
     if sf['path'] in geometry_audits:continue
     raw=(CACHE/sf['path']).read_bytes()
     assert hashlib.sha256(raw).hexdigest()==sf['sha256']
     blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
     assert 'OS:WaterUse' not in raw.decode('utf-8-sig')
     geometry_audits[sf['path']]=dict(source_locator=sf['path']+'#whole-file object-kind inventory',source_revision=REV,source_file_sha256=sf['sha256'],git_blob_sha1=blob,original_value='0 OS:WaterUse object declarations',original_unit='object count',transformation='Verify immutable geometry SHA256; inspect entire source text for OS:WaterUse object kinds',extraction_date=DATE,interpretation_note='No embedded fixture draws in source geometry; model_add_swh creates the reviewed source demand paths')
    for a in analyses:
     geopaths=sorted({sfiles[prov[m['provenance_id']]['source_file_id']]['path'] for m in mappings if m['building_type']==a['building_type'] and m['template']==a['template']})
     a['geometry_embedded_draw_audit']=[geometry_audits[p] for p in geopaths]
     assert geopaths,(a['building_type'],a['template'])
    assert {g['program_id'] for g in gaps}==missingids
    assert len({d['path_id'] for d in paths})==len(paths)
    for d in paths: assert d['source_schedule_name'] in scheds,d['path_id']
    report=dict(schema_version='0.1.0',source_revision=REV,extraction_date=DATE,base_atlas='v0.2.0',interpretation='Read-only static branch extraction of pinned official Ruby code and JSON. No OpenStudio execution or fixture beneficiary guessing. Source unknown fields remain null/empty. Actual floor area belongs to geometry atlas.',summary=dict(building_types=len(buildings),building_template_paths=len(analyses),demand_rules=len(paths),missing_programs=len(gaps),gap_classifications=dict(collections.Counter(g['classification'] for g in gaps)),unallocated_service_rules=sum(d['allocation_status']=='building_service_unallocated' for d in paths),schedule_names=len(usedschedules)),branch_analyses=analyses,draw_paths=paths,missing_program_evidence=gaps,schedules=[source_schedule(s) for s in sorted(usedschedules) if s is not None],required_additional_sources=[r for r in receipts if r['path'] not in lockpaths],source_receipts=receipts,execution_policy=['Never overwrite immutable raw cache. Verify source SHA256 and pinned revision before extraction.','Per-space main branch uses table flow per area with represented floor area and multiplier applied once; deduplicate source space identities across HVAC services.','Core main branch creates three separate same-rated-flow fixtures; retain source core multiplier semantics and audit full model before magnitude export.','Lumped, booster and laundry draws remain building services until source beneficiary evidence is sufficient; no occupancy-copy rule.','Preserve all source schedule rows dates selectors design days source order; normalize Q and f together; conservation interval-by-interval.','No-local-fixture proof closes only local source-path absence; unknown sanitary beneficiary allocations remain explicit.'])
    report['summary']['coverage_resolution_status']=dict(collections.Counter(g['coverage_resolution_status'] for g in gaps))
    report['summary']['new_source_schedule_names_without_atlas_id']=[s['source_name'] for s in report['schedules'] if not s['matching_atlas_schedule_ids']]
    assert all(len(s['matching_atlas_schedule_ids'])<=1 for s in report['schedules'])
    report['summary']['missing_gap_resolution_by_building']={b:dict(collections.Counter(g['coverage_resolution_status'] for g in gaps if g['building_type']==b)) for b in sorted({g['building_type'] for g in gaps})}
    report['summary']['verified_geometry_files_without_embedded_water_use_objects']=len(geometry_audits)

    return report
