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
BOOTSTRAP = b'''"""Run an independent extracted release from this ordinary ZIP."""\nimport pathlib,runpy,sys,tempfile,zipfile\narchive=pathlib.Path(sys.argv[0]).resolve()\nwith tempfile.TemporaryDirectory(prefix="atlas-schedules-") as directory:\n    with zipfile.ZipFile(archive) as source:\n        names=source.namelist()\n        if len(names)!=len(set(names)) or any(name.startswith("/") or "\\\\" in name or ":" in name or any(part in ("..", ".", "") for part in name.split("/")) for name in names):\n            raise SystemExit("Unsafe ZIP inventory")\n        source.extractall(directory)\n    sys.path.insert(0,directory)\n    sys.argv[0]=str(archive)\n    if len(sys.argv)==2 and sys.argv[1]=="--reproduce":\n        runpy.run_module("atlas_schedules.reproduction",run_name="__main__")\n    else:\n        runpy.run_module("atlas_schedules.__main__",run_name="__main__")\n'''


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


def validate_native_join(resources: ResourceSet, scope: dict) -> None:
    """Close the cumulative scope against actual component resource hashes."""
    try:
        join=resources.get('reference','family-native-join')
        components=join['components']
        keys=[c['reference_resource_key'] for c in components]
        if keys!=['residential-native-lock','commercial-native-lock']:
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
            commercial=case['building_type']=='MediumOffice'
            key='commercial-native-lock' if commercial else 'residential-native-lock'
            component=by_key[key]
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
    if scope['milestone_id']=='C2': validate_native_join(resources,scope)


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
        if compiled_scope['milestone_id'] == 'R1':
            for name in ('sources/schedule-generator-residential-scope.json',
                         'sources/schedule-generator-residential-lock.json',
                         'sources/schedule-generator-residential-family-reference-lock.json',
                         'data/schedule-generator/residential-family-native.json.gz'):
                files[name] = (ROOT/name).read_bytes()
        if compiled_scope['milestone_id'] == 'C2':
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
            validate_native_join(ResourceSet(Path(resources_root),strict_json(files['atlas_schedules/data/manifest.json'],'manifest')['resource_set_id']),compiled_scope)
            join=strict_json(files['data/schedule-generator/medium-office-cumulative-native.json'],'native join')
            native_cases={}
            for component in join['components']:
                vector=component['lock']['vectors']
                blob=files[vector['source_path']]
                if _digest(blob)!={'sha256':vector['sha256'],'size_bytes':vector['size_bytes']}:
                    raise ValueError('Packaged native component hash differs')
                payload=gzip.decompress(blob)
                if hashlib.sha256(payload).hexdigest()!=vector['payload_sha256']:
                    raise ValueError('Packaged native component payload differs')
                captured=strict_json(payload,'native component')
                identifiers=[c['case_id'] for c in captured['cases']]
                if len(identifiers)!=len(set(identifiers)):
                    raise ValueError('Packaged native component repeats a case')
                native_cases[component['reference_resource_key']]=set(identifiers)
            if any(binding['native_case_id'] not in native_cases[binding['reference_resource_key']] for binding in join['fixture_bindings']):
                raise ValueError('Packaged native component misses a scoped configuration')
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
        if resources_root is not None and compiled_scope['milestone_id'] == 'C2':
            guide = (ROOT/'docs/schedule-generator-medium-office.md').read_text(encoding='utf-8')
            files['docs/schedule-generator.md'] = guide.replace('RESOURCE_SET_ID',manifest['resource_set_id']).encode('utf-8')
            if scope!=compiled_scope:
                templates=', '.join(sorted({c['template'] for c in scope['cases']}))
                files['docs/schedule-generator.md']=(
                    f"# Offline schedule generator — {scope['milestone_id']}\n\n"
                    f"This restricted milestone declares {len(scope['cases'])} exact case(s), selected from independently certified C2. "
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
    instances = []
    for case in scope['cases']:
        record = strict_json(files[f"atlas_schedules/data/program/{case['program_id']}.json"], case['program_id'])
        inputs = record['recipe']['bound_inputs']
        instances.append({'key': case['case_id'], 'program_id': case['program_id'], 'inputs': inputs,
                          'basis_bindings': {}, 'operating_group': None if 'residents' in inputs else ('medium-office-building' if scope['milestone_id']=='M1' else case['configuration_id'])})
    return {'schema_version': '1.0.0', 'params': {'resource_set_id': resource_set_id,
            'calendar': {'year': 2007, 'clock': 'local_standard_time', 'holidays': []},
            'instances': instances}, 'seed': 42}


def _mixed_request(scope: dict, resources: ResourceSet) -> dict:
    """Concrete caller-declared physical experiment from actual bound members."""
    residential=next(c for c in scope['cases'] if c['building_type']!='MediumOffice'
                     and resources.get('program',c['program_id'])['recipe']['bound_inputs']['residents']>0)
    commercial=next(c for c in scope['cases'] if c['template']=='DOE Ref Pre-1980' and 'Office_MediumOffice' in c['name'])
    instances=[]
    for case,basis,value,unit in [(residential,'dwelling_unit',1,'dwelling'),(commercial,'floor_area',100,'m2')]:
        instances.append({'key':case['case_id'],'program_id':case['program_id'],
            'inputs':copy.deepcopy(resources.get('program',case['program_id'])['recipe']['bound_inputs']),
            'operating_group':None,'basis_bindings':{'extents':{basis:{'value':value,'unit':unit,
                'evidence':{'caller':'Explicit example experiment extent; no source geometry inferred'}}}}})
    return {'schema_version':'1.0.0','seed':42,'params':{'resource_set_id':resources.resource_set_id,
        'calendar':{'year':2007,'clock':'local_standard_time','holidays':[]},'instances':instances,
        'mixture':{'program_id':'cumulative-residential-doe-office','composition_id':None,
            'members':[{'instance_key':i['key'],'weight':.5} for i in instances],
            'result_basis':'floor_area','denominator':{'value':100,'unit':'m2',
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
    target = Path(target)
    if target.exists():
        raise ValueError('Immutable release target already exists; choose a new version')
    original_root = Path(resources_root) if resources_root is not None else ROOT/'atlas_schedules/data'
    approved = {'M1':'sources/schedule-generator-m1-scope.json',
                'R1':'sources/schedule-generator-residential-scope.json',
                'C2':'sources/schedule-generator-medium-office-scope.json'}
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
    if not scope['cases'] or len({case['case_id'] for case in scope['cases']}) != len(scope['cases']):
        raise ValueError('Declared scope must contain distinct cases')
    manifest = strict_json((original_root/'manifest.json').read_bytes(), 'resource manifest')
    resources = ResourceSet(original_root, manifest['resource_set_id'])
    if resources.get('reference', 'm1-scope') != authoritative:
        raise ValueError('Compiled resource scope differs from authoritative M1')
    if any(case not in authoritative['cases'] for case in scope['cases']):
        raise ValueError('Unknown or modified source case in partial scope')
    if resources_root is not None and authoritative['milestone_id'] in {'R1','C2'}:
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
    if len(bundle['constituents']) != len(scope['cases']):
        raise ValueError('Generated case count differs from declared scope')
    for case, constituent in zip(scope['cases'], bundle['constituents']):
        if case['case_id'] != constituent['instance_key'] or case['program_id'] != constituent['program_id']:
            raise ValueError('Generated case identity differs from scope')
        expected = next(row for row in coverage['cases'] if row['case_id'] == case['case_id'])
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
    if scope['milestone_id']=='C2' and len(scope['cases'])==len(authoritative['cases']):
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
    target.mkdir(parents=True)
    (target / 'generator.zip').write_bytes(archive)
    (target / 'manifest.json').write_bytes(canonical(release))
    return release


def verify_generator(target: Path) -> list[str]:
    target = Path(target)
    errors = []
    try:
        manifest = strict_json((target / 'manifest.json').read_bytes(), 'manifest.json')
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


def reproduce_generator(target: Path) -> list[str]:
    errors = verify_generator(target)
    if errors:
        return errors
    BUILD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=BUILD) as directory:
        result = subprocess.run([sys.executable, '-I', '-S', str(Path(target).resolve() / 'generator.zip'), '--reproduce'],
                                cwd=directory, capture_output=True, text=True, timeout=300)
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
    parser.add_argument('--scope', type=Path)
    parser.add_argument('--resources-root', type=Path)
    args = parser.parse_args(argv)
    if sum((args.freeze, args.verify, args.reproduce)) != 1:
        parser.error('Choose exactly one of --freeze, --verify, --reproduce')
    if args.freeze:
        scope = strict_json(args.scope.read_bytes(), str(args.scope)) if args.scope else None
        manifest = freeze_generator(args.target, args.target.name.removeprefix('v'), scope, args.resources_root)
        print(f"Frozen {manifest['scope']['case_count']} cases at {args.target}")
    else:
        errors = verify_generator(args.target) if args.verify else reproduce_generator(args.target)
        if errors:
            raise SystemExit('\n'.join(errors))
        print('Frozen generator verified' if args.verify else 'Frozen generator reproduced')


if __name__ == '__main__':
    main()
