#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { createContentObjectStore, importContentObject } = require("../lib/content-object-store.js");
const { normalizeMarketingVideoPack } = require("../lib/marketing-video-generation-adapter.js");
const { resolveDataRoot } = require("../lib/runtime-paths.js");

const TENANT = "dais-local";
const LANES = Object.freeze([
  Object.freeze({ lane_id: "honne-en", product_id: "honne-ai", format_id: "reelclaw", form: "relationship-confession", locale: "en", platform: "tiktok", account_id: "@honne_reveal", pack_env: "LM_HONNE_EN_PACK_REF" }),
  Object.freeze({ lane_id: "honne-ja", product_id: "honne-ai", format_id: "reelclaw", form: "relationship-confession", locale: "ja", platform: "tiktok", account_id: "@honnevideo", pack_env: "LM_HONNE_JA_PACK_REF" }),
  Object.freeze({ lane_id: "anicca-main-ja", product_id: "anicca-ios", format_id: "reelclaw-card", form: "nudge-card", locale: "ja", platform: "tiktok", account_id: "@anicca.jp", pack_env: "LM_ANICCA_MAIN_PACK_REF" }),
]);
const HASH = /^[0-9a-f]{64}$/;
const OBJECT_REF = /^object:\/\/sha256\/[0-9a-f]{64}$/;

function exactInstant(value) {
  const text = String(value || ""); const date = new Date(text);
  if (!Number.isFinite(date.getTime()) || date.toISOString() !== text) throw new Error("hook assignment observed_at is invalid");
  return text;
}

function hookValue(variant, hook) {
  const hookSha256 = crypto.createHash("sha256").update(hook.text).digest("hex");
  return { variant, hook_id: hook.id, hook_sha256: hookSha256, hook_text: hook.text };
}

function buildHookAssignment(lane, pack, observedAt) {
  const expected = { productId: lane.product_id, formatId: lane.format_id, locale: lane.locale };
  const normalized = normalizeMarketingVideoPack(pack, expected);
  const hooks = normalized.hooks.filter(({ status }) => status !== "killed").sort((left, right) => left.id.localeCompare(right.id));
  if (hooks.length < 2) throw new Error(`${lane.lane_id} needs two active hooks`);
  const baseline = hookValue("baseline", hooks[0]); const challenger = hookValue("challenger", hooks[1]);
  const identity = { lane_id: lane.lane_id, product_id: lane.product_id, format_id: lane.format_id, locale: lane.locale, account_id: lane.account_id, pack_ref: lane.pack_ref || null, baseline_hook_id: baseline.hook_id, challenger_hook_id: challenger.hook_id };
  const digest = crypto.createHash("sha256").update(JSON.stringify(identity)).digest("hex");
  return { schema_version: 1, kind: "marketing_hook_experiment_assignment", assignment_id: `mkt12-hook-${digest.slice(0, 24)}`, experiment_id: `mkt12-hook-${digest.slice(0, 16)}`, tenant_id: TENANT, lane_id: lane.lane_id, product_id: lane.product_id, format_id: lane.format_id, form: normalized.form, locale: lane.locale, platform: lane.platform, account_id: lane.account_id, pack_ref: lane.pack_ref || null, baseline, challenger, allocation: { baseline: 0.5, challenger: 0.5 }, primary_metric: "attributed_installs_per_1000_impressions", secondary_metrics: ["views", "engagement", "activation", "paid_active"], guardrail_metrics: ["negative_feedback", "source_unavailable_rate"], status: "assigned", observed_at: exactInstant(observedAt) };
}

function assignmentPointer(dataDir) { return path.join(dataDir, "tenants", TENANT, "marketing", "experiments", "hook-assignments.json"); }

function assignmentRefFor(dataDir, laneId) {
  const pointer = assignmentPointer(dataDir); if (!fs.statSync(pointer, { throwIfNoEntry: false })?.isFile()) return null;
  const snapshot = JSON.parse(fs.readFileSync(pointer, "utf8")); if (snapshot.schema_version !== 1 || snapshot.kind !== "marketing_hook_experiment_assignments" || snapshot.tenant_id !== TENANT || !OBJECT_REF.test(String(snapshot.snapshot_ref || "")) || !Array.isArray(snapshot.assignments)) throw new Error("marketing hook assignment pointer is invalid");
  return snapshot.assignments.some((assignment) => assignment.lane_id === laneId) ? snapshot.snapshot_ref : null;
}

function requiredAssignmentRef(dataDir, laneId) {
  const ref = assignmentRefFor(dataDir, laneId); if (!ref) throw new Error(`${laneId} hook assignment missing`); return ref;
}

function persistHookAssignments({ dataDir = resolveDataRoot(process.env), env = process.env, observedAt = new Date().toISOString() } = {}) {
  const pointer = assignmentPointer(dataDir); const objectStore = createContentObjectStore({ objectDir: path.join(dataDir, "objects") });
  if (fs.statSync(pointer, { throwIfNoEntry: false })?.isFile()) return { ...JSON.parse(fs.readFileSync(pointer, "utf8")), created: false, pointer };
  const assignments = LANES.map((lane) => {
    const packRef = String(env[lane.pack_env] || "").trim(); if (!OBJECT_REF.test(packRef)) throw new Error(`${lane.lane_id} pack reference is invalid`);
    const pack = JSON.parse(fs.readFileSync(objectStore.resolve(packRef), "utf8")); return buildHookAssignment({ ...lane, pack_ref: packRef }, pack, observedAt);
  });
  const snapshot = { schema_version: 1, kind: "marketing_hook_experiment_assignments", tenant_id: TENANT, observed_at: exactInstant(observedAt), assignment_scope: "product_locale_account", assignments };
  fs.mkdirSync(path.dirname(pointer), { recursive: true, mode: 0o700 }); const candidate = `${pointer}.candidate-${process.pid}`; fs.writeFileSync(candidate, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o600 });
  const imported = importContentObject(candidate, { objectDir: path.join(dataDir, "objects") }); fs.unlinkSync(candidate); const value = { ...snapshot, snapshot_ref: imported.ref }; const temporary = `${pointer}.tmp-${process.pid}`; fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 }); fs.renameSync(temporary, pointer); fs.chmodSync(pointer, 0o600);
  return { ...value, created: true, pointer };
}

if (require.main === module) {
  const result = persistHookAssignments();
  process.stdout.write(`${JSON.stringify({ created: result.created, snapshot_ref: result.snapshot_ref, assignments: result.assignments?.map(({ lane_id, assignment_id, baseline, challenger }) => ({ lane_id, assignment_id, baseline: baseline.hook_id, challenger: challenger.hook_id })) })}\n`);
}

module.exports = { LANES, assignmentPointer, assignmentRefFor, buildHookAssignment, persistHookAssignments, requiredAssignmentRef };
