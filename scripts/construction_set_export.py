"""Selected unified construction-set JSON; review examples only, no BEM translator."""
import argparse
import copy
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from scripts.common import ROOT,load_json
from scripts.definition_contract import stable_id
from scripts.construction_export import select_package
from scripts.construction_set_validation import COMPONENT_TYPES,validate_set
from scripts.construction_set_geometry import geometry_rule

LIBRARY=ROOT/'data/construction-releases/v1.0.0'
GEOMETRY=ROOT/'data/construction-inputs/geometry-v1.json'
OUTPUT=ROOT/'docs/examples/construction-json-v2'
SLOT_TYPES={'exterior_floor':'ExteriorFloor','exterior_wall':'ExteriorWall',
    'exterior_roof':'ExteriorRoof','exterior_fixed_window':'ExteriorWindow',
    'exterior_operable_window':'ExteriorWindow','exterior_door':'ExteriorDoor',
    'exterior_glass_door':'GlassDoor','exterior_overhead_door':'OverheadDoor',
    'exterior_skylight':'Skylight','interior_floors':'InteriorFloor',
    'interior_walls':'InteriorWall','interior_ceilings':'InteriorCeiling',
    'interior_doors':'InteriorDoor','interior_fixed_windows':'InteriorWindow',
    'interior_operable_windows':'InteriorWindow','interior_partitions':'InteriorPartition',
    'tubular_daylight_domes':'TubularDaylightDome','tubular_daylight_diffusers':'TubularDaylightDiffuser',
    'space_shading':'SpaceShading','building_shading':'BuildingShading','site_shading':'SiteShading'}
RES_TYPES={'Roof':'ExteriorRoof','ExteriorWall':'ExteriorWall','InteriorWall':'InteriorWall',
    'Ceiling':'InteriorCeiling','Floor':'ExteriorFloor','OrdinaryInteriorFloor':'InteriorFloor',
    'Door':'ExteriorDoor','Window':'ExteriorWindow','Skylight':'Skylight','InteriorPartition':'InteriorPartition'}


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def source_inputs():
    frozen={r['id']:r for r in load_json(ROOT/'data/definition-releases/v0.1.1/constructions.json')}
    return frozen,load_json(GEOMETRY)


def input_hashes():
    manifest=load_json(LIBRARY/'manifest.json')
    if digest(LIBRARY/'catalogue.json')!=manifest['files']['catalogue.json']['sha256']:
        raise ValueError('Frozen construction catalogue checksum mismatch')
    paths=[LIBRARY/'catalogue.json',LIBRARY/'manifest.json',GEOMETRY,
           ROOT/'data/definition-releases/v0.1.1/constructions.json',
           ROOT/'scripts/construction_set_export.py',ROOT/'scripts/construction_set_validation.py',
           ROOT/'scripts/construction_set_geometry.py',
           ROOT/'scripts/construction_set_release.py',ROOT/'schemas/construction-catalogue-v2.schema.json',
           ROOT/'schemas/construction-json-v2.schema.json',ROOT/'sources/construction-v2-source-lock.json',ROOT/'scripts/construction_export.py',
           ROOT/'scripts/construction_validation.py',ROOT/'scripts/energy_json_review.py',
           ROOT/'scripts/recover_construction_selectors.py',ROOT/'scripts/common.py',ROOT/'scripts/definition_contract.py']
    source_hashes=manifest['input_sha256']
    for path,checksum in source_hashes.items():
        if digest(ROOT/path)!=checksum:raise ValueError('Frozen v1 input changed: '+path)
    paths.extend(ROOT/path for path in source_hashes)
    return {p.relative_to(ROOT).as_posix():digest(p) for p in paths}




def empty_components():
    definitions=load_json(ROOT/'schemas/construction-json-v2.schema.json')['properties']['components']['properties']
    return {k:{'target':copy.deepcopy(definitions[k]['allOf'][1]['properties']['target']['const']),
               'disposition':'source_absent','assignments':[]} for k in COMPONENT_TYPES}


def assembly_rule(catalogue,aid,definition_id,when,slot=None):
    a=catalogue['assemblies'][aid]
    return {'id':stable_id('construction-assignment',{'definition_id':definition_id,'slot':slot,'assembly_id':aid,'when':when}),
        'assembly_id':aid,'source_definition_id':definition_id,'source_selector':slot,
        'when':when,'source_element_ids':a['source_surface_ids'],
        'geometry':geometry_rule(a),'evidence_ids':copy.deepcopy(a['evidence_ids'])}


def commercial_components(catalogue,primary,climate,reference,variant_selections=None):
    variant_selections=variant_selections or {};used_choices=set()
    selected=select_package(catalogue,primary['id'],climate,reference)
    initial={'scope':'space_type','space_type':primary['space_type']} if primary['space_type'] else {'scope':'building_default'}
    definitions=[(primary,initial)]
    _,geometry=source_inputs()
    template,building=selected['reference_id'].split('/',1)
    references=[r for r in geometry['commercial'] if (r['template'],r['building_type'])==(template,building)]
    if len(references)!=1:raise ValueError('Missing/ambiguous source reference geometry')
    # Exact source query records preserve source set and scope. Compatibility
    # lookups are evidence; they never override a building construction choice.
    if primary['space_type'] is None:
        for query in references[0]['queries']:
            source=query.get('source_set')
            query_scope=query['query']['context']
            if query_scope not in {'space_type','story_override'} or source is None:continue
            matches=[p for p in catalogue['packages'].values() if
                catalogue['evidence'][p['evidence_ids'][0]]['original_value']==source]
            if len(matches)!=1:raise ValueError('Missing/ambiguous source space construction definition')
            if query_scope=='space_type':when={'scope':'space_type','space_type':query['query']['space_type']}
            else:when={'scope':'story','source_story_id':query['query']['story']}
            definitions.append((matches[0],when))
    components=empty_components()
    decisions=[]
    for definition,scope_when in definitions:
        # Space overrides retain the chosen building reference ACH; only assembly
        # selection is resolved here, not a second enclosure infiltration load.
        from scripts.recover_construction_selectors import resolve_source_selector
        packet={'records':catalogue['packages'],'elements':catalogue['assemblies'],
                'climate_zone_sets':catalogue['climate_zone_sets']}
        for slot,selector in definition['selectors'].items():
            component=SLOT_TYPES[slot]
            if not selector['elements']:continue
            resolved=resolve_source_selector(packet,definition['id'],slot,climate)
            policy=selector.get('selection_policy')
            candidates=sorted({aid for row in policy['source_order'] if row['predicate']['climate_zone_set']==resolved['property_climate_group'] for aid in row['element_ids']}) if policy else list(selector['elements'])
            key=definition['id']+'/'+slot
            if key in variant_selections:
                resolved=resolve_source_selector(packet,definition['id'],slot,climate,variant_selections[key]);used_choices.add(key)
            when=copy.deepcopy(scope_when)
            if 'fixed_window' in slot:when['window_operation']='fixed'
            elif 'operable_window' in slot:when['window_operation']='operable'
            for aid in resolved['element_ids']:
                components[component]['assignments'].append(assembly_rule(catalogue,aid,definition['id'],when,slot))
            components[component]['disposition']='provided'
            decisions.append({'source_definition_id':definition['id'],'source_selector':slot,
                'scope':when,'resolved_climate_selection':resolved,'candidate_element_ids':candidates,'evidence_id':selector['evidence_id']})
    if used_choices!=set(variant_selections):raise ValueError('Unsupported source variant selector key')
    return components,selected,list(dict.fromkeys(p['id'] for p,_ in definitions)),decisions


def residential_components(catalogue,primary,context_evidence_id):
    components=empty_components()
    attrs=primary['source_context']['source_surface_attributes']
    for aid in primary['assembly_ids']:
        a=catalogue['assemblies'][aid];ctype=RES_TYPES[a['role']]
        when={'scope':'whole_dwelling'}
        adjacencies=[]
        for sid in a['source_surface_ids']:
            source=attrs.get(sid,{}).get('attributes',{})
            parent=source.get('attached_to_wall_idref') or source.get('attached_to_roof_idref')
            parent_source=attrs.get(parent,{}).get('attributes',{}) if parent else source
            interior=parent_source.get('interior_adjacent_to')
            exterior=parent_source.get('exterior_adjacent_to')
            if a['role'] in {'Roof','Skylight'} and exterior is None:exterior='outside'
            if interior is not None or exterior is not None:adjacencies.append((interior,exterior))
        unique=set(adjacencies)
        if len(unique)>1:raise ValueError('Mixed source adjacency in a residential recipe')
        if unique:
            interior,exterior=next(iter(unique))
            if interior is not None:when['interior_space_type']=interior
            if exterior is not None:when['exterior_space_type']=exterior
            if a['role']=='Window' and exterior not in {None,'outside'}:ctype='InteriorWindow'
            if a['role']=='Door' and exterior not in {None,'outside'}:ctype='InteriorDoor'
            if a['role']=='Floor' and exterior not in {None,'outside'}:ctype='InteriorFloor'
        if a['role']=='OrdinaryInteriorFloor':when['boundary_condition']='Adiabatic'
        components[ctype]['disposition']='provided'
        rule=assembly_rule(catalogue,aid,primary['id'],when)
        rule['evidence_ids'].append(context_evidence_id)
        components[ctype]['assignments'].append(rule)
    return components


def dependency_closure(catalogue,components,source,infiltration,decisions):
    ids={r['assembly_id'] for c in components.values() for r in c['assignments']}
    ids.update(aid for d in decisions for aid in d['candidate_element_ids'])
    assemblies={i:copy.deepcopy(catalogue['assemblies'][i]) for i in sorted(ids)}
    for a in assemblies.values():a.pop('required_bindings',None)
    mids={l['material_id'] for a in assemblies.values() for l in a['layers']}
    materials={i:copy.deepcopy(catalogue['materials'][i]) for i in sorted(mids)}
    evidence_ids={e['id'] for e in source['evidence']}
    def collect(node):
        if isinstance(node,dict):
            for key,value in node.items():
                if key=='evidence_id':evidence_ids.add(value)
                elif key=='evidence_ids':evidence_ids.update(value)
                elif key=='property_evidence':evidence_ids.update(value.values())
                elif key!='original_value':collect(value)
        elif isinstance(node,list):
            for value in node:collect(value)
    for node in [assemblies,materials,components,infiltration,decisions]:collect(node)
    pending=list(evidence_ids)
    while pending:
        e=catalogue['evidence'][pending.pop()];original=e.get('original_value')
        for ref in original.get('source_layer_evidence_ids',[]) if isinstance(original,dict) else []:
            if ref not in evidence_ids:evidence_ids.add(ref);pending.append(ref)
    evidence={i:copy.deepcopy(catalogue['evidence'][i]) for i in sorted(evidence_ids)}
    return assemblies,materials,evidence


def precedence_evidence(catalogue):
    import urllib.request
    descriptor=load_json(ROOT/'sources/construction-v2-source-lock.json')['sources']['openstudio-construction-inheritance']
    path=ROOT/descriptor['cache_path']
    if not path.exists():
        content=urllib.request.urlopen(descriptor['url'],timeout=30).read()
        if hashlib.sha256(content).hexdigest()!=descriptor['sha256']:raise ValueError('Source SDK documentation checksum mismatch')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    if digest(path)!=descriptor['sha256']:raise ValueError('Source SDK documentation checksum mismatch')
    catalogue=dict(catalogue,evidence=dict(catalogue['evidence']),source_files=dict(catalogue['source_files']))
    catalogue['source_files']['openstudio-construction-inheritance']=dict(descriptor)
    proof={'source_project':'OpenStudio SDK','source_revision':descriptor['source_revision'],
        'source_file_sha256':descriptor['sha256'],'source_locator':descriptor['url']+'#getDefaultConstructionWithSearchDistance',
        'original_value':['space','space_type','building_story','building','building_space_type'],
        'original_unit':'ordered categorical construction scopes','transformation':'Retain the source space-type, story and building hierarchy for recovered construction defaults.',
        'extraction_date':descriptor['extraction_date'],'interpretation_note':descriptor['interpretation_note']}
    eid=stable_id('construction-evidence',proof);catalogue['evidence'][eid]=dict(proof,id=eid)
    return catalogue,eid


def export_set(catalogue,construction_id,climate_zone,reference_id=None,variant_selections=None,*,hashes=None,validation_cache=None):
    catalogue,precedence_eid=precedence_evidence(catalogue)
    frozen,_=source_inputs()
    if construction_id not in catalogue['packages'] and construction_id not in catalogue['enclosures']:
        raise ValueError('Unknown construction-set source definition')
    row=frozen[construction_id]
    if construction_id in catalogue['packages']:
        primary=catalogue['packages'][construction_id]
        components,selection,definition_ids,decisions=commercial_components(catalogue,primary,climate_zone,reference_id,variant_selections)
        reference=selection['reference_id'];natural=selection['natural_ach']
        scope='space_type' if primary['space_type'] else 'building'
    elif construction_id in catalogue['enclosures']:
        if variant_selections:raise ValueError('Residential variants are component rules, not commercial selector overrides')
        primary=catalogue['enclosures'][construction_id]
        reference=primary['infiltration']['reference_id']
        if reference_id not in {None,reference}:raise ValueError('Unsupported residential reference')
        if climate_zone not in primary['infiltration']['climates']:raise ValueError('Unsupported source residential climate')
        natural=primary['infiltration']['climates'][climate_zone]
        # Preserve the actual context operands used for parent-wall adjacency.
        # The legacy context proof only points at those operands by name.
        context=primary['source_context']
        proof={'source_project':'atlas_source_derivation','source_revision':'construction-json/1.0.0',
            'source_file_sha256':digest(LIBRARY/'catalogue.json'),
            'source_locator':(LIBRARY/'catalogue.json').relative_to(ROOT).as_posix()+'#/enclosures/'+construction_id+'/source_context',
            'original_value':{'source_surface_attributes':context['source_surface_attributes'],
                              'source_context_provenance':context['context_provenance']},
            'original_unit':context['context_provenance']['original_unit'],
            'transformation':'Recover parent-wall/roof adjacency for openings; copy source-specific assignment and geometry conventions without changing physics.',
            'extraction_date':'2026-10-14','interpretation_note':'Original source categories and reference geometry remain evidence; BEMGen supplies consumer geometry.'}
        context_eid=stable_id('construction-evidence',proof)
        catalogue=dict(catalogue,evidence=dict(catalogue['evidence']))
        catalogue['evidence'][context_eid]=dict(proof,id=context_eid)
        components=residential_components(catalogue,primary,context_eid)
        definition_ids=[construction_id];decisions=[];scope='whole_dwelling'
    else:raise ValueError('Unknown construction-set source definition')
    eids=set(primary.get('evidence_ids',[]))|{natural['evidence_id'],precedence_eid}
    for did in definition_ids:
        if did in catalogue['packages']:eids.update(catalogue['packages'][did]['evidence_ids'])
    source={'construction_set_id':construction_id,'definition_release':'v0.1.1',
        'building_type':row['building_type'],'template':row['template'],'evidence_view':row['evidence_view'],
        'source_family':row['source_family'],'climate':{'status':'exact','value':climate_zone},
        'vintage':{'status':'exact','value':row.get('vintage') or row['template'],
                   'kind':'stock_vintage' if scope=='whole_dwelling' else 'source_template'},
        'space_type':primary.get('space_type'),'reference_variant_id':reference,
        'source_fixture_id':primary.get('source_fixture_id'),
        'evidence':[copy.deepcopy(catalogue['evidence'][i]) for i in sorted(eids)]}
    if scope=='whole_dwelling':source['source_climate_label']=primary['source_climate_label']
    infiltration={'method':primary['infiltration']['method'],'reference_id':reference,
                  'natural_ach':copy.deepcopy(natural)}
    assemblies,materials,evidence=dependency_closure(catalogue,components,source,infiltration,decisions)
    payload={'schema_version':'2.0.0','kind':'construction_set','export_mode':'source_ready',
        'id':stable_id('construction-set',{'construction_id':construction_id,'climate_zone':climate_zone,'reference_id':reference}),
        'name':row['name'],'scope':scope,'source':source,'components':components,
        'infiltration':infiltration,'assemblies':assemblies,'materials':materials,'evidence':evidence,
        'metadata':{'source_definition_ids':definition_ids,'selection_decisions':decisions,
            'assignment_policy':{'precedence':'space_type_then_story_then_building_default','evidence_id':precedence_eid,
                'variant_resolution':'explicit_assignment_id_or_unique_compatible_rule',
                'source_absent_override':'inherit_building_default','unmatched_or_ambiguous':'error'},
            'variant_selections':variant_selections or {},
            'input_sha256':hashes if hashes is not None else input_hashes(),'source_files':copy.deepcopy(catalogue['source_files']),
            'migration':{'source_contract':'construction-json/1.0.0','physics':'unchanged',
                'translator_owner':'BEMGen','review_status':'design_accepted'}}}
    validate_set(payload,cache=validation_cache)
    return payload


def build_index(catalogue):
    rows={}
    frozen,_=source_inputs()
    for identity,primary in sorted({**catalogue['packages'],**catalogue['enclosures']}.items()):
        row=frozen[identity]
        variants=primary['infiltration'].get('reference_variants') or [primary['infiltration']]
        climates=primary.get('supported_climates') or list(variants[0]['climates'])
        rows[identity]={'name':row['name'],'building_type':row['building_type'],'template':row['template'],
            'source_family':row['source_family'],'space_type':primary.get('space_type'),
            'scope':'whole_dwelling' if identity in catalogue['enclosures'] else ('space_type' if primary['space_type'] else 'building'),
            'climates':sorted(climates),'reference_variant_ids':[v['reference_id'] for v in variants]}
    return {'schema_version':'2.0.0','kind':'construction_set_index','construction_sets':rows,
            'source_catalogue_sha256':digest(LIBRARY/'catalogue.json')}


def encoded(value):return (json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--examples',action='store_true');parser.add_argument('--check',action='store_true')
    parser.add_argument('--construction-id');parser.add_argument('--climate-zone')
    parser.add_argument('--reference-id');parser.add_argument('--output',type=Path)
    parser.add_argument('--variant',action='append',default=[],help='source-definition-id/selector=assembly-id; explicit source alternative')
    args=parser.parse_args()
    manifest=load_json(LIBRARY/'manifest.json')
    if digest(LIBRARY/'catalogue.json')!=manifest['files']['catalogue.json']['sha256']:
        raise ValueError('Frozen construction catalogue checksum mismatch')
    catalogue=load_json(LIBRARY/'catalogue.json')
    if args.examples:
        medium=next(i for i,p in catalogue['packages'].items() if p['building_type']=='MediumOffice' and p['template']=='90.1-2019' and p['space_type'] is None)
        residential=next(i for i,p in catalogue['enclosures'].items() if p['source_fixture_id']=='residential_archetype-0157cd8578ba44bf8a77')
        outputs={OUTPUT/'medium-office.json':encoded(export_set(catalogue,medium,'4A')),
                 OUTPUT/'residential.json':encoded(export_set(catalogue,residential,'5A')),
                 OUTPUT/'index.json':encoded(build_index(catalogue))}
        review={'schema_version':'2.0.0','status':'design_accepted','steps_completed':[1,2,3],
            'input_sha256':input_hashes(),'schema_sha256':digest(ROOT/'schemas/construction-json-v2.schema.json'),
            'files':{p.name:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for p,b in outputs.items()}}
        outputs[OUTPUT/'review-manifest.json']=encoded(review)
    else:
        if not all([args.construction_id,args.climate_zone,args.output]):parser.error('Provide --examples or --construction-id, --climate-zone and --output')
        choices=dict(v.split('=',1) for v in args.variant)
        outputs={args.output:encoded(export_set(catalogue,args.construction_id,args.climate_zone,args.reference_id,choices))}
    for path,value in outputs.items():
        if args.check:
            if not path.exists() or path.read_bytes()!=value:raise ValueError('Nonreproducible construction-set export: '+path.name)
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
    print(f'Construction-set v2: {len(outputs)} review artifacts '+('verified' if args.check else 'written'))


if __name__=='__main__':main()
