"""Build-only, exact R76/R77 matrix admission and lossless graph bookkeeping.

The private structural descriptor binds canonical content, not source scientific
qualification. Public wrappers admit only the fixed approved inputs and invoke
the same engines exercised by bounded qualified fixtures. No file I/O, RNG,
ResourceSet lookup, runtime change or release builder belongs in this module;
generate_and_stream_union only calls the public generate() its caller supplies.
Declared scientific-code pins are provenance, never live-code authentication;
the controller/runner must authenticate implementation bytes before cold use.
"""
import copy
import hashlib
import json
import time

from atlas_schedules.canonical import canonical
from atlas_schedules.contract import validate_bundle
from atlas_schedules.errors import GeneratorError
from atlas_schedules.resources import manifest_identity
from atlas_schedules.seeds import assign_physical_unit_sequence
from atlas_schedules.source_compositions import remap_binding_references

_DESCRIPTOR = 'case-matrix-structure-descriptor-1.0.0'
_MAPPING_VERSION = 'r74-static-case-matrix-design-1.0.0'
_MATRIX_VERSION = '1.0.0'
_CASE_ORDER = ('unit-chain-and-caller-closure', 'commercial-group-and-source-parent-closure')
_RAW_INPUTS = {
    'request': {'size_bytes': 450192, 'sha256': '61e0e1175edfbc161dd2ea2fbf61cfe73070ae3b48bf7363e341fb03dc63b59c'},
    'resource_manifest': {'size_bytes': 1308701, 'sha256': '4ce3102071a801b24ad903eac22e4a8011f643d8a6a7f8d7de6f9badfdc12564'},
    'mapping': {'size_bytes': 24013603, 'sha256': 'a44112fe884c35d18b44f69977ccdbcecf5dfb453a2f8095c08b3f8cc302eb52'}}
_CONTENT_INPUTS = {
    'request': {'size_bytes': 450192, 'sha256': '61e0e1175edfbc161dd2ea2fbf61cfe73070ae3b48bf7363e341fb03dc63b59c'},
    'resource_manifest': {'size_bytes': 1308701, 'sha256': '4ce3102071a801b24ad903eac22e4a8011f643d8a6a7f8d7de6f9badfdc12564'},
    'mapping': {'size_bytes': 16858843, 'sha256': '221bfe29967a88293b7e9a8599af2b552bc157f1c83c87a51cc9f2361b7cbe30'}}
_CODE_PROVENANCE = {
    'scientific_code_commit': '42d05b7b6e73386c28de50cbe8786a1b2dba4bb9',
    'authority_lock_sha256': '083390097f463e22c9c184f1f111594b49b3b3c3c285a27dd21a179928495b26',
    'code_cut_sha256': 'fe62770f0e2cfeeb28646cdc35e7b206592fddb2f0d77735c748c51e2da0a5c8'}
_REFERENCE = {'size_bytes': 1092759826, 'sha256': '06bfc6aa7d01d0cc76fd099616a7ac94ab2ba807220ff4653cea5ba5dfb6e33d'}
_BASE_GENERATION = frozenset(('master_seed', 'residential_unit_order', 'unit_seeds',
                            'operating_groups', 'source_seed_policy', 'physical_unit_seed_sequence'))
_ALLOCATION_GENERATION = frozenset(('request_instance_order', 'physical_member_generation_order',
                                  'source_parent_derivation_order', 'source_compositions'))
_OBLIGATIONS = {
    'native_physical_unit_sequence': 'matrix_native_closure',
    'operating_groups': 'matrix_group_closure',
    'building_contexts': 'matrix_context_closure',
    'source_parents': 'matrix_parent_closure',
    'typed_slot_obligations': 'matrix_slot_closure',
    'full_constituent_order': 'matrix_owner_closure',
    'full_physical_member_generation_order': 'matrix_owner_closure',
    'full_source_parent_derivation_order': 'matrix_parent_closure'}
_ACTOR_FIELDS = ('actor_kind', 'instance_key', 'building_realization_id', 'unit_id',
                 'stochastic_action', 'position', 'unit_seed')


def _fail(code, path, message):
    raise GeneratorError(code, '/case_matrix/'+path, message)


def _identity(value):
    """Canonical content identity without a second full-reference-sized byte tree.

    Containers down to depth two are framed here and every deeper value is
    encoded whole by json's C encoder: the same bytes as canonical(value), at
    C speed, while no single chunk exceeds one second-level member.
    """
    digest = hashlib.sha256(); size = 0
    try:
        for blob in _canonical_chunks(value, 2):
            digest.update(blob); size += len(blob)
        digest.update(b'\n')
    except (ValueError, TypeError, UnicodeError) as error:
        _fail('matrix_identity', 'content', str(error))
    return {'size_bytes': size+1, 'sha256': digest.hexdigest()}


def _canonical_chunks(value, depth):
    """Yield canonical JSON bytes of value (no trailing newline) in bounded chunks."""
    if depth and isinstance(value, dict):
        yield b'{'
        for n, key in enumerate(sorted(value)):
            if not isinstance(key, str): raise TypeError('Canonical JSON keys must be strings')
            yield (b',' if n else b'') + json.dumps(key, ensure_ascii=False).encode('utf-8') + b':'
            yield from _canonical_chunks(value[key], depth-1)
        yield b'}'
    elif depth and isinstance(value, (list, tuple)):
        yield b'['
        for n, item in enumerate(value):
            if n: yield b','
            yield from _canonical_chunks(item, depth-1)
        yield b']'
    else:
        yield json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                         separators=(',', ':')).encode('utf-8')


def _same(left, right):
    return left == right and canonical(left) == canonical(right)


def _require(condition, code, path, message):
    if not condition: _fail(code, path, message)


def _expectations(request, manifest, mapping):
    """Production only: raw inventory is admitted before extracting obligations."""
    return {'case_order': [c['case_id'] for c in mapping['cases']],
            'request_instance_order': [i['key'] for i in request['params']['instances']],
            **{k: mapping[k] for k in _OBLIGATIONS},
            'physical_owners': [i for i in request['params']['instances'] if i['owner_kind'] == 'physical_service'],
            'resource_entries': manifest['resources']}


def _production_descriptor(request, manifest, mapping):
    return {'schema_version': _DESCRIPTOR, **copy.deepcopy(_CONTENT_INPUTS),
            'expected': _expectations(request, manifest, mapping)}


def _admit_inputs(request, manifest, mapping):
    for key, value in [('request', request), ('resource_manifest', manifest), ('mapping', mapping)]:
        _require(_identity(value) == _CONTENT_INPUTS[key], 'matrix_admission', key,
                 'Exact approved canonical content required; caller identities are not authority')
    _require(mapping.get('schema_version') == _MAPPING_VERSION and
             tuple(c['case_id'] for c in mapping['cases']) == _CASE_ORDER,
             'matrix_admission', 'version', 'Exact approved production version and case order required')


def compile_case_matrix(full_request: dict, resource_manifest: dict, mapping: dict) -> dict:
    _admit_inputs(full_request, resource_manifest, mapping)
    return _compile_structure(full_request, resource_manifest, mapping,
                              _production_descriptor(full_request, resource_manifest, mapping))


def _admit_matrix(matrix):
    _require(isinstance(matrix, dict) and matrix.get('schema_version') == _MATRIX_VERSION,
             'matrix_admission', 'matrix', 'Approved compiled matrix required')
    _admit_inputs(matrix.get('full_request'), matrix.get('resource_manifest'), matrix.get('mapping'))
    expected = compile_case_matrix(matrix['full_request'], matrix['resource_manifest'], matrix['mapping'])
    _require(_same(matrix, expected), 'matrix_admission', 'matrix', 'Recompiled exact matrix differs')
    return _production_descriptor(matrix['full_request'], matrix['resource_manifest'], matrix['mapping'])


def route_reference_case(full_reference: dict, matrix: dict, case_id: str) -> dict:
    identities = _admit_matrix(matrix)
    _require(_identity(full_reference) == _REFERENCE, 'matrix_admission', 'full_reference',
             'Authenticated original full reference canonical content required')
    identities['full_reference'] = copy.deepcopy(_REFERENCE)
    validate_bundle(full_reference)
    result = _route_reference_structure(full_reference, matrix, case_id, identities)
    validate_bundle(result)
    return result


def assemble_original_union(case_bundles: dict[str, dict], matrix: dict) -> dict:
    identities = _admit_matrix(matrix)
    _require(isinstance(case_bundles, dict) and set(case_bundles) == set(_CASE_ORDER),
             'matrix_admission', 'case_bundles', 'Every exact approved case is required')
    identities['case_bundles'] = {key: _identity(value) for key, value in case_bundles.items()}
    for bundle in case_bundles.values(): validate_bundle(bundle)
    result = _assemble_union_structure(case_bundles, matrix, identities)
    validate_bundle(result)
    return result


def stream_original_union(case_bundles: dict[str, dict], matrix: dict):
    """Admit exactly like assemble_original_union, then stream canonical union pieces.

    Returns an iterator of (JSON pointer, bytes) whose concatenation equals
    canonical(assemble_original_union(...)). Under R145 the union itself is not
    revalidated here: each case is, and union bytes are compared exactly with
    the authenticated reference that generate() validated when it was made.
    All checks run before this returns, but encoding is lazy and reads the
    caller's cases: do not mutate them until the iterator is exhausted.
    """
    identities = _admit_matrix(matrix)
    _require(isinstance(case_bundles, dict) and set(case_bundles) == set(_CASE_ORDER),
             'matrix_admission', 'case_bundles', 'Every exact approved case is required')
    identities['case_bundles'] = {key: _identity(value) for key, value in case_bundles.items()}
    for bundle in case_bundles.values(): validate_bundle(bundle)
    return _stream_union_structure(case_bundles, matrix, identities)


def generate_and_stream_union(matrix: dict, generate, on_generated=None):
    """Generate every admitted case request with generate(), then stream the union.

    generate is the public atlas_schedules.generate (callers bind its resources).
    It validates each bundle it returns, so the bundles are not validated a
    second time; repeating it while both cases are held adds a whole-case deep
    copy (R145, R146). The requests come only from the admitted matrix. The
    byte-exact reference comparison of the returned pieces is the
    qualification; nothing here trusts a caller digest.
    on_generated(case_id, bundle, seconds) may record per-case receipts; it must
    not mutate the bundle, which the lazy pieces read until they are exhausted.
    """
    identities = _admit_matrix(matrix)
    _require([c['case_id'] for c in matrix['mapping']['cases']] == list(_CASE_ORDER),
             'matrix_admission', 'case_bundles', 'Every exact approved case is required')
    return _generate_and_stream_structure(matrix, generate, identities, on_generated)


def _generate_and_stream_structure(matrix, generate, identities, on_generated=None):
    cases = {}
    for case in matrix['mapping']['cases']:
        started = time.perf_counter()
        cases[case['case_id']] = generate(copy.deepcopy(case['request']['params']), case['request']['seed'])
        if on_generated is not None: on_generated(case['case_id'], cases[case['case_id']], time.perf_counter()-started)
    identities = {**identities, 'case_bundles': {key: _identity(value) for key, value in cases.items()}}
    return _stream_union_structure(cases, matrix, identities)


def _check_identities(identities, **values):
    _require(isinstance(identities, dict) and identities.get('schema_version') == _DESCRIPTOR,
             'matrix_identity', 'descriptor', 'Explicit versioned structural descriptor required')
    for key, value in values.items():
        _require(identities.get(key) == _identity(value), 'matrix_identity', key,
                 'Canonical input content differs from structural descriptor')
    _require(isinstance(identities.get('expected'), dict), 'matrix_identity', 'expected',
             'Independent complete structural obligations required')


def _compile_structure(full_request: dict, resource_manifest: dict, mapping: dict, identities: dict) -> dict:
    _check_identities(identities, request=full_request, resource_manifest=resource_manifest, mapping=mapping)
    _require(mapping.get('schema_version') == _MAPPING_VERSION and
             mapping.get('status') == 'DESIGN_ONLY_NOT_RELEASE_AUTHORITY',
             'matrix_version', 'mapping', 'Reviewed static mapping version/status required')
    expected = identities['expected']
    for field, code in _OBLIGATIONS.items():
        _require(field in expected and _same(mapping.get(field), expected[field]), code, field,
                 'Mapping differs from independently declared complete obligation')
    cases = mapping['cases']; case_order = [c['case_id'] for c in cases]
    _require(case_order == expected.get('case_order') and len(case_order) == len(set(case_order)) == 2,
             'matrix_partition', 'cases', 'Two ordered unique cases required')
    params = full_request['params']; instances = params['instances']; rows = mapping['requested_owners']
    request_order = [i['key'] for i in instances]
    _require(full_request.get('schema_version') == params.get('schema_version') == '1.2.0' and
             request_order == expected.get('request_instance_order') and len(set(request_order)) == len(request_order),
             'matrix_owner_closure', 'request_instance_order', 'Exact unique original request order required')
    _require(len(rows) == len(instances) and all(r['request_index'] == n and r['instance'] == instances[n]
             for n, r in enumerate(rows)), 'matrix_owner_closure', 'requested_owners', 'Exact original instances required')
    _require(resource_manifest.get('schema_version') == '1.0.0' and
             manifest_identity(resource_manifest) == resource_manifest.get('resource_set_id') == params['resource_set_id'] == mapping['resource_set_id'] and
             _same(resource_manifest['resources'], expected.get('resource_entries')) and
             _same(resource_manifest['resources'], mapping['all_resource_entries_retained_in_each_case']),
             'matrix_resource_closure', 'resources', 'Complete unchanged ResourceSet required in every case')
    _require(full_request['seed'] == mapping['master_seed'] and params['calendar'] == mapping['calendar'],
             'matrix_context_closure', 'calendar', 'Original master/resource/calendar required')
    physical = [i for i in instances if i['owner_kind'] == 'physical_service']
    _require(_same(physical, expected.get('physical_owners')), 'matrix_physical_closure', 'physical_owners',
             'Exact physical mode/identity/extent/evidence operands required')
    owner_case = {r['instance']['key']: r['case_id'] for r in rows}
    indices = []
    for case in cases:
        cid = case['case_id']; ix = case['request_indices']; indices.extend(ix)
        _require(ix == [n for n, r in enumerate(rows) if r['case_id'] == cid], 'matrix_partition', cid,
                 'Original request projection order required')
        projection = copy.deepcopy(full_request)
        projection['params']['instances'] = [instances[n] for n in ix]
        projection['params']['building_realizations'] = [c['request_realization'] for c in mapping['building_contexts'] if c['case_id'] == cid]
        _require(_same(case['request'], projection) and case['canonical_request_identity'] == _identity(projection),
                 'matrix_partition', cid+'/request', 'Case request must be a lossless original projection')
    _require(sorted(indices) == list(range(len(instances))), 'matrix_partition', 'request_indices', 'Disjoint exhaustive partition required')
    actors = mapping['native_physical_unit_sequence']
    native = [{k: a[k] for k in _ACTOR_FIELDS} for a in actors]
    computed = assign_physical_unit_sequence(full_request['seed'], [{k: a[k] for k in _ACTOR_FIELDS[:-2]} for a in actors])
    _require(native == computed and len({a['case_id'] for a in actors}) <= 1 and
             [a['instance_key'] for a in actors] == [k for k in request_order if k in {a['instance_key'] for a in actors}] and
             all(owner_case.get(a['instance_key']) == a['case_id'] for a in actors),
             'matrix_native_closure', 'native_physical_unit_sequence', 'Entire cumulative native chain including skip_n0 must remain in source order')
    parents = {p['parent_key']: p for p in mapping['source_parents']}
    expanded = []
    for row in rows:
        key = row['instance']['key']; children = row['generated_children']
        if key in parents:
            parent = parents[key]; expected_children = [c['key'] for c in parent['children']]
            _require(children == expected_children and bool(children) and parent['case_id'] == owner_case[key] and
                     all(c['member_index'] == n and c['case_id'] == parent['case_id'] for n, c in enumerate(parent['children'])),
                     'matrix_parent_closure', key, 'Complete ordered real source members required')
            for child in children:
                _require(child not in owner_case, 'matrix_parent_closure', child, 'Generated member key collision')
                owner_case[child] = owner_case[key]
            expanded.extend(children)
        else:
            _require(not children, 'matrix_parent_closure', key, 'Undeclared source parent')
            expanded.append(key)
    parent_order = [k for k in request_order if k in parents]
    _require(expanded == mapping['full_physical_member_generation_order'] and parent_order == mapping['full_source_parent_derivation_order'] and
             expanded+parent_order == mapping['full_constituent_order'] and len(set(expanded+parent_order)) == len(owner_case),
             'matrix_owner_closure', 'full_constituent_order', 'Exact physical-member-then-parent order required')
    for group in mapping['operating_groups']:
        members = group['ordered_members']
        _require(members and len(set(members)) == len(members) and all(owner_case.get(k) == group['case_id'] for k in members) and
                 not set(members) & {a['instance_key'] for a in actors}, 'matrix_group_closure', group['key'], 'Whole consumed operating group must remain together')
    contexts = mapping['building_contexts']
    _require([c['request_realization'] for c in contexts] == params['building_realizations'],
             'matrix_context_closure', 'building_contexts', 'Every entire original realization required')
    for context in contexts:
        building = context['request_realization']['building_realization_id']
        members = [i['key'] for i in instances if i.get('building_realization_id') == building]
        _require(members == context['requested_keys'] and all(owner_case.get(k) == context['case_id'] for k in members) and
                 bool(context['full_static_pool_programme_ids']), 'matrix_context_closure', building,
                 'Entire caller inventory, selected aliases and complete static pool stay together')
    slot_keys = [(s['owner_key'], s['slot']) for s in mapping['typed_slot_obligations']]
    _require(len(set(slot_keys)) == len(slot_keys) and {k for k, _ in slot_keys} <= set(owner_case) and
             all(owner_case.get(s['owner_key']) == s['case_id'] for s in mapping['typed_slot_obligations']),
             'matrix_slot_closure', 'typed_slot_obligations', 'Every typed slot and binding obligation required, regardless of weight')
    for edge in mapping['dependency_edges']:
        _require(owner_case.get(edge['from']) == owner_case.get(edge['to']) == edge['case_id'],
                 'matrix_dependency_closure', 'dependency_edges', 'Open dependency crosses case boundary')
    for case in cases:
        _require(case['full_constituent_order_projection'] == [k for k in mapping['full_constituent_order'] if owner_case[k] == case['case_id']],
                 'matrix_owner_closure', case['case_id'], 'Exact full constituent projection required')
    return copy.deepcopy({'schema_version': _MATRIX_VERSION, 'case_order': case_order,
                          'full_request': full_request, 'resource_manifest': resource_manifest, 'mapping': mapping,
                          'input_identities': {k: identities[k] for k in ('request', 'resource_manifest', 'mapping')},
                          'expected': expected, 'production_provenance': {
                              'raw_file_identities': _RAW_INPUTS, 'canonical_content_identities': _CONTENT_INPUTS,
                              'scientific_code': _CODE_PROVENANCE,
                              'interpretation': 'Fixed provenance only; live implementation bytes require controller/runner authentication'}})


def _matrix_structure(matrix, identities):
    _require(isinstance(matrix, dict) and matrix.get('schema_version') == _MATRIX_VERSION,
             'matrix_version', 'matrix', 'Versioned compiled matrix required')
    derived = _compile_structure(matrix['full_request'], matrix['resource_manifest'], matrix['mapping'], identities)
    _require(_same(matrix, derived), 'matrix_identity', 'matrix', 'Compiled matrix differs from rederived structure')
    return matrix['mapping']


def _generation_shape(generation, parents):
    expected = _BASE_GENERATION | (_ALLOCATION_GENERATION if parents else frozenset())
    _require(isinstance(generation, dict) and set(generation) == expected,
             'matrix_generation_fields', 'generation', 'Exact generation-root allowlist required; unknown fields fail closed')


def _native(mapping, cid=None):
    return [{k: a[k] for k in _ACTOR_FIELDS} for a in mapping['native_physical_unit_sequence'] if cid is None or a['case_id'] == cid]


def _graph(bundle, mapping, cid=None):
    """Structural obligations only; caller/harness separately runs strict science."""
    keys = mapping['full_constituent_order'] if cid is None else next(c['full_constituent_order_projection'] for c in mapping['cases'] if c['case_id'] == cid)
    _require([c['instance_key'] for c in bundle['constituents']] == keys, 'matrix_owner_closure', 'constituents', 'Complete exact ordered owner projection required')
    _require(bundle['schema_version'] == '1.2.0' and bundle['metadata']['resource_set_id'] == mapping['resource_set_id'] and
             bundle['metadata']['calendar'] == mapping['calendar'], 'matrix_context_closure', 'metadata', 'Original resource/calendar context required')
    parents = [p for p in mapping['source_parents'] if cid is None or p['case_id'] == cid]
    _generation_shape(bundle['generation'], bool(parents))
    generation = bundle['generation']; native = _native(mapping, cid)
    _require(generation['master_seed'] == mapping['master_seed'] and
             generation['source_seed_policy'] == 'native_unit_order_and_atlas_conditional_seeded_v1' and
             generation['physical_unit_seed_sequence'] == native and
             generation['residential_unit_order'] == [a['instance_key'] for a in native] and
             generation['unit_seeds'] == {a['instance_key']: a['unit_seed'] for a in native},
             'matrix_native_closure', 'generation', 'Actual complete source seed allocation differs')
    groups = [g for g in mapping['operating_groups'] if cid is None or g['case_id'] == cid]
    _require(set(generation['operating_groups']) == {g['key'] for g in groups}, 'matrix_group_closure', 'operating_groups', 'Complete actual operating group receipts required')
    for group in groups:
        _require([c['instance_key'] for c in bundle['constituents'] if c['generation'].get('operating_group') == group['key']] == group['ordered_members'],
                 'matrix_group_closure', group['key'], 'Complete ordered actual group membership differs')
        if 'exact_consumed_context' in group:
            _require(_same(generation['operating_groups'][group['key']]['context'], group['exact_consumed_context']),
                     'matrix_group_closure', group['key'], 'Consumed group context changed')
    if parents:
        request_keys = [r['instance']['key'] for r in mapping['requested_owners'] if cid is None or r['case_id'] == cid]
        _require(generation['request_instance_order'] == request_keys and
                 generation['physical_member_generation_order'] == [k for k in mapping['full_physical_member_generation_order'] if k in keys] and
                 generation['source_parent_derivation_order'] == [p['parent_key'] for p in parents] and
                 [(p['parent_instance_key'], p['member_instance_keys']) for p in generation['source_compositions']] ==
                 [(p['parent_key'], [c['key'] for c in p['children']]) for p in parents],
                 'matrix_parent_closure', 'source_compositions', 'Every actual parent/member receipt required')
    owners = {c['instance_key']: c for c in bundle['constituents']}
    for parent in parents:
        key = parent['parent_key']; children = [c['key'] for c in parent['children']]
        actual_parent = owners[key]
        _require([m['instance_key'] for m in actual_parent['generation']['members']] == children and
                 actual_parent['generation']['member_instance_keys'] == children,
                 'matrix_parent_closure', key, 'Every actual source member required even for zero participation')
    contexts = [c for c in mapping['building_contexts'] if cid is None or c['case_id'] == cid]
    retained_contexts = bundle['metadata']['building_realizations']
    _require([r['building_realization_id'] for r in retained_contexts] ==
             [c['request_realization']['building_realization_id'] for c in contexts],
             'matrix_context_closure', 'building_realizations', 'Complete ordered caller context projection required')
    for context, retained in zip(contexts, retained_contexts):
        declaration = {k: v for k, v in retained.items() if k not in {'source_requirements', 'method_qualification'}}
        _require(_same(declaration, context['request_realization']) and
                 [q['value']['programme_id'] for q in retained['method_qualification']['value']['qualifications']] == context['full_static_pool_programme_ids'],
                 'matrix_context_closure', retained['building_realization_id'],
                 'Entire original caller declaration and unselected static qualification pool required')
    schedules = set(); indices = []
    for key, owner in owners.items():
        slots = [s for s in mapping['typed_slot_obligations'] if s['owner_key'] == key]
        _require(set(owner['schedule_ids']) == {s['slot'] for s in slots}, 'matrix_slot_closure', key, 'All slots required even for zero participation')
        indices.extend(owner['binding_indices']); schedules.update(owner['schedule_ids'].values())
        actual = [bundle['bindings'][i] for i in owner['binding_indices']]
        for slot in slots:
            sid = owner['schedule_ids'][slot['slot']]
            _require(sid in bundle['schedules'] and bundle['schedules'][sid]['unit'] == slot['unit'],
                     'matrix_slot_closure', key+'/'+slot['slot'], 'Exact typed schedule required')
            loads = [b for b in actual if b['slot'] == slot['slot'] and b['kind'] == 'load']
            controls = [b for b in actual if b['slot'] == slot['slot'] and b['kind'] == 'control']
            _require([b['demand_id'] for b in loads] == [d['demand_id'] for d in slot['demands']] and
                     len(controls) == len(slot['controls']), 'matrix_slot_closure', key+'/'+slot['slot'], 'Every original demand/control binding required')
            for demand in slot['demands']:
                actual_demand = next((d for d in owner['demands'] if d['demand_id'] == demand['demand_id']), {})
                _require(all(actual_demand.get(k) == demand[k] for k in
                         ('demand_id', 'slot', 'quantity', 'unit', 'basis', 'fuel', 'host') if k in demand),
                         'matrix_slot_closure', key+'/'+slot['slot'], 'Original typed demand semantics differ')
            for actual_control, control in zip(controls, slot['controls']):
                _require('quantity' not in control or actual_control['control_quantity'] == control['quantity'],
                         'matrix_slot_closure', key+'/'+slot['slot'], 'Original typed control quantity differs')
    _require(sorted(indices) == list(range(len(bundle['bindings']))) and schedules == set(bundle['schedules']),
             'matrix_slot_closure', 'bindings', 'No missing, duplicate or extra binding/schedule')


def _global_consistency(value):
    objects = {}; files = {}; physical = {}; modes_sid = {}; modes_raw = {}
    def revision(path, digest):
        _require(path not in files or files[path] == digest, 'matrix_source_conflict', 'source_revision', 'One source file has conflicting revisions')
        files[path] = digest
    def walk(current):
        if isinstance(current, dict):
            if set(current) == {'path', 'sha256', 'locator', 'value'}:
                revision(current['path'], current['sha256'])
                key = (current['path'], current['sha256'], current['locator'])
                if key in objects:
                    _require(_same(objects[key], current['value']), 'matrix_source_conflict', 'source_value', 'One immutable SourceObject has conflicting values')
                objects[key] = current['value']
            if isinstance(current.get('source_path'), str) and isinstance(current.get('source_sha256'), str):
                revision(current['source_path'], current['source_sha256'])
            for child in current.values(): walk(child)
        elif isinstance(current, list):
            for child in current: walk(child)
    walk(value)
    bundles = value.values() if isinstance(value, dict) and 'constituents' not in value else [value]
    for bundle in bundles:
        for owner in bundle['constituents']:
            if owner['owner_kind'] != 'physical_service': continue
            kind = owner['physical_binding_kind']; sid = owner['source_service_id']; raw = owner['physical_id']
            if raw in physical:
                _require(physical[raw] == owner['instance_key'], 'matrix_physical_collision', 'physical_id', 'Distinct case owners collide on physical identity')
            physical[raw] = owner['instance_key']
            _require((sid not in modes_sid or modes_sid[sid] == kind) and
                     (raw not in modes_raw or modes_raw[raw] == kind), 'matrix_physical_collision', 'physical_mode', 'Cross-mode source/raw identity collision')
            modes_sid[sid] = kind; modes_raw[raw] = kind


def _copy_generated(value):
    """Copy mutable generated paths; immutable proof trees may share read-only data.

    The returned public graph still owns all mutable paths: SourceObjects and
    schedules are copied as well, so subsequent caller edits cannot leak back.
    deepcopy's memo shares repeated nested proof objects only within the result.
    """
    return copy.deepcopy(value)


def _workspace_copy(value):
    """Private remapping workspace: share immutable source subtrees read-only.

    No workspace escapes; _select_graph performs the one owned public-result
    copy. In particular, remap_binding_references never enters a SourceObject.
    """
    if isinstance(value, dict):
        if set(value) == {'path', 'sha256', 'locator', 'value'}: return value
        return {k: _workspace_copy(v) for k, v in value.items()}
    if isinstance(value, list): return [_workspace_copy(v) for v in value]
    return value


def _project_generation(generation, mapping, cid):
    parents = [p for p in mapping['source_parents'] if p['case_id'] == cid]
    result = {k: _copy_generated(generation[k]) for k in _BASE_GENERATION}
    native = [a for a in generation['physical_unit_seed_sequence'] if a['instance_key'] in {a['instance_key'] for a in _native(mapping, cid)}]
    result.update(physical_unit_seed_sequence=_copy_generated(native),
                  residential_unit_order=[a['instance_key'] for a in native],
                  unit_seeds={a['instance_key']: generation['unit_seeds'][a['instance_key']] for a in native},
                  operating_groups={g['key']: _copy_generated(generation['operating_groups'][g['key']]) for g in mapping['operating_groups'] if g['case_id'] == cid})
    if parents:
        keys = next(c['full_constituent_order_projection'] for c in mapping['cases'] if c['case_id'] == cid)
        result.update(request_instance_order=[r['instance']['key'] for r in mapping['requested_owners'] if r['case_id'] == cid],
                      physical_member_generation_order=[k for k in generation['physical_member_generation_order'] if k in keys],
                      source_parent_derivation_order=[p['parent_key'] for p in parents],
                      source_compositions=[_copy_generated(p) for p in generation['source_compositions'] if p['parent_instance_key'] in keys])
    return result


def _select_graph(bundle, keys):
    owners = {c['instance_key']: c for c in bundle['constituents']}
    indices = [i for key in keys for i in owners[key]['binding_indices']]
    index_map = {original: local for local, original in enumerate(indices)}
    selected = _copy_generated({'constituents': [owners[key] for key in keys],
                                'bindings': [bundle['bindings'][i] for i in indices],
                                'schedules': {sid: bundle['schedules'][sid] for key in keys for sid in owners[key]['schedule_ids'].values()}})
    remap_binding_references(selected['constituents'], index_map)
    remap_binding_references(selected['bindings'], index_map)
    return selected, index_map


def _route_reference_structure(full_reference: dict, matrix: dict, case_id: str, identities: dict) -> dict:
    mapping = _matrix_structure(matrix, identities)
    _check_identities(identities, full_reference=full_reference)
    _require(case_id in matrix['case_order'], 'matrix_case', 'case_id', 'Unknown matrix case')
    _graph(full_reference, mapping); _global_consistency(full_reference)
    keys = next(c['full_constituent_order_projection'] for c in mapping['cases'] if c['case_id'] == case_id)
    selected, indices = _select_graph(full_reference, keys)
    result = {k: _copy_generated(full_reference[k]) for k in ('schema_version', 'algorithm_version', 'metadata')}
    result.update(selected)
    buildings = {c.get('building_realization_id') for c in selected['constituents']}
    result['metadata']['building_realizations'] = [r for r in result['metadata']['building_realizations'] if r['building_realization_id'] in buildings]
    result['generation'] = _project_generation(full_reference['generation'], mapping, case_id)
    remap_binding_references(result['generation'], indices)
    _graph(result, mapping, case_id)
    return result


def _assemble_union_structure(case_bundles: dict[str, dict], matrix: dict, identities: dict) -> dict:
    mapping = _matrix_structure(matrix, identities)
    _require(isinstance(case_bundles, dict) and set(case_bundles) == set(matrix['case_order']),
             'matrix_partition', 'case_bundles', 'Every exact case required')
    _require(identities.get('case_bundles') == {k: _identity(v) for k, v in case_bundles.items()},
             'matrix_identity', 'case_bundles', 'Actual case content differs from descriptor')
    # Global checks deliberately precede local checks: two locally consistent
    # source revisions or independently scoped physical IDs may conflict jointly.
    _global_consistency(case_bundles)
    for cid in matrix['case_order']: _graph(case_bundles[cid], mapping, cid)
    first = case_bundles[matrix['case_order'][0]]
    metadata = {k: v for k, v in first['metadata'].items() if k != 'building_realizations'}
    owners = {}; bindings = []; schedules = {}; generations = {}; realizations = {}
    for cid in matrix['case_order']:
        bundle = case_bundles[cid]
        _require(bundle['algorithm_version'] == first['algorithm_version'] and
                 _same({k: v for k, v in bundle['metadata'].items() if k != 'building_realizations'}, metadata),
                 'matrix_context_closure', 'metadata', 'Actual cases disagree on algorithm/resource/calendar/policy')
        offset = len(bindings); shift = {i: offset+i for i in range(len(bundle['bindings']))}
        graph = _workspace_copy({'owners': bundle['constituents'], 'bindings': bundle['bindings'], 'generation': bundle['generation']})
        remap_binding_references(graph, shift)
        owners.update({c['instance_key']: c for c in graph['owners']}); bindings.extend(graph['bindings'])
        _require(not set(schedules) & set(bundle['schedules']), 'matrix_slot_closure', 'schedules', 'Cross-case schedule collision')
        schedules.update(bundle['schedules']); generations[cid] = graph['generation']
        for r in bundle['metadata']['building_realizations']:
            key = r['building_realization_id']
            _require(key not in realizations, 'matrix_context_closure', key, 'Cross-case realization collision')
            realizations[key] = r
    combined = {'constituents': [owners[k] for k in mapping['full_constituent_order']], 'bindings': bindings, 'schedules': schedules}
    selected, remap = _select_graph(combined, mapping['full_constituent_order'])
    actual_native = [a for cid in matrix['case_order'] for a in generations[cid]['physical_unit_seed_sequence']]
    actual_groups = {k: v for cid in matrix['case_order'] for k, v in generations[cid]['operating_groups'].items()}
    generation = {'master_seed': generations[matrix['case_order'][0]]['master_seed'],
                  'source_seed_policy': generations[matrix['case_order'][0]]['source_seed_policy'],
                  'physical_unit_seed_sequence': actual_native,
                  'residential_unit_order': [a['instance_key'] for a in actual_native],
                  'unit_seeds': {a['instance_key']: generations[cid]['unit_seeds'][a['instance_key']]
                                 for cid in matrix['case_order'] for a in generations[cid]['physical_unit_seed_sequence']},
                  'operating_groups': actual_groups}
    if mapping['source_parents']:
        receipts = {p['parent_instance_key']: p for g in generations.values() for p in g.get('source_compositions', [])}
        generation.update(request_instance_order=[r['instance']['key'] for r in mapping['requested_owners']],
                          physical_member_generation_order=mapping['full_physical_member_generation_order'],
                          source_parent_derivation_order=mapping['full_source_parent_derivation_order'],
                          source_compositions=[receipts[k] for k in mapping['full_source_parent_derivation_order']])
    generation = _copy_generated(generation); remap_binding_references(generation, remap)
    result = {'schema_version': first['schema_version'], 'algorithm_version': first['algorithm_version'],
              'metadata': _copy_generated(metadata), 'generation': generation, **selected}
    result['metadata']['building_realizations'] = [_copy_generated(realizations[c['request_realization']['building_realization_id']]) for c in mapping['building_contexts']]
    _graph(result, mapping); _global_consistency(result)
    return result


_UNION_KEYS = frozenset(('schema_version', 'algorithm_version', 'metadata', 'generation',
                         'constituents', 'bindings', 'schedules'))
_CANONICAL_OPTIONS = {'ensure_ascii': False, 'allow_nan': False, 'sort_keys': True, 'separators': (',', ':')}


def _union_skeleton(case_bundles, matrix, identities):
    """Check the exact _assemble_union_structure value without materializing it.

    Returns (view, members). Every check and order is unchanged and runs here,
    before any byte is emitted. Generation receipts are private remapped copies;
    schedules, metadata and SourceObjects stay shared read-only with the cases;
    owners and bindings are remapped one private copy at a time by the members
    generators while they are encoded, so peak memory stays near the two cases.
    Nothing here leaves this module except as encoded bytes.
    Single faults raise the same code as _assemble_union_structure; with several
    simultaneous faults the first code reported may differ, because binding
    references are remapped after, not during, the per-case collision loop.
    """
    mapping = _matrix_structure(matrix, identities)
    _require(isinstance(case_bundles, dict) and set(case_bundles) == set(matrix['case_order']),
             'matrix_partition', 'case_bundles', 'Every exact case required')
    _require(identities.get('case_bundles') == {k: _identity(v) for k, v in case_bundles.items()},
             'matrix_identity', 'case_bundles', 'Actual case content differs from descriptor')
    _global_consistency(case_bundles)
    for cid in matrix['case_order']: _graph(case_bundles[cid], mapping, cid)
    first = case_bundles[matrix['case_order'][0]]
    metadata = {k: v for k, v in first['metadata'].items() if k != 'building_realizations'}
    owners = {}; schedules = {}; realizations = {}
    for cid in matrix['case_order']:
        bundle = case_bundles[cid]
        _require(bundle['algorithm_version'] == first['algorithm_version'] and
                 _same({k: v for k, v in bundle['metadata'].items() if k != 'building_realizations'}, metadata),
                 'matrix_context_closure', 'metadata', 'Actual cases disagree on algorithm/resource/calendar/policy')
        owners.update({c['instance_key']: (cid, c) for c in bundle['constituents']})
        _require(not set(schedules) & set(bundle['schedules']), 'matrix_slot_closure', 'schedules', 'Cross-case schedule collision')
        schedules.update(bundle['schedules'])
        for r in bundle['metadata']['building_realizations']:
            key = r['building_realization_id']
            _require(key not in realizations, 'matrix_context_closure', key, 'Cross-case realization collision')
            realizations[key] = r
    # One composed map per case: case-local index -> case offset -> union owner order.
    order = mapping['full_constituent_order']; maps = {cid: {} for cid in matrix['case_order']}; positions = []
    for key in order:
        cid, owner = owners[key]
        for index in owner['binding_indices']:
            maps[cid][index] = len(positions); positions.append((cid, index))
    def private(value, cid):
        copied = _workspace_copy(value); remap_binding_references(copied, maps[cid]); return copied
    generations = {cid: private(case_bundles[cid]['generation'], cid) for cid in matrix['case_order']}
    actual_native = [a for cid in matrix['case_order'] for a in generations[cid]['physical_unit_seed_sequence']]
    generation = {'master_seed': generations[matrix['case_order'][0]]['master_seed'],
                  'source_seed_policy': generations[matrix['case_order'][0]]['source_seed_policy'],
                  'physical_unit_seed_sequence': actual_native,
                  'residential_unit_order': [a['instance_key'] for a in actual_native],
                  'unit_seeds': {a['instance_key']: generations[cid]['unit_seeds'][a['instance_key']]
                                 for cid in matrix['case_order'] for a in generations[cid]['physical_unit_seed_sequence']},
                  'operating_groups': {k: v for cid in matrix['case_order'] for k, v in generations[cid]['operating_groups'].items()}}
    if mapping['source_parents']:
        receipts = {p['parent_instance_key']: p for g in generations.values() for p in g.get('source_compositions', [])}
        generation.update(request_instance_order=[r['instance']['key'] for r in mapping['requested_owners']],
                          physical_member_generation_order=mapping['full_physical_member_generation_order'],
                          source_parent_derivation_order=mapping['full_source_parent_derivation_order'],
                          source_compositions=[receipts[k] for k in mapping['full_source_parent_derivation_order']])
    # Every owner and binding must remap; check read-only now so failure precedes any byte.
    for key in order:
        cid, owner = owners[key]
        if not _remappable(owner, maps[cid]): private(owner, cid)  # raises remap's own error
    for cid, index in positions:
        if not _remappable(case_bundles[cid]['bindings'][index], maps[cid]): private(case_bundles[cid]['bindings'][index], cid)
    # The checked view differs from the emitted union only below binding references that
    # _graph never reads: owners carry their remapped binding_indices, bindings are shared.
    view = {'schema_version': first['schema_version'], 'algorithm_version': first['algorithm_version'],
            'metadata': {**metadata, 'building_realizations': [
                realizations[c['request_realization']['building_realization_id']] for c in mapping['building_contexts']]},
            'generation': generation,
            'constituents': [dict(owners[key][1], binding_indices=[maps[owners[key][0]][i] for i in owners[key][1]['binding_indices']])
                             for key in order],
            'bindings': [case_bundles[cid]['bindings'][index] for cid, index in positions],
            'schedules': {sid: schedules[sid] for key in order for sid in owners[key][1]['schedule_ids'].values()}}
    _graph(view, mapping); _global_consistency(view)
    # Emitted owners and bindings are remapped private copies made one at a time.
    members = {'constituents': (private(owners[key][1], owners[key][0]) for key in order),
               'bindings': (private(case_bundles[cid]['bindings'][index], cid) for cid, index in positions)}
    return view, members


def _remappable(value, index_map):
    """Read-only mirror of remap_binding_references' walk: True if it would succeed."""
    seen = set(); stack = [value]
    while stack:
        current = stack.pop()
        if not isinstance(current, (dict, list)) or id(current) in seen: continue
        seen.add(id(current))
        if isinstance(current, list): stack.extend(current); continue
        if set(current) == {'path', 'sha256', 'locator', 'value'}: continue
        for key, child in current.items():
            if key == 'binding_index':
                if type(child) is not int or child not in index_map: return False
            elif key == 'binding_indices':
                if not isinstance(child, list) or any(type(i) is not int or i not in index_map for i in child): return False
            else: stack.append(child)
    return True


def _encode(value, path):
    try:
        return json.dumps(value, **_CANONICAL_OPTIONS).encode('utf-8')
    except (ValueError, TypeError, UnicodeError) as error:
        raise GeneratorError('invalid_json', path or '/', str(error)) from error


def _pointer(token):
    return str(token).replace('~', '~0').replace('/', '~1')


def _canonical_pieces(union, members=None):
    """Yield (JSON pointer, bytes); their concatenation is canonical(union).

    Owner and binding lists and the schedule map are split per member; every
    other top-level value is one piece. Keys follow json's sort_keys order.
    members may supply the owner/binding items lazily in place of union's lists.
    """
    _require(isinstance(union, dict) and set(union) == _UNION_KEYS, 'matrix_union_shape', 'union',
             'Exact seven-member union required')
    members = members or {}
    yield '', b'{'
    for n, key in enumerate(sorted(union)):
        path = '/'+_pointer(key); head = (b',' if n else b'') + _encode(key, path) + b':'; value = union[key]
        if key in ('bindings', 'constituents'):
            yield path, head + b'['
            for i, item in enumerate(members.get(key, value)):
                yield path+'/'+str(i), (b',' if i else b'') + _encode(item, path+'/'+str(i))
            yield path, b']'
        elif key == 'schedules':
            yield path, head + b'{'
            for i, sid in enumerate(sorted(value)):
                member = path+'/'+_pointer(sid)
                yield member, (b',' if i else b'') + _encode(sid, member) + b':' + _encode(value[sid], member)
            yield path, b'}'
        else:
            yield path, head + _encode(value, path)
    yield '', b'}\n'


def _stream_union_structure(case_bundles: dict[str, dict], matrix: dict, identities: dict):
    """Run every union check eagerly, then return the lazy canonical piece iterator."""
    view, members = _union_skeleton(case_bundles, matrix, identities)
    return _canonical_pieces(view, members)
