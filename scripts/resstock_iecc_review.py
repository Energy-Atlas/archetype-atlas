"""Evidence report: ResStock 2000s and 2010s dwellings against the IECC residential prototypes (plan R1).

python -m scripts.resstock_iecc_review [--check]

Writes docs/reviews/resstock-vs-iecc-residential.md from release 1.4.0. The families stay
separate (code prototypes vs sampled stock, plan O2): the report pairs each ResStock
dwelling built in the 2000s or 2010s with the code prototype nearest in type, climate,
foundation and appliance fuel, and tables what each gives. No value changes.
- Loads: annual electricity and gas per dwelling by group (ResStock filled values over
  their annual series; IECC source values over their rulesets on a 2006 calendar,
  weekdays Default, weekends Wknd where given), occupants, and hot water per day.
- Envelope: window U-factor and SHGC; infiltration as each source states it (ResStock
  annual-average natural ACH, IECC AirflowNetwork effective leakage area of the
  living zone). A common basis needs weather and is not attempted.
"""
import argparse
import datetime
import math
from collections import defaultdict

from scripts.common import ROOT

OUTPUT = ROOT/'docs/reviews/resstock-vs-iecc-residential.md'
RELEASE = '1.4.0'
VINTAGES = {'2000s': '2006', '2010s': '2012'}  # vintage: nearest IECC edition in force (agent decision)
CLIMATES = {'1A': '1A-warm-humid', '2A': '2A-warm-humid'}  # ResStock humid 1A/2A: the warm-humid locations
FOUNDATIONS = {'Slab': 'slab', 'Vented Crawlspace': 'crawlspace', 'Unvented Crawlspace': 'crawlspace',
               'Heated Basement': 'heatedbsmt', 'Unheated Basement': 'unheatedbsmt'}
TYPES = {'single-family-detached': 'single-family', 'single-family-attached': 'single-family',
         'multifamily-2-to-4': 'multifamily', 'multifamily-5-plus-low-rise': 'multifamily', 'midrise-apartment': 'multifamily'}
GROUPS = {'lighting': 'Interior lighting', 'exterior_lighting': 'Exterior and garage lighting',
          'electric_equipment': 'Electric equipment', 'gas_equipment': 'Gas equipment',
          'reference_design_adjustment': 'IECC adjustment'}
DAYS = [datetime.date(2006, 1, 1) + datetime.timedelta(d) for d in range(365)]


def full_load_hours(schedule):
    """Sum of the hourly fractions over one year."""
    if schedule['type'] == 'annual':
        return math.fsum(schedule['values']) * schedule.get('timestep_minutes', 60) / 60
    total = 0.0
    for day in DAYS:
        kind = 'Wknd' if day.weekday() >= 5 else 'Weekday'
        key = day.strftime('%m-%d')
        covering = [r for r in schedule['rules'] if r['start_date'] <= key <= r['end_date']]
        specific = [r for r in covering if kind in r['day_types'] or (kind == 'Weekday' and 'Wkdy' in r['day_types'])]
        default = [r for r in covering if 'Default' in r['day_types']]
        rule = (specific or default)[-1]
        values = rule['values']
        total += math.fsum(values) * 24 / len(values)
    return total


def annual(document, floor_area=None):
    """{group: kWh}, occupants and hot water (litres per day) of an exported program; W/m2 loads times the
    dwelling floor area the program records."""
    out, occupants, water = defaultdict(float), None, 0.0
    schedules = document['schedules']
    for load in [*document['loads'], *(l for s in document.get('shared_services') or [] for l in s.get('loads', []))]:
        hours = full_load_hours(schedules[load['schedule_id']]) if load.get('schedule_id') in schedules else 0.0
        kind = load['type']
        if kind == 'occupancy':
            occupants = load['value']
        elif kind == 'hot_water' or load.get('unit', '').startswith('m3/s'):
            water += load['value'] * hours * 3600 * 1000 / 365
        elif load.get('unit', '').startswith('W') and load.get('value'):
            fuel = load.get('fuel') or 'electricity'
            group = 'gas_equipment' if kind == 'gas_equipment' or (kind == 'electric_equipment' and fuel != 'electricity') else kind
            group = 'exterior_lighting' if group == 'lighting' and load.get('host') == 'garage' else group
            group = load['role'] if load.get('role') == 'reference_design_adjustment' else group
            scale = floor_area if load['unit'] == 'W/m2' else 1.0
            if scale is None:
                raise ValueError(f'{document["id"]}: a W/m2 load without a recorded floor area')
            out[group] += load['value'] * scale * hours / 1000
    for stage in document.get('water_heating') or []:
        draw = stage['draw']
        water += draw['value'] * full_load_hours(schedules[draw['schedule_id']]) * 3600 * 1000 / 365
    return dict(out), occupants, water


def windows(document):
    """Area-weighted window U-factor and SHGC of a construction export."""
    if document.get('kind') == 'source_model_construction':
        rows = [(w['area_m2'], document['assemblies'][w['assembly_id']]) for w in document['windows']]
        area = math.fsum(a for a, _ in rows)
        return (math.fsum(a*r['u_factor_W_m2_K'] for a, r in rows)/area, math.fsum(a*r['solar_heat_gain_coefficient'] for a, r in rows)/area)
    glazing = [m['properties'] for m in document['materials'].values() if 'shgc' in m.get('properties', {})]
    return (glazing[0]['u_W_m2_K'], glazing[0]['shgc']) if glazing else (None, None)


def infiltration(document):
    if document.get('kind') == 'source_model_construction':
        network = document['infiltration'].get('airflow_network')
        if network:
            leak = [c for c in network['components'] if c['name'].lower().startswith('zoneleak')]
            return f'ELA {math.fsum(c["effective_leakage_area_m2"] for c in leak)*1e4:.0f} cm² (living zone, AirflowNetwork)'
        ela = [r for r in document['infiltration'].get('effective_leakage_area') or [] if r.get('zone', 'living') == 'living']
        units = len({r.get('unit') for r in ela}) or 1
        total = math.fsum(r.get('effective_air_leakage_area_cm2', 0) or 0 for r in ela)/units
        return f'ELA {total:.0f} cm² per unit (living zone{"s" if units > 1 else ""})' if ela else 'as stated in the set'
    natural = document['infiltration'].get('natural_ach') or {}
    return f'{natural["value"]*3600:.3f} ACH (annual-average natural)' if natural.get('value') is not None else 'unknown'


def pairs(release):
    dwellings = release.dwellings
    ids = dwellings.program_ids()
    out = []
    for pid in ids:
        if not pid.startswith('resstock-sdr.'):
            continue
        stored = dwellings.stored(pid)
        if stored.get('vintage') not in VINTAGES:
            continue
        kind = pid.split('.')[1]
        context = stored.get('building_context', {})
        filled = release.program(pid, 'filled')
        fuels = {s['fuel'] for w in filled.get('water_heating') or [] for s in w['stages']}
        gas = 'natural gas' in fuels
        if kind == 'manufactured-home':
            section = 'multi-section' if stored.get('floor_area_bin', '') >= '1500' else 'single-section'
            iecc = next(p for p in ids if p.startswith(f'hud-code.{section}.'))
            out.append((pid, stored, filled, iecc, None, f'HUD Code {section}'))
            continue
        edition = VINTAGES[stored['vintage']]
        climate = CLIMATES.get(stored['climate'], stored['climate'])
        foundation = FOUNDATIONS.get(context.get('Geometry Foundation Type'), 'slab')
        fuel = 'gas-appliances' if gas else 'electric-appliances'
        iecc = next(p for p in ids if p.startswith(f'iecc-{edition}.{TYPES[kind]}.{fuel}.'))
        heating = 'gasfurnace' if gas else 'heatpump'
        out.append((pid, stored, filled, iecc, {'climate': climate, 'foundation': foundation, 'heating': heating},
                    f'IECC {edition} {TYPES[kind]}, {fuel}, {climate} {foundation} {heating}'))
    return out


def report(release):
    from scripts import prototype_dwellings
    dwellings = release.dwellings
    lines = ['# ResStock 2000s/2010s dwellings vs the IECC residential prototypes', '',
             'Evidence only (plan 2026-10-27 R1, from plan 2026-10-24 O2 option c). Generated by',
             '`python -m scripts.resstock_iecc_review` from release 1.4.0; the families stay separate and no value changes.',
             '', '## Method', '',
             '- **Pairs.** Each ResStock SDR dwelling of the 2000s or 2010s is paired with a code prototype:',
             '  - edition by vintage: 2000s with IECC 2006, 2010s with IECC 2012;',
             '  - type: detached and attached with single-family (the prototypes have no attached type); every',
             '    multifamily size with the 18-unit multifamily prototype; manufactured homes with the HUD Code home;',
             '  - climate: ResStock 1A and 2A with the warm-humid locations; foundation as ResStock states it;',
             '  - appliance fuel and heating: gas appliances and a gas furnace where the ResStock water heater burns',
             '    gas, else electric appliances and a heat pump.',
             '- **Annual energy.** Design level times the sum of the hourly schedule fractions over a year: ResStock',
             '  filled values over their annual series; IECC source values over their rulesets on a 2006 calendar',
             '  (weekdays the Default rule, weekends the Wknd rule where given).',
             '- **Hot water.** Peak flow times the schedule sum, in litres per day, at the fixtures (no temperature',
             '  mixing).',
             '- **Envelope.** Window U-factor and SHGC, and infiltration as each source states it. ResStock gives an',
             '  annual-average natural ACH; the IECC prototypes an effective leakage area. A common basis needs',
             '  weather and is not attempted.', '',
             '## Pairs', '', '| ResStock dwelling | Climate | Floor area (ft²) | Foundation | Prototype and context |',
             '| --- | --- | --- | --- | --- |']
    found = pairs(release)
    rows = []
    for pid, stored, filled, iecc, context, label in found:
        lines.append(f'| `{pid.split(".")[1]}.{pid.split(".")[2]}` | {stored["climate"]} | {stored.get("floor_area_bin")} '
                     f'| {stored.get("building_context", {}).get("Geometry Foundation Type")} | {label} |')
        if context:
            document = prototype_dwellings.document(dwellings, iecc, 'source', context)
        else:
            document = release.program(iecc, 'source')
        rows.append((pid, stored, filled, iecc, context, document))
    lines += ['', '## Loads per dwelling per year', '',
              '| ResStock dwelling | Source | Occupants | ' + ' | '.join(f'{g} (kWh)' for g in GROUPS.values()) + ' | Hot water (L/day) |',
              '| --- | --- | ---: | ' + ' | '.join('---:' for _ in GROUPS) + ' | ---: |']
    ratios = defaultdict(list)
    for pid, stored, filled, iecc, context, document in rows:
        short = f'`{pid.split(".")[2]}`'
        a, occ_a, w_a = annual(filled)
        areas = dwellings.stored(iecc).get('floor_area') or []
        b, occ_b, w_b = annual(document, areas[0]['conditioned_floor_area_m2'] if len(areas) == 1 else None)
        for name, (values, occ, water) in (('ResStock', (a, occ_a, w_a)), ('Prototype', (b, occ_b, w_b))):
            cells = ' | '.join(f'{values.get(g, 0.0):,.0f}' for g in GROUPS)
            lines.append(f'| {short if name == "ResStock" else ""} | {name} | {occ if occ is not None else "—"} | {cells} | {water:,.0f} |')
        for g in GROUPS:
            if b.get(g) and g != 'reference_design_adjustment' and len(filled['loads']) > 2:
                ratios[g].append(a.get(g, 0.0)/b[g])
        if w_b and len(filled['loads']) > 2:
            ratios['hot water'].append(w_a/w_b)
    lines += ['', '## Envelope', '', '| ResStock dwelling | Source | Window U (W/m²K) | Window SHGC | Infiltration |',
              '| --- | --- | ---: | ---: | --- |']
    for pid, stored, filled, iecc, context, document in rows:
        set_id = stored['construction_set_id']
        [key] = release.constructions.sets[set_id]['contexts']
        mine = release.construction(set_id, key, 'detailed')
        theirs_set = dwellings.stored(iecc)['construction_set_id']
        theirs_key = (f'{prototype_dwellings.slug(context["climate"])}.{context["foundation"]}' if context
                      else prototype_dwellings.slug(stored['climate']))
        try:
            theirs = release.construction(theirs_set, theirs_key, 'detailed')
        except (KeyError, StopIteration, ValueError):
            theirs = None
        for name, doc in (('ResStock', mine), ('Prototype', theirs)):
            if doc is None:
                lines.append(f'| | {name} | — | — | no context `{theirs_key}` |')
                continue
            u, shgc = windows(doc)
            lines.append(f'| {"`"+pid.split(".")[2]+"`" if name == "ResStock" else ""} | {name} | '
                         f'{"—" if u is None else f"{u:.2f}"} | {"—" if shgc is None else f"{shgc:.2f}"} | {infiltration(doc)} |')
    lines += ['', '## Findings', '']
    for g, values in ratios.items():
        if values:
            label = GROUPS.get(g, g.capitalize())
            lines.append(f'- **{label}:** ResStock over prototype ranges {min(values):.2f}–{max(values):.2f} '
                         f'(median {sorted(values)[len(values)//2]:.2f}) over {len(values)} pairs.')
    sparse = [pid.split('.')[2] for pid, _, filled, *_ in rows if len(filled['loads']) <= 2]
    if sparse:
        lines.append('- **Sparse ResStock records:** ' + ', '.join(f'`{s}`' for s in sparse) + (' carries' if len(sparse) == 1 else ' carry') + ' only one or two '
                     'recovered loads (the fixture gives the other end uses zero full-load hours); their totals are not '
                     'comparable.')
    lines += ['- **IECC adjustment:** `IECC_Adj` is the reference-design adjustment load (ADR 0041 R2), not an end use; '
              'it is tabled apart and left out of the ratios.',
              '- **Occupants:** ResStock samples occupants per dwelling; the prototypes fix them by bedrooms.',
              '- **Infiltration:** the two sources state different quantities; compare them only after converting',
              '  the leakage areas with weather (open question in the plan).', '',
              '## Open questions', '',
              '- Whether ResStock 2010s dwellings should pair with IECC 2009 or 2012 (code adoption varies by state).',
              '- A weather-based conversion of the prototype leakage areas to annual-average ACH for a like-for-like',
              '  infiltration comparison.', '']
    return '\n'.join(lines)


def main():
    from scripts.atlas_exports import Release
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = report(Release(release=RELEASE)).encode('utf-8')
    if args.check:
        if OUTPUT.read_bytes() != data:
            raise SystemExit(f'{OUTPUT.relative_to(ROOT)} does not reproduce; run python -m scripts.resstock_iecc_review')
        print('ResStock vs IECC review reproduces')
        return
    OUTPUT.write_bytes(data)
    print(f'Wrote {OUTPUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
