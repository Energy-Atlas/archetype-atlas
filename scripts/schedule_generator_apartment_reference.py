"""Build-only actual apartment fixed/getter proofs; production routing stays closed.

The native experiment combines c8 constructors/data with the distinct 0.8.6
getter at OpenStudio 3.10. It establishes no full-prototype or timing parity.
"""
import argparse
import copy
from datetime import date, timedelta
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import tarfile
import time

from atlas_schedules.calendar import evaluate_rules
from atlas_schedules.caller_unit_water import compile_requirement
from atlas_schedules.canonical import canonical
from atlas_schedules.companions import _native_constant
from atlas_schedules.comparison import _close
from atlas_schedules.commercial.parametric import _hourly, _stored
from atlas_schedules.errors import GeneratorError
from atlas_schedules.physical_sets import _source, _typed
from atlas_schedules.resources import safe_path, strict_json
from scripts.common import ROOT
from scripts.schedule_generator_apartments import (
    CALENDAR, ORDERED_PROGRAMME_IDS_SHA256, _water_evidence,
    compile_apartment_sources,
)
from scripts.runtime import extract_verified


BASE = 'data/schedule-generator/apartment/'
LOCK = 'sources/schedule-generator-apartment-fixed-reference-lock.json'
REVISION = 'c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907'
SOURCE_METHOD = 'create_water_use.rb:39-62; Standards0.8.6 information.rb:338-382'
SOURCE_MEMBERS = (
    ('standards/standard.rb', 'df744cee34d40d50fd80f485da6b6171741adbbda1806fb0a56816b03284305a'),
    ('standards/Standards.Model.rb', 'c88dada83a0e1a25db534917912766dcb2c451da8a0402befff1a16b3497f145'),
    ('standards/Standards.ServiceWaterHeating.rb', '50f6c89f3e1371b198d33eb5acd6b25b81c0c4319fa261efc067ea511f6b1156'),
    ('service_water_heating/create_water_use.rb', '6c506aeecc764d019ccc2d2bb1524560ab8130605b790f41bc9506f843d14e18'),
    ('schedules/create.rb', '11c2a369ec2f4c566a9119e34ddd2e32260f41ebe3ab9273b137fea60342b7e0'),
)
GETTER = ('schedules/information.rb', '35497de539ee674ab234f4efbf0eab7ad7cfdc36ad21c8e5a0e41bfc141bdc30')
RAW_SCHEDULES = 'data/raw/openstudio-standards/lib/openstudio-standards/standards/ashrae_90_1/data/ashrae_90_1.schedules.json'
RAW_SCHEDULES_SHA = '51240ccea12e2c626017c937c05ace3cd3e5085b60279d78522d29ac58d7719b'
CONTROL_SLOTS = (('water_target_temperature', 'target_temperature'),
                 ('water_sensible_fraction', 'sensible_fraction'),
                 ('water_latent_fraction', 'latent_fraction'))


def _fail(path, message):
    raise GeneratorError('source_integrity', path, message)


def _keys(value, names, path):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail(path, 'Missing or unknown actual-native proof fields')


def _native_shapes(native):
    """Strict actual-capture boundary; no optional/foreign receipt fields."""
    _keys(native, ('schema_version', 'input_sha256', 'source_members', 'reference_calendar',
        'model_version', 'legacy_round5', 'steps_per_hour', 'ruby_description', 'schedules', 'water_paths'), '/native')
    if not isinstance(native['schedules'], list) or not isinstance(native['water_paths'], list):
        _fail('/native', 'Ordered native schedule/path arrays required')
    receipt_fields = ('profiles', 'rule_order', 'day_rule_indices', 'special_profiles', 'values')
    def receipt(value, path):
        for key in ('values', 'day_rule_indices', 'rule_order'):
            if not isinstance(value[key], list): _fail(path + '/' + key, 'Native array required')
        if (len(value['values']) != 8760 or any(type(v) not in (int, float) or not math.isfinite(v) for v in value['values']) or
                len(value['day_rule_indices']) != 365 or any(type(v) is not int for v in value['day_rule_indices'])):
            _fail(path, 'Exact finite8760 getter and integer365 rule decisions required')
        if not isinstance(value['profiles'], dict): _fail(path + '/profiles', 'Native profile map required')
        _keys(value['special_profiles'], ('WntrDsn', 'SmrDsn'), path + '/special_profiles')
    for i, schedule in enumerate(native['schedules']):
        path = '/native/schedules/' + str(i)
        _keys(schedule, (*receipt_fields, 'id', 'source_rows', 'programme_ids', 'construction_kind',
            'overlay_provenance', 'original_explicit_special_day_selectors'), path)
        receipt(schedule, path)
    for i, water in enumerate(native['water_paths']):
        path = '/native/water_paths/' + str(i)
        _keys(water, ('path_id', 'service', 'row', 'schedule_id', 'programme_ids',
                     'requirement_ids', 'helper_sources', 'probes'), path)
        if not isinstance(water['probes'], list): _fail(path + '/probes', 'Native area probes required')
        for j, probe in enumerate(water['probes']):
            pp = path + '/probes/' + str(j)
            _keys(probe, ('floor_area_m2', 'space_multiplier', 'is_flow_per_area', 'lookup_building_type',
                'lookup_criteria', 'source_density_gal_h_ft2', 'native_area_ft2', 'source_temperature_F',
                'native_temperature_operand_C', 'source_system_type', 'native_peak_flow_m3_s',
                'flow_schedule_name', 'flow_values', 'attached_space', 'controls'), pp)
            _keys(probe['controls'], ('target_temperature', 'sensible_fraction', 'latent_fraction'), pp + '/controls')
            if any(type(probe[k]) not in (int, float) for k in ('floor_area_m2', 'space_multiplier')):
                _fail(pp, 'Numeric controlled area/multiplier required; booleans rejected')
            for name, control in probe['controls'].items():
                cp = pp + '/controls/' + name
                _keys(control, receipt_fields, cp); receipt(control, cp)
                _keys(control['profiles'], ('default',), cp + '/profiles')
                points = control['profiles']['default']
                if (not isinstance(points, list) or len(points) != 1 or
                        not isinstance(points[0], list) or len(points[0]) != 2 or
                        any(type(v) not in (int, float) or not math.isfinite(v) for v in points[0])):
                    _fail(cp + '/profiles/default', 'Complete finite native constant point required')


def _same(left, right):
    return canonical(left) == canonical(right)


def _read(path):
    return strict_json(Path(path).read_bytes(), str(path))


def _digest(blob):
    return hashlib.sha256(blob).hexdigest()


def _bytes(path, sha):
    path = Path(path)
    if not path.is_file() or _digest(path.read_bytes()) != sha:
        _fail(str(path), 'Missing or changed locked bytes')
    return path.read_bytes()


def _pointer(value, locator):
    if locator == '/':
        return value
    for token in locator[1:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def _original(obj, cache):
    _source(obj, '/original')
    path = obj['path']
    if path not in cache:
        blob = _bytes(ROOT / str(safe_path(path)), obj['sha256'])
        cache[path] = (obj['sha256'], blob.decode('utf-8') if path.endswith('.rb') else strict_json(blob, path))
    sha, whole = cache[path]
    try:
        valid = sha == obj['sha256'] and _same(_pointer(whole, obj['locator']), obj['value'])
    except (KeyError, IndexError, ValueError, TypeError):
        valid = False
    if not valid:
        _fail(path + '#' + obj['locator'], 'Complete independently located original differs')


def apartment_fixed_capture_inputs(scope: dict, sources: dict) -> dict:
    """Ordered original 90 Rulesets, 20 per-area paths and their 40 views."""
    locked_scope = _read(ROOT / 'sources/schedule-generator-apartment-scope.json')
    if not _same(scope, locked_scope) or _digest(canonical([p['id'] for p in scope['programmes']])) != ORDERED_PROGRAMME_IDS_SHA256:
        _fail('/scope', 'Exact reviewed ordered candidate scope required')
    if set(sources) != {'programmes', 'requirements', 'source_objects', 'locations'}:
        _fail('/sources', 'Exact reviewed A2 source result required')
    originals = {}; schedules = sources['source_objects']['schedules']
    programmes = sources['programmes']; requirements = sources['requirements']
    if (list(programmes) != [p['id'] for p in scope['programmes']] or
            len(schedules) != 90 or len(requirements) != 40 or
            len(sources['source_objects']['services']) != 20):
        _fail('/sources', 'Complete 84/90/40/20 inventory required')
    for obj in programmes.values(): _original(obj, originals)
    for obj in sources['source_objects']['water_helpers']: _original(obj, originals)
    raw = strict_json(_bytes(ROOT / RAW_SCHEDULES, RAW_SCHEDULES_SHA), RAW_SCHEDULES)['schedules']
    scheduled = []
    for sid, obj in schedules.items():
        _original(obj, originals); value = obj['value']
        rows = []; overlay_evidence = []
        overlay = value['source_name'].startswith('resolution-')
        if overlay:
            if (value.get('calendar_independent') is not True or len(value['rules']) != 1 or
                    value['rules'][0] != {'day_types': 'Default', 'end_date': '2000-12-31',
                        'source_index': 0, 'start_date': '2000-01-01', 'values': [0]} or
                    not value.get('evidence_ids')):
                _fail('/schedules/' + sid, 'Exact reviewed zero overlay rule/provenance required')
            for eid in value['evidence_ids']:
                evidence = sources['source_objects']['field_evidence'][eid]
                _original(evidence, originals)
                if (evidence['value']['source_file_id'] is not None or
                        evidence['value']['transformation'] != 'explicit frozen reviewed overlay' or
                        evidence['value']['original_value'] != {'calendar_independent': True, 'constant_value': 0}):
                    _fail('/schedules/' + sid, 'Reviewed overlay cannot claim upstream source association')
                overlay_evidence.append(copy.deepcopy(evidence))
        for rule in ([] if overlay else value['rules']):
            index = rule['source_index']; row = raw[index]
            expected = {'day_types': row['day_types'], 'end_date': row['end_date'],
                        'source_category': row['category'], 'source_index': index,
                        'source_units': row['units'], 'start_date': row['start_date'],
                        'type': row['type'], 'values': row['values']}
            if not _same(expected, rule) or row['name'] != value['source_name']:
                _fail('/schedules/' + sid, 'Original entire ordered schedule rows differ')
            rows.append({'path': RAW_SCHEDULES, 'sha256': RAW_SCHEDULES_SHA,
                         'locator': '/schedules/' + str(index), 'value': copy.deepcopy(row)})
        all_indices = [i for i, row in enumerate(raw) if row['name'] == value['source_name']]
        if not overlay and all_indices != [r['source_index'] for r in value['rules']]:
            _fail('/schedules/' + sid, 'Whole original name/row order required')
        pids = [pid for pid, p in programmes.items() if sid in (
            [x['schedule_id'] for x in p['value']['loads']] +
            [v['value'] for k, v in p['value']['parameters'].items() if k.endswith('_schedule_id') and v['status'] == 'known'])]
        scheduled.append({'id': sid, 'source': copy.deepcopy(obj), 'rows': rows, 'programme_ids': pids,
            'construction_kind': ('reviewed_zero_overlay_native_representation' if overlay else 'original_c8_named_ruleset'),
            'overlay_provenance': overlay_evidence,
            'original_explicit_special_day_selectors': [key for key in ('WntrDsn', 'SmrDsn')
                if any(key in r['day_types'].split('|') for r in value['rules'])]})
    if sum(s['construction_kind'] == 'reviewed_zero_overlay_native_representation' for s in scheduled) != 44:
        _fail('/schedules', 'Exact 46 original and 44 reviewed-zero native representations required')
    paths = {}
    for pid, req in requirements.items():
        _typed(req, 'caller_requirement', '/requirements/' + pid)
        service = req['service_definition']; row = sources['source_objects']['raw_rows'][pid]
        for obj in (service, row, req['programme'], req['original_demand'], req['source_ruleset']):
            _original(obj, originals)
        if req['programme'] != programmes[pid] or req['source_ruleset'] != schedules[req['source_ruleset']['value']['id']]:
            _fail('/requirements/' + pid, 'Original programme/view/Ruleset join differs')
        proof = _water_evidence(programmes[pid], service, req['source_ruleset'], row,
                                sources['source_objects']['water_helpers'])
        # Whole original byte/locator checks above share only this call's local
        # decoded-file cache. The unchanged strict Core4 compiler still runs
        # independently for every per-ID original requirement.
        compiled = compile_requirement(programmes[pid], service, req['source_ruleset'], proof)
        if not _same(compiled, req):
            _fail('/requirements/' + pid, 'Whole independently compiled requirement differs')
        key = service['value']['path_id']
        if key not in paths:
            paths[key] = {'path_id': key, 'service': copy.deepcopy(service),
                          'row': copy.deepcopy(row), 'schedule_id': req['source_ruleset']['value']['id'],
                          'programme_ids': [], 'requirement_ids': [],
                          'helper_sources': copy.deepcopy(sources['source_objects']['water_helpers'])}
        path = paths[key]
        if not _same(path['service'], service) or not _same(path['row'], row):
            _fail('/water_paths/' + key, 'Alternative view changes whole original water authority')
        path['programme_ids'].append(pid); path['requirement_ids'].append(req['requirement_id'])
    if len(paths) != 20 or any(len(p['programme_ids']) != 2 for p in paths.values()):
        _fail('/water_paths', '20 original paths, each with two exact alternative views required')
    members = [{'source_path': BASE + 'capture-sources/' + name, 'sha256': sha,
                'original_path': 'lib/openstudio-standards/' + name, 'source_revision': REVISION,
                'size_bytes': (ROOT / BASE / 'capture-sources' / name).stat().st_size,
                'source_url': 'https://raw.githubusercontent.com/NatLabRockies/openstudio-standards/' + REVISION + '/lib/openstudio-standards/' + name}
               for name, sha in SOURCE_MEMBERS]
    members.append({'source_path': BASE + 'capture-sources/' + GETTER[0], 'sha256': GETTER[1],
                    'original_path': 'lib/openstudio-standards/' + GETTER[0], 'source_revision': '0.8.6',
                    'size_bytes': (ROOT / BASE / 'capture-sources' / GETTER[0]).stat().st_size,
                    'source_archive_sha256': '9a3477cdb6aac7501430a214cc1be5fc93c28b8ddd444e39579d442931e3a19f'})
    return {'schema_version': '1.0.0', 'reference_calendar': copy.deepcopy(CALENDAR),
            'steps_per_hour': 6, 'synthetic_floor_areas_m2': [80.0, 120.0], 'space_multiplier': 1,
            'construction_revision': REVISION, 'getter_revision': '0.8.6',
            'source_members': members, 'schedules': scheduled, 'water_paths': list(paths.values()),
            'prior_complete_apartment_proof_index': {
                'fixed_rulesets': [{'schedule_id': s['id'], 'construction_kind': s['construction_kind'],
                    'matching_complete_prior_capture': None} for s in scheduled],
                'water_paths': [{'path_id': p, 'matching_complete_prior_capture': None} for p in paths],
                'interpretation': '0/90 and 0/20 complete reusable apartment associations; C5 numeric precedent only'}}


def _member(entry):
    path = ROOT / str(safe_path(entry['source_path']))
    blob = _bytes(path, entry['sha256'])
    if len(blob) != entry['size_bytes']:
        _fail(str(path), 'Locked compressed member size differs')
    payload = gzip.decompress(blob)
    if len(payload) != entry['payload_size_bytes'] or _digest(payload) != entry['payload_sha256']:
        _fail(str(path), 'Locked actual capture payload differs')
    return strict_json(payload, str(path))


def load_apartment_fixed_reference(lock: dict | None = None) -> dict:
    """Verify retained actual input/output bytes and exact source identities offline."""
    historical_path = BASE + 'evidence/a3-reviewed-lock.json'
    historical_blob = _bytes(ROOT / historical_path,
        '6165bfbfbec59caa59d09e2c754c3d7a7e29e305f7053331165cc32c5bd51f87')
    authoritative = json.loads(historical_blob)
    if not _same(_read(ROOT / LOCK), authoritative):
        _fail('/lock', 'Original reviewed historical lock changed')
    if lock is not None and not _same(lock, authoritative):
        _fail('/lock', 'Supplied reference lock differs from independently retained lock')
    lock = authoritative
    if lock['qualification_boundary'] != 'fixed_getter_water_associations_only_runtime_closed':
        _fail('/lock', 'Unexpected method boundary')
    for entry in lock['capture_provenance']['source_members']:
        _bytes(ROOT / str(safe_path(entry['source_path'])), entry['sha256'])
    for entry in (lock['harness'], lock['builder']):
        _bytes(ROOT / entry['source_path'], entry['sha256'])
    retention = _read(ROOT / (BASE + 'evidence/authority-retention.json'))
    entries = [lock['qualification_builder'], *lock['qualification_dependencies']]
    expected = [{'original_path': e['source_path'],
        'retained_path': BASE+'qualification-code/a3/'+e['source_path'],
        'sha256': e['sha256'], 'size_bytes': e['size_bytes']} for e in entries]
    if not _same(retention['historical_dependency_relocations'], expected):
        _fail('/historical_dependencies', 'Exact complete historical relocation table differs')
    for entry in expected:
        blob = _bytes(ROOT / str(safe_path(entry['retained_path'])), entry['sha256'])
        if len(blob) != entry['size_bytes']:
            _fail('/historical_dependencies', 'Retained historical source size differs')
    for entry in [lock['capture_provenance']['source_origins'],
                  *lock['capture_provenance']['upstream_notices'],
                  *lock['evidence_files'], lock['qualification_manifest']]:
        _bytes(ROOT / str(safe_path(entry['source_path'])), entry['sha256'])
    inputs, native = _member(lock['inputs']), _member(lock['vectors'])
    if (not _same(inputs['source_members'], lock['capture_provenance']['source_members']) or
            native['input_sha256'] != lock['inputs']['payload_sha256'] or
            not _same(native['source_members'], inputs['source_members'])):
        _fail('/capture', 'Actual capture input/source association differs')
    return {'lock': lock, 'inputs': inputs, 'native': native}


def _pack(payload, path):
    blob = gzip.compress(payload, mtime=0)
    return blob, {'source_path': path, 'sha256': _digest(blob), 'size_bytes': len(blob),
                  'payload_sha256': _digest(payload), 'payload_size_bytes': len(payload),
                  'format': 'gzip JSON actual native capture'}


def capture_apartment_fixed(runtime_archive: Path, standards_archive: Path,
                            destination: Path, inputs: dict) -> dict:
    """Opt-in bounded native development experiment; never called by unit tests."""
    destination = Path(destination)
    if destination.exists(): _fail(str(destination), 'Capture destination must be new')
    runtime = _read(ROOT / 'sources/runtime-lock.json')['archives'][0]
    gem = next(a for a in _read(ROOT / 'sources/schedule-generator-lock.json')['archives'] if a['format'] == 'gem')
    _bytes(runtime_archive, runtime['sha256']); gem_bytes = _bytes(standards_archive, gem['sha256'])
    for member in inputs['source_members']:
        _bytes(ROOT / member['source_path'], member['sha256'])
    with tarfile.open(fileobj=io.BytesIO(gem_bytes)) as outer:
        with tarfile.open(fileobj=io.BytesIO(outer.extractfile('data.tar.gz').read())) as archive:
            if _digest(archive.extractfile('lib/openstudio-standards/' + GETTER[0]).read()) != GETTER[1]:
                _fail('/getter', 'Actual selected getter gem member differs')
    destination.mkdir(parents=True)
    selected = [runtime['root'] + '/' + p for p in ('bin/', 'Ruby/', 'lib/', 'LICENSE.md', 'copyright.txt')]
    extracted = extract_verified(runtime_archive, runtime['sha256'], destination / 'runtime', include=selected)
    executable = extracted / runtime['root'] / 'bin/openstudio.exe'
    source = destination / 'source'
    for member in inputs['source_members']:
        relative = member['original_path'].removeprefix('lib/openstudio-standards/')
        target = source / relative; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_bytes(ROOT / member['source_path'], member['sha256']))
    input_path = destination / 'input.json'; input_path.write_bytes(canonical(inputs))
    harness = ROOT / 'scripts/reference_apartment_fixed.rb'
    copied_harness = destination / harness.name; copied_harness.write_bytes(harness.read_bytes())
    watched = [p for p in (destination / 'runtime').rglob('*') if p.is_file()]
    watched += [p for p in source.rglob('*') if p.is_file()] + [input_path, copied_harness]
    manifest = lambda: [{'path': p.relative_to(destination).as_posix(), 'sha256': _digest(p.read_bytes()),
                         'size_bytes': p.stat().st_size} for p in sorted(watched)]
    before = manifest(); (destination / 'source-runtime-before.json').write_bytes(canonical(before))
    started = time.monotonic()
    completed = subprocess.run([str(executable.resolve()), str(copied_harness.resolve()),
        str(source.resolve()), str(input_path.resolve()), str((destination / 'native-output.json').resolve())],
        cwd=destination, capture_output=True, text=True, env=dict(os.environ, TZ='UTC'))
    elapsed = time.monotonic() - started
    (destination / 'execution.log').write_text(completed.stdout + completed.stderr, encoding='utf-8')
    after = manifest(); (destination / 'source-runtime-after.json').write_bytes(canonical(after))
    receipt = {'command': [str(executable), str(copied_harness), str(source), str(input_path)],
               'exit_code': completed.returncode, 'runtime_seconds': elapsed,
               'archive_before_sha256': runtime['sha256'], 'gem_before_sha256': gem['sha256']}
    (destination / 'command.json').write_bytes(canonical(receipt))
    if not _same(before, after): _fail('/source-runtime-after', 'Executed input/source/runtime changed')
    completed.check_returncode()
    _bytes(runtime_archive, runtime['sha256']); _bytes(standards_archive, gem['sha256'])
    native = _read(destination / 'native-output.json')
    provenance = {'runtime_archive': runtime, 'standards_gem_sha256': gem['sha256'],
        'executed_openstudio_sha256': _digest(executable.read_bytes()),
        'source_members': inputs['source_members'], 'construction_revision': REVISION,
        'getter_revision': '0.8.6', 'hybrid': True,
        'interpretation': 'Exact c8 constructors/data/helpers and c8 standard lookup, distinct actual0.8.6 getter; no all-c8 getter equivalence',
        'native_getter_policy': 'OpenStudio3.10 lexical<3.8 branch; six timesteps/hour; original getter round5',
        'ruby_description': native['ruby_description'], 'extraction_date': '2026-10-15',
        'source_origins': {'source_path': BASE + 'capture-source-origins.json',
                          'sha256': _digest((ROOT / BASE / 'capture-source-origins.json').read_bytes())},
        'upstream_notices': [{'source_path': BASE + 'capture-sources/' + name,
            'sha256': _digest((ROOT / BASE / 'capture-sources' / name).read_bytes())}
            for name in ('LICENSE-c8.md', 'LICENSE-standards086.md')],
        'source_class_counts': {'original_c8_named_rulesets': 46, 'reviewed_zero_overlays': 44}}
    lock = {'schema_version': '1.0.0', 'qualification_boundary': 'fixed_getter_water_associations_only_runtime_closed',
        'capture_provenance': provenance,
        'harness': {'source_path': BASE + 'capture-code/reference_apartment_fixed.rb', 'sha256': _digest(harness.read_bytes())},
        'builder': {'source_path': BASE + 'capture-code/schedule_generator_apartment_reference.py', 'sha256': _digest(Path(__file__).read_bytes())},
        'native_canonical_sha256': _digest(canonical(native))}
    (destination / 'capture-builder.py').write_bytes(Path(__file__).read_bytes())
    for key, payload, name in (('inputs', input_path.read_bytes(), 'fixed-native-inputs.json.gz'),
                               ('vectors', (destination / 'native-output.json').read_bytes(), 'fixed-native.json.gz')):
        blob, entry = _pack(payload, BASE + name); (destination / name).write_bytes(blob); lock[key] = entry
    (destination / 'apartment-fixed-reference-lock.json').write_bytes(canonical(lock))
    return {'lock': lock, 'inputs': inputs, 'native': native}


def _expected_discrete(definition):
    """Independent Python rule selection; native order newest first."""
    rules = definition['rules']; ordered = []
    day_names = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
    for index, rule in enumerate(rules):
        tokens = rule['day_types'].split('|')
        if any(t in tokens for t in (*day_names, 'Wkdy', 'Wknd')):
            selectors = [d for d in day_names if d in tokens or
                         (d in day_names[:5] and 'Wkdy' in tokens) or
                         (d in day_names[5:] and 'Wknd' in tokens)]
            ordered.insert(0, {'source_index': rule['source_index'],
                'start_date': rule['start_date'][5:10], 'end_date': rule['end_date'][5:10],
                'day_selectors': selectors})
    decisions = []
    for offset in range(365):
        day = date(2007, 1, 1) + timedelta(days=offset); md = day.isoformat()[5:]
        selected = -1
        for index, rule in enumerate(ordered):
            start, end = rule['start_date'], rule['end_date']
            active = start <= md <= end if start <= end else md >= start or md <= end
            if active and day_names[day.weekday()] in rule['day_selectors']:
                selected = index; break
        decisions.append(selected)
    return ordered, decisions


def _profile(rule):
    values = rule['values']; values = [values[0]] * 24 if rule.get('type', 'Constant') == 'Constant' else values
    # The native constructor stores only the final endpoint of each equal run.
    return [[float(i + 1), _stored(v)] for i, v in enumerate(values)
            if i == 23 or v != values[i + 1]]


def _compare_schedule(expected, actual, pointer):
    definition = expected['source']['value']
    if actual['id'] != expected['id'] or actual['source_rows'] != expected['rows'] or actual['programme_ids'] != expected['programme_ids']:
        _fail(pointer, 'Complete original native schedule association differs')
    for key in ('construction_kind', 'overlay_provenance', 'original_explicit_special_day_selectors'):
        if not _same(actual[key], expected[key]): _fail(pointer + '/' + key, 'Original upstream/overlay authority distinction differs')
    ordered, decisions = _expected_discrete(definition)
    if not _same(actual['rule_order'], ordered) or not _same(actual['day_rule_indices'], decisions):
        _fail(pointer, 'Native original rule order/date/day decisions differ')
    profiles = {'default': []}; specials = {}
    ordinary = [r for r in definition['rules'] if any(t in r['day_types'].split('|')
                for t in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Wkdy', 'Wknd'))]
    for i, r in enumerate(reversed(ordinary)): profiles[str(i)] = _profile(r)
    for r in definition['rules']:
        if 'Default' in r['day_types']: profiles['default'] = _profile(r)
        for key in ('WntrDsn', 'SmrDsn'):
            if key in r['day_types']: specials[key] = _profile(r)
    # Unset design-day objects alias the native default; retain explicit state.
    for key in ('WntrDsn', 'SmrDsn'): specials.setdefault(key, profiles['default'])
    if not _same(actual['profiles'], profiles) or not _same(actual['special_profiles'], specials):
        _fail(pointer, 'Native stored default/rule/design profiles differ')
    values = evaluate_rules(definition, 2007, [])['values']
    rounded = []
    for start in range(0, 8760, 24):
        rounded.extend(_hourly([[float(i + 1), _stored(v)] for i, v in enumerate(values[start:start + 24])], 6))
    if not _same(actual['values'], rounded):
        _fail(pointer, '8760 original Python/native getter values differ under existing precision policy')
    return max(abs(a - b) for a, b in zip(rounded, actual['values']))


def compare_apartment_fixed(sources: dict, reference: dict) -> dict:
    """Independently compare numerical and discrete actual native facts."""
    inputs = apartment_fixed_capture_inputs(_read(ROOT / 'sources/schedule-generator-apartment-scope.json'), sources)
    if not _same(inputs, reference['inputs']): _fail('/inputs', 'Actual input preimage differs from original sources')
    native = reference['native']; lock = reference['lock']
    _native_shapes(native)
    if (native['schema_version'] != '1.0.0' or not _same(native['reference_calendar'], CALENDAR) or
            native['ruby_description'] != lock['capture_provenance']['ruby_description'] or
            native['model_version'] != '3.10.0' or
            native['legacy_round5'] is not True or native['steps_per_hour'] != 6 or
            not _same(native['source_members'], inputs['source_members']) or
            native['input_sha256'] != _digest(canonical(inputs)) or
            _digest(canonical(native)) != lock['native_canonical_sha256']):
        _fail('/native', 'Locked actual getter/runtime/input identity differs')
    if len(native['schedules']) != 90 or len(native['water_paths']) != 20:
        _fail('/native', 'Incomplete actual 90/20 capture inventory')
    fixed = []; fixed_records = []
    for expected, actual in zip(inputs['schedules'], native['schedules']):
        error = _compare_schedule(expected, actual, '/schedules/' + expected['id'])
        fixed.append(error)
        fixed_records.append({'schedule_id': expected['id'], 'construction_kind': expected['construction_kind'],
            'hourly_count': len(actual['values']), 'hourly_max_abs_error': error,
            'native_hourly_array_sha256': _digest(canonical(actual['values'])),
            'rule_order_equal': True, 'day_rule_decisions_equal': True,
            'stored_default_and_special_profiles_equal': True,
            'native_day_rule_indices_sha256': _digest(canonical(actual['day_rule_indices']))})
    policy_path = 'atlas_schedules/data/reference/comparison-policy.json'
    policy = _read(ROOT / policy_path); tolerances = policy['tolerances']
    flows = []; controls = []; water = []
    for expected, actual in zip(inputs['water_paths'], native['water_paths']):
        for key in ('path_id', 'service', 'row', 'schedule_id', 'programme_ids', 'requirement_ids', 'helper_sources'):
            if not _same(expected[key], actual[key]): _fail('/water_paths/' + key, 'Exact original row/path/SID/view/helper association differs')
        if len(actual['probes']) != 2: _fail('/water_paths/probes', 'Both explicit synthetic areas required')
        row = expected['row']['value']
        q = sources['requirements'][expected['programme_ids'][0]]['original_demand']['value']['value']
        schedule = next(s for s in native['schedules'] if s['id'] == expected['schedule_id'])
        budget = q * math.fsum(schedule['values']) * 3600
        for area, probe in zip((80.0, 120.0), actual['probes']):
            if (probe['floor_area_m2'] != area or probe['space_multiplier'] != 1 or
                    probe['is_flow_per_area'] is not True or probe['lookup_building_type'] != row['building_type'] or
                    probe['lookup_criteria'] != {k: row[k] for k in ('template', 'building_type', 'space_type')} or
                    probe['source_density_gal_h_ft2'] != row['service_water_heating_peak_flow_per_area'] or
                    probe['source_temperature_F'] != row['service_water_heating_target_temperature'] or
                    type(probe['native_temperature_operand_C']) not in (int, float) or
                    not math.isfinite(probe['native_temperature_operand_C']) or
                    probe['source_system_type'] != row['service_water_heating_system_type'] or
                    probe['flow_schedule_name'] != row['service_water_heating_schedule'] or
                    not _same(probe['flow_values'], schedule['values']) or probe['attached_space'] is not None):
                _fail('/water_paths/probes', 'Original per-area branch/selected row/synthetic operands differ')
            expected_flow = q * area; error = abs(probe['native_peak_flow_m3_s'] - expected_flow)
            if not _close(probe['native_peak_flow_m3_s'], expected_flow, tolerances['source_arithmetic']):
                _fail('/water_paths/flow', 'Native selected q*A*1 differs from original SI density')
            if not _close(probe['native_area_ft2'], area / 0.09290304, tolerances['source_arithmetic']):
                _fail('/water_paths/area', 'Native controlled area conversion differs from original SI area')
            native_volume = probe['native_peak_flow_m3_s'] * math.fsum(probe['flow_values']) * 3600
            source_volume = budget * area
            if not _close(native_volume, source_volume, tolerances['annual_volume_m3']):
                _fail('/water_paths/annual_volume', 'Native/source whole B*A annual integral differs')
            flows.append(error)
            for slot, name in CONTROL_SLOTS:
                control = probe['controls'][name]
                value = (row['service_water_heating_target_temperature'] - 32) / 1.8 if name == 'target_temperature' else row['service_water_heating_fraction_' + name.split('_')[0]]
                stored = control['profiles']['default'][0][1]
                expected_stored = 60.0000000000001 if name == 'target_temperature' else value
                if (stored != expected_stored or control['rule_order'] != [] or
                        (name == 'target_temperature' and _stored(probe['native_temperature_operand_C']) != stored) or
                        control['day_rule_indices'] != [-1] * 365 or
                        control['special_profiles'] != {k: [[24.0, stored]] for k in ('WntrDsn', 'SmrDsn')} or
                        control['profiles'] != {'default': [[24.0, stored]]} or
                        control['values'] != [round(value, 5)] * 8760):
                    _fail('/water_paths/controls/' + name, 'Actual canonical/native stored/getter/control decision differs')
                controls.append({'path_id': expected['path_id'], 'area_m2': area, 'control': name,
                    'canonical_value': value, 'native_stored_value': stored, 'native_hourly_value': control['values'][0],
                    'native_temperature_operand_C': probe['native_temperature_operand_C'] if name == 'target_temperature' else None,
                    'canonical_vs_stored_delta': stored - value, 'hourly_max_abs_error': 0})
            water.append({'path_id': expected['path_id'], 'area_m2': area, 'B_m3_m2': budget,
                          'W_m3': source_volume, 'native_annual_volume_m3': native_volume,
                          'annual_volume_abs_error_m3': abs(native_volume - source_volume),
                          'native_area_ft2': probe['native_area_ft2'],
                          'native_peak_flow_m3_s': probe['native_peak_flow_m3_s'],
                          'canonical_peak_flow_m3_s': expected_flow, 'peak_flow_abs_error_m3_s': error})
    return {'schema_version': '1.0.0', 'passed': True,
        'counts': {'fixed_rulesets': 90, 'water_paths': 20, 'alternative_views': 40,
                   'synthetic_area_probes': 40, 'source_created_control_associations': 120},
        'fixed_hourly_max_abs_error': max(fixed), 'discrete_mismatches': [],
        'fixed_rule_comparisons': fixed_records,
        'comparison_policy': {'path': policy_path, 'sha256': _digest((ROOT / policy_path).read_bytes()),
            'peak_flow': 'source_arithmetic', 'annual_volume': 'annual_volume_m3',
            'tolerances': {k: tolerances[k] for k in ('source_arithmetic', 'annual_volume_m3')}},
        'peak_flow_max_abs_error_m3_s': max(flows), 'water_comparisons': water,
        'fixed_control_comparisons': controls,
        'boundary': 'c8 construction/helper plus actual0.8.6 getter; no native caller/full-prototype/timing certificate'}


def _artifact(name, value, locator='/'):
    payload = canonical(value if locator == '/' else {locator[1:]: value})
    return {'path': BASE + 'proofs/' + name + '.json', 'sha256': _digest(payload),
            'locator': locator, 'value': copy.deepcopy(value)}


def _field(entry, locator, value, unit, interpretation):
    return {'source_revision': 'apartment-a3-native-c8-construction-standards086-getter',
        'source_path': entry['source_path'], 'source_sha256': entry['sha256'],
        'locator': locator, 'original_value': copy.deepcopy(value), 'original_unit': unit,
        'transformation': 'Native-output-derived fixed source/control compilation; original capture retained',
        'extraction_date': '2026-10-15', 'interpretation_note': interpretation}


def _native_evidence(reference, locator, value, unit=None):
    return _field(reference['lock']['vectors'], locator, value, unit,
        'Actual native experiment under exact c8 source construction/helpers and distinct0.8.6 getter; not an upstream table field or whole-prototype certificate')


def _native_rules(reference, path_index, requirement, association, controls):
    native = reference['native']['water_paths'][path_index]
    row = native['row']['value']; rules = {}
    for slot, name in CONTROL_SLOTS:
        pointer = '/water_paths/' + str(path_index) + '/probes/0/controls/' + name
        actual = native['probes'][0]['controls'][name]
        canonical_value = (row['service_water_heating_target_temperature'] - 32) / 1.8 if name == 'target_temperature' else row['service_water_heating_fraction_' + name.split('_')[0]]
        operand = ({'value': row['service_water_heating_target_temperature'], 'unit': 'F',
            'source_field': 'service_water_heating_target_temperature',
            'source_receipt': copy.deepcopy(native['row']),
            'method': 'OpenStudio.convert(F,C) then native constant ScheduleDay storage'}
            if name == 'target_temperature' else {'value': canonical_value, 'unit': 'fraction',
                'source_field': 'create_water_use default ' + name,
                'method': 'Exact source fixed create_water_use constructor argument'})
        rules[slot] = {'method': 'native_constant_ruleset', 'original_value': canonical_value,
            'stored_value': actual['profiles']['default'][0][1],
            'native_hourly_value': actual['values'][0],
            'native_source_profile': copy.deepcopy(actual['profiles']['default']),
            'native_special_profiles': copy.deepcopy(actual['special_profiles']),
            'source_operand': operand,
            'source_profile_creation': {'method': 'create_constant_schedule_ruleset',
                'source_locator': REVISION + ' schedules/create.rb:113-147',
                'original_rule_order': [], 'original_special_state': 'not_explicitly_set',
                'getter_alias': 'Actual native getter returns fixed default'},
            'evidence': {'source_method': SOURCE_METHOD,
                'native_output_sha256': reference['lock']['vectors']['payload_sha256'],
                'source_native_pointer': pointer, 'native_capture_source': reference['lock']['vectors'],
                'source_members': copy.deepcopy(reference['inputs']['source_members']),
                'original_path_id': native['path_id'], 'original_service': copy.deepcopy(native['service']),
                'programme_id': requirement['programme']['value']['id'],
                'interpretation': 'Actual original source-created control representation; fixed fractions assign no zone heat'}}
        if _native_constant(slot, rules[slot]) != actual['values']:
            _fail(pointer, 'Existing strict native-constant method does not reproduce actual getter')
    pid = requirement['programme']['value']['id']
    value = {'programme_id': pid, 'requirement_id': requirement['requirement_id'],
        'association': copy.deepcopy(association), 'fixed_controls': copy.deepcopy(controls),
        'reference_calendar': copy.deepcopy(CALENDAR), 'rules': rules,
        'evidence': [_native_evidence(reference, '/water_paths/' + str(path_index) + '/path_id', native['path_id']),
                     _native_evidence(reference, '/water_paths/' + str(path_index) + '/programme_ids', native['programme_ids']),
                     _native_evidence(reference, '/water_paths/' + str(path_index) + '/probes/0/native_temperature_operand_C',
                                      native['probes'][0]['native_temperature_operand_C'], 'C')]}
    return _artifact('caller-water-native-controls__' + pid, value, '/native_control_schedules')


def compile_apartment_qualifications(sources: dict, native: dict) -> dict:
    """Pure build-only fixed proofs; no selector, ready flag or request-derived pool."""
    compare_apartment_fixed(sources, native)
    resources = {}; per_id = {}; by_path = {x['path_id']: i for i, x in enumerate(native['inputs']['water_paths'])}
    for pid, requirement in sources['requirements'].items():
        path_id = requirement['service_definition']['value']['path_id']; i = by_path[path_id]
        path = native['native']['water_paths'][i]
        row = sources['source_objects']['raw_rows'][pid]
        proof = _water_evidence(sources['programmes'][pid], requirement['service_definition'],
            requirement['source_ruleset'], row, sources['source_objects']['water_helpers'])
        controls = _artifact('caller-water-controls__' + pid, proof['fixed_controls']['value'])
        a = copy.deepcopy(proof['association']['value']); a['fixed_controls'] = controls
        association = _artifact('caller-water-association__' + pid, a)
        proof['fixed_controls'] = controls; proof['association'] = association
        recompiled = compile_requirement(sources['programmes'][pid],
            requirement['service_definition'], requirement['source_ruleset'], proof)
        if not _same(requirement, recompiled): _fail('/requirements/' + pid, 'A3 original requirement changed')
        control_source = _native_rules(native, i, requirement, association, controls)
        control_evidence = _field({'source_path': control_source['path'], 'sha256': control_source['sha256']},
            '/native_control_schedules', control_source['value'], None,
            'Native-output-derived control compilation, not an upstream table field; original row/helper/control associations retained')
        q = {'qualification_id': 'apartment-fixed-' + pid,
            'qualification_scope': 'exact_apartment_programme_fixed_rule_calendar_controls',
            'programme_id': pid, 'requirement': copy.deepcopy(requirement),
            'association': association, 'fixed_controls': controls,
            'evidence': [_native_evidence(native, '/water_paths/' + str(i) + '/path_id', path['path_id']), control_evidence]}
        qualification = _artifact('caller-water-qualification__' + pid, q)
        per_id[pid] = qualification
        for key, value in (('requirement', requirement), ('controls', controls),
                           ('association', association), ('qualification', qualification),
                           ('native-controls', control_source)):
            resources['reference', 'caller-water-' + key + '__' + pid] = copy.deepcopy(value)
    groups = {}
    for pid, qualification in per_id.items():
        req = qualification['value']['requirement']
        context = {'family': req['family'], 'template': req['template'], 'reference_calendar': copy.deepcopy(CALENDAR)}
        key = _digest(canonical(context)); groups.setdefault(key, (context, []))[1].append(qualification)
    if len(groups) != 8: _fail('/qualification_sets', 'Exact eight static family/template pools required')
    for key, (context, qualifications) in groups.items():
        qualifications.sort(key=lambda q: int(q['value']['requirement']['programme']['locator'][1:]))
        value = dict(context, qualification_scope='caller_unit_fixed_water_programme_coverage',
            qualifications=qualifications,
            evidence=[_native_evidence(native, '/reference_calendar', native['native']['reference_calendar'])])
        name = 'caller-water-qualification-set__' + key
        resources['reference', name] = _artifact(name, value)
    schedules = native['inputs']['schedules']
    for pid, programme in sources['programmes'].items():
        linked = [(i, s) for i, s in enumerate(schedules) if pid in s['programme_ids']]
        value = {'programme_id': pid, 'programme': copy.deepcopy(programme),
            'reference_calendar': copy.deepcopy(CALENDAR),
            'source_fixed_rules': [{'source': copy.deepcopy(s['source']),
                'construction_kind': s['construction_kind'], 'overlay_provenance': copy.deepcopy(s['overlay_provenance']),
                'original_explicit_special_day_selectors': s['original_explicit_special_day_selectors'],
                'native_representation': {'profiles': copy.deepcopy(native['native']['schedules'][i]['profiles']),
                    'special_profiles': copy.deepcopy(native['native']['schedules'][i]['special_profiles']),
                    'rule_order': copy.deepcopy(native['native']['schedules'][i]['rule_order']),
                    'day_rule_indices': copy.deepcopy(native['native']['schedules'][i]['day_rule_indices']),
                    'hourly_count': 8760,
                    'hourly_array_sha256': _digest(canonical(native['native']['schedules'][i]['values'])),
                    'source_path': native['lock']['vectors']['source_path'],
                    'source_gzip_sha256': native['lock']['vectors']['sha256'],
                    'payload_sha256': native['lock']['vectors']['payload_sha256'],
                    'locator': '/schedules/' + str(i),
                    'getter_policy': native['lock']['capture_provenance']['native_getter_policy'],
                    'source_members': copy.deepcopy(native['inputs']['source_members'])}} for i, s in linked],
            'original_loads': copy.deepcopy(programme['value']['loads']),
            'original_parameters': copy.deepcopy(programme['value']['parameters']),
            'evidence': [_native_evidence(native, '/schedules/' + str(i) + '/id', native['native']['schedules'][i]['id']) for i, _ in linked],
            'interpretation': 'All original fixed load/control Rulesets at exact programme/view association; selected dwelling timing authority remains separate'}
        if pid in per_id: value['water_qualification'] = copy.deepcopy(per_id[pid])
        name = 'apartment-fixed-programme__' + pid
        resources['reference', name] = _artifact(name, value)
    return resources


def verify_apartment_qualifications(sources: dict, native: dict, resources: dict) -> None:
    """Reject any missing/unused/foreign pool or entire independently derived proof."""
    expected = compile_apartment_qualifications(sources, native)
    if set(resources) != set(expected): _fail('/resources', 'Complete independent proof resource inventory differs')
    located = {}
    def verify_nested(value):
        if isinstance(value, dict):
            if set(value) == {'path', 'sha256', 'locator', 'value'}:
                _original(value, located)
            if set(value) == {'source_revision', 'source_path', 'source_sha256', 'locator',
                    'original_value', 'original_unit', 'transformation', 'extraction_date', 'interpretation_note'}:
                _typed(value, 'field_evidence', '/resources/evidence')
            for child in value.values(): verify_nested(child)
        elif isinstance(value, list):
            for child in value: verify_nested(child)
    for key, value in resources.items():
        if not _same(value, expected[key]): _fail('/resources/' + key[1], 'Whole independent proof resource differs')
        verify_nested(value)
        if set(value) == {'path', 'sha256', 'locator', 'value'}:
            _source(value, '/resources/' + key[1])
            payload = canonical(value['value'] if value['locator'] == '/' else {value['locator'][1:]: value['value']})
            if _bytes(ROOT / value['path'], value['sha256']) != payload:
                _fail('/resources/' + key[1], 'Derived exact JSON preimage differs')


def _write_proofs(resources, destination):
    """Retain separate immutable proof preimages and inspection resource manifest."""
    destination.mkdir(parents=True, exist_ok=False)
    files = {}
    for (kind, key), value in resources.items():
        if set(value) == {'path', 'sha256', 'locator', 'value'}:
            payload = canonical(value['value'] if value['locator'] == '/' else {value['locator'][1:]: value['value']})
            name = Path(value['path']).name
        else:
            payload = canonical(value); name = key + '.json'
        (destination / name).write_bytes(payload)
        files[key] = {'source_path': BASE + 'proofs/' + name, 'sha256': _digest(payload),
                      'size_bytes': len(payload), 'kind': kind}
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--inputs', type=Path)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--runtime-archive', type=Path)
    parser.add_argument('--standards-archive', type=Path)
    args = parser.parse_args()
    if args.capture == args.verify_only: parser.error('Choose exactly --capture or --verify-only')
    if args.capture:
        if any(v is None for v in (args.inputs, args.destination, args.runtime_archive, args.standards_archive)):
            parser.error('Capture requires explicit inputs, new destination and both pinned archive paths')
        result = capture_apartment_fixed(args.runtime_archive, args.standards_archive,
                                         args.destination, _read(args.inputs))
        print(json.dumps({'fixed_rulesets': len(result['native']['schedules']),
                          'water_paths': len(result['native']['water_paths'])}))
    else:
        scope = _read(ROOT / 'sources/schedule-generator-apartment-scope.json')
        sources = compile_apartment_sources(scope); native = load_apartment_fixed_reference()
        report = compare_apartment_fixed(sources, native)
        resources = compile_apartment_qualifications(sources, native)
        verify_apartment_qualifications(sources, native, resources)
        manifest = _read(ROOT / BASE / 'fixed-qualification-manifest.json')
        actual = {key: {'kind': kind, 'sha256': _digest(canonical(value))}
                  for (kind, key), value in resources.items()}
        if manifest['resources'] != actual: _fail('/manifest', 'Independent entire resource manifest differs')
        print(json.dumps({'passed': report['passed'], 'counts': report['counts'],
                          'resource_count': len(resources), 'static_pools': 8}))


if __name__ == '__main__': main()
