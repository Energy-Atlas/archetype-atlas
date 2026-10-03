"""Independently compare normalized tables with locked source records.

This is source-input comparison, not a simulated-model/scorecard benchmark.
"""
import argparse
import math
import csv
import re
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
    option_indices = {}
    for sid, table in [('resstock', 'residential_options'), ('comstock', 'commercial_options')]:
        path = Path(raw_root)/sid/'resources/options_lookup.tsv'
        lines = path.read_text(encoding='utf-8').splitlines()
        parameter = option = None
        indexed = {}
        for number, line in enumerate(lines, 1):
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            cols = line.split('\t')
            if len(cols) < 3:
                continue
            if cols[0]:
                parameter, option = cols[:2]
            elif cols[1]:
                option = cols[1]
            args = dict(c.split('=', 1) for c in cols[3:] if '=' in c)
            indexed[number] = (parameter, option, cols[2], args)
        option_indices[sid] = indexed
        for row in data[table]:
            number = int(re.match(r'line (\d+)', provenance[row['provenance_id']]['locator']).group(1))
            parameter, option, measure, args = indexed[number]
            for field, expected in [('parameter', parameter), ('option', option), ('measure', measure), ('arguments', args)]:
                same(row[field], expected, row['id']+'/'+field)
    if data.get('residential_archetypes'):
        selection = load_json(ROOT/'sources/selection.json')
        with (Path(raw_root)/'resstock'/selection['residential_fixture']).open(encoding='utf-8', newline='') as f:
            fixture = {row['Building']: row for row in csv.DictReader(f)}
        parameters = {p for p, _, _, _ in option_indices['resstock'].values()}
        option_lines = {o['id']: int(re.match(r'line (\d+)', provenance[o['provenance_id']]['locator']).group(1))
                        for o in data['residential_options']}
        known = {(p, o) for p, o, _, _ in option_indices['resstock'].values()}
        for row in data['residential_archetypes']:
            raw = fixture[row['source_building_id']]
            selected = {k: v for k, v in raw.items() if k in parameters}
            same(row['selected_options'], selected, row['id']+'/selected_options')
            expected_lines = {n for n, (p, o, measure, args) in option_indices['resstock'].items()
                              if selected.get(p) == o and measure and args}
            same({option_lines.get(oid) for oid in row['option_ids']}, expected_lines, row['id']+'/option_bindings')
            argument_pairs = {(p, o) for n, (p, o, _, _) in option_indices['resstock'].items() if n in expected_lines}
            same({(o['parameter'], o['option']) for o in row['unresolved_options']},
                 set(selected.items())-known, row['id']+'/unresolved_options')
            same({(o['parameter'], o['option']) for o in row['non_argument_options']},
                 (set(selected.items()) & known)-argument_pairs, row['id']+'/non_argument_options')
            same(row['occupants'], float(raw['Occupants']), row['id']+'/occupants')
            for output, source in [('heating_base_C', 'Heating Setpoint'), ('cooling_base_C', 'Cooling Setpoint')]:
                same(row[output], (float(raw[source][:-1])-32)*5/9, row['id']+'/'+output)
            for key, value in row['source_context'].items():
                same(value, raw[key], row['id']+'/context/'+key)
    for row in data.get('specialized_rules', []):
        if row['rule_type'] == 'prototype_generator_source':
            file = files[provenance[row['provenance_id']]['source_file_id']]
            text = (Path(raw_root)/file['source_id']/file['path']).read_text(encoding='utf-8')
            same(row['source_attributes'], {'source_path': file['path'], 'generator_source': text}, row['id']+'/source_attributes')
        else:
            same(row['source_attributes'], raw_record(row), row['id']+'/source_attributes')
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
