"""Refresh construction pages/packets in an existing verified local build only."""
import argparse
import gzip
import html
import json
import posixpath
import re
import shutil
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit

import markdown
import yaml
from scripts.common import ROOT,load_json
from scripts.definition_contract import canonical
from scripts.construction_site import update_existing,install_contract,verify_delivery,PREFIX
from scripts.site_asset_versions import version_asset_urls
from website.hooks.card_icons import on_page_content as inline_card_icons


@lru_cache(maxsize=1)
def extensions():
    config=yaml.safe_load((ROOT/'mkdocs.yml').read_text(encoding='utf-8'))
    names=[];settings={}
    for item in config['markdown_extensions']:
        if isinstance(item,str):names.append(item)
        else:
            for name,value in item.items():names.append(name);settings[name]=value
    return names,settings


def render_page(source,existing,source_path,docs):
    """Use the configured Markdown renderer and retain the verified theme shell."""
    if source.startswith('---\n'):source=source.split('\n---\n',1)[1]
    names,settings=extensions();body=markdown.markdown(source,extensions=names,extension_configs=settings)
    body=inline_card_icons(body,page=None,config=None,files=None)
    root=Path(docs).resolve()
    def link(match):
        href=html.unescape(match[1]);u=urlsplit(href)
        if u.scheme or u.netloc or not u.path:return match[0]
        if u.path.startswith(PREFIX):return match[0]
        if u.path.startswith('/'):raise ValueError('Local link omits project prefix: '+href)
        target=(root/posixpath.dirname(source_path)/u.path).resolve()
        if target.is_relative_to(root) and not target.is_file():
            target=next((p for p in (target/'index.md',target.with_suffix('.md'),target/'index.html') if p.is_file()),target)
        if not target.is_relative_to(root) or not target.is_file():raise ValueError('Unresolved/outside local documentation link: '+href)
        route=target.relative_to(root).as_posix()
        if route.endswith('.md'):route=route.removesuffix('index.md') if route.endswith('index.md') else route.removesuffix('.md')+'/'
        return 'href="'+html.escape(urlunsplit(('', '',PREFIX+route,u.query,u.fragment)),quote=True)+'"'
    body=re.sub(r'href="([^"]+)"',link,body)
    pattern=re.compile(r'(<article\b[^>]*>).*?(</article>)',re.S)
    if len(pattern.findall(existing))!=1:raise ValueError('Expected one verified page article')
    return version_asset_urls(pattern.sub(lambda m:m[1]+body+m[2],existing))


def descriptor_set(report):
    values=list(report['packets'].values())+list(report.get('unified_packets',{}).values())+[v['json'] for table in report['resources'].values() for v in table.values()]
    return {d['href']:d for d in values}


def refresh(docs,site,release=None,bundle=None):
    docs=Path(docs).resolve();site=Path(site).resolve();build=(ROOT/'build').resolve()
    if docs==site or any(p==build or not p.is_relative_to(build) for p in (docs,site)) or docs.is_relative_to(site) or site.is_relative_to(docs):raise ValueError('Outputs must be separate marked workspace build directories')
    if any(not (p/'site-manifest.json').is_file() or not (p/'construction-site.json').is_file() for p in (docs,site)):raise ValueError('A marked construction build is required')
    old=load_json(site/'construction-site.json')
    if load_json(docs/'construction-site.json')!=old:raise ValueError('Local source/build descriptors differ; refresh requires a consistent prior build')
    from scripts.construction_distribution import load_current_release,OUTPUT as distribution
    release=release or load_current_release()
    retired=set(load_json(distribution/'selection.json')['retired_space_type_ids'])
    removed=set(old['packets'])-set(release['construction_sets'])
    if not removed<=retired or set(release['construction_sets'])-set(old['packets']):raise ValueError('Focused refresh only permits the approved space-type retirement')
    # Preflight every target before replacing any generated content.
    existing={}
    for identity,descriptor in old['packets'].items():
        path=site/f'definitions/{identity}/index.html';text=path.read_text(encoding='utf-8')
        attr=re.search(r'\bdata-construction="([^"]+)"',text)
        if attr is None or json.loads(html.unescape(attr[1]))!=descriptor:raise ValueError('Existing construction page binding differs: '+identity)
        if len(re.findall(r'<article\b',text))!=1:raise ValueError('Existing construction shell is unavailable')
        existing[identity]=text
        if identity in removed:
            packet=json.loads(gzip.decompress((site/descriptor['href']).read_bytes()))
            if packet['profile']['id']!=identity or packet['profile']['scope']!='space_type':raise ValueError('Retired route is not a source space-type packet')
    guide=site/'guides/construction-json/index.html';old_guide=guide.read_text(encoding='utf-8')
    if bundle is None:
        from scripts.definition_release import read_bundle
        bundle=read_bundle(ROOT/'data/definition-releases/v0.1.1')
    report=update_existing(bundle,docs,release);install_contract(docs)
    if set(report['packets'])!=set(release['construction_sets']):raise ValueError('Unexpected construction definition census')
    rendered={site/f'definitions/{i}/index.html':render_page((docs/f'definitions/{i}.md').read_text(encoding='utf-8'),text,f'definitions/{i}.md',docs) for i,text in existing.items() if i not in removed}
    rendered[guide]=render_page((docs/'guides/construction-json.md').read_text(encoding='utf-8'),old_guide,'guides/construction-json.md',docs)
    from scripts.construction_site import projection,library_guide,write
    from scripts.active_site import landing
    if (docs/'index.md').is_file():write(docs,'index.md',landing(projection(release,bundle)))
    if (docs/'guides/definitions.md').is_file():write(docs,'guides/definitions.md',library_guide())
    for name in ('index.md','guides/definitions.md','catalogue/residential/construction/index.md','catalogue/nonresidential/construction/index.md'):
        target=site/('index.html' if name=='index.md' else name.removesuffix('index.md')+'index.html' if name.endswith('index.md') else name.removesuffix('.md')+'/index.html')
        if target.is_file() and (docs/name).is_file():rendered[target]=render_page((docs/name).read_text(encoding='utf-8'),target.read_text(encoding='utf-8'),name,docs)
    previous=descriptor_set(old)
    for href,descriptor in descriptor_set(report).items():
        if href in previous:continue
        target=site/href;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(docs/href,target)
    for table,entries in report['resources'].items():
        for identity,entry in entries.items():
            if old['resources'][table].get(identity)==entry:continue
            path=entry['path'];target=site/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(docs/path,target)
    for path,text in rendered.items():path.write_text(text,encoding='utf-8',newline='\n')
    from scripts.construction_site import repair_retired_references,prune_construction_history,remove_empty_retired_routes
    repaired=repair_retired_references(site,bundle,release)
    for identity in removed:
        raw=re.search(r'\bdata-raw="([^"]+)"',existing[identity])
        descriptors=[old['packets'][identity]]+([json.loads(html.unescape(raw[1]))] if raw else [])
        for root in (docs,site):
            for path in (root/f'definitions/{identity}.md',root/f'definitions/{identity}/index.html'):
                if not path.resolve().is_relative_to(root):raise ValueError('Retired route escapes generated tree')
                path.unlink(missing_ok=True)
            for d in descriptors:
                if d['href'] in descriptor_set(report):continue
                if not re.fullmatch(r'json/[a-f0-9]{64}\.json\.gz',d['href']):raise ValueError('Unsafe retired packet path')
                (root/d['href']).unlink(missing_ok=True)
    for root in (docs,site):remove_empty_retired_routes(root,retired)
    search=site/'search/search_index.json'
    if search.is_file() and removed:
        locations={'definitions/'+identity for identity in removed}
        data=load_json(search);data['docs']=[d for d in data['docs'] if d.get('location','').split('#')[0].rstrip('/') not in locations]
        search.write_bytes(canonical(data))
    registry=load_json(docs/'object-index.json')
    for identity in retired:registry.pop(identity,None)
    (docs/'object-index.json').write_bytes(canonical(registry))
    for name in ('construction-site.json','object-index.json','site-manifest.json','construction/coverage.json'):
        shutil.copyfile(docs/name,site/name)
    for directory in ('construction/applicability','construction/distribution','contracts'):
        for source in (docs/directory).iterdir():
            if source.is_file():
                target=site/directory/source.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    for source in (docs/'examples/construction').glob('*.json'):
        target=site/'examples/construction'/source.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    # Only construction interaction assets change; cached program pages and
    # schedule assets remain untouched by this focused renderer.
    for name in ('construction.js','construction_core.js','object.js','site.css'):
        for root in (docs,site):
            target=root/'assets'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'website/assets'/name,target)
    for gate in ('residential','nonresidential'):
        path=f'catalogue/{gate}/construction/entries.json';target=site/path
        if target.parent.is_dir():shutil.copyfile(docs/path,target)
    if (docs/'delivery/v2/latest.json').is_file() and (site/'delivery/v2/latest.json').is_file():
        from scripts.query_v2 import QueryClient
        from scripts.query_delivery import references
        client=QueryClient(docs/'delivery/v2');pending=[client.manifest_ref];seen=set()
        while pending:
            d=pending.pop();href=d['href']
            if href in seen:continue
            seen.add(href);target=site/'delivery/v2'/href
            if target.exists():continue
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(docs/'delivery/v2'/href,target)
            value=client.fetch(d);pending.extend(references(value))
        shutil.copyfile(docs/'delivery/v2/latest.json',site/'delivery/v2/latest.json')
        prune_construction_history(site/'delivery/v2')
    errors=verify_delivery(site,release)
    if errors:raise ValueError('Refreshed construction delivery invalid: '+str(errors[:5]))
    return {'construction_pages':len(report['packets']),'retired_space_type_pages':len(removed),'contexts':report['contexts'],'program_pages_regenerated':0,
            'source_reference_pages_repaired':len(repaired),
            'new_json_resources':len(set(descriptor_set(report))-set(previous)),
            'validation':'Configured Markdown rendering, original theme shells and all construction packet/resource bindings verified; no full site/program build'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--docs',type=Path,default=ROOT/'build/site-docs');parser.add_argument('--site',type=Path,default=ROOT/'build/site')
    args=parser.parse_args();report=refresh(args.docs,args.site)
    path=ROOT/'build/construction-site-refresh.json';path.write_bytes(canonical(report));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
