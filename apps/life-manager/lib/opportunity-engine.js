"use strict";
// 10h BRAIN-b — proactive opportunity engine (§9.2).
// Separates definite good (never violate an explicit prohibition, never act on
// nothing) from personal good (estimated from the 10g intent graph), then
// arbitrates each candidate through the benefit/urgency/confidence/
// reversibility/cost/risk gate. Within delegation scope and reversible/low-risk
// → act without asking. Only a material preference earns one closed question,
// and the same intent is never asked twice. Doing nothing is a first-class
// correct answer, not a failure mode.

const { buildGraph, effectiveEntries } = require("./intent-graph.js");

const CATEGORIES = Object.freeze(["body", "mind", "finance", "life_admin"]);
const LEVELS = Object.freeze(["low", "medium", "high"]);
const DECISIONS = Object.freeze(["act", "ask", "skip"]);

const CANDIDATE_KEYS = Object.freeze([
  "id", "category", "description", "benefit", "urgency", "cost", "risk",
  "reversible", "supportsIntentIds", "violatesIntentIds", "delegationId",
  "materialPreference", "previouslyAsked",
]);

function nonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function validateCandidate(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("candidate must be an object");
  for (const key of Object.keys(input)) {
    if (!CANDIDATE_KEYS.includes(key)) throw new Error(`unknown key: ${key}`);
  }
  if (!nonEmptyString(input.id)) throw new Error("id must be a non-empty string");
  if (!CATEGORIES.includes(input.category)) throw new Error(`category must be one of ${CATEGORIES.join("|")}`);
  if (!nonEmptyString(input.description)) throw new Error("description must be a non-empty string");
  for (const field of ["benefit", "urgency", "cost", "risk"]) {
    if (!LEVELS.includes(input[field])) throw new Error(`${field} must be one of ${LEVELS.join("|")}`);
  }
  if (typeof input.reversible !== "boolean") throw new Error("reversible must be a boolean");
  for (const field of ["supportsIntentIds", "violatesIntentIds"]) {
    const ids = input[field];
    if (!Array.isArray(ids) || ids.some((id) => !nonEmptyString(id))) {
      throw new Error(`${field} must be an array of entry ids`);
    }
  }
  if (input.delegationId !== null && !nonEmptyString(input.delegationId)) {
    throw new Error("delegationId must be null or an entry id");
  }
  if (typeof input.materialPreference !== "boolean") throw new Error("materialPreference must be a boolean");
  if (typeof input.previouslyAsked !== "boolean") throw new Error("previouslyAsked must be a boolean");
  return input;
}

// Ordered deterministic cascade. Every branch names its reason so the panel
// and the outcome ledger can show WHY, not just WHAT.
function decideOpportunity(graphEntries, candidate, nowMs) {
  validateCandidate(candidate);
  const graph = buildGraph(graphEntries);
  const active = effectiveEntries(graph, nowMs);
  const activeById = new Map(active.map((entry) => [entry.id, entry]));

  // Definite good first: an explicit, still-active prohibition ends the
  // arbitration regardless of every other factor.
  const violated = candidate.violatesIntentIds.find((id) => {
    const hit = activeById.get(id);
    return hit && hit.kind === "prohibition";
  });
  if (violated) return { decision: "skip", reason: `prohibition:${violated}` };

  // Personal good: confidence comes only from still-effective supporting
  // intents — corrected or expired predictions contribute nothing.
  const support = candidate.supportsIntentIds
    .map((id) => activeById.get(id))
    .filter((entry) => entry && entry.kind !== "prohibition");
  const confidence = support.reduce((best, entry) => Math.max(best, entry.confidence), 0);
  if (confidence === 0) return { decision: "skip", reason: "no-active-supporting-intent" };

  if (candidate.risk === "high") {
    return candidate.benefit === "high"
      ? { decision: "ask", reason: "high-risk-needs-consent" }
      : { decision: "skip", reason: "risk-outweighs-benefit" };
  }
  if (candidate.cost === "high" && candidate.benefit !== "high") {
    return { decision: "skip", reason: "cost-outweighs-benefit" };
  }
  if (candidate.benefit === "low" && candidate.urgency === "low") {
    return { decision: "skip", reason: "low-benefit-low-urgency" };
  }

  // Only the user can settle a material preference — one closed question,
  // never repeated for the same intent.
  if (candidate.materialPreference) {
    return candidate.previouslyAsked
      ? { decision: "skip", reason: "already-asked-awaiting-user" }
      : { decision: "ask", reason: "material-preference-closed-question" };
  }

  // Single-shot inference alone never drives an action or a question — keep
  // observing until the pattern repeats or the user says it out loud.
  if (confidence < 0.6) return { decision: "skip", reason: "inferred-only-observe-more" };

  const delegation = candidate.delegationId ? activeById.get(candidate.delegationId) : undefined;
  const delegated = Boolean(delegation && delegation.kind === "delegation");
  if (delegated && candidate.reversible && candidate.risk === "low") {
    return { decision: "act", reason: `delegated-reversible-low-risk:${delegation.id}` };
  }
  if (!candidate.reversible) return { decision: "ask", reason: "irreversible-needs-consent" };
  return { decision: "ask", reason: "outside-delegation-scope" };
}

module.exports = { CATEGORIES, LEVELS, DECISIONS, validateCandidate, decideOpportunity };
