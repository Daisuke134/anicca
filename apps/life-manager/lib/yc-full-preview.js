"use strict";

const { createHash } = require("node:crypto");

const SHA256 = /^[0-9a-f]{64}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const RFC3339 = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;
const ISSUE_CODE = /^[a-z][a-z0-9_]{2,79}$/;
const APPLICATION_ID = "0b61fe42-e383-490d-b60e-04f1ad7ec5df";
const APPLICATION_ORIGIN = "https://apply.ycombinator.com";
const APPLICATION_PATH = `/apps/${APPLICATION_ID}`;
const SCOPE_ORDER = Object.freeze(["company_facts", "founder_profile", "founder_video", "demo", "progress"]);
const SOURCE_REFS = Object.freeze({
  readme_en: "repo://README.md",
  readme_ja: "repo://README.ja.md",
  agent_registry: "repo://agents/registry.json",
  provider_manifest: "repo://apps/life-manager/config/yc-application-provider.json",
  answer_draft: "workspace://funders/results/FT-YC/yc-answers-lifemanager-2026fall.json",
  application_kit: "application-kit://KIT.md",
  founder_video_source: "application-kit://videos/Anicca_intro_EN.mp4",
  demo_source: "workspace://funders/assets/life-manager-demo.mp4",
});
const REQUIRED_SOURCE_ROLES = Object.freeze(Object.keys(SOURCE_REFS).filter((role) => role !== "demo_source"));
const EFFECT_KEYS = Object.freeze([
  "read_only_navigations",
  "owned_page_closes",
  "form_field_writes",
  "option_selections",
  "file_attachments",
  "save_controls",
  "update_submissions",
  "application_submissions",
  "browser_closes",
]);
const MUTATION_EFFECTS = Object.freeze(EFFECT_KEYS.slice(2));

function fail(reason) {
  throw new Error(`YC full preview ${reason} invalid`);
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

function timestamp(value, label) {
  const text = String(value == null ? "" : value);
  if (!RFC3339.test(text)) fail(label);
  const milliseconds = Date.parse(text);
  if (!Number.isFinite(milliseconds) || new Date(milliseconds).toISOString() !== text) fail(label);
  return { text, milliseconds };
}

function nowMilliseconds(value) {
  if (value instanceof Date) return value.getTime();
  if (typeof value === "function") return Number(value());
  if (value == null) return Date.now();
  const parsed = Date.parse(String(value));
  if (!Number.isFinite(parsed)) fail("wall clock");
  return parsed;
}

function safePositiveInteger(value, label) {
  if (!Number.isSafeInteger(value) || value <= 0) fail(label);
  return value;
}

function finitePositive(value, label, maximum = Number.MAX_SAFE_INTEGER) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0 || number > maximum) fail(label);
  return number;
}

function digest(value, label) {
  const text = String(value || "");
  if (!SHA256.test(text)) fail(label);
  return text;
}

function issueCodes(value, label) {
  if (!Array.isArray(value) || new Set(value).size !== value.length) fail(label);
  const codes = value.map(String);
  if (codes.some((code) => !ISSUE_CODE.test(code))) fail(label);
  return codes;
}

function parseApplication(value) {
  exactKeys(value, ["id", "batch", "state", "prior_application_submit_count", "origin", "path", "observed_at"], "application");
  if (!UUID.test(String(value.id || "")) || String(value.id).toLowerCase() !== APPLICATION_ID
    || value.batch !== "Fall 2026" || value.state !== "In review"
    || value.prior_application_submit_count !== 1
    || value.origin !== APPLICATION_ORIGIN || value.path !== APPLICATION_PATH) fail("application identity");
  const observed = timestamp(value.observed_at, "application observation");
  return {
    value: {
      id: APPLICATION_ID,
      batch: "Fall 2026",
      state: "In review",
      prior_application_submit_count: 1,
      origin: APPLICATION_ORIGIN,
      path: APPLICATION_PATH,
      observed_at: observed.text,
    },
    observedMs: observed.milliseconds,
  };
}

function parseSources(value) {
  if (!Array.isArray(value) || value.length < REQUIRED_SOURCE_ROLES.length || value.length > REQUIRED_SOURCE_ROLES.length + 1) fail("source set");
  const roles = value.map(({ role }) => String(role || ""));
  if (new Set(roles).size !== roles.length || REQUIRED_SOURCE_ROLES.some((role) => !roles.includes(role))
    || roles.some((role) => !Object.hasOwn(SOURCE_REFS, role))) fail("source set");
  const parsed = value.map((item) => {
    exactKeys(item, ["role", "ref", "observed_at", "sha256", "bytes"], "source");
    const role = String(item.role || "");
    if (item.ref !== SOURCE_REFS[role]) fail("source ref");
    const observed = timestamp(item.observed_at, "source observation");
    return {
      value: {
        role,
        ref: item.ref,
        observed_at: observed.text,
        sha256: digest(item.sha256, "source digest"),
        bytes: safePositiveInteger(item.bytes, "source bytes"),
      },
      observedMs: observed.milliseconds,
    };
  });
  parsed.sort((a, b) => Object.keys(SOURCE_REFS).indexOf(a.value.role) - Object.keys(SOURCE_REFS).indexOf(b.value.role));
  return parsed;
}

function parseRoleSet(value, knownRoles, label) {
  if (!Array.isArray(value) || new Set(value).size !== value.length) fail(label);
  const roles = value.map(String);
  if (roles.some((role) => !knownRoles.has(role))) fail(label);
  return roles;
}

function parseRemoteMedia(value, label) {
  exactKeys(value, ["ready_state", "duration_seconds", "width", "height", "storage_origin", "source_path_sha256"], label);
  if (value.ready_state !== 4 || value.storage_origin !== "https://yc-app-vids.s3.us-west-2.amazonaws.com") fail(label);
  return {
    ready_state: 4,
    duration_seconds: finitePositive(value.duration_seconds, `${label} duration`, 60),
    width: safePositiveInteger(value.width, `${label} width`),
    height: safePositiveInteger(value.height, `${label} height`),
    storage_origin: value.storage_origin,
    source_path_sha256: digest(value.source_path_sha256, `${label} path digest`),
  };
}

function parseCompanyObservation(value) {
  exactKeys(value, ["field_count", "value_set_digest"], "company observation");
  return { field_count: safePositiveInteger(value.field_count, "company field count"), value_set_digest: digest(value.value_set_digest, "company value digest") };
}

function parseFounderObservation(value) {
  exactKeys(value, ["structurally_complete", "section_count", "value_set_digest"], "founder observation");
  if (typeof value.structurally_complete !== "boolean") fail("founder structural state");
  return { structurally_complete: value.structurally_complete, section_count: safePositiveInteger(value.section_count, "founder section count"), value_set_digest: digest(value.value_set_digest, "founder value digest") };
}

function parseFounderVideoObservation(value) {
  exactKeys(value, ["remote", "local"], "founder video observation");
  exactKeys(value.local, ["duration_seconds", "bytes", "container", "video_codec", "audio_codec", "width", "height"], "founder video local");
  if (value.local.container !== "mp4" || value.local.video_codec !== "h264" || value.local.audio_codec !== "aac") fail("founder video local");
  return {
    remote: parseRemoteMedia(value.remote, "founder video remote"),
    local: {
      duration_seconds: finitePositive(value.local.duration_seconds, "founder video local duration", 60),
      bytes: safePositiveInteger(value.local.bytes, "founder video local bytes"),
      container: "mp4",
      video_codec: "h264",
      audio_codec: "aac",
      width: safePositiveInteger(value.local.width, "founder video local width"),
      height: safePositiveInteger(value.local.height, "founder video local height"),
    },
  };
}

function parseDemoObservation(value, status, roles) {
  exactKeys(value, ["dedicated_source_role", "remote"], "demo observation");
  if (status === "missing") {
    if (value.dedicated_source_role !== null || value.remote !== null || roles.length !== 0) fail("missing demo");
    return { dedicated_source_role: null, remote: null };
  }
  if (value.dedicated_source_role !== "demo_source" || roles.length !== 1 || roles[0] !== "demo_source") fail("demo provenance");
  return { dedicated_source_role: "demo_source", remote: parseRemoteMedia(value.remote, "demo remote") };
}

function parseProgressObservation(value) {
  exactKeys(value, ["field_count", "value_set_digest", "update_control_present"], "progress observation");
  if (typeof value.update_control_present !== "boolean") fail("progress control state");
  return { field_count: safePositiveInteger(value.field_count, "progress field count"), value_set_digest: digest(value.value_set_digest, "progress value digest"), update_control_present: value.update_control_present };
}

function parseScopes(value, sources) {
  if (!Array.isArray(value) || value.length !== SCOPE_ORDER.length) fail("scope set");
  if (stable(value.map(({ scope }) => scope)) !== stable(SCOPE_ORDER)) fail("scope order");
  const knownRoles = new Set(sources.map(({ value: source }) => source.role));
  return value.map((item) => {
    exactKeys(item, ["scope", "status", "observed_at", "source_roles", "issue_codes", "observation"], "scope");
    const observed = timestamp(item.observed_at, `${item.scope} observation`);
    const roles = parseRoleSet(item.source_roles, knownRoles, `${item.scope} source roles`);
    const issues = issueCodes(item.issue_codes, `${item.scope} issues`);
    let allowed;
    let observation;
    if (item.scope === "company_facts") {
      allowed = new Set(["current", "stale"]);
      if (roles.length < 1) fail("company source roles");
      observation = parseCompanyObservation(item.observation);
    } else if (item.scope === "founder_profile") {
      allowed = new Set(["current", "needs_review"]);
      if (roles.length < 1) fail("founder source roles");
      observation = parseFounderObservation(item.observation);
    } else if (item.scope === "founder_video") {
      allowed = new Set(["present"]);
      if (roles.length !== 1 || roles[0] !== "founder_video_source") fail("founder video provenance");
      observation = parseFounderVideoObservation(item.observation);
    } else if (item.scope === "demo") {
      allowed = new Set(["present", "missing"]);
      observation = parseDemoObservation(item.observation, item.status, roles);
    } else if (item.scope === "progress") {
      allowed = new Set(["current", "stale"]);
      if (roles.length < 1) fail("progress source roles");
      observation = parseProgressObservation(item.observation);
    }
    if (!allowed || !allowed.has(item.status)) fail(`${item.scope} status`);
    const good = item.status === "current" || item.status === "present";
    if ((good && issues.length !== 0) || (!good && issues.length === 0)) fail(`${item.scope} issue consistency`);
    return {
      value: { scope: item.scope, status: item.status, observed_at: observed.text, source_roles: roles, issue_codes: issues, observation },
      observedMs: observed.milliseconds,
    };
  });
}

function parseEffects(value) {
  exactKeys(value, EFFECT_KEYS, "effects");
  if (value.read_only_navigations !== 5 || value.owned_page_closes !== 5) fail("read effect count");
  for (const key of MUTATION_EFFECTS) {
    if (value[key] !== 0) fail(`${key} effect`);
  }
  return Object.fromEntries(EFFECT_KEYS.map((key) => [key, value[key]]));
}

function parseAssessment(value, scopes) {
  exactKeys(value, ["decision_owner", "preview_complete", "submit_ready", "blocking_issue_codes"], "assessment");
  if (value.decision_owner !== "agent" || value.preview_complete !== true || typeof value.submit_ready !== "boolean") fail("assessment");
  const blocking = issueCodes(value.blocking_issue_codes, "blocking issues");
  const observed = [];
  for (const { value: scope } of scopes) for (const code of scope.issue_codes) if (!observed.includes(code)) observed.push(code);
  if (stable(blocking) !== stable(observed) || value.submit_ready !== (blocking.length === 0)) fail("submit readiness");
  return { decision_owner: "agent", preview_complete: true, submit_ready: value.submit_ready, blocking_issue_codes: blocking };
}

function parseCore(value, { input = false } = {}) {
  exactKeys(value, input
    ? ["verified_at", "application", "sources", "scopes", "assessment", "effects"]
    : ["schema_version", "verified_at", "application", "sources", "scopes", "decision_owner", "preview_complete", "submit_ready", "blocking_issue_codes", "effects"], input ? "input" : "receipt");
  if (!input && value.schema_version !== 1) fail("schema version");
  const verified = timestamp(value.verified_at, "verified timestamp");
  const application = parseApplication(value.application);
  const sources = parseSources(value.sources);
  const scopes = parseScopes(value.scopes, sources);
  const assessmentInput = input ? value.assessment : {
    decision_owner: value.decision_owner,
    preview_complete: value.preview_complete,
    submit_ready: value.submit_ready,
    blocking_issue_codes: value.blocking_issue_codes,
  };
  const assessment = parseAssessment(assessmentInput, scopes);
  const effects = parseEffects(value.effects);
  const observations = [application.observedMs, ...sources.map(({ observedMs }) => observedMs), ...scopes.map(({ observedMs }) => observedMs)];
  if (Math.max(...observations) > verified.milliseconds
    || verified.milliseconds - Math.min(...observations) > 15 * 60_000) fail("receipt chronology");
  return {
    verified,
    application: application.value,
    sources: sources.map(({ value: source }) => source),
    scopes: scopes.map(({ value: scope }) => scope),
    assessment,
    effects,
  };
}

function buildYcFullPreviewReceipt(input = {}, options = {}) {
  const parsed = parseCore(input, { input: true });
  const nowMs = nowMilliseconds(options.now);
  if (!Number.isFinite(nowMs) || parsed.verified.milliseconds > nowMs || nowMs - parsed.verified.milliseconds > 5 * 60_000) fail("receipt freshness");
  const core = {
    schema_version: 1,
    verified_at: parsed.verified.text,
    application: parsed.application,
    sources: parsed.sources,
    scopes: parsed.scopes,
    decision_owner: parsed.assessment.decision_owner,
    preview_complete: parsed.assessment.preview_complete,
    submit_ready: parsed.assessment.submit_ready,
    blocking_issue_codes: parsed.assessment.blocking_issue_codes,
    effects: parsed.effects,
  };
  return deepFreeze({ ...core, preview_receipt_digest: sha(stable(core)) });
}

function validateYcFullPreviewReceiptStructure(receipt = {}) {
  exactKeys(receipt, ["schema_version", "verified_at", "application", "sources", "scopes", "decision_owner", "preview_complete", "submit_ready", "blocking_issue_codes", "effects", "preview_receipt_digest"], "receipt envelope");
  const { preview_receipt_digest: declared, ...core } = receipt;
  digest(declared, "receipt digest");
  parseCore(core);
  if (sha(stable(core)) !== declared) fail("receipt digest");
  return true;
}

module.exports = { buildYcFullPreviewReceipt, validateYcFullPreviewReceiptStructure };
