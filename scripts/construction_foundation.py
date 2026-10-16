"""Shared embedded foundation contract; no separate suite or geometry matcher."""
import math
from functools import lru_cache
from jsonschema import Draft202012Validator
from scripts.common import ROOT,load_json

ROLES=('GroundFloor','FoundationWall','FloorOverFoundation','RimJoist')
NATIVE_MODELS={'FFactorGroundFloorConstruction','CFactorUndergroundWallConstruction','native_opaque_layers'}
TARGETS={
    'GroundFloor':{'surface_type':'Floor','boundary_conditions':['Ground','GroundFCfactorMethod','Foundation']},
    'FoundationWall':{'surface_type':'Wall','boundary_conditions':['Ground','GroundFCfactorMethod','Foundation','Surface','Adiabatic','Outdoors']},
    'FloorOverFoundation':{'surface_type':'Floor','boundary_conditions':['Surface','Adiabatic']},
    'RimJoist':{'surface_type':'Wall','boundary_conditions':['Outdoors','Surface','Adiabatic']}}


@lru_cache(maxsize=1)
def validator():
    return Draft202012Validator(load_json(ROOT/'schemas/construction-foundation-ground-v1.schema.json'))


def _references(value,key):
    if isinstance(value,dict):
        for k,v in value.items():
            if k==key:yield v
            else:yield from _references(v,key)
    elif isinstance(value,list):
        for v in value:yield from _references(v,key)


def validate_foundation_extension(document:dict)->None:
    ground=document['foundation_ground']
    errors=list(validator().iter_errors(ground))
    if errors:raise ValueError('Invalid foundation method/configuration: '+errors[0].message)
    methods=ground['methods'];settings=ground['model_parameters'];geometry=ground['required_geometry']
    assemblies=document['assemblies'];materials=document.get('materials',{})
    allowed_native={'id','name','model','status','f_W_m_K','c_W_m2_K','layers','layer_orientation','evidence_ids'}
    for assembly in assemblies.values():
        if assembly['model'] in NATIVE_MODELS:
            if set(assembly)-allowed_native:raise ValueError('Unexpected shadow parameter in native assembly')
            if assembly['model']=='native_opaque_layers' and not assembly.get('layers'):
                raise ValueError('Missing native assembly layers')
    for method in methods.values():
        if method['model_parameters_id'] not in settings:raise ValueError('Orphan ground model parameters')
        if not set(method['required_geometry'])<=set(geometry):raise ValueError('Orphan required ground geometry')
        for name in _references(method,'geometry_input'):
            if name not in geometry:raise ValueError('Orphan method geometry input')
        for mid in _references(method,'material_id'):
            if mid not in materials:raise ValueError('Orphan Kiva material reference')
        for mid in _references(method,'material_thickness_id'):
            if mid not in materials or materials[mid]['properties'].get('thickness_m') is None:raise ValueError('Orphan material thickness expression')
        for aid in _references(method,'assembly_thickness_id'):
            if aid not in assemblies:raise ValueError('Orphan assembly thickness expression')
        init=method['parameters'].get('initialization')
        if init and not math.isclose(sum(init[k] for k in ('outdoor','ground','indoor')),1.,abs_tol=1e-12):
            raise ValueError('Invalid initialization weights')
        expected={'FFactor':'FCBoundary','CFactor':'FCBoundary','LayeredGround':'LayeredGroundBoundary','Kiva':'Kiva'}[method['model']]
        if settings[method['model_parameters_id']]['model']!=expected:raise ValueError('Incompatible model-wide ground settings')
    for setting in settings.values():
        if setting['model']=='Kiva' and setting['soil_material_id'] not in materials:raise ValueError('Orphan Kiva soil material')
    used_methods=set()
    unified=document.get('kind')=='building_level_equivalent'
    no_contact=ground['configuration']['type']=='no_direct_ground_contact'
    for role,component in document['components'].items():
        if role not in ROLES:
            if unified and component.get('assignments'):raise ValueError('Unified ordinary component must retain simplified form')
            continue
        rules=component.get('assignments',[])
        if unified and component.get('assembly_id'):
            rules=[{'assembly_id':component['assembly_id'],'ground_method_id':component.get('ground_method_id'),'when':component.get('when',{})}]
        if unified and len(rules)>1 and not component.get('native_exception_reason'):
            raise ValueError('Native unified assignment exception requires a physical reason')
        if unified and len(rules)>1 and role not in {'GroundFloor','FoundationWall'}:
            raise ValueError('Unified ordinary foundation interface must be simplified')
        if component.get('disposition')=='provided' and not rules:raise ValueError('Provided foundation component has no recipe')
        if component.get('disposition')=='source_absent' and rules:raise ValueError('Absent foundation component has assignments')
        if no_contact and rules:raise ValueError('Source-supported no-contact configuration cannot acquire foundation recipes')
        for rule in rules:
            aid=rule['assembly_id']
            if aid not in assemblies:raise ValueError('Orphan foundation assembly')
            a=assemblies[aid];model=a['model'];method_id=rule.get('ground_method_id')
            if role in {'GroundFloor','FoundationWall'}:
                ordinary_wall=role=='FoundationWall' and rule.get('when',{}).get('boundary_condition') in {'Surface','Adiabatic','Outdoors'}
                if ordinary_wall:
                    if method_id or model!='native_opaque_layers':raise ValueError('Non-soil wall has invalid native method')
                else:
                    if method_id not in methods:raise ValueError('Missing native ground method')
                    used_methods.add(method_id)
                    kind=methods[method_id]['model']
                    expected={'FFactor':'FFactorGroundFloorConstruction','CFactor':'CFactorUndergroundWallConstruction','LayeredGround':'native_opaque_layers','Kiva':'native_opaque_layers'}[kind]
                    if model!=expected:raise ValueError('Ground method/assembly model mismatch')
            elif method_id:raise ValueError('Ordinary foundation interface cannot own a soil-transfer method')
            if model in {'FFactorGroundFloorConstruction','CFactorUndergroundWallConstruction'}:
                key='f_W_m_K' if model.startswith('F') else 'c_W_m2_K'
                if not isinstance(a.get(key),(float,int)) or not math.isfinite(a[key]) or a[key]<=0:
                    raise ValueError('Invalid authoritative ground factor')
                if 'kiva' in a or 'parameters' in a or 'layers' in a:raise ValueError('Unexpected shadow native physics')
            for mid in _references(a,'material_id'):
                if mid not in materials:raise ValueError('Orphan ground-layer material')
    if used_methods!=set(methods):raise ValueError('Unused native ground method in consumer export')
    used_settings={methods[m]['model_parameters_id'] for m in used_methods}
    if used_settings!=set(settings):raise ValueError('Unused model-wide ground settings')
    if no_contact and (not ground['configuration'].get('reason') or methods or geometry):
        raise ValueError('Source-supported absence needs a reason and empty ground execution inputs')
