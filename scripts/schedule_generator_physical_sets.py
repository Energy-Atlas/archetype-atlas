"""Compile locked exact-source water extraction adapters without qualification.

The separate census and method extraction artifacts retain their complete
upstream SourceObjects. No caller aliases, positive-only filtering, or native
pilot receipts define the source inventory. See the approved Task2 adapter table.
"""
import copy
import hashlib

from atlas_schedules.canonical import canonical
from atlas_schedules import physical_sets as authority


SOURCE_KEYS = ('inventory_id', 'family', 'template', 'evidence_view', 'geometry',
               'ordered_fixture_roles', 'programmes', 'compositions', 'method_references', 'evidence')


def _adapter(source_records):
    authority._exact(source_records, SOURCE_KEYS, '/source_records')
    authority._source(source_records['geometry'], '/source_records/geometry')
    authority._evidence(source_records['evidence'], '/source_records/evidence')
    for field in ('ordered_fixture_roles', 'programmes', 'compositions', 'method_references'):
        if not isinstance(source_records[field], list): authority._fail('/source_records/'+field, 'Ordered source list required')
    for field in ('programmes', 'compositions', 'method_references'):
        for record in source_records[field]:
            authority._source(record, '/source_records/'+field)
            if not isinstance(record['value'], dict): authority._fail('/source_records/'+field, 'Entire original object/derived method record required')


def compile_exact_inventory(source_records: dict) -> dict:
    """Compile complete ordered roles independently of programmes/positivity."""
    _adapter(source_records)
    schema = authority._load_schema('bundle', '1.2.0')
    role_keys = set(schema['$defs']['role']['required']) - {'consumed_extent'}
    roles = copy.deepcopy(source_records['ordered_fixture_roles'])
    for i, role in enumerate(roles):
        path = '/ordered_fixture_roles/'+str(i)
        authority._exact(role, role_keys, path)
        # Validate all source role primitives before doing operand arithmetic.
        candidate = dict(role, consumed_extent={'value': 1, 'unit': '1', 'evidence': role['evidence']})
        authority._typed(candidate, 'role', path)
        role['consumed_extent'] = authority._extent(role, path)
    payload = {k: copy.deepcopy(source_records[k]) for k in
               ('inventory_id', 'family', 'template', 'evidence_view', 'geometry', 'evidence')}
    payload['roles'] = roles
    inventory = {'inventory_sha256': hashlib.sha256(canonical(payload)).hexdigest(), 'payload': payload}
    return authority.validate_inventory(inventory)


def compile_exact_requirements(source_records: dict, inventory: dict) -> list[dict]:
    """Extract demand/reference/component union from entire original sources."""
    _adapter(source_records)
    if not authority._same(compile_exact_inventory(source_records), inventory):
        authority._fail('/inventory', 'Inventory differs from the complete locked extraction adapter')
    payload = inventory['payload']; programmes, methods, compositions = {}, {}, {}
    for i, obj in enumerate(source_records['programmes']):
        value = authority._programme(obj['value'], '/programmes/'+str(i)); pid = value.get('id')
        if not pid or pid in programmes: authority._fail('/programmes', 'Unique exact original programme identity required')
        if value.get('building_type') != payload['family'] or value.get('template') != payload['template']:
            authority._fail('/programmes', 'Programme family/template differs from inventory')
        programmes[pid] = obj
    for obj in source_records['method_references']:
        pid = obj['value'].get('program_id')
        authority._typed(pid, 'id', '/method_references/program_id')
        if pid not in programmes or pid in methods: authority._fail('/method_references', 'Missing/duplicate exact original member method')
        authority._method(obj, programmes[pid]['value']); methods[pid] = obj
    for i, obj in enumerate(source_records['compositions']):
        value = authority._composition(obj['value'], '/compositions/'+str(i))
        cid = value['id']
        if not cid or cid in compositions: authority._fail('/compositions', 'Unique entire original composition required')
        compositions[cid] = obj
    services = {}
    for role in payload['roles']: services[role['source_service_id']] = role['service_definition']

    def common(pid, kind, original_index):
        method = methods.get(pid)
        if method is None: authority._fail('/method_references/'+pid, 'Original water programme method is missing', 'requires_binding')
        identity = [payload['inventory_id'], pid, kind, original_index]
        return {'requirement_id': 'exact-requirement-'+hashlib.sha256(canonical(identity)).hexdigest(),
            'kind': kind, 'required': True, 'source_channel': 'hot_water_volume',
            'inventory_id': payload['inventory_id'], 'inventory_sha256': inventory['inventory_sha256'],
            'family': payload['family'], 'template': payload['template'],
            'source_hoo_configuration_id': method['value']['source_hoo_configuration_id'],
            'evidence': copy.deepcopy(source_records['evidence'])}

    leaves, ordered = {}, {pid: [] for pid in programmes}
    for pid, programme in programmes.items():
        p = programme['value']; occupied = set()
        if not isinstance(p.get('loads'), list) or not isinstance(p.get('service_ids'), list):
            authority._fail('/programmes/'+pid, 'Entire original loads and service relation required')
        for i, load in enumerate(p['loads']):
            if load.get('quantity') != 'hot_water_volume' or 'source_components' in load: continue
            sid = load.get('service_id')
            if sid not in services: authority._fail('/programmes/'+pid, 'Water load has no independently compiled service roles', 'requires_binding')
            if sid in occupied: authority._fail('/programmes/'+pid, 'Duplicate original water channel/SID')
            occupied.add(sid)
            roles = [r['role_id'] for r in payload['roles'] if r['source_service_id'] == sid and
                     p.get('source_id') in r['service_definition']['value'].get('beneficiary_program_ids', [])]
            r = dict(common(pid, 'original_programme_demand', i), programme=copy.deepcopy(programme),
                original_demand=authority.nested_source(programme, '/loads/'+str(i), load),
                service_definition=copy.deepcopy(services[sid]), source_service_id=sid, source_beneficiary_id=p.get('source_id'),
                expected_role_ids=roles, interpretation='canonical_density_partition')
            ordered[pid].append(r); leaves.setdefault(pid, []).append(r)
        for i, sid in enumerate(p['service_ids']):
            if sid in occupied: continue
            if sid not in services: authority._fail('/programmes/'+pid, 'Original service reference has no independent inventory', 'requires_binding')
            occupied.add(sid)
            roles = [r['role_id'] for r in payload['roles'] if r['source_service_id'] == sid and
                     p.get('source_id') in r['service_definition']['value'].get('beneficiary_program_ids', [])]
            ordered[pid].append(dict(common(pid, 'original_service_reference', i), programme=copy.deepcopy(programme),
                original_service_relation=authority.nested_source(programme, '/service_ids', p['service_ids']),
                service_definition=copy.deepcopy(services[sid]), source_service_id=sid, source_beneficiary_id=p.get('source_id'),
                expected_role_ids=roles, interpretation='conserved_original_input_components'))
    for pid, programme in programmes.items():
        p = programme['value']
        for i, load in enumerate(p['loads']):
            if load.get('quantity') != 'hot_water_volume' or 'source_components' not in load: continue
            composition = compositions.get(p.get('composition_id'))
            if composition is None: authority._fail('/compositions', 'Original component composition is missing', 'requires_binding')
            original = authority.nested_source(programme, '/loads/'+str(i), load); components = []
            for j, component in enumerate(load['source_components']):
                member_id = component.get('program_id'); candidates = [r for r in leaves.get(member_id, [])
                    if authority._same(r['original_demand']['value'], component.get('load'))]
                if len(candidates) != 1:
                    authority._fail('/source_components', 'Original component needs one exact independent demand leaf', 'requires_binding')
                child = candidates[0]; member = child['programme']['value']
                matches = [m for m in composition['value']['members'] if m.get('program_id') == member_id]
                if len(matches) != 1: authority._fail('/source_components', 'Exact original composition membership is missing/ambiguous')
                cm = matches[0]
                components.append({'component_index': j, 'member_program_id': member_id,
                    'member_evidence_view': member['evidence_view'], 'member_source_id': member['source_id'],
                    'represented_area_m2': cm.get('represented_area_m2'), 'original_weight': cm.get('weight'),
                    'original_component': authority.nested_source(original, '/source_components/'+str(j), component),
                    'child_requirement_id': child['requirement_id'], 'original_method_reference': copy.deepcopy(methods[member_id])})
            ordered[pid].append(dict(common(pid, 'original_source_components', i), parent_programme=copy.deepcopy(programme),
                original_mixed_demand=original, composition=copy.deepcopy(composition), components=components,
                interpretation='canonical_component_integral_projection'))
    requirements = [r for pid in programmes for r in ordered[pid]]
    return authority.validate_requirements(requirements, inventory)


def compile_child_variant(original_member: dict, selected_context: dict, qualification: dict) -> dict:
    """Compile only an exactly qualified selected tuple, retaining original view."""
    return authority._variant_record(original_member, selected_context, qualification)
