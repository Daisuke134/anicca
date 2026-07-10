/**
 * harness-health-snapshot.test.mjs — RED (Phase 2a, feature anicca-harness-tooluse-health).
 * R7 (behavioral-spec.md + verification-architecture.md proof table).
 *
 * runtime/loop/harness-health-snapshot.mjs does not exist yet -> spawn fails -> RED.
 *
 * Testability note: computeHarnessHealth's `generatedAt` field is a wall-clock ISO timestamp, which
 * cannot be literally reproduced by two independent invocations. The snapshot script accepts an
 * optional HARNESS_HEALTH_NOW env override (same test-injection idiom this codebase already uses for
 * ANICCA_BALANCE_OVERRIDE / CLAUDE_BIN) so this test can pin BOTH the direct computeHarnessHealth call
 * and the spawned script to the identical instant, making the deep-equal assertion the proof table
 * requires meaningful rather than trivially flaky.
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { computeHarnessHealth } from '../harness-health.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SNAPSHOT_ENTRY = path.resolve(__dirname, '../harness-health-snapshot.mjs');

function makeTmpHome() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'anicca-harness-snapshot-test-'));
}

function runSnapshot(env) {
  return spawnSync(process.execPath, [SNAPSHOT_ENTRY], {
    env: { ...process.env, ...env },
    encoding: 'utf8',
  });
}

test('R7: fixture ledger.jsonl -> harness-health.json deep-equal to computeHarnessHealth on the same parsed fixture', () => {
  const home = makeTmpHome();
  const statePath = path.join(home, 'state');
  fs.mkdirSync(statePath, { recursive: true });
  const ledgerPath = path.join(statePath, 'ledger.jsonl');
  const records = [
    { ts: 1, wake_id: 'a', kind: 'wake', slot: 'yield' },
    { ts: 2, wake_id: 'b', kind: 'skill_error', slot: 'yield' },
    { ts: 3, wake_id: 'c', kind: 'wake_error' },
  ];
  fs.writeFileSync(ledgerPath, records.map((r) => JSON.stringify(r)).join('\n') + '\n');

  const fixedNow = 1700000000000;
  const result = runSnapshot({ ANICCA_HOME: home, HARNESS_HEALTH_NOW: String(fixedNow) });
  assert.equal(result.status, 0, `snapshot script must exit 0; stderr: ${result.stderr}`);

  const snapshotPath = path.join(statePath, 'harness-health.json');
  assert.ok(fs.existsSync(snapshotPath), 'harness-health.json must be written');
  const written = JSON.parse(fs.readFileSync(snapshotPath, 'utf8'));

  const direct = computeHarnessHealth(records, { now: fixedNow });
  assert.deepEqual(written, direct);

  fs.rmSync(home, { recursive: true, force: true });
});

test('R7: missing ledger.jsonl -> writes the R4 empty shape, exit code 0, no throw', () => {
  const home = makeTmpHome();
  const fixedNow = 1700000000000;
  const result = runSnapshot({ ANICCA_HOME: home, HARNESS_HEALTH_NOW: String(fixedNow) });
  assert.equal(result.status, 0, `snapshot script must exit 0 on missing ledger; stderr: ${result.stderr}`);

  const snapshotPath = path.join(home, 'state', 'harness-health.json');
  const written = JSON.parse(fs.readFileSync(snapshotPath, 'utf8'));
  const expectedEmpty = computeHarnessHealth([], { now: fixedNow });
  assert.deepEqual(written, expectedEmpty);

  fs.rmSync(home, { recursive: true, force: true });
});

test('R7: re-running overwrites -- output reflects only the latest run, no unbounded growth', () => {
  const home = makeTmpHome();
  const statePath = path.join(home, 'state');
  fs.mkdirSync(statePath, { recursive: true });
  const ledgerPath = path.join(statePath, 'ledger.jsonl');
  const snapshotPath = path.join(statePath, 'harness-health.json');

  fs.writeFileSync(ledgerPath, JSON.stringify({ ts: 1, wake_id: 'a', kind: 'wake', slot: 'yield' }) + '\n');
  let result = runSnapshot({ ANICCA_HOME: home, HARNESS_HEALTH_NOW: '1700000000000' });
  assert.equal(result.status, 0);
  const firstRun = JSON.parse(fs.readFileSync(snapshotPath, 'utf8'));
  assert.deepEqual(Object.keys(firstRun.perSlot), ['yield']);

  fs.writeFileSync(ledgerPath,
    [{ ts: 1, wake_id: 'a', kind: 'wake', slot: 'yield' }, { ts: 2, wake_id: 'b', kind: 'wake', slot: 'x402_sell' }]
      .map((r) => JSON.stringify(r)).join('\n') + '\n');
  result = runSnapshot({ ANICCA_HOME: home, HARNESS_HEALTH_NOW: '1700000001000' });
  assert.equal(result.status, 0);
  const secondRun = JSON.parse(fs.readFileSync(snapshotPath, 'utf8'));
  assert.deepEqual(Object.keys(secondRun.perSlot).sort(), ['x402_sell', 'yield']);

  fs.rmSync(home, { recursive: true, force: true });
});
