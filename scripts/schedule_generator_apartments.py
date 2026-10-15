"""Compile closed apartment source recipes from pinned original definitions.

This build-only module neither qualifies a native method nor routes generation.
"""
import copy
import hashlib
import json
import math
from collections import Counter

from atlas_schedules.budgets import reference_budget
from atlas_schedules.calendar import evaluate_rules
from atlas_schedules.canonical import canonical
from atlas_schedules.errors import GeneratorError
from scripts.common import ROOT
from scripts.schedule_generator_apartment_water import compile_apartment_water_requirement
from atlas_schedules.apartment_recipes import _water_evidence


CALENDAR = {'year': 2007, 'clock': 'local_standard_time', 'holidays': []}
ORDERED_PROGRAMME_IDS_SHA256 = '3c0d169db7dd01f6cf0ebd5ce1c5a77d991d5a1cf16891b36178d6167c6794f0'
SLOTS = {'occupancy': 'occupants', 'lighting': 'lighting_interior',
         'additional_lighting': 'additional_lighting',
         'electric_equipment': 'electric_equipment', 'gas_equipment': 'gas_equipment'}
CONTROL_SLOTS = {'activity_schedule_id': ('activity', 'W/person', 'activity'),
                 'heating_setpoint_schedule_id': ('heating_setpoint', 'C', 'temperature'),
                 'cooling_setpoint_schedule_id': ('cooling_setpoint', 'C', 'temperature')}
HELPERS = ('lib/openstudio-standards/standards/Standards.ServiceWaterHeating.rb',
           'lib/openstudio-standards/service_water_heating/create_water_use.rb')


def _fail(path, message, code='source_integrity'):
    raise GeneratorError(code, path, message)


def _same(left, right):
    return canonical(left) == canonical(right)


def _locked(path, sha):
    if not isinstance(path, str) or not path.startswith(('data/definition-releases/v0.1.1/',
                                                          'data/raw/openstudio-standards/',
                                                          'data/schedule-generator/apartment/')):
        _fail('/source_files', 'Original or reviewed timing source path required')
    data = (ROOT / path).read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        _fail('/source_files/' + path, 'Whole source SHA-256 differs')
    return data


def _object(path, sha, locator, value):
    return {'path': path, 'sha256': sha, 'locator': locator, 'value': copy.deepcopy(value)}


def _derived(name, value):
    # The canonical value is regenerated from verified originals. It is not a
    # qualification certificate or a claim that a generated file ships today.
    return _object('derived/apartment-a2/' + name + '.json',
                   hashlib.sha256(canonical(value)).hexdigest(), '/', value)


def _field(path, sha, locator, value, unit, transformation):
    return {'source_revision': 'c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907',
            'source_path': path, 'source_sha256': sha, 'locator': locator,
            'original_value': copy.deepcopy(value), 'original_unit': unit,
            'transformation': transformation, 'extraction_date': '2026-10-15',
            'interpretation_note': 'Original selected source field; source-only, no native fixture qualification'}


def _row(obj, locator):
    value = obj
    for token in locator.lstrip('/').split('/'):
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def _evidence_ids(value):
    if isinstance(value, dict):
        result = ([value['evidence_id']] if isinstance(value.get('evidence_id'), str) else [])
        for child in value.values():
            result.extend(_evidence_ids(child))
        return result
    if isinstance(value, list):
        return [eid for child in value for eid in _evidence_ids(child)]
    return []


def compile_apartment_sources(scope: dict) -> dict:
    """Verify exact source identities, then return complete original objects."""
    if (not isinstance(scope, dict) or scope.get('schema_version') != '1.0.0' or
            scope.get('method') != 'candidate_exact_apartment_source_recipes' or
            scope.get('qualification_state') != 'closed' or scope.get('calendar') != CALENDAR or
            len(scope.get('programmes', [])) != 84 or len(scope.get('locations', [])) != 37):
        _fail('/scope', 'Exact closed 84-programme, 37-location candidate scope required')
    if (any(not isinstance(row, dict) or not isinstance(row.get('id'), str)
            for row in scope['programmes']) or
            hashlib.sha256(canonical([row['id'] for row in scope['programmes']])).hexdigest()
            != ORDERED_PROGRAMME_IDS_SHA256):
        _fail('/programmes', 'Appendix A exact ordered programme inventory differs')
    expected = {'programs.json', 'schedules.json', 'services.json',
                'provenance.json', 'source_files.json'}
    if set(scope.get('source_files', {})) != expected:
        _fail('/source_files', 'Five locked original definition files required')
    arrays = {}
    for name, receipt in scope['source_files'].items():
        path = 'data/definition-releases/v0.1.1/' + name
        if receipt.get('path') != path:
            _fail('/source_files/' + name, 'Definition path differs')
        arrays[name] = json.loads(_locked(path, receipt['sha256']))
    index = {name: {v['id']: (i, v) for i, v in enumerate(values)}
             for name, values in arrays.items()}
    if any(len(index[name]) != len(arrays[name]) for name in arrays):
        _fail('/source_files', 'Duplicate original source identity')
    timing = scope.get('timing_domain', {})
    timing_lock = scope.get('timing_lock', {})
    if timing_lock.get('path') != 'sources/schedule-generator-apartment-timing-lock.json':
        _fail('/timing_lock', 'Reviewed A1 timing lock required')
    locked = (ROOT / timing_lock['path']).read_bytes()
    if hashlib.sha256(locked).hexdigest() != timing_lock.get('sha256'):
        _fail('/timing_lock', 'Reviewed A1 timing lock SHA differs')
    if json.loads(locked)['domain_artifact'] != timing:
        _fail('/timing_domain', 'A1 timing lock and candidate domain differ')
    if timing.get('path') != 'data/schedule-generator/apartment/timing-domain.json':
        _fail('/timing_domain', 'Reviewed A1 location source required')
    domain = json.loads(_locked(timing['path'], timing['sha256']))
    locations = domain['locations']
    projected = [{k: x[k] for k in ('location_id', 'state', 'latitude', 'longitude',
                                    'time_zone_utc_offset')} for x in locations]
    if not _same(projected, scope['locations']) or len({canonical(x) for x in projected}) != 37:
        _fail('/locations', 'Complete A1 tuples and source order must match')
    if (Counter(x['role'] for x in scope['programmes']) !=
            {'dwelling': 40, 'corridor': 28, 'support_office': 16} or
            Counter(x['view'] for x in scope['programmes']) != {'source': 42, 'reviewed': 42} or
            len({(x['family'], x['template']) for x in scope['programmes']}) != 8 or
            len({x['id'] for x in scope['programmes']}) != 84):
        _fail('/programmes', 'Exact candidate role/view/template identities required')
    programmes = {}; requirements = {}; schedules = {}; services = {}; evidence = {}; raw_rows = {}; raw_sources = {}
    helpers = []
    for path in HELPERS:
        full = 'data/raw/openstudio-standards/' + path
        # These two whole helper SHAs are pinned by the independent Core4 contract.
        sha = ('50f6c89f3e1371b198d33eb5acd6b25b81c0c4319fa261efc067ea511f6b1156'
               if path == HELPERS[0] else
               '6c506aeecc764d019ccc2d2bb1524560ab8130605b790f41bc9506f843d14e18')
        helpers.append(_object(full, sha, '/', _locked(full, sha).decode('utf-8')))
    for item in scope['programmes']:
        pid = item['id']
        if pid not in index['programs.json']:
            _fail('/programmes/' + pid, 'Unknown original programme ID')
        i, p = index['programs.json'][pid]
        role = ('dwelling' if p['name'].startswith('Apartment') else
                'corridor' if p['name'].startswith('Corridor') else 'support_office')
        if (item != {'id': pid, 'family': p['building_type'], 'template': p['template'],
                     'view': p['evidence_view'], 'role': role, 'name': p['name'],
                     'locator': '/' + str(i)} or
                p['building_type'] not in ('HighriseApartment', 'MidriseApartment')):
            _fail('/programmes/' + pid, 'Original identity/view/room or locator differs')
        obj = _object(scope['source_files']['programs.json']['path'],
                      scope['source_files']['programs.json']['sha256'], '/' + str(i), p)
        programmes[pid] = obj
        for load in p['loads']:
            if load['quantity'] not in (*SLOTS, 'hot_water_volume'):
                _fail('/programmes/' + pid + '/loads', 'Unmapped original load', 'requires_binding')
            if load['status'] == 'unknown' and load['value'] is not None:
                _fail('/programmes/' + pid + '/loads', 'Unknown magnitude must remain null')
            if load['status'] == 'known' and (type(load['value']) not in (int, float) or
                                               not math.isfinite(load['value']) or load['value'] < 0):
                _fail('/programmes/' + pid + '/loads', 'Finite nonnegative original magnitude required')
        for eid in set(p['evidence_ids']) | set(_evidence_ids(p)):
            if eid not in index['provenance.json']:
                _fail('/programmes/' + pid, 'Original field provenance missing')
            ei, ev = index['provenance.json'][eid]
            evidence[eid] = _object(scope['source_files']['provenance.json']['path'],
                                    scope['source_files']['provenance.json']['sha256'],
                                    '/' + str(ei), ev)
        for sid in [l['schedule_id'] for l in p['loads'] if l['schedule_id']] + [
                v['value'] for key, v in p['parameters'].items()
                if key in CONTROL_SLOTS and v['status'] == 'known']:
            if sid not in index['schedules.json']:
                _fail('/programmes/' + pid, 'Original rule object missing')
            si, rule = index['schedules.json'][sid]
            schedules[sid] = _object(scope['source_files']['schedules.json']['path'],
                                     scope['source_files']['schedules.json']['sha256'],
                                     '/' + str(si), rule)
            provenance_ids = ([rule['provenance_id']] if 'provenance_id' in rule else
                              rule.get('evidence_ids', []))
            if not provenance_ids:
                _fail('/source_objects/schedules/' + sid, 'Source rule provenance missing')
            for provenance_id in provenance_ids:
                if provenance_id not in index['provenance.json']:
                    _fail('/source_objects/schedules/' + sid, 'Source rule provenance missing')
                ei, ev = index['provenance.json'][provenance_id]
                evidence[provenance_id] = _object(scope['source_files']['provenance.json']['path'],
                                                  scope['source_files']['provenance.json']['sha256'],
                                                  '/' + str(ei), ev)
        ev = index['provenance.json'][p['loads'][0]['evidence_id']][1]
        fi, sourcefile = index['source_files.json'][ev['source_file_id']]
        raw_sources[sourcefile['id']] = _object(scope['source_files']['source_files.json']['path'],
                                                scope['source_files']['source_files.json']['sha256'],
                                                '/' + str(fi), sourcefile)
        rawpath = 'data/raw/openstudio-standards/' + sourcefile['path']
        raw = json.loads(_locked(rawpath, sourcefile['sha256']))
        row_locator = ev['locator'].rsplit('/', 1)[0]
        row = _object(rawpath, sourcefile['sha256'], row_locator, _row(raw, row_locator))
        raw_rows[pid] = row
        if role != 'dwelling':
            if p['service_ids']:
                _fail('/programmes/' + pid, 'Non-dwelling water path unexpected')
            continue
        if len(p['service_ids']) != 1:
            _fail('/programmes/' + pid, 'One source water SID required', 'requires_binding')
        sid = p['service_ids'][0]
        if sid not in index['services.json']:
            _fail('/programmes/' + pid, 'Original service absent')
        si, service = index['services.json'][sid]
        services[sid] = _object(scope['source_files']['services.json']['path'],
                                scope['source_files']['services.json']['sha256'],
                                '/' + str(si), service)
        water = next(l for l in p['loads'] if l['quantity'] == 'hot_water_volume')
        ruleset = schedules[water['schedule_id']]
        proof = _water_evidence(obj, services[sid], ruleset, row, helpers)
        requirements[pid] = compile_apartment_water_requirement(obj, services[sid], ruleset, proof)
    for entry in evidence.values():
        source_id = entry['value'].get('source_file_id')
        if source_id is None:
            continue
        if source_id not in index['source_files.json']:
            _fail('/source_objects/field_evidence', 'Referenced raw source file missing')
        fi, sourcefile = index['source_files.json'][source_id]
        raw_sources[source_id] = _object(scope['source_files']['source_files.json']['path'],
                                         scope['source_files']['source_files.json']['sha256'],
                                         '/' + str(fi), sourcefile)
    if len(schedules) != 90 or len(requirements) != 40 or len(services) != 20:
        _fail('/source_objects', 'Exact 90 rules, 40 requirements and 20 paths required')
    return {'programmes': programmes, 'requirements': requirements,
            'source_objects': {'schedules': schedules, 'services': services,
                               'field_evidence': evidence, 'raw_rows': raw_rows,
                               'raw_source_files': raw_sources,
                               'water_helpers': helpers}, 'locations': copy.deepcopy(locations)}


def compile_apartment_recipes(records: dict, scope: dict) -> dict:
    """Build unpublished (kind,key) programme resources from exact source objects."""
    if set(records) != {'programmes', 'requirements', 'source_objects', 'locations'}:
        _fail('/records', 'Exact compiled source result required')
    if not _same(records, compile_apartment_sources(scope)):
        _fail('/records', 'Compiled source objects differ from pinned originals')
    if list(records['programmes']) != [x['id'] for x in scope['programmes']]:
        _fail('/records/programmes', 'Programme order or identity differs')
    from atlas_schedules.apartment_recipes import compile_recipes
    result = compile_recipes(records, scope)
    for record in result.values():
        recipe=record['recipe']
        for demand in recipe['resolved']['demands']:
            values=evaluate_rules(recipe['reference_sources'][demand['slot']],2007,[])['values']
            reference_budget(demand,values)
    return result
