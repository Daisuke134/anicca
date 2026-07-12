/**
 * think-claude-p-timeout.test.mjs — Phase 2a (RED) tests for config-delivery-verification REQ-009.
 *
 * Today (verified live, behavioral-spec.md Context): `thinkClaudeP`'s `spawn()` call has NO timeout at
 * all — only `proc.on('exit', ...)` — so a hung `claude -p` child hangs the wake FOREVER (never
 * resolves, never rejects). This file imports two names that do not exist on `../brain.mjs` yet:
 *   - `resolveClaudePTimeoutMs(overrideVal, resolvedSleepBaseS) -> number` (pure core, REQ-009)
 *   - `thinkClaudeP(ctx, config) -> Promise` (exported directly, bypassing `think()`'s catch-and-
 *     fall-through-to-proxy, so the timeout/reject behavior itself is observable in a test — `think()`
 *     itself is intentionally left unchanged per behavioral-spec.md's "existing catch...fall through to
 *     proxy...unchanged" note)
 * The whole file is expected to fail to load until Phase 2b adds these exports — that is the intended
 * RED signal.
 *
 * Every fixture process below is driven through `config.CLAUDE_BIN`, an override point that ALREADY
 * exists in brain.mjs today (`config.CLAUDE_BIN || process.env.CLAUDE_BIN || 'claude'`) — no production
 * code change is needed to make these fixtures reachable. No real `claude` binary is ever invoked.
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { thinkClaudeP, resolveClaudePTimeoutMs } from '../brain.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FAST_FIXTURE = path.join(__dirname, 'fixtures', 'claude-fake-fast.sh');
const HANG_IGNORE_TERM_FIXTURE = path.join(__dirname, 'fixtures', 'claude-fake-hang-ignore-term.sh');

const baseCtx = () => ({
  wakeId: 'W1', walletAddress: '0xabc', balanceUsdc: 1.23, tier: 'lean',
  model: 'nvidia/llama-4-maverick', positionsSummary: '', recentSlots: [],
  recentLedgerLines: [], activeSkillSlots: [], skillCatalog: {},
});

// ── PROP-017 — resolveClaudePTimeoutMs: default / override validation / clamp (pure, table-driven) ────

test('PROP-017: default (no override) resolves to resolvedSleepBaseS (120s) converted to ms', () => {
  assert.equal(resolveClaudePTimeoutMs(undefined, 120), 120000);
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

test('PROP-017: invalid overrides (non-numeric, zero, negative, non-integer) all fall back to the default', () => {
  for (const bad of ['abc', '0', '-5', '45.5', '', null, undefined, 'NaN']) {
    assert.equal(resolveClaudePTimeoutMs(bad, 120), 120000, `override ${JSON.stringify(bad)} must fall back to default`);
  }
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
