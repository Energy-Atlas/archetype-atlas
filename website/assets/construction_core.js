(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ConstructionCore = api;
})(typeof globalThis === 'undefined' ? this : globalThis, function () {
  'use strict';
  function massFor(packet, context) {
    const id = context.mass_contract_id;
    if (!id || !packet.mass_contracts || !Object.hasOwn(packet.mass_contracts, id)) throw new Error('Missing shared mass contract.');
    return packet.mass_contracts[id];
  }
  function withFoundation(base, packet, contextId, unified) {
    const f = packet.foundation, eid = f?.contexts?.[contextId], ext = f?.extensions?.[eid];
    if (!ext) throw new Error('Missing selected foundation extension.');
    const take = (table, ids) => Object.fromEntries(ids.map(id => {
      if (!Object.hasOwn(f[table], id)) throw new Error('Missing foundation resource: ' + id);
      return [id, f[table][id]];
    }));
    const refs = (value, keys, found = new Set()) => {
      if (Array.isArray(value)) value.forEach(v => refs(v, keys, found));
      else if (value && typeof value === 'object') for (const [k, v] of Object.entries(value)) {
        if (keys.includes(k)) found.add(v);else refs(v, keys, found);
      }
      return found;
    };
    const doc = structuredClone(base);
    doc.schema_version = unified ? '2.0.0' : '3.0.0';doc.foundation_ground = structuredClone(ext.foundation_ground);
    Object.assign(doc.components, structuredClone(unified ? ext.unified_components : ext.components));
    Object.assign(doc.assemblies, take('assemblies', ext.assemblies), unified ? take('unified_assemblies', ext.unified_assemblies) : {});
    const used = refs(doc.components, ['assembly_id']);used.delete(null);
    refs(doc.foundation_ground, ['assembly_thickness_id']).forEach(id => used.add(id));
    doc.assemblies = Object.fromEntries(Object.entries(doc.assemblies).filter(([id]) => used.has(id)));
    const materials = {...doc.materials, ...take('materials', ext.materials)};
    const mids = refs(doc.assemblies, ['material_id']);
    refs(doc.foundation_ground, ['material_id', 'material_thickness_id', 'soil_material_id']).forEach(id => mids.add(id));
    doc.materials = Object.fromEntries(Object.entries(materials).filter(([id]) => mids.has(id)));
    doc.evidence = {...doc.evidence, ...take('evidence', ext.evidence)};
    const proof = f.evidence[ext.evidence[0]];
    if (unified) doc.provenance.foundation_ground = {source_locator:proof.source_locator, source_sha256:proof.source_file_sha256};
    else {
      const needed = new Set(Object.values(doc.evidence).flatMap(p => typeof p.source_file_sha256 === 'object' ? Object.values(p.source_file_sha256) : [p.source_file_sha256]));
      doc.metadata.source_files = Object.fromEntries(Object.entries(doc.metadata.source_files).filter(([,v]) => needed.has(v.sha256)));
      for (const [key, hash] of Object.entries(proof.source_file_sha256)) doc.metadata.source_files['atlas-foundation-' + key] = {sha256:hash, source_revision:'foundation-execution/1.0.0'};
    }
    return doc;
  }
  function hydrate(packet, contextId) {
    if (packet.kind !== 'construction_site_packet' || !['1.0.0', '1.1.0', '1.2.0'].includes(packet.schema_version)) throw new Error('Unsupported construction delivery.');
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
    const doc = structuredClone({schema_version: packet.schema_version !== '1.0.0' ? '2.1.0' : '2.0.0',
      ...(packet.schema_version !== '1.0.0' ? {mass_accounting: massFor(packet, c)} : {}), kind: 'construction_set', export_mode: 'source_ready',
      id: contextId, name: packet.profile.name, scope: packet.profile.scope,
      source: {...packet.profile.source, climate: {status: 'exact', value: c.climate_zone},
        reference_variant_id: c.reference_id, evidence: c.source_evidence_ids.map(id => required('evidence', id))},
      components: config.components, infiltration: c.infiltration, assemblies, materials,
      evidence: select('evidence', evidenceIds), metadata: {...packet.metadata,
        source_definition_ids: config.source_definition_ids, selection_decisions: decisions, variant_selections: {}}});
    return packet.schema_version === '1.2.0' ? withFoundation(doc, packet, contextId, false) : doc;
  }
  function hydrateUnified(packet, contextId) {
    if (packet.kind !== 'construction_equivalent_site_packet' || !['1.0.0', '1.1.0', '1.2.0'].includes(packet.schema_version)) throw new Error('Unsupported unified construction delivery.');
    if (!Object.hasOwn(packet.contexts, contextId)) throw new Error('Unsupported unified construction context.');
    const context = structuredClone(packet.contexts[contextId]);
    if (context.detailed_context_id !== contextId || context.kind !== 'building_level_equivalent' || context.schema_version !== (packet.schema_version !== '1.0.0' ? '1.2.0' : '1.1.0')) throw new Error('Invalid unified context.');
    if (!Object.hasOwn(packet.component_sets, context.component_set_id)) throw new Error('Missing unified component set.');
    const body = packet.component_sets[context.component_set_id];delete context.component_set_id;
    const ids = new Set(Object.values(body.components).filter(c => c.status === 'ready').map(c => c.assembly_id));
    const assemblies = Object.fromEntries([...ids].sort().map(id => {
      if (!Object.hasOwn(packet.assemblies, id)) throw new Error('Missing unified assembly: ' + id);
      return [id, packet.assemblies[id]];
    }));
    const mass = packet.schema_version !== '1.0.0' ? {mass_accounting: massFor(packet, context)} : {};
    delete context.mass_contract_id;
    const doc = structuredClone({...context, ...body, assemblies, ...mass});
    return packet.schema_version === '1.2.0' ? withFoundation(doc, packet, contextId, true) : doc;
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
  return {hydrate, hydrateUnified, select};
});
