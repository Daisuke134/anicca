"use strict";

const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const SAFE_TEXT = /^[a-zA-Z0-9][a-zA-Z0-9:._-]{0,159}$/;
const SHA = /^sha256:[0-9a-f]{64}$/;
const PRIVATE = /(?:https?:\/\/|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|bearer\s+[a-z0-9._-]{12,})/i;
const EFFECTS = new Set(["success", "tool_failure", "timeout", "process_crash"]);

function unavailable() {
  throw new Error("Connector observation must be privacy-safe");
}

function safe(value) {
  const text = String(value == null ? "" : value);
  if (!SAFE_TEXT.test(text) || PRIVATE.test(text)) unavailable();
  return text;
}

function buildObservation(input = {}) {
  const observedEffect = safe(input.observed_effect);
  const incidentClass = safe(input.incident_class);
  if (!EFFECTS.has(observedEffect)) unavailable();
  if ((observedEffect === "success") !== (incidentClass === "none")) unavailable();
  const stable = {
    stage: safe(input.stage),
    safe_action: safe(input.safe_action),
    expected_effect: safe(input.expected_effect),
    observed_effect: observedEffect,
    incident_class: incidentClass,
    owner_generation: input.owner_generation,
    code_commit: safe(input.code_commit),
    cursor: safe(input.cursor),
    provider_readback: safe(input.provider_readback || "none"),
    screenshot_sha: safe(input.screenshot_sha || "none"),
  };
  if (!Number.isInteger(stable.owner_generation) || stable.owner_generation < 1) unavailable();
  const observedAt = String(input.observed_at || "");
  if (!Number.isFinite(Date.parse(observedAt))) unavailable();
  const fingerprint = `sha256:${createHash("sha256").update(JSON.stringify(stable)).digest("hex")}`;
  return Object.freeze({
    schema_version: 1,
    wake_id: safe(input.wake_id),
    run_id: safe(input.run_id),
    ...stable,
    observed_at: observedAt,
    fingerprint,
  });
}

function appendObservation(file, observation) {
  const resolved = path.resolve(String(file || ""));
  if (!path.isAbsolute(resolved) || resolved === path.parse(resolved).root) unavailable();
  if (!observation || typeof observation !== "object" || !SHA.test(String(observation.fingerprint || ""))) unavailable();
  let source = "";
  try {
    const stat = fs.statSync(resolved);
    if (stat.size > 1_000_000) unavailable();
    source = fs.readFileSync(resolved, "utf8");
  } catch (error) {
    if (!error || error.code !== "ENOENT") throw error;
  }
  const duplicate = observation.incident_class !== "none" && source.split(/\r?\n/).filter(Boolean).some((line) => {
    try { return JSON.parse(line).fingerprint === observation.fingerprint; }
    catch { unavailable(); }
  });
  if (duplicate) return false;
  fs.mkdirSync(path.dirname(resolved), { recursive: true, mode: 0o700 });
  fs.appendFileSync(resolved, `${JSON.stringify(observation)}\n`, { encoding: "utf8", mode: 0o600 });
  fs.chmodSync(resolved, 0o600);
  return true;
}

module.exports = { appendObservation, buildObservation };

if (require.main === module) {
  const [command, file, wakeId, runId, codeCommit] = process.argv.slice(2);
  if (command !== "process-crash" || !file || !wakeId || !runId || !codeCommit) process.exit(2);
  try {
    const observation = buildObservation({
      wake_id: wakeId,
      run_id: runId,
      stage: "native_pass",
      safe_action: "runtime_execute",
      expected_effect: "applied_bundle",
      observed_effect: "process_crash",
      incident_class: "process_crash",
      owner_generation: 1,
      code_commit: codeCommit,
      cursor: "provider:none",
      observed_at: new Date().toISOString(),
    });
    appendObservation(file, observation);
    appendObservation(path.join(path.dirname(file), "observer-incidents.jsonl"), observation);
    process.exit(0);
  } catch {
    process.exit(2);
  }
}
