"""Structural, physical, referential, and provenance validation."""
import argparse
import datetime as dt
import math
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from scripts.common import ROOT, TABLES, UNITS, load_json, load_atlas
from scripts.semantics import DAY_TYPES, profile


def validate_atlas(data, contract_root=ROOT):
    errors = []
    contract_root = Path(contract_root)
    schema = load_json(contract_root/'schemas/atlas.schema.json')
    Draft202012Validator.check_schema(schema)
    for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data):
        errors.append(f'schema /{"/".join(map(str, e.absolute_path))}: {e.message}')
    if data.get('units') != UNITS:
        errors.append('units: canonical SI unit map does not match contract')
    # Structural errors must not prevent useful cross-table diagnostics.
    if any(not isinstance(data.get(t), list) for t in TABLES):
        return errors
    indices = {}
    for table in TABLES:
        index = {}
        for row in data[table]:
            if not isinstance(row, dict) or 'id' not in row:
                continue
            if row['id'] in index:
                errors.append(f'duplicate {table} primary key: {row["id"]}')
            index[row['id']] = row
        indices[table] = index
    expected = load_json(contract_root/'sources/selection.json')
    templates = {t['template'] for t in expected['templates']}
    buildings = set(expected['buildings'])
    if set(data.get('templates', [])) != templates or set(data.get('building_types', [])) != buildings:
        errors.append('template/building vocabulary differs from pinned selection')
    climate_names = set(data.get('climate_zone_sets', []))
    if climate_names != set(expected['climate_zone_sets']):
        errors.append('climate: vocabulary differs from pinned selection')
    lock = load_json(contract_root/'sources/lock.json')
    sources = {s['source_id']: s for s in lock['sources']}
    locked_files = {(r['source_id'], r['path']): r for r in lock['files']}
    if len(data['source_files']) != len(locked_files):
        errors.append('source lock: file count mismatch')
    for row in data['source_files']:
        entry = locked_files.get((row.get('source_id'), row.get('path')))
        source = sources.get(row.get('source_id'))
        if not entry or not source or any(row.get(k) != v for k, v in entry.items()) or any(
                row.get(k) != source[k] for k in ['version', 'project', 'repository', 'license_path']):
            errors.append(f'source lock: inconsistent metadata for {row.get("id")}')
    for table in TABLES:
        for row in data[table]:
            if not isinstance(row, dict):
                continue
            rid = row.get('id', '?')
            if 'template' in row and row['template'] not in templates:
                errors.append(f'template: unknown label in {rid}')
            if 'building_type' in row and row['building_type'] not in buildings:
                errors.append(f'mapping/building vocabulary: unknown label in {rid}')
            if row.get('climate_zone_set') is not None and row['climate_zone_set'] not in climate_names:
                errors.append(f'climate: unknown label in {rid}')
            if table not in {'provenance', 'source_files'}:
                prov = indices['provenance'].get(row.get('provenance_id'))
                if not prov or prov.get('table') != table or prov.get('record_id') != rid:
                    errors.append(f'orphan provenance for {table}/{rid}')
                elif set(prov.get('fields', {})) != set(row) - {'id', 'provenance_id'}:
                    errors.append(f'provenance field coverage incomplete for {rid}')
            for field, value in row.items():
                if field.endswith('_schedule_id') and value is not None:
                    schedule = indices['schedules'].get(value)
                    if schedule is None:
                        errors.append(f'orphan schedule {field} in {rid}')
                    else:
                        kind = 'temperature' if 'setpoint' in field else ('activity' if field == 'activity_schedule_id' else 'fraction')
                        if schedule.get('schedule_type') != kind:
                            errors.append(f'schedule role mismatch {field} in {rid}')
    for row in data['provenance']:
        if row.get('source_file_id') not in indices['source_files']:
            errors.append(f'orphan source file for provenance {row.get("id")}')
        if row.get('record_id') not in indices.get(row.get('table'), {}):
            errors.append(f'orphan provenance target {row.get("id")}')
    for row in data['mappings']:
        p = indices['programs'].get(row.get('program_id'))
        s = indices['systems'].get(row.get('system_id')) if row.get('system_id') is not None else None
        if p is None:
            errors.append(f'orphan mapping program {row.get("id")}')
        if row.get('system_id') is not None and s is None:
            errors.append(f'orphan mapping system {row.get("id")}')
        for ref in [p, s]:
            if ref and any(row.get(k) != ref.get(k) for k in ['building_type', 'template']):
                errors.append(f'mapping cross-building/template assignment {row.get("id")}')
    for s in data['schedules']:
        kind = s.get('schedule_type')
        expected_unit = {'fraction': 'dimensionless', 'temperature': 'C', 'activity': 'W/person'}.get(kind)
        if s.get('units') != expected_unit:
            errors.append(f'schedule units mismatch {s.get("id")}')
        for r in s.get('rules', []):
            values = r.get('values', [])
            if len(values) != (1 if r.get('type') == 'Constant' else 24):
                errors.append(f'schedule length/time-resolution mismatch {s.get("id")}')
            if not set(r.get('day_types', '').split('|')) <= DAY_TYPES:
                errors.append(f'schedule day selector invalid {s.get("id")}')
            for k in ['start_date', 'end_date']:
                try:
                    dt.datetime.fromisoformat(r[k])
                except (KeyError, TypeError, ValueError):
                    errors.append(f'schedule date invalid {s.get("id")}')
            if all(isinstance(v, (int, float)) for v in values):
                if kind == 'fraction' and any(not 0 <= v <= 1 for v in values):
                    errors.append(f'schedule bounds fraction outside [0,1] {s.get("id")}')
                if kind == 'temperature' and any(not -50 <= v <= 100 for v in values):
                    errors.append(f'schedule bounds temperature outside [-50,100] C {s.get("id")}')
                if kind == 'activity' and any(not 0 <= v <= 1000 for v in values):
                    errors.append(f'schedule bounds activity outside [0,1000] W/person {s.get("id")}')
    pairs = set()
    for p in data['programs']:
        pair = (p.get('heating_setpoint_schedule_id'), p.get('cooling_setpoint_schedule_id'))
        if None not in pair and pair not in pairs:
            pairs.add(pair)
            heat, cool = [indices['schedules'].get(s) for s in pair]
            if not heat or not cool:
                continue
            # Check every date and all concrete weekday/holiday/design-day types.
            violation = False
            day = dt.date(2000, 1, 1)
            for offset in range(366):
                md = (day + dt.timedelta(days=offset)).strftime('%m-%d')
                for typ in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Hol', 'WntrDsn', 'SmrDsn']:
                    try:
                        hp, cp = profile(heat['rules'], typ, md), profile(cool['rules'], typ, md)
                        if any(h > c + 1e-9 for h, c in zip(hp, cp)):
                            errors.append(f'deadband: heating above cooling for {p["id"]} {typ} {md}')
                            violation = True
                    except (ValueError, KeyError, TypeError):
                        errors.append(f'schedule coverage/profile invalid for {p["id"]} {typ} {md}')
                        violation = True
                    if violation:
                        break
                if violation:
                    break
    for r in data['efficiency_rules']:
        for metric, value in r.get('metrics', {}).items():
            fractional = {'minimum_annual_fuel_utilization_efficiency', 'minimum_thermal_efficiency',
                          'minimum_combustion_efficiency'}
            if isinstance(value, (int, float)) and metric in fractional and not 0 < value <= 1:
                errors.append(f'efficiency bounds invalid {r.get("id")}/{metric}')
        attrs = r.get('source_attributes', {})
        low, high = attrs.get('minimum_capacity'), attrs.get('maximum_capacity')
        if isinstance(low, (int, float)) and isinstance(high, (int, float)) and not 0 <= low <= high:
            errors.append(f'efficiency capacity interval invalid {r.get("id")}')
    def finite(value, path=''):
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(f'non-finite numeric value at {path}')
        elif isinstance(value, dict):
            for k, v in value.items():
                finite(v, f'{path}/{k}')
        elif isinstance(value, list):
            for i, v in enumerate(value):
                finite(v, f'{path}/{i}')
    finite(data)
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('path', nargs='?', type=Path, default=ROOT/'data/processed')
    args = p.parse_args()
    contract = args.path if (args.path/'schemas/atlas.schema.json').exists() else ROOT
    errors = validate_atlas(load_atlas(args.path), contract)
    if errors:
        print('\n'.join(errors[:50]))
        raise SystemExit(f'Validation failed: {len(errors)} errors')
    print('Atlas schema, physical, schedule, relationship and provenance checks passed')


if __name__ == '__main__':
    main()
