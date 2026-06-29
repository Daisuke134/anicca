// node:test — settle line must satisfy the loop's isProfitable gate (FIND-001 final).
// A real record-earn-verified inflow → a line with tx+status+external+net>0 that classifies profitable.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { isProfitable } from '../../../_shared/lib/ledger.mjs';

const LIB = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'lib', 'settle-write.mjs');

function runSettleWrite(earn, env = {}) {
  const ledger = path.join(os.tmpdir(), 'gig-ledger-' + Date.now() + Math.random() + '.jsonl');
  const r = spawnSync('node', [LIB, String(earn), '0x810f6d61f7606deee2657d3083e150a222bc29c5', 'WAKE-ULID-1', ledger],
    { encoding: 'utf8', timeout: 30000, env: { ...process.env, ...env } });
  let line = null; try { line = JSON.parse(r.stdout.trim().split('\n').pop()); } catch {}
  const onDisk = fs.existsSync(ledger) ? fs.readFileSync(ledger, 'utf8').trim() : '';
  return { line, onDisk, status: r.status };
}

test('verified inflow with a real tx → line is classified PROFITABLE by the loop gate', () => {
  const tx = '0x' + 'a'.repeat(64);
  const { line } = runSettleWrite(50, { FOUNDER_TEST: '1', GIG_SETTLE_TX: tx });   // seam (test-gated) injects the tx
  assert.equal(line.source, 'gig');
  assert.equal(line.earn_usdc, 50);
  assert.equal(line.tx, tx);
  assert.equal(line.status, '0x1');
  assert.equal(line.external, true);
  assert.equal(line.wake, 'WAKE-ULID-1');
  assert.equal(isProfitable(line), true, 'settle line not accepted by isProfitable: ' + JSON.stringify(line));
});

test('zero earn → no profitable line (never fabricates)', () => {
  const { line } = runSettleWrite(0);
  assert.equal(line.earn_usdc, 0);
  assert.ok(!isProfitable(line));
});

test('FIND-001: GIG_SETTLE_TX is IGNORED without FOUNDER_TEST (no forged receipt in prod)', () => {
  // no FOUNDER_TEST, unreachable RPC → cannot get a real tx → must be no_tx (not profitable)
  const { line } = runSettleWrite(50, { GIG_SETTLE_TX: '0x' + 'b'.repeat(64), BASE_RPC_URL: 'http://127.0.0.1:1' });
  assert.ok(!line.tx, 'prod honored the test-only GIG_SETTLE_TX seam (forgeable receipt!)');
  assert.equal(line.no_tx, true);
  assert.ok(!isProfitable(line), 'no_tx line must NOT classify profitable');
});

test('FIND-004: real path with no reachable tx → honest no_tx under-count (never false-green)', () => {
  const { line } = runSettleWrite(25, { BASE_RPC_URL: 'http://127.0.0.1:1' });
  assert.equal(line.earn_usdc, 25);   // amount preserved (record-earn truth)
  assert.equal(line.no_tx, true);
  assert.ok(!isProfitable(line));
});

