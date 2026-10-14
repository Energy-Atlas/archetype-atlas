"""Versioned hotel GuestRoom applicability delta; frozen source physics stays intact."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from scripts.common import ROOT,load_json
from scripts.definition_contract import canonical,stable_id
from scripts.construction_set_release import load_release,hydrate_context,OUTPUT as BASE
from scripts.construction_set_validation import validate_set,BatchValidationCache

POLICY=ROOT/'sources/hotel-guestroom-applicability-v1.json'
SCHEMA=ROOT/'schemas/construction-applicability-v1.schema.json'
OUTPUT=ROOT/'data/construction-releases/v2.1.0'
PATCH_TABLES={'contexts','component_configurations','selector_receipts','evidence'}


def checksum(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def missing_hotels(base):
    result={}
    for identity,p in base['construction_sets'].items():
        if p['scope']!='building' or p['source']['building_type'] not in {'SmallHotel','LargeHotel'}:continue
        contexts=[c for c in base['contexts'].values() if c['construction_set_id']==identity]
        flags=[any(a['when'].get('space_type')=='GuestRoom' for comp in base['component_configurations'][c['configuration_id']]['components'].values() for a in comp['assignments']) for c in contexts]
        if any(flags) and not all(flags):raise ValueError('Partially assigned hotel generic recipe requires explicit policy')
        if not any(flags):result[identity]=contexts
    return result


def validate_policy(base,policy):
    if policy.get('schema_version')!='1.0.0' or policy.get('kind')!='hotel_guestroom_applicability_policy' or policy.get('base_release')!='v2.0.0' or policy.get('space_type')!='GuestRoom':raise ValueError('Unsupported hotel applicability policy')
    missing=missing_hotels(base)
    if set(policy['entries'])!=set(missing):raise ValueError('Hotel policy census differs from missing generic definitions')
    geometry_path=ROOT/'data/construction-inputs/geometry-v1.json'
    if checksum(geometry_path)!=base['metadata']['input_sha256'][geometry_path.relative_to(ROOT).as_posix()]:raise ValueError('Frozen hotel geometry checksum mismatch')
    geometry=load_json(geometry_path)
    for identity,entry in policy['entries'].items():
        if set(entry)!={'mode','recipe_construction_id','source_space_type_instantiated'}:raise ValueError('Unexpected hotel policy fields')
        p=base['construction_sets'][identity];source=p['source']
        reference=next(r for r in geometry['commercial'] if r['template']==source['template'] and r['building_type']==source['building_type'])
        instantiated=any(s['standards_space_type']=='GuestRoom' for s in reference['spaces'])
        if type(entry['source_space_type_instantiated']) is not bool or instantiated!=entry['source_space_type_instantiated']:raise ValueError('Changed source hotel space inventory')
        candidates=[i for i,r in base['construction_sets'].items() if r['scope']=='space_type' and r['source']['space_type']=='GuestRoom' and r['source']['building_type']==source['building_type'] and r['source']['template']==source['template']]
        if candidates:
            if len(candidates)!=1 or entry['mode']!='attach_source_recipe' or entry['recipe_construction_id']!=candidates[0]:raise ValueError('Wrong hotel/template generic source recipe')
        elif entry['mode']!='inherit_existing_building_story_rules' or entry['recipe_construction_id'] is not None:raise ValueError('Hotel without native generic recipe must preserve inheritance')
    return missing


def build_overlay(base=None,policy=None):
    base=base or load_release();policy=policy or load_json(POLICY)
    missing=validate_policy(base,policy);policy_sha=checksum(POLICY)
    inputs={p.relative_to(ROOT).as_posix():checksum(p) for p in (POLICY,SCHEMA,Path(__file__),BASE/'manifest.json')}
    overlay={'schema_version':'1.0.0','kind':'construction_applicability_overlay','release':'v2.1.0',
        'base_release':'v2.0.0','base_manifest_sha256':checksum(BASE/'manifest.json'),'policy_sha256':policy_sha,
        'input_sha256':inputs,'patches':{t:{} for t in sorted(PATCH_TABLES)},
        'metadata_additions':{'input_sha256':inputs,'source_files':{
            'atlas-hotel-guestroom-applicability':{'path':POLICY.relative_to(ROOT).as_posix(),'sha256':policy_sha,'source_revision':'atlas-hotel-guestroom/1.0.0'},
            'atlas-hotel-guestroom-implementation':{'path':Path(__file__).relative_to(ROOT).as_posix(),'sha256':checksum(__file__),'source_revision':'atlas-hotel-guestroom/1.0.0'}}},
        'coverage':{'building_definitions':len(missing),'contexts':0,'attached_recipe_contexts':0,'inherited_contexts':0}}
    patches=overlay['patches']
    for identity,contexts in sorted(missing.items()):
        entry=policy['entries'][identity]
        proof={'source_project':'Atlas applicability policy','source_revision':'atlas-hotel-guestroom/1.0.0',
            'source_file_sha256':policy_sha,'source_locator':POLICY.relative_to(ROOT).as_posix()+'#/entries/'+identity,
            'original_value':{'construction_set_id':identity,'space_type':'GuestRoom',**entry},
            'original_unit':'categorical construction applicability',
            'transformation':'Attach same-template native GuestRoom recipe.' if entry['mode']=='attach_source_recipe' else 'Declare GuestRoom applicability through existing building/story defaults without inserting a masking space override.',
            'extraction_date':'2026-10-14',
            'interpretation_note':'Atlas-added applicability approved by the user. Preserve native specific variants, source scope inventory, physics and the single building infiltration reference.'}
        eid=stable_id('construction-evidence',proof);patches['evidence'][eid]=dict(proof,id=eid)
        extension={'schema_version':'1.0.0','origin':'atlas_added_applicability','space_type':'GuestRoom',
            'mode':entry['mode'],'source_space_type_instantiated':entry['source_space_type_instantiated'],'evidence_id':eid}
        for c in contexts:
            context=copy.deepcopy(c);config=copy.deepcopy(base['component_configurations'][c['configuration_id']])
            decisions=copy.deepcopy(base['selector_receipts'][c['selector_receipt_id']])
            context['source_evidence_ids'].append(eid)
            if entry['mode']=='attach_source_recipe':
                donors=[d for d in base['contexts'].values() if d['construction_set_id']==entry['recipe_construction_id'] and d['climate_zone']==c['climate_zone'] and d['reference_id']==c['reference_id']]
                if len(donors)!=1:raise ValueError('Missing/ambiguous matching hotel recipe context')
                donor=donors[0];donor_config=base['component_configurations'][donor['configuration_id']]
                for role,component in donor_config['components'].items():
                    if component['assignments']:
                        config['components'][role]['assignments'].extend(copy.deepcopy(component['assignments']))
                        config['components'][role]['disposition']='provided'
                config['source_definition_ids']=list(dict.fromkeys(config['source_definition_ids']+donor_config['source_definition_ids']))
                additions=copy.deepcopy(base['selector_receipts'][donor['selector_receipt_id']])
                for d in additions:d['atlas_added_applicability']=copy.deepcopy(extension)
                decisions.extend(additions)
                context['source_evidence_ids']=list(dict.fromkeys(context['source_evidence_ids']+donor['source_evidence_ids']))
                overlay['coverage']['attached_recipe_contexts']+=1
            else:
                for d in decisions:
                    if d['scope']['scope'] in {'building_default','story'}:d['atlas_added_applicability']=copy.deepcopy(extension)
                overlay['coverage']['inherited_contexts']+=1
            cid=stable_id('construction-configuration',config);sid=stable_id('construction-selection',decisions)
            if cid not in base['component_configurations']:patches['component_configurations'][cid]=config
            patches['selector_receipts'][sid]=decisions
            context.update(configuration_id=cid,selector_receipt_id=sid);patches['contexts'][c['id']]=context
            overlay['coverage']['contexts']+=1
    return overlay


def apply_overlay(base,overlay):
    if set(overlay.get('patches',{}))!=PATCH_TABLES:raise ValueError('Unexpected applicability patch tables')
    if overlay!=build_overlay(base):raise ValueError('Applicability overlay differs from approved deterministic policy')
    # Copy changed maps only; never mutate the frozen source dictionaries.
    current=dict(base,metadata=copy.deepcopy(base['metadata']))
    for table,patch in overlay['patches'].items():current[table]={**base[table],**copy.deepcopy(patch)}
    for key,values in overlay['metadata_additions'].items():current['metadata'][key].update(copy.deepcopy(values))
    return current


def validate_extensions(document):
    validator=Draft202012Validator(load_json(SCHEMA));count=0
    identity=document['source']['construction_set_id'];policy_entry=load_json(POLICY)['entries'].get(identity)
    for d in document['metadata']['selection_decisions']:
        ext=d.get('atlas_added_applicability')
        required=policy_entry is not None and (d['source_definition_id']==policy_entry['recipe_construction_id'] if policy_entry['mode']=='attach_source_recipe' else d['scope']['scope'] in {'building_default','story'})
        if bool(ext)!=required:raise ValueError('Missing or unexpected Atlas applicability declaration')
        if ext is None:continue
        validator.validate(ext);proof=document['evidence'].get(ext['evidence_id'])
        if proof is None or proof['source_project']!='Atlas applicability policy':raise ValueError('Missing Atlas applicability provenance')
        entry=proof['original_value']
        expected={'construction_set_id':identity,'space_type':'GuestRoom',**policy_entry}
        if entry!=expected or proof['source_file_sha256']!=checksum(POLICY) or proof['source_locator']!=POLICY.relative_to(ROOT).as_posix()+'#/entries/'+identity:raise ValueError('Applicability provenance differs from approved policy')
        if entry['construction_set_id']!=document['source']['construction_set_id'] or any(entry[k]!=ext[k] for k in ('space_type','mode','source_space_type_instantiated')):raise ValueError('Applicability receipt contradicts policy evidence')
        if ext['mode']=='attach_source_recipe':
            if d['source_definition_id']!=entry['recipe_construction_id'] or d['scope'].get('space_type')!='GuestRoom':raise ValueError('Wrong generic hotel recipe assignment')
        elif d['scope']['scope'] not in {'building_default','story'}:raise ValueError('Generic inheritance must preserve native fallback scopes')
        count+=1
    if policy_entry is not None and count==0:raise ValueError('Approved generic hotel applicability is missing')
    return count


def load_current_release(directory=OUTPUT):
    directory=Path(directory);manifest=load_json(directory/'manifest.json')
    names={'overlay.json','coverage.json','policy.json','construction-applicability-v1.schema.json','README.md'}
    if manifest.get('kind')!='construction_applicability_release' or manifest.get('release')!='v2.1.0' or set(manifest.get('files',{}))!=names or manifest.get('base_manifest_sha256')!=checksum(BASE/'manifest.json'):raise ValueError('Invalid applicability release manifest')
    for name,expected in manifest['files'].items():
        if checksum(directory/name)!=expected['sha256'] or (directory/name).stat().st_size!=expected['bytes']:raise ValueError('Applicability release checksum mismatch: '+name)
    overlay=load_json(directory/'overlay.json')
    return apply_overlay(load_release(),overlay)


def validate_overlay(base,overlay):
    current=apply_overlay(base,overlay);cache=BatchValidationCache();contexts=overlay['patches']['contexts']
    for i in contexts:
        p=hydrate_context(current,i,cache=cache);validate_extensions(p)
    for source_id in ('construction-93cb2afe2fe44c8e084b9b99','construction-0079ce7b163bdb1bd0154dbe'):
        i=next(i for i,c in base['contexts'].items() if c['construction_set_id']==source_id)
        p=hydrate_context(current,i,cache=cache);validate_extensions(p)
    if current['assemblies']!=base['assemblies'] or current['materials']!=base['materials']:raise ValueError('Applicability changed construction physics')
    return {**overlay['coverage'],'validation':'All affected contexts: schema, physics, references, provenance and Atlas extension; unchanged Medium Office/residential pilots'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    parser.add_argument('--context-id');parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.context_id:
        if not args.output:parser.error('--context-id requires --output')
        document=hydrate_context(load_current_release(),args.context_id);validate_extensions(document)
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(canonical(document));print('Current construction context exported');return
    base=load_release();overlay=build_overlay(base);receipt=validate_overlay(base,overlay)
    outputs={'overlay.json':canonical(overlay),'coverage.json':canonical(receipt),
        'policy.json':POLICY.read_bytes(),'construction-applicability-v1.schema.json':SCHEMA.read_bytes(),
        'README.md':b'# Construction applicability release v2.1.0\n\nChecksum-locked delta over immutable v2.0.0; consumer schema stays 2.0.0.\nSmallHotel 2019 attaches its native generic GuestRoom recipe. Older SmallHotel\nsets explicitly declare generic GuestRoom inheritance through existing building/\nstory rules. All specific variants, physics and infiltration remain unchanged.\nAtlas-added applicability is marked on selector receipts with typed provenance.\nNo program, ground, system or BEMGen translator changes.\n\nLoad with scripts.construction_hotel_applicability.load_current_release(), then\nuse the existing hydrate_context(). The original v2.0.0 API stays unchanged.\nRun python -m scripts.construction_hotel_applicability --check to reproduce.\nThis delta requires the frozen v2.0.0 tables and their original license notices;\nit contains no copied material or assembly physics. Original Atlas work remains\nunlicensed by user choice. No production publication is part of this task.\n'}
    outputs['manifest.json']=canonical({'schema_version':'1.0.0','kind':'construction_applicability_release','release':'v2.1.0',
        'base_release':'v2.0.0','base_manifest_sha256':overlay['base_manifest_sha256'],'consumer_schema':'2.0.0',
        'input_sha256':overlay['input_sha256'],'coverage':receipt,
        'files':{k:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for k,v in outputs.items()}})
    for name,value in outputs.items():
        path=OUTPUT/name
        if args.check:
            if not path.exists() or path.read_bytes()!=value:raise ValueError('Applicability release bytes differ: '+name)
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
