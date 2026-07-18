/**
 * tool2-catalog-docs.test.mjs — TOOL-2 Phase A: tool-description quality + structured result feedback.
 *
 * Contract:
 *  - every status:"live" slot in skills/registry.json defines a real toolDescription + argsExample
 *    (registry sanity, catches stale/missing docs before they reach the model)
 *  - buildSystemPrompt renders the richer toolDescription/argsExample when ctx.skillToolDocs has one
 *    for a slot, and falls back to the plain summary line otherwise (additive, backward-compatible)
 *  - summarizeSkillResult prefers a trailing JSON stdout line (skills' "stdout emits one JSON line"
 *    contract) over the raw-text slice, unchanged for output with no clean trailing JSON
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildSystemPrompt } from '../prompt.mjs';
import { summarizeSkillResult } from '../result-summary.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REGISTRY_PATH = path.join(__dirname, '..', '..', '..', 'skills', 'registry.json');

// ── 1. registry sanity ───────────────────────────────────────────────────────────────────────────

test('registry sanity: every live slot has a real toolDescription + argsExample', async () => {
  const registry = JSON.parse(await readFile(REGISTRY_PATH, 'utf8'));
  const liveSlots = Object.entries(registry.slots).filter(([, s]) => s && s.status === 'live');
  assert.ok(liveSlots.length > 0, 'sanity: registry has at least one live slot');

  for (const [name, slotDef] of liveSlots) {
    const td = slotDef.toolDescription;
    assert.ok(typeof td === 'string' && td.length >= 120, `${name}: toolDescription missing/too short`);
    assert.ok('argsExample' in slotDef, `${name}: argsExample missing`);
    assert.ok(!/7 preset/i.test(td), `${name}: toolDescription still says "7 preset" (stale x402_sell fact)`);
    assert.ok(!/7 fixed/i.test(td), `${name}: toolDescription still says "7 fixed" (stale x402_sell fact)`);
  }
});

test('registry sanity: x402_sell summary and toolDescription no longer hardcode a route count', async () => {
  const registry = JSON.parse(await readFile(REGISTRY_PATH, 'utf8'));
  const slot = registry.slots.x402_sell;
  assert.ok(slot, 'x402_sell slot exists');
  assert.ok(!/7 preset/i.test(slot.summary) && !/7 fixed/i.test(slot.summary), 'summary rewritten off the stale "7" count');
  assert.match(slot.toolDescription, /preset catalog/i, 'toolDescription describes a preset catalog, not a fixed count');
});

// ── 2. prompt render ─────────────────────────────────────────────────────────────────────────────

test('buildSystemPrompt: renders toolDescription + args example when skillToolDocs has an entry', () => {
  const ctx = {
    walletAddress: '0xabc', balanceUsdc: 1, tier: 'lean', model: 'auto',
    wakeId: 'W1', recentLedgerLines: [],
    activeSkillSlots: ['fake_slot'],
    skillCatalog: { fake_slot: 'plain one-line summary' },
    skillToolDocs: {
      fake_slot: {
        toolDescription: 'FAKE_SLOT does a fake thing, for testing only, pick it when testing, do not pick it otherwise.',
        argsExample: { action: 'take', gigId: 1 },
      },
    },
  };
  const p = buildSystemPrompt(ctx, ctx.activeSkillSlots);
  assert.ok(p.includes('FAKE_SLOT does a fake thing'), 'includes the rich toolDescription');
  assert.ok(p.includes('args example:'), 'includes the args example label');
  assert.ok(p.includes(JSON.stringify({ action: 'take', gigId: 1 })), 'includes the serialized argsExample');
  assert.ok(!p.includes('plain one-line summary'), 'does not also render the plain summary for a documented slot');
});

test('buildSystemPrompt: falls back to plain summary when skillToolDocs has no entry for a slot', () => {
  const ctx = {
    walletAddress: '0xabc', balanceUsdc: 1, tier: 'lean', model: 'auto',
    wakeId: 'W1', recentLedgerLines: [],
    activeSkillSlots: ['fake_slot'],
    skillCatalog: { fake_slot: 'plain one-line summary' },
    // no skillToolDocs at all — byte-identical to pre-TOOL-2 behaviour
  };
  const p = buildSystemPrompt(ctx, ctx.activeSkillSlots);
  assert.ok(p.includes('plain one-line summary'), 'falls back to the summary line');
  assert.ok(!p.includes('args example:'), 'no args-example line when undocumented');
});

test('buildSystemPrompt: skillToolDocs entry without argsExample still renders (no args-example line)', () => {
  const ctx = {
    walletAddress: '0xabc', balanceUsdc: 1, tier: 'lean', model: 'auto',
    wakeId: 'W1', recentLedgerLines: [],
    activeSkillSlots: ['fake_slot'],
    skillCatalog: { fake_slot: 'plain one-line summary' },
    skillToolDocs: { fake_slot: { toolDescription: 'FAKE_SLOT rich description with no example.' } },
  };
  const p = buildSystemPrompt(ctx, ctx.activeSkillSlots);
  assert.ok(p.includes('FAKE_SLOT rich description with no example.'));
});

// ── 3. result-summary (extracted pure helper) ───────────────────────────────────────────────────

test('summarizeSkillResult: stdout ending in a JSON line -> result is the parsed+re-serialized JSON', () => {
  const out = 'some narrate text\nmore log lines\n{"sales":3,"error":null}';
  const result = summarizeSkillResult(out);
  assert.equal(result, JSON.stringify({ sales: 3, error: null }));
});

test('summarizeSkillResult: JSON line surrounded by blank lines/whitespace is still found', () => {
  const out = 'log line one\n\n  {"action":"close","coin":"ETH"}  \n\n';
  const result = summarizeSkillResult(out);
  assert.equal(result, JSON.stringify({ action: 'close', coin: 'ETH' }));
});

test('summarizeSkillResult: no trailing JSON -> raw-slice behaviour unchanged (whitespace-collapsed, 900 cap)', () => {
  const out = 'plain   narrate\n  text   with   whitespace';
  const result = summarizeSkillResult(out);
  assert.equal(result, out.replace(/\s+/g, ' ').slice(0, 900));
});

test('summarizeSkillResult: trailing line is a JSON array or primitive -> not treated as structured, raw-slice used', () => {
  const out = 'log\n[1,2,3]';
  const result = summarizeSkillResult(out);
  // arrays are valid JSON.parse results but not "an object" per the summary contract -- raw slice.
  assert.equal(result, out.replace(/\s+/g, ' ').slice(0, 900));
});

test('summarizeSkillResult: JSON object longer than 600 chars is capped at 600', () => {
  const bigObj = { note: 'x'.repeat(700) };
  const out = `log line\n${JSON.stringify(bigObj)}`;
  const result = summarizeSkillResult(out);
  assert.equal(result.length, 600);
  assert.equal(result, JSON.stringify(bigObj).slice(0, 600));
});

test('summarizeSkillResult: empty input -> empty string', () => {
  assert.equal(summarizeSkillResult(''), '');
  assert.equal(summarizeSkillResult(undefined), '');
});
