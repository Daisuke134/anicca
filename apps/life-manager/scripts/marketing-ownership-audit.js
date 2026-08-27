#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const { importContentObject } = require("../lib/content-object-store.js");
const { ROUTES } = require("./marketing-cadence-reconcile.js");
const { resolveDataRoot } = require("../lib/runtime-paths.js");

const TENANT = "dais-local";
const LEGACY_FILE = /^ai\.anicca\.(?:marketing-|larry-|reelclaw-|watercolor-)/;
const SELECTED_LABELS = Object.freeze([...ROUTES.map((route) => route.label), "ai.anicca.life-manager-instagram-metrics", "ai.anicca.life-manager-tiktok-metrics"]);

function classifyOwnership({ selectedLabels = SELECTED_LABELS, selectedStates = {}, legacyRows = [], disabledOverrides = {} } = {}) {
  const selected = selectedLabels.map((label) => ({ label, ...(selectedStates[label] || { loaded: false, last_exit_code: null }), healthy: selectedStates[label]?.loaded === true && selectedStates[label]?.last_exit_code === 0 }));
  const conflicts = legacyRows.filter((row) => row.loaded === true || disabledOverrides[row.label] !== true).map((row) => ({ label: row.label, loaded: row.loaded === true, disabled_override: disabledOverrides[row.label] === true, reason: row.loaded === true ? "legacy_loaded" : "legacy_not_disabled" }));
  return { schema_version: 1, kind: "marketing_ownership_audit", tenant_id: TENANT, selected_healthy: selected.every((row) => row.healthy), selected, legacy_safe: conflicts.length === 0, legacy: legacyRows.map((row) => ({ label: row.label, loaded: row.loaded === true, last_exit_code: row.last_exit_code, disabled_override: disabledOverrides[row.label] === true, source_boundary: row.source_boundary || "unknown" })), conflicts, status: selected.every((row) => row.healthy) && conflicts.length === 0 ? "ready" : "not_ready" };
}

function launchdRows() {
  const result = spawnSync("/bin/launchctl", ["list"], { encoding: "utf8", timeout: 10_000 }); const rows = new Map();
  if (result.status !== 0) throw new Error("marketing ownership launchd list failed");
  for (const line of result.stdout.split(/\r?\n/).filter(Boolean).slice(1)) { const fields = line.trim().split(/\s+/); const label = fields.at(-1); if (!label) continue; const status = fields.length >= 3 && /^-?\d+$/.test(fields.at(-2)) ? Number(fields.at(-2)) : null; rows.set(label, { loaded: true, last_exit_code: status }); }
  return rows;
}

function disabledOverrides() {
  const result = spawnSync("/bin/launchctl", ["print-disabled", `gui/${process.getuid()}`], { encoding: "utf8", timeout: 10_000 }); if (result.status !== 0) throw new Error("marketing ownership disabled-state read failed"); const output = {};
  for (const match of result.stdout.matchAll(/"([^"]+)"\s*=>\s*(enabled|disabled)/g)) output[match[1]] = match[2] === "disabled";
  return output;
}

function plistRow(file, loaded) {
  const result = spawnSync("/usr/bin/plutil", ["-convert", "json", "-o", "-", "--", file], { encoding: "utf8", timeout: 10_000 }); const fallback = path.basename(file, ".plist");
  if (result.status !== 0) return { label: fallback, loaded, last_exit_code: null, source_boundary: "plist_parse_error" };
  const value = JSON.parse(result.stdout); const label = String(value.Label || fallback); const args = Array.isArray(value.ProgramArguments) ? value.ProgramArguments.map(String) : []; const program = args[1] || args[0] || ""; const legacyPath = new RegExp(["open", "claw"].join("") + "|" + ["profitable", "-claude"].join("") + "|/anicca/skills/", "i"); return { label, loaded, last_exit_code: null, source_boundary: legacyPath.test(program) ? "legacy_or_openclaw_path" : "other" };
}

function auditInstalledOwnership({ launchd = launchdRows(), disabled = disabledOverrides(), plistDir = path.join(process.env.HOME || "/Users/anicca", "Library/LaunchAgents") } = {}) {
  const selectedStates = Object.fromEntries(SELECTED_LABELS.map((label) => [label, launchd.get(label) || { loaded: false, last_exit_code: null }])); const legacyRows = fs.readdirSync(plistDir).filter((name) => LEGACY_FILE.test(name) && name.endsWith(".plist")).map((name) => { const file = path.join(plistDir, name); const parsed = plistRow(file, launchd.has(path.basename(name, ".plist"))); const state = launchd.get(parsed.label); return { ...parsed, ...(state || { loaded: false, last_exit_code: null }) }; });
  return classifyOwnership({ selectedStates, legacyRows, disabledOverrides: disabled });
}

function auditPointer(dataDir) { return path.join(dataDir, "marketing/ownership/28d.json"); }

function persistOwnershipAudit({ dataDir = resolveDataRoot(process.env), audit = auditInstalledOwnership(), observedAt = new Date().toISOString() } = {}) {
  const pointer = auditPointer(dataDir); if (fs.statSync(pointer, { throwIfNoEntry: false })?.isFile()) return { ...JSON.parse(fs.readFileSync(pointer, "utf8")), created: false, pointer };
  const snapshot = { ...audit, observed_at: observedAt }; fs.mkdirSync(path.dirname(pointer), { recursive: true, mode: 0o700 }); const candidate = `${pointer}.candidate-${process.pid}`; fs.writeFileSync(candidate, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o600 }); const imported = importContentObject(candidate, { objectDir: path.join(dataDir, "objects") }); fs.unlinkSync(candidate); const value = { ...snapshot, snapshot_ref: imported.ref }; const temporary = `${pointer}.tmp-${process.pid}`; fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 }); fs.renameSync(temporary, pointer); fs.chmodSync(pointer, 0o600); return { ...value, created: true, pointer };
}

if (require.main === module) {
  const result = persistOwnershipAudit(); process.stdout.write(`${JSON.stringify({ created: result.created, status: result.status, selected_healthy: result.selected_healthy, legacy_safe: result.legacy_safe, conflicts: result.conflicts })}\n`);
}

module.exports = { LEGACY_FILE, SELECTED_LABELS, auditInstalledOwnership, auditPointer, classifyOwnership, persistOwnershipAudit };
