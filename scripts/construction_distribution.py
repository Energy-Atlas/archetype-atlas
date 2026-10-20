"""Current complete construction sets; partial source scopes remain evidence."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from scripts.common import ROOT,load_json
from scripts.definition_contract import canonical
from scripts.construction_hotel_applicability import load_current_release as load_source,OUTPUT as SOURCE
from scripts.construction_set_export import dependency_closure
from scripts.construction_set_release import hydrate_context

OUTPUT=ROOT/'data/construction-releases/v2.2.0'
FILES={'selection.json','source-evidence.json','README.txt'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rules(release,context):
    config=release['component_configurations'][context['configuration_id']]
    assignments={canonical({'component':role,'assignment':a}) for role,comp in config['components'].items() for a in comp['assignments']}
    # The approved applicability extension augments, rather than replaces, proof.
    receipts={canonical({k:v for k,v in d.items() if k!='atlas_added_applicability'}) for d in release['selector_receipts'][context['selector_receipt_id']]}
    return assignments,receipts


def build_distribution(source=None):
    source=source or load_source();profiles=source['construction_sets'];contexts=source['contexts']
    complete={i:p for i,p in profiles.items() if p['scope'] in {'building','whole_dwelling'}}
    retired={i:p for i,p in profiles.items() if p['scope']=='space_type'}
    if len(complete)!=177 or len(retired)!=47:raise ValueError('Changed complete/partial construction census requires review')
    selected={i:c for i,c in contexts.items() if c['construction_set_id'] in complete}
    parents=defaultdict(list)
    for c in selected.values():
        if complete[c['construction_set_id']]['scope']=='building':parents[c['reference_id'],c['climate_zone']].append(c)
    cached={i:rules(source,c) for i,c in contexts.items()};embedded={};unsupported={}
    for i,c in contexts.items():
        if c['construction_set_id'] not in retired:continue
        candidates=parents[c['reference_id'],c['climate_zone']]
        if not candidates:unsupported[i]=c;continue
        donor=cached[i]
        matches=[b['id'] for b in candidates if donor[0]<=cached[b['id']][0] and donor[1]<=cached[b['id']][1]]
        if not matches:raise ValueError('Source space rules/selector alternatives are not fully embedded: '+i)
        embedded[i]=sorted(matches)
    expected={(template+'/'+building,climate) for template in ('DOE Ref Pre-1980','DOE Ref 1980-2004') for building in ('MediumOffice','LargeOffice') for climate in ('0A','0B')}
    if len(unsupported)!=8 or {(c['reference_id'],c['climate_zone']) for c in unsupported.values()}!=expected or any(retired[c['construction_set_id']]['source']['space_type']!='Plenum' for c in unsupported.values()):
        raise ValueError('Unexpected unsupported space contexts require review')
    current=dict(source,construction_sets=complete,contexts=selected)
    parent_sets=defaultdict(set)
    for i,parents in embedded.items():
        parent_sets[contexts[i]['construction_set_id']].update(contexts[p]['construction_set_id'] for p in parents)
    selection={'schema_version':'1.0.0','kind':'complete_construction_distribution','release':'v2.2.0','source_release':'v2.1.0',
        'construction_set_ids':sorted(complete),'retired_space_type_ids':sorted(retired),'embedded_contexts':embedded,
        'embedded_parent_sets':{i:sorted(parents) for i,parents in sorted(parent_sets.items())},
        'source_evidence_context_ids':sorted(unsupported),
        'coverage':{'construction_sets':len(complete),'building_sets':136,'whole_dwelling_sets':41,'contexts':len(selected),
                    'retired_space_type_sets':len(retired),'embedded_space_contexts':len(embedded),'source_evidence_contexts':len(unsupported)}}
    configs={c['configuration_id']:source['component_configurations'][c['configuration_id']] for c in unsupported.values()}
    receipts={c['selector_receipt_id']:source['selector_receipts'][c['selector_receipt_id']] for c in unsupported.values()}
    components={'all':{'assignments':[a for cfg in configs.values() for comp in cfg['components'].values() for a in comp['assignments']]}}
    proofs={eid for c in unsupported.values() for eid in c['source_evidence_ids']}
    assemblies,materials,evidence=dependency_closure(source,components,{'evidence':[source['evidence'][i] for i in proofs]},
        [c['infiltration'] for c in unsupported.values()],[d for rows in receipts.values() for d in rows])
    archive={'schema_version':'1.0.0','kind':'construction_source_evidence','consumer_selectable':False,
        'reason':'Legacy office Plenum source recipes support 0A/0B lookups, but their corresponding building sets do not. Preserve evidence without extending building climate coverage.',
        'source_release':'v2.1.0','construction_sets':{i:retired[i] for i in sorted({c['construction_set_id'] for c in unsupported.values()})},
        'contexts':unsupported,'component_configurations':configs,'selector_receipts':receipts,
        'assemblies':assemblies,'materials':materials,'evidence':evidence,'metadata':source['metadata']}
    return current,selection,archive


def artifacts(source=None):
    _,selection,archive=build_distribution(source)
    outputs={'selection.json':canonical(selection),'source-evidence.json':canonical(archive),
        'README.txt':b'Construction distribution v2.2.0\n\n177 complete construction sets and 3,320 contexts, projected over immutable\nv2.1.0/v2.0.0. Consumer schema remains 2.0.0. All 47 partial space-type\nsets are retired from current selection/export; 1,470 source contexts have\nunchanged assignments and selector alternatives within building sets.\nEight legacy office plenum 0A/0B contexts remain nonselectable source evidence.\nOriginal source records and all earlier frozen releases are preserved.\nNo physics, infiltration, program, foundation, system or translator changes.\nUse scripts.construction_distribution.load_current_release() and the existing\nhydrate_context(); python -m scripts.construction_distribution --check reproduces\nthis distribution. Earlier release loaders remain historical APIs. Preserve\nupstream licenses from the base releases; original Atlas work is unlicensed.\n'}
    inputs={p.relative_to(ROOT).as_posix():sha(p) for p in (SOURCE/'manifest.json',Path(__file__))}
    outputs['manifest.json']=canonical({'schema_version':'1.0.0','kind':'construction_distribution_release','release':'v2.2.0',
        'consumer_schema':'2.0.0','source_release':'v2.1.0','input_sha256':inputs,'coverage':selection['coverage'],
        'files':{name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in outputs.items()}})
    return outputs


def load_current_release(directory=OUTPUT):
    directory=Path(directory);manifest=load_json(directory/'manifest.json')
    if manifest.get('kind')!='construction_distribution_release' or manifest.get('release')!='v2.2.0' or set(manifest.get('files',{}))!=FILES:raise ValueError('Invalid construction distribution manifest')
    source=load_source();expected=artifacts(source)
    for name,data in expected.items():
        if (directory/name).read_bytes()!=data:raise ValueError('Construction distribution checksum/reproducibility mismatch: '+name)
    return build_distribution(source)[0]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    parser.add_argument('--context-id');parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.context_id:
        if not args.output:parser.error('--context-id requires --output')
        current=load_current_release()
        if args.context_id not in current['contexts']:parser.error('Context is not a current complete construction set; consult frozen source evidence')
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(canonical(hydrate_context(current,args.context_id)));return
    outputs=artifacts()
    for name,data in outputs.items():
        path=OUTPUT/name
        if args.check:
            if not path.exists() or path.read_bytes()!=data:raise ValueError('Distribution bytes differ: '+name)
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    print(json.dumps(json.loads(outputs['manifest.json'])['coverage'],indent=2))


if __name__=='__main__':main()
