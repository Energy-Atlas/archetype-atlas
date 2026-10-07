(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.DefinitionCore = api;
})(typeof globalThis === 'undefined' ? this : globalThis, function () {
  'use strict';
  function filter(entries, filters) {
    let pool = entries;
    if (filters.evidence_view === 'reviewed') {
      const replaced = new Set(entries.map(r => r.source_definition_id).filter(Boolean));
      pool = entries.filter(r => !replaced.has(r.id));
    }
    return pool.filter(row => {
      const contextual = Object.entries(filters).filter(([k,v]) => ['building','climate'].includes(k) && v);
      if (row.applicability?.length && !row.applicability.some(c => contextual.every(([k,v]) => c[k] === v))) return false;
      return Object.entries(filters).every(([key, value]) => {
      if (!value) return true;
      if (row.applicability?.length && ['building','climate'].includes(key)) return true;
      if (key === 'search') return [row.name, row.id, row.building, row.template, row.source_family].join(' ').toLowerCase().includes(value.toLowerCase());
      if (key === 'detail') return (row.available_details || [row.detail]).includes(value);
      if (key === 'evidence_view' && value === 'reviewed') return true;
      return row[key] === value;
    });});
  }
  function change(filters, key, value) {
    const next = {...filters, [key]: value};
    if (key === 'building') for (const dependent of ['detail', 'vintage', 'climate', 'system_type']) next[dependent] = '';
    if (key === 'vintage') next.climate = '';
    return next;
  }
  function defaults(entries, filters, explicitKeys = []) {
    const next = {...filters};
    for (const [key,value] of [['vintage','90.1-2019'],['detail','SourcePrograms']]) {
      if (!next[key] && !explicitKeys.includes(key) && filter(entries,{...next,[key]:value}).length) next[key] = value;
    }
    return next;
  }
  return {filter, change, defaults};
});
