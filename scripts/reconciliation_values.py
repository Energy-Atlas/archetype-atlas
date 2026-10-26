"""Extract the DOE reference values that release 1.1.0 applies (ADR 0037).

python -m scripts.reconciliation_values --idf-root <extracted doe-reference/v1.4_7.2> --standards-root <ashrae_90_1 dir>
    [--out data/reconciliation/doe-reference-values-v1.json]

Reads the register (data/reconciliation/doe-reference-v1.json) and the Chicago (5A)
IDFs it pins, and writes the definition input that scripts.reconciliation_overlay
applies without the IDFs:
- source_files: one per IDF, located inside its pinned archive;
- evidence: one row per extracted value, in the definition provenance shape;
- schedules: the DOE Schedule:Compact objects the applications use, as hourly
  definition rulesets. Compact rules match first-to-last; atlas rules take the last
  matching specific rule, so each Through period's For lines are written in reverse,
  with AllOtherDays as its Default. Every conversion is checked over the full year,
  holidays and design days against the compact original;
- folders: per template and building type, the applications: program schedule slots,
  loads, heat fractions, humidity setpoints, window ratios and hot-water zero fills;
  hot-water gains; building services; infiltration; internal mass; building window
  ratios; the calendar.
Only register rows that replace, fill or add are applied; keep, leave and omit rows
change nothing.
"""
import argparse
import datetime as dt
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from scripts import idf_reader, idf_schedules, reference_extras, reference_loads
from scripts.common import ROOT, load_json
from scripts.definition_contract import stable_id
from scripts.reconciliation_register import REGISTER_PATH, TEMPLATES, zone_program_map

LOCK = ROOT/'sources/reference-models-lock.json'
EXTRACTION_DATE = '2026-10-25'
YEAR = '2014'  # the atlas rule calendar year
ALL_DAYS = 'Default|Mon|Tue|Wed|Thu|Fri|Sat|Sun|Hol|SmrDsn|WntrDsn'
TOKENS = {'weekdays': 'Wkdy', 'weekday': 'Wkdy', 'weekends': 'Wknd', 'weekend': 'Wknd', 'saturdays': 'Sat',
          'monday': 'Mon', 'tuesday': 'Tue', 'wednesday': 'Wed', 'thursday': 'Thu', 'friday': 'Fri',
          'saturday': 'Sat', 'sunday': 'Sun', 'holiday': 'Hol', 'holidays': 'Hol',
          'summerdesignday': 'SmrDsn', 'winterdesignday': 'WntrDsn', 'alldays': ALL_DAYS,
          'allotherdays': 'Default', 'customday1': None, 'customday2': None}
KINDS = {'fraction': ('fraction', 'dimensionless'), 'temperature': ('temperature', 'C'),
         'activity': ('activity', 'W/person'), 'humidity': ('humidity', '%')}
APPLIED = ('replace', 'fill', 'add')
SCHEDULE_CLASSES = ('A1-holidays', 'A3-upstream-edit', 'A3-vintage-variant', 'A3-no-atlas-counterpart',
                    'A4-assignment', 'A4-slot-assignment', 'A9-design-days', 'B1-hot-water-schedule')
UNITS = {'flow/exteriorarea': 'm3/s-m2 exterior surface', 'flow/exteriorwallarea': 'm3/s-m2 exterior wall',
         'flow/area': 'm3/s-m2 floor', 'flow/zone': 'm3/s', 'airchanges/hour': '1/h'}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Extract:
    """Source files, evidence and schedules shared by every folder."""

    def __init__(self):
        self.source_files, self.evidence, self.schedules = {}, {}, {}

    def source_file(self, path, idf_root, archive):
        relative = path.relative_to(idf_root).as_posix()
        row = {'source_id': 'doe-reference', 'project': 'DOE Commercial Reference Buildings', 'version': 'v1.4_7.2',
               'path': relative, 'archive_path': archive['path'], 'archive_sha256': archive['sha256'],
               'url': archive['url'], 'retrieval_date': load_json(LOCK)['retrieval_date'],
               'sha256': sha256(path), 'size_bytes': path.stat().st_size,
               'license_path': 'sources/licenses/doe-reference.txt'}
        key = stable_id('sourcefile', row)[:len('sourcefile-')+20]
        self.source_files[key] = {'id': key, **row}
        return key

    def cite(self, source_file, locator, value, unit, transformation, note):
        row = {'source_file_id': source_file, 'locator': locator, 'original_value': value, 'original_unit': unit,
               'transformation': transformation, 'extraction_date': EXTRACTION_DATE, 'interpretation': note}
        key = stable_id('evidence', row)
        self.evidence[key] = {'id': key, **row}
        return key

    def schedule(self, model, source_file, name, kind, days):
        fields = model.schedules().get(name.lower())
        if fields is None:
            raise ValueError(f'No Schedule:Compact {name} in {source_file}')
        rules = ruleset(fields)
        expected, _ = idf_schedules.evaluate_compact(fields, days)
        got = idf_schedules.evaluate_ruleset(rules, lambda r: r['values'] * (24 // len(r['values'])), days)
        bad = [k for k in days if not (expected[k] is None and got[k] is None) and not idf_schedules.same(expected[k], got[k])]
        if bad:
            raise ValueError(f'Converted {name} differs from its compact source on {bad[:3]}')
        evidence = self.cite(source_file, f'Schedule:Compact {fields[0]}', fields[1:], fields[1] or 'schedule type limits',
                             'compact For order to last-specific-wins rules; Until times to hourly energy-conserving means',
                             'DOE reference source schedule (ADR 0037); checked over the full year, holidays and design days.')
        schedule_type, units = KINDS[kind]
        content = {'source_name': fields[0], 'schedule_type': schedule_type, 'units': units, 'interpolation': 'none',
                   'time_resolution_minutes': 60, 'evidence_ids': [evidence], 'rules': rules}
        key = stable_id('schedule', content)
        self.schedules[key] = {'id': key, **content}
        return key


def ruleset(fields):
    """Definition rules for a Schedule:Compact, in atlas rule order."""
    rules, start = [], (1, 1)
    for (month, day), block in idf_schedules.compact_rules(fields):
        period = []
        for tokens, steps in block:
            names = [TOKENS[t] for t in tokens if TOKENS.get(t)]
            if not names:
                continue
            values = [round(v, 10) for v in idf_schedules.hourly_means(steps)]
            constant = len(set(values)) == 1
            period.append({'day_types': '|'.join(dict.fromkeys('|'.join(names).split('|'))),
                           'start_date': f'{YEAR}-{start[0]:02d}-{start[1]:02d}T00:00:00+00:00',
                           'end_date': f'{YEAR}-{month:02d}-{day:02d}T00:00:00+00:00',
                           'type': 'Constant' if constant else 'Hourly', 'values': values[:1] if constant else values})
        defaults = [r for r in period if r['day_types'] == 'Default']
        rules += defaults + [r for r in reversed(period) if r['day_types'] != 'Default']
        start = next_day(month, day)
    for i, rule in enumerate(rules):
        rule['source_index'] = i
    return rules


def next_day(month, day):
    d = dt.date(int(YEAR), month, 28 if (month, day) == (2, 29) else day) + dt.timedelta(days=1)
    return d.month, d.day


def register_rows(register, template, building_type):
    return [r for r in register['rows'] if r['template'] == template and r['building_type'] == building_type]


def program_schedules(extract, model, source_file, rows, zone_programs, floors, days):
    """{program: {slot: schedule id}} for the slots whose DOE schedule a register row replaces or fills."""
    named = {r['source_value']['object'].split(' ', 1)[1].lower() for r in rows
             if r['klass'] in SCHEDULE_CLASSES and r['klass'] != 'A4-slot-assignment' and r['decision'] in APPLIED}
    slotted = {(r['target'][0], r['field'].rsplit('(', 1)[1].rstrip(')')) for r in rows
               if r['klass'] == 'A4-slot-assignment' and r['decision'] in APPLIED}
    added = {'humidifying', 'dehumidifying'} if any(r['klass'] == 'C6-humidity-setpoint' for r in rows) else set()
    choices, conflicts = reference_extras.slot_choices(model, zone_programs, floors)
    result = defaultdict(dict)
    for program, slots in sorted(choices.items()):
        for slot, name in sorted(slots.items()):
            if name.lower() in named or (program, slot) in slotted or slot in added:
                result[program][slot] = extract.schedule(model, source_file, name, reference_extras.SLOTS[slot][2], days)
    return result, conflicts


def build(idf_root, standards_root, register, check_climates=True):
    geometry = {(e['template'], e['building_type']): e
                for e in load_json(ROOT/'data/construction-inputs/geometry-v1.json')['commercial']}
    archives = {e['path'].removesuffix('.zip').split('/')[-1]: e for e in load_json(LOCK)['files']
                if e['source_id'] == 'doe-reference'}
    extract = Extract()
    folders = {}
    for vintage, template in TEMPLATES.items():
        _, standards_template, geometry_template = reference_loads.VINTAGES[vintage]
        spc = load_json(standards_root/standards_template/'data'/f'{standards_template}.spc_typ.json')
        standards = {(r['building_type'], r['space_type']): r for r in spc['space_types']}
        for key, (building_type, folder) in reference_loads.TYPES.items():
            directory = f'refbldg_{key}_{vintage}_v1-4_7-2'
            path = next((idf_root/directory).glob('*5A_USA_IL_CHICAGO-OHARE.idf'))
            if register['input_sha256'][path.name] != sha256(path):
                raise ValueError('IDF differs from the register input: '+path.name)
            model = idf_reader.Model(path)
            source_file = extract.source_file(path, idf_root, archives[directory])
            days = idf_schedules.calendar_days(model.holidays())
            rows = register_rows(register, template, building_type)
            floors = reference_extras.zone_floors(model)
            load_rows = reference_loads.compare_type(model, building_type, folder, template, standards,
                                                     geometry[(geometry_template, building_type)])
            zone_programs = zone_program_map(load_rows, building_type)
            schedules, conflicts = program_schedules(extract, model, source_file, rows, zone_programs, floors, days)
            folders[f'{template}/{folder}'] = {
                'building_type': building_type, 'source_file': source_file,
                'program_schedules': schedules, 'schedule_conflicts': conflicts,
                'program_values': program_values(extract, source_file, rows),
                'alternates': alternates(extract, model, source_file, rows, days),
                'fenestration': fenestration(extract, source_file, rows, model),
                'hot_water': hot_water(extract, model, source_file, rows, days),
                'services': services(extract, model, source_file, rows, zone_programs, days),
                'calendar': calendar(extract, source_file, model),
                'infiltration': infiltration(extract, model, source_file, zone_programs, days),
                'mass_fills': mass_fills(extract, model, source_file, rows),
                'new_programs': new_programs(extract, model, source_file, rows, load_rows, geometry[(geometry_template, building_type)], days),
                'climate_files_checked': climate_check(idf_root, directory, model) if check_climates else None}
    return extract, folders


def program_values(extract, source_file, rows):
    """[{row, program, path, value, evidence}] for the load, fraction and zero fills."""
    out = []
    for r in rows:
        if r['decision'] not in APPLIED or not r['target'] or r['target'][0] is None:
            continue
        value = r['source_value'].get('value')
        if r['klass'] in ('A5-explicitly-wrong', 'A5-folded-service', 'B5-missing-density', 'B7-filling-sourced',
                          'B2-additional-lighting'):
            path = ('load', r['field'], 'value')
        elif r['klass'] == 'A12-heat-fraction':
            quantity, _, effect = r['field'].split('.')
            path = ('load', quantity, 'thermal_effects', effect)
        elif r['klass'] == 'B3-unconditioned-equipment':
            path, value = ('load', 'electric_equipment', 'zero'), 0.0
        else:
            continue
        locator = r['source_value'].get('object') or 'zones '+', '.join(r['source_value'].get('zones', []))
        evidence = extract.cite(source_file, locator, value, 'SI (W/m2, person/m2 or fraction)',
                                'area-weighted over the program zones; absent objects count as zero',
                                f'DOE reference value applied under register row {r["id"]} ({r["klass"]}).')
        out.append({'row': r['id'], 'program': r['target'][0], 'path': list(path), 'value': value, 'evidence': evidence})
    return out


def alternates(extract, model, source_file, rows, days):
    """Second backed values on kept rows: DOE densities, and DOE schedules where a documented edit is kept."""
    out = []
    for r in rows:
        if r['decision'] != 'keep' or not r.get('alternate') or not r['target'] or r['target'][0] is None:
            continue
        if r['klass'] == 'A5-existing-density':
            value = r['alternate']['value']
            evidence = extract.cite(source_file, 'zones '+', '.join(r['source_value']['zones']), value,
                                    'SI (W/m2 or person/m2)', 'area-weighted over the program zones',
                                    f'DOE reference alternate under register row {r["id"]} (ADR 0037 section 1).')
            out.append({'row': r['id'], 'programs': r['target'], 'path': ['load', r['field']], 'value': value,
                        'reason_id': r['reason_id'], 'evidence': evidence})
        else:
            name = r['source_value']['object'].split(' ', 1)[1]
            schedule = extract.schedule(model, source_file, name, 'fraction', days)
            programs = r['target'] if r['klass'] != 'A3-upstream-edit' or not r.get('programs') else r['programs']
            out.append({'row': r['id'], 'programs': [p for p in programs if not str(p).startswith('schedules.json')],
                        'schedule_source_name': r['current']['value'], 'value': schedule, 'reason_id': r['reason_id'],
                        'evidence': extract.schedules[schedule]['evidence_ids'][0]})
    return out


def fenestration(extract, source_file, rows, model):
    out = {'programs': {}, 'building': None}
    for r in rows:
        if r['klass'] == 'C10-program-wwr':
            out['programs'][r['target'][0]] = {'row': r['id'], 'value': r['source_value']['value'],
                                               'evidence': extract.cite(source_file, 'FenestrationSurface:Detailed by zone', r['source_value']['value'], 'm2/m2',
                                                                        'window over exterior wall area by direction, zone multipliers applied',
                                                                        'DOE reference program window ratios (ADR 0037 C10).')}
        elif r['klass'] == 'C10-building-wwr':
            out['building'] = {'row': r['id'], 'value': r['source_value']['value'],
                               'evidence': extract.cite(source_file, 'FenestrationSurface:Detailed, building', r['source_value']['value'], 'm2/m2',
                                                        'area-weighted over conditioned, unconditioned and all zone surfaces',
                                                        'DOE reference building window ratios (ADR 0037 C10).')}
    return out


def hot_water(extract, model, source_file, rows, days):
    """Zero fills, zone gains, and DOE flow schedules by the atlas schedule name they replace
    (for hot-water services that name no beneficiary program)."""
    out = {'zero_programs': [], 'gains': [], 'schedules_by_name': {}}
    for r in rows:
        if (r['field'] == 'schedule (hot-water flow)' and r['decision'] in APPLIED and r['klass'] in SCHEDULE_CLASSES
                and r['current'].get('value')):
            name = r['source_value']['object'].split(' ', 1)[1]
            out['schedules_by_name'][r['current']['value']] = extract.schedule(model, source_file, name, 'fraction', days)
        if r['klass'] == 'B1-hot-water' and r['decision'] == 'fill' and not r['source_value']['draws']:
            out['zero_programs'].append({'row': r['id'], 'program': r['target'][0], 'evidence': extract.cite(
                source_file, 'WaterUse:Equipment (none in the program zones)', 0.0, 'm3/s',
                'absence in the complete DOE model is a source-backed zero', 'No DOE hot-water draw in this program (ADR 0037 B1).')})
        elif r['klass'] == 'C5-water-use-gains':
            v = r['source_value']['value']
            out['gains'].append({'row': r['id'], 'program': (r['target'] or [None])[0], 'zone': v['zone'],
                                 'peak_flow_m3_s': v['peak_flow_m3_s'], 'sensible_fraction': v['sensible_fraction'],
                                 'latent_fraction': v['latent_fraction'], 'evidence': extract.cite(
                                     source_file, r['source_value']['object'], v, 'm3/s; fractions',
                                     'sensible = fraction x m x cp x (T_mixed - T_zone); latent = fraction of evaporable water',
                                     'DOE reference water-use zone gains (ADR 0037 C5).')})
    return out


def services(extract, model, source_file, rows, zone_programs, days):
    out = []
    for r in rows:
        if r['klass'] not in ('C3-building-service', 'C4-refrigeration') or r['decision'] != 'add':
            continue
        v = dict(r['source_value']['value'])
        zones = [z.lower() for z in v.get('zones', [])] or ([v['zone'].lower()] if v.get('zone') else [])
        for field in ('schedule', 'availability', 'lighting_schedule'):
            if v.get(field):
                v[field+'_id'] = extract.schedule(model, source_file, v[field], 'fraction', days)
        out.append({'row': r['id'], 'end_use': v['end_use'], 'value': v,
                    'beneficiary_programs': sorted({zone_programs[z] for z in zones if z in zone_programs}),
                    'evidence': extract.cite(source_file, r['source_value']['object'], r['source_value']['value'],
                                             'SI (W, W/m, W/m2, C)', 'object fields as written in the IDF',
                                             f'DOE reference building service (ADR 0037 {r["klass"][:2]}).')})
    return out


FRACTIONS = {'lights': ('lighting', {'radiant': 'radiant', 'return_air': 'to_return_air', 'visible': 'visible'}),
             'electricequipment': ('electric_equipment', {'radiant': 'radiant', 'latent': 'latent', 'lost': 'lost'}),
             'gasequipment': ('gas_equipment', {'radiant': 'radiant', 'latent': 'latent', 'lost': 'lost'})}


def new_programs(extract, model, source_file, rows, load_rows, geometry, days):
    """The programs NEW_PROGRAMS adds: DOE loads, heat fractions, slot schedules and window ratios of
    the zone group, and the geometry spaces it represents."""
    out = []
    spaces = {s['name']: s for s in geometry['spaces']}
    for r in rows:
        if r['klass'] not in ('A4-retag', 'C8-basement-program') or r['decision'] != 'add':
            continue
        name = r['field'].split(' ', 1)[1]
        zones = [z for z in load_rows if z['zone'] in r['source_value']['zones']]
        keys = {z['zone'].lower() for z in zones}
        fractions = {}
        for z in zones:
            for obj in z['objects']:
                if obj['class'] in FRACTIONS and not obj.get('outside_space_type_table'):
                    quantity, names = FRACTIONS[obj['class']]
                    fractions.setdefault(quantity, {a: obj['fractions'][i] for i, a in names.items() if obj['fractions'].get(i) is not None})
        floors = reference_extras.zone_floors(model)
        choices, conflicts = reference_extras.slot_choices(model, {k: name for k in keys}, floors)
        if conflicts:
            raise ValueError(f'Zones of {name} use several schedules in one slot: {conflicts}')
        slots = {slot: extract.schedule(model, source_file, schedule, reference_extras.SLOTS[slot][2], days)
                 for slot, schedule in choices.get(name, {}).items()}
        draws = [d for d in reference_extras.water_draws(model) if d['zone'].lower() in keys]
        if draws:
            raise ValueError(f'{name} has DOE hot-water draws; a new program would need their service')
        evidence = extract.cite(source_file, 'zones '+', '.join(r['source_value']['zones']), r['source_value']['value'],
                                'SI (W/m2, person/m2)', 'area-weighted over the zone group; absent objects count as zero',
                                f'DOE reference zone group given its own program under register row {r["id"]} (ADR 0037 A4, C8).')
        out.append({'row': r['id'], 'name': name, 'space_type': name.rsplit('_', 1)[0], 'parent': r['target'][0],
                    'zones': r['source_value']['zones'], 'loads': r['source_value']['value'], 'fractions': fractions,
                    'slots': slots, 'fenestration': reference_extras.fenestration(model, {k: name for k in keys})['programs'].get(
                        name, dict.fromkeys(reference_extras.DIRECTIONS)),
                    'spaces': [{'name': spaces[z]['name'], 'floor_area_m2': spaces[z]['floor_area_m2'], 'multiplier': spaces[z]['multiplier']}
                               for z in r['source_value']['zones']],
                    'evidence': evidence})
    return out


def infiltration(extract, model, source_file, zone_programs, days):
    """DOE ZoneInfiltration:DesignFlowRate rules, grouped by method, rate, coefficients and schedule."""
    rules = {}
    for item in model.infiltration():
        rate = next(v for v in item['values'] if v is not None)
        key = (item['method'], rate, tuple(item['coefficients']), item['schedule'])
        rules.setdefault(key, set()).update(item['zones'])
    out = []
    for (method, rate, coefficients, schedule), zones in sorted(rules.items(), key=str):
        out.append({'method': method, 'value': rate, 'unit': UNITS[method], 'coefficients': list(coefficients),
                    'schedule_id': extract.schedule(model, source_file, schedule, 'fraction', days),
                    'zones': sorted(model.zones[z]['name'] for z in zones),
                    'programs': sorted({zone_programs[z] for z in zones if z in zone_programs})})
    return {'zone_rules': out, 'excluded_zones': sorted(model.zones[z]['name'] for z in model.zones
                                                         if not any(z in r for r in rules.values())),
            'evidence': extract.cite(source_file, 'ZoneInfiltration:DesignFlowRate', [{k: v for k, v in r.items() if k != 'programs'} for r in out],
                                     'SI (m3/s-m2, m3/s, 1/h)', 'objects grouped by method, rate, coefficients and schedule',
                                     'DOE reference design-flow infiltration (ADR 0037 A10).')}


def mass_fills(extract, model, source_file, rows):
    """InternalMass of the zones whose atlas source space has no additional-mass entry (register B8 fills)."""
    objects = defaultdict(list)
    for m in model.internal_mass():
        for zone in m['zones']:
            objects[zone].append(m)
    floors = reference_extras.zone_floors(model)
    layers = {c[0].lower(): c[1:] for c in model.all('construction')}
    out = []
    for r in rows:
        if r['klass'] != 'B8-internal-mass' or r['decision'] != 'fill':
            continue
        zone = r['source_value']['zone']
        items = objects[zone]
        out.append({'row': r['id'], 'zone': model.zones[zone]['name'], 'space': r['source_value']['space'],
                    'programs': r['target'], 'area_per_floor_area': sum(m['area'] for m in items) / floors[zone],
                    'constructions': sorted({m['construction'] for m in items}),
                    'layers': sorted({l for m in items for l in layers[m['construction'].lower()]}),
                    'evidence': extract.cite(source_file, 'InternalMass '+', '.join(m['name'] for m in items),
                                             [{'area_m2': m['area'], 'construction': m['construction']} for m in items],
                                             'm2', 'object area over the DOE zone floor area, applied to the atlas source space',
                                             f'DOE reference internal mass filled under register row {r["id"]} (ADR 0037 B8).')})
    return out


def climate_check(idf_root, directory, model):
    """The other climate files give the same window ratios and infiltration rules as the 5A file."""
    signature = lambda m: json.dumps([reference_extras.fenestration(m, {})['building'],
                                      sorted(map(str, ((i['method'], i['values'], i['schedule']) for i in m.infiltration())))])
    expected = signature(model)
    files = sorted((idf_root/directory).glob('*.idf'))
    differ = [p.name for p in files if signature(idf_reader.Model(p)) != expected]
    if differ:
        raise ValueError(f'Window ratios or infiltration differ by climate in {directory}: {differ[:3]}')
    return len(files)


def calendar(extract, source_file, model):
    holidays = [{'name': name, 'rule': rule} for name, rule in model.holidays()]
    dst = model.first('runperiodcontrol:daylightsavingtime', None)
    value = {'holidays': holidays,
             'daylight_saving': {'start': dst[0], 'end': dst[1], 'applied': False} if dst else None}
    return {**value, 'evidence': extract.cite(source_file, 'RunPeriodControl:SpecialDays, RunPeriodControl:DaylightSavingTime',
                                              value, 'calendar rules', 'rules as written; dates are resolved per consumer year',
                                              'DOE reference holiday calendar (ADR 0037 C1, C2).')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--idf-root', type=Path, required=True)
    parser.add_argument('--standards-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT/'data/reconciliation/doe-reference-values-v1.json')
    parser.add_argument('--skip-climate-check', action='store_true',
                        help='do not confirm that the other 15 climate files give the same ratios and infiltration')
    args = parser.parse_args()
    register = load_json(REGISTER_PATH)
    extract, folders = build(args.idf_root, args.standards_root, register, not args.skip_climate_check)
    document = {'schema_version': '1.0.0', 'kind': 'reconciliation_values', 'adr': 'docs/adr/0037-doe-reference-reconciliation.md',
                'generated_by': 'python -m scripts.reconciliation_values', 'register_sha256': sha256(REGISTER_PATH),
                'lock_sha256': sha256(LOCK), 'source_files': extract.source_files, 'evidence': extract.evidence,
                'schedules': extract.schedules, 'folders': folders}
    args.out.write_text(json.dumps(document, indent=1, sort_keys=True) + '\n', newline='\n')
    conflicts = sum(len(f['schedule_conflicts']) for f in folders.values())
    print(f'{len(extract.schedules)} schedules, {len(extract.evidence)} evidence rows, {conflicts} schedule-slot conflicts')


if __name__ == '__main__':
    main()
