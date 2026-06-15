// TDD for the runner's gate-override logic (spec27b first-birth proof). The deterministic gate stays
// authoritative for autonomous wakes (broke parent never spawns). A founder-authorized FIRST birth may
// override ONLY the balance reason (rate-limit + cap STILL bind) so the colony's very first child can be
// born to prove the pipeline LIVE, without ever letting a broke parent autonomously drain itself.
const test = require("node:test");
const assert = require("node:assert");
const { effectiveDecision } = require("../spawn-decision.js");
const { decideSpawn } = require("../spawn-gate.js");

test("no force: a broke parent stays dormant (autonomous safety preserved)", () => {
  const d = effectiveDecision({ balanceUsdc: 0.01, children: [], now: Date.now(), force: false });
  assert.strictEqual(d.eligible, false);
  assert.strictEqual(d.reason, "low_balance");
});

test("force: overrides ONLY low_balance -> eligible (first-birth proof)", () => {
  const d = effectiveDecision({ balanceUsdc: 0.01, children: [], now: Date.now(), force: true });
  assert.strictEqual(d.eligible, true);
  assert.strictEqual(d.reason, "forced_genesis_birth");
});

test("force does NOT override the concurrency cap (max_children still binds)", () => {
  const children = [{ childId: "anicca-c001", spawned_ms: 1 }]; // old child, but caps at 1
  const d = effectiveDecision({ balanceUsdc: 0.01, children, now: Date.now(), force: true });
  assert.strictEqual(d.eligible, false);
  assert.strictEqual(d.reason, "max_children");
});

test("force does NOT override the rate-limit (a recent child still blocks)", () => {
  const now = Date.now();
  const children = [{ childId: "anicca-c001", spawned_ms: now - 1000 }]; // spawned a second ago
  // raise the cap so rate-limit is the binding constraint we're testing
  const d = effectiveDecision({ balanceUsdc: 0.01, children, now, force: true, maxChildren: 5 });
  assert.strictEqual(d.eligible, false);
  assert.strictEqual(d.reason, "rate_limited");
});

test("force eligible matches the funded gate (parity above threshold)", () => {
  const funded = decideSpawn({ balanceUsdc: 50, children: [], now: Date.now() });
  const forced = effectiveDecision({ balanceUsdc: 50, children: [], now: Date.now(), force: false });
  assert.strictEqual(funded.eligible, forced.eligible);
});
