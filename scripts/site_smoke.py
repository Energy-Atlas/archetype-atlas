"""Browser checks of the built suite site (ADR 0043) in Chromium through Playwright.

python -m scripts.site_smoke                         # build/site, Playwright's Chromium
python -m scripts.site_smoke --channel chrome        # an installed Chrome or Edge (msedge) instead
python -m scripts.site_smoke --screenshots build/screenshots
python -m scripts.site_smoke --serve                 # serve build/site at http://127.0.0.1:8765/archetype-atlas/

The site is served under its project prefix, with 404.html for missing paths as
GitHub Pages does. Pages are chosen from site-manifest.json: a program with fillings,
a source-only program, a dwelling with annual schedules and a construction set with
several context axes.
"""
import argparse
import functools
import http.server
import json
import re
import threading
from pathlib import Path

from scripts.common import ROOT

PREFIX = '/archetype-atlas/'


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = path.split('?', 1)[0].split('#', 1)[0]
        if not path.startswith(PREFIX):
            return str(Path(self.directory)/'__outside_prefix__')
        return super().translate_path('/'+path[len(PREFIX):])

    def send_error(self, code, message=None, explain=None):
        page = Path(self.directory)/'404.html'
        if code != 404 or not page.is_file():
            return super().send_error(code, message, explain)
        body = page.read_bytes()
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class Server(http.server.ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass  # The browser closes connections it no longer needs; that is not a site fault.


def serve(site, port=0):
    handler = functools.partial(Handler, directory=str(site))
    server = Server(('127.0.0.1', port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_address[1]}{PREFIX}'


def pick(site):
    """Representative pages from the manifest and the built HTML."""
    manifest = json.loads((site/'site-manifest.json').read_text(encoding='utf-8'))
    programs = manifest['programs']
    filled = next(p for p, e in sorted(programs.items()) if e.get('filled') and
                  'ea-filling' in (site/e['page']/'index.html').read_text(encoding='utf-8'))
    source_only = next(p for p, e in sorted(programs.items()) if e.get('filled_reason') and p.startswith('iecc-'))
    dwelling = next((p for p in sorted(programs) if p.startswith('resstock-sdr.')), None)
    sets = manifest['construction_sets']
    axes = next((s for s, e in sorted(sets.items()) if s.startswith('iecc-') and '.' in next(iter(e['contexts'])) and
                 'data-foundation' in (site/e['page']/'index.html').read_text(encoding='utf-8')), None)
    commercial = next(s for s, e in sorted(sets.items()) if len(e['contexts']) > 3 and s.startswith('90-1-2019.'))
    return manifest, filled, source_only, dwelling, axes or commercial, commercial


def check(site, channel=None, screenshots=None):
    from playwright.sync_api import sync_playwright
    site = Path(site)
    manifest, filled, source_only, dwelling, axes, commercial = pick(site)
    server, base = serve(site)
    failures, notes = [], []

    def expect(condition, message):
        (notes if condition else failures).append(message)

    def shot(page, name):
        if screenshots:
            Path(screenshots).mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(Path(screenshots)/f'{name}.png'), full_page=False)

    page_url = lambda record_id: base+manifest['programs'].get(record_id, manifest['construction_sets'].get(record_id, {})).get('page', '')
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=channel) if channel else playwright.chromium.launch()
            context = browser.new_context(accept_downloads=True)
            context.grant_permissions(['clipboard-read', 'clipboard-write'], origin=base.split(PREFIX)[0])
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' and 'Failed to load resource' not in message.text else None)
            # Only the site's own resources count; Material's repository widget also asks api.github.com.
            page.on('response', lambda response: errors.append(f'{response.status} {response.url}')
                    if response.status >= 400 and response.url.startswith(base) else None)

            # A program with fillings: version switch, copy and download.
            page.goto(page_url(filled))
            expect(page.locator('.ea-filling').count() > 0, f'{filled}: fillings are marked')
            exports = page.locator('.ea-suite > .ea-exports').first
            expect(exports.locator('.ea-copy:visible').count() == 2, f'{filled}: copy buttons for source and filled')
            page.goto(page_url(filled)+'?version=source')
            hidden = page.eval_on_selector('.ea-filling', 'e => getComputedStyle(e).display')
            expect(hidden == 'none', f'{filled}: ?version=source hides fillings')
            page.goto(page_url(filled)+'?version=filled')
            shown = page.eval_on_selector('.ea-filling', 'e => getComputedStyle(e).display')
            expect(shown != 'none', f'{filled}: ?version=filled shows fillings')
            expect(page.locator('[data-switch="version"] a[aria-current="true"]').inner_text() == 'Filled', f'{filled}: active version marked')
            shot(page, 'program-filled')
            holder = page.locator('.ea-suite > .ea-exports').first.locator('.ea-json').nth(1)
            holder.locator('.ea-copy').click()
            page.wait_for_function('document.querySelectorAll(".ea-json__status").length > 0 && '
                                   '/Copied|clipboard/.test(document.querySelector(".ea-json__status").textContent)', timeout=20000)
            text = page.evaluate('navigator.clipboard.readText()')
            copied = json.loads(text) if text.startswith('{') else {}
            expect(copied.get('id') == filled and copied.get('version') == 'filled', f'{filled}: copied filled JSON verified')
            with page.expect_download() as download:
                page.locator('.ea-suite > .ea-exports').first.locator('.ea-json').nth(0).locator('a[download]').click()
            saved = json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
            expect(saved.get('id') == filled and saved.get('version') == 'source' and download.value.suggested_filename.endswith('.source.json'),
                   f'{filled}: downloaded source JSON verified and decompressed')

            # A source-only program asked for its filled version.
            page.goto(page_url(source_only)+'?version=filled')
            expect(page.locator('.ea-notice[data-when-version="filled"]').is_visible(), f'{source_only}: notice for the missing filled version')
            expect(page.locator('.ea-suite > .ea-exports').first.locator('.ea-json--absent').count() == 1,
                   f'{source_only}: filled export marked absent with its reason')
            shot(page, 'program-source-only')

            # A dwelling: annual schedules as monthly and typical-day plots, no hourly table.
            if dwelling:
                page.goto(page_url(dwelling))
                expect(page.locator('.ea-schedule svg.ea-plot').count() >= 2, f'{dwelling}: annual schedule plots')
                expect(page.locator('text=Typical day').count() > 0, f'{dwelling}: typical day shown')
                biggest = max(len(t) for t in page.locator('.ea-schedule table').all_inner_texts()) if page.locator('.ea-schedule table').count() else 0
                expect(biggest < 20000, f'{dwelling}: no hourly table')
                shot(page, 'dwelling')

            # A construction set: context filters in the query string.
            page.goto(page_url(axes)+'?climate=4A')
            expect(page.locator('form[data-filters]').is_visible(), f'{axes}: filters shown')
            visible = page.eval_on_selector_all('.ea-context:not([hidden])', 'es => es.map(e => e.dataset.climate)')
            expect(visible and all(re.match(r'^4A', v or '') for v in visible), f'{axes}: ?climate=4A keeps zone 4A only ({len(visible)})')
            count = page.locator('.ea-filter-count').inner_text()
            expect(count.startswith(f'{len(visible)} of '), f'{axes}: count says {count}')
            if page.locator('select[data-filter="foundation"]').count():
                value = page.eval_on_selector('select[data-filter="foundation"]', 's => s.options[1].value')
                page.select_option('select[data-filter="foundation"]', value)
                expect(f'foundation={value}' in page.url, f'{axes}: foundation choice is kept in the URL')
                foundations = page.eval_on_selector_all('.ea-context:not([hidden])', 'es => es.map(e => e.dataset.foundation)')
                expect(foundations and set(foundations) == {value}, f'{axes}: foundation filter')
            shot(page, 'construction-filtered')
            page.goto(page_url(commercial))
            expect(page.locator('.ea-context').count() == len(manifest['construction_sets'][commercial]['contexts']),
                   f'{commercial}: every context is listed')

            # The viewer: a schedule opens its page and anchor; an evidence row shows its JSON.
            page.goto(page_url(filled))
            schedule = page.eval_on_selector('.ea-schedule[id]', 'e => e.id') if page.locator('.ea-schedule[id]').count() else None
            if schedule:
                page.goto(base+'view/?id='+schedule)
                page.wait_for_url(re.compile('#'+re.escape(schedule)+'$'), timeout=20000)
                expect('/catalogue/' in page.url, f'viewer opens schedule {schedule}')
            page.goto(page_url(filled))
            evidence_id = page.eval_on_selector('.ea-evidence[id]', 'e => e.id') if page.locator('.ea-evidence[id]').count() else None
            if evidence_id:
                page.goto(base+'view/?id='+evidence_id)
                page.wait_for_selector('.ea-viewer__json', timeout=20000)
                expect(evidence_id in page.locator('.ea-viewer__json').inner_text(), f'viewer shows evidence {evidence_id}')
                shot(page, 'viewer')
            page.goto(base+'view/?id=no-such-object-id')
            page.wait_for_function('/No object/.test(document.querySelector(".ea-viewer__status").textContent)', timeout=20000)
            expect(True, 'viewer reports an unknown ID')

            # Search finds a suite page by its ID.
            page.goto(base)
            page.locator('label.md-search__icon, .md-search__input').first.click()
            page.locator('.md-search__input').fill(filled.split('.')[-2])
            page.wait_for_selector('.md-search-result__item', timeout=30000)
            hrefs = page.eval_on_selector_all('.md-search-result__item a', 'es => es.map(e => e.getAttribute("href"))')
            expect(any(manifest['programs'][filled]['page'] in (h or '') for h in hrefs), f'search finds {filled}')

            expect(not errors, 'no console errors: '+'; '.join(errors[:3]))

            # Retired URLs answer with the 404 page and its search box.
            response = page.goto(base+'definitions/old-record/')
            expect(response.status == 404 and page.locator('.md-search__input').count() > 0, 'retired URL shows the 404 page with search')

            # Without JavaScript the record and its gzip download remain.
            plain = browser.new_context(java_script_enabled=False)
            nojs = plain.new_page()
            nojs.goto(page_url(filled))
            expect(nojs.locator('.ea-section').count() > 2 and nojs.locator('.ea-suite > .ea-exports').first.locator('a[download]').count() == 2,
                   f'{filled}: reads without JavaScript')
            plain.close()

            # Phone width: no horizontal page scroll.
            phone = browser.new_context(viewport={'width': 375, 'height': 812})
            small = phone.new_page()
            for record_id in (filled, axes):
                small.goto(page_url(record_id))
                overflow = small.evaluate('document.documentElement.scrollWidth - window.innerWidth')
                expect(overflow <= 1, f'{record_id}: no horizontal scroll at 375 px ({overflow})')
            shot(small, 'phone')
            phone.close()
            browser.close()
    finally:
        server.shutdown()
    return failures, notes


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--site', type=Path, default=ROOT/'build/site')
    parser.add_argument('--channel', help='an installed browser channel (chrome, msedge) instead of Playwright Chromium')
    parser.add_argument('--screenshots', type=Path)
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if args.serve:
        server, url = serve(args.site, args.port)
        print('Serving', url, '(Ctrl+C to stop)')
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            server.shutdown()
        return
    failures, notes = check(args.site, args.channel, args.screenshots)
    for note in notes:
        print('ok  ', note)
    if failures:
        raise SystemExit('\n'.join('FAIL '+f for f in failures))
    print(f'{len(notes)} browser checks passed')


if __name__ == '__main__':
    main()
