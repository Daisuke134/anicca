"use strict";

const { createHash } = require("node:crypto");

const {
  createPreparedFence,
  markEffectAttempted,
  recordOperationReadback,
} = require("./yc-typed-update.js");
const { persistPreparedFence, replaceFence } = require("./yc-typed-update-store.js");

const SHA = /^[0-9a-f]{64}$/;
function fail(reason) { throw new Error(`YC typed update executor ${reason}`); }
function unknownDigest(operationId) {
  return createHash("sha256").update(`unknown_effect:${operationId}`, "utf8").digest("hex");
}

async function executeYcTypedUpdateOperation(input = {}) {
  const { plan, operationId, fenceFile, adapter, now = () => new Date().toISOString() } = input;
  if (!adapter || typeof adapter.apply !== "function" || typeof adapter.readback !== "function") fail("adapter invalid");
  if (typeof fenceFile !== "string" || !fenceFile) fail("fence path invalid");

  const operation = plan && Array.isArray(plan.operations)
    ? plan.operations.find((candidate) => candidate.operation_id === operationId)
    : null;
  if (!operation || operation.disposition !== "execute") fail("operation invalid");

  const prepared = createPreparedFence(plan, operationId, { at: now() });
  persistPreparedFence(fenceFile, prepared);

  const attempted = markEffectAttempted(prepared, { at: now() });
  replaceFence(fenceFile, prepared.fence_digest, attempted);

  let applyFailed = false;
  try {
    await adapter.apply(operation);
  } catch {
    applyFailed = true;
  }

  let observed = null;
  try {
    observed = await adapter.readback(operation);
  } catch {
    observed = null;
  }

  let result = "unknown_effect";
  let readbackDigest = unknownDigest(operation.operation_id);
  if (observed && ["confirmed", "not_applied"].includes(observed.result) && SHA.test(String(observed.readback_digest || ""))) {
    if (observed.result === "confirmed" && observed.readback_digest === operation.expected_readback_digest) {
      result = "confirmed";
      readbackDigest = observed.readback_digest;
    } else if (observed.result === "not_applied") {
      result = "not_applied";
      readbackDigest = observed.readback_digest;
    } else {
      readbackDigest = observed.readback_digest;
    }
  }

  const terminal = recordOperationReadback(attempted, { at: now(), result, readback_digest: readbackDigest });
  replaceFence(fenceFile, attempted.fence_digest, terminal);
  if (terminal.state === "unknown_effect" || (applyFailed && terminal.state !== "confirmed")) fail("effect outcome unknown");
  return terminal;
}

module.exports = { executeYcTypedUpdateOperation };
