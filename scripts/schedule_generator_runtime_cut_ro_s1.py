"""Build-only Retail/Office S1 authority transition check, never qualification.

S1 (Stripmall People groups and local water carrier) changed two pinned
commercial runtime files and rebased the R70 checker onto its retained lock.
This verifies exactly that delta: the retained predecessor lock, the retained
pre-edit copies, the changed and added current rows, unchanged everything else,
and the activated evidence. It confers no authority on any later edit.
"""
import hashlib
import json
from pathlib import Path

from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import safe_path
from scripts.common import ROOT

BASE = 'data/schedule-generator/apartment/'
LOCK = 'sources/schedule-generator-apartment-authority-lock.json'
THEN_LOCK = BASE+'evidence/ro-s1-current-then/authority-lock.json'
THEN_ANCHOR = {'source_path': THEN_LOCK, 'sha256': '083390097f463e22c9c184f1f111594b49b3b3c3c285a27dd21a179928495b26',
               'size_bytes': 31916}
CHANGED = ('atlas_schedules/commercial/parametric.py', 'atlas_schedules/commercial/source_models.py',
           'scripts/schedule_generator_runtime_cut.py', 'tests/test_schedule_generator_runtime_cut.py')
ADDED = ('scripts/schedule_generator_runtime_cut_ro_s1.py', 'tests/test_schedule_generator_runtime_cut_ro_s1.py')
# Exact S1 end state of the changed files: any later edit needs its own transition.
S1_END = {
    'atlas_schedules/commercial/parametric.py': {'source_path': 'atlas_schedules/commercial/parametric.py', 'sha256': 'c6fdd1fa594680c1d2af8598d8505010922d874e05800a2b153d5cc63bcff88f', 'size_bytes': 37785},
    'atlas_schedules/commercial/source_models.py': {'source_path': 'atlas_schedules/commercial/source_models.py', 'sha256': 'd1566c853a9b680d5214fcfd48dd4ed877f8ce56c62e7ccbda745a22342a9f3e', 'size_bytes': 20290},
    'scripts/schedule_generator_runtime_cut.py': {'source_path': 'scripts/schedule_generator_runtime_cut.py', 'sha256': 'c74192b9af5f1510fd9e1bf764321c7698f1a165ec1edffb4fc09b7c63d7c6e6', 'size_bytes': 14181},
    'tests/test_schedule_generator_runtime_cut.py': {'source_path': 'tests/test_schedule_generator_runtime_cut.py', 'sha256': 'bb5465cff35ee2e9ae7513e079dbcbc2fe5a0b8e9e369bd0f22a5fb11a4e5a08', 'size_bytes': 8032},
}
TRANSITION = BASE+'evidence/ro-s1/transition.json'
COVERING = BASE+'evidence/ro-s1/covering-results.json'
RETAINED = {p: BASE+'qualification-code/ro-s1-current-then/'+p for p in CHANGED}
# R70-era bytes of a live document R70 resolved and v0.8.0 later edited; retained
# from Git (496b47b) so the R70 checker keeps verifying its historical edge.
RELOCATED = {'source_path': BASE+'qualification-code/ro-s1-current-then/docs/schedule-generator.md',
             'sha256': '18d216be49f2da14eb718985188560b4a7d6be94ce82e86071027c587914238c', 'size_bytes': 9296}


def _fail(path, message): raise GeneratorError('source_integrity', path, message)


def _read(root, path): return json.loads((Path(root)/str(safe_path(path))).read_bytes())


def _identity(root, path):
    blob = (Path(root)/str(safe_path(path))).read_bytes()
    return {'source_path': path, 'sha256': hashlib.sha256(blob).hexdigest(), 'size_bytes': len(blob)}


def _check(root, row, path=None):
    actual = _identity(root, path or row['source_path'])
    if (actual['sha256'], actual['size_bytes']) != (row['sha256'], row['size_bytes']):
        _fail(path or row['source_path'], 'Exact retained or current bytes differ')


def _rows(rows):
    result = {}
    for row in rows:
        if set(row) != {'source_path', 'sha256', 'size_bytes'} or row['source_path'] in result:
            _fail('/rows', 'Exact unique identity rows required')
        result[row['source_path']] = row
    return result


def expected_transition(root=ROOT, lock=None):
    """The exact transition record implied by the retained predecessor and the current files."""
    then = _read(root, THEN_LOCK)
    then_rows = _rows([then['current_producer'], *then['current_dependencies']])
    return {'schema_version': '1.0.0', 'predecessor': dict(THEN_ANCHOR),
            'changed': [{'original': then_rows[p], 'current': _identity(root, p), 'historical_path': RETAINED[p]} for p in CHANGED],
            'added': [_identity(root, p) for p in ADDED],
            'relocated': dict(RELOCATED),
            'interpretation': 'Retail/Office S1: Stripmall ordered People Ruleset groups and local first-registration water carrier '
                              'in commercial source_models/parametric; R70 checker rebased onto its retained lock and retained R70-era '
                              'bytes of later-moved live edges. All other pinned '
                              'code, evidence and historical authority unchanged.'}


def verify_ro_s1_transition(root=ROOT, lock=None, transition=None):
    root = Path(root)
    _check(root, THEN_ANCHOR)
    then = _read(root, THEN_LOCK); current = _read(root, LOCK) if lock is None else lock
    if set(current) != set(then): _fail('/authority', 'Lock top-level fields changed')
    record = _read(root, TRANSITION) if transition is None else transition
    if record != expected_transition(root):
        _fail('/transition', 'Transition record differs from the retained predecessor and current files')
    then_rows = _rows([then['current_producer'], *then['current_dependencies']])
    current_rows = _rows([current['current_producer'], *current['current_dependencies']])
    if set(current_rows) != set(then_rows) | set(ADDED): _fail('/current', 'Missing or foreign current code path')
    if current['current_producer'] != then['current_producer']: _fail('/producer', 'Pinned producer changed')
    for path, row in current_rows.items():
        _check(root, row)
        if path in then_rows and path not in CHANGED and row != then_rows[path]: _fail(path, 'Unapproved current dependency change')
        if path in CHANGED and row == then_rows[path]: _fail(path, 'Stale approved delta')
        if path in CHANGED and row != S1_END[path]: _fail(path, 'Changed after S1 without its own transition')
    for path in CHANGED: _check(root, then_rows[path], RETAINED[path])
    _check(root, RELOCATED)
    new_evidence = [THEN_LOCK, *RETAINED.values(), RELOCATED['source_path'], TRANSITION, COVERING]
    then_evidence = _rows(then['verification_evidence']); activated = _rows(current['verification_evidence'])
    if set(activated) != set(then_evidence) | set(new_evidence): _fail('/evidence', 'Missing or foreign activated evidence')
    for path, row in then_evidence.items():
        if activated[path] != row: _fail(path, 'Earlier evidence rebound')
    for path in new_evidence: _check(root, activated[path])
    for field in ('historical_fixed_lock', 'historical_dependency_relocations', 'timing_evidence', 'schema_version'):
        if current[field] != then[field]: _fail('/authority/'+field, 'Original scientific/historical authority changed')
    return {'schema_version': '1.0.0', 'passed': True, 'changed': list(CHANGED), 'added': list(ADDED),
            'current_code_count': len(current_rows),
            'scope': 'Retail/Office S1 bounded transition integrity only; no source/native/runtime release qualification'}


if __name__ == '__main__': print(json.dumps(verify_ro_s1_transition(), sort_keys=True))
