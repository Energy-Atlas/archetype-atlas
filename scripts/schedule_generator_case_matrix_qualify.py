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
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
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


def process_memory():
    """Windows process counters; None elsewhere (unknown, never zero)."""
    if os.name != 'nt': return None
    counters = _ProcessMemory(); counters.cb = ctypes.sizeof(counters)
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),
                                                  ctypes.byref(counters), counters.cb)
    if not ok: return None
    return {'working_set_bytes': counters.WorkingSetSize, 'peak_working_set_bytes': counters.PeakWorkingSetSize,
            'commit_bytes': counters.PrivateUsage, 'peak_commit_bytes': counters.PeakPagefileUsage}


def system_memory():
    if os.name != 'nt': return None
    status = _SystemMemory(); status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)): return None
    return {'available_physical_bytes': status.ullAvailPhys, 'available_commit_bytes': status.ullAvailPageFile,
            'total_physical_bytes': status.ullTotalPhys, 'commit_limit_bytes': status.ullTotalPageFile}


class Watchdog(threading.Thread):
    """Samples memory; hard-exits before the system floor is crossed."""

    def __init__(self, receipt_path, interval=0.25):
        super().__init__(daemon=True)
        self.receipt_path, self.interval = receipt_path, interval
        self.minimum = {'available_physical_bytes': None, 'available_commit_bytes': None}
        self.samples = 0; self.stop = threading.Event()

    def run(self):
        while not self.stop.wait(self.interval):
            current = system_memory()
            if current is None: return
            self.samples += 1
            for key in self.minimum:
                if self.minimum[key] is None or current[key] < self.minimum[key]: self.minimum[key] = current[key]
            if current['available_physical_bytes'] < FLOOR_PHYSICAL or current['available_commit_bytes'] < FLOOR_COMMIT:
                note = {'status': 'MEMORY_FLOOR_STOP', 'utc': utc(), 'system': current, 'process': process_memory(),
                        'floors': {'physical_bytes': FLOOR_PHYSICAL, 'commit_bytes': FLOOR_COMMIT}}
                Path(self.receipt_path).with_suffix('.memory-stop.json').write_text(json.dumps(note, indent=2), encoding='utf-8')
                sys.stderr.write('MEMORY_FLOOR_STOP '+json.dumps(note)+'\n'); sys.stderr.flush()
                os._exit(3)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def file_identity(path):
    blob = Path(path).read_bytes()
    return {'size_bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}


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
    args = parser.parse_args(argv)
    receipt = {'schema_version': 'case-matrix-route-b-receipt-1.0.0', 'ruling': 'R145',
               'argv': sys.argv, 'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
               'started_utc': utc(), 'phases': [], 'status': 'INCOMPLETE',
               'code': {name: file_identity(ROOT/name) for name in CODE_FILES},
               'inputs': {name: file_identity(args.inputs/name) for name in INPUT_FILES},
               'system_memory_at_start': system_memory()}
    watchdog = Watchdog(args.receipt); watchdog.start()
    clock = time.perf_counter(); begin = clock

    def phase(name, **details):
        nonlocal clock
        now = time.perf_counter()
        receipt['phases'].append({'phase': name, 'seconds': round(now-clock, 3), 'utc': utc(),
                                  'process_memory': process_memory(), **details})
        clock = now
        args.receipt.write_text(json.dumps(receipt, indent=2), encoding='utf-8')

    try:
        request, manifest, mapping = load_inputs(args.inputs)
        matrix = adapter.compile_case_matrix(request, manifest, mapping)
        phase('admit_and_compile_matrix')
        resources = ResourceSet(args.resources, mapping['resource_set_id'])
        phase('authenticate_resource_set', resource_set_id=resources.resource_set_id)
        cases = {}
        with patch('atlas_schedules.generator.ResourceSet.load', return_value=resources):
            for case in mapping['cases']:
                case_request = case['request']
                cases[case['case_id']] = generate(case_request['params'], case_request['seed'])
                phase('generate:'+case['case_id'], owners=len(cases[case['case_id']]['constituents']),
                      schedules=len(cases[case['case_id']]['schedules']))
        pieces = adapter.stream_original_union(cases, matrix)
        phase('admit_cases_and_union_checks')
        result = comparer.compare_canonical_stream(pieces, args.reference, **REFERENCE)
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
        args.receipt.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return 0 if receipt['status'] == 'MATCH' else 1


if __name__ == '__main__':
    raise SystemExit(main())
