"""Versioned full consumer schemas composed over immutable construction contracts."""
import argparse
import copy
from scripts.common import ROOT,load_json,dump_json
from scripts.construction_foundation import ROLES,TARGETS


def schemas():
    detailed=load_json(ROOT/'schemas/construction-json-v2.1.schema.json')
    unified=load_json(ROOT/'schemas/construction-equivalent-v1.2.schema.json')
    ground=load_json(ROOT/'schemas/construction-foundation-ground-v1.schema.json')
    def prefix(value):
        if isinstance(value,dict):return {k:('#/$defs/foundation_'+v.removeprefix('#/$defs/') if k=='$ref' and v.startswith('#/$defs/') else prefix(v)) for k,v in value.items()}
        if isinstance(value,list):return [prefix(v) for v in value]
        return value
    ground=prefix(ground)
    defs={'foundation_'+k:v for k,v in ground.pop('$defs').items()}
    ground.pop('$schema',None);defs['foundationGround']=ground
    native={'type':'object','additionalProperties':False,'required':['id','model','status','evidence_ids'],
        'properties':{'id':{'type':'string','minLength':1},'name':{'type':'string'},'status':{'const':'ready'},
            'model':{'enum':['FFactorGroundFloorConstruction','CFactorUndergroundWallConstruction','native_opaque_layers']},
            'f_W_m_K':{'type':'number','exclusiveMinimum':0},'c_W_m2_K':{'type':'number','exclusiveMinimum':0},
            'layers':copy.deepcopy(detailed['$defs']['assembly']['properties']['layers']),
            'layer_orientation':{'const':'exterior_to_interior'},'evidence_ids':{'type':'array','minItems':1,'items':{'type':'string'}}},
        'allOf':[
            {'if':{'properties':{'model':{'const':'native_opaque_layers'}}},'then':{'required':['layers','layer_orientation'],'not':{'anyOf':[{'required':['f_W_m_K']},{'required':['c_W_m2_K']}]}}},
            {'if':{'properties':{'model':{'const':'FFactorGroundFloorConstruction'}}},'then':{'required':['f_W_m_K'],'not':{'anyOf':[{'required':['c_W_m2_K']},{'required':['layers']}]}}},
            {'if':{'properties':{'model':{'const':'CFactorUndergroundWallConstruction'}}},'then':{'required':['c_W_m2_K'],'not':{'anyOf':[{'required':['f_W_m_K']},{'required':['layers']}]}}}]}
    material=copy.deepcopy(detailed['$defs']['material']);material['properties']['model']['enum'].append('BulkMaterial')
    when=copy.deepcopy(detailed['$defs']['when']);when['properties']['thermal_host']={'type':'string','minLength':1}
    when['properties']['boundary_condition']['enum']=['Outdoors','Surface','Adiabatic','Ground']
    assignment=copy.deepcopy(detailed['$defs']['assignment']);assignment['properties']['ground_method_id']={'type':'string','minLength':1}
    for doc,version in ((detailed,'3.0.0'),(unified,'2.0.0')):
        doc['properties']['schema_version']={'const':version}
        doc['properties']['scope']={'enum':['building','whole_dwelling']}
        doc['properties']['foundation_ground']={'$ref':'#/$defs/foundationGround'}
        doc['required'].append('foundation_ground')
        doc['$defs'].update(copy.deepcopy(defs));doc['$defs']['nativeAssembly']=copy.deepcopy(native)
        doc['$defs']['assembly']={'oneOf':[doc['$defs']['assembly'],{'$ref':'#/$defs/nativeAssembly'}]}
        doc['$defs']['material']=copy.deepcopy(material)
        doc['$defs']['when']=copy.deepcopy(when);doc['$defs']['assignment']=copy.deepcopy(assignment)
        if doc is unified:
            for k in ('evidence','area','geometry'):doc['$defs'][k]=copy.deepcopy(detailed['$defs'][k])
            doc['properties']['materials']={'type':'object','additionalProperties':{'$ref':'#/$defs/material'}}
            doc['properties']['evidence']={'type':'object','additionalProperties':{'$ref':'#/$defs/evidence'}}
            doc['required'].extend(['materials','evidence'])
            cp=doc['properties']['components']
            cp['properties']={k:copy.deepcopy(cp['additionalProperties']) for k in cp['propertyNames']['enum']}
            cp['propertyNames']['enum'].extend(ROLES)
            cp['required']=[]
            cp['additionalProperties']=False
        for role in ROLES:
            if doc is detailed:
                shape={'allOf':[{'$ref':'#/$defs/component'},{'properties':{'target':{'const':TARGETS[role]}}}]}
            else:
                absent={'type':'object','additionalProperties':False,'required':['status','assembly_id','reason'],
                    'properties':{'status':{'const':'not_applicable'},'assembly_id':{'type':'null'},'reason':{'type':'string'}}}
                single={'type':'object','additionalProperties':False,'required':['status','assembly_id','when'],
                    'properties':{'status':{'const':'ready'},'assembly_id':{'type':'string'},'when':{'$ref':'#/$defs/when'},'ground_method_id':{'type':'string'}}}
                multi={'type':'object','additionalProperties':False,'required':['status','assembly_id','assignments','native_exception_reason'],
                    'properties':{'status':{'const':'ready'},'assembly_id':{'type':'null'},'assignments':{'type':'array','minItems':2,'items':{'$ref':'#/$defs/assignment'}},'native_exception_reason':{'type':'string','minLength':1}}}
                shape={'oneOf':[absent,single,multi]} if role in {'GroundFloor','FoundationWall'} else {'$ref':'#/$defs/component'}
            doc['properties']['components']['properties'][role]=shape
            doc['properties']['components']['required'].append(role)
    return {'construction-json-v3.schema.json':detailed,'construction-equivalent-v2.schema.json':unified}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args()
    for name,data in schemas().items():
        path=ROOT/'schemas'/name
        if args.check:
            if load_json(path)!=data:raise ValueError('Consumer schema reproduction mismatch: '+name)
        else:dump_json(path,data)


if __name__=='__main__':main()
