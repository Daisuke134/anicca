// node:test — earn/gig SLOT CONTRACT (RED first).
// Asserts run.sh satisfies the run-skill.mjs interface:
//  exit 0 · ONE structured JSON line on stdout (source=gig, task, earn_usdc, cost_usdc, wake)
//  · never leaks a private key present in the env · bounded (under timeout) · idempotent.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RUN = path.join(HERE, '..', 'run.sh');
const LEAK = '0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef';

function runSlot(extraEnv = {}) {
  return spawnSync('bash', [RUN], {
    encoding: 'utf8',
    timeout: 60_000, // must finish well under SKILL_TIMEOUT_S
    env: {
      ...process.env,
      WAKE_ID: 'test-wake-1',
      GIG_MODE: 'detect',           // detect = the always-safe bounded unit (no side effects)
      // a planted private key the slot must NEVER echo (REQ-004):
      BLOCKRUN_WALLET_KEY: LEAK,
      SOME_PRIVATE_KEY: LEAK,
      ...extraEnv,
    },
  });
}

function lastJsonLine(stdout) {
  const lines = stdout.trim().split('\n').filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i--) {
    const m = lines[i].match(/\{.*\}/);
    if (m) { try { return JSON.parse(m[0]); } catch {} }
  }
  return null;
}

test('exit 0 on a detect wake', () => {
  const r = runSlot();
  assert.equal(r.status, 0, `run.sh exited ${r.status}: ${r.stderr}`);
});

test('emits ONE structured result line with the required keys', () => {
  const r = runSlot();
  const j = lastJsonLine(r.stdout);
  assert.ok(j, `no JSON result line in stdout:\n${r.stdout}`);
  assert.equal(j.source, 'gig');
  for (const k of ['task', 'earn_usdc', 'cost_usdc', 'wake']) {
    assert.ok(k in j, `missing key ${k} in ${JSON.stringify(j)}`);
  }
  assert.equal(typeof j.earn_usdc, 'number');
  assert.equal(typeof j.cost_usdc, 'number');
});

test('detect wake earns nothing and is NOT a fake earn (no tx/external)', () => {
  const j = lastJsonLine(runSlot().stdout);
  assert.equal(j.earn_usdc, 0);
  assert.ok(!j.external, 'detect must not claim external earn');
  assert.ok(!j.tx, 'detect must not invent a tx');
});

test('never leaks a private key from the env (REQ-004)', () => {
  const r = runSlot();
  assert.ok(!(`${r.stdout}${r.stderr}`).includes(LEAK), 'private key leaked to output');
});

test('idempotent: two detect wakes both exit 0 with valid output', () => {
  for (let i = 0; i < 2; i++) {
    const r = runSlot();
    assert.equal(r.status, 0);
    assert.ok(lastJsonLine(r.stdout), 'no valid result on repeat wake');
  }
});

test('reads the loop decision channel $ANICCA_ARGS (not GIG_MODE) — drives the mode', () => {
  // the live loop passes ANICCA_ARGS (JSON), never GIG_MODE — settle must be reachable from it
  const r = spawnSync('bash', [RUN], {
    encoding: 'utf8', timeout: 60_000,
    env: { ...process.env, WAKE_ID: 'args-wake', GIG_MODE: '', ANICCA_ARGS: '{"mode":"settle"}', BLOCKRUN_WALLET_KEY: LEAK },
  });
  assert.equal(r.status, 0, r.stderr);
  const j = lastJsonLine(r.stdout);
  assert.ok(j && j.task && j.task.startsWith('settle'), `settle not driven via ANICCA_ARGS: ${r.stdout}`);
  // non-tautological (FIND-006): with no real external inflow the settle MUST be 0 and not flagged external —
  // a fabricated earn would fail here. record-earn must actually have been invoked (its line appears).
  assert.equal(j.earn_usdc, 0, 'settle fabricated a non-zero earn without on-chain inflow');
  assert.ok(!j.external, 'settle claimed external with no inflow');
  assert.ok(/record-earn|settle:/.test(r.stdout), 'record-earn oracle was not invoked');
  assert.ok(!(`${r.stdout}${r.stderr}`).includes(LEAK), 'key leaked');
});

test('empty ANICCA_ARGS defaults safely to detect (earns 0)', () => {
  const r = spawnSync('bash', [RUN], {
    encoding: 'utf8', timeout: 60_000,
    env: { ...process.env, WAKE_ID: 'empty-args', GIG_MODE: '', ANICCA_ARGS: '{}' },
  });
  assert.equal(r.status, 0);
  const j = lastJsonLine(r.stdout);
  assert.equal(j.task, 'detect');
  assert.equal(j.earn_usdc, 0);
});
