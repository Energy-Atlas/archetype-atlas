const test = require('node:test');
const assert = require('node:assert/strict');
const core = require('../website/assets/schedule_core.js');
const rule = (day_types, values, start_date='01-01', end_date='12-31') => ({day_types,values,start_date,end_date});
const schedule = rules => ({id:'s',name:'Test',type:'ruleset',unit:'1',timestep_minutes:60,rules});
test('last matching specific rule wins even when a weekday rule comes first', () => {
 const s=schedule([rule(['Default'],[0]),rule(['Mon'],[.8]),rule(['Wkdy'],[.4])]);
 assert.equal(core.profile(s,'Mon','2007-01-01').values[0],.4);
 assert.equal(core.profile(s,'Mon','2007-01-01').ruleIndex,2);
});
test('wrapped seasonal dates and leap day are preserved', () => {
 const s=schedule([rule(['Default'],[0]),rule(['Wkdy'],[1],'11-01','02-29')]);
 assert.equal(core.profile(s,'Mon','2000-02-29').values[0],1);
 assert.equal(core.profile(s,'Mon','2000-07-01').values[0],0);
 assert.equal(core.annual(s,2000,[]).dates.length,366);
 assert.equal(core.annual(s,2007,[]).dates.length,365);
});
test('holiday and design-day rules are distinct from ordinary weekdays', () => {
 const s=schedule([rule(['Default'],[.1]),rule(['Wkdy'],[.5]),rule(['Hol'],[.2]),rule(['WntrDsn'],[.9])]);
 assert.equal(core.annual(s,2007,['01-01']).z[0][0],.2);
 assert.equal(core.annual(s,2007,[]).z[0][0],.5);
 assert.equal(core.profile(s,'WntrDsn','2007-01-01').values[0],.9);
});
test('gaps remain null and are counted, rather than becoming zero', () => {
 const s=schedule([rule(['Wkdy'],[1])]);
 assert.deepEqual(core.profile(s,'Sun','2007-01-07').values,Array(24).fill(null));
 const y=core.annual(s,2007,[]);assert.equal(y.z[0][6],null);assert.ok(y.missingHours>0);
});
test('constant and explicit identical day profiles deduplicate exactly', () => {
 const s=schedule([rule(['Wkdy'],[.5]),rule(['Wknd'],Array(24).fill(.5)),rule(['Hol'],[.50000001])]);
 assert.equal(core.uniqueDays(s).length,2);assert.equal(core.uniqueDays(s)[0].rules.length,2);
});
test('source record dates and aliases normalize without reordering', () => {
 const s=core.normalize({id:'source',units:'C',source_name:'Source',rules:[{day_types:'DummySmrDsn|Wkdy',start_date:'2000-01-01',end_date:'2000-12-31',values:[20]}]});
 assert.equal(s.unit,'degC');assert.deepEqual(s.rules[0].day_types,['SmrDsn','Wkdy']);
});
test('annual realizations retain their recorded year, length and clock', () => {
 const s={id:'a',name:'Annual',type:'annual',unit:'1',timestep_minutes:60,year:2007,clock:'local_standard_time',values:Array(8760).fill(.4)};
 assert.equal(core.annual(s,2007,[]).z[23][364],.4);
 assert.throws(()=>core.annual(s,2008,[]),/recorded year/);
 assert.throws(()=>core.annual(s,2007,['01-01']),/holiday/);
 assert.equal(core.uniqueDays(s).length,1);
 assert.throws(()=>core.normalize({...s,values:Array(8761).fill(0)}),/length/);
});
test('invalid dates, holiday strings and unsupported units fail explicitly', () => {
 assert.throws(()=>core.profile(schedule([rule(['Default'],[1])]),'Mon','2007-02-29'),/date/);
 assert.throws(()=>core.annual(schedule([rule(['Default'],[1])]),2007,['02-30']),/date/);
 assert.throws(()=>core.normalize({...schedule([]),unit:'bananas'}),/unit/);
});
