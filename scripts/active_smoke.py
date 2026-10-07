"""Browser acceptance of the current definition catalogue, without deployment."""
import json


def active_smoke(browser, base, screenshot_dir=None):
    from playwright.sync_api import expect
    context = browser.new_context(viewport={'width': 1440, 'height': 960}, permissions=['clipboard-read', 'clipboard-write'])
    page = context.new_page();errors = [];failed = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('response', lambda response: failed.append(response.url) if response.status >= 400 and response.url.startswith(base) else None)
    if screenshot_dir: screenshot_dir.mkdir(parents=True, exist_ok=True)
    def screenshot(name):
        if screenshot_dir: page.screenshot(path=str(screenshot_dir / (name + '.png')), full_page=True)
    try:
        page.goto(base);query = page.locator('[data-md-component="search-query"]');query.fill('Office')
        expect(page.locator('.md-search-result__list')).to_contain_text('Office');query.press('Escape')
        screenshot('home')
        page.goto(base + 'catalogue/');expect(page.locator('.definition-gate')).to_have_count(2)
        page.locator('.definition-gate').nth(1).focus();page.keyboard.press('Enter')
        expect(page.locator('.definition-kind')).to_have_count(3);page.locator('.definition-kind').first.click()
        expect(page.locator('.definition-status')).to_contain_text('matching entries')
        expect(page.locator('[data-filter="vintage"]')).to_have_value('90.1-2019')
        expect(page.locator('[data-filter="detail"]')).to_have_value('SourcePrograms')
        expect(page.locator('[data-filter="climate"]')).to_have_count(0)
        page.locator('[data-filter="building"]').select_option('Medium Office')
        expect(page.locator('.definition-result a').first).to_be_visible();saved = page.url
        page.reload();expect(page.locator('[data-filter="building"]')).to_have_value('Medium Office')
        screenshot('finder');page.locator('.definition-result a').first.click()
        page.locator('.object-source summary').click();expect(page.locator('.object-status')).to_contain_text('Complete raw JSON')
        raw = json.loads(page.locator('.object-source pre').inner_text())
        page.locator('.object-copy').click();page.get_by_role('button', name='Copy with defaults', exact=True).click()
        expect(page.locator('.object-status')).to_contain_text('copied')
        ready = json.loads(page.evaluate('navigator.clipboard.readText()'))
        assert ready['export_mode'] == 'defaulted' and ready['source']['program_id'] == raw['id']
        screenshot('program-json')
        registry = page.request.get(base + 'object-index.json').json()
        schedule = next(identity for identity in raw['schedules'] if identity in registry)
        page.goto(base + registry[schedule]['path'].removesuffix('.md') + '/')
        page.locator('.schedule-load').click();expect(page.locator('.schedule-status')).to_contain_text('days')
        assert page.locator('.schedule-day-chart').evaluate('e=>e.data[0].type') == 'scatter'
        assert page.locator('.schedule-annual-chart').evaluate('e=>e.data[0].type') == 'heatmap'
        screenshot('schedule')
        metadata = next((entry for entry in registry.values() if entry['path'].endswith('index.html')), None)
        if metadata:
            page.goto(base + metadata['path']);page.locator('.object-source summary').click()
            expect(page.locator('.object-status')).to_contain_text('Complete raw JSON')
            page.locator('.object-copy').click();expect(page.get_by_role('button', name='Copy with defaults', exact=True)).to_be_disabled()
            page.get_by_role('button', name='Copy raw', exact=True).click();expect(page.locator('.object-status')).to_contain_text('copied')
        page.goto(base + 'catalogue/nonresidential/program/?building=Medium+Office&vintage=Unsupported')
        expect(page.locator('.definition-status')).to_contain_text('No entries match')
        page.goto(saved);page.locator('.definition-finder button[type="reset"]').click()
        expect(page.locator('[data-filter="vintage"]')).to_have_value('90.1-2019')
        page.set_viewport_size({'width': 390, 'height': 844});page.goto(base + 'catalogue/')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), 'Mobile gate overflow'
        screenshot('mobile-gate')
        page.goto(base + registry[schedule]['path'].removesuffix('.md') + '/')
        page.locator('.schedule-load').click();expect(page.locator('.schedule-status')).to_contain_text('days')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), 'Mobile schedule overflow'
        screenshot('mobile-schedule')
        offline = browser.new_context(java_script_enabled=False)
        try:
            fallback = offline.new_page();fallback.goto(base + 'catalogue/')
            expect(fallback.locator('.definition-gate')).to_have_count(2)
            fallback.goto(base + 'catalogue/nonresidential/program/');fallback.locator('.definition-static summary').click()
            expect(fallback.locator('.definition-static a').first).to_be_visible()
            fallback.locator('.definition-static a').first.click();expect(fallback.locator('h1')).to_be_visible()
            fallback.goto(base + registry[schedule]['path'].removesuffix('.md') + '/')
            fallback.locator('.schedule-static summary').click()
            expect(fallback.locator('.schedule-static table')).to_be_visible()
        finally: offline.close()
        assert not errors and not failed, {'browser_errors': errors, 'failed_local_requests': failed}
    finally: context.close()


def smoke(root, screenshot_dir=None):
    from playwright.sync_api import sync_playwright
    from scripts.site_smoke import serve
    server, base = serve(root)
    try:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch()
            try: active_smoke(browser, base, screenshot_dir)
            finally: browser.close()
        print('Active browser checks passed: gates, search, filters, complete copying, plots, mobile and no-JS')
    finally: server.shutdown();server.server_close()
