"use strict";

const RECONCILED_EFFECTS = new Set(["publish", "message", "money"]);

async function reconcileUnknownEffect(job, dependencies = {}) {
  if (!job || job.status !== "reconciling") {
    throw new Error("runtime job is not reconciling");
  }
  if (!RECONCILED_EFFECTS.has(job.effect_class)) {
    throw new Error("runtime effect class cannot be reconciled");
  }
  if (!job.effect_key) throw new Error("runtime effect key missing");
  const { adapter, store } = dependencies;
  if (!adapter || typeof adapter.inspectEffect !== "function") {
    throw new Error("runtime reconciliation adapter invalid");
  }
  if (!store || typeof store.resolveReconciliation !== "function") {
    throw new Error("runtime reconciliation store invalid");
  }

  const proof = await adapter.inspectEffect({
    tenantId: job.tenant_id,
    loopId: job.loop_id,
    effectClass: job.effect_class,
    effectKey: job.effect_key,
    jobId: job.job_id,
    attempt: job.attempt,
  });
  if (!proof || !["present", "absent", "unknown"].includes(proof.state)) {
    throw new Error("runtime adapter proof invalid");
  }
  if (proof.state === "unknown") {
    return { status: "reconciling", decision: "unknown" };
  }
  if (!proof.receipt || typeof proof.receipt !== "object" || Array.isArray(proof.receipt)) {
    throw new Error("runtime adapter proof receipt invalid");
  }

  return store.resolveReconciliation({
    tenantId: job.tenant_id,
    jobId: job.job_id,
    attempt: job.attempt,
    decision: proof.state,
    receipt: proof.receipt,
  });
}

module.exports = { reconcileUnknownEffect };
