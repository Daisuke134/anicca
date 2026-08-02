"use strict";

const { createHash } = require("node:crypto");

const SHA256 = /^[0-9a-f]{64}$/;
const IDENTIFIER = /^[a-z0-9][a-z0-9._-]{1,99}$/;
const MONTH = /^\d{4}-(?:0[1-9]|1[0-2])$/;
const CURRENCY = /^[A-Z]{3}$/;
const OFFSET_RFC3339 = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:Z|[+-]\d{2}:\d{2})$/;
const SOURCE_URLS = Object.freeze({
  apply: "https://www.ycombinator.com/apply",
  deal: "https://www.ycombinator.com/deal",
});
const LEGACY_DEADLINE_KINDS = new Set(["rolling", "quarterly", "annual", "biannual"]);
const TRUSTED_FACT_RECEIPTS = new WeakSet();

function fail(reason) {
  throw new Error(`YC current program facts ${reason} invalid`);
}

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function sha(value) {
  return createHash("sha256").update(value).digest("hex");
}

function deepFreeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const nested of Object.values(value)) deepFreeze(nested);
  }
  return value;
}

function exactKeys(value, expected, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)
    || stable(Object.keys(value).sort()) !== stable([...expected].sort())) fail(`${label} schema`);
}

function cleanText(value, label, max = 300) {
  const text = String(value == null ? "" : value);
  if (!text || text.trim() !== text || text.length > max || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(text)) fail(label);
  return text;
}

function instant(value, label) {
  const parsed = Date.parse(String(value == null ? "" : value));
  if (!Number.isFinite(parsed)) fail(label);
  return parsed;
}

function offsetInstant(value, label, canonical = false) {
  const text = String(value == null ? "" : value);
  if (!OFFSET_RFC3339.test(text)) fail(label);
  const parsed = instant(text, label);
  if (canonical && new Date(parsed).toISOString() !== text) fail(label);
  return parsed;
}

function exactHttpsUrl(value, expected, label) {
  let url;
  try { url = new URL(String(value == null ? "" : value)); } catch { fail(label); }
  if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash || url.toString() !== expected) fail(label);
  return url.toString();
}

function retrievalUrl(value, official, label) {
  const raw = String(value == null ? "" : value);
  const allowed = new Set([official, `https://r.jina.ai/${official}`]);
  if (!allowed.has(raw)) fail(label);
  return raw;
}

function linkInventory(value, label) {
  if (!Array.isArray(value) || value.length > 300 || new Set(value).size !== value.length) fail(label);
  const links = value.map((raw) => {
    let url;
    try { url = new URL(String(raw == null ? "" : raw)); } catch { fail(label); }
    if (url.protocol !== "https:" || url.username || url.password) fail(label);
    return url.toString();
  });
  return {
    links,
    count: links.length,
    digest: sha(stable([...links].sort())),
  };
}

function parseSource(value) {
  exactKeys(value, ["role", "official_url", "retrieval_url", "observed_at", "body", "body_sha256", "body_length", "links"], "source");
  const role = String(value.role || "");
  const expectedUrl = SOURCE_URLS[role];
  if (!expectedUrl) fail("source role");
  const body = String(value.body == null ? "" : value.body);
  const bodyLength = Buffer.byteLength(body);
  if (!body || bodyLength > 2_000_000 || !SHA256.test(String(value.body_sha256 || ""))
    || sha(body) !== value.body_sha256 || value.body_length !== bodyLength) fail("source body");
  const inventory = linkInventory(value.links, "source links");
  return {
    role,
    officialUrl: exactHttpsUrl(value.official_url, expectedUrl, "official URL"),
    retrievalUrl: retrievalUrl(value.retrieval_url, expectedUrl, "retrieval URL"),
    observedMs: offsetInstant(value.observed_at, "source observation"),
    body,
    bodySha256: value.body_sha256,
    bodyLength,
    links: inventory.links,
    linkCount: inventory.count,
    linkDigest: inventory.digest,
  };
}

function selectedEvidence(value, expectedKeys, source, label) {
  exactKeys(value, expectedKeys, label);
  if (value.source_role !== source.role) fail(`${label} source`);
  const excerpt = cleanText(value.evidence_excerpt, `${label} excerpt`, 1_500);
  if (!source.body.includes(excerpt)) fail(`${label} excerpt`);
  if (!Array.isArray(value.selected_texts) || value.selected_texts.length < 1 || value.selected_texts.length > 12
    || new Set(value.selected_texts).size !== value.selected_texts.length) fail(`${label} selections`);
  const selected = value.selected_texts.map((item) => cleanText(item, `${label} selection`, 300));
  if (selected.some((item) => !excerpt.includes(item))) fail(`${label} binding`);
  return { excerptSha256: sha(excerpt), selectedSha256: selected.map(sha) };
}

function positiveSafeInteger(value, label) {
  if (!Number.isSafeInteger(value) || value <= 0) fail(label);
  return value;
}

function nowMilliseconds(value) {
  if (value instanceof Date) return value.getTime();
  if (typeof value === "function") return Number(value());
  if (value == null) return Date.now();
  return instant(value, "wall clock");
}

function calendarDate(value) {
  const text = String(value == null ? "" : value);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return false;
  const parsed = new Date(`${text}T00:00:00.000Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === text;
}

function buildYcCurrentProgramFactsReceipt(input = {}, options = {}) {
  exactKeys(input, ["legacy_config_id", "verified_at", "sources", "assessment", "effects"], "input");
  const legacyConfigId = String(input.legacy_config_id || "");
  if (legacyConfigId !== "yc-w26") fail("legacy config identity");
  if (!Array.isArray(input.sources) || input.sources.length !== 2) fail("source set");
  const parsedSources = input.sources.map(parseSource);
  const sources = new Map(parsedSources.map((source) => [source.role, source]));
  if (sources.size !== 2 || !sources.has("apply") || !sources.has("deal")) fail("source set");

  const verifiedMs = offsetInstant(input.verified_at, "verified timestamp");
  const observed = parsedSources.map(({ observedMs }) => observedMs);
  const nowMs = nowMilliseconds(options.now);
  if (!Number.isFinite(nowMs) || Math.max(...observed) > verifiedMs || verifiedMs > nowMs
    || Math.max(...observed) - Math.min(...observed) > 15 * 60_000
    || verifiedMs - Math.min(...observed) > 15 * 60_000
    || nowMs - verifiedMs > 5 * 60_000) fail("receipt freshness");

  const assessment = input.assessment;
  exactKeys(assessment, ["decision_owner", "program_id", "program_name", "batch", "deadline", "application", "investment", "rationale"], "assessment");
  if (assessment.decision_owner !== "agent") fail("decision owner");
  const programId = String(assessment.program_id || "");
  if (!IDENTIFIER.test(programId)) fail("program identity");
  const programName = cleanText(assessment.program_name, "program name");
  const rationale = cleanText(assessment.rationale, "assessment rationale", 1_000);

  const applySource = sources.get("apply");
  const dealSource = sources.get("deal");
  const batchProof = selectedEvidence(assessment.batch,
    ["label", "starts_month", "ends_month", "location", "source_role", "evidence_excerpt", "selected_texts"],
    applySource, "batch");
  const batch = {
    label: cleanText(assessment.batch.label, "batch label"),
    starts_month: String(assessment.batch.starts_month || ""),
    ends_month: String(assessment.batch.ends_month || ""),
    location: cleanText(assessment.batch.location, "batch location"),
  };
  if (!MONTH.test(batch.starts_month) || !MONTH.test(batch.ends_month) || batch.starts_month > batch.ends_month) fail("batch months");

  const deadlineProof = selectedEvidence(assessment.deadline,
    ["status", "display", "on_time_at", "timezone", "late_applications_open", "compatibility_deadline_kind", "compatibility_next_deadline", "source_role", "evidence_excerpt", "selected_texts"],
    applySource, "deadline");
  const deadlineInstant = String(assessment.deadline.on_time_at || "");
  if (!OFFSET_RFC3339.test(deadlineInstant) || !Number.isFinite(Date.parse(deadlineInstant))) fail("deadline instant");
  const compatibilityNextDeadline = assessment.deadline.compatibility_next_deadline;
  if (compatibilityNextDeadline !== null && !calendarDate(compatibilityNextDeadline)) fail("compatibility deadline");
  if (!LEGACY_DEADLINE_KINDS.has(assessment.deadline.compatibility_deadline_kind)) fail("compatibility deadline kind");
  if (typeof assessment.deadline.late_applications_open !== "boolean") fail("late application state");
  const deadline = {
    status: cleanText(assessment.deadline.status, "deadline status", 100),
    display: cleanText(assessment.deadline.display, "deadline display"),
    on_time_at: new Date(Date.parse(deadlineInstant)).toISOString(),
    timezone: cleanText(assessment.deadline.timezone, "deadline timezone", 100),
    late_applications_open: assessment.deadline.late_applications_open,
    compatibility_deadline_kind: cleanText(assessment.deadline.compatibility_deadline_kind, "compatibility deadline kind", 100),
    compatibility_next_deadline: compatibilityNextDeadline,
  };

  const applicationProof = selectedEvidence(assessment.application,
    ["url", "source_role", "evidence_excerpt", "selected_texts"], applySource, "application");
  const applicationUrl = exactHttpsUrl(assessment.application.url, "https://apply.ycombinator.com/home", "application URL");
  if (!applySource.links.includes(applicationUrl)) fail("observed application link");

  const investmentProof = selectedEvidence(assessment.investment,
    ["currency", "total_amount", "fixed_safe_amount", "fixed_equity_percent", "mfn_safe_amount", "mfn_uncapped", "most_favored_nation", "source_role", "evidence_excerpt", "selected_texts"],
    dealSource, "investment");
  const totalAmount = positiveSafeInteger(assessment.investment.total_amount, "total amount");
  const fixedSafeAmount = positiveSafeInteger(assessment.investment.fixed_safe_amount, "fixed safe amount");
  const mfnSafeAmount = positiveSafeInteger(assessment.investment.mfn_safe_amount, "MFN safe amount");
  const fixedEquityPercent = Number(assessment.investment.fixed_equity_percent);
  if (!CURRENCY.test(String(assessment.investment.currency || "")) || !Number.isFinite(fixedEquityPercent)
    || fixedEquityPercent <= 0 || fixedEquityPercent > 100 || typeof assessment.investment.mfn_uncapped !== "boolean"
    || typeof assessment.investment.most_favored_nation !== "boolean" || fixedSafeAmount + mfnSafeAmount !== totalAmount) fail("investment arithmetic");
  const investment = {
    currency: assessment.investment.currency,
    total_amount: totalAmount,
    fixed_safe_amount: fixedSafeAmount,
    fixed_equity_percent: fixedEquityPercent,
    mfn_safe_amount: mfnSafeAmount,
    mfn_uncapped: assessment.investment.mfn_uncapped,
    most_favored_nation: assessment.investment.most_favored_nation,
  };

  exactKeys(input.effects, ["read_operations", "write_operations", "submit_operations"], "effects");
  if (!Number.isSafeInteger(input.effects.read_operations) || input.effects.read_operations < 2 || input.effects.read_operations > 20
    || input.effects.write_operations !== 0 || input.effects.submit_operations !== 0) fail("effects");

  const sourceReceipts = [applySource, dealSource].map((source) => ({
    role: source.role,
    official_url: source.officialUrl,
    retrieval_url: source.retrievalUrl,
    observed_at: new Date(source.observedMs).toISOString(),
    body_sha256: source.bodySha256,
    body_length: source.bodyLength,
    link_count: source.linkCount,
    link_inventory_sha256: source.linkDigest,
  }));
  const core = {
    schema_version: 1,
    legacy_config_id: legacyConfigId,
    program_id: programId,
    program_name: programName,
    official_url: applySource.officialUrl,
    application_url: applicationUrl,
    verified_at: new Date(verifiedMs).toISOString(),
    batch,
    deadline,
    investment,
    source_receipts: sourceReceipts,
    assessment_proof: {
      decision_owner: "agent",
      excerpt_sha256: {
        batch: batchProof.excerptSha256,
        deadline: deadlineProof.excerptSha256,
        application: applicationProof.excerptSha256,
        investment: investmentProof.excerptSha256,
      },
      selected_text_sha256: {
        batch: batchProof.selectedSha256,
        deadline: deadlineProof.selectedSha256,
        application: applicationProof.selectedSha256,
        investment: investmentProof.selectedSha256,
      },
      rationale_sha256: sha(rationale),
    },
    effects: {
      read_operations: input.effects.read_operations,
      write_operations: 0,
      submit_operations: 0,
    },
  };
  const receipt = deepFreeze({ ...core, fact_receipt_digest: sha(stable(core)) });
  TRUSTED_FACT_RECEIPTS.add(receipt);
  return receipt;
}

function validateFactReceipt(receipt) {
  exactKeys(receipt, ["schema_version", "legacy_config_id", "program_id", "program_name", "official_url", "application_url", "verified_at", "batch", "deadline", "investment", "source_receipts", "assessment_proof", "effects", "fact_receipt_digest"], "receipt");
  if (receipt.schema_version !== 1 || receipt.legacy_config_id !== "yc-w26"
    || !IDENTIFIER.test(String(receipt.program_id || "")) || !SHA256.test(String(receipt.fact_receipt_digest || ""))) fail("receipt identity");
  cleanText(receipt.program_name, "receipt program name");
  exactHttpsUrl(receipt.official_url, SOURCE_URLS.apply, "receipt official URL");
  exactHttpsUrl(receipt.application_url, "https://apply.ycombinator.com/home", "receipt application URL");
  offsetInstant(receipt.verified_at, "receipt verified timestamp", true);

  exactKeys(receipt.batch, ["label", "starts_month", "ends_month", "location"], "receipt batch");
  cleanText(receipt.batch.label, "receipt batch label");
  cleanText(receipt.batch.location, "receipt batch location");
  if (!MONTH.test(String(receipt.batch.starts_month || "")) || !MONTH.test(String(receipt.batch.ends_month || ""))
    || receipt.batch.starts_month > receipt.batch.ends_month) fail("receipt batch months");

  exactKeys(receipt.deadline, ["status", "display", "on_time_at", "timezone", "late_applications_open", "compatibility_deadline_kind", "compatibility_next_deadline"], "receipt deadline");
  cleanText(receipt.deadline.status, "receipt deadline status", 100);
  cleanText(receipt.deadline.display, "receipt deadline display");
  cleanText(receipt.deadline.timezone, "receipt deadline timezone", 100);
  cleanText(receipt.deadline.compatibility_deadline_kind, "receipt compatibility deadline kind", 100);
  if (!OFFSET_RFC3339.test(String(receipt.deadline.on_time_at || "")) || !Number.isFinite(Date.parse(receipt.deadline.on_time_at))
    || !LEGACY_DEADLINE_KINDS.has(receipt.deadline.compatibility_deadline_kind)
    || typeof receipt.deadline.late_applications_open !== "boolean"
    || (receipt.deadline.compatibility_next_deadline !== null
      && !calendarDate(receipt.deadline.compatibility_next_deadline))) fail("receipt deadline");

  exactKeys(receipt.investment, ["currency", "total_amount", "fixed_safe_amount", "fixed_equity_percent", "mfn_safe_amount", "mfn_uncapped", "most_favored_nation"], "receipt investment");
  const total = positiveSafeInteger(receipt.investment.total_amount, "receipt total amount");
  const fixed = positiveSafeInteger(receipt.investment.fixed_safe_amount, "receipt fixed amount");
  const mfn = positiveSafeInteger(receipt.investment.mfn_safe_amount, "receipt MFN amount");
  if (!CURRENCY.test(String(receipt.investment.currency || "")) || !Number.isFinite(receipt.investment.fixed_equity_percent)
    || receipt.investment.fixed_equity_percent <= 0 || receipt.investment.fixed_equity_percent > 100
    || typeof receipt.investment.mfn_uncapped !== "boolean" || typeof receipt.investment.most_favored_nation !== "boolean"
    || fixed + mfn !== total) fail("receipt investment");

  if (!Array.isArray(receipt.source_receipts) || receipt.source_receipts.length !== 2) fail("receipt sources");
  const sourceRoles = new Set();
  for (const source of receipt.source_receipts) {
    exactKeys(source, ["role", "official_url", "retrieval_url", "observed_at", "body_sha256", "body_length", "link_count", "link_inventory_sha256"], "receipt source");
    const expected = SOURCE_URLS[source.role];
    if (!expected || sourceRoles.has(source.role)) fail("receipt source role");
    sourceRoles.add(source.role);
    exactHttpsUrl(source.official_url, expected, "receipt source URL");
    retrievalUrl(source.retrieval_url, expected, "receipt retrieval URL");
    offsetInstant(source.observed_at, "receipt source observation", true);
    if (!SHA256.test(String(source.body_sha256 || "")) || !SHA256.test(String(source.link_inventory_sha256 || ""))
      || !Number.isSafeInteger(source.body_length) || source.body_length <= 0 || source.body_length > 2_000_000
      || !Number.isSafeInteger(source.link_count) || source.link_count < 0 || source.link_count > 300) fail("receipt source metadata");
  }
  if (sourceRoles.size !== 2 || !sourceRoles.has("apply") || !sourceRoles.has("deal")) fail("receipt source set");

  exactKeys(receipt.assessment_proof, ["decision_owner", "excerpt_sha256", "selected_text_sha256", "rationale_sha256"], "receipt assessment proof");
  if (receipt.assessment_proof.decision_owner !== "agent" || !SHA256.test(String(receipt.assessment_proof.rationale_sha256 || ""))) fail("receipt assessment proof");
  exactKeys(receipt.assessment_proof.excerpt_sha256, ["batch", "deadline", "application", "investment"], "receipt excerpt proof");
  exactKeys(receipt.assessment_proof.selected_text_sha256, ["batch", "deadline", "application", "investment"], "receipt selection proof");
  for (const key of ["batch", "deadline", "application", "investment"]) {
    if (!SHA256.test(String(receipt.assessment_proof.excerpt_sha256[key] || ""))
      || !Array.isArray(receipt.assessment_proof.selected_text_sha256[key])
      || receipt.assessment_proof.selected_text_sha256[key].length < 1
      || receipt.assessment_proof.selected_text_sha256[key].length > 12
      || new Set(receipt.assessment_proof.selected_text_sha256[key]).size !== receipt.assessment_proof.selected_text_sha256[key].length
      || receipt.assessment_proof.selected_text_sha256[key].some((value) => !SHA256.test(String(value || "")))) fail("receipt evidence proof");
  }

  exactKeys(receipt.effects, ["read_operations", "write_operations", "submit_operations"], "receipt effects");
  if (!Number.isSafeInteger(receipt.effects.read_operations) || receipt.effects.read_operations < 2 || receipt.effects.read_operations > 20
    || receipt.effects.write_operations !== 0 || receipt.effects.submit_operations !== 0) fail("receipt effects");
  const { fact_receipt_digest: digest, ...core } = receipt;
  if (sha(stable(core)) !== digest) fail("receipt digest");
  return receipt;
}

const LEGACY_FACT_PATHS = Object.freeze([
  "application_url",
  "amount_range",
  "current_batch",
  "deadline",
  "deadline_kind",
  "fact_receipt_digest",
  "fact_sources",
  "facts_verified_at",
  "name",
  "next_deadline",
  "official_url",
  "standard_deal",
  "url",
]);

function clone(value) {
  return structuredClone(value);
}

function nonFactDigest(value) {
  const masked = clone(value);
  for (const key of LEGACY_FACT_PATHS) delete masked[key];
  return sha(stable(masked));
}

function projectYcCurrentFactsIntoLegacy(legacySpec, factReceipt) {
  if (!legacySpec || typeof legacySpec !== "object" || Array.isArray(legacySpec)) fail("legacy spec");
  const receipt = validateFactReceipt(factReceipt);
  if (!TRUSTED_FACT_RECEIPTS.has(receipt)) fail("receipt provenance");
  if (legacySpec.id !== receipt.legacy_config_id) fail("legacy spec identity");
  if (legacySpec.currency !== receipt.investment.currency
    || legacySpec.equity_pct !== receipt.investment.fixed_equity_percent) fail("legacy deal compatibility");
  const projected = clone(legacySpec);
  projected.name = receipt.program_name;
  projected.url = receipt.application_url;
  projected.official_url = receipt.official_url;
  projected.application_url = receipt.application_url;
  projected.facts_verified_at = receipt.verified_at;
  projected.current_batch = clone(receipt.batch);
  projected.deadline_kind = receipt.deadline.compatibility_deadline_kind;
  projected.next_deadline = receipt.deadline.compatibility_next_deadline;
  projected.deadline = clone(receipt.deadline);
  projected.amount_range = { min: receipt.investment.total_amount, max: receipt.investment.total_amount };
  projected.standard_deal = clone(receipt.investment);
  projected.fact_sources = clone(receipt.source_receipts);
  projected.fact_receipt_digest = receipt.fact_receipt_digest;
  const beforeDigest = nonFactDigest(legacySpec);
  const afterDigest = nonFactDigest(projected);
  if (beforeDigest !== afterDigest) fail("legacy non-fact drift");
  const changedPaths = LEGACY_FACT_PATHS.filter((key) => stable(legacySpec[key]) !== stable(projected[key]));
  return deepFreeze({
    projected,
    before_non_fact_digest: beforeDigest,
    after_non_fact_digest: afterDigest,
    changed_paths: changedPaths,
  });
}

function validateYcCurrentProgramFactsManifestStructure(manifest) {
  validateFactReceipt(manifest);
  return true;
}

module.exports = {
  buildYcCurrentProgramFactsReceipt,
  projectYcCurrentFactsIntoLegacy,
  validateYcCurrentProgramFactsManifestStructure,
};
