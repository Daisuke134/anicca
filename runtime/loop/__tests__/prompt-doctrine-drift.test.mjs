/**
 * prompt-doctrine-drift.test.mjs — TOOL-1: the "## Your earn tools" doctrine (and the COLONY
 * BOOTSTRAP block it feeds) must never name a slot that is not in the live `slots` menu.
 *
 * Before this fix, buildSystemPrompt() emitted static doctrine text for economy/gig, hl_trade,
 * and token_launch (including a "your FIRST action this wake MUST be economy/gig" order)
 * regardless of whether those slots were actually live — so the model was told to call a tool
 * that run_skill would reject. See docs/research/2026-07-18-agent-tool-calling-best-practice-and-franklin-gap.md.
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildSystemPrompt } from '../prompt.mjs';

// The doctrine's slot-gated keys (kept here, independent of prompt.mjs's own DOCTRINE_LINES map,
// so this test proves the CONTRACT — not just mirrors the implementation).
const DOCTRINE_SLOTS = ['economy/gig', 'yield', 'x402_sell', 'hl_trade', 'token_launch'];

const baseCtx = (slots) => ({
  walletAddress: '0xabc',
  balanceUsdc: 1.23,
  tier: 'lean',
  model: 'auto',
  wakeId: 'W1',
  recentLedgerLines: [],
  activeSkillSlots: slots,
  skillCatalog: {},
});

test('a) dormant economy/gig, hl_trade, token_launch → doctrine and BOOTSTRAP block absent', () => {
  const ctx = baseCtx(['earn', 'yield', 'x402_sell', 'cook']);
  const p = buildSystemPrompt(ctx, ctx.activeSkillSlots);
  assert.ok(!p.includes('economy/gig'), 'must not mention economy/gig');
  assert.ok(!p.includes('hl_trade'), 'must not mention hl_trade');
  assert.ok(!p.includes('token_launch'), 'must not mention token_launch');
  assert.ok(!p.includes('COLONY BOOTSTRAP'), 'must not emit the BOOTSTRAP block');
});

test('b) live economy/gig → BOOTSTRAP block present', () => {
  const ctx = baseCtx(['earn', 'economy/gig', 'yield']);
  const p = buildSystemPrompt(ctx, ctx.activeSkillSlots);
  assert.ok(p.includes('COLONY BOOTSTRAP'), 'BOOTSTRAP block must be present when economy/gig is live');
  assert.ok(p.includes('economy/gig'), 'doctrine line for economy/gig must be present');
});

test('c) drift invariant: every doctrine slot token appears iff it is in the live menu', () => {
  const cases = [
    ['earn'],
    ['earn', 'yield'],
    ['earn', 'economy/gig'],
    ['earn', 'x402_sell', 'hl_trade'],
    ['earn', 'economy/gig', 'yield', 'x402_sell', 'hl_trade', 'token_launch'],
  ];
  for (const slots of cases) {
    const ctx = baseCtx(slots);
    const p = buildSystemPrompt(ctx, ctx.activeSkillSlots);
    for (const slotName of DOCTRINE_SLOTS) {
      const doctrineHeader = `  - ${slotName}`;
      const isLive = slots.includes(slotName);
      const mentioned = p.includes(doctrineHeader);
      assert.equal(
        mentioned,
        isLive,
        `slot "${slotName}" (live=${isLive}) doctrine-line presence mismatch for menu [${slots.join(', ')}]`
      );
    }
  }
});

test('d) x402_sell doctrine no longer hardcodes the stale route count/list', () => {
  const ctx = baseCtx(['earn', 'x402_sell']);
  const p = buildSystemPrompt(ctx, ctx.activeSkillSlots);
  assert.ok(!p.includes('7 preset paid routes'), 'must not contain the stale "7 preset paid routes" text');
});
