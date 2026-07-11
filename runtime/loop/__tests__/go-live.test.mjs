// go-live.mjs — Phase 3 impl-review iteration-1 FIND-002 fix: the effectful shell half of REQ-512's
// go-live operational action. recordGoLive() is unit-tested directly here (real fs, tmp ledger path,
// never a spawned index.mjs process — unlike index.mjs itself, go-live.mjs has no top-level
// side-effecting code outside its `import.meta.url === process.argv[1]` CLI guard, so it is safely
// importable). The pure planning half (buildGoLiveRecord/shouldRecordGoLive) is unit-tested in
// always-act-router.test.mjs::PROP-512a.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { recordGoLive } from '../go-live.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');

function tmpLedgerPath() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'go-live-test-'));
  return path.join(dir, 'ledger.jsonl');
}

function readLines(ledgerPath) {
  if (!fs.existsSync(ledgerPath)) return [];
  return fs.readFileSync(ledgerPath, 'utf8')
    .split('\n')
    .filter((l) => l.trim().length > 0)
    .map((l) => JSON.parse(l));
}

test('REQ-512 AC: the go-live operational action appends kind:\'always_act_go_live\' exactly once at the flip -- first call against a fresh (missing) ledger file writes the line', async () => {
  const ledgerPath = tmpLedgerPath();
  const wrote = await recordGoLive({ ledgerPath, configSource: '.env', now: () => '2026-07-11T00:00:00.000Z' });
  assert.equal(wrote, true);
  const lines = readLines(ledgerPath);
  assert.equal(lines.length, 1);
  assert.equal(lines[0].kind, 'always_act_go_live');
  assert.equal(lines[0].ts, '2026-07-11T00:00:00.000Z');
  assert.equal(lines[0].config_source, '.env');
});

test('REQ-512 AC: a SECOND invocation of the go-live action never duplicates the anchor line -- exactly once, never on any other invocation', async () => {
  const ledgerPath = tmpLedgerPath();
  const first = await recordGoLive({ ledgerPath, configSource: 'env', now: () => 't0' });
  const second = await recordGoLive({ ledgerPath, configSource: 'env', now: () => 't1' });
  assert.equal(first, true);
  assert.equal(second, false, 'a second invocation must be a safe no-op, never a duplicate always_act_go_live line');
  const lines = readLines(ledgerPath);
  assert.equal(lines.length, 1, 'exactly ONE always_act_go_live line must exist, regardless of how many times the operational action runs');
  assert.equal(lines.filter((l) => l.kind === 'always_act_go_live').length, 1);
});

test('REQ-512 AC: recordGoLive never appends when a go-live line already exists in the tail from an EARLIER, unrelated append (real ledger tail read, not an in-memory flag)', async () => {
  const ledgerPath = tmpLedgerPath();
  fs.mkdirSync(path.dirname(ledgerPath), { recursive: true });
  fs.writeFileSync(ledgerPath, JSON.stringify({ ts: 'prior', kind: 'always_act_go_live', config_source: 'manual-earlier-flip' }) + '\n');
  const wrote = await recordGoLive({ ledgerPath, configSource: 'env', now: () => 't1' });
  assert.equal(wrote, false);
  const lines = readLines(ledgerPath);
  assert.equal(lines.length, 1);
  assert.equal(lines[0].config_source, 'manual-earlier-flip', 'the pre-existing anchor line must be preserved verbatim, never overwritten');
});

test('REQ-512 AC ("never on any other wake"): index.mjs -- the wake-loop entry point -- never imports or invokes go-live.mjs/recordGoLive; the go-live line is written ONLY by the operator\'s own separate one-time command, never automatically by any wake', () => {
  const indexSrc = fs.readFileSync(path.join(REPO_ROOT, 'runtime', 'loop', 'index.mjs'), 'utf8');
  assert.ok(!indexSrc.includes('go-live.mjs'), 'index.mjs must never import go-live.mjs');
  assert.ok(!indexSrc.includes('recordGoLive'), 'index.mjs must never call recordGoLive -- REQ-512\'s go-live line is a separate operational action (behavioral-spec.md sec6 item 10), out of the wake loop\'s own control flow');
});
