"""Additive building-level recipe export; detailed APIs and source rules unchanged."""
import copy
import math
from collections import defaultdict

from scripts.construction_equivalence import reduce_opaque
from scripts.definition_contract import stable_id


MASS_ROLES = ('InternalMass', 'FloorDistributedMass')
SHADING = ('SpaceShading', 'BuildingShading', 'SiteShading')


def _operand(value, positive=False):
    if (not isinstance(value,(float,int)) or isinstance(value,bool) or not math.isfinite(value)
            or value < 0 or (positive and value == 0)):
        raise ValueError('Unknown or invalid source exposure/material operand')
    return value


def blocked(reason):
    return {'status': 'blocked', 'assembly_id': None, 'reason': reason}


def absent(reason='source_absent'):
    return {'status': 'not_applicable', 'assembly_id': None, 'reason': reason}


def source_layers(release, assembly):
    layers = []
    for row in assembly['layers']:
        material = release['materials'][row['material_id']]
        p = material['properties']
        if material['model'] == 'StandardOpaqueMaterial':
            thickness,conductivity,density,cp = (_operand(p.get(k),positive=True) for k in
                ('thickness_m','conductivity_W_m_K','density_kg_m3','specific_heat_J_kg_K'))
            if cp < 100:
                raise ValueError('Invalid source specific heat')
            r = thickness/conductivity
            c = thickness*density*cp
        elif material['model'] in ('MasslessOpaqueMaterial', 'AirGap'):
            r, c = _operand(p.get('resistance_m2_K_W'),positive=True), 0.
        else:
            raise ValueError('Source is not a linear opaque material recipe')
        layers.append({'R': r, 'C': c})
    return layers


def _match(assignments, space, operation=None):
    choices = []
    for a in assignments:
        w = a['when']
        if w.get('window_operation') and w['window_operation'] != operation:
            continue
        scope = w['scope']
        if scope == 'space_type' and w['space_type'] != space.get('source_space_type'):
            continue
        if scope == 'story' and w['source_story_id'] != space['story']:
            continue
        if scope not in ('space_type', 'story', 'building_default'):
            continue
        choices.append(({'building_default': 0, 'story': 1, 'space_type': 2}[scope], a))
    if not choices:
        return None
    rank = max(i for i, _ in choices)
    top = {a['assembly_id']: a for i, a in choices if i == rank}
    if len(top) != 1:
        raise ValueError('Ambiguous source assignment after precedence')
    return next(iter(top.values()))


def contributors_for(component, role, profile):
    assignments = component['assignments']
    amounts = defaultdict(float)
    if 'assembly_areas' in profile:
        for a in assignments:
            area = _operand(profile['assembly_areas'].get(a['assembly_id'], {}).get('area_m2'))
            amounts[a['assembly_id']] += area
    else:
        for space in profile['spaces']:
            area = _operand(space.get('exposure_m2',{}).get(role))
            if role in ('ExteriorWindow', 'InteriorWindow'):
                if area == 0:
                    continue
                op = space.get('operation_area_m2',{}).get(role,{})
                fixed,operable = _operand(op.get('FixedWindow')), _operand(op.get('OperableWindow'))
                if not math.isclose(fixed+operable, area, rel_tol=1e-8,abs_tol=1e-7):
                    raise ValueError('Window operation exposure does not match its semantic')
                operations = [('fixed', fixed), ('operable', operable)]
            else:
                operations = [(None, area)]
            for operation, area in operations:
                if area <= 0:
                    continue
                selected = _match(assignments, space, operation)
                if selected is None:
                    raise ValueError('Positive exposure lacks a compatible source recipe')
                amounts[selected['assembly_id']] += area
    positive = {a: v for a,v in amounts.items() if v > 0}
    total = sum(positive.values())
    if total:
        return [{'assembly_id': a, 'weight': v/total, 'reference_area_m2': v}
                for a,v in sorted(positive.items())], total, 'source_archetype_net_component_area'
    unique = sorted({a['assembly_id'] for a in assignments})
    if len(unique) == 1:
        return [{'assembly_id': unique[0], 'weight': 1., 'reference_area_m2': 0.}], 0., 'unique_source_recipe_without_reference_exposure'
    return [], 0., 'source_reference_zero_exposure'


def _surface_properties(release, rows):
    result = {}
    for side, index in (('exterior', 0), ('interior', -1)):
        properties = []
        for row in rows:
            a = release['assemblies'][row['assembly_id']]
            properties.append((row, release['materials'][a['layers'][index]['material_id']]['properties']))
        face = {}
        for key in ('thermal_absorptance', 'solar_absorptance', 'visible_absorptance'):
            values = [p.get(key) for _,p in properties]
            if any(v is None or not 0 <= v <= 1 for v in values):
                raise ValueError('Unknown or invalid source surface absorptance')
            face[key] = sum(row['weight']*p[key] for row,p in properties)
        dominant = min(properties, key=lambda x: (-x[0]['weight'], x[0]['assembly_id']))[1]
        if 'roughness' not in dominant:
            raise ValueError('Unknown source roughness')
        face['roughness'] = dominant['roughness']
        result[side] = face
    return result


def _opening(release, rows):
    sources = [release['assemblies'][r['assembly_id']] for r in rows]
    # Approved boundary: geometric overhangs are BEMGen inputs, not material
    # modifiers. Every source dimension remains in the component derivation.
    modifiers = [{k:copy.deepcopy(v) for k,v in a.get('solar_modifiers',{}).items()
                  if k!='overhang_geometry'} for a in sources]
    def physics(value):
        if isinstance(value, dict):
            return {k: physics(v) for k,v in value.items() if k != 'evidence_id'}
        return value
    if any(physics(m) != physics(modifiers[0]) for m in modifiers):
        raise ValueError('Different source solar modifiers need an explicit aggregate policy')
    physical = [[{'model': release['materials'][l['material_id']]['model'],
                  'properties': release['materials'][l['material_id']]['properties']} for l in a['layers']] for a in sources]
    # Identical layered optics need no proxy even when source construction IDs differ.
    if all(p == physical[0] for p in physical):
        return {'status': 'ready', 'model': sources[0]['model'], 'layers': copy.deepcopy(physical[0]),
                'quality': 'unchanged_source_physics', 'fit': None,
                'solar_modifiers': modifiers[0]}
    if all(a['model'] == 'simple_glazing' and len(p) == 1 for a,p in zip(sources, physical)):
        p = {}
        for name in ('u_W_m2_K', 'shgc', 'visible_transmittance'):
            values = [v[0]['properties'].get(name) for v in physical]
            if any(v is None for v in values):
                raise ValueError('Unknown glazing property: '+name)
            p[name] = sum(r['weight']*v for r,v in zip(rows, values))
        return {'status': 'ready', 'model': 'simple_glazing',
                'layers': [{'model': 'SimpleGlazing', 'properties': p}],
                'quality': 'area_weighted_optical_proxy', 'fit': None,
                'solar_modifiers': modifiers[0]}
    raise ValueError('Heterogeneous detailed glazing requires attained optical properties')


def _recipe(release, rows, role):
    sources = [release['assemblies'][r['assembly_id']] for r in rows]
    if all(a['model'] in ('simple_glazing', 'detailed_glazing') for a in sources):
        return _opening(release, rows)
    contributors = [{'weight': row['weight'], 'layers': source_layers(release, a)} for row,a in zip(rows, sources)]
    inside = role.startswith('Interior') or role in MASS_ROLES
    result = reduce_opaque(contributors, films=(.13,.13) if inside else (.04,.13), one_sided=role in MASS_ROLES)
    result['model'] = 'opaque_layers'
    if result['status'] == 'ready':
        result['surface_properties'] = _surface_properties(release, rows)
    return result


def _mass_from_profile(profile, packet):
    amounts = defaultdict(float)
    for s in profile['spaces']:
        for mass in s['added_mass']:
            if mass['status'] != 'ready' or mass['recipe_id'] is None:
                raise ValueError('Unknown source added-mass quantity or material')
            amounts[mass['recipe_id']] += _operand(mass.get('area_m2'))
    total = sum(amounts.values())
    if total == 0:
        return absent('source_has_no_added_internal_mass'), None
    rows = [{'assembly_id': aid, 'weight': a/total, 'reference_area_m2': a} for aid,a in sorted(amounts.items())]
    raw = []
    for row in rows:
        layers = packet['mass_recipes'][row['assembly_id']]
        fake = {'materials': {str(i):{'model':'StandardOpaqueMaterial','properties':p} for i,p in enumerate(layers)}}
        raw.append({'weight': row['weight'], 'layers': source_layers(fake, {'layers':[{'material_id':str(i)} for i in range(len(layers))]})})
    result = reduce_opaque(raw, films=(.13,.13), one_sided=True)
    result['model'] = 'opaque_layers'
    # Native furnishing material is a homogeneous source recipe; use its faces.
    faces = {}
    for side,index in (('exterior',0),('interior',-1)):
        face = {}
        for key in ('thermal_absorptance','solar_absorptance','visible_absorptance'):
            face[key] = sum(row['weight']*packet['mass_recipes'][row['assembly_id']][index][key] for row in rows)
        dominant = min(rows, key=lambda r: (-r['weight'],r['assembly_id']))
        face['roughness'] = packet['mass_recipes'][dominant['assembly_id']][index]['roughness']
        faces[side] = face
    result['surface_properties'] = faces
    return {'status': result['status'], 'assembly_id': None,
            'quantity': {'area_per_counted_floor_area': total/profile['counted_floor_area_m2'],
                         'unit': 'm2/m2', 'application': 'additional_source_mass_only'},
            'derivation': {'contributors': rows, 'weight_basis': 'source_exposed_added_mass_area'}}, result


def _mass_budgets(release, configuration, profile):
    """Capacity ledger references physical assemblies once, not both face areas."""
    budgets = {}
    for role, key in (('InteriorFloor','floor_inventory'), ('InteriorWall','wall_inventory')):
        amounts = defaultdict(float)
        if 'spaces' in profile:
            spaces = {s['name']: s for s in profile['spaces']}
            for item in profile.get(key, []):
                if item['area_m2'] is None:
                    raise ValueError('Unequal source paired-face multipliers require an explicit area policy')
                _operand(item['area_m2'])
                a = _match(configuration['components'][role]['assignments'], spaces[item['source_space_name']])
                if a is None:
                    raise ValueError('Unresolved physical mass inventory assignment')
                amounts[a['assembly_id']] += item['area_m2']
        else:
            for a in configuration['components'][role]['assignments']:
                area = profile['assembly_areas'][a['assembly_id']]['area_m2']
                if area is None:
                    raise ValueError('Unknown physical mass inventory area')
                amounts[a['assembly_id']] += area
        budgets[role] = [{'source_assembly_id': aid,
                          'area_per_counted_floor_area': area/profile['counted_floor_area_m2'],
                          'capacity_per_counted_floor_area_J_m2_K': area/profile['counted_floor_area_m2']*sum(
                              l['C'] for l in source_layers(release, release['assemblies'][aid]))}
                         for aid,area in sorted(amounts.items()) if area > 0]
    return budgets


def export_equivalent(release, context_id, packet):
    if context_id not in release['contexts']:
        raise ValueError('Unsupported detailed construction context')
    c = release['contexts'][context_id]
    primary = release['construction_sets'][c['construction_set_id']]
    configuration = release['component_configurations'][c['configuration_id']]
    profile_id = primary['source'].get('source_fixture_id') or c['reference_id']
    profile = packet['profiles'].get(profile_id)
    components, assemblies = {}, {}
    def attach(role, component, recipe):
        if recipe and recipe['status'] == 'ready':
            aid = stable_id('equivalent-assembly', recipe)
            assemblies[aid] = dict(recipe, id=aid)
            component['assembly_id'] = aid
        elif recipe:
            component.update(status=recipe['status'], reason=recipe.get('reason','invalid_equivalent_recipe'))
        components[role] = component
    for role, component in configuration['components'].items():
        if role == 'InteriorPartition':
            role = 'InternalMass'
            if primary['scope'] == 'building':
                continue  # Actual native added-mass objects, not a guessed recipe quantity.
        if not component['assignments']:
            components[role] = absent()
            continue
        if profile is None:
            components[role] = blocked('Missing source weighting profile')
            continue
        if role in SHADING:
            components[role] = blocked('Geometric shading cannot be reduced as material layers')
            continue
        try:
            rows, area, basis = contributors_for(component, role, profile)
            if not rows:
                components[role] = dict(absent('source_reference_zero_exposure'),
                                        derivation={'contributors': [], 'weight_basis': basis,
                                                    'source_reference_area_m2': 0.})
                continue
            recipe = _recipe(release, rows, role)
            output = {'status': recipe['status'], 'assembly_id': None,
                      'derivation': {'contributors': rows, 'weight_basis': basis,
                                     'source_reference_area_m2': area}}
            geometry = [{'source_assembly_id': row['assembly_id'],
                         'overhang_geometry': copy.deepcopy(release['assemblies'][row['assembly_id']]['solar_modifiers']['overhang_geometry'])}
                        for row in rows if 'overhang_geometry' in release['assemblies'][row['assembly_id']].get('solar_modifiers',{})]
            if geometry:
                output['derivation'].update(geometry_evidence=geometry,
                    geometry_policy='consumer_overhang_geometry_by_BEMGen')
            if role == 'InternalMass':
                output['quantity'] = {'area_per_counted_floor_area': area/profile['counted_floor_area_m2'],
                                      'unit': 'm2/m2', 'application': 'additional_source_mass_only'}
            attach(role, output, recipe)
        except (ValueError, KeyError, TypeError) as exc:
            components[role] = blocked(str(exc))
    if primary['scope'] == 'building':
        try:
            output, recipe = _mass_from_profile(profile, packet) if profile else (blocked('Missing source weighting profile'), None)
            attach('InternalMass', output, recipe)
        except (ValueError, KeyError, TypeError) as exc:
            components['InternalMass'] = blocked(str(exc))
    # Floor mass is one physical inventory, with a recipe independent of zoning.
    if profile:
        if 'spaces' in profile:
            area = None
            by_space = {s['name']: s for s in profile['spaces']}
            amounts = defaultdict(float)
            try:
                for f in profile['floor_inventory']:
                    if f['area_m2'] is None:
                        raise ValueError('Unequal source paired-face multipliers require an explicit area policy')
                    a = _match(configuration['components']['InteriorFloor']['assignments'], by_space[f['source_space_name']])
                    if not a:
                        raise ValueError('Physical floor inventory has no source construction')
                    amounts[a['assembly_id']] += f['area_m2']
                # Normalize grouped contributions against their own sum, avoiding
                # a different floating accumulation order for the denominator.
                area = sum(amounts.values())
            except ValueError as exc:
                components['FloorDistributedMass'] = blocked(str(exc))
                area = None
        else:
            amounts = {a['assembly_id']: profile['assembly_areas'][a['assembly_id']]['area_m2']
                       for a in configuration['components']['InteriorFloor']['assignments']}
            area = sum(amounts.values()) if all(v is not None for v in amounts.values()) else None
        if area is not None and area > 0:
            rows = [{'assembly_id': aid, 'weight': value/area, 'reference_area_m2': value} for aid,value in sorted(amounts.items()) if value > 0]
            try:
                recipe = _recipe(release, rows, 'FloorDistributedMass')
                attach('FloorDistributedMass', {'status': recipe['status'], 'assembly_id': None,
                       'quantity': {'area_per_counted_floor_area': area/profile['counted_floor_area_m2'], 'unit': 'm2/m2',
                                    'application': 'residual_floor_mass_only; deduct explicitly represented physical slabs once'},
                       'derivation': {'contributors': rows, 'weight_basis': 'unique_physical_floor_inventory'}}, recipe)
            except (ValueError, KeyError, TypeError) as exc:
                components['FloorDistributedMass'] = blocked(str(exc))
        elif 'FloorDistributedMass' not in components:
            components['FloorDistributedMass'] = absent('source_has_no_above_ground_interstory_inventory') if area == 0 else blocked('Unknown floor mass area')
    else:
        components['FloorDistributedMass'] = blocked('Missing source weighting profile')
    mass_budgets = {}
    if profile:
        try:
            mass_budgets = _mass_budgets(release, configuration, profile)
        except (ValueError,KeyError,TypeError) as exc:
            components['InternalMass'] = blocked(str(exc))
    # If the source adds no furnishings, retain a source-backed wall-transfer
    # recipe at zero additional area. It creates no mass in the reference case.
    if (profile and components['InternalMass']['status'] == 'not_applicable'
            and configuration['components']['InteriorWall']['assignments']):
        try:
            rows, _, basis = contributors_for(configuration['components']['InteriorWall'], 'InteriorWall', profile)
            if rows:
                recipe = _recipe(release, rows, 'InternalMass')
                attach('InternalMass', {'status': recipe['status'], 'assembly_id': None,
                       'quantity': {'area_per_counted_floor_area': 0., 'unit': 'm2/m2',
                                    'application': 'zero added source mass; recipe available only for removed wall capacity'},
                       'derivation': {'contributors': rows, 'weight_basis': basis}}, recipe)
        except (ValueError,KeyError,TypeError) as exc:
            components['InternalMass'] = blocked(str(exc))
    # Final status changes (e.g. ambiguous physical inventories) may retire an
    # earlier successful recipe; close resources over final ready components.
    used = {v['assembly_id'] for v in components.values() if v['status']=='ready'}
    assemblies = {aid:a for aid,a in assemblies.items() if aid in used}
    area_approximations = {kind: sum(bool(item.get('approximation')) for item in profile.get(key,[])) if profile else 0
                          for kind,key in (('floor_pairs','floor_inventory'),('wall_pairs','wall_inventory'))}
    consumer_inputs = ['actual component areas and geometry', 'actual counted floor area',
                       'physical mass already represented by instantiated interior surfaces']
    if any('geometry_evidence' in v.get('derivation',{}) for v in components.values()):
        consumer_inputs.append('actual overhang geometry resolved by BEMGen; source dimensions are evidence only')
    return {'schema_version': '1.1.0', 'kind': 'building_level_equivalent',
            'id': stable_id('equivalent-construction', {'context_id': context_id, 'policy': '1.1.0'}),
            'name': primary['name']+' / building-level equivalent', 'scope': primary['scope'],
            'source': copy.deepcopy(primary['source']), 'detailed_context_id': context_id,
            'climate_zone': c['climate_zone'], 'reference_id': c['reference_id'],
            'supporting_profile_id': profile_id, 'weighting_policy': 'precomputed_source_archetype',
            'status': 'blocked' if any(x['status'] == 'blocked' for x in components.values()) else 'ready',
            'components': components, 'assemblies': assemblies, 'infiltration': copy.deepcopy(c['infiltration']),
            'consumer_inputs': consumer_inputs,
            'mass_accounting': {'floor_pair_policy': 'one physical slab; do not add both floor and ceiling capacity',
                                'paired_surface_policy': {'canonical_side':'InteriorFloor',
                                    'adjacent_ceiling':'reverse the same canonical floor assembly',
                                    'unpaired_ceiling':'use InteriorCeiling recipe'},
                                'added_mass_policy': 'additional source furnishings/partition objects are separate from explicit surfaces',
                                'removed_wall_policy': 'Convert removed physical wall capacity to InternalMass area using its equivalent areal capacity; heat-exchange equivalence remains approximate',
                                'residual_floor_policy': 'Convert only unrepresented floor capacity to FloorDistributedMass area; explicit slabs retain their capacity',
                                'physical_inventory_profile_id': profile_id,
                                'paired_face_area_policy': 'mean_zone_weighted_faces',
                                'reference_area_approximation': {
                                    'unequal_multiplier_pair_counts': area_approximations,
                                    'evidence_profile_id': profile_id,
                                    'interpretation': 'Mean of multiplied face areas where multipliers differ; reference-model approximation, not physical copy reconstruction'},
                                'physical_capacity_budgets': mass_budgets},
            'provenance': {'detailed_release': 'v2.2.0', 'profile_release': 'construction-weighting-v1.1.0',
                           'original_unit': 'source SI layers and archetype reference areas',
                           'transformation': 'Source precedence, precomputed area weights, fixed two-parameter thermal approximation; fixed ACH unchanged',
                           'interpretation_note': 'Additive approximation, not replacement detailed rules. Reported fit errors are not building energy error bounds.'}}
