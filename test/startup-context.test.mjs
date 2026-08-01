import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import {
  contextDigest,
  loadStartupContext,
  validateStartupContext,
} from "../scripts/startup-context/lib.mjs";

const contextPath = new URL("../.agents/startup-context.json", import.meta.url);
const marketingPath = new URL(
  "../.agents/product-marketing-context.md",
  import.meta.url,
);

function clone(value) {
  return structuredClone(value);
}

test("canonical startup context is valid and names Life Manager as the product", async () => {
  const context = await loadStartupContext(contextPath);

  assert.equal(context.product.name, "Life Manager");
  assert.equal(context.company.legal_name, "Anicca");
  assert.notEqual(context.product.name, context.company.legal_name);
  assert.deepEqual(validateStartupContext(context), []);
});

test("marketing context defines the audience, pain, three organs, and truthful proof", async () => {
  const markdown = await readFile(marketingPath, "utf8");

  for (const heading of [
    "## Product Overview",
    "## Target Audience",
    "## Core Pain / Job to Be Done",
    "## Physical / Mental / Financial Organs",
    "## Differentiation",
    "## Alternatives / Competition",
    "## Objections",
    "## Customer Language",
    "## Brand Voice",
    "## Current Proof and Unknowns",
    "## Fundraising Goals",
  ]) {
    assert.match(markdown, new RegExp(`^${heading}$`, "m"));
  }
});

test("validator rejects missing required fields", async () => {
  const context = clone(await loadStartupContext(contextPath));
  delete context.links.repository;

  assert.match(validateStartupContext(context).join("\n"), /links\.repository/);
});

test("validator rejects product and company name confusion", async () => {
  const context = clone(await loadStartupContext(contextPath));
  context.product.name = context.company.legal_name;

  assert.match(validateStartupContext(context).join("\n"), /product.*company/i);
});

test("validator rejects claims without evidence", async () => {
  const context = clone(await loadStartupContext(contextPath));
  context.claims.push({
    id: "unsupported-growth",
    statement: "Life Manager guarantees investment returns.",
    verified_at: "2026-08-02T00:00:00+09:00",
    evidence: [],
  });

  const errors = validateStartupContext(context).join("\n");
  assert.match(errors, /unsupported-growth/);
  assert.match(errors, /evidence/i);
});

test("context digest is stable and changes with the facts", async () => {
  const context = await loadStartupContext(contextPath);
  const sameFacts = clone(context);
  const changedFacts = clone(context);
  changedFacts.product.name = "Different Product";

  assert.equal(contextDigest(context), contextDigest(sameFacts));
  assert.notEqual(contextDigest(context), contextDigest(changedFacts));
  assert.match(contextDigest(context), /^[a-f0-9]{64}$/);
});
