import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

import {
  auditStartupContext,
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

test("audit detects stale facts and reports unverified optional media", async () => {
  const context = clone(await loadStartupContext(contextPath));
  const result = await auditStartupContext(context, {
    now: new Date("2026-10-02T00:00:00+09:00"),
    maxAgeDays: 30,
    checkLinks: false,
  });

  assert.equal(result.ok, false);
  assert.match(result.errors.join("\n"), /stale/i);
  assert.match(result.warnings.join("\n"), /links\.demo.*unverified/i);
  assert.match(result.warnings.join("\n"), /links\.founder_video.*unverified/i);
  assert.match(result.warnings.join("\n"), /links\.dashboard.*legacy/i);
});

test("audit rejects forbidden legacy exact values", async () => {
  const context = clone(await loadStartupContext(contextPath));
  context.links.repository.url = context.forbidden_exact_values.repositories[0];

  const result = await auditStartupContext(context, {
    now: new Date("2026-08-02T13:00:00+09:00"),
    checkLinks: false,
  });

  assert.equal(result.ok, false);
  assert.match(result.errors.join("\n"), /forbidden.*repository/i);
});

test("audit reads back every verified canonical link", async () => {
  const context = clone(await loadStartupContext(contextPath));
  const requested = [];
  const fetchImpl = async (url) => {
    requested.push(url);
    return new Response("Life Manager", { status: 200 });
  };

  const result = await auditStartupContext(context, {
    now: new Date("2026-08-02T13:00:00+09:00"),
    fetchImpl,
  });

  assert.equal(result.ok, true);
  assert.deepEqual(
    requested.sort(),
    ["product", "repository", "telegram"]
      .map((key) => context.links[key].url)
      .sort(),
  );
  assert.equal(result.link_checks.every((check) => check.ok), true);
});

test("audit rejects a 200 page that does not contain the expected product identity", async () => {
  const context = clone(await loadStartupContext(contextPath));
  const result = await auditStartupContext(context, {
    now: new Date("2026-08-02T13:00:00+09:00"),
    fetchImpl: async () => new Response("Unrelated legacy product", { status: 200 }),
  });

  assert.equal(result.ok, false);
  assert.match(result.errors.join("\n"), /expected text/i);
});

test("English README first view explains the Life Manager product experience", async () => {
  const readme = (await readFile(new URL("../README.md", import.meta.url), "utf8")).slice(0, 4_000);

  assert.match(readme, /body, mind, and money/i);
  assert.match(readme, /Telegram/);
  assert.match(readme, /acts? within/i);
  assert.match(readme, /same core/i);
  assert.match(readme, /https:\/\/aniccaai\.com\/lm/);
  assert.doesNotMatch(readme, /Live Dashboard/);
});

test("Japanese README first view explains the Life Manager product experience", async () => {
  const readme = (await readFile(new URL("../README.ja.md", import.meta.url), "utf8")).slice(0, 4_000);

  assert.match(readme, /身体/);
  assert.match(readme, /心/);
  assert.match(readme, /お金/);
  assert.match(readme, /Telegram/);
  assert.match(readme, /委任された範囲/);
  assert.match(readme, /同じcore/);
  assert.match(readme, /https:\/\/aniccaai\.com\/lm/);
  assert.doesNotMatch(readme, /Live Dashboard/);
});
