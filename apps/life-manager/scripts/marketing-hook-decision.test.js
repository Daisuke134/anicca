"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { importContentObject } = require("../lib/content-object-store.js");
const { assignmentPointer } = require("./marketing-hook-assignment.js");
const { decisionSummary, evaluateHookDecision, persistHookDecisions } = require("./marketing-hook-decision.js");

const ASSIGNMENT = { schema_version: 1, kind: "marketing_hook_experiment_assignment", assignment_id: "mkt12-hook-test", experiment_id: "mkt12-test", tenant_id: "dais-local", lane_id: "honne-en", product_id: "honne-ai", format_id: "reelclaw", form: "relationship-confession", locale: "en", platform: "tiktok", account_id: "@honne_reveal", pack_ref: `object://sha256/${"a".repeat(64)}`, baseline: { variant: "baseline", hook_id: "HEN-001", hook_sha256: "b".repeat(64), hook_text: "baseline" }, challenger: { variant: "challenger", hook_id: "HEN-002", hook_sha256: "c".repeat(64), hook_text: "challenger" }, allocation: { baseline: 0.5, challenger: 0.5 }, primary_metric: "attributed_installs_per_1000_impressions", status: "assigned", observed_at: "2026-08-28T00:00:00.000Z" };

function rows(baseline, challenger, sourceStatus = "attributed") {
  return ["baseline", "challenger"].flatMap((variant) => Array.from({ length: 4 }, (_, index) => ({ variant, source_status: sourceStatus, sample_ref: `object://sha256/${crypto.createHash("sha256").update(`${variant}-${index}`).digest("hex")}`, primary_metric: { status: "measured", value: variant === "baseline" ? baseline : challenger } })));
}

test("hook decision stays pending when attribution or samples are insufficient", () => {
  assert.deepEqual(evaluateHookDecision(ASSIGNMENT, []).decision, { status: "pending", decision: null, reason: "attribution_unavailable" });
  assert.deepEqual(evaluateHookDecision(ASSIGNMENT, rows(1, 2, "unattributed")).decision, { status: "pending", decision: null, reason: "attribution_unavailable" });
  assert.deepEqual(evaluateHookDecision(ASSIGNMENT, rows(1, 2).slice(0, 7)).decision, { status: "pending", decision: null, reason: "sample_insufficient" });
});

test("hook decision keeps only a challenger that beats the baseline", () => {
  const result = evaluateHookDecision(ASSIGNMENT, rows(1, 2));
  assert.equal(result.decision.status, "decided");
  assert.equal(result.decision.decision, "keep_challenger");
  assert.equal(result.metrics.baseline, 1);
  assert.equal(result.metrics.challenger, 2);
});

test("pending decision summary renders a null decision safely", () => {
  assert.deepEqual(decisionSummary({ decisions: [{ lane_id: "honne-en", decision_status: "pending", decision: null, reason: "attribution_unavailable" }] }), [{ lane_id: "honne-en", status: "pending", decision: null, reason: "attribution_unavailable" }]);
});

test("hook decisions persist pending state and require the current ref for CAS", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-hook-decision-")); const objectDir = path.join(dataDir, "objects");
  const source = path.join(dataDir, "assignment.json"); fs.writeFileSync(source, JSON.stringify({ schema_version: 1, kind: "marketing_hook_experiment_assignments", tenant_id: "dais-local", assignments: [ASSIGNMENT] }));
  const assignmentRef = importContentObject(source, { objectDir }).ref; const pointer = assignmentPointer(dataDir); fs.mkdirSync(path.dirname(pointer), { recursive: true }); fs.writeFileSync(pointer, JSON.stringify({ schema_version: 1, kind: "marketing_hook_experiment_assignments", tenant_id: "dais-local", snapshot_ref: assignmentRef, assignments: [ASSIGNMENT] }));
  const first = persistHookDecisions({ dataDir, observations: {}, observedAt: "2026-08-28T00:00:00.000Z" }); const replay = persistHookDecisions({ dataDir, observations: {}, observedAt: "2026-08-28T01:00:00.000Z" });
  assert.equal(first.created, true); assert.equal(first.decisions[0].decision_status, "pending"); assert.equal(replay.created, false); assert.equal(replay.snapshot_ref, first.snapshot_ref); assert.equal(fs.statSync(first.pointer).mode & 0o777, 0o600);
  const updated = persistHookDecisions({ dataDir, observations: { [ASSIGNMENT.assignment_id]: rows(1, 2) }, expectedSnapshotRef: first.snapshot_ref, observedAt: "2026-08-28T02:00:00.000Z" });
  assert.equal(updated.created, true); assert.equal(updated.decisions[0].decision, "keep_challenger"); assert.throws(() => persistHookDecisions({ dataDir, observations: { [ASSIGNMENT.assignment_id]: rows(2, 1) }, observedAt: "2026-08-28T03:00:00.000Z" }), /CAS|required current ref/i);
});
