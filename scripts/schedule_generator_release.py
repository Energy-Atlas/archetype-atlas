"""Freeze, verify, and reproduce an immutable offline schedule-generator ZIP."""
import argparse
import copy
import gzip
import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from atlas_schedules.canonical import canonical
from atlas_schedules.resources import ResourceSet, manifest_identity, safe_path, strict_json
from atlas_schedules.errors import GeneratorError
from scripts.schedule_generator_coverage import build_coverage, coverage_errors

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build' / 'schedule-generator-shipment'
TARGET = ROOT / 'data/generator-releases/v0.1.1'
# Development allowance includes both complete generation and scientific comparison.
COMPLETE_REPRODUCTION_TIMEOUT_SECONDS = 600
BOOTSTRAP = b'''"""Run an independent extracted release from this ordinary ZIP."""\nimport pathlib,runpy,sys,tempfile,zipfile\narchive=pathlib.Path(sys.argv[0]).resolve()\nwith tempfile.TemporaryDirectory(prefix="atlas-schedules-") as directory:\n    with zipfile.ZipFile(archive) as source:\n        names=source.namelist()\n        if len(names)!=len(set(names)) or any(name.startswith("/") or "\\\\" in name or ":" in name or any(part in ("..", ".", "") for part in name.split("/")) for name in names):\n            raise SystemExit("Unsafe ZIP inventory")\n        source.extractall(directory)\n    sys.path.insert(0,directory)\n    sys.argv[0]=str(archive)\n    if len(sys.argv)==2 and sys.argv[1]=="--reproduce":\n        runpy.run_module("atlas_schedules.reproduction",run_name="__main__")\n    else:\n        runpy.run_module("atlas_schedules.__main__",run_name="__main__")\n'''
BOOTSTRAP_V2 = b'''"""Ordinary generation from layout2; reproduction needs the local release."""
import pathlib,runpy,stat,sys,tempfile,zipfile
if len(sys.argv)==2 and sys.argv[1]=="--reproduce":
    print("Release layout 2 reproduction requires manifest.json, reproduce.py and references/all-cases-bundle.json.gz. Run the release-level reproduce.py with --release-root and an outside --receipt path.",file=sys.stderr)
    raise SystemExit(2)
archive=pathlib.Path(sys.argv[0]).resolve()
with tempfile.TemporaryDirectory(prefix="atlas-schedules-") as directory:
    with zipfile.ZipFile(archive) as source:
        names=source.namelist();prefixes={}
        if len(names)!=len(set(names)):
            raise SystemExit("Unsafe ZIP inventory")
        for info in source.infolist():
            name=info.filename;parts=name.split("/")
            reserved={"CON","PRN","AUX","NUL"}|{a+str(i) for a in ("COM","LPT") for i in range(1,10)}
            if name.startswith("/") or "\\\\" in name or ":" in name or any(p in ("..",".","") or p.endswith(("."," ")) or p.split(".")[0].upper() in reserved for p in parts) or info.is_dir() or info.flag_bits&1 or stat.S_IFMT(info.external_attr>>16) not in (0,stat.S_IFREG):
                raise SystemExit("Unsafe ZIP inventory")
            for i in range(1,len(parts)+1):
                prefix="/".join(parts[:i]);key=prefix.casefold()
                if key in prefixes and prefixes[key]!=prefix:
                    raise SystemExit("Unsafe ZIP inventory")
                prefixes[key]=prefix
        source.extractall(directory)
    sys.path.insert(0,directory)
    sys.argv[0]=str(archive)
    runpy.run_module("atlas_schedules.__main__",run_name="__main__")
'''


def _digest(content: bytes) -> dict:
    return {'sha256': hashlib.sha256(content).hexdigest(), 'size_bytes': len(content)}


def _archive(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for name, content in sorted(files.items()):
            safe_path(name)
            info = zipfile.ZipInfo(name, (2007, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def certification_dependency_hash(manifest: dict) -> str:
    """Hash the tested immutable operands without a circular report self-hash."""
    payload = {k: v for k, v in manifest.items() if k != 'resource_set_id'}
    payload['resources'] = [e for e in manifest['resources']
                            if (e['kind'],e['key']) != ('reference','family-certification')]
    return hashlib.sha256(canonical(payload)).hexdigest()


def implementation_source_hash(content):
    """Git-portable code receipt; frozen ZIP hashes still use exact raw bytes."""
    return hashlib.sha256(content.replace(b'\r\n',b'\n')).hexdigest()


def implementation_sources(milestone):
    paths={p.relative_to(ROOT).as_posix() for p in (ROOT/'atlas_schedules').rglob('*.py')}
    paths.update({'scripts/schedule_generator_build.py','scripts/schedule_generator_reference.py',
        'scripts/schedule_generator_release.py','scripts/schedule_generator_coverage.py',
        'scripts/schedule_generator_families.py'})
    if milestone in {'C5','C6'}:
        paths.update({'scripts/schedule_generator_restaurants.py','scripts/schedule_generator_restaurant_build.py',
            'scripts/schedule_generator_restaurant_certification.py'})
        paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'atlas_schedules/schemas').glob('*.json'))
    if milestone=='C6':
        paths.update({'scripts/schedule_generator_retail.py','scripts/schedule_generator_retail_certification.py',
            'scripts/schedule_generator_service_build.py','scripts/schedule_generator_native_codec.py'})
    return paths


def _native_component_entries(lock):
    entries=[lock['vectors']]
    entries.extend(lock[k] for k in ('inputs','driver','harness') if isinstance(lock.get(k),dict))
    entries.extend(lock.get('capture_sources',[]))
    return entries


def native_component_files(resources):
    """Copy actual locked captures once, including their executed source/input evidence."""
    files={}
    for component in resources.get('reference','family-native-join')['components']:
        for entry in _native_component_entries(component['lock']):
            name=str(safe_path(entry['source_path']));content=(ROOT/name).read_bytes()
            if name in files and files[name]!=content:raise ValueError('Conflicting native component identity')
            files[name]=content
    return files


def validate_packaged_native_components(resources,files):
    """Close packaged raw bytes and actual arrays against extracted operands/pointers."""
    join=resources.get('reference','family-native-join');case_ids={};seen=set()
    for component in join['components']:
        key=component['reference_resource_key'];lock=component['lock']
        if key in seen:raise ValueError('Duplicate packaged native component identity')
        seen.add(key)
        if resources.get('reference',key)!=lock or hashlib.sha256(canonical(lock)).hexdigest()!=component['reference_resource_sha256']:
            raise ValueError('Packaged native component resource identity differs')
        for entry in _native_component_entries(lock):
            name=entry['source_path']
            if name not in files:raise ValueError('Missing packaged native component: '+name)
            if _digest(files[name])!={'sha256':entry['sha256'],'size_bytes':entry['size_bytes']}:
                raise ValueError('Packaged native component hash differs: '+name)
        vector=lock['vectors']
        if key=='retail-programme-native-lock' or vector.get('format') is not None:
            from scripts.schedule_generator_native_codec import decode_native_component
            payload=decode_native_component(files[vector['source_path']],component)
        else:
            if not vector['source_path'].endswith('.json.gz'):
                raise ValueError('Legacy native gzip extension differs')
            payload=gzip.decompress(files[vector['source_path']])
        if hashlib.sha256(payload).hexdigest()!=vector['payload_sha256']:
            raise ValueError('Packaged native payload hash differs')
        if key=='retail-programme-native-lock':
            entry=lock['inputs']
            decode_native_component(files[entry['source_path']],component,'inputs')
        capture=strict_json(payload,'packaged actual native component')
        ids=[c['case_id'] for c in capture['cases']]
        if len(ids)!=len(set(ids)):raise ValueError('Packaged native cases repeat')
        case_ids[key]=set(ids)
        if key=='restaurant-water-native-lock':
            from scripts.schedule_generator_restaurants import validate_fixed_native_operands
            validate_fixed_native_operands(resources.get('reference','restaurant-water-fixed-native-operands'),
                {'native':capture,'lock':lock})
        if key=='retail-context-native-lock':
            from scripts.schedule_generator_retail import validate_fixed_native_operands
            validate_fixed_native_operands(resources.get('reference','retail-fixed-native-operands'),
                {'vectors':capture,'lock':lock})
        for binding in join.get('service_bindings',[]):
            retail_service=resources.get('reference',binding['resource_key'])['definition']['building_type']=='RetailStandalone'
            if retail_service:
                if (len(binding['public_native_contexts'])!=2 or
                        any(field in binding for field in ('private_native_fixtures','public_native_fixtures'))):
                    raise ValueError('Retail packaged native context denominator/shape differs')
            elif 'public_native_contexts' in binding:
                raise ValueError('Foreign service uses Retail native context pointer shape')
            for field in ('private_native_fixtures','public_native_fixtures'):
                for reference in ([] if retail_service else binding[field]):
                    if reference['reference_resource_key']!=key:continue
                    parts=reference['pointer'].strip('/').split('/')
                    if (len(parts)!=4 or parts[0]!='cases' or parts[2]!='fixtures' or
                            any(not parts[i].isdigit() for i in (1,3))):
                        raise ValueError('Packaged native fixture pointer shape differs')
                    source_case=capture['cases'][int(parts[1])]
                    value=source_case['fixtures'][int(parts[3])]
                    if (source_case['case_id']!=reference['native_case_id'] or
                            source_case['source_hoo_configuration_id']!=binding['source_hoo_configuration_id'] or
                            reference['reference_resource_sha256']!=component['reference_resource_sha256'] or
                            reference['native_vectors_sha256']!=vector['sha256'] or
                            value['source_service_id']!=binding['source_service_id']):
                        raise ValueError('Packaged native fixture pointer identity differs')
            for reference in binding.get('public_native_contexts',[]):
                if reference['reference_resource_key']!=key:continue
                parts=reference['pointer'].strip('/').split('/')
                if len(parts)!=2 or parts[0]!='cases' or not parts[1].isdigit():
                    raise ValueError('Packaged native context pointer shape differs')
                value=capture['cases'][int(parts[1])]
                if (value['case_id']!=reference['native_case_id'] or
                        value['configuration_id']!=binding['source_hoo_configuration_id'] or
                        value['source_service_id']!=binding['source_service_id'] or
                        reference['reference_resource_sha256']!=component['reference_resource_sha256'] or
                        reference['native_vectors_sha256']!=vector['sha256']):
                    raise ValueError('Packaged native context pointer identity differs')
        del capture,payload
    for binding in join['fixture_bindings']:
        for reference in binding.get('native_members',[binding]):
            expected=[reference['native_case_id']]+reference.get('public_native_case_ids',[])
            if not set(expected)<=case_ids[reference['reference_resource_key']]:
                raise ValueError('Packaged native component misses exact scoped source cases')


def validate_native_join(resources: ResourceSet, scope: dict) -> None:
    """Close the cumulative scope against actual component resource hashes."""
    if scope['milestone_id']=='C6':
        from scripts.schedule_generator_retail_certification import validate_native_associations
        packaged=resources.get('reference','m1-scope')
        if scope['cases']!=packaged['cases'] or scope.get('service_cases')!=packaged.get('service_cases'):
            raise ValueError('C6 source/native qualification requires the exact complete compiled scope')
        validate_native_associations(resources,resources.get('reference','family-native-join'))
        return
    if scope['milestone_id']=='C5':
        from scripts.schedule_generator_restaurant_certification import validate_native_associations
        packaged=resources.get('reference','m1-scope')
        if scope['cases']!=packaged['cases'] or scope.get('service_cases')!=packaged.get('service_cases'):
            raise ValueError('C5 source/native qualification requires the exact complete compiled scope')
        validate_native_associations(resources,resources.get('reference','family-native-join'))
        return
    try:
        join=resources.get('reference','family-native-join')
        components=join['components']
        keys=[c['reference_resource_key'] for c in components]
        expected_keys=['residential-native-lock','commercial-native-lock']
        if scope['milestone_id'] in {'C3','C4'}:expected_keys.append('small-office-native-lock')
        if scope['milestone_id']=='C4':expected_keys.append('warehouse-native-lock')
        if keys!=expected_keys:
            raise ValueError('Native join component keys differ or repeat')
        by_key={}
        for component in components:
            key=component['reference_resource_key']
            actual=resources.get('reference',key)
            if actual!=component['lock'] or hashlib.sha256(canonical(actual)).hexdigest()!=component['reference_resource_sha256']:
                raise ValueError('Native join component identity differs')
            by_key[key]=component
        expected=[]
        for case in scope['cases']:
            commercial=case['building_type'] in {'MediumOffice','SmallOffice','Warehouse'}
            key={'MediumOffice':'commercial-native-lock','SmallOffice':'small-office-native-lock','Warehouse':'warehouse-native-lock'}.get(case['building_type'],'residential-native-lock')
            component=by_key[key]
            if case['building_type']=='Warehouse':
                recipe=resources.get('program',case['program_id'])['recipe']
                allocation=recipe.get('source_composition')
                if allocation is not None:
                    expected.append({'configuration_id':case['configuration_id'],'program_id':case['program_id'],
                        'composition_id':allocation['composition_id'],
                        'native_members':[{'member_index':i,'program_id':m['program_id'],
                            'native_case_id':case['case_id']+'/member-'+str(i),'reference_resource_key':key,
                            'reference_resource_sha256':component['reference_resource_sha256'],
                            'native_vectors_sha256':component['lock']['vectors']['sha256']}
                            for i,m in enumerate(allocation['definition']['members'])]})
                    continue
            expected.append({'configuration_id':case['configuration_id'],'program_id':case['program_id'],
                'native_case_id':case['case_id'] if commercial else case['configuration_id'],
                'reference_resource_key':key,'reference_resource_sha256':component['reference_resource_sha256'],
                'native_vectors_sha256':component['lock']['vectors']['sha256']})
        if join['fixture_bindings']!=expected:
            raise ValueError('Native join scoped configurations/source references differ')
    except (GeneratorError,KeyError,TypeError) as error:
        raise ValueError('Native join source component is missing or invalid') from error


def validate_family_certification(resources: ResourceSet, scope: dict) -> None:
    try:
        certificate = resources.get('reference','family-certification')
    except GeneratorError as error:
        raise ValueError('Expanded family source certification is missing') from error
    expected = [c['case_id'] for c in scope['cases']]
    if scope['milestone_id'] in {'C5','C6'}:
        services=scope.get('service_cases',[])
        milestone=scope['milestone_id']
        programmes,physical,slots,definitions=(165,26,1370,13) if milestone=='C5' else (229,32,1738,16)
        if (certificate.get('service_case_ids')!=[c['case_id'] for c in services] or
                len(expected)!=programmes or len(services)!=physical or
                certificate.get('declared_owned_slot_count')!=slots or
                certificate.get('required_service_link_count')!=10 or
                certificate.get('source_service_definition_count')!=definitions):
            raise ValueError(milestone+' programme/service/owned-slot/link certification denominator differs')
        qualifications=certificate.get('family_qualifications',{})
        families={'FullServiceRestaurant','QuickServiceRestaurant'}
        if milestone=='C6':families.add('RetailStandalone')
        if set(qualifications)!=families:
            raise ValueError(milestone+' separate family qualification is missing')
        for family in qualifications:
            qualified=qualifications[family]
            if (qualified.get('programme_case_ids')!=[c['case_id'] for c in scope['cases'] if c['building_type']==family] or
                    qualified.get('service_case_ids')!=[c['case_id'] for c in services if c['building_type']==family] or
                    qualified.get('master_seeds')!=[42,51] or
                    qualified.get('native_source_discrete_numerical_passed') is not True or
                    qualified.get('bound_public_examples_passed') is not True):
                raise ValueError(milestone+' exact family native/public qualification differs: '+family)
    if (certificate.get('status') != 'passed' or certificate.get('case_ids') != expected or
            certificate.get('scope_sha256') != hashlib.sha256(canonical(scope)).hexdigest() or
            certificate.get('dependency_sha256') != certification_dependency_hash(resources.manifest) or
            certificate.get('native_source_discrete_numerical_passed') is not True or
            certificate.get('annual_target_invariance_passed') is not True or
            certificate.get('temporal_variation_and_fixed_channels_passed') is not True or
            len(set(certificate.get('master_seeds',[]))) < 2):
        raise ValueError('Expanded family certification differs from complete tested scope/operands')
    native = certificate.get('native_reference', {})
    lock = resources.get('reference','family-native-lock')
    if native != lock['vectors'] or set(lock['fixture_order']) != {c['configuration_id'] for c in scope['cases']}:
        raise ValueError('Expanded family certification has incomplete native reference identity')
    if scope['milestone_id'] in {'C2','C3','C4','C5','C6'}: validate_native_join(resources,scope)
    if scope['milestone_id'] in {'C4','C5','C6'}:
        expected=implementation_sources(scope['milestone_id'])
        receipts=certificate.get('implementation_source_sha256',{})
        if set(receipts)!=expected or any(implementation_source_hash((ROOT/name).read_bytes())!=digest for name,digest in receipts.items()):
            raise ValueError('Family certificate implementation/checker source differs from tested code')


def validate_native_case_sources(resources,scope,join,payloads):
    """Tie actual new room/member captures to packaged source operands/draws."""
    from atlas_schedules.commercial.sampling import sample_operating_parameters
    from atlas_schedules.seeds import commercial_group_seed
    selected=[c for c in scope['cases'] if c['building_type']=='Warehouse']
    if not selected:return
    try:
        capture=payloads['warehouse-native-lock']
        cases={c['case_id']:c for c in capture['cases']}
        if len(cases)!=len(capture['cases']):raise ValueError('Native source case IDs repeat')
        bindings={b['program_id']:b for b in join['fixture_bindings']}
        expected_ids=[]
        for declaration in selected:
            binding=bindings[declaration['program_id']]
            members=binding.get('native_members',[dict(binding,program_id=declaration['program_id'])])
            for member in members:
                recipe=resources.get('program',member['program_id'])['recipe']
                context=recipe['source_context']
                probes=[('',42)]
                probes.extend(('@'+kind+'-'+str(seed),commercial_group_seed(seed,group))
                    for kind,group in [('instance',declaration['case_id']),('full_request',declaration['configuration_id'])]
                    for seed in (42,51))
                for suffix,draw_seed in probes:
                    identifier=member['native_case_id']+suffix;expected_ids.append(identifier)
                    actual=cases[identifier]
                    if actual['schedules']!=context['slot_sources']:
                        raise ValueError('Native room/member profiles differ from packaged source: '+identifier)
                    for key in ('case_id','configuration_id','configuration_association','standards_version','steps_per_hour',
                                'slot_modes','occupancy_aggregation','occupancy_adjustment','source_clock','carrier_program_id',
                                'source_discard_method_evidence','source_rounding_method_evidence','adaptation'):
                        if actual['source_context'][key]!=context[key]:
                            raise ValueError('Native source '+key+' differs from packaged association: '+identifier)
                    if actual['source_context']['year']!=scope['calendar']['year'] or actual['source_context']['holidays']:
                        raise ValueError('Native source calendar differs')
                    operating=sample_operating_parameters(declaration['configuration']['conditioning_inputs'],draw_seed,resources)
                    original=copy.deepcopy(actual['operating'])
                    for receipt in (operating,original):receipt.get('rng',{}).pop('python_version',None)
                    if operating!=original:raise ValueError('Native source/discrete public operating draw differs: '+identifier)
        if set(expected_ids)!=set(cases):raise ValueError('Actual native source case denominator differs')
    except (GeneratorError,KeyError,TypeError) as error:
        raise ValueError('Native source association is missing or invalid') from error


def _members(scope: dict, resources_root: Path | None = None) -> tuple[dict[str, bytes], str]:
    files = {'__main__.py': BOOTSTRAP}
    for path in sorted((ROOT / 'atlas_schedules').rglob('*')):
        if path.is_file() and path.suffix in {'.py', '.json'} and '__pycache__' not in path.parts:
            if resources_root is not None and path.is_relative_to(ROOT/'atlas_schedules/data'):
                continue
            files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    if resources_root is not None:
        for path in sorted(Path(resources_root).rglob('*.json')):
            files['atlas_schedules/data/'+path.relative_to(resources_root).as_posix()] = path.read_bytes()
        compiled_scope = strict_json(files['atlas_schedules/data/reference/m1-scope.json'],'source family scope')
        if compiled_scope['milestone_id'] in {'C4','C5','C6'}:
            certificate=strict_json(files['atlas_schedules/data/reference/family-certification.json'],'certificate')
            for name,digest in certificate['implementation_source_sha256'].items():
                if name.startswith('atlas_schedules/') and implementation_source_hash(files[name])!=digest:
                    raise ValueError('Packaged runtime differs from implementation source qualification')
        if compiled_scope['milestone_id'] == 'R1':
            for name in ('sources/schedule-generator-residential-scope.json',
                         'sources/schedule-generator-residential-lock.json',
                         'sources/schedule-generator-residential-family-reference-lock.json',
                         'data/schedule-generator/residential-family-native.json.gz'):
                files[name] = (ROOT/name).read_bytes()
        if compiled_scope['milestone_id'] in {'C2','C3','C4','C5','C6'}:
            for name in ('sources/schedule-generator-medium-office-scope.json',
                         'sources/schedule-generator-ruby-float-lock.json',
                         'data/schedule-generator/source-methods/ruby-numeric-v3_2_2.c',
                         'sources/schedule-generator-medium-office-lock.json',
                         'sources/schedule-generator-medium-office-cumulative-reference-lock.json',
                         'sources/schedule-generator-medium-office-family-reference-lock.json',
                         'sources/schedule-generator-residential-family-reference-lock.json',
                         'data/schedule-generator/medium-office-cumulative-native.json',
                         'data/schedule-generator/medium-office-family-native.json.gz',
                         'data/schedule-generator/residential-family-native.json.gz'):
                files[name] = (ROOT/name).read_bytes()
            if compiled_scope['milestone_id'] in {'C3','C4','C5','C6'}:
                for name in ('sources/schedule-generator-small-office-scope.json',
                             'sources/schedule-generator-small-office-lock.json',
                             'sources/schedule-generator-small-office-cumulative-reference-lock.json',
                             'sources/schedule-generator-small-office-family-reference-lock.json',
                             'data/schedule-generator/small-office-sampling-audit.json',
                             'data/schedule-generator/small-office-cumulative-native.json',
                             'data/schedule-generator/small-office-family-native.json.gz'):
                    files[name]=(ROOT/name).read_bytes()
            if compiled_scope['milestone_id'] in {'C4','C5','C6'}:
                for name in ('sources/schedule-generator-warehouse-scope.json',
                             'sources/schedule-generator-warehouse-lock.json',
                             'sources/schedule-generator-warehouse-cumulative-reference-lock.json',
                             'sources/schedule-generator-warehouse-family-reference-lock.json',
                             'data/schedule-generator/warehouse-sampling-audit.json',
                             'data/schedule-generator/warehouse-cumulative-native.json',
                             'data/schedule-generator/warehouse-family-native.json.gz'):
                    files[name]=(ROOT/name).read_bytes()
            current_resources=ResourceSet(Path(resources_root),strict_json(files['atlas_schedules/data/manifest.json'],'manifest')['resource_set_id'])
            validate_native_join(current_resources,compiled_scope)
            if compiled_scope['milestone_id'] in {'C5','C6'}:
                for name in ('sources/schedule-generator-restaurant-scope.json',
                    'sources/schedule-generator-restaurant-lock.json',
                    'sources/schedule-generator-restaurant-cumulative-reference-lock.json',
                    'sources/schedule-generator-restaurant-programme-reference-lock.json',
                    'sources/schedule-generator-restaurant-water-reference-lock.json',
                    'sources/schedule-generator-restaurant-water-public-reference-lock.json',
                    'data/schedule-generator/restaurant-cumulative-native.json',
                    'data/schedule-generator/reference/restaurant-native-discrete.json'):
                    files[name]=(ROOT/name).read_bytes()
                files.update(native_component_files(current_resources))
                validate_packaged_native_components(current_resources,files)
            if compiled_scope['milestone_id']=='C6':
                for name in ('sources/schedule-generator-retail-scope.json',
                    'sources/schedule-generator-retail-cumulative-reference-lock.json',
                    'sources/schedule-generator-retail-context-reference-lock.json',
                    'sources/schedule-generator-retail-programme-reference-lock.json',
                    'data/schedule-generator/retail-cumulative-native.json',
                    'data/schedule-generator/reference/retail-native-discrete.json'):
                    files[name]=(ROOT/name).read_bytes()
            join_name={'C2':'medium-office','C3':'small-office','C4':'warehouse','C5':'restaurant','C6':'retail'}[compiled_scope['milestone_id']]
            join=strict_json(files['data/schedule-generator/'+join_name+'-cumulative-native.json'],'native join')
            native_cases={};native_payloads={}
            for component in join['components']:
                vector=component['lock']['vectors']
                blob=files[vector['source_path']]
                if _digest(blob)!={'sha256':vector['sha256'],'size_bytes':vector['size_bytes']}:
                    raise ValueError('Packaged native component hash differs')
                if component['reference_resource_key']=='retail-programme-native-lock' or vector.get('format') is not None:
                    from scripts.schedule_generator_native_codec import decode_native_component
                    payload=decode_native_component(blob,component)
                else:
                    payload=gzip.decompress(blob)
                if hashlib.sha256(payload).hexdigest()!=vector['payload_sha256']:
                    raise ValueError('Packaged native component payload differs')
                captured=strict_json(payload,'native component')
                identifiers=[c['case_id'] for c in captured['cases']]
                if len(identifiers)!=len(set(identifiers)):
                    raise ValueError('Packaged native component repeats a case')
                native_cases[component['reference_resource_key']]=set(identifiers)
                if component['reference_resource_key']=='warehouse-native-lock':native_payloads[component['reference_resource_key']]=captured
            bindings=[member for binding in join['fixture_bindings'] for member in binding.get('native_members',[binding])]
            if any(binding['native_case_id'] not in native_cases[binding['reference_resource_key']] for binding in bindings):
                raise ValueError('Packaged native component misses a scoped configuration')
            validate_native_case_sources(ResourceSet(Path(resources_root),strict_json(files['atlas_schedules/data/manifest.json'],'manifest')['resource_set_id']),compiled_scope,join,native_payloads)
    for relative in ('sources/schedule-generator-m1-scope.json',
                     'sources/schedule-generator-policy.json',
                     'sources/schedule-evidence-lock.json',
                     'sources/completion-evidence-lock.json',
                     'sources/definition-evidence-lock.json',
                     'sources/water-evidence-lock.json',
                     'data/schedule-generator/comstock-sampling-audit.json',
                     'docs/schedule-generator.md',
                     'docs/validation/schedule-generator-coverage.json',
                     'LICENSE'):
        files[relative] = (ROOT / relative).read_bytes()
    for base in ('sources/licenses', 'docs/examples/schedule-generator-v1'):
        for path in sorted((ROOT / base).rglob('*')):
            if path.is_file():
                files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    if scope['milestone_id'] != 'M1':
        # A separately named partial milestone has its own closed runtime scope
        # and hence a new resource identity. Every other immutable record stays.
        files['atlas_schedules/data/reference/m1-scope.json'] = canonical(scope)
        manifest = strict_json(files['atlas_schedules/data/manifest.json'], 'manifest.json')
        entry = next(e for e in manifest['resources'] if e['kind'] == 'reference' and e['key'] == 'm1-scope')
        entry.update(_digest(files['atlas_schedules/data/reference/m1-scope.json']))
        manifest['cases'] = copy.deepcopy(scope['cases'])
        if 'service_cases' in scope:manifest['service_cases']=copy.deepcopy(scope['service_cases'])
        manifest['milestone_id'] = scope['milestone_id']
        manifest['scope_version'] = scope['scope_version']
        manifest['resource_set_id'] = manifest_identity(manifest)
        files['atlas_schedules/data/manifest.json'] = canonical(manifest)
        files['sources/schedule-generator-m1-scope.json'] = canonical(scope)
        original_root = Path(resources_root) if resources_root is not None else ROOT/'atlas_schedules/data'
        original_manifest = strict_json((original_root/'manifest.json').read_bytes(), 'resource manifest')
        original_resources = ResourceSet(original_root, original_manifest['resource_set_id'])
        partial_coverage = build_coverage(original_resources, scope)
        partial_coverage['resource_set_id'] = manifest['resource_set_id']
        files['docs/validation/schedule-generator-coverage.json'] = canonical(partial_coverage)
        example_root = 'docs/examples/schedule-generator-v1/'
        for name in list(files):
            if name.startswith(example_root):
                del files[name]
        files[example_root + 'README.md'] = (f"Complete example for {scope['milestone_id']}: "
                                                "references/all-cases-request.json and "
                                                "references/all-cases-bundle.json.gz.\n"
                                                "The request uses this release's resource identity.\n").encode()
        doc = files['docs/schedule-generator.md'].decode('utf-8')
        paragraphs = doc.split('\n\n')
        paragraphs[0] = f"# Offline schedule generator — {scope['milestone_id']}"
        paragraphs[1] = ("This independently frozen partial milestone contains an ordinary `generator.zip`. "
                         "Use Python 3.11+ with `python -I -S generator.zip --request REQUEST.json --output BUNDLE.json`. "
                         "Its own manifest declares the exact supported case set. The complete example is "
                         "`references/all-cases-request.json` with `references/all-cases-bundle.json.gz`.")
        paragraphs = [(f"This partial milestone declares exactly {len(scope['cases'])} source-certified case(s). "
                       "Its packaged coverage report lists all other catalogue identities as unsupported until separately bound. "
                       "A request outside this declaration fails clearly."
                       if p.startswith('M1 advertises exactly') else p) for p in paragraphs]
        files['docs/schedule-generator.md'] = '\n\n'.join(paragraphs).encode('utf-8')
        if resources_root is not None and compiled_scope['milestone_id'] == 'R1':
            files['docs/schedule-generator.md'] = (
                f"# Offline schedule generator — {scope['milestone_id']}\n\n"
                f"This immutable residential milestone declares {len(scope['cases'])} exact source fixture cases. "
                "The complete runnable request is `references/all-cases-request.json`; its numerical reference is "
                "`references/all-cases-bundle.json.gz`. Extract those files from this ZIP and run "
                "`python -I -S generator.zip --request REQUEST.json --output BUNDLE.json` from any directory. "
                f"The public API remains `atlas_schedules.generate(params, seed)`; use resource identity `{manifest['resource_set_id']}`.\n\n"
                "Each instance supplies its exact recipe operands shown in the request: residents, bedrooms, installed end uses, "
                "state, coordinates, physical UTC offset, station weather ID and thermostat arguments. Calendar is 2007, "
                "8760 local-standard hourly intervals, with no holidays or implicit DST. An explicit uint64 master seed is required. "
                "Instance order is source-significant: residential unit seeds multiply cumulatively by one-based position. "
                "The all-case request's seeds differ from independent single-fixture tests and original native fixture seeds.\n\n"
                "Original annual energy and volume targets are preserved before generated-amplitude binding. People counts, "
                "activity and controls retain their source semantics. Source-fixed schedules use actual day/month methods. "
                "Zero residents retain the native stochastic skip and explicit zero occupancy. EV and HVAC equipment-unavailability "
                "overlays remain excluded. Weather is the recorded ZIP-mapped station-proxy variant, not the unavailable county EPW.\n\n"
                "This intermediate family ZIP does not advertise commercial programs or cross-release mixtures. The packaged coverage "
                "report retains all outside-scope catalogue identities. A later cumulative resource set must prove generated and bound "
                "mixed-family members before advertising them. Sources, notices, native reference lock and independent family certification "
                "are packaged. Generation uses Python's standard library offline; native/source tools are development-only. "
                "Frozen artifact/resource checksums are integrity gates; fresh schedules are compared by source/discrete and numerical equivalence.\n"
            ).encode('utf-8')
        if resources_root is not None and compiled_scope['milestone_id'] in {'C2','C3','C4','C5','C6'}:
            guide_name={'C2':'medium-office','C3':'small-office','C4':'warehouse','C5':'restaurants','C6':'retail'}[compiled_scope['milestone_id']]
            guide = (ROOT/('docs/schedule-generator-'+guide_name+'.md')).read_text(encoding='utf-8')
            files['docs/schedule-generator.md'] = guide.replace('RESOURCE_SET_ID',manifest['resource_set_id']).encode('utf-8')
            if scope!=compiled_scope:
                templates=', '.join(sorted({c['template'] for c in scope['cases']}))
                declared_count=(f"{len(scope['cases'])} exact programme case(s) and {len(scope.get('service_cases',[]))} physical service/configuration case(s)"
                    if compiled_scope['milestone_id'] in {'C5','C6'} else f"{len(scope['cases'])} exact case(s)")
                files['docs/schedule-generator.md']=(
                    f"# Offline schedule generator — {scope['milestone_id']}\n\n"
                    f"This restricted milestone declares {declared_count}, selected from independently certified {compiled_scope['milestone_id']}. "
                    f"Included templates: {templates}. Resource identity: `{manifest['resource_set_id']}`. "
                    "Its complete runnable example is `references/all-cases-request.json`, with numerical reference "
                    "`references/all-cases-bundle.json.gz`. Extract the request and run "
                    "`python -I -S generator.zip --request REQUEST.json --output BUNDLE.json` from any directory. "
                    "The public API remains `atlas_schedules.generate(params, seed)`.\n\n"
                    "Only this manifest's exact case IDs are supported. Its coverage report enumerates other catalogue identities. "
                    "Original source/template/view targets, locked native component evidence, caller inputs and local-standard "
                    "2007 calendar remain explicit. Fresh reproduction uses source/discrete and numerical comparison; "
                    "frozen hashes verify artifact integrity. Runtime is offline Python standard library only. "
                    "Different resource identities cannot be composed. This restricted example does not advertise a mixed-family example.\n"
                ).encode('utf-8')
    else:
        manifest = strict_json(files['atlas_schedules/data/manifest.json'], 'manifest.json')
    return files, manifest['resource_set_id']


def _request(scope: dict, files: dict[str, bytes], resource_set_id: str) -> dict:
    if 'service_cases' in scope:
        if scope.get('qualification_request_order') is not None:
            from scripts.schedule_generator_retail import qualification_request
        else:
            from scripts.schedule_generator_restaurants import qualification_request
        records={('reference','m1-scope'):scope}
        pairs=[('program',c['program_id']) for c in scope['cases']]
        pairs.extend(('reference',c['resource_key']) for c in scope.get('service_cases',[]))
        for kind,key in pairs:
            records[kind,key]=strict_json(files['atlas_schedules/data/'+kind+'/'+key+'.json'],key)
        params=qualification_request(records);params['resource_set_id']=resource_set_id
        return {'schema_version':'1.1.0','params':params,'seed':42}
    instances = []
    for case in scope['cases']:
        record = strict_json(files[f"atlas_schedules/data/program/{case['program_id']}.json"], case['program_id'])
        inputs = copy.deepcopy(record['recipe']['bound_inputs'])
        if 'source_composition' in record['recipe']:inputs['composition_basis_mode']='source_reference_area_normalized'
        instances.append({'key': case['case_id'], 'program_id': case['program_id'], 'inputs': inputs,
                          'basis_bindings': {}, 'operating_group': None if 'residents' in inputs else ('medium-office-building' if scope['milestone_id']=='M1' else case['configuration_id'])})
    return {'schema_version': '1.0.0', 'params': {'resource_set_id': resource_set_id,
            'calendar': {'year': 2007, 'clock': 'local_standard_time', 'holidays': []},
            'instances': instances}, 'seed': 42}


def _mixed_request(scope: dict, resources: ResourceSet) -> dict:
    """Concrete caller-declared physical experiment from actual bound members."""
    if scope['milestone_id'] in {'C5','C6'}:
        if scope['milestone_id']=='C6':
            from scripts.schedule_generator_retail import mixed_qualification_request
        else:
            from scripts.schedule_generator_restaurants import mixed_qualification_request
        records={('reference','m1-scope'):scope}
        for case in scope['cases']:records['program',case['program_id']]=resources.get('program',case['program_id'])
        for case in scope['service_cases']:records['reference',case['resource_key']]=resources.get('reference',case['resource_key'])
        return mixed_qualification_request(records,resources.resource_set_id)
    residential=next(c for c in scope['cases'] if c['template']=='ResStock SDR source fixture'
                     and resources.get('program',c['program_id'])['recipe']['bound_inputs']['residents']>0)
    commercial=next(c for c in scope['cases'] if c['template']=='DOE Ref Pre-1980' and 'Office_MediumOffice' in c['name'])
    instances=[]
    members=[(residential,'dwelling_unit',1,'dwelling'),(commercial,'floor_area',100,'m2')]
    if scope['milestone_id'] in {'C3','C4'}:
        small=next(c for c in scope['cases'] if c['template']=='90.1-2013' and 'Office_SmallOffice' in c['name'])
        members.append((small,'floor_area',100,'m2'))
    if scope['milestone_id']=='C4':
        warehouse=next(c for c in scope['cases'] if c['template']=='90.1-2013' and c['building_type']=='Warehouse'
                       and resources.get('program',c['program_id'])['definition'].get('composition_id'))
        members.append((warehouse,'floor_area',100,'m2'))
    for case,basis,value,unit in members:
        recipe=resources.get('program',case['program_id'])['recipe']
        inputs=copy.deepcopy(recipe['bound_inputs'])
        if 'source_composition' in recipe:inputs['composition_basis_mode']='caller_parent_floor_area'
        instances.append({'key':case['case_id'],'program_id':case['program_id'],
            'inputs':inputs,
            'operating_group':None,'basis_bindings':{'extents':{basis:{'value':value,'unit':unit,
                'evidence':{'caller':'Explicit example experiment extent; no source geometry inferred'}}}}})
    return {'schema_version':'1.0.0','seed':42,'params':{'resource_set_id':resources.resource_set_id,
        'calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},'instances':instances,
        'mixture':{'program_id':'cumulative-residential-offices-warehouse' if scope['milestone_id']=='C4' else 'cumulative-residential-doe-office','composition_id':None,
            'members':[{'instance_key':i['key'],'weight':1/len(instances)} for i in instances],
            'result_basis':'floor_area','denominator':{'value':100*(len(instances)-1),'unit':'m2',
                'evidence':{'caller':'Explicit experiment result area; participation multipliers are not population weights'}}}}}


def _execute_zip(blob: bytes, request: dict) -> bytes:
    BUILD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=BUILD) as directory:
        root = Path(directory)
        archive = root / 'generator.zip'
        archive.write_bytes(blob)
        (root / 'request.json').write_bytes(canonical(request))
        output = root / 'bundle.json'
        command = [sys.executable, '-I', '-S', str(archive), '--request', str(root / 'request.json'), '--output', str(output)]
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=240)
        if result.returncode:
            raise ValueError(f'Packaged generator failed: {result.stderr[:2000]}')
        return output.read_bytes()


def freeze_generator(target: Path, version: str, scope: dict | None = None,
                     resources_root: Path | None = None) -> dict:
    if scope is not None and scope.get('milestone_id') == 'A1':
        from scripts.schedule_generator_apartment_certification import freeze_apartment_generator
        return freeze_apartment_generator(target,version,scope,resources_root)
    target = Path(target)
    if target.exists():
        raise ValueError('Immutable release target already exists; choose a new version')
    original_root = Path(resources_root) if resources_root is not None else ROOT/'atlas_schedules/data'
    approved = {'M1':'sources/schedule-generator-m1-scope.json',
                'R1':'sources/schedule-generator-residential-scope.json',
                'C2':'sources/schedule-generator-medium-office-scope.json',
                'C3':'sources/schedule-generator-small-office-scope.json',
                'C4':'sources/schedule-generator-warehouse-scope.json',
                'C5':'sources/schedule-generator-restaurant-scope.json',
                'C6':'sources/schedule-generator-retail-scope.json'}
    compiled_scope = strict_json((original_root/'reference/m1-scope.json').read_bytes(),'compiled source scope')
    family = compiled_scope.get('milestone_id')
    if family not in approved:
        raise ValueError('No approved source family for explicit resource root')
    authoritative = strict_json((ROOT/approved[family]).read_bytes(), 'authoritative source scope')
    if compiled_scope != authoritative:
        raise ValueError('Compiled scope differs from the approved source family')
    scope = copy.deepcopy(scope if scope is not None else authoritative)
    if scope['milestone_id'] == 'M1' and scope != authoritative:
        raise ValueError('M1 declaration must equal the authoritative ten-case scope')
    if (not scope['cases'] and not scope.get('service_cases') or
            len({case['case_id'] for case in scope['cases']}) != len(scope['cases'])):
        raise ValueError('Declared scope must contain distinct cases')
    manifest = strict_json((original_root/'manifest.json').read_bytes(), 'resource manifest')
    resources = ResourceSet(original_root, manifest['resource_set_id'])
    if resources.get('reference', 'm1-scope') != authoritative:
        raise ValueError('Compiled resource scope differs from authoritative M1')
    if any(case not in authoritative['cases'] for case in scope['cases']):
        raise ValueError('Unknown or modified source case in partial scope')
    if authoritative['milestone_id'] in {'C5','C6'}:
        services=scope.get('service_cases')
        if (not isinstance(services,list) or len({c['case_id'] for c in services})!=len(services) or
                any(c not in authoritative['service_cases'] for c in services)):
            raise ValueError('Unknown, duplicated or modified physical service/configuration in partial scope')
        allowed_changes={'milestone_id','cases','service_cases'}
        if authoritative['milestone_id']=='C6':
            selected={c['case_id'] for c in scope['cases']+services}
            expected_order=[key for key in authoritative['qualification_request_order'] if key in selected]
            if scope.get('qualification_request_order')!=expected_order:
                raise ValueError('Restricted C6 request order differs from authoritative selected order')
            allowed_changes.add('qualification_request_order')
        if {k:v for k,v in scope.items() if k not in allowed_changes}!={k:v for k,v in authoritative.items() if k not in allowed_changes}:
            raise ValueError('Modified source qualification metadata in partial scope')
    if resources_root is not None and authoritative['milestone_id'] in {'R1','C2','C3','C4','C5','C6'}:
        # Restricted runtimes select from the fully certified source family;
        # source evidence and operands remain tied to its exact full scope.
        validate_family_certification(resources, authoritative)
    audit = strict_json((ROOT / 'data/schedule-generator/comstock-sampling-audit.json').read_bytes(), 'commercial audit')
    if audit.get('gate_status') != 'passed' or audit.get('configuration_id') != authoritative['commercial_sampling_gate']['configuration_id']:
        raise ValueError('Commercial sampling gate not passed')
    coverage = build_coverage(resources, scope)
    errors = coverage_errors(coverage, resources)
    if errors:
        raise ValueError('Incomplete declared scope: ' + '; '.join(errors[:10]))
    files, resource_set_id = _members(scope, resources_root)
    if scope['milestone_id'] == 'M1' and strict_json(
            files['docs/validation/schedule-generator-coverage.json'], 'frozen coverage') != coverage:
        raise ValueError('Current M1 coverage report differs from closed packaged evidence')
    request = _request(scope, files, resource_set_id)
    generated = _execute_zip(_archive(files), request)
    bundle = strict_json(generated, 'generated reference bundle')
    requested={c['case_id'] for c in scope['cases']+scope.get('service_cases',[])}
    child_keys={k for a in bundle['generation'].get('source_compositions',[]) for k in a['member_instance_keys']}
    owners={c['instance_key']:c for c in bundle['constituents']}
    if len(owners)!=len(bundle['constituents']) or set(owners)!=requested|child_keys:
        raise ValueError('Generated requested/actual-member owner count differs from declared scope')
    from atlas_schedules.owners import owner_identity
    requested_instances={i['key']:i for i in request['params']['instances']}
    for case in scope['cases']+scope.get('service_cases',[]):
        constituent=owners[case['case_id']]
        declared_identity=owner_identity(requested_instances[case['case_id']])
        if case['case_id'] != constituent['instance_key'] or owner_identity(constituent)!=declared_identity:
            raise ValueError('Generated case identity differs from scope')
        expected = next(row for row in coverage['cases']+coverage.get('service_cases',[]) if row['case_id'] == case['case_id'])
        if set(constituent['schedule_ids']) != set(expected['expected_slots']):
            raise ValueError('Generated channels differ from complete declared channel list: ' + case['case_id'])
    if scope['milestone_id'] == 'M1':
        from atlas_schedules.comparison import compare_bundles
        original = strict_json(gzip.decompress((ROOT / 'docs/examples/schedule-generator-v1/all-declared-cases-bundle.json.gz').read_bytes()), 'source example')
        differences = compare_bundles(bundle, original, original['metadata']['comparison_policy'])
        if differences:
            raise ValueError('Task 8 source reference differs: ' + '; '.join(differences[:10]))
    files['references/all-cases-request.json'] = canonical(request)
    files['references/all-cases-bundle.json.gz'] = gzip.compress(generated, mtime=0)
    if scope['milestone_id'] in {'C2','C3','C4','C5','C6'} and scope==authoritative:
        mixed=_mixed_request(scope,resources)
        mixed['params']['resource_set_id']=resource_set_id
        files['references/mixed-family-request.json']=canonical(mixed)
        files['references/mixed-family-bundle.json.gz']=gzip.compress(_execute_zip(_archive(files),mixed),mtime=0)
    archive = _archive(files)
    release = {'schema_version': '1.0.0', 'release_version': version,
               'scope': {'milestone_id': scope['milestone_id'], 'scope_version': scope['scope_version'],
                         'case_count': len(scope['cases']), 'case_ids': [c['case_id'] for c in scope['cases']],
                         'sha256': hashlib.sha256(files['sources/schedule-generator-m1-scope.json']).hexdigest()},
               'resource_set_id': resource_set_id,
               'source_manifest_sha256': hashlib.sha256(files['atlas_schedules/data/manifest.json']).hexdigest(),
               'commercial_audit_sha256': hashlib.sha256(files['data/schedule-generator/comstock-sampling-audit.json']).hexdigest(),
               'files': {'generator.zip': _digest(archive)},
               'members': {name: _digest(content) for name, content in sorted(files.items())}}
    if 'service_cases' in scope:
        release['scope'].update(service_case_count=len(scope['service_cases']),
            service_case_ids=[c['case_id'] for c in scope['service_cases']],
            source_service_definition_count=len({c['source_service_id'] for c in scope['service_cases']}),
            declared_owned_slot_count=coverage['scope']['declared_owned_slot_count'],
            required_programme_service_link_count=coverage['scope']['required_programme_service_link_count'])
    target.mkdir(parents=True)
    (target / 'generator.zip').write_bytes(archive)
    (target / 'manifest.json').write_bytes(canonical(release))
    return release


def verify_generator(target: Path) -> list[str]:
    target = Path(target)
    errors = []
    try:
        manifest = strict_json((target / 'manifest.json').read_bytes(), 'manifest.json')
        if not isinstance(manifest,dict):raise ValueError('Expected release manifest object')
        if manifest.get('schema_version') == '2.0.0':
            from scripts.schedule_generator_release_reproduction import verify_v2_release
            try:verify_v2_release(target)
            except Exception as error:return [str(error)]
            return []
        if manifest.get('schema_version') != '1.0.0':
            errors.append('Invalid release schema version')
        if {p.name for p in target.iterdir()} != {'manifest.json', 'generator.zip'}:
            errors.append('Release file inventory differs')
        archive = (target / 'generator.zip').read_bytes()
        if _digest(archive) != manifest['files']['generator.zip']:
            errors.append('Frozen ZIP hash or size differs')
        with zipfile.ZipFile(io.BytesIO(archive)) as source:
            names = source.namelist()
            if len(names) != len(set(names)) or set(names) != set(manifest['members']):
                errors.append('Frozen ZIP member inventory differs')
            for name in names:
                safe_path(name)
                if _digest(source.read(name)) != manifest['members'][name]:
                    errors.append('Frozen member hash or size differs: ' + name)
            scope = strict_json(source.read('sources/schedule-generator-m1-scope.json'), 'scope')
            resource_manifest = strict_json(source.read('atlas_schedules/data/manifest.json'), 'resource manifest')
            if [case['case_id'] for case in scope['cases']] != manifest['scope']['case_ids'] or len(scope['cases']) != manifest['scope']['case_count']:
                errors.append('Frozen scope case inventory differs')
            if 'service_cases' in scope:
                if (manifest['scope'].get('service_case_ids')!=[c['case_id'] for c in scope['service_cases']] or
                        manifest['scope'].get('service_case_count')!=len(scope['service_cases']) or
                        resource_manifest.get('service_cases')!=scope['service_cases']):
                    errors.append('Frozen physical service/configuration inventory differs')
            if _digest(source.read('sources/schedule-generator-m1-scope.json'))['sha256'] != manifest['scope']['sha256']:
                errors.append('Frozen source scope hash differs')
            if resource_manifest['resource_set_id'] != manifest['resource_set_id'] or manifest_identity(resource_manifest) != manifest['resource_set_id']:
                errors.append('Frozen resource identity differs')
            if _digest(source.read('atlas_schedules/data/manifest.json'))['sha256'] != manifest['source_manifest_sha256']:
                errors.append('Frozen resource manifest hash differs')
            if _digest(source.read('data/schedule-generator/comstock-sampling-audit.json'))['sha256'] != manifest['commercial_audit_sha256']:
                errors.append('Frozen commercial audit hash differs')
            if strict_json(source.read('atlas_schedules/data/reference/m1-scope.json'), 'runtime scope') != scope:
                errors.append('Runtime and source scopes differ')
            for entry in resource_manifest['resources']:
                name = 'atlas_schedules/data/' + str(safe_path(entry['path']))
                if _digest(source.read(name)) != {'sha256': entry['sha256'], 'size_bytes': entry['size_bytes']}:
                    errors.append('Resource checksum differs: ' + name)
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as error:
        errors.append(str(error))
    return errors


def _release_reproduction_command(target: Path, receipt: Path) -> list[str]:
    """Small strict discovery only; expensive v2 verification stays in the child."""
    target=Path(target).resolve()
    manifest=strict_json((target/'manifest.json').read_bytes(),'manifest.json')
    if not isinstance(manifest,dict):raise ValueError('Expected release manifest object')
    if manifest.get('schema_version')=='1.0.0':
        return [sys.executable,'-I','-S',str(target/'generator.zip'),'--reproduce']
    if manifest.get('schema_version')=='2.0.0':
        if manifest.get('reference_layout')!='external_local_gzip_json_v1':
            raise ValueError('Unsupported version2 reference layout')
        return [sys.executable,'-I','-S',str(target/'reproduce.py'),'--release-root',str(target),'--receipt',str(Path(receipt).resolve())]
    raise ValueError('Unsupported release schema version')


def _pin_v2_runner(target: Path, manifest: dict) -> None:
    """Pin the small executable before launch; full verification repeats inside."""
    from scripts.schedule_generator_release_reproduction import _inventory,_regular,_identity,FILES
    _inventory(target)
    if not isinstance(manifest.get('files'),dict) or set(manifest['files'])!=FILES:
        raise ValueError('Invalid version2 runner file inventory')
    _identity(manifest['files']['reproduce.py'])
    runner=target/'reproduce.py';_regular(runner)
    if _digest(runner.read_bytes())!=manifest['files']['reproduce.py']:
        raise ValueError('Version2 runner identity differs before launch')


def _v2_reproduction_receipt(path: Path, manifest: dict, manifest_identity: dict) -> dict:
    """Require actual completed comparison and exact incoming transport identities."""
    receipt=strict_json(Path(path).read_bytes(),'reproduction receipt')
    if not isinstance(receipt,dict):raise ValueError('Expected reproduction receipt object')
    if not isinstance(receipt.get('input_identities'),dict):raise ValueError('Invalid receipt input identities')
    if (receipt.get('passed') is not True or receipt.get('strict_actual_validated') is not True
            or receipt.get('strict_expected_validated') is not True or receipt.get('comparison_difference_count')!=0
            or type(receipt.get('comparison_difference_count')) is not int
            or receipt.get('actual_counts')!={k:manifest['public_counts'][k] for k in ('constituents','schedules','bindings')}
            or receipt.get('requested_owners')!=manifest['public_counts']['requested_owners']
            or receipt.get('input_identities',{}).get('manifest.json')!=manifest_identity
            or any(receipt.get('input_identities',{}).get(k)!=v for k,v in manifest['files'].items())):
        raise ValueError('Missing/failed/inconsistent version2 scientific reproduction receipt')
    if (not all(type(v) is int for v in receipt['actual_counts'].values())
            or type(receipt.get('requested_owners')) is not int
            or receipt.get('request_identity')!={k:manifest['request'][k] for k in ('sha256','size_bytes')}
            or receipt.get('reference')!=manifest['reference']):
        raise ValueError('Version2 receipt counts/request/reference differ')
    modules=receipt.get('packaged_modules',{})
    required={'atlas_schedules.__main__','atlas_schedules.contract','atlas_schedules.resources','atlas_schedules.comparison'}
    if not isinstance(modules,dict) or not required<=set(modules):raise ValueError('Missing packaged module origins')
    for module in modules.values():
        if not isinstance(module,dict):raise ValueError('Invalid packaged module identity')
        name=module.get('path','');safe_path(name)
        if not name.startswith('atlas_schedules/') or {k:module.get(k) for k in ('sha256','size_bytes')}!=manifest['members'].get(name):
            raise ValueError('Foreign packaged module identity')
    return receipt


def reproduce_generator(target: Path) -> list[str]:
    # v2 verifies all actual files inside the one600s child, rather than spending
    # an unbounded verifier/decode before starting its development deadline.
    try:
        incoming_target=Path(target)
        target=incoming_target.resolve()
        manifest_blob=(target/'manifest.json').read_bytes()
        manifest=strict_json(manifest_blob,'manifest.json')
        if not isinstance(manifest,dict):raise ValueError('Expected release manifest object')
        if manifest.get('schema_version')=='2.0.0':
            _pin_v2_runner(incoming_target,manifest)
            with tempfile.TemporaryDirectory(prefix='atlas-release-dev-') as directory:
                work=Path(directory);receipt=work/'reproduction.json'
                command=_release_reproduction_command(target,receipt)
                result=subprocess.run(command,cwd=work,capture_output=True,text=True,timeout=COMPLETE_REPRODUCTION_TIMEOUT_SECONDS)
                if result.returncode:return ['Frozen runtime reproduction failed: '+result.stderr[:2000]]
                _v2_reproduction_receipt(receipt,manifest,_digest(manifest_blob))
                print(result.stdout.strip())
            return []
    except (OSError,ValueError,subprocess.TimeoutExpired) as error:
        return [str(error)]
    errors = verify_generator(target)
    if errors:
        return errors
    BUILD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=BUILD) as directory:
        result = subprocess.run([sys.executable, '-I', '-S', str(Path(target).resolve() / 'generator.zip'), '--reproduce'],
                                cwd=directory, capture_output=True, text=True,
                                timeout=COMPLETE_REPRODUCTION_TIMEOUT_SECONDS)
    if result.returncode:
        errors.append('Frozen runtime reproduction failed: ' + result.stderr[:2000])
    else:
        print(result.stdout.strip())
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=TARGET)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--reproduce', action='store_true')
    parser.add_argument('--scope')
    parser.add_argument('--resources-root', type=Path)
    args = parser.parse_args(argv)
    if sum((args.freeze, args.verify, args.reproduce)) != 1:
        parser.error('Choose exactly one of --freeze, --verify, --reproduce')
    if args.freeze:
        if args.scope=='a1':
            from scripts.schedule_generator_apartment_certification import apartment_scope
            scope=apartment_scope()
        else:
            scope = strict_json(Path(args.scope).read_bytes(), str(args.scope)) if args.scope else None
        manifest = freeze_generator(args.target, args.target.name.removeprefix('v'), scope, args.resources_root)
        print(f"Frozen {manifest['scope']['case_count']} cases at {args.target}")
    else:
        errors = verify_generator(args.target) if args.verify else reproduce_generator(args.target)
        if errors:
            raise SystemExit('\n'.join(errors))
        print('Frozen generator verified' if args.verify else 'Frozen generator reproduced')


if __name__ == '__main__':
    main()
