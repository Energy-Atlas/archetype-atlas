"""Independent exact-source authority; no sampling or physical-owner creation.

Extraction adapters are internal resource joins, never caller authority. Native
qualification selectors deliberately have no production entries. A source pilot,
certificate-shaped JSON, equal arrays, or a same-family context cannot open them.
"""
import calendar
import copy
from datetime import date
import hashlib
import math

from .canonical import canonical
from .contract import _check_schema, _finite, _load_schema
from .errors import GeneratorError
from .resources import ResourceSet


CENSUS_FIELDS = ('role_id', 'source_order', 'source_service_id', 'source_path_id',
                 'role_kind', 'source_space', 'geometry_operands')
FULL_SCOPE = 'full_selected_programme_and_water_registration'


def _fail(path, message, code='source_integrity'):
    raise GeneratorError(code, path, message)


def _exact(value, keys, path):
    if not isinstance(value, dict) or set(value) != set(keys):
        _fail(path, 'Missing or unknown extraction/authority fields')


def _same(left, right):
    """JSON identity distinguishes booleans from otherwise equal numbers."""
    return canonical(left) == canonical(right)


def _typed(value, name, path):
    schema = _load_schema('bundle', '1.2.0')
    _finite(value, path)
    try:
        _check_schema(value, schema['$defs'][name], schema, path)
    except GeneratorError as error:
        raise GeneratorError('source_integrity', error.path, error.message) from error
    return value


def _evidence(value, path):
    if not isinstance(value, list) or not value:
        _fail(path, 'Independent field evidence is required')
    for i, item in enumerate(value):
        _typed(item, 'field_evidence', path+'/'+str(i))
        try:
            date.fromisoformat(item['extraction_date'])
        except ValueError:
            _fail(path+'/'+str(i), 'Invalid extraction date')


def _source(value, path):
    return _typed(value, 'source_object', path)


def _positive(value, path, zero=False):
    if type(value) not in (int, float) or not math.isfinite(value) or (value < 0 if zero else value <= 0):
        _fail(path, 'Finite evidenced source operand required')


def _qualified_exact_context(qualification):
    """Closed until exact full-slot evidence is separately reviewed and packaged."""
    return False


def _qualified_recovered_bridge(role):
    """No recovered-null bridge (including LargeHotel Laundry) is qualified."""
    return False


def _extent(role, path):
    operands = role['geometry_operands']
    _evidence(operands['evidence'], path+'/geometry_operands/evidence')
    for field in ('floor_area_m2', 'space_multiplier', 'zone_multiplier'):
        if operands[field] is not None:
            _positive(operands[field], path+'/geometry_operands/'+field)
    if role['source_basis'] == 'absolute':
        value, unit = 1, '1'
    else:
        for field in ('floor_area_m2', 'space_multiplier'):
            _positive(operands[field], path+'/geometry_operands/'+field)
        value = operands['floor_area_m2'] * operands['space_multiplier']
        _positive(value, path+'/consumed_extent/value')
        unit = 'm2'
    return {'value': value, 'unit': unit, 'evidence': copy.deepcopy(operands['evidence'])}


def validate_inventory(inventory, *, _incoming=False):
    """Validate a locked independent inventory, including its separate census."""
    _exact(inventory, ('inventory_sha256', 'payload'), '/inventory')
    payload = inventory['payload']; _typed(payload, 'inventory_payload', '/inventory/payload')
    if inventory['inventory_sha256'] != hashlib.sha256(canonical(payload)).hexdigest():
        _fail('/inventory/inventory_sha256', 'Inventory payload checksum differs')
    _evidence(payload['evidence'], '/inventory/evidence')
    geometry = payload['geometry']['value']
    if not isinstance(geometry, dict) or 'fixture_role_census' not in geometry:
        _fail('/inventory/geometry', 'Independent source-extraction census is missing', 'requires_binding')
    _exact(geometry, ('source_geometry', 'fixture_role_census', 'evidence'), '/inventory/geometry')
    _source(geometry['source_geometry'], '/inventory/geometry/source_geometry')
    _evidence(geometry['evidence'], '/inventory/geometry/evidence')
    expected = [{k: role[k] for k in CENSUS_FIELDS} for role in payload['roles']]
    if not _same(geometry['fixture_role_census'], expected):
        _fail('/inventory/roles', 'Ordered roles differ from the independent complete source census')
    seen, identities, services, schedules = set(), set(), {}, {}
    for i, role in enumerate(payload['roles']):
        path = '/inventory/roles/'+str(i)
        if type(role['source_order']) is not int or role['source_order'] != i or role['role_id'] in seen:
            _fail(path, 'Role identity/order must be unique and contiguous in original enumeration')
        seen.add(role['role_id']); _evidence(role['evidence'], path+'/evidence')
        definition = role['service_definition']['value']; sid = role['source_service_id']
        if not isinstance(definition, dict) or not isinstance(definition.get('load'), dict):
            _fail(path, 'Entire original service definition is required')
        load = definition['load']
        if (definition.get('id') != sid or definition.get('path_id') != role['source_path_id'] or
                definition.get('building_type') != payload['family'] or definition.get('template') != payload['template'] or
                definition.get('ownership') != 'instantiate_once' or
                definition.get('assignment') != 'consumer_host_when_applicable' or
                load.get('demand_id') != sid or load.get('service_id') != sid or
                load.get('quantity') != 'hot_water_volume' or load.get('scope') != 'building_service' or
                load.get('basis') != role['source_basis'] or
                load.get('unit') != {'floor_area': 'm3/s/m2', 'absolute': 'm3/s'}[role['source_basis']]):
            _fail(path, 'Original service identity, source family/path, basis or volume semantics differs')
        if load.get('value') is None or load.get('status') != 'known':
            _fail(path, 'Unknown original magnitude is not zero', 'requires_binding')
        _positive(load['value'], path+'/service_definition/load/value', zero=True)
        space = role['source_space']
        if (role['role_kind'] == 'absolute_fixture' and (space is not None or role['source_basis'] != 'absolute') or
                role['role_kind'] == 'source_space_fixture' and space is None):
            _fail(path, 'Source-space identity and unallocated absolute role disagree')
        identity = (sid, space['handle'] if space else None)
        if identity in identities:
            _fail(path, 'One source fixture cannot be relisted under another role ID')
        identities.add(identity)
        if not _same(role['consumed_extent'], _extent(role, path)):
            _fail(path+'/consumed_extent', 'Extent must equal original area times space multiplier once, or absolute one')
        authority = role['schedule_authority']
        if authority['kind'] == 'canonical_ruleset':
            if (not isinstance(authority['canonical_schedule']['value'], dict) or not load.get('schedule_id') or
                    authority['canonical_schedule']['value'].get('id') != load['schedule_id']):
                _fail(path+'/schedule_authority', 'Original complete Ruleset ID differs from the service')
        else:
            if (load.get('schedule_id') is not None or authority['frozen_schedule_id'] is not None or
                    not _same(authority['service_definition'], role['service_definition']) or not authority['source_rows']):
                _fail(path+'/schedule_authority', 'Recovered source bridge must retain frozen null and entire original service/rows')
            _evidence(authority['bridge_evidence'], path+'/schedule_authority/bridge_evidence')
            if not _incoming and not _qualified_recovered_bridge(role):
                _fail(path+'/schedule_authority', 'Recovered-null source Ruleset bridge is not independently qualified', 'requires_binding')
        if sid in services and (not _same(services[sid], role['service_definition']) or not _same(schedules[sid], authority)):
            _fail(path, 'Repeated service definition/Ruleset authority differs')
        services[sid], schedules[sid] = role['service_definition'], authority
    return copy.deepcopy(inventory)


def nested_source(parent, suffix, value):
    """Locate an entire nested object without changing its source-file identity."""
    return dict(copy.deepcopy(parent), locator=parent['locator'].rstrip('/')+suffix, value=copy.deepcopy(value))


def _method(reference, programme):
    _source(reference, '/original_method_reference')
    value = reference['value']
    _exact(value, ('program_id', 'source_hoo_configuration_id', 'context_evidence_view',
                   'method_consumed_context', 'original_method', 'evidence'), '/original_method_reference/value')
    if (value['program_id'] != programme['id'] or value['context_evidence_view'] != programme['evidence_view'] or
            not isinstance(value['source_hoo_configuration_id'], str) or not value['source_hoo_configuration_id']):
        _fail('/original_method_reference', 'Original member method/source view identity differs')
    _source(value['original_method'], '/original_method_reference/original_method')
    _source(value['method_consumed_context'], '/original_method_reference/method_consumed_context')
    _evidence(value['evidence'], '/original_method_reference/evidence')
    return value


def _programme_requirement(requirement):
    return requirement['parent_programme'] if requirement['kind'] == 'original_source_components' else requirement['programme']


def _source_components(value, path):
    if not isinstance(value, list) or not value:
        _fail(path, 'Nonempty original source-component array required')
    for i, component in enumerate(value):
        where = path+'/'+str(i)
        if not isinstance(component, dict): _fail(where, 'Entire original component object required')
        _typed(component.get('program_id'), 'id', where+'/program_id')
        _positive(component.get('weight'), where+'/weight', zero=True)
        load = component.get('load')
        if not isinstance(load, dict): _fail(where+'/load', 'Entire original component load required')
        for field in ('demand_id', 'service_id'):
            _typed(load.get(field), 'id', where+'/load/'+field)
        if load.get('schedule_id') is not None:
            _typed(load['schedule_id'], 'id', where+'/load/schedule_id')


def _composition(value, path):
    if not isinstance(value, dict): _fail(path, 'Entire original composition object required')
    _typed(value.get('id'), 'id', path+'/id')
    members = value.get('members')
    if not isinstance(members, list) or not members: _fail(path+'/members', 'Nonempty original composition member array required')
    for i, member in enumerate(members):
        where = path+'/members/'+str(i)
        if not isinstance(member, dict): _fail(where, 'Entire original composition member object required')
        for field in ('program_id', 'source_program_id'):
            _typed(member.get(field), 'id', where+'/'+field)
        _positive(member.get('represented_area_m2'), where+'/represented_area_m2')
        _positive(member.get('weight'), where+'/weight', zero=True)
    return value


def _programme(value, path):
    if (not isinstance(value, dict) or any(not isinstance(value.get(k), str) or not value[k]
            for k in ('id', 'source_id', 'building_type', 'template')) or value.get('evidence_view') not in ('source', 'reviewed') or
            not isinstance(value.get('loads'), list) or any(not isinstance(load, dict) for load in value['loads']) or
            not isinstance(value.get('service_ids'), list) or any(not isinstance(sid, str) or not sid for sid in value['service_ids']) or
            len(set(value['service_ids'])) != len(value['service_ids'])):
        _fail(path, 'Entire original programme identity, loads and unique service relation required')
    for i, load in enumerate(value['loads']):
        if load.get('quantity') == 'hot_water_volume' and 'source_components' in load:
            _typed(value.get('composition_id'), 'id', path+'/composition_id')
            _source_components(load['source_components'], path+'/loads/'+str(i)+'/source_components')
    return value


def validate_requirements(requirements, inventory):
    """Close retained original demand/reference/components against the inventory."""
    payload = inventory['payload']
    if not isinstance(requirements, list): _fail('/source_requirements', 'Independent requirement array required')
    seen = set(); by_id = {}
    for r in requirements:
        _typed(r, 'service_requirement', '/source_requirements')
        if r['kind'] == 'original_apartment_unit_demand':
            _fail('/source_requirements', 'Caller-unit authority is separate from exact-source authority')
        if r['requirement_id'] in seen: _fail('/source_requirements', 'Duplicate source requirement')
        seen.add(r['requirement_id']); by_id[r['requirement_id']] = r
        if any(r[field] != payload[field] for field in ('inventory_id', 'family', 'template')) or r['inventory_sha256'] != inventory['inventory_sha256']:
            _fail('/source_requirements', 'Requirement source inventory/family/template differs')
        _evidence(r['evidence'], '/source_requirements/evidence')
        programme = _programme_requirement(r); p = _programme(programme['value'], '/source_requirements/programme')
        if (p.get('building_type') != payload['family'] or
                p.get('template') != payload['template'] or p.get('evidence_view') not in ('source', 'reviewed')):
            _fail('/source_requirements/programme', 'Complete original programme source identity differs')
        if r['kind'] == 'original_source_components': continue
        sid = r['source_service_id']
        roles = [role for role in payload['roles'] if role['source_service_id'] == sid and
                 p.get('source_id') in role['service_definition']['value'].get('beneficiary_program_ids', [])]
        if (not roles or r['source_beneficiary_id'] != p.get('source_id') or
                r['expected_role_ids'] != [role['role_id'] for role in roles] or
                not _same(r['service_definition'], roles[0]['service_definition'])):
            _fail('/source_requirements', 'Original beneficiary/ordered role coverage/service definition differs')
        if r['kind'] == 'original_programme_demand':
            original = r['original_demand']; matches = [i for i, load in enumerate(p.get('loads', [])) if _same(load, original['value'])]
            if len(matches) != 1 or not _same(original, nested_source(programme, '/loads/'+str(matches[0]), original['value'])):
                _fail('/source_requirements/original_demand', 'Entire original load and its source locator are required')
            load = copy.deepcopy(original['value']); load['scope'] = 'building_service'
            if (original['value'].get('scope') != 'program_service' or original['value'].get('basis') != 'floor_area' or
                    not _same(load, r['service_definition']['value']['load'])):
                _fail('/source_requirements/original_demand', 'Entire source programme load must equal service load except scope')
        else:
            if (not _same(r['original_service_relation'], nested_source(programme, '/service_ids', p.get('service_ids'))) or
                    sid not in p.get('service_ids', []) or roles[0]['source_basis'] != 'absolute' or
                    any(load.get('service_id') == sid for load in p.get('loads', []))):
                _fail('/source_requirements/original_service_relation', 'Whole original absolute service relation required without invented local demand')
    for r in requirements:
        if r['kind'] != 'original_source_components': continue
        programme = r['parent_programme']; p = programme['value']; original = r['original_mixed_demand']
        matches = [i for i, load in enumerate(p.get('loads', [])) if _same(load, original['value'])]
        if len(matches) != 1 or not _same(original, nested_source(programme, '/loads/'+str(matches[0]), original['value'])):
            _fail('/source_requirements/original_mixed_demand', 'Entire original mixed load must be retained')
        composition = _composition(r['composition']['value'], '/source_requirements/composition')
        if (composition.get('id') != p.get('composition_id') or composition.get('building_type') != p.get('building_type') or
                composition.get('template') != p.get('template') or composition.get('evidence_view') != p.get('evidence_view')):
            _fail('/source_requirements/composition', 'Original composition source/view differs')
        originals = original['value'].get('source_components', [])
        if not originals or len(r['components']) != len(originals): _fail('/source_requirements/components', 'Original component cardinality differs')
        covered, member_ids = set(), []
        for i, (c, original_component) in enumerate(zip(r['components'], originals)):
            child = by_id.get(c['child_requirement_id'])
            if child is None or child['kind'] != 'original_programme_demand':
                _fail('/source_requirements/components', 'Only independently compiled demand leaves are supported', 'requires_binding')
            member = child['programme']['value']; member_ids.append(member['id'])
            matches = [m for m in composition.get('members', []) if m.get('program_id') == member['id']]
            if len(matches) != 1: _fail('/source_requirements/components', 'Composition membership is missing/ambiguous')
            cm = matches[0]
            if (type(c['component_index']) is not int or c['component_index'] != i or
                    c['member_program_id'] != member['id'] or c['member_evidence_view'] != member['evidence_view'] or
                    c['member_source_id'] != member['source_id'] or cm.get('source_program_id') != member['source_id'] or
                    not _same(c['represented_area_m2'], cm.get('represented_area_m2')) or
                    not _same(c['original_weight'], cm.get('weight')) or
                    not _same(c['original_component'], nested_source(original, '/source_components/'+str(i), original_component)) or
                    original_component.get('program_id') != member['id'] or
                    not _same(original_component.get('weight'), cm.get('weight')) or
                    not _same(original_component.get('load'), child['original_demand']['value'])):
                _fail('/source_requirements/components', 'Entire original component load/member own view/source area/weight/order differs')
            method = _method(c['original_method_reference'], member)
            if method['source_hoo_configuration_id'] != child['source_hoo_configuration_id']:
                _fail('/source_requirements/components', 'Original child method configuration differs')
            overlap = covered.intersection(child['expected_role_ids'])
            if overlap: _fail('/source_requirements/components', 'Duplicate/overlapping component role authority')
            covered.update(child['expected_role_ids'])
        if member_ids != [m['program_id'] for m in composition['members'] if m['program_id'] in member_ids]:
            _fail('/source_requirements/components', 'Original component/composition order differs')
    return copy.deepcopy(requirements)


def _get(resources, key):
    _typed(key, 'id', '/reference/key')
    try:
        return resources.get('reference', key)
    except GeneratorError as error:
        if error.code != 'missing_resource': raise
        raise GeneratorError('requires_binding', '/reference/'+key, 'Exact independently packaged authority is missing') from error


def _selected_context(context):
    _source(context, '/selected_method_context'); value = context['value']
    _exact(value, ('selected_method_context_id', 'source_hoo_configuration_id', 'context_evidence_view',
                   'qualification_scope', 'qualification_id', 'method_consumed_context'), '/selected_method_context/value')
    for field in ('selected_method_context_id', 'source_hoo_configuration_id', 'qualification_id'):
        _typed(value[field], 'id', '/selected_method_context/'+field)
    if value['qualification_scope'] != FULL_SCOPE or value['context_evidence_view'] not in ('source', 'reviewed'):
        _fail('/selected_method_context', 'Full selected programme and water registration scope required', 'requires_binding')
    _source(value['method_consumed_context'], '/selected_method_context/method_consumed_context')
    consumed = value['method_consumed_context']['value']
    _exact(consumed, ('calendar', 'source_resources', 'caller_policy', 'object_order', 'people', 'registration', 'fixed_companions'), '/method_consumed_context')
    clock = consumed['calendar']; _exact(clock, ('year', 'clock', 'holidays'), '/method_consumed_context/calendar')
    if (type(clock['year']) is not int or not 1 <= clock['year'] <= 9999 or calendar.isleap(clock['year']) or
            clock['clock'] != 'local_standard_time' or clock['holidays'] != []):
        _fail('/method_consumed_context/calendar', 'Exact nonleap local-standard calendar required', 'requires_binding')
    for field in ('caller_policy', 'people', 'registration', 'fixed_companions'):
        _source(consumed[field], '/method_consumed_context/'+field)
    if not isinstance(consumed['source_resources'], list) or not consumed['source_resources']:
        _fail('/method_consumed_context/source_resources', 'Complete locked method resource context required')
    for item in consumed['source_resources']: _source(item, '/method_consumed_context/source_resources')
    if not isinstance(consumed['object_order'], list) or not consumed['object_order']:
        _fail('/method_consumed_context/object_order', 'Original consumed object order required')
    for item in consumed['object_order']: _typed(item, 'id', '/method_consumed_context/object_order')
    return value


def resolve_exact_authority(instance: dict, realization: dict, recipe: dict, resources: ResourceSet) -> dict:
    """Resolve complete independently locked source authority before any RNG."""
    # The first lookup is invariant: no alias, recipe child or SID selects census.
    inventory = validate_inventory(_get(resources, 'physical-fixture-inventory__'+realization['inventory_id']))
    reference = recipe.get('exact_source_authority')
    _exact(reference, ('inventory_id', 'inventory_sha256', 'requirements_key', 'qualification_key'), '/recipe/exact_source_authority')
    payload = inventory['payload']
    if (realization.get('mode') != 'exact_source_fixture_extents' or
            realization.get('inventory_id') != payload['inventory_id'] or
            realization.get('inventory_sha256') != inventory['inventory_sha256'] or
            reference['inventory_id'] != payload['inventory_id'] or reference['inventory_sha256'] != inventory['inventory_sha256']):
        _fail('/building_realizations', 'Exact source inventory identity/hash differs')
    if instance.get('building_realization_id') != realization.get('building_realization_id'):
        _fail('/building_realization_id', 'Owner realization identity differs', 'shared_service_conflict')
    if instance.get('operating_group') != realization.get('operating_group'):
        _fail('/operating_group', 'Actual owner and selected realization groups differ', 'operating_group_conflict')
    requirements = validate_requirements(_get(resources, reference['requirements_key']), inventory)
    if not isinstance(recipe.get('required_service_links'), list) or not isinstance(recipe.get('required_service_sets'), list):
        _fail('/recipe', 'Both independent C5 and exact-set inventories are mandatory')
    own = [r for r in requirements if _programme_requirement(r)['value']['id'] == instance.get('program_id')]
    if instance.get('owner_kind') == 'program' and not _same(own, recipe['required_service_sets']):
        _fail('/recipe/required_service_sets', 'Recipe requirements differ from independently compiled original source inventory')
    _no_double_listing(recipe['required_service_links'], recipe['required_service_sets'])
    qualification = _source(_get(resources, reference['qualification_key']), '/method_qualification')
    q = qualification['value']
    _exact(q, ('qualification_id', 'qualification_scope', 'inventory_id', 'inventory_sha256', 'program_ids',
               'selected_method_context', 'evidence'), '/method_qualification/value')
    _evidence(q['evidence'], '/method_qualification/evidence')
    context = _selected_context(q['selected_method_context'])
    if (q['inventory_id'] != payload['inventory_id'] or q['inventory_sha256'] != inventory['inventory_sha256'] or
            q['qualification_id'] != context['qualification_id'] or q['qualification_scope'] != FULL_SCOPE):
        _fail('/method_qualification', 'Qualified inventory/full-slot context identity differs')
    if (context['selected_method_context_id'] != realization.get('selected_method_context_id') or
            context['source_hoo_configuration_id'] != realization.get('source_hoo_configuration_id')):
        _fail('/selected_method_context_id', 'Selected actual realization method differs', 'operating_group_conflict')
    if not isinstance(q['program_ids'], list):
        _fail('/method_qualification/program_ids', 'Exact qualified programme coverage is malformed')
    for pid in q['program_ids']: _typed(pid, 'id', '/method_qualification/program_ids')
    if len(set(q['program_ids'])) != len(q['program_ids']):
        _fail('/method_qualification/program_ids', 'Exact qualified programme coverage is malformed')
    if instance.get('owner_kind') == 'program' and instance.get('program_id') not in q['program_ids']:
        _fail('/method_qualification/program_ids', 'Exact programme full-slot qualification is missing', 'requires_binding')
    if own and any(_programme_requirement(r)['value']['evidence_view'] != payload['evidence_view'] for r in own):
        _fail('/source_requirements', 'Programme own view differs from selected inventory; child variant required')
    if not _qualified_exact_context(qualification):
        _fail('/method_qualification', 'Exact full selected programme/water registration is not qualified', 'requires_binding')
    return copy.deepcopy({'inventory': inventory, 'source_requirements': requirements, 'method_qualification': qualification})


def _no_double_listing(links, sets):
    legacy = {(r.get('source_channel'), r.get('source_service_id')) for r in links}
    exact = {(r['source_channel'], r['source_service_id']) for r in sets if 'source_service_id' in r}
    if legacy.intersection(exact):
        _fail('/required_service_sets', 'One original channel/SID cannot occur in both independent inventories')


def _member(adapter):
    _exact(adapter, ('parent_inventory_id', 'parent_inventory_sha256', 'canonical_member', 'original_method_reference',
                     'conserved_source_authority', 'evidence'), '/original_member')
    _source(adapter['canonical_member'], '/original_member/canonical_member')
    programme = _programme(adapter['canonical_member']['value'], '/original_member/canonical_member')
    _method(adapter['original_method_reference'], programme)
    _evidence(adapter['evidence'], '/original_member/evidence')
    authority = adapter['conserved_source_authority']
    if not isinstance(authority, list) or not authority: _fail('/original_member', 'Entire original source targets/Rulesets required')
    for item in authority: _source(item, '/original_member/conserved_source_authority')
    for load in programme.get('loads', []):
        if load.get('quantity') != 'hot_water_volume': continue
        if not any(_same(item['value'], load) for item in authority):
            _fail('/original_member/conserved_source_authority', 'Full original water load is missing')
        if not load.get('schedule_id') or not any(isinstance(item['value'], dict) and item['value'].get('id') == load['schedule_id'] for item in authority):
            _fail('/original_member/conserved_source_authority', 'Original full water Ruleset is missing', 'requires_binding')
    return programme


def _variant_record(original_member, selected_context, qualification, *, _incoming=False):
    """Shared source validator/constructor for compiler and locked runtime record."""
    p = _member(original_member); context = _selected_context(selected_context)
    key = {'parent_inventory_id': original_member['parent_inventory_id'],
           'parent_inventory_sha256': original_member['parent_inventory_sha256'],
           'member_program_id': p['id'], 'member_evidence_view': p['evidence_view'],
           'selected_method_context_id': context['selected_method_context_id']}
    _source(qualification, '/qualification'); q = qualification['value']
    _exact(q, ('qualification_id', 'qualification_scope', 'key', 'selected_method_context', 'canonical_member',
               'original_method_reference', 'conserved_source_authority', 'evidence'), '/qualification/value')
    _evidence(q['evidence'], '/qualification/evidence')
    if q['qualification_scope'] != FULL_SCOPE:
        _fail('/qualification', 'Pilot/unqualified proof is not full-slot authority', 'requires_binding')
    if (not _same(q['key'], key) or q['qualification_id'] != context['qualification_id'] or
            not _same(q['selected_method_context'], selected_context) or
            any(not _same(q[k], original_member[k]) for k in ('canonical_member', 'original_method_reference', 'conserved_source_authority'))):
        _fail('/qualification', 'Exact selected tuple and entire immutable original member/method/targets differ')
    method = original_member['original_method_reference']['value']
    original = (method['source_hoo_configuration_id'] == context['source_hoo_configuration_id'] and
                method['context_evidence_view'] == context['context_evidence_view'] and
                _same(method['method_consumed_context'], context['method_consumed_context']))
    if not original and p['evidence_view'] == context['context_evidence_view']:
        _fail('/selected_method_context', 'Changed same-view method context has no qualified adapter', 'requires_binding')
    adaptation = None if original else {
        'kind': 'qualified_crossview_method_context', 'original_member_evidence_view': p['evidence_view'],
        'selected_context_evidence_view': context['context_evidence_view'],
        'original_source_hoo_configuration_id': method['source_hoo_configuration_id'],
        'selected_source_hoo_configuration_id': context['source_hoo_configuration_id'],
        **{k: copy.deepcopy(original_member[k]) for k in ('original_method_reference', 'canonical_member', 'conserved_source_authority', 'evidence')},
        'qualification': copy.deepcopy(qualification)}
    result = {'key': key, 'canonical_member': copy.deepcopy(original_member['canonical_member']),
        'original_method_reference': copy.deepcopy(original_member['original_method_reference']),
        'selected_method_context': copy.deepcopy(selected_context),
        'context_relation': 'original_context' if original else 'qualified_crossview_context',
        'adaptation': adaptation, 'qualification': copy.deepcopy(qualification)}
    result['variant_id'] = 'variant-'+hashlib.sha256(canonical(result)).hexdigest()
    _typed(result, 'child_variant', '/child_variant')
    if not _incoming and not _qualified_exact_context(qualification):
        _fail('/qualification', 'Exact selected child full-slot tuple remains unqualified', 'requires_binding')
    return result


def resolve_child_variant(parent_inventory: dict, member: dict, selected_method_context_id: str,
                          recipe: dict, resources: ResourceSet) -> dict:
    """Select one permitted full tuple; never infer a member view/context variant."""
    validate_inventory(parent_inventory); programme = _member(member)
    payload = parent_inventory['payload']
    if (member['parent_inventory_id'] != payload['inventory_id'] or
            member['parent_inventory_sha256'] != parent_inventory['inventory_sha256'] or
            programme['building_type'] != payload['family'] or programme['template'] != payload['template']):
        _fail('/original_member', 'Member parent inventory identity/hash differs')
    for load in programme['loads']:
        if load.get('quantity') != 'hot_water_volume': continue
        roles = [r for r in payload['roles'] if r['source_service_id'] == load.get('service_id') and
                 programme['source_id'] in r['service_definition']['value'].get('beneficiary_program_ids', [])]
        physical_load = dict(load, scope='building_service')
        if (not roles or load.get('scope') != 'program_service' or
                not _same(physical_load, roles[0]['service_definition']['value']['load'])):
            _fail('/original_member', 'Entire original member water load differs from independently locked service authority')
        rules = roles[0]['schedule_authority']
        if rules['kind'] != 'canonical_ruleset' or not any(_same(rules['canonical_schedule'], original)
                for original in member['conserved_source_authority']):
            _fail('/original_member/conserved_source_authority', 'Original member Ruleset differs from independently locked source authority')
    key = {'parent_inventory_id': payload['inventory_id'], 'parent_inventory_sha256': parent_inventory['inventory_sha256'],
           'member_program_id': programme['id'], 'member_evidence_view': programme['evidence_view'],
           'selected_method_context_id': selected_method_context_id}
    entries = recipe.get('permitted_child_variants', [])
    if not isinstance(entries, list): _fail('/permitted_child_variants', 'Exact variant list required')
    for entry in entries:
        _exact(entry, ('variant_id', 'key'), '/permitted_child_variants')
        _typed(entry['variant_id'], 'id', '/permitted_child_variants/variant_id')
        schema = _load_schema('bundle', '1.2.0')
        _check_schema(entry['key'], schema['$defs']['child_variant']['properties']['key'], schema, '/permitted_child_variants/key')
    matches = [entry for entry in entries if _same(entry['key'], key)]
    if len(matches) != 1:
        _fail('/permitted_child_variants', 'Absent or ambiguous exact parent/member/own-view/selected-context tuple', 'requires_binding')
    entry = matches[0]; variant = _get(resources, 'physical-child-variant__'+entry['variant_id'])
    _typed(variant, 'child_variant', '/child_variant')
    if variant['variant_id'] != entry['variant_id'] or not _same(variant['key'], key):
        _fail('/child_variant', 'Loaded variant resource ID/full key differs')
    expected = _variant_record(member, variant['selected_method_context'], variant['qualification'])
    if not _same(expected, variant): _fail('/child_variant', 'Loaded variant hash/original source/adaptation differs')
    return copy.deepcopy(variant)


def _canonical_record(resources, kind, key):
    """Retain the complete verified artifact separately from upstream originals."""
    try:
        record = resources.get(kind, key)
    except GeneratorError as error:
        if error.code != 'missing_resource': raise
        raise GeneratorError('requires_binding','/execution_authority/'+key,'Canonical executable resource is missing') from error
    matches = [e for e in resources.manifest['resources'] if (e['kind'], e['key']) == (kind, key)]
    if len(matches) != 1: _fail('/execution_authority', 'Canonical manifest entry missing')
    return {'path': matches[0]['path'], 'sha256': matches[0]['sha256'], 'locator': '/', 'value': record}


def _qualified_execution_association(qualification):
    """Closed independent proof domain for native-to-executable association."""
    return False


def _direct_program_ids(params, building):
    return list(dict.fromkeys(i['program_id'] for i in params['instances']
        if i.get('owner_kind')=='program' and i.get('building_realization_id')==building))


def _execution_association(authority, realization, resources, direct_program_ids):
    selected = authority['method_qualification']['value']['selected_method_context']
    association = _get(resources, 'physical-execution-association__'+realization['selected_method_context_id'])
    _exact(association, ('selected_method_context', 'physical_service_records', 'child_program_records', 'evidence'), '/execution_association')
    _evidence(association['evidence'], '/execution_association/evidence')
    if not _same(association['selected_method_context'], selected):
        _fail('/execution_association/selected_method_context', 'Whole qualified selected context differs', 'operating_group_conflict')
    _selected_context(selected)
    for name in ('physical_service_records', 'child_program_records'):
        if not isinstance(association[name], list): _fail('/execution_association/'+name, 'Ordered executable array required')
        for item in association[name]:
            if name == 'child_program_records':
                _exact(item, ('variant_id', 'key', 'program_record'), '/execution_association/child_program_records')
                _typed(item['variant_id'], 'id', '/execution_association/variant_id')
                schema = _load_schema('bundle', '1.2.0')
                _check_schema(item['key'], schema['$defs']['child_variant']['properties']['key'], schema, '/execution_association/key')
                item = item['program_record']
            _source(item, '/execution_association/executable_record')
            if not isinstance(item['value'], dict):
                _fail('/execution_association/executable_record', 'Whole executable record object required')
    # Executable packaging is a separately qualified artifact, not an actual
    # native consumed input. Embedding it in native resources would recurse for
    # original_context recipes that retain their complete original method.
    qualification=_source(_get(resources,'physical-execution-qualification__'+realization['selected_method_context_id']),'/execution_qualification')
    q=qualification['value']
    _exact(q,('qualification_id','qualification_scope','selected_method_context','execution_association','standalone_program_records','evidence'),'/execution_qualification/value')
    _typed(q['qualification_id'],'id','/execution_qualification/qualification_id')
    _evidence(q['evidence'],'/execution_qualification/evidence')
    if q['qualification_scope']!=FULL_SCOPE:
        _fail('/execution_qualification/qualification_scope','Full native/executable association scope required','requires_binding')
    if not _same(q['selected_method_context'],selected):
        _fail('/execution_qualification/selected_method_context','Entire selected native context differs','operating_group_conflict')
    _source(q['execution_association'],'/execution_qualification/execution_association')
    original=_canonical_record(resources,'reference','physical-execution-association__'+realization['selected_method_context_id'])
    if not _same(q['execution_association'],original):
        _fail('/execution_qualification/execution_association','Whole qualified association value/path/hash/locator differs')
    records=q['standalone_program_records']
    if not isinstance(records,list):_fail('/execution_qualification/standalone_program_records','Ordered direct executable records required')
    ids=[]
    for i,record in enumerate(records):
        where='/execution_qualification/standalone_program_records/'+str(i)
        _source(record,where)
        value=record['value']
        if not isinstance(value,dict) or not isinstance(value.get('definition'),dict):_fail(where,'Whole canonical programme executable required')
        pid=_typed(value['definition'].get('id'),'id',where+'/definition/id')
        if pid in ids:_fail(where,'Ambiguous duplicate direct programme executable','requires_binding')
        ids.append(pid)
        if pid not in authority['method_qualification']['value']['program_ids']:
            _fail(where,'Eligible programme is absent from independent native qualification coverage')
        if not _same(record,_canonical_record(resources,'program',pid)):
            _fail(where,'Actual canonical executable value/path/hash/locator differs from qualified record')
    # The qualified source-order pool belongs to the immutable context; caller
    # selection/order does not change that context or add unselected actors.
    if any(pid not in ids for pid in direct_program_ids):
        _fail('/execution_qualification/standalone_program_records','Selected direct programme lacks a whole eligible executable record','requires_binding')
    if not _qualified_execution_association(qualification):
        _fail('/execution_qualification','Native-to-executable association is not independently qualified','requires_binding')
    return copy.deepcopy(association),copy.deepcopy(qualification)


def _original_executable(selected, original, allowed, path):
    if not isinstance(selected, dict) or not isinstance(selected.get('recipe'), dict):
        _fail(path, 'Whole executable record/recipe required')
    left, right = copy.deepcopy(selected), copy.deepcopy(original)
    for field in allowed:
        left['recipe'].pop(field, None); right['recipe'].pop(field, None)
    if not _same(left, right): _fail(path, 'Selected executable changed original record or annual authority')


def _executable_context(context, realization, clock, path):
    if (not isinstance(context, dict) or
            context.get('source_hoo_configuration_id') != realization['source_hoo_configuration_id'] or
            context.get('configuration_id') != realization['source_hoo_configuration_id'] or
            context.get('year') != clock['year'] or context.get('holidays') != clock.get('holidays', [])):
        _fail(path, 'Executable configuration/calendar differs from realization', 'operating_group_conflict')


def _resolve_exact_physical(instance, clock, realization, authority, association, resources):
    from .services import _resolve_physical_service_record
    sid = instance['source_service_id']; where = '/instances/'+instance['key']
    roles = [r for r in authority['inventory']['payload']['roles'] if r['role_id'] == instance['source_fixture_role_id']]
    if len(roles) != 1 or roles[0]['source_service_id'] != sid:
        _fail(where+'/source_fixture_role_id', 'Exact inventory role/SID differs', 'shared_service_conflict')
    role = roles[0]
    candidates = [r for r in association['physical_service_records'] if isinstance(r['value'].get('definition'), dict) and r['value']['definition'].get('id') == sid]
    if len(candidates) != 1: _fail(where+'/execution_association', 'One explicit physical executable required', 'requires_binding')
    selected = candidates[0]['value']; original = _canonical_record(resources, 'reference', 'physical-service__'+sid)
    _original_executable(selected, original['value'], {'configurations'}, where+'/execution_association')
    if not _same(selected['definition'], role['service_definition']['value']):
        _fail(where+'/source_service_id', 'Whole original service definition differs', 'shared_service_conflict')
    configurations = selected['recipe'].get('configurations')
    variant = configurations.get(realization['source_hoo_configuration_id']) if isinstance(configurations, dict) else None
    if not isinstance(variant, dict): _fail(where+'/execution_association', 'Selected physical configuration absent', 'requires_binding')
    _executable_context(variant.get('source_context'), realization, clock, where+'/source_context')
    schedule = role['schedule_authority']
    reference = schedule['canonical_schedule']['value'] if schedule['kind'] == 'canonical_ruleset' else schedule['compiled_ruleset']
    if not _same(variant.get('reference_source'), reference): _fail(where+'/reference_source', 'Original role Ruleset changed')
    if instance['inputs'].get('source_hoo_configuration_id') != realization['source_hoo_configuration_id']:
        _fail(where+'/inputs/source_hoo_configuration_id', 'Physical selected context differs', 'operating_group_conflict')
    if instance.get('operating_group') != realization['operating_group']:
        _fail(where+'/operating_group', 'Physical actual group differs', 'operating_group_conflict')
    try:
        resolved = _resolve_physical_service_record(instance, clock, selected)
    except GeneratorError as error:
        raise GeneratorError(error.code, where+error.path, error.message) from error
    return resolved, original


def _prepare_exact_instances(params, resources):
    """Private actual-record resolution seam for Task7; public1.2 stays closed."""
    from .programs import resolve_program
    realizations = {r['building_realization_id']: r for r in params['building_realizations'] if r['mode'] == 'exact_source_fixture_extents'}
    pairs = []; authorities = {}
    for instance in params['instances']:
        if instance.get('owner_kind') != 'program': continue
        record = resources.get('program', instance['program_id'])
        if (any(r['kind']=='original_source_components' for r in record['recipe'].get('required_service_sets',[])) and
                instance['inputs'].get('composition_basis_mode')!='source_reference_area_normalized'):
            _fail('/instances/'+instance['key']+'/composition_basis_mode','Exact parent requires original reference area','incompatible_source_composition')
        clock = params['calendar']; inputs = dict(instance['inputs'], year=clock['year'], holidays=clock.get('holidays', []))
        building = instance.get('building_realization_id')
        if building in realizations:
            recipe = resources.get('program', instance['program_id'])['recipe']
            authority = resolve_exact_authority(instance, realizations[building], recipe, resources)
            _execution_association(authority,realizations[building],resources,_direct_program_ids(params,building))
            authorities[building] = authority
        resolved = resolve_program(instance['program_id'], inputs, resources)
        pairs.append((instance, resolved))
    for instance in params['instances']:
        if instance.get('owner_kind') != 'physical_service': continue
        if instance.get('physical_binding_kind') == 'legacy_whole':
            from .services import resolve_physical_service
            pairs.append((instance, resolve_physical_service(instance, params['calendar'], resources)))
            continue
        if instance.get('physical_binding_kind') != 'exact_source_role': continue
        building = instance.get('building_realization_id'); realization = realizations.get(building)
        if realization is None: _fail('/instances/'+instance['key']+'/building_realization_id', 'Unknown realization', 'shared_service_conflict')
        authority = authorities.get(building)
        if authority is None:
            recipe = _get(resources, 'physical-service__'+instance['source_service_id'])['recipe']
            authority = resolve_exact_authority(instance, realization, recipe, resources); authorities[building] = authority
        association,_ = _execution_association(authority,realization,resources,_direct_program_ids(params,building))
        resolved, _ = _resolve_exact_physical(instance, params['calendar'], realization, authority, association, resources)
        pairs.append((instance, resolved))
    order = {i['key']: n for n, i in enumerate(params['instances'])}
    return sorted(pairs, key=lambda pair: order[pair[0]['key']])


def _without_owned_water(resolved):
    result = copy.deepcopy(resolved)
    result['slots'] = [s for s in result['slots'] if s['slot'] != 'hot_water_volume']
    water_ids={d['demand_id'] for d in result['demands'] if d['slot']=='hot_water_volume'}
    result['demands'] = [d for d in result['demands'] if d['slot'] != 'hot_water_volume']
    result['shared_services'] = [d for d in result['shared_services'] if d.get('demand_id') not in water_ids]
    result['inputs']['reference_channels'].pop('hot_water_volume', None)
    result['inputs']['reference_budgets'] = {k:v for k,v in result['inputs']['reference_budgets'].items() if v['quantity'] != 'hot_water_volume'}
    return result


def _requirement_roles(requirement, by_id):
    if requirement['kind'] != 'original_source_components': return list(requirement['expected_role_ids'])
    return [role for c in requirement['components'] for role in by_id[c['child_requirement_id']]['expected_role_ids']]


def _original_target(requirement, roles, clock):
    from .budgets import reference_budget
    from .calendar import evaluate_rules
    role = roles[0]; load = role['service_definition']['value']['load']
    if requirement is not None and requirement['kind'] == 'original_programme_demand': load = requirement['original_demand']['value']
    schedule = role['schedule_authority']
    rules = schedule['canonical_schedule']['value'] if schedule['kind'] == 'canonical_ruleset' else schedule['compiled_ruleset']
    values = evaluate_rules(rules, clock['year'], clock.get('holidays', []))['values']
    demand = {k: copy.deepcopy(load[k]) for k in ('quantity', 'value', 'unit', 'basis')}
    demand.update(fuel='water', host='building_service', evidence={'original_value': copy.deepcopy(load),
        'original_unit': load['unit'], 'locator': role['service_definition']['locator']+'/load'})
    return reference_budget(demand, values)


def prepare_exact_bindings(params: dict, resolved_instances: list[tuple[dict,dict]], resources: ResourceSet) -> dict:
    """Prove exact ordered ownership, original B/e/W and child variants before RNG."""
    from .owners import physical_identity
    from .source_compositions import _prepare_exact_parent
    if params.get('schema_version') != '1.2.0':
        return {'resolved_instances':resolved_instances,'source_allocations':[],'owners':[],'projections':[],'building_realizations':[]}
    pairs=copy.deepcopy(resolved_instances)
    exact=[r for r in params['building_realizations'] if r['mode']=='exact_source_fixture_extents']
    realizations={r['building_realization_id']:r for r in exact}
    if len(realizations)!=len(exact):_fail('/building_realizations','Duplicate realization','shared_service_conflict')
    if len({i['key'] for i,r in pairs})!=len(pairs):_fail('/instances','Duplicate instance key','shared_service_conflict')
    authorities={};associations={};execution_qualifications={};canonical_physical={};canonical_programs={};used=set()
    for instance,resolved in pairs:
        building=instance.get('building_realization_id')
        has_sets=bool(resolved.get('required_service_sets'))
        is_exact=instance.get('physical_binding_kind')=='exact_source_role'
        if not has_sets and not is_exact and building is None:continue
        if building not in realizations:
            _fail('/instances/'+instance['key']+'/building_realization_id','Exact requirement needs declared realization','requires_binding')
        if instance.get('owner_kind')=='program':
            original=_canonical_record(resources,'program',instance['program_id']);recipe=original['value']['recipe']
            canonical_programs.setdefault(building,{})[instance['program_id']]=original
        elif is_exact:recipe=_get(resources,'physical-service__'+instance['source_service_id'])['recipe']
        else:continue
        authority=resolve_exact_authority(instance,realizations[building],recipe,resources)
        if building in authorities and not _same(authorities[building],authority):_fail('/building_realizations/'+building,'Realization authorities disagree')
        authorities[building]=authority;used.add(building)
        associations[building],execution_qualifications[building]=_execution_association(
            authority,realizations[building],resources,_direct_program_ids(params,building))
        clock=authority['method_qualification']['value']['selected_method_context']['value']['method_consumed_context']['value']['calendar']
        if not _same(params['calendar'],clock):_fail('/calendar','Selected qualified calendar differs','operating_group_conflict')
        payload=authority['inventory']['payload']
        if any(resolved['source'].get(k)!=payload[v] for k,v in (('building_type','family'),('template','template'))):
            _fail('/instances/'+instance['key']+'/source','Resolved source family/template differs','shared_service_conflict')
        if instance.get('owner_kind')=='program':
            programme=original['value']['definition']
            if (resolved.get('program_id')!=instance['program_id'] or any(resolved['source'].get(k)!=programme.get(v) for k,v in (
                    ('source_id','source_id'),('building_type','building_type'),('template','template'),('evidence_view','evidence_view'))) or
                    not _same(resolved.get('required_service_sets'),recipe['required_service_sets'])):
                _fail('/instances/'+instance['key']+'/source','Resolved canonical programme identity/requirements differs')
            if any(not _same(_programme_requirement(r)['value'],programme) for r in recipe['required_service_sets']):
                _fail('/instances/'+instance['key']+'/definition','Canonical programme differs from independent requirement')
            expected_context=dict(copy.deepcopy(recipe['source_context']),year=params['calendar']['year'],holidays=params['calendar'].get('holidays',[]))
            if not _same(resolved['inputs']['source_context'],expected_context):
                _fail('/instances/'+instance['key']+'/source_context','Supplied resolved context differs from qualified actual executable')
            _executable_context(resolved['inputs']['source_context'],realizations[building],params['calendar'],'/instances/'+instance['key']+'/source_context')
    if set(realizations)!=used:_fail('/building_realizations','Unused realization declaration','requires_binding')
    owner_plans=[];physical={};identities=set();exact_sids=set();legacy_sids=set()
    for instance,resolved in pairs:
        if instance.get('physical_binding_kind')!='exact_source_role':
            if instance.get('owner_kind')=='physical_service':legacy_sids.add(instance['source_service_id'])
            continue
        building=instance['building_realization_id'];authority=authorities[building]
        role=next((r for r in authority['inventory']['payload']['roles'] if r['role_id']==instance['source_fixture_role_id']),None)
        where='/instances/'+instance['key']
        if role is None or role['source_service_id']!=instance['source_service_id']:_fail(where+'/source_fixture_role_id','Foreign role/SID','shared_service_conflict')
        key=(building,role['role_id']);identity=physical_identity(instance)
        if key in physical or identity in identities:_fail(where,'Duplicate role or scoped owner','shared_service_conflict')
        identities.add(identity);exact_sids.add(instance['source_service_id'])
        actual,original=_resolve_exact_physical(instance,params['calendar'],realizations[building],authority,associations[building],resources)
        if not _same(actual,resolved):_fail(where,'Resolved physical differs from selected executable','shared_service_conflict')
        extent=actual['shared_services'][0]['extent'];expected=role['consumed_extent']
        if extent['value']!=expected['value'] or extent['unit']!=expected['unit']:_fail(where+'/basis_bindings','Extent differs from original source','shared_service_conflict')
        if role['source_basis']=='floor_area' and any(instance['inputs'][a]!=role['geometry_operands'][b] for a,b in (
                ('fixture_floor_area_m2','floor_area_m2'),('fixture_space_multiplier','space_multiplier'))):
            _fail(where+'/inputs','Original area/space multiplier differs','shared_service_conflict')
        demands=actual['demands']
        if len(demands)!=1 or demands[0]['slot']!='hot_water_volume':_fail(where+'/demands','One physical water demand required')
        target=actual['inputs']['reference_budgets'][demands[0]['demand_id']];independent=_original_target(None,[role],params['calendar'])
        if any(not _same(target[k],independent[k]) for k in ('total','basis','unit','magnitude_unit','quantity','method','fuel','host')) or target['original_magnitude']['value']!=independent['original_magnitude']['value']:
            _fail(where+'/reference_target','Original physical source target differs')
        entry={'instance_key':instance['key'],'building_realization_id':building,'role':copy.deepcopy(role),
            'source_basis_target':copy.deepcopy(target),'extent':copy.deepcopy(expected),
            'whole_input_target':{'quantity':'hot_water_volume','total':target['total']*expected['value'],
                'unit':'m3','basis':'absolute','derivation':'source_basis_target_times_extent'}}
        _positive(entry['whole_input_target']['total'],where+'/whole_input_target',zero=True)
        physical[key]=entry;owner_plans.append(entry);canonical_physical.setdefault(building,{})[instance['source_service_id']]=original
    if legacy_sids & exact_sids:_fail('/instances','Legacy/exact same-SID scope ambiguous','shared_service_conflict')
    realization_order={building:i for i,building in enumerate(realizations)}
    owner_plans.sort(key=lambda e:(realization_order[e['building_realization_id']],e['role']['source_order']))
    expanded=[];allocations=[];projections=[];closures={};occupied={i['key'] for i,r in pairs}
    for instance,resolved in pairs:
        if instance.get('owner_kind')!='program':expanded.append((instance,resolved));continue
        requirements=resolved.get('required_service_sets',[])
        if not requirements:expanded.append((instance,resolved));continue
        building=instance['building_realization_id'];authority=authorities[building];by_id={r['requirement_id']:r for r in authority['source_requirements']}
        closure=[role for req in requirements for role in _requirement_roles(req,by_id)]
        if len(set(closure))!=len(closure):_fail('/instances/'+instance['key'],'Overlapping programme requirements','shared_service_conflict')
        prior=closures.setdefault(building,set())
        if prior.intersection(closure):_fail('/instances/'+instance['key'],'Independently requested sets overlap','shared_service_conflict')
        prior.update(closure)
        if any((building,role) not in physical for role in closure):_fail('/instances/'+instance['key']+'/required_service_sets','Missing explicit role owner','requires_binding')
        if any(r['kind']=='original_source_components' for r in requirements):
            allocation,children,child_projections,originals=_prepare_exact_parent(params,instance,resolved,authority,associations[building],resources,occupied)
            allocations.append(allocation);expanded.extend(children);projections.extend(child_projections)
            canonical_programs.setdefault(building,{}).update(originals)
        else:
            expanded.append((instance,_without_owned_water(resolved)))
            for req in requirements:
                projections.append({'instance_key':instance['key'],'building_realization_id':building,'requirement':req,'children':[]})
                roles=[physical[building,r]['role'] for r in req['expected_role_ids']]
                extent=math.fsum(r['consumed_extent']['value'] for r in roles) if req['kind']=='original_programme_demand' else 1
                bound=instance.get('basis_bindings',{}).get('extents',{}).get('floor_area')
                if bound is not None and (bound.get('value')!=extent or bound.get('unit')!='m2'):
                    _fail('/instances/'+instance['key']+'/basis_bindings','Caller area differs from exact programme extent','shared_service_conflict')
    for building,authority in authorities.items():
        for role in authority['inventory']['payload']['roles']:
            if (building,role['role_id']) in physical and closures.get(building) and role['role_id'] not in closures[building] and role['source_space'] is not None:
                _fail('/instances/'+physical[building,role['role_id']]['instance_key'],'Extra source-space role outside requested closure','shared_service_conflict')
    # Phase5 closes original component areas/targets before any sampler runs.
    for item in projections:
        building=item['building_realization_id']; req=item['requirement']
        by_id={r['requirement_id']:r for r in authorities[building]['source_requirements']}
        if req['kind']=='original_source_components':
            total=math.fsum(c['represented_area_m2'] for c in req['components'])
            for component in req['components']:
                child=by_id[component['child_requirement_id']]
                entries=[physical[building,r] for r in child['expected_role_ids']]
                area=math.fsum(e['extent']['value'] for e in entries)
                target=_original_target(child,[e['role'] for e in entries],params['calendar'])
                whole=math.fsum(e['whole_input_target']['total'] for e in entries)
                if (not math.isclose(area,component['represented_area_m2'],rel_tol=1e-12,abs_tol=1e-8) or
                        not math.isclose(whole,component['represented_area_m2']*target['total'],rel_tol=1e-12,abs_tol=1e-8) or
                        not math.isclose(component['original_weight'],component['represented_area_m2']/total,rel_tol=1e-12,abs_tol=1e-12)):
                    _fail('/instances/'+item['instance_key']+'/source_components','Original A/B/weight differs from child physical coverage')
        elif req['kind']=='original_programme_demand':
            entries=[physical[building,r] for r in req['expected_role_ids']]
            target=_original_target(req,[e['role'] for e in entries],params['calendar'])
            whole=math.fsum(e['whole_input_target']['total'] for e in entries)
            if not math.isclose(whole,target['total']*math.fsum(e['extent']['value'] for e in entries),rel_tol=1e-12,abs_tol=1e-8):
                _fail('/instances/'+item['instance_key']+'/required_service_sets','Original programme B differs from physical coverage')
    receipts=[]
    for building,realization in realizations.items():
        authority=authorities[building];key='physical-fixture-inventory__'+realization['inventory_id']
        entry=next(e for e in resources.manifest['resources'] if (e['kind'],e['key'])==('reference',key))
        native=authority['method_qualification']['value'];context=native['selected_method_context']['value']
        actual=next(r['inputs']['source_context'] for i,r in expanded if i.get('building_realization_id')==building)
        receipts.append(dict(copy.deepcopy(realization),inventory=copy.deepcopy(authority['inventory']['payload']),
            inventory_resource={'resource_set_id':resources.resource_set_id,'kind':'reference','key':key,'sha256':entry['sha256']},
            native_context={'source_hoo_configuration_id':realization['source_hoo_configuration_id'],'selected_method_context_id':realization['selected_method_context_id'],
                'qualification_id':context['qualification_id'],'source_context':copy.deepcopy(actual),'evidence':copy.deepcopy(native['evidence']),
                'execution_qualification':copy.deepcopy(execution_qualifications[building]),
                'execution_authority':{'method_qualification':copy.deepcopy(authority['method_qualification']),'execution_association':copy.deepcopy(associations[building]),
                    'canonical_physical_records':list(copy.deepcopy(canonical_physical.get(building,{})).values()),
                    'canonical_program_records':list(copy.deepcopy(canonical_programs.get(building,{})).values())}}))
    return {'resolved_instances':expanded,'source_allocations':allocations,'owners':owner_plans,'projections':projections,
        'building_realizations':receipts,'authorities':authorities}


def bind_exact_projections(bundle: dict, plan: dict) -> None:
    """Attach B/e/W receipts and non-owning references to actual emitted bindings."""
    from .budgets import bind_budget
    owners={c['instance_key']:c for c in bundle['constituents']};bindings=bundle['bindings'];physical={}
    for entry in plan['owners']:
        key=entry['instance_key'];owner=owners.get(key);where='/constituents/'+key
        if owner is None:_fail(where,'Actual physical owner missing','invalid_reference')
        role=entry['role'];building=entry['building_realization_id']
        if (owner.get('building_realization_id')!=building or owner.get('source_fixture_role_id')!=role['role_id'] or
                owner.get('source_service_id')!=role['source_service_id']):_fail(where,'Physical identity differs','shared_service_conflict')
        indices=[i for i in owner['binding_indices'] if type(i) is int and 0<=i<len(bindings) and bindings[i].get('kind')=='load' and bindings[i].get('slot')=='hot_water_volume']
        if len(indices)!=1:_fail(where+'/binding_indices','One actual owned water binding required','invalid_reference')
        index=indices[0];b=bindings[index]
        for field in ('instance_key','building_realization_id','source_service_id','physical_id','physical_binding_kind','source_fixture_role_id'):
            if b.get(field)!=owner.get(field):_fail(where+'/binding_indices','Binding identifies another physical owner','invalid_reference')
        if b.get('demand_id')!=role['source_service_id'] or owner['schedule_ids'].get('hot_water_volume')!=b.get('schedule_id'):
            _fail(where+'/binding_indices','Owned demand/slot/schedule differs','invalid_reference')
        if not _same(b['reference_target'],entry['source_basis_target']):_fail(where+'/reference_target','Generated B changed')
        sid=b['schedule_id'];actual=bind_budget(entry['source_basis_target'],bundle['schedules'][sid]['values'])
        if any(not _same(actual[k],b[k]) for k in ('effective_magnitude','scaling_receipt')):_fail(where+'/effective_magnitude','Magnitude does not fit emitted fractions')
        owner['shared_services'][0].update(source_basis_target=copy.deepcopy(entry['source_basis_target']),extent=copy.deepcopy(entry['extent']),whole_input_target=copy.deepcopy(entry['whole_input_target']))
        reference={k:copy.deepcopy(b[k]) for k in ('instance_key','building_realization_id','physical_id','source_service_id','demand_id','slot','schedule_id')};reference['binding_index']=index
        physical[building,role['role_id']]={'reference':reference,'entry':entry}
    for owner in owners.values():
        if owner.get('owner_kind')!='physical_service':owner['service_set_projections']=[]
    by_projection={}
    for item in plan['projections']:
        key=item['instance_key'];owner=owners.get(key);req=item['requirement'];building=item['building_realization_id']
        if owner is None:_fail('/constituents/'+key,'Actual programme/parent missing','invalid_reference')
        if (any(d.get('slot')=='hot_water_volume' for d in owner['demands']) or 'hot_water_volume' in owner['schedule_ids'] or
                any(s.get('slot')=='hot_water_volume' for s in owner['slots'])):_fail('/constituents/'+key,'Projection programme owns duplicate water','shared_service_conflict')
        authority=plan['authorities'][building];by_id={r['requirement_id']:r for r in authority['source_requirements']}
        role_ids=_requirement_roles(req,by_id);entries=[physical[building,r] for r in role_ids]
        whole=math.fsum(e['entry']['whole_input_target']['total'] for e in entries);components=[]
        if req['kind']=='original_service_reference':
            denominator={'value':1,'unit':'1','evidence':req['evidence']};total=whole;kind='source_reference_inputs';target_kind='derived_input_component_sum';unit='m3';basis='absolute'
        elif req['kind']=='original_programme_demand':
            extent=math.fsum(e['entry']['extent']['value'] for e in entries)
            original=_original_target(req,[e['entry']['role'] for e in entries],bundle['metadata']['calendar'])
            if not math.isclose(whole,original['total']*extent,rel_tol=1e-12,abs_tol=1e-8):_fail('/projections/'+key,'Original programme integral/physical W differs')
            denominator={'value':extent,'unit':'m2','evidence':req['evidence']};total=original['total'];kind='programme_density';target_kind='canonical_programme_density';unit='m3/m2';basis='floor_area'
        else:
            areas=[c['represented_area_m2'] for c in req['components']];extent=math.fsum(areas);terms=[]
            for c,child in zip(req['components'],item['children']):
                child_key=child['instance']['key'];child_owner=owners[child_key]
                projection_index,cp=by_projection[child_key,c['child_requirement_id']]
                if not math.isclose(c['original_weight'],c['represented_area_m2']/extent,rel_tol=1e-12,abs_tol=1e-12):_fail('/source_composition/weights','Original weight differs from area ratio','incompatible_source_composition')
                target=_original_target(child['requirement'],[physical[building,r]['entry']['role'] for r in child['requirement']['expected_role_ids']],bundle['metadata']['calendar'])
                w=c['represented_area_m2']*target['total'];terms.append(w)
                if not math.isclose(cp['denominator']['value'],c['represented_area_m2'],rel_tol=1e-12,abs_tol=1e-8) or not math.isclose(cp['whole_input_target']['total'],w,rel_tol=1e-12,abs_tol=1e-8):_fail('/source_composition/components','Child physical W differs from original A times B')
                components.append({'component_index':c['component_index'],'member_program_id':c['member_program_id'],'member_instance_key':child_key,
                    'child_requirement_id':c['child_requirement_id'],'child_projection_index':projection_index,'represented_area_m2':c['represented_area_m2'],
                    'whole_input_target':copy.deepcopy(cp['whole_input_target']),'selected_child_variant':copy.deepcopy(child['variant'])})
                child_owner['generation'].update(method_variant=copy.deepcopy(child['variant']),operating_group=child['instance']['operating_group'])
            expected=math.fsum(terms)
            if not math.isclose(whole,expected,rel_tol=1e-12,abs_tol=1e-8):_fail('/source_composition/whole_input_target','Parent W differs from original component integrals')
            denominator={'value':extent,'unit':'m2','evidence':req['evidence']};total=expected/extent;kind='source_components_density';target_kind='derived_source_components_density';unit='m3/m2';basis='floor_area'
        projection={'projection_kind':kind,'requirement_id':req['requirement_id'],'programme_instance_key':key,'building_realization_id':building,
            'inventory_id':req['inventory_id'],'inventory_sha256':req['inventory_sha256'],'role_ids':role_ids,
            'members':[{'role_id':r,'physical':copy.deepcopy(physical[building,r]['reference'])} for r in role_ids],'components':components,
            'denominator':copy.deepcopy(denominator),'projected_target':{'target_kind':target_kind,'quantity':'hot_water_volume','total':total,'unit':unit,'basis':basis},
            'whole_input_target':{'quantity':'hot_water_volume','total':whole,'unit':'m3','basis':'absolute','derivation':'sum_unique_physical_whole_input_targets'},'interpretation':req['interpretation']}
        by_projection[key,req['requirement_id']]=(len(owner['service_set_projections']),projection)
        owner['required_service_sets']=copy.deepcopy(owner.get('required_service_sets',[req]));owner['service_set_projections'].append(projection)
    bundle['metadata']['building_realizations']=copy.deepcopy(plan['building_realizations'])
