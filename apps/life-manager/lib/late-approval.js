"use strict";

// The late-notice transport must not know how approval is stored.  This module owns the durable
// state machine and exposes a very small boundary: create a snapshot, decide once, claim once, and
// record one provider receipt.  The Supabase implementation below is deliberately an RPC-only
// adapter; no caller can turn a failed read/insert into an optimistic send.

const {
  createHmac,
  randomBytes,
  randomUUID,
  timingSafeEqual,
} = require("node:crypto");
const { isDeepStrictEqual } = require("node:util");

const APPROVAL_STATES = Object.freeze([
  "draft", "awaiting_decision", "send_claimed", "sent", "do_not_send",
  "recipient_missing", "recipient_ambiguous",
]);
const RECIPIENT_STATUSES = new Set(["resolved", "recipient_missing", "recipient_ambiguous"]);
const DECISIONS = new Set(["send", "do_not_send"]);
const DEFAULT_LEASE_MS = 120_000;
const DEFAULT_CALLBACK_TTL_MS = 10 * 60_000;
// Existing late-notice unit tests run without a process env.  Production cards use one of the
// explicit secrets below; this fallback keeps local card construction signed (never plaintext) while
// making it obvious that a deployed service must configure a secret of its own.
const DEVELOPMENT_CALLBACK_SECRET = "lm-late-approval-callback-development-only";
const MAX_BODY_LENGTH = 64_000;
const MAX_JSON_LENGTH = 128_000;

class LateApprovalError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "LateApprovalError";
    this.code = code;
    Object.assign(this, details);
  }
}

function fail(code, message, details) {
  throw new LateApprovalError(code, message, details);
}

function text(value, label, max = 512) {
  const result = String(value == null ? "" : value).trim();
  if (!result || result.length > max) fail("invalid_input", `${label} is required and bounded`);
  return result;
}

function optionalText(value, label, max = 512) {
  if (value == null || value === "") return null;
  return text(value, label, max);
}

function clone(value) {
  if (value === undefined) return undefined;
  return JSON.parse(JSON.stringify(value));
}

function boundedJson(value, label, fallback) {
  const normalized = value === undefined || value === null ? fallback : clone(value);
  if (normalized === undefined) fail("invalid_input", `${label} is required`);
  let encoded;
  try { encoded = JSON.stringify(normalized); } catch { fail("invalid_input", `${label} must be JSON`); }
  if (encoded.length > MAX_JSON_LENGTH) fail("invalid_input", `${label} is too large`);
  return normalized;
}

function finiteNow(value, label = "timestamp") {
  if (value === undefined || value === null) return Date.now();
  const number = typeof value === "number" ? value : Date.parse(String(value));
  if (!Number.isFinite(number)) fail("invalid_input", `${label} is invalid`);
  return number;
}

function iso(value, label = "timestamp") {
  return new Date(finiteNow(value, label)).toISOString();
}

function requiredEmail(value) {
  const candidate = String(value == null ? "" : value).trim().toLowerCase();
  if (!/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(candidate)) {
    fail("invalid_input", "recipient email is invalid");
  }
  return candidate;
}

function normalizeRecipients(value, recipientStatus) {
  const values = value == null ? [] : (Array.isArray(value) ? value : [value]);
  if (recipientStatus === "resolved" && values.length < 1) {
    fail("invalid_input", "a resolved late draft needs at least one recipient");
  }
  return values.map((recipient) => {
    if (!recipient || typeof recipient !== "object" || Array.isArray(recipient)) {
      fail("invalid_input", "recipient snapshot must contain objects");
    }
    const result = clone(recipient);
    result.email = requiredEmail(recipient.email || recipient.email_address || recipient.emailAddress);
    if (result.display_name == null && recipient.displayName != null) result.display_name = String(recipient.displayName);
    if (result.evidence_refs == null && recipient.evidenceRefs != null) result.evidence_refs = clone(recipient.evidenceRefs);
    return result;
  });
}

function normalizeRecipientStatus(input) {
  const raw = input && (input.recipientStatus || input.recipient_status || input.recipientResolution || input.status);
  if (raw === "missing" || raw === "recipient_missing" || raw === "no_recipient") return "recipient_missing";
  if (raw === "ambiguous" || raw === "recipient_ambiguous" || raw === "uncertain") return "recipient_ambiguous";
  if (raw === "resolved") return "resolved";
  if (input && input.recipientMissing === true) return "recipient_missing";
  if (input && input.recipientAmbiguous === true) return "recipient_ambiguous";
  fail("invalid_input", "recipient status is required");
}

function normalizeDraftInput(input = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) fail("invalid_input", "late draft input is required");
  const uid = text(input.uid, "uid", 256);
  const eventKey = text(input.eventKey || input.event_key, "event key", 512);
  const recipientStatus = normalizeRecipientStatus(input);
  const recipients = normalizeRecipients(
    input.recipients ?? input.candidates ?? input.recipientCandidates
      ?? input.recipientSnapshot ?? input.recipient_snapshot ?? input.recipient,
    recipientStatus,
  );
  const evidenceSnapshot = boundedJson(
    input.evidenceSnapshot ?? input.evidence_snapshot ?? input.evidenceRefs ?? input.evidence_refs,
    "evidence snapshot",
    {},
  );
  const bodySnapshot = text(
    input.bodySnapshot ?? input.body_snapshot ?? input.body ?? input.messageBody,
    "body snapshot",
    MAX_BODY_LENGTH,
  );
  const etaEvidence = boundedJson(
    input.etaEvidence ?? input.eta_evidence_snapshot ?? input.etaSnapshot ?? input.eta,
    "ETA evidence",
    {},
  );
  const draftId = optionalText(input.draftId || input.draft_id, "draft id", 128);
  return {
    uid,
    eventKey,
    draftId,
    recipientStatus,
    recipients,
    evidenceSnapshot,
    bodySnapshot,
    etaEvidence,
    nowMs: finiteNow(input.nowMs),
    __nowProvided: Object.prototype.hasOwnProperty.call(input, "nowMs"),
  };
}

function normalizeDecision(value) {
  const raw = String(value == null ? "" : value).trim().toLowerCase();
  if (raw === "send") return "send";
  if (["do_not_send", "dont_send", "don't_send", "do-not-send", "no", "decline"].includes(raw)) {
    return "do_not_send";
  }
  fail("invalid_decision", "late approval decision must be send or do_not_send");
}

function normalizeDecisionInput(input = {}) {
  return {
    uid: text(input.uid, "uid", 256),
    draftId: text(input.draftId || input.draft_id, "draft id", 128),
    decision: normalizeDecision(input.decision),
    idempotencyKey: text(input.idempotencyKey || input.idempotency_key, "idempotency key", 512),
    nowMs: finiteNow(input.nowMs),
    __nowProvided: Object.prototype.hasOwnProperty.call(input, "nowMs"),
  };
}

function normalizeClaimInput(input = {}) {
  const leaseMs = input.leaseMs == null ? DEFAULT_LEASE_MS : Number(input.leaseMs);
  if (!Number.isFinite(leaseMs) || leaseMs < 100 || leaseMs > 900_000) fail("invalid_input", "claim lease is invalid");
  return {
    draftId: text(input.draftId || input.draft_id, "draft id", 128),
    workerId: text(input.workerId || input.worker_id, "worker id", 256),
    leaseMs,
    nowMs: finiteNow(input.nowMs),
    __nowProvided: Object.prototype.hasOwnProperty.call(input, "nowMs"),
  };
}

function normalizeDeliveryInput(input = {}) {
  return {
    uid: text(input.uid, "uid", 256),
    draftId: text(input.draftId || input.draft_id, "draft id", 128),
    providerMessageId: text(input.providerMessageId || input.provider_message_id, "provider message id", 512),
    deliveredAt: iso(input.deliveredAt || input.delivered_at, "deliveredAt"),
    claimToken: text(input.claimToken ?? input.claim_token, "claim token", 512),
    workerId: text(input.workerId ?? input.worker_id, "worker id", 256),
    nowMs: finiteNow(input.nowMs),
    __nowProvided: Object.prototype.hasOwnProperty.call(input, "nowMs"),
  };
}

function exposeRow(row, flags = {}) {
  if (!row) return null;
  const result = { ...clone(row), ...flags };
  // PostgREST returns snake_case and the public JS contract is camelCase.  Non-enumerable aliases
  // keep both forms readable without making exact row comparisons noisy.
  const aliases = {
    draft_id: "draftId", event_key: "eventKey", recipient_status: "recipientStatus",
    recipient_snapshot: "recipients", evidence_snapshot: "evidenceSnapshot",
    body_snapshot: "bodySnapshot", eta_evidence_snapshot: "etaEvidence",
    idempotency_key: "idempotencyKey", claim_token: "claimToken", claim_worker_id: "workerId",
    claim_acquired_at: "claimedAt", claim_expires_at: "claimExpiresAt",
    provider_idempotency_key: "providerIdempotencyKey",
    provider_message_id: "providerMessageId", delivered_at: "deliveredAt",
    created_at: "createdAt", updated_at: "updatedAt",
  };
  for (const [alias, key] of Object.entries(aliases)) {
    if (result[key] !== undefined && result[alias] === undefined) {
      Object.defineProperty(result, alias, { value: result[key], enumerable: false, writable: false });
    }
  }
  return result;
}

function rowFromPersistence(raw) {
  if (!raw) return null;
  if (Array.isArray(raw)) return rowFromPersistence(raw[0]);
  const value = raw.row && typeof raw.row === "object" ? raw.row : raw;
  return {
    draftId: value.draftId ?? value.draft_id,
    uid: value.uid,
    eventKey: value.eventKey ?? value.event_key,
    status: value.status,
    recipientStatus: value.recipientStatus ?? value.recipient_status,
    recipients: clone(value.recipients ?? value.recipient_snapshot ?? []),
    evidenceSnapshot: clone(value.evidenceSnapshot ?? value.evidence_snapshot ?? {}),
    bodySnapshot: value.bodySnapshot ?? value.body_snapshot,
    etaEvidence: clone(value.etaEvidence ?? value.eta_evidence_snapshot ?? {}),
    decision: value.decision ?? null,
    idempotencyKey: value.idempotencyKey ?? value.idempotency_key ?? null,
    providerIdempotencyKey: value.providerIdempotencyKey ?? value.provider_idempotency_key ?? null,
    claimToken: value.claimToken ?? value.claim_token ?? null,
    workerId: value.workerId ?? value.claim_worker_id ?? null,
    claimedAt: value.claimedAt ?? value.claim_acquired_at ?? null,
    claimExpiresAt: value.claimExpiresAt ?? value.claim_expires_at ?? null,
    providerMessageId: value.providerMessageId ?? value.provider_message_id ?? null,
    deliveredAt: value.deliveredAt ?? value.delivered_at ?? null,
    createdAt: value.createdAt ?? value.created_at ?? null,
    updatedAt: value.updatedAt ?? value.updated_at ?? null,
    ...(value.duplicate === true ? { duplicate: true } : {}),
    ...(value.retry === true ? { retry: true } : {}),
    ...(value.recovered === true ? { recovered: true } : {}),
    ...(value.claimed === true ? { claimed: true } : {}),
  };
}

function assertRowId(row) {
  if (!row || !row.draftId) fail("draft_not_found", "late draft was not found");
}

function assertTenant(row, uid) {
  if (row.uid !== uid) fail("scope_mismatch", "late draft belongs to another user");
}

function assertSnapshotCollision(existing, input) {
  if (existing.uid !== input.uid || existing.eventKey !== input.eventKey) fail("scope_mismatch", "late draft key mismatch");
  const same = existing.recipientStatus === input.recipientStatus
    && isDeepStrictEqual(existing.recipients, input.recipients)
    && isDeepStrictEqual(existing.evidenceSnapshot, input.evidenceSnapshot)
    && existing.bodySnapshot === input.bodySnapshot
    && isDeepStrictEqual(existing.etaEvidence, input.etaEvidence);
  if (!same) fail("draft_collision", "a late draft event key already has a different immutable snapshot");
}

function newClaimToken() {
  return `${randomUUID()}.${randomBytes(18).toString("hex")}`;
}

function newProviderIdempotencyKey() {
  return randomBytes(32).toString("hex");
}

function callbackSecret(options = {}) {
  const explicit = options.secret ?? options.callbackSecret;
  if (explicit !== undefined) return String(explicit);
  return String(
    process.env.LM_LATE_APPROVAL_CALLBACK_SECRET
      || process.env.LM_UID_SECRET
      || process.env.LM_TELEGRAM_WEBHOOK_SECRET
      || DEVELOPMENT_CALLBACK_SECRET,
  );
}

function callbackActionCode(action) {
  const value = String(action || "").trim().toLowerCase();
  if (value === "send" || value === "s") return "s";
  if (value === "do_not_send" || value === "dont_send" || value === "don't_send" || value === "d") return "d";
  fail("invalid_callback", "late approval callback action is invalid");
}

function callbackAction(code) {
  return code === "s" ? "send" : "do_not_send";
}

function callbackPayload(code, draftId, expiresAtSeconds) {
  return `late:v1:${code}:${draftId}:${expiresAtSeconds}`;
}

function callbackSignature(payload, secret) {
  // Telegram limits callback_data to 64 bytes.  An 8-byte truncated HMAC is encoded in 11 URL-safe
  // characters and still makes a copied/tampered draft id or action unverifiable at the webhook.
  return createHmac("sha256", secret).update(payload, "utf8").digest("base64url").slice(0, 11);
}

function createLateApprovalCallbackData(input = {}) {
  const action = callbackActionCode(input.action);
  const draftId = text(input.draftId || input.draft_id, "draft id", 128);
  const nowMs = finiteNow(input.nowMs, "callback timestamp");
  const expiryMs = input.expiresAtMs == null
    ? nowMs + DEFAULT_CALLBACK_TTL_MS
    : finiteNow(input.expiresAtMs, "callback expiry");
  const expiresAtSeconds = Math.floor(expiryMs / 1000);
  if (!Number.isSafeInteger(expiresAtSeconds) || expiresAtSeconds <= 0) {
    fail("invalid_callback", "late approval callback expiry is invalid");
  }
  const expiresToken = expiresAtSeconds.toString(36);
  const payload = callbackPayload(action, draftId, expiresToken);
  const signature = callbackSignature(payload, callbackSecret(input));
  const result = `late:${action}:${draftId}:${expiresToken}:${signature}`;
  if (Buffer.byteLength(result, "utf8") > 64) fail("invalid_callback", "late approval callback is too long");
  return result;
}

function parseLateApprovalCallback(data, options = {}) {
  const raw = String(data || "");
  const match = /^late:([sd]):([A-Za-z0-9._-]{1,128}):([0-9a-z]{1,8}):([A-Za-z0-9_-]{11})$/.exec(raw);
  if (!match) return null;
  const [, code, draftId, expiresToken, receivedSignature] = match;
  const payload = callbackPayload(code, draftId, expiresToken);
  const expectedSignature = callbackSignature(payload, callbackSecret(options));
  const received = Buffer.from(receivedSignature, "utf8");
  const expected = Buffer.from(expectedSignature, "utf8");
  if (received.length !== expected.length || !timingSafeEqual(received, expected)) return null;
  const expiresAtSeconds = Number.parseInt(expiresToken, 36);
  if (!Number.isSafeInteger(expiresAtSeconds) || expiresAtSeconds <= 0) return null;
  const nowMs = finiteNow(options.nowMs, "callback timestamp");
  return {
    action: callbackAction(code),
    code,
    draftId,
    expiresAtMs: expiresAtSeconds * 1000,
    expired: nowMs > expiresAtSeconds * 1000,
    callbackData: raw,
  };
}

function initialLateDraft(input) {
  const normalized = normalizeDraftInput(input);
  const now = iso(normalized.nowMs, "createdAt");
  return {
    draftId: normalized.draftId || randomUUID(),
    uid: normalized.uid,
    eventKey: normalized.eventKey,
    // A resolved snapshot is immediately eligible for one approval card.  The transient `draft`
    // state is represented by this pure constructor's input boundary; no external send can observe
    // it before the transaction moves to awaiting_decision.
    status: normalized.recipientStatus === "resolved" ? "awaiting_decision" : normalized.recipientStatus,
    recipientStatus: normalized.recipientStatus,
    recipients: normalized.recipients,
    evidenceSnapshot: normalized.evidenceSnapshot,
    bodySnapshot: normalized.bodySnapshot,
    etaEvidence: normalized.etaEvidence,
    decision: null,
    idempotencyKey: null,
    // This identity belongs to the provider callback boundary, not to a lease.  It must survive
    // every claim recovery so a provider can deduplicate an accepted send before its receipt lands.
    providerIdempotencyKey: newProviderIdempotencyKey(),
    claimToken: null,
    workerId: null,
    claimedAt: null,
    claimExpiresAt: null,
    providerMessageId: null,
    deliveredAt: null,
    createdAt: now,
    updatedAt: now,
  };
}

function transitionLateDecision(row, input) {
  const normalized = normalizeDecisionInput(input);
  assertRowId(row);
  assertTenant(row, normalized.uid);
  const next = clone(row);
  if (row.decision) {
    if (row.decision === normalized.decision) return { row: next, duplicate: true };
    fail("decision_conflict", "a different late approval decision already won");
  }
  if (row.status === "recipient_missing" || row.status === "recipient_ambiguous") {
    if (normalized.decision === "send") fail("recipient_not_sendable", "a missing or ambiguous recipient cannot be sent");
    fail("decision_not_allowed", "a missing or ambiguous recipient is already terminal");
  }
  if (row.status !== "awaiting_decision") fail("decision_not_allowed", `late draft is ${row.status}`);
  next.decision = normalized.decision;
  next.idempotencyKey = normalized.idempotencyKey;
  next.updatedAt = iso(normalized.nowMs, "decision timestamp");
  if (normalized.decision === "do_not_send") next.status = "do_not_send";
  // `send` remains awaiting_decision until a worker obtains the separate delivery claim.  This
  // makes the approval record durable before any transport boundary can be crossed.
  return { row: next, duplicate: false };
}

function transitionLateClaim(row, input) {
  const normalized = normalizeClaimInput(input);
  assertRowId(row);
  const next = clone(row);
  if (row.status === "sent") return { row: next, claimed: false, reason: "sent" };
  if (row.status === "do_not_send") return { row: next, claimed: false, reason: "do_not_send" };
  if (row.status === "recipient_missing" || row.status === "recipient_ambiguous") {
    return { row: next, claimed: false, reason: row.status };
  }
  if (row.decision !== "send") return { row: next, claimed: false, reason: "decision_required" };
  if (row.status !== "awaiting_decision" && row.status !== "send_claimed") {
    return { row: next, claimed: false, reason: row.status };
  }

  const now = normalized.nowMs;
  const activeUntil = row.claimExpiresAt == null ? 0 : Date.parse(row.claimExpiresAt);
  if (row.status === "send_claimed" && activeUntil > now) {
    if (row.workerId !== normalized.workerId) {
      return { row: next, claimed: false, reason: "claimed_by_other_worker" };
    }
    next.claimExpiresAt = new Date(now + normalized.leaseMs).toISOString();
    next.updatedAt = new Date(now).toISOString();
    return { row: next, claimed: true, retry: true };
  }

  next.status = "send_claimed";
  next.claimToken = newClaimToken();
  next.workerId = normalized.workerId;
  next.claimedAt = new Date(now).toISOString();
  next.claimExpiresAt = new Date(now + normalized.leaseMs).toISOString();
  next.updatedAt = next.claimedAt;
  return {
    row: next,
    claimed: true,
    ...(row.status === "send_claimed" ? { recovered: true } : {}),
  };
}

function transitionLateDelivery(row, input) {
  const normalized = normalizeDeliveryInput(input);
  assertRowId(row);
  assertTenant(row, normalized.uid);
  const next = clone(row);
  if (row.status === "send_claimed" || row.status === "sent") {
    if (row.claimToken !== normalized.claimToken) {
      fail("claim_token_mismatch", "delivery receipt does not belong to the current claim");
    }
    if (row.workerId !== normalized.workerId) {
      fail("claim_worker_mismatch", "delivery receipt worker does not own the claim");
    }
  }
  if (row.status === "sent") {
    if (row.providerMessageId === normalized.providerMessageId) return { row: next, duplicate: true };
    fail("receipt_conflict", "a different provider receipt already won");
  }
  if (row.status !== "send_claimed") fail("delivery_not_claimed", `late draft is ${row.status}`);
  next.status = "sent";
  next.providerMessageId = normalized.providerMessageId;
  next.deliveredAt = normalized.deliveredAt;
  next.updatedAt = new Date(normalized.nowMs).toISOString();
  return { row: next, duplicate: false };
}

function lookupOperation(store, names) {
  for (const name of names) if (store && typeof store[name] === "function") return store[name].bind(store);
  fail("store_invalid", `late approval store needs ${names[0]}`);
}

async function getLateDraft(input, store) {
  const normalized = {
    uid: text(input && input.uid, "uid", 256),
    draftId: text(input && (input.draftId || input.draft_id), "draft id", 128),
  };
  const target = store || createSupabaseLateApprovalStore();
  const result = await lookupOperation(target, ["getLateDraft", "getDraft"])(normalized);
  const row = rowFromPersistence(result);
  assertRowId(row);
  assertTenant(row, normalized.uid);
  return exposeRow(row);
}

async function createLateDraft(input, store) {
  const normalized = normalizeDraftInput(input);
  const target = store || createSupabaseLateApprovalStore();
  const result = await lookupOperation(target, ["createLateDraft", "insertLateDraft", "createDraft"])(normalized);
  return exposeRow(rowFromPersistence(result), { ...(result && result.duplicate ? { duplicate: true } : {}) });
}

async function decideLateDraft(input, store) {
  const normalized = normalizeDecisionInput(input);
  const target = store || createSupabaseLateApprovalStore();
  const result = await lookupOperation(target, ["decideLateDraft", "decideDraft", "recordDecision"])(normalized);
  const row = rowFromPersistence(result);
  return exposeRow(row, {
    ...(result && result.duplicate ? { duplicate: true } : {}),
  });
}

async function claimApprovedDelivery(input, store) {
  const normalized = normalizeClaimInput(input);
  // Keep a store-specific lease default available to injected stores (the in-memory test store uses
  // a short lease to exercise interruption recovery).  An explicit lease remains normalized here.
  if (input.leaseMs == null) normalized.leaseMs = undefined;
  const target = store || createSupabaseLateApprovalStore();
  const result = await lookupOperation(target, ["claimApprovedDelivery", "claimLateDelivery", "claimDelivery"])(normalized);
  const row = rowFromPersistence(result && result.row ? result.row : result);
  const flags = {
    claimed: result && result.claimed === true,
    ...(result && result.reason ? { reason: result.reason } : {}),
    ...(result && result.retry ? { retry: true } : {}),
    ...(result && result.recovered ? { recovered: true } : {}),
  };
  return exposeRow(row, flags);
}

async function recordLateDelivery(input, store) {
  const normalized = normalizeDeliveryInput(input);
  const target = store || createSupabaseLateApprovalStore();
  const result = await lookupOperation(target, ["recordLateDelivery", "recordDelivery", "recordReceipt"])(normalized);
  const row = rowFromPersistence(result && result.row ? result.row : result);
  return exposeRow(row, {
    ...(result && result.duplicate ? { duplicate: true } : {}),
  });
}

function createInMemoryLateApprovalStore(options = {}) {
  const rowsById = new Map();
  const idsByKey = new Map();
  const defaultNow = options.nowMs == null ? null : finiteNow(options.nowMs);
  const defaultLeaseMs = options.leaseMs == null ? DEFAULT_LEASE_MS : Number(options.leaseMs);

  function nowInput(input) {
    return defaultNow == null || input.__nowProvided === true ? input : { ...input, nowMs: defaultNow };
  }
  function get(draftId) {
    const row = rowsById.get(draftId);
    if (!row) fail("draft_not_found", "late draft was not found");
    return row;
  }
  return {
    async createLateDraft(input) {
      const normalized = normalizeDraftInput(nowInput(input));
      const key = `${normalized.uid}\u0000${normalized.eventKey}`;
      const existingId = idsByKey.get(key);
      if (existingId) {
        const existing = get(existingId);
        assertSnapshotCollision(existing, normalized);
        return exposeRow(existing, { duplicate: true });
      }
      const row = initialLateDraft(normalized);
      if (rowsById.has(row.draftId)) fail("draft_collision", "draft id already exists");
      rowsById.set(row.draftId, row);
      idsByKey.set(key, row.draftId);
      return exposeRow(row);
    },
    async decideLateDraft(input) {
      const normalized = normalizeDecisionInput(nowInput(input));
      const current = get(normalized.draftId);
      const transition = transitionLateDecision(current, normalized);
      if (!transition.duplicate) rowsById.set(current.draftId, transition.row);
      return exposeRow(transition.row, transition.duplicate ? { duplicate: true } : {});
    },
    async claimApprovedDelivery(input) {
      const normalized = normalizeClaimInput({
        ...input,
        leaseMs: input.leaseMs == null ? defaultLeaseMs : input.leaseMs,
      });
      const current = get(normalized.draftId);
      const transition = transitionLateClaim(current, normalized);
      if (transition.claimed) rowsById.set(current.draftId, transition.row);
      return exposeRow(transition.row, {
        claimed: transition.claimed,
        ...(transition.reason ? { reason: transition.reason } : {}),
        ...(transition.retry ? { retry: true } : {}),
        ...(transition.recovered ? { recovered: true } : {}),
      });
    },
    async recordLateDelivery(input) {
      const normalized = normalizeDeliveryInput(nowInput(input));
      const current = get(normalized.draftId);
      const transition = transitionLateDelivery(current, normalized);
      if (!transition.duplicate) rowsById.set(current.draftId, transition.row);
      return exposeRow(transition.row, transition.duplicate ? { duplicate: true } : {});
    },
    getDraft(draftId) { return exposeRow(get(draftId)); },
    async getLateDraft(input) {
      const uid = text(input && input.uid, "uid", 256);
      const row = get(text(input && (input.draftId || input.draft_id), "draft id", 128));
      assertTenant(row, uid);
      return exposeRow(row);
    },
    size() { return rowsById.size; },
  };
}

function supabaseCredentials(options = {}) {
  const supaUrl = String(options.supaUrl || process.env.SUPABASE_URL || "").replace(/\/$/, "");
  const supaKey = options.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey) fail("storage_unavailable", "late approval store needs Supabase credentials");
  if (typeof fetchImpl !== "function") fail("storage_unavailable", "late approval store needs fetch");
  return { supaUrl, supaKey, fetchImpl };
}

function rpcHeaders(key) {
  return {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
  };
}

function createSupabaseLateApprovalStore(options = {}) {
  const credentials = supabaseCredentials(options);
  async function rpc(name, payload) {
    const response = await credentials.fetchImpl(`${credentials.supaUrl}/rest/v1/rpc/${name}`, {
      method: "POST",
      headers: rpcHeaders(credentials.supaKey),
      body: JSON.stringify(payload),
    }).catch((error) => ({ __error: String(error && error.message || error) }));
    if (!response || response.__error || !response.ok) {
      const status = response && response.status;
      fail("storage_error", `late approval RPC ${name} failed`, { status, cause: response && response.__error });
    }
    const body = await response.json().catch(() => null);
    if (body == null) fail("storage_error", `late approval RPC ${name} returned no row`);
    return body;
  }
  return {
    async getLateDraft(input) {
      const uid = text(input && input.uid, "uid", 256);
      const draftId = text(input && (input.draftId || input.draft_id), "draft id", 128);
      const url = `${credentials.supaUrl}/rest/v1/lm_late_approval_drafts` +
        `?uid=eq.${encodeURIComponent(uid)}&draft_id=eq.${encodeURIComponent(draftId)}&select=*&limit=1`;
      const response = await credentials.fetchImpl(url, { headers: rpcHeaders(credentials.supaKey) })
        .catch((error) => ({ __error: String(error && error.message || error) }));
      if (!response || response.__error || !response.ok) {
        fail("storage_error", "late approval draft lookup failed", {
          status: response && response.status, cause: response && response.__error,
        });
      }
      const body = await response.json().catch(() => null);
      const row = rowFromPersistence(body);
      if (!row) fail("draft_not_found", "late draft was not found");
      return row;
    },
    async createLateDraft(input) {
      const body = await rpc("lm_create_late_draft", {
        p_uid: input.uid,
        p_event_key: input.eventKey,
        p_recipient_status: input.recipientStatus,
        p_recipient_snapshot: input.recipients,
        p_evidence_snapshot: input.evidenceSnapshot,
        p_body_snapshot: input.bodySnapshot,
        p_eta_evidence_snapshot: input.etaEvidence,
        p_draft_id: input.draftId,
      });
      return rowFromPersistence(body);
    },
    async decideLateDraft(input) {
      const body = await rpc("lm_decide_late_draft", {
        p_uid: input.uid,
        p_draft_id: input.draftId,
        p_decision: input.decision,
        p_idempotency_key: input.idempotencyKey,
      });
      return rowFromPersistence(body);
    },
    async claimApprovedDelivery(input) {
      const body = await rpc("lm_claim_late_delivery", {
        p_draft_id: input.draftId,
        p_worker_id: input.workerId,
        p_lease_seconds: Math.max(1, Math.round((input.leaseMs == null ? DEFAULT_LEASE_MS : input.leaseMs) / 1000)),
      });
      const row = rowFromPersistence(body);
      return {
        ...row,
        claimed: Boolean(row && row.status === "send_claimed" && row.workerId === input.workerId),
      };
    },
    async recordLateDelivery(input) {
      const body = await rpc("lm_record_late_delivery", {
        p_uid: input.uid,
        p_draft_id: input.draftId,
        p_provider_message_id: input.providerMessageId,
        p_delivered_at: input.deliveredAt,
        p_claim_token: input.claimToken,
        p_worker_id: input.workerId,
      });
      return rowFromPersistence(body);
    },
  };
}

function callbackOwner(options = {}) {
  const owner = options.owner || options.row || options.user;
  if (!owner || !owner.uid) return null;
  const chatId = String(options.chatId || "");
  if (!chatId || String(options.actorId || "") !== chatId) return null;
  if (owner.telegram_chat_id != null && String(owner.telegram_chat_id) !== chatId) return null;
  return owner;
}

function providerMessageId(result) {
  if (!result || typeof result !== "object") return "";
  return String(result.id || result.providerMessageId || result.provider_message_id || "").trim();
}

function approvalReceiptText(row, providerId) {
  const recipient = Array.isArray(row && row.recipients) && row.recipients[0];
  const identity = recipient && recipient.email
    ? `${recipient.display_name || recipient.displayName || "宛先"} <${recipient.email}>`
    : "宛先";
  return `✅ 遅刻連絡を送信しました\n宛先: ${identity}\nResend: ${providerId}`;
}

async function handleLateApprovalCallback(data, options = {}) {
  const parsed = parseLateApprovalCallback(data, options);
  if (!parsed) return { handled: true, ok: false, reason: "invalid_callback" };
  if (parsed.expired) return { handled: true, ok: false, reason: "expired" };

  const owner = callbackOwner(options);
  if (!owner) return { handled: true, ok: false, reason: "scope_mismatch" };
  const store = options.store || options.lateApprovalStore || createSupabaseLateApprovalStore({
    supaUrl: options.supaUrl,
    supaKey: options.supaKey,
    fetchImpl: options.fetchImpl,
  });
  let current;
  try {
    current = options.draft || await getLateDraft({ uid: owner.uid, draftId: parsed.draftId }, store);
  } catch (error) {
    const code = error && error.code;
    return {
      handled: true,
      ok: false,
      reason: code === "draft_not_found" ? "expired" : (code || "draft_lookup_failed"),
    };
  }

  // A missing/ambiguous resolution is terminal at creation time.  Even a valid signed callback
  // cannot turn an evidence gap into an email address, and the card renderer never gives these rows
  // buttons in the first place.
  if (["recipient_missing", "recipient_ambiguous"].includes(current.status)) {
    return { handled: true, ok: false, reason: current.status, draft: current };
  }
  if (current.status === "do_not_send" && parsed.action === "send") {
    return { handled: true, ok: false, reason: "do_not_send", draft: current };
  }
  if (current.status === "sent" && parsed.action === "send") {
    return { handled: true, ok: true, sent: false, reason: "already_sent", draft: current };
  }

  const nowMs = options.nowMs === undefined ? Date.now() : options.nowMs;
  const idempotencyKey = `telegram:${parsed.callbackData}`;
  let decided;
  try {
    decided = await decideLateDraft({
      uid: owner.uid, draftId: parsed.draftId, decision: parsed.action,
      idempotencyKey, nowMs,
    }, store);
  } catch (error) {
    return { handled: true, ok: false, reason: (error && error.code) || "decision_failed" };
  }

  if (parsed.action === "do_not_send") {
    if (!decided.duplicate && typeof options.reflectAnswer === "function") {
      await options.reflectAnswer({
        token: options.token, chatId: options.chatId, messageId: options.messageId,
        messageText: options.messageText, label: "送らない", fetchImpl: options.fetchImpl,
      }).catch(() => {});
    }
    return { handled: true, ok: true, sent: false, decision: "do_not_send", draft: decided };
  }

  const workerId = String(options.workerId ||
    `telegram:${owner.uid}:${parsed.draftId}:${options.callbackQueryId || parsed.callbackData}`).slice(0, 256);
  let claim;
  try {
    claim = await claimApprovedDelivery({ draftId: parsed.draftId, workerId, nowMs }, store);
  } catch (error) {
    return { handled: true, ok: false, reason: (error && error.code) || "claim_failed", draft: decided };
  }
  if (!claim.claimed) {
    if (claim.status === "sent") return { handled: true, ok: true, sent: false, reason: "already_sent", draft: claim };
    return { handled: true, ok: false, reason: claim.reason || "claim_unavailable", draft: claim };
  }

  const sendLateNotice = options.sendLateNotice || require("./notify.js").sendLateNotice;
  const draft = claim;
  const recipients = Array.isArray(draft.recipients) ? draft.recipients : [];
  const event = options.event || {
    id: draft.eventKey,
    summary: draft.eventKey,
    attendees: recipients.map((recipient) => ({
      email: recipient.email,
      displayName: recipient.display_name || recipient.displayName,
    })),
  };
  let provider;
  try {
    provider = await sendLateNotice(owner.uid, event, {
      userName: owner.name,
      userEmail: owner.email,
      etaMinutes: draft.etaEvidence && draft.etaEvidence.etaMinutes,
      recipientSnapshot: recipients,
      bodySnapshot: draft.bodySnapshot,
      providerIdempotencyKey: draft.providerIdempotencyKey,
      idempotencyKey: draft.providerIdempotencyKey,
      resendKey: options.resendKey || process.env.RESEND_API_KEY,
      fetchImpl: options.providerFetchImpl || options.fetchImpl,
    });
  } catch (error) {
    return { handled: true, ok: false, sent: false, reason: "provider_send_failed", error: String(error && error.message || error), draft };
  }
  const providerId = providerMessageId(provider);
  if (!provider || provider.sent !== true || !providerId) {
    return { handled: true, ok: false, sent: false, reason: "provider_receipt_missing", draft };
  }

  let receipt;
  try {
    receipt = await recordLateDelivery({
      uid: owner.uid, draftId: parsed.draftId, providerMessageId: providerId,
      deliveredAt: new Date(nowMs).toISOString(), claimToken: draft.claimToken,
      workerId, nowMs,
    }, store);
  } catch (error) {
    return { handled: true, ok: false, sent: true, reason: "provider_receipt_failed", error: String(error && error.message || error), draft };
  }

  if (typeof options.reflectAnswer === "function") {
    await options.reflectAnswer({
      token: options.token, chatId: options.chatId, messageId: options.messageId,
      messageText: options.messageText, label: "送る", fetchImpl: options.fetchImpl,
    }).catch(() => {});
  }
  const sendMessage = options.sendMessage || require("./telegram.js").sendMessage;
  let telegramReceipt;
  try {
    telegramReceipt = await sendMessage(
      options.token || process.env.LM_TELEGRAM_BOT_TOKEN,
      options.chatId,
      approvalReceiptText(draft, providerId),
    );
  } catch (error) {
    telegramReceipt = { ok: false, error: String(error && error.message || error) };
  }
  return {
    handled: true,
    ok: Boolean(telegramReceipt && telegramReceipt.ok !== false),
    sent: true,
    decision: "send",
    providerMessageId: providerId,
    telegramMessageId: telegramReceipt && telegramReceipt.result && telegramReceipt.result.message_id,
    draft: receipt,
  };
}

module.exports = {
  APPROVAL_STATES,
  DECISIONS,
  LateApprovalError,
  createLateDraft,
  decideLateDraft,
  claimApprovedDelivery,
  recordLateDelivery,
  createInMemoryLateApprovalStore,
  createSupabaseLateApprovalStore,
  createSupabaseStore: createSupabaseLateApprovalStore,
  initialLateDraft,
  transitionLateDecision,
  transitionLateClaim,
  transitionLateDelivery,
  getLateDraft,
  createLateApprovalCallbackData,
  parseLateApprovalCallback,
  handleLateApprovalCallback,
};
