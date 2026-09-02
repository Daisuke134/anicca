"use strict";

const { createHash } = require("node:crypto");

const SHA = /^[0-9a-f]{64}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TYPES = Object.freeze(["demo_update", "progress_update", "team_update", "founder_profile_update"]);
const CONDITIONAL = new Set(["demo_update", "team_update", "founder_profile_update"]);
const PAYLOAD_KEYS = Object.freeze({
  demo_update: ["demo_video"],
  progress_update: ["productLink", "productCreds", "howfar", "worked", "techstack", "people_using", "have_revenue"],
  team_update: ["others2", "cofounder"],
  founder_profile_update: ["fhack", "fability", "projects", "awards", "testScores", "clubs"],
});
const EFFECT_KEYS = Object.freeze(["form_field_writes", "option_selections", "file_attachments", "update_control_activations", "application_submissions", "browser_closes"]);
const FENCE_KEYS = Object.freeze(["schema_version", "plan_digest", "operation_id", "operation_type", "payload_digest", "expected_readback_digest", "state", "prepared_at", "effect_attempted_at", "readback_at", "activation_count", "readback_digest", "fence_digest"]);

function fail(reason) { throw new Error(`YC typed update ${reason} invalid`); }
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
function digest(value) { return createHash("sha256").update(stable(value), "utf8").digest("hex"); }
function exactKeys(value, keys, label) {
  if (!value || typeof value !== "object" || Array.isArray(value) || stable(Object.keys(value).sort()) !== stable([...keys].sort())) fail(label);
}
function deepFreeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const nested of Object.values(value)) deepFreeze(nested);
  }
  return value;
}
function instant(value, label) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value) || !Number.isFinite(Date.parse(value))) fail(label);
  return Date.parse(value);
}
function nonSecretText(value) {
  return typeof value === "string" && value.trim() === value && value.length > 0 && value.length <= 10000 && !/(?:password\s*[:=]|api[_ -]?key\s*[:=]|cookie\s*[:=]|bearer\s+[a-z0-9._-]+)/i.test(value);
}
function expectedRoute(id, type) {
  if (type === "demo_update") return `/apps/${id}/edit/demo`;
  if (type === "progress_update") return `/apps/${id}/edit/progress`;
  if (type === "team_update") return `/apps/${id}/edit/cofounder`;
  return "/bio/721f696b-0566-4a16-bda7-a9c368b1eac1/edit";
}
function validatePayload(type, disposition, payload) {
  if (disposition === "omit_equal") {
    if (!CONDITIONAL.has(type)) fail("required operation omission");
    if (type !== "demo_update") {
      exactKeys(payload, [], "omitted payload");
      return;
    }
  }
  exactKeys(payload, PAYLOAD_KEYS[type], `${type} payload`);
  if (type === "demo_update") {
    exactKeys(payload.demo_video, ["source_ref", "artifact_digest"], "demo source");
    if (!/^application-kit:\/\/videos\/[A-Za-z0-9._-]+\.mp4$/.test(payload.demo_video.source_ref) || !SHA.test(payload.demo_video.artifact_digest)) fail("demo source");
    return;
  }
  for (const [key, value] of Object.entries(payload)) {
    if (["people_using", "have_revenue"].includes(key)) {
      if (typeof value !== "boolean") fail("progress choice");
    } else if (!nonSecretText(value)) fail("payload text");
  }
  if (type === "progress_update" && !/^https:\/\//.test(payload.productLink)) fail("product link");
}

function buildYcTypedUpdatePlan(input = {}, options = {}) {
  exactKeys(input, ["verified_at", "application", "provider_manifest_digest", "preview", "operations", "effects"], "input");
  const now = instant(options.now || new Date().toISOString(), "now");
  const verifiedAt = instant(input.verified_at, "verified_at");
  if (verifiedAt > now || now - verifiedAt > 300000) fail("freshness");
  exactKeys(input.application, ["id", "batch", "state", "prior_application_submit_count"], "application");
  const id = String(input.application.id || "").toLowerCase();
  if (!UUID.test(id) || input.application.batch !== "Fall 2026" || input.application.state !== "In review" || input.application.prior_application_submit_count !== 1) fail("application boundary");
  if (!SHA.test(String(input.provider_manifest_digest || ""))) fail("provider digest");
  exactKeys(input.preview, ["preview_complete", "submit_ready", "blocking_issue_codes", "preview_receipt_digest"], "preview");
  if (input.preview.preview_complete !== true || input.preview.submit_ready !== true || !Array.isArray(input.preview.blocking_issue_codes) || input.preview.blocking_issue_codes.length !== 0 || !SHA.test(String(input.preview.preview_receipt_digest || ""))) fail("preview gate");
  exactKeys(input.effects, EFFECT_KEYS, "effects");
  if (EFFECT_KEYS.some((key) => input.effects[key] !== 0)) fail("pre-effect boundary");
  if (!Array.isArray(input.operations) || input.operations.length !== TYPES.length || stable(input.operations.map(({ operation_type }) => operation_type)) !== stable(TYPES)) fail("operation inventory");
  const operations = input.operations.map((operation) => {
    exactKeys(operation, ["operation_type", "disposition", "route", "payload", "observed_at", "expected_readback_digest"], "operation");
    const type = operation.operation_type;
    if (!TYPES.includes(type) || !["execute", "omit_equal"].includes(operation.disposition) || operation.route !== expectedRoute(id, type) || !SHA.test(String(operation.expected_readback_digest || ""))) fail("operation contract");
    const observedAt = instant(operation.observed_at, "operation observation");
    if (observedAt > verifiedAt || verifiedAt - observedAt > 900000) fail("operation chronology");
    validatePayload(type, operation.disposition, operation.payload);
    const payloadDigest = digest(operation.payload);
    if (operation.expected_readback_digest !== payloadDigest) fail("expected readback binding");
    const assetDigest = type === "demo_update" ? operation.payload.demo_video.artifact_digest : null;
    const core = {
      operation_type: type,
      disposition: operation.disposition,
      route: operation.route,
      payload: structuredClone(operation.payload),
      payload_digest: payloadDigest,
      asset_digest: assetDigest,
      observed_at: operation.observed_at,
      expected_readback_digest: operation.expected_readback_digest,
    };
    return { ...core, operation_id: digest({ application_id: id, operation_type: type, route: operation.route, payload_digest: payloadDigest, asset_digest: assetDigest }) };
  });
  if (new Set(operations.map(({ operation_id }) => operation_id)).size !== operations.length) fail("duplicate operation identity");
  const core = {
    schema_version: 1,
    verified_at: input.verified_at,
    application: structuredClone(input.application),
    provider_manifest_digest: input.provider_manifest_digest,
    preview: structuredClone(input.preview),
    planned_application_submissions: 0,
    operations,
    effects: structuredClone(input.effects),
  };
  return deepFreeze({ ...core, plan_digest: digest(core) });
}

function fenceCore(value) {
  return Object.fromEntries(FENCE_KEYS.filter((key) => key !== "fence_digest").map((key) => [key, value[key]]));
}
function validateFence(fence) {
  exactKeys(fence, FENCE_KEYS, "fence");
  if (fence.schema_version !== 1 || !SHA.test(String(fence.plan_digest || "")) || !SHA.test(String(fence.operation_id || "")) || !TYPES.includes(fence.operation_type) || !SHA.test(String(fence.payload_digest || "")) || !SHA.test(String(fence.expected_readback_digest || "")) || !["prepared", "effect_attempted", "confirmed", "not_applied", "unknown_effect"].includes(fence.state) || !SHA.test(String(fence.fence_digest || "")) || digest(fenceCore(fence)) !== fence.fence_digest) fail("fence integrity");
  instant(fence.prepared_at, "fence prepared_at");
  if (fence.effect_attempted_at !== null) instant(fence.effect_attempted_at, "fence attempted_at");
  if (fence.readback_at !== null) instant(fence.readback_at, "fence readback_at");
  if (!Number.isSafeInteger(fence.activation_count) || fence.activation_count < 0 || fence.activation_count > 1 || (fence.activation_count === 0) !== (fence.state === "prepared")) fail("fence activation");
  return fence;
}
function sealFence(core) { return deepFreeze({ ...core, fence_digest: digest(core) }); }

function createPreparedFence(plan, operationId, options = {}) {
  if (!plan || !SHA.test(String(plan.plan_digest || "")) || !Object.isFrozen(plan)) fail("prepared plan");
  const operation = plan.operations.find(({ operation_id }) => operation_id === operationId);
  if (!operation || operation.disposition !== "execute") fail("prepared operation");
  instant(options.at, "prepared time");
  return sealFence({ schema_version: 1, plan_digest: plan.plan_digest, operation_id: operation.operation_id, operation_type: operation.operation_type, payload_digest: operation.payload_digest, expected_readback_digest: operation.expected_readback_digest, state: "prepared", prepared_at: options.at, effect_attempted_at: null, readback_at: null, activation_count: 0, readback_digest: null });
}
function markEffectAttempted(fence, options = {}) {
  validateFence(fence);
  const at = instant(options.at, "attempted time");
  if (fence.state !== "prepared" || fence.activation_count !== 0 || at < instant(fence.prepared_at, "prepared time")) fail("duplicate activation");
  return sealFence({ ...fenceCore(fence), state: "effect_attempted", effect_attempted_at: options.at, activation_count: 1 });
}
function recordOperationReadback(fence, input = {}) {
  validateFence(fence);
  exactKeys(input, ["at", "result", "readback_digest"], "readback");
  const at = instant(input.at, "readback time");
  if (fence.state !== "effect_attempted" || at < instant(fence.effect_attempted_at, "attempted time") || !["confirmed", "not_applied", "unknown_effect"].includes(input.result) || !SHA.test(String(input.readback_digest || ""))) fail("readback transition");
  if (input.result === "confirmed" && input.readback_digest !== fence.expected_readback_digest) fail("confirmed readback");
  return sealFence({ ...fenceCore(fence), state: input.result, readback_at: input.at, readback_digest: input.readback_digest });
}

module.exports = {
  buildYcTypedUpdatePlan,
  createPreparedFence,
  markEffectAttempted,
  recordOperationReadback,
  validateYcTypedUpdateFence: validateFence,
};
