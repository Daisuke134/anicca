"use strict";

const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const { isVerifiedEventTalkOpportunity } = require("./event-talk-opportunity.js");
const { isVerifiedGroundedTalkPack } = require("./grounded-talk-pack.js");

const REF = /^[a-z][a-z0-9_-]+-event:\/\/event\/[A-Za-z0-9_-]+$/;
const RECEIPT = /^provider-receipt:\/\/[a-z0-9._~:/?#@!$&'()*+,;=%-]{1,950}$/i;

function unavailable() { throw new Error("talk evidence unavailable"); }
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
function digest(value) { return createHash("sha256").update(stable(value), "utf8").digest("hex"); }

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
        return Object.freeze({ status: "applied_bundle", bundle_id: existing.bundle_id, completion_disposition: "reused" });
      }
      const observed = now();
      if (!(observed instanceof Date) || !Number.isFinite(observed.getTime())) unavailable();
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
        created_at: observed.toISOString(),
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
