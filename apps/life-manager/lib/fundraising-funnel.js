"use strict";

const { containsSensitiveDisplayValue } = require("./panel-display-policy.js");

const ROOT_KEYS = Object.freeze(["events", "schema_version"]);
const EVENT_KEYS = Object.freeze(["event_kind", "funder_id", "occurred_at", "source_id"]);
const EVENT_KINDS = new Set([
  "application", "confirmation", "interview", "offer", "rejected", "funded",
]);
const SOURCE_ID = /^funder-ledger:[0-9a-f]{64}$/;
const FUNDER_ID = /^[a-z0-9][a-z0-9-]{0,127}$/;
const PROGRAM_NAMES = Object.freeze({ "yc-fall-2026": "YC Fall 2026" });

function fail() {
  throw new Error("fundraising funnel invalid");
}

function record(value) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function exactKeys(value, expected) {
  if (!record(value)) return false;
  const actual = Object.keys(value).sort();
  return actual.length === expected.length
    && actual.every((key, index) => key === expected[index]);
}

function canonicalInstant(value) {
  if (typeof value !== "string") fail();
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) fail();
  return new Date(parsed).toISOString();
}

function stage(id, occurredAt, extra = {}) {
  return Object.freeze({
    id,
    state: occurredAt === null ? "pending" : "reached",
    ...extra,
    occurred_at: occurredAt,
  });
}

function projectApplication(sourceId, events) {
  const byKind = new Map();
  let funderId = "";
  for (const event of events) {
    if (!exactKeys(event, EVENT_KEYS)
      || !FUNDER_ID.test(String(event.funder_id || ""))
      || event.source_id !== sourceId
      || !EVENT_KINDS.has(event.event_kind)
      || containsSensitiveDisplayValue(event)) fail();
    if (funderId && funderId !== event.funder_id) fail();
    funderId = event.funder_id;
    if (byKind.has(event.event_kind)) fail();
    byKind.set(event.event_kind, canonicalInstant(event.occurred_at));
  }
  if (!byKind.has("application")) fail();

  const time = (kind) => byKind.get(kind) || null;
  const ordered = ["application", "confirmation", "interview", "offer", "funded"];
  let previous = null;
  for (const kind of ordered) {
    const current = time(kind);
    if (current !== null) {
      if (previous === null && kind !== "application") fail();
      if (previous !== null && Date.parse(current) < Date.parse(previous)) fail();
      previous = current;
    } else if (ordered.slice(ordered.indexOf(kind) + 1).some((later) => time(later))) fail();
  }
  const rejectedAt = time("rejected");
  if (rejectedAt !== null) {
    if (time("confirmation") === null
      || Date.parse(rejectedAt) < Date.parse(time("confirmation"))
      || (previous !== null && Date.parse(rejectedAt) < Date.parse(previous))
      || time("offer") !== null || time("funded") !== null) fail();
  }

  const currentStage = time("funded") ? "funded"
    : time("offer") ? "offer"
      : time("interview") ? "interview"
        : time("confirmation") ? "confirmation" : "application";
  const terminal = rejectedAt ? "rejected" : time("funded") ? "funded" : null;
  const allTimes = [...byKind.values()];
  const lastEventAt = allTimes.sort((a, b) => Date.parse(b) - Date.parse(a))[0];
  const decisionAt = rejectedAt || time("offer");
  const decisionOutcome = rejectedAt ? "rejected" : time("offer") ? "offer_received" : null;
  return Object.freeze({
    sourceId,
    dto: Object.freeze({
      program: PROGRAM_NAMES[funderId] || funderId,
      current_stage: currentStage,
      terminal_outcome: terminal,
      last_event_at: lastEventAt,
      stages: Object.freeze([
        stage("application", time("application")),
        stage("confirmation", time("confirmation")),
        stage("interview", time("interview")),
        stage("decision", decisionAt, { outcome: decisionOutcome }),
        stage("funded", time("funded")),
      ]),
    }),
    kinds: new Set(byKind.keys()),
  });
}

function buildFundraisingFunnel(candidate) {
  if (!exactKeys(candidate, ROOT_KEYS)
    || candidate.schema_version !== 1
    || !Array.isArray(candidate.events)
    || candidate.events.length > 10_000
    || containsSensitiveDisplayValue(candidate)) fail();
  const grouped = new Map();
  for (const event of candidate.events) {
    if (!record(event) || !SOURCE_ID.test(String(event.source_id || ""))) fail();
    const list = grouped.get(event.source_id) || [];
    list.push(event);
    grouped.set(event.source_id, list);
  }
  const projected = [...grouped.entries()].map(([sourceId, events]) =>
    projectApplication(sourceId, events));
  projected.sort((left, right) =>
    left.dto.program.localeCompare(right.dto.program)
      || left.sourceId.localeCompare(right.sourceId));
  const summary = {
    application: projected.length,
    confirmation: 0,
    interview: 0,
    offer: 0,
    rejected: 0,
    funded: 0,
  };
  for (const item of projected) {
    for (const kind of ["confirmation", "interview", "offer", "rejected", "funded"]) {
      if (item.kinds.has(kind)) summary[kind] += 1;
    }
  }
  return Object.freeze({
    schema_version: 1,
    summary: Object.freeze(summary),
    applications: Object.freeze(projected.map((item) => item.dto)),
  });
}

function validateFundraisingFunnel(value) {
  const summaryKeys = ["application", "confirmation", "funded", "interview", "offer", "rejected"];
  if (!exactKeys(value, ["applications", "schema_version", "summary"])
    || value.schema_version !== 1
    || !exactKeys(value.summary, summaryKeys)
    || summaryKeys.some((key) => !Number.isSafeInteger(value.summary[key]) || value.summary[key] < 0)
    || !Array.isArray(value.applications)
    || value.applications.length !== value.summary.application
    || containsSensitiveDisplayValue(value)) fail();
  const counts = { confirmation: 0, interview: 0, offer: 0, rejected: 0, funded: 0 };
  for (const application of value.applications) {
    if (!exactKeys(application, [
      "current_stage", "last_event_at", "program", "stages", "terminal_outcome",
    ]) || typeof application.program !== "string" || !application.program.trim()
      || application.program.length > 200
      || !new Set(["application", "confirmation", "interview", "offer", "funded"])
        .has(application.current_stage)
      || !new Set([null, "rejected", "funded"]).has(application.terminal_outcome)
      || canonicalInstant(application.last_event_at) !== application.last_event_at
      || !Array.isArray(application.stages) || application.stages.length !== 5) fail();
    const expectedIds = ["application", "confirmation", "interview", "decision", "funded"];
    for (let index = 0; index < expectedIds.length; index += 1) {
      const item = application.stages[index];
      const decision = expectedIds[index] === "decision";
      if (!exactKeys(item, decision
        ? ["id", "occurred_at", "outcome", "state"]
        : ["id", "occurred_at", "state"])
        || item.id !== expectedIds[index]
        || !new Set(["pending", "reached"]).has(item.state)
        || (item.state === "pending" ? item.occurred_at !== null
          : canonicalInstant(item.occurred_at) !== item.occurred_at)) fail();
      if (decision && !new Set([null, "offer_received", "rejected"]).has(item.outcome)) fail();
    }
    const [applicationStage, confirmation, interview, decision, funded] = application.stages;
    const expectedCurrentStage = funded.state === "reached" ? "funded"
      : decision.outcome === "offer_received" ? "offer"
        : interview.state === "reached" ? "interview"
          : confirmation.state === "reached" ? "confirmation" : "application";
    const reachedTimes = application.stages
      .filter((item) => item.state === "reached")
      .map((item) => item.occurred_at);
    const lastObservedAt = [...reachedTimes]
      .sort((left, right) => Date.parse(right) - Date.parse(left))[0];
    if (applicationStage.state !== "reached"
      || (interview.state === "reached" && confirmation.state !== "reached")
      || (decision.outcome === "offer_received" && interview.state !== "reached")
      || (funded.state === "reached" && decision.outcome !== "offer_received")
      || (decision.outcome === "rejected" && funded.state === "reached")
      || (decision.state === "pending") !== (decision.outcome === null)
      || (application.terminal_outcome === "rejected") !== (decision.outcome === "rejected")
      || (application.terminal_outcome === "funded") !== (funded.state === "reached")
      || application.current_stage !== expectedCurrentStage
      || application.last_event_at !== lastObservedAt) fail();
    for (let index = 1; index < reachedTimes.length; index += 1) {
      if (Date.parse(reachedTimes[index]) < Date.parse(reachedTimes[index - 1])) fail();
    }
    if (confirmation.state === "reached") counts.confirmation += 1;
    if (interview.state === "reached") counts.interview += 1;
    if (decision.outcome === "offer_received") counts.offer += 1;
    if (decision.outcome === "rejected") counts.rejected += 1;
    if (funded.state === "reached") counts.funded += 1;
  }
  for (const key of Object.keys(counts)) if (counts[key] !== value.summary[key]) fail();
  return value;
}

module.exports = { buildFundraisingFunnel, validateFundraisingFunnel };
