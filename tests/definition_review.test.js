const test = require('node:test');
const assert = require('node:assert/strict');
const core = require('../website/assets/definition_core.js');
const rows = [{id:'a',building:'Office',vintage:'90.1-2019',detail:'SourcePrograms',evidence_view:'source'},
  {id:'b',building:'Dwelling',vintage:'ResStock',detail:'SourcePrograms',evidence_view:'source'}];
test('supported context gets specified defaults and unsupported vintage stays All', () => {
  assert.equal(core.defaults(rows,{building:'Office',vintage:'',detail:''}).vintage,'90.1-2019');
  assert.equal(core.defaults(rows,{building:'Office',vintage:'',detail:''}).detail,'SourcePrograms');
  assert.equal(core.defaults(rows,{building:'Dwelling',vintage:'',detail:''}).vintage,'');
});
test('explicit stale and explicit All URL choices are preserved', () => {
  assert.equal(core.defaults(rows,{vintage:'stale',detail:''},['vintage']).vintage,'stale');
  assert.equal(core.defaults(rows,{vintage:'',detail:''},['vintage']).vintage,'');
});
test('construction building and climate must match the same applicability context', () => {
  const entries=[{id:'wall',building:'Shared elements',climate:null,applicability:[
    {building:'Office',climate:'CZ1'},{building:'Restaurant',climate:'CZ7'}]}];
  assert.equal(core.filter(entries,{building:'Restaurant',climate:'CZ7'}).length,1);
  assert.equal(core.filter(entries,{building:'Restaurant',climate:'CZ1'}).length,0);
});
