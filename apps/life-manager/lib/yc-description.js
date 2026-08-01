"use strict";

const { createHash } = require("node:crypto");

const SOURCE_REF = "application-kit://KIT.md#english-one-liner";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

function buildYcDescriptionPatch(input = {}) {
  const draftId = String(input.draftId || "");
  const currentValue = String(input.currentValue == null ? "" : input.currentValue);
  const value = String(input.canonicalValue == null ? "" : input.canonicalValue);
  const sourceRef = String(input.sourceRef || "");
  const sourceDigest = String(input.sourceDigest || "");
  const unicodeLength = [...value].length;
  if (!UUID.test(draftId) || sourceRef !== SOURCE_REF || !/^[0-9a-f]{64}$/.test(sourceDigest)
    || unicodeLength < 1 || unicodeLength >= 50 || value.trim() !== value || /[\r\n]/.test(value)
    || /\{\{|\}\}|placeholder|tbd|todo/i.test(value)) {
    throw new Error("YC description input invalid");
  }
  const core = {
    schema_version: 1,
    draft_id: draftId.toLowerCase(),
    field_name: "describe",
    value,
    unicode_length: unicodeLength,
    max_exclusive: 50,
    source_ref: sourceRef,
    source_digest: sourceDigest,
    operation: currentValue === value ? "no_op" : "update",
    submit_application: false,
  };
  return Object.freeze({ ...core, patch_digest: createHash("sha256").update(stable(core)).digest("hex") });
}

module.exports = { buildYcDescriptionPatch };
