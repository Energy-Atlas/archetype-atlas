"""Freeze the combined construction delivery; native/program/site work is opt-in elsewhere."""
import argparse
import copy
import hashlib
from pathlib import Path
from scripts.common import ROOT,load_json
from scripts.definition_contract import stable_id
from scripts.construction_set_export import encoded
from scripts.construction_foundation_export import session,compose_foundation_export,EXECUTION,AIRFLOW
from scripts.construction_foundation_recovery import sha

OUTPUT=ROOT/'data/construction-foundation-releases/v1.0.0'
EXAMPLES=ROOT/'docs/examples/construction-foundation-v1'
TABLES=('contexts','extensions','assemblies','unified_assemblies','materials','evidence')
SCHEMAS=('construction-json-v3.schema.json','construction-equivalent-v2.schema.json','construction-foundation-ground-v1.schema.json')
# Notices of the upstream sources this release uses; unrelated licences added later stay out.
NOTICES=('comstock','energyplus-26.2','openstudio-hpxml','openstudio-standards','resstock','weather')

README='''# Combined Construction Suite 1.0.0

Complete detailed construction JSON 3.0.0 and unified JSON 2.0.0 include native
foundation/ground physics alongside their existing above-ground definitions.
The shared mass contract remains 1.0.0. Historical releases are immutable.

Select the existing suite/climate/reference. GroundFloor, FoundationWall,
FloorOverFoundation and RimJoist use normal component/assignment and resource
structures. F/C factors live on assemblies; Kiva parameters live once on the
referenced method; material properties use material resources. No independent
foundation suite, matching system or compatibility object is shipped.

This normalized directory is internal delivery storage. Use export_pair to get
two complete standalone documents, each with its selected dependency closure.
Raw recovery inventories and detailed validation evidence are not copied into
consumer JSON. completeness.json reports the fixed 177-suite/3320-context gate,
source-supported absence and native unified exceptions separately.

Actual BEM geometry, foundation groups/hosts and method-specific weather/site
inputs remain necessary. A no-contact source unit cannot supply an invented
whole-building ground slab. Missing executable physics prevents publication.
Ordinary unified components retain their simplified representations; native
ground assignments are preserved only where homogenization is unjustified.

python -m scripts.construction_foundation_release --check
python -m scripts.construction_foundation_release --examples --check
python -m scripts.validate_construction_foundation --all

Use --context-id ID --representation detailed|unified --output PATH to export.
Native source recovery, program/schedule generation and site publication are
not run by these commands. BEMGen integration/simulation is a separate worker's
responsibility. Preserve LICENSE and notices/. Original Atlas work remains
unlicensed; upstream licenses do not grant MIT relicensing of Atlas originals.
'''


def intern(table,key,value):
    if key in table and table[key]!=value:raise ValueError('Foundation resource identity collision: '+key)
    table[key]=copy.deepcopy(value)


def artifacts(context_ids=None):
    s=session();ids=sorted(context_ids if context_ids is not None else s.source['contexts'])
    data={k:{} for k in TABLES};contact=0;absent=0;exceptions={};role_counts={}
    for cid in ids:
        e=copy.deepcopy(s.extension(cid));ctx=s.source['contexts'][cid];suite=ctx['construction_set_id']
        for row in e.pop('native_exceptions'):
            exceptions[(suite,row['role'])]={'suite_id':suite,**row}
        for key in ('assemblies','unified_assemblies','materials','evidence'):
            for k,v in e[key].items():intern(data[key],k,v)
            e[key]=sorted(e[key])
        eid=stable_id('construction-foundation-extension',e);intern(data['extensions'],eid,e)
        data['contexts'][cid]={'extension_id':eid}
        if e['foundation_ground']['configuration']['type']=='no_direct_ground_contact':absent+=1
        else:contact+=1
        for role,c in e['components'].items():role_counts[role]=role_counts.get(role,0)+(c['disposition']=='provided')
    complete=set(ids)==set(s.source['contexts'])
    report={'denominator':{'suites':177,'contexts':3320},'complete':complete,'contexts':len(ids),
        'suites':len({s.source['contexts'][i]['construction_set_id'] for i in ids}),
        'context_dispositions':{'executable_contact':contact,'source_supported_no_contact':absent,'missing_executable_physics':0},
        'provided_component_contexts':role_counts,'native_unified_exceptions':list(exceptions.values()),
        'source_evidence_context_ids':s.census['source_evidence_context_ids'],
        'source_evidence_archive':'data/construction-releases/v2.2.0/source-evidence.json',
        'interpretation_note':'Source-supported absence is complete; unsupported external geometry requests are separate. No native method is forced into equivalent layers.'}
    files={k+'.json':encoded(v) for k,v in data.items()}
    files['completeness.json']=encoded(report);files['README.md']=README.encode('utf-8')
    for name in SCHEMAS:files['schemas/'+name]=(ROOT/'schemas'/name).read_bytes()
    files['LICENSE']=(ROOT/'LICENSE').read_bytes()
    for name in NOTICES:files['notices/'+name+'.txt']=(ROOT/'sources/licenses'/(name+'.txt')).read_bytes()
    paths=[EXECUTION,AIRFLOW,ROOT/'data/construction-inputs/foundation-source-v1.json',
        ROOT/'data/construction-mass-releases/v1.0.0/manifest.json',
        ROOT/'data/construction-releases/v2.2.0/manifest.json',
        ROOT/'data/construction-equivalent-releases/v1.1.0/manifest.json',
        ROOT/'sources/foundation-engine-lock.json',
        ROOT/'sources/foundation-engine-runtime-lock.json',ROOT/'data/construction-inputs/foundation-smoke-v1.json',
        *[ROOT/'scripts'/name for name in ('construction_foundation_release.py','construction_foundation_export.py',
            'construction_foundation_profiles.py','construction_foundation.py','construction_foundation_schemas.py','validate_construction_foundation.py')],
        *[ROOT/'schemas'/name for name in SCHEMAS]]
    manifest={'schema_version':'1.0.0','kind':'combined_construction_release','release':'1.0.0',
        'consumer_schemas':{'detailed':'3.0.0','unified':'2.0.0','mass_accounting':'1.0.0'},
        'coverage':{k:report[k] for k in ('denominator','complete','contexts','suites','context_dispositions')},
        'input_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in paths},
        'files':{name:{'sha256':hashlib.sha256(value).hexdigest(),'bytes':len(value)} for name,value in sorted(files.items())}}
    files['manifest.json']=encoded(manifest);return files


def load_release(directory=OUTPUT,*,require_full=True):
    directory=Path(directory);m=load_json(directory/'manifest.json')
    if m.get('kind')!='combined_construction_release' or m.get('release')!='1.0.0':raise ValueError('Invalid combined construction release')
    if require_full and (not m['coverage']['complete'] or m['coverage']['contexts']!=3320 or m['coverage']['suites']!=177):raise ValueError('Refusing partial combined construction release')
    for name,row in m['files'].items():
        p=directory/name
        if not p.resolve().is_relative_to(directory.resolve()):raise ValueError('Combined release path escapes directory')
        if sha(p)!=row['sha256'] or p.stat().st_size!=row['bytes']:raise ValueError('Combined release checksum mismatch: '+name)
    for name,h in m['input_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError('Changed combined release input: '+name)
    data={k:load_json(directory/(k+'.json')) for k in TABLES}
    if {r['extension_id'] for r in data['contexts'].values()}!=set(data['extensions']):raise ValueError('Orphan combined context/extension')
    for eid,e in data['extensions'].items():
        if stable_id('construction-foundation-extension',e)!=eid:raise ValueError('Changed extension identity')
        for key in ('assemblies','unified_assemblies','materials','evidence'):
            if not set(e[key])<=set(data[key]):raise ValueError('Orphan combined resource')
    for key in ('assemblies','unified_assemblies','materials','evidence'):
        if {i for e in data['extensions'].values() for i in e[key]}!=set(data[key]):raise ValueError('Unused combined resource')
    data.update(manifest=m,completeness=load_json(directory/'completeness.json'));return data


def extension(release,context_id):
    e=copy.deepcopy(release['extensions'][release['contexts'][context_id]['extension_id']])
    for key in ('assemblies','unified_assemblies','materials','evidence'):e[key]={k:copy.deepcopy(release[key][k]) for k in e[key]}
    return e


def export_pair(context_id,*,release=None):
    r=release if release is not None else load_release();s=session()
    base=s.mass.export_pair(context_id,s.source,s.mass_release,index=s.index,cache=s.cache)
    e=extension(r,context_id)
    return tuple(compose_foundation_export(d,e,rep) for d,rep in zip(base,('detailed','unified')))


def pilot_contexts():
    s=session();result={'medium-office-2019-3B':'construction-set-beb5e983644344ce44d4a299',
        'warehouse-2019-3B':'construction-set-8d06e1ae4ed4c1c397f4ae12'}
    cases={'residential-slab':'Slab-on-Grade','residential-conditioned-basement':'Basement, Conditioned',
        'residential-unconditioned-basement':'Basement, Unconditioned','residential-vented-crawlspace':'Crawlspace, Vented',
        'residential-unvented-crawlspace':'Crawlspace, Unvented','residential-ambient':'Ambient','residential-above-apartment':'Above Apartment'}
    for name,typ in cases.items():
        sid=next(k for k,v in s.census['suites'].items() if v.get('effective_configuration')==typ)
        result[name]=next(c['id'] for c in s.source['contexts'].values() if c['construction_set_id']==sid)
    for name,building,template in [('small-data-centre-2019','SmallDataCenterLowITE','90.1-2019'),
        ('legacy-hospital-basement','Hospital','DOE Ref Pre-1980'),('tall-building-2019','TallBuilding','90.1-2019'),
        ('supertall-building-2019','SuperTallBuilding','90.1-2019')]:
        result[name]=next(c['id'] for c in s.source['contexts'].values() if c['climate_zone']=='3B' and
            s.source['construction_sets'][c['construction_set_id']]['source']['building_type']==building and
            s.source['construction_sets'][c['construction_set_id']]['source']['template']==template)
    return result


def example_artifacts(release=None):
    r=release if release is not None else load_release();files={};contexts=pilot_contexts()
    from scripts.validate_construction_foundation import validate_document
    for name,cid in contexts.items():
        for doc,rep in zip(export_pair(cid,release=r),('detailed','unified')):
            validate_document(doc,rep);files[name+'.'+rep+'.json']=encoded(doc)
    files['manifest.json']=encoded({'kind':'combined_construction_examples','release':'1.0.0','contexts':contexts,
        'files':{name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in sorted(files.items())}})
    return files


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--examples',action='store_true')
    p.add_argument('--context-id');p.add_argument('--representation',choices=['detailed','unified'],default='detailed');p.add_argument('--output',type=Path)
    args=p.parse_args()
    if args.context_id:
        if args.output is None:p.error('--context-id requires --output')
        args.output.write_bytes(encoded(export_pair(args.context_id)[args.representation=='unified']));return
    for name,data in artifacts().items():
        path=OUTPUT/name
        if args.check:
            if path.read_bytes()!=data:raise ValueError('Combined release reproduction mismatch: '+name)
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    r=load_release()
    if args.examples:
        for name,data in example_artifacts(r).items():
            path=EXAMPLES/name
            if args.check:
                if path.read_bytes()!=data:raise ValueError('Combined example reproduction mismatch: '+name)
            else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    print(r['manifest']['coverage'])


if __name__=='__main__':main()
