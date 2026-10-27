/* Context switches of suite pages (ADR 0043): a zone selects every atlas climate label in it. */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const suite = require('../website/assets/suite.js');

test('zones are read from atlas labels and context keys', () => {
  assert.equal(suite.zone('1A-tropical-semi-conditioned'), '1A');
  assert.equal(suite.zone('4-c'), '4C');
  assert.equal(suite.zone('7'), '7');
  assert.equal(suite.zone('0-a.90-1-2007-large-office'), '0A');
  assert.equal(suite.zone('10A'), null);
  assert.equal(suite.zone(''), null);
});

test('a zone matches every label in it; a full label matches itself only', () => {
  assert.ok(suite.matches('climate', '1A-tropical-semi-conditioned', '1A'));
  assert.ok(suite.matches('climate', '1A-tropical', '1A-tropical'));
  assert.ok(!suite.matches('climate', '1A-tropical-semi-conditioned', '1A-tropical'));
  assert.ok(!suite.matches('climate', '2A-warm-humid', '1A'));
  assert.ok(suite.matches('climate', '4A', ''));
});

test('other axes match exactly', () => {
  assert.ok(suite.matches('foundation', 'slab', 'slab'));
  assert.ok(!suite.matches('foundation', 'slab', 'crawlspace'));
  assert.ok(suite.matches('location', undefined, ''));
});
