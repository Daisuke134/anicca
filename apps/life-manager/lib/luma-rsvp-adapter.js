"use strict";

const {
  buildEventApplicationJob,
  CAPABILITY,
  LOOP_ID,
} = require("./outbound-event-job.js");
const { verifyOutboundEvidence } = require("./outbound-evidence.js");
const {
  assertVerifiedOutboundReceipt,
  buildVerifiedOutboundReceipt,
} = require("./outbound-success.js");

const ADAPTER_ID = "outbound-luma-rsvp";
const EVENT_REF = /^luma-event:\/\/event\/([A-Za-z0-9_-]+)\?starts_at=(.+)$/;
const EFFECT_KEY = /^event-application:luma:([A-Za-z0-9_-]+):([0-9a-f]{64})$/;
const IDENTITY_REF = /^identity:\/\/[a-z0-9._-]+\/[a-z0-9._-]+$/i;
const BROWSER_REF = "browser-profile://cloakbrowser/daily-driver";
const CALENDAR_REF = /^calendar:\/\/google\/[a-z0-9._-]+$/i;

class LumaRsvpError extends Error {
  constructor(message, code, unknownEffect = false) {
    super(message);
    this.name = "LumaRsvpError";
    this.code = code;
    this.unknownEffect = unknownEffect;
  }
}

function jobContract(job) {
  const refs = job && job.input_refs;
  const keys = refs && typeof refs === "object" && !Array.isArray(refs)
    ? Object.keys(refs).sort()
    : [];
  if (
    !job
    || job.capability !== CAPABILITY
    || job.loop_id !== LOOP_ID
    || job.effect_class !== "publish"
    || JSON.stringify(keys) !== JSON.stringify([
      "browser_profile_ref",
      "calendar_ref",
      "event_ref",
      "identity_ref",
    ])
  ) {
    throw new Error("Luma RSVP job contract invalid");
  }
  const event = EVENT_REF.exec(String(refs.event_ref || ""));
  const effect = EFFECT_KEY.exec(String(job.effect_key || ""));
  if (
    !event
    || !effect
    || event[1] !== effect[1]
    || !IDENTITY_REF.test(String(refs.identity_ref || ""))
    || refs.browser_profile_ref !== BROWSER_REF
    || !CALENDAR_REF.test(String(refs.calendar_ref || ""))
  ) {
    throw new Error("Luma RSVP job contract invalid");
  }
  const startsAt = decodeURIComponent(event[2]);
  const expected = buildEventApplicationJob({
    tenantId: job.tenant_id,
    eventUrl: `https://luma.com/${event[1]}`,
    eventStartIso: startsAt,
    identityRef: refs.identity_ref,
    browserProfileRef: refs.browser_profile_ref,
    calendarRef: refs.calendar_ref,
  });
  for (const key of [
    "job_id",
    "tenant_id",
    "loop_id",
    "capability",
    "effect_class",
    "effect_key",
    "max_attempts",
  ]) {
    if (job[key] !== expected[key]) throw new Error("Luma RSVP job contract invalid");
  }
  return Object.freeze({
    tenant_id: job.tenant_id,
    job_id: job.job_id,
    attempt: job.attempt,
    effect_key: job.effect_key,
    event_ref: `luma-event://event/${event[1]}`,
    canonical_url: `https://luma.com/${event[1]}`,
    starts_at: new Date(Date.parse(startsAt)).toISOString(),
    identity_ref: refs.identity_ref,
    browser_profile_ref: refs.browser_profile_ref,
    calendar_ref: refs.calendar_ref,
  });
}

function attemptRef(contract) {
  return `runtime-attempt://${contract.tenant_id}/${contract.job_id}/${contract.attempt}`;
}

function unknown(error, message) {
  const value = error instanceof Error ? error : new Error(message);
  value.unknownEffect = true;
  return value;
}

async function verifiedReceipt(contract, proof, deps) {
  const evidence = await verifyOutboundEvidence({
    tenantId: contract.tenant_id,
    attemptRef: attemptRef(contract),
    externalReceiptRef: proof && proof.external_receipt_ref,
    artifactRef: proof && proof.artifact_ref,
    canonicalUrl: proof && proof.canonical_url,
  }, {
    readExternalReceipt: deps.readExternalReceipt,
    readArtifact: deps.readArtifact,
    fetchImpl: deps.fetchImpl,
  });
  return buildVerifiedOutboundReceipt({
    tenantId: contract.tenant_id,
    jobId: contract.job_id,
    attempt: contract.attempt,
    verifiedAt: typeof deps.now === "function" ? deps.now() : undefined,
  }, evidence);
}

async function executeLumaRsvpJob(job, deps = {}) {
  const contract = jobContract(job);
  const provider = deps.provider;
  if (
    !provider
    || typeof provider.inspectRegistration !== "function"
    || typeof provider.submitRegistration !== "function"
  ) {
    throw new Error("Luma RSVP provider unavailable");
  }
  const before = await provider.inspectRegistration(contract);
  if (!before || ![
    "absent",
    "registered",
    "login_required",
    "unavailable",
    "unknown",
  ].includes(before.state)) {
    throw new Error("Luma RSVP effect fence invalid");
  }
  if (before.state === "login_required") {
    throw new LumaRsvpError("Luma login required", "LUMA_LOGIN_REQUIRED", false);
  }
  if (before.state === "unavailable") {
    throw new LumaRsvpError("Luma RSVP unavailable", "LUMA_RSVP_UNAVAILABLE", false);
  }
  if (before.state === "unknown") {
    throw new LumaRsvpError("Luma registration state unknown", "LUMA_EFFECT_UNKNOWN", true);
  }

  let proof = before;
  let effectStarted = false;
  if (before.state === "absent") {
    effectStarted = true;
    try {
      proof = await provider.submitRegistration(contract);
    } catch (error) {
      if (error && typeof error === "object" && typeof error.unknownEffect === "boolean") {
        throw error;
      }
      throw unknown(error, "Luma RSVP submit failed");
    }
  }
  try {
    const receipt = await verifiedReceipt(contract, proof, deps);
    return Object.freeze({ receipt, effect_started: effectStarted });
  } catch (error) {
    throw unknown(error, "Luma RSVP evidence unavailable");
  }
}

function effectContract(effect = {}) {
  const match = EFFECT_KEY.exec(String(effect.effectKey || ""));
  const attempt = Number(effect.attempt);
  if (
    !match
    || !String(effect.tenantId || "").trim()
    || !String(effect.jobId || "").trim()
    || !Number.isSafeInteger(attempt)
    || attempt < 1
  ) {
    throw new Error("Luma RSVP reconciliation effect invalid");
  }
  return Object.freeze({
    tenant_id: String(effect.tenantId),
    job_id: String(effect.jobId),
    attempt,
    effect_key: String(effect.effectKey),
    event_ref: `luma-event://event/${match[1]}`,
    canonical_url: `https://luma.com/${match[1]}`,
  });
}

function createLumaRsvpLoopAdapter(deps = {}) {
  return Object.freeze({
    async plan(context = {}) {
      return [buildEventApplicationJob(context)];
    },
    execute(job, services = {}) {
      return executeLumaRsvpJob(job, { ...deps, ...services });
    },
    async reconcile(effect) {
      const contract = effectContract(effect);
      if (!deps.provider || typeof deps.provider.inspectRegistration !== "function") {
        return { state: "unknown" };
      }
      const proof = await deps.provider.inspectRegistration(contract);
      if (!proof || proof.state === "unknown" || proof.state === "login_required") {
        return { state: "unknown" };
      }
      if (proof.state === "absent") {
        return {
          state: "absent",
          receipt: {
            kind: "outbound_event_reconciliation",
            status: "absent",
            effect_key: contract.effect_key,
          },
        };
      }
      try {
        return { state: "present", receipt: await verifiedReceipt(contract, proof, deps) };
      } catch {
        return { state: "unknown" };
      }
    },
    verify(receipt, job) {
      try {
        return assertVerifiedOutboundReceipt(receipt, job) === receipt;
      } catch {
        return false;
      }
    },
    report(receipt) {
      if (!receipt || receipt.kind !== "outbound_event_application") {
        throw new Error("Luma RSVP receipt invalid");
      }
      return Object.freeze({
        status: receipt.status,
        canonical_url: receipt.canonical_url,
        verified_at: receipt.verified_at,
      });
    },
  });
}

module.exports = {
  ADAPTER_ID,
  CAPABILITY,
  LOOP_ID,
  createLumaRsvpLoopAdapter,
  executeLumaRsvpJob,
};
