"use strict";

const { createHash } = require("node:crypto");

const TYPES = new Set(["accelerator", "grant", "foundation", "prize"]);
const ID = /^[a-z0-9][a-z0-9._-]{1,99}$/;

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

function officialUrl(value) {
  let url;
  try { url = new URL(String(value || "")); } catch { throw new Error("funder registry URL invalid"); }
  if (url.protocol !== "https:" || url.username || url.password || !url.hostname.includes(".")) throw new Error("funder registry URL invalid");
  url.hash = "";
  return url.toString();
}

function buildFunderRegistry(input = {}) {
  const tenantId = String(input.tenantId || "").trim();
  const observedMs = Date.parse(String(input.observedAt || ""));
  const portfolio = input.portfolio;
  if (!tenantId || tenantId.length > 128 || !Number.isFinite(observedMs) || !portfolio || !Array.isArray(portfolio.funders) || !Array.isArray(input.specs)) {
    throw new Error("funder registry input invalid");
  }
  const specs = new Map();
  for (const spec of input.specs) {
    const id = String(spec && spec.id || "");
    if (!ID.test(id) || specs.has(id)) throw new Error("funder registry spec invalid");
    specs.set(id, spec);
  }
  const portfolioIds = portfolio.funders.map(({ id }) => String(id || ""));
  if (new Set(portfolioIds).size !== portfolioIds.length || portfolioIds.some((id) => !specs.has(id)) || specs.size !== portfolioIds.length) {
    throw new Error("funder registry set mismatch");
  }
  const priorities = new Set();
  const entries = [];
  for (const row of portfolio.funders) {
    const priority = Number(row.priority);
    if (!Number.isSafeInteger(priority) || priority < 1 || priorities.has(priority)) throw new Error("funder registry priority invalid");
    priorities.add(priority);
    const spec = specs.get(row.id);
    if (!TYPES.has(spec.funder_type)) throw new Error("funder registry type invalid");
    const name = String(spec.name || "").replace(/\s+/g, " ").trim();
    const sourceFile = String(row.spec || "").trim();
    if (!name || name.length > 300 || sourceFile !== `${row.id}.json`) throw new Error("funder registry source invalid");
    let gate = "review_required";
    if (spec.captcha != null && String(spec.captcha).trim()) gate = "captcha_blocked";
    else if (spec.auth && spec.auth.kind === "institutional_2fa") gate = "auth_blocked";
    const legacyClaims = Object.freeze({
      fact_status: "stale_claim",
      portfolio_updated_at: String(portfolio.updated_at || ""),
      verified: spec.verified === true,
      currency: spec.currency == null ? null : String(spec.currency),
      amount_range: spec.amount_range == null ? null : spec.amount_range,
      deadline_kind: spec.deadline_kind == null ? null : String(spec.deadline_kind),
      next_deadline: spec.next_deadline == null ? null : String(spec.next_deadline),
      auth_kind: spec.auth && spec.auth.kind || null,
      captcha: spec.captcha == null ? null : String(spec.captcha),
    });
    const core = {
      schema_version: 1,
      tenant_id: tenantId,
      funder_id: row.id,
      name,
      official_url: officialUrl(spec.url),
      funder_type: spec.funder_type,
      priority,
      verification_status: "needs_reverification",
      automation_gate: gate,
      source_ref: `legacy-funder-spec://${sourceFile}`,
      observed_at: new Date(observedMs).toISOString(),
      legacy_claims: legacyClaims,
    };
    const revision = createHash("sha256").update(stable(core)).digest("hex");
    entries.push(Object.freeze({ ...core, registry_id: `funder-registry:${revision}`, revision_digest: revision }));
  }
  entries.sort((left, right) => left.priority - right.priority);
  const registryDigest = createHash("sha256").update(stable(entries)).digest("hex");
  return Object.freeze({
    schema_version: 1,
    tenant_id: tenantId,
    observed_at: new Date(observedMs).toISOString(),
    registry_digest: registryDigest,
    entries: Object.freeze(entries),
  });
}

module.exports = { buildFunderRegistry };
