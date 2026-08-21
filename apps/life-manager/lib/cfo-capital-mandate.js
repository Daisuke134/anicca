"use strict";

const ERROR = "cfo_capital_mandate_invalid:policy";
const ID = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const ASSET = /^[A-Z0-9._-]{2,32}$/;
function fail() { throw new Error(ERROR); }
function plain(value) { return value !== null && typeof value === "object" && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype; }
function integer(value) { return Number.isSafeInteger(value) && value >= 0; }
function iso(value) { return typeof value === "string" && Number.isFinite(Date.parse(value)); }
function freeze(value, seen = new WeakSet()) { if (value === null || typeof value !== "object" || seen.has(value)) return value; seen.add(value); Object.values(value).forEach((child) => freeze(child, seen)); return Object.freeze(value); }

/** Policy-only gate. It never signs, broadcasts, transfers, or calls an executor. */
function evaluateCapitalMandate(input = {}) {
  try {
    if (!plain(input) || typeof input.mandateId !== "string" || !ID.test(input.mandateId)
      || typeof input.tenantId !== "string" || !ID.test(input.tenantId)
      || typeof input.businessId !== "string" || !ID.test(input.businessId)
      || typeof input.venue !== "string" || input.venue.length === 0
      || typeof input.asset !== "string" || !ASSET.test(input.asset)
      || !integer(input.amountMinor) || !integer(input.spendCapMinor) || !integer(input.lossCapMinor)
      || !Array.isArray(input.allowedVenues) || !Array.isArray(input.allowedAssets)
      || input.allowedVenues.length === 0 || input.allowedAssets.length === 0 || !input.allowedVenues.includes(input.venue) || !input.allowedAssets.includes(input.asset)
      || !iso(input.expiresAt) || !plain(input.reserves) || !plain(input.receipt) || !["verified", "unknown"].includes(input.reserves.status)
      || !["verified", "unknown"].includes(input.receipt.status)) fail();
    if (input.reserves.status === "verified" && (!integer(input.reserves.operatingFloorMinor) || !integer(input.reserves.taxReserveMinor) || !integer(input.reserves.availableMinor))) fail();
    if (input.receipt.status === "verified" && (typeof input.receipt.ref !== "string" || input.receipt.ref.length === 0 || !iso(input.receipt.observedAt))) fail();
    const exceptions = [];
    if (Date.parse(input.expiresAt) <= Date.now()) exceptions.push("mandate_expired");
    if (input.reserves.status !== "verified") exceptions.push("reserve_unknown");
    if (input.receipt.status !== "verified") exceptions.push("receipt_unknown");
    if (input.amountMinor > input.spendCapMinor) exceptions.push("spend_cap_exceeded");
    if (!input.allowedVenues.includes(input.venue)) exceptions.push("venue_not_allowed");
    if (!input.allowedAssets.includes(input.asset)) exceptions.push("asset_not_allowed");
    if (input.reserves.status === "verified" && input.amountMinor > Math.max(0, input.reserves.availableMinor - input.reserves.operatingFloorMinor - input.reserves.taxReserveMinor)) exceptions.push("non_investable_reserve_floor");
    const unique = [...new Set(exceptions)].sort();
    return freeze({ schemaVersion: 1, mandateId: input.mandateId, tenantId: input.tenantId, businessId: input.businessId, decision: unique.length ? "repair" : "hold", reason: unique.length ? unique[0] : "policy_passed_review_required", execute: false, ownerApprovalRequired: true, exceptions: unique });
  } catch { throw new Error(ERROR); }
}

module.exports = { evaluateCapitalMandate };
