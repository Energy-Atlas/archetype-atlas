"""Prepare exact progressive family scope/locks from immutable source operands."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import zipfile

from atlas_schedules.canonical import canonical
from scripts.common import ROOT


def prepare_residential_family():
    read = lambda name: json.loads((ROOT/name).read_text(encoding='utf-8'))
    original = read('sources/schedule-generator-m1-scope.json')
    lock = read('sources/schedule-generator-lock.json')
    definitions = read('data/definition-releases/v0.1.1/programs.json')
    cases = [copy.deepcopy(c) for c in original['cases'] if c['template'] == 'ResStock SDR source fixture']
    seen = {c['program_id'] for c in cases}
    def freeze_file(name):
        data = (ROOT/name).read_bytes()
        lock['frozen_files'][name] = {'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data)}
        return hashlib.sha256(data).hexdigest()
    for index, program in enumerate(definitions):
        if program['template'] != 'ResStock SDR source fixture' or program['id'] in seen:
            continue
        file = f"data/resolution-releases/v0.4.0/profiles/{program['source_id']}.json"
        metadata = read(file)['metadata']
        weather = {k: metadata['weather'][k] for k in
                   ('station_filename','archive_member','sha256','variant','original_path')}
        weather['provenance_pointer'] = '/metadata/weather'
        cases.append({'case_id': 'R1-'+program['id'], 'program_id': program['id'],
            'building_type': program['building_type'], 'name': program['name'],
            'template': program['template'], 'vintage': metadata['selected_options']['Vintage'],
            'evidence_view': program['evidence_view'], 'configuration_id': program['source_id'],
            'program_definition': {'file': 'data/definition-releases/v0.1.1/programs.json',
                'json_pointer': '/'+str(index), 'sha256': original['cases'][0]['program_definition']['sha256'],
                'original_unit': 'versioned JSON record', 'transformation': 'Exact record reference; no merged views'},
            'required_slot_resolution': original['cases'][0]['required_slot_resolution'],
            'configuration': {'file': file, 'json_pointer': '/metadata', 'sha256': freeze_file(file),
                'original_unit': 'source metadata and input strings',
                'transformation': 'Use exact recovered inputs; override only reference seed under native unit allocation'},
            'climate': program['climate'], 'weather': weather, 'source_gate_status': 'passed'})
    scope = {'schema_version': '1.0.0', 'milestone_id': 'R1', 'scope_version': '1.0.0',
        'calendar': original['calendar'], 'cases': cases,
        'commercial_sampling_gate': original['commercial_sampling_gate'],
        'source_order_policy': 'Retain six original residential M1 cases in original order, then remaining actual definition order; no reorder of an existing request. New ordered requests have native coupling and distinct unit seeds.',
        'source_gate_boundary': 'Exact original inputs/weather/physical targets; native branch certification required before shipment'}
    weather_source = next(a for a in lock['archives'] if a['source_id'] == 'tmy3-station-proxy')
    template = weather_source['members'][0]
    weather_source['members'] = []
    with zipfile.ZipFile(ROOT/'data/raw'/weather_source['cache_path']) as archive:
        for case in cases:
            weather = case['weather']
            key = weather['station_filename'].removesuffix('.epw')
            if any(e['key'] == key for e in weather_source['members']):
                continue
            data = archive.read(weather['archive_member'])
            if hashlib.sha256(data).hexdigest() != weather['sha256']:
                raise ValueError('Original fixture weather differs: '+case['program_id'])
            entry = copy.deepcopy(template)
            entry.update(path=weather['archive_member'], key=key, sha256=weather['sha256'], size_bytes=len(data))
            weather_source['members'].append(entry)
    lock['scope_cases'] = cases
    lock['required_resources'] = [r for r in lock['required_resources'] if r['kind'] != 'weather'] + [
        {'kind': 'weather', 'key': e['key']} for e in weather_source['members']]
    lock['milestone_id'] = 'R1'
    lock['scope_version'] = scope['scope_version']
    lock['blocked_families'] = [{'family': 'outside_R1', 'status': 'requires_binding',
        'reason': 'Commercial source occupancy carriers/aggregation, transforms and any original annual decomposition must be certified before their own shipment'}]
    scope_file = 'sources/schedule-generator-residential-scope.json'
    (ROOT/scope_file).write_bytes(canonical(scope))
    freeze_file(scope_file)
    for case in cases:
        freeze_file(case['configuration']['file'])
    (ROOT/'sources/schedule-generator-residential-lock.json').write_bytes(canonical(lock))
    return scope, lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-residential', action='store_true', required=True)
    parser.parse_args()
    scope, lock = prepare_residential_family()
    print(f"Prepared {len(scope['cases'])} exact residential fixtures; {len(next(a for a in lock['archives'] if a['source_id']=='tmy3-station-proxy')['members'])} station members")


if __name__ == '__main__':
    main()
