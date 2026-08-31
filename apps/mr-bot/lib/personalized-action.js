"use strict";

const { decideOpportunity } = require("./opportunity-engine");

function providerId(receipt) {
  return receipt && typeof receipt.provider_id === "string" && receipt.provider_id.trim()
    ? receipt.provider_id
    : null;
}

function selectManagedAccount(user, accounts) {
  if (user && typeof user.email === "string" && user.email.trim()) return user.email;
  const capable = (Array.isArray(accounts) ? accounts : []).filter((account) =>
    account
    && typeof account.email === "string"
    && account.email.trim()
    && Array.isArray(account.services)
    && account.services.includes("calendar")
    && account.services.includes("gmail"));
  return capable.length === 1 ? capable[0].email : null;
}

function hasCompletedAction(events) {
  const rows = Array.isArray(events) ? events : events?.items;
  return Array.isArray(rows) && rows.some((event) =>
    event && typeof event.id === "string" && event.id.trim());
}

function baseReceipt(candidate, decision) {
  return {
    schema_version: 1,
    candidate_id: candidate.id,
    decision: decision.decision,
    decision_reason: decision.reason,
    outcome: "not_executed",
    email_provider_id: null,
    email_message_id: null,
    calendar_provider_id: null,
    telegram_provider_id: null,
    honest_failure: false,
    approval_questions: 0,
  };
}

async function runPersonalizedAction(options) {
  const {
    intents,
    candidate,
    nowMs,
    executeEmail,
    createCalendarReport,
    sendTelegramReport,
  } = options;
  const decision = decideOpportunity(intents, candidate, nowMs);
  const receipt = baseReceipt(candidate, decision);
  if (decision.decision !== "act") return receipt;

  let email = null;
  let honestFailure = false;
  try {
    email = await executeEmail();
    if (!providerId(email)) throw new Error("missing provider receipt");
  } catch {
    honestFailure = true;
  }

  const calendar = await createCalendarReport({ honestFailure });
  const telegram = await sendTelegramReport({ honestFailure });
  return {
    ...receipt,
    outcome: honestFailure ? "reported_failure" : "completed",
    email_provider_id: providerId(email),
    email_message_id: !honestFailure
      && typeof email.message_id === "string"
      && /^<[^<>\s]+>$/.test(email.message_id)
      ? email.message_id
      : null,
    calendar_provider_id: providerId(calendar),
    telegram_provider_id: providerId(telegram),
    honest_failure: honestFailure,
  };
}

module.exports = { runPersonalizedAction, selectManagedAccount, hasCompletedAction };
