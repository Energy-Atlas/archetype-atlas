"""Before/after report of generator 3.0.0 (ADR 0047; plan section 8, B10).

python -m scripts.generator_3_0_0_report

Writes `docs/validation/generator-3-0-0-before-after.json` and `.md`. The 2.x figures need no
old code: generator 2.x held each load's annual total at `source value × Σ original shape`
and fitted the amplitude to the generated shape, so both follow from the same recipes.
- Commercial: every 10th commercial recipe, seeds 42 and 51 (the O15 catalogue scan's seeds);
  per load the 3.0 / 2.x annual ratio and the peak over the installed rating in each.
- Shared water: every service variant at seed 42.
- Apartment units: the 90.1-2007 Midrise and Highrise programmes in Hickory NC (4A), 80 m²,
  1 to 4 residents, 25 units each; per-unit electricity, gas and hot water against the 2.x
  prototype densities (release 2.0.0 `generator.json`) on the 2.x schedule table, read from
  `BASE` with git because B7 removed the schedules only the prototype recipes used.
"""
import json
import math
import subprocess
from pathlib import Path

import numpy as np

from atlas_schedules import generate, programmes
from atlas_schedules.budgets import ANNUAL_UNITS, annual_target
from atlas_schedules.calendar import evaluate_rules
from scripts.common import ROOT

DATA = ROOT/'atlas_schedules/data'
OUTPUT = ROOT/'docs/validation/generator-3-0-0-before-after'
RELEASE = ROOT/'data/atlas-releases/v2.0.0/commercial'
LOCATION = {'state': 'NC', 'latitude': 35.741, 'longitude': -81.389, 'utc_offset': -5, 'climate_zone': '4A'}
APARTMENTS = {'90.1-2007 Midrise': ('program-1bff8c83069c349972223cbf', '90-1-2007/midrise-apartment'),
              '90.1-2007 Highrise': ('program-60b1063b9fe00c5c29654bb9', '90-1-2007/highrise-apartment')}
UNITS_PER_CASE = 25
BASE = 'origin/main'
AREA = 80.0


def quantiles(values):
    values = np.asarray(values, dtype=float)
    return {'n': int(values.size), 'p05': float(np.quantile(values, 0.05)), 'median': float(np.median(values)),
            'p95': float(np.quantile(values, 0.95)), 'max': float(values.max())}


def binding_rows(owner, bundle, before_totals):
    rows = []
    for load, before in zip(owner['loads'], before_totals):
        shape = np.asarray(bundle['schedules'][owner['schedules'][load['slot']]]['values'])
        seconds = ANNUAL_UNITS[load['unit']][1]
        if before <= 0 or shape.sum() == 0:
            continue
        fitted = before / (shape.sum() * seconds)
        rows.append({'slot': load['slot'], 'ratio': load['annual_total'] / before,
                     'peak_before': fitted * shape.max() / load['amplitude'], 'peak_after': float(shape.max())})
    return rows


def commercial():
    rows = {}
    paths = [p for p in sorted((DATA/'recipes').glob('*.json'))
             if json.loads(p.read_text(encoding='utf-8'))['kind'] == 'commercial'][::10]
    for path in paths:
        recipe = programmes.load_recipe(path.stem)
        if recipe['required_services'] or not recipe['demands']:
            continue
        before = programmes.annual_targets(recipe)
        for seed in (42, 51):
            bundle = generate({'schema_version': '3.0.0', 'seed': seed, 'instances': [
                {'key': 'p', 'program_id': path.stem, 'operating_group': 'g'}]})
            for row in binding_rows(bundle['owners'][0], bundle, before):
                rows.setdefault(row['slot'], []).append(row)
    return rows


def services():
    rows = []
    table = programmes.schedules()
    for path in sorted((DATA/'services').glob('*.json')):
        service = json.loads(path.read_text(encoding='utf-8'))
        demand = service['demand']
        for configuration_id, configuration in service['configurations'].items():
            before = annual_target(demand['value'], demand['unit'], evaluate_rules(table[configuration['schedule']])[0])
            bundle = generate({'schema_version': '3.0.0', 'seed': 42, 'instances': [
                {'key': 'w', 'service_id': service['service_id'], 'configuration_id': configuration_id,
                 'physical_id': 'w', 'extent': {demand['basis']: 1.0}, 'operating_group': 'g'}]})
            rows += binding_rows(bundle['owners'][0], bundle, [before])
    return rows


def prototype_unit(folder, program_id):
    """2.x apartment unit at AREA m²: electricity kWh/yr and hot water m³/yr from the prototype densities."""
    recipes = json.loads((RELEASE/folder/'generator.json').read_text(encoding='utf-8'))
    recipe = next(v for views in recipes.values() for v in views.values() if v['program_id'] == program_id)
    table = json.loads(subprocess.run(['git', '-c', 'core.longpaths=true', 'show', f'{BASE}:atlas_schedules/data/schedules.json'],
                                      cwd=ROOT, check=True, capture_output=True).stdout)
    slots = {s['slot']: s['schedule'] for s in recipe['slots'] if s['schedule']}
    kwh = math.fsum(annual_target(d['value'], d['unit'], evaluate_rules(table[slots[d['slot']]])[0]) * AREA / 1000
                    for d in recipe['demands'])
    water = recipe['caller_water']
    m3 = annual_target(water['density'], water['density_unit'], evaluate_rules(table[water['schedule']])[0]) * AREA
    return kwh, m3


def apartments():
    out = {}
    for name, (program_id, folder) in APARTMENTS.items():
        before_kwh, before_m3 = prototype_unit(folder, program_id)
        units = [{'key': f'u{r}-{i}', 'program_id': program_id, 'extent': {'floor_area': AREA}, 'residents': r,
                  'location': LOCATION} for r in (1, 2, 3, 4) for i in range(UNITS_PER_CASE)]
        bundle = generate({'schema_version': '3.0.0', 'seed': 42, 'instances': units})
        owners = {o['key']: o for o in bundle['owners']}
        by_residents = {}
        for unit in units:
            owner = owners[unit['key']]
            electricity = math.fsum(l['annual_total'] for l in owner['loads'] if l['fuel'] == 'electricity') / 1000
            gas = math.fsum(l['annual_total'] for l in owner['loads'] if l['fuel'] != 'electricity') / 1000
            water = owners[unit['key'] + '/water']['loads'][0]['annual_total']
            row = by_residents.setdefault(unit['residents'], {'electricity_kwh': [], 'other_fuel_kwh': [], 'water_m3': []})
            row['electricity_kwh'].append(electricity)
            row['other_fuel_kwh'].append(gas)
            row['water_m3'].append(water)
        out[name] = {'before': {'electricity_kwh': before_kwh, 'other_fuel_kwh': 0.0, 'water_m3': before_m3},
                     'after': {str(r): {k: quantiles(v) for k, v in row.items()} for r, row in sorted(by_residents.items())}}
    return out


def markdown(report):
    lines = ['# Generator 3.0.0: before and after', '',
             'Written by `python -m scripts.generator_3_0_0_report` (ADR 0047). Generator 2.x held',
             'each load at `source value × Σ original shape` and fitted its amplitude; 3.0 binds the',
             'source value (commercial, shared water) or uses ResStock units (apartments).', '',
             '## Commercial loads (every 10th recipe, seeds 42 and 51)', '',
             '| Load | Loads | Annual 3.0 / 2.x, p05 / median / p95 | 2.x peak above rating | 2.x peak / rating, max |',
             '|---|---:|---|---:|---:|']
    for slot, row in report['commercial'].items():
        lines.append(f"| {slot} | {row['ratio']['n']} | {row['ratio']['p05']:.3f} / {row['ratio']['median']:.3f} / "
                     f"{row['ratio']['p95']:.3f} | {row['share_peak_before_above_rating']:.0%} | {row['peak_before']['max']:.2f} |")
    row = report['services']
    lines += ['', '## Shared hot-water services (every variant, seed 42)', '',
              f"{row['ratio']['n']} variants: annual volume 3.0 / 2.x {row['ratio']['p05']:.3f} / {row['ratio']['median']:.3f} / "
              f"{row['ratio']['p95']:.3f} (p05 / median / p95); the 2.x peak flow exceeded the source peak in "
              f"{row['share_peak_before_above_rating']:.0%} (max {row['peak_before']['max']:.2f}×). In 3.0 the peak is the source "
              'peak × the schedule maximum.', '',
              f'## Apartment units (Hickory NC, 4A, {AREA:.0f} m², {UNITS_PER_CASE} units per resident count, seed 42)', '',
              '| Programme | Residents | Electricity kWh/yr, p05 / median / p95 | Other fuels kWh/yr, median | Hot water m³/yr, median |',
              '|---|---|---|---:|---:|']
    for name, case in report['apartments'].items():
        before = case['before']
        lines.append(f"| {name} | 2.x prototype | {before['electricity_kwh']:.0f} | 0 | {before['water_m3']:.1f} |")
        for residents, row in case['after'].items():
            e = row['electricity_kwh']
            lines.append(f"| {name} | {residents} | {e['p05']:.0f} / {e['median']:.0f} / {e['p95']:.0f} | "
                         f"{row['other_fuel_kwh']['median']:.0f} | {row['water_m3']['median']:.1f} |")
    lines += ['', 'The 2.x prototype figures are per unit regardless of residents; 2.x had no gas in units.', '']
    return '\n'.join(lines)


def main():
    rows = commercial()
    report = {'commercial': {slot: {'ratio': quantiles([r['ratio'] for r in items]),
                                    'peak_before': quantiles([r['peak_before'] for r in items]),
                                    'share_peak_before_above_rating': float(np.mean([r['peak_before'] > 1 for r in items]))}
                             for slot, items in sorted(rows.items())}}
    water = services()
    report['services'] = {'ratio': quantiles([r['ratio'] for r in water]),
                          'peak_before': quantiles([r['peak_before'] for r in water]),
                          'share_peak_before_above_rating': float(np.mean([r['peak_before'] > 1 for r in water]))}
    report['apartments'] = apartments()
    OUTPUT.with_suffix('.json').write_bytes((json.dumps(report, indent=1, sort_keys=True) + '\n').encode('utf-8'))
    OUTPUT.with_suffix('.md').write_bytes(markdown(report).encode('utf-8'))
    print(f'wrote {OUTPUT.relative_to(ROOT).as_posix()}.json and .md')


if __name__ == '__main__':
    main()
