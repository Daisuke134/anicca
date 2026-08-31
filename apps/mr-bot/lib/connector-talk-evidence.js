"use strict";

const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { isVerifiedEventTalkOpportunity } = require("./event-talk-opportunity.js");
const { isVerifiedGroundedTalkPack } = require("./grounded-talk-pack.js");

const REF = /^[a-z][a-z0-9_-]+-event:\/\/event\/[A-Za-z0-9_-]+$/;
const RECEIPT = /^provider-receipt:\/\/[a-z0-9._~:/?#@!$&'()*+,;=%-]{1,950}$/i;
const TRANSITION_ID = /^talk-transition:[0-9a-f]{64}$/;
const TRANSITION_KEYS = Object.freeze([
  "event_ref", "from_state", "observed_at", "provider", "provider_receipt_ref",
  "schema_version", "to_state", "transition_id",
]);

function unavailable() { throw new Error("talk evidence unavailable"); }
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
function digest(value) { return createHash("sha256").update(stable(value), "utf8").digest("hex"); }

function talkTransitions(candidate, providerState, identitySha256, observedAt) {
  return Object.freeze([
    ["discovered", "application_ready"],
    ["application_ready", "submitted"],
    ["submitted", "provider_verified"],
  ].map(([fromState, toState]) => {
    const core = {
      schema_version: 1,
      event_ref: candidate.event_ref,
      provider: candidate.provider,
      from_state: fromState,
      to_state: toState,
      provider_receipt_ref: providerState.receipt_ref,
      observed_at: observedAt,
    };
    return Object.freeze({ ...core, transition_id: `talk-transition:${digest({ identitySha256, ...core })}` });
  }));
}

function validateStoredTransition(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)
    || Object.keys(row).sort().join(",") !== [...TRANSITION_KEYS].sort().join(",")
    || row.schema_version !== 1 || !REF.test(String(row.event_ref || ""))
    || !/^[a-z][a-z0-9_-]{1,31}$/.test(String(row.provider || ""))
    || !TRANSITION_ID.test(String(row.transition_id || ""))
    || !RECEIPT.test(String(row.provider_receipt_ref || ""))
    || !Number.isFinite(Date.parse(String(row.observed_at || "")))
    || new Date(Date.parse(row.observed_at)).toISOString() !== row.observed_at
    || ![["discovered", "application_ready"], ["application_ready", "submitted"], ["submitted", "provider_verified"]]
      .some(([fromState, toState]) => row.from_state === fromState && row.to_state === toState)) unavailable();
  return row;
}

function persistTalkTransitions(stateDir, rows) {
  const file = path.join(stateDir, "talk-application-transitions.jsonl");
  let existing = [];
  try {
    const stat = fs.statSync(file);
    if (!stat.isFile() || stat.size > 2_000_000) unavailable();
    existing = fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean).map((line) => {
      try { return validateStoredTransition(JSON.parse(line)); } catch { unavailable(); }
    });
  } catch (error) {
    if (!error || error.code !== "ENOENT") throw error;
  }
  const byId = new Map(existing.map((row) => [row.transition_id, row]));
  const missing = [];
  for (const row of rows) {
    const prior = byId.get(row.transition_id);
    if (prior && stable(prior) !== stable(row)) unavailable();
    if (!prior) missing.push(row);
  }
  if (missing.length > 0) {
    fs.appendFileSync(file, `${missing.map((row) => JSON.stringify(row)).join("\n")}\n`, { encoding: "utf8", mode: 0o600 });
  }
  fs.chmodSync(file, 0o600);
}

function createTalkEvidenceChain(options = {}) {
  const stateDir = path.resolve(String(options.stateDir || ""));
  const now = options.now || (() => new Date());
  if (!path.isAbsolute(stateDir) || stateDir === path.parse(stateDir).root || typeof now !== "function") unavailable();
  return Object.freeze({
    async completeTalkEvidence(input = {}) {
      const candidate = input.candidate;
      const providerState = input.providerState;
      if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)
        || !/^[a-z][a-z0-9_-]{1,31}$/.test(String(candidate.provider || ""))
        || !REF.test(String(candidate.event_ref || ""))
        || candidate.priority_class !== "open_talk"
        || typeof candidate.preference_reason !== "string" || !candidate.preference_reason.trim() || candidate.preference_reason.length > 500
        || !isVerifiedEventTalkOpportunity(candidate.talk_opportunity)
        || !isVerifiedGroundedTalkPack(candidate.talk_pack)
        || !providerState || providerState.status !== "provider_verified"
        || !RECEIPT.test(String(providerState.receipt_ref || ""))) unavailable();
      const identity = {
        event_ref: candidate.event_ref,
        application_url: candidate.talk_opportunity.application_url,
        provider_receipt_ref: providerState.receipt_ref,
      };
      const key = digest(identity);
      const directory = path.join(stateDir, "talk-applied-bundles");
      const file = path.join(directory, `${key}.json`);
      if (fs.existsSync(file)) {
        let existing;
        try { existing = JSON.parse(fs.readFileSync(file, "utf8")); } catch { unavailable(); }
        const { bundle_id: existingBundleId, ...existingCore } = existing || {};
        if (!existing || existing.identity_sha256 !== key || existingBundleId !== `talk-applied-bundle:${digest(existingCore)}`) unavailable();
        persistTalkTransitions(stateDir, talkTransitions(candidate, providerState, key, existing.created_at));
        return Object.freeze({ status: "applied_bundle", bundle_id: existing.bundle_id, completion_disposition: "reused" });
      }
      const observed = now();
      if (!(observed instanceof Date) || !Number.isFinite(observed.getTime())) unavailable();
      const observedAt = observed.toISOString();
      persistTalkTransitions(stateDir, talkTransitions(candidate, providerState, key, observedAt));
      const core = {
        schema_version: 1,
        kind: "talk_application",
        identity_sha256: key,
        provider: candidate.provider,
        event_ref: candidate.event_ref,
        application_url: candidate.talk_opportunity.application_url,
        talk_format: candidate.talk_opportunity.talk_format,
        talk_state: "provider_verified",
        provider_receipt_ref: providerState.receipt_ref,
        priority_class: candidate.priority_class,
        preference_reason: candidate.preference_reason.trim(),
        application_deadline_at: candidate.application_deadline_at || null,
        talk_pack_sha256: digest(candidate.talk_pack),
        created_at: observedAt,
      };
      const bundle = Object.freeze({ ...core, bundle_id: `talk-applied-bundle:${digest(core)}` });
      try {
        fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
        fs.chmodSync(directory, 0o700);
        fs.writeFileSync(file, `${JSON.stringify(bundle)}\n`, { encoding: "utf8", mode: 0o600, flag: "wx" });
        fs.chmodSync(file, 0o600);
      } catch { unavailable(); }
      return Object.freeze({ status: "applied_bundle", bundle_id: bundle.bundle_id, completion_disposition: "created" });
    },
  });
}

module.exports = { createTalkEvidenceChain };
