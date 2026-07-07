// VCSDD anicca-agent-spawn, Phase 2a (RED). REQ-101/REQ-102 pure treasury-gate functions.
// treasury-gate.mjs does not exist yet — this whole file is expected to fail at import time
// (module-not-found), the expected Red-phase state.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  computeColonySurplusUsd,
  computePerCitizenSurplusUsd,
  filterProductiveCitizens,
  deriveRecentSpawnAttempts,
  countChildrenProvisioning,
  deriveMeasuredShelterCostUsd,
  decideColonySpawn,
  BOOTSTRAP_WINDOW_DAYS,
  SPAWN_COOLDOWN_DAYS,
} from "../treasury-gate.mjs";

const DAY_MS = 86400000;

function selfFundedCitizen({ id, balanceUsd }) {
  return {
    id,
    wallet: { evm: true },
    fuel: { provider: "clawrouter-own-wallet" },
    humanDependencies: [],
    balanceUsd,
  };
}

function notSelfFundedCitizen({ id, balanceUsd }) {
  return {
    id,
    wallet: { evm: true },
    fuel: { provider: "anthropic-subscription" }, // not in OWN_FUNDED_FUEL_PROVIDERS
    humanDependencies: [],
    balanceUsd,
  };
}

function baseCitizen(id) {
  return { id, wallet: { evm: true }, fuel: { provider: "clawrouter-own-wallet" }, humanDependencies: [] };
}

function ledgerRow({ childId, status, activeSince, attemptedMs }) {
  const row = { child_id: childId, status };
  if (activeSince !== undefined) row.active_since = activeSince;
  if (attemptedMs !== undefined) row.attempted_ms = attemptedMs;
  return row;
}

// ---- REQ-101: computeColonySurplusUsd / computePerCitizenSurplusUsd ----

test("PROP-101a: sums max(0, balance_i - reserve) over a mixed fixture", () => {
  const citizens = [selfFundedCitizen({ id: "a", balanceUsd: 8 }), selfFundedCitizen({ id: "b", balanceUsd: 3 })];
  assert.equal(computeColonySurplusUsd({ citizens, perCitizenReserveUsd: 5 }), 3);
});

test("PROP-101b: a citizen failing isSelfFunded contributes 0 regardless of raw balance magnitude", () => {
  const citizens = [notSelfFundedCitizen({ id: "human", balanceUsd: 1000 }), selfFundedCitizen({ id: "a", balanceUsd: 8 })];
  assert.equal(computeColonySurplusUsd({ citizens, perCitizenReserveUsd: 5 }), 3);
});

test("REQ-101 edge case: exactly one self-funded citizen (N=1) needs no special case", () => {
  const citizens = [selfFundedCitizen({ id: "solo", balanceUsd: 12 })];
  assert.equal(computeColonySurplusUsd({ citizens, perCitizenReserveUsd: 5 }), 7);
});

test("PROP-101c/PROP-102d mirror: non-finite/negative balance fails closed to 0, never throws", () => {
  assert.equal(computeColonySurplusUsd({ citizens: [selfFundedCitizen({ id: "nan", balanceUsd: NaN })], perCitizenReserveUsd: 5 }), 0);
  assert.doesNotThrow(() =>
    computeColonySurplusUsd({ citizens: [selfFundedCitizen({ id: "neg", balanceUsd: -100 })], perCitizenReserveUsd: 5 })
  );
});

test("PROP-101i: computePerCitizenSurplusUsd returns one record per citizen, and computeColonySurplusUsd equals its sum by construction", () => {
  const citizens = [
    selfFundedCitizen({ id: "a", balanceUsd: 8 }),
    selfFundedCitizen({ id: "b", balanceUsd: 3 }),
    selfFundedCitizen({ id: "c", balanceUsd: 20 }),
  ];
  const perCitizen = computePerCitizenSurplusUsd({ citizens, perCitizenReserveUsd: 5 });
  assert.equal(perCitizen.length, 3);
  const byId = Object.fromEntries(perCitizen.map((p) => [p.citizenId, p.surplusUsd]));
  assert.equal(byId.a, 3);
  assert.equal(byId.b, 0);
  assert.equal(byId.c, 15);
  const total = computeColonySurplusUsd({ citizens, perCitizenReserveUsd: 5 });
  const summed = perCitizen.reduce((s, p) => s + p.surplusUsd, 0);
  assert.equal(total, summed);
});

// ---- REQ-101: filterProductiveCitizens ----

test("PROP-101d: excludes bootstrap_failed / window-overdue-active, passes through no-row citizens, last-write-wins on duplicate child_id rows", () => {
  const nowMs = 1_000_000_000_000;
  const bootstrapWindowDays = 14;
  const citizens = [
    baseCitizen("healthy"),
    baseCitizen("bootstrapFailed"),
    baseCitizen("overdue"),
    baseCitizen("noRow"),
    baseCitizen("dupHealthy"),
    baseCitizen("dupFailed"),
  ];
  const ledgerRows = [
    ledgerRow({ childId: "healthy", status: "active", activeSince: nowMs - 1 * DAY_MS }),
    ledgerRow({ childId: "bootstrapFailed", status: "bootstrap_failed", activeSince: nowMs - 20 * DAY_MS }),
    ledgerRow({ childId: "overdue", status: "active", activeSince: nowMs - 20 * DAY_MS }),
    ledgerRow({ childId: "dupHealthy", status: "provisioning" }),
    ledgerRow({ childId: "dupHealthy", status: "active", activeSince: nowMs - 1 * DAY_MS }),
    ledgerRow({ childId: "dupFailed", status: "provisioning" }),
    ledgerRow({ childId: "dupFailed", status: "active", activeSince: nowMs - 1 * DAY_MS }),
    ledgerRow({ childId: "dupFailed", status: "bootstrap_failed" }),
  ];
  const result = filterProductiveCitizens({ citizens, ledgerRows, nowMs, bootstrapWindowDays });
  const ids = result.map((c) => c.id).sort();
  assert.deepEqual(ids, ["dupHealthy", "healthy", "noRow"].sort());
});

test("PROP-101d edge case: malformed active row (missing/non-finite active_since) is excluded, fail-closed", () => {
  const nowMs = 1_000_000_000_000;
  const citizens = [baseCitizen("malformed")];
  const ledgerRows = [{ child_id: "malformed", status: "active" }]; // no active_since at all
  const result = filterProductiveCitizens({ citizens, ledgerRows, nowMs, bootstrapWindowDays: 14 });
  assert.equal(result.length, 0);
});

test("PROP-101k: bootstrapWindowDays defaults to BOOTSTRAP_WINDOW_DAYS (14) when omitted", () => {
  const nowMs = 1_000_000_000_000;
  const citizens = [baseCitizen("edge")];
  const ledgerRows = [ledgerRow({ childId: "edge", status: "active", activeSince: nowMs - (BOOTSTRAP_WINDOW_DAYS * DAY_MS - 1) })];
  const result = filterProductiveCitizens({ citizens, ledgerRows, nowMs });
  assert.equal(result.length, 1); // just inside the default window, still included
});

// ---- REQ-101/402: BOOTSTRAP_WINDOW_DAYS === SPAWN_COOLDOWN_DAYS by construction ----

test("PROP-101k/PROP-402e: BOOTSTRAP_WINDOW_DAYS and SPAWN_COOLDOWN_DAYS are identical by construction, both default 14", () => {
  assert.equal(SPAWN_COOLDOWN_DAYS, 14);
  assert.equal(BOOTSTRAP_WINDOW_DAYS, 14);
  assert.equal(BOOTSTRAP_WINDOW_DAYS, SPAWN_COOLDOWN_DAYS);
});

// ---- REQ-102: deriveRecentSpawnAttempts ----

test("PROP-102f: deriveRecentSpawnAttempts maps ledger rows, grouped by child_id, to one {ts,outcome} entry across all 4 cases", () => {
  const t0 = 1_000_000_000_000;
  const ledgerRows = [
    ledgerRow({ childId: "failedOnly", status: "failed", attemptedMs: t0 }),
    ledgerRow({ childId: "activeOnly", status: "provisioning", attemptedMs: t0 + 1 }),
    ledgerRow({ childId: "activeOnly", status: "active", attemptedMs: t0 + 1, activeSince: t0 + 1 }),
    ledgerRow({ childId: "activeThenBF", status: "provisioning", attemptedMs: t0 + 2 }),
    ledgerRow({ childId: "activeThenBF", status: "active", attemptedMs: t0 + 2, activeSince: t0 + 2 }),
    ledgerRow({ childId: "activeThenBF", status: "bootstrap_failed", attemptedMs: t0 + 2 }),
    ledgerRow({ childId: "inFlight", status: "provisioning", attemptedMs: t0 + 3 }),
  ];
  const attempts = deriveRecentSpawnAttempts({ ledgerRows });
  assert.equal(attempts.length, 3); // in-flight "provisioning"-only child_id excluded entirely
  const byTs = Object.fromEntries(attempts.map((a) => [a.ts, a.outcome]));
  assert.equal(byTs[t0], "failure");
  assert.equal(byTs[t0 + 1], "success");
  assert.equal(byTs[t0 + 2], "success"); // never retroactively flipped by the later bootstrap_failed row
  assert.equal(byTs[t0 + 3], undefined);
});

// ---- REQ-102: countChildrenProvisioning ----

test("PROP-102h: countChildrenProvisioning counts only child_id groups whose LAST row is exactly provisioning", () => {
  const ledgerRows = [
    ledgerRow({ childId: "onlyProvisioning", status: "provisioning" }),
    ledgerRow({ childId: "provThenActive", status: "provisioning" }),
    ledgerRow({ childId: "provThenActive", status: "active", activeSince: 1 }),
    ledgerRow({ childId: "provThenFailed", status: "provisioning" }),
    ledgerRow({ childId: "provThenFailed", status: "failed" }),
    ledgerRow({ childId: "provActiveBF", status: "provisioning" }),
    ledgerRow({ childId: "provActiveBF", status: "active", activeSince: 1 }),
    ledgerRow({ childId: "provActiveBF", status: "bootstrap_failed" }),
  ];
  assert.equal(countChildrenProvisioning({ ledgerRows }), 1);
});

// ---- REQ-102/303: deriveMeasuredShelterCostUsd ----

test("PROP-102j: deriveMeasuredShelterCostUsd returns null on an empty ledger, else ONLY the last-appended entry", () => {
  assert.equal(deriveMeasuredShelterCostUsd({ shelterCostLedgerRows: [] }), null);
  const rows = [
    { ts: 1, settledLeaseCostUsd: 3.5 },
    { ts: 2, settledLeaseCostUsd: 20 },
    { ts: 3, settledLeaseCostUsd: 4.25 },
  ];
  assert.equal(deriveMeasuredShelterCostUsd({ shelterCostLedgerRows: rows }), 4.25);
});

// ---- REQ-102: decideColonySpawn ----

function baseDecideArgs(overrides = {}) {
  return {
    colonySurplusUsd: 10,
    spawnThresholdUsd: 10,
    recentSpawnAttempts: [],
    nowMs: 2_000_000_000_000,
    cooldownDays: 14,
    failureCooldownCap: 3,
    childrenProvisioning: 0,
    maxConcurrentSpawns: 1,
    ...overrides,
  };
}

test("PROP-102a: colonySurplusUsd === spawnThresholdUsd exactly -> eligible (inclusive boundary)", () => {
  const r = decideColonySpawn(baseDecideArgs());
  assert.equal(r.eligible, true);
  assert.equal(r.reason, "ok");
});

test("PROP-102a: colonySurplusUsd 0.01 below threshold -> not eligible, insufficient_surplus", () => {
  const r = decideColonySpawn(baseDecideArgs({ colonySurplusUsd: 9.99 }));
  assert.equal(r.eligible, false);
  assert.equal(r.reason, "insufficient_surplus");
});

test("PROP-102b: a success within the cooldown window blocks spawn regardless of surplus size", () => {
  const nowMs = baseDecideArgs().nowMs;
  const r = decideColonySpawn(
    baseDecideArgs({ colonySurplusUsd: 999999, recentSpawnAttempts: [{ ts: nowMs - 1 * DAY_MS, outcome: "success" }] })
  );
  assert.equal(r.eligible, false);
  assert.equal(r.reason, "rate_limited");
});

test("PROP-102b/PROP-305c: failureCooldownCap (3) failures in-window blocks spawn even with huge surplus", () => {
  const nowMs = baseDecideArgs().nowMs;
  const attempts = Array.from({ length: 3 }, (_, i) => ({ ts: nowMs - (i + 1) * DAY_MS, outcome: "failure" }));
  const r = decideColonySpawn(baseDecideArgs({ colonySurplusUsd: 999999, recentSpawnAttempts: attempts }));
  assert.equal(r.eligible, false);
  assert.equal(r.reason, "rate_limited");
});

test("PROP-305g: strictly fewer than failureCooldownCap failures does NOT trigger cooldown", () => {
  const nowMs = baseDecideArgs().nowMs;
  const attempts = Array.from({ length: 2 }, (_, i) => ({ ts: nowMs - (i + 1) * DAY_MS, outcome: "failure" }));
  const r = decideColonySpawn(baseDecideArgs({ recentSpawnAttempts: attempts }));
  assert.equal(r.eligible, true);
});

test("PROP-305g: the MOMENT the cap (3rd failure) is reached, cooldown applies (exact boundary)", () => {
  const nowMs = baseDecideArgs().nowMs;
  const attempts = Array.from({ length: 3 }, (_, i) => ({ ts: nowMs - (i + 1) * DAY_MS, outcome: "failure" }));
  const r = decideColonySpawn(baseDecideArgs({ recentSpawnAttempts: attempts }));
  assert.equal(r.eligible, false);
  assert.equal(r.reason, "rate_limited");
});

test("PROP-102c: childrenProvisioning >= maxConcurrentSpawns blocks eligibility regardless of surplus/cooldown", () => {
  const r = decideColonySpawn(baseDecideArgs({ childrenProvisioning: 1, maxConcurrentSpawns: 1 }));
  assert.equal(r.eligible, false);
  assert.equal(r.reason, "max_concurrent_spawns");
});

test("PROP-102d: non-finite/negative colonySurplusUsd is treated as 0 (never eligible)", () => {
  assert.equal(decideColonySpawn(baseDecideArgs({ colonySurplusUsd: NaN })).eligible, false);
  assert.equal(decideColonySpawn(baseDecideArgs({ colonySurplusUsd: -5 })).eligible, false);
});

test("PROP-102e: check order is surplus -> cooldown -> concurrency cap (a fixture failing all three reports the SURPLUS failure)", () => {
  const nowMs = baseDecideArgs().nowMs;
  const r = decideColonySpawn(
    baseDecideArgs({
      colonySurplusUsd: 0,
      recentSpawnAttempts: [{ ts: nowMs - 1 * DAY_MS, outcome: "success" }],
      childrenProvisioning: 1,
      maxConcurrentSpawns: 1,
    })
  );
  assert.equal(r.eligible, false);
  assert.equal(r.reason, "insufficient_surplus");
});

// ---- REQ-102: decideColonySpawn fail-closed coercion for spawnThresholdUsd/childrenProvisioning/maxConcurrentSpawns ----

test("PROP-102l: undefined/null/NaN spawnThresholdUsd never falls through to eligible:true, even at colonySurplusUsd:0", () => {
  for (const malformed of [undefined, null, NaN]) {
    const r = decideColonySpawn(baseDecideArgs({ colonySurplusUsd: 0, spawnThresholdUsd: malformed }));
    assert.equal(r.eligible, false);
    assert.equal(r.reason, "insufficient_surplus");
  }
});

test("PROP-102l: null/NaN childrenProvisioning never silently bypasses the concurrency cap", () => {
  // undefined is intentionally excluded here: it triggers the parameter's own default (0), not this
  // fail-closed coercion path, so it is not a "malformed" case for this specific parameter.
  for (const malformed of [null, NaN]) {
    const r = decideColonySpawn(
      baseDecideArgs({ colonySurplusUsd: 100, spawnThresholdUsd: 10, childrenProvisioning: malformed, maxConcurrentSpawns: 1 })
    );
    assert.equal(r.eligible, false);
    assert.equal(r.reason, "max_concurrent_spawns");
  }
});

test("PROP-102l: null/NaN maxConcurrentSpawns is treated as zero capacity, never an infinite/no-op cap", () => {
  // undefined is intentionally excluded here: it triggers the parameter's own default (1), not this
  // fail-closed coercion path, so it is not a "malformed" case for this specific parameter.
  for (const malformed of [null, NaN]) {
    const r = decideColonySpawn(
      baseDecideArgs({ colonySurplusUsd: 100, spawnThresholdUsd: 10, childrenProvisioning: 0, maxConcurrentSpawns: malformed })
    );
    assert.equal(r.eligible, false);
    assert.equal(r.reason, "max_concurrent_spawns");
  }
});

// ---- REQ-101: filterProductiveCitizens null-entry handling (consistency with computeColonySurplusUsd) ----

test("PROP-101l: a null entry mixed into citizens is excluded gracefully, never thrown, consistent with computeColonySurplusUsd on the same fixture", () => {
  const nowMs = 1_000_000_000_000;
  const citizens = [null, baseCitizen("healthy"), undefined];
  const ledgerRows = [];
  assert.doesNotThrow(() => filterProductiveCitizens({ citizens, ledgerRows, nowMs, bootstrapWindowDays: 14 }));
  const result = filterProductiveCitizens({ citizens, ledgerRows, nowMs, bootstrapWindowDays: 14 });
  assert.deepEqual(result.map((c) => c.id), ["healthy"]);

  const mixedForSurplus = [null, selfFundedCitizen({ id: "healthy", balanceUsd: 10 }), undefined];
  assert.doesNotThrow(() => computeColonySurplusUsd({ citizens: mixedForSurplus, perCitizenReserveUsd: 0 }));
  assert.equal(computeColonySurplusUsd({ citizens: mixedForSurplus, perCitizenReserveUsd: 0 }), 10);
});
