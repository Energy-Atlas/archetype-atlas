"""Apply the DOE reference reconciliation (ADR 0037) to the release writers' definition sources.

Release 1.1.0 is release 1.0.0's writers run on overlaid sources:
`apply_programs` edits an atlas_programs.Sources in place from the committed definition
input data/reconciliation/doe-reference-values-v1.json, keyed to release 1.0.0's
program IDs. DOE values are source values, so a source record and its reviewed twin
change together and no filling is created; unresolved rows that a DOE value now
answers are retired. Zone groups that DOE models apart get programs of their own
(the re-tags and the Large Office basement). The mixes are then recomposed by
scripts.program_composition.compose itself (ADR 0012), with the moved source spaces
counted for their new programs; every other template's mixes must come out as stored.
`apply_systems` and `Constructions` carry the building services, hot-water gains,
infiltration method, internal mass and window ratios.
"""
import copy
import json
import math
from collections import defaultdict

from scripts.common import ROOT, load_json
from scripts.definition_contract import parameter, stable_id

VALUES = ROOT/'data/reconciliation/doe-reference-values-v1.json'
BASE = ROOT/'data/atlas-releases/v1.0.0'
TEMPLATES = {'doe-ref-1980-2004': 'DOE Ref 1980-2004', 'doe-ref-pre-1980': 'DOE Ref Pre-1980'}
UNRESOLVED_FIELDS = {('load', 'hot_water_volume'): 'service_water_heating_schedule_id'}
ZERO_SCHEDULE = {'source_name': 'DOE reference: no object (constant 0)', 'schedule_type': 'fraction',
                 'units': 'dimensionless', 'interpolation': 'none', 'time_resolution_minutes': 60,
                 'rules': [{'day_types': 'Default', 'start_date': '2014-01-01T00:00:00+00:00',
                            'end_date': '2014-12-31T00:00:00+00:00', 'type': 'Constant', 'values': [0.0],
                            'source_index': 0}]}


def base_programs():
    """{release 1.0.0 program ID: (template, building type, source ID or None, name)}."""
    out = {}
    for path in (BASE/'commercial').glob('doe-ref-*/*/programs/*/*.json'):
        p = json.loads(path.read_text(encoding='utf-8'))
        out[p['id']] = (p['template'], p['building_type'], p.get('source_id'), p['name'])
    return out


class Programs:
    """The definition records behind release 1.0.0 program IDs: source record first, then its twin."""

    def __init__(self, sources):
        self.sources = sources
        by_source = defaultdict(list)
        for p in sources.programs.values():
            if p['template'] in TEMPLATES.values() and p['derivation'] != 'composed':
                by_source[(p['template'], p['building_type'], p['source_id'])].append(p)
        self.records = {}
        for atlas_id, (template, building_type, source_id, _) in base_programs().items():
            if source_id is not None:
                found = sorted(by_source[(template, building_type, source_id)], key=lambda p: p['evidence_view'] != 'source')
                self.records[atlas_id] = found

    def __call__(self, atlas_id):
        if atlas_id not in self.records:
            raise ValueError('No definition record for '+atlas_id)
        return self.records[atlas_id]


def cite(record, evidence_id):
    if evidence_id not in record['evidence_ids']:
        record['evidence_ids'] = sorted({*record['evidence_ids'], evidence_id})


def load_entry(record, quantity):
    return next((l for l in record['loads'] if l['quantity'] == quantity), None)


def retire_unresolved(sources, record, target):
    field = UNRESOLVED_FIELDS.get(target, target[1]+'_schedule_id' if target[0] == 'load' else target[1])
    rows = sources.unresolved.get(record['source_id'], [])
    sources.unresolved[record['source_id']] = [r for r in rows if r['field'] != field]


def set_slot(sources, record, kind, field, schedule_id, evidence_id):
    """Set a program slot; False when the slot is hot water served by a building service instead."""
    if kind == 'load':
        entry = load_entry(record, field)
        if entry is None and field == 'hot_water_volume':
            return False
        if entry is None:
            raise ValueError(f'No {field} load in {record["id"]}')
        lighting = entry['schedule_id']
        entry['schedule_id'] = schedule_id
        if field == 'lighting':  # additional lighting runs on the lighting schedule
            extra = load_entry(record, 'additional_lighting')
            if extra is not None and extra['schedule_id'] in (lighting, None):
                extra['schedule_id'] = schedule_id
    else:
        record['parameters'][field] = parameter(schedule_id, 'schedule reference', evidence_id)
    retire_unresolved(sources, record, (kind, field))
    cite(record, evidence_id)
    return True


def apply_programs(sources, values=None):
    """Edit the program sources; returns the changed record IDs and, per program source ID, the DOE
    hot-water flow schedule for the building service that serves it."""
    values = values or load_json(VALUES)
    from scripts import reference_extras
    sources.evidence.update(values['evidence'])
    sources.source_files.update(values['source_files'])
    sources.schedules.update(copy.deepcopy(values['schedules']))
    zero = {'id': stable_id('schedule', ZERO_SCHEDULE), **copy.deepcopy(ZERO_SCHEDULE)}
    programs = Programs(sources)
    changed, service_schedules = set(), {}
    for key, folder in sorted(values['folders'].items()):
        template = TEMPLATES[key.split('/')[0]]
        for atlas_id, slots in folder['program_schedules'].items():
            for slot, schedule_id in slots.items():
                kind, field, _ = reference_extras.SLOTS[slot]
                evidence = values['schedules'][schedule_id]['evidence_ids'][0]
                for record in programs(atlas_id):
                    if set_slot(sources, record, kind, field, schedule_id, evidence):
                        changed.add(record['id'])
                    else:
                        service_schedules[record['source_id']] = schedule_id
        for item in folder['program_values']:
            kind, quantity, *rest = item['path']
            for record in programs(item['program']):
                entry = load_entry(record, quantity)
                if entry is None:
                    raise ValueError(f'No {quantity} load in {record["id"]}')
                if rest == ['value']:
                    entry.update(value=item['value'], status='known', evidence_id=item['evidence'])
                    if item['value'] == 0 and entry.get('schedule_id') is None:  # no DOE object: no schedule either
                        sources.schedules[zero['id']] = zero
                        entry['schedule_id'] = zero['id']
                        retire_unresolved(sources, record, ('load', quantity))
                elif rest == ['zero']:
                    sources.schedules[zero['id']] = zero
                    entry.update(value=0.0, status='known', evidence_id=item['evidence'], schedule_id=zero['id'])
                    retire_unresolved(sources, record, ('load', quantity))
                else:
                    entry.setdefault('thermal_effects', {})[rest[1]] = parameter(item['value'], '1', item['evidence'])
                cite(record, item['evidence'])
                changed.add(record['id'])
        for item in folder['alternates']:
            for atlas_id in item['programs']:
                for record in programs(atlas_id):
                    alternate = {'source_family': 'doe-reference', 'evidence_id': item['evidence'], 'reason_id': item['reason_id']}
                    if 'path' in item:
                        entry = load_entry(record, item['path'][1])
                        entry['alternates'] = [{**alternate, 'value': item['value']}]
                    else:
                        for entry in record['loads']:
                            name = sources.schedules.get(entry.get('schedule_id'), {}).get('source_name')
                            if name == item['schedule_source_name']:
                                entry['alternates'] = [{**alternate, 'schedule_id': item['value']}]
                    cite(record, item['evidence'])
                    changed.add(record['id'])
        for item in folder['hot_water']['zero_programs']:
            sources.schedules[zero['id']] = zero
            for record in programs(item['program']):
                if load_entry(record, 'hot_water_volume') is None:
                    record['loads'].append({
                        'basis': 'floor_area', 'quantity': 'hot_water_volume', 'unit': 'm3/s/m2', 'value': 0.0,
                        'status': 'known', 'scope': 'program', 'schedule_id': zero['id'], 'evidence_id': item['evidence'],
                        'required_inputs': ['floor_area'], 'thermal_effects': {},
                        'demand_id': stable_id('demand', {'program': record['source_id'], 'quantity': 'hot_water_volume',
                                                          'source': 'doe-reference'})})
                retire_unresolved(sources, record, ('load', 'hot_water_volume'))
                cite(record, item['evidence'])
                changed.add(record['id'])
        for atlas_id, item in folder['fenestration']['programs'].items():
            for record in programs(atlas_id):
                record['fenestration'] = {'basis': 'program_zone_surfaces', 'wwr': {d: item['value'][d] for d in 'NESW'},
                                          'roof': item['value']['roof'], 'evidence_id': item['evidence']}
                cite(record, item['evidence'])
                changed.add(record['id'])
    changed |= apply_program_water_gains(sources, values)
    added = add_programs(sources, values, programs, zero)
    compose_mixes(sources, added)
    for key, folder in sorted(values['folders'].items()):
        template, calendar = TEMPLATES[key.split('/')[0]], folder['calendar']
        for record in sources.programs.values():
            if (record['template'], record['building_type']) == (template, folder['building_type']):
                record['source_calendar'] = {'holidays': calendar['holidays'], 'daylight_saving': calendar['daylight_saving'],
                                             'evidence_id': calendar['evidence']}
                if record['derivation'] != 'composed':
                    cite(record, calendar['evidence'])
    return changed, service_schedules


SLOT_OF = {'occupancy': 'occupancy', 'lighting': 'lighting', 'additional_lighting': 'lighting',
           'electric_equipment': 'electric_equipment', 'gas_equipment': 'gas_equipment', 'hot_water_volume': 'hot_water'}


def add_programs(sources, values, programs, zero):
    """The NEW_PROGRAMS records: the parent's record with the zone group's DOE values; the parent
    lists the moved source spaces. Returns the moves the composition areas follow."""
    from scripts import reference_extras
    moves = []
    for key, folder in sorted(values['folders'].items()):
        template = TEMPLATES[key.split('/')[0]]
        for item in folder['new_programs']:
            parents = programs(item['parent'])
            source_id = 'program-'+stable_id('program', {'parent': parents[0]['source_id'], 'name': item['name'],
                                                         'source': 'doe-reference'})[-20:]
            record = copy.deepcopy(parents[0])
            for field in ('reviewed_resolution_ids', 'source_definition_id', 'excluded_source_spaces'):
                record.pop(field, None)
            record.update(id=stable_id('program', {'source_id': source_id, 'derivation': 'normalized'}), source_id=source_id,
                          name=item['name'], available_details=['SourcePrograms'], service_ids=[], source_spaces=item['spaces'])
            sources.schedules[zero['id']] = zero
            for load in record['loads']:
                q = load['quantity']
                value = item['loads'].get(q, 0.0 if q in ('additional_lighting', 'hot_water_volume') else load.get('value'))
                schedule = item['slots'].get(SLOT_OF.get(q))
                load.update(value=value, status='unknown' if value is None else 'known', evidence_id=item['evidence'],
                            scope='program', schedule_id=schedule or (zero['id'] if value == 0 else load['schedule_id']),
                            demand_id=stable_id('demand', {'program': source_id, 'quantity': q, 'source': 'doe-reference'}))
                load.pop('service_id', None)
                for effect, v in item['fractions'].get(q, {}).items():
                    load.setdefault('thermal_effects', {})[effect] = parameter(v, '1', item['evidence'])
                if q == 'hot_water_volume':
                    load['thermal_effects'] = {}
                    load.pop('zone_heat_assignment', None)
                    load.pop('target_temperature_degC', None)
            for slot, schedule in item['slots'].items():
                kind, field, _ = reference_extras.SLOTS[slot]
                if kind == 'parameter':
                    record['parameters'][field] = parameter(schedule, 'schedule reference', sources.schedules[schedule]['evidence_ids'][0])
            record['fenestration'] = {'basis': 'program_zone_surfaces', 'wwr': {d: item['fenestration'][d] for d in 'NESW'},
                                      'roof': item['fenestration']['roof'], 'evidence_id': item['evidence']}
            record['evidence_ids'] = sorted({item['evidence'], *(sources.schedules[s]['evidence_ids'][0] for s in item['slots'].values())})
            sources.programs[record['id']] = record
            names = [s['name'] for s in item['spaces']]
            for parent in parents:
                parent['excluded_source_spaces'] = sorted({*parent.get('excluded_source_spaces', []), *names})
            moves.append({'building_type': folder['building_type'], 'template': template, 'space_type': item['space_type'],
                          'parent_source_id': parents[0]['source_id'], 'source_id': source_id, 'spaces': names})
    return moves


def compose_mixes(sources, moves):
    """Every mix recomposed by scripts.program_composition.compose on the overlaid leaves.

    The moved source spaces count for their new programs instead of their parents. The DOE Ref
    templates take the result; every other template's mixes must come out as stored."""
    from scripts import program_composition
    from scripts.definition_contract import load_context
    from scripts.fetch import fetch_file
    from scripts.semantics import spaces
    from scripts.water_reporting import floor_areas
    context = load_context(scope='full')
    legacy = {p['id']: p for p in context.atlas['programs']}
    files = {r['path']: r for r in context.atlas['source_files'] if r['source_id'] == 'openstudio-standards'}
    extract = program_composition.extract_areas

    def areas(ctx):
        result = extract(ctx)
        for move in moves:
            rows = result[(move['building_type'], move['template'])]
            parent = next(r for r in rows if r['program_id'] == move['parent_source_id'])
            text = fetch_file(files[parent['geometry_path']], ctx.root/'data/raw').read_text(encoding='utf-8-sig')
            by_name, area = {s['name']: s for s in spaces(text)}, floor_areas(text)
            moved = [by_name[n] for n in move['spaces']]
            counted = [s for s in moved if s['handle'] in parent['space_handles']]
            represented = math.fsum(area[s['handle']]*s['multiplier'] for s in counted)
            parent['represented_area_m2'] -= represented
            parent['space_handles'] = [h for h in parent['space_handles'] if h not in {s['handle'] for s in moved}]
            rows.append({**parent, 'program_id': move['source_id'], 'source_space_type': move['space_type'],
                         'represented_area_m2': represented, 'area_status': 'derived' if counted else 'non_counted',
                         'space_handles': [s['handle'] for s in counted], 'uncounted_space_handles': []})
            ctx.atlas['programs'].append({**legacy[move['parent_source_id']], 'id': move['source_id'],
                                          'source_space_type': move['space_type'], 'program': move['space_type']})
        return result

    table = areas(context)
    leaves = [copy.deepcopy(p) for p in sources.programs.values()
              if p['derivation'] != 'composed' and (p['building_type'], p['template']) in table]
    program_composition.extract_areas = lambda ctx: table
    try:
        bundle = program_composition.compose(context, {'programs': leaves, 'schedules': list(sources.schedules.values())})
    finally:
        program_composition.extract_areas = extract
    doe = set(TEMPLATES.values())
    composed = {p['id']: p for p in bundle['programs']}
    recipes = {c['id']: c for c in bundle['compositions']}
    for p in sources.programs.values():
        if p['derivation'] == 'composed' and p['template'] not in doe and composed.get(p['id']) != p:
            raise ValueError('The composer does not reproduce the stored mix '+p['id'])
    for leaf in leaves:  # compose resets each leaf's details, then adds the mix modes it is not covered by
        if leaf['template'] in doe:
            sources.programs[leaf['id']]['available_details'] = leaf['available_details']
        elif leaf['available_details'] != sources.programs[leaf['id']]['available_details']:
            raise ValueError('The composer changes the details of '+leaf['id'])
    for key in [k for k, p in sources.programs.items() if p['derivation'] == 'composed' and p['template'] in doe]:
        del sources.programs[key]
    for key in [k for k, c in sources.compositions.items() if c['template'] in doe]:
        del sources.compositions[key]
    sources.programs.update({k: p for k, p in composed.items() if p['template'] in doe})
    sources.compositions.update({k: c for k, c in recipes.items() if c['template'] in doe})
    sources.schedules.update({s['id']: s for s in bundle['schedules']})
    sources.evidence.update({e['id']: e for e in bundle['provenance']})
    sources.twins = {p['source_definition_id']: p for p in sources.programs.values() if p.get('source_definition_id')}


GAINS = {'zone_gains': 'applied', 'semantics': 'EnergyPlus WaterUse:Equipment',
         'sensible': 'fraction x mass flow x cp x (mixed - zone air temperature)',
         'latent': 'fraction of the water that can evaporate'}


def gain_effects(folder):
    """Water-use zone gain fractions of a folder (every DOE Ref draw uses 0.2 and 0.05), or None."""
    pairs = {(g['sensible_fraction'], g['latent_fraction']) for g in folder['hot_water']['gains']}
    if len(pairs) > 1:
        raise ValueError('Several water-use gain fractions in one folder: '+str(sorted(pairs)))
    if not pairs:
        return None
    sensible, latent = next(iter(pairs))
    evidence = folder['hot_water']['gains'][0]['evidence']
    return {**GAINS, 'sensible_fraction': parameter(sensible, '1', evidence), 'latent_fraction': parameter(latent, '1', evidence)}


def service_load(item):
    """A definition service load from a DOE building-service object."""
    v, evidence = item['value'], item['evidence']
    base = {'evidence_id': evidence, 'status': 'known', 'scope': 'building_service', 'required_inputs': []}
    if item['end_use'] in ('elevator', 'exhaust_fan') and 'method' in v:
        level, per_area, _ = v['values']
        absolute = v['method'] == 'equipmentlevel'
        f = v['fractions']
        return {**base, 'quantity': 'electric_equipment', 'basis': 'absolute' if absolute else 'floor_area',
                'unit': 'W' if absolute else 'W/m2', 'value': level if absolute else per_area,
                'required_inputs': [] if absolute else ['floor_area'], 'schedule_id': v['schedule_id'],
                'thermal_effects': {k: parameter(f[k], '1', evidence) for k in ('latent', 'radiant', 'lost') if f.get(k) is not None}}
    if item['end_use'] in ('elevator', 'exterior_equipment'):
        electric = v['fuel'].lower() == 'electricity'
        return {**base, 'quantity': 'electric_equipment' if electric else 'gas_equipment', 'basis': 'absolute',
                'unit': 'W', 'value': v['design_level_W'], 'schedule_id': v['schedule_id'], 'fuel': v['fuel'],
                'thermal_effects': {'lost': parameter(1.0, '1', evidence)}}
    if item['end_use'] == 'exterior_lighting':
        return {**base, 'quantity': 'exterior_lighting', 'basis': 'absolute', 'unit': 'W', 'value': v['design_level_W'],
                'schedule_id': v['schedule_id'], 'control': v['control'] or None}
    if item['end_use'] == 'refrigeration_case':
        return {**base, 'quantity': 'refrigeration_case', 'basis': 'case_length', 'unit': 'W/m', 'value': v['capacity_W_m'],
                'length_m': v['length_m'], 'operating_temperature_degC': v['operating_temperature_C'],
                'latent_heat_ratio': v['latent_heat_ratio'], 'runtime_fraction': v['runtime_fraction'],
                'fan_power_W_m': v['fan_power_W_m'], 'lighting_power_W_m': v['lighting_power_W_m'],
                'schedule_id': v['availability_id'], 'lighting_schedule_id': v['lighting_schedule_id']}
    if item['end_use'] == 'refrigeration_rack':
        return {**base, 'quantity': 'refrigeration_rack', 'basis': 'absolute', 'unit': 'W', 'value': v['condenser_fan_W'],
                'cop': v['cop'], 'heat_rejection': v['heat_rejection'], 'schedule_id': None}
    raise ValueError('Unknown building service: '+item['end_use'])


def apply_systems(systems, programs_sources, service_schedules, values=None):
    """Edit the systems sources: hot-water service schedules and zone gains, and the DOE building services.

    `programs_sources` is the overlaid atlas_programs.Sources, which the systems writer then reads."""
    values = values or load_json(VALUES)
    systems.definitions = programs_sources
    systems.schedules = {**programs_sources.schedules, **{s['id']: s for s in systems.water['schedules']}}
    programs = Programs(programs_sources)
    for key, folder in sorted(values['folders'].items()):
        template, building_type = TEMPLATES[key.split('/')[0]], folder['building_type']
        effects = gain_effects(folder)
        by_name = folder['hot_water']['schedules_by_name']
        for service in systems.services.values():
            if (service['template'], service['building_type']) != (template, building_type):
                continue
            load = service['load']
            if load.get('quantity') != 'hot_water_volume':
                continue
            chosen = sorted({service_schedules[b] for b in service['beneficiary_program_ids'] if b in service_schedules})
            name = systems.schedules.get(load['schedule_id'], {}).get('source_name')
            if len(chosen) == 1:
                load['schedule_id'] = chosen[0]
            elif not chosen and name in by_name:
                load['schedule_id'] = by_name[name]
            if load['schedule_id'] in values['schedules']:
                service['evidence_ids'] = sorted({*service['evidence_ids'], *values['schedules'][load['schedule_id']]['evidence_ids']})
            if effects:
                load['thermal_effects'] = copy.deepcopy(effects)
                load['zone_heat_assignment'] = 'beneficiary_program_zones' if service['beneficiary_program_ids'] else 'unresolved'
                service['evidence_ids'] = sorted({*service['evidence_ids'], effects['sensible_fraction']['evidence_id']})
        for item in folder['services']:
            beneficiaries = sorted({programs(p)[0]['source_id'] for p in item['beneficiary_programs']})
            sid = stable_id('service', {'template': template, 'building_type': building_type, 'end_use': item['end_use'],
                                        'name': item['value']['name'], 'source': 'doe-reference'})
            load = {**service_load(item), 'service_id': sid, 'demand_id': sid}
            systems.services[sid] = {
                'id': sid, 'template': template, 'building_type': building_type, 'end_use': item['end_use'],
                'name': item['value']['name'], 'assignment': 'consumer_host_when_applicable' if beneficiaries else 'building_level',
                'beneficiary_program_ids': beneficiaries, 'ownership': 'instantiate_once',
                'path_id': f"{building_type}|{template}|{item['end_use']}|{item['value']['name']}",
                'load': load, 'evidence_ids': [item['evidence']], 'source_evidence_ids': []}


class Constructions:
    """The construction-document overlay: building window ratios, the DOE design-flow infiltration
    method and the internal-mass fills, the same in every climate context (checked over all 16 files)."""

    def __init__(self, values=None):
        self.values = values or load_json(VALUES)
        self.geometry = {(e['template'], e['building_type']): e
                         for e in load_json(ROOT/'data/construction-inputs/geometry-v1.json')['commercial']}
        self.folders = {(TEMPLATES[k.split('/')[0]], f['building_type']): f for k, f in self.values['folders'].items()}

    def evidence(self, key):
        row = self.values['evidence'][key]
        source = self.values['source_files'][row['source_file_id']]
        out = {'extraction_date': row['extraction_date'], 'interpretation_note': row['interpretation'],
               'original_unit': row['original_unit'], 'original_value': row['original_value'],
               'source_file_sha256': source['sha256'], 'source_locator': f"{source['archive_path']}!{source['path']}#{row['locator']}",
               'source_project': source['project'], 'source_revision': source['version'], 'transformation': row['transformation']}
        return {'id': stable_id('construction-evidence', out), **out}

    def schedule(self, key):
        s = self.values['schedules'][key]
        return {k: s[k] for k in ('source_name', 'schedule_type', 'units', 'time_resolution_minutes', 'rules')}

    def __call__(self, entry, row, *documents):
        source = entry['source']
        folder = self.folders.get((source['template'], source['building_type']))
        if folder is None:
            return
        building = folder['fenestration']['building']
        infiltration = folder['infiltration']
        cited = [self.evidence(building['evidence']), self.evidence(infiltration['evidence'])]
        fills = [(fill, self.evidence(fill['evidence'])) for fill in folder['mass_fills']]
        detailed = documents[0]['mass_accounting']  # unified documents cite the detailed recipes
        recipes, counted = detailed['recipes'], detailed['reference']['counted_floor_area_m2']
        spaces = {s['name']: s for s in self.geometry[(source['template'], source['building_type'])]['spaces']}
        for document in documents:
            document['fenestration_defaults'] = {**{k: dict(v) for k, v in building['value'].items()},
                                                 'basis': 'whole_building_zone_surfaces', 'evidence_id': cited[0]['id']}
            current = document['infiltration']
            current['default_method'] = current['method']
            current['methods'] = {'doe_design_flow': {
                'zone_rules': [{'method': r['method'], 'value': r['value'], 'unit': r['unit'], 'coefficients': r['coefficients'],
                                'schedule': self.schedule(r['schedule_id']), 'zones': r['zones']}
                               for r in infiltration['zone_rules']],
                'excluded_zones': infiltration['excluded_zones'], 'evidence_id': cited[1]['id'],
                'consumer_inputs': 'exterior surface or wall area of each zone, from the consumer geometry'}}
            accounting = document['mass_accounting']
            entries = accounting['additional_mass'].setdefault('entries', [])
            for fill, evidence in fills:
                recipe = next((k for k, r in recipes.items() if sorted(l['properties']['name'] for l in r['layers']) == fill['layers']), None)
                if recipe is None:
                    raise ValueError(f'No mass recipe with layers {fill["layers"]} in {entry["name"]}')
                space = spaces[fill['space']]
                area = fill['area_per_floor_area'] * space['floor_area_m2'] * space['multiplier']
                item = {'area_convention': 'DOE InternalMass area per DOE zone floor area, applied to the source space; multiplier applied once',
                        'area_per_counted_floor_area': area / counted,
                        'capacity_per_counted_floor_area_J_m2_K': area / counted * recipes[recipe]['capacity_J_m2_K'],
                        'recipe_id': recipe, 'reference_area_m2': area, 'evidence_id': evidence['id'],
                        'scope': {'counted_floor_area': space['part_of_total_floor_area'], 'kind': 'source_space',
                                  'native_building_type': space['standards_building_type'],
                                  'native_space_type': space['standards_space_type'], 'source_space_name': space['name'],
                                  'source_story': None},
                        'source_locator': f"DOE reference InternalMass in zone {fill['zone']} (register {fill['row']})",
                        'source_operands': {'area_per_floor_area': fill['area_per_floor_area'], 'area_per_person_m2': None,
                                            'direct_area_m2': None, 'id': f"{fill['zone']} DOE mass",
                                            'source_multiplier': space['multiplier'], 'source_space_floor_area_m2': space['floor_area_m2']}}
                item['id'] = stable_id('source-mass-quantity', item)
                if all(e['id'] != item['id'] for e in entries):
                    entries.append(item)
            for e in [*cited, *(e for _, e in fills)]:
                document['evidence'][e['id']] = e


def apply_program_water_gains(sources, values=None):
    """Zone gains on the program-scope hot-water loads of the DOE Ref folders; returns the changed record IDs."""
    values = values or load_json(VALUES)
    changed = set()
    for key, folder in sorted(values['folders'].items()):
        template, building_type = TEMPLATES[key.split('/')[0]], folder['building_type']
        effects = gain_effects(folder)
        if not effects:
            continue
        for record in sources.programs.values():
            if (record['template'], record['building_type']) != (template, building_type) or record['derivation'] == 'composed':
                continue
            entry = load_entry(record, 'hot_water_volume')
            if entry and entry.get('value'):
                entry['thermal_effects'] = copy.deepcopy(effects)
                entry['zone_heat_assignment'] = 'program_zones'
                cite(record, effects['sensible_fraction']['evidence_id'])
                changed.add(record['id'])
    return changed
