// ubi.test.mjs — pure-function tests for economy/ubi/ubi.js (Task #5, colony spec §5.2/§5.3).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { contribute, distributeAI } from '../ubi.js';

// ── contribute() ──────────────────────────────────────────────────────────

test('contribute: no realized profit -> no-op (the honest today-state)', () => {
  const r = contribute(0, 10);
  assert.equal(r.amount_usd, 0);
  assert.match(r.reason, /no realized profit/);
});

test('contribute: negative realized profit -> no-op', () => {
  const r = contribute(-3.5, 10);
  assert.equal(r.amount_usd, 0);
  assert.match(r.reason, /no realized profit/);
});

test('contribute: profit below threshold -> no-op (matches spec "automaton +$0.2013" today)', () => {
  const r = contribute(0.2013, 10, { contributeThresholdUsd: 1 });
  assert.equal(r.amount_usd, 0);
  assert.match(r.reason, /below threshold/);
});

test('contribute: profit above threshold with healthy liquid -> distributes contributePct', () => {
  const r = contribute(10, 100, { contributePct: 0.1, contributeThresholdUsd: 1, reserveUsd: 5 });
  assert.equal(r.amount_usd, 1);
  assert.match(r.reason, /10% of \$10/);
});

test('contribute: would breach reserve -> no-op even if profit clears threshold', () => {
  const r = contribute(10, 5.5, { contributePct: 0.5, contributeThresholdUsd: 1, reserveUsd: 5 });
  // raw = 5, liquid-after = 0.5, below reserve(5) -> reject
  assert.equal(r.amount_usd, 0);
  assert.match(r.reason, /breach reserve/);
});

test('contribute: unknown liquid balance fails closed', () => {
  const r = contribute(10, NaN);
  assert.equal(r.amount_usd, 0);
  assert.match(r.reason, /fail closed/);
});

test('contribute: non-finite profit fails closed (never guesses)', () => {
  const r = contribute(NaN, 100);
  assert.equal(r.amount_usd, 0);
});

// ── distributeAI() (gojo, REQ-DRAIN) ────────────────────────────────────────

const REGISTRY = ['0xaaa1111111111111111111111111111111111aa', '0xbbb2222222222222222222222222222222222bb'];

test('distributeAI: recipient not in signed registry -> reject', () => {
  const r = distributeAI('0xdead', 100, REGISTRY, []);
  assert.equal(r.amount_usd, 0);
  assert.match(r.reason, /not in the signed colony registry/);
});

test('distributeAI: registered recipient, no recent gift, healthy surplus -> gated amount', () => {
  const r = distributeAI(REGISTRY[0], 100, REGISTRY, [], { giftCeilingUsd: 5, giftPct: 0.25 });
  // min(5, 0.25*100=25) = 5 (ceiling binds)
  assert.equal(r.amount_usd, 5);
});

test('distributeAI: percentage binds when surplus is small (ceiling does not)', () => {
  const r = distributeAI(REGISTRY[0], 8, REGISTRY, [], { giftCeilingUsd: 5, giftPct: 0.25 });
  // min(5, 0.25*8=2) = 2
  assert.equal(r.amount_usd, 2);
});

test('distributeAI: rate-limited if gifted within the last 24h', () => {
  const now = Date.now();
  const recent = [{ to: REGISTRY[0], ts: now - 3600 * 1000 }]; // 1h ago
  const r = distributeAI(REGISTRY[0], 100, REGISTRY, recent, { rateLimitHours: 24 });
  assert.equal(r.amount_usd, 0);
  assert.match(r.reason, /rate-limited/);
});

test('distributeAI: NOT rate-limited once the window has passed', () => {
  const now = Date.now();
  const old = [{ to: REGISTRY[0], ts: now - 25 * 3600 * 1000 }]; // 25h ago
  const r = distributeAI(REGISTRY[0], 100, REGISTRY, old, { rateLimitHours: 24 });
  assert.ok(r.amount_usd > 0);
});

test('distributeAI: a gift to a DIFFERENT recipient does not rate-limit this one', () => {
  const now = Date.now();
  const other = [{ to: REGISTRY[1], ts: now - 60 * 1000 }];
  const r = distributeAI(REGISTRY[0], 100, REGISTRY, other, { rateLimitHours: 24 });
  assert.ok(r.amount_usd > 0);
});

test('distributeAI: sender with no surplus above reserve -> reject', () => {
  const r = distributeAI(REGISTRY[0], 0, REGISTRY, []);
  assert.equal(r.amount_usd, 0);
  assert.match(r.reason, /no surplus/);
});

test('distributeAI: negative surplus fails closed', () => {
  const r = distributeAI(REGISTRY[0], -2, REGISTRY, []);
  assert.equal(r.amount_usd, 0);
});
