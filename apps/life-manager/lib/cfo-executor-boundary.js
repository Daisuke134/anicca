"use strict";

const ERROR = "cfo_executor_boundary_invalid:attachment";
const ID = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const REF = /^secret:\/\/[a-z0-9][a-z0-9._-]*(?:\/[a-z0-9][a-z0-9._-]*)*$/i;
function fail() { throw new Error(ERROR); }
function plain(value) { return value !== null && typeof value === "object" && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype; }
function freeze(value, seen = new WeakSet()) { if (value === null || typeof value !== "object" || seen.has(value)) return value; seen.add(value); Object.values(value).forEach((child) => freeze(child, seen)); return Object.freeze(value); }

/** Attach policy metadata only; this function never starts an executor. */
function attachCfoExecutor(input = {}) {
  try {
    if (!plain(input) || typeof input.tenantId !== "string" || !ID.test(input.tenantId)
      || typeof input.businessId !== "string" || !ID.test(input.businessId)
      || !plain(input.mandate) || input.mandate.execute !== false || input.mandate.ownerApprovalRequired !== true
      || !Array.isArray(input.readerSecretRefs) || !Array.isArray(input.executorSecretRefs)
      || input.readerSecretRefs.length === 0 || input.executorSecretRefs.length === 0
      || input.readerSecretRefs.some((ref) => typeof ref !== "string" || !REF.test(ref))
      || input.executorSecretRefs.some((ref) => typeof ref !== "string" || !REF.test(ref))
      || input.readerSecretRefs.some((ref) => input.executorSecretRefs.includes(ref))
      || !plain(input.business) || !["complete", "partial", "unknown"].includes(input.business.status)) fail();
    if (input.business.status !== "complete" || input.business.profitStatus !== "verified_positive") {
      return freeze({ schemaVersion: 1, tenantId: input.tenantId, businessId: input.businessId, status: "blocked", reason: "business_not_verified_profitable", execute: false, readerSecretRefs: [...input.readerSecretRefs], executorSecretRefs: [...input.executorSecretRefs] });
    }
    return freeze({ schemaVersion: 1, tenantId: input.tenantId, businessId: input.businessId, status: "ready_for_owner_approval", reason: "policy_passed_no_executor_started", execute: false, readerSecretRefs: [...input.readerSecretRefs], executorSecretRefs: [...input.executorSecretRefs] });
  } catch { throw new Error(ERROR); }
}

module.exports = { attachCfoExecutor };
