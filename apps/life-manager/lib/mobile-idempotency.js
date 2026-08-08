"use strict";

const { MobileError, canonicalJson, sha256 } = require("./mobile-utils.js");

function canonicalPayloadHash(payload) {
  return sha256(canonicalJson(payload));
}

function validateKey(key) {
  const value = String(key || "").trim();
  if (!value || value.length > 200 || /[\x00-\x1f\x7f]/u.test(value)) {
    throw new MobileError("idempotency_required", "Idempotency-Key is required for this mutation.");
  }
  return value;
}

function asReplayError(row) {
  const error = row && row.error;
  if (!error) return null;
  return new MobileError(error.code || "mutation_failed", error.message || "The previous mutation failed.", error.status || 502, Boolean(error.retryable));
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
    if (status === "completed" || status === "failed") {
      const replayError = asReplayError(existing);
      if (replayError) throw replayError;
      return existing.result === undefined ? existing.result_json : existing.result;
    }
    throw new MobileError("idempotency_in_progress", "The same mutation is already in progress.", 409, true);
  }

  const claimed = await store.claimIdempotency(scope, value, { requestHash, status: "pending" });
  if (!claimed) {
    const raced = await store.readIdempotency(scope, value);
    if (raced && String(raced.requestHash || raced.request_hash) !== requestHash) {
      throw new MobileError("idempotency_conflict", "The idempotency key was already used for a different request.", 409);
    }
    if (raced && (raced.status === "completed" || raced.status === "failed")) {
      const replayError = asReplayError(raced);
      if (replayError) throw replayError;
      return raced.result === undefined ? raced.result_json : raced.result;
    }
    throw new MobileError("idempotency_in_progress", "The same mutation is already in progress.", 409, true);
  }

  try {
    const result = await operation();
    await store.completeIdempotency(scope, value, { requestHash, status: "completed", result });
    return result;
  } catch (error) {
    const normalized = error instanceof MobileError
      ? error
      : new MobileError("mutation_failed", "The mutation could not be completed.", 502, true);
    await store.completeIdempotency(scope, value, {
      requestHash,
      status: "failed",
      error: { code: normalized.code, message: normalized.message, status: normalized.status, retryable: normalized.retryable },
    }).catch(() => {});
    throw error;
  }
}

module.exports = { canonicalPayloadHash, withMobileIdempotency, MobileError };
