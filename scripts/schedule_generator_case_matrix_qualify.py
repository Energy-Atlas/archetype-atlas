"""One Route B (R145) A5 qualification run: generate both cases, stream the union, compare.

Usage (from the repository root):
    python -I scripts/schedule_generator_case_matrix_qualify.py --inputs DIR --resources DIR
        --reference FILE --receipt FILE

--inputs holds the three admitted production archives (full-request.json.gz,
resource-manifest.json.gz, r74-design-mapping.json.gz; the durable test
fixtures qualify). --resources is an extracted resource set whose identity the
mapping names. Only ResourceSet.load is redirected, exactly as the bounded
tests do; no strict predicate, seed or source qualification is patched.

A watchdog thread aborts the process (exit 3) before the machine runs out of
memory. That is a safety stop, never a retry signal: rerunning is a separate
decision. The receipt records phases, peak memory and the comparison result.
"""
import argparse
import ctypes
import datetime
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from atlas_schedules import generate  # noqa: E402
from atlas_schedules.resources import ResourceSet, strict_json  # noqa: E402
from scripts import schedule_generator_case_matrix as adapter  # noqa: E402
from scripts import schedule_generator_case_matrix_stream as comparer  # noqa: E402

REFERENCE = {'compressed': {'size_bytes': 65467798,
                            'sha256': '62ccd3e3b6a11b2ad81d34b51c8157164f2d96365bd3efc24398e76eda0e583b'},
             'decoded': {'size_bytes': 1092759826,
                         'sha256': '06bfc6aa7d01d0cc76fd099616a7ac94ab2ba807220ff4653cea5ba5dfb6e33d'}}
INPUT_FILES = ('full-request.json.gz', 'resource-manifest.json.gz', 'r74-design-mapping.json.gz')
FLOOR_PHYSICAL = 1536 * 1024 * 1024
FLOOR_COMMIT = 1024 * 1024 * 1024
CODE_FILES = ('scripts/schedule_generator_case_matrix.py', 'scripts/schedule_generator_case_matrix_stream.py',
              'scripts/schedule_generator_case_matrix_qualify.py')


class _ProcessMemory(ctypes.Structure):
    _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong),
                ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t),
                ('PrivateUsage', ctypes.c_size_t)]


class _SystemMemory(ctypes.Structure):
    _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]


if os.name == 'nt':
    _kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    _psapi = ctypes.WinDLL('psapi', use_last_error=True)
    _kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    _kernel32.GetCurrentProcess.argtypes = []
    _kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.c_void_p]
    _psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]


def process_memory():
    """Windows process counters; None means unknown, never zero."""
    if os.name != 'nt': return None
    counters = _ProcessMemory(); counters.cb = ctypes.sizeof(counters)
    if not _psapi.GetProcessMemoryInfo(_kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return None
    return {'working_set_bytes': counters.WorkingSetSize, 'peak_working_set_bytes': counters.PeakWorkingSetSize,
            'commit_bytes': counters.PrivateUsage, 'peak_commit_bytes': counters.PeakPagefileUsage}


def system_memory():
    if os.name != 'nt': return None
    status = _SystemMemory(); status.dwLength = ctypes.sizeof(status)
    if not _kernel32.GlobalMemoryStatusEx(ctypes.byref(status)): return None
    return {'available_physical_bytes': status.ullAvailPhys, 'available_commit_bytes': status.ullAvailPageFile,
            'total_physical_bytes': status.ullTotalPhys, 'commit_limit_bytes': status.ullTotalPageFile}


def write_json(path, value):
    """Write via a temporary sibling and os.replace, so a reader never sees half a receipt."""
    temporary = Path(str(path)+'.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    os.replace(temporary, path)


class Watchdog(threading.Thread):
    """Samples system memory; hard-exits (code 3) at the floor or if sampling fails.

    Fails closed: an unreadable sample stops the run, and the stop note is best
    effort, so a failed note write can never leave the process unguarded. A
    long C-level call holds the GIL and can delay one sample; the floors keep
    headroom for that.
    """

    def __init__(self, receipt_path, interval=0.25):
        super().__init__(daemon=True)
        self.receipt_path, self.interval = receipt_path, interval
        self.minimum = {'available_physical_bytes': None, 'available_commit_bytes': None}
        self.samples = 0; self.stop = threading.Event()

    def halt(self, reason, current):
        try:
            note = {'status': reason, 'utc': utc(), 'system': current, 'process': process_memory(),
                    'floors': {'physical_bytes': FLOOR_PHYSICAL, 'commit_bytes': FLOOR_COMMIT}}
            sys.stderr.write(reason+' '+json.dumps(note)+'\n'); sys.stderr.flush()
            write_json(Path(self.receipt_path).with_suffix('.memory-stop.json'), note)
        finally:
            os._exit(3)

    def run(self):
        while not self.stop.wait(self.interval):
            try:
                current = system_memory()
            except Exception:
                current = None
            if current is None: self.halt('MEMORY_SAMPLE_FAILED', None)
            self.samples += 1
            for key in self.minimum:
                if self.minimum[key] is None or current[key] < self.minimum[key]: self.minimum[key] = current[key]
            if current['available_physical_bytes'] < FLOOR_PHYSICAL or current['available_commit_bytes'] < FLOOR_COMMIT:
                self.halt('MEMORY_FLOOR_STOP', current)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def file_identity(path):
    blob = Path(path).read_bytes()
    return {'size_bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}


def code_identity():
    """Recorded, not pinned: every runtime module plus the three Route B scripts, and git state."""
    files = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'atlas_schedules').rglob('*.py')) + list(CODE_FILES)
    rows = [(name, file_identity(ROOT/name)['sha256']) for name in files]
    aggregate = hashlib.sha256('\n'.join(f'{sha}  {name}' for name, sha in rows).encode('utf-8')).hexdigest()
    git = {'head': None, 'dirty_paths': None}
    try:
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=30)
        status = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True, timeout=60)
        if head.returncode == 0 and status.returncode == 0:
            git = {'head': head.stdout.strip(), 'dirty_paths': [line[3:] for line in status.stdout.splitlines()]}
    except (OSError, subprocess.SubprocessError):
        pass  # unknown stays None, never an empty list
    return {'files': dict(rows), 'aggregate_sha256': aggregate, 'git': git,
            'note': 'Recorded for audit; no code pin is enforced by this runner.'}


def load_inputs(folder):
    values = []
    for name in INPUT_FILES:
        values.append(strict_json(gzip.decompress((Path(folder)/name).read_bytes()), name))
    return values


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--resources', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--reference-python-version', default=None,
                        help='Interpreter version recorded in the reference. When it differs from this '
                             'interpreter, only rng.python_version is normalized (comparison-policy.json '
                             'ignored_administrative_fields); all other bytes stay exact.')
    args = parser.parse_args(argv)
    receipt = {'schema_version': 'case-matrix-route-b-receipt-1.1.0', 'ruling': 'R145',
               'argv': sys.argv, 'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
               'started_utc': utc(), 'phases': [], 'status': 'INCOMPLETE',
               'system_memory_at_start': system_memory(), 'process_memory_at_start': process_memory()}
    if receipt['system_memory_at_start'] is None or receipt['process_memory_at_start'] is None:
        receipt['status'] = 'REFUSED_UNGUARDED'
        write_json(args.receipt, receipt)
        sys.stderr.write('Memory counters unavailable; refusing to run without the watchdog\n')
        return 2
    watchdog = Watchdog(args.receipt); watchdog.start()
    clock = time.perf_counter(); begin = clock

    def phase(name, **details):
        nonlocal clock
        now = time.perf_counter()
        receipt['phases'].append({'phase': name, 'seconds': round(now-clock, 3), 'utc': utc(),
                                  'process_memory': process_memory(), **details})
        clock = now
        write_json(args.receipt, receipt)

    try:
        receipt.update(code=code_identity(), inputs={name: file_identity(args.inputs/name) for name in INPUT_FILES})
        phase('record_identities')
        request, manifest, mapping = load_inputs(args.inputs)
        matrix = adapter.compile_case_matrix(request, manifest, mapping)
        phase('admit_and_compile_matrix')
        resources = ResourceSet(args.resources, mapping['resource_set_id'])
        phase('authenticate_resource_set', resource_set_id=resources.resource_set_id)
        def generated(case_id, bundle, seconds):
            gc.collect()
            phase('generate:'+case_id, owners=len(bundle['constituents']), schedules=len(bundle['schedules']),
                  generate_seconds=round(seconds, 3))
        # generate() validates each case it returns; the adapter does not repeat it (R145, R146).
        with patch('atlas_schedules.generator.ResourceSet.load', return_value=resources):
            pieces = adapter.generate_and_stream_union(matrix, generate, generated)
        phase('case_identities_and_union_checks')
        normalize = None
        if args.reference_python_version and args.reference_python_version != platform.python_version():
            normalize = comparer.runtime_version_normalizer(platform.python_version(), args.reference_python_version)
        receipt['normalization'] = None if normalize is None else {
            'field': 'rng.python_version', 'generated': platform.python_version(),
            'reference': args.reference_python_version,
            'authority': 'atlas_schedules/data/reference/comparison-policy.json ignored_administrative_fields'}
        result = comparer.compare_canonical_stream(pieces, args.reference, normalize=normalize, **REFERENCE)
        phase('stream_and_compare')
        receipt.update(status=result['status'], comparison=result)
    except BaseException as error:  # record, then re-raise: no retry or repair here
        receipt.update(status='ERROR', error={'type': type(error).__name__, 'message': str(error),
                                              'code': getattr(error, 'code', None), 'path': getattr(error, 'path', None)})
        raise
    finally:
        watchdog.stop.set()
        receipt.update(finished_utc=utc(), total_seconds=round(time.perf_counter()-begin, 3),
                       process_memory_at_end=process_memory(), watchdog_minimum=watchdog.minimum,
                       watchdog_samples=watchdog.samples)
        write_json(args.receipt, receipt)
    return 0 if receipt['status'] == 'MATCH' else 1


if __name__ == '__main__':
    raise SystemExit(main())
