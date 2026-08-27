#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { createContentObjectStore, importContentObject } = require("../lib/content-object-store.js");
const { ROUTES } = require("./marketing-cadence-reconcile.js");
const { auditInstalledOwnership } = require("./marketing-ownership-audit.js");
const { assignmentPointer } = require("./marketing-hook-assignment.js");
const { decisionPointer } = require("./marketing-hook-decision.js");
const { proofPointer } = require("./marketing-hook-consumption.js");
const { resolveDataRoot } = require("../lib/runtime-paths.js");

const TENANT = "dais-local";
const OBJECT_REF = /^object:\/\/sha256\/[0-9a-f]{64}$/;

function classifyFinalAudit(input) {
  const blockers = [];
  if (input.selected_healthy !== true || input.selected_count !== ROUTES.length + 2) blockers.push("selected_owner_unhealthy");
  if (input.cadence?.published !== ROUTES.length * 3 || input.cadence?.pending !== 0 || input.cadence?.missed !== 0 || input.cadence?.duplicate !== 0) blockers.push("cadence_not_complete");
  if (input.daily_accounts !== ROUTES.length) blockers.push("daily_account_coverage_incomplete");
  if (!Number.isInteger(input.weekly_message_length) || input.weekly_message_length > 4096) blockers.push("weekly_report_invalid");
  if ((input.decisions?.decided || 0) < (input.decisions?.total || 0)) blockers.push("hook_decisions_pending");
  if ((input.proofs?.proved || 0) < (input.proofs?.total || 0)) blockers.push("hook_consumption_pending");
  if (input.ownership?.status !== "ready" || (input.ownership?.conflicts || 0) > 0) blockers.push("legacy_owner_conflicts");
  return { status: blockers.length ? "not_ready" : "ready", blockers };
}

function day(nowMs) { const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(nowMs)).map(({ type, value }) => [type, value])); return `${parts.year}-${parts.month}-${parts.day}`; }

function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }

function latestSummary(dataDir, productId) {
  const root = path.join(dataDir, "tenants/dais-local/marketing/metrics/summaries", productId, "daily"); if (!fs.existsSync(root)) return null; const files = fs.readdirSync(root).filter((name) => /^\d{4}-\d{2}-\d{2}(?:\.correction)?\.json$/.test(name)).map((name) => path.join(root, name)); return files.map((file) => ({ file, snapshot: readJson(file) })).sort((left, right) => String(left.snapshot.observed_at || "").localeCompare(String(right.snapshot.observed_at || ""))).at(-1) || null;
}

function latestWeekly(dataDir) {
  const root = path.join(dataDir, "tenants/dais-local/marketing/metrics/summaries/mobile-marketing/weekly"); if (!fs.existsSync(root)) return null; const files = fs.readdirSync(root).filter((name) => /^\d{4}-W\d{2}(?:\.correction(?:\.\d+)?)?\.json$/.test(name)).map((name) => path.join(root, name)); return files.map((file) => ({ file, snapshot: readJson(file) })).sort((left, right) => String(left.snapshot.observed_at || "").localeCompare(String(right.snapshot.observed_at || ""))).at(-1) || null;
}

function pointerSnapshot(dataDir, file, kind, field) {
  if (!fs.statSync(file, { throwIfNoEntry: false })?.isFile()) return { status: "unavailable", ref: null, items: [] };
  const pointer = readJson(file); if (pointer.schema_version !== 1 || pointer.kind !== kind || pointer.tenant_id !== TENANT || !OBJECT_REF.test(String(pointer.snapshot_ref || ""))) throw new Error(`${kind} pointer invalid`);
  const snapshot = readJson(createContentObjectStore({ objectDir: path.join(dataDir, "objects") }).resolve(pointer.snapshot_ref)); if (snapshot.schema_version !== 1 || snapshot.kind !== kind || snapshot.tenant_id !== TENANT || !Array.isArray(snapshot[field])) throw new Error(`${kind} snapshot invalid`);
  return { status: "observed", ref: pointer.snapshot_ref, items: snapshot[field] };
}

function auditCurrent({ dataDir = resolveDataRoot(process.env), nowMs = Date.now() } = {}) {
  const reportDay = day(nowMs); const ownership = auditInstalledOwnership(); const cadencePath = path.join(dataDir, "marketing/cadence", `${reportDay}.json`); const cadence = fs.statSync(cadencePath, { throwIfNoEntry: false })?.isFile() ? readJson(cadencePath).counts : { published: 0, pending: ROUTES.length * 3, missed: 0, duplicate: 0 };
  const honne = latestSummary(dataDir, "honne-ai"); const anicca = latestSummary(dataDir, "anicca-ios"); const weekly = latestWeekly(dataDir); const decisions = pointerSnapshot(dataDir, decisionPointer(dataDir), "marketing_hook_decisions", "decisions"); const proofs = pointerSnapshot(dataDir, proofPointer(dataDir), "marketing_hook_consumption_proofs", "proofs"); const input = { selected_healthy: ownership.selected_healthy, selected_count: ownership.selected.length, cadence, daily_accounts: (honne?.snapshot.account_coverage?.length || 0) + (anicca?.snapshot.account_coverage?.length || 0), weekly_message_length: weekly?.snapshot.message?.length || 0, decisions: { total: decisions.items.length, decided: decisions.items.filter((item) => item.decision_status === "decided").length }, proofs: { total: proofs.items.length, proved: proofs.items.filter((item) => item.status === "proved").length }, ownership: { status: ownership.status, conflicts: ownership.conflicts.length } }; const verdict = classifyFinalAudit(input);
  return { schema_version: 1, kind: "marketing_final_audit", tenant_id: TENANT, report_day: reportDay, observed_at: new Date(nowMs).toISOString(), status: verdict.status, blockers: verdict.blockers, input, evidence: { cadence_file: fs.statSync(cadencePath, { throwIfNoEntry: false })?.isFile() ? cadencePath : null, daily_summary_files: [honne?.file, anicca?.file].filter(Boolean), weekly_summary_file: weekly?.file || null, assignment_ref: fs.statSync(assignmentPointer(dataDir), { throwIfNoEntry: false })?.isFile() ? readJson(assignmentPointer(dataDir)).snapshot_ref : null, decision_ref: decisions.ref, proof_ref: proofs.ref } };
}

function persistFinalAudit({ dataDir = resolveDataRoot(process.env), nowMs = Date.now() } = {}) {
  const snapshot = auditCurrent({ dataDir, nowMs }); const directory = path.join(dataDir, "marketing/final-audit"); const pointer = path.join(directory, `${snapshot.report_day}.json`); if (fs.statSync(pointer, { throwIfNoEntry: false })?.isFile()) return { ...readJson(pointer), created: false, pointer };
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 }); const candidate = `${pointer}.candidate-${process.pid}`; fs.writeFileSync(candidate, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o600 }); const imported = importContentObject(candidate, { objectDir: path.join(dataDir, "objects") }); fs.unlinkSync(candidate); const value = { ...snapshot, snapshot_ref: imported.ref }; const temporary = `${pointer}.tmp-${process.pid}`; fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 }); fs.renameSync(temporary, pointer); fs.chmodSync(pointer, 0o600); return { ...value, created: true, pointer };
}

if (require.main === module) { const result = persistFinalAudit(); process.stdout.write(`${JSON.stringify({ created: result.created, report_day: result.report_day, status: result.status, blockers: result.blockers, snapshot_ref: result.snapshot_ref })}\n`); }

module.exports = { auditCurrent, classifyFinalAudit, persistFinalAudit };
