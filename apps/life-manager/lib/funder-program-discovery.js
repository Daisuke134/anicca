"use strict";

const { createHash } = require("node:crypto");

const ID = /^[a-z0-9][a-z0-9._-]{1,99}$/;
const SHA = /^[0-9a-f]{64}$/;
const TYPES = new Set(["accelerator", "grant", "foundation", "prize"]);
const STATUSES = new Set(["open", "closed", "announced", "unknown"]);
const SOLO = new Set(["yes", "no", "unknown"]);
const RETRIEVAL = new Set(["direct_https", "firecrawl", "jina_reader"]);
const CANDIDATE_KEYS = ["evidence_excerpt", "funder_id", "funder_type", "location", "name", "next_deadline", "official_url", "rationale", "solo_allowed", "source_id", "status", "terms_hash"];

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
function digest(value) { return createHash("sha256").update(typeof value === "string" ? value : stable(value)).digest("hex"); }
function fail(reason) { throw new Error(`funder discovery ${reason} invalid`); }
function httpsUrl(value) {
  let url; try { url = new URL(String(value || "")); } catch { fail("URL"); }
  if (url.protocol !== "https:" || url.username || url.password || !url.hostname.includes(".")) fail("URL");
  url.hash = "";
  return url.toString();
}
function tokyoDay(ms) {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(ms));
  const get = (type) => parts.find((part) => part.type === type).value;
  return `${get("year")}-${get("month")}-${get("day")}`;
}

function buildDailyFunderDiscovery(input = {}) {
  const tenantId = String(input.tenantId || "").trim();
  const observedMs = Date.parse(String(input.observedAt || ""));
  if (!tenantId || tenantId.length > 128 || !Number.isFinite(observedMs) || !Array.isArray(input.sources)
    || !Array.isArray(input.existingEntries) || !input.assessment || !Array.isArray(input.assessment.assessed_source_ids)
    || !Array.isArray(input.assessment.candidates)) fail("input");

  const sources = new Map();
  const safeSources = [];
  for (const source of input.sources) {
    const id = String(source && source.source_id || "");
    const content = String(source && source.content || "");
    const fetchedMs = Date.parse(String(source && source.fetched_at || ""));
    if (!ID.test(id) || sources.has(id) || !content || content.length > 2_000_000 || !Number.isFinite(fetchedMs)
      || fetchedMs > observedMs + 300_000 || observedMs - fetchedMs > 26 * 60 * 60 * 1000
      || !Array.isArray(source.links) || !RETRIEVAL.has(source.retrieved_via)) fail("source");
    if (!SHA.test(String(source.content_sha256 || "")) || digest(content) !== source.content_sha256) fail("source hash");
    const sourceUrl = httpsUrl(source.source_url);
    const links = [...new Set(source.links.map(httpsUrl))].sort();
    const normalized = { id, source_url: sourceUrl, retrieved_via: source.retrieved_via, fetched_at: new Date(fetchedMs).toISOString(), content_sha256: source.content_sha256, links, content };
    sources.set(id, normalized);
    safeSources.push({ source_id: id, source_url: sourceUrl, retrieved_via: source.retrieved_via, fetched_at: normalized.fetched_at, content_sha256: source.content_sha256, link_count: links.length });
  }
  if (sources.size === 0) fail("source");
  const assessed = input.assessment.assessed_source_ids.map(String);
  if (new Set(assessed).size !== assessed.length || stable([...assessed].sort()) !== stable([...sources.keys()].sort())) fail("assessment");

  const existingById = new Map();
  const existingByUrl = new Map();
  let maxPriority = 0;
  for (const entry of input.existingEntries) {
    const id = String(entry && entry.funder_id || "");
    const url = httpsUrl(entry && entry.official_url);
    const priority = Number(entry && entry.priority);
    if (!ID.test(id) || existingById.has(id) || existingByUrl.has(url) || !Number.isSafeInteger(priority) || priority < 1) fail("existing registry");
    existingById.set(id, entry); existingByUrl.set(url, entry); maxPriority = Math.max(maxPriority, priority);
  }

  const seenIds = new Set();
  const seenUrls = new Set();
  const entries = [];
  for (const candidate of input.assessment.candidates) {
    if (!candidate || stable(Object.keys(candidate).sort()) !== stable(CANDIDATE_KEYS)) fail("candidate");
    const source = sources.get(String(candidate.source_id || ""));
    const id = String(candidate.funder_id || "");
    const url = httpsUrl(candidate.official_url);
    const name = String(candidate.name || "").replace(/\s+/g, " ").trim();
    const excerpt = String(candidate.evidence_excerpt || "").trim();
    const rationale = String(candidate.rationale || "").trim();
    const location = String(candidate.location || "").replace(/\s+/g, " ").trim();
    if (!source || !ID.test(id) || seenIds.has(id) || seenUrls.has(url)) fail("duplicate candidate");
    if (url !== source.source_url && !source.links.includes(url)) fail("linked URL");
    if (!name || name.length > 300 || !TYPES.has(candidate.funder_type) || !excerpt || excerpt.length > 1000
      || !source.content.includes(excerpt) || !rationale || rationale.length > 1000) fail("evidence");
    if (!STATUSES.has(candidate.status) || !SOLO.has(candidate.solo_allowed) || !location || location.length > 300) fail("candidate");
    if (candidate.next_deadline !== null && !/^\d{4}-\d{2}-\d{2}$/.test(String(candidate.next_deadline))) fail("deadline");
    if (candidate.terms_hash !== null && !SHA.test(String(candidate.terms_hash))) fail("terms");
    const byId = existingById.get(id); const byUrl = existingByUrl.get(url);
    if (byId && byUrl && byId !== byUrl) fail("identity collision");
    if ((byId && httpsUrl(byId.official_url) !== url) || (byUrl && String(byUrl.funder_id) !== id)) fail("identity collision");
    const prior = byId || byUrl || null;
    const facts = { funder_id: id, name, official_url: url, funder_type: candidate.funder_type, source_url: source.source_url,
      source_content_sha256: source.content_sha256, evidence_sha256: digest(excerpt), rationale_sha256: digest(rationale), status: candidate.status,
      next_deadline: candidate.next_deadline, terms_hash: candidate.terms_hash, solo_allowed: candidate.solo_allowed, location };
    const factsDigest = digest(facts);
    seenIds.add(id); seenUrls.add(url);
    if (prior && prior.discovery_facts_digest === factsDigest) continue;
    const core = { schema_version: 1, tenant_id: tenantId, ...facts,
      priority: prior ? Number(prior.priority) : ++maxPriority,
      verification_status: "verified", automation_gate: "review_required",
      source_ref: `official-source://${source.content_sha256}`, observed_at: new Date(observedMs).toISOString(),
      legacy_claims: {}, discovery_kind: prior ? "existing_change" : "new_program", discovery_facts_digest: factsDigest };
    const revision = digest(core);
    entries.push(Object.freeze({ ...core, registry_id: `funder-registry:${revision}`, revision_digest: revision }));
  }
  const runCore = { schema_version: 1, tenant_id: tenantId, tokyo_day: tokyoDay(observedMs), observed_at: new Date(observedMs).toISOString(),
    status: "complete", source_count: sources.size, candidate_count: input.assessment.candidates.length, appended_count: entries.length,
    source_receipts: safeSources.sort((a, b) => a.source_id.localeCompare(b.source_id)), registry_ids: entries.map((entry) => entry.registry_id).sort() };
  const runDigest = digest(runCore);
  return Object.freeze({ schema_version: 1, tenant_id: tenantId, entries: Object.freeze(entries),
    run: Object.freeze({ ...runCore, discovery_run_id: `funder-discovery:${runDigest}`, run_digest: runDigest }) });
}

module.exports = { buildDailyFunderDiscovery };
