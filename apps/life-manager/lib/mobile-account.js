"use strict";

const { MobileError, nowIso, randomOpaque, sha256 } = require("./mobile-utils.js");

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

function outputReceipt(value, capability = null) {
  if (!value) return value;
  const result = {
    operationId: value.operationId || value.operation_id,
    status: value.status,
    completedAt: value.completedAt || value.completed_at || null,
    providerCleanup: value.providerCleanup || value.provider_cleanup || [],
  };
  const replayCapability = capability || value.deletionCapability || value.deletion_capability;
  if (replayCapability) result.deletionCapability = replayCapability;
  return result;
}

function mergeCleanup(previous, current) {
  const byProvider = new Map((Array.isArray(previous) ? previous : []).map((item) => [item.provider, item]));
  for (const item of Array.isArray(current) ? current : []) byProvider.set(item.provider, item);
  return [...byProvider.values()];
}

async function deleteMobileAccount(scope, input = {}, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  if (input.confirmed !== true) throw new MobileError("deletion_confirmation_required", "Confirm account deletion before continuing.");
  const store = deps.store;
  if (!store || typeof store.writeDeletionReceipt !== "function" || (typeof store.finalizeAccountDeletion !== "function" && (typeof store.revokeAllSessions !== "function" || typeof store.deleteAccount !== "function"))) throw new MobileError("deletion_store_unavailable", "Account deletion storage is unavailable.", 503, true);
  const providedCapability = input.deletionCapability || input.capability || input.idempotencyKey || null;
  const operationId = input.operationId || (providedCapability ? `deletion:v1:${sha256(providedCapability).slice(0, 32)}` : randomOpaque("deletion:v1:", deps));
  const capability = providedCapability || operationId;
  const capabilityHash = sha256(capability);
  let existing = null;
  if (typeof store.readDeletionReceipt === "function") {
    existing = await store.readDeletionReceipt(scope, operationId);
    const storedCapabilityHash = existing && (existing.capabilityHash || existing.capability_hash);
    if (storedCapabilityHash && storedCapabilityHash !== capabilityHash) {
      throw new MobileError("deletion_capability_invalid", "The deletion replay capability is invalid.", 403);
    }
    if (existing && existing.status === "completed") return outputReceipt(existing, capability);
  }
  const previousCleanup = existing && (existing.providerCleanup || existing.provider_cleanup) || [];
  const started = {
    operationId, status: "incomplete", completedAt: null, providerCleanup: previousCleanup, capabilityHash,
  };
  if (!existing) await store.writeDeletionReceipt(scope, started);
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
    const receipt = { ...started, providerCleanup: mergeCleanup(previousCleanup, cleanup) };
    await store.writeDeletionReceipt(scope, receipt);
    throw new MobileError("deletion_incomplete", "Account deletion is incomplete because a provider connection could not be verified.", 502, true, { receipt: outputReceipt(receipt, capability) });
  }
  const completedAt = nowIso(deps);
  const providerCleanup = mergeCleanup(previousCleanup, cleanup);
  const receipt = { operationId, status: "completed", completedAt, providerCleanup, capabilityHash };
  if (typeof store.finalizeAccountDeletion === "function") {
    try {
      const finalized = await store.finalizeAccountDeletion(scope, {
        operationId, capabilityHash, providerCleanup,
        preserveIdempotencyKey: input.idempotencyKey || null,
      });
      return outputReceipt({ ...receipt, ...(finalized || {}) }, capability);
    } catch (error) {
      const incomplete = { ...started, providerCleanup };
      await store.writeDeletionReceipt(scope, incomplete).catch(() => {});
      throw new MobileError("deletion_incomplete", "Account data could not be finalized; the provider cleanup receipt remains resumable.", 503, true, {
        receipt: outputReceipt(incomplete, capability), cause: error && error.code ? error.code : "account_finalize_failed",
      });
    }
  }
  // Compatibility fallback for injected legacy stores. Production Supabase uses the atomic RPC above.
  try {
    await store.revokeAllSessions(scope);
    await store.deleteAccount(scope, { preserveIdempotencyKey: input.idempotencyKey || null });
  } catch (error) {
    const incomplete = { ...started, providerCleanup };
    await store.writeDeletionReceipt(scope, incomplete).catch(() => {});
    throw new MobileError("deletion_incomplete", "Account data could not be deleted; the provider cleanup receipt remains incomplete.", 503, true, { receipt: outputReceipt(incomplete, capability), cause: error && error.code ? error.code : "account_delete_failed" });
  }
  try {
    await store.writeDeletionReceipt(scope, receipt);
  } catch (error) {
    throw new MobileError("deletion_incomplete", "Account data was deleted but the completion receipt could not be stored.", 503, true, {
      receipt,
      cause: error && error.code ? error.code : "deletion_receipt_failed",
    });
  }
  return outputReceipt(receipt, capability);
}

module.exports = { deleteMobileAccount, cleanupResult, outputReceipt };
