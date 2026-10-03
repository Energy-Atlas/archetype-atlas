"""Independently compare normalized tables with locked source records.

This is source-input comparison, not a simulated-model/scorecard benchmark.
"""
import argparse
import math
from pathlib import Path

from scripts.common import ROOT, dump_json, load_atlas, load_json
from scripts.fetch import verify_file

# Independent reference arithmetic: deliberately not imported from the builder.
REFERENCE_FIELDS = {
    'people_per_m2': ('occupancy_per_area', 1/92.90304),
    'lighting_W_m2': ('lighting_per_area', 1/0.09290304),
    'additional_lighting_W_m2': ('additional_lighting_per_area', 1/0.09290304),
    'electric_equipment_W_m2': ('electric_equipment_per_area', 1/0.09290304),
    'gas_equipment_W_m2': ('gas_equipment_per_area', 0.2930710701722222/0.09290304),
    'ventilation_m3_s_m2': ('ventilation_per_area', 0.0004719474432/0.09290304),
    'ventilation_m3_s_person': ('ventilation_per_person', 0.0004719474432),
    'ventilation_ach': ('ventilation_air_changes', 1),
}


def compare_sources(data, raw_root=ROOT/'data/raw'):
    lock = load_json(ROOT/'sources/lock.json')
    for e in lock['files']:
        verify_file(e, raw_root)
    files = {r['id']: r for r in data['source_files']}
    provenance = {r['id']: r for r in data['provenance']}
    systems = {r['id']: r for r in data['systems']}
    cache, errors, checks = {}, [], 0
    def raw_record(row):
        prov = provenance[row['provenance_id']]
        f = files[prov['source_file_id']]
        path = Path(raw_root)/f['source_id']/f['path']
        if path not in cache:
            cache[path] = load_json(path)
        raw = cache[path]
        for part in prov['locator'].strip('/').split('/'):
            raw = raw[int(part)] if isinstance(raw, list) else raw[part]
        return raw
    def same(actual, expected, label):
        nonlocal checks
        checks += 1
        equal = math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12) if (
            isinstance(actual, (int, float)) and isinstance(expected, (int, float))) else actual == expected
        if not equal:
            errors.append('Source comparison mismatch: ' + label)
    for row in data['programs']:
        raw = raw_record(row)
        same(row['source_attributes'], raw, row['id']+'/source_attributes')
        for output, (source, factor) in REFERENCE_FIELDS.items():
            value = raw.get(source)
            same(row[output], None if value is None else value*factor, row['id']+'/'+output)
    for row in data['envelope_components']:
        raw = raw_record(row)
        u = raw.get('assembly_maximum_u_value')
        same(row['u_W_m2_K'], None if u is None or u == 0 else u*5.678263341113487, row['id']+'/u')
        same(row['source_attributes'], raw, row['id']+'/source_attributes')
    for row in data['systems']:
        raw = raw_record(row)
        same(row['system_type'], raw['type'], row['id']+'/type')
        same(row['source_attributes'], {k: v for k, v in raw.items() if k != 'space_names'}, row['id']+'/source_attributes')
    for row in data['mappings']:
        if row['system_id'] is not None:
            names = set(raw_record(systems[row['system_id']]).get('space_names', []))
            same(set(row['source_space_names']) <= names, True, row['id']+'/system_assignment')
    for row in data['schedules']:
        prov = provenance[row['provenance_id']]
        f = files[prov['source_file_id']]
        raw = load_json(Path(raw_root)/f['source_id']/f['path'])['schedules'] if f['path'] not in cache else cache[f['path']]
        cache[f['path']] = raw
        matches = [(i, r) for i, r in enumerate(raw) if r['name'] == row['source_name']]
        same(len(row['rules']), len(matches), row['id']+'/rule_count')
        for actual, (index, expected) in zip(row['rules'], matches):
            for field in ['values', 'type', 'day_types', 'start_date', 'end_date']:
                same(actual[field], expected[field], row['id']+'/'+field)
            same(actual['source_index'], index, row['id']+'/source_index')
    return {'comparison_type': 'locked_source_inputs_and_hvac_map_membership',
            'simulation_or_external_scorecard_validated': False, 'checks': checks, 'errors': errors}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('path', nargs='?', type=Path, default=ROOT/'data/processed')
    p.add_argument('--report', type=Path, default=ROOT/'docs/validation/source-comparison.json')
    args = p.parse_args()
    report = compare_sources(load_atlas(args.path))
    dump_json(args.report, report)
    if report['errors']:
        raise SystemExit('\n'.join(report['errors'][:20]))
    print(f'Passed {report["checks"]} locked-source comparison checks')


if __name__ == '__main__':
    main()
