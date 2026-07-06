// decide.test.mjs — pure-function tests for economy/gig/decide.mjs's ELIGIBILITY gate (surplus->post,
// broke+open-gig->take, nothing->idle). Injectable balance + board state only, no real network — mirrors
// economy/ubi/__tests__/ubi.test.mjs's style for the sibling colony-decision gate.
import { test } from "node:test";
import assert from "node:assert/strict";
import { decideGigAction, DEFAULT_RESERVE_USDC, DEFAULT_LOW_USDC } from "../decide.mjs";

// ── post: surplus above reserve ──────────────────────────────────────────────────────────

test("decideGigAction: balance well above reserve -> post-eligible with the real surplus", () => {
  const r = decideGigAction({ balanceUsdc: 12, openGigs: [] });
  assert.equal(r.action, "post");
  assert.equal(r.surplusUsdc, +(12 - DEFAULT_RESERVE_USDC).toFixed(6));
  assert.match(r.reason, /surplus/);
});

test("decideGigAction: post-eligibility ignores the board entirely (posting doesn't need existing gigs)", () => {
  const r = decideGigAction({ balanceUsdc: 100, openGigs: [{ id: "1" }, { id: "2" }] });
  assert.equal(r.action, "post");
});

// ── take: below survival floor with real open gigs ───────────────────────────────────────

test("decideGigAction: balance below survival floor with open gigs -> take-eligible", () => {
  const r = decideGigAction({ balanceUsdc: 0.1, openGigs: [{ id: "1" }] });
  assert.equal(r.action, "take");
  assert.equal(r.openGigCount, 1);
  assert.match(r.reason, /survival floor/);
});

test("decideGigAction: balance below survival floor but board is empty -> idle (nothing to take)", () => {
  const r = decideGigAction({ balanceUsdc: 0.1, openGigs: [] });
  assert.equal(r.action, "idle");
  assert.match(r.reason, /no open gigs/);
});

test("decideGigAction: take-eligibility counts every open gig on the board, not just the first", () => {
  const r = decideGigAction({ balanceUsdc: 0, openGigs: [{ id: "1" }, { id: "2" }, { id: "3" }] });
  assert.equal(r.action, "take");
  assert.equal(r.openGigCount, 3);
});

// ── idle: healthy middle zone ─────────────────────────────────────────────────────────────

test("decideGigAction: balance between floor and reserve -> idle regardless of open gigs", () => {
  const r = decideGigAction({ balanceUsdc: 2, openGigs: [{ id: "1" }] });
  assert.equal(r.action, "idle");
  assert.match(r.reason, /holding/);
});

// ── boundaries (exact equality, not strictly above/below) ────────────────────────────────

test("decideGigAction: balance exactly at reserve -> idle (surplus must be strictly positive)", () => {
  const r = decideGigAction({ balanceUsdc: DEFAULT_RESERVE_USDC, openGigs: [] });
  assert.equal(r.action, "idle");
});

test("decideGigAction: balance exactly at the survival floor -> idle (must be strictly below)", () => {
  const r = decideGigAction({ balanceUsdc: DEFAULT_LOW_USDC, openGigs: [{ id: "1" }] });
  assert.equal(r.action, "idle");
});

// ── fail-closed on bad input ───────────────────────────────────────────────────────────────

test("decideGigAction: unknown balance (NaN) -> idle, fail closed", () => {
  const r = decideGigAction({ balanceUsdc: NaN, openGigs: [{ id: "1" }] });
  assert.equal(r.action, "idle");
  assert.match(r.reason, /unknown/);
});

test("decideGigAction: missing balance -> idle, fail closed", () => {
  const r = decideGigAction({ openGigs: [{ id: "1" }] });
  assert.equal(r.action, "idle");
});

test("decideGigAction: inverted config (lowUsdc > reserveUsdc) -> idle, fail closed", () => {
  const r = decideGigAction({ balanceUsdc: 3, reserveUsdc: 1, lowUsdc: 2, openGigs: [] });
  assert.equal(r.action, "idle");
  assert.match(r.reason, /invalid reserve/);
});

test("decideGigAction: custom reserve/low thresholds are honored", () => {
  const r = decideGigAction({ balanceUsdc: 50, reserveUsdc: 40, lowUsdc: 5, openGigs: [] });
  assert.equal(r.action, "post");
  assert.equal(r.surplusUsdc, 10);
});

// ── no crash on malformed openGigs ────────────────────────────────────────────────────────

test("decideGigAction: non-array openGigs treated as zero gigs, never throws", () => {
  const r = decideGigAction({ balanceUsdc: 0.1, openGigs: null });
  assert.equal(r.action, "idle");
});
