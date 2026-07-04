// node:test — can_run() precondition gating (D1). Pure: availableRails(opts) → rail names.
// gig is LABOR-based (capital-free), so labor rails are available with just creds;
// Coconala is CONDITIONAL (human-funded brain + creds); capital rails (yield/hl_trade)
// are OTHER slots, never returned here.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { availableRails } from '../lib/can-run.mjs';

test('laborx NOT offered until apply/deliver code exists (no pretended-live rail, D2)', () => {
  const r = availableRails({ creds: new Set(['LABORX_EMAIL', 'LABORX_PASSWORD']), brain: 'proxy', usdc: 0 });
  assert.ok(!r.includes('laborx'));
});

test('dealwork available with API key, even at USDC 0 (chicken-egg: labor funds capital)', () => {
  const r = availableRails({ creds: new Set(['DEALWORK_API_KEY']), brain: 'proxy', usdc: 0 });
  assert.ok(r.includes('dealwork'));
});

test('coconala is NEVER offered (human KYC/bank = human loop = disqualified)', () => {
  // even with creds + human-funded brain, a human-loop rail must never appear
  const creds = new Set(['COCONALA_EMAIL', 'COCONALA_PASSWORD', 'LABORX_EMAIL', 'LABORX_PASSWORD']);
  assert.ok(!availableRails({ creds, brain: 'claude-p', usdc: 0 }).includes('coconala'));
  assert.ok(!availableRails({ creds, brain: 'proxy', usdc: 0 }).includes('coconala'));
});

test('no creds → no rails (do not pretend a dead/unconfigured rail works)', () => {
  assert.deepEqual(availableRails({ creds: new Set(), brain: 'claude-p', usdc: 100 }), []);
});

test('never returns capital-only slots (yield/hl_trade are separate slots)', () => {
  const r = availableRails({ creds: new Set(['LABORX_EMAIL', 'LABORX_PASSWORD', 'DEALWORK_API_KEY']), brain: 'proxy', usdc: 9999 });
  assert.ok(!r.includes('yield') && !r.includes('hl_trade'));
});
