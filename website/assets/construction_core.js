(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ConstructionCore = api;
})(typeof globalThis === 'undefined' ? this : globalThis, function () {
  'use strict';
  function hydrate(packet, contextId) {
    if (packet.kind !== 'construction_site_packet' || packet.schema_version !== '1.0.0') throw new Error('Unsupported construction delivery.');
    const c = packet.contexts[contextId];
    if (!c || c.construction_set_id !== packet.profile.id) throw new Error('Unsupported construction context.');
    const config = packet.component_configurations[c.configuration_id], decisions = packet.selector_receipts[c.selector_receipt_id];
    if (!config || !decisions) throw new Error('Missing construction selection.');
    const required = (table, id) => {
      if (!Object.hasOwn(packet[table], id)) throw new Error('Missing construction resource: ' + id);
      return packet[table][id];
    };
    const ids = new Set(Object.values(config.components).flatMap(v => v.assignments.map(a => a.assembly_id)));
    decisions.forEach(d => d.candidate_element_ids.forEach(id => ids.add(id)));
    const select = (table, keys) => Object.fromEntries([...keys].sort().map(id => [id, required(table, id)]));
    const assemblies = select('assemblies', ids);
    const materials = select('materials', new Set(Object.values(assemblies).flatMap(a => a.layers.map(l => l.material_id))));
    const evidenceIds = new Set(c.source_evidence_ids);
    function collect(value) {
      if (Array.isArray(value)) value.forEach(collect);
      else if (value && typeof value === 'object') for (const [key, v] of Object.entries(value)) {
        if (key === 'evidence_id') evidenceIds.add(v);
        else if (key === 'evidence_ids') v.forEach(id => evidenceIds.add(id));
        else if (key === 'property_evidence') Object.values(v).forEach(id => evidenceIds.add(id));
        else if (key !== 'original_value') collect(v);
      }
    }
    [assemblies, materials, config.components, c.infiltration, decisions].forEach(collect);
    const pending = [...evidenceIds];
    while (pending.length) {
      const proof = required('evidence', pending.pop());
      for (const id of proof.original_value?.source_layer_evidence_ids || []) {
        if (!evidenceIds.has(id)) {evidenceIds.add(id);pending.push(id);}
      }
    }
    return structuredClone({schema_version: '2.0.0', kind: 'construction_set', export_mode: 'source_ready',
      id: contextId, name: packet.profile.name, scope: packet.profile.scope,
      source: {...packet.profile.source, climate: {status: 'exact', value: c.climate_zone},
        reference_variant_id: c.reference_id, evidence: c.source_evidence_ids.map(id => required('evidence', id))},
      components: config.components, infiltration: c.infiltration, assemblies, materials,
      evidence: select('evidence', evidenceIds), metadata: {...packet.metadata,
        source_definition_ids: config.source_definition_ids, selection_decisions: decisions, variant_selections: {}}});
  }
  function select(contexts, climate = '', reference = '', building = '') {
    const climates = [...new Set(contexts.map(c => c.climate))];
    if (climate && !climates.includes(climate)) throw new Error('Unsupported construction climate.');
    if (!climate && climates.length === 1) climate = climates[0];
    const available = contexts.filter(c => !climate || c.climate === climate);
    const references = [...new Set(available.map(c => c.reference))];
    if (reference && !references.includes(reference)) throw new Error('Unsupported source reference for this climate.');
    if (climate && !reference) {
      const hinted = [...new Set(available.filter(c => c.building === building).map(c => c.reference))];
      if (building && hinted.length === 1) reference = hinted[0];
      else if (references.length === 1) reference = references[0];
    }
    const matches = available.filter(c => c.climate === climate && c.reference === reference);
    if (matches.length > 1) throw new Error('Ambiguous construction context.');
    return {climate, reference, id:matches.length === 1 ? matches[0].id : null};
  }
  return {hydrate, select};
});
