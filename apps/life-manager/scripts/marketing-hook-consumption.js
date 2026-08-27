#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { createContentObjectStore, importContentObject } = require("../lib/content-object-store.js");
const { decisionPointer } = require("./marketing-hook-decision.js");
const { resolveDataRoot } = require("../lib/runtime-paths.js");
const { verifyMarketingVideoGenerationReceipt } = require("../lib/marketing-video-generation-adapter.js");

const TENANT = "dais-local";
const OBJECT_REF = /^object:\/\/sha256\/[0-9a-f]{64}$/;

function consumptionProof(decision, generationReceipt) {
  if (!decision || decision.decision_status !== "decided") return { status: "pending", reason: "decision_pending", assignment_id: decision?.assignment_id || null };
  if (!generationReceipt) return { status: "pending", reason: "generation_receipt_missing", assignment_id: decision.assignment_id };
  if (generationReceipt.assignment_ref !== decision.assignment_ref) return { status: "invalid", reason: "assignment_ref_mismatch", assignment_id: decision.assignment_id };
  const expected = decision.decision === "keep_challenger" ? "challenger" : decision.decision === "revert_challenger" ? "baseline" : null;
  if (!expected) return { status: "invalid", reason: "decision_value_invalid", assignment_id: decision.assignment_id };
  if (generationReceipt.hook_variant !== expected) return { status: "invalid", reason: "variant_mismatch", assignment_id: decision.assignment_id };
  return { status: "proved", assignment_id: decision.assignment_id, slot: generationReceipt.slot, hook_id: generationReceipt.hook_id, hook_variant: generationReceipt.hook_variant };
}

function latestGenerationReceipt(dataDir, decision) {
  const file = path.join(dataDir, "marketing", "receipts.jsonl"); if (!fs.statSync(file, { throwIfNoEntry: false })?.isFile()) return null;
  const rows = fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean).map((line) => { try { return JSON.parse(line).receipt; } catch { return null; } }).filter((receipt) => receipt && receipt.kind === "marketing_video_artifact" && receipt.assignment_ref === decision.assignment_ref && receipt.product_id === decision.product_id && receipt.format_id === decision.format_id && receipt.locale === decision.locale && verifyMarketingVideoGenerationReceipt(receipt));
  return rows.sort((left, right) => left.slot.localeCompare(right.slot) || left.generated_at.localeCompare(right.generated_at)).at(-1) || null;
}

function proofPointer(dataDir) { return path.join(dataDir, "tenants", TENANT, "marketing", "experiments", "hook-consumption-proofs.json"); }

function readDecisions(dataDir) {
  const pointer = decisionPointer(dataDir); if (!fs.statSync(pointer, { throwIfNoEntry: false })?.isFile()) throw new Error("hook decision pointer is missing");
  const snapshot = JSON.parse(fs.readFileSync(pointer, "utf8")); if (snapshot.schema_version !== 1 || snapshot.kind !== "marketing_hook_decisions" || snapshot.tenant_id !== TENANT || !OBJECT_REF.test(String(snapshot.snapshot_ref || "")) || !Array.isArray(snapshot.decisions)) throw new Error("hook decision pointer is invalid");
  createContentObjectStore({ objectDir: path.join(dataDir, "objects") }).resolve(snapshot.snapshot_ref);
  return { decisionRef: snapshot.snapshot_ref, decisions: snapshot.decisions };
}

function persistHookConsumptionProof({ dataDir = resolveDataRoot(process.env), expectedSnapshotRef = null, observedAt = new Date().toISOString() } = {}) {
  const { decisionRef, decisions } = readDecisions(dataDir); const proofs = decisions.map((decision) => consumptionProof(decision, latestGenerationReceipt(dataDir, decision))); const fingerprint = crypto.createHash("sha256").update(JSON.stringify(proofs)).digest("hex");
  const pointer = proofPointer(dataDir); const existing = fs.statSync(pointer, { throwIfNoEntry: false })?.isFile() ? JSON.parse(fs.readFileSync(pointer, "utf8")) : null;
  if (existing?.input_fingerprint === fingerprint) return { ...existing, created: false, pointer };
  if (existing && expectedSnapshotRef !== existing.snapshot_ref) throw new Error("hook consumption proof CAS requires current ref");
  const snapshot = { schema_version: 1, kind: "marketing_hook_consumption_proofs", tenant_id: TENANT, decision_ref: decisionRef, revision: (existing?.revision || 0) + 1, input_fingerprint: fingerprint, observed_at: observedAt, proofs };
  fs.mkdirSync(path.dirname(pointer), { recursive: true, mode: 0o700 }); const candidate = `${pointer}.candidate-${process.pid}`; fs.writeFileSync(candidate, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o600 }); const imported = importContentObject(candidate, { objectDir: path.join(dataDir, "objects") }); fs.unlinkSync(candidate); const value = { ...snapshot, snapshot_ref: imported.ref }; const temporary = `${pointer}.tmp-${process.pid}`; fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 }); fs.renameSync(temporary, pointer); fs.chmodSync(pointer, 0o600); return { ...value, created: true, pointer };
}

if (require.main === module) {
  const result = persistHookConsumptionProof();
  process.stdout.write(`${JSON.stringify({ created: result.created, snapshot_ref: result.snapshot_ref, proofs: result.proofs?.map(({ assignment_id, status, reason, hook_variant }) => ({ assignment_id, status, reason, hook_variant })) })}\n`);
}

module.exports = { consumptionProof, latestGenerationReceipt, persistHookConsumptionProof, proofPointer };
