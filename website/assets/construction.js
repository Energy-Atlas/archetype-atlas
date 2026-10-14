(function () {
  'use strict';
  const node = (tag, text) => {const n = document.createElement(tag);n.textContent = text;return n;};
  function init(section) {
    const contexts = JSON.parse(section.dataset.contexts), params = new URLSearchParams(location.search);
    const climate = section.querySelector('.construction-climate'), reference = section.querySelector('.construction-reference');
    const status = section.querySelector('.object-status'), details = section.querySelector('.object-source');
    const trigger = section.querySelector('.object-copy');let selected = null;
    climate.value = params.get('climate') || '';
    if (params.get('climate') && ![...climate.options].some(o => o.value === params.get('climate'))) {
      const option = node('option', params.get('climate') + ' (unavailable)');option.value = params.get('climate');climate.append(option);climate.value = option.value;
    }
    function update(requested = reference.value, building = '') {
      selected = null;reference.replaceChildren();
      try {
        const state = ConstructionCore.select(contexts, climate.value, requested, building);climate.value = state.climate;
        const first = node('option', state.climate ? 'Choose source reference' : 'Choose climate first');first.value = '';reference.append(first);
        const available = contexts.filter(c => c.climate === state.climate);
        for (const value of [...new Set(available.map(c => c.reference))].sort()) {
          const option = node('option', value);option.value = value;reference.append(option);
        }
        reference.value = state.reference;reference.disabled = !state.climate;selected = state.id;
        status.textContent = selected ? 'Source-ready construction v2. Expand JSON or copy the selected set.' : 'Choose a climate and source reference to export construction JSON.';
        const query = new URLSearchParams(location.search);
        if (state.climate) query.set('climate', state.climate);else query.delete('climate');
        if (state.reference) query.set('reference', state.reference);else query.delete('reference');
        history.replaceState(null, '', location.pathname + (query.size ? '?' + query : ''));
      } catch (error) {status.textContent = error.message;}
      details.querySelector('pre').textContent = 'Expand to load the complete selected construction JSON.';
      if (details.open) preview();
    }
    async function ready() {
      const identity = selected;
      if (!identity) throw new Error('Choose a supported climate and source reference.');
      const packet = await AtlasObjects.load(section, 'construction');
      if (identity !== selected) throw new Error('Selection changed while loading; try again.');
      return ConstructionCore.hydrate(packet, identity);
    }
    async function preview() {
      status.textContent = 'Loading verified construction JSON…';
      try {const value = await ready();details.querySelector('pre').textContent = JSON.stringify(value, null, 2);status.textContent = 'Complete construction JSON v2; source physics and reference ACH retained.';}
      catch (error) {status.textContent = error.message;}
    }
    climate.addEventListener('change', () => update(''));
    reference.addEventListener('change', () => update());
    details.addEventListener('toggle', () => {if (details.open) preview();});
    trigger.addEventListener('click', () => {
      const dialog = document.createElement('dialog');dialog.className = 'object-dialog';
      const heading = node('h2', 'Copy construction JSON');heading.id = 'construction-copy-title';dialog.setAttribute('aria-labelledby', heading.id);
      const info = node('p', 'Construction JSON v2 contains the selected above-ground component set, materials, fixed reference ACH and provenance. BEMGen supplies actual model geometry. Raw source JSON retains the original source definition.');
      const copyReady = node('button', 'Copy construction JSON'), copyRaw = node('button', 'Copy source JSON'), cancel = node('button', 'Cancel');
      [copyReady, copyRaw, cancel].forEach(b => b.type = 'button');copyReady.disabled = !selected;
      const output = node('p', selected ? '' : 'Choose climate and source reference first.');output.setAttribute('role', 'status');output.setAttribute('aria-live', 'polite');
      dialog.append(heading, info, copyReady, copyRaw, cancel, output);document.body.append(dialog);
      cancel.addEventListener('click', () => dialog.close());dialog.addEventListener('close', () => {dialog.remove();trigger.focus();});
      async function copy(mode) {
        copyReady.disabled = true;copyRaw.disabled = true;output.textContent = 'Loading verified JSON…';dialog.querySelector('textarea')?.remove();
        try {
          const value = JSON.stringify(mode === 'construction' ? await ready() : await AtlasObjects.load(section, 'raw'), null, 2);
          if (!dialog.open) return;
          try {await navigator.clipboard.writeText(value);}
          catch (_) {output.textContent = 'The clipboard is unavailable. Select and copy the complete JSON below.';
            const text = document.createElement('textarea');text.readOnly = true;text.value = value;text.setAttribute('aria-label', 'Complete construction JSON for manual copy');dialog.append(text);text.focus();text.select();return;}
          status.textContent = (mode === 'construction' ? 'Construction JSON v2' : 'Source JSON') + ' copied.';dialog.close();
        } catch (error) {if (dialog.open) output.textContent = error.message;}
        finally {copyReady.disabled = !selected;copyRaw.disabled = false;}
      }
      copyReady.addEventListener('click', () => copy('construction'));copyRaw.addEventListener('click', () => copy('raw'));
      dialog.showModal();(selected ? copyReady : copyRaw).focus();
    });
    update(params.get('reference') || '', params.get('building') || '');
  }
  window.AtlasConstruction = {init};
})();
