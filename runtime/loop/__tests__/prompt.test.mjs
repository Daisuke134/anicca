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
import { getToolDefinitions, buildSystemPrompt, liveSlotNames } from '../prompt.mjs';

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
