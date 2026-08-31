"use strict";

const {
  CAPABILITY,
  LOOP_ID,
  buildMarketplaceApplicationJob,
  marketplaceApplicationContract,
} = require("./marketplace-application-job.js");
const {
  runMarketplaceApplicationEffect,
} = require("./marketplace-application-effect.js");

const ADAPTER_ID = "marketplace-application";

function createMarketplaceApplicationLoopAdapter(deps = {}) {
  return Object.freeze({
    async plan(context = {}) {
      return [buildMarketplaceApplicationJob(context)];
    },
    execute(job, services = {}) {
      const runtime = { ...deps, ...services };
      return runMarketplaceApplicationEffect(job, {
        inspectApplication: runtime.inspectApplication,
        executeOnce: runtime.executeBoundedApplication,
        verifyReceipt: runtime.verifyReceipt,
      });
    },
    async reconcile(effect) {
      if (typeof deps.inspectEffect !== "function") return { state: "unknown" };
      try {
        const proof = await deps.inspectEffect(effect);
        if (!proof || !["present", "absent"].includes(proof.state)) return { state: "unknown" };
        if (!proof.receipt || typeof proof.receipt !== "object" || Array.isArray(proof.receipt)) {
          return { state: "unknown" };
        }
        return proof;
      } catch {
        return { state: "unknown" };
      }
    },
    verify(receipt, job) {
      if (typeof deps.verifyReceipt !== "function") return false;
      try {
        const verified = deps.verifyReceipt(receipt, marketplaceApplicationContract(job));
        return verified === true || verified === receipt;
      } catch {
        return false;
      }
    },
    report(receipt) {
      if (
        !receipt || receipt.record_type !== "application_receipt"
        || receipt.status !== "verified" || typeof receipt.platform !== "string"
        || typeof receipt.application_external_id !== "string"
        || typeof receipt.observed_at !== "string"
      ) throw new Error("marketplace application receipt invalid");
      return Object.freeze({
        status: receipt.status,
        platform: receipt.platform,
        application_external_id: receipt.application_external_id,
        observed_at: receipt.observed_at,
      });
    },
  });
}

module.exports = {
  ADAPTER_ID,
  CAPABILITY,
  LOOP_ID,
  createMarketplaceApplicationLoopAdapter,
};
