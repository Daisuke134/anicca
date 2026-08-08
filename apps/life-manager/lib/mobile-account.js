"use strict";

const { MobileError, nowIso, randomOpaque } = require("./mobile-utils.js");

function cleanupResult(provider, result) {
  if (!result || typeof result !== "object") return { provider, status: "unknown" };
  const state = result.state || result.status;
  return {
    provider,
    status: state === "disconnected" || state === "deleted" || state === "action_required" || state === "missing" || result.ok === true
      ? "disconnected"
      : "unknown",
  };
}

function outputReceipt(value) {
  if (!value) return value;
  return {
    operationId: value.operationId || value.operation_id,
    status: value.status,
    completedAt: value.completedAt || value.completed_at || null,
    providerCleanup: value.providerCleanup || value.provider_cleanup || [],
  };
}

async function deleteMobileAccount(scope, input = {}, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  if (input.confirmed !== true) throw new MobileError("deletion_confirmation_required", "Confirm account deletion before continuing.");
  const store = deps.store;
  if (!store || typeof store.revokeAllSessions !== "function" || typeof store.deleteAccount !== "function" || typeof store.writeDeletionReceipt !== "function") throw new MobileError("deletion_store_unavailable", "Account deletion storage is unavailable.", 503, true);
  const operationId = input.operationId || randomOpaque("deletion:v1:", deps);
  if (typeof store.readDeletionReceipt === "function") {
    const existing = await store.readDeletionReceipt(scope, operationId);
    if (existing && existing.status === "completed") return outputReceipt(existing);
  }
  await store.revokeAllSessions(scope);
  const disconnect = deps.disconnectCalendar || deps.disconnectProvider;
  const cleanup = [];
  let complete = true;
  if (typeof disconnect !== "function") {
    cleanup.push({ provider: "calendar", status: "unknown" });
    complete = false;
  } else {
    try {
      cleanup.push(cleanupResult("calendar", await disconnect(scope)));
      if (cleanup[0].status !== "disconnected") complete = false;
    } catch {
      cleanup.push({ provider: "calendar", status: "failed" });
      complete = false;
    }
  }
  if (!complete) {
    const receipt = { operationId, status: "incomplete", completedAt: null, providerCleanup: cleanup };
    await store.writeDeletionReceipt(scope, receipt);
    throw new MobileError("deletion_incomplete", "Account deletion is incomplete because a provider connection could not be verified.", 502, true, { receipt });
  }
  const completedAt = nowIso(deps);
  const receipt = { operationId, status: "completed", completedAt, providerCleanup: cleanup };
  try {
    await store.deleteAccount(scope, { preserveIdempotencyKey: input.idempotencyKey || null });
  } catch (error) {
    const incomplete = { operationId, status: "incomplete", completedAt: null, providerCleanup: cleanup };
    await store.writeDeletionReceipt(scope, incomplete).catch(() => {});
    throw new MobileError("deletion_incomplete", "Account data could not be deleted; the provider cleanup receipt remains incomplete.", 503, true, { receipt: incomplete, cause: error && error.code ? error.code : "account_delete_failed" });
  }
  try {
    await store.writeDeletionReceipt(scope, receipt);
  } catch (error) {
    throw new MobileError("deletion_incomplete", "Account data was deleted but the completion receipt could not be stored.", 503, true, {
      receipt,
      cause: error && error.code ? error.code : "deletion_receipt_failed",
    });
  }
  return outputReceipt(receipt);
}

module.exports = { deleteMobileAccount, cleanupResult, outputReceipt };
