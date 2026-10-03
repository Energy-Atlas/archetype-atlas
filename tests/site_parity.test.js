/* Exhaustively compare inspection selectors with the canonical Python helper. */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const core = require('../website/assets/core.js');
test('all v0.2.0 schedule selections agree with the Python atlas inspector', () => {
  const windowsPython = path.resolve(__dirname, '../.venv/Scripts/python.exe');
  const python = process.env.PYTHON || (fs.existsSync(windowsPython) ? windowsPython : 'python');
  const code = [
    'import json',
    'from scripts.common import load_json',
    'from scripts.semantics import profile',
    "schedules=load_json('data/releases/v0.2.0/schedules.json')",
    "days=['Mon','Tue','Wed','Thu','Fri','Sat','Sun','Hol','WntrDsn','SmrDsn']",
    "dates=['01-15','03-31','06-01','07-15','09-01','12-31','02-29']",
    'cases=[]',
    'for s in schedules:',
    ' for day in days:',
    '  for date in dates:',
    '   try: value=profile(s["rules"],day,date)',
    '   except ValueError: value=None',
    '   cases.append([s["id"],day,"2000-"+date,value])',
    'print(json.dumps({"schedules":schedules,"cases":cases}))',
  ].join('\n');
  const data = JSON.parse(execFileSync(python, ['-c', code], {maxBuffer: 80 * 1024 * 1024}));
  const schedules = new Map(data.schedules.map(r => [r.id, r]));
  for (const [id, day, date, expected] of data.cases) {
    if (expected === null) {
      assert.throws(() => core.selectProfile(schedules.get(id), day, date), /No profile/, id + '/' + day + '/' + date);
    } else {
      assert.deepEqual(core.selectProfile(schedules.get(id), day, date).values, expected, id + '/' + day + '/' + date);
    }
  }
  assert.equal(data.cases.length, 39830);
});
