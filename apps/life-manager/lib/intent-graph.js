"use strict";
// 10g BRAIN-a — intent-aware context graph (§9.1/§9.2).
// Closed schema over six intent kinds, each entry carrying provenance,
// a confidence tier ordered explicit > repeated > inferred, and expiry.
// A correction expires the prediction it supersedes; corrected or expired
// entries never re-enter the effective set, so the same intent is never
// re-asked and a corrected inference cannot resurface.

const INTENT_KINDS = Object.freeze([
  "explicit_goal", "repeated_preference", "family_dependent",
  "delegation", "prohibition", "correction",
]);

const PROVENANCE_SOURCES = Object.freeze([
  "user_message", "telegram_reply", "calendar_pattern", "mail", "correction",
]);

// Ordered strongest-first; values encode §9.2's 明示 > 繰り返し > 単発推定.
const CONFIDENCE_TIERS = Object.freeze(["explicit", "repeated", "inferred"]);
const TIER_CONFIDENCE = Object.freeze({ explicit: 0.9, repeated: 0.6, inferred: 0.3 });

const STATUSES = Object.freeze(["active", "expired", "corrected"]);

const ENTRY_KEYS = Object.freeze([
  "id", "uid", "kind", "statement", "provenance",
  "confidenceTier", "confidence", "expiresAt", "status", "supersedes",
]);
const PROVENANCE_KEYS = Object.freeze(["source", "evidence", "observedAt"]);

function isIsoDate(value) {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function nonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function confidenceForTier(tier) {
  const value = TIER_CONFIDENCE[tier];
  if (value === undefined) throw new Error(`unknown confidence tier: ${String(tier)}`);
  return value;
}

function validateIntentEntry(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("entry must be an object");
  for (const key of Object.keys(input)) {
    if (!ENTRY_KEYS.includes(key)) throw new Error(`unknown key: ${key}`);
  }
  if (!nonEmptyString(input.id)) throw new Error("id must be a non-empty string");
  if (!nonEmptyString(input.uid)) throw new Error("uid must be a non-empty string");
  if (!INTENT_KINDS.includes(input.kind)) throw new Error(`kind must be one of ${INTENT_KINDS.join("|")}`);
  if (!nonEmptyString(input.statement) || input.statement.length > 500) {
    throw new Error("statement must be a non-empty string of at most 500 chars");
  }
  const p = input.provenance;
  if (!p || typeof p !== "object" || Array.isArray(p)) throw new Error("provenance must be an object");
  for (const key of Object.keys(p)) {
    if (!PROVENANCE_KEYS.includes(key)) throw new Error(`unknown key: provenance.${key}`);
  }
  if (!PROVENANCE_SOURCES.includes(p.source)) throw new Error(`provenance.source must be one of ${PROVENANCE_SOURCES.join("|")}`);
  if (!nonEmptyString(p.evidence)) throw new Error("provenance.evidence must be a non-empty string");
  if (!isIsoDate(p.observedAt)) throw new Error("provenance.observedAt must be an ISO date");
  if (!CONFIDENCE_TIERS.includes(input.confidenceTier)) throw new Error(`confidenceTier must be one of ${CONFIDENCE_TIERS.join("|")}`);
  if (typeof input.confidence !== "number" || !(input.confidence > 0) || input.confidence > 1) {
    throw new Error("confidence must be a number in (0, 1]");
  }
  if (input.expiresAt !== null && !isIsoDate(input.expiresAt)) throw new Error("expiresAt must be null or an ISO date");
  if (!STATUSES.includes(input.status)) throw new Error(`status must be one of ${STATUSES.join("|")}`);
  if (input.supersedes !== null && !nonEmptyString(input.supersedes)) {
    throw new Error("supersedes must be null or a non-empty entry id");
  }
  return input;
}

function buildGraph(entries) {
  const validated = (Array.isArray(entries) ? entries : []).map(validateIntentEntry);
  const ids = new Set();
  for (const e of validated) {
    if (ids.has(e.id)) throw new Error(`duplicate entry id: ${e.id}`);
    ids.add(e.id);
  }
  return { entries: validated };
}

// A correction targets one prior entry via `supersedes`: the target flips to
// status "corrected" (never deleted — provenance history stays auditable) and
// the correction joins the graph as the active truth.
function applyCorrection(graph, correction, nowMs) {
  validateIntentEntry(correction);
  if (correction.kind !== "correction") throw new Error("kind must be correction");
  if (!nonEmptyString(correction.supersedes)) throw new Error("supersedes must name the corrected entry");
  const target = graph.entries.find((e) => e.id === correction.supersedes);
  if (!target) throw new Error(`supersedes target not found: ${correction.supersedes}`);
  if (graph.entries.some((e) => e.id === correction.id)) throw new Error(`duplicate entry id: ${correction.id}`);
  const stamped = { ...correction, status: "active" };
  const entries = graph.entries.map((e) =>
    e.id === target.id ? { ...e, status: "corrected" } : e,
  );
  entries.push(validateIntentEntry(stamped));
  return { entries };
}

// Pure read: active entries whose expiry has not passed. Never mutates.
function effectiveEntries(graph, nowMs) {
  const now = Number.isFinite(nowMs) ? nowMs : 0;
  return graph.entries.filter((e) =>
    e.status === "active" && (e.expiresAt === null || Date.parse(e.expiresAt) > now),
  );
}

module.exports = {
  INTENT_KINDS, PROVENANCE_SOURCES, CONFIDENCE_TIERS,
  validateIntentEntry, confidenceForTier, buildGraph,
  applyCorrection, effectiveEntries,
};
