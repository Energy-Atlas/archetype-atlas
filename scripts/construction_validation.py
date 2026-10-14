"""Focused model, dependency, provenance and completeness validation."""
import math
from jsonschema import Draft202012Validator
from scripts.common import ROOT, load_json
from scripts.energy_json_review import GLASS, OPAQUE

MODELS = {'StandardOpaqueMaterial':OPAQUE|{'thickness_m','conductivity_W_m_K','density_kg_m3','specific_heat_J_kg_K'},
          'MasslessOpaqueMaterial':OPAQUE|{'resistance_m2_K_W'},
          'AirGap':{'resistance_m2_K_W'}, 'Gas':{'thickness_m','gas_type'},
          'StandardGlazing':GLASS|{'conductivity_W_m_K'},
          'SimpleGlazing':{'u_W_m2_K','shgc'}}
CATEGORIES = {'roughness','gas_type','optical_data_type','visible_transmittance_mode'}
POSITIVE = {'thickness_m','conductivity_W_m_K','density_kg_m3','specific_heat_J_kg_K','resistance_m2_K_W','u_W_m2_K'}
CLIMATES = {'0A','0B','1A','1B','2A','2B','3A','3B','3C','4A','4B','4C','5A','5B','5C','6A','6B','7A','7B','8A','8B'}


def validate_references(node, evidence):
    """Check executable/projection references, not embedded original source values."""
    if isinstance(node,dict):
        for key,value in node.items():
            if key == 'evidence_id' and value not in evidence:
                raise ValueError('Orphan evidence reference: '+value)
            elif key == 'evidence_ids' and not set(value) <= set(evidence):
                raise ValueError('Orphan evidence references')
            elif key not in {'original_value','evidence_id','evidence_ids'}:
                validate_references(value,evidence)
    elif isinstance(node,list):
        for value in node:
            validate_references(value,evidence)


def validate_material(properties):
    model = properties.get('model')
    if model not in MODELS:
        raise ValueError('Unsupported construction material model: '+str(model))
    missing = sorted(k for k in MODELS[model] if properties.get(k) is None)
    if missing:
        raise ValueError('Missing source material physics: '+', '.join(missing))
    if model == 'SimpleGlazing' and properties.get('visible_transmittance') is None and properties.get('visible_transmittance_mode') != 'energyplus_autocalculate_from_shgc':
        raise ValueError('Missing visible transmittance or explicit engine autocalculation')
    if model == 'SimpleGlazing' and properties.get('visible_transmittance') is not None and properties.get('visible_transmittance_mode'):
        raise ValueError('Conflicting visible transmittance modes')
    for k,v in properties.items():
        if k in {'name','model','source_code_defaults'} or v is None:
            continue
        if k in CATEGORIES:
            if not isinstance(v,str) or not v:
                raise ValueError('Invalid material category: '+k)
        elif k == 'solar_diffusing':
            if not isinstance(v,bool):
                raise ValueError('Invalid source glazing flag')
        else:
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v < 0:
                raise ValueError('Invalid physical material value: '+k)
            if k in POSITIVE and v <= 0:
                raise ValueError('Nonpositive material value: '+k)
            if any(token in k for token in ('absorptance','emissivity','reflectance','transmittance','shgc','solar_heat_gain_coefficient','dirt_correction')) and v > 1:
                raise ValueError('Invalid physical fraction: '+k)


def validate_inventory(actual, expected):
    actual,expected = set(actual),set(expected)
    if expected-actual:
        raise ValueError('Eligible construction identities missing: '+str(sorted(expected-actual)[:5]))
    if actual-expected:
        raise ValueError('Export contains orphan construction identities: '+str(sorted(actual-expected)[:5]))


def validate_catalogue(payload, expected_ids):
    Draft202012Validator(load_json(ROOT/'schemas/construction-json-v1.schema.json')).validate(payload)
    actual = set(payload['assemblies']) | set(payload['packages']) | set(payload['enclosures'])
    validate_inventory(actual,expected_ids)
    validate_inventory(payload['inventory']['eligible_ids'],expected_ids)
    if len(payload['inventory']['eligible_ids']) != len(actual):
        raise ValueError('Duplicate eligible construction identity')
    if sum(len(payload[t]) for t in ('assemblies','packages','enclosures')) != len(actual):
        raise ValueError('Construction primary IDs collide')
    materials,evidence = payload['materials'],payload['evidence']
    known_hashes = {d['sha256'] for d in payload['source_files'].values()}
    known_hashes |= set(payload['input_sha256'].values())
    for identity,e in evidence.items():
        if identity != e['id']:
            raise ValueError('Evidence identity mismatch')
        hashes = e['source_file_sha256']
        hashes = list(hashes.values()) if isinstance(hashes,dict) else [hashes]
        if not hashes or not set(hashes) <= known_hashes:
            raise ValueError('Unregistered source evidence checksum: '+identity)
        original=e.get('original_value')
        if isinstance(original,dict) and not set(original.get('source_layer_evidence_ids',[])) <= set(evidence):
            raise ValueError('Orphan source-layer evidence dependency')
    for table in ('materials','assemblies','packages','enclosures'):
        validate_references(payload[table],evidence)
    for mid,m in materials.items():
        if mid != m['id']:
            raise ValueError('Material identity mismatch')
        validate_material(dict(m['properties'],model=m['model']))
        if set(m['property_evidence']) != set(m['properties']) or not set(m['property_evidence'].values()) <= set(evidence):
            raise ValueError('Material property evidence missing/orphan: '+mid)
    used_materials = set()
    for identity,a in payload['assemblies'].items():
        if identity != a['id'] or a['status'] != 'ready' or not a['layers']:
            raise ValueError('Unresolved assembly: '+identity)
        if a['role'].startswith('GroundContact') or a['role'] in {'FoundationWall','Slab','RimJoist','FloorOverFoundation'}:
            raise ValueError('Deferred ground assembly entered above-ground export')
        if [l['order'] for l in a['layers']] != list(range(len(a['layers']))):
            raise ValueError('Construction layer order changed')
        mids = [l['material_id'] for l in a['layers']]
        if not set(mids) <= set(materials):
            raise ValueError('Orphan construction material')
        used_materials.update(mids)
        models = {materials[m]['model'] for m in mids}
        if a['model'] == 'simple_glazing' and models != {'SimpleGlazing'}:
            raise ValueError('Simple glazing has incompatible layers')
        if a['model'] == 'detailed_glazing' and not ('StandardGlazing' in models and models <= {'StandardGlazing','Gas'}):
            raise ValueError('Detailed glazing has incompatible layers')
        if a['model'] == 'opaque_layers' and not models <= {'StandardOpaqueMaterial','MasslessOpaqueMaterial','AirGap'}:
            raise ValueError('Opaque assembly has incompatible layers')
        if not set(a['evidence_ids']) <= set(evidence) or not a['evidence_ids']:
            raise ValueError('Assembly evidence is missing')
        for binding in a['required_bindings']:
            if any(term in binding for term in ('missing','unknown','assembly_layers','performance')):
                raise ValueError('Unresolved source physics relabelled as consumer binding')
        for modifier in a.get('solar_modifiers',{}).values():
            if modifier['evidence_id'] not in evidence:
                raise ValueError('Solar modifier has orphan evidence')
        incident = a.get('solar_modifiers',{}).get('incident_solar_multiplier')
        if incident and (not 0 <= incident['value'] <= 1 or incident['model'] != 'constant'):
            raise ValueError('Unsupported source solar multiplier')
    if used_materials != set(materials):
        raise ValueError('Orphan exported material resources')
    from scripts.recover_construction_selectors import TARGET_SLOTS,DIRECT_SLOTS,GROUND_SLOTS,resolve_source_selector
    context_count=0
    source_packet={'records':payload['packages'],'elements':payload['assemblies'],
                   'climate_zone_sets':payload['climate_zone_sets']}
    for identity,p in payload['packages'].items():
        if identity != p['id'] or p['status'] != 'ready':
            raise ValueError('Unresolved package')
        if set(p['selectors']) != set(TARGET_SLOTS)|set(DIRECT_SLOTS) or set(p['deferred_selectors']) != set(GROUND_SLOTS):
            raise ValueError('Incomplete source selector census')
        supported=p['supported_climates']
        if len(supported)!=len(set(supported)) or not set(supported)<=CLIMATES or not set(p['unsupported_climates'])<=CLIMATES or set(supported)&set(p['unsupported_climates']):
            raise ValueError('Invalid supported source climate contexts')
        for slot,selector in p['selectors'].items():
            if selector['source_selector']!=slot or selector['role']!=dict(TARGET_SLOTS,**DIRECT_SLOTS)[slot]:
                raise ValueError('Source selector role/identity mismatch')
            if not set(selector['elements']) <= set(payload['assemblies']):
                raise ValueError('Orphan package selector')
            if selector['disposition'].startswith('resolved') and not selector['elements']:
                raise ValueError('Active package selector is missing')
            if selector['evidence_id'] not in evidence:
                raise ValueError('Missing selector provenance')
            if len(selector['elements'])!=len(set(selector['elements'])):
                raise ValueError('Duplicate source selector dependency')
            policy=selector.get('selection_policy')
            if selector['disposition']=='resolved_source_context' and not policy:
                raise ValueError('Missing source ordered-selection policy')
            if policy:
                order=policy['source_order']
                ordered_ids=[i for row in order for i in row['element_ids']]
                indices=[row['source_index'] for row in order]
                if not order or set(ordered_ids)!=set(selector['elements']) or indices!=sorted(set(indices)) or policy['default']!='source_first_match':
                    raise ValueError('Broken source selector order/dependencies')
                for row in order:
                    if not row['element_ids'] or any(payload['assemblies'][i]['climate_group']!=row['predicate']['climate_zone_set'] for i in row['element_ids']):
                        raise ValueError('Source selector climate predicate mismatch')
            elif selector['disposition']=='source_absent_at_this_scope' and selector['elements']:
                raise ValueError('Absent source selector contains dependencies')
        for slot,selector in p['deferred_selectors'].items():
            if selector['source_selector']!=slot or selector['disposition']!='deferred_ground_axis':
                raise ValueError('Invalid deferred ground selector')
        if not p['infiltration']['reference_variants']:
            raise ValueError('Missing package ACH reference')
        refs=p['infiltration']['reference_variants']
        if len({r['reference_id'] for r in refs})!=len(refs):
            raise ValueError('Duplicate package source reference variant')
        for climate in supported:
            for slot,selector in p['selectors'].items():
                if selector['elements']:
                    resolved=resolve_source_selector(source_packet,identity,slot,climate)
                    if not resolved['element_ids'] or not set(resolved['element_ids'])<=set(selector['elements']):
                        raise ValueError('Unresolved supported source selector')
            for ref in refs:
                if climate not in ref['climates']:
                    raise ValueError('Missing supported climate ACH reference')
                context_count+=1
    for identity,e in payload['enclosures'].items():
        if identity != e['id'] or e['status'] != 'ready' or not set(e['assembly_ids']) <= set(payload['assemblies']):
            raise ValueError('Unresolved/orphan enclosure')
    for primary in list(payload['packages'].values())+list(payload['enclosures'].values()):
        infil = primary['infiltration']
        variants = infil.get('reference_variants') or [infil]
        for variant in variants:
            if not variant['climates'] or not set(variant['climates'])<=CLIMATES:
                raise ValueError('Invalid ACH climate contexts')
            for ach in variant['climates'].values():
                if isinstance(ach['value'],bool) or not math.isfinite(ach['value']) or ach['value'] <= 0 or ach['unit'] != '1/s' or ach['evidence_id'] not in evidence:
                    raise ValueError('Invalid/missing natural ACH')
    return {'eligible_count':len(expected_ids),'ready_count':len(actual),'missing_ids':[],
            'active_blockers':[], 'assembly_count':len(payload['assemblies']),
            'package_count':len(payload['packages']),'enclosure_count':len(payload['enclosures']),
            'material_count':len(materials),'evidence_count':len(evidence),
            'validated_package_climate_reference_contexts':context_count}
