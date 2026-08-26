"use strict";

const { isVerifiedEventTalkOpportunity } = require("./event-talk-opportunity.js");
const { isVerifiedGroundedTalkPack } = require("./grounded-talk-pack.js");

const ALLOWED_FIELDS = new Set(["title", "abstract", "bio", "application_reason", "product_demo_summary"]);
const BLOCKERS = new Set(["payment", "captcha", "identity_verification"]);
const RECEIPT = /^provider-receipt:\/\/[a-z0-9._~:/?#@!$&'()*+,;=%-]{1,950}$/i;

function invalid() { throw new Error("talk application workflow invalid"); }

function createTalkApplicationWorkflow(options = {}) {
  const inspectForm = options.inspectForm;
  const fillFields = options.fillFields;
  const clickSubmit = options.clickSubmit;
  const readProviderState = options.readProviderState;
  if ([inspectForm, fillFields, clickSubmit, readProviderState].some((fn) => typeof fn !== "function")) invalid();
  return Object.freeze({
    async run(input = {}) {
      const candidate = input.candidate;
      if (!input.page || typeof input.page !== "object" || !candidate || typeof candidate !== "object"
        || !isVerifiedEventTalkOpportunity(candidate.talk_opportunity)
        || candidate.talk_opportunity.should_create_talk_application !== true
        || !isVerifiedGroundedTalkPack(candidate.talk_pack)) invalid();
      const inspection = await inspectForm({ page: input.page, applicationUrl: candidate.talk_opportunity.application_url });
      if (!inspection || typeof inspection !== "object" || Array.isArray(inspection)
        || Object.keys(inspection).sort().join(",") !== "blocking_flags,required_fields"
        || !Array.isArray(inspection.required_fields) || !Array.isArray(inspection.blocking_flags)
        || new Set(inspection.required_fields).size !== inspection.required_fields.length
        || new Set(inspection.blocking_flags).size !== inspection.blocking_flags.length) invalid();
      const blocker = inspection.blocking_flags.find((flag) => BLOCKERS.has(flag));
      if (blocker) return Object.freeze({ status: "human_action_required", safe_reason: blocker });
      if (inspection.blocking_flags.length > 0
        || inspection.required_fields.some((field) => !ALLOWED_FIELDS.has(field))) {
        return Object.freeze({ status: "human_action_required", safe_reason: "unknown_required_field" });
      }
      const values = Object.freeze(Object.fromEntries(
        inspection.required_fields.map((field) => [field, candidate.talk_pack[field]]),
      ));
      if (Object.values(values).some((value) => typeof value !== "string" || !value.trim())) invalid();
      await fillFields({ page: input.page, values });
      await clickSubmit({ page: input.page });
      const state = await readProviderState({ page: input.page, candidate });
      if (state && state.status === "provider_verified" && RECEIPT.test(String(state.receipt_ref || ""))) {
        return Object.freeze({ status: "provider_verified", receipt_ref: state.receipt_ref });
      }
      return Object.freeze({ status: "submitted", safe_reason: "provider_readback_unavailable" });
    },
  });
}

module.exports = { createTalkApplicationWorkflow };
