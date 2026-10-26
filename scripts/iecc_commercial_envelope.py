"""Extract the IECC commercial envelope per type and location (ADR 0040 items 6 to 8).

Used by scripts.iecc_commercial_values. Per location model:
- assemblies and materials of every surface, fenestration and internal-mass construction,
  content-addressed so equal layers share one record;
- the assignment of each component: one construction, or rules by story position and
  space type (precedence space type, then story, then building default) where the
  source varies, with surface-level overrides for what neither explains;
- the design-flow infiltration rules per zone with their schedules;
- the 15 whole-building window ratios over true outdoor walls (ADR 0037);
- internal mass and the interior wall and floor capacity budgets.
Story positions come from zone floor elevations: basement below grade, then ground,
middle and top floors; plenums and attics take the story they sit on.
"""
import math
from collections import defaultdict

from scripts import idf_reader, reference_extras
from scripts.definition_contract import stable_id
from scripts.iecc_commercial_zones import BASE_CITY, CITIES

DIRECTIONS = reference_extras.DIRECTIONS
UNITS = {'flow/exteriorarea': 'm3/s-m2 exterior surface', 'flow/exteriorwallarea': 'm3/s-m2 exterior wall',
         'flow/area': 'm3/s-m2 floor', 'flow/zone': 'm3/s', 'airchanges/hour': '1/h'}
GROUND = ('ground', 'groundfcfactormethod', 'foundation', 'groundslabpreprocessoraverage', 'groundbasementpreprocessoraverage')
INTERIOR = ('surface', 'zone', 'adiabatic')
FIELD = {'flow/zone': 0, 'flow/area': 1, 'flow/exteriorarea': 2, 'flow/exteriorwallarea': 2, 'airchanges/hour': 3}
DEFAULTS = {'thermal_absorptance': 0.9, 'solar_absorptance': 0.7, 'visible_absorptance': 0.7}


def component(kind, boundary, construction=''):
    if boundary == 'outdoors':
        return {'wall': 'ExteriorWall', 'roof': 'ExteriorRoof', 'ceiling': 'ExteriorRoof', 'floor': 'ExteriorFloor'}[kind]
    if boundary in GROUND:
        return {'wall': 'FoundationWall', 'floor': 'GroundFloor', 'roof': 'GroundFloor', 'ceiling': 'GroundFloor'}[kind]
    if boundary in INTERIOR:
        return {'wall': 'InteriorWall', 'floor': 'InteriorFloor', 'ceiling': 'InteriorCeiling', 'roof': 'InteriorCeiling'}[kind]
    raise ValueError(f'Unported outside boundary condition {boundary}')


def fenestration_component(kind, host, construction):
    exterior = host['boundary'] == 'outdoors'
    if kind == 'door':
        if not exterior:
            return 'InteriorDoor'
        return 'OverheadDoor' if 'overhead' in construction.lower() else 'ExteriorDoor'
    if kind == 'glassdoor':
        return 'GlassDoor' if exterior else 'InteriorWindow'
    if kind in ('window', 'tdd:dome', 'tdd:diffuser'):
        if not exterior:
            return 'InteriorWindow'
        return 'Skylight' if host['type'] in ('roof', 'ceiling') else 'ExteriorWindow'
    raise ValueError(f'Unported fenestration type {kind}')


def number(v):
    return idf_reader.number(v)


def materials(model):
    """{material key: (model, name, properties)} as written in the IDF, blank absorptances at their IDD defaults."""
    out = {}
    for f in model.all('material'):
        props = {'roughness': f[1], 'thickness_m': number(f[2]), 'conductivity_W_m_K': number(f[3]), 'density_kg_m3': number(f[4]),
                 'specific_heat_J_kg_K': number(f[5])}
        for i, key in ((6, 'thermal_absorptance'), (7, 'solar_absorptance'), (8, 'visible_absorptance')):
            props[key] = number(f[i]) if len(f) > i and f[i] != '' else DEFAULTS[key]
        out[f[0].lower()] = ('StandardOpaqueMaterial', f[0], props)
    for f in model.all('material:nomass'):
        props = {'roughness': f[1], 'resistance_m2_K_W': number(f[2])}
        for i, key in ((3, 'thermal_absorptance'), (4, 'solar_absorptance'), (5, 'visible_absorptance')):
            props[key] = number(f[i]) if len(f) > i and f[i] != '' else DEFAULTS[key]
        out[f[0].lower()] = ('MasslessOpaqueMaterial', f[0], props)
    for f in model.all('material:airgap'):
        out[f[0].lower()] = ('AirGap', f[0], {'resistance_m2_K_W': number(f[1])})
    for f in model.all('windowmaterial:simpleglazingsystem'):
        out[f[0].lower()] = ('SimpleGlazing', f[0], {'u_W_m2_K': number(f[1]), 'shgc': number(f[2]),
                                                     'visible_transmittance': number(f[3]) if len(f) > 3 and f[3] != '' else None})
    names = ('optical_data_type', 'spectral_data_set', 'thickness_m', 'solar_transmittance_at_normal_incidence',
             'front_side_solar_reflectance_at_normal_incidence', 'back_side_solar_reflectance_at_normal_incidence',
             'visible_transmittance_at_normal_incidence', 'front_side_visible_reflectance_at_normal_incidence',
             'back_side_visible_reflectance_at_normal_incidence', 'infrared_transmittance_at_normal_incidence',
             'front_side_infrared_hemispherical_emissivity', 'back_side_infrared_hemispherical_emissivity', 'conductivity_W_m_K',
             'dirt_correction_factor_for_solar_and_visible_transmittance', 'solar_diffusing')
    for f in model.all('windowmaterial:glazing'):
        props = {}
        for i, key in enumerate(names, start=1):
            value = f[i] if len(f) > i else ''
            props[key] = value if key in ('optical_data_type', 'spectral_data_set') else (
                value.lower() == 'yes' if key == 'solar_diffusing' else number(value))
        props['dirt_correction_factor_for_solar_and_visible_transmittance'] = props['dirt_correction_factor_for_solar_and_visible_transmittance'] or 1.0
        props['solar_diffusing'] = bool(props['solar_diffusing'])
        if not props['spectral_data_set']:
            del props['spectral_data_set']
        out[f[0].lower()] = ('StandardGlazing', f[0], props)
    for f in model.all('windowmaterial:gas'):
        out[f[0].lower()] = ('Gas', f[0], {'gas_type': f[1], 'thickness_m': number(f[2])})
    return out


class Library:
    """Content-addressed materials and assemblies of one type, with their evidence. Keys include the type,
    so the records the release writer puts in one template library never clash between types."""

    def __init__(self, x, template, family, building_type):
        self.x, self.template, self.family, self.building_type = x, template, family, building_type
        self.materials, self.assemblies = {}, {}

    def material(self, mat, source_file, locator):
        """Materials are keyed by physics; the first IDF name seen names the record."""
        model, name, props = mat
        content = {'model': model, 'properties': {k: v for k, v in sorted(props.items()) if v is not None}}
        key = stable_id('iecc-material', {**content, 'building_type': self.building_type})
        if key not in self.materials:
            ev = self.x.cite(source_file, locator, props, 'SI (m, W/m-K, kg/m3, J/kg-K, m2-K/W, W/m2-K)',
                             'object fields as written in the IDF; blank absorptances take their EnergyPlus IDD defaults',
                             'IECC prototype material (ADR 0040 item 6).')
            self.materials[key] = {'id': key, 'name': name, **content, 'property_evidence': {p: ev for p in content['properties']}}
        return key

    def assembly(self, model, name, role, source_file, mats):
        """The assembly a construction stands for, keyed by role and physics; every IDF name is listed."""
        cons = model.constructions().get(name.lower())
        if cons is None:
            raise ValueError(f'No construction {name} in {model.path.name}')
        if cons['kind'] == 'ffactor':
            content = {'model': 'FFactorGroundFloorConstruction', 'f_W_m_K': cons['f_factor']}
        elif cons['kind'] == 'cfactor':
            content = {'model': 'CFactorUndergroundWallConstruction', 'c_W_m2_K': cons['c_factor']}
        else:
            layers = [mats[layer] for layer in cons['layers']]
            ids = [self.material(m, source_file, f'{m[0]} {m[1]}') for m in layers]
            kinds = {m[0] for m in layers}
            if kinds <= {'SimpleGlazing'}:
                assembly_model = 'simple_glazing'
            elif kinds & {'StandardGlazing', 'Gas'}:
                assembly_model = 'detailed_glazing'
            else:
                assembly_model = 'opaque_layers'
            content = {'model': assembly_model, 'role': role, 'layers': [{'material_id': i, 'order': n} for n, i in enumerate(ids)],
                       'metrics': metrics(layers) if assembly_model == 'opaque_layers' else {}}
        key = stable_id('iecc-assembly', {**content, 'building_type': self.building_type})
        if key not in self.assemblies:
            ev = self.x.cite(source_file, f'Construction {name}', cons, 'layer names outside to inside, or F/C factor (W/m-K, W/m2-K)',
                             'construction as written in the IDF; layers resolved to content-addressed materials',
                             'IECC prototype construction (ADR 0040 item 6).')
            if content['model'] in ('FFactorGroundFloorConstruction', 'CFactorUndergroundWallConstruction'):
                record = {'id': key, 'name': name, 'status': 'ready', 'evidence_ids': [ev], **content}
            else:
                record = {'id': key, 'name': name, 'status': 'ready', 'evidence_ids': [ev], 'source_family': self.family,
                          'template': self.template, 'climate_group': None, 'layer_orientation': 'exterior_to_interior',
                          'applicability': {}, 'source_attributes': {'idf_constructions': []}, 'source_surface_ids': [],
                          'source_adjacency': [], 'source_parameters': {}, 'target_adjustment': None, **content}
            self.assemblies[key] = record
        names = self.assemblies[key].get('source_attributes', {}).get('idf_constructions')
        if names is not None and name not in names:
            names.append(name)
            names.sort()
        return key


def metrics(layers):
    resistance = capacity = 0.0
    for model, _, p in layers:
        if model == 'StandardOpaqueMaterial':
            resistance += p['thickness_m']/p['conductivity_W_m_K']
            capacity += p['thickness_m']*p['density_kg_m3']*p['specific_heat_J_kg_K']
        else:
            resistance += p['resistance_m2_K_W']
    out = {'layer_resistance_m2_K_W': resistance, 'layer_conductance_W_m2_K': 1/resistance}
    if capacity > 0:
        out['areal_heat_capacity_J_m2_K'] = capacity
    return out


def capacity(assembly, library):
    out = 0.0
    for layer in assembly.get('layers', []):
        m = library.materials[layer['material_id']]
        p = m['properties']
        if m['model'] == 'StandardOpaqueMaterial':
            out += p['thickness_m']*p['density_kg_m3']*p['specific_heat_J_kg_K']
    return out


def stories(model, geometry):
    """{zone: story position} from the zones' lowest vertex elevation."""
    low = defaultdict(lambda: math.inf)
    for s in model.surfaces():
        for p in s['vertices']:
            low[s['zone'].lower()] = min(low[s['zone'].lower()], p[2])
    regular = lambda z: not any(w in z for w in ('plenum', 'attic'))
    levels = sorted({round(low[z], 2) for z in geometry if regular(z) and low[z] > -0.3})
    out = {}
    for z in geometry:
        if low[z] <= -0.3:
            out[z] = 'basement'
            continue
        level = max((v for v in levels if v <= round(low[z], 2) + 0.01), default=levels[0])
        index = levels.index(level)
        out[z] = ('single_story' if len(levels) == 1 else 'ground_floor' if index == 0 else
                  'top_floor' if index == len(levels) - 1 else 'middle_floors')
    return out


def select(entries):
    """Assignment rules for one component: [(when, assembly, surfaces)], precedence space type > story > default."""
    area = defaultdict(float)
    for e in entries:
        area[e['assembly']] += e['area']
    keys = sorted(area, key=lambda k: (-area[k], k))
    default = keys[0]
    out = [({'scope': 'building_default'}, default)]
    if len(keys) == 1:
        return [({'scope': 'building_default'}, default, sorted({e['surface'] for e in entries}))], []

    def dominant(group):
        weights = defaultdict(float)
        for e in group:
            weights[e['assembly']] += e['area']
        return min(weights, key=lambda k: (-weights[k], k))
    by_story, by_space = defaultdict(list), defaultdict(list)
    for e in entries:
        by_story[e['story']].append(e)
        by_space[e['space_type']].append(e)
    story_rule = {s: dominant(g) for s, g in by_story.items() if dominant(g) != default}
    predict = lambda e: story_rule.get(e['story'], default)
    space_rule = {}
    for t, group in by_space.items():
        found = {e['assembly'] for e in group}
        if len(found) == 1 and any(predict(e) != e['assembly'] for e in group):
            space_rule[t] = next(iter(found))
    final = lambda e: space_rule.get(e['space_type'], predict(e))
    out += [({'scope': 'story', 'source_story_id': s}, a) for s, a in sorted(story_rule.items())]
    out += [({'scope': 'space_type', 'space_type': t}, a) for t, a in sorted(space_rule.items())]
    rules = []
    for when, assembly in out:
        if when['scope'] == 'building_default':
            covered = [e for e in entries if final(e) == assembly and e['story'] not in story_rule and e['space_type'] not in space_rule]
        elif when['scope'] == 'story':
            covered = [e for e in entries if e['story'] == when['source_story_id'] and e['space_type'] not in space_rule]
        else:
            covered = [e for e in entries if e['space_type'] == when['space_type']]
        rules.append((when, assembly, sorted({e['surface'] for e in covered if e['assembly'] == assembly})))
    overrides = defaultdict(list)
    for e in entries:
        if final(e) != e['assembly']:
            overrides[e['assembly']].append(e)
    extra = []
    for assembly, group in sorted(overrides.items()):
        extra.append(({'scope': 'building_default'}, assembly, sorted(e['surface'] for e in group)))
    return rules + extra, [s for _, _, s in extra]


def window_ratios(model, zone_programs, conditioned=None):
    """Per-program and whole-building window over true outdoor wall ratios (reference_extras), with the
    whole-building split on the zones' thermostats rather than their names."""
    zones = reference_extras.zone_fenestration(model)
    groups = defaultdict(lambda: (defaultdict(float), defaultdict(float)))
    building = {c: (defaultdict(float), defaultdict(float)) for c in ('conditioned', 'unconditioned', 'all')}
    for key, z in zones.items():
        multiplier = model.zones[key]['multiplier']
        if conditioned is None:
            unconditioned = any(w in key for w in ('plenum', 'attic'))
        else:
            unconditioned = key not in conditioned
        targets = [building['unconditioned' if unconditioned else 'conditioned'], building['all']]
        if zone_programs.get(key):
            targets.append(groups[zone_programs[key]])
        for wall, window in targets:
            for d in DIRECTIONS:
                wall[d] += z['wall'][d] * multiplier
                window[d] += z['window'][d] * multiplier
    return {'programs': {k: reference_extras.ratios(*v) for k, v in sorted(groups.items())},
            'building': {k: reference_extras.ratios(*v) for k, v in building.items()}}


def extract(x, models, types):
    """The envelope payload of one type: library, story positions and one context per location."""
    m = models
    library = Library(x, m.template, 'iecc_commercial_prototype', m.building_type)
    position = stories(m.base, m.geometry)
    counted = math.fsum(g['floor_m2']*g['multiplier'] for g in m.geometry.values() if g['counted'])
    contexts = {}
    for city, model in m.models.items():
        source_file = m.files[city]
        mats = materials(model)
        conditioned = {z for z, t in types.thermostats[city].items() if t}
        entries = defaultdict(list)
        surfaces = {s['name'].lower(): s for s in model.surfaces()}
        for s in model.surfaces():
            role = component(s['type'], s['boundary'])
            key = library.assembly(model, s['construction'], role, source_file, mats)
            z = s['zone'].lower()
            entries[role].append({'assembly': key, 'surface': s['name'], 'story': position[z], 'space_type': m.space[z][1],
                                  'area': idf_reader.area(s['vertices'])*m.geometry[z]['multiplier']})
        for f in model.fenestration():
            host = surfaces[f['host'].lower()]
            role = fenestration_component(f['type'], host, f['construction'])
            key = library.assembly(model, f['construction'], role, source_file, mats)
            z = host['zone'].lower()
            entries[role].append({'assembly': key, 'surface': f['name'], 'story': position[z], 'space_type': m.space[z][1],
                                  'area': idf_reader.area(f['vertices'])*f['multiplier']*m.geometry[z]['multiplier']})
        mass = []
        for item in model.internal_mass():
            key = library.assembly(model, item['construction'], 'InteriorPartition', source_file, mats)
            for z in item['zones']:
                mass.append({'object': item['name'], 'assembly': key, 'zone': m.geometry[z]['name'], 'area_m2': item['area'],
                             'multiplier': m.geometry[z]['multiplier'], 'space_type': m.space[z][1],
                             'standards_building_type': m.space[z][0], 'counted': m.geometry[z]['counted']})
                entries['InteriorPartition'].append({'assembly': key, 'surface': item['name'], 'story': position[z],
                                                     'space_type': m.space[z][1], 'area': item['area']*m.geometry[z]['multiplier']})
        components, overrides = {}, {}
        for role, group in sorted(entries.items()):
            rules, extra = select(group)
            components[role] = [{'when': w, 'assembly': a, 'surfaces': s, **({'override': True} if n >= len(rules) - len(extra) and extra else {})}
                                for n, (w, a, s) in enumerate(rules)]
            if extra:
                overrides[role] = sum(len(s) for s in extra)
        budgets = interior_budgets(model, m, library, entries)
        fen = window_ratios(model, {}, conditioned)['building']
        fen_ev = x.cite(source_file, 'FenestrationSurface:Detailed, building', fen, 'm2/m2',
                        'window over true outdoor wall area by direction, zone multipliers applied, over conditioned (thermostat), '
                        'unconditioned and all zone surfaces', 'IECC prototype building window ratios (ADR 0040 item 8).')
        contexts[CITIES[city][1]] = {
            'location': city, 'source_climate_label': CITIES[city][0], 'source_file_id': source_file,
            'components': components, 'surface_overrides': overrides, 'mass': mass, 'budgets': budgets,
            'fenestration': {'value': fen, 'evidence_id': fen_ev},
            'infiltration': infiltration(x, model, m, source_file),
            'file_evidence_id': x.cite(source_file, 'whole file', {'sha256': x.source_files[source_file]['sha256']}, 'IDF',
                                       'parsed as text; constructions, materials, surfaces, infiltration and internal mass read',
                                       f'IECC prototype model for climate zone {CITIES[city][0]} ({city}) (ADR 0040).')}
    return {'reference': {'counted_floor_area_m2': counted, 'profile_id': f'{m.template}/{m.building_type}'},
            'stories': {m.geometry[z]['name']: p for z, p in sorted(position.items())},
            'assemblies': library.assemblies, 'materials': library.materials, 'contexts': contexts}


def interior_budgets(model, m, library, entries):
    """Interior wall and floor capacity: faces x multiplier, paired faces halved; floors counted once."""
    out = {'InteriorWall': defaultdict(float), 'InteriorFloor': defaultdict(float)}
    assembly_of = {(role, e['surface']): e['assembly'] for role in out for e in entries.get(role, [])}
    for s in model.surfaces():
        role = component(s['type'], s['boundary'])
        if role not in out:
            continue
        z = s['zone'].lower()
        face = idf_reader.area(s['vertices'])*m.geometry[z]['multiplier']
        if role == 'InteriorWall' and s['boundary'] in ('surface', 'zone'):
            face /= 2
        out[role][assembly_of[(role, s['name'])]] += face
    return {role: [{'assembly': k, 'reference_area_m2': a, 'source_areal_capacity_J_m2_K': capacity(library.assemblies[k], library)}
                   for k, a in sorted(v.items())] for role, v in out.items()}


def infiltration(x, model, m, source_file):
    """ZoneInfiltration:DesignFlowRate rules grouped by method, rate, coefficients and schedule."""
    rules = {}
    for item in model.infiltration():
        rate = item['values'][FIELD[item['method']]]
        if rate is None:
            raise ValueError(f'No {item["method"]} rate in {item["name"]} ({model.path.name})')
        key = (item['method'], rate, tuple(item['coefficients']), item['schedule'])
        rules.setdefault(key, set()).update(item['zones'])
    out = []
    for (method, rate, coefficients, schedule), zones in sorted(rules.items(), key=str):
        out.append({'method': method, 'value': rate, 'unit': UNITS[method], 'coefficients': list(coefficients),
                    'schedule_id': x.schedule(model, source_file, schedule, 'fraction', m.days),
                    'zones': sorted(m.geometry[z]['name'] for z in zones)})
    excluded = sorted(g['name'] for z, g in m.geometry.items() if not any(z in r for r in rules.values()))
    ev = x.cite(source_file, 'ZoneInfiltration:DesignFlowRate', [{k: v for k, v in r.items()} for r in out],
                'SI (m3/s-m2, m3/s, 1/h)', 'objects grouped by method, rate, coefficients and schedule',
                'IECC prototype design-flow infiltration (ADR 0040 item 7); the source method, with no fixed natural ACH.')
    return {'zone_rules': out, 'excluded_zones': excluded, 'evidence_id': ev}
