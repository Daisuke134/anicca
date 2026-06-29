// RED-first tests for the PURE dashboard-core (REQ-4/5/6/8, edges). No network, no Date.now —
// `nowSec` is always a parameter. Run: node --test apps/landing/lib/dashboard-core.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  deriveStatus, isSelfFundedEconomic, countByStatus, normalizeLogKind, toCardModel,
} from './dashboard-core.mjs';

const NOW = 1_000_000; // seconds
const row = (o = {}) => ({
  id: '0x810f6d61f7606deee2657d3083e150a222bc29c5', host: 'anicca-810f6d', ts: NOW,
  model_live: 'claude-sonnet-4-6', model_tier: 'frontier', net_worth_usd: 12.5,
  revenue_mo_usd: 9, burn_day_usd: 0.2, status: 'alive',
  funding: 'human', env: 'local', brain: 'claude-p', log: [], ...o,
});

// REQ-4 deriveStatus
test('deriveStatus: fresh = alive', () => assert.equal(deriveStatus(row({ ts: NOW }), NOW), 'alive'));
test('deriveStatus: dead overrides everything', () => assert.equal(deriveStatus(row({ status: 'dead', ts: NOW }), NOW), 'dead'));
test('deriveStatus: exactly 300s = alive (strict >)', () => assert.equal(deriveStatus(row({ ts: NOW - 300 }), NOW), 'alive'));
test('deriveStatus: 301s = stale', () => assert.equal(deriveStatus(row({ ts: NOW - 301 }), NOW), 'stale'));
test('deriveStatus: missing ts = stale', () => assert.equal(deriveStatus(row({ ts: undefined }), NOW), 'stale'));
test('deriveStatus: null ts = stale', () => assert.equal(deriveStatus(row({ ts: null }), NOW), 'stale'));
test('deriveStatus: NaN ts = stale', () => assert.equal(deriveStatus(row({ ts: NaN }), NOW), 'stale'));
test('deriveStatus: critical preserved (fresh)', () => assert.equal(deriveStatus(row({ status: 'critical', ts: NOW }), NOW), 'critical'));
test('deriveStatus: stale beats critical when old', () => assert.equal(deriveStatus(row({ status: 'critical', ts: NOW - 999 }), NOW), 'stale'));

// REQ-5 isSelfFundedEconomic
test('selfFunded: revenue/30 >= burn → true', () => assert.equal(isSelfFundedEconomic(row({ revenue_mo_usd: 9, burn_day_usd: 0.2 }), NOW), true));
test('selfFunded: revenue/30 < burn → false', () => assert.equal(isSelfFundedEconomic(row({ revenue_mo_usd: 3, burn_day_usd: 0.2 }), NOW), false));
test('selfFunded: dead → false', () => assert.equal(isSelfFundedEconomic(row({ status: 'dead' }), NOW), false));
test('selfFunded: burn 0, revenue 0 → true (0>=0)', () => assert.equal(isSelfFundedEconomic(row({ revenue_mo_usd: 0, burn_day_usd: 0 }), NOW), true));

// REQ-6 countByStatus
test('countByStatus: mixed', () => {
  const rows = [row({ ts: NOW }), row({ ts: NOW - 999 }), row({ status: 'dead' }), row({ status: 'critical', ts: NOW })];
  assert.deepEqual(countByStatus(rows, NOW), { alive: 1, stale: 1, critical: 1, dead: 1 });
});
test('countByStatus: empty fleet = all zero', () => assert.deepEqual(countByStatus([], NOW), { alive: 0, stale: 0, critical: 0, dead: 0 }));

// normalizeLogKind
test('normalizeLogKind: known passes', () => assert.equal(normalizeLogKind('earn'), 'earn'));
test('normalizeLogKind: unknown → info', () => assert.equal(normalizeLogKind('zzz'), 'info'));
test('normalizeLogKind: undefined → info', () => assert.equal(normalizeLogKind(undefined), 'info'));

// REQ-8 toCardModel (full fixed shape)
test('toCardModel: full shape + mappings', () => {
  const c = toCardModel(row(), NOW);
  assert.equal(c.id, '0x810f6d61f7606deee2657d3083e150a222bc29c5');
  assert.equal(c.statusDisplay, 'alive');
  assert.equal(c.funding, 'human'); assert.equal(c.env, 'local'); assert.equal(c.brain, 'claude-p');
  assert.equal(c.model, 'claude-sonnet-4-6'); assert.equal(c.modelTier, 'frontier');
  assert.equal(c.assetsUsd, 12.5); assert.equal(c.revenueMoUsd, 9); assert.equal(c.burnDayUsd, 0.2);
  assert.equal(c.netUsd, +(9 - 0.2 * 30).toFixed(6)); // monthly basis (M1)
  assert.equal(c.selfFundedEconomic, true);
  assert.ok(c.walletUrl.includes('basescan.org/address/0x810f'));
  assert.ok(Array.isArray(c.logs));
});
test('toCardModel: null funding/env/brain → unknown (REQ-14)', () => {
  const c = toCardModel(row({ funding: null, env: undefined, brain: null }), NOW);
  assert.equal(c.funding, 'unknown'); assert.equal(c.env, 'unknown'); assert.equal(c.brain, 'unknown');
});
test('toCardModel: logs newest-first, capped at 20, kinds normalized', () => {
  const log = Array.from({ length: 25 }, (_, i) => ({ ts: i, kind: i === 0 ? 'weird' : 'earn', note: `n${i}` }));
  const c = toCardModel(row({ log }), NOW);
  assert.equal(c.logs.length, 20);
  assert.equal(c.logs[0].ts, 24);        // newest first
  assert.equal(c.logs[0].note, 'n24');
  assert.equal(c.logs.at(-1).kind, 'earn');
});
test('toCardModel: missing log → empty array', () => assert.deepEqual(toCardModel(row({ log: undefined }), NOW).logs, []));
test('toCardModel: null/undefined row → safe defaults, no throw (FIND-006/010)', () => {
  for (const bad of [null, undefined, 42, 'x']) {
    const c = toCardModel(bad, NOW);
    assert.equal(c.funding, 'unknown'); assert.equal(c.env, 'unknown'); assert.equal(c.brain, 'unknown');
    assert.deepEqual(c.logs, []); assert.equal(c.assetsUsd, 0); assert.equal(c.statusDisplay, 'stale');
  }
});
