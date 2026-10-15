(function () {
  'use strict';
  const node = (tag, text) => {const n = document.createElement(tag);n.textContent = text;return n;};
  function init(section) {
    const contexts = JSON.parse(section.dataset.contexts), params = new URLSearchParams(location.search);
    const climate = section.querySelector('.construction-climate'), reference = section.querySelector('.construction-reference');
    const representation = section.querySelector('.construction-representation'), download = section.querySelector('.construction-download');
    const status = section.querySelector('.object-status'), details = section.querySelector('.object-source');
    const trigger = section.querySelector('.object-copy');let selected = null, revision = 0, previewToken = 0;
    representation.value = params.get('representation') === 'unified' ? 'unified' : 'detailed';
    const label = () => representation.value === 'unified' ? 'Unified' : 'Detailed';
    function describe() {
      trigger.textContent = 'Copy ' + label().toLowerCase() + ' JSON';
      download.textContent = 'Download ' + label().toLowerCase() + ' JSON';download.disabled = !selected;
      section.querySelector('.construction-description').textContent = representation.value === 'unified' ?
        'Unified building construction: one assembly per component type, using precomputed source-archetype shares. Fit errors and mass-budget approximations remain explicit. BEMGen supplies actual geometry, including overhangs.' :
        'Detailed construction set: original assemblies, materials, program/story assignment rules and source evidence. BEMGen resolves assignments using actual model geometry.';
    }
    climate.value = params.get('climate') || '';
    if (params.get('climate') && ![...climate.options].some(o => o.value === params.get('climate'))) {
      const option = node('option', params.get('climate') + ' (unavailable)');option.value = params.get('climate');climate.append(option);climate.value = option.value;
    }
    function update(requested = reference.value, building = '') {
      revision++;selected = null;reference.replaceChildren();
      try {
        const state = ConstructionCore.select(contexts, climate.value, requested, building);climate.value = state.climate;
        const first = node('option', state.climate ? 'Choose source reference' : 'Choose climate first');first.value = '';reference.append(first);
        const available = contexts.filter(c => c.climate === state.climate);
        for (const value of [...new Set(available.map(c => c.reference))].sort()) {
          const option = node('option', value);option.value = value;reference.append(option);
        }
        reference.value = state.reference;reference.disabled = !state.climate;selected = state.id;
        status.textContent = selected ? label() + ' construction JSON selected. Expand, copy or download this representation.' : 'Choose a climate and source reference to export construction JSON.';
        const query = new URLSearchParams(location.search);
        if (state.climate) query.set('climate', state.climate);else query.delete('climate');
        if (state.reference) query.set('reference', state.reference);else query.delete('reference');
        if (representation.value === 'unified') query.set('representation', 'unified');else query.delete('representation');
        history.replaceState(null, '', location.pathname + (query.size ? '?' + query : ''));
      } catch (error) {status.textContent = error.message;}
      describe();previewToken++;details.querySelector('pre').textContent = 'Expand to load the complete selected ' + label().toLowerCase() + ' construction JSON.';
      if (details.open) preview();
    }
    async function ready() {
      const identity = selected, version = revision, mode = representation.value;
      if (!identity) throw new Error('Choose a supported climate and source reference.');
      const packet = await AtlasObjects.load(section, mode === 'unified' ? 'unified' : 'construction');
      if (identity !== selected || version !== revision) throw new Error('Selection changed while loading; try again.');
      return mode === 'unified' ? ConstructionCore.hydrateUnified(packet, identity) : ConstructionCore.hydrate(packet, identity);
    }
    async function preview() {
      const token = ++previewToken;
      status.textContent = 'Loading verified construction JSON…';
      try {const value = await ready();if (token !== previewToken) return;details.querySelector('pre').textContent = JSON.stringify(value, null, 2);status.textContent = label() + ' JSON verified; fixed reference ACH and provenance retained.';}
      catch (error) {if (token === previewToken) status.textContent = error.message;}
    }
    climate.addEventListener('change', () => update(''));
    reference.addEventListener('change', () => update());
    representation.addEventListener('change', () => update());
    details.addEventListener('toggle', () => {if (details.open) preview();});
    download.addEventListener('click', async () => {
      const identity = selected, mode = representation.value;
      download.disabled = true;status.textContent = 'Preparing verified ' + mode + ' JSON…';
      try {
        const value = await ready(), blob = new Blob([JSON.stringify(value, null, 2) + '\n'], {type: 'application/json'});
        const url = URL.createObjectURL(blob), link = document.createElement('a');
        link.href = url;link.download = identity + '-' + mode + '.json';document.body.append(link);link.click();link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);status.textContent = label() + ' JSON downloaded as a separate file.';
      } catch (error) {status.textContent = error.message;}
      finally {download.disabled = !selected;}
    });
    trigger.addEventListener('click', () => {
      const dialog = document.createElement('dialog');dialog.className = 'object-dialog';
      const heading = node('h2', 'Copy construction JSON');heading.id = 'construction-copy-title';dialog.setAttribute('aria-labelledby', heading.id);
      const info = node('p', section.querySelector('.construction-description').textContent + ' Copy exports only the selected representation. Source JSON retains the original source definition.');
      const copyReady = node('button', 'Copy ' + label().toLowerCase() + ' JSON'), copyRaw = node('button', 'Copy source JSON'), cancel = node('button', 'Cancel');
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
          status.textContent = (mode === 'construction' ? label() + ' construction JSON' : 'Source JSON') + ' copied.';dialog.close();
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
