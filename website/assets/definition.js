(function () {
  'use strict';
  const text = (tag, value) => {const node = document.createElement(tag); node.textContent = value; return node;};
  async function finder(section) {
    const response = await fetch(new URL(section.dataset.index, location.href));
    if (!response.ok) throw new Error('Entry metadata unavailable');
    const entries = await response.json();
    const controls = [...section.querySelectorAll('[data-filter]')];
    const params = new URLSearchParams(location.search);
    let filters = Object.fromEntries(controls.map(c => [c.dataset.filter, params.get(c.dataset.filter) || (c.dataset.filter === 'evidence_view' ? 'source' : '')]));
    let limit = 40;
    const status = section.querySelector('.definition-status'), results = section.querySelector('.definition-results'), more = section.querySelector('.definition-more');
    function render() {
      for (const c of controls) {
        const value = filters[c.dataset.filter];
        if (c.tagName === 'SELECT' && value && ![...c.options].some(o => o.value === value)) {
          const option = text('option', value + ' (unavailable)'); option.value = value; c.append(option);
        }
        c.value = value;
        if (c.tagName === 'SELECT') for (const o of c.options) {
          if (o.value && c.dataset.filter !== 'evidence_view') o.disabled = !DefinitionCore.filter(entries, {...filters, [c.dataset.filter]: o.value}).length;
        }
      }
      const matches = DefinitionCore.filter(entries, filters);
      status.textContent = matches.length ? matches.length + ' matching entries' : 'No entries match this combination. Change or reset the filters.';
      results.replaceChildren();
      for (const row of matches.slice(0, limit)) {
        const card = text('div', ''); card.className = 'definition-result';
        const a = text('a', row.name); a.href = row.path;
        card.append(a, text('p', [row.building, row.vintage, row.climate, row.evidence_view, row.derivation].filter(Boolean).join(' · ')));
        results.append(card);
      }
      more.hidden = matches.length <= limit;
      const query = new URLSearchParams(Object.entries(filters).filter(([,v]) => v));
      history.replaceState(null, '', location.pathname + (query.size ? '?' + query : ''));
    }
    for (const c of controls) c.addEventListener(c.type === 'search' ? 'input' : 'change', () => {
      filters = DefinitionCore.change(filters, c.dataset.filter, c.value); limit = 40; render();
    });
    section.querySelector('form').addEventListener('submit', e => e.preventDefault());
    section.querySelector('form').addEventListener('reset', e => {
      e.preventDefault(); filters = Object.fromEntries(controls.map(c => [c.dataset.filter, c.dataset.filter === 'evidence_view' ? 'source' : ''])); limit = 40; render();
    });
    more.addEventListener('click', () => {limit += 40; render();}); render();
  }
  async function resource(section) {
    const output = section.querySelector('pre'), button = section.querySelector('button');
    button.disabled = true; output.textContent = 'Loading and verifying…';
    try {
      const ref = JSON.parse(section.dataset.ref);
      if (!/^resources\/[a-f0-9]{64}\.json(?:\.gz)?$/.test(ref.href) || ref.decoded_size_bytes > 16777216) throw new Error('Invalid resource descriptor');
      const response = await fetch(new URL(section.dataset.root + ref.href, location.href));
      if (!response.ok) throw new Error('Resource unavailable (' + response.status + ')');
      const bytes = await response.arrayBuffer();
      const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(b => b.toString(16).padStart(2,'0')).join('');
      if (bytes.byteLength !== ref.size_bytes || digest !== ref.sha256) throw new Error('Resource checksum or size mismatch');
      let decoded = bytes;
      if (ref.encoding === 'gzip') {
        const reader = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')).getReader();
        const chunks = []; let size = 0;
        while (true) {const {done, value} = await reader.read(); if (done) break; size += value.length;
          if (size > ref.decoded_size_bytes) {await reader.cancel(); throw new Error('Resource exceeds decoded bound');} chunks.push(value);}
        if (size !== ref.decoded_size_bytes) throw new Error('Decoded resource size mismatch');
        decoded = await new Blob(chunks).arrayBuffer();
      }
      const value = JSON.parse(new TextDecoder().decode(decoded));
      if (value.schema_version !== '2.0.0' || value.kind !== 'resource') throw new Error('Unsupported resource schema');
      output.textContent = JSON.stringify(value.record, null, 2); button.textContent = 'Verified';
    } catch (error) {output.textContent = error.message; button.disabled = false;}
  }
  function start() {
    document.querySelectorAll('.definition-finder').forEach(s => finder(s).catch(e => {s.querySelector('.definition-status').textContent = e.message + '. Use the static list below.';}));
    document.querySelectorAll('.definition-resource').forEach(s => s.querySelector('button').addEventListener('click', () => resource(s)));
    document.querySelectorAll('.definition-copy').forEach(b => b.addEventListener('click', async () => {
      try {await navigator.clipboard.writeText(b.dataset.id); b.textContent = 'Copied';} catch (_) {b.textContent = 'Select the ID to copy';}
    }));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
