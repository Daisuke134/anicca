"use strict";

const crypto = require("node:crypto");
const { MobileError, canonicalJson, sha256 } = require("./mobile-utils.js");

const GOOGLE_EVENT_ID = /^[a-v0-9]{5,1024}$/u;
const LEG_SET = new Set(["go", "return"]);
const DEFAULT_LEASE_SECONDS = 120;

function text(value, field, { required = false, max = 2048 } = {}) {
  if (value == null && !required) return "";
  const output = String(value == null ? "" : value).replace(/\s+/gu, " ").trim();
  if ((required && !output) || output.length > max || /[\x00-\x1f\x7f]/u.test(output)) {
    throw new MobileError("travel_block_invalid", `Invalid ${field}.`);
  }
  return output;
}

function datePart(value, timezone, field) {
  const source = value && typeof value === "object" ? value : { dateTime: value };
  const dateTime = text(source.dateTime || source.date_time, `${field}.dateTime`, { required: true, max: 128 });
  if (!Number.isFinite(Date.parse(dateTime)) || !/(?:Z|[+-]\d\d:\d\d)$/u.test(dateTime)) {
    throw new MobileError("travel_block_invalid", `Invalid ${field}.dateTime.`);
  }
  const timeZone = text(source.timeZone || source.timezone || timezone, `${field}.timeZone`, { max: 128 });
  return timeZone ? { dateTime, timeZone } : { dateTime };
}

function normalizeTravelPayload(payload = {}) {
  const timezone = text(payload.timezone || payload.timeZone, "timezone", { max: 128 });
  const start = datePart(payload.start || payload.startDateTime || payload.start_datetime, timezone, "start");
  const end = datePart(payload.end || payload.endDateTime || payload.end_datetime, timezone, "end");
  if (Date.parse(end.dateTime) <= Date.parse(start.dateTime)) throw new MobileError("travel_block_invalid", "Travel block end must be after start.");
  return {
    summary: text(payload.summary, "summary", { required: true, max: 500 }),
    description: text(payload.description, "description", { max: 8_000 }),
    location: text(payload.location, "location", { max: 2_000 }),
    start,
    end,
  };
}

function canonicalTravelPayload(payload = {}) {
  const normalized = normalizeTravelPayload(payload);
  return { value: normalized, hash: sha256(canonicalJson(normalized)) };
}

function deriveTravelProviderEventId({ secret, serverSecret, uid, calendarId = "primary", sourceEventId, leg } = {}) {
  const key = String(secret || serverSecret || "");
  if (!key) throw new MobileError("travel_block_config_invalid", "Travel block server secret is not configured.", 503, true);
  const user = text(uid, "uid", { required: true, max: 512 });
  const calendar = text(calendarId, "calendarId", { required: true, max: 1024 });
  const source = text(sourceEventId, "sourceEventId", { required: true, max: 1024 });
  if (!LEG_SET.has(String(leg))) throw new MobileError("travel_block_invalid", "Travel leg is invalid.");
  const digest = crypto.createHmac("sha256", key).update(`${user}\u0000${calendar}\u0000${source}\u0000${leg}`).digest("hex");
  const id = `lm${digest}`;
  if (!GOOGLE_EVENT_ID.test(id)) throw new MobileError("travel_block_invalid", "Generated provider event ID is invalid.", 500);
  return id;
}

function validateGoogleEventId(value) {
  const id = text(value, "providerEventId", { required: true, max: 1024 });
  if (!GOOGLE_EVENT_ID.test(id)) throw new MobileError("travel_block_invalid", "Provider event ID is invalid.");
  return id;
}

function deriveTravelMarker(providerEventId, payloadHash) {
  const id = validateGoogleEventId(providerEventId);
  const hash = text(payloadHash, "payloadHash", { required: true, max: 64 });
  if (!/^[0-9a-f]{64}$/u.test(hash)) throw new MobileError("travel_block_invalid", "Payload hash is invalid.");
  // Private extended-property values are bounded, opaque, and contain no
  // title, address, email, provider account, or other user content.
  return `lm_travel_v1_${sha256(`${id}\u0000${hash}`)}`;
}

function providerEventData(response) {
  if (!response || typeof response !== "object") return null;
  const data = response.data;
  if (data && typeof data === "object" && data.data && typeof data.data === "object") return data.data;
  return data && typeof data === "object" ? data : null;
}

function providerPayload(event) {
  if (!event || typeof event !== "object") return null;
  try {
    return normalizeTravelPayload({
      summary: event.summary,
      description: event.description,
      location: event.location,
      start: event.start,
      end: event.end,
    });
  } catch {
    return null;
  }
}

function privateMarker(event) {
  const privateValues = event && event.extendedProperties && event.extendedProperties.private;
  const legacyValues = event && event.extended_properties && event.extended_properties.private;
  const values = privateValues && typeof privateValues === "object" ? privateValues : legacyValues;
  if (!values || typeof values !== "object") return null;
  return values.lm_travel_block || values.life_manager_travel_block || values.lmTravelBlock || null;
}

function providerEventMatches(response, { providerEventId, marker, payloadHash } = {}) {
  const event = providerEventData(response);
  if (!event || event.id !== providerEventId || privateMarker(event) !== marker) return { matched: false, event: null, etag: null };
  const payload = providerPayload(event);
  const matched = Boolean(payload && sha256(canonicalJson(payload)) === payloadHash);
  return { matched, event: matched ? event : null, etag: response && response.headers && (response.headers.etag || response.headers.ETag) || event.etag || null };
}

function statusOf(response) {
  const value = Number(response && response.status);
  return Number.isFinite(value) ? value : 0;
}

function nowIso(deps = {}) {
  const raw = typeof deps.now === "function" ? deps.now() : deps.nowMs;
  const ms = raw instanceof Date ? raw.getTime() : Number(raw);
  return new Date(Number.isFinite(ms) ? ms : Date.now()).toISOString();
}

function rowFrom(result) {
  return result && result.row && typeof result.row === "object" ? result.row : result || {};
}

function output(input, facts = {}) {
  const { composioUserId: _composioUserId, connectedAccountId: _connectedAccountId, ...safeFacts } = facts;
  return {
    uid: input.uid,
    sourceEventId: input.sourceEventId || input.source_event_id,
    eventKey: input.eventKey || input.event_key,
    leg: input.leg,
    calendarId: input.calendarId || input.calendar_id || "primary",
    providerEventId: facts.providerEventId,
    marker: facts.marker,
    payloadHash: facts.payloadHash,
    ...safeFacts,
  };
}

function boundedProviderErrorCode(error, fallback) {
  const code = error && (error.code || error.errorCode || error.error_code);
  if (code === "budget_denied") return "budget_denied";
  if (code === "provider_binding_invalid") return "provider_binding_invalid";
  return fallback;
}

async function exactGet(provider, input, facts) {
  try {
    const response = await provider.getExactEvent(input.uid, {
      calendarId: facts.calendarId,
      providerEventId: facts.providerEventId,
      connectedAccountId: facts.connectedAccountId,
      composioUserId: facts.composioUserId,
      marker: facts.marker,
    });
    return { response, status: statusOf(response), match: providerEventMatches(response, facts) };
  } catch (error) {
    return { response: null, status: 0, errorCode: boundedProviderErrorCode(error, "provider_readback_failed"), match: { matched: false, event: null, etag: null } };
  }
}

async function release(store, input, token, errorCode, currentNow) {
  if (!token || !store || typeof store.releaseTravelClaim !== "function") return null;
  try {
    return await store.releaseTravelClaim({
      uid: input.uid, eventKey: input.eventKey || input.event_key, leg: input.leg,
      claimToken: token, errorCode, now: currentNow,
    });
  } catch {
    return null;
  }
}

async function ensureMobileTravelBlock(input = {}, deps = {}) {
  const store = deps.store;
  const provider = deps.provider || deps.calendar;
  if (!store || typeof store.claimTravelBlock !== "function") throw new MobileError("travel_block_unavailable", "Travel block storage is unavailable.", 503, true);
  if (!provider || typeof provider.getExactEvent !== "function" || typeof provider.createExactEvent !== "function") throw new MobileError("travel_block_unavailable", "Travel block provider is unavailable.", 503, true);
  const eventKey = text(input.eventKey || input.event_key || input.sourceEventId || input.source_event_id, "eventKey", { required: true, max: 1024 });
  const sourceEventId = text(input.sourceEventId || input.source_event_id || eventKey, "sourceEventId", { required: true, max: 1024 });
  const uid = text(input.uid, "uid", { required: true, max: 512 });
  const leg = String(input.leg || "");
  if (!LEG_SET.has(leg)) throw new MobileError("travel_block_invalid", "Travel leg is invalid.");
  const calendarId = text(input.calendarId || input.calendar_id || "primary", "calendarId", { required: true, max: 1024 });
  const analysisKey = text(input.analysisKey || input.analysis_key, "analysisKey", { required: true, max: 1024 });
  const composioUserId = text(input.composioUserId || input.composio_user_id || input.calendarComposioUserId, "composioUserId", { max: 1024 });
  const connectedAccountId = text(input.connectedAccountId || input.connected_account_id || input.gmailAccountId, "connectedAccountId", { max: 1024 });
  const payload = canonicalTravelPayload(input.payload || input.event || {});
  const providerEventId = deriveTravelProviderEventId({ secret: deps.serverSecret || deps.secret || input.serverSecret, uid, calendarId, sourceEventId, leg });
  const marker = deriveTravelMarker(providerEventId, payload.hash);
  const currentNow = nowIso(deps);
  const facts = { calendarId, providerEventId, marker, payloadHash: payload.hash, composioUserId, connectedAccountId };
  if (!composioUserId || !connectedAccountId) {
    return output(input, { ...facts, status: "provider_binding_invalid", errorCode: "provider_binding_invalid" });
  }
  const claim = await store.claimTravelBlock({
    uid, eventKey, leg, calendarId, analysisKey, payloadHash: payload.hash, marker, providerEventId, composioUserId, connectedAccountId,
    claimWorkerId: input.workerId || input.claimWorkerId || deps.workerId || "mobile",
    leaseSeconds: input.leaseSeconds == null ? DEFAULT_LEASE_SECONDS : input.leaseSeconds,
    now: currentNow,
  });
  const row = rowFrom(claim);
  const decision = claim && (claim.decision || claim.status || row.status);
  if (decision === "analysis_conflict") return output(input, { ...facts, status: "analysis_conflict", errorCode: "analysis_conflict" });
  if (decision === "legacy_terminal") return output(input, { ...facts, status: "legacy_terminal", errorCode: "legacy_terminal" });
  if (decision === "busy") return output(input, { ...facts, status: "busy", errorCode: "claim_pending" });
  if (decision === "blocked_collision" || row.status === "blocked_collision") return output(input, { ...facts, status: "provider_collision", errorCode: "provider_collision" });
  if (decision === "provider_binding_invalid") return output(input, { ...facts, status: "provider_binding_invalid", errorCode: "provider_binding_invalid" });
  if (decision === "reused" || row.status === "confirmed") return output(input, { ...facts, status: "existing", verifiedAt: row.confirmedAt || row.confirmed_at || null });
  const claimToken = row.claimToken || row.claim_token;
  if (decision !== "claimed" || !claimToken) return output(input, { ...facts, status: "claim_pending", errorCode: "claim_pending" });

  const durableComposioUserId = text(row.composioUserId || row.composio_user_id, "storedComposioUserId", { required: true, max: 1024 });
  const durableConnectedAccountId = text(row.connectedAccountId || row.connected_account_id, "storedConnectedAccountId", { required: true, max: 1024 });
  if (durableComposioUserId !== composioUserId || durableConnectedAccountId !== connectedAccountId) {
    return output(input, { ...facts, status: "provider_binding_invalid", errorCode: "provider_binding_invalid" });
  }
  const boundFacts = { ...facts, composioUserId: durableComposioUserId, connectedAccountId: durableConnectedAccountId };

  const before = await exactGet(provider, { ...input, uid, eventKey }, boundFacts);
  if (before.match.matched) {
    const confirmed = await store.confirmTravelBlock({ uid, eventKey, leg, claimToken, providerEtag: before.match.etag, providerObservedAt: currentNow, now: currentNow });
    if (confirmed && confirmed.confirmed === false) return output(input, { ...facts, status: "claim_pending", errorCode: "claim_pending" });
    return output(input, { ...facts, status: "existing", verifiedAt: currentNow, providerEtag: before.match.etag || null });
  }
  // A successful GET for the deterministic id that carries another marker or
  // payload is already an ID collision.  Do not release and do not mint a
  // second id; the durable collision state is the only safe terminal result.
  if (before.status >= 200 && before.status < 300) {
    await store.blockTravelCollision({ uid, eventKey, leg, claimToken, errorCode: "provider_collision", now: currentNow });
    return output(input, { ...facts, status: "provider_collision", errorCode: "provider_collision" });
  }
  if (before.status !== 404) {
    const errorCode = before.errorCode || "provider_readback_failed";
    await release(store, { ...input, uid, eventKey }, claimToken, errorCode, currentNow);
    return output(input, { ...facts, status: errorCode, errorCode });
  }

  const started = await store.markTravelCreateStarted({ uid, eventKey, leg, claimToken, now: currentNow });
  if (!started || started.started !== true) return output(input, { ...facts, status: "claim_pending", errorCode: "claim_pending" });
  const body = {
    id: providerEventId,
    summary: payload.value.summary,
    description: payload.value.description || undefined,
    location: payload.value.location || undefined,
    start: payload.value.start,
    end: payload.value.end,
    extendedProperties: { private: { lm_travel_block: marker } },
  };
  let created;
  let postErrorCode = null;
  try {
    created = await provider.createExactEvent(uid, {
      calendarId, providerEventId, connectedAccountId: durableConnectedAccountId,
      composioUserId: durableComposioUserId, body, marker,
    });
  } catch (error) {
    postErrorCode = boundedProviderErrorCode(error, "provider_write_failed");
    created = { status: 0, data: null };
  }
  // Every POST outcome, including timeout and 5xx, converges through one exact
  // GET.  No POST response alone can become a success receipt.
  const postStatus = statusOf(created);
  const after = await exactGet(provider, { ...input, uid, eventKey }, boundFacts);
  if (after.match.matched) {
    const confirmed = await store.confirmTravelBlock({ uid, eventKey, leg, claimToken, providerEtag: after.match.etag, providerObservedAt: currentNow, now: currentNow });
    if (confirmed && confirmed.confirmed === false) return output(input, { ...facts, status: "claim_pending", errorCode: "claim_pending" });
    return output(input, { ...facts, status: postStatus >= 200 && postStatus < 300 ? "created" : "existing", verifiedAt: currentNow, providerEtag: after.match.etag || null });
  }
  if (postStatus === 409 && after.status >= 200 && after.status < 300) {
    await store.blockTravelCollision({ uid, eventKey, leg, claimToken, errorCode: "provider_collision", now: currentNow });
    return output(input, { ...facts, status: "provider_collision", errorCode: "provider_collision" });
  }
  const errorCode = postErrorCode === "budget_denied" || after.errorCode === "budget_denied" ? "budget_denied"
    : after.status !== 404 ? "provider_readback_failed"
      : postErrorCode || (postStatus >= 400 || postStatus === 0 ? "provider_write_failed" : "provider_readback_failed");
  await release(store, { ...input, uid, eventKey }, claimToken, errorCode, currentNow);
  return output(input, { ...facts, status: errorCode, errorCode });
}

module.exports = {
  GOOGLE_EVENT_ID,
  DEFAULT_LEASE_SECONDS,
  canonicalTravelPayload,
  deriveTravelProviderEventId,
  deriveProviderEventId: deriveTravelProviderEventId,
  validateGoogleEventId,
  deriveTravelMarker,
  providerEventMatches,
  ensureMobileTravelBlock,
  ensureTravelBlock: ensureMobileTravelBlock,
  createTravelBlock: ensureMobileTravelBlock,
};
