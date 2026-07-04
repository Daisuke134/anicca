import { test } from 'node:test';
import assert from 'node:assert/strict';
import { selfEval } from '../self-eval.mjs';

test('flags a repeated ~$0 action as DEAD and names it in the steer', () => {
  const lines = Array.from({ length: 12 }, () => ({ source: 'hl-trade', task: 'hl-close ETH', net_usdc: 0 }));
  const { bySlot, steer } = selfEval(lines, { deadCount: 4 });
  assert.equal(bySlot['hl-trade'].dead, true);
  assert.match(steer, /hl-trade.*DEAD/);
  assert.match(steer, /do NOT pick them again/);
});

test('does NOT flag a profitable action; marks it WORKS', () => {
  const lines = [
    { source: 'yield', task: 'deposit', net_usdc: 0.12 },
    { source: 'yield', task: 'deposit', net_usdc: 0.03 },
  ];
  const { bySlot, steer } = selfEval(lines);
  assert.equal(bySlot['yield'].dead, false);
  assert.ok(bySlot['yield'].net > 0);
  assert.match(steer, /yield.*WORKS/);
});

test('empty ledger → empty steer, no crash', () => {
  const { bySlot, steer } = selfEval([]);
  assert.deepEqual(bySlot, {});
  assert.equal(steer, '');
});

test('a few uses below deadCount is not DEAD even at $0', () => {
  const lines = [ { source: 'x402-serve', net_usdc: 0 }, { source: 'x402-serve', net_usdc: 0 } ];
  const { bySlot } = selfEval(lines, { deadCount: 4 });
  assert.equal(bySlot['x402-serve'].dead, false);
});

test('tolerates malformed rows and alt field names (slot/net)', () => {
  const lines = [ null, 'garbage', { slot: 'gig', net: 0.3 }, { source: 'gig', net_usdc: -0.1 } ];
  const { bySlot } = selfEval(lines);
  assert.equal(bySlot['gig'].count, 2);
  assert.equal(bySlot['gig'].net, 0.2);
});
