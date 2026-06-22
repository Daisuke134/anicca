/**
 * prompt.test.mjs — spec 25 O1: the LLM must see EACH live skill as a pickable
 * flat tool (not just an opaque run_skill('earn')).
 *
 * Contract:
 *  - liveSlotNames(registry) → string[] of slots whose status === 'live'
 *  - getToolDefinitions(slots) → run_skill's `slot` param carries enum=slots
 *  - buildSystemPrompt(ctx) lists each active slot (with its summary if given)
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { getToolDefinitions, buildSystemPrompt, liveSlotNames, buildUserMessage } from '../prompt.mjs';

// #7 AUT: low-liquid → the wake message must steer "replenish first" so the agent never strands itself.
const baseCtx = (over) => ({ wakeId: 'W', balanceUsdc: 0.06, tier: 'broke', positionsSummary: 'HL ETH long 2x', reserveUsdc: 5, recentSlots: [], ...over });

test('buildUserMessage: liquid below the instance buffer → REPLENISH-FIRST directive present', () => {
  const m = buildUserMessage(baseCtx());
  assert.match(m, /BELOW COMPUTE BUFFER/);
  assert.match(m, /close/i, 'steers to close the HL position it holds');
});

test('buildUserMessage: healthy liquid (>= buffer) → no low-liquid directive', () => {
  const m = buildUserMessage(baseCtx({ balanceUsdc: 12, tier: 'funded' }));
  assert.doesNotMatch(m, /BELOW COMPUTE BUFFER/);
});

test('buildUserMessage: low liquid + NO position → steer to withdraw yield (not close)', () => {
  const m = buildUserMessage(baseCtx({ positionsSummary: '' }));
  assert.match(m, /withdraw/i);
});


const REGISTRY = {
  slots: {
    report: { status: 'live', summary: 'per-wake report' },
    earn: { status: 'live', summary: 'earn USDC' },
    'self/spawn': { status: 'declared', summary: 'spawn child' },
    'economy/ubi': { status: 'declared', summary: 'ubi' },
  },
};

test('liveSlotNames returns only status==="live" slots', () => {
  assert.deepEqual(liveSlotNames(REGISTRY).sort(), ['earn', 'report']);
});

test('liveSlotNames is safe on empty/garbage input', () => {
  assert.deepEqual(liveSlotNames(null), []);
  assert.deepEqual(liveSlotNames({}), []);
  assert.deepEqual(liveSlotNames({ slots: {} }), []);
});

test('getToolDefinitions(slots) puts the live slots in the run_skill enum', () => {
  const tools = getToolDefinitions(['earn', 'report']);
  const runSkill = tools.find(t => t.function.name === 'run_skill');
  assert.ok(runSkill, 'run_skill tool present');
  assert.deepEqual(runSkill.function.parameters.properties.slot.enum, ['earn', 'report']);
  assert.ok(tools.find(t => t.function.name === 'sleep'), 'sleep tool still present');
});

test('getToolDefinitions() with no slots still works (backward compat, no enum)', () => {
  const tools = getToolDefinitions();
  const runSkill = tools.find(t => t.function.name === 'run_skill');
  assert.ok(runSkill);
  assert.equal(runSkill.function.parameters.properties.slot.enum, undefined);
});

test('buildSystemPrompt lists each active slot with its summary', () => {
  const ctx = {
    walletAddress: '0xabc', balanceUsdc: 1.23, tier: 'lean', model: 'auto',
    wakeId: 'W1', recentLedgerLines: [],
    activeSkillSlots: ['earn', 'report'],
    skillCatalog: { earn: 'earn USDC', report: 'per-wake report' },
  };
  const p = buildSystemPrompt(ctx, ctx.activeSkillSlots);
  assert.ok(p.includes('earn'), 'lists earn');
  assert.ok(p.includes('report'), 'lists report');
  assert.ok(p.includes('earn USDC'), 'includes earn summary');
});
