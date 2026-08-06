"use strict";

const { createHash } = require("node:crypto");
const { buildRuntimeJob } = require("./runtime-job-store.js");
const { canonicalEventUrl } = require("./canonical-event-url.js");
const { verifyOutboundEvidence } = require("./outbound-evidence.js");
const { buildVerifiedOutboundReceipt } = require("./outbound-success.js");

const CAPABILITY = "outbound.event.apply";
const LOOP_ID = "outbound.events";
const EVENT_REF = /^connpass-event:\/\/event\/([1-9][0-9]*)\?starts_at=(.+)$/;
const EFFECT_KEY = /^event-application:connpass:([1-9][0-9]*):([0-9a-f]{64})$/;
const IDENTITY = /^identity:\/\/[a-z0-9._-]+\/[a-z0-9._-]+$/i;
const BROWSER = "browser-profile://cloakbrowser/daily-driver";
const CALENDAR = /^calendar:\/\/google\/[a-z0-9._-]+$/i;

class ConnpassRsvpError extends Error {
  constructor(message, code, unknownEffect = false) {
    super(message); this.code = code; this.unknownEffect = unknownEffect;
  }
}
function required(value) {
  const text = String(value || "").trim();
  if (!text) throw new Error("Connpass RSVP job contract invalid");
  return text;
}
function connpassUrl(value) {
  const url = canonicalEventUrl(value);
  if (!url) throw new Error("Connpass RSVP job contract invalid");
  const parsed = new URL(url);
  const match = /^\/event\/([1-9][0-9]*)\/$/.exec(parsed.pathname);
  if (!(parsed.hostname === "connpass.com" || parsed.hostname.endsWith(".connpass.com")) || !match) {
    throw new Error("Connpass RSVP job contract invalid");
  }
  return { url, eventId: match[1] };
}
function start(value) {
  const text = required(value);
  if (!Number.isFinite(Date.parse(text)) || !/[zZ]|[+-]\d\d:\d\d$/.test(text)) {
    throw new Error("Connpass RSVP job contract invalid");
  }
  return new Date(Date.parse(text)).toISOString();
}

function buildConnpassEventApplicationJob(input = {}) {
  const tenantId = required(input.tenantId);
  const event = connpassUrl(input.eventUrl);
  const startsAt = start(input.eventStartIso);
  const identityRef = required(input.identityRef);
  const browserProfileRef = required(input.browserProfileRef);
  const calendarRef = required(input.calendarRef);
  if (!IDENTITY.test(identityRef) || browserProfileRef !== BROWSER || !CALENDAR.test(calendarRef)) {
    throw new Error("Connpass RSVP job contract invalid");
  }
  const eventRef = `connpass-event://event/${event.eventId}?starts_at=${encodeURIComponent(startsAt)}`;
  const digest = createHash("sha256").update(`${tenantId}\n${eventRef}\n${event.url}\n${identityRef}`, "utf8").digest("hex");
  return buildRuntimeJob({
    jobId: `outbound-event:${digest}`, tenantId, loopId: LOOP_ID, capability: CAPABILITY,
    effectClass: "publish", effectKey: `event-application:connpass:${event.eventId}:${digest}`,
    inputRefs: {
      event_ref: eventRef, canonical_url_ref: event.url, identity_ref: identityRef,
      browser_profile_ref: browserProfileRef, calendar_ref: calendarRef,
    },
    maxAttempts: 5,
  });
}

function jobContract(job) {
  const refs = job && job.input_refs;
  const event = EVENT_REF.exec(String(refs && refs.event_ref || ""));
  const effect = EFFECT_KEY.exec(String(job && job.effect_key || ""));
  const canonical = connpassUrl(refs && refs.canonical_url_ref);
  if (
    !event || !effect || event[1] !== effect[1] || event[1] !== canonical.eventId
    || !IDENTITY.test(String(refs.identity_ref || "")) || refs.browser_profile_ref !== BROWSER
    || !CALENDAR.test(String(refs.calendar_ref || "")) || job.capability !== CAPABILITY
    || job.loop_id !== LOOP_ID || job.effect_class !== "publish"
  ) throw new Error("Connpass RSVP job contract invalid");
  const startsAt = start(decodeURIComponent(event[2]));
  const expected = buildConnpassEventApplicationJob({
    tenantId: job.tenant_id, eventUrl: canonical.url, eventStartIso: startsAt,
    identityRef: refs.identity_ref, browserProfileRef: refs.browser_profile_ref,
    calendarRef: refs.calendar_ref,
  });
  for (const key of ["job_id", "effect_key", "max_attempts"]) {
    if (job[key] !== expected[key]) throw new Error("Connpass RSVP job contract invalid");
  }
  return Object.freeze({
    tenant_id: job.tenant_id, job_id: job.job_id, attempt: job.attempt,
    effect_key: job.effect_key, event_ref: `connpass-event://event/${event[1]}`,
    canonical_url: canonical.url, starts_at: startsAt,
    identity_ref: refs.identity_ref, browser_profile_ref: refs.browser_profile_ref,
    calendar_ref: refs.calendar_ref,
  });
}
function attemptRef(contract) {
  return `runtime-attempt://${contract.tenant_id}/${contract.job_id}/${contract.attempt}`;
}
async function receipt(contract, proof, deps) {
  const evidence = await verifyOutboundEvidence({
    tenantId: contract.tenant_id, attemptRef: attemptRef(contract),
    externalReceiptRef: proof && proof.external_receipt_ref,
    artifactRef: proof && proof.artifact_ref, canonicalUrl: proof && proof.canonical_url,
  }, deps);
  return buildVerifiedOutboundReceipt({
    tenantId: contract.tenant_id, jobId: contract.job_id, attempt: contract.attempt,
    verifiedAt: typeof deps.now === "function" ? deps.now() : undefined,
  }, evidence);
}

async function executeConnpassRsvpJob(job, deps = {}) {
  const contract = jobContract(job);
  const provider = deps.provider;
  if (!provider || typeof provider.inspectRegistration !== "function"
    || typeof provider.submitRegistration !== "function") throw new Error("Connpass RSVP provider unavailable");
  const before = await provider.inspectRegistration(contract);
  if (!before || !["absent", "registered", "login_required", "unavailable", "unknown"].includes(before.state)) {
    throw new Error("Connpass RSVP effect fence invalid");
  }
  if (before.state === "login_required") throw new ConnpassRsvpError("Connpass login required", "CONNPASS_LOGIN_REQUIRED", false);
  if (before.state === "unavailable") throw new ConnpassRsvpError("Connpass registration unavailable", "CONNPASS_RSVP_UNAVAILABLE", false);
  if (before.state === "unknown") throw new ConnpassRsvpError("Connpass effect unknown", "CONNPASS_EFFECT_UNKNOWN", true);
  let proof = before;
  let effectStarted = false;
  if (before.state === "absent") {
    effectStarted = true;
    try { proof = await provider.submitRegistration(contract); }
    catch (error) {
      if (error && typeof error.unknownEffect === "boolean") throw error;
      throw new ConnpassRsvpError("Connpass submit unknown", "CONNPASS_EFFECT_UNKNOWN", true);
    }
  }
  try { return Object.freeze({ receipt: await receipt(contract, proof, deps), effect_started: effectStarted }); }
  catch { throw new ConnpassRsvpError("Connpass evidence unknown", "CONNPASS_EFFECT_UNKNOWN", true); }
}

function createConnpassRsvpLoopAdapter(deps = {}) {
  return Object.freeze({
    plan: async (context) => [buildConnpassEventApplicationJob(context)],
    execute: (job, services = {}) => executeConnpassRsvpJob(job, { ...deps, ...services }),
    async reconcile(effect) {
      const match = EFFECT_KEY.exec(String(effect && effect.effectKey || ""));
      if (!match || !deps.provider) return { state: "unknown" };
      const proof = await deps.provider.inspectRegistration({
        tenant_id: effect.tenantId, job_id: effect.jobId, attempt: effect.attempt,
        event_ref: `connpass-event://event/${match[1]}`, canonical_url: effect.canonicalUrl,
      });
      if (!proof || ["unknown", "login_required"].includes(proof.state)) return { state: "unknown" };
      if (["absent", "unavailable"].includes(proof.state)) return { state: "absent" };
      return { state: "present" };
    },
  });
}

module.exports = {
  buildConnpassEventApplicationJob,
  createConnpassRsvpLoopAdapter,
  executeConnpassRsvpJob,
};
