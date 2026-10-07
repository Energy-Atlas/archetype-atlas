(function () {
  'use strict';
  const root = new URL('../', document.currentScript.src), cache = new WeakMap(), limit = 16000000;
  const node = (tag, value) => { const n = document.createElement(tag); n.textContent = value; return n; };
  async function bounded(stream, size) {
    const reader = stream.getReader(), chunks = []; let total = 0;
    try {
      for (;;) {
        const {done, value} = await reader.read(); if (done) break;
        total += value.byteLength;
        if (total > size) { await reader.cancel(); throw new Error('JSON resource exceeds its declared size.'); }
        chunks.push(value);
      }
    } finally { reader.releaseLock(); }
    if (total !== size) throw new Error('JSON resource size does not match its declaration.');
    const result = new Uint8Array(total); let offset = 0;
    chunks.forEach(chunk => { result.set(chunk, offset); offset += chunk.byteLength; }); return result;
  }
  async function fetchObject(section, mode) {
    const d = JSON.parse(section.dataset[mode] || 'null');
    if (!d || !/^json\/[a-f0-9]{64}\.json\.gz$/.test(d.href) ||
        !/^[a-f0-9]{64}$/.test(d.sha256) || !d.href.includes(d.sha256) || d.encoding !== 'gzip' ||
        ![d.size_bytes, d.decoded_size_bytes].every(n => Number.isSafeInteger(n) && n > 0 && n <= limit) ||
        new URL(section.dataset.root, location.href).href !== root.href) throw new Error('Invalid JSON resource descriptor.');
    const url = new URL(d.href, root), controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(url, {signal: controller.signal, credentials: 'same-origin'});
      if (!response.ok) throw new Error('JSON resource unavailable (' + response.status + ').');
      const encoded = await bounded(response.body, d.size_bytes);
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', encoded)), n => n.toString(16).padStart(2, '0')).join('');
      if (digest !== d.sha256) throw new Error('JSON checksum verification failed.');
      const decoded = await bounded(new Blob([encoded]).stream().pipeThrough(new DecompressionStream('gzip')), d.decoded_size_bytes);
      return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(decoded));
    } finally { clearTimeout(timer); }
  }
  function load(section, mode = 'raw') {
    if (!section || !['raw', 'defaulted'].includes(mode)) return Promise.reject(new Error('Unknown JSON export mode.'));
    if (!cache.has(section)) cache.set(section, new Map());
    const modes = cache.get(section);
    if (!modes.has(mode)) modes.set(mode, fetchObject(section, mode).catch(error => { modes.delete(mode); throw error; }));
    return modes.get(mode);
  }
  function chooser(section, trigger) {
    section.querySelector('.object-status').textContent = '';
    const dialog = document.createElement('dialog'); dialog.className = 'object-dialog';
    const heading = node('h2', 'Copy JSON'); heading.id = 'object-copy-title'; dialog.setAttribute('aria-labelledby', heading.id);
    const explanation = node('p', section.dataset.defaulted ?
      'Raw keeps unknowns as null. With defaults applies the documented program policy (' + section.dataset.assumptions + ' recorded assumptions). Source evidence retains unknowns; geometry bindings remain your responsibility.' :
      section.dataset.defaultReason);
    const raw = node('button', 'Copy raw'), ready = node('button', 'Copy with defaults'), cancel = node('button', 'Cancel');
    [raw, ready, cancel].forEach(b => { b.type = 'button'; }); ready.disabled = !section.dataset.defaulted;
    const status = node('p', ''); status.className = 'object-dialog-status'; status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
    dialog.append(heading, explanation, raw, ready, cancel, status); document.body.append(dialog);
    dialog.addEventListener('close', () => { dialog.remove(); trigger.focus(); });
    cancel.addEventListener('click', () => dialog.close());
    async function copy(mode) {
      raw.disabled = true; ready.disabled = true; status.textContent = 'Loading verified JSON…';
      dialog.querySelector('textarea')?.remove();
      try {
        const value = JSON.stringify(await load(section, mode), null, 2);
        if (!dialog.open) return;
        try { await navigator.clipboard.writeText(value); }
        catch (_) {
          status.textContent = 'The clipboard is unavailable. Select and copy the complete JSON below.';
          const text = document.createElement('textarea'); text.readOnly = true; text.value = value;
          text.setAttribute('aria-label', 'Complete JSON for manual copy'); dialog.append(text); text.focus(); text.select(); return;
        }
        section.querySelector('.object-status').textContent = (mode === 'raw' ? 'Raw JSON' : 'JSON with defaults') + ' copied.';
        if (dialog.open) dialog.close();
      } catch (error) { if (dialog.open) status.textContent = error.message; }
      finally { raw.disabled = false; ready.disabled = !section.dataset.defaulted; }
    }
    raw.addEventListener('click', () => copy('raw')); ready.addEventListener('click', () => copy('defaulted'));
    dialog.showModal(); raw.focus();
  }
  function init() {
    document.querySelectorAll('.object-json').forEach(section => {
      const details = section.querySelector('.object-source'), status = section.querySelector('.object-status');
      details.addEventListener('toggle', async () => {
        if (!details.open) return; status.textContent = 'Loading verified JSON…';
        try { details.querySelector('pre').textContent = JSON.stringify(await load(section), null, 2); status.textContent = 'Complete raw JSON; unknowns remain null.'; }
        catch (error) { status.textContent = error.message; }
      });
      const trigger = section.querySelector('.object-copy'); trigger.addEventListener('click', () => chooser(section, trigger));
    });
  }
  window.AtlasObjects = {load};
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
