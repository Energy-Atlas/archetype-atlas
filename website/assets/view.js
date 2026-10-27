/* The `view/?id=` viewer (ADR 0043): finds any published ID in the store's index packets and either opens the
   page and anchor that render it or shows its own JSON (evidence rows have no page of their own). */
(function () {
  'use strict';

  async function lookup(root, index, id) {
    const packets = index.packets;
    let low = 0, high = packets.length - 1, found = -1;
    while (low <= high) {
      const middle = (low + high) >> 1;
      if (packets[middle].first <= id) { found = middle; low = middle + 1; } else high = middle - 1;
    }
    if (found < 0) return null;
    const packet = await window.AtlasStore.load(packets[found], root);
    return Object.prototype.hasOwnProperty.call(packet, id) ? packet[id] : null;
  }

  function init() {
    const viewer = document.querySelector('[data-viewer]');
    if (!viewer) return;
    const root = new URL(viewer.dataset.root, location.href);
    const form = viewer.querySelector('form');
    const input = form.querySelector('input[name="id"]');
    const message = viewer.querySelector('.ea-viewer__status');
    const result = viewer.querySelector('.ea-viewer__result');
    let index;

    async function show(id) {
      result.replaceChildren();
      if (!id) { message.textContent = 'Enter a program, schedule, construction, assembly, material or evidence ID.'; return; }
      message.textContent = 'Looking up ' + id + '…';
      try {
        if (!index) {
          const response = await fetch(new URL(viewer.dataset.index, location.href));
          if (!response.ok) throw new Error('ID index unavailable (' + response.status + ').');
          index = await response.json();
        }
        const row = await lookup(root, index, id);
        if (!row) { message.textContent = 'No object with ID ' + id + ' in release ' + index.release + '.'; return; }
        if (row.page) {
          const target = new URL(row.page, root);
          target.hash = row.anchor;
          message.textContent = 'Opening ' + id + '…';
          location.replace(target.href);
          return;
        }
        const value = row.object !== undefined ? row.object : await window.AtlasStore.load(row.json, root);
        message.textContent = id + ' (release ' + index.release + ')';
        const pre = document.createElement('pre');
        pre.className = 'ea-viewer__json';
        pre.textContent = JSON.stringify(value, null, 2);
        result.append(pre);
      } catch (error) { message.textContent = error.message; }
    }

    form.addEventListener('submit', event => {
      event.preventDefault();
      const id = input.value.trim();
      history.replaceState(null, '', location.pathname + '?id=' + encodeURIComponent(id));
      show(id);
    });
    const id = new URLSearchParams(location.search).get('id') || '';
    input.value = id;
    show(id);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
