"""Build the DOE reference reconciliation register (ADR 0037).

python -m scripts.reconciliation_register --idf-root <extracted doe-reference/v1.4_7.2>
    --standards-root <ashrae_90_1 dir> [--out data/reconciliation/doe-reference-v1.json]

One row per item, for the DOE Ref templates (post-1980 IDFs against doe-ref-1980-2004,
pre-1980 against doe-ref-pre-1980), the 15 non-residential types. Each row records the
current atlas value, the DOE value with its locator, and a decision under the ADR 0037
rules; decisions that keep, leave or omit cite a reason from REASONS.
Identical schedules and exactly matching loads produce no row; the summary counts them.
"""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts import atlas_exports, idf_reader, idf_schedules, reference_extras, reference_loads, reference_schedules
from scripts.common import ROOT

RELEASE = ROOT/'data/atlas-releases/v1.0.0/commercial'
EDITS = ROOT/'data/reconciliation/upstream-edits-v1.json'
REGISTER_PATH = ROOT/'data/reconciliation/doe-reference-v1.json'
ALTERNATE_THRESHOLD = 0.5
REASONS = {
    'R-ROUNDING': 'Same source value; the IDF prints SI values to 2-4 significant figures (within 1%).',
    'R-NEWER-DOCUMENTED': 'The openstudio-standards row was edited after the DOE v1.4 release (2012-11-13) and the edit is documented; the DOE value is kept as an alternate.',
    'R-EXISTING-DENSITY': 'Existing-building density kept: the atlas value is plausible and not explicitly wrong (ADR 0037 section 1).',
    'R-MIXED-ZONE': 'The DOE zone spans several atlas space types, so its single value cannot be assigned to one program.',
    'R-NO-ATLAS-PROGRAM': 'No atlas program represents this DOE zone.',
    'R-NO-LIGHTING-SPLIT': 'The DOE model has one lighting object per zone; the additional-lighting share cannot be separated.',
    'R-SYSTEMS-DEFERRED': 'Systems are deferred; BEMGen tests at ideal-loads grade (HVAC, outdoor air, zone mixing, water heaters).',
    'R-SITE-DATA': 'Site, weather and cost data are supplied by the consumer at model creation.',
    'R-COMFORT-ONLY': 'Comfort-only People fields have no effect on the heat balance.',
    'R-DAYLIGHTING-ONLY': 'The lights replaceable fraction only affects daylighting control, which the DOE Ref models do not have.',
    'R-GEOMETRY-BEMGEN': 'Plan geometry, shading and skylight placement belong to BEMGen; the atlas carries only window ratios.',
    'R-NOT-COMPARED': 'Midrise Apartment was not compared in this reconciliation; it is taken up with the residential work.',
    'R-HOURLY': 'Atlas schedules are hourly; a time inside an hour is stored as its energy-conserving hourly mean.',
    'R-SLOT-CONFLICT': 'Several DOE schedules serve this slot across the program zones; the program takes the area-dominant one (a tie goes to the first name).',
    'R-UNCONTROLLED': 'The DOE model gives these zones no thermostat, so the atlas null setpoint is source-backed.',
}
TEMPLATES = {'post1980': 'doe-ref-1980-2004', 'pre1980': 'doe-ref-pre-1980'}
RETAGS = {('Outpatient', 'Janitor'): 'storage and utility rooms tagged Janitor in ASHRAEOutpatient.osm',
          ('PrimarySchool', 'Classroom'): 'Computer_Class and Library tagged Classroom in DOERefPrimarySchool.osm'}
RETAGGED_ZONES = {'Outpatient': ('storage', 'utility', 'sterile'), 'PrimarySchool': ('computer_class', 'library')}
EXPLICIT_FACTOR = 10 * (1 - 1e-2)  # a factor of ten, allowing for the IDFs' printed rounding


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Register:
    def __init__(self):
        self.rows = []

    def add(self, **row):
        row['id'] = f'rec-{len(self.rows) + 1:05d}'
        if row['decision'] in ('keep', 'leave', 'omit'):
            assert row.get('reason_id') in REASONS, row
        self.rows.append(row)


def documented_edits():
    edits = json.loads(EDITS.read_text())['edits']
    return {e['key']: e for e in edits if e['kind'] == 'schedules'}


def schedule_rows(register, idf_file, template, building_type, rows, edits, zone_programs, uses, conflicts):
    chosen = {c['chosen'].lower() for c in conflicts}
    minority = {name.lower(): c for c in conflicts for name in c['schedules'] if name.lower() not in chosen}
    for c in conflicts:
        register.add(category='inconsistency', klass='A4-slot-conflict', decision='keep', reason_id='R-SLOT-CONFLICT',
                     source_family='doe-reference', template=template, building_type=building_type, target=[c['program']],
                     field=f"schedule ({c['slot']})", current={'value': None},
                     source_value={'file': idf_file, 'value': c['schedules'], 'chosen': c['chosen']})
    for r in rows:
        cause = r['cause']
        if cause == 'identical':
            continue
        atlas = r['atlas'] or {}
        common = {'source_family': 'doe-reference', 'template': template, 'building_type': building_type,
                  'target': f"schedules.json#{atlas.get('name')}" if atlas else None, 'field': f"schedule ({r['role']})",
                  'current': {'value': atlas.get('source_name'), 'differing_days': atlas.get('differing_days')},
                  'source_value': {'file': idf_file, 'object': f"Schedule:Compact {r['schedule']}"},
                  'upstream': {'best_match': (r['standards'] or {}).get('name'), 'class': (r['standards'] or {}).get('class')},
                  'programs': sorted({zone_programs[z] for z in uses.get(r['schedule'].lower(), ()) if z in zone_programs})}
        if r['subhour']:
            common['note'] = REASONS['R-HOURLY']
        if r['schedule'].lower() in minority:
            register.add(category='inconsistency', klass='A4-slot-minority', decision='leave', reason_id='R-SLOT-CONFLICT',
                         **common)
        elif cause == 'holidays':
            register.add(category='inconsistency', klass='A1-holidays', decision='replace', **common)
        elif cause == 'design days':
            register.add(category='inconsistency', klass='A9-design-days', decision='replace', **common)
        elif cause == 'assignment':
            register.add(category='inconsistency', klass='A4-assignment', decision='replace', **common)
        elif cause in ('source edit', 'vintage variant'):
            edit = edits.get(atlas.get('source_name'))
            if edit and edit['applies_to_doe_ref'] == 'keep_with_alternate':
                register.add(category='inconsistency', klass='A3-upstream-edit', decision='keep',
                             reason_id='R-NEWER-DOCUMENTED', alternate={'source_family': 'doe-reference', 'value': 'DOE profile'},
                             upstream_edit=edit, **common)
            else:
                register.add(category='inconsistency', klass='A3-upstream-edit' if cause == 'source edit' else 'A3-vintage-variant',
                             decision='replace', upstream_edit=edit, **common)
        elif cause.startswith('out of program scope: infiltration'):
            register.add(category='missing', klass='A10-infiltration-schedule', decision='add', **common)
        elif cause.startswith('out of program scope: building service'):
            register.add(category='missing', klass='C3-building-service-schedule', decision='add', **common)
        elif r['role'] == 'hot-water flow':
            register.add(category='gap', klass='B1-hot-water-schedule', decision='fill', **common)
        else:
            register.add(category='inconsistency', klass='A3-no-atlas-counterpart', decision='replace', **common)


def retagged(building_type, zone):
    return any(w in zone.lower() for w in RETAGGED_ZONES.get(building_type, ()))


def zone_program_map(load_rows, building_type):
    """{zone (lower case): program id} for zones mapped to one atlas program, re-tagged zones excluded."""
    return {z['zone'].lower(): z['refs']['atlas_programs'][0] for z in load_rows
            if z.get('mapping') and not z['mapping']['mixed'] and len(z.get('refs', {}).get('atlas_programs', [])) == 1
            and not retagged(building_type, z['zone'])}


def slot_rows(register, idf_file, template, building_type, model, choices, programs, suite, edits):
    """A4-slot-assignment: a program slot whose atlas schedule differs from its DOE schedule over the year,
    where no schedule row already replaces that DOE schedule."""
    days = idf_schedules.calendar_days(model.holidays())
    replaced = {r['source_value']['object'].split(' ', 1)[1].lower() for r in register.rows
                if r['template'] == template and r['building_type'] == building_type and r['field']
                and str(r['field']).startswith('schedule (') and r['decision'] == 'replace'}
    kept = {name for name, e in edits.items() if e['applies_to_doe_ref'] == 'keep_with_alternate'}
    for program_id, slots in sorted(choices.items()):
        program = programs.get(program_id)
        for slot, name in sorted(slots.items()):
            kind, field, _ = reference_extras.SLOTS[slot]
            if program is None or name.lower() in replaced or slot == 'hot_water':
                continue
            entry = (next((l for l in program['loads'] if l['quantity'] == field), None) if kind == 'load'
                     else program['parameters'].get(field))
            key = 'schedule_id' if kind == 'load' else 'value'
            current = (entry or {}).get(key)
            if current is None and entry and 'filling' in entry:
                current = entry['filling']['set'].get(key)
            common = {'source_family': 'doe-reference', 'template': template, 'building_type': building_type,
                      'target': [program_id], 'field': f'{field} schedule ({slot})',
                      'source_value': {'file': idf_file, 'object': f'Schedule:Compact {name}'}}
            if not isinstance(current, str):
                if slot in ('humidifying', 'dehumidifying'):
                    continue  # added by the C6 rows
                register.add(category='gap', klass='A4-slot-assignment', decision='fill', current={'value': current}, **common)
                continue
            atlas = suite.schedule(current)
            got = idf_schedules.evaluate_ruleset(atlas['rules'], lambda r: r['values'] * (24 // len(r['values'])), days)
            expected, _ = idf_schedules.evaluate_compact(model.schedules()[name.lower()], days)
            differing = sum(1 for k in days if not idf_schedules.same(expected[k], got[k]))
            if not differing:
                continue
            row = dict(current={'value': atlas.get('source_name') or current, 'differing_days': differing}, **common)
            if atlas.get('source_name') in kept:
                register.add(category='inconsistency', klass='A3-upstream-edit', decision='keep', reason_id='R-NEWER-DOCUMENTED',
                             alternate={'source_family': 'doe-reference', 'value': 'DOE profile'},
                             upstream_edit=edits[atlas['source_name']], **row)
            else:
                register.add(category='inconsistency', klass='A4-slot-assignment', decision='replace', **row)


def program_load_rows(register, idf_file, template, building_type, rows):
    """One row per atlas program and quantity whose DOE value differs; mixed zones get a leave row."""
    groups = defaultdict(list)
    for z in rows:
        if retagged(building_type, z['zone']):
            continue  # compared after re-tagging; the A4-retag row carries these zones
        mapping = z.get('mapping')
        if mapping is None:
            register.add(category='gap', klass='zone-unmapped', decision='leave', reason_id='R-NO-ATLAS-PROGRAM',
                         source_family='doe-reference', template=template, building_type=building_type,
                         target=None, field='zone', current=None, source_value={'file': idf_file, 'zone': z['zone']})
            continue
        if mapping['mixed']:
            register.add(category='inconsistency', klass='mixed-zone', decision='leave', reason_id='R-MIXED-ZONE',
                         source_family='doe-reference', template=template, building_type=building_type, target=None,
                         field='loads', current={'space_types': mapping['space_types']},
                         source_value={'file': idf_file, 'zone': z['zone'], 'values': z['idf']})
            continue
        if 'atlas' in z.get('refs', {}):
            groups[tuple(z['refs']['atlas_programs'])].append(z)
    for programs, zones in groups.items():
        weight = sum(z['floor_m2'] for z in zones)
        for q in reference_loads.QUANTITIES:
            idf_value = sum(z['idf'][q] * z['floor_m2'] for z in zones) / weight
            atlas_value = zones[0]['refs']['atlas'][q]
            grade = reference_loads.match(idf_value, atlas_value) if atlas_value is not None else None
            if grade == 'exact':
                continue
            common = {'source_family': 'doe-reference', 'template': template, 'building_type': building_type,
                      'target': list(programs), 'field': q, 'current': {'value': atlas_value},
                      'source_value': {'file': idf_file, 'zones': [z['zone'] for z in zones], 'value': round(idf_value, 6)}}
            if atlas_value is None:
                # absence in the complete DOE model is a source-backed zero
                register.add(category='gap', klass='B5-missing-density', decision='fill', **common)
            elif grade == 'rounding':
                register.add(category='inconsistency', klass='A7-rounding', decision='keep', reason_id='R-ROUNDING', **common)
            else:
                larger, smaller = max(abs(idf_value), abs(atlas_value)), min(abs(idf_value), abs(atlas_value))
                folded = q == 'electric_equipment' and idf_value == 0 and any(
                    o.get('outside_space_type_table') for z in zones for o in z['objects'])
                if folded:
                    register.add(category='inconsistency', klass='A5-folded-service', decision='replace',
                                 note='openstudio-standards folds a building service (elevator, exhaust fan) into this '
                                      'space type; the service moves to services (C3) and the program takes the DOE value.',
                                 **common)
                elif smaller > 0 and larger / smaller >= EXPLICIT_FACTOR:
                    register.add(category='inconsistency', klass='A5-explicitly-wrong', decision='replace', **common)
                else:
                    alternate = ({'source_family': 'doe-reference', 'value': round(idf_value, 6)}
                                 if (larger - smaller) / larger > ALTERNATE_THRESHOLD else None)
                    register.add(category='inconsistency', klass='A5-existing-density', decision='keep',
                                 reason_id='R-EXISTING-DENSITY', alternate=alternate, **common)


def fraction_rows(register, idf_file, template, building_type, rows, programs):
    """Heat fractions of lighting and equipment: DOE object fractions against atlas thermal_effects."""
    keys = {'lights': ('lighting', {'radiant': 'radiant', 'return_air': 'to_return_air', 'visible': 'visible'}),
            'electricequipment': ('electric_equipment', {'radiant': 'radiant', 'latent': 'latent', 'lost': 'lost'}),
            'gasequipment': ('gas_equipment', {'radiant': 'radiant', 'latent': 'latent', 'lost': 'lost'})}
    seen = set()
    for z in rows:
        if not z.get('mapping') or z['mapping']['mixed'] or 'atlas_programs' not in z.get('refs', {}):
            continue
        program_id = z['refs']['atlas_programs'][0]
        stored = programs.get(program_id)
        if stored is None:
            continue
        for obj in z['objects']:
            if obj['class'] not in keys or obj.get('outside_space_type_table'):
                continue
            quantity, names = keys[obj['class']]
            load = next((l for l in stored['loads'] if l['quantity'] == quantity), None)
            effects = (load or {}).get('thermal_effects', {})
            for idf_name, atlas_name in names.items():
                idf_value = obj['fractions'].get(idf_name)
                atlas_value = (effects.get(atlas_name) or {}).get('value')
                key = (program_id, quantity, atlas_name)
                if idf_value is None or key in seen or reference_loads.match(idf_value, atlas_value) in ('exact', 'rounding'):
                    continue
                seen.add(key)
                register.add(category='gap' if atlas_value is None else 'inconsistency', klass='A12-heat-fraction',
                             decision='fill' if atlas_value is None else 'replace', source_family='doe-reference',
                             template=template, building_type=building_type, target=[program_id],
                             field=f'{quantity}.thermal_effects.{atlas_name}', current={'value': atlas_value},
                             source_value={'file': idf_file, 'object': f"{obj['class']} {obj['name']}", 'value': idf_value})


def stored_programs(template, folder):
    result = {}
    for path in (RELEASE/template/folder/'programs/source').glob('*.json'):
        program = json.loads(path.read_text(encoding='utf-8'))
        result[program['id']] = program
    return result


def space_key(name):
    return name.lower().replace(' ', '_')


def atlas_mass(release, template, folder):
    """{source space key: stored additional-mass area, source multiplier applied}."""
    path = next((RELEASE/template/folder/'constructions').glob('*.json'))
    document = release.constructions.export(json.loads(path.read_text(encoding='utf-8'))['id'], '5-a', 'detailed')
    result = defaultdict(float)
    for entry in document['mass_accounting']['additional_mass'].get('entries', []):
        if entry['scope'].get('source_space_name'):
            result[space_key(entry['scope']['source_space_name'])] += entry['reference_area_m2']
    return result


def component_rows(register, idf_file, template, building_type, model, rows, programs, atlas_mass, geometry):
    common = {'source_family': 'doe-reference', 'template': template, 'building_type': building_type}
    zone_program = zone_program_map(rows, building_type)
    # B1/C5: hot water by program, with zone gain fractions
    draws = reference_extras.water_draws(model)
    drawn = defaultdict(list)
    for d in draws:
        drawn[zone_program.get(d['zone'].lower())].append(d)
    for program_id, program in programs.items():
        if 'service_water_heating_schedule_id' not in program.get('unresolved', {}):
            continue
        items = drawn.get(program_id, [])
        register.add(category='gap', klass='B1-hot-water', decision='fill', target=[program_id],
                     field='service_water_heating_schedule_id', current={'value': None, 'unresolved': program['unresolved']['service_water_heating_schedule_id']},
                     source_value={'file': idf_file, 'draws': [d['name'] for d in items],
                                   'value': sorted({d['flow_schedule'] for d in items}) or 'no draw: zero'}, **common)
    for d in draws:
        register.add(category='missing', klass='C5-water-use-gains', decision='add',
                     target=[zone_program.get(d['zone'].lower())], field='hot_water.thermal_effects',
                     current={'value': 'zone_heat_gains excluded (ADR 0018)'},
                     source_value={'file': idf_file, 'object': f"WaterUse:Equipment {d['name']}", 'value': d}, **common)
    # C3/C4 building services and refrigeration
    for s in reference_extras.services(model):
        klass = 'C4-refrigeration' if s['end_use'].startswith('refrigeration') else 'C3-building-service'
        register.add(category='missing', klass=klass, decision='add', target=[f'services.json#{s["end_use"]}'],
                     field=s['end_use'], current={'value': None},
                     source_value={'file': idf_file, 'object': s['name'], 'value': s}, **common)
    # C6 humidity controls
    for h in reference_extras.humidistats(model):
        register.add(category='missing', klass='C6-humidity-setpoint', decision='add',
                     target=[zone_program.get(h['zone'].lower())], field='humidity setpoints', current={'value': None},
                     source_value={'file': idf_file, 'zone': h['zone'], 'value': h}, **common)
    # Q16 window ratios: per program and the 15 building values
    fen = reference_extras.fenestration(model, zone_program)
    for program_id, ratios in fen['programs'].items():
        register.add(category='missing', klass='C10-program-wwr', decision='add', target=[program_id],
                     field='fenestration', current={'value': None}, source_value={'file': idf_file, 'value': ratios}, **common)
    register.add(category='missing', klass='C10-building-wwr', decision='add', target=['constructions'],
                 field='fenestration_defaults', current={'value': None},
                 source_value={'file': idf_file, 'value': fen['building']}, **common)
    # A10 second infiltration method
    rules = sorted({(i['method'], i['values'][2] or i['values'][3] or i['values'][1] or i['values'][0], i['schedule'])
                    for i in model.infiltration()}, key=str)
    register.add(category='missing', klass='A10-infiltration-method', decision='add', target=['constructions'],
                 field='infiltration.methods.doe_design_flow', current={'value': 'fixed_source_reference_natural_ach'},
                 source_value={'file': idf_file, 'value': [list(r) for r in rules]}, **common)
    # B8 internal mass: DOE InternalMass area per zone floor area against the atlas source-space entries
    mass = defaultdict(float)
    for m in model.internal_mass():
        for zone in m['zones']:
            mass[zone] += (m['area'] or 0.0) / len(m['zones'])
    floors = reference_extras.zone_floors(model)
    spaces = {space_key(s['name']): s for s in geometry['spaces']}
    for zone, area in sorted(mass.items()):
        if not floors.get(zone):
            continue
        doe = area / floors[zone]
        name = model.zones[zone]['name']
        z = next((r for r in rows if r['zone'].lower() == zone), {})
        for key in [space_key(n) for n in reference_loads.ALIASES.get(building_type, {}).get(name, [name])]:
            space = spaces.get(key)
            if space is None:
                continue
            row = dict(target=z.get('refs', {}).get('atlas_programs', [None]), field='mass_accounting.additional_mass',
                       source_value={'file': idf_file, 'zone': zone, 'space': space['name'], 'value': round(doe, 4)}, **common)
            if key not in atlas_mass:
                register.add(category='gap', klass='B8-internal-mass', decision='fill', current={'value': None}, **row)
                continue
            stored = atlas_mass[key] / (space['floor_area_m2'] * space['multiplier'])
            if reference_loads.match(doe, stored) not in ('exact', 'rounding'):
                register.add(category='inconsistency', klass='B8-internal-mass', decision='review',
                             current={'value': round(stored, 4)}, **row)
    # B2 additional lighting and B3 plenum and attic equipment, null in the atlas
    for program_id, program in programs.items():
        loads = {l['quantity']: l for l in program['loads']}
        extra = loads.get('additional_lighting')
        if extra and extra.get('value') is None and 'filling' not in extra:
            zones = [z for z in rows if program_id in z.get('refs', {}).get('atlas_programs', ())]
            base = bool(zones) and all(z['match']['atlas']['lighting'] in ('exact', 'rounding') for z in zones)
            register.add(category='gap', klass='B2-additional-lighting', decision='fill' if base else 'leave',
                         reason_id=None if base else 'R-NO-LIGHTING-SPLIT', target=[program_id],
                         field='additional_lighting', current={'value': None},
                         source_value={'file': idf_file, 'zones': [z['zone'] for z in zones],
                                       'value': 0.0 if base else 'one lighting object per zone'}, **common)
        equipment = loads.get('electric_equipment')
        name = program['name'].lower()
        if (equipment and 'filling' not in equipment and ('plenum' in name or 'attic' in name)
                and (equipment.get('schedule_id') is None or equipment.get('value') is None)):
            register.add(category='gap', klass='B3-unconditioned-equipment', decision='fill', target=[program_id],
                         field='electric_equipment', current={'value': equipment.get('value'),
                                                              'schedule_id': equipment.get('schedule_id')},
                         source_value={'file': idf_file, 'value': 'no ElectricEquipment in the complete DOE model: 0, constant 0'},
                         **common)
    # B4 setpoints where the atlas has none and the DOE zone is controlled
    thermostats = reference_extras.zone_thermostats(model)
    for program_id, program in programs.items():
        missing = [k for k in ('heating_setpoint_schedule_id', 'cooling_setpoint_schedule_id')
                   if program['parameters'].get(k, {}).get('value') is None and 'filling' not in program['parameters'].get(k, {})]
        mapped = sorted(z for z, p in zone_program.items() if p == program_id)
        zones = [z for z in mapped if z in thermostats]
        if missing and zones:
            register.add(category='gap', klass='B4-setpoints', decision='fill', target=[program_id], field=missing,
                         current={'value': None}, note='Composed department and general programs resolve once their members do.',
                         source_value={'file': idf_file, 'zones': zones,
                                       'value': sorted({thermostats[z] for z in zones})}, **common)
        elif missing and mapped:
            register.add(category='gap', klass='B4-setpoints', decision='keep', reason_id='R-UNCONTROLLED',
                         target=[program_id], field=missing, current={'value': None},
                         source_value={'file': idf_file, 'zones': mapped, 'value': 'no ZoneControl:Thermostat'}, **common)
    # A4 re-tags
    for (bt, space_type), note in RETAGS.items():
        if bt == building_type:
            register.add(category='inconsistency', klass='A4-retag', decision='replace', target=[space_type],
                         field='space-type assignment', current={'value': space_type, 'note': note},
                         source_value={'file': idf_file, 'value': 'DOE zone loads and schedules'}, **common)
    # Q15 Large Office basement
    if building_type == 'LargeOffice':
        basement = next((z for z in rows if z['zone'].lower() == 'basement'), None)
        if basement:
            register.add(category='missing', klass='C8-basement-program', decision='add', target=['Basement_LargeOffice'],
                         field='program', current={'value': 'basement uses WholeBuilding - Lg Office'},
                         source_value={'file': idf_file, 'zone': 'Basement', 'value': basement['idf']}, **common)


def template_rows(register, template, idf_sample):
    common = {'source_family': 'doe-reference', 'template': template, 'building_type': None, 'target': None}
    holidays = idf_reader.Model(idf_sample).holidays()
    register.add(category='missing', klass='C1-holiday-calendar', decision='add', field='source_calendar.holidays',
                 current={'value': None}, source_value={'file': str(idf_sample.name), 'value': holidays}, **common)
    register.add(category='missing', klass='C2-daylight-saving', decision='add', field='source_calendar.daylight_saving',
                 current={'value': None}, source_value={'file': str(idf_sample.name), 'value': 'RunPeriodControl:DaylightSavingTime, not applied'}, **common)
    for klass, field, reason in (('C7-systems', 'HVAC, outdoor air, zone mixing, water heaters', 'R-SYSTEMS-DEFERRED'),
                                 ('C11-site-data', 'ground temperatures, water mains, sizing, tariffs', 'R-SITE-DATA'),
                                 ('C12-comfort-fields', 'People comfort fields', 'R-COMFORT-ONLY'),
                                 ('C13-replaceable-fraction', 'Lights replaceable fraction', 'R-DAYLIGHTING-ONLY'),
                                 ('C10-geometry', 'plan geometry, shading, skylight placement', 'R-GEOMETRY-BEMGEN')):
        register.add(category='missing', klass=klass, decision='omit', reason_id=reason, field=field,
                     current={'value': None}, source_value={'value': 'present in the DOE files'}, **common)
    register.add(category='gap', klass='midrise-apartment', decision='leave', reason_id='R-NOT-COMPARED',
                 field='all', current={'value': None}, source_value={'value': 'not compared'},
                 **dict(common, building_type='MidriseApartment'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--idf-root', type=Path, required=True)
    parser.add_argument('--standards-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=REGISTER_PATH)
    args = parser.parse_args()
    edits = documented_edits()
    rulesets = reference_schedules.standards_rulesets(args.standards_root)
    cache = {}

    def standards_index_for(days):
        signature = tuple(sorted(k for k, (_, kind) in days.items() if kind == 'Hol'))
        if signature not in cache:
            cache[signature] = reference_schedules.Index(rulesets, days)
        return cache[signature]

    geometry = {(e['template'], e['building_type']): e
                for e in json.loads((ROOT/'data/construction-inputs/geometry-v1.json').read_text())['commercial']}
    release = atlas_exports.Release()
    register = Register()
    inputs = {}
    counts = Counter()
    for vintage, template in TEMPLATES.items():
        _, standards_template, geometry_template = reference_loads.VINTAGES[vintage]
        spc = json.loads((args.standards_root/standards_template/'data'/f'{standards_template}.spc_typ.json').read_text())
        standards = {(r['building_type'], r['space_type']): r for r in spc['space_types']}
        sample = None
        for key, (building_type, folder) in reference_loads.TYPES.items():
            path = next((args.idf_root/f'refbldg_{key}_{vintage}_v1-4_7-2').glob('*5A_USA_IL_CHICAGO-OHARE.idf'))
            sample = sample or path
            inputs[path.name] = sha256(path)
            model = idf_reader.Model(path)
            load_rows = reference_loads.compare_type(model, building_type, folder, template, standards,
                                                     geometry[(geometry_template, building_type)])
            sched_rows = reference_schedules.compare_type(model, template, folder, standards_index_for)
            counts['identical schedules'] += sum(1 for r in sched_rows if r['cause'] == 'identical')
            programs = stored_programs(template, folder)
            zone_programs = zone_program_map(load_rows, building_type)
            choices, conflicts = reference_extras.slot_choices(model, zone_programs, reference_extras.zone_floors(model))
            schedule_rows(register, path.name, template, building_type, sched_rows, edits, zone_programs,
                          reference_extras.schedule_zones(model), conflicts)
            slot_rows(register, path.name, template, building_type, model, choices, programs,
                      release.suite(f'commercial/{template}/{folder}/'), edits)
            program_load_rows(register, path.name, template, building_type, load_rows)
            fraction_rows(register, path.name, template, building_type, load_rows, programs)
            component_rows(register, path.name, template, building_type, model, load_rows, programs,
                           atlas_mass(release, template, folder), geometry[(geometry_template, building_type)])
        template_rows(register, template, sample)
    summary = {'rows': len(register.rows), 'by_decision': dict(Counter(r['decision'] for r in register.rows)),
               'by_class': dict(sorted(Counter(r['klass'] for r in register.rows).items())), 'not_listed': dict(counts)}
    document = {'schema_version': '1.0.0', 'kind': 'reconciliation_register', 'adr': 'docs/adr/0037-doe-reference-reconciliation.md',
                'generated_by': 'python -m scripts.reconciliation_register', 'release_base': 'data/atlas-releases/v1.0.0',
                'input_sha256': dict(sorted(inputs.items())), 'reasons': REASONS, 'summary': summary,
                'rows': register.rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=1, default=str) + '\n', newline='\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
