"""Extract the IECC commercial prototype definitions of one edition (ADR 0040).

python -m scripts.iecc_commercial_values --idf-root <commercial-iecc dir> --edition 2021
    [--manifest <SOURCES-prototypes.json>] [--check]

Reads the 16 types x 19 locations of one edition from the extracted PNNL archives
pinned in sources/reference-models-lock.json (family commercial-iecc) and writes the
committed definition input data/program-inputs/iecc-commercial-<edition>.json, which
scripts.iecc_commercial_overlay applies without the IDFs:
- source_files and provenance in the definition shapes, one source file per IDF;
- schedules: every schedule the records use, as hourly definition rulesets, each
  checked over the full year, holidays and design days against its IDF original;
- programs: one per standards space type (scripts.iecc_commercial_zones), loads
  area-weighted over the zones with their multipliers, absent objects as source zeros,
  and the area-dominant schedule per slot. A load that differs by location keeps the
  most common value in `value` and the others in `value_by_climate` (plan C6);
- mixes from scripts.program_composition.compose with the composition-policy recipes,
  weighted by IDF zone floor area times multiplier;
- services: hot-water draws with their zone gains, and the building services
  (elevators, reach-in refrigeration, exhaust fans, exterior lights and equipment,
  refrigeration cases and racks);
- envelope: per type and location, the detailed constructions, design-flow
  infiltration and window ratios (scripts.iecc_commercial_envelope).
With --manifest, every IDF is checked against the archive member checksums recorded
when the pinned archives were extracted. --check rebuilds and compares the file.
"""
import argparse
import copy
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

from scripts import iecc_commercial_envelope as envelope
from scripts import idf_reader, idf_schedules
from scripts.common import ROOT, load_json
from scripts.definition_contract import parameter, record, stable_id
from scripts.iecc_commercial_zones import BASE_CITY, CITIES, FAMILY, TYPES, Lookup, normalize, template
from scripts.reconciliation_values import KINDS, ruleset

LOCK = ROOT/'sources/reference-models-lock.json'
EXTRACTION_DATE = '2026-10-26'
OUTPUT = 'data/program-inputs/iecc-commercial-{}.json'
ELEVATOR = {'elevatorlift', 'elevatorlightsfan', 'elevators'}
REACH_IN = {'reachinfreezer', 'reachinrefrigerator'}
ADDITIONAL_LIGHTING = ('plugin', 'allowance', 'display')
ZERO = {'source_name': 'IECC prototype: no object (constant 0)', 'schedule_type': 'fraction', 'units': 'dimensionless',
        'interpolation': 'none', 'time_resolution_minutes': 60,
        'rules': [{'day_types': 'Default', 'start_date': '2014-01-01T00:00:00+00:00', 'end_date': '2014-12-31T00:00:00+00:00',
                   'type': 'Constant', 'values': [0.0], 'source_index': 0}]}
GAINS = {'zone_gains': 'applied', 'semantics': 'EnergyPlus WaterUse:Equipment',
         'sensible': 'fraction x mass flow x cp x (mixed - zone air temperature)',
         'latent': 'fraction of the water that can evaporate'}
FRACTIONS = {'lighting': {'radiant': 'radiant', 'return_air': 'to_return_air', 'visible': 'visible'},
             'additional_lighting': {'radiant': 'radiant', 'return_air': 'to_return_air', 'visible': 'visible'},
             'electric_equipment': {'radiant': 'radiant', 'latent': 'latent', 'lost': 'lost'},
             'gas_equipment': {'radiant': 'radiant', 'latent': 'latent', 'lost': 'lost'}}
UNITS = {'occupancy': 'person/m2', 'lighting': 'W/m2', 'additional_lighting': 'W/m2', 'electric_equipment': 'W/m2',
         'gas_equipment': 'W/m2'}
QUANTITIES = tuple(UNITS)
SAME = 1e-9  # relative; values equal across locations are written by one generator


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def close(a, b, tolerance=SAME):
    if a is None or b is None:
        return a is b
    return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))


class Extract:
    """Source files, evidence and schedules shared by the whole edition."""

    def __init__(self, idf_root, archives, members):
        self.idf_root, self.archives, self.members = Path(idf_root), archives, members
        self.source_files, self.evidence, self.schedules, self.checked = {}, {}, {}, 0
        self.retrieval = load_json(LOCK)['retrieval_date']

    def source_file(self, path):
        relative = Path(path).relative_to(self.idf_root).as_posix()
        archive = self.archives[relative.split('/')[0]+'.zip']
        digest = sha256(path)
        member = 'commercial-iecc/'+relative
        if self.members is not None and self.members.get(member) != digest:
            raise ValueError(f'IDF differs from its archive member record: {member}')
        row = {'source_id': 'pnnl-prototypes', 'project': 'DOE/PNNL Prototype Building Models (IECC commercial)',
               'version': 'energycodes.gov 2023-10 IECC bundles, EnergyPlus 22.1', 'path': relative,
               'archive_path': archive['path'], 'archive_sha256': archive['sha256'], 'url': archive['url'],
               'retrieval_date': self.retrieval, 'sha256': digest, 'size_bytes': Path(path).stat().st_size,
               'license_path': 'sources/licenses/pnnl-prototypes.txt'}
        key = stable_id('sourcefile', row)[:len('sourcefile-')+20]
        self.source_files[key] = {'id': key, **row}
        return key

    def cite(self, source_file, locator, value, unit, transformation, note):
        row = {'source_file_id': source_file, 'locator': locator, 'original_value': value, 'original_unit': unit,
               'transformation': transformation, 'extraction_date': EXTRACTION_DATE, 'interpretation': note}
        key = stable_id('evidence', row)
        self.evidence[key] = {'id': key, **row}
        return key

    def schedule(self, model, source_file, name, kind, days, note=''):
        """A definition schedule from a Schedule:Compact or Schedule:Constant, checked over the year."""
        compact = model.schedules().get(name.lower())
        constant = next((f for f in model.all('schedule:constant') if f[0].lower() == name.lower()), None)
        if compact is not None:
            rules, fields = ruleset(compact), compact
            expected, _ = idf_schedules.evaluate_compact(compact, days)
            locator = f'Schedule:Compact {compact[0]}'
        elif constant is not None:
            value = float(constant[2])
            rules = [{'day_types': 'Default', 'start_date': '2014-01-01T00:00:00+00:00', 'end_date': '2014-12-31T00:00:00+00:00',
                      'type': 'Constant', 'values': [value], 'source_index': 0}]
            fields, expected = constant, {k: [value]*24 for k in days}
            locator = f'Schedule:Constant {constant[0]}'
        else:
            raise ValueError(f'No Schedule:Compact or Schedule:Constant {name} in {model.path.name}')
        got = idf_schedules.evaluate_ruleset(rules, lambda r: r['values'] * (24 // len(r['values'])), days)
        bad = [k for k in days if not (expected[k] is None and got[k] is None) and not idf_schedules.same(expected[k], got[k])]
        if bad:
            raise ValueError(f'Converted {name} differs from its source on {bad[:3]} ({model.path.name})')
        self.checked += 1
        evidence = self.cite(source_file, locator, fields[1:], fields[1] or 'schedule type limits',
                             'compact For order to last-specific-wins rules; Until times to hourly energy-conserving means',
                             'IECC prototype source schedule (ADR 0040); checked over the full year, holidays and design days.'+note)
        schedule_type, units = KINDS[kind]
        content = {'source_name': fields[0], 'schedule_type': schedule_type, 'units': units, 'interpolation': 'none',
                   'time_resolution_minutes': 60, 'evidence_ids': [evidence], 'rules': rules}
        key = stable_id('schedule', content)
        self.schedules[key] = {'id': key, **content}
        return key

    def zero(self):
        key = stable_id('schedule', ZERO)
        self.schedules[key] = {'id': key, **copy.deepcopy(ZERO)}
        return key


# ---------------------------------------------------------------- per-model objects

def schedule_fields(model, name):
    """Comparable content of a schedule, for checking that locations agree."""
    if not name:
        return None
    compact = model.schedules().get(name.lower())
    if compact is not None:
        return ['compact', *compact]
    constant = next((f for f in model.all('schedule:constant') if f[0].lower() == name.lower()), None)
    return ['constant', *constant] if constant else ['missing', name]


def zones(model):
    """{zone key: name, multiplier, floor area (unmultiplied), counted flag}."""
    floors = defaultdict(float)
    for s in model.surfaces():
        if s['type'] == 'floor':
            floors[s['zone'].lower()] += idf_reader.area(s['vertices'])
    out = {}
    for f in model.all('zone'):
        key = f[0].lower()
        counted = not (len(f) > 12 and f[12].strip().lower() == 'no')
        out[key] = {'name': f[0], 'multiplier': model.zones[key]['multiplier'], 'floor_m2': floors[key], 'counted': counted}
    return out


def density(item, cls, floor, people):
    """An internal-gain object's value per zone floor area (person/m2 or W/m2)."""
    a, b, c = item['values']
    method = item['method']
    if cls == 'people':
        return {'people': (a or 0.0)/floor if floor else 0.0, 'people/area': b, 'area/person': 1/c if c else None}[method]
    if method in ('lightinglevel', 'equipmentlevel'):
        return (a or 0.0)/floor if floor else 0.0
    if method == 'watts/area':
        return b
    if method == 'watts/person':
        return (c or 0.0)*people
    raise ValueError(f'Unknown design level method {method} in {item["name"]}')


def zone_objects(model, geometry):
    """{zone: {quantity: object}} for the program loads, and the zone-located service equipment."""
    out, services = defaultdict(dict), []
    people = defaultdict(float)

    def put(zone, quantity, entry):
        if quantity in out[zone]:
            raise ValueError(f'Several {quantity} objects in zone {zone} ({model.path.name})')
        out[zone][quantity] = entry
    for item in model.loads('people'):
        for z in item['zones']:
            value = density(item, 'people', geometry[z]['floor_m2'], 0)
            people[z] += value
            put(z, 'occupancy', {'object': item['name'], 'value': value, 'schedule': item['schedule'],
                                 'activity': item['activity_schedule'] or None, 'fractions': {}})
    lights = defaultdict(list)
    for item in model.loads('lights'):
        for z in item['zones']:
            lights[z].append(item)
    for z, items in lights.items():
        extra = [i for i in items if any(t in (i['name']+' '+i['subcategory']).lower() for t in ADDITIONAL_LIGHTING)]
        base = [i for i in items if i not in extra]
        if len(base) != 1 or len(extra) > 1:
            raise ValueError(f'Unexpected lights objects in zone {z}: {[i["name"] for i in items]}')
        for quantity, group in (('lighting', base), ('additional_lighting', extra)):
            for i in group:
                put(z, quantity, {'object': i['name'], 'value': density(i, 'lights', geometry[z]['floor_m2'], people[z]),
                                  'schedule': i['schedule'], 'fractions': i['fractions'], 'subcategory': i['subcategory']})
    for cls, quantity in (('electricequipment', 'electric_equipment'), ('gasequipment', 'gas_equipment')):
        for item in model.loads(cls):
            subcategory = item['subcategory'].lower().replace(' ', '')
            for z in item['zones']:
                if cls == 'electricequipment' and subcategory in ELEVATOR | REACH_IN:
                    services.append({'end_use': 'elevator' if subcategory in ELEVATOR else 'refrigeration_equipment',
                                     'name': item['name'], 'zone': z, 'method': item['method'], 'values': item['values'],
                                     'schedule': item['schedule'], 'fractions': item['fractions'], 'subcategory': item['subcategory'],
                                     'multiplier': geometry[z]['multiplier'], 'class': cls})
                    continue
                put(z, quantity, {'object': item['name'], 'value': density(item, cls, geometry[z]['floor_m2'], people[z]),
                                  'schedule': item['schedule'], 'fractions': item['fractions'], 'subcategory': item['subcategory']})
    for cls in ('hotwaterequipment', 'steamequipment', 'otherequipment', 'swimmingpool:indoor'):
        if model.all(cls):
            raise ValueError(f'Unported {cls} objects in {model.path.name}')
    return out, services


def thermostats(model):
    """{zone: {'heating': schedule, 'cooling': schedule}} from ZoneControl:Thermostat and its setpoint objects."""
    single_heat = {f[0].lower(): f[1] for f in model.all('thermostatsetpoint:singleheating')}
    single_cool = {f[0].lower(): f[1] for f in model.all('thermostatsetpoint:singlecooling')}
    dual = {f[0].lower(): (f[1], f[2]) for f in model.all('thermostatsetpoint:dualsetpoint')}
    out = {}
    for f in model.all('zonecontrol:thermostat'):
        found = {}
        names = [v.lower() for v in f[3:] if v]
        for v in names:
            if v in dual:
                found['heating'], found['cooling'] = dual[v]
            elif v in single_heat:
                found['heating'] = single_heat[v]
            elif v in single_cool:
                found['cooling'] = single_cool[v]
        for zone in model.zone_names(f[1]):
            out[zone] = {**out.get(zone, {}), **found}
    return out


def humidistats(model):
    out = {}
    for f in model.all('zonecontrol:humidistat'):
        for zone in model.zone_names(f[1]):
            out[zone] = {'humidifying': f[2], **({'dehumidifying': f[3]} if len(f) > 3 and f[3] else {})}
    return out


def schedule_constant(model, name):
    fields = schedule_fields(model, name)
    if not fields or fields[0] == 'missing':
        return None
    numbers = sorted({idf_reader.number(v) for v in fields[3:] if idf_reader.number(v) is not None})
    return numbers[0] if len(numbers) == 1 else None


def water_draws(model, geometry):
    """WaterUse:Equipment draws, and stand-alone water heaters' use-side draws (no plant connection)."""
    out = []
    for f in model.all('wateruse:equipment'):
        zone = f[7].lower() if len(f) > 7 and f[7] else None
        out.append({'kind': 'WaterUse:Equipment', 'name': f[0], 'zone': zone, 'peak_flow_m3_s': idf_reader.number(f[2]),
                    'schedule': f[3], 'target_C': schedule_constant(model, f[4]) if len(f) > 4 and f[4] else None,
                    'sensible': schedule_constant(model, f[8]) if len(f) > 8 and f[8] else None,
                    'latent': schedule_constant(model, f[9]) if len(f) > 9 and f[9] else None,
                    'multiplier': geometry[zone]['multiplier'] if zone else 1})
    for f in model.all('waterheater:mixed'):
        peak, schedule, inlet = idf_reader.number(f[27]) if len(f) > 27 else None, f[28] if len(f) > 28 else '', f[30] if len(f) > 30 else ''
        if peak and not inlet:
            zone = f[21].lower() if f[19].strip().lower() == 'zone' and f[21] else None
            out.append({'kind': 'WaterHeater:Mixed use side', 'name': f[0], 'zone': zone, 'peak_flow_m3_s': peak,
                        'schedule': schedule, 'target_C': schedule_constant(model, f[2]), 'sensible': None, 'latent': None,
                        'multiplier': 1})  # a water heater's use flow is not zone equipment: no zone multiplier
    if any(len(f) > 0 for f in model.all('waterheater:stratified') if _stratified_standalone(f)):
        raise ValueError(f'Unported stand-alone WaterHeater:Stratified draw in {model.path.name}')
    return out


def _stratified_standalone(f):
    """WaterHeater:Stratified with a use-side flow and no use-side node (none in the IECC set)."""
    peak = idf_reader.number(f[41]) if len(f) > 41 else None
    return bool(peak) and not (len(f) > 43 and f[43])


def exhaust_fans(model):
    """Fan:ZoneExhaust with its zone (through the zone equipment lists) and its electric power."""
    lists = {}
    for f in model.all('zonehvac:equipmentlist'):
        for i in range(2, len(f) - 1, 6):
            if f[i].lower() == 'fan:zoneexhaust':
                lists.setdefault(f[0].lower(), []).append(f[i+1].lower())
    zone_of = {}
    for f in model.all('zonehvac:equipmentconnections'):
        for fan in lists.get(f[1].lower(), []):
            zone_of[fan] = f[0].lower()
    out = []
    for f in model.all('fan:zoneexhaust'):
        efficiency, pressure, flow = (idf_reader.number(v) for v in f[2:5])
        out.append({'end_use': 'exhaust_fan', 'name': f[0], 'zone': zone_of.get(f[0].lower()), 'schedule': f[1],
                    'efficiency': efficiency, 'pressure_rise_Pa': pressure, 'flow_m3_s': flow,
                    'flow_fraction_schedule': f[8] if len(f) > 8 and f[8] else None,
                    'subcategory': f[7] if len(f) > 7 else '',
                    'power_W': flow*pressure/efficiency if efficiency and flow is not None and pressure is not None else None})
    return out


def other_services(model):
    out = []
    for f in model.all('exterior:lights'):
        out.append({'end_use': 'exterior_lighting', 'name': f[0], 'schedule': f[1], 'design_level_W': idf_reader.number(f[2]),
                    'control': f[3] if len(f) > 3 else '', 'subcategory': f[4] if len(f) > 4 else ''})
    for f in model.all('exterior:fuelequipment'):
        out.append({'end_use': 'elevator' if 'elevator' in f[0].lower() else 'exterior_equipment', 'name': f[0], 'fuel': f[1],
                    'schedule': f[2], 'design_level_W': idf_reader.number(f[3]), 'subcategory': f[4] if len(f) > 4 else ''})
    for f in model.all('refrigeration:case'):
        out.append({'end_use': 'refrigeration_case', 'name': f[0], 'zone': f[2].lower(), 'availability': f[1],
                    'capacity_W_m': idf_reader.number(f[5]), 'latent_heat_ratio': idf_reader.number(f[6]),
                    'runtime_fraction': idf_reader.number(f[7]), 'length_m': idf_reader.number(f[8]),
                    'operating_temperature_C': idf_reader.number(f[9]), 'fan_power_W_m': idf_reader.number(f[13]),
                    'lighting_power_W_m': idf_reader.number(f[14]), 'lighting_schedule': f[16]})
    for f in model.all('refrigeration:compressorrack'):
        out.append({'end_use': 'refrigeration_rack', 'name': f[0], 'heat_rejection': f[1].lower(),
                    'cop': idf_reader.number(f[2]), 'condenser_fan_W': idf_reader.number(f[4])})
    return out


# ---------------------------------------------------------------- one type

class TypeModels:
    """The 19 location models of one type and edition, with the zone groups."""

    def __init__(self, extract, idf_root, pnnl, edition, lookup):
        self.pnnl, self.building_type, self.edition = pnnl, TYPES[pnnl], edition
        self.template = template(edition)
        self.paths = {city: Path(idf_root)/f'IECC_{pnnl}'/f'IECC_{pnnl}_STD{edition}_{city}.idf' for city in CITIES}
        self.models, self.files = {}, {}
        for city, path in self.paths.items():
            model = idf_reader.Model(path)
            header = next((line for line in path.read_text(errors='replace').splitlines()[:300] if 'AnalysisClimateZone' in line), '')
            if header.split('=')[-1].strip() != CITIES[city][0]:
                raise ValueError(f'{path.name} names climate zone {header!r}, not {CITIES[city][0]}')
            self.models[city] = model
            self.files[city] = extract.source_file(path)
        self.base = self.models[BASE_CITY]
        self.geometry = zones(self.base)
        for city, model in self.models.items():
            other = zones(model)
            if set(other) != set(self.geometry) or any(
                    other[k]['multiplier'] != g['multiplier'] or other[k]['counted'] != g['counted']
                    or not close(other[k]['floor_m2'], g['floor_m2'], 1e-9) for k, g in self.geometry.items()):
                raise ValueError(f'Zone geometry differs between {BASE_CITY} and {city} for {pnnl} {edition}')
        self.space = {k: lookup(self.building_type, g['name']) for k, g in self.geometry.items()}
        self.groups = defaultdict(list)
        for k in sorted(self.geometry):
            self.groups[self.space[k][1]].append(k)
        self.days = idf_schedules.calendar_days(self.base.holidays())

    def area(self, zone):
        g = self.geometry[zone]
        return g['floor_m2']*g['multiplier']


def modal(values):
    """The most common value (ties: the base location's) and the exceptions by atlas climate."""
    counts = Counter(json.dumps(v, sort_keys=True) for v in values.values())
    top = max(counts.values())
    base_key = json.dumps(values[BASE_CITY], sort_keys=True)
    chosen = base_key if counts[base_key] == top else sorted(k for k, n in counts.items() if n == top)[0]
    value = json.loads(chosen)
    exceptions = {CITIES[c][1]: v for c, v in values.items() if json.dumps(v, sort_keys=True) != chosen}
    return value, dict(sorted(exceptions.items())), next(c for c, v in values.items() if json.dumps(v, sort_keys=True) == chosen)


def rounded(value):
    return None if value is None else round(value, 12)


class TypeExtract:
    """Programs, services and envelope of one type and edition."""

    def __init__(self, extract, models):
        self.x, self.m = extract, models
        self.conflicts, self.decisions = [], []
        self.objects, self.zone_services = {}, {}
        for city, model in models.models.items():
            self.objects[city], self.zone_services[city] = zone_objects(model, models.geometry)
        self.thermostats = {city: thermostats(model) for city, model in models.models.items()}
        self.humidistats = {city: humidistats(model) for city, model in models.models.items()}

    # -- helpers
    def same_schedule(self, name_by_city, what):
        """The schedule a slot uses must be the same content in every location."""
        contents = {city: schedule_fields(self.m.models[city], name) for city, name in name_by_city.items()}
        if len({json.dumps(c) for c in contents.values()}) > 1:
            raise ValueError(f'{what} schedule differs by location in {self.m.pnnl} {self.m.edition}: '
                             f'{sorted({c: n for c, n in name_by_city.items()}.items())[:4]}')

    def dominant(self, zones_, pick, label):
        """The area-dominant value of pick(zone) over the zones where it is not None; conflicts recorded."""
        weights = defaultdict(float)
        for z in zones_:
            v = pick(z)
            if v is not None:
                weights[json.dumps(v, sort_keys=True)] += self.m.area(z)
        if not weights:
            return None
        chosen = max(sorted(weights), key=lambda k: weights[k])
        if len(weights) > 1:
            self.conflicts.append({'program': label[0], 'slot': label[1], 'values': {k: round(w, 6) for k, w in sorted(weights.items())},
                                   'chosen': json.loads(chosen), 'reason_id': 'R-SLOT-CONFLICT'})
        return json.loads(chosen)

    def schedule(self, name, kind, note=''):
        return self.x.schedule(self.m.base, self.m.files[BASE_CITY], name, kind, self.m.days, note)

    # -- programs
    def programs(self):
        out = {}
        m = self.m
        calendar = self.calendar()
        draws, lumped = self.water()
        self.boosters = {city: [] for city in m.models}
        fenestration = self.fenestration()
        for space_type, zones_ in sorted(m.groups.items()):
            standards_building_type = m.space[zones_[0]][0]
            name = f'{space_type}_{m.building_type}'
            source_id = 'program-'+stable_id('program', {'template': m.template, 'building_type': m.building_type,
                                                         'space_type': space_type, 'source': 'iecc'})[-20:]
            source = {'id': source_id, 'building_type': m.building_type, 'template': m.template, 'source_family': FAMILY}
            r = record('program', source, name)
            area = math.fsum(m.area(z) for z in zones_)
            zone_list = ', '.join(m.geometry[z]['name'] for z in zones_)
            r.update(detail='SourcePrograms', available_details=['SourcePrograms'], optional=False, required_inputs=['floor_area'],
                     service_ids=[], loads=[], pnnl_building_type=m.pnnl, standards_building_type=standards_building_type,
                     source_zones=[{'name': m.geometry[z]['name'], 'floor_area_m2': rounded(m.geometry[z]['floor_m2']),
                                    'multiplier': m.geometry[z]['multiplier'], 'counted': m.geometry[z]['counted']} for z in zones_])
            evidence = set()
            for quantity in QUANTITIES:
                load = self.load(source_id, name, quantity, zones_, area, zone_list)
                r['loads'].append(load)
                evidence |= {load['evidence_id'], *load.get('climate_evidence_ids', {}).values()}
                evidence |= {e['evidence_id'] for e in load['thermal_effects'].values()}
                if load['schedule_id'] in self.x.schedules:
                    evidence |= set(self.x.schedules[load['schedule_id']].get('evidence_ids', []))
            water = self.hot_water(source_id, name, zones_, area, draws)
            r['loads'].append(water['load'])
            if water.get('service'):
                r['service_ids'] = [water['service']['id']]
                self.services_out.append(water['service'])
            evidence |= {water['load']['evidence_id']}
            for slot, (field, kind) in {'heating': ('heating_setpoint_schedule_id', 'temperature'),
                                        'cooling': ('cooling_setpoint_schedule_id', 'temperature')}.items():
                chosen = self.dominant(zones_, lambda z: self.thermostats[BASE_CITY].get(z, {}).get(slot), (name, slot))
                if chosen:
                    self.same_schedule({c: self.dominant_city(c, zones_, slot) for c in m.models}, f'{name} {slot}')
                    ems = self.ems_note(chosen)
                    sid = self.schedule(chosen, kind, ems)
                    r['parameters'][field] = parameter(sid, 'schedule reference', self.x.schedules[sid]['evidence_ids'][0])
                else:
                    ev = self.x.cite(m.files[BASE_CITY], 'ZoneControl:Thermostat (none in zones '+zone_list+')', None, 'schedule reference',
                                     'absence in the complete IECC model', f'No {slot} thermostat in this program (ADR 0040 item 4).')
                    r['parameters'][field] = parameter(None, 'schedule reference', ev, status='known')
                evidence.add(r['parameters'][field]['evidence_id'])
            activity = self.dominant(zones_, lambda z: (self.objects[BASE_CITY][z].get('occupancy') or {}).get('activity'), (name, 'activity'))
            if activity:
                sid = self.schedule(activity, 'activity')
                r['parameters']['activity_schedule_id'] = parameter(sid, 'schedule reference', self.x.schedules[sid]['evidence_ids'][0])
            else:
                ev = self.x.cite(m.files[BASE_CITY], 'People (none in zones '+zone_list+')', None, 'schedule reference',
                                 'absence in the complete IECC model', 'No occupants, so no activity schedule (ADR 0040 item 4).')
                r['parameters']['activity_schedule_id'] = parameter(None, 'schedule reference', ev, status='known')
            evidence.add(r['parameters']['activity_schedule_id']['evidence_id'])
            for slot in ('humidifying', 'dehumidifying'):
                chosen = self.dominant(zones_, lambda z: self.humidistats[BASE_CITY].get(z, {}).get(slot), (name, slot))
                if chosen:
                    sid = self.schedule(chosen, 'humidity')
                    r['parameters'][slot+'_setpoint_schedule_id'] = parameter(sid, 'schedule reference', self.x.schedules[sid]['evidence_ids'][0])
                    evidence.add(self.x.schedules[sid]['evidence_ids'][0])
            heating = r['parameters']['heating_setpoint_schedule_id']['value'] is not None
            cooling = r['parameters']['cooling_setpoint_schedule_id']['value'] is not None
            ev = self.x.cite(m.files[BASE_CITY], 'ZoneControl:Thermostat in zones '+zone_list,
                             {'heating': heating, 'cooling': cooling}, 'state', 'thermostat setpoint objects present in the program zones',
                             'Conditioning as the complete IECC model controls it (ADR 0040 item 4).')
            r['parameters']['conditioning'] = parameter({'heating_enabled': heating, 'cooling_enabled': cooling}, 'state', ev)
            evidence.add(ev)
            if space_type in fenestration:
                r['fenestration'] = fenestration[space_type]
                evidence.add(r['fenestration']['evidence_id'])
            r['source_calendar'] = calendar
            evidence.add(calendar['evidence_id'])
            r['evidence_ids'] = sorted(evidence)
            out[source_id] = (r, area, zones_)
        return out, lumped

    def dominant_city(self, city, zones_, slot):
        weights = defaultdict(float)
        for z in zones_:
            v = self.thermostats[city].get(z, {}).get(slot)
            if v:
                weights[v] += self.m.area(z)
        return max(sorted(weights), key=lambda k: weights[k]) if weights else None

    def ems_note(self, name):
        actuated = [f[0] for f in self.m.base.all('energymanagementsystem:actuator') if f[1].lower() == name.lower()]
        if not actuated:
            return ''
        return (f' EnergyManagementSystem actuator {", ".join(actuated)} overrides this schedule at run time in the source model; '
                'the input schedule is stored and the EMS control is not reproduced.')

    def load(self, source_id, name, quantity, zones_, area, zone_list):
        m = self.m
        per_city = {}
        for city in m.models:
            objs = self.objects[city]
            per_city[city] = rounded(math.fsum((objs[z].get(quantity) or {}).get('value', 0.0)*m.area(z) for z in zones_)/area) if area else 0.0
        value, exceptions, _ = modal(per_city)
        present = [z for z in zones_ if quantity in self.objects[BASE_CITY][z]]
        names = {city: self.dominant_name(city, zones_, quantity, name) for city in m.models}
        if any(names.values()):
            self.same_schedule({c: n for c, n in names.items() if n}, f'{name} {quantity}')
            if not all(names.values()) or not present:
                raise ValueError(f'{name} {quantity}: the object exists in some locations only')
        demand = stable_id('demand', {'program': source_id, 'quantity': quantity, 'source': 'iecc'})
        by_zone = {m.geometry[z]['name']: {'value': rounded((self.objects[BASE_CITY][z].get(quantity) or {}).get('value', 0.0)),
                                           'object': (self.objects[BASE_CITY][z].get(quantity) or {}).get('object'),
                                           'floor_area_m2': rounded(m.geometry[z]['floor_m2']), 'multiplier': m.geometry[z]['multiplier']}
                   for z in zones_}
        evidence = self.x.cite(m.files[BASE_CITY], f'{quantity} objects in zones {zone_list}', by_zone, UNITS[quantity]+' per zone',
                               'area-weighted over the program zones with their multipliers; absent objects count as zero',
                               'IECC prototype program load (ADR 0040); the most common value over the 19 location files'
                               + (', with the others in value_by_climate.' if exceptions else ', identical in all of them.'))
        load = {'basis': 'floor_area', 'quantity': quantity, 'unit': UNITS[quantity], 'value': value, 'status': 'known',
                'scope': 'program', 'evidence_id': evidence, 'required_inputs': ['floor_area'], 'demand_id': demand,
                'thermal_effects': {}}
        if exceptions:
            load['value_by_climate'] = exceptions
            load['climate_evidence_ids'] = {}
            for climate in exceptions:
                city = next(c for c, v in CITIES.items() if v[1] == climate)
                load['climate_evidence_ids'][climate] = self.x.cite(
                    m.files[city], f'{quantity} objects in zones {zone_list}',
                    {m.geometry[z]['name']: rounded((self.objects[city][z].get(quantity) or {}).get('value', 0.0)) for z in zones_},
                    UNITS[quantity]+' per zone', 'area-weighted over the program zones with their multipliers',
                    f'IECC prototype program load in climate zone {CITIES[city][0]} ({city}), which differs from the most common value (plan C6).')
        if not present:
            load['schedule_id'] = self.x.zero()
            return load
        schedule = names[BASE_CITY]
        load['schedule_id'] = self.schedule(schedule, 'fraction')
        self.peak_normalize(load)
        fractions = self.dominant(present, lambda z: {k: v for k, v in self.objects[BASE_CITY][z][quantity]['fractions'].items()
                                                      if k in FRACTIONS.get(quantity, {})}, (name, quantity+' fractions'))
        for source_key, target in FRACTIONS.get(quantity, {}).items():
            if fractions.get(source_key) is not None:
                load['thermal_effects'][target] = parameter(fractions[source_key], '1', evidence)
        return load

    def peak_normalize(self, load):
        """A fraction schedule above 1 (PNNL's 2006 and 2009 meeting and lounge lighting reach 1.1) becomes its
        peak-normalized equivalent with the density multiplied by the peak, so the load trajectory is unchanged."""
        original = self.x.schedules[load['schedule_id']]
        peak = max(v for r in original['rules'] for v in r['values'])
        if peak <= 1 + 1e-12:
            return
        rules = [{**r, 'values': [round(v/peak, 10) for v in r['values']]} for r in original['rules']]
        evidence = self.x.cite(self.x.evidence[original['evidence_ids'][0]]['source_file_id'], self.x.evidence[original['evidence_ids'][0]]['locator'],
                               {'peak': peak}, 'dimensionless', 'schedule values divided by their peak; the load density multiplied by it',
                               'Peak-normalized equivalent of a source fraction schedule above 1 (ADR 0040 agent decision 19); '
                               'the hourly load trajectory is unchanged.')
        content = {k: v for k, v in original.items() if k not in ('id', 'rules', 'evidence_ids')}
        content.update(rules=rules, evidence_ids=[*original['evidence_ids'], evidence], peak_divisor=peak)
        key = stable_id('schedule', content)
        self.x.schedules[key] = {'id': key, **content}
        load['schedule_id'] = key
        load['value'] = rounded(load['value']*peak)
        if load.get('value_by_climate'):
            load['value_by_climate'] = {c: rounded(v*peak) for c, v in load['value_by_climate'].items()}
        load['schedule_peak_scaling'] = peak

    def dominant_name(self, city, zones_, quantity, name):
        weights = defaultdict(float)
        for z in zones_:
            entry = self.objects[city][z].get(quantity)
            if entry:
                weights[entry['schedule']] += self.m.area(z)
        if not weights:
            return None
        if len(weights) > 1 and city == BASE_CITY:
            self.conflicts.append({'program': name, 'slot': quantity, 'values': dict(sorted(weights.items())),
                                   'chosen': max(sorted(weights), key=lambda k: weights[k]), 'reason_id': 'R-SLOT-CONFLICT'})
        return max(sorted(weights), key=lambda k: weights[k])

    # -- hot water
    def water(self):
        """Per-location zone draws and zoneless (lumped) draws."""
        m = self.m
        found = {city: water_draws(model, m.geometry) for city, model in m.models.items()}
        return ({city: [d for d in draws if d['zone']] for city, draws in found.items()},
                {city: [d for d in draws if not d['zone']] for city, draws in found.items()})

    def hot_water(self, source_id, name, zones_, area, draws):
        """The program's hot-water draw: the most common value over the locations, the others by climate."""
        m = self.m
        mine = {city: [d for d in found if d['zone'] in zones_] for city, found in draws.items()}
        if any(d['kind'] == 'WaterUse:Equipment' for ds in mine.values() for d in ds):
            for city, ds in mine.items():  # heater use flows beside fixture draws are boosters, kept as services
                self.boosters[city] += [{**d, 'program': source_id} for d in ds if d['kind'] != 'WaterUse:Equipment']
            mine = {city: [d for d in ds if d['kind'] == 'WaterUse:Equipment'] for city, ds in mine.items()}
        per_city = {city: rounded(math.fsum(d['peak_flow_m3_s']*d['multiplier'] for d in ds)/area) if ds else 0.0
                    for city, ds in mine.items()}
        value, exceptions, _ = modal(per_city)
        demand = stable_id('demand', {'program': source_id, 'quantity': 'hot_water_volume', 'source': 'iecc'})
        zone_list = ', '.join(m.geometry[z]['name'] for z in zones_)
        if not any(mine.values()):
            ev = self.x.cite(m.files[BASE_CITY], 'WaterUse:Equipment (none in zones '+zone_list+')', 0.0, 'm3/s',
                             'absence in the complete IECC model is a source zero', 'No hot-water draw in this program (ADR 0040 item 4).')
            return {'load': {'basis': 'floor_area', 'quantity': 'hot_water_volume', 'unit': 'm3/s/m2', 'value': 0.0, 'status': 'known',
                             'scope': 'program', 'schedule_id': self.x.zero(), 'evidence_id': ev, 'required_inputs': ['floor_area'],
                             'thermal_effects': {}, 'demand_id': demand}}
        city = BASE_CITY if mine[BASE_CITY] else next(c for c in CITIES if mine[c])
        shapes = {c: json.dumps(sorted([json.dumps(schedule_fields(m.models[c], d['schedule'])), d['target_C'], d['sensible'], d['latent']]
                                       for d in ds), default=str) for c, ds in mine.items() if ds}
        if len(set(shapes.values())) > 1:
            raise ValueError(f'Hot-water schedules or fractions of {name} differ by location')
        model, source_file, ds = m.models[city], m.files[city], mine[city]
        weights = defaultdict(float)
        for d in ds:
            weights[d['schedule']] += d['peak_flow_m3_s']*d['multiplier']
        schedule = max(sorted(weights), key=lambda k: weights[k])
        if len(weights) > 1:
            self.conflicts.append({'program': name, 'slot': 'hot_water', 'values': dict(sorted(weights.items())), 'chosen': schedule,
                                   'reason_id': 'R-SLOT-CONFLICT'})
        targets = {d['target_C'] for d in ds}
        pairs = {(d['sensible'], d['latent']) for d in ds}
        if len(targets) > 1 or len(pairs) > 1:
            raise ValueError(f'Several hot-water targets or gain fractions in {name}: {targets} {pairs}')

        def cite(c):
            return self.x.cite(
                m.files[c], 'WaterUse:Equipment and stand-alone water heaters '+', '.join(d['name'] for d in mine[c]),
                [{k: d[k] for k in ('kind', 'name', 'zone', 'peak_flow_m3_s', 'multiplier', 'schedule', 'target_C', 'sensible', 'latent')}
                 for d in mine[c]], 'm3/s; C; fractions',
                'sum of peak flow x zone multiplier (WaterUse:Equipment only; a water heater use flow is not zone equipment) over the '
                'program zones, divided by their multiplied floor area',
                f'IECC prototype hot-water draw (ADR 0040 item 9), climate zone {CITIES[c][0]} ({c}).')
        evidence = cite(city)
        sensible, latent = next(iter(pairs))
        effects = {}
        if sensible is not None or latent is not None:
            effects = {**GAINS, 'sensible_fraction': parameter(sensible or 0.0, '1', evidence),
                       'latent_fraction': parameter(latent or 0.0, '1', evidence)}
        sid = stable_id('service', {'template': m.template, 'building_type': m.building_type, 'end_use': 'main',
                                    'program': source_id, 'source': 'iecc'})
        schedule_id = self.x.schedule(model, source_file, schedule, 'fraction', m.days)
        load = {'basis': 'floor_area', 'quantity': 'hot_water_volume', 'unit': 'm3/s/m2', 'value': value, 'status': 'known',
                'scope': 'building_service', 'schedule_id': schedule_id, 'evidence_id': evidence, 'required_inputs': ['floor_area'],
                'service_id': sid, 'demand_id': sid, 'target_temperature_degC': next(iter(targets)), 'thermal_effects': copy.deepcopy(effects),
                'zone_heat_assignment': 'beneficiary_program_zones' if effects else 'unresolved'}
        evidence_ids = {evidence, *self.x.schedules[schedule_id]['evidence_ids']}
        if exceptions:
            load['value_by_climate'] = exceptions
            load['climate_evidence_ids'] = {}
            for climate in exceptions:
                c = next(k for k, v in CITIES.items() if v[1] == climate)
                load['climate_evidence_ids'][climate] = cite(c) if mine[c] else self.x.cite(
                    m.files[c], 'WaterUse:Equipment (none in zones '+zone_list+')', 0.0, 'm3/s',
                    'absence in the complete IECC model is a source zero',
                    f'No hot-water draw in this program in climate zone {CITIES[c][0]} ({c}), which differs from the most common value.')
            evidence_ids |= set(load['climate_evidence_ids'].values())
        service = {'id': sid, 'template': m.template, 'building_type': m.building_type, 'end_use': 'main',
                   'assignment': 'consumer_host_when_applicable', 'beneficiary_program_ids': [source_id], 'ownership': 'instantiate_once',
                   'path_id': f'{m.building_type}|{m.template}|main|{source_id}', 'load': load,
                   'evidence_ids': sorted(evidence_ids), 'source_evidence_ids': []}
        program_load = {**copy.deepcopy(load), 'scope': 'program_service',
                        'zone_heat_assignment': 'program_zones' if effects else 'unresolved'}
        return {'load': program_load, 'service': service}

    # -- services
    def services(self, programs):
        """Building services; a value that differs by location keeps the most common one and value_by_climate."""
        m = self.m
        by_city = {}
        for city, model in m.models.items():
            items = [*self.zone_services[city], *exhaust_fans(model), *other_services(model)]
            by_city[city] = {(i['end_use'], i['name'], i.get('zone')): i for i in items}
        keys = set(by_city[BASE_CITY])
        if any(set(v) != keys for v in by_city.values()):
            raise ValueError(f'Building services differ by location in {m.pnnl} {m.edition}')
        program_of = {z: sid for sid, (_, _, zones_) in programs.items() for z in zones_}
        out = []
        for key in sorted(keys, key=str):
            item = by_city[BASE_CITY][key]
            for field in ('schedule', 'availability', 'lighting_schedule', 'flow_fraction_schedule'):
                if item.get(field):
                    self.same_schedule({c: by_city[c][key][field] for c in m.models}, f'service {item["name"]} {field}')
            per_city = {c: self.service_load(by_city[c][key], m.models[c], None)[1] for c in m.models}
            value, exceptions, chosen = modal(per_city)
            item = by_city[chosen][key]
            load, _ = self.service_load(item, m.models[chosen], m.files[chosen])
            evidence = load['evidence_id']
            if exceptions:
                first = lambda v: v[0] if isinstance(v, list) else v
                load['value_by_climate'] = {c: first(v) for c, v in exceptions.items()}
                if any(isinstance(v, list) for v in exceptions.values()):
                    load['source_fields_by_climate'] = exceptions
                load['climate_evidence_ids'] = {}
                for climate in exceptions:
                    city = next(c for c, v in CITIES.items() if v[1] == climate)
                    load['climate_evidence_ids'][climate] = self.x.cite(
                        m.files[city], f'{item["end_use"]} {item["name"]}', {k: v for k, v in by_city[city][key].items() if k != 'values'},
                        'SI (W, W/m, m3/s, Pa)', 'object fields as written in the IDF',
                        f'IECC prototype building service in climate zone {CITIES[city][0]} ({city}), which differs from the most common value.')
            zone = item.get('zone')
            beneficiaries = [program_of[zone]] if zone in program_of else []
            sid = stable_id('service', {'template': m.template, 'building_type': m.building_type, 'end_use': item['end_use'],
                                        'name': item['name'], 'zone': zone, 'source': 'iecc'})
            load.update(service_id=sid, demand_id=sid)
            evidence_ids = {evidence, *load.get('climate_evidence_ids', {}).values()}
            for key2 in ('schedule_id', 'lighting_schedule_id', 'flow_fraction_schedule_id'):
                if load.get(key2):
                    evidence_ids |= set(self.x.schedules[load[key2]]['evidence_ids'])
            out.append({'id': sid, 'template': m.template, 'building_type': m.building_type, 'end_use': item['end_use'],
                        'name': item['name'], 'assignment': 'consumer_host_when_applicable' if beneficiaries else 'building_level',
                        'beneficiary_program_ids': beneficiaries, 'ownership': 'instantiate_once',
                        'path_id': f"{m.building_type}|{m.template}|{item['end_use']}|{item['name']}",
                        'load': load, 'evidence_ids': sorted(evidence_ids), 'source_evidence_ids': []})
        return out

    def service_load(self, item, model, source_file):
        """(definition service load, comparable value) for one building-service object."""
        end_use = item['end_use']
        base = {'status': 'known', 'scope': 'building_service', 'required_inputs': []}
        if end_use in ('elevator', 'refrigeration_equipment') and 'method' in item:
            level, per_area, _ = item['values']
            floor = self.m.geometry[item['zone']]['floor_m2']
            watts = (level if item['method'] == 'equipmentlevel' else (per_area or 0.0)*floor)*item['multiplier']
            value = rounded(watts)
            fractions = {k: v for k, v in item['fractions'].items() if v is not None}
            if source_file is None:
                return None, value
            ev = self.x.cite(source_file, f'ElectricEquipment {item["name"]} ({item["subcategory"]})',
                             {k: item[k] for k in ('method', 'values', 'schedule', 'fractions', 'multiplier', 'zone')},
                             'W or W/m2; fractions', 'design level times the zone multiplier, instantiated once per building',
                             'IECC prototype zone-located service equipment (ADR 0040 item 9).')
            return {**base, 'evidence_id': ev, 'quantity': 'electric_equipment', 'basis': 'absolute', 'unit': 'W', 'value': value,
                    'schedule_id': self.x.schedule(model, source_file, item['schedule'], 'fraction', self.m.days),
                    'fuel': 'Electricity', 'source_zone_multiplier': item['multiplier'],
                    'thermal_effects': {k: parameter(v, '1', ev) for k, v in sorted(fractions.items())}}, value
        if end_use == 'exhaust_fan':
            value = rounded(item['power_W'])
            if source_file is None:
                return None, [value, item['flow_m3_s']]
            ev = self.x.cite(source_file, f'Fan:ZoneExhaust {item["name"]}', {k: v for k, v in item.items() if k != 'end_use'},
                             'm3/s; Pa; efficiency', 'electric power = maximum flow x pressure rise / total efficiency',
                             'IECC prototype exhaust fan (ADR 0040 item 9); air flow stays with the systems, which are deferred.')
            load = {**base, 'evidence_id': ev, 'quantity': 'electric_equipment', 'basis': 'absolute', 'unit': 'W', 'value': value,
                    'schedule_id': self.x.schedule(model, source_file, item['schedule'], 'fraction', self.m.days), 'fuel': 'Electricity',
                    'exhaust_flow_m3_s': item['flow_m3_s'], 'pressure_rise_Pa': item['pressure_rise_Pa'],
                    'fan_total_efficiency': item['efficiency'], 'thermal_effects': {'lost': parameter(1.0, '1', ev)}}
            if item['flow_fraction_schedule']:
                load['flow_fraction_schedule_id'] = self.x.schedule(model, source_file, item['flow_fraction_schedule'], 'fraction', self.m.days)
            return load, [value, item['flow_m3_s']]
        if end_use in ('elevator', 'exterior_equipment'):
            value = rounded(item['design_level_W'])
            if source_file is None:
                return None, value
            ev = self.x.cite(source_file, f'Exterior:FuelEquipment {item["name"]}', item, 'W', 'object fields as written in the IDF',
                             'IECC prototype exterior equipment (ADR 0040 item 9).')
            electric = item['fuel'].lower() == 'electricity'
            return {**base, 'evidence_id': ev, 'quantity': 'electric_equipment' if electric else 'gas_equipment', 'basis': 'absolute',
                    'unit': 'W', 'value': value, 'fuel': item['fuel'],
                    'schedule_id': self.x.schedule(model, source_file, item['schedule'], 'fraction', self.m.days),
                    'thermal_effects': {'lost': parameter(1.0, '1', ev)}}, value
        if end_use == 'exterior_lighting':
            value = rounded(item['design_level_W'])
            if source_file is None:
                return None, value
            ev = self.x.cite(source_file, f'Exterior:Lights {item["name"]}', item, 'W', 'object fields as written in the IDF',
                             'IECC prototype exterior lights (ADR 0040 item 9).')
            return {**base, 'evidence_id': ev, 'quantity': 'exterior_lighting', 'basis': 'absolute', 'unit': 'W', 'value': value,
                    'schedule_id': self.x.schedule(model, source_file, item['schedule'], 'fraction', self.m.days),
                    'control': item['control'] or None}, value
        if end_use == 'refrigeration_case':
            value = [item[k] for k in ('capacity_W_m', 'length_m', 'fan_power_W_m', 'lighting_power_W_m')]
            if source_file is None:
                return None, value
            ev = self.x.cite(source_file, f'Refrigeration:Case {item["name"]}', item, 'W/m; m; C', 'object fields as written in the IDF',
                             'IECC prototype refrigeration case (ADR 0040 item 9).')
            return {**base, 'evidence_id': ev, 'quantity': 'refrigeration_case', 'basis': 'case_length', 'unit': 'W/m',
                    'value': item['capacity_W_m'], 'length_m': item['length_m'], 'operating_temperature_degC': item['operating_temperature_C'],
                    'latent_heat_ratio': item['latent_heat_ratio'], 'runtime_fraction': item['runtime_fraction'],
                    'fan_power_W_m': item['fan_power_W_m'], 'lighting_power_W_m': item['lighting_power_W_m'],
                    'schedule_id': self.x.schedule(model, source_file, item['availability'], 'fraction', self.m.days),
                    'lighting_schedule_id': self.x.schedule(model, source_file, item['lighting_schedule'], 'fraction', self.m.days)}, value
        if end_use == 'refrigeration_rack':
            value = [item['condenser_fan_W'], item['cop']]
            if source_file is None:
                return None, value
            ev = self.x.cite(source_file, f'Refrigeration:CompressorRack {item["name"]}', item, 'W; COP', 'object fields as written in the IDF',
                             'IECC prototype compressor rack (ADR 0040 item 9).')
            return {**base, 'evidence_id': ev, 'quantity': 'refrigeration_rack', 'basis': 'absolute', 'unit': 'W',
                    'value': item['condenser_fan_W'], 'cop': item['cop'], 'heat_rejection': item['heat_rejection'], 'schedule_id': None}, value
        raise ValueError('Unknown building service: '+end_use)

    # -- the rest
    def calendar(self):
        m = self.m
        holidays = [{'name': n, 'rule': r} for n, r in m.base.holidays()]
        dst = m.base.first('runperiodcontrol:daylightsavingtime', None)
        value = {'holidays': holidays, 'daylight_saving': {'start': dst[0], 'end': dst[1], 'applied': False} if dst else None}
        for city, model in m.models.items():
            if [(n, r) for n, r in model.holidays()] != [(h['name'], h['rule']) for h in holidays]:
                raise ValueError(f'Holidays differ by location: {city}')
        ev = self.x.cite(m.files[BASE_CITY], 'RunPeriodControl:SpecialDays, RunPeriodControl:DaylightSavingTime', value, 'calendar rules',
                         'rules as written; dates are resolved per consumer year', 'IECC prototype holiday calendar (ADR 0040).')
        return {**value, 'evidence_id': ev}

    def fenestration(self):
        """Program window ratios per location: the most common, and the others by climate."""
        m = self.m
        zone_programs = {z: m.space[z][1] for z in m.geometry}
        per_city = {city: envelope.window_ratios(model, zone_programs)['programs'] for city, model in m.models.items()}
        out = {}
        for space_type in m.groups:
            values = {city: per_city[city].get(space_type) for city in m.models}
            if all(v is None for v in values.values()):
                continue
            value, exceptions, _ = modal(values)
            ev = self.x.cite(m.files[BASE_CITY], 'FenestrationSurface:Detailed by zone', value, 'm2/m2',
                             'window over true outdoor wall area by direction, zone multipliers applied',
                             'IECC prototype program window ratios (ADR 0040 item 8); the most common over the 19 locations.')
            entry = {'basis': 'program_zone_surfaces', 'wwr': {d: value[d] for d in 'NESW'}, 'roof': value['roof'], 'evidence_id': ev}
            if exceptions:
                entry['value_by_climate'] = {c: {'wwr': {d: v[d] for d in 'NESW'}, 'roof': v['roof']} for c, v in exceptions.items()}
            out[space_type] = entry
        return out


def compose_mixes(extract, building_type, tmpl, programs):
    """Department and general mixes through scripts.program_composition.compose itself."""
    from scripts import program_composition
    rows, legacy = [], []
    for sid, (r, area, zones_) in programs.items():
        space_type = r['name'][:-len(building_type)-1]
        counted = math.fsum(z['floor_area_m2']*z['multiplier'] for z in r['source_zones'] if z['counted'])
        rows.append({'program_id': sid, 'source_space_type': space_type, 'source_building_type': r['standards_building_type'],
                     'represented_area_m2': counted, 'area_status': 'derived' if counted > 0 else 'non_counted',
                     'source_file_id': r['zone_source_file_id'], 'geometry_path': None, 'space_handles': [], 'uncounted_space_handles': []})
        legacy.append({'id': sid, 'source_space_type': space_type})
    context = SimpleNamespace(atlas={'programs': legacy}, scope='full', root=ROOT, extraction_date=EXTRACTION_DATE)
    leaves = [copy.deepcopy(r) for r, _, _ in programs.values()]
    saved = program_composition.extract_areas
    program_composition.extract_areas = lambda ctx: {(building_type, tmpl): rows}
    try:
        bundle = program_composition.compose(context, {'programs': leaves, 'schedules': list(extract.schedules.values())})
    finally:
        program_composition.extract_areas = saved
    for leaf in leaves:
        programs[leaf['source_id']][0]['available_details'] = leaf['available_details']
    return bundle


def climate_mixes(extract, bundle):
    """value_by_climate on mix loads, from their members'; a mixed schedule that would change by climate is an error."""
    from scripts.program_composition import mix_schedule
    for program in bundle['programs']:
        for load in program['loads']:
            components = load.get('source_components') or []
            climates = sorted({c for comp in components for c in comp['load'].get('value_by_climate', {})})
            if not climates or load['value'] is None:
                continue
            out = {}
            for climate in climates:
                values = [comp['load'].get('value_by_climate', {}).get(climate, comp['load']['value']) for comp in components]
                weights = [comp['weight'] for comp in components]
                value = math.fsum(w*v for w, v in zip(weights, values))
                schedules = [extract.schedules.get(comp['load']['schedule_id']) for comp in components]
                mixed = mix_schedule(schedules, weights, values, value or 1) if value else None
                base = next((s for s in bundle['schedules'] if s['id'] == load['schedule_id']), None)
                if mixed and base and not same_rules(mixed['rules'], base['rules']):
                    mixed['evidence_ids'] = list(base['evidence_ids'])
                    mixed['id'] = stable_id('mixed-schedule', mixed)
                    bundle['schedules'].append(mixed)
                    load.setdefault('schedule_id_by_climate', {})[climate] = mixed['id']
                out[climate] = rounded(value)
            load['value_by_climate'] = {c: v for c, v in out.items() if not close(v, load['value'])}
            if not load['value_by_climate']:
                del load['value_by_climate']


def same_rules(a, b):
    return len(a) == len(b) and all(
        x['day_types'] == y['day_types'] and x['start_date'] == y['start_date'] and len(x['values']) == len(y['values'])
        and all(close(p, q, 1e-9) for p, q in zip(x['values'], y['values'])) for x, y in zip(a, b))


def build(idf_root, edition, members=None, types=None):
    lookup = Lookup()
    archives = {e['path'].split('/')[-1]: e for e in load_json(LOCK)['files'] if e.get('family') == 'commercial-iecc'}
    extract = Extract(idf_root, archives, members)
    programs, compositions, services, conflicts, decisions, envelopes = [], [], [], [], [], {}
    for pnnl in types or TYPES:
        models = TypeModels(extract, idf_root, pnnl, edition, lookup)
        t = TypeExtract(extract, models)
        t.services_out = []
        found, lumped = t.programs()
        for sid, (r, _, _) in found.items():
            r['zone_source_file_id'] = models.files[BASE_CITY]
        bundle = compose_mixes(extract, models.building_type, models.template, found)
        climate_mixes(extract, bundle)
        for sid, (r, _, _) in found.items():
            r.pop('zone_source_file_id')
        programs += [r for r, _, _ in found.values()] + bundle['programs']
        compositions += bundle['compositions']
        for row in bundle['provenance']:
            extract.evidence[row['id']] = row
        for s in bundle['schedules']:
            extract.schedules[s['id']] = s
        services += t.services_out + t.services(found) + lumped_services(t, lumped) + lumped_services(t, t.boosters, 'booster')
        conflicts += [{'building_type': models.building_type, **c} for c in t.conflicts]
        decisions += t.decisions
        envelopes[models.building_type] = envelope.extract(extract, models, t)
    used = set(json.dumps([programs, services, envelopes]).split('"'))
    return {
        'schema_version': '1.0.0', 'kind': 'iecc_commercial_definitions', 'adr': 'docs/adr/0040-iecc-commercial-family.md',
        'generated_by': f'python -m scripts.iecc_commercial_values --edition {edition}', 'edition': edition,
        'template': template(edition), 'source_family': FAMILY, 'extraction_date': EXTRACTION_DATE,
        'input_sha256': {p: sha256(ROOT/p) for p in ('sources/reference-models-lock.json', 'sources/iecc-commercial-zone-aliases.json',
                                                       'data/construction-inputs/geometry-v1.json', 'sources/program-composition-policy.json')},
        'zone_table': {f'{bt}|{name}': {'standards_building_type': v[0], 'space_type': v[1], 'origin': lookup.origin[(bt, name)]}
                       for (bt, name), v in sorted(lookup.table.items())},
        'schedule_checks': extract.checked,
        'source_files': [extract.source_files[k] for k in sorted(extract.source_files)],
        'provenance': [extract.evidence[k] for k in sorted(extract.evidence)],
        'schedules': [extract.schedules[k] for k in sorted(extract.schedules) if k in used],
        'programs': sorted(programs, key=lambda p: p['id']), 'compositions': sorted(compositions, key=lambda c: c['id']),
        'services': sorted(services, key=lambda s: s['id']), 'schedule_conflicts': conflicts, 'decisions': decisions,
        'envelope': envelopes}


def lumped_services(t, lumped, end_use='main'):
    """Zoneless hot-water draws: building-level services without a beneficiary program; with end use 'booster',
    the water heaters' use flows in zones that also have fixture draws, for their program. A draw that only some
    locations have keeps the most common value (zero where absent) and the others by climate."""
    m, out = t.m, []
    names = sorted({d['name'] for ds in lumped.values() for d in ds})
    for name in names:
        beneficiaries = sorted({d['program'] for ds in lumped.values() for d in ds if d['name'] == name and d.get('program')})
        found = {city: next((d for d in ds if d['name'] == name), None) for city, ds in lumped.items()}
        per_city = {city: d['peak_flow_m3_s'] if d else 0.0 for city, d in found.items()}
        value, exceptions, _ = modal(per_city)
        city = BASE_CITY if found[BASE_CITY] else next(c for c in CITIES if found[c])
        d = found[city]
        if len({json.dumps([schedule_fields(m.models[c], x['schedule']), x['target_C']]) for c, x in found.items() if x}) > 1:
            raise ValueError(f'Lumped hot-water draw {name} differs by location beyond its flow')

        def cite(c):
            row = {k: found[c][k] for k in ('name', 'peak_flow_m3_s', 'schedule', 'target_C')} if found[c] else None
            return t.x.cite(m.files[c], f'WaterUse:Equipment {name}', row, 'm3/s; C',
                            'peak flow as written; no zone, so no zone gain; absent is zero',
                            f'IECC prototype building hot-water draw without a zone (ADR 0040 item 9), climate zone {CITIES[c][0]} ({c}).')
        evidence = cite(city)
        sid = stable_id('service', {'template': m.template, 'building_type': m.building_type, 'end_use': end_use, 'name': name, 'source': 'iecc'})
        schedule_id = t.x.schedule(m.models[city], m.files[city], d['schedule'], 'fraction', m.days)
        load = {'basis': 'absolute', 'quantity': 'hot_water_volume', 'unit': 'm3/s', 'value': value, 'status': 'known',
                'scope': 'building_service', 'schedule_id': schedule_id, 'evidence_id': evidence, 'required_inputs': [],
                'service_id': sid, 'demand_id': sid, 'target_temperature_degC': d['target_C'], 'thermal_effects': {},
                'zone_heat_assignment': 'unresolved'}
        evidence_ids = {evidence, *t.x.schedules[schedule_id]['evidence_ids']}
        if exceptions:
            load['value_by_climate'] = exceptions
            load['climate_evidence_ids'] = {c: cite(next(k for k, v in CITIES.items() if v[1] == c)) for c in exceptions}
            evidence_ids |= set(load['climate_evidence_ids'].values())
        out.append({'id': sid, 'template': m.template, 'building_type': m.building_type, 'end_use': end_use, 'name': name,
                    'assignment': 'consumer_host_when_applicable' if beneficiaries else 'building_level',
                    'beneficiary_program_ids': beneficiaries, 'ownership': 'instantiate_once',
                    'path_id': f'{m.building_type}|{m.template}|{end_use}|{name}', 'load': load,
                    'evidence_ids': sorted(evidence_ids), 'source_evidence_ids': []})
    return out


def layered(value, depth=4, pad=''):
    """JSON with one record per line down to `depth` levels, compact below: diffable and under 25 MB."""
    compact = lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    if depth == 0 or not isinstance(value, (dict, list)) or not value:
        return compact(value)
    inner = pad + ' '
    if isinstance(value, dict):
        items = [f'{inner}{compact(k)}:{layered(v, depth - 1, inner)}' for k, v in sorted(value.items())]
        return '{\n' + ',\n'.join(items) + '\n' + pad + '}'
    return '[\n' + ',\n'.join(inner + layered(v, depth - 1, inner) for v in value) + '\n' + pad + ']'


def encode(document):
    return (layered(document) + '\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--idf-root', type=Path, required=True)
    parser.add_argument('--edition', choices=('2006', '2009', '2012', '2015', '2018', '2021'), required=True)
    parser.add_argument('--manifest', type=Path, help='SOURCES-prototypes.json with the archive member checksums')
    parser.add_argument('--type', action='append', help='limit to PNNL type names (for inspection; not for the committed file)')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    members = None
    if args.manifest:
        records = load_json(args.manifest)
        members = {f['path']: f['sha256'] for a in records['archives'] if a['family'] == 'commercial-iecc' for f in a['files']}
    document = build(args.idf_root, args.edition, members, args.type)
    data = encode(document)
    out = args.out or ROOT/OUTPUT.format(args.edition)
    if args.check:
        if out.read_bytes() != data:
            raise SystemExit(f'{out} does not reproduce; rerun python -m scripts.iecc_commercial_values')
        print(f'{out.name} reproduces')
        return
    out.write_bytes(data)
    print(f'IECC {args.edition}: {sum(p["derivation"] != "composed" for p in document["programs"])} programs, '
          f'{sum(p["derivation"] == "composed" for p in document["programs"])} mixes, {len(document["services"])} services, '
          f'{len(document["schedules"])} schedules ({document["schedule_checks"]} conversions checked), '
          f'{len(document["schedule_conflicts"])} slot conflicts; {len(data)/1e6:.1f} MB')


if __name__ == '__main__':
    main()
