"""Validate and freeze normalized construction v2; no site/native/program build."""
import argparse
import copy
import hashlib
from pathlib import Path
from jsonschema import Draft202012Validator
from scripts.common import ROOT,load_json
from scripts.definition_contract import stable_id
from scripts.construction_set_export import (LIBRARY,export_set,input_hashes,build_index,
    encoded,dependency_closure,assembly_rule,SLOT_TYPES,digest)
from scripts.construction_set_validation import BatchValidationCache,validate_set,validate_resource_graph

OUTPUT=ROOT/'data/construction-releases/v2.0.0'
TABLES=('construction_sets','contexts','component_configurations','selector_receipts','assemblies','materials','evidence')
README='''# Construction JSON v2.0.0

Accepted unified above-ground construction sets, frozen on the feature branch.
Site integration and protected-main publication remain pending. Ground,
foundation-dependent assemblies, systems and the BEMGen translator are deferred.

Coverage: 224 source definitions, 4,798 supported climate/reference contexts,
4,868 assemblies, 858 materials and 8,014 evidence records. The source-identity
denominator is 5,092 (224 definitions plus 4,868 assemblies), all ready.
Of the assemblies, 3,429 participate in supported prototype selections;
1,439 additional source-table recipes have complete physics and provenance but
no recovered prototype mapping. They are retained separately, without invented
applicability. Unsupported source climates remain unsupported.

## Files

catalogue.json contains source definitions, contexts and common metadata.
component_configurations.json and selector_receipts.json contain interned
assignment configurations and source selections. assemblies.json, materials.json
and evidence.json contain shared resources. Together these files satisfy the
reconstructed-catalogue schema in schemas/construction-catalogue-v2.schema.json.
The raw catalogue.json header alone is not a self-contained catalogue.

index.json supports source/climate/reference selection. completeness.json records
coverage and validation. manifest.json locks input and output SHA-256 hashes and
byte counts. examples/ contains complete selected Medium Office and residential
documents matching schemas/construction-json-v2.schema.json.

## Use and reproduction

From the repository root, load the frozen tables and verify every file checksum:

    from scripts.construction_set_release import load_release, hydrate_context
    release = load_release()
    document = hydrate_context(release, context_id)

The CLI exports a standalone document from frozen v2 tables only:

    python -m scripts.construction_set_release --context-id ID --output selected.json

Optional --variant source-definition-id/selector=assembly-id selects a retained
source alternative for its supported context. Invalid contexts or ambiguous
consumer matching must fail explicitly; BEMGen supplies actual geometry.

To rebuild or compare exact UTF-8/LF release bytes, using locked v1 inputs:

    python -m scripts.construction_set_release
    python -m scripts.construction_set_release --check

Both commands validate every context and selector alternative; they do not run
native source recovery, program generation, site builds or CI. Schema, physical,
reference, provenance, source-equality and hydration checks cover all resources.
V1 assemblies/materials and fixed ACH are unchanged. Preserve LICENSE and all
sources/licenses notices. Original Atlas work remains unlicensed by user choice.
'''


def merge_unique(table,identity,value):
    if identity in table:
        if table[identity]!=value:raise ValueError('Construction identity collision: '+identity)
        return
    table[identity]=copy.deepcopy(value)


class ReleaseBuilder:
    def __init__(self):
        self.data={'schema_version':'2.0.0','kind':'construction_set_catalogue',
                   **{k:{} for k in TABLES},'metadata':None}

    def add(self,document):
        p=document;identity=p['source']['construction_set_id']
        source=copy.deepcopy(p['source'])
        proof_ids=[e['id'] for e in source.pop('evidence')]
        source.pop('climate');source.pop('reference_variant_id')
        profile={'id':identity,'name':p['name'],'scope':p['scope'],'source':source}
        merge_unique(self.data['construction_sets'],identity,profile)
        configuration={'components':p['components'],'source_definition_ids':p['metadata']['source_definition_ids']}
        cid=stable_id('construction-configuration',configuration)
        merge_unique(self.data['component_configurations'],cid,configuration)
        decisions=p['metadata']['selection_decisions'];sid=stable_id('construction-selection',decisions)
        merge_unique(self.data['selector_receipts'],sid,decisions)
        context={'id':p['id'],'construction_set_id':identity,'climate_zone':p['source']['climate']['value'],
            'reference_id':p['source']['reference_variant_id'],'configuration_id':cid,
            'selector_receipt_id':sid,'source_evidence_ids':proof_ids,'infiltration':p['infiltration']}
        merge_unique(self.data['contexts'],p['id'],context)
        metadata={k:v for k,v in p['metadata'].items() if k not in {'source_definition_ids','selection_decisions','variant_selections'}}
        if p['metadata']['variant_selections']:raise ValueError('Freeze contexts must retain source defaults, not explicit overrides')
        if self.data['metadata'] is None:self.data['metadata']=copy.deepcopy(metadata)
        elif self.data['metadata']!=metadata:raise ValueError('Inconsistent freeze metadata')
        for table in ('assemblies','materials','evidence'):
            for key,value in p[table].items():merge_unique(self.data[table],key,value)

    def finish(self):
        return {k:dict(sorted(v.items())) if k in TABLES else v for k,v in self.data.items()}


def hydrate_context(release,context_id,variant_selections=None,*,cache=None):
    """Assemble a selected standalone set using frozen v2 tables only."""
    if context_id not in release['contexts']:raise ValueError('Unsupported frozen context')
    context=release['contexts'][context_id];profile=release['construction_sets'][context['construction_set_id']]
    config=release['component_configurations'][context['configuration_id']]
    components=copy.deepcopy(config['components'])
    decisions=copy.deepcopy(release['selector_receipts'][context['selector_receipt_id']])
    choices=variant_selections or {};used=set()
    for decision in decisions:
        key=decision['source_definition_id']+'/'+decision['source_selector']
        if key not in choices:continue
        aid=choices[key]
        if aid not in decision['candidate_element_ids']:raise ValueError('Unsupported frozen source alternative')
        component=SLOT_TYPES[decision['source_selector']]
        matching=[r for r in components[component]['assignments'] if r['source_definition_id']==decision['source_definition_id'] and r['source_selector']==decision['source_selector'] and r['when']==decision['scope']]
        if not matching:raise ValueError('Missing source selector assignment')
        replacement=assembly_rule(release,aid,decision['source_definition_id'],decision['scope'],decision['source_selector'])
        assignments=[];inserted=False
        for rule in components[component]['assignments']:
            if rule in matching:
                if not inserted:assignments.append(replacement);inserted=True
            else:assignments.append(rule)
        components[component]['assignments']=assignments
        decision['resolved_climate_selection']['element_ids']=[aid]
        if decision['resolved_climate_selection']['property_climate_group'] is not None:
            decision['resolved_climate_selection']['selection_rule']='explicit_source_variant_id'
        used.add(key)
    if used!=set(choices):raise ValueError('Unsupported frozen source selector key')
    source=copy.deepcopy(profile['source'])
    source.update(climate={'status':'exact','value':context['climate_zone']},
                  reference_variant_id=context['reference_id'],
                  evidence=[copy.deepcopy(release['evidence'][i]) for i in context['source_evidence_ids']])
    infiltration=copy.deepcopy(context['infiltration'])
    assemblies,materials,evidence=dependency_closure(release,components,source,infiltration,decisions)
    metadata=copy.deepcopy(release['metadata'])
    metadata.pop('source_table_only_assembly_ids',None)
    metadata.update(source_definition_ids=copy.deepcopy(config['source_definition_ids']),selection_decisions=decisions,variant_selections=choices)
    p={'schema_version':'2.0.0','kind':'construction_set','export_mode':'source_ready',
        'id':context_id,'name':profile['name'],'scope':profile['scope'],'source':source,
        'components':components,'infiltration':infiltration,'assemblies':assemblies,
        'materials':materials,'evidence':evidence,'metadata':metadata}
    validate_set(p,cache=cache)
    return p


def expected_contexts(catalogue):
    for identity,p in sorted(catalogue['packages'].items()):
        for climate in p['supported_climates']:
            for variant in p['infiltration']['reference_variants']:yield identity,climate,variant['reference_id']
    for identity,p in sorted(catalogue['enclosures'].items()):
        for climate in sorted(p['infiltration']['climates']):yield identity,climate,p['infiltration']['reference_id']


def reconcile(release,original):
    definitions=set(original['packages'])|set(original['enclosures'])
    if set(release['construction_sets'])!=definitions:raise ValueError('Missing/orphan construction definition')
    expected=set(expected_contexts(original))
    actual={(r['construction_set_id'],r['climate_zone'],r['reference_id']) for r in release['contexts'].values()}
    if actual!=expected or len(actual)!=len(release['contexts']):raise ValueError('Missing/orphan/duplicate construction context')
    if set(release['assemblies'])!=set(original['assemblies']):raise ValueError('Missing/orphan source assembly')
    for identity,assembly in original['assemblies'].items():
        expected_assembly=copy.deepcopy(assembly);expected_assembly.pop('required_bindings')
        if release['assemblies'][identity]!=expected_assembly:raise ValueError('Source assembly physics changed: '+identity)
    if release['materials']!=original['materials']:raise ValueError('Source materials changed')
    for identity,evidence in original['evidence'].items():
        if release['evidence'].get(identity)!=evidence:raise ValueError('Source provenance changed: '+identity)
    for context in release['contexts'].values():
        identity,climate,ref=context['construction_set_id'],context['climate_zone'],context['reference_id']
        if identity in original['packages']:
            variants=original['packages'][identity]['infiltration']['reference_variants']
            expected_ach=next(v['climates'][climate] for v in variants if v['reference_id']==ref)
        else:expected_ach=original['enclosures'][identity]['infiltration']['climates'][climate]
        if context['infiltration']['natural_ach']!=expected_ach:raise ValueError('Source fixed ACH changed')
    return {'definitions':len(definitions),'contexts':len(actual),'assemblies':len(release['assemblies']),
            'materials':len(release['materials']),'evidence':len(release['evidence']),
            'eligible_count':len(definitions)+len(original['assemblies']),
            'ready_count':len(definitions)+len(release['assemblies']),'missing_ids':[],'active_blockers':[]}


def build_release(progress=True):
    hashes=input_hashes();original=load_json(LIBRARY/'catalogue.json')
    cache=BatchValidationCache();builder=ReleaseBuilder();seen=set();variants_checked=set()
    for n,(identity,climate,reference) in enumerate(expected_contexts(original),1):
        p=export_set(original,identity,climate,reference,hashes=hashes,validation_cache=cache)
        builder.add(p);seen.update(p['assemblies'])
        # Every candidate is explicitly selectable in at least one supported
        # context. Do not count retained table rows as selectable variants.
        for d in p['metadata']['selection_decisions']:
            key=d['source_definition_id']+'/'+d['source_selector']
            for aid in d['candidate_element_ids']:
                token=(d['source_definition_id'],d['source_selector'],aid)
                if token in variants_checked:continue
                chosen=export_set(original,identity,climate,reference,{key:aid},hashes=hashes,validation_cache=cache)
                if not any(r['assembly_id']==aid for c in chosen['components'].values() for r in c['assignments']):raise ValueError('Source candidate was not assigned')
                variants_checked.add(token)
        if progress and n%250==0:print(f'Construction contexts validated: {n}/4798',flush=True)
    release=builder.finish()
    # The frozen source library also contains independent source table recipes
    # outside the prototype caller's selected climate groups. Retain their fully
    # recovered physics explicitly; never force them into a different context.
    unselected=set(original['assemblies'])-seen
    for identity in sorted(unselected):
        a=copy.deepcopy(original['assemblies'][identity]);a.pop('required_bindings')
        release['assemblies'][identity]=a
    release['materials']=copy.deepcopy(original['materials'])
    for identity,e in original['evidence'].items():merge_unique(release['evidence'],identity,e)
    release['metadata']['source_table_only_assembly_ids']=sorted(unselected)
    Draft202012Validator(load_json(ROOT/'schemas/construction-catalogue-v2.schema.json')).validate(release)
    receipt=reconcile(release,original)
    receipt.update(schema_version='2.0.0',selected_context_assembly_count=len(seen),
        source_table_only_assembly_ids=sorted(unselected),explicit_selector_variants_checked=len(variants_checked),
        component_configurations=len(release['component_configurations']),selector_receipts=len(release['selector_receipts']),
        validation_scope='All selected contexts and distinct resources: schema, physics, rules, references, provenance, source equality and hydration; no native/program/site/CI work')
    # Include table-only recipes in physical, layer, material and provenance checks.
    validate_resource_graph(release)
    for a in release['assemblies'].values():cache.check('assembly',a)
    for m in release['materials'].values():cache.check('material',m)
    for e in release['evidence'].values():cache.check('evidence',e)
    for n,identity in enumerate(sorted(release['contexts']),1):
        p=hydrate_context(release,identity,cache=cache)
        c=release['contexts'][identity]
        reference=export_set(original,c['construction_set_id'],c['climate_zone'],c['reference_id'],hashes=hashes,validation_cache=cache)
        if p!=reference:raise ValueError('Frozen hydration changed standalone context')
        if progress and n%1000==0:print(f'Context hydration equality verified: {n}/4798',flush=True)
    if input_hashes()!=hashes:raise ValueError('Inputs changed during construction validation')
    receipt['cached_distinct_schema_blocks']=len(cache.checked)
    return release,receipt


def load_release(directory=OUTPUT):
    directory=Path(directory);manifest=load_json(directory/'manifest.json')
    for path,entry in manifest['files'].items():
        content=(directory/path).read_bytes()
        if hashlib.sha256(content).hexdigest()!=entry['sha256'] or len(content)!=entry['bytes']:raise ValueError('Frozen release checksum mismatch: '+path)
    release=load_json(directory/'catalogue.json')
    for table in TABLES:
        if table not in release:release[table]=load_json(directory/(table+'.json'))
    return release


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true');parser.add_argument('--quiet',action='store_true')
    parser.add_argument('--context-id');parser.add_argument('--output',type=Path)
    parser.add_argument('--variant',action='append',default=[])
    args=parser.parse_args()
    if args.context_id:
        if not args.output:parser.error('--context-id requires --output')
        value=encoded(hydrate_context(load_release(),args.context_id,dict(v.split('=',1) for v in args.variant)))
        if args.check:
            if args.output.read_bytes()!=value:raise ValueError('Frozen context bytes differ')
        else:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(value)
        print('Frozen context export verified' if args.check else 'Frozen context exported');return
    release,receipt=build_release(progress=not args.quiet)
    header={k:v for k,v in release.items() if k not in TABLES or k in {'construction_sets','contexts'}}
    outputs={OUTPUT/'catalogue.json':encoded(header),OUTPUT/'index.json':encoded(build_index(load_json(LIBRARY/'catalogue.json'))),OUTPUT/'completeness.json':encoded(receipt)}
    for table in TABLES:
        if table not in header:outputs[OUTPUT/(table+'.json')]=encoded(dict(sorted(release[table].items())))
    for name,source_id,climate in [('medium-office','construction-93cb2afe2fe44c8e084b9b99','4A'),('residential','construction-0079ce7b163bdb1bd0154dbe','5A')]:
        context=next(i for i,c in release['contexts'].items() if c['construction_set_id']==source_id and c['climate_zone']==climate)
        outputs[OUTPUT/'examples'/(name+'.json')]=encoded(hydrate_context(release,context))
    for name in ('construction-json-v2','construction-catalogue-v2'):
        outputs[OUTPUT/'schemas'/(name+'.schema.json')]=(ROOT/'schemas'/(name+'.schema.json')).read_bytes()
    outputs[OUTPUT/'LICENSE']=(ROOT/'LICENSE').read_bytes()
    outputs[OUTPUT/'README.md']=README.encode('utf-8')
    for path in (LIBRARY/'sources/licenses').glob('*.txt'):outputs[OUTPUT/'sources/licenses'/path.name]=path.read_bytes()
    outputs[OUTPUT/'sources/construction-v2-source-lock.json']=(ROOT/'sources/construction-v2-source-lock.json').read_bytes()
    manifest={'schema_version':'2.0.0','kind':'construction_set_release','release':'v2.0.0',
        'design_acceptance':'User accepted both unified examples on 2026-10-14',
        'publication_status':'Frozen on feature branch; site integration and protected-main publication pending',
        'input_sha256':release['metadata']['input_sha256'],'coverage':receipt,
        'files':{p.relative_to(OUTPUT).as_posix():{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for p,b in outputs.items()}}
    outputs[OUTPUT/'manifest.json']=encoded(manifest)
    for path,value in outputs.items():
        if args.check:
            if not path.exists() or path.read_bytes()!=value:raise ValueError('Frozen v2 bytes differ: '+path.name)
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
    print(f"Construction v2: {receipt['ready_count']}/{receipt['eligible_count']} source identities; {receipt['contexts']} contexts; zero active blockers")


if __name__=='__main__':main()
