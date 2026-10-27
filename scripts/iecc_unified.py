"""Unified (building-level equivalent) constructions of the IECC commercial family, release 1.6.0 (ADR 0045).

python -m scripts.iecc_unified [--idf-root DIR] [--check]

The 90.1 and DOE Ref sets weight their equivalent assemblies by profiles recovered with
OpenStudio over the openstudio-standards geometry. The IECC sets come from the PNNL IDFs,
so their weights come from the IDFs too:
- `build` reads the 1,824 IDFs and writes data/program-inputs/iecc-unified-areas-v1.json:
  for every edition, type and location, the net area of each component entry of the
  envelope payload (base surfaces less their windows and doors, subsurfaces as drawn,
  both times their multipliers), in the payload's entry order;
- `unified(detailed, areas)` composes the equivalent document of one context from its
  detailed document and those areas with the existing equivalence physics
  (scripts.construction_equivalent_export): area-weighted opaque fits and glazing
  proxies per component, F- and C-factor ground constructions as their native
  assemblies, the source internal mass and the interior floor inventory as mass
  components, and the detailed document's mass accounting, foundation methods and
  design-flow infiltration unchanged.
--check rebuilds the areas from the IDFs and compares the committed file.
"""
import argparse
import copy
import math
import os
from collections import defaultdict
from pathlib import Path

from scripts import idf_reader
from scripts.common import ROOT, load_json
from scripts.construction_equivalent_export import _recipe, absent, blocked
from scripts.definition_contract import stable_id
from scripts.iecc_commercial_values import encode, sha256
from scripts.iecc_commercial_zones import CITIES, EDITIONS, TYPES

OUTPUT = ROOT/'data/program-inputs/iecc-unified-areas-v1.json'
INPUT = 'data/program-inputs/iecc-commercial-{}.json'
ADR = 'docs/adr/0045-iecc-unified-constructions.md'
SHADING = ('SpaceShading', 'BuildingShading', 'SiteShading')
GROUND = ('FFactorGroundFloorConstruction', 'CFactorUndergroundWallConstruction')
GROUND_ROLES = ('GroundFloor', 'FoundationWall')
POLICY = 'iecc-unified-1.0.0'
CONSUMER_INPUTS = ['actual component areas and geometry', 'actual counted floor area',
                   'physical mass already represented by instantiated interior surfaces']


def idf_root():
    return Path(os.environ.get('IECC_IDF_ROOT', os.environ.get('ATLAS_PROTOTYPE_ROOT', 'D:/Prototype Building Models')+'/commercial-iecc'))


def net_areas(model):
    """{surface or subsurface name (lower case): net area times multipliers}."""
    zones = {k: z['multiplier'] for k, z in model.zones.items()}
    out, openings = {}, defaultdict(float)
    for f in model.fenestration():
        mult = zones.get((f['zone'] or '').lower(), 1)
        area = idf_reader.area(f['vertices'])*f['multiplier']
        out[f['name'].lower()] = area*mult
        openings[f['host'].lower()] += area
    for s in model.surfaces():
        mult = zones[s['zone'].lower()]
        gross = idf_reader.area(s['vertices'])
        net = gross - openings[s['name'].lower()]
        if net < -1e-6:
            raise ValueError(f'Openings exceed surface {s["name"]} in {model.path.name}')
        out[s['name'].lower()] = max(net, 0.0)*mult
    return out


def build(root=None):
    root = Path(root or idf_root())
    areas, digests = {}, {}
    for edition in EDITIONS:
        payloads = load_json(ROOT/INPUT.format(edition))['envelope']
        digests[INPUT.format(edition)] = sha256(ROOT/INPUT.format(edition))
        for pnnl, building_type in TYPES.items():
            payload = payloads[building_type]
            for city in CITIES:
                path = root/f'IECC_{pnnl}'/f'IECC_{pnnl}_STD{edition}_{city}.idf'
                found = net_areas(idf_reader.Model(path))
                ctx = payload['contexts'][CITIES[city][1]]
                if ctx['location'] != city:
                    raise ValueError(f'{building_type} {edition}: context {CITIES[city][1]} is {ctx["location"]}, not {city}')
                areas.setdefault(edition, {}).setdefault(building_type, {})[CITIES[city][1]] = {
                    role: [round(math.fsum(found[s.lower()] for s in entry['surfaces']), 9) for entry in entries]
                    for role, entries in sorted(ctx['components'].items()) if role != 'InteriorPartition'}
    return {'schema_version': '1.0.0', 'kind': 'iecc_unified_component_areas', 'adr': ADR,
            'generated_by': 'python -m scripts.iecc_unified', 'basis': 'net surface area (m2) per envelope component entry, '
            'base surfaces less their subsurfaces, subsurfaces as drawn, both times subsurface and zone multipliers',
            'input_sha256': {'sources/reference-models-lock.json': sha256(ROOT/'sources/reference-models-lock.json'), **digests},
            'areas': areas}


# ---------------------------------------------------------------- composition

def _mass_release(recipes):
    """Pseudo assemblies and materials for the source internal-mass recipes."""
    assemblies, materials = {}, {}
    for rid, recipe in recipes.items():
        layers = []
        for n, layer in enumerate(recipe['layers']):
            mid = f'{rid}:{n}'
            materials[mid] = {'model': layer['model'], 'properties': {k: v for k, v in layer['properties'].items() if k != 'name'}}
            layers.append({'material_id': mid})
        assemblies[rid] = {'layers': layers, 'model': 'opaque_layers'}
    return {'assemblies': assemblies, 'materials': materials}


def _rows(amounts):
    total = sum(amounts.values())
    return [{'assembly_id': a, 'weight': v/total, 'reference_area_m2': v} for a, v in sorted(amounts.items()) if v > 0], total


def unified(detailed, areas):
    """The frozen building-level equivalent document of one IECC context."""
    release = {'assemblies': detailed['assemblies'], 'materials': detailed['materials']}
    counted = detailed['mass_accounting']['reference']['counted_floor_area_m2']
    components, assemblies, excluded = {}, {}, []

    def attach(role, component, recipe):
        if recipe and recipe['status'] == 'ready':
            aid = stable_id('equivalent-assembly', recipe)
            assemblies[aid] = dict(recipe, id=aid)
            component['assembly_id'] = aid
        elif recipe:
            component.update(status=recipe['status'], reason=recipe.get('reason', 'invalid_equivalent_recipe'))
        components[role] = component
    for role, component in detailed['components'].items():
        if role == 'InteriorPartition':
            continue  # the building scope's added mass is the InternalMass component below
        assignments = component['assignments']
        if not assignments:
            components[role] = absent()
            continue
        if role in SHADING:
            components[role] = blocked('Geometric shading cannot be reduced as material layers')
            continue
        models = {detailed['assemblies'][a['assembly_id']]['model'] for a in assignments}
        if role in GROUND_ROLES and models & set(GROUND):
            ids = {a['assembly_id'] for a in assignments}
            if len(ids) != 1 or len(models) != 1:
                components[role] = blocked('Several ground constructions need an explicit aggregate policy')
                continue
            a = assignments[0]
            components[role] = {'assembly_id': a['assembly_id'], 'ground_method_id': a['ground_method_id'], 'status': 'ready',
                                'when': copy.deepcopy(a['when'])}
            assemblies[a['assembly_id']] = copy.deepcopy(detailed['assemblies'][a['assembly_id']])
            continue
        entries = areas.get(role, [])
        if len(entries) != len(assignments):
            raise ValueError(f'{detailed["id"]} {role}: {len(assignments)} assignments but {len(entries)} areas')
        amounts = defaultdict(float)
        for a, area in zip(assignments, entries):
            if detailed['assemblies'][a['assembly_id']]['model'] in GROUND:
                # PNNL gives some adiabatic core floors an F-factor construction: no layers to fit.
                excluded.append({'role': role, 'assembly_id': a['assembly_id'], 'area_m2': area})
                continue
            amounts[a['assembly_id']] += area
        if not amounts:
            components[role] = absent('source_ground_construction_on_interior_surface')
            continue
        rows, total = _rows(amounts)
        basis = 'source_model_net_component_area'
        if not rows:
            unique = sorted(amounts)
            if len(unique) != 1:
                components[role] = dict(absent('source_reference_zero_exposure'), derivation={
                    'contributors': [], 'weight_basis': basis, 'source_reference_area_m2': 0.})
                continue
            rows, total, basis = [{'assembly_id': unique[0], 'weight': 1., 'reference_area_m2': 0.}], 0., \
                'unique_source_recipe_without_reference_exposure'
        try:
            recipe = _recipe(release, rows, role)
        except (ValueError, KeyError, TypeError) as exc:
            components[role] = blocked(str(exc))
            continue
        attach(role, {'status': recipe['status'], 'assembly_id': None,
                      'derivation': {'contributors': rows, 'weight_basis': basis, 'source_reference_area_m2': total}}, recipe)
    mass = detailed['mass_accounting']
    amounts = defaultdict(float)
    for entry in mass['additional_mass']['entries']:
        amounts[entry['recipe_id']] += entry['reference_area_m2']
    rows, total = _rows(amounts)
    if rows:
        try:
            recipe = _recipe(_mass_release(mass['recipes']), rows, 'InternalMass')
            attach('InternalMass', {'status': recipe['status'], 'assembly_id': None,
                                    'quantity': {'area_per_counted_floor_area': total/counted, 'unit': 'm2/m2',
                                                 'application': 'additional_source_mass_only'},
                                    'derivation': {'contributors': rows, 'weight_basis': 'source_exposed_added_mass_area'}}, recipe)
        except (ValueError, KeyError, TypeError) as exc:
            components['InternalMass'] = blocked(str(exc))
    else:
        components['InternalMass'] = absent('source_has_no_added_internal_mass')
        walls = components.get('InteriorWall', {})
        if walls.get('status') == 'ready':
            contributors = walls['derivation']['contributors']
            recipe = _recipe(release, contributors, 'InternalMass')
            attach('InternalMass', {'status': recipe['status'], 'assembly_id': None,
                                    'quantity': {'area_per_counted_floor_area': 0., 'unit': 'm2/m2',
                                                 'application': 'zero added source mass; recipe available only for removed wall capacity'},
                                    'derivation': {'contributors': copy.deepcopy(contributors),
                                                   'weight_basis': walls['derivation']['weight_basis']}}, recipe)
    floors = {}
    for b in mass['physical_capacity_budgets']['InteriorFloor']:
        if detailed['assemblies'][b['source_assembly_id']]['model'] in GROUND:
            excluded.append({'role': 'FloorDistributedMass', 'assembly_id': b['source_assembly_id'],
                             'area_m2': b['area_per_counted_floor_area']*counted})
            continue
        floors[b['source_assembly_id']] = b['area_per_counted_floor_area']*counted
    rows, total = _rows(floors)
    if rows:
        try:
            recipe = _recipe(release, rows, 'FloorDistributedMass')
            attach('FloorDistributedMass', {'status': recipe['status'], 'assembly_id': None,
                                            'quantity': {'area_per_counted_floor_area': total/counted, 'unit': 'm2/m2',
                                                         'application': 'residual_floor_mass_only; deduct explicitly represented physical slabs once'},
                                            'derivation': {'contributors': rows, 'weight_basis': 'unique_physical_floor_inventory'}}, recipe)
        except (ValueError, KeyError, TypeError) as exc:
            components['FloorDistributedMass'] = blocked(str(exc))
    else:
        components['FloorDistributedMass'] = absent('source_has_no_above_ground_interstory_inventory')
    used = {v['assembly_id'] for v in components.values() if v['status'] == 'ready'}
    assemblies = {aid: a for aid, a in assemblies.items() if aid in used}
    source = detailed['source']
    document = {
        'schema_version': '1.1.0', 'kind': 'building_level_equivalent',
        'id': stable_id('equivalent-construction', {'context_id': detailed['id'], 'policy': POLICY}),
        'name': detailed['name']+' / building-level equivalent', 'scope': detailed['scope'], 'source': copy.deepcopy(source),
        'detailed_context_id': detailed['id'], 'climate_zone': source['climate']['value'],
        'reference_id': source['reference_variant_id'], 'supporting_profile_id': source['reference_variant_id'],
        'weighting_policy': 'precomputed_source_archetype',
        'status': 'blocked' if any(x['status'] == 'blocked' for x in components.values()) else 'ready',
        'components': components, 'assemblies': assemblies, 'infiltration': copy.deepcopy(detailed['infiltration']),
        'consumer_inputs': list(CONSUMER_INPUTS), 'mass_accounting': copy.deepcopy(mass),
        'foundation_ground': copy.deepcopy(detailed['foundation_ground']), 'materials': {},
        'provenance': {'detailed_release': f'atlas-release IECC set {source["construction_set_id"]}', 'profile_release': POLICY,
                       'original_unit': 'source SI layers and IDF net surface areas',
                       'transformation': 'source assignments, net IDF surface areas as weights, fixed two-parameter thermal '
                                         'approximation (scripts.construction_equivalence); design-flow infiltration unchanged',
                       'interpretation_note': 'Additive approximation, not replacement detailed rules. Reported fit errors are '
                                              'not building energy error bounds (ADR 0045).'}}
    if excluded:
        document['provenance']['excluded_ground_constructions'] = {
            'entries': excluded, 'interpretation': 'F- or C-factor constructions on interior (adiabatic) surfaces of the source '
            'model have no layers; they are left out of the opaque fits and the floor mass (ADR 0045).'}
    text = str(document)
    document['evidence'] = {k: copy.deepcopy(v) for k, v in detailed['evidence'].items() if k in text}
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--idf-root', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = encode(build(args.idf_root))
    if args.check:
        if OUTPUT.read_bytes() != data:
            raise SystemExit(f'{OUTPUT.name} does not reproduce; rerun python -m scripts.iecc_unified')
        print(f'{OUTPUT.name} reproduces')
        return
    OUTPUT.write_bytes(data)
    print(f'IECC unified areas: {sum(len(c) for t in load_json(OUTPUT)["areas"].values() for c in t.values())} contexts; '
          f'{len(data)/1e6:.1f} MB')


if __name__ == '__main__':
    main()
