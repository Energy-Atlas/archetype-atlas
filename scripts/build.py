"""Build deterministic source-input tables from immutable locked raw blobs."""
import argparse
import collections
import csv
import json
import re
from pathlib import Path

from scripts.common import ROOT, TABLES, UNITS, VERSION, dump_json, load_json, stable_id
from scripts.fetch import verify_file
from scripts.semantics import convert, spaces, unique_match, option_rows

SCHEDULE_PATH = 'lib/openstudio-standards/standards/ashrae_90_1/data/ashrae_90_1.schedules.json'
CLIMATE_PATH = 'lib/openstudio-standards/standards/ashrae_90_1/data/ashrae_90_1.climate_zone_sets.json'
METRICS = {
    'people_per_m2': ('occupancy_per_area', 'people/1000 ft2'),
    'lighting_W_m2': ('lighting_per_area', 'W/ft2'),
    'additional_lighting_W_m2': ('additional_lighting_per_area', 'W/ft2'),
    'electric_equipment_W_m2': ('electric_equipment_per_area', 'W/ft2'),
    'gas_equipment_W_m2': ('gas_equipment_per_area', 'Btu/h-ft2'),
    'ventilation_m3_s_m2': ('ventilation_per_area', 'cfm/ft2'),
    'ventilation_m3_s_person': ('ventilation_per_person', 'cfm/person'),
    'ventilation_ach': ('ventilation_air_changes', '1/h'),
}
SCHEDULE_FIELDS = {
    'occupancy_schedule_id': ('occupancy_schedule', 'fraction'),
    'lighting_schedule_id': ('lighting_schedule', 'fraction'),
    'electric_equipment_schedule_id': ('electric_equipment_schedule', 'fraction'),
    'gas_equipment_schedule_id': ('gas_equipment_schedule', 'fraction'),
    'heating_setpoint_schedule_id': ('heating_setpoint_schedule', 'temperature'),
    'cooling_setpoint_schedule_id': ('cooling_setpoint_schedule', 'temperature'),
    'activity_schedule_id': ('occupancy_activity_schedule', 'activity'),
    'service_water_heating_schedule_id': ('service_water_heating_schedule', 'fraction'),
}


def slug(text):
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def program_name(text):
    if text.startswith('WholeBuilding - ') and 'Office' in text:
        return 'office'
    if text.startswith('Apartment'):
        return 'apartment_unit'
    return slug(text)


class Builder:
    def __init__(self, raw_root):
        self.raw_root = Path(raw_root)
        self.lock = load_json(ROOT/'sources/lock.json')
        self.selection = load_json(ROOT/'sources/selection.json')
        self.entries = {(e['source_id'], e['path']): e for e in self.lock['files']}
        self.sources = {s['source_id']: s for s in self.lock['sources']}
        self.data = {'schema_version': VERSION, 'units': UNITS.copy(),
                     'templates': [t['template'] for t in self.selection['templates']] + [self.selection['residential_template']],
                     'building_types': self.selection['buildings'],
                     'climate_zone_sets': [], 'scope': 'source_inputs_with_explicit_gaps'}
        self.data.update({t: [] for t in TABLES})
        self.schedule_cache = {}
        self.used_programs = {}
        self.warnings = []
        # Verify every locked blob before parsing any source; no network during build.
        for entry in self.lock['files']:
            verify_file(entry, self.raw_root)
            source = self.sources[entry['source_id']]
            self.data['source_files'].append({
                'id': stable_id('sourcefile', entry['source_id'], entry['path']),
                **entry, 'project': source['project'], 'repository': source['repository'],
                'version': source['version'], 'license_path': source['license_path'],
                'retrieval_date': self.lock['retrieval_date'],
            })
        self.schedule_rows = self.read('openstudio-standards', SCHEDULE_PATH)['schedules']
        self.schedule_index = collections.defaultdict(list)
        for i, r in enumerate(self.schedule_rows):
            self.schedule_index[r['name']].append((i, r))
        climate = self.read('openstudio-standards', CLIMATE_PATH)['climate_zone_sets']
        self.data['climate_zone_sets'] = sorted(r['name'] for r in climate)

    def read(self, source_id, path):
        return load_json(self.raw_root/source_id/path)

    def add(self, table, record, source_id, path, locator, raw, specs=None, note=None):
        """Attach a provenance entry for every canonical field, including nulls."""
        specs = specs or {}
        pid = stable_id('provenance', table, record['id'])
        fields = {}
        for key, value in record.items():
            if key == 'id':
                continue
            original, unit, transform = specs.get(key, (key, 'source text', 'identity'))
            original_value = (raw if original == 'source row' else raw.get(original)) if isinstance(raw, dict) else raw
            if transform == 'identity' and original not in raw:
                transform = 'atlas metadata or explicit unresolved value; see notes'
            fields[key] = {'original_field': original, 'original_units': unit,
                           'original_value': original_value, 'transformation': transform,
                           'status': 'unresolved' if value is None else 'normalized'}
        self.data['provenance'].append({
            'id': pid, 'table': table, 'record_id': record['id'],
            'source_file_id': stable_id('sourcefile', source_id, path),
            'locator': locator, 'extraction_date': self.lock['retrieval_date'],
            'confidence': 'direct_source_with_documented_transformations',
            'notes': note or 'Source inputs; no defaults substituted for null fields.',
            'fields': fields,
        })
        record['provenance_id'] = pid
        self.data[table].append(record)
        return record['id']

    def schedule(self, name, kind):
        if name is None or name == '':
            return None
        key = (name, kind)
        if key in self.schedule_cache:
            return self.schedule_cache[key]
        matches = self.schedule_index.get(name, [])
        if not matches:
            raise ValueError(f'Missing source schedule: {name}')
        # A name may serve different physical roles. IDs include the role so that
        # schedule bounds/units cannot depend on whichever program was read first.
        rules = []
        for i, r in matches:
            rules.append({k: r[k] for k in ['day_types', 'start_date', 'end_date', 'type', 'values']}
                         | {'source_index': i, 'source_units': r['units'], 'source_category': r['category']})
        sid = stable_id('schedule', 'openstudio-standards', name, kind)
        record = {'id': sid, 'source_name': name, 'schedule_type': kind,
                  'units': {'fraction': 'dimensionless', 'temperature': 'C', 'activity': 'W/person'}[kind],
                  'time_resolution_minutes': 60, 'interpolation': 'none', 'rules': rules}
        self.add('schedules', record, 'openstudio-standards', SCHEDULE_PATH,
                 'schedules indices ' + ','.join(str(i) for i, _ in matches),
                 {'source_name': name, 'rules': [r for _, r in matches]},
                 {'rules': ('rules', 'source units preserved per rule', 'retain order and values exactly'),
                  'units': ('rules', 'source units / category', 'role from referring field; temperature C verified'),
                  'schedule_type': ('source_name', 'source text', 'role from referring field')},
                 'Rule source order retained; fractional units may be absent upstream. '
                 'Roles follow referring fields. No annual calendar or weather applied.')
        self.schedule_cache[key] = sid
        return sid

    def program(self, t, building, source_building, source_space, rows):
        key = (t['template'], building, source_building, source_space)
        if key in self.used_programs:
            return self.used_programs[key]
        index, raw = unique_match(rows, source_building, source_space)
        rid = stable_id('program', 'openstudio-standards', *key)
        record = {'id': rid, 'building_type': building, 'program': program_name(source_space),
                  'template': t['template'], 'variant': slug(source_space),
                  'source_building_type': source_building, 'source_space_type': source_space,
                  'source_family': t['family'], 'infiltration_m3_s_m2': None,
                  'infiltration_basis': None, 'source_attributes': raw}
        specs = {
            'building_type': ('building_type', 'source text', 'associate source OSM with prototype building type'),
            'source_building_type': ('building_type', 'source text', 'identity'),
            'source_space_type': ('space_type', 'source text', 'identity'),
            'program': ('space_type', 'source text', 'explicit vocabulary: office/apartment_unit; otherwise reversible slug'),
            'variant': ('space_type', 'source text', 'slug; preserve distinct source-space identities'),
            'source_attributes': ('source row', 'mixed upstream units', 'retain complete original row as evidence'),
        }
        for field, (original, unit) in METRICS.items():
            record[field] = convert(raw.get(original), unit)
            specs[field] = (original, unit, f'convert {unit} to {UNITS[field]}; null stays null')
        for field, (original, kind) in SCHEDULE_FIELDS.items():
            record[field] = self.schedule(raw.get(original), kind)
            specs[field] = (original, 'schedule name', f'resolve schedule ID with role {kind}')
        self.add('programs', record, 'openstudio-standards', t['space_types'],
                 f'/space_types/{index}', raw, specs,
                 'Pre-control standards inputs; additional lighting remains separate. '
                 'Infiltration is not reported in this space-type table. '
                 'Other source fields retained as evidence with upstream units, not silently applied.')
        self.used_programs[key] = rid
        return rid

    def model(self, t, model):
        building = model['building_type']
        rows = self.read('openstudio-standards', t['space_types'])['space_types']
        text = (self.raw_root/'openstudio-standards'/model['geometry']).read_text(encoding='utf-8')
        source_spaces = spaces(text)
        hvac = self.read('openstudio-standards', model['hvac']) if model['hvac'] else []
        assignments = collections.defaultdict(list)
        for i, raw in enumerate(hvac):
            rid = stable_id('system', t['template'], building, model['hvac'], i)
            record = {'id': rid, 'building_type': building, 'template': t['template'],
                      'source_family': t['family'], 'variant': f'source_system_{i}',
                      'climate_zone_set': None, 'system_type': raw['type'],
                      'heating_type': raw.get('heating_type'), 'heating_fuel': None,
                      'cooling_type': raw.get('cooling_type'), 'efficiency_or_cop': None,
                      'zone_terminal_type': None, 'ventilation_strategy': None,
                      'system_schedule_id': self.schedule(raw.get('operation_schedule'), 'fraction'),
                      'oa_schedule_id': self.schedule(raw.get('oa_damper_schedule'), 'fraction'),
                      'source_attributes': {k: v for k, v in raw.items() if k != 'space_names'}}
            self.add('systems', record, 'openstudio-standards', model['hvac'], f'/{i}', raw,
                     {'system_type': ('type', 'source text', 'identity'),
                      'system_schedule_id': ('operation_schedule', 'schedule name', 'resolve typed ID'),
                      'oa_schedule_id': ('oa_damper_schedule', 'schedule name', 'resolve typed ID'),
                      'source_attributes': ('source row', 'mixed upstream units', 'retain descriptors except space_names')},
                     'HVAC map inputs; Ruby generation, sizing and climate-specific efficiency selection '
                     'not executed. Null COP/terminal/fuel/strategy require downstream resolution.')
            for name in raw.get('space_names', []):
                assignments[name].append(rid)
        groups = collections.defaultdict(list)
        for space in source_spaces:
            source_building = space['source_building_type']
            source_space = space['source_space_type']
            if not source_building and source_space == 'Plenum':
                source_building = 'Any'
            if not source_building or not source_space:
                self.warnings.append({'template': t['template'], 'building_type': building,
                                      'space': space['name'], 'reason': 'No standards space-type tags; excluded, not guessed'})
                continue
            matches = [r for r in rows if r['building_type'] == source_building and r['space_type'] == source_space]
            if not matches:
                self.warnings.append({'template': t['template'], 'building_type': building,
                                      'space': space['name'], 'reason': f'No exact standards row for {source_building}/{source_space}'})
                continue
            pid = self.program(t, building, source_building, source_space, rows)
            systems = assignments.get(space['name'], [None])
            for sid in systems:
                groups[(pid, sid)].append(space)
        for (pid, sid), group in groups.items():
            rid = stable_id('mapping', t['template'], building, pid, sid)
            record = {'id': rid, 'building_type': building, 'template': t['template'],
                      'program_id': pid, 'system_id': sid, 'area_fraction': None,
                      'multiplicity': sum(s['multiplier'] for s in group), 'conditioned': None,
                      'source_space_names': [s['name'] for s in group],
                      'part_of_total_floor_area': sorted(set(s['part_of_total_floor_area'] for s in group))}
            self.add('mappings', record, 'openstudio-standards', model['geometry'],
                     'OS:Space handles ' + ','.join(s['handle'] for s in group),
                     {'spaces': group, 'Part of Total Floor Area': [s['part_of_total_floor_area'] for s in group]},
                     {'multiplicity': ('spaces', 'zone multiplier/count', 'sum source thermal-zone multipliers'),
                      'source_space_names': ('spaces', 'source text', 'group exact source names by program and system'),
                      'program_id': ('spaces', 'source text', 'exact standards-tag lookup'),
                      'part_of_total_floor_area': ('Part of Total Floor Area', 'source Yes/No flag',
                                                  'sorted distinct flags from source OS:Space objects'),
                      'system_id': ('spaces', 'source text', 'exact space name join to HVAC JSON; null if unassigned')},
                     'Mapping counts are source benchmark context. Area fractions and conditioned '
                     'state are unresolved: no geometric evaluation or thermostat generation. '
                     'One space may have multiple HVAC services; counts across systems need not be additive.')

    def envelope(self, t):
        rows = self.read('openstudio-standards', t['envelope'])['construction_properties']
        for i, raw in enumerate(rows):
            if raw['intended_surface_type'] not in {'ExteriorWall', 'ExteriorRoof', 'ExteriorFloor', 'ExteriorWindow'}:
                continue
            invalid_u = raw.get('assembly_maximum_u_value') == 0
            record = {'id': stable_id('envelope', t['template'], t['envelope'], i),
                      'template': t['template'], 'source_family': t['family'],
                      'climate_zone_set': raw['climate_zone_set'],
                      'surface_type': raw['intended_surface_type'],
                      'construction_type': raw['standards_construction_type'],
                      'building_category': raw['building_category'],
                      'u_W_m2_K': None if invalid_u else convert(raw.get('assembly_maximum_u_value'), 'Btu/h-ft2-F'),
                      'shgc': raw.get('assembly_maximum_solar_heat_gain_coefficient'),
                      'visible_transmittance': raw.get('assembly_minimum_visible_transmittance'),
                      'value_basis': 'unresolved_invalid_source' if invalid_u else 'source_assembly_limit_or_target',
                      'source_attributes': raw}
            source_u = raw.get('assembly_maximum_u_value_unit')
            if record['u_W_m2_K'] is not None and source_u not in {None, 'Btu/h-ft2-F'}:
                raise ValueError(f'Unrecognized envelope units: {source_u}')
            self.add('envelope_components', record, 'openstudio-standards', t['envelope'],
                     f'/construction_properties/{i}', raw,
                     {'surface_type': ('intended_surface_type', 'source text', 'identity'),
                      'construction_type': ('standards_construction_type', 'source text', 'identity'),
                      'u_W_m2_K': ('assembly_maximum_u_value', source_u or 'Btu/h-ft2-F (legacy convention)',
                                    'withhold impossible source zero as null; original zero preserved' if invalid_u else 'multiply by 5.678263341113487'),
                      'shgc': ('assembly_maximum_solar_heat_gain_coefficient', 'dimensionless', 'identity'),
                      'visible_transmittance': ('assembly_minimum_visible_transmittance', 'dimensionless', 'identity'),
                      'source_attributes': ('source row', 'mixed upstream units', 'retain all constraints/films/operation types')},
                     'Conditional assembly limit/target; not material-layer construction. '
                     'All window percentage/projection and category predicates remain in source_attributes. '
                     'Legacy missing unit labels use standards IP construction convention explicitly. '
                     + ('Source zero U-value is invalid and withheld; no substitute chosen.' if invalid_u else ''))

    def efficiencies(self, t):
        for path in t['efficiency_files']:
            tables = self.read('openstudio-standards', path)
            for key, rows in tables.items():
                for i, raw in enumerate(rows):
                    metrics = {k: v for k, v in raw.items() if v is not None and
                               (k.startswith('minimum_') and any(x in k for x in ['efficiency', 'coefficient', 'eer', 'cop', 'hspf', 'performance']))}
                    record = {'id': stable_id('efficiency', t['template'], path, key, i),
                              'template': t['template'], 'equipment_table': key,
                              'metrics': metrics, 'source_attributes': raw,
                              'assignment_status': 'conditional_unassigned'}
                    self.add('efficiency_rules', record, 'openstudio-standards', path, f'/{key}/{i}', raw,
                             {'metrics': ('source row', 'metric-specific IP ratings or dimensionless efficiency',
                                          'retain named efficiency metrics; no SEER-to-COP substitution'),
                              'source_attributes': ('source row', 'mixed IP/source units', 'retain capacity/subtype/date/fuel qualifiers')},
                             'Capacity-dependent rules, not installed performance. Capacity units follow '
                             'standards equipment lookup (Btu/h); ratings retain metric-specific meaning.')

    def specialized(self, t):
        for path in t.get('specialized_files', []):
            for kind, rows in self.read('openstudio-standards', path).items():
                for i, raw in enumerate(rows):
                    record = {'id': stable_id('specialized', t['template'], path, i),
                              'template': t['template'], 'source_family': t['family'],
                              'rule_type': kind, 'source_attributes': raw}
                    self.add('specialized_rules', record, 'openstudio-standards', path, f'/{kind}/{i}', raw,
                             {'source_attributes': ('source row', 'field-specific upstream units',
                                                    'retain specialized source rules; no unconditional SI interpretation')},
                             'Conditional refrigeration evidence, not installed loads or selected equipment. '
                             'Capacity curves, size categories and schedules require generator resolution. '
                             'Raw numeric units remain source-specific; no guesses applied.')

    def residential(self):
        from scripts.residential import selected_pairs
        selected = selected_pairs(self)
        path = 'resources/options_lookup.tsv'
        wanted = {'Heating Setpoint', 'Cooling Setpoint', 'Occupants', 'Infiltration',
                  'Plug Loads', 'Lighting', 'HVAC Heating Efficiency', 'Geometry Building Type RECS'}
        text = (self.raw_root/'resstock'/path).read_text(encoding='utf-8')
        for line_number, cols, context_line in option_rows(text):
            if (cols[0] not in wanted and (cols[0], cols[1]) not in selected) or len(cols) < 3 or not cols[2]:
                continue
            args = dict(c.split('=', 1) for c in cols[3:] if '=' in c)
            # Rows without measure arguments cannot supply deterministic semantics.
            if not args:
                continue
            record = {'id': stable_id('residential', cols[0], cols[1], line_number),
                      'parameter': cols[0], 'option': cols[1], 'measure': cols[2],
                      'arguments': args, 'applicability': 'dwelling_unit_option_requires_complete_resstock_configuration',
                      'normalized_value': None, 'normalized_units': None}
            specs = {'parameter': ('parameter', 'source text', 'identity'), 'option': ('option', 'source text', 'identity'),
                     'arguments': ('arguments', 'measure-argument-specific', 'split argument=value; preserve strings')}
            if cols[0] in {'Heating Setpoint', 'Cooling Setpoint'}:
                prefix = 'heating' if cols[0] == 'Heating Setpoint' else 'cooling'
                arg = f'hvac_control_{prefix}_weekday_setpoint_temp'
                if arg in args:
                    record['normalized_value'] = convert(float(args[arg]), 'F')
                    record['normalized_units'] = 'C'
                    specs['normalized_value'] = ('arguments', 'F', f'convert argument {arg} to C; full season/weekend args retained')
            elif cols[0] == 'Occupants' and 'geometry_unit_num_occupants' in args:
                record['normalized_value'] = float(args['geometry_unit_num_occupants'])
                record['normalized_units'] = 'person/unit'
                specs['normalized_value'] = ('arguments', 'person/unit', 'parse geometry_unit_num_occupants; no area assumed')
            raw = {'parameter': cols[0], 'option': cols[1], 'measure': cols[2], 'arguments': args}
            self.add('residential_options', record, 'resstock', path, f'line {line_number}; context line {context_line}', raw, specs,
                     'Explicit options, not probabilities or a complete model. Multifamily assembly '
                     'requires building type, unit adjacency, floor area, equipment, and schedule defaults. '
                     'ACH50/ELA/natural infiltration definitions remain in source argument names.')

    def commercial(self):
        path = 'resources/options_lookup.tsv'
        wanted = {'hvac_system_type', 'hvac_tst_clg_sp_f', 'hvac_tst_htg_sp_f',
                  'hvac_tst_clg_delta_f', 'hvac_tst_htg_delta_f', 'lighting_generation',
                  'energy_code_followed_during_last_interior_equipment_replacement',
                  'energy_code_followed_during_last_hvac_replacement'}
        text = (self.raw_root/'comstock'/path).read_text(encoding='utf-8')
        for line_number, cols, context_line in option_rows(text):
            if cols[0] not in wanted or len(cols) < 3 or not cols[2]:
                continue
            args = dict(c.split('=', 1) for c in cols[3:] if '=' in c)
            if not args:
                continue
            record = {'id': stable_id('commercial', cols[0], cols[1], line_number),
                      'parameter': cols[0], 'option': cols[1], 'measure': cols[2],
                      'arguments': args, 'applicability': 'commercial_option_requires_complete_comstock_configuration',
                      'normalized_value': None, 'normalized_units': None}
            self.add('commercial_options', record, 'comstock', path, f'line {line_number}; context line {context_line}',
                     {'parameter': cols[0], 'option': cols[1], 'measure': cols[2], 'arguments': args},
                     {'arguments': ('arguments', 'measure-argument-specific', 'split argument=value; preserve strings')},
                     'ComStock explicit option/measure row evidence; not a sampled probability or '
                     'a complete building variant. Generator references standards; this lock does '
                     'not claim that ComStock runs with this atlas standards revision.')


def build_atlas(pilot=False, raw_root=ROOT/'data/raw'):
    b = Builder(raw_root)
    templates = [t for t in b.selection['templates'] if not pilot or t['template'] == '90.1-2013']
    for t in templates:
        for model in t['models']:
            if not pilot or model['building_type'] == 'MediumOffice':
                b.model(t, model)
        b.envelope(t)
        b.efficiencies(t)
        b.specialized(t)
    if not pilot:
        b.residential()
        from scripts.residential import add_configurations
        add_configurations(b)
        b.commercial()
    b.data['coverage_gaps'] = b.warnings
    for table in TABLES:
        b.data[table].sort(key=lambda r: r['id'])
    return b.data


def write_atlas(data, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    dump_json(output/'atlas.json', data)
    dump_json(output/'metadata.json', {k: v for k, v in data.items() if k not in TABLES})
    for table in TABLES:
        rows = data[table]
        dump_json(output/(table + '.json'), rows)
        if not rows:
            continue
        keys = list(rows[0])
        with (output/(table+'.csv')).open('w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, keys, lineterminator='\n')
            writer.writeheader()
            for r in rows:
                writer.writerow({k: json.dumps(v, sort_keys=True, ensure_ascii=False) if isinstance(v, (dict, list))
                                 else ('null' if v is None else v) for k, v in r.items()})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot', action='store_true')
    p.add_argument('--output', type=Path, default=ROOT/'data/processed')
    p.add_argument('--raw-root', type=Path, default=ROOT/'data/raw')
    args = p.parse_args()
    data = build_atlas(args.pilot, args.raw_root)
    from scripts.validate import validate_atlas
    errors = validate_atlas(data)
    if errors:
        raise ValueError('\n'.join(errors[:30]))
    write_atlas(data, args.output)
    print('Built and validated ' + ', '.join(f'{len(data[t])} {t}' for t in TABLES))


if __name__ == '__main__':
    main()
