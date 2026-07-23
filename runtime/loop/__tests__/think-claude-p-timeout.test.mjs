/**
 * think-claude-p-timeout.test.mjs — regression tests for config-delivery-verification REQ-009.
 *
 * Regression coverage for bounded `claude -p` execution. A model subprocess must never inherit a
 * multi-hour wake cadence as its request deadline or leave helper processes behind. This file covers:
 *   - `resolveClaudePTimeoutMs(overrideVal, resolvedSleepBaseS) -> number` (pure core, REQ-009)
 *   - `thinkClaudeP(ctx, config) -> Promise` (exported directly so timeout/reject behavior is observable)
 *   - process-group cleanup and truthful effective-model resolution
 * Every fixture process below is driven through `config.CLAUDE_BIN`, an override point that ALREADY
 * exists in brain.mjs today (`config.CLAUDE_BIN || process.env.CLAUDE_BIN || 'claude'`) — no production
 * code change is needed to make these fixtures reachable. No real `claude` binary is ever invoked.
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  thinkClaudeP,
  resolveBrainModel,
  resolveClaudePTimeoutMs,
  runClaudePWithTimeout,
} from '../brain.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FAST_FIXTURE = path.join(__dirname, 'fixtures', 'claude-fake-fast.sh');
const HANG_IGNORE_TERM_FIXTURE = path.join(__dirname, 'fixtures', 'claude-fake-hang-ignore-term.sh');
const ARGV_CAPTURE_FIXTURE = path.join(__dirname, 'fixtures', 'claude-fake-argv-capture.sh');
const SIGTERM_HONORING_FIXTURE = path.join(__dirname, 'fixtures', 'claude-fake-sigterm-then-exit.sh');
const PROCESS_TREE_FIXTURE = path.join(__dirname, 'fixtures', 'claude-fake-process-tree.mjs');

const baseCtx = () => ({
  wakeId: 'W1', walletAddress: '0xabc', balanceUsdc: 1.23, tier: 'lean',
  model: 'nvidia/llama-4-maverick', positionsSummary: '', recentSlots: [],
  recentLedgerLines: [], activeSkillSlots: [], skillCatalog: {},
});

// ── PROP-017 — resolveClaudePTimeoutMs: default / override validation / clamp (pure, table-driven) ────

test('PROP-017: default (no override) resolves to resolvedSleepBaseS (120s) converted to ms', () => {
  assert.equal(resolveClaudePTimeoutMs(undefined, 120), 120000);
});

test('live regression: a 12-hour wake cadence still bounds one Claude call to 180 seconds', () => {
  assert.equal(resolveClaudePTimeoutMs(undefined, 43200), 180000);
});

test('PROP-017: a valid override smaller than SLEEP_BASE_S is used as-is (converted to ms)', () => {
  assert.equal(resolveClaudePTimeoutMs('60', 120), 60000);
});

test('PROP-017: an override LARGER than the resolved SLEEP_BASE_S is clamped to SLEEP_BASE_S itself (not a hardcoded 21600)', () => {
  assert.equal(resolveClaudePTimeoutMs('999', 120), 120000);
  // Explicit non-hardcoded-ceiling proof: change SLEEP_BASE_S and the SAME override now clamps to a
  // DIFFERENT ceiling — this fails if 21600 (mainloop-timeout-lib.sh's own unrelated constant) or any
  // other fixed number were ever hardcoded as the clamp ceiling instead of the passed-in resolvedSleepBaseS.
  assert.equal(resolveClaudePTimeoutMs('999', 30), 30000);
});

test('live regression: even an oversized override cannot disable the five-minute hard safety ceiling', () => {
  assert.equal(resolveClaudePTimeoutMs('999', 43200), 300000);
});

test('PROP-017: invalid overrides (non-numeric, zero, negative, non-integer) all fall back to the default', () => {
  for (const bad of ['abc', '0', '-5', '45.5', '', null, undefined, 'NaN']) {
    assert.equal(resolveClaudePTimeoutMs(bad, 120), 120000, `override ${JSON.stringify(bad)} must fall back to default`);
  }
});

test('Claude-p context and ledger use the model actually passed to the Claude CLI', () => {
  assert.equal(
    resolveBrainModel({ ANICCA_BRAIN: 'claude-p', ANICCA_BRAIN_MODEL: 'claude-sonnet-5' }, 'free/glm-4.7'),
    'claude-sonnet-5',
  );
  assert.equal(resolveBrainModel({ ANICCA_BRAIN: 'proxy' }, 'free/glm-4.7'), 'free/glm-4.7');
});

// ── PROP-015 — thinkClaudeP resolves normally for a fixture process that exits well within the timeout ─

test('PROP-015: thinkClaudeP resolves normally when the child exits fast, well inside the timeout', async () => {
  const result = await thinkClaudeP(baseCtx(), { CLAUDE_BIN: FAST_FIXTURE, SLEEP_BASE_S: 30 });
  assert.equal(result.choices[0].message.content, 'ok');
});

// ── PROP-016 — thinkClaudeP two-stage kill: SIGTERM first (ignored by fixture), then SIGKILL after the
//    2000ms grace period, rejecting with a claude_p_timeout-shaped error. This is the exact bug fix:
//    today's thinkClaudeP would hang on this fixture FOREVER (no timeout at all). ──────────────────────

test('PROP-016: thinkClaudeP times out, two-stage-kills a SIGTERM-ignoring hung child, and rejects with claude_p_timeout (does not hang forever)', async (t) => {
  const timeoutSeconds = 1; // short so the test itself stays fast
  const startedAt = Date.now();
  await assert.rejects(
    () => thinkClaudeP(baseCtx(), {
      CLAUDE_BIN: HANG_IGNORE_TERM_FIXTURE,
      SLEEP_BASE_S: timeoutSeconds,
    }),
    (err) => {
      assert.match(String(err.message), /claude_p_timeout/, 'rejection must explicitly say claude_p_timeout');
      return true;
    },
  );
  const elapsedMs = Date.now() - startedAt;
  // Proves the TWO-STAGE sequence actually ran (SIGTERM sent at timeoutMs, then a further ~2000ms grace
  // before SIGKILL) rather than an immediate single-stage kill: since the fixture ignores SIGTERM, the
  // process can ONLY have died via SIGKILL, which (per index.mjs:1037-1041's existing pattern) only
  // fires after timeoutMs + 2000ms have elapsed.
  assert.ok(elapsedMs >= timeoutSeconds * 1000 + 2000, `expected >= ${timeoutSeconds * 1000 + 2000}ms (timeout + 2000ms SIGKILL grace) to elapse, got ${elapsedMs}ms — a single-stage or missing-timeout implementation would either resolve too early or never at all`);
});

// ── FIND-005 (adversary iteration-1, minor, addressed anyway): verification-architecture.md documents a
// standalone `runClaudePWithTimeout` effectful-shell primitive — confirm it is actually exported and
// independently usable, not just inlined inside thinkClaudeP. ─────────────────────────────────────────

test('FIND-005: runClaudePWithTimeout is exported as a standalone function and works independently of thinkClaudeP', async () => {
  const { stdout, code } = await runClaudePWithTimeout(FAST_FIXTURE, ['--anything'], {
    env: { HOME: process.env.HOME, PATH: process.env.PATH },
    cwd: process.env.HOME,
    timeoutMs: 5000,
  });
  assert.equal(code, 0);
  assert.match(stdout, /"content":"ok"/);
});

// ── FIND-002 (adversary iteration-1, dismissed as a "revert" request by the lead — the flag itself is
// correct, pre-existing behavior — but the adversary's underlying observation stands: pin it with a
// test so nobody silently drops it and regresses back into the narrate-hell this flag exists to fix). ──

test('FIND-002 regression guard: thinkClaudeP always spawns claude -p with --dangerously-skip-permissions in argv (without it, tool-permission prompts silently degrade every wake to narrate)', async () => {
  const result = await thinkClaudeP(baseCtx(), { CLAUDE_BIN: ARGV_CAPTURE_FIXTURE, SLEEP_BASE_S: 30 });
  const decoded = Buffer.from(result.choices[0].message.content, 'base64').toString('utf8');
  const argv = decoded.split('\0').filter(Boolean);
  assert.ok(argv.includes('--dangerously-skip-permissions'), `expected --dangerously-skip-permissions in argv, got: ${JSON.stringify(argv)}`);
  assert.ok(argv.includes('-p'), 'sanity check: the argv capture itself must be working');
  assert.ok(argv.includes('--output-format'), 'sanity check: the argv capture itself must be working');
});

// ── FIND-004 (adversary iteration-1, major): the inner SIGKILL grace-period timer was never captured,
// so a child that honors SIGTERM and exits cleanly within the grace period left it dangling. This test
// intercepts the real global setTimeout/clearTimeout calls runClaudePWithTimeout makes (Node resolves
// unqualified `setTimeout`/`clearTimeout` through the global scope, so this reaches the real code path
// without needing any dependency-injection seam) to prove the SPECIFIC 2000ms grace timer is captured
// and then actually cleared once the child exits during the grace period. ──────────────────────────────

test('FIND-004 fix: the 2000ms SIGKILL grace-period timer is captured and cleared when the child honors SIGTERM and exits within the grace period (no dangling timer)', async () => {
  const realSetTimeout = global.setTimeout;
  const realClearTimeout = global.clearTimeout;
  const graceTimerIds = [];
  const clearedIds = new Set();

  global.setTimeout = (fn, ms, ...args) => {
    const id = realSetTimeout(fn, ms, ...args);
    if (ms === 2000) graceTimerIds.push(id); // the SIGKILL grace-period timer specifically
    return id;
  };
  global.clearTimeout = (id) => {
    clearedIds.add(id);
    return realClearTimeout(id);
  };

  try {
    await assert.rejects(
      () => thinkClaudeP(baseCtx(), { CLAUDE_BIN: SIGTERM_HONORING_FIXTURE, SLEEP_BASE_S: 1 }),
      (err) => {
        assert.match(String(err.message), /claude_p_timeout/);
        return true;
      },
    );
  } finally {
    global.setTimeout = realSetTimeout;
    global.clearTimeout = realClearTimeout;
  }

  assert.equal(graceTimerIds.length, 1, 'exactly one 2000ms grace-period timer must be created on this timeout path');
  assert.ok(clearedIds.has(graceTimerIds[0]), 'the grace-period timer must be cleared once the child exits during the grace period — a dangling (never-cleared) timer is exactly FIND-004');
});

test('live regression: timeout terminates the whole Claude process group, not only its direct child', async (t) => {
  const tmpDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'claude-p-tree-'));
  const childPidPath = path.join(tmpDir, 'child.pid');
  let childPid = null;

  t.after(async () => {
    if (childPid) {
      try { process.kill(childPid, 'SIGKILL'); } catch {}
    }
    await fs.promises.rm(tmpDir, { recursive: true, force: true });
  });

  await assert.rejects(
    () => runClaudePWithTimeout(process.execPath, [PROCESS_TREE_FIXTURE], {
      env: { HOME: process.env.HOME, PATH: process.env.PATH, CHILD_PID_PATH: childPidPath },
      cwd: os.tmpdir(),
      timeoutMs: 100,
    }),
    /claude_p_timeout/,
  );

  childPid = Number(await fs.promises.readFile(childPidPath, 'utf8'));
  await new Promise((resolve) => setTimeout(resolve, 100));
  assert.throws(
    () => process.kill(childPid, 0),
    { code: 'ESRCH' },
    `grandchild ${childPid} survived the Claude timeout`,
  );
});
