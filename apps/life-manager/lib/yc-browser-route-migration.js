"use strict";

const { createHash } = require("node:crypto");
const { validateFunderBrowserRoutes } = require("./funder-browser-policy.js");
const { loadYcApplicationProviderManifest } = require("./yc-application-provider.js");

const SHA = /^[0-9a-f]{64}$/;
const MAX_BODY_BYTES = 2 * 1024 * 1024;
const MAX_SOURCE_SPAN_MS = 15 * 60 * 1000;
const MAX_RECEIPT_AGE_MS = 5 * 60 * 1000;
const EXPECTED_COMMAND = "bash $HOME/.openclaw/skills/_dispatcher/scripts/cron-bash.sh apply-to-funder/scripts/run.sh --funder yc-w26";
const ARTIFACT_REFS = Object.freeze({
  checked_in_skill: "repo://apps/life-manager/runtime-assets/apply-to-yc/SKILL.md",
  checked_in_shim: "repo://apps/life-manager/runtime-assets/apply-to-yc/scripts/apply.sh",
  installed_skill: "openclaw://skills/apply-to-yc/SKILL.md",
  installed_shim: "openclaw://skills/apply-to-yc/scripts/apply.sh",
  successor_run: "openclaw://skills/apply-to-funder/scripts/run.sh",
  successor_form_filler: "openclaw://skills/apply-to-funder/scripts/lib/form_filler.sh",
  recovery_inventory: "recovery://apply-to-yc/inventory.json",
});
const EFFECT_KEYS = Object.freeze([
  "browser_launch",
  "owned_read_only_navigation",
  "form_write",
  "file_write",
  "save",
  "submit",
  "browser_close",
  "owned_page_close",
  "gig_process_signal",
]);

function fail() {
  throw new Error("YC browser route migration invalid");
}

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function digest(value) {
  return createHash("sha256").update(typeof value === "string" ? value : stable(value), "utf8").digest("hex");
}

function exactKeys(value, keys) {
  if (!value || typeof value !== "object" || Array.isArray(value)
    || stable(Object.keys(value).sort()) !== stable([...keys].sort())) fail();
}

function deepFreeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const nested of Object.values(value)) deepFreeze(nested);
  }
  return value;
}

function canonicalTime(value) {
  if (typeof value !== "string") fail();
  const ms = Date.parse(value);
  if (!Number.isFinite(ms) || new Date(ms).toISOString() !== value) fail();
  return ms;
}

function safePid(value) {
  return Number.isSafeInteger(value) && value > 0;
}

function validateRouteAndProvider(routeManifest, providerManifest) {
  const routeSummary = validateFunderBrowserRoutes(structuredClone(routeManifest));
  if (routeSummary.browser_ref !== "browser-profile://cloakbrowser/daily-driver"
    || routeSummary.endpoint !== "http://127.0.0.1:9222") fail();
  const route = routeManifest.routes.find(({ route_id: routeId }) => routeId === "yc-application");
  if (!route
    || route.provider_id !== "yc-fall-2026"
    || route.origin_binding !== "exact"
    || route.form_origin !== "https://apply.ycombinator.com") fail();

  const provider = loadYcApplicationProviderManifest({
    readFile: () => JSON.stringify(providerManifest),
  });
  if (provider.provider_id !== "yc-application"
    || provider.successor_provider !== "apply-to-funder"
    || provider.ported_from !== "apply-to-yc"
    || provider.browser_route_id !== "yc-application"
    || provider.mode !== "preview_only"
    || provider.submit_operations !== 0) fail();
  return {
    browser_ref: routeSummary.browser_ref,
    endpoint: routeSummary.endpoint,
    connection_mode: routeManifest.connection_mode,
    shared_context_count: routeManifest.shared_context_count,
    route_id: route.route_id,
    provider_id: route.provider_id,
    form_origin: route.form_origin,
    successor: provider.successor_provider,
    funder_id: "yc-w26",
    route_manifest_sha256: digest(routeManifest),
    provider_manifest_sha256: digest(providerManifest),
  };
}

function validateArtifacts(artifacts, observedTimes) {
  if (!Array.isArray(artifacts) || artifacts.length !== Object.keys(ARTIFACT_REFS).length) fail();
  const byRole = new Map();
  const output = [];
  for (const item of artifacts) {
    exactKeys(item, ["role", "ref", "observed_at", "body", "body_sha256", "body_length"]);
    if (!Object.hasOwn(ARTIFACT_REFS, item.role) || byRole.has(item.role)
      || item.ref !== ARTIFACT_REFS[item.role]
      || typeof item.body !== "string") fail();
    const bodyLength = Buffer.byteLength(item.body, "utf8");
    if (bodyLength < 1 || bodyLength > MAX_BODY_BYTES || item.body_length !== bodyLength
      || !SHA.test(item.body_sha256) || digest(item.body) !== item.body_sha256) fail();
    const observed = canonicalTime(item.observed_at);
    observedTimes.push(observed);
    byRole.set(item.role, item);
    output.push({
      role: item.role,
      ref: item.ref,
      observed_at: item.observed_at,
      body_sha256: item.body_sha256,
      body_length: item.body_length,
    });
  }
  for (const role of Object.keys(ARTIFACT_REFS)) if (!byRole.has(role)) fail();
  if (byRole.get("checked_in_skill").body_sha256 !== byRole.get("installed_skill").body_sha256
    || byRole.get("checked_in_shim").body_sha256 !== byRole.get("installed_shim").body_sha256) fail();
  return { byRole, output };
}

function validateBrowsers(browsers, observedTimes) {
  if (!Array.isArray(browsers) || browsers.length !== 2) fail();
  const expected = {
    daily_driver: {
      endpoint: "http://127.0.0.1:9222",
      profile_ref: "cloak-profile://daily-driver",
    },
    gig_driver: {
      endpoint: "http://127.0.0.1:9223",
      profile_ref: "cloak-profile://gig-daily-driver",
    },
  };
  const roles = new Set();
  const output = [];
  for (const item of browsers) {
    exactKeys(item, ["role", "endpoint", "pid", "preserved_pid", "profile_ref", "browser", "protocol_version", "observed_at"]);
    const contract = expected[item.role];
    if (!contract || roles.has(item.role) || item.endpoint !== contract.endpoint
      || item.profile_ref !== contract.profile_ref || !safePid(item.pid)
      || item.preserved_pid !== item.pid || typeof item.browser !== "string"
      || !/^Chrome\/[0-9]+(?:\.[0-9]+){3}$/.test(item.browser)
      || item.protocol_version !== "1.3") fail();
    observedTimes.push(canonicalTime(item.observed_at));
    roles.add(item.role);
    output.push(structuredClone(item));
  }
  if (roles.size !== 2) fail();
  return { byRole: new Map(output.map((item) => [item.role, item])), output };
}

function validateCron(cron, observedTimes) {
  exactKeys(cron, ["id", "name", "enabled", "command", "live_readback", "durable_readback", "observed_at"]);
  if (cron.id !== "accelerator-application-monthly-1777948324077"
    || cron.name !== "accelerator-application-monthly" || cron.enabled !== false
    || cron.command !== EXPECTED_COMMAND || cron.live_readback !== true
    || cron.durable_readback !== true) fail();
  observedTimes.push(canonicalTime(cron.observed_at));
  return structuredClone(cron);
}

function validateDeployment(deployment, artifactsByRole, browsersByRole) {
  exactKeys(deployment, [
    "recovery_ref",
    "recovery_inventory_sha256",
    "installed_skill_sha256",
    "installed_shim_sha256",
    "retired_helpers",
    "installed_readback_exact",
    "gig_driver_pid_before",
    "gig_driver_pid_after",
  ]);
  const recovery = artifactsByRole.get("recovery_inventory");
  const gig = browsersByRole.get("gig_driver");
  if (!SHA.test(deployment.recovery_inventory_sha256)
    || deployment.recovery_inventory_sha256 !== recovery.body_sha256
    || deployment.recovery_ref !== `~/.openclaw/recovery/apply-to-yc/o1c24-${recovery.body_sha256}`
    || deployment.installed_skill_sha256 !== artifactsByRole.get("installed_skill").body_sha256
    || deployment.installed_shim_sha256 !== artifactsByRole.get("installed_shim").body_sha256
    || stable(deployment.retired_helpers) !== stable(["scripts/fill.js", "scripts/progress.js"])
    || deployment.installed_readback_exact !== true
    || deployment.gig_driver_pid_before !== gig.pid
    || deployment.gig_driver_pid_after !== gig.pid) fail();
  return structuredClone(deployment);
}

function validateEffects(effects) {
  exactKeys(effects, EFFECT_KEYS);
  for (const key of EFFECT_KEYS) {
    const expected = key === "owned_read_only_navigation" || key === "owned_page_close" ? 1 : 0;
    if (effects[key] !== expected) fail();
  }
  return structuredClone(effects);
}

function validateReceiptCore(receipt) {
  exactKeys(receipt, ["schema_version", "verified_at", "route", "artifacts", "browsers", "cron", "deployment", "effects", "migration_receipt_digest"]);
  if (receipt.schema_version !== 1 || !SHA.test(receipt.migration_receipt_digest)) fail();
  canonicalTime(receipt.verified_at);
  exactKeys(receipt.route, ["browser_ref", "endpoint", "connection_mode", "shared_context_count", "route_id", "provider_id", "form_origin", "successor", "funder_id", "route_manifest_sha256", "provider_manifest_sha256"]);
  if (receipt.route.browser_ref !== "browser-profile://cloakbrowser/daily-driver"
    || receipt.route.endpoint !== "http://127.0.0.1:9222"
    || receipt.route.connection_mode !== "connect_over_cdp"
    || receipt.route.shared_context_count !== 1
    || receipt.route.route_id !== "yc-application"
    || receipt.route.provider_id !== "yc-fall-2026"
    || receipt.route.form_origin !== "https://apply.ycombinator.com"
    || receipt.route.successor !== "apply-to-funder"
    || receipt.route.funder_id !== "yc-w26"
    || !SHA.test(receipt.route.route_manifest_sha256)
    || !SHA.test(receipt.route.provider_manifest_sha256)) fail();
  if (!Array.isArray(receipt.artifacts) || receipt.artifacts.length !== Object.keys(ARTIFACT_REFS).length) fail();
  const artifactRoles = new Set();
  const artifactsByRole = new Map();
  for (const item of receipt.artifacts) {
    exactKeys(item, ["role", "ref", "observed_at", "body_sha256", "body_length"]);
    if (!Object.hasOwn(ARTIFACT_REFS, item.role) || artifactRoles.has(item.role)
      || item.ref !== ARTIFACT_REFS[item.role] || !SHA.test(item.body_sha256)
      || !Number.isSafeInteger(item.body_length) || item.body_length < 1
      || item.body_length > MAX_BODY_BYTES) fail();
    canonicalTime(item.observed_at);
    artifactRoles.add(item.role);
    artifactsByRole.set(item.role, item);
  }
  if (artifactRoles.size !== Object.keys(ARTIFACT_REFS).length
    || artifactsByRole.get("checked_in_skill").body_sha256 !== artifactsByRole.get("installed_skill").body_sha256
    || artifactsByRole.get("checked_in_shim").body_sha256 !== artifactsByRole.get("installed_shim").body_sha256) fail();
  const browsers = validateBrowsers(receipt.browsers, []);
  validateCron(receipt.cron, []);
  validateDeployment(receipt.deployment, artifactsByRole, browsers.byRole);
  validateEffects(receipt.effects);
  const { migration_receipt_digest: claimed, ...core } = receipt;
  if (digest(core) !== claimed) fail();
  return receipt;
}

function buildYcBrowserRouteMigrationReceipt(input = {}, options = {}) {
  exactKeys(input, ["verified_at", "route_manifest", "provider_manifest", "artifacts", "browsers", "cron", "deployment", "effects"]);
  const now = typeof options.now === "function" ? options.now() : Date.now();
  if (!Number.isFinite(now)) fail();
  const verifiedAt = canonicalTime(input.verified_at);
  if (verifiedAt > now || now - verifiedAt > MAX_RECEIPT_AGE_MS) fail();

  const observedTimes = [];
  const route = validateRouteAndProvider(input.route_manifest, input.provider_manifest);
  const artifacts = validateArtifacts(input.artifacts, observedTimes);
  const browsers = validateBrowsers(input.browsers, observedTimes);
  const cron = validateCron(input.cron, observedTimes);
  const deployment = validateDeployment(input.deployment, artifacts.byRole, browsers.byRole);
  const effects = validateEffects(input.effects);
  if (observedTimes.length === 0
    || observedTimes.some((observed) => observed > verifiedAt)
    || verifiedAt - Math.min(...observedTimes) > MAX_SOURCE_SPAN_MS
    || Math.max(...observedTimes) - Math.min(...observedTimes) > MAX_SOURCE_SPAN_MS) fail();

  const core = {
    schema_version: 1,
    verified_at: input.verified_at,
    route,
    artifacts: artifacts.output,
    browsers: browsers.output,
    cron,
    deployment,
    effects,
  };
  const receipt = { ...core, migration_receipt_digest: digest(core) };
  validateReceiptCore(receipt);
  return deepFreeze(receipt);
}

function validateYcBrowserRouteMigrationReceiptStructure(receipt) {
  validateReceiptCore(structuredClone(receipt));
  return true;
}

module.exports = {
  buildYcBrowserRouteMigrationReceipt,
  validateYcBrowserRouteMigrationReceiptStructure,
};
