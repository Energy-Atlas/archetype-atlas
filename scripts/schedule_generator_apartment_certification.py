"""Exact A1 apartment scope, independent certification and bounded shipment profiling.

The finite source association set is separate from variable N/seed domains.  A1
retains the immutable C6 ledger; it does not claim complete energy definitions.
"""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import zipfile

from atlas_schedules.canonical import canonical
from atlas_schedules.resources import ResourceSet, strict_json, manifest_identity

ROOT = Path(__file__).resolve().parents[1]
BASE = 'data/schedule-generator/apartment/'
NORMAL_TIMEOUT_SECONDS = 240
MAX_TRACKED_BLOB_BYTES = 104857600
PREDECESSOR_SHA256 = '366b2f1596cb1f29173d5541e7074b0dababa7430327f9108650d98d602462cf'


def _read(name):
    return strict_json((ROOT/name).read_bytes(), name)


def _sha(blob):
    return hashlib.sha256(blob).hexdigest()


def _predecessor():
    path = ROOT/'data/generator-releases/v0.7.0/generator.zip'
    if _sha(path.read_bytes()) != PREDECESSOR_SHA256:
        raise ValueError('Exact immutable C6 predecessor required')
    return zipfile.ZipFile(path)


def apartment_scope() -> dict:
    """Compile the approved ordered finite join without restricting N or seeds."""
    from atlas_schedules.apartment_authority_pins import SCOPE_ROWS
    source = _read('sources/schedule-generator-apartment-scope.json')
    if source['programmes'] != list(SCOPE_ROWS):
        raise ValueError('Exact ordered apartment source identities differ')
    domain = _read(BASE+'timing-domain.json')
    with _predecessor() as package:
        scope = strict_json(package.read('sources/schedule-generator-m1-scope.json'), 'C6 scope')
    cases = [{'case_id':'apartment-'+row['id'], 'program_id':row['id'],
              'building_type':row['family'], 'template':row['template'],
              'evidence_view':row['view'], 'role':row['role'], 'name':row['name'],
              'source_locator':row['locator']} for row in source['programmes']]
    finite = []
    for row in source['programmes']:
        pid = row['id']
        if row['role'] == 'dwelling':
            finite.extend({'program_id':pid, 'branch':'positive_N', 'location':copy.deepcopy(location)}
                          for location in domain['locations'])
            finite.append({'program_id':pid, 'branch':'skip_N0', 'location':None})
        else:
            finite.append({'program_id':pid, 'branch':'fixed', 'location':None})
    scope.update(milestone_id='A1', qualification_status='requires_independent_A5_certification',
                 cases=scope['cases']+cases, apartment_source_scope=source,
                 apartment_finite_configurations=finite,
                 apartment_location_tuples=copy.deepcopy(domain['locations']),
                 variable_domains={'N':{'type':'integer','minimum':0,'maximum':None},
                                   'master_seed':{'type':'integer','minimum':0,'maximum':2**64-1},
                                   'derived_unit_seed':{'type':'integer','minimum':0,'maximum':None}},
                 method_coverage={'programme_methods':313,'catalogue_programmes':1900,
                                  'compositions':30,'catalogue_compositions':378,
                                  'full_energy_definitions':False},
                 predecessor_archive_sha256=PREDECESSOR_SHA256)
    return scope


def validate_scope(scope: dict) -> None:
    if canonical(scope) != canonical(apartment_scope()):
        raise ValueError('Exact A1 ordered source/finite/variable/cumulative scope differs')


def load_resources(root):
    root = Path(root)
    manifest = strict_json((root/'manifest.json').read_bytes(), 'resource manifest')
    return ResourceSet(root, manifest['resource_set_id'])


def apartment_request(resources, scope=None, *, n=1, location=None, include_previous=True,
                      group_contexts=True):
    """Actual public 1.2 graph; areas/identities are labelled synthetic caller facts."""
    from atlas_schedules.apartment_authority import SELECTED, FIXED
    scope = apartment_scope() if scope is None else scope
    location = scope['apartment_location_tuples'][0] if location is None else location
    with _predecessor() as package:
        old = strict_json(package.read('references/all-cases-request.json'), 'C6 request')
    params = copy.deepcopy(old['params'])
    params.update(schema_version='1.2.0',resource_set_id=resources.resource_set_id,building_realizations=[])
    if not include_previous:
        params['instances'] = []
    for instance in params['instances']:
        if instance.get('owner_kind') == 'physical_service':
            instance['physical_binding_kind'] = 'legacy_whole'
    for index,row in enumerate(scope['apartment_source_scope']['programmes']):
        pid = row['id']; key = 'apartment-'+pid
        instance = {'key':key,'owner_kind':'program','program_id':pid,'operating_group':None,
                    'inputs':{'apartment_method':SELECTED if row['role']=='dwelling' else FIXED},
                    'basis_bindings':{}}
        if row['role'] == 'dwelling':
            requirement = resources.get('reference','caller-water-requirement__'+pid)
            building = 'synthetic-apartment-'+str(index)
            unit_id = 'synthetic-unit-'+str(index); physical = 'synthetic-water-'+str(index)
            area = 80.0 if index % 2 == 0 else 120.0
            facts = {'building_realization_id':building,'unit_inventory_id':'synthetic-inventory-'+str(index),
                     'units':[{'unit_id':unit_id,'physical_id':physical,
                               'source_service_id':requirement['source_service_id'],
                               'source_beneficiary_id':requirement['source_beneficiary_id'],
                               'programme_ids':[pid],'water_authority_programme_id':pid,'floor_area_m2':area}]}
            def claim(locator,value,unit=None):
                return {'source_revision':'A5-labelled-synthetic-caller-realization',
                        'source_path':'examples/synthetic-caller-facts-'+str(index)+'.json',
                        'source_sha256':_sha(canonical(facts)),'locator':locator,'original_value':value,
                        'original_unit':unit,'transformation':'Caller fact in SI; no prototype geometry inferred',
                        'extraction_date':'2026-10-15','interpretation_note':'Synthetic caller realization, not source dimensions'}
            unit = copy.deepcopy(facts['units'][0]); unit.update(multiplicity=1,
                    area_evidence=[claim('/units/0/floor_area_m2',area,'m2')],
                    identity_evidence=[claim('/building_realization_id',building),
                        claim('/unit_inventory_id',facts['unit_inventory_id'])]+
                        [claim('/units/0/'+k,v) for k,v in facts['units'][0].items() if k!='floor_area_m2'])
            inventory = {'authority':'caller_declared_units','units':[unit]}
            params['building_realizations'].append({'mode':'caller_unit_prototype_density_fixed_dhw',
                'building_realization_id':building,'building_type':row['family'],'template':row['template'],
                'unit_inventory_id':facts['unit_inventory_id'],'unit_inventory':inventory,
                'unit_inventory_sha256':_sha(canonical(inventory))})
            extent = {'value':area,'unit':'m2','evidence':copy.deepcopy(unit['area_evidence'])}
            owner = {'key':'water-'+pid,'owner_kind':'physical_service','physical_binding_kind':
                'caller_unit_prototype_density_fixed_dhw','building_realization_id':building,'unit_id':unit_id,
                'physical_id':physical,'source_service_id':requirement['source_service_id'],'operating_group':None,
                'inputs':{'water_method':'source_fixed_apartment_dhw','source_geometry_departure':'caller_unit_area'},
                'basis_bindings':{'multiplicity':1,'extents':{'floor_area':copy.deepcopy(extent)}}}
            params['instances'].append(owner)
            instance.update(building_realization_id=building,unit_id=unit_id,
                basis_bindings={'multiplicity':1,'extents':{'floor_area':dict(extent,evidence={
                    'field_evidence':copy.deepcopy(unit['area_evidence'])})}})
            instance['inputs']['N'] = n
            if n > 0:
                instance['inputs'].update({k:location[k] for k in
                    ('state','latitude','longitude','time_zone_utc_offset')})
        params['instances'].append(instance)
    if group_contexts:
        _group_synthetic_realizations(params)
    return {'schema_version':'1.2.0','params':params,'seed':42}


def _group_synthetic_realizations(params):
    """R62: same40 physical units in eight source family/template contexts.

    Source objects and controls remain per unit. Only the synthetic building
    grouping and its corresponding caller-fact indices change.
    """
    groups = {}; remap = {}; indexed_units = {}
    fields = ('unit_id','physical_id','source_service_id','source_beneficiary_id',
              'programme_ids','water_authority_programme_id','floor_area_m2')
    for realization in params['building_realizations']:
        context = (realization['building_type'],realization['template'])
        if context not in groups:
            index = len(groups)
            groups[context] = dict(copy.deepcopy(realization),
                building_realization_id='synthetic-building-'+str(index),
                unit_inventory_id='synthetic-inventory-'+str(index),
                unit_inventory={'authority':'caller_declared_units','units':[]})
        target = groups[context]
        remap[realization['building_realization_id']] = target['building_realization_id']
        target['unit_inventory']['units'].extend(copy.deepcopy(realization['unit_inventory']['units']))
    for index,target in enumerate(groups.values()):
        units = target['unit_inventory']['units']
        facts = {'building_realization_id':target['building_realization_id'],
                 'unit_inventory_id':target['unit_inventory_id'],
                 'units':[{key:copy.deepcopy(unit[key]) for key in fields} for unit in units]}
        def claim(locator,value,unit=None):
            return {'source_revision':'A5-labelled-synthetic-caller-realization',
                'source_path':'examples/synthetic-caller-facts-'+str(index)+'.json',
                'source_sha256':_sha(canonical(facts)),'locator':locator,'original_value':copy.deepcopy(value),
                'original_unit':unit,'transformation':'Caller fact in SI; no prototype geometry inferred',
                'extraction_date':'2026-10-15','interpretation_note':'Synthetic caller realization, not source dimensions'}
        for i,unit in enumerate(units):
            unit['area_evidence'] = [claim('/units/'+str(i)+'/floor_area_m2',unit['floor_area_m2'],'m2')]
            unit['identity_evidence'] = ([claim('/building_realization_id',facts['building_realization_id']),
                claim('/unit_inventory_id',facts['unit_inventory_id'])]+
                [claim('/units/'+str(i)+'/'+key,unit[key]) for key in fields if key!='floor_area_m2'])
            indexed_units[unit['unit_id']] = unit
        target['unit_inventory_sha256'] = _sha(canonical(target['unit_inventory']))
    for instance in params['instances']:
        old = instance.get('building_realization_id')
        if old not in remap:
            continue
        instance['building_realization_id'] = remap[old]
        unit = indexed_units[instance['unit_id']]
        evidence = copy.deepcopy(unit['area_evidence'])
        if instance['owner_kind']=='program':
            evidence = {'field_evidence':evidence}
        instance['basis_bindings']['extents']['floor_area']['evidence'] = evidence
    params['building_realizations'] = list(groups.values())


def validate_transport_inventory(inventory):
    for entry in inventory:
        if type(entry['size_bytes']) is not int or entry['size_bytes'] > MAX_TRACKED_BLOB_BYTES:
            raise ValueError('Tracked blob exceeds104857600 bytes: '+entry['path'])


def build_apartment_coverage(resources: ResourceSet, scope=None) -> dict:
    """Cumulative exact method coverage, with original unknowns kept explicit."""
    from scripts.schedule_generator_coverage import build_coverage, _channel_evidence
    from atlas_schedules.apartment_authority import validate_apartment_authority
    scope=apartment_scope() if scope is None else scope
    validate_scope(scope)
    with _predecessor() as package:
        old_scope=strict_json(package.read('sources/schedule-generator-m1-scope.json'),'C6 scope')
    report=build_coverage(resources,old_scope)
    entries={(e['kind'],e['key']):e for e in resources.manifest['resources']}
    proofs={(e['resource_kind'],e['resource_key'],e['pointer']):e for e in report['evidence_inventory']}
    apartment_ids=set();unknowns=[]
    for row in scope['apartment_source_scope']['programmes']:
        pid=row['id'];apartment_ids.add(pid);record=resources.get('program',pid);recipe=record['recipe']
        qualification=resources.get('reference','apartment-programme-qualification__'+pid)
        validate_apartment_authority(pid,record,qualification)
        resolved=recipe['resolved'];channels=[]
        demand_slots={d['slot'] for d in resolved['demands']}
        for slot in resolved['slots']:
            name=slot['slot'];evidence=_channel_evidence(resources,entries,pid,recipe,name,slot['source_schedule_id'])
            if not evidence:raise ValueError('Apartment owned slot lacks exact evidence: '+pid+'/'+name)
            proofs[evidence['resource_kind'],evidence['resource_key'],evidence['pointer']]=evidence
            channels.append({'slot':name,'kind':'load' if name in demand_slots else 'control',
                'status':'generated' if row['role']=='dwelling' and name in {'occupants','lighting_interior','additional_lighting'} else 'source_fixed',
                'source_schedule_id':slot['source_schedule_id'],'source_evidence':evidence})
        exclusions=recipe['source_context']['unresolved_exclusions']
        unknowns.extend({'programme_id':pid,**copy.deepcopy(e)} for e in exclusions)
        report['cases'].append({'case_id':'apartment-'+pid,'program_id':pid,'configuration_id':None,
            'template':row['template'],'evidence_view':row['view'],'weather':None,
            'status':'compiled','expected_slots':[s['slot'] for s in resolved['slots']],
            'channels':channels,'errors':[],'accepted_absence':False,'absence_evidence':None,
            'unresolved_exclusions':exclusions,'method':recipe['source_context']['method'],
            'required_caller_unit_water':row['role']=='dwelling',
            'authority_sha256':entries['reference','apartment-programme-qualification__'+pid]['sha256']})
    report['scope'].update(milestone_id='A1',scope_sha256=_sha(canonical(scope)),
        case_count=313,case_ids=[c['case_id'] for c in scope['cases']],
        finite_configuration_count=len(scope['apartment_finite_configurations']),
        declared_owned_slot_count=sum(len(c['expected_slots']) for c in report['cases']+report['service_cases']),
        method_coverage=scope['method_coverage'],caller_unit_water_requirements=40,
        variable_domains=scope['variable_domains'],full_energy_definitions=False)
    report['evidence_inventory']=[proofs[k] for k in sorted(proofs)]
    report['outside_scope']['programs']=[p for p in report['outside_scope']['programs'] if p['id'] not in apartment_ids]
    report['outside_scope']['program_count']=len(report['outside_scope']['programs'])
    report['apartment_unresolved_exclusions']=unknowns
    report['qualification_status']='source_method_coverage_only_independent_shipment_gates_required'
    return report


def apartment_coverage_errors(report,resources=None):
    errors=[]
    if resources is None:return ['Verified actual apartment resources required']
    try:
        actual=build_apartment_coverage(resources)
        if canonical(report)!=canonical(actual):errors.append('Exact apartment/cumulative source coverage differs')
        if len(report['cases'])!=313 or len(report.get('declared_compositions',[]))!=30:
            errors.append('Exact313method/30composition denominator differs')
    except Exception as error:
        errors.append('Apartment source coverage failed: '+str(error))
    return errors


def assemble_apartment_members(resources_root, scope):
    """Retain the frozen source/native ledger; replace only current code/resources."""
    validate_scope(scope)
    from scripts.schedule_generator_release import BOOTSTRAP_V2
    with _predecessor() as package:
        files = {name:package.read(name) for name in package.namelist()
                 if not name.startswith(('atlas_schedules/','references/'))}
    files['__main__.py'] = BOOTSTRAP_V2
    for name in ('scripts/schedule_generator_release.py','scripts/schedule_generator_apartment_certification.py',
                 'scripts/schedule_generator_release_reproduction.py'):
        files['provenance/implementation/'+name]=(ROOT/name).read_bytes()
    for path in (ROOT/'atlas_schedules').rglob('*'):
        if path.is_file() and path.suffix in {'.py','.json'} and '__pycache__' not in path.parts and not path.is_relative_to(ROOT/'atlas_schedules/data'):
            files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for path in Path(resources_root).rglob('*.json'):
        files['atlas_schedules/data/'+path.relative_to(resources_root).as_posix()] = path.read_bytes()
    # Raw source runtime archives are unnecessary; these are redistributable
    # exact original inputs, qualified preimages, captures, and upstream notices.
    for base in (ROOT/BASE, ROOT/'sources/licenses'):
        for path in base.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.pyc':
                files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for path in (ROOT/'sources').glob('schedule-generator-apartment*.json'):
        files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    files['sources/schedule-generator-m1-scope.json'] = canonical(scope)
    files['docs/schedule-generator.md'] = (
        '# Offline apartment method milestone A1\n\n'
        '313 of1900 programme methods and30 of378 compositions. Unknown gas/additional loads and other '
        'source exclusions remain unresolved; this is not complete energy-definition coverage. '
        'Caller areas80/120m2 are synthetic realizations, never prototype dimensions. '
        'The complete public1.2 request is references/all-cases-request.json. '
        'Use Python3.11+ offline: python -I -S generator.zip --request REQUEST --output BUNDLE. '
        'Layout2 reproduction requires all four local files: manifest.json, generator.zip, reproduce.py, '
        'references/all-cases-bundle.json.gz. Run python -I -S reproduce.py --release-root RELEASE '
        '--receipt OUTSIDE_WORK/reproduction.json. ZIP-only --reproduce is unsupported.\n').encode()
    validate_transport_inventory([{'path':name,'size_bytes':len(blob)} for name,blob in files.items()])
    return files


def _run(command,cwd,timeout):
    started = time.perf_counter()
    try:
        result = subprocess.run(command,cwd=cwd,capture_output=True,text=True,timeout=timeout)
        return {'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
                'elapsed_seconds':time.perf_counter()-started,'timeout_seconds':timeout,'timed_out':False}
    except subprocess.TimeoutExpired as error:
        return {'returncode':None,'stdout':str(error.stdout or ''),'stderr':str(error.stderr or ''),
                'elapsed_seconds':time.perf_counter()-started,'timeout_seconds':timeout,'timed_out':True}


def freeze_apartment_generator(target, version, scope, resources_root):
    """A1 route through the existing immutable assembly/execution primitives."""
    from scripts.schedule_generator_release import _archive, _execute_zip, _digest
    if Path(target).exists():
        raise ValueError('Immutable release target already exists; choose a new version')
    validate_scope(scope)
    diagnostic = Path(target).parent if Path(target).resolve().is_relative_to(
        (ROOT/'build/task-10/apartment-a5/profile').resolve()) else None
    if diagnostic is None:
        raise ValueError('A1 final freeze remains closed until independent A5 public and measured shipment gates pass')
    phases = {}
    def receipt():
        if diagnostic is not None:
            diagnostic.mkdir(parents=True,exist_ok=True)
            (diagnostic/'candidate-phases.json').write_bytes(canonical(phases))
    started = time.perf_counter()
    resources = load_resources(resources_root)
    phases['resource_decoding'] = {'elapsed_seconds':time.perf_counter()-started,
        'resource_set_id':resources.resource_set_id,'resource_files':len(resources.manifest['resources'])}
    started = time.perf_counter()
    files = assemble_apartment_members(resources_root,scope)
    phases['source_and_transport_assembly'] = {'elapsed_seconds':time.perf_counter()-started,
        'members':len(files),'raw_bytes':sum(map(len,files.values()))}
    receipt()
    manifest = strict_json(files['atlas_schedules/data/manifest.json'],'manifest')
    files['atlas_schedules/data/reference/m1-scope.json'] = canonical(scope)
    entry = next(e for e in manifest['resources'] if (e['kind'],e['key'])==('reference','m1-scope'))
    entry.update(_digest(files['atlas_schedules/data/reference/m1-scope.json']))
    manifest.update(cases=scope['cases'],service_cases=scope['service_cases'],milestone_id='A1')
    manifest['resource_set_id'] = manifest_identity(manifest)
    files['atlas_schedules/data/manifest.json'] = canonical(manifest)
    request = apartment_request(resources,scope)
    request['params']['resource_set_id'] = manifest['resource_set_id']
    files['references/all-cases-request.json'] = canonical(request)
    # The normal public subprocess is bounded by the existing240s helper.
    started = time.perf_counter()
    initial_archive = _archive(files)
    phases['initial_zip_serialization'] = {'elapsed_seconds':time.perf_counter()-started,
        'size_bytes':len(initial_archive),'sha256':_sha(initial_archive)}
    if diagnostic is not None:
        (diagnostic/'pre-generation-generator.zip').write_bytes(initial_archive)
        (diagnostic/'pre-generation-request.json').write_bytes(canonical(request))
        (diagnostic/'pre-generation-members.json').write_bytes(canonical(
            [{'path':k,**_digest(v)} for k,v in sorted(files.items())]))
    phases['request_counts'] = {'owners':len(request['params']['instances']),
        'programme_methods':sum(i['owner_kind']=='program' for i in request['params']['instances']),
        'caller_unit_owners':sum(i.get('physical_binding_kind')=='caller_unit_prototype_density_fixed_dhw'
                                for i in request['params']['instances']),
        'caller_building_contexts':len(request['params']['building_realizations'])}
    receipt();started = time.perf_counter()
    try:
        generated = _execute_zip(initial_archive,request)
    except subprocess.TimeoutExpired:
        phases['normal_packaged_generation'] = {'elapsed_seconds':time.perf_counter()-started,
            'timeout_seconds':NORMAL_TIMEOUT_SECONDS,'timed_out':True}
        receipt()
        raise
    phases['normal_packaged_generation'] = {'elapsed_seconds':time.perf_counter()-started,
        'timeout_seconds':NORMAL_TIMEOUT_SECONDS,'timed_out':False,'serialized_bundle_bytes':len(generated)}
    receipt()
    bundle = strict_json(generated,'A1 public bundle')
    if {c['program_id'] for c in scope['cases']} != {i['program_id'] for i in request['params']['instances'] if i['owner_kind']=='program'}:
        raise ValueError('Cumulative313 public request method identity differs')
    started = time.perf_counter()
    reference = gzip.compress(generated,mtime=0)
    phases['reference_gzip_serialization'] = {'elapsed_seconds':time.perf_counter()-started,
        'raw_bytes':len(generated),'size_bytes':len(reference),'sha256':_sha(reference)}
    started = time.perf_counter()
    archive = _archive(files)
    phases['final_zip_serialization'] = {'elapsed_seconds':time.perf_counter()-started,
        'size_bytes':len(archive),'sha256':_sha(archive)}
    receipt()
    runner=(ROOT/'scripts/schedule_generator_release_reproduction.py').read_bytes()
    validate_transport_inventory([{'path':'generator.zip','size_bytes':len(archive)},
        {'path':'reproduce.py','size_bytes':len(runner)},
        {'path':'references/all-cases-bundle.json.gz','size_bytes':len(reference)}]+
        [{'path':k,'size_bytes':len(v)} for k,v in files.items()])
    release = {'schema_version':'2.0.0','release_version':version,
        'reference_layout':'external_local_gzip_json_v1','bundle_schema_version':'1.2.0',
        'entrypoints':{'generation':{'kind':'zip_request_output','path':'generator.zip'},
                       'reproduction':{'kind':'release_script','path':'reproduce.py'}},
        'request':{'location':'generator_zip_member','path':'references/all-cases-request.json',
                   **_digest(files['references/all-cases-request.json'])},
        'reference':{'location':'release_file','path':'references/all-cases-bundle.json.gz',
            'codec':'gzip-json-v1',**_digest(reference),'decoded_sha256':_sha(generated),'decoded_size_bytes':len(generated)},
        'scope':{'milestone_id':'A1','scope_version':scope['scope_version'],'case_count':313,
                 'case_ids':[c['case_id'] for c in scope['cases']],
                 'sha256':_sha(files['sources/schedule-generator-m1-scope.json'])},
        'resource_set_id':manifest['resource_set_id'],
        'source_manifest_sha256':_sha(files['atlas_schedules/data/manifest.json']),
        'commercial_audit_sha256':_sha(files['data/schedule-generator/comstock-sampling-audit.json']),
        'files':{'generator.zip':_digest(archive),'reproduce.py':_digest(runner),
                 'references/all-cases-bundle.json.gz':_digest(reference)},
        'implementation_sources':{name:{'location':'generator_zip_member',
            'path':'provenance/implementation/'+name,**_digest(files['provenance/implementation/'+name])}
            for name in ('scripts/schedule_generator_release.py','scripts/schedule_generator_apartment_certification.py',
                         'scripts/schedule_generator_release_reproduction.py')},
        'members':{k:_digest(v) for k,v in sorted(files.items())},
        'public_counts':{'requested_owners':len(request['params']['instances']),
                         'constituents':len(bundle['constituents']),'schedules':len(bundle['schedules']),
                         'bindings':len(bundle['bindings'])}}
    release['scope'].update(service_case_ids=[c['case_id'] for c in scope['service_cases']],
                            service_case_count=len(scope['service_cases']))
    Path(target).mkdir(parents=True)
    (Path(target)/'generator.zip').write_bytes(archive)
    (Path(target)/'reproduce.py').write_bytes(runner)
    (Path(target)/'references').mkdir()
    (Path(target)/'references/all-cases-bundle.json.gz').write_bytes(reference)
    (Path(target)/'manifest.json').write_bytes(canonical(release))
    return release


def _profile_copied_apartment_release(candidate, outside):
    """Copy exactly the four v2 inputs, then run both real isolated consumers."""
    from scripts.schedule_generator_release import _release_reproduction_command,_v2_reproduction_receipt
    from scripts.schedule_generator_release_reproduction import _inventory
    candidate=Path(candidate);outside=Path(outside)
    _inventory(candidate)
    manifest=strict_json((candidate/'manifest.json').read_bytes(),'candidate manifest')
    if manifest.get('schema_version')!='2.0.0' or set(manifest['files'])!={'generator.zip','reproduce.py','references/all-cases-bundle.json.gz'}:
        raise ValueError('Apartment profiling requires explicit four-file layout2')
    release=outside/'release';work=outside/'work';release.mkdir();work.mkdir()
    copied={}
    for name in ('manifest.json',*manifest['files']):
        source=candidate/name
        if source.is_symlink() or not source.is_file():raise ValueError('Regular candidate input required: '+name)
        blob=source.read_bytes()
        if name!='manifest.json' and {'sha256':_sha(blob),'size_bytes':len(blob)}!=manifest['files'][name]:
            raise ValueError('Candidate copy identity differs: '+name)
        target=release/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
        if target.read_bytes()!=blob:raise ValueError('Outside copy differs')
        copied[name]={'sha256':_sha(blob),'size_bytes':len(blob)}
    with zipfile.ZipFile(release/'generator.zip') as package:request=package.read('references/all-cases-request.json')
    if {'sha256':_sha(request),'size_bytes':len(request)}!={k:manifest['request'][k] for k in ('sha256','size_bytes')}:
        raise ValueError('Copied request identity differs')
    req=work/'normal-request.json';req.write_bytes(request)
    phases={'normal_generation':_run([sys.executable,'-I','-S',str(release/'generator.zip'),
        '--request',str(req),'--output',str(work/'normal-bundle.json')],work,NORMAL_TIMEOUT_SECONDS)}
    receipt=work/'dev-reproduction.json'
    phases['combined_reproduction']=_run(_release_reproduction_command(release,receipt),work,600)
    if phases['combined_reproduction']['returncode']==0 and not phases['combined_reproduction']['timed_out']:
        try:
            result=_v2_reproduction_receipt(receipt,manifest,copied['manifest.json'])
            phases['combined_reproduction']['scientific_receipt']=result
        except (OSError,ValueError) as error:
            phases['combined_reproduction']['receipt_error']=str(error)
    combined=phases['combined_reproduction']
    passed=all(p['returncode']==0 and not p['timed_out'] for p in phases.values()) and 'scientific_receipt' in combined
    return {'passed':passed,'phases':phases,'outside_input_inventory':copied,
            'normal_request_identity':{'sha256':_sha(request),'size_bytes':len(request)}}


def profile_apartment_shipment(resources_root: Path, scope: dict, destination: Path) -> dict:
    """Build and exercise the actual cumulative candidate at unchanged limits."""
    from scripts.schedule_generator_release import freeze_generator
    destination = Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    candidate = destination/'candidate-v0.8.0'
    report = {'schema_version':'1.0.0','runtime':sys.version,'platform':platform.platform(),
              'normal_timeout_seconds':NORMAL_TIMEOUT_SECONDS,'combined_timeout_seconds':600,
              'max_tracked_blob_bytes':MAX_TRACKED_BLOB_BYTES,'scope_sha256':_sha(canonical(scope)),
              'candidate_path':candidate.name,'passed':False,'phases':{}}
    started = time.perf_counter()
    try:
        manifest = freeze_generator(candidate,'0.8.0',scope,resources_root)
        report['phases']['candidate_freeze'] = {'elapsed_seconds':time.perf_counter()-started,'passed':True}
        report['transport_inventory'] = [{'path':k,**v} for k,v in manifest['files'].items()]
        report['member_inventory'] = [{'path':k,**v} for k,v in manifest['members'].items()]
        validate_transport_inventory(report['transport_inventory']+report['member_inventory'])
        with tempfile.TemporaryDirectory(prefix='atlas-a5-profile-') as temporary:
            result=_profile_copied_apartment_release(candidate,Path(temporary))
            report['phases'].update(result['phases'])
            report['outside_input_inventory']=result['outside_input_inventory']
            report['normal_request_identity']=result['normal_request_identity']
            report['passed']=result['passed']
    except Exception as error:
        report['failure'] = {'type':type(error).__name__,'message':str(error),
                             'elapsed_seconds':time.perf_counter()-started}
    phase_path=destination/'candidate-phases.json'
    if phase_path.exists():report['candidate_phases']=strict_json(phase_path.read_bytes(),'candidate phases')
    if not report['passed']:
        created=report['phases'].get('candidate_freeze',{}).get('passed') is True
        report['unreached_gates']={'complete_development_reproduction':
            ('See actual combined child phase/receipt failure' if 'combined_reproduction' in report['phases'] else
             'Combined600s child not run after candidate creation failure'),
            'candidate_created':created,
            'final_archive_bytes':manifest['files']['generator.zip']['size_bytes'] if created else None,
            'serialized_reference_bytes':manifest['reference']['decoded_size_bytes'] if created else None,
            'production_freeze':'closed'}
    report['total_elapsed_seconds'] = time.perf_counter()-started
    (destination/'profile.json').write_bytes(canonical(report))
    return report


def certify_apartments(resources_root: Path, scope: dict) -> dict:
    """Independent proof/resource closure; public generation is separately measured."""
    validate_scope(scope)
    from scripts.schedule_generator_apartment_authority import verify_current_authority
    authority = verify_current_authority()
    resources = load_resources(resources_root)
    from atlas_schedules.programs import resolve_program
    rows = []
    for row in scope['apartment_source_scope']['programmes']:
        record = resources.get('program',row['id'])
        inputs = {'year':2007,'holidays':[],'apartment_method':record['recipe']['source_context']['method']}
        if row['role']=='dwelling': inputs['N']=0
        resolved = resolve_program(row['id'],inputs,resources)
        rows.append({'programme_id':row['id'],'source_definition_sha256':_sha(canonical(record['definition'])),
                     'resolved_sha256':_sha(canonical(resolved)),
                     'slots':[s['slot'] for s in resolved['slots']],
                     'unresolved_exclusions':record['recipe']['source_context']['unresolved_exclusions']})
    receipt = _read(BASE+'evidence/a1-fix1-native-comparison.json')
    if len(receipt['targets'])!=58 or any(c['mismatch_count'] for t in receipt['targets'] for c in t['channels'].values()):
        raise ValueError('Actual reviewed58-target timing proof failed')
    return {'schema_version':'1.0.0','scope_sha256':_sha(canonical(scope)),
            'resource_set_id':resources.resource_set_id,'authority':authority,'programme_rows':rows,
            'finite_configuration_count':1564,'native_timing_targets':58,
            'method_coverage':scope['method_coverage'],
            'qualification_status':'source_closure_passed_public_and_shipment_gates_required'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resources-root',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--profile-shipment',action='store_true')
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args(argv);scope=apartment_scope()
    report=(profile_apartment_shipment(args.resources_root,scope,args.destination) if args.profile_shipment
            else certify_apartments(args.resources_root,scope))
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_bytes(canonical(report))
    print(json.dumps({k:v for k,v in report.items() if k not in {'member_inventory','transport_inventory','programme_rows'}}))
    if args.profile_shipment and not report['passed']: raise SystemExit(1)


if __name__=='__main__':main()
