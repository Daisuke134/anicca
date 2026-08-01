"use strict";

const CONTINUE = new Set([
  "approval_required",
  "cancelled",
  "conflict",
  "full",
  "not_eligible",
  "waitlist",
]);
const RECOVER = new Set([
  "inventory_incomplete",
  "login_required",
  "transport_unavailable",
]);
const EVENT_REF = /^luma-event:\/\/event\/[A-Za-z0-9_-]+$/;
const RECEIPT_REF = /^provider-receipt:\/\/luma\/[A-Za-z0-9._:~-]+$/;
const VERIFIED = new WeakSet();

function verified(value) {
  const result = Object.freeze(value);
  VERIFIED.add(result);
  return result;
}

function validCandidate(candidate) {
  if (!candidate || typeof candidate !== "object") return false;
  if (!EVENT_REF.test(String(candidate.event_ref || ""))) return false;
  try {
    const url = new URL(String(candidate.canonical_url || ""));
    return url.protocol === "https:"
      && ["luma.com", "www.luma.com", "lu.ma"].includes(url.hostname.toLowerCase());
  } catch {
    return false;
  }
}

async function runLumaCandidateSequence(options = {}) {
  const candidates = options.candidates;
  const attempt = options.attempt;
  if (!Array.isArray(candidates) || typeof attempt !== "function") {
    throw new Error("Luma candidate sequence invalid");
  }
  if (candidates.some((candidate) => !validCandidate(candidate))) {
    throw new Error("Luma candidate invalid");
  }

  const skipped = [];
  for (const candidate of candidates) {
    let outcome;
    try {
      outcome = await attempt(candidate);
    } catch {
      return verified({
        status: "recovery_required",
        reason: "adapter_failure",
        candidate,
        skipped: Object.freeze([...skipped]),
      });
    }
    const status = String(outcome && outcome.status || "").trim();
    if (status === "verified_registered" && RECEIPT_REF.test(
      String(outcome.receipt_ref || ""),
    )) {
      return verified({
        status: "booked",
        candidate,
        receipt_ref: String(outcome.receipt_ref),
        skipped: Object.freeze([...skipped]),
      });
    }
    if (CONTINUE.has(status)) {
      skipped.push(Object.freeze({ event_ref: candidate.event_ref, reason: status }));
      continue;
    }
    if (RECOVER.has(status)) {
      return verified({
        status: "recovery_required",
        reason: status,
        candidate,
        skipped: Object.freeze([...skipped]),
      });
    }
    return verified({
      status: "reconciliation_required",
      reason: status === "unknown_effect" ? "unknown_effect" : "unverified_result",
      candidate,
      skipped: Object.freeze([...skipped]),
    });
  }
  return verified({
    status: "next_provider_required",
    reason: "luma_candidates_exhausted",
    skipped: Object.freeze([...skipped]),
  });
}

function isVerifiedLumaCandidateSequence(value) {
  return Boolean(value && typeof value === "object" && VERIFIED.has(value));
}

module.exports = {
  isVerifiedLumaCandidateSequence,
  runLumaCandidateSequence,
};
