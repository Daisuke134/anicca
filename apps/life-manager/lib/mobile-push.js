"use strict";

const {
  ApnsError,
  invalidTokenResponse,
  normalizeEnvironment,
  validateDeviceToken,
} = require("./apns-client.js");

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
      const providerResult = await send({
        token: device.token,
        environment: device.environment,
        messageId: row.id,
        cursor: row.cursor,
        locale: device.locale,
      });
      const receipt = receiptFor(scope, row, device, providerResult);
      if (receipt.ok) delivered += 1;
      if (recordApnsResult) await recordApnsResult(scope, receipt);
      if (receipt.invalidToken) {
        if (!removeDevice) {
          throw new MobilePushError("mobile_device_cleanup_unavailable", "An invalid APNs token requires a device cleanup operation.", { receipt });
        }
        await removeDevice(scope, device.token, receipt.reason);
        removed += 1;
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

module.exports = {
  MobilePushError,
  ApnsError,
  createMobilePushOrchestrator,
  deviceForSend,
  isInvalidTokenResponse,
  notifyCommittedOutbox,
  sendCommittedOutboxMessage: notifyCommittedOutbox,
  validateCommittedOutboxRow,
};

