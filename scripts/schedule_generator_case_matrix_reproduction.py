"""Standalone layout-3 (case-matrix) release verifier and streaming reproducer.

This exact stdlib source is shipped as reproduce.py. It verifies the four local
release files, extracts generator.zip, generates both admitted case requests
with the packaged generator, streams the original union in canonical byte
order and compares it byte for byte with references/all-cases-bundle.json.gz
(ruling 145). Neither the union nor the reference is ever held as one graph.
When this interpreter differs from the reference producer, only
rng.python_version is normalized, per the packaged comparison policy's
ignored_administrative_fields (ruling 146). No checkout import, nested
process or network access is used.

    python -I -S reproduce.py --release-root RELEASE --receipt OUTSIDE/receipt.json
"""
import argparse
import gzip
import hashlib
import importlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import sys
import sysconfig
import tempfile
import time
import zipfile

FILES = {'generator.zip', 'reproduce.py', 'references/all-cases-bundle.json.gz'}
REQUEST = 'references/all-cases-request.json'
REFERENCE = 'references/all-cases-bundle.json.gz'
PRODUCERS = {'scripts/schedule_generator_release.py', 'scripts/schedule_generator_apartment_certification.py',
             'scripts/schedule_generator_release_reproduction.py', 'scripts/schedule_generator_case_matrix_release.py',
             'scripts/schedule_generator_case_matrix_reproduction.py'}
RUNNER = 'scripts/schedule_generator_case_matrix_reproduction.py'
MATRIX_INPUTS = ('full-request.json.gz', 'resource-manifest.json.gz', 'r74-design-mapping.json.gz')
MATRIX_CODE = ('schedule_generator_case_matrix.py', 'schedule_generator_case_matrix_stream.py')
CAP = 104857600


def _require(condition, message):
    if not condition: raise ValueError(message)


def _canonical(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':'))+'\n').encode()


def _json(blob):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'Duplicate JSON key'); result[key] = value
        return result
    def number(token):
        value = float(token); _require(math.isfinite(value), 'Nonfinite JSON number'); return value
    return json.loads(blob, object_pairs_hook=pairs, parse_float=number,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON constant')))


def _digest(blob): return {'sha256': hashlib.sha256(blob).hexdigest(), 'size_bytes': len(blob)}


def _path(name):
    _require(isinstance(name, str) and name and '\\' not in name and ':' not in name, 'Unsafe path')
    p = PurePosixPath(name); reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{a}{i}' for a in ('COM', 'LPT') for i in range(1, 10)}
    _require(not p.is_absolute() and all(x not in {'', '.', '..'} and not x.endswith(('.', ' '))
             and x.split('.')[0].upper() not in reserved for x in name.split('/')), 'Unsafe path')
    return p


def _unique_paths(names):
    prefixes = {}
    _require(len(names) == len(set(names)), 'Duplicate path')
    for name in names:
        parts = _path(name).parts
        for i in range(1, len(parts)+1):
            prefix = '/'.join(parts[:i]); key = prefix.casefold()
            _require(key not in prefixes or prefixes[key] == prefix, 'Case-colliding path'); prefixes[key] = prefix


def _identity(entry, *, positive=True):
    _require(isinstance(entry, dict) and set(entry) == {'sha256', 'size_bytes'}, 'Invalid identity fields')
    _require(isinstance(entry['sha256'], str) and re.fullmatch('[0-9a-f]{64}', entry['sha256']) is not None, 'Invalid SHA256')
    _require(type(entry['size_bytes']) is int and entry['size_bytes'] >= (1 if positive else 0), 'Invalid byte size')


def _member(entry, path):
    _require(isinstance(entry, dict) and set(entry) == {'location', 'path', 'sha256', 'size_bytes'}
             and entry['location'] == 'generator_zip_member' and entry['path'] == path, 'Invalid member descriptor: '+path)
    identity = {k: entry[k] for k in ('sha256', 'size_bytes')}; _identity(identity)
    return identity


def _reparse(path):
    return getattr(path.lstat(), 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024)


def _inventory(root):
    _require(root.is_dir() and not root.is_symlink() and not _reparse(root), 'Release root must be a regular directory')
    root = root.resolve(); found = []; directories = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs+files:
            path = Path(directory)/name; info = path.lstat()
            _require(not path.is_symlink() and not _reparse(path), 'Symlink/reparse input rejected')
            _require(path.resolve().is_relative_to(root), 'Input escapes release root')
            if name in files:
                _require(stat.S_ISREG(info.st_mode), 'Input is not a regular file'); found.append(path.relative_to(root).as_posix())
            else:
                _require(stat.S_ISDIR(info.st_mode), 'Foreign directory type'); directories.append(path.relative_to(root).as_posix())
    _unique_paths(found)
    _require(set(found) == FILES | {'manifest.json'}, 'Release file inventory differs')
    _require(set(directories) == {'references'}, 'Release directory inventory differs')


def _manifest(manifest):
    required = {'schema_version', 'release_version', 'scope', 'resource_set_id', 'source_manifest_sha256',
                'commercial_audit_sha256', 'files', 'members', 'public_counts', 'reference_layout', 'bundle_schema_version',
                'entrypoints', 'request', 'reference', 'implementation_sources', 'case_matrix'}
    _require(isinstance(manifest, dict) and set(manifest) == required, 'Invalid layout-3 manifest fields')
    _require(manifest['schema_version'] == '3.0.0' and manifest['reference_layout'] == 'external_local_gzip_json_v1'
             and manifest['bundle_schema_version'] == '1.2.0', 'Unsupported release layout/version')
    _require(isinstance(manifest['release_version'], str) and manifest['release_version'], 'Invalid release version')
    _require(isinstance(manifest['resource_set_id'], str) and re.fullmatch('resources-[0-9a-f]{64}', manifest['resource_set_id']) is not None,
             'Invalid resource identity')
    for field in ('source_manifest_sha256', 'commercial_audit_sha256'): _identity({'sha256': manifest[field], 'size_bytes': 1})
    _require(manifest['entrypoints'] == {'generation': {'kind': 'zip_request_output', 'path': 'generator.zip'},
             'reproduction': {'kind': 'release_script', 'path': 'reproduce.py'}}, 'Unsupported entrypoints')
    _require(isinstance(manifest['files'], dict) and set(manifest['files']) == FILES, 'Invalid file inventory')
    for entry in manifest['files'].values(): _identity(entry); _require(entry['size_bytes'] <= CAP, 'Transported file exceeds104857600')
    members = manifest['members']
    _require(isinstance(members, dict) and members, 'Invalid member inventory'); _unique_paths(list(members))
    for entry in members.values(): _identity(entry, positive=False); _require(entry['size_bytes'] <= CAP, 'Tracked member exceeds104857600')
    _require(members.get(REQUEST) == _member(manifest['request'], REQUEST), 'Request member identity differs')
    reference = manifest['reference']
    _require(isinstance(reference, dict) and set(reference) == {'location', 'path', 'codec', 'sha256', 'size_bytes', 'decoded_sha256',
             'decoded_size_bytes', 'producer_python_version'} and reference['location'] == 'release_file'
             and reference['path'] == REFERENCE and reference['codec'] == 'gzip-json-v1', 'Invalid reference descriptor')
    _identity({k: reference[k] for k in ('sha256', 'size_bytes')})
    _identity({'sha256': reference['decoded_sha256'], 'size_bytes': reference['decoded_size_bytes']})
    _require(isinstance(reference['producer_python_version'], str) and
             re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', reference['producer_python_version']) is not None, 'Invalid producer version')
    _require(manifest['files'][REFERENCE] == {k: reference[k] for k in ('sha256', 'size_bytes')}, 'Reference file identity differs')
    _require(REFERENCE not in members, 'Ambiguous inline/external reference')
    scope = manifest['scope']
    _require(isinstance(scope, dict) and {'milestone_id', 'scope_version', 'case_ids', 'case_count', 'sha256'} <= set(scope), 'Invalid scope')
    _require(isinstance(scope['case_ids'], list) and type(scope['case_count']) is int and scope['case_count'] == len(scope['case_ids'])
             == len(set(scope['case_ids'])), 'Invalid scope case inventory')
    counts = manifest['public_counts']
    _require(isinstance(counts, dict) and set(counts) == {'requested_owners', 'constituents', 'schedules', 'bindings'}
             and all(type(v) is int and v >= 0 for v in counts.values()), 'Invalid public counts')
    implementations = manifest['implementation_sources']
    _require(isinstance(implementations, dict) and set(implementations) == PRODUCERS, 'Missing explicit runner/producer provenance')
    for name, entry in implementations.items():
        _require(members.get('provenance/implementation/'+name) == _member(entry, 'provenance/implementation/'+name),
                 'Implementation member identity differs')
    runner = implementations[RUNNER]
    _require(manifest['files']['reproduce.py'] == {k: runner[k] for k in ('sha256', 'size_bytes')}, 'Shipped runner differs from producer provenance')
    matrix = manifest['case_matrix']
    _require(isinstance(matrix, dict) and set(matrix) == {'contract_version', 'case_order', 'cases', 'inputs', 'code'}
             and matrix['contract_version'] == '1.0.0', 'Invalid case-matrix descriptor')
    order = matrix['case_order']
    _require(isinstance(order, list) and len(order) >= 1 and all(isinstance(c, str) and c for c in order)
             and len(order) == len(set(order)), 'Invalid case order')
    _require(isinstance(matrix['cases'], list) and [c.get('case_id') if isinstance(c, dict) else None for c in matrix['cases']] == order,
             'Case descriptors differ from case order')
    for case in matrix['cases']:
        _require(set(case) == {'case_id', 'request', 'requested_owners'} and type(case['requested_owners']) is int
                 and case['requested_owners'] > 0, 'Invalid case descriptor')
        path = 'references/case-matrix/'+case['case_id']+'.request.json'
        _require(members.get(path) == _member(case['request'], path), 'Case request member identity differs')
    _require(sum(c['requested_owners'] for c in matrix['cases']) == counts['requested_owners'], 'Case owners do not partition the request')
    _require(isinstance(matrix['inputs'], dict) and set(matrix['inputs']) == set(MATRIX_INPUTS), 'Invalid case-matrix inputs')
    for name, entry in matrix['inputs'].items():
        _require(members.get('case_matrix/inputs/'+name) == _member(entry, 'case_matrix/inputs/'+name), 'Case-matrix input identity differs')
    _require(isinstance(matrix['code'], dict) and set(matrix['code']) == set(MATRIX_CODE), 'Invalid case-matrix code')
    for name, entry in matrix['code'].items():
        _require(members.get('case_matrix/'+name) == _member(entry, 'case_matrix/'+name), 'Case-matrix code identity differs')


def _file_identity(path):
    digest = hashlib.sha256(); count = 0
    with path.open('rb') as stream:
        while chunk := stream.read(1048576): count += len(chunk); digest.update(chunk)
    return {'sha256': digest.hexdigest(), 'size_bytes': count}


def verify_v3_release(release_root: Path) -> dict:
    """Verify transport identities and packaged inventories; never scientific authority.

    The decoded reference identity is checked during the streaming comparison.
    """
    incoming = Path(release_root)
    _require(not incoming.is_symlink() and not _reparse(incoming), 'Symlink/reparse release root rejected')
    root = incoming.resolve()
    _inventory(root); manifest_bytes = (root/'manifest.json').read_bytes(); manifest = _json(manifest_bytes); _manifest(manifest)
    identities = {'manifest.json': _digest(manifest_bytes)}
    for name, expected in manifest['files'].items():
        identities[name] = _file_identity(root/name)
        _require(identities[name] == expected, 'Release file hash/size differs: '+name)
    with zipfile.ZipFile(root/'generator.zip') as archive:
        names = archive.namelist(); _unique_paths(names); _require(set(names) == set(manifest['members']), 'ZIP member inventory differs')
        for info in archive.infolist():
            _require(not info.is_dir() and not info.flag_bits & 1 and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG),
                     'Unsafe ZIP member type')
            _require(info.file_size == manifest['members'][info.filename]['size_bytes'], 'ZIP member declared size differs')
            digest = hashlib.sha256(); count = 0
            with archive.open(info) as stream:
                while chunk := stream.read(1048576):
                    count += len(chunk); _require(count <= info.file_size, 'ZIP member size overflow'); digest.update(chunk)
            _require({'sha256': digest.hexdigest(), 'size_bytes': count} == manifest['members'][info.filename],
                     'ZIP member identity differs: '+info.filename)
        read = lambda name: _json(archive.read(name))
        scope = read('sources/schedule-generator-m1-scope.json'); resources = read('atlas_schedules/data/manifest.json')
        _require(hashlib.sha256(archive.read('sources/schedule-generator-m1-scope.json')).hexdigest() == manifest['scope']['sha256'],
                 'Source scope hash differs')
        _require([c['case_id'] for c in scope['cases']] == manifest['scope']['case_ids'], 'Scope case inventory differs')
        for field in ('milestone_id', 'scope_version'): _require(scope.get(field) == manifest['scope'][field], 'Scope label differs')
        _require(read('atlas_schedules/data/reference/m1-scope.json') == scope, 'Runtime/source scope differs')
        rid = 'resources-'+hashlib.sha256(_canonical({k: v for k, v in resources.items() if k != 'resource_set_id'})).hexdigest()
        _require(resources.get('schema_version') == '1.0.0' and resources['resource_set_id'] == rid == manifest['resource_set_id'],
                 'Resource identity differs')
        _require(hashlib.sha256(archive.read('atlas_schedules/data/manifest.json')).hexdigest() == manifest['source_manifest_sha256'],
                 'Resource manifest hash differs')
        _require(hashlib.sha256(archive.read('data/schedule-generator/comstock-sampling-audit.json')).hexdigest()
                 == manifest['commercial_audit_sha256'], 'Commercial audit hash differs')
        if 'service_cases' in scope:
            _require(manifest['scope'].get('service_case_ids') == [c['case_id'] for c in scope['service_cases']]
                     and manifest['scope'].get('service_case_count') == len(scope['service_cases'])
                     and resources.get('service_cases') == scope['service_cases'], 'Physical service/configuration inventory differs')
        resource_paths = []; resource_keys = []
        for entry in resources['resources']:
            name = 'atlas_schedules/data/'+str(_path(entry['path'])); resource_paths.append(name); resource_keys.append((entry['kind'], entry['key']))
            _require(manifest['members'].get(name) == {k: entry[k] for k in ('sha256', 'size_bytes')}, 'Resource member checksum differs')
        _unique_paths(resource_paths); _require(len(resource_keys) == len(set(resource_keys)), 'Duplicate resource identity')
        _require(set(n for n in names if n.startswith('atlas_schedules/data/')) == set(resource_paths) | {'atlas_schedules/data/manifest.json'},
                 'Resource inventory differs')
        policy = [e for e in resources['resources'] if (e['kind'], e['key']) == ('reference', 'comparison-policy')]
        _require(len(policy) == 1, 'Exact packaged comparison policy required')
        policy_member = 'atlas_schedules/data/'+policy[0]['path']
        def wrapper(name):
            value = read(name)
            _require(isinstance(value, dict) and set(value) == {'schema_version', 'params', 'seed'} and value['schema_version'] == '1.2.0'
                     and isinstance(value['params'], dict) and value['params'].get('schema_version') == '1.2.0'
                     and value['params'].get('resource_set_id') == rid and type(value['seed']) is int and 0 <= value['seed'] < 2**64,
                     'Invalid packaged request wrapper/version/identity: '+name)
            return value
        full = wrapper(REQUEST)
        _require(len(full['params']['instances']) == manifest['public_counts']['requested_owners'], 'Requested owner count differs')
        for case in manifest['case_matrix']['cases']:
            value = wrapper(case['request']['path'])
            _require(len(value['params']['instances']) == case['requested_owners'], 'Case owner count differs: '+case['case_id'])
        for name in ('__main__.py', 'atlas_schedules/__main__.py', 'atlas_schedules/generator.py', 'atlas_schedules/contract.py',
                     'atlas_schedules/resources.py'):
            _require(name in manifest['members'], 'Missing packaged entry/validator: '+name)
    return {'manifest': manifest, 'release_root': root, 'input_identities': identities, 'policy_member': policy_member}


def _install_isolation(root, work, extraction, state, receipt):
    stdlib = Path(sysconfig.get_path('stdlib')).resolve(); base = Path(sys.base_prefix).resolve()
    def audit(event, args):
        if event.startswith(('socket.', 'subprocess.')) or event in {'os.system', 'os.posix_spawn', 'os.spawn'}:
            raise RuntimeError('Network/subprocess denied: '+event)
        if event != 'open' or isinstance(args[0], int): return
        path = Path(os.fsdecode(args[0])).resolve(); mode = args[1] or ''; flags = args[2]
        writing = any(c in mode for c in 'wax+') or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        if writing:
            _require(path.is_relative_to(work) or (state['phase'] == 'receipt' and path == receipt), 'Write outside owned work denied'); return
        _require(not any(p in {'site-packages', 'dist-packages'} for p in path.parts), 'Ambient package denied')
        if state['phase'] == 'generation':
            allowed = path.is_relative_to(extraction/'atlas_schedules') or path.is_relative_to(extraction/'case_matrix')
        elif state['phase'] == 'comparison':
            allowed = path == root/REFERENCE or path.is_relative_to(extraction/'atlas_schedules') or path.is_relative_to(extraction/'case_matrix')
        else:
            allowed = path.is_relative_to(work) or path.is_relative_to(root)
        allowed = allowed or path.is_relative_to(stdlib) or (path.is_relative_to(base) and path.suffix in {'.zip', '.pyd', '.dll'})
        _require(allowed, 'Read outside verified execution inputs denied: '+str(path))
    sys.addaudithook(audit)


def _peak_memory():
    """Best-effort Windows process counters; None means unknown."""
    if os.name != 'nt': return None
    try:
        import ctypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong), ('PeakWorkingSetSize', ctypes.c_size_t),
                        ('WorkingSetSize', ctypes.c_size_t), ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPagedPoolUsage', ctypes.c_size_t), ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaNonPagedPoolUsage', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t),
                        ('PeakPagefileUsage', ctypes.c_size_t), ('PrivateUsage', ctypes.c_size_t)]
        kernel32 = ctypes.WinDLL('kernel32'); psapi = ctypes.WinDLL('psapi')
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        counters = Counters(); counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb): return None
        return {'peak_working_set_bytes': counters.PeakWorkingSetSize, 'peak_commit_bytes': counters.PeakPagefileUsage}
    except (OSError, AttributeError):
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument('--release-root', required=True, type=Path); parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args(argv); root = args.release_root.resolve(); receipt = args.receipt.resolve()
    _require(not args.receipt.is_symlink(), 'Symlink receipt rejected')
    _require(not receipt.is_relative_to(root) and not receipt.exists(), 'Receipt must be new and outside release')
    _require(not any(n == 'atlas_schedules' or n.startswith('atlas_schedules.') for n in sys.modules), 'Preloaded atlas_schedules modules rejected')
    started = time.perf_counter(); phases = {}
    with tempfile.TemporaryDirectory(prefix='atlas-v3-repro-') as directory:
        work = Path(directory).resolve(); extraction = work/'package'; extraction.mkdir()
        verified = verify_v3_release(args.release_root); manifest = verified['manifest']
        _require(_digest(Path(__file__).read_bytes()) == manifest['files']['reproduce.py'], 'Executing runner differs from verified runner')
        with zipfile.ZipFile(root/'generator.zip') as archive: archive.extractall(extraction)
        phases['verify_and_extract'] = time.perf_counter()-started
        state = {'phase': 'import'}; _install_isolation(root, work, extraction, state, receipt)
        sys.path.insert(0, str(extraction/'case_matrix')); sys.path.insert(0, str(extraction))
        package = importlib.import_module('atlas_schedules')
        resources = importlib.import_module('atlas_schedules.resources')
        adapter = importlib.import_module('schedule_generator_case_matrix')
        comparer = importlib.import_module('schedule_generator_case_matrix_stream')
        _require(Path(adapter.__file__).resolve() == extraction/'case_matrix/schedule_generator_case_matrix.py' and
                 Path(comparer.__file__).resolve() == extraction/'case_matrix/schedule_generator_case_matrix_stream.py',
                 'Foreign case-matrix module origin')
        state['phase'] = 'inputs'
        inputs = [resources.strict_json(gzip.decompress((extraction/'case_matrix/inputs'/name).read_bytes()), name) for name in MATRIX_INPUTS]
        matrix = adapter.compile_case_matrix(*inputs)
        _require(matrix['case_order'] == manifest['case_matrix']['case_order'], 'Packaged matrix case order differs')
        _require((extraction/REQUEST).read_bytes() == _canonical(matrix['full_request']), 'Packaged full request differs from the admitted matrix')
        policy = resources.strict_json((extraction/verified['policy_member']).read_bytes(), 'packaged comparison policy')
        for case in matrix['mapping']['cases']:
            _require((extraction/'references/case-matrix'/(case['case_id']+'.request.json')).read_bytes() == _canonical(case['request']),
                     'Packaged case request differs from the admitted matrix: '+case['case_id'])
        counts = {'constituents': 0, 'schedules': 0, 'bindings': 0}; cases = {}
        def generated(case_id, bundle, seconds):
            cases[case_id] = {'seconds': seconds, 'constituents': len(bundle['constituents']),
                              'schedules': len(bundle['schedules']), 'bindings': len(bundle['bindings'])}
            for key in counts: counts[key] += cases[case_id][key]
        state['phase'] = 'generation'; phase_start = time.perf_counter()
        pieces = adapter.generate_and_stream_union(matrix, package.generate, generated)
        phases['generation_and_union_checks'] = time.perf_counter()-phase_start
        reference = manifest['reference']; version = platform.python_version(); normalize = None
        if version != reference['producer_python_version']:
            _require('rng.python_version' in policy.get('ignored_administrative_fields', []),
                     'Packaged comparison policy does not allow rng.python_version normalization')
            normalize = comparer.runtime_version_normalizer(version, reference['producer_python_version'])
        state['phase'] = 'comparison'; phase_start = time.perf_counter()
        result = comparer.compare_canonical_stream(
            pieces, root/REFERENCE, compressed={k: reference[k] for k in ('sha256', 'size_bytes')},
            decoded={'sha256': reference['decoded_sha256'], 'size_bytes': reference['decoded_size_bytes']}, normalize=normalize)
        phases['stream_and_compare'] = time.perf_counter()-phase_start
        _require(result['status'] == 'MATCH', 'Union differs from the reference: '+json.dumps(result['first_difference']))
        _require(all(counts[k] == manifest['public_counts'][k] for k in counts), 'Actual output counts differ: '+json.dumps(counts))
        modules = {}
        for name, module in list(sys.modules.items()):
            if name == 'atlas_schedules' or name.startswith('atlas_schedules.') or name.startswith('schedule_generator_case_matrix'):
                path = Path(module.__file__).resolve(); _require(path.is_relative_to(extraction), 'Foreign module origin')
                modules[name] = {'path': path.relative_to(extraction).as_posix(), **_digest(path.read_bytes())}
        output = {'schema_version': '3.0.0', 'passed': True, 'runtime': sys.version, 'python_version': version,
                  'platform': {'sys_platform': sys.platform, 'machine': sysconfig.get_platform()},
                  'elapsed_seconds': time.perf_counter()-started, 'phases': phases, 'cases': cases,
                  'input_identities': verified['input_identities'], 'reference': reference,
                  'normalization': None if normalize is None else {'field': 'rng.python_version', 'generated': version,
                                                                   'reference': reference['producer_python_version'],
                                                                   'substitutions': result['normalized_substitutions']},
                  'comparison': {k: result[k] for k in ('status', 'pieces', 'generated', 'reference')},
                  'validation': {'cases': 'validate_bundle inside packaged generate()',
                                 'union': 'not revalidated; byte-equal to the authenticated reference (R145)'},
                  'actual_counts': counts, 'packaged_modules': modules, 'memory': _peak_memory()}
        content = _canonical(output); state['phase'] = 'receipt'
        with receipt.open('xb') as stream: stream.write(content)
        print('Case-matrix union reproduced byte for byte: '+json.dumps(counts))
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as error:
        print(type(error).__name__+': '+str(error), file=sys.stderr); raise SystemExit(1)
