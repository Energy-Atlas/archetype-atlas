"""Focused validation of selected construction-set schema and dependency closure."""
import math
import copy
import hashlib
import json
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


class BatchValidationCache:
    """Check each distinct immutable block once; check every context's graph/rules.

    Cache keys fingerprint content, not IDs, so a changed record is checked anew.
    The reduced context schema retains all root/scope/component conditions.
    Only the separately validated resource/registry records are factored out.
    """
    def __init__(self):
        full=schema_validator().schema
        context=copy.deepcopy(full)
        for table in ('assemblies','materials','evidence'):context['properties'][table]={'type':'object'}
        context['$defs']['source']['properties']['evidence']['items']={}
        for key in ('source_files','input_sha256'):
            context['$defs']['metadata']['properties'][key]={'type':'object'}
        self.context=Draft202012Validator(context)
        self.blocks={name:Draft202012Validator({'$defs':full['$defs'],'$ref':'#/$defs/'+name}) for name in ('assembly','material','evidence')}
        for key in ('source_files','input_sha256'):
            self.blocks[key]=Draft202012Validator({'$defs':full['$defs'],**full['$defs']['metadata']['properties'][key]})
        self.checked=set();self.hits=0;self.previous={}

    def check(self,name,value):
        identity=(name,value.get('id')) if name in {'assembly','material','evidence'} else (name,None)
        if identity in self.previous and value==self.previous[identity]:self.hits+=1;return
        encoded=json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()
        key=(name,hashlib.sha256(encoded).digest())
        if key in self.checked:self.hits+=1;return
        self.blocks[name].validate(value)
        self.checked.add(key)
        self.previous[identity]=copy.deepcopy(value)

    def validate_schema(self,payload):
        self.context.validate(payload)
        for key in ('source_files','input_sha256'):self.check(key,payload['metadata'][key])
        for table,kind in [('assemblies','assembly'),('materials','material'),('evidence','evidence')]:
            for value in payload[table].values():self.check(kind,value)
        for value in payload['source']['evidence']:self.check('evidence',value)


def validate_set(payload,cache=None):
    if cache is None:schema_validator().validate(payload)
    else:cache.validate_schema(payload)
    assemblies,materials,evidence=(payload[k] for k in ('assemblies','materials','evidence'))
    for table in ('source','components','infiltration','assemblies','metadata'):
        validate_references(payload[table],evidence)
    if payload['source']['construction_set_id'] not in payload['metadata']['source_definition_ids']:
        raise ValueError('Selected source definition is missing')
    validate_resource_graph(payload)
    for e in payload['source']['evidence']:
        if e!=evidence.get(e['id']):raise ValueError('Source evidence differs from resource')
    used_assemblies=set();rule_ids=set()
    for decision in payload['metadata']['selection_decisions']:
        candidates=decision['candidate_element_ids']
        if not candidates or not set(candidates)<=set(assemblies):raise ValueError('Orphan source alternative')
        if not set(decision['resolved_climate_selection']['element_ids'])<=set(candidates):raise ValueError('Selected source variant not among candidates')
        used_assemblies.update(candidates)
    choices=payload['metadata']['variant_selections']
    keys={d['source_definition_id']+'/'+d['source_selector'] for d in payload['metadata']['selection_decisions']}
    if not set(choices)<=keys:raise ValueError('Unknown explicit variant selector')
    for decision in payload['metadata']['selection_decisions']:
        key=decision['source_definition_id']+'/'+decision['source_selector']
        if key in choices and decision['resolved_climate_selection']['element_ids']!=[choices[key]]:
            raise ValueError('Explicit source variant selection not applied')
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
            if rule['source_selector'] is not None and not any(d['source_definition_id']==rule['source_definition_id'] and d['source_selector']==rule['source_selector'] and d['scope']==rule['when'] for d in payload['metadata']['selection_decisions']):
                raise ValueError('Construction assignment lacks source selector receipt')
            when=rule['when']
            if when['scope']=='space_type' and not when.get('space_type'):raise ValueError('Missing source space condition')
            if payload['scope']=='space_type' and when.get('space_type')!=payload['source']['space_type']:
                raise ValueError('Inconsistent selected source space type')
            if rule['geometry']!=geometry_rule(assemblies[aid]):raise ValueError('Changed source geometry convention')
            if not rule['evidence_ids']:raise ValueError('Missing assignment evidence')
    for decision in payload['metadata']['selection_decisions']:
        matching=[r['assembly_id'] for c in payload['components'].values() for r in c['assignments']
                  if r['source_definition_id']==decision['source_definition_id']
                  and r['source_selector']==decision['source_selector'] and r['when']==decision['scope']]
        if matching!=decision['resolved_climate_selection']['element_ids']:
            raise ValueError('Source selector receipt contradicts construction assignments')
    if used_assemblies!=set(assemblies):raise ValueError('Orphan exported assembly')
    ach=payload['infiltration']['natural_ach']
    if not math.isfinite(ach['value']) or ach['value']<=0 or isinstance(ach['value'],bool):raise ValueError('Invalid natural ACH')
    if payload['source']['reference_variant_id']!=payload['infiltration']['reference_id']:raise ValueError('Inconsistent selected reference')
    return {'component_types':len(payload['components']),'assignments':len(rule_ids),
            'assemblies':len(assemblies),'materials':len(materials),'evidence':len(evidence)}


def validate_resource_graph(payload):
    """Validate every shared physical resource, including unmapped source recipes."""
    assemblies,materials,evidence=(payload[k] for k in ('assemblies','materials','evidence'))
    for table in ('assemblies','materials'):validate_references(payload[table],evidence)
    known_hashes=set(payload['metadata']['input_sha256'].values())
    known_hashes|={d['sha256'] for d in payload['metadata']['source_files'].values()}
    for identity,e in evidence.items():
        if identity!=e['id']:raise ValueError('Evidence identity mismatch')
        hashes=e['source_file_sha256'];hashes=set(hashes.values()) if isinstance(hashes,dict) else {hashes}
        if not hashes<=known_hashes:raise ValueError('Unregistered evidence checksum')
        original=e['original_value']
        if isinstance(original,dict) and not set(original.get('source_layer_evidence_ids',[]))<=set(evidence):
            raise ValueError('Orphan source-layer evidence')
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
