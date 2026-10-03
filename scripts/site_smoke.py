"""Exercise built catalogue, schedules, downloads and mobile/no-JS fallbacks."""
import argparse
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
            if screenshot_dir:
                page.screenshot(path=str(screenshot_dir/'office.png'), full_page=True)
            page.goto(base + residential['path'].removesuffix('.md') + '/')
            expect(page.locator('body')).to_contain_text('Profiles unavailable')
            assert page.locator('.atlas-explorer').count() == 0
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
        print('Browser checks passed: filters/permalinks, plots/overlays/CSV, residential gaps, mobile and no-JS')
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
