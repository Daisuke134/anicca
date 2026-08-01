import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

const REQUIRED_LINKS = ["product", "repository", "telegram"];
const OPTIONAL_LINKS = ["dashboard", "demo", "founder_video"];

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
    if (!isNonEmptyString(link.expected_text)) errors.push(`links.${key}.expected_text is required`);
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

function ageInDays(value, now) {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return Number.POSITIVE_INFINITY;
  return (now.getTime() - timestamp) / 86_400_000;
}

export async function auditStartupContext(
  context,
  {
    now = new Date(),
    maxAgeDays = 30,
    checkLinks = true,
    fetchImpl = globalThis.fetch,
  } = {},
) {
  const errors = validateStartupContext(context);
  const warnings = [];
  const linkChecks = [];

  if (ageInDays(context?.updated_at, now) > maxAgeDays) {
    errors.push(`startup context is stale: updated_at exceeds ${maxAgeDays} days`);
  }

  for (const key of REQUIRED_LINKS) {
    const link = context?.links?.[key];
    if (link && ageInDays(link.verified_at, now) > maxAgeDays) {
      errors.push(`links.${key} is stale: verified_at exceeds ${maxAgeDays} days`);
    }
  }

  for (const key of OPTIONAL_LINKS) {
    const link = context?.links?.[key];
    if (!link || link.status !== "verified") {
      warnings.push(`links.${key} is ${link?.status ?? "missing"} and cannot be attached`);
    }
  }

  const forbiddenProductNames = context?.forbidden_exact_values?.product_names ?? [];
  if (forbiddenProductNames.includes(context?.product?.name)) {
    errors.push(`forbidden product name: ${context.product.name}`);
  }

  const forbiddenRepositories = context?.forbidden_exact_values?.repositories ?? [];
  if (forbiddenRepositories.includes(context?.links?.repository?.url)) {
    errors.push("forbidden repository URL is configured as canonical");
  }

  const forbiddenHomepages = context?.forbidden_exact_values?.homepages ?? [];
  if (forbiddenHomepages.includes(context?.links?.product?.url)) {
    errors.push("forbidden homepage URL is configured as canonical");
  }

  if (checkLinks) {
    if (typeof fetchImpl !== "function") {
      errors.push("link audit requires a fetch implementation");
    } else {
      for (const key of REQUIRED_LINKS) {
        const url = context?.links?.[key]?.url;
        if (!isNonEmptyString(url)) continue;
        try {
          const response = await fetchImpl(url, {
            method: "GET",
            redirect: "follow",
            headers: { "user-agent": "life-manager-startup-context-audit/1.0" },
          });
          const body = await response.text();
          const expectedText = context.links[key].expected_text;
          const identityMatches = body.toLocaleLowerCase().includes(expectedText.toLocaleLowerCase());
          const check = {
            key,
            url,
            ok: response.ok && identityMatches,
            status: response.status,
            final_url: response.url || url,
            identity_matches: identityMatches,
          };
          linkChecks.push(check);
          if (!response.ok) errors.push(`links.${key} readback returned HTTP ${response.status}`);
          if (response.ok && !identityMatches) {
            errors.push(`links.${key} did not contain expected text: ${expectedText}`);
          }
        } catch (error) {
          linkChecks.push({ key, url, ok: false, error: error.message });
          errors.push(`links.${key} readback failed: ${error.message}`);
        }
      }
    }
  }

  return {
    ok: errors.length === 0,
    context_version: context?.context_version ?? null,
    context_digest: contextDigest(context),
    audited_at: now.toISOString(),
    errors,
    warnings,
    link_checks: linkChecks,
  };
}
