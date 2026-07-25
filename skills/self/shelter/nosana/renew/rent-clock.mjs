// rent-clock.mjs — pure clock logic for the self-renewal path (S3 of "agent financial
// independence"): given a job's real on-chain timeStart/timeout and the current time, decide
// whether it is time to renew, with enough lead time that a renewal attempt (RPC round-trip, tx
// build/sign/send, a retry after a hiccup) can land BEFORE the job actually expires and the node
// tears it down.
//
// No I/O here — every input is already-known data (real job state is read elsewhere via the
// authoritative jobs API, exactly like deploy.mjs's reconcileNosanaJobViaApi — see job-lookup.mjs
// in this directory). Fails closed by THROWING on invalid/missing numeric input rather than
// silently guessing a yes/no verdict — an executor that cannot tell what time it is must never
// guess "not due yet", because that is exactly the failure mode that lets a job silently expire.

export const DEFAULT_RENEWAL_LEAD_SECONDS = 180; // 3 minutes of safety margin before expiry.

/**
 * Pure: a job's real expiry timestamp (unix seconds). Fails closed (throws) on non-finite or
 * negative timeStart/timeout — never silently computes NaN/Infinity as "not expiring".
 */
export function computeExpiresAtTs({ timeStart, timeout }) {
  for (const [key, value] of Object.entries({ timeStart, timeout })) {
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
      throw new Error(`computeExpiresAtTs: ${key} must be a non-negative finite number, got ${value}`);
    }
  }
  return timeStart + timeout;
}

/**
 * Pure: the renewal decision. dueForRenewal is true once secondsUntilExpiry drops to leadSeconds
 * or below — leadSeconds must be sized generously enough (default 180s) that even a slow RPC
 * round-trip plus one retry can complete before secondsUntilExpiry reaches zero. Fails closed
 * (throws) on any non-finite input.
 */
export function evaluateRentClock({ nowTs, expiresAtTs, leadSeconds = DEFAULT_RENEWAL_LEAD_SECONDS }) {
  for (const [key, value] of Object.entries({ nowTs, expiresAtTs, leadSeconds })) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new Error(`evaluateRentClock: ${key} must be a finite number, got ${value}`);
    }
  }
  if (leadSeconds < 0) {
    throw new Error("evaluateRentClock: leadSeconds must be >= 0");
  }
  const secondsUntilExpiry = expiresAtTs - nowTs;
  return {
    expiresAtTs,
    nowTs,
    leadSeconds,
    secondsUntilExpiry,
    alreadyExpired: secondsUntilExpiry <= 0,
    dueForRenewal: secondsUntilExpiry <= leadSeconds,
  };
}

/**
 * Pure: the at-most-once identity of "the renewal that keeps this job/lineage alive past
 * `referenceExpiresAtTs`". Anchored to a REAL on-chain expiry (not wall clock) so it is
 * deterministic and re-derivable from real state on every run — the same window always produces
 * the same id. Once a renewal actually lands, the job's real timeout moves, so a fresh read
 * naturally derives a NEW windowId — the intent ledger only needs to catch the narrow gap between
 * "we sent the tx" and "the indexer reflects it" (see executor.mjs's findWindowRecord).
 */
export function computeRenewalWindowId({ jobAddress, referenceExpiresAtTs }) {
  if (typeof jobAddress !== "string" || jobAddress.length === 0) {
    throw new Error("computeRenewalWindowId: jobAddress is required");
  }
  if (typeof referenceExpiresAtTs !== "number" || !Number.isFinite(referenceExpiresAtTs)) {
    throw new Error("computeRenewalWindowId: referenceExpiresAtTs must be a finite number");
  }
  return `${jobAddress}:${Math.floor(referenceExpiresAtTs)}`;
}

/**
 * Pure: the window id used when there has NEVER been any job to anchor to (the very first ever
 * post has no prior job address). Bucketed by `bucketSeconds` so repeated checks close together
 * (e.g. a cron every minute) fall in the same bucket and dedupe the same way a real job-anchored
 * window would. The "bootstrap:" prefix makes it structurally impossible for this to collide with
 * a real `${jobAddress}:${ts}` window id.
 */
export function computeBootstrapWindowId({ nowTs, bucketSeconds = DEFAULT_RENEWAL_LEAD_SECONDS * 2 }) {
  if (typeof nowTs !== "number" || !Number.isFinite(nowTs)) {
    throw new Error("computeBootstrapWindowId: nowTs must be a finite number");
  }
  if (typeof bucketSeconds !== "number" || !Number.isFinite(bucketSeconds) || bucketSeconds <= 0) {
    throw new Error("computeBootstrapWindowId: bucketSeconds must be a positive finite number");
  }
  return `bootstrap:${Math.floor(nowTs / bucketSeconds)}`;
}
