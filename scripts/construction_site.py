"""Present immutable construction v2 as selectable sets and linked resources."""
import copy
import gzip
import hashlib
import html
import json
import re
from pathlib import Path
from scripts.common import ROOT,load_json
from scripts.definition_contract import canonical
from scripts.definition_site import generate,write
from scripts.catalogue_names import building_label
from scripts.object_site import JSONStore,json_markup,PREFIX
from scripts.construction_set_release import OUTPUT
from scripts.construction_distribution import load_current_release as load_release
from scripts.construction_set_export import dependency_closure
from scripts.site_asset_versions import version_asset_urls


def esc(value):return html.escape(str(value),quote=True)


def remove_empty_retired_routes(root,identities):
    root=Path(root).resolve()
    for identity in identities:
        if not re.fullmatch(r'construction-[a-f0-9]{24}',identity):raise ValueError('Unsafe retired construction identity')
        leaf=(root/f'definitions/{identity}').resolve()
        if not leaf.is_relative_to(root):raise ValueError('Retired route escapes generated tree')
        if leaf.is_dir() and not any(leaf.iterdir()):leaf.rmdir()


def rewrite_retired_links(text,parents,profiles):
    def replace(match):
        identity=match[1]
        if identity not in parents:return match[0]
        links='; '.join(f'<a href="{PREFIX}definitions/{p}/">{esc(profiles[p]["name"])}</a>' for p in parents[identity])
        return f'<span>Source space recipe <code>{identity}</code> · Embedded in {links}</span>'
    return re.sub(r'<a\b[^>]*href="'+re.escape(PREFIX)+r'definitions/(construction-[a-f0-9]{24})/"[^>]*>.*?</a>',replace,text,flags=re.S)


def repair_retired_references(root,bundle,release):
    from scripts.construction_distribution import OUTPUT as distribution
    from scripts.object_site import references
    parents=load_json(distribution/'selection.json')['embedded_parent_sets'];root=Path(root).resolve();changed=[]
    for row in bundle['constructions']:
        if row['id'] in parents or not references(row,parents):continue
        if not re.fullmatch(r'construction-[a-f0-9]{24}',row['id']):raise ValueError('Unsafe source construction identity')
        for path in (root/f'definitions/{row["id"]}.md',root/f'definitions/{row["id"]}/index.html'):
            if not path.resolve().is_relative_to(root):raise ValueError('Source reference route escapes generated tree')
            if not path.is_file():continue
            text=path.read_text(encoding='utf-8');revised=rewrite_retired_links(text,parents,release['construction_sets'])
            if revised!=text:path.write_text(revised,encoding='utf-8',newline='\n');changed.append(path.relative_to(root).as_posix())
    return changed


def prune_construction_history(root):
    """Current site carries one query snapshot; immutable research freezes stay."""
    from scripts.query_v2 import QueryClient
    from scripts.query_delivery import descriptor,safe_path
    root=Path(root).resolve();current=QueryClient(root)
    selected=current.fetch(current.manifest['record_types']['construction']['index'])
    keep={current.manifest['record_types']['construction']['index']['href']}
    keep.update(d['href'] for route in selected['routes'] for d in route['packets'])
    obsolete=[];resources=set()
    for path in (root/'snapshots').glob('*/manifest.json'):
        if path.relative_to(root).as_posix()==current.manifest_ref['href']:continue
        if not re.fullmatch(r'[a-f0-9]{64}',path.parent.name):raise ValueError('Unexpected historical snapshot path')
        previous=QueryClient(root,manifest_ref=descriptor(path.relative_to(root).as_posix(),path.read_bytes()))
        old=previous.manifest['record_types']['construction']['index'];index=previous.fetch(old)
        retired=[old]+[d for route in index['routes'] for d in route['packets']]
        resources.update(d['href'] for d in retired if d['href'] not in keep)
        if not path.resolve().is_relative_to(root):raise ValueError('Snapshot escapes current delivery')
        obsolete.append(path)
    for href in resources:safe_path(root,href).unlink(missing_ok=True)
    for path in obsolete:
        path.unlink();path.parent.rmdir()


def context_choices(profile,contexts):
    return [{'id':c['id'],'climate':c['climate_zone'],'reference':c['reference_id'],
             'building':building_label(c['reference_id'].split('/',1)[-1]) if profile['scope']!='whole_dwelling' else building_label(profile['source']['building_type'])} for c in contexts.values()]


def packet_for(release,identity,contexts):
    configs={c['configuration_id']:release['component_configurations'][c['configuration_id']] for c in contexts.values()}
    receipts={c['selector_receipt_id']:release['selector_receipts'][c['selector_receipt_id']] for c in contexts.values()}
    combined={'all':{'assignments':[a for config in configs.values() for comp in config['components'].values() for a in comp['assignments']]}}
    eids={i for c in contexts.values() for i in c['source_evidence_ids']}
    assemblies,materials,evidence=dependency_closure(release,combined,{'evidence':[release['evidence'][i] for i in eids]},
        [c['infiltration'] for c in contexts.values()],[d for rows in receipts.values() for d in rows])
    metadata={k:v for k,v in release['metadata'].items() if k!='source_table_only_assembly_ids'}
    from scripts.construction_equivalent_site import mass_fields
    links,contracts=mass_fields(contexts)
    contexts={cid:{**c,'mass_contract_id':links[cid]} for cid,c in contexts.items()}
    return {'schema_version':'1.1.0','kind':'construction_site_packet','profile':release['construction_sets'][identity],
        'mass_contracts':contracts,
        'contexts':contexts,'component_configurations':configs,'selector_receipts':receipts,
        'assemblies':assemblies,'materials':materials,'evidence':evidence,'metadata':metadata}


def projection(release,bundle):
    originals={r['id']:r for r in bundle['constructions']};rows=[]
    for identity,p in release['construction_sets'].items():
        source=p['source'];contexts=[c for c in release['contexts'].values() if c['construction_set_id']==identity]
        row=copy.deepcopy(originals.get(identity,{}))
        row.update(id=identity,name=p['name'],building_type=source['building_type'],template=source['template'],
            source_family=source['source_family'],evidence_view=source['evidence_view'],construction_schema='2.1.0',
            vintage=source['vintage']['value'],scope=p['scope'],derivation='source-ready construction set',
            gate=originals.get(identity,{}).get('gate') or ['residential' if p['scope']=='whole_dwelling' else 'nonresidential'],
            applicability=[{'building_type':c['reference_id'].split('/',1)[-1] if p['scope']!='whole_dwelling' else source['building_type'],
                            'climate':c['climate_zone']} for c in contexts])
        rows.append(row)
    return {**bundle,'constructions':rows}


def resource_path(table,identity):return f'construction/{table}/{identity}/index.html'


def static_page(name,body):
    return version_asset_urls('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{esc(name)}</title><link rel="stylesheet" href="{PREFIX}assets/fonts.css"><link rel="stylesheet" href="{PREFIX}assets/site.css">'
        f'<script src="{PREFIX}assets/theme.js"></script></head><body><header class="definition-header"><a href="{PREFIX}">Energy Archetype Atlas</a> · '
        f'<a href="{PREFIX}catalogue/">Catalogue</a> · <a href="{PREFIX}sources/">Sources</a></header><main class="definition-document">'
        f'<h1>{esc(name)}</h1>{body}</main><script src="{PREFIX}assets/object.js"></script></body></html>')


def generate_constructions(release,bundle,root,reuse_resources=False):
    if any(p['scope']=='space_type' for p in release['construction_sets'].values()):raise ValueError('Partial space-type sets belong to frozen source evidence, not current consumer delivery')
    root=Path(root);store=JSONStore(root);projected=projection(release,bundle)
    previous=load_json(root/'construction-site.json') if reuse_resources and (root/'construction-site.json').is_file() else {}
    generate(projected,root,publish=False,pages=False,only_kinds={'construction'})
    registry=load_json(root/'object-index.json') if (root/'object-index.json').exists() else {}
    from scripts.construction_distribution import OUTPUT as distribution
    retired=load_json(distribution/'selection.json')['retired_space_type_ids']
    for identity in retired:
        if not re.fullmatch(r'construction-[a-f0-9]{24}',identity):raise ValueError('Unsafe retired construction identity')
        registry.pop(identity,None)
        for path in (root/f'definitions/{identity}.md',root/f'definitions/{identity}/index.html'):
            if not path.resolve().is_relative_to(root.resolve()):raise ValueError('Retired route escapes generated tree')
            if path.is_file():
                raw=re.search(r'\bdata-raw="([^"]+)"',path.read_text(encoding='utf-8'))
                if raw:
                    d=json.loads(html.unescape(raw[1]))
                    if not re.fullmatch(r'json/[a-f0-9]{64}\.json\.gz',d['href']):raise ValueError('Unsafe retired source JSON path')
                    blob=root/d['href']
                    if blob.exists():
                        value=json.loads(gzip.decompress(blob.read_bytes()))
                        if value.get('id')!=identity:raise ValueError('Retired source JSON identity mismatch')
                        blob.unlink()
            path.unlink(missing_ok=True)
    remove_empty_retired_routes(root,retired)
    from scripts.construction_equivalent_site import load_equivalents,packet_for as equivalent_packet
    equivalents=load_equivalents()
    report={'schema_version':'1.0.0','construction_schema':'2.1.0','definitions':len(release['construction_sets']),
        'contexts':len(release['contexts']),'packets':{},'unified_schema':'1.2.0','unified_packets':{},
        'resources':{k:{} for k in ('assemblies','materials','evidence')}}
    for identity,profile in release['construction_sets'].items():
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',identity):raise ValueError('Unsafe construction identity')
        contexts={i:c for i,c in release['contexts'].items() if c['construction_set_id']==identity}
        packet=packet_for(release,identity,contexts);descriptor=store.put(packet);report['packets'][identity]=descriptor
        unified=store.put(equivalent_packet(equivalents,identity,contexts));report['unified_packets'][identity]=unified
        source=profile['source']
        choices=context_choices(profile,contexts)
        controls='<div class="definition-filters construction-controls"><label>Climate<select class="construction-climate"><option value="">Choose climate</option>'
        controls+=''.join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in sorted({c['climate_zone'] for c in contexts.values()}))
        controls+='</select></label><label>Source reference<select class="construction-reference"><option value="">Choose source reference</option></select></label>'
        controls+='<label>JSON representation<select class="construction-representation"><option value="detailed">Detailed construction set</option><option value="unified">Unified building construction</option></select></label></div>'
        controls+='<p class="construction-description">Detailed JSON retains original assemblies and program/story assignment rules. Unified JSON provides one assembly per semantic with approximation evidence.</p>'
        markup=(f'<section class="object-json" data-construction="{esc(json.dumps(descriptor,separators=(",",":")))}" '
            f'data-unified="{esc(json.dumps(unified,separators=(",",":")))}" '
            f'data-contexts="{esc(json.dumps(choices,separators=(",",":")))}" data-root="../../">'+controls+
            '<button type="button" class="object-copy" disabled>Copy detailed JSON</button>'+
            '<button type="button" class="construction-copy-unified" disabled>Copy unified JSON</button>'+
            '<details class="object-source"><summary>JSON</summary><pre tabindex="0">Expand to load the selected construction JSON.</pre></details>'+
            '<p class="object-status" role="status" aria-live="polite"></p></section>')
        page=f'# {esc(profile["name"])}\n\n[Construction catalogue](../catalogue/{"residential" if profile["scope"]=="whole_dwelling" else "nonresidential"}/construction/index.md) · [Construction JSON contract](../guides/construction-json.md)\n\n'
        page+=f'`{identity}` · Construction set · {esc(profile["scope"])} · {esc(source["template"])} · {esc(source["source_family"])}\n\n'
        page+='One set contains its source-supported exterior and interior components. Select a climate and source reference, then copy **Detailed** or **Unified** JSON using its own button. The representation selector controls the preview. Both copies use the same selected context. Fixed reference ACH remains explicit. BEMGen supplies actual model geometry.\n\n'
        if profile['scope']=='space_type':page+='This is a partial source space set; it is not a complete building set.\n\n'
        additions=[d['atlas_added_applicability'] for rows in packet['selector_receipts'].values() for d in rows if 'atlas_added_applicability' in d]
        if additions:
            mode=additions[0]['mode']
            page+='**Atlas-added GuestRoom applicability:** '+('The source generic recipe is attached as an additional floor-agnostic construction option; all four specific variants are retained.' if mode=='attach_source_recipe' else 'A generic GuestRoom inherits this set’s existing building/story construction rules; source space-specific overrides remain separate.')
            page+=' This is an explicit Atlas applicability decision. Physics and the single building infiltration reference are unchanged. [Policy](../construction/applicability/policy.json).\n\n'
        page+=markup+'\n\n## Component resources\n\nThese links retain the original detailed assemblies. Unified equivalent assemblies are included in the selected unified JSON.\n\n'
        page+='| Component type | Available assembly resources |\n|---|---|\n'
        roles={}
        for config in packet['component_configurations'].values():
            for role,component in config['components'].items():roles.setdefault(role,set()).update(a['assembly_id'] for a in component['assignments'])
        for role,ids in roles.items():
            links=' · '.join(f'[{esc(release["assemblies"][i]["name"])}]({PREFIX}{resource_path("assemblies",i)})' for i in sorted(ids)) or 'Absent at this source scope; applicable source defaults inherit by the declared hierarchy'
            page+=f'| {esc(role)} | {links} |\n'
        page+='\n[All assembly resources](../construction/assemblies/index.md) · [Frozen source coverage](../construction/coverage.json)\n'
        write(root,f'definitions/{identity}.md',page)
        registry[identity]={'table':'constructions','name':profile['name'],'path':f'definitions/{identity}.md'}
    for table in report['resources']:
        for identity,item in release[table].items():
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',identity):raise ValueError('Unsafe construction resource identity')
            cached=previous.get('resources',{}).get(table,{}).get(identity)
            if cached and cached['path']==resource_path(table,identity) and (root/cached['path']).is_file() and re.fullmatch(r'json/[a-f0-9]{64}\.json\.gz',cached['json']['href']) and (root/cached['json']['href']).is_file():
                # Focused refresh reuses unchanged immutable source resources;
                # verify_delivery subsequently checks their bytes and bindings.
                report['resources'][table][identity]=cached
                continue
            name=item.get('name') or item.get('source_locator') or identity;descriptor=store.put(item);path=resource_path(table,identity)
            report['resources'][table][identity]={'path':path,'json':descriptor}
            registry[identity]={'table':'construction_'+table,'name':name,'path':path}
            body=f'<p><code>{esc(identity)}</code> · Construction {esc(table)}</p><p><a href="{PREFIX}catalogue/">Catalogue</a> · <a href="{PREFIX}construction/assemblies/">All assembly resources</a></p>'
            if table=='assemblies':
                body+='<p>Source-ready assembly resource. A construction set groups applicable components; this individual assembly is not a whole-building set.</p>'
                if identity in release['metadata'].get('source_table_only_assembly_ids',[]):body+='<p>Independent source-table recipe: complete physics and provenance; no recovered prototype mapping.</p>'
                body+=f'<p>Role: {esc(item["role"])} · Model: {esc(item["model"])} · Source climate group: {esc(item.get("climate_group"))}</p><table><tr><th>Layer (outside → inside)</th><th>Material</th></tr>'
                for layer in item['layers']:
                    mid=layer['material_id'];body+=f'<tr><td>{layer["order"]+1}</td><td><a href="{PREFIX}{resource_path("materials",mid)}">{esc(release["materials"][mid]["name"])}</a></td></tr>'
                body+='</table>'
            elif table=='materials':
                body+=f'<p>Model: {esc(item["model"])}</p><table><tr><th>SI property / model option</th><th>Value</th><th>Source evidence</th></tr>'
                for key,value in item['properties'].items():
                    eid=item['property_evidence'][key]
                    body+=f'<tr><th>{esc(key)}</th><td>{esc(value if value is not None else "Unknown")}</td><td><a href="{PREFIX}{resource_path("evidence",eid)}">Source</a></td></tr>'
                body+='</table>'
            else:
                body+='<dl>'+''.join(f'<dt>{esc(key)}</dt><dd>{esc(item[key])}</dd>' for key in ('source_project','source_revision','source_locator','original_unit','transformation','extraction_date','interpretation_note'))+'</dl>'
            body+=json_markup(descriptor,reason='Source-recovered construction resource; program defaults do not apply.',relative_root='../../../')
            if item.get('evidence_ids'):
                body+='<details class="object-references"><summary>Source evidence</summary><ul>'+''.join(f'<li><a href="{PREFIX}{resource_path("evidence",i)}">{esc(i)}</a></li>' for i in item['evidence_ids'])+'</ul></details>'
            write(root,path,static_page(name,body))
    rows=report['resources']['assemblies']
    page='# Assembly resources\n\nThese are individual source-ready recipes, separate from whole construction sets. Independent source-table recipes retain explicit missing prototype applicability.\n\n<details class="definition-static"><summary>All assembly resources — accessible without JavaScript</summary><ul>'
    page+=''.join(f'<li><a href="{PREFIX}{entry["path"]}">{esc(release["assemblies"][i]["name"])} · {esc(release["assemblies"][i]["role"])} · {esc(i)}</a></li>' for i,entry in rows.items())+'</ul></details>\n'
    write(root,'construction/assemblies/index.md',page)
    write(root,'construction/coverage.json',canonical({'definitions':report['definitions'],'contexts':report['contexts'],
        'unified_release':'1.1.0','unified_schema':report['unified_schema'],
        'construction_schema':report['construction_schema'],'shared_mass_release':'1.0.0',
        'unified_contexts':report['contexts'],
        'assemblies':len(rows),'source_table_only_assembly_ids':release['metadata'].get('source_table_only_assembly_ids',[])}).decode())
    write(root,'object-index.json',canonical(registry).decode());write(root,'construction-site.json',canonical(report).decode())
    repair_retired_references(root,bundle,release)
    if (root/'delivery/v2/latest.json').is_file():
        from scripts.query_v2 import generate_delivery
        generate_delivery(projected,root/'delivery/v2',only_kind='construction')
        prune_construction_history(root/'delivery/v2')
    return report


def update_existing(bundle,root,release=None):
    root=Path(root).resolve()
    if not (root/'site-manifest.json').is_file() or not (root/'object-index.json').is_file():raise ValueError('A marked generated tree with a site manifest is required')
    if not root.is_relative_to((ROOT/'build').resolve()) or root==(ROOT/'build').resolve():raise ValueError('Existing output must be inside a workspace build directory')
    report=generate_constructions(release or load_release(),bundle,root,reuse_resources=True)
    manifest=load_json(root/'site-manifest.json');registry=load_json(root/'object-index.json')
    manifest['objects']=len(registry);manifest['counts']['constructions']=report['definitions']
    manifest['construction_v2']={k:report[k] for k in ('construction_schema','definitions','contexts')}
    write(root,'site-manifest.json',canonical(manifest).decode())
    return report


def install_contract(root,include_resources=True):
    root=Path(root)
    guide='''# Construction JSON for simulation import

Contract **2.1.0**. One construction set supplies all source-supported above-ground
component types, fixed reference infiltration, materials and provenance.

Each definition page offers two separate JSON exports for the same selected
climate and source reference:

- **Detailed construction set (2.1.0):** original assemblies, materials,
  program/story assignment rules and provenance.
- **Unified building construction (1.2.0):** one assembly per applicable semantic,
  precomputed archetype weights, mass budgets, fixed reference ACH and fit errors.

The unified export is additive. It does not replace detailed source rules. Its
fixed two-mass-layer plus massless-resistance approximation may inadequately
reproduce source transient responses; measured errors and review flags remain
visible. Do not combine both representations' mass quantities in one model.
Source overhang dimensions remain evidence; BEMGen supplies actual overhang
geometry. Paired-face budget means retain original operands in supporting
profiles, with unequal-multiplier approximation flags and affected pair counts.

Current distribution **v2.2.0** ships 177 complete building/dwelling sets and
3,320 supported contexts. Room-specific rules are embedded in building sets.
The detailed consumer schema is **2.1.0** and the unified consumer schema is
**1.2.0**, supported by shared mass release **1.0.0**. The frozen unified
thermal-assembly release remains **1.1.0**. Release versions and schema versions identify
different artifacts and must not be inferred from each other.
Standalone space-type sets are retained in frozen source releases rather than
offered as independent consumer choices. Eight legacy office plenum contexts
without a supported 0A/0B building context are preserved as nonselectable evidence.

Applicability release **v2.1.0** adds explicit generic hotel GuestRoom support.
SmallHotel 2019 attaches its native generic recipe and retains all four specific
variants. Older SmallHotel sets declare inheritance through their existing
building/story rules. Selector receipts mark `atlas_added_applicability`, with
origin, mode, original source-instantiation status and an evidence reference.
No program loads, physics or infiltration values are changed.

- [Construction-set schema](../contracts/construction-json-v2.1.schema.json)
- [Normalized catalogue schema](../contracts/construction-catalogue-v2.schema.json)
- [Complete Medium Office example](../examples/construction/medium-office.json)
- [Complete residential example](../examples/construction/residential.json)
- [Unified construction schema](../contracts/construction-equivalent-v1.2.schema.json)
- [Unified Medium Office example](../examples/construction/unified-medium-office.json)
- [Unified residential example](../examples/construction/unified-residential.json)
- [Source coverage](../construction/coverage.json)
- [All assembly resources](../construction/assemblies/index.md)
- [Pinned source retrieval](../construction/source-lock.json)
- [Atlas hotel applicability policy](../construction/applicability/policy.json)
- [Applicability receipt extension schema](../contracts/construction-applicability-v1.schema.json)
- [Current distribution and embedding coverage](../construction/distribution/selection.json)
- [Eight unsupported source contexts](../construction/distribution/source-evidence.json)

## Shared mass accounting

Both exports include the same `mass_accounting` contract (1.0.0): reference
wall/slab capacity budgets, source additional-mass quantities and scaling,
recipe materials, original operands and provenance. Use one representation's
ledger once. Subtract explicit modeled surface capacity from the corresponding
reference budget before restoring omitted mass. A negative residual means
explicit modeled capacity exceeds the reference; report it and add no negative
mass. Do not remove actual walls/slabs or rescale source materials silently.
Additional furnishings/partition objects remain separate from explicit surfaces.

- [Shared mass schema](../contracts/construction-mass-accounting-v1.schema.json)

## Select and copy

Choose Residential or Non Residential, then Constructions. Filters select the
source construction set and full climate label. The record page preserves the
filter selection; choose a source reference where more than one is supported.
No climate or ambiguous reference is guessed. A uniquely supported choice is
resolved automatically. Climate controls both supported applicability and the
selected construction/reference ACH. Scope and source evidence remain metadata;
they are not separate construction catalogue filters.

Choose **JSON representation: Detailed / Unified** to preview either version.
**Copy detailed JSON** and **Copy unified JSON** each copy their named
representation, independently of the preview selection. Both use the same
climate and source reference and copy immediately, without a chooser or popup.
Each compressed packet loads only when needed and is verified before use.
If clipboard access fails, the selected JSON appears inline for manual copying.
Construction pages do not expose the older Atlas source-record copy option.
Construction copying does not apply program defaults. Other object types keep
their existing source/default copy controls.

## Components and geometry

Exterior and interior walls are components in the same set. The schema controls
component targets, conditions, source scope precedence and geometry conventions.
Source space/story overrides and alternative recipe identities remain explicit.
BEMGen owns matching to actual BEM components and IDF translation, including
areas, paired surfaces, roof pitch, adjacency and internal-mass scaling.
An unmatched or ambiguous consumer component must fail explicitly.

Fixed natural ACH uses the accepted source-reference geometry and 2013 climate
map; it is preserved across zoning changes. Layer/material physics, source
targets versus attained properties, source defaults and evidence are unchanged
from the frozen recovery. Metadata follows Program JSON source conventions.
There is no generic required_bindings or deferred_scope in this consumer JSON.

## Coverage and boundaries

The complete freeze covers 224 source definitions, 4,798 supported contexts and
4,868 ready assemblies. Of those assemblies, 1,439 independent source-table
recipes have complete physics/provenance but no recovered prototype mapping.
They remain accessible and explicitly identified; their applicability is not
invented. Unsupported source climates remain unsupported.

Foundation-dependent assemblies, ground and systems remain separate deferred
work. Program JSON stays independent. Ready exports establish contract completeness
under the documented policies, not annual building-energy accuracy. Preserve
source license notices when reusing artifacts.
'''
    if not include_resources:
        guide=guide.replace('- [Source coverage](../construction/coverage.json)\n','').replace('- [All assembly resources](../construction/assemblies/index.md)\n','')
        guide+='\nThis small presentation pilot does not include the frozen construction catalogue.\n'
    write(root,'guides/construction-json.md',guide)
    for name in ('construction-json-v2.schema.json','construction-catalogue-v2.schema.json'):
        write(root,'contracts/'+name,(OUTPUT/'schemas'/name).read_text(encoding='utf-8'))
    from scripts.construction_mass_release import EXAMPLES
    for name in ('construction-json-v2.1.schema.json','construction-equivalent-v1.2.schema.json','construction-mass-accounting-v1.schema.json'):
        write(root,'contracts/'+name,(ROOT/'schemas'/name).read_text(encoding='utf-8'))
    for source,target in (('medium-office-2019-3B','medium-office'),('residential-5A','residential')):
        for mode,prefix in (('detailed',''),('unified','unified-')):
            write(root,'examples/construction/'+prefix+target+'.json',(EXAMPLES/(source+'.'+mode+'.json')).read_text(encoding='utf-8'))
    write(root,'construction/source-lock.json',(OUTPUT/'sources/construction-v2-source-lock.json').read_text(encoding='utf-8'))
    for path in (OUTPUT/'sources/licenses').glob('*.txt'):
        write(root,'notices/construction/'+path.name,path.read_text(encoding='utf-8'))
    from scripts.construction_hotel_applicability import OUTPUT as applicability,SCHEMA
    write(root,'contracts/'+SCHEMA.name,SCHEMA.read_text(encoding='utf-8'))
    delivered={}
    for name in ('overlay.json','policy.json','coverage.json','README.md','construction-applicability-v1.schema.json'):
        # Publish an accurate delivery manifest for the static-download filenames.
        target='README.txt' if name=='README.md' else name
        content=(applicability/name).read_bytes();write(root,'construction/applicability/'+target,content.decode('utf-8'))
        delivered[target]={'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content)}
    delivery={'schema_version':'1.0.0','kind':'construction_applicability_site_delivery','release':'v2.1.0',
        'base_release':'v2.0.0','source_manifest_sha256':hashlib.sha256((applicability/'manifest.json').read_bytes()).hexdigest(),
        'interpretation_note':'Static delivery of the immutable applicability delta; README.md is served byte-identically as README.txt. The extension schema is also served under contracts/.',
        'files':delivered}
    write(root,'construction/applicability/manifest.json',canonical(delivery).decode())
    from scripts.construction_distribution import OUTPUT as distribution
    for name in ('manifest.json','selection.json','source-evidence.json','README.txt'):
        write(root,'construction/distribution/'+name,(distribution/name).read_text(encoding='utf-8'))


def program_presentation_inputs(bundle):
    paths=['scripts/program_json_v3.py','scripts/program_json.py','scripts/schedule_json.py',
           'scripts/program_json_aggregation.py','scripts/program_composition.py','scripts/semantics.py',
           'scripts/common.py','scripts/definition_contract.py','scripts/object_site.py',
           'schemas/program-json-v3.schema.json','schemas/program-json-v2.schema.json','schemas/schedule-json-v2.schema.json',
           'sources/program-json-defaults-v2.json','data/releases/v0.2.0/programs.json',
           'data/program-inputs/residential-v1.json','data/program-inputs/er-triage-v1.json']
    return {'files':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
            'bundle':hashlib.sha256(canonical(bundle)).hexdigest()}


def integrate_existing(bundle,root):
    """Local opt-in overlay; retain unrelated pages and verified program outputs."""
    import shutil
    from scripts.object_site import generate_objects
    root=Path(root).resolve()
    if not root.is_relative_to((ROOT/'build').resolve()) or not (root/'site-manifest.json').is_file():raise ValueError('A marked workspace generated tree is required')
    registry=load_json(root/'object-index.json');expected={r['id'] for table in bundle.values() if isinstance(table,list) for r in table if isinstance(r,dict) and 'id' in r}
    if not expected<=set(registry):raise ValueError('Cached site uses different source definitions')
    manifest=load_json(root/'site-manifest.json');fingerprint=program_presentation_inputs(bundle)
    if manifest.get('program_presentation_inputs')!=fingerprint:
        print('Refreshing stale local program presentation to the current v3 contract (no research recovery)',flush=True)
        result=generate_objects(bundle,root,only_tables={'programs'})
        if result['default_export_failures']:raise ValueError('Program presentation has unresolved exports')
        manifest.update(default_export_failures=result['default_export_failures'],program_presentation_inputs=fingerprint)
        write(root,'site-manifest.json',canonical(manifest).decode())
    else:print('Reusing unchanged verified v3 program presentation',flush=True)
    for source in (ROOT/'website/assets').iterdir():
        if source.is_file():shutil.copyfile(source,root/'assets'/source.name)
    install_contract(root)
    # Current program documentation and examples accompany the cached v3 payloads.
    contract=(ROOT/'docs/program-json-v3-contract.md').read_text(encoding='utf-8')
    contract=contract.replace('../schemas/','../contracts/').replace('../sources/','../contracts/').replace('examples/program-json-v3/','../examples/').replace('reviews/program-json-remaining-decisions.md','program-json-remaining-decisions.md')
    write(root,'guides/program-json.md',contract)
    write(root,'guides/program-json-remaining-decisions.md',(ROOT/'docs/reviews/program-json-remaining-decisions.md').read_text(encoding='utf-8'))
    for source in (ROOT/'docs/examples/program-json-v3').glob('*.json'):shutil.copyfile(source,root/'examples'/source.name)
    for name in ('program-json-v3.schema.json','schedule-json-v2.schema.json'):shutil.copyfile(ROOT/'schemas'/name,root/'contracts'/name)
    shutil.copyfile(ROOT/'sources/program-json-defaults-v2.json',root/'contracts/program-json-defaults-v2.json')
    report=update_existing(bundle,root)
    from scripts.active_site import landing
    projected=projection(load_release(),bundle);write(root,'index.md',landing(projected))
    selection=(root/'guides/selection.md').read_text(encoding='utf-8')
    selection=selection.replace('Other library objects expose their exact raw JSON; unresolved physical inputs stay explicit.',
        'Constructions offer source-ready JSON v2 after climate/reference selection, with complete component and material/provenance closure. [Construction contract](construction-json.md). HVAC objects retain exact source JSON and explicit unresolved inputs.')
    write(root,'guides/selection.md',selection)
    write(root,'guides/definitions.md',library_guide())
    sources=(root/'sources.md').read_text(encoding='utf-8')
    if 'https://data.openei.org/submissions/157' not in sources:
        sources+='\n\nHospital ER_Triage equipment recovery uses Deru, Michael, et al., *Commercial Reference Building: Hospital*, National Renewable Energy Laboratory, 25 November 2014, [OEDI submission 157](https://data.openei.org/submissions/157), under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). The post-1980 v1.3_5.0 SI scorecard supplies the recovered magnitude; copied program metadata retains the exact cell, checksum and transformation.\n'
    write(root,'sources.md',sources)
    return report


def library_guide():
    return ('# Library definitions\n\nPrograms supply loads and determined schedules. '
            'A construction set groups its source-supported above-ground components, materials, fixed reference infiltration and provenance. '
            'Choose its climate and source reference, then preview either representation and use its own Copy detailed JSON or Copy unified JSON button. '
            'Unified JSON uses precomputed archetype shares and one assembly per semantic, retaining approximation evidence and mass-budget rules. '
            'Room-specific construction rules are embedded in complete building sets. Independent assembly resources and unsupported contexts retain their source evidence. '
            'BEMGen owns component matching and translation using actual model geometry. '
            'Ground and systems completion remain deferred; existing HVAC pages retain source evidence.\n\n'
            '[Construction JSON contract](construction-json.md) · [Program JSON contract](program-json.md) · [Sources](../sources.md)\n')


def verify_delivery(root,release=None,*,require_construction=False):
    """Compare every presentation packet/resource to the checksum-locked freeze."""
    import gzip
    from html.parser import HTMLParser
    root=Path(root)
    if not (root/'construction-site.json').exists():
        return ['Missing required construction delivery: construction-site.json'] if require_construction else []
    release=release or load_release();report=load_json(root/'construction-site.json');errors=[];loaded={}
    from scripts.construction_equivalent_site import load_equivalents,packet_for as equivalent_packet
    equivalents=load_equivalents()
    class Section(HTMLParser):
        def __init__(self):super().__init__();self.sections=[]
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if 'object-json' in attrs.get('class','').split():self.sections.append(attrs)
    def page_attributes(path):
        parser=Section();parser.feed(path.read_text(encoding='utf-8'))
        if len(parser.sections)!=1:raise ValueError('Missing or ambiguous construction JSON section')
        return parser.sections[0]
    def read(descriptor):
        key=canonical(descriptor)
        if key in loaded:return loaded[key]
        if not re.fullmatch(r'json/[a-f0-9]{64}\.json\.gz',descriptor['href']) or descriptor['encoding']!='gzip':raise ValueError('Invalid construction resource path/encoding')
        if not 0<descriptor['decoded_size_bytes']<=16_000_000:raise ValueError('Invalid decoded construction bound')
        encoded=(root/descriptor['href']).read_bytes()
        if len(encoded)!=descriptor['size_bytes'] or hashlib.sha256(encoded).hexdigest()!=descriptor['sha256']:raise ValueError('Construction resource checksum/size mismatch')
        with gzip.open(root/descriptor['href'],'rb') as stream:decoded=stream.read(descriptor['decoded_size_bytes']+1)
        if len(decoded)!=descriptor['decoded_size_bytes']:raise ValueError('Construction decoded size mismatch')
        value=json.loads(decoded)
        # Profile packets repeat shared proofs; retaining every packet wastes memory.
        if value.get('kind') not in ('construction_site_packet','construction_equivalent_site_packet'):loaded[key]=value
        return value
    if set(report['packets'])!=set(release['construction_sets']):errors.append('Construction set census mismatch')
    if set(report.get('unified_packets',{}))!=set(release['construction_sets']):errors.append('Unified construction set census mismatch')
    contexts=set()
    for identity,descriptor in report['packets'].items():
        try:
            packet=read(descriptor)
            expected={i:c for i,c in release['contexts'].items() if c['construction_set_id']==identity}
            if packet!=packet_for(release,identity,expected):raise ValueError('Construction packet differs from complete frozen dependency closure')
            page=root/f'definitions/{identity}/index.html'
            if not page.exists():page=root/f'definitions/{identity}.md'
            attrs=page_attributes(page)
            if json.loads(attrs['data-construction'])!=descriptor:raise ValueError('Construction page packet binding mismatch')
            unified=report['unified_packets'][identity]
            if json.loads(attrs['data-unified'])!=unified:raise ValueError('Unified construction page packet binding mismatch')
            if read(unified)!=equivalent_packet(equivalents,identity,expected):raise ValueError('Unified packet differs from frozen equivalent release')
            if json.loads(attrs['data-contexts'])!=context_choices(release['construction_sets'][identity],expected):raise ValueError('Construction page context binding mismatch')
            if attrs['data-root']!='../../':raise ValueError('Construction page resource root mismatch')
            contexts.update(expected)
        except (KeyError,ValueError,OSError) as error:errors.append(identity+': '+str(error))
    if contexts!=set(release['contexts']):errors.append('Construction context census mismatch')
    for table,entries in report['resources'].items():
        if set(entries)!=set(release[table]):errors.append('Construction '+table+' census mismatch')
        for identity,entry in entries.items():
            try:
                if read(entry['json'])!=release[table][identity]:raise ValueError('Frozen construction resource changed')
                if entry['path']!=resource_path(table,identity):raise ValueError('Construction resource route mismatch')
                attrs=page_attributes(root/entry['path'])
                if json.loads(attrs['data-raw'])!=entry['json'] or attrs['data-root']!='../../../':raise ValueError('Construction resource page JSON binding mismatch')
            except (KeyError,ValueError,OSError) as error:errors.append(identity+': '+str(error))
    return errors
