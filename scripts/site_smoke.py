"""Exercise built catalogue, schedules, downloads and mobile/no-JS fallbacks."""
import argparse
import csv
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time

from scripts.common import ROOT, load_json

PREFIX = '/archetype-atlas/'


class Handler(SimpleHTTPRequestHandler):
    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (ConnectionError, BrokenPipeError):
            # Browser navigation/closing cancels in-flight asset requests.
            pass

    def do_GET(self):
        if not self.path.startswith(PREFIX):
            self.send_error(404)
            return
        self.path = '/' + self.path[len(PREFIX):]
        super().do_GET()

    def log_message(self, *args):
        pass


def serve(root, port=0):
    server = ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_port}' + PREFIX


def smoke(root, screenshot_dir=None):
    from playwright.sync_api import sync_playwright, expect
    root = Path(root)
    index = load_json(root/'releases/v0.2.0/catalogue.json')
    office = next(r for r in index['entries'] if r['kind'] == 'programs'
                  and r['building'] == 'MediumOffice' and r['program'] == 'office'
                  and r['template'] == '90.1-2013')
    residential = next(r for r in index['entries'] if r['kind'] == 'residential_archetypes')
    server, base = serve(root)
    errors, failed = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={'width': 1440, 'height': 960})
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('response', lambda response: failed.append(response.url) if
                    response.status >= 400 and response.url.startswith(base) else None)
            page.goto(base)
            query=page.locator('[data-md-component="search-query"]')
            query.fill('Medium Office')
            expect(page.locator('.md-search-result__list')).to_contain_text('Medium Office')
            query.fill('')
            query.press('Escape')
            expect(page.locator('.atlas-hero')).to_be_visible()
            if screenshot_dir:
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot_dir/'home.png'), full_page=True)
            page.goto(base + 'releases/v0.2.0/catalogue/')
            expect(page.locator('#atlas-results-count')).to_contain_text('matching entries')
            page.locator('#atlas-filter-building').select_option('MediumOffice')
            page.locator('#atlas-filter-template').select_option('90.1-2013')
            page.locator('#atlas-filter-kind').select_option('programs')
            expect(page.locator('#atlas-results-count')).to_contain_text('2 matching entries')
            saved = page.url
            page.reload()
            expect(page.locator('#atlas-filter-building')).to_have_value('MediumOffice')
            expect(page.locator('#atlas-results-count')).to_contain_text('2 matching entries')
            page.locator('#atlas-query').fill('no-such-program-xyz')
            expect(page.locator('#atlas-results-count')).to_contain_text('0 matching entries')
            expect(page.locator('#atlas-results')).to_contain_text('No matching')
            page.locator('#atlas-reset').click()
            expect(page.locator('#atlas-filter-building')).to_have_value('')
            if not index.get('pilot'):
                page.locator('#atlas-filter-kind').select_option('schedules')
                page.locator('#atlas-filter-building').select_option('HighriseApartment')
                page.locator('#atlas-filter-template').select_option('90.1-2019')
                page.locator('#atlas-query').fill('schedule-9841fa9f62ff202db619')
                expect(page.locator('#atlas-results-count')).to_contain_text('0 matching entries')
                page.locator('#atlas-filter-template').select_option('90.1-2007')
                expect(page.locator('#atlas-results-count')).to_contain_text('1 matching entries')
                page.locator('#atlas-filter-building').select_option('MidriseApartment')
                page.locator('#atlas-filter-template').select_option('90.1-2019')
                expect(page.locator('#atlas-results-count')).to_contain_text('1 matching entries')
                page.locator('#atlas-reset').click()
            page.goto(base + office['path'].removesuffix('.md') + '/')
            expect(page.locator('.atlas-charts .js-plotly-plot').first).to_be_visible(timeout=30000)
            page.locator('.atlas-day').select_option('SmrDsn')
            expect(page.locator('.atlas-chart-status')).to_contain_text('schedules inspected')
            page.locator('.atlas-date').fill('2000-07-15')
            page.locator('.atlas-date').dispatch_event('change')
            expect(page.locator('.atlas-profile-table')).to_contain_text('SELECTED')
            overlay = page.locator('.atlas-controls select').last
            overlay_id = overlay.locator('option').nth(1).get_attribute('value')
            overlay.select_option(overlay_id)
            expect(page.locator('.atlas-profile-table')).to_contain_text('overlay')
            with page.expect_download() as download:
                page.locator('.atlas-csv').click()
            assert download.value.suggested_filename == 'atlas-selected-profiles.csv'
            exported_water = list(csv.DictReader(Path(download.value.path()).read_text().splitlines()))
            normalized = [float(r['value']) for r in exported_water
                          if r['role'] == 'fixture_draw_equivalent_peak_normalized']
            source_draw = [float(r['value']) for r in exported_water
                           if r['role'] == 'service_water_heating_schedule_id']
            assert len(normalized) == len(source_draw) == 24, 'Water equivalent missing from explorer CSV'
            assert all(abs(a-b*0.57) < 1e-12 for a,b in zip(source_draw,normalized)), 'Water equivalent changes draw shape/scaling'
            water_link = page.locator('.atlas-profile-table details').filter(has_text='fixture_draw_equivalent_peak_normalized').locator('a').first
            detail_url = water_link.get_attribute('href')
            assert detail_url and context.request.get(detail_url).status == 200, 'Equivalent source-rule detail page is unavailable'
            if screenshot_dir:
                page.screenshot(path=str(screenshot_dir/'office.png'), full_page=True)
            hospital = next((r for r in index['entries'] if r['id'] == 'program-063ce56e8cb91eedd1ae'), None)
            if not index.get('pilot'):
                assert hospital is not None, 'Full build must contain the shared-role regression fixture'
            if hospital:
                page.goto(base + hospital['path'].removesuffix('.md') + '/')
                expect(page.locator('.atlas-charts .js-plotly-plot').first).to_be_visible(timeout=30000)
                expect(page.locator('.atlas-profile-table')).to_contain_text('heating_setpoint_schedule_id')
                expect(page.locator('.atlas-profile-table')).to_contain_text('cooling_setpoint_schedule_id')
                expect(page.locator('.atlas-profile-table')).to_contain_text('minimum deadband: 0.000')
                with page.expect_download() as shared_csv:
                    page.locator('.atlas-csv').click()
                exported = list(csv.DictReader(Path(shared_csv.value.path()).read_text().splitlines()))
                for role in ['heating_setpoint_schedule_id', 'cooling_setpoint_schedule_id']:
                    assert len([r for r in exported if r['role'] == role]) == 24, 'Shared schedule role missing from CSV'
            race = context.new_page()
            race.add_init_script("""
                let api;
                window.__pendingPlots = 0;
                Object.defineProperty(window, 'Plotly', {
                  configurable: true,
                  get() { return api; },
                  set(value) {
                    const original = value.newPlot;
                    value.newPlot = function (...args) {
                      window.__pendingPlots++;
                      const result = original.apply(value, args);
                      if (!window.__plotHeld) {
                        window.__plotHeld = true;
                        return new Promise(resolve => {
                          window.__releasePlot = () => {
                            window.__plotReleased = true;
                            Promise.resolve(result).then(value => {
                              window.__pendingPlots--; resolve(value);
                            });
                          };
                        });
                      }
                      return Promise.resolve(result).finally(() => window.__pendingPlots--);
                    };
                    api = value;
                  }
                });
            """)
            race.goto(base + office['path'].removesuffix('.md') + '/')
            race.wait_for_function('window.__plotHeld === true')
            race.locator('.atlas-day').select_option('Sat')
            expect(race.locator('.atlas-charts .js-plotly-plot')).to_have_count(3)
            race.evaluate('window.__releasePlot()')
            race.wait_for_function('window.__plotReleased && window.__pendingPlots === 0')
            race.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
            expect(race.locator('.atlas-charts .js-plotly-plot')).to_have_count(3)
            race.close()
            page.goto(base + residential['path'].removesuffix('.md') + '/')
            expect(page.locator('body')).to_contain_text('Profiles unavailable')
            assert page.locator('.atlas-explorer').count() == 0
            expect(page.locator('.atlas-res-charts .js-plotly-plot')).to_have_count(2)
            expect(page.locator('.atlas-res-status')).to_contain_text('24 executed hourly intervals')
            profile_packet = page.request.get(base + residential['download']).json()['resolution_supplement']['profile']
            canonical = page.request.get(base + profile_packet['download']).json()
            page.locator('.atlas-res-view').select_option('annual')
            page.wait_for_function("document.querySelector('.atlas-res-charts .js-plotly-plot')?.data?.[0]?.y?.length === 8760")
            expect(page.locator('.atlas-res-date')).to_be_disabled()
            page.locator('.atlas-res-view').select_option('day')
            page.locator('.atlas-res-date').fill('2007-07-01')
            page.locator('.atlas-res-date').dispatch_event('change')
            page.wait_for_function("document.querySelector('.atlas-res-charts .js-plotly-plot')?.data?.[0]?.x?.[0] === '2007-07-01T00:00:00'")
            plotted = page.locator('.atlas-res-charts .js-plotly-plot').first.evaluate('(el) => el.data[0].y')
            assert plotted == canonical['series']['occupants'][181*24:182*24], 'Residential chart must show actual generated calendar data'
            if screenshot_dir:
                page.screenshot(path=str(screenshot_dir/'residential-profiles.png'), full_page=True)
            fixed_record=next(r for r in index['entries'] if r['id']=='residential_archetype-28457c00121833f065f2')
            page.goto(base + fixed_record['path'].removesuffix('.md') + '/')
            fixed_section=page.locator('.atlas-residential-profile[data-fixed="true"]')
            expect(fixed_section.locator('.atlas-res-columns option')).to_have_count(1)
            expect(fixed_section.locator('.atlas-res-status')).to_contain_text('no temperature feedback')
            page.wait_for_function("document.querySelector('[data-fixed=true] .js-plotly-plot')?.data?.[0]?.y?.length === 24")
            fixed_url=fixed_section.get_attribute('data-profile')
            from urllib.parse import urljoin
            fixed_packet=page.request.get(urljoin(page.url,fixed_url)).json()
            actual=fixed_section.locator('.js-plotly-plot').first.evaluate('(el) => el.data[0].y')
            assert actual==fixed_packet['series']['refrigerator'][:24], 'Fixed refrigeration chart differs from canonical recipe expansion'
            fixed_section.locator('.atlas-res-view').select_option('annual')
            page.wait_for_function("document.querySelector('[data-fixed=true] .js-plotly-plot')?.data?.[0]?.y?.length === 8760")
            if screenshot_dir:
                page.screenshot(path=str(screenshot_dir/'fixed-refrigeration.png'),full_page=True)
            response = page.request.get(base + office['download'])
            assert response.ok and response.json()['record']['id'] == office['id']
            page.set_viewport_size({'width': 390, 'height': 844})
            page.goto(saved)
            expect(page.locator('#atlas-query')).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'Mobile layout overflows'
            if screenshot_dir:
                page.screenshot(path=str(screenshot_dir/'mobile.png'), full_page=True)
            offline = browser.new_context(java_script_enabled=False)
            fallback = offline.new_page()
            fallback.goto(base + 'releases/v0.2.0/catalogue/')
            expect(fallback.locator('body')).to_contain_text('Browse by climate')
            expect(fallback.locator('a[href*="buildings/"]').first).to_be_visible()
            fallback.goto(base + office['path'].removesuffix('.md') + '/')
            expect(fallback.locator('body')).to_contain_text('Source locator')
            expect(fallback.locator('a[href$=".json"]').first).to_be_visible()
            browser.close()
        if errors or failed:
            raise AssertionError({'browser_errors': errors, 'failed_local_requests': failed})
        print('Browser checks passed: filters/permalinks, plots/overlays/CSV, executed residential annual/day profiles, mobile and no-JS')
    finally:
        server.shutdown()
        server.server_close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--site', type=Path, default=ROOT/'build/site')
    p.add_argument('--screenshots', type=Path)
    p.add_argument('--serve', action='store_true', help='Serve a persistent local preview')
    p.add_argument('--port', type=int, default=8765)
    args = p.parse_args()
    if args.serve:
        server, url = serve(args.site, args.port)
        print(url, flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.shutdown()
    else:
        smoke(args.site, args.screenshots)


if __name__ == '__main__':
    main()
