// REQ-305 edge case (FIND-003, Phase-3 sprint-2 round-2 review): "the ledger write ('active')
// succeeds but the SUBSEQUENT registry-append write fails for a TRANSIENT reason ... THE SYSTEM SHALL
// retry the registry-append on the NEXT wake before any further spawn evaluation runs". Reuses
// ledger.js's own generic (file, row) read/append primitives -- the SAME "reuse, never reimplement"
// convention shelter-cost-ledger.js already establishes -- for a durable, retryable queue. One row per
// queue/resolve event; the LAST row per child_id wins (the SAME last-row-wins convention children.jsonl's
// own `status` field already establishes, read via deriveOutstandingRegistryAppends below).
const { readChildren, appendChild } = require("./ledger.js");

function readPendingRegistryAppends(file) {
  return readChildren(file);
}

function queuePendingRegistryAppend(file, { childId, citizenRecord, citizensRegistryFile, queuedMs, error }) {
  return appendChild(file, {
    child_id: childId,
    citizen_record: citizenRecord,
    citizens_registry_file: citizensRegistryFile,
    queued_ms: queuedMs,
    status: "pending",
    error,
  });
}

function resolvePendingRegistryAppend(file, childId) {
  return appendChild(file, { child_id: childId, status: "resolved" });
}

// Pure: last row per child_id wins. Returns the still-outstanding queue entries (status:"pending" as of
// their own last row) -- never a row already superseded by a later "resolved" row for the SAME child_id.
function deriveOutstandingRegistryAppends(rows) {
  const lastByChild = new Map();
  for (const row of rows) {
    if (row && typeof row.child_id === "string") lastByChild.set(row.child_id, row);
  }
  return [...lastByChild.values()].filter((row) => row.status === "pending");
}

module.exports = {
  readPendingRegistryAppends,
  queuePendingRegistryAppend,
  resolvePendingRegistryAppend,
  deriveOutstandingRegistryAppends,
};
