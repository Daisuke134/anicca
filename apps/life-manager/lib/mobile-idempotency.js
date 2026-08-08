"use strict";

const crypto = require("node:crypto");
const { MobileError, canonicalJson, sha256 } = require("./mobile-utils.js");

const REPLAY_TTL_MS = 5 * 60 * 1000;
const PROCESS_REPLAY_SECRET = crypto.randomBytes(32);

function canonicalPayloadHash(payload) {
  return sha256(canonicalJson(payload));
}

function validateKey(key) {
  const value = String(key || "").trim();
  if (value.length < 8 || value.length > 128 || /[\x00-\x1f\x7f]/u.test(value)) {
    throw new MobileError("idempotency_required", "Idempotency-Key is required for this mutation.");
  }
  return value;
}

function asReplayError(row, requestHash, deps = {}) {
  const error = row && row.error;
  if (!error) return null;
  const details = decryptReplayResult(error.details, requestHash, deps);
  return new MobileError(error.code || "mutation_failed", error.message || "The previous mutation failed.", error.status || 502, Boolean(error.retryable), details);
}

function isCompleted(status) {
  return status === "succeeded" || status === "completed";
}

function hasTokenField(value) {
  if (Array.isArray(value)) return value.some(hasTokenField);
  if (!value || typeof value !== "object") return false;
  return Object.entries(value).some(([key, child]) => /^(?:access|refresh)(?:Token|_token)$|^deletion(?:Capability|_capability)$/u.test(key) || hasTokenField(child));
}

function replayKey(requestHash, deps = {}) {
  const configured = deps.replaySecret || process.env.LM_MOBILE_REPLAY_SECRET || process.env.LM_UID_SECRET || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const master = configured ? Buffer.from(String(configured)) : PROCESS_REPLAY_SECRET;
  return crypto.createHash("sha256").update(master).update(String(requestHash)).digest();
}

function encryptReplayResult(result, requestHash, deps = {}) {
  if (!hasTokenField(result)) return result;
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", replayKey(requestHash, deps), iv);
  const ciphertext = Buffer.concat([cipher.update(JSON.stringify(result), "utf8"), cipher.final()]);
  return {
    kind: "encrypted_replay:v1",
    ciphertext: ciphertext.toString("base64url"),
    iv: iv.toString("base64url"),
    tag: cipher.getAuthTag().toString("base64url"),
    expiresAt: new Date(Date.now() + REPLAY_TTL_MS).toISOString(),
  };
}

function decryptReplayResult(value, requestHash, deps = {}) {
  if (!value || value.kind !== "encrypted_replay:v1") {
    if (hasTokenField(value)) throw new MobileError("idempotency_replay_unavailable", "The previous token response cannot be replayed safely.", 409, true);
    return value;
  }
  if (!value.expiresAt || Date.parse(value.expiresAt) <= Date.now()) {
    throw new MobileError("idempotency_replay_expired", "The token response replay window has expired.", 409, true);
  }
  try {
    const decipher = crypto.createDecipheriv("aes-256-gcm", replayKey(requestHash, deps), Buffer.from(value.iv, "base64url"));
    decipher.setAuthTag(Buffer.from(value.tag, "base64url"));
    const clear = Buffer.concat([decipher.update(Buffer.from(value.ciphertext, "base64url")), decipher.final()]);
    return JSON.parse(clear.toString("utf8"));
  } catch {
    throw new MobileError("idempotency_replay_unavailable", "The previous token response cannot be replayed safely.", 409, true);
  }
}

function storedResult(row, requestHash, deps = {}) {
  return decryptReplayResult(row && (row.result === undefined ? row.result_json : row.result), requestHash, deps);
}

async function withMobileIdempotency({ scope, key, payload, operation }, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  if (typeof operation !== "function") throw new TypeError("operation must be a function");
  const store = deps.store;
  if (!store || typeof store.readIdempotency !== "function" || typeof store.claimIdempotency !== "function" || typeof store.completeIdempotency !== "function") {
    throw new MobileError("idempotency_unavailable", "Mutation storage is unavailable.", 503, true);
  }
  const value = validateKey(key);
  const requestHash = canonicalPayloadHash(payload);
  const existing = await store.readIdempotency(scope, value);
  if (existing) {
    if (String(existing.requestHash || existing.request_hash) !== requestHash) {
      throw new MobileError("idempotency_conflict", "The idempotency key was already used for a different request.", 409);
    }
    const status = existing.status;
    if (isCompleted(status) || status === "failed") {
      const replayError = asReplayError(existing, requestHash, deps);
      if (replayError) throw replayError;
      return storedResult(existing, requestHash, deps);
    }
    throw new MobileError("idempotency_in_progress", "The same mutation is already in progress.", 409, true);
  }

  const claimed = await store.claimIdempotency(scope, value, { requestHash, status: "pending" });
  if (!claimed) {
    const raced = await store.readIdempotency(scope, value);
    if (raced && String(raced.requestHash || raced.request_hash) !== requestHash) {
      throw new MobileError("idempotency_conflict", "The idempotency key was already used for a different request.", 409);
    }
    if (raced && (isCompleted(raced.status) || raced.status === "failed")) {
      const replayError = asReplayError(raced, requestHash, deps);
      if (replayError) throw replayError;
      return storedResult(raced, requestHash, deps);
    }
    throw new MobileError("idempotency_in_progress", "The same mutation is already in progress.", 409, true);
  }

  try {
    const result = await operation();
    const stored = encryptReplayResult(result, requestHash, deps);
    await store.completeIdempotency(scope, value, {
      requestHash, status: "succeeded", result: stored,
      ...(stored && stored.kind === "encrypted_replay:v1" ? { resultExpiresAt: stored.expiresAt } : {}),
    });
    return result;
  } catch (error) {
    const normalized = error instanceof MobileError
      ? error
      : new MobileError("mutation_failed", "The mutation could not be completed.", 502, true);
    const errorDetails = normalized.details === undefined ? undefined : encryptReplayResult(normalized.details, requestHash, deps);
    await store.completeIdempotency(scope, value, {
      requestHash,
      status: "failed",
      error: {
        code: normalized.code, message: normalized.message, status: normalized.status, retryable: normalized.retryable,
        ...(errorDetails === undefined ? {} : { details: errorDetails }),
      },
    }).catch(() => {});
    throw error;
  }
}

module.exports = { canonicalPayloadHash, withMobileIdempotency, MobileError };
