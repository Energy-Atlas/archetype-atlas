const test = require('node:test'), assert = require('node:assert/strict');
const core = require('../website/assets/construction_core.js');
const finder = require('../website/assets/definition_core.js');
const contexts = [
  {id:'a',climate:'4A',reference:'2019/SmallOffice',building:'Small Office'},
  {id:'b',climate:'4A',reference:'2019/MediumOffice',building:'Medium Office'},
  {id:'c',climate:'5A',reference:'2019/MediumOffice',building:'Medium Office'}
];
test('construction selection requires climate and resolves only unique references', () => {
  assert.equal(core.select(contexts,'','','').id,null);
  assert.equal(core.select(contexts,'4A','','').id,null);
  assert.equal(core.select(contexts,'4A','','Medium Office').id,'b');
  assert.equal(core.select(contexts,'4A','2019/SmallOffice','Medium Office').id,'a');
  assert.equal(core.select(contexts,'5A','','').id,'c');
  assert.equal(core.select([contexts[2]],'','','').id,'c');
  assert.throws(()=>core.select(contexts,'4D','',''),/Unsupported/);
  assert.throws(()=>core.select(contexts,'5A','2019/SmallOffice',''),/Unsupported/);
});
test('construction links preserve selected climate and building; program links stay unchanged', () => {
  const row={path:'../../../definitions/set/',construction_schema:'2.0.0'};
  const url=finder.href(row,{building:'Medium Office',climate:'4A',vintage:'90.1-2019'});
  assert.equal(url,'../../../definitions/set/?climate=4A&building=Medium+Office');
  assert.equal(finder.href({path:'../../../definitions/program/'},{climate:'4A'}),'../../../definitions/program/');
});
