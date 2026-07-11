// franklin-alwaysact-skill-router — Phase 2a (RED phase), REQ-504 wiring-seam (PROP-504b).
//
// This is the "money-doctrine-critical" test spec-review FIND-001/FIND-005 exists to force: a green
// PROP-504a (the standalone pure helper, always-act-router.test.mjs) is NECESSARY but NOT SUFFICIENT —
// this file proves the REAL outbound wire (the literal `tools` field of the HTTP request body
// runtime/loop/brain.mjs::thinkProxy actually sends) is conditionally governed by `ctx.alwaysActEngaged`.
//
// Ground truth on the CURRENT (pre-Phase-2b) HEAD, re-verified this session (matches
// behavioral-spec.md sec1 + the iteration-5 adversary's own independent spot-check):
//   brain.mjs:63  tools: getToolDefinitions(ctx.activeSkillSlots)                         <- unconditional
//   brain.mjs:92  'Respond with a JSON tool_calls block using run_skill or sleep.'         <- unconditional
// Every test below therefore FAILS against current brain.mjs: `tools` always includes `sleep`
// regardless of `ctx.alwaysActEngaged`, and the claude-p prompt text always mentions "or sleep".
//
// Test-Money-Safety-Rule-compliant network mocking: `think()` (the ALREADY-exported function; no new
// export needed since default config.ANICCA_BRAIN==='proxy' routes into thinkProxy internally) is
// called directly against a local mock HTTP server standing in for OPENAI_BASE_URL — this is
// verification-architecture.md's permitted "PROP-504b exception": import and execute the REAL
// thinkProxy code path, mock ONLY the module-level network call, never issue a real HTTP request to a
// paid provider.

import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { think } from '../brain.mjs';
import { startMockBrainServer, makeNarrateResponse } from './helpers/always-act-harness.mjs';

function baseCtx(overrides = {}) {
  return {
    walletAddress: 'FakeWallet111',
    balanceUsdc: 42,
    positionsSummary: '',
    tier: 'lean',
    model: 'auto',
    wakeId: 'w-wire-seam-test',
    recentLedgerLines: [],
    activeSkillSlots: ['economy/gig', 'earn/clip', 'earn/sol-trade'],
    skillCatalog: {},
    genesisPrompt: '',
    avoidSlot: null,
    recentSlots: [],
    earnSteer: '',
    reserveUsdc: 5,
    ...overrides,
  };
}

const openServers = [];
after(async () => { for (const s of openServers) { try { s.close(); } catch { /* already closed */ } } });

// ===========================================================================
// PROP-504b — always-act-engaged: the REAL outbound `tools` array omits sleep
// ===========================================================================

test('PROP-504b (money-doctrine-critical): thinkProxy\'s REAL outbound request body has NO tool named "sleep" when ctx.alwaysActEngaged===true and ctx.alwaysActMenu is set', async () => {
  const { server, url, requests } = await startMockBrainServer(() => makeNarrateResponse());
  openServers.push(server);

  const ctx = baseCtx({
    alwaysActEngaged: true,
    alwaysActMenu: ['economy/gig', 'earn/clip'],
  });
  const config = { OPENAI_BASE_URL: url, ANICCA_BRAIN: 'proxy' };

  await think(ctx, config);

  assert.equal(requests.length, 1, 'exactly one outbound request must have been captured');
  const body = requests[0];
  assert.ok(body, 'request body must have parsed as JSON');
  assert.ok(Array.isArray(body.tools), 'request body must carry a tools array');
  const hasSleep = body.tools.some((t) => t.function?.name === 'sleep');
  assert.equal(hasSleep, false, 'the REAL outbound tools array must NOT include sleep when always-act is engaged');
  const runSkillTool = body.tools.find((t) => t.function?.name === 'run_skill');
  assert.ok(runSkillTool, 'run_skill must still be offered');
  assert.deepEqual(
    runSkillTool.function.parameters.properties.slot.enum,
    ['economy/gig', 'earn/clip'],
    'the enum offered on the wire must equal ctx.alwaysActMenu, not ctx.activeSkillSlots',
  );

  server.close();
});

// ===========================================================================
// PROP-504b — non-always-act: today's behavior preserved byte-for-byte
// ===========================================================================

test('PROP-504b (non-regression): thinkProxy\'s outbound tools array STILL includes sleep when ctx.alwaysActEngaged is falsy/absent — proving the conditional wiring, not a hardcoded omission', async () => {
  const { server, url, requests } = await startMockBrainServer(() => makeNarrateResponse());
  openServers.push(server);

  const ctx = baseCtx(); // no alwaysActEngaged field at all — the overwhelming majority of all wakes
  const config = { OPENAI_BASE_URL: url, ANICCA_BRAIN: 'proxy' };

  await think(ctx, config);

  assert.equal(requests.length, 1);
  const body = requests[0];
  const hasSleep = body.tools.some((t) => t.function?.name === 'sleep');
  assert.equal(hasSleep, true, 'today\'s existing behavior (sleep always offered) must be preserved for non-always-act ctx');
  const runSkillTool = body.tools.find((t) => t.function?.name === 'run_skill');
  assert.deepEqual(
    runSkillTool.function.parameters.properties.slot.enum,
    ctx.activeSkillSlots,
    'a non-always-act ctx must still offer ctx.activeSkillSlots, unchanged',
  );

  server.close();
});

test('PROP-504b (non-regression): ctx.alwaysActEngaged === false (explicit) behaves identically to absent', async () => {
  const { server, url, requests } = await startMockBrainServer(() => makeNarrateResponse());
  openServers.push(server);

  const ctx = baseCtx({ alwaysActEngaged: false, alwaysActMenu: ['economy/gig'] });
  const config = { OPENAI_BASE_URL: url, ANICCA_BRAIN: 'proxy' };
  await think(ctx, config);

  const body = requests[0];
  const hasSleep = body.tools.some((t) => t.function?.name === 'sleep');
  assert.equal(hasSleep, true);
  const runSkillTool = body.tools.find((t) => t.function?.name === 'run_skill');
  assert.deepEqual(
    runSkillTool.function.parameters.properties.slot.enum,
    ctx.activeSkillSlots,
    'alwaysActEngaged===false must use ctx.activeSkillSlots, never ctx.alwaysActMenu',
  );

  server.close();
});
