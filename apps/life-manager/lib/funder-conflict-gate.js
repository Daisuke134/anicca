"use strict";

const { createHash } = require("node:crypto");

const BLOCKING_ROLES = new Set(["operator", "cvc", "corporate_partner"]);
const ROLES = new Set(["operator", "cvc", "corporate_partner", "lp_only", "service_vendor", "unrelated", "unknown"]);
const ID = /^[a-z0-9][a-z0-9._-]{0,99}$/;
const DEFAULT_MAX_AGE_MS = 24 * 60 * 60 * 1000;

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

function httpsUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return url.protocol === "https:" && !url.username && !url.password && url.hostname.includes(".");
  } catch { return false; }
}

function time(value) {
  const ms = Date.parse(String(value || ""));
  return Number.isFinite(ms) ? ms : null;
}

function validateRelationship(value, sourceIds) {
  if (!value || !ID.test(String(value.entity_id || "")) || !["mufg_family", "other"].includes(value.conflict_group) || !ROLES.has(value.role)) return false;
  if (!String(value.entity_name || "").trim() || !String(value.rationale || "").trim()) return false;
  if (!Array.isArray(value.source_refs) || value.source_refs.length < 1) return false;
  return value.source_refs.every((sourceId) => sourceIds.has(sourceId));
}

async function judgeFunderRelationships(input = {}, deps = {}) {
  if (typeof deps.judge !== "function") throw new Error("explicit model judgment is required");
  const programId = String(input.programId || "");
  const observedAt = String(input.observedAt || "");
  if (!ID.test(programId) || time(observedAt) == null || !Array.isArray(input.officialPages) || input.officialPages.length < 1) {
    throw new Error("funder relationship judgment input invalid");
  }
  const sources = input.officialPages.map((page) => ({
    source_id: String(page.sourceId || ""),
    url: String(page.url || ""),
    fetched_at: String(page.fetchedAt || ""),
    content: String(page.content || "").slice(0, 200_000),
  }));
  const sourceIds = new Set(sources.map(({ source_id }) => source_id));
  if (sourceIds.size !== sources.length || sources.some(({ source_id, url, fetched_at, content }) =>
    !ID.test(source_id) || !httpsUrl(url) || time(fetched_at) == null || !content.trim())) {
    throw new Error("official relationship source invalid");
  }
  const answer = await deps.judge({
    task: "classify_funder_relationships",
    instructions: "Read the official evidence by meaning, identify every operator, CVC, corporate partner, LP-only investor, and relevant service vendor. Classify Mitsubishi UFJ Financial Group, MUFG Bank, Mitsubishi UFJ Information Technology (MUIT), Mitsubishi UFJ Capital (MUCAP), and MUFG Innovation Partners (MUIP) as conflict_group=mufg_family; classify unrelated entities as other. Do not decide from name tokens alone. Mark the partner roster complete only when the official page exposes the whole current roster. Return evidence source IDs and a concise rationale for every relationship.",
    program_id: programId,
    sources: sources.map(({ content, ...source }) => ({ ...source, content })),
  });
  const relationships = answer && answer.relationships;
  if (!answer || !["complete", "incomplete"].includes(answer.partner_roster_status) || !Array.isArray(relationships)
    || relationships.some((relationship) => !validateRelationship(relationship, sourceIds))) {
    throw new Error("model judgment output invalid");
  }
  return Object.freeze({
    schema_version: 1,
    observed_at: new Date(time(observedAt)).toISOString(),
    partner_roster_status: answer.partner_roster_status,
    sources: Object.freeze(sources.map(({ content, ...source }) => Object.freeze({
      ...source,
      content_digest: createHash("sha256").update(content).digest("hex"),
    }))),
    relationships: Object.freeze(relationships.map((relationship) => Object.freeze({
      entity_id: String(relationship.entity_id),
      entity_name: String(relationship.entity_name).trim(),
      conflict_group: relationship.conflict_group,
      role: relationship.role,
      source_refs: Object.freeze([...relationship.source_refs]),
      rationale: String(relationship.rationale).trim(),
    }))),
  });
}

function evaluateFunderConflict(input = {}) {
  const tenantId = String(input.tenantId || "").trim();
  const programId = String(input.programId || "");
  const evaluatedMs = time(input.evaluatedAt);
  const observation = input.observation;
  if (!tenantId || tenantId.length > 128 || !ID.test(programId) || evaluatedMs == null || !observation) {
    throw new Error("funder conflict gate input invalid");
  }
  const maxAgeMs = Number.isFinite(input.maxAgeMs) && input.maxAgeMs > 0 ? input.maxAgeMs : DEFAULT_MAX_AGE_MS;
  const sourceIds = new Set(Array.isArray(observation.sources) ? observation.sources.map(({ source_id }) => source_id) : []);
  const observedMs = time(observation.observed_at);
  const invalidEvidence = observation.schema_version !== 1
    || observation.partner_roster_status !== "complete"
    || observedMs == null || observedMs > evaluatedMs || evaluatedMs - observedMs > maxAgeMs
    || !Array.isArray(observation.sources) || observation.sources.length < 1 || sourceIds.size !== observation.sources.length
    || observation.sources.some((source) => {
      const fetchedMs = time(source.fetched_at);
      return !ID.test(String(source.source_id || "")) || !httpsUrl(source.url) || fetchedMs == null
        || fetchedMs > evaluatedMs || evaluatedMs - fetchedMs > maxAgeMs;
    })
    || !Array.isArray(observation.relationships)
    || observation.relationships.some((relationship) => !validateRelationship(relationship, sourceIds) || relationship.role === "unknown");
  let decision = "allow";
  let reason = "current complete partner check found no restricted operating relationship";
  let blocking = [];
  if (invalidEvidence) {
    decision = "research_required";
    reason = "official operator/CVC/partner evidence is incomplete, stale, unknown, or invalid";
  } else {
    blocking = observation.relationships.filter(({ conflict_group, role }) => conflict_group === "mufg_family" && BLOCKING_ROLES.has(role));
    if (blocking.length > 0) {
      decision = "deny_conflict";
      reason = `restricted ${blocking.map(({ entity_id, role }) => `${entity_id}:${role}`).join(",")}`;
    }
  }
  const core = {
    schema_version: 1,
    tenant_id: tenantId,
    program_id: programId,
    evaluated_at: new Date(evaluatedMs).toISOString(),
    observed_at: observedMs == null ? null : new Date(observedMs).toISOString(),
    decision,
    submit_allowed: decision === "allow",
    reason,
    blocking_relationships: blocking,
    source_refs: Array.isArray(observation.sources) ? observation.sources.map(({ source_id, url, fetched_at }) => ({ source_id, url, fetched_at })) : [],
  };
  return Object.freeze({ ...core, decision_digest: createHash("sha256").update(stable(core)).digest("hex") });
}

module.exports = { judgeFunderRelationships, evaluateFunderConflict };
