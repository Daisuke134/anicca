"use strict";

const { createHash } = require("node:crypto");

const { canonicalEventUrl } = require("./canonical-event-url.js");

const EVENT_REF = /^[a-z][a-z0-9+.-]*:\/\/[a-z0-9._~:/?=&%-]{3,500}$/i;
const RECEIPT_REF = /^[a-z][a-z0-9+.-]*:\/\/[^\s]{3,500}$/i;
const KINDS = Object.freeze(["audience_registration", "talk_application"]);
const AUDIENCE_TRANSITIONS = Object.freeze({
  discovered: Object.freeze(["queued", "unavailable"]),
  queued: Object.freeze(["registered", "unavailable"]),
  registered: Object.freeze(["cancelled"]),
  unavailable: Object.freeze([]),
  cancelled: Object.freeze([]),
});
const TALK_TRANSITIONS = Object.freeze({
  discovered: Object.freeze(["drafted", "closed"]),
  drafted: Object.freeze(["submitted", "closed"]),
  submitted: Object.freeze(["accepted", "rejected", "withdrawn"]),
  accepted: Object.freeze(["presented", "withdrawn"]),
  rejected: Object.freeze([]),
  withdrawn: Object.freeze([]),
  presented: Object.freeze([]),
  closed: Object.freeze([]),
});
const RECEIPT_REQUIRED = new Set(["registered", "submitted", "accepted", "rejected", "presented"]);

function invalid(label = "contract") {
  throw new Error(`event entity ${label} invalid`);
}

function bounded(value, max, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text || text.length > max) invalid(label);
  return text;
}

function instant(value, label) {
  const text = bounded(value, 80, label);
  const time = Date.parse(text);
  if (!Number.isFinite(time) || !/[zZ]|[+-]\d\d:\d\d$/.test(text)) invalid(label);
  return new Date(time).toISOString();
}

function applicationUrl(value) {
  let url;
  try { url = new URL(String(value || "").trim()); } catch { invalid("application URL"); }
  if (url.protocol !== "https:" || url.username || url.password || !url.hostname.includes(".")) {
    invalid("application URL");
  }
  url.hash = "";
  return url.toString();
}

function entityId(tenantId, eventRef, kind, discriminator = "") {
  const hash = createHash("sha256")
    .update(`${tenantId}\n${eventRef}\n${kind}\n${discriminator}`, "utf8")
    .digest("hex");
  return `event-entity:${hash}`;
}

function makeEntity({ tenantId, eventRef, canonicalUrl, startsAt, kind, payload, discriminator }) {
  return Object.freeze({
    schema_version: 1,
    entity_id: entityId(tenantId, eventRef, kind, discriminator),
    tenant_id: tenantId,
    kind,
    event_ref: eventRef,
    canonical_url: canonicalUrl,
    status: "discovered",
    payload: Object.freeze({ starts_at: startsAt, ...payload }),
    version: 1,
  });
}

function buildEventParticipationEntities(input = {}) {
  const tenantId = bounded(input.tenantId, 128, "tenant");
  const eventRef = bounded(input.eventRef, 500, "event ref");
  if (!EVENT_REF.test(eventRef)) invalid("event ref");
  const canonicalUrl = canonicalEventUrl(input.canonicalUrl);
  if (!canonicalUrl) invalid("canonical URL");
  const startsAt = instant(input.startsAt, "start time");
  const decision = input.decision;
  if (!decision || typeof decision !== "object" || Array.isArray(decision)) invalid("decision");
  const participationKind = String(decision.participation_kind || "");
  const audience = participationKind === "audience_only" || participationKind === "both";
  const talk = decision.should_create_talk_application === true
    && ["talk_application", "both"].includes(participationKind)
    && decision.application_status === "open"
    && typeof decision.talk_format === "string";
  const entities = [];
  if (audience) {
    entities.push(makeEntity({
      tenantId,
      eventRef,
      canonicalUrl,
      startsAt,
      kind: "audience_registration",
      payload: {},
      discriminator: "audience",
    }));
  }
  if (talk) {
    const url = applicationUrl(decision.application_url);
    const format = bounded(decision.talk_format, 40, "talk format");
    entities.push(makeEntity({
      tenantId,
      eventRef,
      canonicalUrl,
      startsAt,
      kind: "talk_application",
      payload: { application_url: url, talk_format: format },
      discriminator: `${format}\n${url}`,
    }));
  }
  return Object.freeze(entities);
}

function transitionEventEntity(entity, toStatus, options = {}) {
  if (
    !entity
    || entity.schema_version !== 1
    || !KINDS.includes(entity.kind)
    || !/^event-entity:[0-9a-f]{64}$/.test(String(entity.entity_id || ""))
    || !Number.isInteger(entity.version)
    || entity.version < 1
  ) invalid("transition");
  const transitions = entity.kind === "audience_registration"
    ? AUDIENCE_TRANSITIONS
    : TALK_TRANSITIONS;
  const fromStatus = String(entity.status || "");
  const next = String(toStatus || "");
  if (!transitions[fromStatus] || !transitions[fromStatus].includes(next)) invalid("transition");
  const at = instant(options.at, "transition");
  const receiptRef = options.receiptRef == null ? null : String(options.receiptRef).trim();
  if (RECEIPT_REQUIRED.has(next) && !RECEIPT_REF.test(receiptRef || "")) invalid("transition");
  if (!RECEIPT_REQUIRED.has(next) && receiptRef !== null) invalid("transition");
  const version = entity.version + 1;
  return Object.freeze({
    entity: Object.freeze({ ...entity, status: next, version }),
    transition: Object.freeze({
      entity_id: entity.entity_id,
      tenant_id: entity.tenant_id,
      kind: entity.kind,
      from_status: fromStatus,
      to_status: next,
      version,
      occurred_at: at,
      receipt_ref: receiptRef,
    }),
  });
}

module.exports = {
  buildEventParticipationEntities,
  transitionEventEntity,
};
