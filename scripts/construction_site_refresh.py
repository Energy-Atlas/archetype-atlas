"""Refresh construction pages/packets in an existing verified local build only."""
import argparse
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
    names,settings=extensions();body=markdown.markdown(source,extensions=names,extension_configs=settings)
    root=Path(docs).resolve()
    def link(match):
        href=html.unescape(match[1]);u=urlsplit(href)
        if u.scheme or u.netloc or not u.path:return match[0]
        if u.path.startswith(PREFIX):return match[0]
        if u.path.startswith('/'):raise ValueError('Local link omits project prefix: '+href)
        target=(root/posixpath.dirname(source_path)/u.path).resolve()
        if not target.is_relative_to(root) or not target.is_file():raise ValueError('Unresolved/outside local documentation link: '+href)
        route=target.relative_to(root).as_posix()
        if route.endswith('.md'):route=route.removesuffix('index.md') if route.endswith('index.md') else route.removesuffix('.md')+'/'
        return 'href="'+html.escape(urlunsplit(('', '',PREFIX+route,u.query,u.fragment)),quote=True)+'"'
    body=re.sub(r'href="([^"]+)"',link,body)
    pattern=re.compile(r'(<article\b[^>]*>).*?(</article>)',re.S)
    if len(pattern.findall(existing))!=1:raise ValueError('Expected one verified page article')
    return pattern.sub(lambda m:m[1]+body+m[2],existing)


def descriptor_set(report):
    values=list(report['packets'].values())+[v['json'] for table in report['resources'].values() for v in table.values()]
    return {d['href']:d for d in values}


def refresh(docs,site,release=None,bundle=None):
    docs=Path(docs).resolve();site=Path(site).resolve();build=(ROOT/'build').resolve()
    if docs==site or any(p==build or not p.is_relative_to(build) for p in (docs,site)) or docs.is_relative_to(site) or site.is_relative_to(docs):raise ValueError('Outputs must be separate marked workspace build directories')
    if any(not (p/'site-manifest.json').is_file() or not (p/'construction-site.json').is_file() for p in (docs,site)):raise ValueError('A marked construction build is required')
    old=load_json(site/'construction-site.json')
    if load_json(docs/'construction-site.json')!=old:raise ValueError('Local source/build descriptors differ; refresh requires a consistent prior build')
    # Preflight every target before replacing any generated content.
    existing={}
    for identity,descriptor in old['packets'].items():
        path=site/f'definitions/{identity}/index.html';text=path.read_text(encoding='utf-8')
        attr=re.search(r'\bdata-construction="([^"]+)"',text)
        if attr is None or json.loads(html.unescape(attr[1]))!=descriptor:raise ValueError('Existing construction page binding differs: '+identity)
        if len(re.findall(r'<article\b',text))!=1:raise ValueError('Existing construction shell is unavailable')
        existing[identity]=text
    guide=site/'guides/construction-json/index.html';old_guide=guide.read_text(encoding='utf-8')
    if bundle is None:
        from scripts.definition_release import read_bundle
        bundle=read_bundle(ROOT/'data/definition-releases/v0.1.1')
    report=update_existing(bundle,docs,release);install_contract(docs)
    if set(report['packets'])!=set(old['packets']):raise ValueError('Focused refresh cannot change the construction definition census')
    rendered={site/f'definitions/{i}/index.html':render_page((docs/f'definitions/{i}.md').read_text(encoding='utf-8'),text,f'definitions/{i}.md',docs) for i,text in existing.items()}
    rendered[guide]=render_page((docs/'guides/construction-json.md').read_text(encoding='utf-8'),old_guide,'guides/construction-json.md',docs)
    previous=descriptor_set(old)
    for href,descriptor in descriptor_set(report).items():
        if href in previous:continue
        target=site/href;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(docs/href,target)
    for table,entries in report['resources'].items():
        for identity,entry in entries.items():
            if old['resources'][table].get(identity)==entry:continue
            path=entry['path'];target=site/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(docs/path,target)
    for path,text in rendered.items():path.write_text(text,encoding='utf-8',newline='\n')
    for name in ('construction-site.json','object-index.json','site-manifest.json','construction/coverage.json'):
        shutil.copyfile(docs/name,site/name)
    for directory in ('construction/applicability','contracts'):
        for source in (docs/directory).iterdir():
            if source.is_file():
                target=site/directory/source.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    errors=verify_delivery(site,release)
    if errors:raise ValueError('Refreshed construction delivery invalid: '+str(errors[:5]))
    return {'construction_pages':len(existing),'contexts':report['contexts'],'program_pages_regenerated':0,
            'new_json_resources':len(set(descriptor_set(report))-set(previous)),
            'validation':'Configured Markdown rendering, original theme shells and all construction packet/resource bindings verified; no full site/program build'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--docs',type=Path,default=ROOT/'build/site-docs');parser.add_argument('--site',type=Path,default=ROOT/'build/site')
    args=parser.parse_args();report=refresh(args.docs,args.site)
    path=ROOT/'build/hotel-guestroom-site-refresh.json';path.write_bytes(canonical(report));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
