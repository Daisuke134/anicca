"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { importContentObject } = require("../lib/content-object-store.js");
const { assignmentPointer } = require("./marketing-hook-assignment.js");
const { consumptionProof, persistHookConsumptionProof } = require("./marketing-hook-consumption.js");

const BASE = { assignment_id: "mkt12-hook-test", assignment_ref: `object://sha256/${"a".repeat(64)}`, decision_status: "decided", decision: "keep_challenger", lane_id: "honne-en", product_id: "honne-ai", locale: "en", account_id: "@honne_reveal" };

test("consumption proof remains pending until a decision and matching generation exist", () => {
  assert.deepEqual(consumptionProof({ ...BASE, decision_status: "pending", decision: null }, null), { status: "pending", reason: "decision_pending", assignment_id: BASE.assignment_id });
  assert.deepEqual(consumptionProof(BASE, null), { status: "pending", reason: "generation_receipt_missing", assignment_id: BASE.assignment_id });
});

test("consumption proof accepts only the decision's expected variant", () => {
  const receipt = { assignment_ref: BASE.assignment_ref, hook_variant: "challenger", hook_id: "HEN-002", slot: "2026-08-28T02:00:00.000Z" };
  assert.deepEqual(consumptionProof(BASE, receipt), { status: "proved", assignment_id: BASE.assignment_id, slot: receipt.slot, hook_id: receipt.hook_id, hook_variant: "challenger" });
  assert.deepEqual(consumptionProof(BASE, { ...receipt, hook_variant: "baseline" }), { status: "invalid", reason: "variant_mismatch", assignment_id: BASE.assignment_id });
});

test("consumption proofs persist pending state and replay without a second object", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-hook-consumption-")); const objectDir = path.join(dataDir, "objects");
  const assignmentSource = path.join(dataDir, "assignment.json"); fs.writeFileSync(assignmentSource, "{}\n"); const assignmentRef = importContentObject(assignmentSource, { objectDir }).ref;
  const assignmentFile = assignmentPointer(dataDir); fs.mkdirSync(path.dirname(assignmentFile), { recursive: true }); fs.writeFileSync(assignmentFile, JSON.stringify({ schema_version: 1, kind: "marketing_hook_experiment_assignments", tenant_id: "dais-local", snapshot_ref: assignmentRef, assignments: [] }));
  const decisionSource = path.join(dataDir, "decision.json"); fs.writeFileSync(decisionSource, "{}\n"); const decisionRef = importContentObject(decisionSource, { objectDir }).ref;
  const decisionFile = path.join(dataDir, "tenants/dais-local/marketing/experiments/hook-decisions.json"); fs.writeFileSync(decisionFile, JSON.stringify({ schema_version: 1, kind: "marketing_hook_decisions", tenant_id: "dais-local", snapshot_ref: decisionRef, decisions: [{ ...BASE, assignment_ref: assignmentRef }] }));
  const first = persistHookConsumptionProof({ dataDir, observedAt: "2026-08-28T02:30:00.000Z" }); const replay = persistHookConsumptionProof({ dataDir, observedAt: "2026-08-28T03:00:00.000Z" });
  assert.equal(first.created, true); assert.equal(first.proofs.length, 1); assert.equal(first.proofs[0].status, "pending"); assert.equal(replay.created, false); assert.equal(replay.snapshot_ref, first.snapshot_ref); assert.equal(fs.statSync(first.pointer).mode & 0o777, 0o600);
});
