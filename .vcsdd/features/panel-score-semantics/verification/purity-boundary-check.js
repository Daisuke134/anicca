"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "../../../..");
const corePath = path.join(repoRoot, "apps/life-call/lib/panel-score-semantics.js");
const coreSource = fs.readFileSync(corePath, "utf8");
const { buildScorePeriods, computePanelScores } = require(corePath);

const externalEffectPatterns = [
  /process\.env/g,
  /Date\.now\s*\(/g,
  /Math\.random\s*\(/g,
  /\bfetch\s*\(/g,
  /require\s*\(\s*["']node:(?:fs|net|http|https|child_process)/g,
];
const externalEffectFindings = externalEffectPatterns.reduce((count, pattern) => count + [...coreSource.matchAll(pattern)].length, 0);
assert.equal(externalEffectFindings, 0);

function deepFreeze(value) {
  if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
  for (const nested of Object.values(value)) deepFreeze(nested);
  return Object.freeze(value);
}

const nowMs = Date.parse("2026-07-15T12:00:00.000Z");
const firstPeriods = buildScorePeriods(nowMs, "UTC");
const secondPeriods = buildScorePeriods(nowMs, "UTC");
assert.deepEqual(secondPeriods, firstPeriods);

const grouped = {
  uid: "proof-tenant",
  daily: [{
    public_ref: "93000000-0000-4000-8000-000000000001",
    revision_key: "94000000-0000-4000-8000-000000000001",
    uid: "proof-tenant",
    organ: "daily",
    entity_key: "proof-entity",
    outcome_kind: "daily_call",
    outcome_status: "required_succeeded",
    occurred_at: "2026-07-14T09:00:00.000Z",
    resolved_at: null,
    recorded_at: "2026-07-14T09:00:00.000Z",
    amount_minor: null,
    currency: null,
    components: {},
  }],
  physical: [],
  mental: [],
  financial: [],
};
const before = JSON.stringify({ grouped, periods: firstPeriods });
deepFreeze(grouped);
deepFreeze(firstPeriods);
const first = computePanelScores(grouped, firstPeriods, "UTC");
const second = computePanelScores(grouped, firstPeriods, "UTC");
assert.deepEqual(second, first);
assert.equal(JSON.stringify({ grouped, periods: firstPeriods }), before);

const moduleLocalCacheWrites = [...coreSource.matchAll(/FORMATTERS\.set\s*\(/g)].length;
assert.equal(moduleLocalCacheWrites, 1);

console.log(`purity-boundary-check external_effect_findings=${externalEffectFindings} input_mutation_findings=0 deterministic_replays=2 module_local_cache_writes=${moduleLocalCacheWrites} result=PASS`);
