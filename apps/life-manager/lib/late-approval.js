"use strict";

// The late-notice transport must not know how approval is stored.  This module owns the durable
// state machine and exposes a very small boundary: create a snapshot, decide once, claim once, and
// record one provider receipt.  The Supabase implementation below is deliberately an RPC-only
// adapter; no caller can turn a failed read/insert into an optimistic send.

const { randomBytes, randomUUID } = require("node:crypto");
const { isDeepStrictEqual } = require("node:util");

const APPROVAL_STATES = Object.freeze([
  "draft", "awaiting_decision", "send_claimed", "sent", "do_not_send",
  "recipient_missing", "recipient_ambiguous",
]);
const RECIPIENT_STATUSES = new Set(["resolved", "recipient_missing", "recipient_ambiguous"]);
const DECISIONS = new Set(["send", "do_not_send"]);
const DEFAULT_LEASE_MS = 120_000;
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
    draftId: text(input.draftId || input.draft_id, "draft id", 128),
    providerMessageId: text(input.providerMessageId || input.provider_message_id, "provider message id", 512),
    deliveredAt: iso(input.deliveredAt || input.delivered_at, "deliveredAt"),
    claimToken: optionalText(input.claimToken || input.claim_token, "claim token", 512),
    workerId: optionalText(input.workerId || input.worker_id, "worker id", 256),
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
  const next = clone(row);
  if (row.status === "sent") {
    if (row.providerMessageId === normalized.providerMessageId) return { row: next, duplicate: true };
    fail("receipt_conflict", "a different provider receipt already won");
  }
  if (row.status !== "send_claimed") fail("delivery_not_claimed", `late draft is ${row.status}`);
  if (normalized.claimToken && row.claimToken !== normalized.claimToken) {
    fail("claim_token_mismatch", "delivery receipt does not belong to the current claim");
  }
  if (normalized.workerId && row.workerId !== normalized.workerId) {
    fail("claim_worker_mismatch", "delivery receipt worker does not own the claim");
  }
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
};
