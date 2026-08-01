"use strict";

const { runLumaCandidateSequence } = require("./luma-candidate-loop.js");

const CONNPASS_RECEIPT = /^provider-receipt:\/\/connpass\/[A-Za-z0-9._:~-]+$/;

async function runEventProviderRouting(options = {}) {
  const date = String(options.date || "").trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || typeof options.runConnpass !== "function") {
    throw new Error("event provider routing invalid");
  }
  const luma = await runLumaCandidateSequence({ candidates: options.lumaCandidates, attempt: options.attemptLuma });
  if (luma.status === "booked") {
    return Object.freeze({ ...luma, provider: "luma", date, connpass_attempted: false });
  }
  if (luma.status !== "next_provider_required" || luma.reason !== "luma_candidates_exhausted") {
    return Object.freeze({ ...luma, provider: "luma", date, connpass_attempted: false });
  }

  const connpass = await options.runConnpass(Object.freeze({ date }));
  const status = String(connpass && connpass.status || "").trim();
  if (status === "booked") {
    const receiptRef = String(connpass.receipt_ref || "").trim();
    if (!CONNPASS_RECEIPT.test(receiptRef)) throw new Error("connpass booking receipt invalid");
    return Object.freeze({
      status: "booked", provider: "connpass", date, receipt_ref: receiptRef,
      luma_candidates_exhausted: true, connpass_attempted: true,
    });
  }
  if (status === "disabled" && connpass.reason === "api_key_unavailable") {
    return Object.freeze({
      status: "coverage_open", date, reason: "api_key_unavailable",
      luma_candidates_exhausted: true, connpass_attempted: true,
    });
  }
  if (status === "exhausted") {
    return Object.freeze({
      status: "coverage_open", date, reason: "provider_candidates_exhausted",
      luma_candidates_exhausted: true, connpass_attempted: true,
    });
  }
  if (status === "unknown_effect") {
    return Object.freeze({
      status: "reconciliation_required", provider: "connpass", date,
      reason: "unknown_effect", luma_candidates_exhausted: true, connpass_attempted: true,
    });
  }
  if (status === "recovery_required") {
    return Object.freeze({
      status: "recovery_required", provider: "connpass", date,
      reason: String(connpass.reason || "provider_recovery_required"),
      luma_candidates_exhausted: true, connpass_attempted: true,
    });
  }
  throw new Error("connpass routing result invalid");
}

module.exports = { runEventProviderRouting };
