"""Exact RetailStripmall and LargeOffice source records for the physical-service 1.2 compiler.

Task P1 of the Retail/Office follow-up (docs/superpowers/plans/2026-10-16-retail-office-p0-preflight.md).
Every programme, composition, service and Ruleset is the entire frozen definition
object with its file SHA-256 and locator. Fixture roles come from the frozen
completion census (one role per physical fixture location), with source space
handles from the locked upstream geometry (Stripmall) or the census itself
(LargeOffice). Nothing here is native evidence or qualification: no method
references are compiled, parents keep their current boundary until the reviewed
reference-union kind exists, and unknown operands stay null.

    python -I scripts/schedule_generator_commercial_followup_sources.py --write
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from atlas_schedules.canonical import canonical  # noqa: E402
from atlas_schedules.errors import GeneratorError  # noqa: E402

FAMILIES = {'RetailStripmall': 'stripmall', 'LargeOffice': 'large-office'}
TEMPLATES = ('90.1-2007', '90.1-2013', '90.1-2019', 'DOE Ref 1980-2004', 'DOE Ref Pre-1980')
VIEWS = ('source', 'reviewed')
DEFINITIONS = 'data/definition-releases/v0.1.1/'
INPUTS = {'programs': DEFINITIONS+'programs.json', 'compositions': DEFINITIONS+'compositions.json',
          'services': DEFINITIONS+'services.json', 'schedules': DEFINITIONS+'schedules.json',
          'completion': 'data/completion-releases/v0.1.0/commercial-completion.json',
          'scope': 'data/schedule-generator/families/retail-office-scope.json',
          'stripmall_geometry': 'data/schedule-generator/stripmall/geometry/ASHRAERetailStripmall.osm'}
GEOMETRY_SHA256 = '614eabad49a412aa2967fbe121e4c5bbaa3b4af0788407d8cc3f6317bd155d31'
REVISIONS = {'programs': 'definition-release-v0.1.1', 'compositions': 'definition-release-v0.1.1',
             'services': 'definition-release-v0.1.1', 'schedules': 'definition-release-v0.1.1',
             'completion': 'openstudio-standards c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907 (completion-release-v0.1.0)',
             'stripmall_geometry': 'openstudio-standards c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907 data/geometry/ASHRAERetailStripmall.osm'}
EXTRACTION_DATE = '2026-10-17'
FIXTURE_BRANCHES = {'RetailStripmall': 'stripmall_individual_space_draw', 'LargeOffice': 'large_office_core_spaces'}


def _fail(path, message, code='source_integrity'):
    raise GeneratorError(code, '/commercial_followup'+path, message)


def load_inputs(root=ROOT):
    inputs = {}
    for name, path in INPUTS.items():
        raw = (Path(root)/path).read_bytes()
        inputs[name] = {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw), 'raw': raw}
    if inputs['stripmall_geometry']['sha256'] != GEOMETRY_SHA256:
        _fail('/geometry', 'Locked ASHRAERetailStripmall.osm bytes differ')
    for name in ('programs', 'compositions', 'services', 'schedules', 'completion', 'scope'):
        inputs[name]['value'] = json.loads(inputs[name]['raw'])
    return inputs


def _object(inputs, name, locator, value):
    return {'path': inputs[name]['path'], 'sha256': inputs[name]['sha256'], 'locator': locator, 'value': copy.deepcopy(value)}


def _evidence(inputs, name, locator, original, unit, transformation, note):
    return {'source_revision': REVISIONS[name], 'source_path': inputs[name]['path'], 'source_sha256': inputs[name]['sha256'],
            'locator': locator, 'original_value': copy.deepcopy(original), 'original_unit': unit,
            'transformation': transformation, 'extraction_date': EXTRACTION_DATE, 'interpretation_note': note}


def osm_spaces(raw):
    """OS:Space name -> source handle, from the locked upstream geometry file (bytes re-hashed here)."""
    if hashlib.sha256(raw).hexdigest() != GEOMETRY_SHA256:
        _fail('/geometry', 'Locked ASHRAERetailStripmall.osm bytes differ')
    spaces = {}
    for block in raw.decode('utf-8').replace('\r\n', '\n').split('\n\n'):
        if not block.lstrip().startswith('OS:Space,'): continue
        fields = [line.split('!-')[0].strip().rstrip(',;') for line in block.strip().splitlines()]
        handle, name = fields[1], fields[2]
        if not re.fullmatch(r'\{[0-9a-f-]{36}\}', handle) or not name or name in spaces:
            _fail('/geometry', 'Unexpected or repeated OS:Space identity: '+name)
        spaces[name] = handle
    return spaces


def _roles(inputs, family, template, services, completion, spaces):
    """Roles in frozen completion-census order (service draw path order, then fixture location order).

    This is the extraction's deterministic census order, not a claim about Ruby
    factory call order; native registration order is captured separately (S3/L2).
    """
    roles, census = [], []
    rows = {r['path_id']: (i, r) for i, r in enumerate(completion['draw_paths']) if r['building_type'] == family}
    missing = [s['id'] for _, s in services if s['path_id'] not in rows]
    if missing: _fail('/services/'+missing[0], 'No frozen completion census for service path')
    services = sorted(services, key=lambda item: rows[item[1]['path_id']][0])
    for sindex, service in services:
        if service['path_id'] not in rows: _fail('/services/'+service['id'], 'No frozen completion census for service path')
        cindex, row = rows[service['path_id']]
        load = service['load']
        planned = next(s for s in inputs['scope']['value']['services'] if s['service_id'] == service['id'])
        # Stripmall census rows carry no instance count; the scope appendix supplies it independently.
        if (row['template'] != template or row['source_branch'] != FIXTURE_BRANCHES[family] or
                row['beneficiary_program_ids'] != service['beneficiary_program_ids'] or
                row['rated_flow_m3_s'] != load['value'] or load['basis'] != 'absolute' or
                row.get('flow_instance_count', planned['flow_instance_count']) != len(row['physical_fixture_locations']) or
                planned['fixture_locations'] != row['physical_fixture_locations'] or
                planned['flow_instance_count'] != len(row['physical_fixture_locations'])):
            _fail('/services/'+service['id'], 'Completion census differs from the frozen absolute service')
        locations = row['physical_fixture_locations']
        instances = row.get('fixture_instances')
        if instances is not None and [f['name'] for f in instances] != locations:
            _fail('/services/'+service['id'], 'Census fixture instances differ from fixture locations')
        schedule = next(((i, s) for i, s in enumerate(inputs['schedules']['value']) if s['id'] == load['schedule_id']), None)
        if schedule is None: _fail('/services/'+service['id'], 'Original water Ruleset is missing')
        for position, location in enumerate(locations):
            if instances is not None:
                fixture = instances[position]; handle = fixture['handle']; zone_multiplier = fixture['multiplier']
                handle_evidence = _evidence(inputs, 'completion', f'/draw_paths/{cindex}/fixture_instances/{position}',
                    fixture, None, 'name, handle and zone multiplier copied unchanged',
                    'Source space and zone multiplier from the frozen completion census; floor area and space multiplier are not in the census and stay null.')
            else:
                if location not in spaces: _fail('/services/'+service['id'], 'Fixture location has no locked OS:Space: '+location)
                handle = spaces[location]; zone_multiplier = None
                handle_evidence = _evidence(inputs, 'stripmall_geometry', '#OS:Space/'+location, {'name': location, 'handle': handle},
                    None, 'OS:Space handle read from the locked upstream geometry',
                    'Source geometry handle, independent of handles regenerated by a native run; area and multipliers are not extracted here and stay null.')
            role = {'role_id': service['id']+'|'+location, 'source_order': len(roles), 'source_service_id': service['id'],
                    'source_path_id': service['path_id'], 'role_kind': 'source_space_fixture',
                    'service_definition': _object(inputs, 'services', '/'+str(sindex), service),
                    'source_space': {'name': location, 'handle': handle},
                    'geometry_operands': {'floor_area_m2': None, 'space_multiplier': None, 'zone_multiplier': zone_multiplier,
                                          'evidence': [handle_evidence]},
                    'source_basis': 'absolute',
                    'schedule_authority': {'kind': 'canonical_ruleset',
                                           'canonical_schedule': _object(inputs, 'schedules', '/'+str(schedule[0]), schedule[1])},
                    'evidence': [_evidence(inputs, 'completion', f'/draw_paths/{cindex}/physical_fixture_locations/{position}',
                        location, None, 'one role per listed physical fixture location',
                        'Whole absolute fixture: the original rate applies once per location, extent 1, never scaled by programme area.')]}
            roles.append(role)
            census.append({k: copy.deepcopy(role[k]) for k in ('role_id', 'source_order', 'source_service_id', 'source_path_id',
                                                               'role_kind', 'source_space', 'geometry_operands')})
    return roles, census


def extract_family_source_records(family, inputs=None):
    """Exact ordered source objects and per template/view SOURCE_KEYS records for one family."""
    if family not in FAMILIES: _fail('/family', 'Unsupported follow-up family', 'requires_binding')
    inputs = inputs or load_inputs()
    scope = inputs['scope']['value']
    expected_programmes = [p for p in scope['programmes'] if p['building_type'] == family]
    expected_compositions = [c for c in scope['compositions'] if c['building_type'] == family]
    expected_services = [s for s in scope['services'] if s['family'] == family]
    programmes = [(i, p) for i, p in enumerate(inputs['programs']['value']) if p.get('building_type') == family]
    if sorted(p['id'] for _, p in programmes) != sorted(p['id'] for p in expected_programmes):
        _fail('/programmes', 'Frozen programme census differs from the exact scope')
    by_id = {p['id']: p for _, p in programmes}
    for row in expected_programmes:
        p = by_id[row['id']]
        if (p['template'], p['evidence_view'], p.get('service_ids', [])) != (row['template'], row['evidence_view'], row['service_ids']):
            _fail('/programmes/'+row['id'], 'Programme template/view/service relation differs from scope')
    compositions = [(i, c) for i, c in enumerate(inputs['compositions']['value']) if c.get('building_type') == family]
    if sorted(c['id'] for _, c in compositions) != sorted(c['id'] for c in expected_compositions):
        _fail('/compositions', 'Frozen composition census differs from the exact scope')
    for row in expected_compositions:
        c = next(c for _, c in compositions if c['id'] == row['id'])
        if [m['program_id'] for m in c['members']] != row['members']:
            _fail('/compositions/'+row['id'], 'Composition member order differs from scope')
    # The appendix copy fixes membership and operands; roles follow the completion census order.
    services = [(i, s) for i, s in enumerate(inputs['services']['value']) if s.get('building_type') == family]
    if sorted(s['id'] for _, s in services) != sorted(s['service_id'] for s in expected_services):
        _fail('/services', 'Frozen service census differs from the exact scope')
    for row in expected_services:
        s = next(s for _, s in services if s['id'] == row['service_id'])
        if (s['template'], s['path_id'], s['load']['value']) != (row['template'], row['path_id'], row['canonical_flow_m3_s_per_fixture']):
            _fail('/services/'+row['service_id'], 'Service template/path/flow differs from scope')
    spaces = osm_spaces(inputs['stripmall_geometry']['raw']) if family == 'RetailStripmall' else {}
    configurations = []; census_values = {}
    for template in TEMPLATES:
        template_services = [(i, s) for i, s in services if s['template'] == template]
        roles, census = _roles(inputs, family, template, template_services, inputs['completion']['value'], spaces)
        for view in VIEWS:
            selected = [(i, p) for i, p in programmes if p['template'] == template and p['evidence_view'] == view]
            selected_ids = {p['id'] for _, p in selected}
            comps = [(i, c) for i, c in compositions if c['template'] == template and c['evidence_view'] == view]
            if any(m['program_id'] not in selected_ids for _, c in comps for m in c['members']):
                _fail('/compositions', 'Composition member outside its own template/view')
            inventory_id = f"{FAMILIES[family]}|{template}|{view}"
            configuration = {'template': template, 'evidence_view': view, 'inventory_id': inventory_id,
                             'programme_ids': [p['id'] for _, p in selected], 'composition_ids': [c['id'] for _, c in comps],
                             'service_ids': [s['id'] for _, s in template_services]}
            if not roles:
                configuration['source_records'] = None
                configuration['absence'] = {'status': 'no_frozen_service_path',
                    'interpretation': 'Exact-template source gate result: the frozen definitions list no water service path for this template; not a global zero-water assertion.'}
            else:
                if family == 'RetailStripmall':
                    source_geometry = _object(inputs, 'stripmall_geometry', '#OS:Space', {
                        'os_space_handles': spaces,
                        'derivation': 'Every OS:Space block of the locked file; field 1 (handle) and field 2 (name) read unchanged; no other field read.'})
                else:
                    rows = [(i, r) for i, r in enumerate(inputs['completion']['value']['draw_paths'])
                            if r['building_type'] == family and r['template'] == template]
                    source_geometry = _object(inputs, 'completion', f'/draw_paths/{rows[0][0]}/fixture_instances',
                                              rows[0][1]['fixture_instances'])
                geometry_value = {'source_geometry': source_geometry,
                                  'fixture_role_census': census,
                                  'evidence': [_evidence(inputs, 'completion', '/draw_paths', {'family': family, 'template': template},
                                               None, 'ordered census of every listed physical fixture location',
                                               'Independent of programmes, aliases and positivity; one role per fixture location in completion census order.')]}
                census_values[inventory_id] = geometry_value
                records = {'inventory_id': inventory_id, 'family': family, 'template': template, 'evidence_view': view,
                           'geometry': None,  # bound below to the census file's own SHA-256

                           'ordered_fixture_roles': copy.deepcopy(roles),
                           'programmes': [_object(inputs, 'programs', '/'+str(i), p) for i, p in selected],
                           'compositions': [_object(inputs, 'compositions', '/'+str(i), c) for i, c in comps],
                           'method_references': [],
                           'evidence': [_evidence(inputs, 'programs', '/', {'family': family, 'template': template, 'view': view},
                                        None, 'entire frozen objects selected by exact family/template/view',
                                        'Source records only: no native evidence, method qualification or shipment readiness.')]}
                configuration['source_records'] = records; configuration['absence'] = None
            configurations.append(configuration)
    census_path, census_blob = census_file(family, census_values)
    census_sha = hashlib.sha256(census_blob).hexdigest()
    for configuration in configurations:
        if configuration['source_records'] is not None:
            iid = configuration['inventory_id']
            configuration['source_records']['geometry'] = {'path': census_path, 'sha256': census_sha,
                                                           'locator': '/'+iid.replace('~', '~0').replace('/', '~1'),
                                                           'value': copy.deepcopy(census_values[iid])}
    used = [n for n in INPUTS if family == 'RetailStripmall' or n != 'stripmall_geometry']
    return {'schema_version': '1.0.0', 'family': family, 'extraction_date': EXTRACTION_DATE,
            'inputs': {name: {k: inputs[name][k] for k in ('path', 'sha256', 'size_bytes')} for name in used},
            'geometry_census': {'path': census_path, 'sha256': census_sha, 'size_bytes': len(census_blob)},
            'programme_ids': [p['id'] for _, p in programmes], 'composition_ids': [c['id'] for _, c in compositions],
            'service_ids': [s['id'] for _, s in services], 'load_status': load_status(family, inputs),
            'programmes': [_object(inputs, 'programs', '/'+str(i), p) for i, p in programmes],
            'compositions': [_object(inputs, 'compositions', '/'+str(i), c) for i, c in compositions],
            'configurations': configurations}


def census_file(family, census_values):
    """The separately written geometry/fixture census: one JSON object keyed by inventory ID."""
    path = 'data/schedule-generator/'+FAMILIES[family]+'/geometry-census.json'
    return path, (json.dumps(census_values, indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def load_status(family, inputs):
    """Known/unknown status per view and load quantity over every programme, parents included (not an absence ruling)."""
    counts = {}
    for p in inputs['programs']['value']:
        if p.get('building_type') != family: continue
        for load in p.get('loads', []):
            key = f"{p['evidence_view']}|{load.get('quantity')}|{load.get('status')}"
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def write_artifacts(root=ROOT):
    inputs = load_inputs(root); written = {}
    for family, slug in FAMILIES.items():
        artifact = extract_family_source_records(family, inputs)
        census_values = {c['inventory_id']: c['source_records']['geometry']['value']
                         for c in artifact['configurations'] if c['source_records'] is not None}
        census_path, census_blob = census_file(family, census_values)
        if hashlib.sha256(census_blob).hexdigest() != artifact['geometry_census']['sha256']: _fail('/geometry', 'Census bytes differ')
        (Path(root)/census_path).parent.mkdir(parents=True, exist_ok=True); (Path(root)/census_path).write_bytes(census_blob)
        blob = (json.dumps(artifact, indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')
        target = Path(root)/'data/schedule-generator'/slug/'source-inventory.json'
        target.write_bytes(blob)
        producer = (Path(root)/'scripts/schedule_generator_commercial_followup_sources.py').read_bytes()
        lock = {'schema_version': '1.0.0', 'family': family, 'producer': {
                    'path': 'scripts/schedule_generator_commercial_followup_sources.py',
                    'sha256': hashlib.sha256(producer).hexdigest(), 'size_bytes': len(producer)},
                'inputs': artifact['inputs'], 'geometry_census': artifact['geometry_census'],
                'artifact': {'path': target.relative_to(root).as_posix(), 'sha256': hashlib.sha256(blob).hexdigest(), 'size_bytes': len(blob)},
                'interpretation': 'Source-record extraction lock only; no native, method or shipment authority.'}
        lock_path = Path(root)/'sources'/f'schedule-generator-{slug}-lock.json'
        lock_path.write_bytes((json.dumps(lock, indent=1, sort_keys=True) + '\n').encode('utf-8'))
        written[family] = lock['artifact']
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--write', action='store_true', required=True)
    parser.parse_args(argv)
    print(json.dumps(write_artifacts(), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
