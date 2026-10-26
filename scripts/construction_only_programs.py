"""Build the program definitions for the construction-only folders (ADR 0039).

python -m scripts.construction_only_programs            # write data/program-inputs/construction-only-v1.json
python -m scripts.construction_only_programs --check    # rebuild and compare

51 template x building-type folders had construction sets but no programs. This
generator runs the existing definition code for those types only, offline, from
pinned sources:
- legacy program, schedule, system and mapping records come from scripts.build's
  Builder, reading the new types' geometry and HVAC files
  (sources/construction-only-programs-lock.json) and the templates' space-type rows.
  The generic Office has no geometry file, so its programs come from the Office
  space-type rows directly;
- definition programs and HVAC systems come from scripts.program_definitions and
  scripts.hvac_definitions, limited to the new types. No completion draw or
  resolution applies to them, so their values are source values only;
- mixes come from scripts.program_composition.compose. Every new type gets a general
  mix and no department mixes. Represented areas come from each type's geometry;
  the generic Office borrows the areas of ASHRAELargeOfficeDetailed.osm, whose spaces
  carry the same Office space types. A blank "Part of Total Floor Area" flag takes
  the OS:Space default of its OSM version, "Yes", pinned in
  sources/openstudio-area-default-lock.json.
The output is a committed definition input that the release 1.2.0 overlay reads.
"""
import argparse
import copy
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from scripts.common import ROOT, load_atlas, load_json
from scripts.definition_contract import BuildContext, DefinitionBundle, evidence, load_context, stable_id
from scripts.fetch import verify_file

OUTPUT = ROOT/'data/program-inputs/construction-only-v1.json'
LOCK = ROOT/'sources/construction-only-programs-lock.json'
DEFAULTS = ROOT/'sources/openstudio-area-default-lock.json'
DEFINITIONS = ROOT/'data/definition-releases/v0.1.1'
NINETY_ONE = ('90.1-2007', '90.1-2013', '90.1-2019')
DOE_REF = ('DOE Ref Pre-1980', 'DOE Ref 1980-2004')
GEOMETRY = 'data/geometry/ASHRAE{}.osm'
# building type: (geometry stem, HVAC file stem or None, templates)
TYPES = {
    'College': ('College', 'College', NINETY_ONE + DOE_REF),
    'Courthouse': ('Courthouse', 'Courthouse', NINETY_ONE + DOE_REF),
    'Laboratory': ('Laboratory', 'Laboratory', NINETY_ONE),
    'LargeDataCenterHighITE': ('LargeDataCenterHighITE', 'LargeDataCenter', NINETY_ONE),
    'LargeDataCenterLowITE': ('LargeDataCenterLowITE', 'LargeDataCenter', NINETY_ONE),
    'SmallDataCenterHighITE': ('SmallDataCenterHighITE', 'SmallDataCenter', NINETY_ONE),
    'SmallDataCenterLowITE': ('SmallDataCenterLowITE', 'SmallDataCenter', NINETY_ONE),
    'LargeOfficeDetailed': ('LargeOfficeDetailed', 'LargeOfficeDetailed', NINETY_ONE + DOE_REF),
    'MediumOfficeDetailed': ('MediumOfficeDetailed', 'MediumOfficeDetailed', NINETY_ONE + DOE_REF),
    'SmallOfficeDetailed': ('SmallOfficeDetailed', 'SmallOfficeDetailed', NINETY_ONE + DOE_REF),
    'TallBuilding': ('TallBuildingbase', None, NINETY_ONE),
    'SuperTallBuilding': ('SuperTallBuildingbase', None, NINETY_ONE),
    'Office': (None, None, NINETY_ONE + DOE_REF),
}
OFFICE_AREAS = 'LargeOfficeDetailed'  # the generic Office borrows these represented areas


def wanted():
    return {(template, building_type) for building_type, (_, _, templates) in TYPES.items() for template in templates}


@dataclass
class Context(BuildContext):
    """The definition build context, limited to the construction-only types."""

    def includes(self, row):
        return (row.get('template'), row.get('building_type')) in wanted()


SPREADSHEET_ERRORS = ('#N/A',)


def builder(raw_root):
    """scripts.build's Builder, reading spreadsheet errors in space-type metrics as source nulls."""
    from scripts import build

    class Builder(build.Builder):
        def program(self, t, building, source_building, source_space, rows):
            clean = [{k: (None if k in METRIC_FIELDS and v in SPREADSHEET_ERRORS else v) for k, v in r.items()} for r in rows]
            rid = super().program(t, building, source_building, source_space, clean)
            index, raw = build.unique_match(rows, source_building, source_space)
            record = next(r for r in self.data['programs'] if r['id'] == rid)
            if record['source_attributes'] != raw:
                record['source_attributes'] = raw
                provenance = next(p for p in self.data['provenance'] if p['id'] == record['provenance_id'])
                for field, (original, _) in build.METRICS.items():
                    if raw.get(original) in SPREADSHEET_ERRORS:
                        provenance['fields'][field].update(original_value=raw[original], status='unresolved',
                                                           transformation='source spreadsheet error; stays unknown')
                provenance['fields']['source_attributes']['original_value'] = raw
            return rid

    METRIC_FIELDS = {original for original, _ in build.METRICS.values()}
    return Builder(raw_root)


def legacy_records(raw_root):
    """Legacy atlas records for the new types, from scripts.build's Builder."""
    b = builder(raw_root)
    lock = load_json(LOCK)
    source = {s['source_id']: s for s in lock['sources']}
    for entry in lock['files']:
        verify_file(entry, Path(raw_root))
        meta = source[entry['source_id']]
        b.data['source_files'].append({'id': stable_id_legacy('sourcefile', entry['source_id'], entry['path']), **entry,
                                       'project': meta['project'], 'repository': meta['repository'], 'version': meta['version'],
                                       'license_path': meta['license_path'], 'retrieval_date': lock['retrieval_date']})
    templates = {t['template']: t for t in b.selection['templates']}
    for building_type, (geometry, hvac, names) in TYPES.items():
        for name in names:
            t = templates[name]
            if geometry is None:
                rows = b.read('openstudio-standards', t['space_types'])['space_types']
                for row in rows:
                    if row['building_type'] == building_type:
                        b.program(t, building_type, building_type, row['space_type'], rows)
                continue
            b.model(t, {'building_type': building_type, 'geometry': GEOMETRY.format(geometry),
                        'hvac': f'data/geometry/ASHRAE{hvac}.json' if hvac else None})
    b.data['coverage_gaps'] = b.warnings
    return b.data


# User-approved fillings for the new programs (2026-10-26, ADR 0039 F1, F2): the resolution
# policy's rules extended by their criteria. Occupancy zero only for spaces with no routine
# occupants; corridors, stairs, storage, restrooms and utility rooms stay unknown.
NO_OCCUPANCY = ('shaft', 'machine room', 'data center', 'datacenter', 'computerroom', 'attic')
SHAFTS = ('shaft',)
NOTES = {
    'occupancy': 'User-approved (ADR 0039): shaft, machine room, data centre or attic with no routine modeled occupancy; transient maintenance visits excluded from this experimental variant.',
    'lighting': 'User-approved (ADR 0039): elevator or service shaft, or elevator machine room, with null source lighting; no modeled lighting.',
    'conditioning': 'User-approved (ADR 0039): elevator or service shaft with no thermostat; heating and cooling disabled; no temperature sentinel.',
    'attic': 'User-approved (ADR 0039): attic space-type row of the generic office, which has no geometry; no thermostat; heating and cooling disabled.'}


def fillings(records, packet):
    """Resolution rows for the new programs, and the fields that stay unresolved."""
    from scripts import resolve
    from scripts.common import stable_id as legacy_id
    programs = [p for p in records['programs']]
    name = lambda p: p['source_space_type'].lower().replace(' ', '')
    errors = {p['id'] for p in programs if p['source_attributes'].get('lighting_per_area') in SPREADSHEET_ERRORS}
    policy = copy.deepcopy(load_json(ROOT/'sources/resolution-policy.json'))
    policy.update(
        no_gas_equipment_program_ids=[p['id'] for p in programs if p['gas_equipment_W_m2'] is None],
        no_occupancy_program_ids=[p['id'] for p in programs if p['people_per_m2'] is None
                                  and any(t.replace(' ', '') in name(p) for t in NO_OCCUPANCY)],
        no_hot_water_program_ids=[p['id'] for p in programs if 'attic' in name(p)],
        unconditioned_program_ids=[p['id'] for p in programs if 'attic' in name(p)],
        no_lighting_program_ids=[],
        occupancy_notes={p['id']: NOTES['occupancy'] for p in programs if 'attic' not in name(p)})
    data = {'programs': programs, 'provenance': records['provenance'], 'source_files': records['source_files'],
            'mappings': records['mappings'], 'residential_archetypes': []}
    result = resolve.resolve_records(data, policy, [], None, packet)
    resolutions, provenance = result['resolutions'], {p['id']: p for p in records['provenance']}
    sources = {s['id']: s for s in records['source_files']}

    def add(row, field, value, unit, rule, note, fields):
        p = provenance[row['provenance_id']]
        s = sources[p['source_file_id']]
        proofs = [{'source_locator': s['path']+'#'+p['locator']+'/'+f, 'source_revision': s['version'],
                   'source_file_sha256': s['sha256'], 'provenance_id': p['id'],
                   'original_value': p['fields'].get(f, {}).get('original_value', row.get(f)),
                   'original_unit': p['fields'].get(f, {}).get('original_units', 'source descriptors'),
                   'transformation': p['fields'].get(f, {}).get('transformation', 'Retain source context') + '; ' + note,
                   'extraction_date': '2026-10-26', 'interpretation_note': note} for f in fields]
        resolutions.append({'id': legacy_id('resolution', 'programs', row['id'], field, rule), 'record_table': 'programs',
                            'record_id': row['id'], 'field': field, 'original_value': row.get(field), 'resolved_value': value,
                            'unit': unit, 'rule': rule, 'basis': 'research_assumption', 'note': note, 'evidence': proofs})
    constant = {'constant_value': 0, 'calendar_independent': True}
    for row in programs:
        shaft = any(t in name(row) for t in SHAFTS) or 'machineroom' in name(row)
        if (row['lighting_W_m2'] is None and row['lighting_schedule_id'] is None and row['id'] not in errors and shaft):
            add(row, 'lighting_schedule_id', constant, 'dimensionless', 'reviewed_no_lighting', NOTES['lighting'],
                ['source_attributes', 'lighting_schedule_id', 'lighting_W_m2'])
        mapped = any(m['program_id'] == row['id'] for m in records['mappings'])
        if ('attic' in name(row) and not mapped and row['heating_setpoint_schedule_id'] is None
                and row['cooling_setpoint_schedule_id'] is None):
            add(row, 'conditioning', {'heating_enabled': False, 'cooling_enabled': False}, 'state', 'reviewed_unconditioned',
                NOTES['attic'], ['source_attributes', 'heating_setpoint_schedule_id', 'cooling_setpoint_schedule_id'])
        if (any(t in name(row) for t in SHAFTS) and row['heating_setpoint_schedule_id'] is None
                and row['cooling_setpoint_schedule_id'] is None):
            add(row, 'conditioning', {'heating_enabled': False, 'cooling_enabled': False}, 'state', 'reviewed_unconditioned',
                NOTES['conditioning'], ['source_attributes', 'heating_setpoint_schedule_id', 'cooling_setpoint_schedule_id'])
    resolved = {(r['record_id'], r['field']) for r in resolutions}
    unresolved = [u for u in result['unresolved'] if (u['record_id'], u['field']) not in resolved
                  and not (u['field'].endswith('setpoint_schedule_id') and (u['record_id'], 'conditioning') in resolved)]
    return sorted(resolutions, key=lambda r: r['id']), unresolved


RECIPE = 'lib/openstudio-standards/standards/Standards.ServiceWaterHeating.rb'
GALLON_M3 = 0.003785411784


def water_packet(records, raw_root, office_area):
    """Hot-water fixture paths of the new types (ADR 0039 F4), ported from scripts.commercial_water_paths.

    The same source branches apply: no main loop (data centres), one lumped building draw
    (college, courthouse, detailed offices), per-space-type draws from the space-type rows
    (laboratory, and the tall buildings, whose prototype adds one per space with a source flow).
    The tall prototypes fix their hotel floors (9 and 17), so their booster and laundry loops
    exist and become unallocated building draws, as for the original types.
    The generic office has no prototype. By user decision it takes the large detailed office's
    lumped draw divided by that building's counted floor area, a per-area research assumption
    (`office_area`: {template: counted area}, from the borrowed geometry)."""
    from scripts import commercial_completion
    from scripts.common import stable_id as legacy_id
    completion_lock = load_json(ROOT/'sources/completion-evidence-lock.json')
    receipt = {r['path']: r for lock in (completion_lock, load_json(LOCK)) for r in lock['files'] if r['source_id'] == 'openstudio-standards'}
    cache = Path(raw_root)/'openstudio-standards'
    date = '2026-10-26'

    def proof(path, locator, value, unit, transformation, note):
        return dict(source_locator=path+'#'+locator, source_revision=REV, source_file_sha256=receipt[path]['sha256'],
                    original_value=value, original_unit=unit, transformation=transformation, extraction_date=date,
                    interpretation_note=note)
    programs, provenance = records['programs'], {p['id']: p for p in records['provenance']}
    files = {s['id']: s for s in records['source_files']}
    names = {p['id']: sorted({n for m in records['mappings'] if m['program_id'] == p['id'] for n in m['source_space_names']})
             for p in programs}

    def attrproof(p):
        pr = provenance[p['provenance_id']]
        return proof(files[pr['source_file_id']]['path'], pr['locator'], {k: v for k, v in p['source_attributes'].items() if 'water' in k},
                     'mixed original source units; gal/h, gal/h/ft2, degF', 'Keep null and empty-string fields unchanged; evaluate source branch separately',
                     'Null and empty source fields are unknown/reporting state; no zero physical water assumption')
    schedule_rows = load_json(cache/SCHEDULE_PATH)['schedules']
    scheds = defaultdict(list)
    for i, r in enumerate(schedule_rows):
        scheds[r['name']].append((i, r))
    paths, gaps, used = [], [], set()
    for building_type, (_, _, templates) in TYPES.items():
        for template in templates:
            active = [p for p in programs if (p['template'], p['building_type']) == (template, building_type)]
            if not active:
                continue
            spec = next(t for t in load_json(ROOT/'sources/selection.json')['templates'] if t['template'] == template)
            rows = load_json(cache/spec['prototype_inputs'])['prototype_inputs']
            found = [(i, r) for i, r in enumerate(rows) if r['building_type'] == building_type]
            missing = [p for p in active if p['service_water_heating_schedule_id'] is None
                       and p['source_space_type'] not in {'Attic', 'Plenum', 'Basement'}]
            if not found:  # the generic Office: no prototype, so it borrows the large detailed office's draw
                ii, r = next((i, r) for i, r in enumerate(rows) if r['building_type'] == OFFICE_AREAS)
                flow, area = r['main_service_water_peak_flowrate'], office_area[template]
                note = ('User-approved research assumption (ADR 0039, 2026-10-26): the generic office has no prototype; it takes '
                        "the large detailed office's lumped main draw divided by that building's counted floor area, "
                        'as a building draw per floor area.')
                paths.append(dict(path_id=f'{building_type}|{template}|main|borrowed-{OFFICE_AREAS}', building_type=building_type,
                                  template=template, end_use='main', source_branch='borrowed_lumped_main_draw_per_area',
                                  source_schedule_name=r['main_service_water_flowrate_schedule'], rated_flow_m3_s=None,
                                  rated_flow_per_area_m3_s_m2=flow*GALLON_M3/60/area, original_flow=flow, original_flow_unit='US gal/min',
                                  alternate_original_total=area, alternate_original_total_unit='m2 counted floor area of ASHRAELargeOfficeDetailed.osm',
                                  physical_fixture_locations=[], beneficiary_program_ids=[], allocation_status='building_service_unallocated',
                                  target_temperature_degC=(r['main_water_use_temperature']-32)/1.8,
                                  evidence=[proof(spec['prototype_inputs'], f'/prototype_inputs/{ii}/main_service_water_peak_flowrate', flow, 'US gal/min',
                                                  'Multiply by 0.003785411784/60 and divide by the borrowed counted floor area', note)],
                                  interpretation_note=note))
                used.add(r['main_service_water_flowrate_schedule'])
                path_id = paths[-1]['path_id']
                for p in missing:
                    gaps.append(dict(program_id=p['id'], building_type=building_type, template=template, source_space_type=p['source_space_type'],
                                     source_space_names=names[p['id']], classification='borrowed_building_main_draw', source_schedule_name=None,
                                     normalized_physical_flow=None, building_service_paths=[path_id], evidence=[attrproof(p)],
                                     coverage_resolution_status='allocation_unknown', zero_schedule_eligible=False))
                continue
            ii, r = found[0]
            ip = spec['prototype_inputs']
            if r['main_water_heater_volume'] is None:
                branch = 'no_main_loop'
            elif building_type in ('TallBuilding', 'SuperTallBuilding'):
                branch = 'tall_building_space_draws'
            elif r['main_service_water_peak_flowrate'] is not None:
                branch = 'lumped_main_draw'
            else:
                branch = 'space_type_main_draw'
            base = [proof(ip, '/prototype_inputs/'+str(ii), {k: v for k, v in r.items() if 'water' in k}, 'mixed source units',
                          'Evaluate main then booster then laundry source branches independently',
                          'Volumes gate loop creation; heater placement does not assign fixture beneficiaries')]
            if branch == 'lumped_main_draw':
                flow = r['main_service_water_peak_flowrate']
                paths.append(dict(path_id=f'{building_type}|{template}|main', building_type=building_type, template=template, end_use='main',
                                  source_branch=branch, source_schedule_name=r['main_service_water_flowrate_schedule'],
                                  rated_flow_m3_s=flow*GALLON_M3/60, rated_flow_per_area_m3_s_m2=None, flow_instance_count=1,
                                  physical_fixture_locations=[], beneficiary_program_ids=[], allocation_status='building_service_unallocated',
                                  target_temperature_degC=(r['main_water_use_temperature']-32)/1.8, original_flow=flow, original_flow_unit='US gal/min',
                                  evidence=[proof(ip, f'/prototype_inputs/{ii}/main_service_water_peak_flowrate', flow, 'US gal/min',
                                                  'Multiply by 0.003785411784/60 to obtain m3/s', 'A lump has no beneficiary allocation'),
                                            proof(RECIPE, 'L112-L121', 'create_water_use(...without space)', 'Ruby code',
                                                  'Use explicit fixture-space argument only', 'A lump has no beneficiary allocation')]))
                used.add(r['main_service_water_flowrate_schedule'])
            if branch in ('space_type_main_draw', 'tall_building_space_draws'):
                for p in active:
                    attrs = p['source_attributes']
                    q, total = attrs.get('service_water_heating_peak_flow_per_area'), attrs.get('service_water_heating_peak_flow_rate')
                    qnum = q if type(q) in (float, int) else 0
                    if qnum < 0.00001 and (total if type(total) in (float, int) else 0) < 0.00001:
                        continue
                    if 'plenum' in p['source_space_type'].lower():
                        continue
                    note = 'Default is_flow_per_area=true; source computes area times space multiplier once. Fixture helper call omits physical space.'
                    paths.append(dict(path_id=f'{building_type}|{template}|main|{p["id"]}', building_type=building_type, template=template,
                                      end_use='main', source_branch=branch, source_schedule_name=attrs.get('service_water_heating_schedule'),
                                      rated_flow_m3_s=None, rated_flow_per_area_m3_s_m2=qnum*GALLON_M3/3600/0.09290304 if type(q) in (int, float) else None,
                                      original_flow=q, original_flow_unit='US gal/h/ft2', alternate_original_total=total,
                                      alternate_original_total_unit='US gal/h (unused default path)', source_space_names=names[p['id']],
                                      physical_fixture_locations=[], beneficiary_program_ids=[p['id']], allocation_status='exact_source_space_type_tag',
                                      target_temperature_degC=(attrs['service_water_heating_target_temperature']-32)/1.8
                                      if type(attrs.get('service_water_heating_target_temperature')) in (int, float) else None,
                                      evidence=[attrproof(p), proof(RECIPE, 'L122-L171 and L236-L307', 'default is_flow_per_area=true; create_water_use(...without space)',
                                                                   'Ruby code', 'Convert flow with factor 0.003785411784/3600/0.09290304; no geometry assumed', note)],
                                      interpretation_note=note))
                    used.add(attrs.get('service_water_heating_schedule'))
            if branch == 'tall_building_space_draws':
                prototype = f'lib/openstudio-standards/prototypes/common/buildings/Prototype.{building_type}.rb'
                lines = (cache/prototype).read_text().splitlines()
                line = next(i for i, l in enumerate(lines) if 'num_of_floor_hotel:' in l)
                hotel = int(lines[line].split(':')[1].strip().rstrip(','))
                for use, prefix, minimum in (('booster', 'booster', 0), ('laundry', 'laundry', 1)):
                    if r[prefix+'_water_heater_volume'] is None or hotel <= minimum:
                        continue
                    flow, temp, schedule = (r[prefix+'_service_water_peak_flowrate'], r[prefix+'_water_use_temperature'],
                                            r[prefix+'_service_water_flowrate_schedule'])
                    used.add(schedule)
                    paths.append(dict(path_id=f'{building_type}|{template}|{use}', building_type=building_type, template=template, end_use=use,
                                      source_branch='tall_building_hotel_floors', source_schedule_name=schedule,
                                      rated_flow_m3_s=flow*GALLON_M3/60 if type(flow) in (int, float) else None, rated_flow_per_area_m3_s_m2=None,
                                      original_flow=flow, original_flow_unit='US gal/min',
                                      target_temperature_degC=(temp-32)/1.8 if type(temp) in (int, float) else None,
                                      physical_fixture_locations=[], beneficiary_program_ids=[], allocation_status='building_service_unallocated',
                                      evidence=[proof(ip, f'/prototype_inputs/{ii}/{prefix}_service_water_peak_flowrate', flow, 'US gal/min',
                                                      'Multiply by 0.003785411784/60; preserve original null', 'Loop volume enables draw; no beneficiary allocation'),
                                                proof(prototype, f'L{line + 1}', lines[line].strip(), 'Ruby code',
                                                      f'{use} loop when the fixed hotel-floor count exceeds {minimum}',
                                                      'Prototype additional parameters fix the hotel floors')]))
            else:
                for use, prefix in (('booster', 'booster'), ('laundry', 'laundry')):
                    if r[prefix+'_water_heater_volume'] is not None:
                        raise ValueError(f'Unported {use} loop for {building_type} {template}')
            served = {pid for d in paths if (d['building_type'], d['template']) == (building_type, template) for pid in d['beneficiary_program_ids']}
            unallocated = [d['path_id'] for d in paths if (d['building_type'], d['template']) == (building_type, template)
                           and d['allocation_status'] == 'building_service_unallocated']
            for p in missing:
                if p['id'] in served:
                    continue
                if branch == 'no_main_loop' and r['booster_water_heater_volume'] is None and r['laundry_water_heater_volume'] is None:
                    status = 'source_no_swh_end_use_for_building_template'
                elif branch == 'space_type_main_draw':
                    status = 'source_no_local_main_fixture_draw'
                elif branch == 'tall_building_space_draws':
                    status = 'unallocated_building_booster_or_laundry'
                else:
                    status = 'unallocated_building_main_draw'
                zero = status in ('source_no_swh_end_use_for_building_template', 'source_no_local_main_fixture_draw') and not unallocated
                gaps.append(dict(program_id=p['id'], building_type=building_type, template=template, source_space_type=p['source_space_type'],
                                 source_space_names=names[p['id']], classification=status, source_schedule_name=None,
                                 normalized_physical_flow=None, building_service_paths=unallocated,
                                 evidence=[attrproof(p), *base], coverage_resolution_status='source_proved_no_modeled_program_draw' if zero else 'allocation_unknown',
                                 zero_schedule_eligible=zero))
    schedules = []
    for name in sorted(n for n in used if n):
        rows = scheds[name]
        if not rows:
            raise ValueError('No source schedule '+name)
        peak = max(v for _, row in rows for v in row['values'])
        schedules.append(dict(source_name=name, status='source_rules_extracted', source_order=[i for i, _ in rows],
                              source_rows=[row for _, row in rows], peak_divisor=peak,
                              matching_atlas_schedule_ids=[s['id'] for s in records['schedules'] if s.get('source_name') == name],
                              evidence=[proof(SCHEDULE_PATH, '/schedules/'+str(i), row, 'dimensionless draw fraction (source units retained)',
                                              'No rule sorting or date truncation; optional equivalent divides values by max and multiplies rated flow by max',
                                              'Rules, design days, source dates and source order retained') for i, row in rows]))
    for d in paths:
        d['matching_atlas_schedule_ids'] = [s['id'] for s in records['schedules'] if s.get('source_name') == d['source_schedule_name']]
        d['allocation_weights'] = {pid: 1 for pid in d['beneficiary_program_ids']} if len(d['beneficiary_program_ids']) == 1 else {}
    packet = {'draw_paths': paths, 'missing_program_evidence': gaps, 'schedules': schedules, 'controls': [], 'summary': {}}
    for s in packet['schedules']:
        s['normalized_source_rows'] = copy.deepcopy(s['source_rows'])
        for row in s['normalized_source_rows']:
            row['values'] = [v/s['peak_divisor'] if s['peak_divisor'] else 0.0 for v in row['values']]

        def schedule(variant, source_rows, s=s):
            return dict(id=legacy_id('completion_schedule', s['source_name'], variant), source_name=s['source_name']+' ('+variant+')',
                        schedule_type='fraction', units='dimensionless', time_resolution_minutes=60, interpolation='none',
                        rules=[{**{k: row[k] for k in ('day_types', 'start_date', 'end_date', 'type', 'values')}, 'source_index': i,
                                'source_units': row['units'], 'source_category': row['category']} for i, row in zip(s['source_order'], source_rows)])
        s['source_schedule'] = schedule('source draw fractions', s['source_rows'])
        s['equivalent_schedule'] = schedule('peak normalized draw', s['normalized_source_rows'])
    by_name = {s['source_name']: s for s in packet['schedules']}
    for d in paths:
        s = by_name[d['source_schedule_name']]
        d['equivalent_schedule_id'] = s['equivalent_schedule']['id']
        d['equivalent_peak_flow_m3_s'] = None if d['rated_flow_m3_s'] is None else d['rated_flow_m3_s']*s['peak_divisor']
        d['equivalent_peak_flow_per_area_m3_s_m2'] = None if d['rated_flow_per_area_m3_s_m2'] is None else d['rated_flow_per_area_m3_s_m2']*s['peak_divisor']
        d['evidence'] += s['evidence']
        d['interpretation_note'] = d.get('interpretation_note', '')+' Mixed fixture draw, not heater energy/circulation. Apply each source fixture once; represented area and multiplier once. Unallocated services are not copied to programs.'
    evidence = {}

    def compact(value):
        if isinstance(value, dict):
            for key in list(value):
                if key == 'evidence':
                    ids = []
                    for e in value.pop(key):
                        i = legacy_id('completion_evidence', e)
                        evidence[i] = e
                        ids.append(i)
                    value['evidence_ids'] = ids
                else:
                    compact(value[key])
        elif isinstance(value, list):
            for v in value:
                compact(v)
    compact(packet)
    packet['evidence'] = dict(sorted(evidence.items()))
    commercial_completion.validate_packet(packet)
    return packet


REV = 'c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907'
from scripts.build import SCHEDULE_PATH  # noqa: E402


def stable_id_legacy(*parts):
    from scripts.common import stable_id as legacy
    return legacy(*parts)


def area_defaults(raw_root):
    """{OSM version: evidence}, the pinned OS:Space default of Part of Total Floor Area."""
    lock = load_json(DEFAULTS)
    out = {}
    for entry in lock['files']:
        verify_file(entry, Path(raw_root))
        if entry['path'] == 'OpenStudio.idd':
            text = (Path(raw_root)/entry['source_id']/entry['path']).read_text(encoding='utf-8', errors='replace').splitlines()
            line = next(i for i, l in enumerate(text) if 'Part of Total Floor Area' in l and l.strip().startswith('A'))
            default = next(l.split('\\default', 1)[1].strip() for l in text[line:line+8] if '\\default' in l)
            out[entry['openstudio_version']] = {'default': default, 'locator': f'{entry["url"]}#L{line + 1}', 'sha256': entry['sha256']}
    return out


def areas(context, raw_root, records, defaults):
    """extract_areas for the new types: represented counted area per legacy program."""
    from scripts.fetch import fetch_file
    from scripts.semantics import osm_objects, spaces
    from scripts.water_reporting import floor_areas
    files = {r['path']: r for r in records['source_files'] if r['source_id'] == 'openstudio-standards'}
    by_key = defaultdict(list)
    for p in records['programs']:
        by_key[(p['building_type'], p['template'])].append(p)
    result, used = {}, set()
    for building_type, (geometry, _, names) in TYPES.items():
        stem = geometry or OFFICE_AREAS
        path = GEOMETRY.format(stem)
        text = fetch_file(files[path], Path(raw_root)).read_text(encoding='utf-8-sig')
        version = next(o['fields']['Version Identifier'] for o in osm_objects(text) if o['kind'] == 'OS:Version')
        ss, area = spaces(text), floor_areas(text)
        if any(s['part_of_total_floor_area'] == '' for s in ss):
            if defaults.get(version, {}).get('default') != 'Yes':
                raise ValueError(f'No pinned Part of Total Floor Area default for OSM version {version} ({path})')
            used.add(version)
            for s in ss:
                if s['part_of_total_floor_area'] == '':
                    s['part_of_total_floor_area'] = 'Yes'
        for name in names:
            lookup = {(p['source_building_type'], p['source_space_type']): p for p in by_key[(building_type, name)]}
            grouped = defaultdict(list)
            for s in ss:
                p = lookup.get((s['source_building_type'], s['source_space_type']))
                if p:
                    grouped[p['id']].append(s)
            rows = []
            for p in by_key[(building_type, name)]:
                matches = grouped[p['id']]
                counted = [s for s in matches if s['part_of_total_floor_area'] == 'Yes']
                rows.append({'program_id': p['id'], 'source_space_type': p['source_space_type'],
                             'source_building_type': p['source_building_type'],
                             'represented_area_m2': math.fsum(area[s['handle']]*s['multiplier'] for s in counted),
                             'area_status': 'derived' if counted else ('non_counted' if matches else 'no_geometry'),
                             'source_file_id': files[path]['id'], 'geometry_path': path,
                             'space_handles': [s['handle'] for s in counted],
                             'uncounted_space_handles': [s['handle'] for s in matches if s not in counted]})
            result[(building_type, name)] = rows
    return result, sorted(used)


def recipe_groups(family, names):
    """Every new type: a general mix over its counted programs, no departments (ADR 0039)."""
    available = sorted(n for n in names if not any(t in n.lower() for t in ('basement', 'attic')))
    return {'departments': {}, 'general': available if len(available) > 1 else []}


def build(raw_root=ROOT/'data/raw'):
    from scripts import program_composition
    from scripts.hvac_definitions import build_hvac
    from scripts.program_definitions import build_programs
    records = legacy_records(raw_root)
    base = load_context(scope='full')
    legacy = load_atlas(ROOT/base.policy['dependencies']['atlas'])
    atlas = copy.deepcopy(legacy)
    for table in ('programs', 'schedules', 'systems', 'mappings', 'provenance', 'source_files'):
        known = {r['id'] for r in atlas[table]}
        atlas[table] += [r for r in records[table] if r['id'] not in known]
    defaults = area_defaults(raw_root)
    table, used = areas(None, raw_root, records, defaults)
    office_area = {t: math.fsum(r['represented_area_m2'] for r in table[(OFFICE_AREAS, t)] if r['area_status'] == 'derived')
                   for t in TYPES['Office'][2]}
    packet = water_packet(records, raw_root, office_area)
    resolutions, unresolved = fillings(records, packet)
    # apply_reviewed and the service build read the policy's resolution and completion releases: point
    # them at the frozen releases' rows plus the new ones, in a scratch folder of the build tree.
    import tempfile
    (ROOT/'build').mkdir(exist_ok=True)
    scratch = tempfile.TemporaryDirectory(dir=ROOT/'build')
    frozen = load_json(ROOT/base.policy['dependencies']['resolution']/'resolutions.json')
    (Path(scratch.name)/'resolutions.json').write_text(json.dumps({**frozen, 'resolutions': frozen['resolutions'] + resolutions}))
    completion = load_json(ROOT/base.policy['dependencies']['completion']/'commercial-completion.json')
    merged = {**completion, 'draw_paths': completion['draw_paths'] + packet['draw_paths'],
              'schedules': completion['schedules'] + packet['schedules'], 'evidence': {**completion['evidence'], **packet['evidence']}}
    (Path(scratch.name)/'commercial-completion.json').write_text(json.dumps(merged))
    policy = copy.deepcopy(base.policy)
    policy['dependencies']['resolution'] = policy['dependencies']['completion'] = Path(scratch.name).relative_to(ROOT).as_posix()
    context = Context(base.root, base.scope, atlas, policy, base.sources, base.extraction_date, base.dependencies)
    bundle = DefinitionBundle()
    programs = build_programs(context)
    scratch.cleanup()
    bundle.merge(programs).merge(build_hvac(context))
    saved = (program_composition.extract_areas, program_composition.recipe_groups)
    program_composition.extract_areas = lambda ctx: table
    program_composition.recipe_groups = recipe_groups
    try:
        bundle.merge(program_composition.compose(context, bundle))
    finally:
        program_composition.extract_areas, program_composition.recipe_groups = saved
    # Schedule provenance, as scripts.definitions.build retains it.
    for source in atlas['provenance']:
        if source['id'] in {r.get('provenance_id') for r in bundle['schedules']}:
            bundle['provenance'].append({'id': source['id'], 'source_file_id': source['source_file_id'],
                'locator': source['locator'], 'original_value': source['fields'], 'original_unit': 'mixed source fields',
                'transformation': 'retained schedule provenance; field-specific conversions preserved',
                'extraction_date': source['extraction_date'], 'interpretation': source['notes']})
    existing = {table: {r['id'] for r in load_json(DEFINITIONS/f'{table}.json')}
                for table in ('schedules', 'components', 'provenance', 'source_files')}
    sources = {r['id']: r for r in atlas['source_files']}
    cited = set(json.dumps(bundle).split('"')) & sources.keys()
    out = {
        'schema_version': '1.0.0', 'kind': 'construction_only_program_definitions',
        'adr': 'docs/adr/0039-construction-only-programs.md', 'generated_by': 'python -m scripts.construction_only_programs',
        'definition_release': 'data/definition-releases/v0.1.1',
        'input_sha256': {p: sha(ROOT/p) for p in ('sources/construction-only-programs-lock.json',
                                                   'sources/openstudio-area-default-lock.json', 'sources/lock.json')},
        'area_defaults': {v: defaults[v] for v in used},
        'programs': bundle['programs'], 'compositions': bundle['compositions'], 'hvac_systems': bundle['hvac_systems'],
        'schedules': [r for r in bundle['schedules'] if r['id'] not in existing['schedules']],
        'components': [r for r in bundle['components'] if r['id'] not in existing['components']],
        'provenance': [r for r in bundle['provenance'] if r['id'] not in existing['provenance']],
        'source_files': [r for r in (sources[i] for i in sorted(cited)) if r['id'] not in existing['source_files']],
        'coverage_gaps': sorted(records['coverage_gaps'], key=json.dumps),
        'resolutions': resolutions, 'unresolved': sorted(unresolved, key=json.dumps),
        'services': bundle['services'], 'completion_evidence': packet['evidence'],
        'water_paths': {'draw_paths': packet['draw_paths'], 'missing_program_evidence': packet['missing_program_evidence']},
    }
    return out


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(document):
    return (json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--raw-root', type=Path, default=ROOT/'data/raw')
    args = parser.parse_args()
    data = encode(build(args.raw_root))
    if args.check:
        if OUTPUT.read_bytes() != data:
            raise SystemExit(f'{OUTPUT.relative_to(ROOT)} does not reproduce; run python -m scripts.construction_only_programs')
        print('Construction-only program definitions reproduce')
        return
    OUTPUT.write_bytes(data)
    document = json.loads(data)
    print(f"{len(document['programs'])} programs, {len(document['compositions'])} compositions, "
          f"{len(document['hvac_systems'])} HVAC systems, {len(document['coverage_gaps'])} unmapped spaces")


if __name__ == '__main__':
    main()
