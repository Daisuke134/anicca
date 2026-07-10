// REQ-003, REQ-004 AC#2, PROP-013 — DEPLOYED Franklin plist checks (franklin-loop-revival).
// Also franklin-alwaysact-skill-router REQ-509 (Phase 3 impl-review iteration-2 FIND-001 fix) — see
// the ALWAYS_ACT_REGISTRY_PATH_OVERRIDE guardrail block below.
//
// These read the REAL, deployed `~/Library/LaunchAgents/ai.anicca.franklin-loop.plist` /
// `ai.anicca.franklin2-loop.plist` directly (Tier 0 per verification-architecture.md — "not a
// unit-test fixture standing in for it"), NOT a copy/fixture. Read-only: this test file never writes
// to either plist and never touches any key material (neither plist carries secrets — Franklin's
// Solana key lives only in `~/.blockrun/.solana-session` / `~/.franklin2-home/.blockrun/.solana-session`,
// untouched here).
//
// RED PHASE:
//  - "model no longer pinned to the rate-limited model" MUST currently FAIL — verified live
//    2026-07-08 that ANICCA_FREE_MODEL/ANICCA_LEAN_MODEL/ANICCA_FUNDED_MODEL are ALL currently
//    'nvidia/llama-4-maverick' (behavioral-spec.md Root cause B) — this is the exact new-feature
//    assertion REQ-004 requires Phase 2b to fix.
//  - "no ANICCA_BALANCE_OVERRIDE key" is a GUARDRAIL that is already true today (verified live) and
//    MUST STAY true — included per REQ-003's explicit acceptance criterion so Phase 2b/2c cannot
//    silently introduce this backdoor. This one assertion is expected to already PASS.
//  - "no ALWAYS_ACT_REGISTRY_PATH_OVERRIDE key" (both plists) is the SAME class of guardrail, added
//    for franklin-alwaysact-skill-router's own test-only registry-path override (index.mjs — the same
//    idiom as ANICCA_BALANCE_OVERRIDE/CLAUDE_BIN, unconditionally honored in production code with NO
//    code-side gate — exactly like ANICCA_BALANCE_OVERRIDE itself, whose ONLY mitigation is this same
//    deployed-plist-absence check). ALWAYS_ACT_REGISTRY_PATH_OVERRIDE governs riskTagBySlot, the
//    source of truth for REQ-506's money-safety-critical reroute filter — verified live 2026-07-11
//    that neither deployed plist currently carries this key. MUST STAY true.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';

const PLIST_PATH = path.join(os.homedir(), 'Library', 'LaunchAgents', 'ai.anicca.franklin-loop.plist');
const FRANKLIN2_PLIST_PATH = path.join(os.homedir(), 'Library', 'LaunchAgents', 'ai.anicca.franklin2-loop.plist');
const RATE_LIMITED_MODEL = 'nvidia/llama-4-maverick'; // behavioral-spec.md Root cause B

function readDeployedEnvironmentVariables(plistPath = PLIST_PATH) {
  const json = execFileSync('plutil', ['-convert', 'json', '-o', '-', plistPath], { encoding: 'utf8' });
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

test('franklin-alwaysact-skill-router REQ-509 guardrail (Phase 3 impl-review iteration-2 FIND-001 fix): deployed ai.anicca.franklin-loop.plist MUST NOT contain an ALWAYS_ACT_REGISTRY_PATH_OVERRIDE key (the arbitrary-risk-tag backdoor this override would otherwise let an attacker-controlled registry.json defeat REQ-506\'s reroute filter through)', () => {
  const env = readDeployedEnvironmentVariables(PLIST_PATH);
  assert.ok(
    !Object.prototype.hasOwnProperty.call(env, 'ALWAYS_ACT_REGISTRY_PATH_OVERRIDE'),
    'ALWAYS_ACT_REGISTRY_PATH_OVERRIDE must never appear in ai.anicca.franklin-loop.plist\'s <EnvironmentVariables> dict',
  );
});

test('franklin-alwaysact-skill-router REQ-509 guardrail (Phase 3 impl-review iteration-2 FIND-001 fix): deployed ai.anicca.franklin2-loop.plist MUST NOT contain an ALWAYS_ACT_REGISTRY_PATH_OVERRIDE key (the second live Franklin instance is covered by the SAME guardrail, never assumed safe by omission)', () => {
  const env = readDeployedEnvironmentVariables(FRANKLIN2_PLIST_PATH);
  assert.ok(
    !Object.prototype.hasOwnProperty.call(env, 'ALWAYS_ACT_REGISTRY_PATH_OVERRIDE'),
    'ALWAYS_ACT_REGISTRY_PATH_OVERRIDE must never appear in ai.anicca.franklin2-loop.plist\'s <EnvironmentVariables> dict',
  );
});
