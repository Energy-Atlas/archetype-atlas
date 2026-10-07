"""Real-browser checks of the local active site; no hosted workflow required."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
try:
    from playwright.sync_api import sync_playwright, expect
    import yaml
except ModuleNotFoundError:
    raise unittest.SkipTest('Install requirements-site.txt and requirements-browser.txt for browser checks')
from scripts.active_site import generate_active_site
from scripts.common import ROOT, load_json
from scripts.site_smoke import serve
from tests.test_active_site import pilot_bundle


class ObjectBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bundle = pilot_bundle()
        bundle['schedules'][0]['rules'] += [
            {'day_types': 'Wknd', 'start_date': '2000-01-01', 'end_date': '2000-12-31', 'values': [.2]},
            {'day_types': 'SmrDsn', 'start_date': '2000-01-01', 'end_date': '2000-12-31', 'values': [.8]}]
        annual = load_json(ROOT / 'docs/examples/program-json-v2/residential-annual.schedule.json')
        bundle['schedules'].append({'id': 'annual-pilot', 'source_channel': 'occupants', 'units': '1',
            'time_resolution_minutes': 60, 'calendar': {'year': 2007}, 'annual_values': annual['values']})
        cls.docs, cls.site = ROOT / 'build/dto-browser-docs', ROOT / 'build/dto-browser-site'
        generate_active_site(bundle, cls.docs)
        config = yaml.safe_load((ROOT / 'mkdocs.yml').read_text())
        config.update(docs_dir=str(cls.docs), site_dir=str(cls.site))
        config['hooks'] = [str(ROOT / p) for p in config['hooks']]
        config['theme']['custom_dir'] = str(ROOT / config['theme']['custom_dir'])
        cfg = ROOT / 'build/dto-browser.yml';cfg.write_text(yaml.safe_dump(config, sort_keys=False))
        run = subprocess.run([sys.executable, '-m', 'mkdocs', 'build', '--strict', '-f', str(cfg)], cwd=ROOT, capture_output=True, text=True)
        if run.returncode: raise AssertionError(run.stdout + run.stderr)
        cls.server, cls.base = serve(cls.site)
        cls.runtime = sync_playwright().start();cls.browser = cls.runtime.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.runtime.stop();cls.server.shutdown();cls.server.server_close()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1280, 'height': 900}, permissions=['clipboard-read', 'clipboard-write'])
        self.page = self.context.new_page();self.errors=[]
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()

    def program(self): self.page.goto(self.base + 'definitions/program-pilot/')

    def test_copy_before_expansion_copies_complete_raw_and_defaulted_json(self):
        self.program();page=self.page
        page.locator('.object-copy').click()
        page.locator('.object-default-info summary').click()
        expect(page.locator('.object-dialog')).to_contain_text('atlas-program-defaults-1.0.0')
        expect(page.locator('.object-default-info pre')).to_contain_text('required_bindings')
        page.get_by_role('button', name='Copy raw', exact=True).click()
        expect(page.locator('.object-status')).to_contain_text('copied')
        raw=json.loads(page.evaluate('navigator.clipboard.readText()'))
        self.assertEqual(raw['export_mode'], 'raw');self.assertIsNone(raw['loads'][0]['value'])
        self.assertIn('schedule-pilot',raw['schedules'])
        page.locator('.object-copy').click();page.get_by_role('button',name='Copy with defaults',exact=True).click()
        expect(page.locator('.object-status')).to_contain_text('copied')
        ready=json.loads(page.evaluate('navigator.clipboard.readText()'))
        self.assertEqual(ready['export_mode'],'defaulted');self.assertEqual(ready['loads'][0]['value'],0)
        self.assertTrue(ready['assumptions']);self.assertEqual(self.errors,[])

    def test_escape_restores_focus_without_copying(self):
        self.program();page=self.page
        page.locator('.object-copy').click()
        expect(page.get_by_role('button',name='Copy raw',exact=True)).to_be_focused()
        page.keyboard.press('Escape');expect(page.locator('.object-dialog')).to_have_count(0)
        expect(page.locator('.object-copy')).to_be_focused()

    def test_active_smoke_exercises_pilot_gates_copy_plots_mobile_and_nojs(self):
        from scripts.active_smoke import active_smoke
        active_smoke(self.browser, self.base)

    def test_clipboard_denial_offers_selectable_complete_json(self):
        self.page.add_init_script("Object.defineProperty(navigator,'clipboard',{value:{writeText:async()=>{throw new Error('denied')}}});")
        self.program();page=self.page
        page.locator('.object-copy').click();page.get_by_role('button',name='Copy raw',exact=True).click()
        expect(page.locator('.object-dialog textarea')).to_be_visible()
        value=json.loads(page.locator('.object-dialog textarea').input_value())
        self.assertEqual(value['id'],'program-pilot')
        expect(page.locator('.object-dialog-status')).to_contain_text('clipboard')

    def test_bad_checksum_never_reaches_clipboard(self):
        self.program();page=self.page
        desc=json.loads(page.locator('.object-json').get_attribute('data-raw'))
        page.route('**/json/*.json.gz',lambda route:route.fulfill(status=200,body=b'x'*desc['size_bytes']))
        page.evaluate("navigator.clipboard.writeText('sentinel')")
        page.locator('.object-copy').click();page.get_by_role('button',name='Copy raw',exact=True).click()
        expect(page.locator('.object-dialog-status')).to_contain_text('checksum')
        self.assertEqual(page.evaluate('navigator.clipboard.readText()'),'sentinel')

    def test_linked_schedule_has_step_plot_heatmap_and_day_selection(self):
        self.program();page=self.page
        page.get_by_role('link',name='Office week',exact=True).click()
        expect(page).to_have_url(self.base+'objects/schedule-pilot/')
        page.locator('.schedule-load').click()
        expect(page.locator('.schedule-status')).to_contain_text('365 days')
        self.assertEqual(page.locator('.schedule-day-chart').evaluate('e=>e.data[0].type'),'scatter')
        self.assertEqual(page.locator('.schedule-annual-chart').evaluate('e=>e.data[0].type'),'heatmap')
        page.locator('.schedule-annual-chart').evaluate("e=>e.emit('plotly_click',{points:[{x:'2007-02-01',y:12}]})")
        expect(page.locator('.schedule-values')).to_contain_text('2007-02-01')
        page.locator('.schedule-year').fill('2000');page.locator('.schedule-update').click()
        expect(page.locator('.schedule-status')).to_contain_text('366 days')
        self.assertEqual(self.errors,[])

    def test_annual_plot_locks_calendar_and_metadata_json_copies(self):
        page=self.page;page.goto(self.base+'objects/annual-pilot/');page.locator('.schedule-load').click()
        expect(page.locator('.schedule-status')).to_contain_text('Recorded 2007')
        expect(page.locator('.schedule-year')).to_be_disabled()
        expect(page.locator('.schedule-holidays')).to_be_disabled()
        self.assertEqual(page.locator('.schedule-annual-chart').evaluate('e=>e.data[0].z.length'),24)
        page.goto(self.base+'objects/component-pilot/')
        page.locator('.object-source summary').click();expect(page.locator('.object-source pre')).to_contain_text('component-pilot')
        page.locator('.object-copy').click();expect(page.get_by_role('button',name='Copy with defaults',exact=True)).to_be_disabled()
        page.get_by_role('button',name='Copy raw',exact=True).click();expect(page.locator('.object-status')).to_contain_text('copied')
        self.assertEqual(json.loads(page.evaluate('navigator.clipboard.readText()'))['id'],'component-pilot')


if __name__ == '__main__': unittest.main()
