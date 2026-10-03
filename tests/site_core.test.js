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
    {name: 'Office hours', kind: 'schedules', building: 'Shared', referenced_buildings: ['MediumOffice']},
  ];
  assert.equal(core.filterEntries(entries, {climate: 'ClimateZone 4'}).length, 1);
  assert.equal(core.filterEntries(entries, {building: 'MediumOffice'}).length, 2);
  assert.equal(core.filterEntries(entries, {q: 'office', kind: 'programs'}).length, 1);
  const state = {q: 'roof & wall', climate: 'ClimateZone 4A', template: '90.1-2013'};
  assert.deepEqual(core.parseState(core.serializeState(state)), state);
});
test('thermostat diagnostics report overlaps without changing source values', () => {
  ready();
  assert.equal(typeof core.thermostatDiagnostic, 'function', 'Thermostat diagnostic is not implemented');
  const heating = [20, 24, 19], cooling = [22, 23, 19];
  assert.deepEqual(core.thermostatDiagnostic(heating, cooling), {minimumDeadband: -1, overlapHours: [1]});
  assert.deepEqual(heating, [20, 24, 19]);
});
