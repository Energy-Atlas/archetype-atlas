"""Local-only browser checks of separate construction exports; no site build."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlencode

from scripts.common import ROOT
from scripts.construction_foundation_release import export_pair,load_release,pilot_contexts
from scripts.site_smoke import serve


def smoke_cases():
    """Read representative current exports; never regenerate source models or fits."""
    from scripts.construction_foundation_export import session
    source=session().source;frozen=load_release();pilots=pilot_contexts()
    names=('medium-office-2019-3B','warehouse-2019-3B','residential-conditioned-basement',
           'residential-above-apartment','small-data-centre-2019')
    ids=[pilots[name] for name in names]
    ids.append(next(c['id'] for c in source['contexts'].values() if c['reference_id']=='90.1-2019/Hospital'
        and c['climate_zone']=='3B' and source['construction_sets'][c['construction_set_id']]['source']['building_type']=='Hospital'))
    cases=[]
    for cid in ids:
        detailed,unified=export_pair(cid,release=frozen)
        cases.append({'context':source['contexts'][cid],'detailed':detailed,'unified':unified})
    return cases


def run(site,screenshots):
    from playwright.sync_api import sync_playwright,expect
    cases=smoke_cases()
    server,base=serve(site);results=[];screenshots.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            context=browser.new_context(viewport={'width':1440,'height':1000},permissions=['clipboard-read','clipboard-write'])
            for index,case in enumerate(cases):
                c=case['context'];detailed=case['detailed'];unified=case['unified']
                page=context.new_page();errors=[];requests=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('request',lambda request:requests.append(request.url) if '/json/' in request.url else None)
                route='definitions/'+c['construction_set_id']+'/?'+urlencode({'climate':c['climate_zone'],'reference':c['reference_id']})
                page.goto(base+route,wait_until='networkidle')
                expect(page.locator('.construction-reference')).to_have_value(c['reference_id'])
                summary=page.locator('.construction-ground-summary')
                configuration=detailed['foundation_ground']['configuration']['type']
                expect(summary).to_contain_text('Configuration: '+configuration)
                methods=sorted({m['model'] for m in detailed['foundation_ground']['methods'].values()})
                for model in methods:expect(summary).to_contain_text(model)
                if not methods:expect(summary).to_contain_text('no direct ground contact')
                assert len(requests)==1,'Selected foundation summary should load one verified detailed packet'
                for mode,expected in (('detailed',detailed),('unified',unified)):
                    page.locator('.construction-representation').select_option(mode)
                    if not page.locator('.object-source').evaluate('(el)=>el.open'):
                        page.locator('.object-source summary').click()
                    expect(page.locator('.object-source pre')).to_contain_text('"kind": "'+expected['kind']+'"')
                    preview=json.loads(page.locator('.object-source pre').inner_text())
                    assert preview==expected,(mode,'preview differs from frozen export')
                    expect(page.get_by_role('button',name='Download',exact=False)).to_have_count(0)
                    # Copy buttons have fixed representations, independent of preview.
                    page.locator('.construction-representation').select_option('unified' if mode=='detailed' else 'detailed')
                    page.get_by_role('button',name='Copy '+mode+' JSON',exact=True).click()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    expect(page.locator('.object-status')).to_contain_text(mode+' construction JSON copied.')
                    assert json.loads(page.evaluate('navigator.clipboard.readText()'))==expected
                    page.locator('.construction-representation').select_option(mode)
                assert len(requests)==2,'Each representation must load once and reuse its verified packet'
                assert page.locator('.object-json').get_attribute('data-raw') is None
                # Browser guard must reject a missing equivalent material resource.
                assert page.evaluate("""async () => {
                    const packet=structuredClone(await AtlasObjects.load(document.querySelector('.object-json'),'unified'));
                    const id=Object.keys(packet.contexts)[0],body=packet.component_sets[packet.contexts[id].component_set_id];
                    const aid=Object.values(body.components).find(c=>c.status==='ready').assembly_id;
                    delete packet.assemblies[aid];
                    try {ConstructionCore.hydrateUnified(packet,id);return false;} catch(e) {return e.message.includes('Missing unified assembly');}
                }""")
                assert page.evaluate("""async () => {
                    const packet=structuredClone(await AtlasObjects.load(document.querySelector('.object-json'),'unified'));
                    const id=Object.keys(packet.contexts)[0];delete packet.foundation.contexts[id];
                    try {ConstructionCore.hydrateUnified(packet,id);return false;} catch(e) {return e.message.includes('Missing selected foundation');}
                }""")
                if index==0:
                    for scheme in ('light','dark'):
                        page.emulate_media(color_scheme=scheme)
                        # Compact pages choose their theme at initial load.
                        page.reload(wait_until='networkidle')
                        expect(page.locator('html')).to_have_attribute('data-md-color-scheme','slate' if scheme=='dark' else 'default')
                        page.screenshot(path=str(screenshots/(scheme+'-desktop.png')),full_page=False)
                    page.set_viewport_size({'width':390,'height':844})
                    page.emulate_media(color_scheme='light');page.reload(wait_until='networkidle')
                    page.locator('.object-json').scroll_into_view_if_needed()
                    page.screenshot(path=str(screenshots/'mobile.png'),full_page=False)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Mobile page overflow'
                    expect(page.get_by_role('button',name='Copy detailed JSON',exact=True)).to_be_visible()
                    expect(page.get_by_role('button',name='Copy unified JSON',exact=True)).to_be_visible()
                    # Shared representation URL restores both selection and mode.
                    page.reload(wait_until='networkidle')
                    expect(page.locator('.construction-representation')).to_have_value('unified')
                    expect(page.locator('.construction-reference')).to_have_value(c['reference_id'])
                assert not errors,errors
                results.append({'context_id':c['id'],'reference':c['reference_id'],'exports':['detailed','unified'],
                                'schema_versions':['3.0.0','2.0.0'],'foundation_configuration':configuration,
                                'ground_methods':methods,'preview_copy_parity':True,
                                'initial_summary_packet_requests':1,'representation_packet_requests':2})
                page.close()
            # Unsupported context must keep both copy actions disabled.
            page=context.new_page();page.goto(base+'definitions/'+cases[0]['context']['construction_set_id']+'/?climate=invalid')
            expect(page.get_by_role('button',name='Copy detailed JSON',exact=True)).to_be_disabled()
            expect(page.get_by_role('button',name='Copy unified JSON',exact=True)).to_be_disabled()
            expect(page.locator('.object-status')).to_contain_text('Unsupported')
            browser.close()
    finally:server.shutdown();server.server_close()
    return {'cases':results,'desktop_mobile_light_dark':True,'unsupported_context_blocked':True,
            'scope':'Local construction controls only; no annual accuracy or broad program/site build'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site',type=Path,default=ROOT/'build/site')
    parser.add_argument('--screenshots',type=Path,default=ROOT/'build/unified-construction-site-screenshots')
    args=parser.parse_args();report=run(args.site,args.screenshots)
    (ROOT/'build/unified-construction-browser.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
