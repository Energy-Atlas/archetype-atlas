"""Two-gate catalogue over immutable definitions, with selective lazy evidence."""
import gzip
import html
import json
import shutil
from pathlib import Path
from scripts.definition_contract import PRIMARY,canonical,stable_id,TABLES
from scripts.catalogue_names import building_label

GATES={'residential':'Residential','nonresidential':'Non Residential'}
KINDS={'program':'Programs','construction':'Constructions','hvac_system':'HVAC systems'}
DETAILS={'SourcePrograms':'Finest','DepartmentMixes':'Intermediate','GeneralMix':'Coarse'}


def esc(value):return html.escape(str(value),quote=True)


def write(root,path,text):
    target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(text,encoding='utf-8',newline='\n')


def generate(bundle,target,publish=True,history=None):
    root=Path(target);refs={}
    if publish:
        from scripts.query_v2 import generate_delivery
        delivery=root/'delivery/v2'
        if history and (Path(history)/'latest.json').exists():
            from scripts.query_history import restore_history
            restore_history(history,delivery,major=2)
        manifest=generate_delivery(bundle,delivery)
        for descriptor in manifest['supporting_tables'].values():
            index=json.loads(gzip.decompress((delivery/descriptor['href']).read_bytes()))
            refs.update(index['resources'])
        from scripts.query_history import export_history
        export_history(delivery,major=2)
    for name in ('definition.js','definition_core.js'):
        shutil.copyfile(Path(__file__).resolve().parents[1]/'website/assets'/name,root/'assets'/name) if (root/'assets').exists() else None
    gate='# Catalogue\n\nChoose a building family.\n\n<div class="definition-gates">'
    for key,label in GATES.items():gate+=f'<a class="definition-gate" href="{key}/">{label}<span>Browse programs, constructions and HVAC systems →</span></a>'
    gate+='</div>\n';write(root,'catalogue.md',gate)
    for gate_key,gate_label in GATES.items():
        page=f'# {gate_label}\n\n<div class="definition-kinds">'
        for kind,label in KINDS.items():page+=f'<a class="definition-kind" href="{kind}/">{label} →</a>'
        page+='</div>\n\n[Change building family](../../catalogue.md)\n';write(root,f'catalogue/{gate_key}/index.md',page)
        for kind,table in PRIMARY.items():
            rows=[r for r in bundle[table] if gate_key in r['gate']]
            entries=[]
            for r in rows:
                entries.append({k:r.get(k) for k in ('id','name','building_type','template','source_family','climate','detail','system_type','role','derivation','evidence_view','source_definition_id','available_details')} |
                    {'building':building_label(r['building_type']) if r['building_type'] else 'Shared elements',
                     'vintage':r.get('vintage') or r['template'],'path':'../../../definitions/'+r['id']+'/'})
            fields=[('search','Search')]
            if kind!='hvac_system' or len({r['building_type'] for r in rows})>1:fields.append(('building','Building type'))
            if kind=='program':fields.append(('detail','Program detail'))
            fields.append(('vintage','Vintage / standard / source'))
            if kind!='program' or any(r.get('climate') for r in rows):fields.append(('climate','Climate'))
            if kind=='hvac_system':fields.append(('system_type','System type'))
            if kind=='construction':fields.append(('role','Element role'))
            fields.append(('evidence_view','Evidence view'))
            page=f'# {gate_label} / {KINDS[kind]}\n\n[Change kind](../index.md) · [Change building family](../../../catalogue.md)\n\n'
            page+='<section class="definition-finder" data-index="entries.json"><form class="definition-filters">'
            for key,label in fields:
                page+=f'<label>{label}'
                if key=='search':page+='<input type="search" data-filter="search" placeholder="Name or ID">'
                else:
                    values=sorted({str(v) for r in entries for v in (r.get('available_details',[]) if key=='detail' else [r.get(key)]) if v is not None})
                    page+=f'<select data-filter="{key}"><option value="">All</option>'
                    page+=''.join(f'<option value="{esc(v)}">{esc(DETAILS.get(v,v))}</option>' for v in values)
                    page+='</select>'
                page+='</label>'
            page+='<button type="reset">Reset filters</button></form><p class="definition-status" role="status">Use the entry list below, or enable JavaScript for search.</p><div class="definition-results"></div><button class="definition-more" hidden>Show more</button></section>'
            page+='\n\n<details class="definition-static"><summary>All entries — accessible without JavaScript</summary><ul>'
            page+=''.join(f'<li><a href="../../../definitions/{esc(r["id"])}/">{esc(r["name"])} · {esc(r["vintage"])} · {esc(r["evidence_view"])}</a></li>' for r in entries)
            page+='</ul></details>\n'
            write(root,f'catalogue/{gate_key}/{kind}/index.md',page)
            write(root,f'catalogue/{gate_key}/{kind}/entries.json',canonical(entries).decode())
    ids={r['id'] for table in PRIMARY.values() for r in bundle[table]}
    supporting={r['id']:(table,r) for table in TABLES if table not in PRIMARY.values() for r in bundle[table]}
    for table in PRIMARY.values():
        for row in bundle[table]:
            page=f'# {esc(row["name"])}\n\n[Catalogue](../catalogue.md)\n\n'
            page+=f'<p class="definition-id"><code>{esc(row["id"])}</code> <button class="definition-copy" data-id="{esc(row["id"])}">Copy ID</button></p>\n\n'
            page+=f'{esc(row["evidence_view"])} · {esc(row["derivation"])} · {esc(row["template"])} · {esc(row["source_family"])}\n\n'
            for key in ('role','scope','system_type','assembly_status','topology_status','fallback_policy','unresolved_reason'):
                if row.get(key):page+=f'**{key.replace("_"," ").capitalize()}:** {esc(row[key])}\n\n'
            page+='**Required consumer inputs:** '+esc(', '.join(row['required_inputs']) or 'See individual fields and component requirements')+'\n\n'
            if row['parameters']:
                page+='| Parameter | Value | Unit | Status |\n|---|---|---|---|\n'
                for name,p in row['parameters'].items():
                    page+=f'| {esc(name)} | {esc(p["value"] if p["value"] is not None else "Unknown")} | {esc(p["unit"])} | {esc(p["status"])} |\n'
                page+='\n'
            if row.get('loads'):
                page+='| Load | Magnitude | Unit | Basis | Scope |\n|---|---|---|---|---|\n'
                for load in row['loads']:
                    page+=f'| {esc(load["quantity"])} | {esc(load["value"] if load["value"] is not None else "Unknown")} | {esc(load["unit"])} | {esc(load["basis"])} | {esc(load.get("scope","program"))} |\n'
                page+='\nMagnitude and determined schedule are separate requirements. Shared service identities are instantiated once.\n\n'
            if row.get('unresolved_loads'):
                page+='**Unresolved mixed demands:** '+esc('; '.join(l['quantity']+': '+l['reason'] for l in row['unresolved_loads']))+'\n\n'
            if row.get('unresolved_options'):
                page+=f'<details><summary>Unresolved source options ({len(row["unresolved_options"])})</summary><ul>'
                page+=''.join('<li>'+esc(o['parameter']+' / '+o['option']+': '+o['reason'])+'</li>' for o in row['unresolved_options'])+'</ul></details>\n\n'
            if row.get('layers'):
                page+='| Layer (outside → inside) | Model | Thickness m | Conductivity W/(m K) | Resistance m2 K/W |\n|---|---|---|---|---|\n'
                for layer in row['layers']:
                    p=layer['properties']
                    page+='| '+ ' | '.join(esc(p.get(k,'Unknown')) for k in ('name','model','thickness_m','conductivity_W_m_K','resistance_m2_K_W'))+' |\n'
                page+='\n'
            links=set(row.get('evidence_ids',[]))|set(row.get('component_ids',[]))|set(row.get('service_ids',[]))|set(row.get('schedule_ids',[]))
            for p in row['parameters'].values():
                links.add(p['evidence_id'])
                if p['unit']=='schedule reference' and p['value']:links.add(p['value'])
            for load in row.get('loads',[]):
                links.add(load['evidence_id'])
                if load['schedule_id']:links.add(load['schedule_id'])
            for layer in row.get('layers',[]):links.add(layer['material_id'])
            if row.get('composition_id'):links.add(row['composition_id'])
            for key in ('air_exchange','source_set','source_descriptor'):
                if row.get(key):links.add(stable_id('detail',{'id':row['id'],'field':key}))
            for values in row.get('elements',{}).values():
                for identity in values:
                    if identity in ids:page+=f'[Element `{identity}`]({identity}.md)\n\n'
            for identity in sorted(links):
                if identity in refs:
                    descriptor=refs[identity]
                    table,item=supporting.get(identity,('details',{}))
                    title=table.replace('_',' ').capitalize()+': '+str(item.get('name') or item.get('source_channel') or item.get('role') or identity)
                    page+=f'<details class="definition-resource" data-ref="{esc(json.dumps(descriptor,separators=(",",":")))}" data-root="../../delivery/v2/"><summary>{esc(title)}</summary><button>Load verified resource</button><pre tabindex="0"></pre></details>\n'
            page+='\n[Definition contract and limitations](../guides/definitions.md)\n'
            write(root,f'definitions/{row["id"]}.md',page)
