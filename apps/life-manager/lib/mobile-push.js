"use strict";

const {
  ApnsError,
  invalidTokenResponse,
  normalizeEnvironment,
  validateDeviceToken,
} = require("./apns-client.js");
const { encodeCursor } = require("./mobile-outbox.js");

class MobilePushError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "MobilePushError";
    this.code = code;
    Object.assign(this, details);
  }
}

function requireScope(scope) {
  if (!scope || typeof scope.uid !== "string" || !scope.uid.trim()) {
    throw new MobilePushError("mobile_scope_required", "An authenticated mobile scope is required.");
  }
  return scope;
}

/**
 * A database sequence is the commit witness for lm_mobile_outbox. The sender
 * deliberately refuses a freshly-built semantic object without that witness:
 * notification delivery can never create or imply a chat message.
 */
function validateCommittedOutboxRow(row = {}) {
  if (!row || typeof row !== "object" || Array.isArray(row)) {
    throw new MobilePushError("mobile_outbox_uncommitted", "A committed semantic outbox row is required.");
  }
  if (row.committed === false || row.persisted === false) {
    throw new MobilePushError("mobile_outbox_uncommitted", "The semantic outbox row is not committed.");
  }
  const id = String(row.id || row.messageId || "").trim();
  if (!id) throw new MobilePushError("mobile_outbox_invalid", "The semantic outbox row needs a stable id.");
  const sequence = Number(row.sequence);
  if (!Number.isSafeInteger(sequence) || sequence <= 0) {
    throw new MobilePushError("mobile_outbox_uncommitted", "The semantic outbox row needs a committed sequence.");
  }
  const cursor = String(row.cursor || "").trim();
  if (!cursor) throw new MobilePushError("mobile_outbox_invalid", "The semantic outbox row needs an opaque cursor.");
  if (row.key !== undefined && (typeof row.key !== "string" || !row.key.trim())) {
    throw new MobilePushError("mobile_outbox_invalid", "The semantic outbox row key is invalid.");
  }
  return {
    id,
    sequence,
    cursor,
    ...(row.key === undefined ? {} : { key: row.key }),
  };
}

function isInvalidTokenResponse(result = {}) {
  return Boolean(result && (result.invalidToken === true || invalidTokenResponse(result)));
}

function deviceForSend(device = {}) {
  if (!device || typeof device !== "object" || Array.isArray(device)) {
    throw new MobilePushError("mobile_device_invalid", "The stored mobile device is invalid.");
  }
  const token = validateDeviceToken(device.token || device.deviceToken);
  const environment = normalizeEnvironment(device.environment);
  return {
    token,
    environment,
    locale: device.locale == null ? "en" : String(device.locale),
    deviceId: device.deviceId || device.device_id || null,
    uid: device.uid == null ? null : String(device.uid),
  };
}

function operation(deps, names) {
  for (const name of names) {
    if (typeof deps[name] === "function") return deps[name];
    if (deps.store && typeof deps.store[name] === "function") return deps.store[name].bind(deps.store);
  }
  return null;
}

function providerSend(apnsClient) {
  if (apnsClient && typeof apnsClient.sendChatMessage === "function") return apnsClient.sendChatMessage.bind(apnsClient);
  if (apnsClient && typeof apnsClient.sendNotification === "function") return apnsClient.sendNotification.bind(apnsClient);
  if (apnsClient && typeof apnsClient.send === "function") return apnsClient.send.bind(apnsClient);
  throw new MobilePushError("mobile_push_unavailable", "An APNs sender is required.");
}

function receiptFor(scope, row, device, providerResult = {}) {
  const result = providerResult && typeof providerResult === "object" ? providerResult : {};
  const status = result.status == null ? null : Number(result.status);
  const receipt = {
    uid: scope.uid,
    messageId: row.id,
    deviceId: device.deviceId,
    environment: device.environment,
    ok: result.ok === true,
    apnsId: result.apnsId == null ? null : String(result.apnsId),
    status: Number.isFinite(status) ? status : null,
    reason: result.reason == null ? null : String(result.reason),
    invalidToken: isInvalidTokenResponse(result),
  };
  if (result.timestamp != null) receipt.timestamp = result.timestamp;
  return receipt;
}

function providerFailure(error, device) {
  const value = error && typeof error === "object" ? error : {};
  const status = value.status == null ? null : Number(value.status);
  const reason = value.reason || value.code || value.message || "apns_push_failed";
  return {
    ok: false,
    status: Number.isFinite(status) ? status : null,
    apnsId: value.apnsId || value.apns_id || null,
    reason: String(reason),
    invalidToken: isInvalidTokenResponse({ status, reason, invalidToken: value.invalidToken }),
    environment: device.environment,
  };
}

function createMobilePushOrchestrator(deps = {}) {
  const listDevices = operation(deps, ["listDevices", "readDevices"]);
  const recordApnsResult = operation(deps, ["recordApnsResult", "recordDelivery", "recordPushResult"]);
  const removeDevice = operation(deps, ["removeDevice", "disableDevice", "deleteDevice"]);

  async function notifyCommittedOutbox(scopeInput, rowInput) {
    const scope = requireScope(scopeInput);
    const inputRow = rowInput || {};
    if (inputRow.uid != null && String(inputRow.uid) !== scope.uid) {
      throw new MobilePushError("mobile_outbox_scope_mismatch", "The outbox row does not belong to the authenticated scope.");
    }
    const row = validateCommittedOutboxRow(inputRow);
    if (!listDevices) throw new MobilePushError("mobile_device_store_unavailable", "Mobile device storage is unavailable.");
    const send = providerSend(deps.apnsClient || deps.client);
    const devices = await listDevices(scope);
    if (!Array.isArray(devices)) throw new MobilePushError("mobile_device_store_invalid", "Mobile device storage returned an invalid list.");

    const results = [];
    let delivered = 0;
    let removed = 0;
    for (const source of devices) {
      const device = deviceForSend(source);
      // Device rows are expected to come from an already scoped store. If a
      // test/durable adapter returns a tenant column, reject cross-tenant data
      // before any provider call; never infer scope from the token itself.
      if (device.uid != null && device.uid !== scope.uid) {
        throw new MobilePushError("mobile_device_scope_mismatch", "The mobile device does not belong to the authenticated scope.");
      }
      let providerResult;
      try {
        providerResult = await send({
          token: device.token,
          environment: device.environment,
          messageId: row.id,
          cursor: row.cursor,
          locale: device.locale,
        });
      } catch (error) {
        // A provider failure is a per-device receipt. It must not prevent the
        // remaining scoped devices from receiving the same committed message.
        providerResult = providerFailure(error, device);
      }
      const receipt = receiptFor(scope, row, device, providerResult);
      if (receipt.ok) delivered += 1;
      if (recordApnsResult) {
        try { await recordApnsResult(scope, receipt); } catch { /* the push job retains the retryable failure */ }
      }
      if (receipt.invalidToken) {
        if (!removeDevice) {
          throw new MobilePushError("mobile_device_cleanup_unavailable", "An invalid APNs token requires a device cleanup operation.", { receipt });
        }
        try {
          await removeDevice(scope, device.token, receipt.reason);
          removed += 1;
        } catch { /* keep the provider receipt; cleanup can be retried separately */ }
      }
      results.push(receipt);
    }
    return { messageId: row.id, attempted: results.length, delivered, removed, results };
  }

  return {
    notifyCommittedOutbox,
    sendCommittedOutboxMessage: notifyCommittedOutbox,
    sendCommittedOutboxRow: notifyCommittedOutbox,
  };
}

async function notifyCommittedOutbox(scope, row, deps = {}) {
  return createMobilePushOrchestrator(deps).notifyCommittedOutbox(scope, row);
}

function drainTimeout(options = {}) {
  const value = Number(options.jobTimeoutMs);
  return Number.isFinite(value) && value > 0 ? value : 30_000;
}

async function bounded(value, options = {}, timeoutOverride) {
  const timeoutMs = timeoutOverride === undefined ? drainTimeout(options) : timeoutOverride;
  const setTimer = options.setTimeoutImpl || options.setTimeout || setTimeout;
  const clearTimer = options.clearTimeoutImpl || options.clearTimeout || clearTimeout;
  let timer;
  try {
    return await new Promise((resolve, reject) => {
      timer = setTimer(() => reject(new MobilePushError("mobile_push_timeout", "The mobile push dispatch timed out.", { retryable: true })), timeoutMs);
      const work = typeof value === "function" ? Promise.resolve().then(value) : Promise.resolve(value);
      work.then(resolve, reject);
    });
  } finally {
    if (timer !== undefined) clearTimer(timer);
  }
}

/**
 * Drain committed semantic rows from durable jobs. Claiming is lease based, so
 * a process crash before provider send leaves the job eligible after the lease
 * expires; a terminal completion is never claimed again.
 */
async function drainMobilePushJobs(options = {}) {
  const store = options.store;
  if (!store || typeof store.listMobilePushJobs !== "function" || typeof store.claimMobilePushJob !== "function") {
    throw new MobilePushError("mobile_push_store_unavailable", "Durable mobile push storage is unavailable.");
  }
  const now = options.now === undefined ? Date.now() : options.now;
  const storageTimeoutMs = Number.isFinite(Number(options.storageTimeoutMs)) && Number(options.storageTimeoutMs) > 0
    ? Number(options.storageTimeoutMs) : 5_000;
  const storageOptions = { ...options, jobTimeoutMs: storageTimeoutMs };
  const listed = await bounded(
    () => store.listMobilePushJobs(options.scope || null, { now, limit: options.messageId ? Math.max(10, Number(options.maxJobs || 1)) : (options.maxJobs || options.limit || 10) }),
    storageOptions,
  );
  const jobs = options.messageId ? listed.filter((job) => job.messageId === options.messageId) : listed;
  const summary = { processed: 0, completed: 0, retried: 0 };
  for (const job of jobs) {
    const scope = { uid: job.uid };
    const claimed = await bounded(() => store.claimMobilePushJob(scope, job.messageId, { now, leaseMs: options.leaseMs }), storageOptions);
    if (!claimed) continue;
    summary.processed += 1;
    try {
      const rowSource = typeof store.readOutbox === "function"
        ? await bounded(() => store.readOutbox(scope, job.messageId), storageOptions)
        : null;
      if (!rowSource) throw new MobilePushError("mobile_outbox_missing", "The durable mobile outbox row is missing.");
      const row = {
        ...rowSource,
        id: rowSource.id || rowSource.messageId || job.messageId,
        sequence: Number(rowSource.sequence),
        cursor: rowSource.cursor || encodeCursor(Number(rowSource.sequence)),
      };
      if (!options.apnsClient) throw new MobilePushError("credentials_missing", "APNs credentials are not configured.", { retryable: true });
      const orchestrator = createMobilePushOrchestrator({
        apnsClient: options.apnsClient,
        store,
        listDevices: options.listDevices,
        recordApnsResult: options.recordApnsResult,
        removeDevice: options.removeDevice,
      });
      const result = await bounded(orchestrator.notifyCommittedOutbox(scope, row), options);
      const retryable = Array.isArray(result.results) && result.results.some((receipt) => !receipt.ok && !receipt.invalidToken);
      if (retryable) {
        await bounded(() => store.markMobilePushJobFailure(scope, job.messageId, result.results.find((receipt) => !receipt.ok && !receipt.invalidToken), { now }), storageOptions);
        summary.retried += 1;
      } else {
        await bounded(() => store.markMobilePushJobSuccess(scope, job.messageId, result), storageOptions);
        summary.completed += 1;
      }
    } catch (error) {
      await bounded(() => store.markMobilePushJobFailure(scope, job.messageId, error, { now }), storageOptions);
      summary.retried += 1;
    }
  }
  return summary;
}

module.exports = {
  MobilePushError,
  ApnsError,
  createMobilePushOrchestrator,
  drainMobilePushJobs,
  deviceForSend,
  isInvalidTokenResponse,
  notifyCommittedOutbox,
  sendCommittedOutboxMessage: notifyCommittedOutbox,
  validateCommittedOutboxRow,
};
