/* Suite pages (ADR 0043, ADR 0057): version and context switches in the query string, and verified JSON copy and
   download. Pages read completely without this script; it only narrows what is shown and handles the store's gzip
   documents. Download saves the store's canonical JSON bytes unchanged, so the file hashes to the SHA-256 the page
   prints (`json_sha256`); Copy puts an indented rendering of the same JSON on the clipboard. */
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

  async function sha256(bytes) {
    return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), n => n.toString(16).padStart(2, '0')).join('');
  }

  /* A store document's canonical JSON bytes: fetched, checked against the SHA-256 and size of the gzip file, then
     decompressed and checked against the SHA-256 and size of the JSON. */
  function loadBytes(descriptor, base) {
    const d = descriptor;
    if (!d || !/(^|\/)store\/[a-f0-9]{64}\.json\.gz$/.test(d.href) || !d.href.includes(d.sha256) || d.encoding !== 'gzip' ||
        !/^[a-f0-9]{64}$/.test(d.json_sha256 || '') ||
        ![d.size_bytes, d.decoded_size_bytes].every(n => Number.isSafeInteger(n) && n > 0 && n <= LIMIT)) {
      return Promise.reject(new Error('Invalid JSON descriptor.'));
    }
    const url = new URL(d.href, base || location.href).href;
    if (!cache.has(url)) {
      cache.set(url, (async () => {
        const response = await fetch(url, {credentials: 'same-origin'});
        if (!response.ok) {
          throw new Error(response.status === 429 ? 'The site is limiting downloads; wait a few minutes and try again.'
            : 'JSON unavailable (' + response.status + ').');
        }
        const encoded = await bounded(response.body, d.size_bytes);
        if (await sha256(encoded) !== d.sha256) throw new Error('JSON checksum verification failed.');
        const decoded = await bounded(new Blob([encoded]).stream().pipeThrough(new DecompressionStream('gzip')), d.decoded_size_bytes);
        if (await sha256(decoded) !== d.json_sha256) throw new Error('JSON checksum verification failed.');
        return decoded;
      })().catch(error => { cache.delete(url); throw error; }));
    }
    return cache.get(url);
  }

  /* A store document, verified, as a JSON value. */
  async function load(descriptor, base) {
    return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(await loadBytes(descriptor, base)));
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
        const bytes = await loadBytes(descriptor);
        const link = document.createElement('a');
        link.href = URL.createObjectURL(new Blob([bytes], {type: 'application/json'}));
        link.download = holder.dataset.file;
        document.body.append(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(link.href), 1000);
        status(holder, 'Downloaded ' + holder.dataset.file + '.');
      } catch (error) { status(holder, error.message); }
    });
  }

  /* A JSON value as the site renders records (site_render.render): objects as definition lists, lists of objects as
     tables, null as an explicit null. Used for the context fields that the largest construction pages load on demand. */
  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function scalarText(value) {
    return typeof value === 'string' ? value : JSON.stringify(value);
  }

  function renderValue(value) {
    if (value === null) return element('span', 'ea-null', 'null');
    if (typeof value !== 'object') return document.createTextNode(scalarText(value));
    if (Array.isArray(value)) {
      if (!value.length) return element('span', 'ea-empty', '[]');
      if (value.every(v => v === null || typeof v !== 'object')) {
        return document.createTextNode(value.map(v => v === null ? 'null' : scalarText(v)).join(', '));
      }
      const columns = [];
      if (value.every(v => v && typeof v === 'object' && !Array.isArray(v))) {
        value.forEach(v => Object.keys(v).forEach(k => { if (!columns.includes(k)) columns.push(k); }));
      }
      if (columns.length && columns.length <= 12) {
        const wrap = element('div', 'ea-table'), table = element('table'), head = element('tr'), body = element('tbody');
        columns.forEach(c => head.append(element('th', null, c)));
        value.forEach(v => {
          const row = element('tr');
          columns.forEach(c => {
            const cell = element('td', c in v ? null : 'ea-absent');
            if (c in v) cell.append(renderValue(v[c]));
            row.append(cell);
          });
          body.append(row);
        });
        const thead = element('thead');
        thead.append(head);
        table.append(thead, body);
        wrap.append(table);
        return wrap;
      }
      const list = element('ol', 'ea-list');
      value.forEach(v => { const item = element('li'); item.append(renderValue(v)); list.append(item); });
      return list;
    }
    const keys = Object.keys(value);
    if (!keys.length) return element('span', 'ea-empty', '{}');
    const fields = element('dl', 'ea-fields');
    keys.forEach(k => {
      const dd = element('dd');
      dd.append(renderValue(value[k]));
      fields.append(element('dt', null, k), dd);
    });
    return fields;
  }

  function initLazy(holder) {
    const button = holder.querySelector('.ea-show');
    if (!button) return;
    button.hidden = false;
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        const document_ = await load(JSON.parse(holder.dataset.json));
        holder.replaceChildren(renderValue(document_.fields));
      } catch (error) {
        button.disabled = false;
        status(holder, error.message);
      }
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
    document.querySelectorAll('.ea-lazy[data-json]').forEach(initLazy);
  }

  if (typeof module === 'object' && module.exports) {
    module.exports = {zone, matches};
    return;
  }
  window.AtlasStore = {load, loadBytes, zone, matches};
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
