/* Suite pages (ADR 0043): version and context switches in the query string, and verified JSON copy and download.
   Pages read completely without this script; it only narrows what is shown and handles the store's gzip documents. */
(function () {
  'use strict';
  const LIMIT = 16000000;

  function zone(label) {
    const match = /^([0-8])(?:-?([A-Ca-c]))?(?![0-9])/.exec(String(label || ''));
    return match ? match[1] + (match[2] || '').toUpperCase() : null;
  }

  function matches(axis, value, wanted) {
    if (!wanted) return true;
    if (axis === 'climate') return value === wanted || zone(value) === wanted;
    return value === wanted;
  }

  async function bounded(stream, size) {
    const reader = stream.getReader(), chunks = [];
    let total = 0;
    try {
      for (;;) {
        const {done, value} = await reader.read();
        if (done) break;
        total += value.byteLength;
        if (total > size) { await reader.cancel(); throw new Error('JSON exceeds its declared size.'); }
        chunks.push(value);
      }
    } finally { reader.releaseLock(); }
    if (total !== size) throw new Error('JSON size does not match its declaration.');
    const out = new Uint8Array(total);
    let offset = 0;
    chunks.forEach(chunk => { out.set(chunk, offset); offset += chunk.byteLength; });
    return out;
  }

  const cache = new Map();

  /* A store document: fetched, checked against its SHA-256 and sizes, then decompressed. */
  function load(descriptor, base) {
    const d = descriptor;
    if (!d || !/(^|\/)store\/[a-f0-9]{64}\.json\.gz$/.test(d.href) || !d.href.includes(d.sha256) || d.encoding !== 'gzip' ||
        ![d.size_bytes, d.decoded_size_bytes].every(n => Number.isSafeInteger(n) && n > 0 && n <= LIMIT)) {
      return Promise.reject(new Error('Invalid JSON descriptor.'));
    }
    const url = new URL(d.href, base || location.href).href;
    if (!cache.has(url)) {
      cache.set(url, (async () => {
        const response = await fetch(url, {credentials: 'same-origin'});
        if (!response.ok) throw new Error('JSON unavailable (' + response.status + ').');
        const encoded = await bounded(response.body, d.size_bytes);
        const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', encoded)),
          n => n.toString(16).padStart(2, '0')).join('');
        if (digest !== d.sha256) throw new Error('JSON checksum verification failed.');
        const decoded = await bounded(new Blob([encoded]).stream().pipeThrough(new DecompressionStream('gzip')), d.decoded_size_bytes);
        return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(decoded));
      })().catch(error => { cache.delete(url); throw error; }));
    }
    return cache.get(url);
  }

  function status(holder, text) {
    let out = holder.querySelector('.ea-json__status');
    if (!out) {
      out = document.createElement('span');
      out.className = 'ea-json__status';
      out.setAttribute('role', 'status');
      holder.append(out);
    }
    out.textContent = text;
  }

  function manualCopy(holder, text) {
    holder.querySelector('textarea')?.remove();
    const area = document.createElement('textarea');
    area.readOnly = true;
    area.value = text;
    area.setAttribute('aria-label', 'Complete JSON for manual copy');
    holder.append(area);
    area.focus();
    area.select();
  }

  function initJson(holder) {
    const descriptor = JSON.parse(holder.dataset.json);
    const copy = holder.querySelector('.ea-copy');
    const download = holder.querySelector('a[download]');
    copy.hidden = false;
    copy.addEventListener('click', async () => {
      copy.disabled = true;
      status(holder, 'Loading verified JSON…');
      try {
        const text = JSON.stringify(await load(descriptor), null, 2);
        try {
          await navigator.clipboard.writeText(text);
          status(holder, 'Copied.');
        } catch (_) {
          status(holder, 'The clipboard is unavailable; select and copy the JSON below.');
          manualCopy(holder, text);
        }
      } catch (error) { status(holder, error.message); }
      finally { copy.disabled = false; }
    });
    download.addEventListener('click', async event => {
      event.preventDefault();
      status(holder, 'Loading verified JSON…');
      try {
        const text = JSON.stringify(await load(descriptor), null, 2) + '\n';
        const link = document.createElement('a');
        link.href = URL.createObjectURL(new Blob([text], {type: 'application/json'}));
        link.download = holder.dataset.file;
        document.body.append(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(link.href), 1000);
        status(holder, 'Downloaded ' + holder.dataset.file + '.');
      } catch (error) { status(holder, error.message); }
    });
  }

  let params;

  function initVersion() {
    const version = params.get('version');
    const chosen = version === 'source' || version === 'filled' ? version : '';
    document.documentElement.dataset.eaVersion = chosen || 'both';
    document.querySelectorAll('[data-switch="version"] a').forEach(link => {
      if (link.dataset.version === chosen) link.setAttribute('aria-current', 'true');
    });
    document.querySelectorAll('[data-when-version]').forEach(notice => {
      notice.hidden = notice.dataset.whenVersion !== chosen;
    });
  }

  function initClimates() {
    const wanted = params.get('climate');
    if (!wanted) return;
    document.querySelectorAll('.ea-climates [data-climate]').forEach(cell => {
      cell.classList.toggle('ea-dim', !matches('climate', cell.dataset.climate, wanted));
    });
  }

  function initFilters(form) {
    const selects = Array.from(form.querySelectorAll('select[data-filter]'));
    const sections = Array.from(document.querySelectorAll('.ea-context'));
    const rows = Array.from(document.querySelectorAll('tr[data-context]'));
    const count = form.querySelector('.ea-filter-count');
    form.hidden = false;
    selects.forEach(select => {
      const value = params.get(select.dataset.filter);
      if (value && !Array.from(select.options).some(o => o.value === value)) {
        select.append(new Option(value, value));
      }
      if (value) select.value = value;
    });
    function apply() {
      const wanted = Object.fromEntries(selects.map(s => [s.dataset.filter, s.value]));
      // A row that spans an axis (`data-across="orientation"`: the robust rows of the zoning pages) matches every value of it.
      const visible = element => Object.entries(wanted).every(([axis, value]) =>
        (element.dataset.across || '').split(' ').includes(axis) || matches(axis, element.dataset[axis], value));
      let shown = 0;
      sections.forEach(section => {
        section.hidden = !visible(section);
        if (!section.hidden) shown += 1;
      });
      rows.forEach(row => { row.hidden = !visible(row); });
      count.textContent = shown + ' of ' + sections.length + ' ' + (form.dataset.unit || 'contexts');
      const next = new URLSearchParams(location.search);
      Object.entries(wanted).forEach(([axis, value]) => { if (value) next.set(axis, value); else next.delete(axis); });
      const query = next.toString();
      history.replaceState(null, '', location.pathname + (query ? '?' + query : '') + location.hash);
    }
    selects.forEach(select => select.addEventListener('change', apply));
    apply();
  }

  function init() {
    params = new URLSearchParams(location.search);
    initVersion();
    initClimates();
    document.querySelectorAll('[data-filters]').forEach(initFilters);
    document.querySelectorAll('.ea-json[data-json]').forEach(initJson);
  }

  if (typeof module === 'object' && module.exports) {
    module.exports = {zone, matches};
    return;
  }
  window.AtlasStore = {load, zone, matches};
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
