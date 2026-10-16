"""Build and profile the layout-3 (case-matrix) apartment release (rulings 145, 146).

freeze: assemble the unchanged layout-2 apartment members, add the admitted
case-matrix inputs, both case requests and the packaged adapter/comparer, and
write manifest 3.0.0 beside generator.zip, reproduce.py and the retained,
authenticated one-call reference. No generation runs during freeze.

profile: run the ordinary packaged CLI once per case (240 s each) and the
release reproduce.py once (600 s), each in a child process watched for the
machine's memory floor, and write one receipt outside the release.

    python -I scripts/schedule_generator_case_matrix_release.py freeze --target DIR --version 0.8.0 \
        --resources-root DIR --reference FILE
    python -I scripts/schedule_generator_case_matrix_release.py profile --release DIR --receipt FILE [--python EXE]
"""
import argparse
import ctypes
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from atlas_schedules.canonical import canonical  # noqa: E402
from atlas_schedules.resources import manifest_identity, strict_json  # noqa: E402
from scripts import schedule_generator_case_matrix as adapter  # noqa: E402

INPUTS = ROOT/'tests/fixtures/schedule_generator_case_matrix'
INPUT_FILES = ('full-request.json.gz', 'resource-manifest.json.gz', 'r74-design-mapping.json.gz')
CODE = ('schedule_generator_case_matrix.py', 'schedule_generator_case_matrix_stream.py')
NEW_PRODUCERS = ('scripts/schedule_generator_case_matrix_release.py', 'scripts/schedule_generator_case_matrix_reproduction.py')
REFERENCE = {'size_bytes': 65467798, 'sha256': '62ccd3e3b6a11b2ad81d34b51c8157164f2d96365bd3efc24398e76eda0e583b',
             'decoded_size_bytes': 1092759826,
             'decoded_sha256': '06bfc6aa7d01d0cc76fd099616a7ac94ab2ba807220ff4653cea5ba5dfb6e33d',
             'producer_python_version': '3.11.9'}
CASE_TIMEOUT_SECONDS = 240
REPRODUCTION_TIMEOUT_SECONDS = 600
FLOOR_COMMIT = 1024 * 1024 * 1024
FLOOR_PHYSICAL = 1536 * 1024 * 1024

BOOTSTRAP_V3 = b'''"""Ordinary generation from layout3; reproduction needs the local release."""
import pathlib,runpy,stat,sys,tempfile,zipfile
if len(sys.argv)==2 and sys.argv[1]=="--reproduce":
    print("Release layout 3 reproduction requires manifest.json, reproduce.py and references/all-cases-bundle.json.gz. Run the release-level reproduce.py with --release-root and an outside --receipt path.",file=sys.stderr)
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

GUIDE = (
    '# Offline apartment method release, layout 3 (case matrix)\n\n'
    '313 of 1900 programme methods and 30 of 378 compositions. Unknown gas/additional loads and other '
    'source exclusions remain unresolved; this is not complete energy-definition coverage. '
    'Caller areas 80/120 m2 are synthetic realizations, never prototype dimensions.\n\n'
    'The original cumulative request (references/all-cases-request.json, 385 owners) is split into two '
    'exact cases, references/case-matrix/<case>.request.json. Generate each with Python 3.11+ offline: '
    'python -I -S generator.zip --request REQUEST --output BUNDLE. The one-call request is retained for '
    'provenance; its single-call 240 s ordinary bound is not claimed.\n\n'
    'Reproduction requires all four local files: manifest.json, generator.zip, reproduce.py and '
    'references/all-cases-bundle.json.gz. Run python -I -S reproduce.py --release-root RELEASE '
    '--receipt OUTSIDE_WORK/reproduction.json. It regenerates both cases, streams their original union in '
    'canonical byte order and requires byte equality with the reference; only rng.python_version is '
    'normalized when the interpreter differs from the reference producer.\n').encode()


def _digest(blob):
    return {'sha256': hashlib.sha256(blob).hexdigest(), 'size_bytes': len(blob)}


def _member(path, blob):
    return {'location': 'generator_zip_member', 'path': path, **_digest(blob)}


def authenticate_reference(path):
    """Stream-check the compressed and decoded identities; returns the compressed bytes."""
    blob = Path(path).read_bytes()
    if _digest(blob) != {'sha256': REFERENCE['sha256'], 'size_bytes': REFERENCE['size_bytes']}:
        raise ValueError('Reference compressed identity differs')
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS); digest = hashlib.sha256(); size = 0; data = blob
    while data:
        out = decoder.decompress(data, 1 << 24); digest.update(out); size += len(out)
        data = decoder.unconsumed_tail
        if decoder.eof and decoder.unused_data: raise ValueError('Bytes follow the single gzip member')
    if not decoder.eof or size != REFERENCE['decoded_size_bytes'] or digest.hexdigest() != REFERENCE['decoded_sha256']:
        raise ValueError('Reference decoded identity differs')
    return blob


def build_layout3_files(resources_root, inputs_dir=INPUTS):
    """All generator.zip members plus the manifest pieces that depend on them."""
    from scripts.schedule_generator_apartment_certification import (apartment_scope, assemble_apartment_members,
                                                                     validate_scope, validate_transport_inventory)
    scope = apartment_scope(); validate_scope(scope)
    inputs = {name: (Path(inputs_dir)/name).read_bytes() for name in INPUT_FILES}
    request, resource_manifest, mapping = (strict_json(gzip.decompress(inputs[n]), n) for n in INPUT_FILES)
    matrix = adapter.compile_case_matrix(request, resource_manifest, mapping)
    files = assemble_apartment_members(resources_root, scope)
    # Same runtime-manifest closure as the layout-2 apartment freeze.
    manifest = strict_json(files['atlas_schedules/data/manifest.json'], 'manifest')
    files['atlas_schedules/data/reference/m1-scope.json'] = canonical(scope)
    entry = next(e for e in manifest['resources'] if (e['kind'], e['key']) == ('reference', 'm1-scope'))
    entry.update(_digest(files['atlas_schedules/data/reference/m1-scope.json']))
    manifest.update(cases=scope['cases'], service_cases=scope['service_cases'], milestone_id='A1')
    manifest['resource_set_id'] = manifest_identity(manifest)
    files['atlas_schedules/data/manifest.json'] = canonical(manifest)
    if manifest['resource_set_id'] != mapping['resource_set_id']:
        raise ValueError('Packaged resource set differs from the admitted matrix: '+manifest['resource_set_id'])
    files['__main__.py'] = BOOTSTRAP_V3
    files['docs/schedule-generator.md'] = GUIDE
    files['references/all-cases-request.json'] = canonical(request)
    for case in mapping['cases']:
        files['references/case-matrix/'+case['case_id']+'.request.json'] = canonical(case['request'])
    for name, blob in inputs.items(): files['case_matrix/inputs/'+name] = blob
    for name in CODE: files['case_matrix/'+name] = (ROOT/'scripts'/name).read_bytes()
    for name in NEW_PRODUCERS: files['provenance/implementation/'+name] = (ROOT/name).read_bytes()
    validate_transport_inventory([{'path': n, 'size_bytes': len(b)} for n, b in files.items()])
    return files, scope, request, mapping, matrix


def layout3_manifest(version, files, scope, request, mapping, archive, runner, reference):
    producers = sorted(n[len('provenance/implementation/'):] for n in files if n.startswith('provenance/implementation/'))
    mapping_counts = {'constituents': len(mapping['full_constituent_order']), 'schedules': len(mapping['typed_slot_obligations'])}
    bindings = sum(len(s['demands']) + len(s['controls']) for s in mapping['typed_slot_obligations'])
    return {'schema_version': '3.0.0', 'release_version': version,
            'reference_layout': 'external_local_gzip_json_v1', 'bundle_schema_version': '1.2.0',
            'entrypoints': {'generation': {'kind': 'zip_request_output', 'path': 'generator.zip'},
                            'reproduction': {'kind': 'release_script', 'path': 'reproduce.py'}},
            'request': _member('references/all-cases-request.json', files['references/all-cases-request.json']),
            'reference': {'location': 'release_file', 'path': 'references/all-cases-bundle.json.gz', 'codec': 'gzip-json-v1',
                          **_digest(reference), 'decoded_sha256': REFERENCE['decoded_sha256'],
                          'decoded_size_bytes': REFERENCE['decoded_size_bytes'],
                          'producer_python_version': REFERENCE['producer_python_version']},
            'case_matrix': {'contract_version': '1.0.0', 'case_order': [c['case_id'] for c in mapping['cases']],
                            'cases': [{'case_id': c['case_id'], 'requested_owners': len(c['request']['params']['instances']),
                                       'request': _member('references/case-matrix/'+c['case_id']+'.request.json',
                                                          files['references/case-matrix/'+c['case_id']+'.request.json'])}
                                      for c in mapping['cases']],
                            'inputs': {n: _member('case_matrix/inputs/'+n, files['case_matrix/inputs/'+n]) for n in INPUT_FILES},
                            'code': {n: _member('case_matrix/'+n, files['case_matrix/'+n]) for n in CODE}},
            'scope': {'milestone_id': 'A1', 'scope_version': scope['scope_version'], 'case_count': len(scope['cases']),
                      'case_ids': [c['case_id'] for c in scope['cases']],
                      'sha256': hashlib.sha256(files['sources/schedule-generator-m1-scope.json']).hexdigest(),
                      'service_case_ids': [c['case_id'] for c in scope['service_cases']],
                      'service_case_count': len(scope['service_cases'])},
            'resource_set_id': strict_json(files['atlas_schedules/data/manifest.json'], 'manifest')['resource_set_id'],
            'source_manifest_sha256': hashlib.sha256(files['atlas_schedules/data/manifest.json']).hexdigest(),
            'commercial_audit_sha256': hashlib.sha256(files['data/schedule-generator/comstock-sampling-audit.json']).hexdigest(),
            'files': {'generator.zip': _digest(archive), 'reproduce.py': _digest(runner),
                      'references/all-cases-bundle.json.gz': _digest(reference)},
            'implementation_sources': {n: _member('provenance/implementation/'+n, files['provenance/implementation/'+n])
                                       for n in producers},
            'members': {k: _digest(v) for k, v in sorted(files.items())},
            'public_counts': {'requested_owners': len(request['params']['instances']), **mapping_counts, 'bindings': bindings}}


def freeze(target, version, resources_root, reference_path):
    """Write a new immutable layout-3 release, then verify it with the shipped verifier."""
    from scripts.schedule_generator_apartment_certification import load_resources, validate_transport_inventory
    from scripts.schedule_generator_case_matrix_reproduction import verify_v3_release
    from scripts.schedule_generator_release import _archive
    target = Path(target)
    if target.exists(): raise ValueError('Immutable release target already exists; choose a new version')
    load_resources(resources_root)  # authenticates every resource file against its manifest, as layout 2 does
    reference = authenticate_reference(reference_path)
    files, scope, request, mapping, _ = build_layout3_files(resources_root)
    archive = _archive(files); runner = (ROOT/'scripts/schedule_generator_case_matrix_reproduction.py').read_bytes()
    validate_transport_inventory([{'path': 'generator.zip', 'size_bytes': len(archive)},
                                  {'path': 'reproduce.py', 'size_bytes': len(runner)},
                                  {'path': 'references/all-cases-bundle.json.gz', 'size_bytes': len(reference)}])
    release = layout3_manifest(version, files, scope, request, mapping, archive, runner, reference)
    target.mkdir(parents=True); (target/'references').mkdir()
    (target/'generator.zip').write_bytes(archive); (target/'reproduce.py').write_bytes(runner)
    (target/'references/all-cases-bundle.json.gz').write_bytes(reference)
    (target/'manifest.json').write_bytes(canonical(release))
    verify_v3_release(target)
    return release


# ---------------------------------------------------------------- profiling

class _SystemMemory(ctypes.Structure):
    _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]


class _ProcessMemory(ctypes.Structure):
    _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong), ('PeakWorkingSetSize', ctypes.c_size_t),
                ('WorkingSetSize', ctypes.c_size_t), ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPagedPoolUsage', ctypes.c_size_t), ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                ('QuotaNonPagedPoolUsage', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t),
                ('PeakPagefileUsage', ctypes.c_size_t), ('PrivateUsage', ctypes.c_size_t)]


def _system_memory():
    if os.name != 'nt': return None
    kernel32 = ctypes.WinDLL('kernel32'); kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.c_void_p]
    status = _SystemMemory(); status.dwLength = ctypes.sizeof(status)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)): return None
    return {'available_physical_bytes': status.ullAvailPhys, 'available_commit_bytes': status.ullAvailPageFile}


def _child_memory(process):
    if os.name != 'nt': return None
    psapi = ctypes.WinDLL('psapi'); psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    counters = _ProcessMemory(); counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(ctypes.c_void_p(int(process._handle)), ctypes.byref(counters), counters.cb): return None
    return {'peak_working_set_bytes': counters.PeakWorkingSetSize, 'peak_commit_bytes': counters.PeakPagefileUsage}


def run_guarded(command, cwd, timeout):
    """Run one child; kill it at the timeout or the system memory floor. Never retried."""
    started = time.perf_counter(); utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        process = subprocess.Popen(command, cwd=cwd, stdout=out, stderr=err)
        stop = None; peak = None; minimum = None
        while process.poll() is None:
            elapsed = time.perf_counter()-started
            memory = _system_memory(); peak = _child_memory(process) or peak
            if memory is None: stop = 'MEMORY_SAMPLE_FAILED'
            else:
                minimum = memory if minimum is None else {k: min(minimum[k], memory[k]) for k in memory}
                if memory['available_commit_bytes'] < FLOOR_COMMIT or memory['available_physical_bytes'] < FLOOR_PHYSICAL:
                    stop = 'MEMORY_FLOOR_STOP'
            if elapsed > timeout: stop = 'TIMEOUT'
            if stop: process.kill(); process.wait(); break
            time.sleep(0.25)
        elapsed = time.perf_counter()-started
        peak = _child_memory(process) or peak  # final sample: the handle stays valid after exit
        if stop is None and elapsed > timeout: stop = 'TIMEOUT'
        out.seek(0); err.seek(0)
        return {'command': command, 'started_utc': utc, 'elapsed_seconds': round(elapsed, 3), 'timeout_seconds': timeout,
                'exit_code': process.returncode, 'stop': stop, 'passed': stop is None and process.returncode == 0,
                'child_peak_memory': peak, 'system_memory_minimum': minimum,
                'stdout_tail': out.read()[-4000:].decode('utf-8', 'replace'),
                'stderr_tail': err.read()[-4000:].decode('utf-8', 'replace')}


def profile(release, receipt, python=None):
    from scripts.schedule_generator_case_matrix_reproduction import verify_v3_release
    release = Path(release).resolve(); receipt = Path(receipt).resolve(); python = python or sys.executable
    if receipt.exists() or receipt.is_relative_to(release): raise ValueError('Receipt must be new and outside the release')
    verified = verify_v3_release(release); manifest = verified['manifest']
    for case in manifest['case_matrix']['cases']:
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', case['case_id']): raise ValueError('Unsafe case id: '+case['case_id'])
    probe = subprocess.run([python, '-I', '-S', '-c', 'import platform;print(platform.python_version())'],
                           capture_output=True, text=True, timeout=60)
    if probe.returncode: raise ValueError('Interpreter probe failed: '+probe.stderr[-500:])
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=30)
    report = {'schema_version': '1.1.0', 'release': str(release), 'release_version': manifest['release_version'],
              'python': python, 'python_version': probe.stdout.strip(), 'host_platform': platform.platform(),
              'input_identities': verified['input_identities'],
              'profiler': {'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           'git_head': head.stdout.strip() if head.returncode == 0 else None},
              'gates': {'case_seconds': CASE_TIMEOUT_SECONDS, 'reproduction_seconds': REPRODUCTION_TIMEOUT_SECONDS},
              'cases': {}, 'reproduction': None}
    def save():
        temporary = Path(str(receipt)+'.tmp'); temporary.write_text(json.dumps(report, indent=2), encoding='utf-8')
        os.replace(temporary, receipt)
    with tempfile.TemporaryDirectory(prefix='atlas-v3-profile-') as directory:
        work = Path(directory)
        import zipfile
        with zipfile.ZipFile(release/'generator.zip') as archive:
            for case in manifest['case_matrix']['cases']:
                (work/(case['case_id']+'.request.json')).write_bytes(archive.read(case['request']['path']))
        for case in manifest['case_matrix']['cases']:
            output = work/(case['case_id']+'.bundle.json')
            result = run_guarded([python, '-I', '-S', str(release/'generator.zip'), '--request',
                                  str(work/(case['case_id']+'.request.json')), '--output', str(output)], work, CASE_TIMEOUT_SECONDS)
            if result['passed'] and output.exists():
                digest = hashlib.sha256(); size = 0
                with output.open('rb') as stream:
                    while chunk := stream.read(1 << 20): digest.update(chunk); size += len(chunk)
                result['output'] = {'size_bytes': size, 'sha256': digest.hexdigest()}
                output.unlink()  # scratch output inside this run's own temporary directory
            report['cases'][case['case_id']] = result; save()
        result = run_guarded([python, '-I', '-S', str(release/'reproduce.py'), '--release-root', str(release),
                              '--receipt', str(work/'reproduction.json')], work, REPRODUCTION_TIMEOUT_SECONDS)
        if (work/'reproduction.json').exists():
            result['receipt'] = json.loads((work/'reproduction.json').read_text(encoding='utf-8'))
        report['reproduction'] = result
    report['passed'] = all(c['passed'] for c in report['cases'].values()) and report['reproduction']['passed']
    save()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0]); commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('freeze')
    build.add_argument('--target', type=Path, required=True); build.add_argument('--version', required=True)
    build.add_argument('--resources-root', type=Path, required=True); build.add_argument('--reference', type=Path, required=True)
    check = commands.add_parser('profile')
    check.add_argument('--release', type=Path, required=True); check.add_argument('--receipt', type=Path, required=True)
    check.add_argument('--python', default=None)
    args = parser.parse_args(argv)
    if args.command == 'freeze':
        release = freeze(args.target, args.version, args.resources_root, args.reference)
        print(json.dumps({'files': release['files'], 'public_counts': release['public_counts']}, indent=2)); return 0
    report = profile(args.release, args.receipt, args.python)
    print(json.dumps({'passed': report['passed'], 'cases': {k: (v['passed'], v['elapsed_seconds']) for k, v in report['cases'].items()},
                      'reproduction': (report['reproduction']['passed'], report['reproduction']['elapsed_seconds'])}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
