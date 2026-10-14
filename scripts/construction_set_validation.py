"""Focused validation of selected construction-set schema and dependency closure."""
import math
from functools import lru_cache
from jsonschema import Draft202012Validator,ValidationError
from scripts.common import ROOT,load_json
from scripts.construction_validation import validate_material,validate_references
from scripts.construction_set_geometry import geometry_rule

COMPONENT_TYPES=('ExteriorWall','ExteriorRoof','ExteriorFloor','ExteriorWindow',
    'ExteriorDoor','GlassDoor','OverheadDoor','Skylight','InteriorWall','InteriorFloor',
    'InteriorCeiling','InteriorDoor','InteriorWindow','InteriorPartition',
    'TubularDaylightDome','TubularDaylightDiffuser','SpaceShading','BuildingShading','SiteShading')
SOURCE_ROLES={k:{k} for k in COMPONENT_TYPES}
SOURCE_ROLES.update({'ExteriorRoof':{'ExteriorRoof','Roof'},'ExteriorFloor':{'ExteriorFloor','Floor'},
    'ExteriorWindow':{'ExteriorWindow','Window'},'ExteriorDoor':{'ExteriorDoor','Door'},
    'OverheadDoor':{'ExteriorDoor'},'InteriorFloor':{'InteriorFloor','OrdinaryInteriorFloor','Floor'},
    'InteriorCeiling':{'InteriorCeiling','Ceiling'},'InteriorDoor':{'InteriorDoor','Door'},
    'InteriorWindow':{'InteriorWindow','Window'}})


@lru_cache(maxsize=1)
def schema_validator():
    schema=load_json(ROOT/'schemas/construction-json-v2.schema.json')
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_set(payload):
    schema_validator().validate(payload)
    assemblies,materials,evidence=(payload[k] for k in ('assemblies','materials','evidence'))
    for table in ('source','components','infiltration','assemblies','metadata'):
        validate_references(payload[table],evidence)
    if payload['source']['construction_set_id'] not in payload['metadata']['source_definition_ids']:
        raise ValueError('Selected source definition is missing')
    known_hashes=set(payload['metadata']['input_sha256'].values())
    known_hashes|={d['sha256'] for d in payload['metadata']['source_files'].values()}
    for identity,e in evidence.items():
        if identity!=e['id']:raise ValueError('Evidence identity mismatch')
        hashes=e['source_file_sha256'];hashes=set(hashes.values()) if isinstance(hashes,dict) else {hashes}
        if not hashes<=known_hashes:raise ValueError('Unregistered evidence checksum')
        original=e['original_value']
        if isinstance(original,dict) and not set(original.get('source_layer_evidence_ids',[]))<=set(evidence):
            raise ValueError('Orphan source-layer evidence')
    for e in payload['source']['evidence']:
        if e!=evidence.get(e['id']):raise ValueError('Source evidence differs from resource')
    used_assemblies=set();rule_ids=set()
    for ctype,component in payload['components'].items():
        assignments=component['assignments']
        if bool(assignments)!=(component['disposition']=='provided'):raise ValueError('Component disposition contradicts assignments')
        for rule in assignments:
            if rule['id'] in rule_ids:raise ValueError('Duplicate construction assignment')
            rule_ids.add(rule['id']);aid=rule['assembly_id'];used_assemblies.add(aid)
            if aid not in assemblies:raise ValueError('Orphan construction assignment assembly')
            attic_override=(ctype=='InteriorFloor' and assemblies[aid]['role']=='ExteriorRoof'
                and rule['source_selector']=='interior_floors' and rule['when'].get('space_type')=='Attic'
                and assemblies[aid]['source_attributes'].get('standards_construction_type')=='Attic and Other')
            if assemblies[aid]['role'] not in SOURCE_ROLES[ctype] and not attic_override:raise ValueError('Assembly role contradicts component target')
            if rule['source_definition_id'] not in payload['metadata']['source_definition_ids']:raise ValueError('Unknown source definition')
            when=rule['when']
            if when['scope']=='space_type' and not when.get('space_type'):raise ValueError('Missing source space condition')
            if payload['scope']=='space_type' and when.get('space_type')!=payload['source']['space_type']:
                raise ValueError('Inconsistent selected source space type')
            if rule['geometry']!=geometry_rule(assemblies[aid]):raise ValueError('Changed source geometry convention')
            if not rule['evidence_ids']:raise ValueError('Missing assignment evidence')
    if used_assemblies!=set(assemblies):raise ValueError('Orphan exported assembly')
    used_materials=set()
    for identity,a in assemblies.items():
        if identity!=a['id'] or not a['layers'] or a['status']!='ready':raise ValueError('Unresolved assembly')
        if a['role'].startswith('GroundContact') or a['role'] in {'FoundationWall','Slab','RimJoist','FloorOverFoundation'}:raise ValueError('Out-of-scope construction physics')
        if [l['order'] for l in a['layers']]!=list(range(len(a['layers']))):raise ValueError('Changed construction layer order')
        mids=[l['material_id'] for l in a['layers']];used_materials.update(mids)
        if not set(mids)<=set(materials):raise ValueError('Orphan assembly material')
        models={materials[i]['model'] for i in mids}
        valid={'opaque_layers':models<={'StandardOpaqueMaterial','MasslessOpaqueMaterial','AirGap'},
               'simple_glazing':models=={'SimpleGlazing'},
               'detailed_glazing':'StandardGlazing' in models and models<={'StandardGlazing','Gas'}}
        if not valid.get(a['model']):raise ValueError('Incompatible assembly material model')
    if used_materials!=set(materials):raise ValueError('Orphan exported material')
    for identity,m in materials.items():
        if identity!=m['id']:raise ValueError('Material identity mismatch')
        validate_material(dict(m['properties'],model=m['model']))
        if set(m['property_evidence'])!=set(m['properties']) or not set(m['property_evidence'].values())<=set(evidence):raise ValueError('Missing material property evidence')
    ach=payload['infiltration']['natural_ach']
    if not math.isfinite(ach['value']) or ach['value']<=0 or isinstance(ach['value'],bool):raise ValueError('Invalid natural ACH')
    if payload['source']['reference_variant_id']!=payload['infiltration']['reference_id']:raise ValueError('Inconsistent selected reference')
    return {'component_types':len(payload['components']),'assignments':len(rule_ids),
            'assemblies':len(assemblies),'materials':len(materials),'evidence':len(evidence)}
