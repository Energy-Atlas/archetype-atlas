"""Focused local browser acceptance of frozen construction delivery; no deployment."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlencode

from scripts.common import ROOT,load_json
from scripts.construction_set_release import hydrate_context
from scripts.construction_distribution import load_current_release as load_release
from scripts.site_smoke import serve


def smoke(root,screenshots):
    from playwright.sync_api import sync_playwright,expect
    root=Path(root);screenshots=Path(screenshots);screenshots.mkdir(parents=True,exist_ok=True)
    release=load_release();report=load_json(root/'construction-site.json');checks=[]
    server,base=serve(root)
    try:
        with sync_playwright() as runtime:
            browser=runtime.chromium.launch()
            context=browser.new_context(viewport={'width':1280,'height':900},permissions=['clipboard-read','clipboard-write'])
            context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
            page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            try:
                medium='construction-93cb2afe2fe44c8e084b9b99';residential='construction-0079ce7b163bdb1bd0154dbe'
                page.goto(base+'catalogue/nonresidential/construction/?'+urlencode({'building':'Medium Office','climate':'4A','vintage':'90.1-2019','evidence_view':'source'}))
                expect(page.locator('.definition-status')).to_contain_text('matching entries')
                expect(page.locator('[data-filter="scope"], [data-filter="evidence_view"]')).to_have_count(0)
                assert 'evidence_view' not in page.url
                link=page.locator('.definition-result a[href*="'+medium+'"]')
                expect(link).to_have_count(1);link.click()
                expect(page.locator('.construction-climate')).to_have_value('4A')
                for identity,climate in ((medium,'4A'),(residential,'5A')):
                    if identity==residential:
                        page.goto(base+'catalogue/residential/construction/?'+urlencode({'building':'Single-family Detached','vintage':'<1940','climate':'5A','evidence_view':'source'}))
                        expect(page.locator('.definition-status')).to_contain_text('matching entries')
                        link=page.locator('.definition-result a[href*="'+identity+'"]');expect(link).to_have_count(1);link.click()
                    expect(page.locator('.object-status')).to_contain_text('Source-ready')
                    reference=page.locator('.construction-reference').input_value()
                    selected=next(c for c in release['contexts'].values() if c['construction_set_id']==identity and c['climate_zone']==climate and c['reference_id']==reference)
                    expected=hydrate_context(release,selected['id'])
                    page.locator('.object-source summary').click();expect(page.locator('.object-status')).to_contain_text('Complete construction JSON v2')
                    assert json.loads(page.locator('.object-source pre').inner_text())==expected
                    page.locator('.object-copy').click();page.get_by_role('button',name='Copy construction JSON',exact=True).click()
                    expect(page.locator('.object-status')).to_contain_text('copied')
                    assert json.loads(page.evaluate('navigator.clipboard.readText()'))==expected
                    page.reload();expect(page.locator('.construction-climate')).to_have_value(climate)
                    page.screenshot(path=str(screenshots/(identity+'.png')))
                    checks.append(identity+': filtered selection, preview, exact frozen copy and reload')
                from scripts.construction_hotel_applicability import validate_extensions
                for identity in ('construction-c6985aaff2845cac856a73ab','construction-3d530eb85c2c6cd7c207e60d'):
                    page.goto(base+'definitions/'+identity+'/?climate=4A')
                    expect(page.locator('main')).to_contain_text('Atlas-added GuestRoom applicability')
                    policy=page.get_by_role('link',name='Policy',exact=True)
                    assert page.request.get(policy.evaluate('e=>e.href')).ok
                    page.locator('.object-copy').click();page.get_by_role('button',name='Copy construction JSON',exact=True).click()
                    expect(page.locator('.object-status')).to_contain_text('copied')
                    value=json.loads(page.evaluate('navigator.clipboard.readText()'));assert validate_extensions(value)>0
                    selected=next(c for c in release['contexts'].values() if c['construction_set_id']==identity and c['climate_zone']=='4A')
                    assert value==hydrate_context(release,selected['id'])
                    page.set_viewport_size({'width':390,'height':844})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),'Hotel mobile overflow'
                    page.screenshot(path=str(screenshots/(identity+'-hotel-mobile.png')))
                    page.set_viewport_size({'width':1280,'height':900})
                checks.append('Hotel generic attachment/inheritance: exact copied JSON, Atlas provenance and working policy downloads')
                # No standalone partial sets, including old direct routes or current query results.
                assert len(release['construction_sets'])==177 and len(release['contexts'])==3320
                for gate in ('residential','nonresidential'):
                    entries=page.request.get(base+'catalogue/'+gate+'/construction/entries.json').json()
                    assert all(r['scope']!='space_type' for r in entries)
                assert page.request.get(base+'definitions/construction-1d0774872c8801caa0afdd44/').status==404
                archive=page.request.get(base+'construction/distribution/source-evidence.json').json()
                assert archive['consumer_selectable'] is False and len(archive['contexts'])==8
                from scripts.query_v2 import QueryClient
                query=QueryClient(root/'delivery/v2').query('construction',{},['scope'])
                assert query['match_count']==177 and all(r['fields']['scope']!='space_type' for r in query['records'])
                page.goto(base+'definitions/'+medium+'/?climate=99Z')
                expect(page.locator('.object-status')).to_contain_text('Unsupported construction climate')
                page.locator('.object-copy').click();expect(page.get_by_role('button',name='Copy construction JSON',exact=True)).to_be_disabled();page.keyboard.press('Escape')
                checks.append('177 complete sets; standalone routes retired; eight evidence contexts retained; current query has no partial sets; unsupported climates rejected')
                # Packet corruption / missing resource cannot reach the clipboard.
                for status,body,message in ((200,b'x'*report['packets'][medium]['size_bytes'],'checksum'),(404,b'missing','404')):
                    page.goto(base+'definitions/'+medium+'/?climate=4A')
                    page.route('**/json/*.json.gz',lambda route,request,status=status,body=body:route.fulfill(status=status,body=body))
                    page.evaluate("navigator.clipboard.writeText('sentinel')")
                    page.locator('.object-copy').click();page.get_by_role('button',name='Copy construction JSON',exact=True).click()
                    expect(page.locator('.object-dialog [role="status"]')).to_contain_text(message)
                    assert page.evaluate('navigator.clipboard.readText()')=='sentinel'
                    page.keyboard.press('Escape');page.unroute('**/json/*.json.gz')
                checks.append('Corrupt and missing packets fail without copying')
                # Every source-only recipe remains inspectable, with material/evidence links.
                source_only=release['metadata']['source_table_only_assembly_ids'][0]
                resource=report['resources']['assemblies'][source_only]
                page.goto(base+resource['path']);expect(page.locator('main')).to_contain_text('no recovered prototype mapping')
                page.locator('.object-source summary').click();expect(page.locator('.object-source pre')).to_contain_text(source_only)
                assert json.loads(page.locator('.object-source pre').inner_text())==release['assemblies'][source_only]
                page.locator('table a').first.click();expect(page.locator('h1')).to_be_visible()
                page.locator('table a').first.click();expect(page.locator('main')).to_contain_text('source_locator')
                checks.append('Source-only assembly, material and evidence routes with verified source JSON')
                for scheme in ('light','dark'):
                    page.emulate_media(color_scheme=scheme);page.set_viewport_size({'width':390,'height':844})
                    palette='slate' if scheme=='dark' else 'default'
                    page.evaluate("scheme=>localStorage.setItem('/archetype-atlas/.__palette',JSON.stringify({index:scheme==='slate'?1:0,color:{scheme,primary:'custom',accent:'custom'}}))",palette)
                    for suffix,name in (('catalogue/nonresidential/construction/?building=Medium%20Office&climate=4A&vintage=90.1-2019','finder'),('definitions/'+medium+'/?climate=4A','set')):
                        page.goto(base+suffix)
                        expect(page.locator('.definition-status' if name=='finder' else '.object-status')).not_to_be_empty()
                        expect(page.locator('[data-md-color-scheme="'+palette+'"]').first).to_be_visible()
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),name+' mobile overflow'
                        page.screenshot(path=str(screenshots/(name+'-mobile-'+scheme+'.png')))
                assert not errors,errors
                checks.append('Light/dark mobile layouts, keyboard cancellation and no JavaScript errors')
            finally:context.close()
            manual=browser.new_context();manual.add_init_script("Object.defineProperty(navigator,'clipboard',{value:{writeText:async()=>{throw new Error('denied')}}});")
            try:
                page=manual.new_page();page.goto(base+'definitions/'+medium+'/?climate=4A')
                page.locator('.object-copy').click();page.get_by_role('button',name='Copy construction JSON',exact=True).click()
                expect(page.locator('.object-dialog textarea')).to_be_visible()
                assert json.loads(page.locator('.object-dialog textarea').input_value())['schema_version']=='2.0.0'
                checks.append('Clipboard denial exposes complete selectable JSON')
            finally:manual.close()
            offline=browser.new_context(java_script_enabled=False)
            try:
                page=offline.new_page();page.goto(base+'catalogue/nonresidential/construction/')
                page.locator('.definition-static summary').click();expect(page.locator('.definition-static a').first).to_be_visible()
                page.locator('.definition-static a').first.click();expect(page.locator('h1')).to_be_visible()
                page.goto(base+'construction/assemblies/');page.locator('.definition-static summary').click()
                expect(page.locator('.definition-static a')).to_have_count(len(release['assemblies']))
                checks.append('No-JavaScript construction-set and complete assembly lists')
            finally:offline.close();browser.close()
        receipt={'checks':checks,'construction_sets':report['definitions'],'contexts':report['contexts'],'screenshots':str(screenshots),'remote_actions':False}
        (screenshots/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(receipt,indent=2))
    finally:server.shutdown();server.server_close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site',type=Path,default=ROOT/'build/site')
    parser.add_argument('--screenshots',type=Path,default=ROOT/'build/construction-site-screenshots')
    args=parser.parse_args();smoke(args.site,args.screenshots)


if __name__=='__main__':main()
