(function () {
  'use strict';
  const node = (tag, text) => {const n = document.createElement(tag);n.textContent = text;return n;};
  function init(section) {
    const contexts = JSON.parse(section.dataset.contexts), params = new URLSearchParams(location.search);
    const climate = section.querySelector('.construction-climate'), reference = section.querySelector('.construction-reference');
    const representation = section.querySelector('.construction-representation'), unifiedCopy = section.querySelector('.construction-copy-unified');
    const status = section.querySelector('.object-status'), details = section.querySelector('.object-source');
    const trigger = section.querySelector('.object-copy');let selected = null, revision = 0, previewToken = 0, copying = false;
    representation.value = params.get('representation') === 'unified' ? 'unified' : 'detailed';
    const label = () => representation.value === 'unified' ? 'Unified' : 'Detailed';
    const descriptions = {
      unified: 'Unified building construction: simplified ordinary components using precomputed archetype shares, with native foundation methods where needed. Physical host/boundary differences remain explicit. BEMGen supplies actual geometry and weather.',
      detailed: 'Detailed construction set: original assemblies, materials and program/story rules, including the selected foundation configuration. BEMGen resolves assignments using actual model geometry, hosts and weather.'
    };
    function describe() {
      trigger.disabled = !selected || copying;unifiedCopy.disabled = !selected || copying;
      section.querySelector('.construction-description').textContent = descriptions[representation.value];
    }
    climate.value = params.get('climate') || '';
    if (params.get('climate') && ![...climate.options].some(o => o.value === params.get('climate'))) {
      const option = node('option', params.get('climate') + ' (unavailable)');option.value = params.get('climate');climate.append(option);climate.value = option.value;
    }
    function update(requested = reference.value, building = '') {
      revision++;selected = null;reference.replaceChildren();section.querySelector('.construction-manual-copy')?.remove();
      try {
        const state = ConstructionCore.select(contexts, climate.value, requested, building);climate.value = state.climate;
        const first = node('option', state.climate ? 'Choose source reference' : 'Choose climate first');first.value = '';reference.append(first);
        const available = contexts.filter(c => c.climate === state.climate);
        for (const value of [...new Set(available.map(c => c.reference))].sort()) {
          const option = node('option', value);option.value = value;reference.append(option);
        }
        reference.value = state.reference;reference.disabled = !state.climate;selected = state.id;
        status.textContent = selected ? label() + ' JSON preview selected. Copy either representation using its button below.' : 'Choose a climate and source reference to copy construction JSON.';
        const query = new URLSearchParams(location.search);
        if (state.climate) query.set('climate', state.climate);else query.delete('climate');
        if (state.reference) query.set('reference', state.reference);else query.delete('reference');
        if (representation.value === 'unified') query.set('representation', 'unified');else query.delete('representation');
        history.replaceState(null, '', location.pathname + (query.size ? '?' + query : ''));
      } catch (error) {status.textContent = error.message;}
      describe();previewToken++;details.querySelector('pre').textContent = 'Expand to load the complete selected ' + label().toLowerCase() + ' construction JSON.';
      if (details.open) preview();
      groundSummary();
    }
    async function ready(mode = representation.value) {
      const identity = selected, version = revision;
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
    async function groundSummary() {
      const target = section.querySelector('.construction-ground-summary');
      if (!target) return;
      const version = revision;
      target.replaceChildren(node('p', selected ? 'Loading selected foundation…' : 'Select a context to see its foundation configuration and required inputs.'));
      if (!selected) return;
      try {
        const doc = await ready();if (version !== revision) return;
        const ground = doc.foundation_ground;
        if (!ground) throw new Error('Selected construction is missing foundation content.');
        target.replaceChildren(node('h2', 'Foundation and ground'));
        target.append(node('p', 'Configuration: ' + ground.configuration.type));
        if (ground.configuration.reason) target.append(node('p', ground.configuration.reason));
        const methods = [...new Set(Object.values(ground.methods).map(m => m.model))];
        if (methods.length) target.append(node('p', 'Native methods: ' + methods.join(', ') + '. Material and method parameters are included in both JSON copies.'));
        else target.append(node('p', 'This source configuration has no direct ground contact. It does not supply a generic soil-contact slab for a different building configuration.'));
        const exceptions = Object.entries(doc.components).filter(([,c]) => c.native_exception_reason);
        for (const [role, c] of exceptions) target.append(node('p', role + ': ' + c.native_exception_reason));
        const inputs = Object.entries(ground.required_geometry);
        if (inputs.length) {
          target.append(node('h3', 'Required BEM inputs'));
          const list = node('ul', '');
          for (const [name, spec] of inputs) list.append(node('li', name + ' (' + spec.unit + '): ' + spec.description));
          target.append(list);
          target.append(node('p', 'BEMGen also supplies the method-specific weather, site and applicable program controls. Unsupported interfaces or missing inputs must be reported.'));
        }
      } catch (error) {if (version === revision) target.replaceChildren(node('p', error.message));}
    }
    climate.addEventListener('change', () => update(''));
    reference.addEventListener('change', () => update());
    representation.addEventListener('change', () => update());
    details.addEventListener('toggle', () => {if (details.open) preview();});
    async function copy(representationMode) {
      if (copying || !selected) return;
      const version = revision;
      copying = true;describe();status.textContent = 'Loading verified ' + representationMode + ' JSON…';
      section.querySelector('.construction-manual-copy')?.remove();
      try {
        const value = JSON.stringify(await ready(representationMode), null, 2);
        try {await navigator.clipboard.writeText(value);}
        catch (_) {
          if (version !== revision) return;
          status.textContent = 'The clipboard is unavailable. Select and copy the ' + representationMode + ' JSON below.';
          const fallback = node('div', '');fallback.className = 'construction-manual-copy';
          const text = node('textarea', '');text.readOnly = true;text.value = value;
          text.setAttribute('aria-label', representationMode + ' construction JSON for manual copy');
          fallback.append(text);section.append(fallback);text.focus();text.select();return;
        }
        if (version === revision) status.textContent = representationMode + ' construction JSON copied.';
      } catch (error) {if (version === revision) status.textContent = error.message;}
      finally {copying = false;describe();}
    }
    trigger.addEventListener('click', () => copy('detailed'));
    unifiedCopy.addEventListener('click', () => copy('unified'));
    update(params.get('reference') || '', params.get('building') || '');
  }
  window.AtlasConstruction = {init};
})();
