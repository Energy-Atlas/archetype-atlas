"""Group code-prototype models into dwelling programs and construction contexts (ADR 0041, ADR 0042).

A family's models differ along axes such as climate, heating system and foundation.
A program covers a group of models (for example one IECC edition, type and appliance
fuel). Within it, every load, service, control, ventilation and window-ratio "slot"
is compared across the group's models: each distinct content becomes one entry, and
an entry that does not hold in every model of the group carries `applies_with`, the
axis values of the models it holds in (as few axis-value products as describe them
exactly). Construction contexts are compared the same way across the axes they do
not key on. Nothing is averaged: every stored value is one the source models hold.
"""
import collections
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

from scripts import prototype_extract
from scripts.prototype_extract import layer_resistance

EXTRACTION_DATE = '2026-10-26'
UNIT_SUFFIX = re.compile(r'(_?unit\d+)(_(front|back)row_(bottom|middle|top)floor)?$', re.I)


def key(value, prefix, length=12):
    return prefix+hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:length]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_unit(name):
    match = UNIT_SUFFIX.search(name)
    return match[0].lstrip('_').lower() if match else None


def conditions(covered, universe, axes):
    """Axis-value products whose union is exactly `covered` within `universe` ([{}] when it is all of it)."""
    covered, universe = set(covered), set(universe)
    if covered == universe:
        return [{}]
    full = [sorted({k[i] for k in universe}) for i in range(len(axes))]

    def describe(keys):
        proj = [sorted({k[i] for k in keys}) for i in range(len(axes))]
        product = {k for k in universe if all(k[i] in proj[i] for i in range(len(axes)))}
        if product == keys:
            return [{a: proj[i] for i, a in enumerate(axes) if proj[i] != full[i]}]
        best = None
        for i in range(len(axes)):
            rests = collections.defaultdict(set)
            for k in keys:
                rests[k[i]].add(k[:i]+k[i+1:])
            merged = collections.defaultdict(list)
            for value, rest in rests.items():
                merged[frozenset(rest)].append(value)
            if len(merged) > 1 and (best is None or len(merged) < len(best[1])):
                best = (i, merged)
        if best is None:
            return [{a: [k[j]] for j, a in enumerate(axes)} for k in sorted(keys)]
        i, merged = best
        out = []
        for values in sorted(merged.values()):
            out += describe({k for k in keys if k[i] in values})
        return out
    return describe(covered)


class Library:
    """Schedules, materials and assemblies of one extraction, keyed by content."""

    def __init__(self):
        self.schedules, self.materials, self.assemblies = {}, {}, {}

    def schedule(self, record, units):
        if record is None:
            return None
        content = {'source_name': record['name'], 'type_limits': record['type_limits'], 'units': units,
                   'rules': record['rules']}
        sid = key(content, 'sch-')
        self.schedules[sid] = content
        return sid

    def assembly(self, model, name):
        construction = model.construction(name)
        layers = []
        for material in construction['layers']:
            mid = key(material, 'mat-')
            self.materials[mid] = material
            layers.append(mid)
        resistance = layer_resistance(construction)
        glazing = [m for m in construction['layers'] if m['model'] == 'SimpleGlazing']
        record = {'name': construction['name'], 'layers': layers, 'layer_orientation': 'outside_to_inside',
                  'layer_resistance_m2_K_W': round(resistance, 9) if resistance is not None else None,
                  'layer_u_factor_W_m2_K': round(1/resistance, 9) if resistance else None}
        if glazing:
            record.update(u_factor_W_m2_K=glazing[0]['u_factor_W_m2_K'],
                          solar_heat_gain_coefficient=glazing[0]['solar_heat_gain_coefficient'],
                          visible_transmittance=glazing[0]['visible_transmittance'])
        aid = key(record, 'asm-')
        self.assemblies[aid] = record
        return aid


SCHEDULE_UNITS = {'schedule': 'dimensionless', 'activity': 'W/person', 'heating': 'C', 'cooling': 'C',
                  'control_type': 'dimensionless', 'target_temperature': 'C', 'hot_supply_temperature': 'C',
                  'cold_supply_temperature': 'C', 'sensible_fraction': 'dimensionless', 'latent_fraction': 'dimensionless',
                  'venting_schedule': 'dimensionless'}
BASIS = {'W': ('W/dwelling', 'dwelling_unit'), 'person': ('person/dwelling', 'dwelling_unit'),
         'm3/s': ('m3/s/dwelling', 'dwelling_unit'), 'W/m2': ('W/m2', 'floor_area'),
         'person/m2': ('person/m2', 'floor_area'), 'W/person': ('W/person', 'person')}
ABSOLUTE = {'W': ('W', 'absolute'), 'person': ('person', 'absolute'), 'm3/s': ('m3/s', 'absolute'),
            'W/m2': ('W/m2', 'floor_area')}
FUELS = {'electric_equipment': 'electricity', 'gas_equipment': 'natural gas'}


def quantity(stem):
    return re.sub(r'[^a-z0-9]+', '_', stem.lower()).strip('_')


def entry(load, library, scope):
    """A stored load entry (without its applies_with) from a load instance."""
    unit, basis = (BASIS if scope == 'dwelling' else ABSOLUTE)[load['source_unit']]
    out = {'quantity': quantity(load['stem']), 'source_object': load['stem'], 'source_class': load['class'],
           'type': load['type'], 'value': load['value'], 'unit': unit, 'basis': basis, 'method': load['method'],
           'host_zone': load['zone'] or ('exterior' if load['type'] == 'exterior_lighting' else None),
           'schedule_id': library.schedule(load['schedule'], 'dimensionless')}
    if 'iecc_adj' in out['quantity']:
        out['role'] = 'reference_design_adjustment'
    if load['type'] in FUELS:
        out['fuel'] = FUELS[load['type']]
    for field in ('fractions', 'subcategory', 'control', 'fraction_radiant', 'sensible_fraction'):
        if field in load:
            out[field] = load[field]
    for field in ('target_temperature', 'hot_supply_temperature', 'cold_supply_temperature', 'sensible_fraction', 'latent_fraction'):
        if load['type'] == 'hot_water' and field in load:
            out[field+'_schedule_id'] = library.schedule(load[field], SCHEDULE_UNITS[field])
    if load['type'] == 'hot_water':
        out.pop('sensible_fraction', None)
    if load['type'] == 'occupancy':
        out['activity_schedule_id'] = library.schedule(load['activity'], 'W/person')
    return out


def dwelling_slots(model, library, building_zones=()):
    """The per-dwelling and building-level slots of one model.

    Loads of a dwelling unit (by zone, or by object name for zone-less objects) are
    per-dwelling; a multifamily model repeats them per unit, and every unit must agree.
    Loads in other zones (or in `building_zones`) are building-level services.
    """
    units = collections.defaultdict(dict)
    services = {}
    for load in model.loads():
        unit = load['unit'] or (object_unit(load['object']) if load['zone'] is None else None)
        slot = (load['class'], load['stem'], load['zone'])
        if unit and load['zone'] not in building_zones:
            if slot in units[unit]:
                raise ValueError(f'Two {slot} loads in unit {unit}')
            units[unit][slot] = entry(load, library, 'dwelling')
        else:
            if slot in services:
                raise ValueError(f'Two {slot} building loads')
            services[slot] = entry(load, library, 'building')
    unit_sets = list(units.values())
    if not unit_sets or any(u != unit_sets[0] for u in unit_sets[1:]):
        raise ValueError(f'Dwelling units differ in their loads: {sorted(units)[:3]}')
    controls = {}
    for t in model.thermostats():
        if t['unit']:
            record = {'heating_setpoint_schedule_id': library.schedule(t['heating'], 'C'),
                      'cooling_setpoint_schedule_id': library.schedule(t['cooling'], 'C'),
                      'control_type_schedule_id': library.schedule(t['control_type'], 'dimensionless')}
            if controls.setdefault('thermostat', record) != record:
                raise ValueError('Dwelling units differ in their thermostats')
    ventilation = {}
    for v in model.ventilation():
        v = dict(v)
        v['schedule_id'] = library.schedule(v.pop('schedule'), 'dimensionless')
        v.pop('unit')
        name = (v['object'], v['zone'])
        if ventilation.setdefault(name, v) != v:
            raise ValueError(f'Dwelling units differ in their ventilation {name}')
    return {'loads': unit_sets[0], 'services': services, 'controls': controls,
            'ventilation': {f'{o}|{z}': v for (o, z), v in sorted(ventilation.items(), key=str)},
            'units': len(units)}


def envelope(model, library):
    """A construction context's content from one model: assemblies by surface class, infiltration, mass, shading."""
    shell = model.envelope()
    out = {}
    for part in ('components', 'windows', 'doors', 'internal_mass'):
        out[part] = [{**{k: v for k, v in item.items() if k != 'construction'}, 'assembly_id': library.assembly(model, item['construction'])}
                     for item in shell[part]]
    shading = {json.dumps(s, sort_keys=True): s for s in shell['window_shading']}
    out['window_shading'] = [{'shading_type': s['shading_type'], 'shaded_assembly_id': library.assembly(model, s['shaded_construction']),
                              'control_type': s['control_type'], 'schedule_id': library.schedule(s['schedule'], 'dimensionless')}
                             for _, s in sorted(shading.items())]
    infiltration = model.infiltration()
    for row in infiltration.get('airflow_network', {}).get('zones', []):
        row['venting_schedule_id'] = library.schedule(row.pop('venting_schedule'), 'dimensionless')
    for method in ('effective_leakage_area', 'design_flow_rate'):
        for row in infiltration.get(method, []):
            row['schedule_id'] = library.schedule(row.pop('schedule'), 'dimensionless')
    out['infiltration'] = infiltration
    return out


def group(models, axes, scope):
    """{slot: [(content, covered model keys)]} for one part of every model's slots, in first-seen order."""
    seen = collections.OrderedDict()
    for model_key, slots in models.items():
        for slot, content in slots[scope].items():
            variants = seen.setdefault(slot, collections.OrderedDict())
            text = json.dumps(content, sort_keys=True)
            variants.setdefault(text, (content, set()))[1].add(model_key)
    return seen


def conditional(models, axes, scope):
    """Stored entries of one part: each distinct content once, with applies_with where it does not always hold."""
    universe = set(models)
    out = []
    for slot, variants in group(models, axes, scope).items():
        for content, covered in variants.values():
            for condition in conditions(covered, universe, axes):
                item = dict(content)
                if condition:
                    item['applies_with'] = condition
                held = sorted(k for k in covered if all(k[axes.index(a)] in v for a, v in condition.items()))
                item['model_count'] = len(held)
                out.append((slot, item, held[0]))
    return out


def source_file(path, root, archive, lock):
    relative = Path(path).relative_to(root).as_posix()
    return {'source_id': 'pnnl-prototypes', 'project': 'DOE/PNNL Prototype Building Models',
            'path': relative, 'archive_path': archive['path'], 'archive_sha256': archive['sha256'], 'url': archive['url'],
            'retrieval_date': lock['retrieval_date'], 'sha256': sha256(path), 'size_bytes': Path(path).stat().st_size,
            'license_path': 'sources/licenses/pnnl-prototypes.txt'}


def read_model(path, building_zones=()):
    """Everything one model contributes, with its own content-keyed library (merged by the caller)."""
    library = Library()
    model = prototype_extract.Model(path)
    zones = model.reader.zones.values()
    out = {'slots': dwelling_slots(model, library, building_zones), 'envelope': envelope(model, library),
           'fenestration': model.fenestration(), 'version': '.'.join(map(str, model.reader.version)),
           'zones': sorted({prototype_extract.zone_kind(z['name']) for z in zones}),
           'units': sorted({u for u in (prototype_extract.unit_of(z['name']) for z in zones) if u})}
    living = sum(prototype_extract.idf_reader.area(s['vertices']) for s in model.reader.surfaces()
                 if s['type'] == 'floor' and prototype_extract.zone_kind(s['zone']) == 'living')
    out['dwelling_floor_area_m2'] = round(living / max(len(out['units']), 1), 6)
    out['library'] = {'schedules': library.schedules, 'materials': library.materials, 'assemblies': library.assemblies}
    return out


def derived(read):
    """Per-model parts computed from geometry: window ratios and the dwelling floor area."""
    return {'fenestration': {'fenestration': {'basis': 'program_zone_surfaces', 'wwr': read['fenestration']}},
            'floor_area': {'floor_area': {'conditioned_floor_area_m2': read['dwelling_floor_area_m2'],
                                          'basis': 'floor surfaces of the living zones over the number of dwelling units'}}}


class Extraction:
    """One family extraction: models read, grouped into programs and construction sets, with evidence."""

    def __init__(self, axes, root, lock):
        self.axes, self.root, self.lock = tuple(axes), Path(root), lock
        self.source_files, self.evidence = {}, {}
        self.library = {'schedules': {}, 'materials': {}, 'assemblies': {}}
        self.models, self.paths = {}, {}

    def add(self, model_key, path, read, archive):
        for table, rows in read['library'].items():
            for k, v in rows.items():
                if self.library[table].setdefault(k, v) != v:
                    raise ValueError(f'Library key clash {k}')
        row = source_file(path, self.root, archive, self.lock)
        sid = key(row, 'sourcefile-', 20)
        self.source_files[sid] = row
        self.models[model_key] = read
        self.paths[model_key] = sid

    def cite(self, model_key, locator, value, unit, transformation, note):
        row = {'source_file_id': self.paths[model_key], 'locator': locator, 'original_value': value,
               'original_unit': unit, 'transformation': transformation, 'extraction_date': EXTRACTION_DATE,
               'interpretation': note}
        eid = key(row, 'evidence-', 24)
        self.evidence[eid] = row
        return eid

    def entries(self, keys, part, label, unit_note):
        """Conditional entries of one slot part over a group of models, each with its evidence."""
        models = {k: {**self.models[k]['slots'], **derived(self.models[k])} for k in keys}
        out = []
        for slot, item, first in conditional(models, self.axes, part):
            locator = ' '.join(str(s) for s in slot if s) if isinstance(slot, tuple) else str(slot)
            value = {k: v for k, v in item.items() if k not in ('model_count', 'applies_with')}
            note = (f'{label}: holds in {item["model_count"]} of the {len(keys)} models of this program'
                    + (' (the models where applies_with holds)' if 'applies_with' in item else ' (every model)') + unit_note)
            item['evidence_id'] = self.cite(first, locator, value, item.get('unit') or 'see value',
                                            'identity; schedules converted to atlas rulesets checked over the full year',
                                            note)
            out.append(item)
        return out

    def program(self, keys, label, unit_note=''):
        """The stored parts of one program over a group of model keys."""
        return {'loads': self.entries(keys, 'loads', label, unit_note),
                'services': self.entries(keys, 'services', label, ''),
                'controls': self.entries(keys, 'controls', label, unit_note),
                'ventilation': self.entries(keys, 'ventilation', label, unit_note),
                'fenestration': self.entries(keys, 'fenestration', label, ''),
                'floor_area': self.entries(keys, 'floor_area', label, unit_note),
                'model_count': len(keys)}

    def context(self, keys, label):
        """One construction context over models that must agree on their envelope."""
        contents = {json.dumps(self.models[k]['envelope'], sort_keys=True) for k in keys}
        if len(contents) != 1:
            raise ValueError(f'Models of construction context {label} differ in their envelope')
        first = sorted(keys)[0]
        content = json.loads(next(iter(contents)))
        evidence = self.cite(first, 'constructions, sub-surfaces, internal mass, window shading control and infiltration',
                             {'assemblies': sorted({c['assembly_id'] for part in ('components', 'windows', 'doors', 'internal_mass')
                                                    for c in content[part]})},
                             'see assemblies', 'identity; surface areas summed by surface class; layers outside to inside',
                             f'{label}: identical in all {len(keys)} models of this context.')
        return {**content, 'model_count': len(keys), 'evidence_id': evidence}
