"""Source assemblies, SI materials, explicit adjustments and scoped air exchange."""
import copy
import re
from scripts.common import load_json
from scripts.definition_contract import DefinitionBundle, DefinitionError, evidence, parameter, record, stable_id
from scripts.definition_compare import physical_properties
from scripts.program_definitions import source_evidence

U_FACTOR = 5.678263337
R_FACTOR = 1/U_FACTOR
BASE = 'lib/openstudio-standards/standards/ashrae_90_1/data/'


def unique_named(rows, name):
    matches = [r for r in rows if r['name'] == name]
    unique = {stable_id('row', r): r for r in matches}
    if len(unique) != 1:
        raise DefinitionError(f'Expected one physical definition for {name}; found {len(unique)}')
    return next(iter(unique.values()))


def normalize_material(source):
    result = {'name': source['name'], 'model': source.get('material_type'), 'source_code_defaults': []}
    if 'simple glazing' in source['name'].lower():
        tokens = source['name'].split()
        for label, field, fallback, factor in [('U','u_W_m2_K',1.23,U_FACTOR),
                ('SHGC','shgc',.61,1), ('VT','visible_transmittance',.81,1)]:
            values = [float(tokens[i+1]) for i, token in enumerate(tokens[:-1]) if token == label]
            result[field] = (values[-1] if values else fallback)*factor
            if not values:
                result['source_code_defaults'].append(field)
        result['model'] = 'SimpleGlazing'
        return result
    conversions = {'thickness': ('thickness_m', .0254),
        'conductivity': ('conductivity_W_m_K', .144227909),
        'density': ('density_kg_m3', 16.01846337396),
        'specific_heat': ('specific_heat_J_kg_K', 4186.8),
        'resistance': ('resistance_m2_K_W', R_FACTOR),
        'u_factor': ('u_W_m2_K', U_FACTOR)}
    for field, (target, factor) in conversions.items():
        if field in source:
            result[target] = source[field]*factor if source[field] is not None else None
    for field in ('thermal_absorptance', 'solar_absorptance', 'visible_absorptance',
                  'solar_heat_gain_coefficient', 'visible_transmittance', 'gas_type', 'roughness',
                  'optical_data_type', 'solar_transmittance_at_normal_incidence',
                  'front_side_solar_reflectance_at_normal_incidence', 'back_side_solar_reflectance_at_normal_incidence',
                  'visible_transmittance_at_normal_incidence', 'front_side_visible_reflectance_at_normal_incidence',
                  'back_side_visible_reflectance_at_normal_incidence', 'infrared_transmittance_at_normal_incidence',
                  'front_side_infrared_hemispherical_emissivity', 'back_side_infrared_hemispherical_emissivity',
                  'dirt_correction_factor_for_solar_and_visible_transmittance', 'solar_diffusing'):
        if field in source:
            result[field] = source[field]
    return result


def film_resistance(role, interior=True, exterior=True):
    outside, inside = .17, .68
    if role in {'ExteriorRoof', 'Skylight', 'GroundContactRoof', 'DemisingRoof'}:
        inside = .61
    elif role in {'ExteriorFloor', 'GroundContactFloor'}:
        inside = .92
    elif role in {'InteriorFloor', 'DemisingFloor'}:
        outside, inside = .61, .92
    elif role == 'InteriorCeiling':
        outside, inside = .92, .61
    elif role.startswith('Interior') or role == 'DemisingWall':
        outside = .68
    elif role.startswith('Attic'):
        inside = .46
    if role.startswith('GroundContact'):
        outside = 0
    return ((inside if interior else 0)+(outside if exterior else 0))*R_FACTOR


def _resistance(layer):
    if layer.get('model') in {'MasslessOpaqueMaterial', 'AirGap'}:
        return layer.get('resistance_m2_K_W')
    t, k = layer.get('thickness_m'), layer.get('conductivity_W_m_K')
    return t/k if t is not None and k is not None and k > 0 else layer.get('resistance_m2_K_W')


def adjust_layers(layers, target_u, insulation_name, films):
    result = copy.deepcopy(layers)
    if target_u is None or target_u <= 0:
        return result, 'unresolved_target'
    if not insulation_name:
        candidates = [(i, _resistance(layer)) for i, layer in enumerate(result)]
        if not candidates or any(r is None for _, r in candidates):
            return result, 'unresolved_insulation'
        insulation_name = result[max(candidates, key=lambda x:x[1])[0]]['name']
    other = [_resistance(layer) for layer in result if layer['name'] != insulation_name]
    if any(r is None for r in other):
        return result, 'unresolved_layer_resistance'
    needed = 1/target_u-sum(other)-films
    matches = [layer for layer in result if layer['name'] == insulation_name]
    if len(matches) != 1:
        return result, 'unresolved_insulation'
    layer = matches[0]
    if needed <= 0:
        return [v for v in result if v is not layer], 'insulation_removed_target_not_attainable'
    if layer.get('conductivity_W_m_K'):
        layer['thickness_m'] = needed*layer['conductivity_W_m_K']
    elif layer.get('resistance_m2_K_W') is not None:
        layer['resistance_m2_K_W'] = needed
    else:
        return result, 'unresolved_insulation_material'
    return result, 'adjusted'


def build_constructions(context, programs):
    bundle = DefinitionBundle()
    construction_path = BASE+'ashrae_90_1.constructions.json'
    material_path = BASE+'ashrae_90_1.materials.json'
    constructions = load_json(context.sources[construction_path])['constructions']
    materials = load_json(context.sources[material_path])['materials']
    elements = {}
    templates = {r['template'] for r in programs['programs']}

    def assembly(source, name, role, target=None, assumed=False):
        row = record('construction', source, name, derivation='assumed' if assumed else 'normalized')
        row.update(role=role, representation='element', layers=[], assembly_status='unresolved',
                   applicable_building_types=[], target_adjustment=None)
        attr = source.get('source_attributes', {})
        eid = evidence(context, None if assumed else stable_id('sourcefile', {'path': construction_path}),
                       construction_path+'#/constructions/name='+name, attr or name, 'source assembly/target',
                       'ordered materials, SI conversion; source target adjustment when resolvable',
                       'Generic experimental fallback' if assumed else 'Source assembly and target are distinct; unresolved is not ready.')
        bundle['provenance'].append(eid); row['evidence_ids'] = [eid['id']]
        for key, unit in [('u_W_m2_K','W/m2/K'), ('shgc','1'), ('visible_transmittance','1')]:
            row['parameters'][key] = parameter(source.get(key), unit, eid['id'])
        try:
            raw = unique_named(constructions, name)
            layers = [normalize_material(unique_named(materials, n))
                      if 'simple glazing' not in n.lower() else normalize_material({'name': n})
                      for n in raw['materials']]
            row['assembly_status'] = 'resolved_source_layers'
            if target and raw['intended_surface_type'] not in {'ExteriorWindow', 'Skylight'}:
                films = film_resistance(role, attr.get('u_value_includes_interior_film_coefficient', True),
                                        attr.get('u_value_includes_exterior_film_coefficient', True))
                layers, status = adjust_layers(layers, target, raw.get('insulation_layer'), films)
                row['target_adjustment'] = {'status': status, 'target_u_W_m2_K': target,
                                            'films_m2_K_W': films}
                if status.startswith('unresolved'):
                    row['assembly_status'] = status
            elif layers and layers[0]['model'] == 'SimpleGlazing':
                if target:
                    layers[0]['u_W_m2_K'] = target
                for key in ('shgc','visible_transmittance'):
                    if source.get(key) is not None:
                        layers[0][key] = source[key]
            for index, layer in enumerate(layers):
                mid = stable_id('material', {'properties': layer, 'assembly_evidence': eid['id']})
                mat = {'id': mid, **layer, 'evidence_ids': [eid['id']],
                       'source_material_locator': material_path+'#/materials/name='+layer['name']}
                bundle['materials'].append(mat)
                row['layers'].append({'material_id': mid, 'properties': layer, 'order': index})
        except DefinitionError as error:
            row['assembly_status'] = str(error)
        if role.startswith('GroundContact'):
            row['required_inputs'] = ['surface_area', 'exposed_perimeter', 'ground_boundary_condition']
            row['ground_model'] = 'consumer_ground_heat_transfer; assembly alone is not soil boundary'
        row['performance_id'] = stable_id('construction-performance',
                                         physical_properties({'layers': row['layers'], 'parameters': row['parameters'],
                                                              'role': role, 'target_adjustment': row['target_adjustment']}))
        bundle['constructions'].append(row)
        elements[source['id']] = row
        return row

    for source in context.atlas.get('envelope_components', []):
        if source['template'] not in templates:
            continue
        attr = source['source_attributes']
        row = assembly(source, attr['construction'], source['surface_type'], source.get('u_W_m2_K'))
        row['conditioning_category'] = source['building_category']
        row['construction_type'] = source['construction_type']
        row['gate'] = ['residential'] if source['building_category']=='Residential' else ['nonresidential']
    source_templates = {}
    provs = {r['id']: r for r in context.atlas.get('provenance', [])}
    for original in context.atlas.get('envelope_components', []):
        pv = provs.get(original['provenance_id'], {})
        source_templates[pv.get('source_file_id')] = original['template']
    for file in context.atlas.get('source_files', []):
        template = source_templates.get(file['id'])
        if template not in templates or not file['path'].endswith('.construction_properties.json'):
            continue
        for index, attr in enumerate(load_json(context.sources[file['path']])['construction_properties']):
            role = attr.get('intended_surface_type') or ''
            if not role.startswith('GroundContact') or not attr.get('construction'):
                continue
            source = {'id': stable_id('ground-source', {'file':file['id'], 'index':index}),
                      'template': template, 'source_family': 'existing_stock_benchmark' if template.startswith('DOE') else 'code_prototype_rules',
                      'climate_zone_set': attr['climate_zone_set'], 'source_attributes': attr}
            row = assembly(source, attr['construction'], role)
            row['conditioning_category'] = attr['building_category']
            row['construction_type'] = attr['standards_construction_type']
            row['gate'] = ['residential'] if attr['building_category']=='Residential' else ['nonresidential']
            for field, target_field, unit, factor in [('assembly_maximum_f_factor','f_W_m_K','W/m/K',1.730734667),
                       ('assembly_maximum_c_factor','c_W_m2_K','W/m2/K',U_FACTOR)]:
                val = attr.get(field)
                ev = evidence(context, file['id'], file['path']+f'#/construction_properties/{index}/{field}',
                              val, attr.get(field+'_unit') or 'source IP factor', f'SI factor {factor}',
                              'Ground F/C target; requires consumer geometry, not an area U-value.')
                bundle['provenance'].append(ev)
                row['parameters'][target_field] = parameter(val*factor if val is not None else None, unit, ev['id'])
            row['ground_model'] = 'F-factor ground floor' if attr.get('assembly_maximum_f_factor') is not None else 'C-factor underground wall'
            row['required_inputs'] = ['surface_area','exposed_perimeter'] if role=='GroundContactFloor' else ['wall_height']
    for path, local in context.sources.items():
        if not path.endswith('.construction_sets.json'):
            continue
        for index, source in enumerate(load_json(local)['construction_sets']):
            if source.get('template') not in templates:
                continue
            if context.scope == 'pilot' and source.get('building_type') not in {'Office', 'Any', 'MediumOffice'}:
                continue
            source = dict(source, id=stable_id('construction-set-source', {'path': path, 'index': index}),
                          source_family='existing_stock_benchmark' if source['template'].startswith('DOE') else 'code_prototype_rules')
            package = record('construction', source, source['building_type']+' construction package')
            package.update(representation='package', role='package', elements={}, air_exchange=[],
                           source_set=source, space_type=source.get('space_type'), climate=source.get('climate_zone_set'))
            pe = evidence(context, stable_id('sourcefile', {'path': path}), path+f'#/construction_sets/{index}',
                          source, 'source selectors', 'exact construction-set references',
                          'Any/Office and source space roles remain explicit, without Cartesian expansion.')
            bundle['provenance'].append(pe); package['evidence_ids'] = [pe['id']]
            for key, role in [('interior_walls','InteriorWall'), ('interior_floors','InteriorFloor'),
                              ('interior_ceilings','InteriorCeiling')]:
                name = source.get(key)
                if name:
                    element = assembly(dict(source, id=source['id']+'/'+key), name, role)
                    package['elements'][key] = [element['id']]
            # Each target role links only the matching construction type/category, retaining its climate.
            for key, role in [('exterior_wall','ExteriorWall'),('exterior_roof','ExteriorRoof'),
                              ('exterior_floor','ExteriorFloor'),('exterior_fixed_window','ExteriorWindow'),
                              ('ground_contact_floor','GroundContactFloor'),('ground_contact_wall','GroundContactWall')]:
                typ, category = source.get(key+'_standards_construction_type'), source.get(key+'_building_category')
                matches = [r for sid, r in elements.items() if r.get('conditioning_category') and
                           r['template']==source['template'] and r['role']==role and
                           r.get('conditioning_category')==category and
                           r.get('construction_type')==typ]
                if typ and category:
                    package['elements'][key] = [r['id'] for r in matches]
            for program in programs['programs']:
                if program['template'] != source['template'] or program['evidence_view'] != 'source':
                    continue
                if source['building_type'] not in {'Any','Office',program['building_type']}:
                    continue
                if source['building_type']=='Office' and program['building_type'] not in {'SmallOffice','MediumOffice','LargeOffice'}:
                    continue
                original = next(s for s in context.atlas['programs'] if s['id']==program['source_id'])
                for field, unit, category in [('infiltration_m3_s_m2','m3/s/m2','infiltration'),
                        ('ventilation_m3_s_m2','m3/s/m2','outdoor_air'),
                        ('ventilation_m3_s_person','m3/s/person','outdoor_air'),
                        ('ventilation_ach','1/h','outdoor_air'), ('minimum_total_air_changes','1/h','total_supply')]:
                    val = original.get(field) if field != 'minimum_total_air_changes' else original['source_attributes'].get(field)
                    aid = source_evidence(context, original, field, unit, bundle)
                    package['air_exchange'].append(dict(parameter(val, unit, aid),
                        category=category, source_program_id=program['source_id'], scope='source_program_requirement',
                        schedule_id=None, basis=field))
            bundle['constructions'].append(package)
    # Explicit experimental generic layers for roles lacking usable source assignment.
    for role, name in [('InteriorWall','Typical Interior Wall'), ('InteriorFloor','Typical Interior Floor'),
                       ('GroundContactFloor','Typical Uninsulated 8in Slab Floor'),
                       ('GroundContactWall','Typical Uninsulated Basement Mass Wall')]:
        fallback = {'id': 'generic-v1/'+role, 'template': 'Generic experimental v1',
                    'source_family': 'experimental_assumption', 'building_type': None}
        element = assembly(fallback, name, role, assumed=True)
        element['gate'] = ['residential','nonresidential']
        element['fallback_policy'] = 'Use building-wide only where no resolved source role assignment exists; keep fixed across comparisons.'
    return DefinitionBundle().merge(bundle)
