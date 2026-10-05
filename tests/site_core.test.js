'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const corePath = path.resolve(__dirname, '../website/assets/core.js');
const exists = fs.existsSync(corePath);
const core = exists ? require(corePath) : null;
const rule = (day, value, start = '2014-01-01', end = '2014-12-31') => ({
  day_types: day, values: [value], start_date: start, end_date: end,
});
function ready() { assert.ok(core, 'Browser schedule/filter logic is not implemented'); }

test('executed profiles select actual calendar hours and reject missing or invalid series', () => {
  const profile = {metadata: {year: 2007, timestep_minutes: 60, columns: {occupants: 'dimensionless'}},
    series: {occupants: Array.from({length: 8760}, (_, i) => (i % 24) / 24)}};
  const day = core.annualProfile(profile, 'day', '2007-02-01', ['occupants']);
  assert.equal(day.startHour, 31 * 24);
  assert.equal(day.labels[0], '2007-02-01T00:00:00');
  assert.equal(day.traces[0].values.length, 24);
  assert.equal(core.annualProfile(profile, 'annual', '', ['occupants']).labels.length, 8760);
  assert.throws(() => core.annualProfile(profile, 'day', '2008-01-01', ['occupants']));
  assert.throws(() => core.annualProfile(profile, 'day', '2007-02-30', ['occupants']));
  assert.throws(() => core.annualProfile(profile, 'day', '2007-01-01', ['missing']));
  profile.series.occupants[0] = 2;
  assert.throws(() => core.annualProfile(profile, 'day', '2007-01-01', ['occupants']));
});

test('specific seasonal rules override defaults in source order, preserving zero', () => {
  ready();
  const schedule = {rules: [rule('Default', 1), rule('Wkdy', 0.5),
    rule('Mon', 0, '2014-06-01', '2014-08-31')]};
  assert.deepEqual(core.selectProfile(schedule, 'Mon', '2000-07-01').values, Array(24).fill(0));
  assert.equal(core.selectProfile(schedule, 'Tue', '2000-07-01').values[0], 0.5);
  assert.equal(core.selectProfile(schedule, 'Sat', '2000-07-01').values[0], 1);
  assert.equal(core.selectProfile(schedule, 'Mon', '2000-01-01').values[0], 0.5);
});
test('wrapped seasons, holidays and DummySmrDsn retain source semantics', () => {
  ready();
  const schedule = {rules: [rule('Default', 0.1), rule('Wknd', 0.2),
    rule('Hol', 0.3), rule('Mon', 0.4, '2014-11-01', '2014-03-31'),
    rule('DummySmrDsn', 0.9)]};
  assert.equal(core.selectProfile(schedule, 'Mon', '2000-12-01').values[0], 0.4);
  assert.equal(core.selectProfile(schedule, 'Sun', '2000-04-01').values[0], 0.2);
  assert.equal(core.selectProfile(schedule, 'Hol', '2000-04-01').values[0], 0.3);
  assert.equal(core.selectProfile(schedule, 'SmrDsn', '2000-04-01').values[0], 0.9);
});
test('missing, malformed or invalid date profiles never become zeros', () => {
  ready();
  assert.throws(() => core.selectProfile({rules: [rule('Mon', 1)]}, 'Sun', '2000-01-01'), /No profile/);
  assert.throws(() => core.selectProfile({rules: [rule('Default', null)]}, 'Mon', '2000-01-01'), /numeric/);
  assert.throws(() => core.selectProfile({rules: []}, 'Mon', '2000-02-30'), /date/);
  assert.throws(() => core.selectProfile({rules: [rule('Bogus', 0)]}, 'Mon', '2000-01-01'), /day/);
});
test('shareable filters preserve exact climate labels and referenced schedule context', () => {
  ready();
  const entries = [
    {name: 'Office', kind: 'programs', building: 'MediumOffice', climate: 'Unspecified', template: '90.1-2013'},
    {name: 'Roof', kind: 'envelope_components', climate: 'ClimateZone 4', template: '90.1-2013'},
    {name: 'Roof', kind: 'envelope_components', climate: 'ClimateZone 4A', template: '90.1-2013'},
    {name: 'Office hours', kind: 'schedules', building: 'Shared', referenced_buildings: ['MediumOffice'],
      referenced_contexts: [{building: 'MediumOffice', template: '90.1-2013'}]},
  ];
  assert.equal(core.filterEntries(entries, {climate: 'ClimateZone 4'}).length, 1);
  assert.equal(core.filterEntries(entries, {building: 'MediumOffice'}).length, 2);
  assert.equal(core.filterEntries(entries, {q: 'office', kind: 'programs'}).length, 1);
  const state = {q: 'roof & wall', climate: 'ClimateZone 4A', template: '90.1-2013'};
  assert.deepEqual(core.parseState(core.serializeState(state)), state);
});
test('shared schedule filters require one real joint building/template reference', () => {
  ready();
  const rows = [{name: 'Apartment schedule', building: 'Shared', template: 'Shared',
    referenced_buildings: ['HighriseApartment', 'MidriseApartment'],
    referenced_templates: ['90.1-2007', '90.1-2019'],
    referenced_contexts: [{building: 'HighriseApartment', template: '90.1-2007'},
      {building: 'MidriseApartment', template: '90.1-2019'}]}];
  assert.equal(core.filterEntries(rows, {building: 'HighriseApartment', template: '90.1-2019'}).length, 0);
  assert.equal(core.filterEntries(rows, {building: 'HighriseApartment', template: '90.1-2007'}).length, 1);
  assert.equal(core.filterEntries(rows, {building: 'MidriseApartment', template: '90.1-2019'}).length, 1);
});

test('legacy facet aliases select the same records as aligned labels without broadening climate sets', () => {
  const rows = [
    {id: 'envelope', climate: '2B', facet_aliases: {climate: ['ClimateZone 2B']}},
    {id: 'dwelling', climate: '2B'},
    {id: 'thermal', climate: '2'},
    {id: 'moist', climate: '2A'},
    {id: 'alaska', climate: '7AK'},
    {id: 'general-seven', climate: '7'},
  ];
  assert.deepEqual(core.filterEntries(rows, {climate: 'ClimateZone 2B'}).map(r => r.id), ['envelope', 'dwelling']);
  assert.deepEqual(core.filterEntries(rows, {climate: '2B'}).map(r => r.id), ['envelope', 'dwelling']);
  assert.deepEqual(core.filterEntries(rows, {climate: '2'}).map(r => r.id), ['thermal']);
  assert.deepEqual(core.normalizeState(rows, {climate: 'ClimateZone 2B', q: 'roof'}), {climate: '2B', q: 'roof'});
  assert.equal(core.filterEntries(rows, {climate: '7AK'}).length, 1);
  assert.equal(core.filterEntries(rows, {climate: 'unknown'}).length, 0);
  assert.equal(core.filterEntries([{source: 'Aligned', facet_aliases: {source: ['Legacy']}}], {source: 'Legacy'}).length, 1);
});
test('thermostat diagnostics report overlaps without changing source values', () => {
  ready();
  assert.equal(typeof core.thermostatDiagnostic, 'function', 'Thermostat diagnostic is not implemented');
  const heating = [20, 24, 19], cooling = [22, 23, 19];
  assert.deepEqual(core.thermostatDiagnostic(heating, cooling), {minimumDeadband: -1, overlapHours: [1]});
  assert.deepEqual(heating, [20, 24, 19]);
});
