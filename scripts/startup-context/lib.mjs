import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

const REQUIRED_LINKS = ["product", "repository", "telegram", "dashboard"];

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, stableValue(value[key])]),
    );
  }
  return value;
}

export async function loadStartupContext(path) {
  const raw = await readFile(path, "utf8");
  return JSON.parse(raw);
}

export function validateStartupContext(context) {
  const errors = [];

  if (context?.schema_version !== 1) errors.push("schema_version must equal 1");
  if (!isNonEmptyString(context?.context_version)) errors.push("context_version is required");
  if (!isNonEmptyString(context?.updated_at)) errors.push("updated_at is required");
  if (!isNonEmptyString(context?.product?.name)) errors.push("product.name is required");
  if (!isNonEmptyString(context?.company?.legal_name)) errors.push("company.legal_name is required");
  if (context?.product?.name === context?.company?.legal_name) {
    errors.push("product name and company legal name must remain distinct");
  }
  if (!isNonEmptyString(context?.product?.one_liner)) errors.push("product.one_liner is required");
  if (!Array.isArray(context?.product?.organs) || context.product.organs.length !== 3) {
    errors.push("product.organs must define exactly three top-level organs");
  }

  for (const key of REQUIRED_LINKS) {
    const link = context?.links?.[key];
    if (!link) {
      errors.push(`links.${key} is required`);
      continue;
    }
    if (!isNonEmptyString(link.url)) errors.push(`links.${key}.url is required`);
    if (link.status !== "verified") errors.push(`links.${key}.status must be verified`);
    if (!isNonEmptyString(link.verified_at)) errors.push(`links.${key}.verified_at is required`);
    if (!isNonEmptyString(link.evidence)) errors.push(`links.${key}.evidence is required`);
  }

  if (!Array.isArray(context?.claims)) {
    errors.push("claims must be an array");
  } else {
    for (const claim of context.claims) {
      const label = isNonEmptyString(claim?.id) ? claim.id : "unnamed claim";
      if (!isNonEmptyString(claim?.statement)) errors.push(`${label}: statement is required`);
      if (!isNonEmptyString(claim?.verified_at)) errors.push(`${label}: verified_at is required`);
      if (!Array.isArray(claim?.evidence) || claim.evidence.length === 0) {
        errors.push(`${label}: evidence is required`);
      }
    }
  }

  if (!Array.isArray(context?.public_field_allowlist)) {
    errors.push("public_field_allowlist must be an array");
  }
  if (!context?.forbidden_exact_values || typeof context.forbidden_exact_values !== "object") {
    errors.push("forbidden_exact_values is required");
  }

  return errors;
}

export function contextDigest(context) {
  const canonical = JSON.stringify(stableValue(context));
  return createHash("sha256").update(canonical).digest("hex");
}
