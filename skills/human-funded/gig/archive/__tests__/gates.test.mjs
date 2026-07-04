// node:test — 5-gate status + anti-shortcut invariant (D5).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { gateStatus, earnFromSettle } from '../lib/gates.mjs';

test('gates reflect progress; V2 is N/A for gig', () => {
  const g = gateStatus({ bids: 3, deliverables: 1, acceptedContracts: 1, externalEarnUsdc: 0 });
  assert.equal(g.V1_proposal, true);
  assert.equal(g.V2_listing, null);
  assert.equal(g.V3_deliverable, true);
  assert.equal(g.V4_inbound, true);
  assert.equal(g.V5_settle, false);   // no on-chain settle yet
});

test('ANTI-SHORTCUT: passing V1..V4 still earns $0 (only on-chain settle counts)', () => {
  const passedButNotSettled = { bids: 99, deliverables: 99, acceptedContracts: 99, externalEarnUsdc: 0 };
  assert.equal(earnFromSettle(passedButNotSettled), 0);
  assert.equal(gateStatus(passedButNotSettled).V5_settle, false);
});

test('earn is ONLY the external on-chain inflow (record-earn), never fabricated', () => {
  assert.equal(earnFromSettle({ externalEarnUsdc: 50 }), 50);
  assert.equal(earnFromSettle({ externalEarnUsdc: 0 }), 0);
  assert.equal(earnFromSettle({}), 0);
});
