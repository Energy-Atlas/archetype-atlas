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


def validate_inventory(inventory):
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
            if not _qualified_recovered_bridge(role):
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


def _variant_record(original_member, selected_context, qualification):
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
    if not _qualified_exact_context(qualification):
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
