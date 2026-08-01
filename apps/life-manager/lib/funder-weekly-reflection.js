"use strict";

const { createHash } = require("node:crypto");

const DIGEST = /^[0-9a-f]{64}$/;
const IDENTIFIER = /^[a-z0-9][a-z0-9._:-]{0,191}$/i;
const LEARNABLE = new Set([
  "reply_received", "rejected", "meeting_requested", "offer_received", "funded",
]);
const RESULT_STATUSES = new Set(["confirmed", "delivery_failed", ...LEARNABLE]);
const EXPOSURE_KINDS = new Set(["submission", "outreach"]);
const VERIFIED = new WeakSet();
const JST_OFFSET_MS = 9 * 60 * 60 * 1000;

const sha = (value) => createHash("sha256").update(String(value), "utf8").digest("hex");
const fail = () => { throw new Error("funder weekly reflection invalid"); };

function exact(value, keys) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value))
    && Object.keys(value).sort().join("\0") === [...keys].sort().join("\0");
}

function canonicalInstant(value) {
  const ms = Date.parse(String(value || ""));
  if (!Number.isFinite(ms)) fail();
  return new Date(ms).toISOString();
}

function tokyoReflectionWeek(value) {
  const nowMs = Date.parse(String(value || ""));
  if (!Number.isFinite(nowMs)) fail();
  const local = new Date(nowMs + JST_OFFSET_MS);
  const localMidnightUtc = Date.UTC(
    local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate(),
  );
  const daysSinceMonday = (local.getUTCDay() + 6) % 7;
  const startMs = localMidnightUtc - (daysSinceMonday * 86_400_000) - JST_OFFSET_MS;
  const weekStart = new Date(startMs).toISOString();
  const weekEnd = new Date(startMs + (6 * 86_400_000) + (20 * 60 * 60 * 1000)
    + (15 * 60 * 1000)).toISOString();
  const keyDate = new Date(startMs + JST_OFFSET_MS);
  const weekKey = [
    keyDate.getUTCFullYear(),
    String(keyDate.getUTCMonth() + 1).padStart(2, "0"),
    String(keyDate.getUTCDate()).padStart(2, "0"),
  ].join("-");
  return Object.freeze({ week_key: weekKey, week_start: weekStart, week_end: weekEnd });
}

function latestCompletedTokyoReflectionWeek(value) {
  const instant = canonicalInstant(value);
  const current = tokyoReflectionWeek(instant);
  if (Date.parse(instant) >= Date.parse(current.week_end)) return current;
  return tokyoReflectionWeek(new Date(Date.parse(current.week_start) - 1).toISOString());
}

function validateExplicitWeek(value, reflectedAt) {
  if (!exact(value, ["week_key", "week_start", "week_end"])) fail();
  const start = canonicalInstant(value.week_start);
  const expected = tokyoReflectionWeek(new Date(Date.parse(start) + 1).toISOString());
  if (value.week_key !== expected.week_key || value.week_start !== expected.week_start
    || value.week_end !== expected.week_end || Date.parse(reflectedAt) < Date.parse(value.week_end)) fail();
  return expected;
}

function normalizeExposures(values, reflectedMs) {
  if (!Array.isArray(values) || values.length > 10_000) fail();
  const seen = new Set();
  const normalized = values.map((item) => {
    if (!exact(item, [
      "exposure_id", "candidate_id", "exposure_kind", "occurred_at",
      "subject_sha256", "body_sha256",
    ]) || !IDENTIFIER.test(String(item.exposure_id || ""))
      || !IDENTIFIER.test(String(item.candidate_id || ""))
      || !EXPOSURE_KINDS.has(item.exposure_kind)
      || !DIGEST.test(String(item.subject_sha256 || ""))
      || !DIGEST.test(String(item.body_sha256 || ""))) fail();
    const occurredAt = canonicalInstant(item.occurred_at);
    if (Date.parse(occurredAt) > reflectedMs || seen.has(item.exposure_id)) fail();
    seen.add(item.exposure_id);
    return Object.freeze({ ...item, occurred_at: occurredAt });
  });
  normalized.sort((a, b) => a.exposure_id.localeCompare(b.exposure_id));
  return normalized;
}

function normalizeResults(values, exposures, week) {
  if (!Array.isArray(values) || values.length > 10_000) fail();
  const exposureById = new Map(exposures.map((item) => [item.exposure_id, item]));
  const seen = new Set();
  const normalized = values.map((item) => {
    if (!exact(item, ["result_id", "exposure_id", "candidate_id", "status", "observed_at"])
      || !IDENTIFIER.test(String(item.result_id || ""))
      || !IDENTIFIER.test(String(item.exposure_id || ""))
      || !IDENTIFIER.test(String(item.candidate_id || ""))
      || !RESULT_STATUSES.has(item.status) || seen.has(item.result_id)) fail();
    const observedAt = canonicalInstant(item.observed_at);
    const exposure = exposureById.get(item.exposure_id);
    if (!exposure || exposure.candidate_id !== item.candidate_id
      || Date.parse(observedAt) < Date.parse(exposure.occurred_at)
      || (Date.parse(observedAt) < Date.parse(week.week_start) && !LEARNABLE.has(item.status))
      || Date.parse(observedAt) >= Date.parse(week.week_end)) fail();
    seen.add(item.result_id);
    return Object.freeze({ ...item, observed_at: observedAt });
  });
  normalized.sort((a, b) => a.result_id.localeCompare(b.result_id));
  return normalized;
}

function normalizeCandidates(values) {
  if (!Array.isArray(values) || values.length > 1_000
    || values.some((item) => !IDENTIFIER.test(String(item || "")))
    || new Set(values).size !== values.length) fail();
  return [...values];
}

function sameSet(left, right) {
  return left.length === right.length
    && [...left].sort().every((value, index) => value === [...right].sort()[index]);
}

function validateJudgment(judgment, outcomes, candidates) {
  if (!exact(judgment, [
    "kind", "decision", "summary", "rationale", "used_result_ids",
    "ranked_candidate_ids", "pitch_directives",
  ]) || judgment.kind !== "agent_judgment"
    || !new Set(["change", "hold"]).has(judgment.decision)) fail();
  const summary = String(judgment.summary || "").trim();
  const rationale = String(judgment.rationale || "").trim();
  const outcomeIds = outcomes.map((item) => item.result_id);
  if (!summary || summary.length > 4_000 || !rationale || rationale.length > 4_000
    || !Array.isArray(judgment.used_result_ids)
    || new Set(judgment.used_result_ids).size !== judgment.used_result_ids.length
    || !sameSet(judgment.used_result_ids, outcomeIds)
    || !Array.isArray(judgment.ranked_candidate_ids)
    || !Array.isArray(judgment.pitch_directives)) fail();

  if (judgment.decision === "hold") {
    if (judgment.ranked_candidate_ids.length !== 0 || judgment.pitch_directives.length !== 0) fail();
    return {
      decision: "hold",
      reason: "agent_hold",
      summary_sha256: sha(summary),
      rationale_sha256: sha(rationale),
      outcome_result_ids: [...judgment.used_result_ids].sort(),
      ranked_candidate_ids: [],
      pitch_directives: [],
    };
  }

  if (candidates.length < 1 || !sameSet(judgment.ranked_candidate_ids, candidates)
    || judgment.pitch_directives.length !== candidates.length) fail();
  const directiveByCandidate = new Set();
  const pitchDirectives = judgment.pitch_directives.map((item) => {
    if (!exact(item, ["candidate_id", "directive", "outcome_result_ids"])
      || !candidates.includes(item.candidate_id) || directiveByCandidate.has(item.candidate_id)) fail();
    const directive = String(item.directive || "").trim();
    if (!directive || directive.length > 240 || directive.includes("\n")
      || directive.split(/\s+/).filter(Boolean).length > 24
      || !Array.isArray(item.outcome_result_ids)
      || item.outcome_result_ids.length < 1
      || new Set(item.outcome_result_ids).size !== item.outcome_result_ids.length
      || item.outcome_result_ids.some((id) => !outcomeIds.includes(id))) fail();
    directiveByCandidate.add(item.candidate_id);
    return Object.freeze({
      candidate_id: item.candidate_id,
      directive,
      directive_sha256: sha(directive),
      outcome_result_ids: Object.freeze([...item.outcome_result_ids].sort()),
    });
  });
  pitchDirectives.sort((a, b) => (
    judgment.ranked_candidate_ids.indexOf(a.candidate_id)
      - judgment.ranked_candidate_ids.indexOf(b.candidate_id)
  ));
  return {
    decision: "change",
    reason: "agent_revision",
    summary_sha256: sha(summary),
    rationale_sha256: sha(rationale),
    outcome_result_ids: [...judgment.used_result_ids].sort(),
    ranked_candidate_ids: [...judgment.ranked_candidate_ids],
    pitch_directives: pitchDirectives,
  };
}

function buildFunderWeeklyReflection(input = {}) {
  const tenantId = String(input.tenantId || "").trim();
  const reflectedAt = canonicalInstant(input.reflectedAt);
  const reflectedMs = Date.parse(reflectedAt);
  if (!IDENTIFIER.test(tenantId)) fail();
  const week = input.week === undefined
    ? latestCompletedTokyoReflectionWeek(reflectedAt)
    : validateExplicitWeek(input.week, reflectedAt);
  const exposures = normalizeExposures(input.exposures, reflectedMs);
  const results = normalizeResults(input.results, exposures, week);
  const candidates = normalizeCandidates(input.candidates);
  const outcomes = results.filter((item) => LEARNABLE.has(item.status));
  const snapshotDigest = sha(JSON.stringify({
    tenant_id: tenantId,
    week_start: week.week_start,
    week_end: week.week_end,
    exposures,
    results,
    candidates: [...candidates].sort(),
  }));
  const revision = outcomes.length === 0 ? {
    decision: "hold",
    reason: "insufficient_outcomes",
    summary_sha256: sha("No verified reply, meeting, rejection, offer, or funding outcome in this week."),
    rationale_sha256: sha("Preserve the current target order and pitch until a typed outcome exists."),
    outcome_result_ids: [],
    ranked_candidate_ids: [],
    pitch_directives: [],
  } : validateJudgment(input.judgment, outcomes, candidates);
  const seed = {
    schema_version: 1,
    tenant_id: tenantId,
    week_key: week.week_key,
    week_start: week.week_start,
    week_end: week.week_end,
    reflected_at: reflectedAt,
    snapshot_digest: snapshotDigest,
    ...revision,
  };
  const value = Object.freeze({
    ...seed,
    reflection_id: `funder-weekly-reflection:${sha(JSON.stringify(seed))}`,
    outcome_result_ids: Object.freeze([...seed.outcome_result_ids]),
    ranked_candidate_ids: Object.freeze([...seed.ranked_candidate_ids]),
    pitch_directives: Object.freeze([...seed.pitch_directives]),
  });
  VERIFIED.add(value);
  return value;
}

function isVerifiedFunderWeeklyReflection(value) {
  return Boolean(value && VERIFIED.has(value));
}

function adoptPersistedFunderWeeklyReflection(row) {
  const keys = [
    "schema_version", "tenant_id", "week_key", "week_start", "week_end", "reflected_at",
    "snapshot_digest", "decision", "reason", "summary_sha256", "rationale_sha256",
    "outcome_result_ids", "ranked_candidate_ids", "pitch_directives", "reflection_id",
  ];
  if (!exact(row, keys) || row.schema_version !== 1
    || !IDENTIFIER.test(String(row.tenant_id || "")) || !/^\d{4}-\d{2}-\d{2}$/.test(String(row.week_key || ""))
    || canonicalInstant(row.week_start) !== row.week_start
    || canonicalInstant(row.week_end) !== row.week_end
    || canonicalInstant(row.reflected_at) !== row.reflected_at
    || !DIGEST.test(String(row.snapshot_digest || ""))
    || !DIGEST.test(String(row.summary_sha256 || ""))
    || !DIGEST.test(String(row.rationale_sha256 || ""))
    || !new Set(["hold", "change"]).has(row.decision)
    || !new Set(["insufficient_outcomes", "agent_hold", "agent_revision"]).has(row.reason)
    || !Array.isArray(row.outcome_result_ids) || !Array.isArray(row.ranked_candidate_ids)
    || !Array.isArray(row.pitch_directives)) fail();
  if ((row.decision === "change") !== (row.reason === "agent_revision")
    || (row.reason === "insufficient_outcomes" && row.outcome_result_ids.length !== 0)
    || (row.decision === "hold" && (row.ranked_candidate_ids.length || row.pitch_directives.length))) fail();
  if (new Set(row.outcome_result_ids).size !== row.outcome_result_ids.length
    || row.outcome_result_ids.some((id) => !IDENTIFIER.test(String(id || "")))
    || new Set(row.ranked_candidate_ids).size !== row.ranked_candidate_ids.length
    || row.ranked_candidate_ids.some((id) => !IDENTIFIER.test(String(id || "")))) fail();
  const directives = row.pitch_directives.map((item) => {
    if (!exact(item, ["candidate_id", "directive", "directive_sha256", "outcome_result_ids"])
      || !row.ranked_candidate_ids.includes(item.candidate_id)
      || !String(item.directive || "").trim() || String(item.directive).length > 240
      || String(item.directive).includes("\n")
      || String(item.directive).split(/\s+/).filter(Boolean).length > 24
      || item.directive_sha256 !== sha(item.directive)
      || !Array.isArray(item.outcome_result_ids) || item.outcome_result_ids.length < 1
      || item.outcome_result_ids.some((id) => !row.outcome_result_ids.includes(id))) fail();
    return Object.freeze({
      candidate_id: item.candidate_id,
      directive: item.directive,
      directive_sha256: item.directive_sha256,
      outcome_result_ids: Object.freeze([...item.outcome_result_ids]),
    });
  });
  if (new Set(directives.map((item) => item.candidate_id)).size !== directives.length
    || directives.length !== row.ranked_candidate_ids.length) fail();
  const seed = {
    schema_version: 1,
    tenant_id: row.tenant_id,
    week_key: row.week_key,
    week_start: row.week_start,
    week_end: row.week_end,
    reflected_at: row.reflected_at,
    snapshot_digest: row.snapshot_digest,
    decision: row.decision,
    reason: row.reason,
    summary_sha256: row.summary_sha256,
    rationale_sha256: row.rationale_sha256,
    outcome_result_ids: [...row.outcome_result_ids],
    ranked_candidate_ids: [...row.ranked_candidate_ids],
    pitch_directives: directives,
  };
  if (row.reflection_id !== `funder-weekly-reflection:${sha(JSON.stringify(seed))}`) fail();
  const value = Object.freeze({
    ...seed,
    reflection_id: row.reflection_id,
    outcome_result_ids: Object.freeze(seed.outcome_result_ids),
    ranked_candidate_ids: Object.freeze(seed.ranked_candidate_ids),
    pitch_directives: Object.freeze(directives),
  });
  VERIFIED.add(value);
  return value;
}

module.exports = {
  tokyoReflectionWeek,
  latestCompletedTokyoReflectionWeek,
  buildFunderWeeklyReflection,
  isVerifiedFunderWeeklyReflection,
  adoptPersistedFunderWeeklyReflection,
};
