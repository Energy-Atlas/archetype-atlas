"""Release files and consumer exports of the code-prototype dwelling families (ADR 0041, ADR 0042).

Builds `residential/<template>/<building-type>/` folders from the committed
definition inputs (data/program-inputs/iecc-residential-<edition>.json and
manufactured-housing.json), without the IDFs:
- `programs/<id>.json`: one dwelling program per type and variant, its entries
  carrying `applies_with` where they hold only for some climate codes, foundations,
  locations or heating systems;
- `schedules.json`: the folder's rulesets, each day profile once;
- `constructions/<id>.json`: one construction set per folder, one context per climate
  code and foundation (IECC) or location (manufactured housing), each with its
  assemblies by surface class, windows, doors, internal mass, window shading control
  and source infiltration;
- `residential/<template>/library/`: the template's materials and assemblies;
- `evidence/residential/<template>/<building-type>.json` and glossary entries.

Exports: Program JSON 5.3.0 `source` documents (`document`), optionally resolved for
one context, and source model constructions 1.0.0 for one context (`construction`).
"""
import collections
import copy
import json

from scripts import atlas_programs, iecc_residential, manufactured_housing
from scripts.atlas_format import h6, slug, suite_bytes, table_bytes, translate
from scripts.common import ROOT, load_json

FAMILIES = {'iecc_residential_prototype': 'IECC residential prototype', 'manufactured_housing_prototype': 'manufactured housing prototype'}
TYPE_FOLDERS = {'SingleFamily': 'single-family', 'Multifamily': 'multifamily', 'SingleSection': 'single-section',
                'MultiSection': 'multi-section'}
SCHEDULE_TYPES = {'dimensionless': 'fraction', 'C': 'temperature', 'W/person': 'activity'}
CONSTRUCTION_SCHEMA = ('construction-source-model-v1.schema.json', '1.0.0')
SCRIPTS = ('scripts/prototype_extract.py', 'scripts/prototype_programs.py', 'scripts/iecc_residential.py',
           'scripts/manufactured_housing.py', 'scripts/prototype_dwellings.py', 'scripts/idf_schedules.py')
PARTS = ('loads', 'services', 'controls', 'ventilation', 'fenestration', 'floor_area')
# The IECC residential codes with suffixes get a distinct, readable climate label each (user, 2026-10-26;
# ADR 0041 section 5). The label is the context's climate; its parts are context attributes, and the
# source code stays in the evidence. WH: a warm-humid location; T: a tropical location; S: the
# semi-conditioned tropical design. Other codes keep their names.
CLIMATES = {
    '1AWH': {'climate': '1A-warm-humid', 'climate_zone': '1A', 'source_location': 'Miami', 'warm_humid': True,
             'tropical': False, 'design': 'standard'},
    '1AWHT': {'climate': '1A-tropical', 'climate_zone': '1A', 'source_location': 'Honolulu', 'warm_humid': True,
              'tropical': True, 'design': 'standard'},
    '1AWHTS': {'climate': '1A-tropical-semi-conditioned', 'climate_zone': '1A', 'source_location': 'Honolulu',
               'warm_humid': True, 'tropical': True, 'design': 'tropical_semi_conditioned'},
    '2AWH': {'climate': '2A-warm-humid', 'climate_zone': '2A', 'source_location': 'Tampa', 'warm_humid': True,
             'tropical': False, 'design': 'standard'},
    '3AWH': {'climate': '3A-warm-humid', 'climate_zone': '3A', 'source_location': 'Montgomery', 'warm_humid': True,
             'tropical': False, 'design': 'standard'},
}


def climate_label(code):
    return CLIMATES[code]['climate'] if code in CLIMATES else code


def relabel(data):
    """An IECC residential input with its climate codes replaced by their labels, contexts carrying the parts."""
    data = copy.deepcopy(data)

    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get('applies_with'), dict) and 'climate' in value['applies_with']:
                value['applies_with']['climate'] = sorted(climate_label(c) for c in value['applies_with']['climate'])
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
    walk(data['programs'])
    for construction in data['constructions']:
        for context in construction['contexts'].values():
            code = context['climate']
            context.update(CLIMATES.get(code, {'climate': code, 'climate_zone': code, 'warm_humid': False,
                                               'tropical': False, 'design': 'standard'}), source_climate_code=code)
    return data


def input_paths():
    paths = [iecc_residential.target(e) for e in iecc_residential.EDITIONS] + [manufactured_housing.TARGET]
    return [p for p in paths if p.exists()]


def inputs():
    return [p.relative_to(ROOT).as_posix() for p in input_paths()] + list(SCRIPTS)


def template_slug(data, program):
    return f'iecc-{data["edition"]}' if data['family'] == 'iecc_residential_prototype' else program['template_key']


def template_name(data, program):
    return data['template'] if 'template' in data else data['templates'][program['template_key']]


def variant_slug(data, program):
    if data['family'] == 'iecc_residential_prototype':
        return f'{program["variant"]["appliance_fuel"]}-appliances'
    return 'dwelling'


def context_slug(data, key, context):
    if data['family'] == 'iecc_residential_prototype':
        return f'{slug(context["climate"])}.{context["foundation"]}'
    return key


def schedule_record(content):
    """A definition-shaped ruleset record from an extracted schedule."""
    return {'source_name': content['source_name'], 'type_limits': content['type_limits'],
            'schedule_type': SCHEDULE_TYPES[content['units']], 'units': content['units'], 'interpolation': 'none',
            'time_resolution_minutes': 60, 'evidence_ids': [],
            'rules': [{**r, 'source_index': i} for i, r in enumerate(content['rules'])]}


def strings(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)
    elif isinstance(value, str):
        yield value


def encode(data, evidence_ids, glossary):
    """Evidence rows with their texts and source files moved to the glossary (the commercial encoding)."""
    out = {}
    for eid in sorted(evidence_ids):
        row = data['evidence'][eid]
        interpretation, transformation = 'i-'+h6(row['interpretation']), 't-'+h6(row['transformation'])
        glossary['interpretations'][interpretation] = row['interpretation']
        glossary['transformations'][transformation] = row['transformation']
        glossary['source_files'][row['source_file_id']] = data['source_files'][row['source_file_id']]
        out[eid] = {'extraction_date': row['extraction_date'], 'locator': row['locator'],
                    'original_unit': row['original_unit'], 'original_value': row['original_value'],
                    'source_file': row['source_file_id'], 'interpretation': interpretation, 'transformation': transformation}
    return out


def axes(program, construction):
    """The axis values a program's applies_with conditions range over."""
    contexts = construction['contexts'].values()
    out = {'climate': sorted({c['climate'] for c in contexts})}
    if 'foundation' in next(iter(contexts)):
        out['foundation'] = sorted({c['foundation'] for c in contexts})
    if 'location' in next(iter(contexts)):
        out['location'] = sorted({c['location'] for c in contexts})
    out['heating'] = program['variant']['heating']
    return out


def build_input(data, glossary):
    """Files of one definition input."""
    if data['family'] == 'iecc_residential_prototype':
        data = relabel(data)
    files = {}
    by_template = collections.defaultdict(list)
    for program in data['programs']:
        by_template[template_slug(data, program)].append(program)
    constructions = {(template_slug(data, c), c['building_type']): c for c in data['constructions']}
    for tslug, programs in sorted(by_template.items()):
        # Library: materials, then assemblies citing them.
        used = {a for (t, _), c in constructions.items() if t == tslug for a in strings(c['contexts']) if a.startswith('asm-')}
        lib = {}
        for mid in sorted({m for a in used for m in data['assemblies'][a]['layers']}):
            record = data['materials'][mid]
            lib[mid] = f'{tslug}.{slug(record["name"])[:60].strip("-")}.{h6(record)}'
        for aid in sorted(used):
            record = translate(data['assemblies'][aid], lib)
            lib[aid] = f'{tslug}.{slug(record["name"])[:60].strip("-")}.{h6(record)}'
        files[f'residential/{tslug}/library/materials.json'] = table_bytes(
            {lib[m]: {**data['materials'][m], 'id': lib[m]} for m in lib if m.startswith('mat-')})
        files[f'residential/{tslug}/library/assemblies.json'] = table_bytes(
            {lib[a]: {**translate(data['assemblies'][a], lib), 'id': lib[a]} for a in lib if a.startswith('asm-')})
        for building_type in sorted({p['building_type'] for p in programs}):
            bslug = TYPE_FOLDERS[building_type]
            folder = f'residential/{tslug}/{bslug}/'
            construction = constructions[(tslug, building_type)]
            members = [p for p in programs if p['building_type'] == building_type]
            # Schedules: readable folder IDs for every schedule the programs and contexts cite.
            cited = sorted({s for s in strings([members, construction]) if s.startswith('sch-')})
            labels = {}
            for program in members:
                for part in PARTS:
                    for item in program[part]:
                        for k, v in item.items():
                            if isinstance(v, str) and v.startswith('sch-'):
                                labels.setdefault(v, f'{item.get("quantity") or part} {k}')
            records = {s: {**schedule_record(data['schedules'][s]), 'id': s} for s in cited}
            days, table, ids = atlas_programs.tabulate(records, {**{s: data['schedules'][s]['source_name'] for s in cited}, **labels},
                                                       f'{tslug}.{bslug}')
            files[folder+'schedules.json'] = table_bytes({'days': days, 'schedules': table}, sections=True)
            # The construction set.
            contexts = {context_slug(data, k, c): translate({kk: vv for kk, vv in c.items()}, {**ids, **lib})
                        for k, c in construction['contexts'].items()}
            set_record = {'name': f'{template_name(data, members[0])} {building_type} envelope', 'kind': 'source_model_construction_set',
                          'source_family': data['family'], 'template': template_name(data, members[0]), 'building_type': building_type,
                          'context_axes': data['context_axes'], 'contexts': dict(sorted(contexts.items()))}
            if construction.get('tier'):
                set_record['tier'] = construction['tier']
            set_id = f'{tslug}.{bslug}.envelope.{h6(set_record)}'
            set_record['id'] = set_id
            files[f'{folder}constructions/{set_id}.json'] = suite_bytes(set_record)
            evidence_ids = {c['evidence_id'] for c in construction['contexts'].values()}
            for program in members:
                record = {'name': f'{template_name(data, program)} {building_type} dwelling'
                                  + (f', {program["variant"]["appliance_fuel"]} appliances' if 'appliance_fuel' in program['variant'] else ''),
                          'kind': 'dwelling', 'source_family': data['family'], 'template': template_name(data, program),
                          'building_type': building_type, 'scope': 'whole_dwelling',
                          'climate': None, 'vintage': None, 'variant': program['variant'],
                          'axes': axes(program, construction), 'model_count': program['model_count'],
                          'construction_set_id': set_id,
                          **{part: translate(program[part], ids) for part in PARTS}}
                for field in ('edition', ):
                    if field in data:
                        record[field] = data[field]
                for field in ('building_context', 'tier', 'template_key'):
                    if field in program and program[field] is not None:
                        record[field] = program[field]
                record['evidence_ids'] = sorted({i['evidence_id'] for part in PARTS for i in program[part]})
                evidence_ids |= set(record['evidence_ids'])
                pid = f'{tslug}.{bslug}.{variant_slug(data, program)}.{h6(record)}'
                record['id'] = pid
                files[f'{folder}programs/{pid}.json'] = suite_bytes(record)
            files[f'evidence/residential/{tslug}/{bslug}.json'] = table_bytes(encode(data, evidence_ids, glossary))
    return files


def build():
    """Every code-prototype file and the glossary entries they need."""
    glossary = {'interpretations': {}, 'transformations': {}, 'source_files': {}}
    files = {}
    for path in input_paths():
        for name, data in build_input(load_json(path), glossary).items():
            if name in files and files[name] != data:
                raise ValueError('File built twice with different content: '+name)
            files[name] = data
    files['evidence/glossary.json'] = table_bytes({**glossary, 'rule_notes': {}, 'unresolved': {}}, sections=True)
    return files


# Exports

def matches(item, context):
    condition = item.get('applies_with') or {}
    return all(context.get(axis) is None or context[axis] in values for axis, values in condition.items())


def select(entries, context):
    """Entries that hold in a context; with a full context the conditions are dropped."""
    out = []
    for item in entries:
        if not matches(item, context):
            continue
        item = copy.deepcopy(item)
        if context and all(axis in context for axis in item.get('applies_with', {})):
            item.pop('applies_with', None)
        out.append(item)
    return out


def load_document(item, demand_id):
    """A Program JSON source-version load from a stored entry."""
    out = {'demand_id': demand_id, 'type': item['type'], 'end_use': item['quantity'], 'value': item['value'],
           'unit': item['unit'], 'basis': item['basis'], 'schedule_id': item['schedule_id'], 'host': 'assigned_zone'}
    if item['type'] == 'lighting':
        f = item['fractions']
        out['heat_fractions'] = {'radiant': f['radiant'], 'visible': f['visible'], 'return_air': f['return_air']}
    elif item['type'] in ('electric_equipment', 'gas_equipment'):
        f = item['fractions']
        out['heat_fractions'] = {'radiant': f['radiant'], 'latent': f['latent'], 'lost': f['lost']}
        out['fuel'] = item['fuel']
    elif item['type'] == 'hot_water':
        out['target_temperature_schedule_id'] = item.get('target_temperature_schedule_id')
        out['inlet_temperature'] = {'method': 'unresolved'}
    elif item['type'] == 'occupancy':
        out['activity_schedule_id'] = item.get('activity_schedule_id')
    if item.get('host_zone'):
        out['host_zone'] = item['host_zone']
    for key in ('role', 'applies_with'):
        if key in item:
            out[key] = copy.deepcopy(item[key])
    return out


def document(dwellings, program_id, version, context=None):
    """Program JSON 5.3.0 of a code-prototype dwelling, optionally resolved for one context."""
    from scripts.residential_exports import PROGRAM_MINOR, dwelling
    from scripts.schedule_json import normalize_schedule
    if version != 'source':
        raise ValueError('Code-prototype dwellings are complete source models and export the source version only '
                         '(ADR 0041): the filled version needs the water heaters, which are systems (ADR 0038 section 7).')
    context = context or {}
    folder, stored = dwellings.programs[program_id]
    table = json.loads(dwellings.files[folder+'schedules.json'])
    loads, services, schedules = [], [], {}
    for part, target in (('loads', loads), ('services', services)):
        for i, item in enumerate(select(stored[part], context)):
            target.append(load_document(item, f'{program_id}:{part}:{i}'))
    controls_entries = select(stored['controls'], context)
    controls = {'heating_enabled': None, 'cooling_enabled': None, 'conditioning_state': 'unknown'}
    if len(controls_entries) == 1:
        thermostat = controls_entries[0]
        controls.update(heating_setpoint_schedule_id=thermostat['heating_setpoint_schedule_id'],
                        cooling_setpoint_schedule_id=thermostat['cooling_setpoint_schedule_id'],
                        heating_enabled=True, cooling_enabled=True, conditioning_state='heating_and_cooling')
    people = [i for i in select(stored['loads'], context) if i['type'] == 'occupancy']
    if len({json.dumps([p.get('activity_schedule_id'), p.get('fraction_radiant'), p.get('sensible_fraction')]) for p in people}) == 1:
        controls.update(activity_schedule_id=people[0]['activity_schedule_id'], people_radiant_fraction=people[0]['fraction_radiant'],
                        people_sensible_fraction=people[0]['sensible_fraction'])
    used = {v for owner in [*loads, *services, controls] for k, v in owner.items()
            if (k == 'schedule_id' or k.endswith('_schedule_id')) and v}
    for sid in sorted(used):
        suite_schedule = {k: v for k, v in table['schedules'][sid].items() if k not in ('name', 'rules')}
        suite_schedule['rules'] = [{**{k: v for k, v in r.items() if k != 'day'}, 'values': table['days'][r['day']]}
                                   for r in table['schedules'][sid]['rules']]
        normalized = normalize_schedule({**suite_schedule, 'id': sid})
        normalized['unit'] = {'dimensionless': '1', 'C': 'degC'}.get(suite_schedule['units'], suite_schedule['units'])
        schedules[sid] = normalized
    glossary = json.loads(dwellings.files['evidence/glossary.json'])
    tslug, bslug = folder.split('/')[1:3]
    evidence = json.loads(dwellings.files[f'evidence/residential/{tslug}/{bslug}.json'])
    from scripts.atlas_exports import decode
    rows = []
    for eid in stored['evidence_ids']:
        row = decode(eid, evidence[eid], glossary)
        rows.append({k: row[k] for k in ('source_file_id', 'locator', 'original_value', 'original_unit', 'transformation',
                                        'extraction_date', 'interpretation')})
    bases = {l['basis'] for l in loads}
    bindings = [v for k, v in (('floor_area', 'floor_area_m2'), ('dwelling_unit', 'dwelling_unit_count'), ('person', 'person_count')) if k in bases]
    if services:
        bindings.append('shared_service_host')
    if any(l['type'] == 'hot_water' for l in loads):
        bindings.append('weather_file')
    doc = {'schema_version': PROGRAM_MINOR[1], 'version': 'source', 'kind': 'program', 'id': program_id, 'name': stored['name'],
           'scope': stored['scope'],
           'source': {'program_id': program_id, 'building_type': stored['building_type'], 'template': stored['template'],
                      'evidence': rows, 'source_family': stored['source_family'],
                      'climate': {'status': 'exact', 'value': context['climate']} if context.get('climate') else
                      {'status': 'shared', 'basis': 'Code-prototype program; entries carry applies_with where they depend on climate'},
                      'vintage': {'status': 'exact', 'value': stored['template'], 'kind': 'source_template'}},
           'loads': loads, 'controls': controls, 'schedules': schedules,
           'shared_services': [{'id': f'{program_id}:service:{i}', 'ownership': 'instantiate_once',
                                'host_assignment': 'consumer_selected_zone', 'loads': [s]} for i, s in enumerate(services)],
           'default_policy_id': None, 'required_bindings': bindings + ['calendar_year', 'holiday_calendar'],
           'metadata': {'context': context, 'ventilation': select(stored['ventilation'], context),
                        'fenestration': select(stored['fenestration'], context),
                        'floor_area': select(stored['floor_area'], context), 'axes': stored['axes'],
                        'excluded_scope': ['hvac', 'water_heaters', 'infiltration (in the construction set)'],
                        'water_mains': 'Site:WaterMainsTemperature Correlation of each location; weather-dependent, not stored'},
           'dwelling': dwelling(stored)}
    fenestration = doc['metadata']['fenestration']
    if len(fenestration) == 1 and 'applies_with' not in fenestration[0]:
        doc['fenestration'] = {'basis': 'program_zone_surfaces', 'wwr': fenestration[0]['wwr'], 'roof': None,
                               'evidence_id': fenestration[0]['evidence_id']}
    return doc


def construction(release, set_id, key):
    """Source model constructions 1.0.0: one context of an IDF-derived construction set, resources embedded."""
    from jsonschema import Draft202012Validator
    path = next(p for p in release.files if p.endswith(f'/constructions/{set_id}.json'))
    record = json.loads(release.files[path])
    context = record['contexts'][key]
    tslug, bslug = path.split('/')[1:3]
    library = {t: json.loads(release.files[f'residential/{tslug}/library/{t}.json']) for t in ('assemblies', 'materials')}
    assemblies = {a: library['assemblies'][a] for a in strings(context) if a in library['assemblies']}
    materials = {m: library['materials'][m] for a in assemblies.values() for m in a['layers']}
    table = json.loads(release.files[f'residential/{tslug}/{bslug}/schedules.json'])
    schedules = {}
    for sid in sorted({s for s in strings(context) if s in table['schedules']}):
        entry = table['schedules'][sid]
        schedules[sid] = {**{k: v for k, v in entry.items() if k != 'rules'},
                          'rules': [{**{k: v for k, v in r.items() if k != 'day'}, 'values': table['days'][r['day']]} for r in entry['rules']]}
    glossary = json.loads(release.files['evidence/glossary.json'])
    evidence = json.loads(release.files[f'evidence/residential/{tslug}/{bslug}.json'])
    from scripts.atlas_exports import decode
    doc = {'schema_version': CONSTRUCTION_SCHEMA[1], 'kind': 'source_model_construction', 'id': f'{set_id}.{key}',
           'construction_set_id': set_id, 'context': key, 'name': record['name'], 'release': f'atlas-release-{release.release}',
           'source': {k: record[k] for k in ('source_family', 'template', 'building_type') if k in record},
           **{k: v for k, v in context.items() if k not in ('evidence_id', 'model_count')},
           'assemblies': assemblies, 'materials': materials, 'schedules': schedules,
           'evidence': {context['evidence_id']: decode(context['evidence_id'], evidence[context['evidence_id']], glossary)}}
    errors = [e.message for e in Draft202012Validator(construction_schema()).iter_errors(doc)]
    if errors:
        raise ValueError(f'{set_id} {key}: '+'; '.join(errors[:5]))
    return doc


def construction_schema():
    """Source model constructions 1.0.0: an IDF-derived construction context (ADR 0041, ADR 0042)."""
    text = {'type': 'string', 'minLength': 1}
    number = {'type': 'number'}
    area = {'type': 'number', 'minimum': 0}
    surface = {'type': 'object', 'required': ['zone', 'boundary', 'assembly_id', 'area_m2'],
               'properties': {'surface_type': text, 'zone': text, 'boundary': text, 'assembly_id': text, 'area_m2': area}}
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:archetype-atlas:source-model-construction:1.0.0',
            'title': 'Source model constructions 1.0.0',
            'description': 'One context (climate code and foundation, or location) of a construction set read from code-prototype '
                           'EnergyPlus models: assemblies by surface class with their summed source areas, windows, doors, internal '
                           'mass, window shading control and the source infiltration method. Layers run outside to inside; '
                           'U-factors are layer-only (no air films); glazing carries its simple-glazing U-factor and SHGC.',
            'type': 'object', 'additionalProperties': False,
            'required': ['schema_version', 'kind', 'id', 'construction_set_id', 'context', 'name', 'release', 'source', 'climate',
                         'components', 'windows', 'doors', 'internal_mass', 'window_shading', 'infiltration', 'assemblies',
                         'materials', 'schedules', 'evidence'],
            'properties': {'schema_version': {'const': CONSTRUCTION_SCHEMA[1]}, 'kind': {'const': 'source_model_construction'},
                           'id': text, 'construction_set_id': text, 'context': text, 'name': text,
                           'release': {'enum': ['atlas-release-1.4.0']}, 'source': {'type': 'object'},
                           'climate': text, 'foundation': text, 'location': text, 'climate_zone': text,
                           'warm_humid': {'type': 'boolean'}, 'tropical': {'type': 'boolean'},
                           'design': {'enum': ['standard', 'tropical_semi_conditioned']}, 'source_climate_code': text,
                           'source_location': text,
                           'components': {'type': 'array', 'items': surface}, 'windows': {'type': 'array', 'items': surface},
                           'doors': {'type': 'array', 'items': surface}, 'internal_mass': {'type': 'array', 'items': {
                               'type': 'object', 'required': ['zone', 'assembly_id', 'area_m2'],
                               'properties': {'zone': text, 'assembly_id': text, 'area_m2': area}}},
                           'window_shading': {'type': 'array', 'items': {'type': 'object'}},
                           'infiltration': {'type': 'object', 'minProperties': 1,
                                            'properties': {'airflow_network': {'type': 'object'},
                                                           'effective_leakage_area': {'type': 'array'},
                                                           'design_flow_rate': {'type': 'array'}}},
                           'assemblies': {'type': 'object', 'additionalProperties': {
                               'type': 'object', 'required': ['name', 'layers', 'layer_orientation'],
                               'properties': {'name': text, 'layers': {'type': 'array', 'items': text},
                                              'layer_orientation': {'const': 'outside_to_inside'},
                                              'layer_u_factor_W_m2_K': {'anyOf': [number, {'type': 'null'}]},
                                              'u_factor_W_m2_K': number, 'solar_heat_gain_coefficient': number}}},
                           'materials': {'type': 'object', 'additionalProperties': {'type': 'object', 'required': ['model', 'name']}},
                           'schedules': {'type': 'object'}, 'evidence': {'type': 'object'}}}
