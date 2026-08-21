"use strict";

const ERROR = "cfo_capital_repair_invalid:workflow";
const ID = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
function fail() { throw new Error(ERROR); }
function plain(value) { return value !== null && typeof value === "object" && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype; }
function freeze(value, seen = new WeakSet()) { if (value === null || typeof value !== "object" || seen.has(value)) return value; seen.add(value); Object.values(value).forEach((child) => freeze(child, seen)); return Object.freeze(value); }

function decideCapitalRepair({ tenantId, mandateId, executorStatus, failureReason, ownerMayStop = false } = {}) {
  if (typeof tenantId !== "string" || !ID.test(tenantId) || typeof mandateId !== "string" || !ID.test(mandateId)
    || !["blocked", "failed", "unknown", "ready_for_owner_approval"].includes(executorStatus)
    || (failureReason !== null && typeof failureReason !== "string")) fail();
  const stop = executorStatus === "failed" && ownerMayStop === true;
  return freeze({ schemaVersion: 1, tenantId, mandateId, decision: stop ? "stop-review" : "repair", reason: stop ? "owner_stop_review_required" : failureReason || "executor_state_unresolved", execute: false, ownerApprovalRequired: stop, nextAction: stop ? "owner_review_before_shutdown" : "reconcile_receipt_and_reserves" });
}

function validateHiringExpense(input = {}) {
  if (!plain(input) || typeof input.tenantId !== "string" || !ID.test(input.tenantId)
    || typeof input.businessId !== "string" || !ID.test(input.businessId)
    || input.expenseStatus !== "verified" && input.expenseStatus !== "unknown"
    || input.deliverableStatus !== "accepted" && input.deliverableStatus !== "unknown"
    || input.paymentReceiptStatus !== "verified" && input.paymentReceiptStatus !== "unknown") fail();
  const approved = input.expenseStatus === "verified" && input.deliverableStatus === "accepted" && input.paymentReceiptStatus === "verified";
  return freeze({ schemaVersion: 1, tenantId: input.tenantId, businessId: input.businessId, decision: approved ? "accepted" : "blocked", execute: false, reason: approved ? "receipt_complete_no_payment_action" : "expense_or_deliverable_receipt_incomplete" });
}

module.exports = { decideCapitalRepair, validateHiringExpense };
