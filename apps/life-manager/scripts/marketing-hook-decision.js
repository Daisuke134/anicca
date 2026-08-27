#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { createContentObjectStore, importContentObject } = require("../lib/content-object-store.js");
const { assignmentPointer } = require("./marketing-hook-assignment.js");
const { resolveDataRoot } = require("../lib/runtime-paths.js");

const TENANT = "dais-local";
const MIN_SAMPLES_PER_VARIANT = 4;
const OBJECT_REF = /^object:\/\/sha256\/[0-9a-f]{64}$/;
const VARIANTS = Object.freeze(["baseline", "challenger"]);

function unavailableDecision(reason) {
  return { status: "pending", decision: null, reason };
}

function evaluateHookDecision(assignment, observations) {
  if (!assignment || !Array.isArray(observations)) throw new Error("hook decision input is invalid");
  if (observations.length === 0) return { decision: unavailableDecision("attribution_unavailable"), samples: { baseline: 0, challenger: 0 }, metrics: { baseline: null, challenger: null }, source_refs: [] };
  const groups = { baseline: [], challenger: [] };
  for (const row of observations) {
    if (!VARIANTS.includes(row?.variant)) throw new Error("hook decision variant is invalid");
    if (row.source_status !== "attributed") return { decision: unavailableDecision("attribution_unavailable"), samples: { baseline: groups.baseline.length, challenger: groups.challenger.length }, metrics: { baseline: null, challenger: null }, source_refs: [] };
    if (!row.primary_metric || row.primary_metric.status !== "measured" || typeof row.primary_metric.value !== "number" || !Number.isFinite(row.primary_metric.value)) return { decision: unavailableDecision("metric_unavailable"), samples: { baseline: groups.baseline.length, challenger: groups.challenger.length }, metrics: { baseline: null, challenger: null }, source_refs: [] };
    if (row.sample_ref != null && !OBJECT_REF.test(String(row.sample_ref))) throw new Error("hook decision sample ref is invalid");
    groups[row.variant].push(row);
  }
  const samples = { baseline: groups.baseline.length, challenger: groups.challenger.length };
  if (samples.baseline < MIN_SAMPLES_PER_VARIANT || samples.challenger < MIN_SAMPLES_PER_VARIANT) return { decision: unavailableDecision("sample_insufficient"), samples, metrics: { baseline: null, challenger: null }, source_refs: groups.baseline.concat(groups.challenger).map((row) => row.sample_ref).filter(Boolean) };
  const average = (rows) => rows.reduce((total, row) => total + row.primary_metric.value, 0) / rows.length;
  const metrics = { baseline: average(groups.baseline), challenger: average(groups.challenger) };
  return { decision: { status: "decided", decision: metrics.challenger > metrics.baseline ? "keep_challenger" : "revert_challenger", reason: metrics.challenger > metrics.baseline ? "challenger_primary_metric_higher" : "baseline_primary_metric_not_lower", primary_metric: assignment.primary_metric, sample_minimum: MIN_SAMPLES_PER_VARIANT }, samples, metrics, source_refs: groups.baseline.concat(groups.challenger).map((row) => row.sample_ref).filter(Boolean) };
}

function decisionPointer(dataDir) { return path.join(dataDir, "tenants", TENANT, "marketing", "experiments", "hook-decisions.json"); }
function decisionSummary(result) { return (result.decisions || []).map(({ lane_id, decision_status, decision, reason }) => ({ lane_id, status: decision_status, decision, reason })); }

function readAssignments(dataDir) {
  const pointer = assignmentPointer(dataDir); if (!fs.statSync(pointer, { throwIfNoEntry: false })?.isFile()) throw new Error("hook assignment pointer is missing");
  const snapshot = JSON.parse(fs.readFileSync(pointer, "utf8")); if (snapshot.schema_version !== 1 || snapshot.kind !== "marketing_hook_experiment_assignments" || snapshot.tenant_id !== TENANT || !OBJECT_REF.test(String(snapshot.snapshot_ref || "")) || !Array.isArray(snapshot.assignments)) throw new Error("hook assignment snapshot is invalid");
  const objectStore = createContentObjectStore({ objectDir: path.join(dataDir, "objects") }); objectStore.resolve(snapshot.snapshot_ref);
  return { assignmentRef: snapshot.snapshot_ref, assignments: snapshot.assignments };
}

function persistHookDecisions({ dataDir = resolveDataRoot(process.env), observations = {}, expectedSnapshotRef = null, observedAt = new Date().toISOString() } = {}) {
  const { assignmentRef, assignments } = readAssignments(dataDir); const decisions = assignments.map((assignment) => { const evaluated = evaluateHookDecision(assignment, observations[assignment.assignment_id] || []); return { assignment_ref: assignmentRef, assignment_id: assignment.assignment_id, experiment_id: assignment.experiment_id, tenant_id: TENANT, lane_id: assignment.lane_id, product_id: assignment.product_id, format_id: assignment.format_id, locale: assignment.locale, account_id: assignment.account_id, primary_metric: assignment.primary_metric, decision_status: evaluated.decision.status, decision: evaluated.decision.decision, reason: evaluated.decision.reason, ...(evaluated.decision.sample_minimum ? { sample_minimum: evaluated.decision.sample_minimum } : {}), samples: evaluated.samples, metrics: evaluated.metrics, source_refs: evaluated.source_refs, observed_at: observedAt }; });
  const fingerprint = crypto.createHash("sha256").update(JSON.stringify(decisions.map(({ observed_at: _observedAt, ...value }) => value))).digest("hex");
  const pointer = decisionPointer(dataDir); const existing = fs.statSync(pointer, { throwIfNoEntry: false })?.isFile() ? JSON.parse(fs.readFileSync(pointer, "utf8")) : null;
  if (existing?.input_fingerprint === fingerprint) return { ...existing, created: false, pointer };
  if (existing && expectedSnapshotRef !== existing.snapshot_ref) throw new Error("hook decision CAS requires current ref");
  const snapshot = { schema_version: 1, kind: "marketing_hook_decisions", tenant_id: TENANT, assignment_ref: assignmentRef, revision: (existing?.revision || 0) + 1, input_fingerprint: fingerprint, observed_at: observedAt, decisions };
  fs.mkdirSync(path.dirname(pointer), { recursive: true, mode: 0o700 }); const candidate = `${pointer}.candidate-${process.pid}`; fs.writeFileSync(candidate, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o600 }); const imported = importContentObject(candidate, { objectDir: path.join(dataDir, "objects") }); fs.unlinkSync(candidate); const value = { ...snapshot, snapshot_ref: imported.ref }; const temporary = `${pointer}.tmp-${process.pid}`; fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 }); fs.renameSync(temporary, pointer); fs.chmodSync(pointer, 0o600); return { ...value, created: true, pointer };
}

if (require.main === module) {
  const result = persistHookDecisions();
  process.stdout.write(`${JSON.stringify({ created: result.created, snapshot_ref: result.snapshot_ref, decisions: decisionSummary(result) })}\n`);
}

module.exports = { MIN_SAMPLES_PER_VARIANT, VARIANTS, decisionPointer, decisionSummary, evaluateHookDecision, persistHookDecisions };
