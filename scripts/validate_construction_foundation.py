"""Focused combined-construction schema, physics, ownership and source checks."""
import argparse
import math
from functools import lru_cache
from jsonschema import Draft202012Validator
from scripts.common import ROOT,load_json
from scripts.construction_foundation import validate_foundation_extension,NATIVE_MODELS
from scripts.construction_foundation_export import _all_refs
from scripts.construction_validation import validate_material


@lru_cache(maxsize=2)
def schema(representation):
    name='construction-json-v3.schema.json' if representation=='detailed' else 'construction-equivalent-v2.schema.json'
    return Draft202012Validator(load_json(ROOT/'schemas'/name))


def validate_document(document,representation):
    errors=list(schema(representation).iter_errors(document))
    if errors:raise ValueError('Combined schema: '+str(list(errors[0].path))+': '+errors[0].message[:300])
    validate_foundation_extension(document)
    native={k:a for k,a in document['assemblies'].items() if a['model'] in NATIVE_MODELS}
    mids=set(_all_refs(native,{'material_id'}))|set(_all_refs(document['foundation_ground'],{'material_id','material_thickness_id','soil_material_id'}))
    for mid in mids:
        m=document['materials'][mid];p=m['properties']
        if m['model']=='BulkMaterial':
            for key in ('conductivity_W_m_K','density_kg_m3','specific_heat_J_kg_K'):
                v=p.get(key)
                if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or v<=0:raise ValueError('Missing/invalid bulk soil physics')
        else:validate_material(dict(p,model=m['model']))
        if not set(m['property_evidence'].values())<=set(document['evidence']):raise ValueError('Orphan native material provenance')
    for a in native.values():
        if not set(a['evidence_ids'])<=set(document['evidence']):raise ValueError('Orphan native assembly provenance')
    if representation=='unified':
        for c in document['components'].values():
            rules=c.get('assignments',[])
            pairs={(r['assembly_id'],r.get('ground_method_id')) for r in rules}
            if len(pairs)!=len(rules):raise ValueError('Redundant native unified assignment; equal physics must be deduplicated')
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--all',action='store_true');args=p.parse_args()
    from scripts.construction_foundation_release import load_release,export_pair
    r=load_release()
    ids=sorted(r['contexts']) if args.all else [next(iter(r['contexts']))]
    for i,cid in enumerate(ids):
        for doc,rep in zip(export_pair(cid,release=r),('detailed','unified')):validate_document(doc,rep)
        if (i+1)%500==0:print('Validated construction pairs',i+1,'/',len(ids),flush=True)
    print('Validated',len(ids),'combined construction pairs')


if __name__=='__main__':main()
