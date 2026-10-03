/* Source-faithful schedule inspection and catalogue state; no DOM dependencies. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AtlasCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const days = new Set(['Default', 'Wkdy', 'Wknd', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri',
    'Sat', 'Sun', 'Hol', 'WntrDsn', 'SmrDsn', 'DummySmrDsn']);
  const keys = ['q', 'kind', 'building', 'program', 'template', 'climate', 'system', 'source', 'status', 'stock_vintage'];
  function selectProfile(schedule, day, date) {
    if (!days.has(day)) throw new Error('Unknown day type');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new Error('Invalid inspection date');
    const parsed = new Date(date + 'T00:00:00Z');
    if (Number.isNaN(parsed.valueOf()) || parsed.toISOString().slice(0, 10) !== date) throw new Error('Invalid inspection date');
    const md = date.slice(5);
    let specific = null, fallback = null;
    const matching = [];
    schedule.rules.forEach((rule, index) => {
      const tokens = new Set(rule.day_types.split('|'));
      if ([...tokens].some(t => !days.has(t))) throw new Error('Unsupported day selector');
      if (tokens.has('DummySmrDsn')) tokens.add('SmrDsn');
      const start = rule.start_date.slice(5, 10), end = rule.end_date.slice(5, 10);
      const applies = start <= end ? md >= start && md <= end : md >= start || md <= end;
      if (!applies) return;
      const values = rule.values.length === 1 ? Array(24).fill(rule.values[0]) : [...rule.values];
      if (values.length !== 24) throw new Error('Expected constant or 24-hour schedule');
      if (values.some(v => typeof v !== 'number' || !Number.isFinite(v))) throw new Error('Expected numeric profile values');
      const exact = tokens.has(day) ||
        (['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].includes(day) && tokens.has('Wkdy')) ||
        (['Sat', 'Sun'].includes(day) && tokens.has('Wknd'));
      if (tokens.has('Default')) fallback = {values, ruleIndex: index};
      if (exact) specific = {values, ruleIndex: index};
      if (tokens.has('Default') || exact) matching.push(index);
    });
    const selected = specific || fallback;
    if (!selected) throw new Error('No profile for this date and day type');
    return {...selected, matching};
  }
  function filterEntries(entries, state) {
    const query = (state.q || '').toLocaleLowerCase().trim();
    return entries.filter(row => {
      if (query && !Object.values(row).flat().join(' ').toLocaleLowerCase().includes(query)) return false;
      return keys.filter(k => k !== 'q' && state[k]).every(k => row[k] === state[k] ||
        (k === 'building' && (row.referenced_buildings || []).includes(state[k])) ||
        (k === 'template' && (row.referenced_templates || []).includes(state[k])));
    });
  }
  function parseState(search) {
    const params = new URLSearchParams(search);
    return Object.fromEntries(keys.filter(k => params.get(k)).map(k => [k, params.get(k)]));
  }
  function serializeState(state) {
    return new URLSearchParams(Object.fromEntries(keys.filter(k => state[k]).map(k => [k, state[k]]))).toString();
  }
  function thermostatDiagnostic(heating, cooling) {
    if (heating.length !== cooling.length || !heating.length) throw new Error('Incompatible thermostat profiles');
    const differences = heating.map((value, i) => cooling[i] - value);
    return {minimumDeadband: Math.min(...differences), overlapHours: differences.flatMap((v, h) => v < 0 ? [h] : [])};
  }
  return {selectProfile, filterEntries, parseState, serializeState, thermostatDiagnostic};
});
