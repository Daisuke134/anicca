"use strict";

const { createHash } = require("node:crypto");

const LEGACY_ID = "99b966b0-7e90-4856-ab0d-93651488a4ea";
const CURRENT_ID = "0b61fe42-e383-490d-b60e-04f1ad7ec5df";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const SHA = /^[0-9a-f]{64}$/;

function fail(reason) { throw new Error(`YC legacy continuation ${reason} invalid`); }
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
function sha(value) { return createHash("sha256").update(value, "utf8").digest("hex"); }
function exactKeys(value, keys, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)
    || stable(Object.keys(value).sort()) !== stable([...keys].sort())) fail(label);
}
function deepFreeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const nested of Object.values(value)) deepFreeze(nested);
  }
  return value;
}
function milliseconds(value, label) {
  const parsed = Date.parse(String(value || ""));
  if (!Number.isFinite(parsed)) fail(label);
  return parsed;
}
function exactUrl(value, expectedPath, label) {
  let url;
  try { url = new URL(String(value || "")); } catch { fail(label); }
  if (url.origin !== "https://apply.ycombinator.com" || url.pathname !== expectedPath
    || url.search || url.hash || url.username || url.password || url.toString() !== `https://apply.ycombinator.com${expectedPath}`) fail(label);
  return url.toString();
}
function linkInventory(value, label) {
  if (!Array.isArray(value) || value.length < 1 || value.length > 100 || new Set(value).size !== value.length) fail(label);
  const ids = [];
  for (const raw of value) {
    let url;
    try { url = new URL(String(raw || "")); } catch { fail(label); }
    const match = url.pathname.match(/^\/apps\/([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})(?:\/edit(?:\/(?:video|demo|progress))?)?$/i);
    if (url.origin !== "https://apply.ycombinator.com" || url.username || url.password || url.search
      || (url.hash && !/^#[A-Za-z][A-Za-z0-9_-]{0,99}$/.test(url.hash))
      || !match || url.toString() !== `https://apply.ycombinator.com${url.pathname}${url.hash}`) fail(label);
    ids.push(match[1].toLowerCase());
  }
  return { ids: [...new Set(ids)], count: value.length, digest: sha(stable([...value].sort())) };
}
function source(value, type, expectedPath) {
  const keys = type === "home"
    ? ["url", "observedAt", "authenticated", "body", "bodySha256", "applicationLinks"]
    : ["url", "observedAt", "accessible", "body", "bodySha256", "applicationLinks"];
  exactKeys(value, keys, `${type} source schema`);
  const body = String(value.body == null ? "" : value.body);
  if (!body || body.length > 2_000_000 || !SHA.test(String(value.bodySha256 || "")) || sha(body) !== value.bodySha256) fail(`${type} body`);
  if ((type === "home" && value.authenticated !== true) || (type === "legacy" && value.accessible !== true)) fail(`${type} access`);
  const links = linkInventory(value.applicationLinks, `${type} application inventory`);
  return {
    url: exactUrl(value.url, expectedPath, `${type} URL`),
    observedMs: milliseconds(value.observedAt, `${type} timestamp`),
    body,
    bodySha256: value.bodySha256,
    applicationIds: links.ids,
    applicationLinkCount: links.count,
    applicationLinkDigest: links.digest,
  };
}
function exactExcerpt(body, value, expectedValue, label) {
  const excerpt = String(value == null ? "" : value);
  if (!excerpt || excerpt.trim() !== excerpt || excerpt.length > 500 || !excerpt.includes(expectedValue) || !body.includes(excerpt)) fail(label);
  return sha(excerpt);
}
function surfaceLabel(value, label) {
  const text = String(value == null ? "" : value);
  if (!text || text.trim() !== text || text.length > 100 || /[\u0000-\u001f\u007f]/.test(text)) fail(label);
  return text;
}

function buildYcLegacyContinuationReceipt(input = {}, options = {}) {
  exactKeys(input, ["recordedAt", "legacyApplicationId", "currentApplicationId", "home", "legacy", "assessment", "effects"], "input schema");
  const legacyId = String(input.legacyApplicationId || "").toLowerCase();
  const currentId = String(input.currentApplicationId || "").toLowerCase();
  if (legacyId !== LEGACY_ID || currentId !== CURRENT_ID || legacyId === currentId) fail("application identity");
  const home = source(input.home, "home", "/home");
  const legacy = source(input.legacy, "legacy", `/apps/${legacyId}`);
  if (!home.applicationIds.includes(currentId) || home.applicationIds.includes(legacyId)
    || !legacy.applicationIds.includes(legacyId) || legacy.applicationIds.includes(currentId)) fail("application relationship");
  const recordedMs = milliseconds(input.recordedAt, "recorded timestamp");
  const nowMs = (options.now || Date.now)();
  if (!Number.isFinite(nowMs) || home.observedMs > legacy.observedMs || legacy.observedMs > recordedMs
    || recordedMs > nowMs || nowMs - recordedMs > 5 * 60_000 || recordedMs - home.observedMs > 15 * 60_000) fail("observation chronology");

  const assessment = input.assessment;
  exactKeys(assessment, ["decision", "homeBatch", "homeStatus", "legacyBatch", "continuationControlObserved", "homeBatchExcerpt", "homeStatusExcerpt", "legacyBatchExcerpt", "rationale"], "assessment schema");
  const reason = String(assessment.rationale == null ? "" : assessment.rationale);
  const homeBatch = surfaceLabel(assessment.homeBatch, "home batch label");
  const homeStatus = surfaceLabel(assessment.homeStatus, "home status label");
  const legacyBatch = surfaceLabel(assessment.legacyBatch, "legacy batch label");
  if (assessment.decision !== "separate_historical_application" || assessment.continuationControlObserved !== false
    || !reason || reason.trim() !== reason || reason.length > 1_000) fail("assessment");
  const excerptDigests = {
    home_batch: exactExcerpt(home.body, assessment.homeBatchExcerpt, homeBatch, "home batch excerpt"),
    home_status: exactExcerpt(home.body, assessment.homeStatusExcerpt, homeStatus, "home status excerpt"),
    legacy_batch: exactExcerpt(legacy.body, assessment.legacyBatchExcerpt, legacyBatch, "legacy batch excerpt"),
  };

  const effects = input.effects;
  exactKeys(effects, ["browserRef", "endpoint", "existingPageCount", "createdOwnedPages", "closedOwnedPages", "browserCloseOperations", "writeOperations", "submitOperations"], "effects schema");
  if (effects.browserRef !== "browser-profile://cloakbrowser/daily-driver" || effects.endpoint !== "http://127.0.0.1:9222"
    || !Number.isSafeInteger(effects.existingPageCount) || effects.existingPageCount < 0
    || effects.createdOwnedPages !== 1 || effects.closedOwnedPages !== 1 || effects.browserCloseOperations !== 0
    || effects.writeOperations !== 0 || effects.submitOperations !== 0) fail("effects");

  const core = {
    schema_version: 1,
    task: "O1C-22",
    recorded_at: new Date(recordedMs).toISOString(),
    decision: "separate_historical_application",
    same_application: false,
    legacy_application_id: legacyId,
    current_application_id: currentId,
    current_home: {
      url: home.url,
      observed_at: new Date(home.observedMs).toISOString(),
      authenticated: true,
      body_sha256: home.bodySha256,
      body_length: home.body.length,
      application_ids: home.applicationIds,
      application_link_count: home.applicationLinkCount,
      application_link_inventory_sha256: home.applicationLinkDigest,
      current_link_present: true,
      legacy_link_present: false,
      batch: homeBatch,
      status: homeStatus,
    },
    legacy_preview: {
      url: legacy.url,
      observed_at: new Date(legacy.observedMs).toISOString(),
      accessible: true,
      body_sha256: legacy.bodySha256,
      body_length: legacy.body.length,
      application_ids: legacy.applicationIds,
      application_link_count: legacy.applicationLinkCount,
      application_link_inventory_sha256: legacy.applicationLinkDigest,
      batch: legacyBatch,
    },
    assessment_proof: {
      decision_owner: "agent",
      excerpt_sha256: excerptDigests,
      reason_sha256: sha(reason),
      continuation_control_observed: false,
    },
    safe_operational_action: "keep_current_application_no_duplicate",
    effects: {
      browser_ref: effects.browserRef,
      endpoint: effects.endpoint,
      existing_page_count: effects.existingPageCount,
      created_owned_pages: 1,
      closed_owned_pages: 1,
      browser_close_operations: 0,
      write_operations: 0,
      submit_operations: 0,
    },
  };
  return deepFreeze({ ...core, receipt_digest: sha(stable(core)) });
}

module.exports = { buildYcLegacyContinuationReceipt };
