// REQ-003, REQ-004 AC#2, PROP-013 — DEPLOYED Franklin plist checks (franklin-loop-revival).
//
// These read the REAL, deployed `~/Library/LaunchAgents/ai.anicca.franklin-loop.plist` directly
// (Tier 0 per verification-architecture.md — "not a unit-test fixture standing in for it"), NOT a
// copy/fixture. Read-only: this test file never writes to the plist and never touches any key
// material (the plist carries no secrets — Franklin's Solana key lives only in
// `~/.blockrun/.solana-session`, untouched here).
//
// RED PHASE:
//  - "model no longer pinned to the rate-limited model" MUST currently FAIL — verified live
//    2026-07-08 that ANICCA_FREE_MODEL/ANICCA_LEAN_MODEL/ANICCA_FUNDED_MODEL are ALL currently
//    'nvidia/llama-4-maverick' (behavioral-spec.md Root cause B) — this is the exact new-feature
//    assertion REQ-004 requires Phase 2b to fix.
//  - "no ANICCA_BALANCE_OVERRIDE key" is a GUARDRAIL that is already true today (verified live) and
//    MUST STAY true — included per REQ-003's explicit acceptance criterion so Phase 2b/2c cannot
//    silently introduce this backdoor. This one assertion is expected to already PASS.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';

const PLIST_PATH = path.join(os.homedir(), 'Library', 'LaunchAgents', 'ai.anicca.franklin-loop.plist');
const RATE_LIMITED_MODEL = 'nvidia/llama-4-maverick'; // behavioral-spec.md Root cause B

function readDeployedEnvironmentVariables() {
  const json = execFileSync('plutil', ['-convert', 'json', '-o', '-', PLIST_PATH], { encoding: 'utf8' });
  const plist = JSON.parse(json);
  return plist.EnvironmentVariables || {};
}

test('REQ-004 AC#2 (new): deployed plist\'s ANICCA_FREE_MODEL/ANICCA_LEAN_MODEL/ANICCA_FUNDED_MODEL no longer pin THINK to the rate-limited free model', () => {
  const env = readDeployedEnvironmentVariables();
  for (const key of ['ANICCA_FREE_MODEL', 'ANICCA_LEAN_MODEL', 'ANICCA_FUNDED_MODEL']) {
    assert.notEqual(
      env[key],
      RATE_LIMITED_MODEL,
      `${key} must no longer be pinned to the exhausted '${RATE_LIMITED_MODEL}' (behavioral-spec.md Root cause B)`,
    );
  }
});

test('REQ-003 guardrail (already-passing): deployed plist MUST NOT contain an ANICCA_BALANCE_OVERRIDE key (the fabricated-balance backdoor REQ-003 forbids)', () => {
  const env = readDeployedEnvironmentVariables();
  assert.ok(
    !Object.prototype.hasOwnProperty.call(env, 'ANICCA_BALANCE_OVERRIDE'),
    'ANICCA_BALANCE_OVERRIDE must never appear in the deployed plist\'s <EnvironmentVariables> dict',
  );
});
