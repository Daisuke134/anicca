"use strict";
// 10g BRAIN-a contract: intent-aware context graph.
// Six intent kinds held with provenance/confidence/expiry; a correction
// expires the prediction it targets; explicit > repeated > inferred.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {
  INTENT_KINDS, CONFIDENCE_TIERS,
  validateIntentEntry, confidenceForTier, buildGraph,
  applyCorrection, effectiveEntries,
} = require("./intent-graph.js");

const NOW_MS = Date.parse("2026-07-24T09:00:00.000Z");

function entry(overrides = {}) {
  return {
    id: "intent-1", uid: "u-1", kind: "explicit_goal",
    statement: "毎朝6時に起きて執筆する",
    provenance: { source: "user_message", evidence: "TG message 2026-07-01", observedAt: "2026-07-01T00:00:00.000Z" },
    confidenceTier: "explicit", confidence: confidenceForTier("explicit"),
    expiresAt: null, status: "active", supersedes: null,
    ...overrides,
  };
}

test("schema: all six intent kinds are accepted and closed", () => {
  assert.deepEqual([...INTENT_KINDS].sort(), [
    "correction", "delegation", "explicit_goal", "family_dependent", "prohibition", "repeated_preference",
  ]);
  for (const kind of INTENT_KINDS) {
    assert.doesNotThrow(() => validateIntentEntry(entry({ kind })), `kind ${kind} must validate`);
  }
});

test("schema: unknown keys, unknown kind, unknown source, and malformed fields are rejected", () => {
  assert.throws(() => validateIntentEntry({ ...entry(), extra: true }), /unknown key/);
  assert.throws(() => validateIntentEntry(entry({ kind: "vibe" })), /kind/);
  assert.throws(() => validateIntentEntry(entry({ provenance: { ...entry().provenance, source: "guess" } })), /source/);
  assert.throws(() => validateIntentEntry(entry({ provenance: { source: "user_message", evidence: "", observedAt: "2026-07-01T00:00:00.000Z" } })), /evidence/);
  assert.throws(() => validateIntentEntry(entry({ provenance: { source: "user_message", evidence: "x", observedAt: "not-a-date" } })), /observedAt/);
  assert.throws(() => validateIntentEntry(entry({ confidence: 1.5 })), /confidence/);
  assert.throws(() => validateIntentEntry(entry({ confidenceTier: "hunch" })), /confidenceTier/);
  assert.throws(() => validateIntentEntry(entry({ status: "maybe" })), /status/);
  assert.throws(() => validateIntentEntry(entry({ statement: "" })), /statement/);
  assert.throws(() => validateIntentEntry(entry({ expiresAt: "soon" })), /expiresAt/);
});

test("confidence: explicit > repeated > inferred, all within [0,1]", () => {
  assert.deepEqual([...CONFIDENCE_TIERS], ["explicit", "repeated", "inferred"]);
  const explicit = confidenceForTier("explicit");
  const repeated = confidenceForTier("repeated");
  const inferred = confidenceForTier("inferred");
  assert.ok(explicit > repeated && repeated > inferred, "ordering explicit > repeated > inferred");
  for (const v of [explicit, repeated, inferred]) assert.ok(v > 0 && v <= 1);
  assert.throws(() => confidenceForTier("hunch"), /tier/);
});

test("contract: a correction expires the old prediction and survives as the active truth", () => {
  const inferred = entry({
    id: "intent-old", kind: "repeated_preference", confidenceTier: "inferred",
    confidence: confidenceForTier("inferred"),
    statement: "夜はイベントに行くのが好き",
    provenance: { source: "calendar_pattern", evidence: "3 evening events in 60d", observedAt: "2026-07-10T00:00:00.000Z" },
  });
  const graph = buildGraph([inferred]);
  const correction = entry({
    id: "intent-corr", kind: "correction", confidenceTier: "explicit",
    confidence: confidenceForTier("explicit"),
    statement: "夜のイベントは好きではない。誘わないでほしい",
    provenance: { source: "correction", evidence: "TG reply 2026-07-20", observedAt: "2026-07-20T00:00:00.000Z" },
    supersedes: "intent-old",
  });
  const next = applyCorrection(graph, correction, NOW_MS);
  const old = next.entries.find((e) => e.id === "intent-old");
  assert.equal(old.status, "corrected", "old prediction must be expired by the correction");
  const active = effectiveEntries(next, NOW_MS);
  assert.ok(!active.some((e) => e.id === "intent-old"), "corrected prediction never resurfaces");
  assert.ok(active.some((e) => e.id === "intent-corr"), "correction is the active truth");
});

test("contract: applyCorrection rejects a correction without a real target", () => {
  const graph = buildGraph([entry({ id: "intent-a" })]);
  const bad = entry({ id: "c", kind: "correction", supersedes: "missing",
    provenance: { source: "correction", evidence: "x", observedAt: "2026-07-20T00:00:00.000Z" } });
  assert.throws(() => applyCorrection(graph, bad, NOW_MS), /supersedes/);
  const notCorrection = entry({ id: "c2", supersedes: "intent-a" });
  assert.throws(() => applyCorrection(graph, notCorrection, NOW_MS), /kind/);
});

test("expiry: entries past expiresAt drop out of the effective set without mutation", () => {
  const expiring = entry({ id: "intent-exp", expiresAt: "2026-07-23T00:00:00.000Z" });
  const alive = entry({ id: "intent-alive", expiresAt: "2026-08-01T00:00:00.000Z" });
  const graph = buildGraph([expiring, alive]);
  const active = effectiveEntries(graph, NOW_MS);
  assert.deepEqual(active.map((e) => e.id), ["intent-alive"]);
  assert.equal(graph.entries.find((e) => e.id === "intent-exp").status, "active", "effectiveEntries is pure");
});

const FIXTURES = path.join(__dirname, "..", "test", "fixtures", "intent-graph");

test("fixtures: Dais-type, mother-type, and non-event-type personas validate and behave", () => {
  const personas = ["dais.json", "mother.json", "non-event.json"];
  for (const file of personas) {
    const rows = JSON.parse(fs.readFileSync(path.join(FIXTURES, file), "utf8"));
    assert.ok(rows.length >= 3, `${file} carries at least 3 entries`);
    const graph = buildGraph(rows);
    assert.equal(graph.entries.length, rows.length, `${file} all entries validate`);
  }
  const dais = buildGraph(JSON.parse(fs.readFileSync(path.join(FIXTURES, "dais.json"), "utf8")));
  assert.ok(effectiveEntries(dais, NOW_MS).some((e) => e.kind === "explicit_goal"), "Dais type carries explicit goals");
  assert.ok(effectiveEntries(dais, NOW_MS).some((e) => e.kind === "delegation"), "Dais type delegates scope");

  const mother = buildGraph(JSON.parse(fs.readFileSync(path.join(FIXTURES, "mother.json"), "utf8")));
  assert.ok(effectiveEntries(mother, NOW_MS).some((e) => e.kind === "family_dependent"), "mother type carries dependents");

  const nonEvent = buildGraph(JSON.parse(fs.readFileSync(path.join(FIXTURES, "non-event.json"), "utf8")));
  const prohibition = effectiveEntries(nonEvent, NOW_MS).find((e) => e.kind === "prohibition");
  assert.ok(prohibition, "non-event type carries a prohibition");
  const corrected = nonEvent.entries.find((e) => e.status === "corrected");
  assert.ok(corrected && corrected.confidenceTier === "inferred",
    "non-event fixture shows an inferred event-liking prediction already expired by correction");
});
