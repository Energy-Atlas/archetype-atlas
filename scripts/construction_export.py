"""Independent above-ground construction consumer export; no program/site build."""
import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path

from scripts.common import ROOT, load_json, dump_json
from scripts.definition_contract import canonical, stable_id
from scripts.construction_validation import validate_material, validate_catalogue

DATE='2026-10-14'
BASE=ROOT/'data/definition-releases/v0.1.1'
COMMERCIAL=ROOT/'data/construction-inputs/selector-closure-v1.json'
RESIDENTIAL=ROOT/'data/construction-inputs/residential-assemblies-v1.json'
ACH=ROOT/'data/construction-inputs/fixed-ach-v1.json'
OUTPUT=ROOT/'data/construction-releases/v1.0.0'
LABELS={'0A','0B','1A','1B','2A','2B','3A','3B','3C','4A','4B','4C','5A','5B','5C','6A','6B','7A','7B','8A','8B'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def climate_matches(group,climate):
    if climate not in LABELS:
        raise ValueError('Unsupported full climate label: '+climate)
    if group is None:
        return True
    label=group.removeprefix('ClimateZone ')
    if re.fullmatch(r'[0-8]',label):
        return label==climate[0]
    if label in LABELS:
        return label==climate
    raise ValueError('Unsupported source climate group: '+str(group))


def opaque_metrics(properties):
    resistance=0;capacity=0;massive=False
    for p in properties:
        if p['model'] in {'MasslessOpaqueMaterial','AirGap'}:
            resistance+=p['resistance_m2_K_W']
        elif p['model']=='StandardOpaqueMaterial':
            resistance+=p['thickness_m']/p['conductivity_W_m_K']
            capacity+=p['thickness_m']*p['density_kg_m3']*p['specific_heat_J_kg_K'];massive=True
        else:
            raise ValueError('Opaque metrics received glazing')
    if resistance<=0:
        raise ValueError('Nonpositive assembly resistance')
    result={'layer_resistance_m2_K_W':resistance,'layer_conductance_W_m2_K':1/resistance}
    if massive:
        result['areal_heat_capacity_J_m2_K']=capacity
    return result


def physical_key(assembly,materials):
    return canonical({'model':assembly.get('model'),
        'layers':[{k:v for k,v in materials[l['material_id']].items() if k in {'model','properties'}} for l in assembly['layers']],
        'applicability':assembly.get('applicability',{}),'solar_modifiers':assembly.get('solar_modifiers',{})})


def resolve_selector(selector,assemblies,materials,climate):
    candidates=[i for i in selector['elements'] if climate_matches(assemblies[i]['climate_group'],climate)]
    if not candidates:
        raise ValueError('Unsupported source selector/climate context')
    ordered=selector.get('source_default_order')
    if ordered:
        matches=[i for i in ordered if i in candidates]
        if set(matches)!=set(candidates):
            raise ValueError('Incomplete source selector order')
        selected=matches[0]
    else:
        if len({physical_key(assemblies[i],materials) for i in candidates})!=1:
            raise ValueError('Ambiguous physical source selector')
        selected=sorted(candidates)[0]
    return {'selected_id':selected,'source_candidate_ids':candidates,
            'selection_policy':'source_first_match' if ordered else 'physically_equivalent_candidates'}


def verify_inputs(packet):
    for path,digest in packet.get('input_sha256',{}).items():
        if sha(ROOT/path)!=digest:
            raise ValueError('Stale construction source recovery: '+path)


class Resources:
    def __init__(self,proofs=None):
        self.evidence={};self.materials={};self.proofs=proofs or {}

    def proof(self,raw):
        source_identity=None
        if set(raw)=={'evidence_id'}:
            source_identity=raw['evidence_id']
            if source_identity in self.evidence:
                return source_identity
            raw=self.proofs[source_identity]
        e=copy.deepcopy(raw)
        e.pop('id',None)
        e['source_file_sha256']=e.pop('source_sha256',e.get('source_file_sha256'))
        e.setdefault('source_project','OpenStudio Standards' if e.get('source_revision')=='c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907' else 'pinned_source')
        if not e.get('source_file_sha256') or not e.get('source_locator'):
            raise ValueError('Incomplete source proof')
        identity=source_identity or stable_id('construction-evidence',e)
        self.evidence[identity]=dict(e,id=identity)
        if isinstance(e.get('original_value'),dict):
            for reference in e['original_value'].get('source_layer_evidence_ids',[]):
                self.proof({'evidence_id':reference})
        return identity

    def material(self,properties,proof,field_proofs=None):
        p=copy.deepcopy(properties)
        validate_material(p)
        model=p.pop('model');name=p.pop('name',model);p.pop('source_code_defaults',None)
        p={k:v for k,v in p.items() if v is not None}
        eid=self.proof(proof)
        material={'name':name,'model':model,'properties':p,
                  'property_evidence':{k:self.proof(field_proofs[k]) if field_proofs and k in field_proofs else eid for k in p}}
        identity=stable_id('construction-material',material)
        self.materials[identity]=dict(material,id=identity)
        return identity


def assembly(row,resources):
    if row.get('unresolved'):
        raise ValueError('Active source assembly gap: '+row['id'])
    eid=resources.proof(row['evidence'])
    layers=[];props=[]
    for index,layer in enumerate(row['layers']):
        mid=resources.material(layer['properties'],layer['evidence'],layer.get('field_evidence'))
        layers.append({'order':index,'material_id':mid})
        props.append(layer['properties'])
    result={'id':row['id'],'name':row['name'],'role':row['role'],'model':row['model'],
        'status':'ready','source_family':row.get('source_family','existing_stock_source_fixture'),
        'template':row.get('template'),'climate_group':row.get('climate'),
        'layers':layers,'layer_orientation':'exterior_to_interior', 'evidence_ids':[eid],
        'required_bindings':row.get('required_bindings',[]),
        'applicability':copy.deepcopy(row.get('applicability',{})),
        'source_attributes':copy.deepcopy(row.get('source_attributes',{})),
        'source_surface_ids':row.get('source_surface_ids',[]),
        'source_adjacency':row.get('source_adjacency',[]),
        'metrics':opaque_metrics(props) if row['model']=='opaque_layers' else {},
        'source_parameters':{},'target_adjustment':None}
    if row.get('property_evidence'):
        result['evidence_ids'].append(resources.proof(row['property_evidence']))
    for key,value in row.get('parameters',{}).items():
        if isinstance(value,dict) and 'value' in value:
            if value['value'] is not None:
                result['source_parameters'][key]={'value':value['value'],'unit':value['unit'],
                                                'evidence_id':resources.proof(value['evidence'])}
        elif value is not None:
            result['source_parameters'][key]={'value':value,'unit':source_parameter_unit(key),'evidence_id':eid}
    if row.get('target_adjustment'):
        adjust=copy.deepcopy(row['target_adjustment'])
        adjust['evidence_id']=resources.proof(adjust.pop('evidence'))
        result['target_adjustment']=adjust
    if row.get('solar_modifiers'):
        modifiers=copy.deepcopy(row['solar_modifiers'])
        for value in modifiers.values():
            value['evidence_id']=resources.proof(value.pop('evidence'))
        result['solar_modifiers']=modifiers
    return result


def source_parameter_unit(name):
    units={'engine_layer_r_m2_K_W':'m2*K/W','source_film_r_m2_K_W':'m2*K/W',
        'u_W_m2_K_including_source_films':'W/m2/K','source_assembly_r_m2_K_W':'m2*K/W',
        'mass_per_area_kg_m2':'kg/m2','heat_capacity_per_area_J_m2_K':'J/m2/K'}
    if name not in units:
        raise ValueError('Unknown source parameter unit: '+name)
    return units[name]


def ach_proof(row,index):
    return {'source_project':'atlas_source_derivation','source_revision':'fixed-ach-v1/1.0.0',
        'source_file_sha256':sha(ACH),'source_locator':ACH.relative_to(ROOT).as_posix()+'#/'+index,
        'extraction_date':DATE,'original_value':copy.deepcopy(row),'original_unit':'SI 1/s; inspection ACH 1/h',
        'transformation':row['transformation'],'interpretation_note':row['interpretation_note']}


def select_package(payload,package_id,climate,reference_id=None):
    """Resolve a package using only consumer catalogue data and pinned source rules."""
    from scripts.recover_construction_selectors import resolve_source_selector
    package=payload['packages'][package_id]
    if climate not in package['supported_climates']:
        raise ValueError('Unsupported source package climate: '+climate)
    variants=package['infiltration']['reference_variants']
    if reference_id is None:
        if len(variants)!=1:
            raise ValueError('Select a source reference variant; variants are not averaged')
        reference_id=variants[0]['reference_id']
    matches=[r for r in variants if r['reference_id']==reference_id]
    if len(matches)!=1 or climate not in matches[0]['climates']:
        raise ValueError('Unsupported source reference variant/climate')
    packet={'records':payload['packages'],'elements':payload['assemblies'],
            'climate_zone_sets':payload['climate_zone_sets']}
    selected={}
    for slot,selector in package['selectors'].items():
        if not selector['elements']:
            continue
        result=resolve_source_selector(packet,package_id,slot,climate)
        if not result['element_ids']:
            raise ValueError('Active source selector has no elements')
        selected[slot]=result
    return {'package_id':package_id,'climate_zone':climate,'reference_id':reference_id,
            'selected_elements':selected,'natural_ach':matches[0]['climates'][climate]}


def build_catalogue():
    commercial,residential,ach=(load_json(p) for p in (COMMERCIAL,RESIDENTIAL,ACH))
    for packet in (commercial,residential,ach):
        verify_inputs(packet)
    frozen=load_json(BASE/'constructions.json')
    by_id={r['id']:r for r in frozen}
    resources=Resources(commercial.get('evidence',{}))
    assemblies={i:assembly(r,resources) for i,r in sorted(commercial['elements'].items())}
    packages={};enclosures={}
    benches={};ach_enclosures={r['construction_id']:r for r in ach['residential']}
    for index,r in enumerate(ach['commercial_reference_benchmarks']):
        eid=resources.proof(ach_proof(r,'commercial_reference_benchmarks/'+str(index)))
        benches.setdefault(r['reference_id'],{})[r['climate_zone']]=dict(r['natural_ach'],evidence_id=eid)
    mappings={m['package_id']:m for m in ach['package_reference_mappings']}
    for identity,row in sorted(commercial['records'].items()):
        selectors=copy.deepcopy(row['selectors'])
        for selector in selectors.values():
            selector['evidence_id']=resources.proof(selector.pop('evidence'))
        mapping=mappings[identity]
        packages[identity]={'id':identity,'name':by_id[identity]['name'],'status':'ready',
            'source_family':by_id[identity]['source_family'],'template':row['template'],
            'building_type':row['building_type'],'space_type':row.get('space_type'),
            'selectors':selectors,'evidence_ids':[resources.proof(row['evidence'])],
            'infiltration':{'method':'fixed_source_reference_natural_ach',
                'reference_variants':[{'reference_id':ref,'climates':benches[ref]} for ref in mapping['reference_ids']],
                'mapping_status':mapping['source_mapping_status'],
                'reference_decision':mapping.get('reference_decision')},
            'deferred_selectors':copy.deepcopy(row['deferred_selectors']),
            'required_bindings':['climate_zone','surface_roles_and_adjacencies','source_reference_variant'],
            'legacy_infiltration_disposition':'Source NIST helper removes legacy space/type infiltration and replaces it with package enclosure benchmark; not an additional program load'}
        from scripts.recover_construction_selectors import resolve_source_selector
        supported=[];unsupported={}
        for climate in sorted(LABELS):
            for slot,selector in row['selectors'].items():
                if not selector['elements']:
                    continue
                try:
                    resolve_source_selector(commercial,identity,slot,climate)
                except ValueError as error:
                    if str(error).startswith('Unsupported source selector climate:'):
                        unsupported[climate]='No source property row for active selector '+slot
                        break
                    raise
            else:
                supported.append(climate)
        if not supported:
            raise ValueError('Source package has no supported climate context')
        packages[identity]['supported_climates']=supported
        packages[identity]['unsupported_climates']=unsupported
        for value in packages[identity]['deferred_selectors'].values():
            value['evidence_id']=resources.proof(value.pop('evidence'))
    by_source={r['source_id']:r for r in frozen if r.get('role')=='dwelling_enclosure'}
    for rid,row in sorted(residential['records'].items()):
        source=by_source[rid];identity=source['id']
        if row['unresolved']:
            raise ValueError('Active residential source physics gap: '+rid)
        ids=[]
        for a in row['assemblies']:
            record=assembly(a,resources)
            record['climate_group']=source['climate'];record['source_fixture_id']=rid
            if record['id'] in assemblies:
                raise ValueError('Residential assembly ID collision')
            assemblies[record['id']]=record;ids.append(record['id'])
        natural=ach_enclosures[identity]
        eid=resources.proof(ach_proof(natural,'residential/reference_id='+rid))
        enclosures[identity]={'id':identity,'name':source['name'],'status':'ready',
            'source_family':'existing_stock_source_fixture','source_fixture_id':rid,
            'source_climate_label':source['climate'],'assembly_ids':ids,
            'infiltration':{'method':'fixed_source_annual_average_natural_ach',
                'reference_id':rid,'climates':{label:dict(natural['natural_ach'],evidence_id=eid) for label in natural['reference_climate_labels']}},
            'deferred_elements':row['deferred_elements'], 'source_context':row['source_context'],
            'required_bindings':sorted({b for aid in ids for b in assemblies[aid]['required_bindings']})}
    inputs=[COMMERCIAL,RESIDENTIAL,ACH,BASE/'constructions.json',
            ROOT/'scripts/construction_export.py',ROOT/'scripts/construction_validation.py',
            ROOT/'scripts/recover_construction_selectors.py',ROOT/'scripts/definition_contract.py',
            ROOT/'scripts/common.py',ROOT/'scripts/energy_json_review.py',
            ROOT/'schemas/construction-json-v1.schema.json']
    source_files={}
    for prefix,packet in [('commercial',commercial),('residential',residential)]:
        for path,descriptor in packet['source_files'].items():
            source_files[prefix+'/'+path]=dict(descriptor)
    expected=set(commercial['elements']) | set(packages) | set(enclosures)
    expected|={a['id'] for r in residential['records'].values() for a in r['assemblies']}
    deferred_ids=sorted(r['id'] for r in frozen if r.get('representation')=='element' and r['role'].startswith('GroundContact'))
    baseline_ids=set(by_id)-set(deferred_ids)
    if not baseline_ids <= expected:
        raise ValueError('Recovery dropped an eligible frozen construction identity')
    payload={'schema_version':'1.0.0','kind':'above_ground_construction_catalogue','export_mode':'source_ready',
        'scope':{'construction':'above_ground','foundation_ground':'deferred','systems':'deferred'},
        'assemblies':dict(sorted(assemblies.items())),'packages':packages,'enclosures':enclosures,
        'materials':dict(sorted(resources.materials.items())), 'evidence':dict(sorted(resources.evidence.items())),
        'climate_zone_sets':commercial['climate_zone_sets'],
        'source_files':source_files,'input_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in inputs},
        'inventory':{'eligible_ids':sorted(expected),'deferred_ground_ids':deferred_ids,
            'baseline_above_ground_ids':sorted(baseline_ids),
            'commercial_source_inventory':commercial['inventory'],
            'residential_fixture_count':len(residential['records'])},
        'consumer_notes':['Assign ordered materials to compatible source surface roles; actual geometry is external.',
            'Reuse selected fixed ACH across geometry/zoning variants; no mechanical air requirements or program loads here.',
            'Ground and foundation-dependent interface assemblies are deferred, not zero.']}
    return payload,expected


def scoped_example(payload,primary,selection=None):
    """Self-contained subset catalogue with explicit example selection metadata."""
    packet=copy.deepcopy({k:v for k,v in payload.items() if k not in {'assemblies','materials','evidence','packages','enclosures'}})
    packet['packages']={};packet['enclosures']={}
    if selection:
        package=copy.deepcopy(payload['packages'][primary])
        for slot,selector in package['selectors'].items():
            ids=selection['selected_elements'].get(slot,{}).get('element_ids',[])
            selector['elements']=ids
            if selector.get('selection_policy'):
                selector['selection_policy']['source_order']=[r for r in selector['selection_policy']['source_order'] if set(r['element_ids']) & set(ids)]
        package['supported_climates']=[selection['climate_zone']]
        package['infiltration']['reference_variants']=[{'reference_id':selection['reference_id'],
            'climates':{selection['climate_zone']:selection['natural_ach']}}]
        packet['packages'][primary]=package
        ids={i for r in selection['selected_elements'].values() for i in r['element_ids']}
    else:
        enclosure=copy.deepcopy(payload['enclosures'][primary]);packet['enclosures'][primary]=enclosure
        ids=set(enclosure['assembly_ids'])
    packet['assemblies']={i:payload['assemblies'][i] for i in sorted(ids)}
    mids={l['material_id'] for a in packet['assemblies'].values() for l in a['layers']}
    packet['materials']={i:payload['materials'][i] for i in sorted(mids)}
    # Evidence references are explicit fields; original source values are preserved.
    evidence_ids=set()
    def collect(node):
        if isinstance(node,dict):
            for key,value in node.items():
                if key=='evidence_id':evidence_ids.add(value)
                elif key=='evidence_ids':evidence_ids.update(value)
                elif key=='property_evidence':evidence_ids.update(value.values())
                else:collect(value)
        elif isinstance(node,list):
            for value in node:collect(value)
    for table in ('assemblies','materials','packages','enclosures'):
        collect(packet[table])
    pending=list(evidence_ids)
    while pending:
        evidence=payload['evidence'][pending.pop()]
        original=evidence.get('original_value')
        refs=original.get('source_layer_evidence_ids',[]) if isinstance(original,dict) else []
        for reference in refs:
            if reference not in evidence_ids:
                evidence_ids.add(reference);pending.append(reference)
    packet['evidence']={i:payload['evidence'][i] for i in sorted(evidence_ids)}
    expected=ids|{primary}
    packet['inventory']={'eligible_ids':sorted(expected),'deferred_ground_ids':[],
        'baseline_above_ground_ids':sorted(expected & set(payload['inventory']['baseline_above_ground_ids'])),
        'example_selection':selection or {'source_enclosure_id':primary}}
    validate_catalogue(packet,expected)
    return packet


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    payload,expected=build_catalogue()
    medium=next(i for i,p in payload['packages'].items() if p['building_type']=='MediumOffice' and p['template']=='90.1-2019' and p['space_type'] is None)
    selection=select_package(payload,medium,'4A','90.1-2019/MediumOffice')
    medium_example=scoped_example(payload,medium,selection)
    residential=next(i for i,p in payload['enclosures'].items() if p['source_fixture_id']=='residential_archetype-0157cd8578ba44bf8a77')
    residential_example=scoped_example(payload,residential)
    receipt=validate_catalogue(payload,expected)
    receipt.update(schema_version='1.0.0',date=DATE,eligible_ids=sorted(expected),
                   deferred_ground_ids=payload['inventory']['deferred_ground_ids'],
                   baseline_preserved_count=len(payload['inventory']['baseline_above_ground_ids']),
                   additional_commercial_dependencies=len(payload['inventory']['commercial_source_inventory']['additional_element_ids']),
                   residential_assembly_children=sum(len(e['assembly_ids']) for e in payload['enclosures'].values()),
                   unsupported_package_climates={i:p['unsupported_climates'] for i,p in payload['packages'].items() if p['unsupported_climates']},
                   validation_scope='All eligible source construction physics/dependencies/provenance/schema; no site, program, systems or ground build')
    def encoded(value):
        return (json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8')
    outputs={OUTPUT/'catalogue.json':encoded(payload),OUTPUT/'completeness.json':encoded(receipt),
             OUTPUT/'examples/medium-office.json':encoded(medium_example),
             OUTPUT/'examples/residential.json':encoded(residential_example),
             OUTPUT/'schemas/construction-json-v1.schema.json':(ROOT/'schemas/construction-json-v1.schema.json').read_bytes(),
             OUTPUT/'LICENSE':(ROOT/'LICENSE').read_bytes()}
    for name in ('openstudio-standards','resstock','openstudio-hpxml','weather'):
        outputs[OUTPUT/'sources/licenses'/f'{name}.txt']=(ROOT/'sources/licenses'/f'{name}.txt').read_bytes()
    manifest={'schema_version':'1.0.0','kind':'above_ground_construction_release','release':'v1.0.0',
        'date':DATE,'scope':payload['scope'],'input_sha256':payload['input_sha256'],
        'source_revisions':sorted({d['source_revision'] for d in payload['source_files'].values()}),
        'coverage':{k:receipt[k] for k in ('eligible_count','ready_count','assembly_count','package_count','enclosure_count','validated_package_climate_reference_contexts')},
        'files':{p.relative_to(OUTPUT).as_posix():{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for p,b in outputs.items()},
        'publication_status':'Frozen on feature branch; protected-main publication and site integration pending'}
    outputs[OUTPUT/'manifest.json']=encoded(manifest)
    for path,value in outputs.items():
        if args.check:
            if not path.exists() or value!=path.read_bytes():
                raise ValueError('Construction export not reproducible: '+path.name)
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(value)
    print(f"Above-ground construction: {receipt['ready_count']}/{receipt['eligible_count']} ready; zero missing IDs/active blockers")


if __name__=='__main__':
    main()
