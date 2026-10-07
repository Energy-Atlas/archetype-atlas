/* Pure, source-faithful schedule inspection. UTC is used only for calendar arithmetic. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ScheduleCore = api;
})(typeof globalThis === 'undefined' ? this : globalThis, function () {
  'use strict';
  const days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
  const allowed = new Set(['Default','Wkdy','Wknd',...days,'Hol','WntrDsn','SmrDsn']);
  function date(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error('Invalid calendar date');
    const d = new Date(value + 'T00:00:00Z');
    if (!Number.isFinite(d.valueOf()) || d.toISOString().slice(0,10) !== value) throw new Error('Invalid calendar date');
    return d;
  }
  function yearDates(year) {
    if (!Number.isInteger(year) || year < 1 || year > 9999) throw new Error('Invalid calendar year');
    const first = date(String(year).padStart(4,'0') + '-01-01');
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    return Array.from({length:leap ? 366 : 365},(_,i)=>new Date(first.valueOf()+i*86400000).toISOString().slice(0,10));
  }
  function validateValues(values, unit, lengths) {
    if (!Array.isArray(values) || !lengths.includes(values.length)) throw new Error('Unsupported schedule length');
    if (values.some(v=>typeof v !== 'number' || !Number.isFinite(v) || unit === '1' && (v<0 || v>1) || unit === 'W/person' && v<0)) throw new Error('Invalid schedule value');
  }
  function normalize(record) {
    const unit = {'dimensionless':'1','C':'degC'}[record.units] || record.unit || record.units;
    if (!['1','degC','W/person'].includes(unit)) throw new Error('Unsupported schedule unit');
    const step = record.timestep_minutes || record.time_resolution_minutes || 60;
    if (step !== 60) throw new Error('Unsupported schedule timestep');
    const common = {id:record.id,name:record.name || record.source_name || record.source_channel || record.id,unit,timestep_minutes:step};
    if (record.type === 'annual' || record.annual_values) {
      const year = record.year || record.calendar?.year, values = record.values || record.annual_values;
      validateValues(values,unit,[yearDates(year).length*24]);
      return {...common,type:'annual',year,clock:'local_standard_time',values};
    }
    if (!Array.isArray(record.rules) || !record.rules.length) throw new Error('Missing schedule rules');
    const rules = record.rules.map(r=>{
      const start = r.start_date.length===5 ? r.start_date : r.start_date.slice(5,10);
      const end = r.end_date.length===5 ? r.end_date : r.end_date.slice(5,10);
      date('2000-'+start);date('2000-'+end);
      const tokens = (Array.isArray(r.day_types) ? r.day_types : r.day_types.split('|')).map(d=>d==='DummySmrDsn'?'SmrDsn':d);
      if (!tokens.length || tokens.some(d=>!allowed.has(d))) throw new Error('Unsupported day selector');
      validateValues(r.values,unit,[1,24]);
      return {start_date:start,end_date:end,day_types:[...new Set(tokens)],values:r.values};
    });
    return {...common,type:'ruleset',rules};
  }
  function choose(s, day, value) {
    const d = date(value), md = value.slice(5);
    day = day || ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getUTCDay()];
    if (!allowed.has(day)) throw new Error('Unknown day selector');
    if (s.type === 'annual') {
      if (d.getUTCFullYear() !== s.year) throw new Error('Choose the recorded year '+s.year);
      if (['Hol','WntrDsn','SmrDsn'].includes(day)) throw new Error('Annual realizations have no special-day overrides');
      const start = (d.valueOf()-date(String(s.year).padStart(4,'0')+'-01-01').valueOf())/3600000;
      return {values:s.values.slice(start,start+24),ruleIndex:null,matching:[],dayType:day};
    }
    let specific=null, fallback=null;const matching=[];
    s.rules.forEach((r,i)=>{
      const applies = r.start_date<=r.end_date ? md>=r.start_date && md<=r.end_date : md>=r.start_date || md<=r.end_date;
      if (!applies) return;
      const tokens=r.day_types;
      const exact=tokens.includes(day) || days.slice(0,5).includes(day) && tokens.includes('Wkdy') || ['Sat','Sun'].includes(day) && tokens.includes('Wknd');
      const picked={values:r.values.length===1?Array(24).fill(r.values[0]):r.values,ruleIndex:i};
      if (tokens.includes('Default')) fallback=picked;
      if (exact) specific=picked;
      if (exact || tokens.includes('Default')) matching.push(i);
    });
    return {...(specific || fallback || {values:Array(24).fill(null),ruleIndex:null}),matching,dayType:day};
  }
  function profile(record, day, value) {return choose(normalize(record),day,value);}
  function annual(record, year, holidays=[]) {
    const s=normalize(record), dates=yearDates(year), holidaySet=new Set(holidays);
    if (s.type==='annual' && year!==s.year) throw new Error('Annual realization requires its recorded year '+s.year);
    if (s.type==='annual' && holidays.length) throw new Error('Annual realizations cannot apply holiday overrides');
    for (const h of holidays) date(String(year).padStart(4,'0')+'-'+h);
    const z=Array.from({length:24},()=>[]), ruleIndices=[], dayTypes=[];let missingHours=0;
    for (const value of dates) {
      const p=choose(s,holidaySet.has(value.slice(5))?'Hol':undefined,value);
      ruleIndices.push(p.ruleIndex);dayTypes.push(p.dayType);
      p.values.forEach((v,h)=>{z[h].push(v);if(v===null)missingHours++;});
    }
    return {dates,z,ruleIndices,dayTypes,missingHours,unit:s.unit,year};
  }
  function uniqueDays(record) {
    const s=normalize(record), profiles=new Map();
    const items=s.type==='ruleset'?s.rules.map((r,i)=>({values:r.values.length===1?Array(24).fill(r.values[0]):r.values,
      label:r.day_types.join('|')+' · '+r.start_date+' → '+r.end_date,rule:i})):
      yearDates(s.year).map((d,i)=>({values:s.values.slice(i*24,i*24+24),label:d,rule:null}));
    for (const item of items) {
      const key=JSON.stringify(item.values);
      if (!profiles.has(key)) profiles.set(key,{values:item.values,labels:[],rules:[]});
      const p=profiles.get(key);p.labels.push(item.label);if(item.rule!==null)p.rules.push(item.rule);
    }
    return [...profiles.values()];
  }
  return {normalize,profile,annual,uniqueDays};
});
