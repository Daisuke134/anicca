// node:test — deliver detection pure logic (RED). Real fetch is the E2E wake (#10).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pendingDeliveries } from '../lib/deliver.mjs';

test('surfaces accepted/in-progress contracts as pending deliveries', () => {
  const p = pendingDeliveries({ data: [
    { id: 'c1', status: 'accepted', title: 'Flask CRUD', amount: 50 },
    { id: 'c2', status: 'in_progress', title: 'Scraper' },
    { id: 'c3', status: 'completed', title: 'done one' },   // not pending
    { id: 'c4', status: 'bidding', title: 'still open' },    // not accepted yet
  ] });
  const ids = p.map(x => x.id);
  assert.deepEqual(ids, ['c1', 'c2']);
});

test('empty / no contracts → no pending (never invents work)', () => {
  assert.deepEqual(pendingDeliveries({ data: [] }), []);
  assert.deepEqual(pendingDeliveries({}), []);
});
