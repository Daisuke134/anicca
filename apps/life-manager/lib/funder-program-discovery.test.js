"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const { buildDailyFunderDiscovery } = require("./funder-program-discovery.js");
const { appendDailyFunderDiscovery } = require("./funder-program-discovery-store.js");
const { fetchSource, linkedUrls } = require("../scripts/fetch-funder-program-sources.js");
const { render } = require("../scripts/render-funder-program-discovery-sql.js");

const SQL = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-funder-program-discovery.sql"), "utf8");
const SOURCES = JSON.parse(fs.readFileSync(path.join(__dirname, "../config/funder-program-sources.json"), "utf8"));
const sha = (value) => createHash("sha256").update(value).digest("hex");

function fixture() {
  const content = "Applications for Frontier Fellowship are open. Solo founders may apply.";
  return {
    tenantId: "dais-local",
    observedAt: "2026-08-02T00:30:00.000Z",
    existingEntries: [{ funder_id: "yc-f26", official_url: "https://www.ycombinator.com/apply", priority: 1, revision_digest: "a".repeat(64) }],
    sources: [{
      source_id: "official-index",
      source_url: "https://accelerator.example/programs",
      retrieved_via: "jina_reader",
      fetched_at: "2026-08-02T00:20:00.000Z",
      content,
      content_sha256: sha(content),
      links: ["https://accelerator.example/frontier"],
    }],
    assessment: {
      assessed_source_ids: ["official-index"],
      candidates: [{
        source_id: "official-index",
        funder_id: "frontier-fellowship",
        name: "Frontier Fellowship",
        official_url: "https://accelerator.example/frontier",
        funder_type: "accelerator",
        evidence_excerpt: "Applications for Frontier Fellowship are open.",
        rationale: "Life Managerに関連するAI founder program。",
        status: "open",
        next_deadline: null,
        terms_hash: null,
        solo_allowed: "yes",
        location: "unknown",
      }],
    },
  };
}

test("a fresh complete assessment appends a new linked official program", () => {
  const result = buildDailyFunderDiscovery(fixture());
  assert.equal(result.entries.length, 1);
  assert.equal(result.entries[0].discovery_kind, "new_program");
  assert.equal(result.entries[0].priority, 2);
  assert.match(result.entries[0].registry_id, /^funder-registry:[0-9a-f]{64}$/);
  assert.match(result.run.discovery_run_id, /^funder-discovery:[0-9a-f]{64}$/);
  assert.equal(result.run.source_count, 1);
  assert.equal(result.run.candidate_count, 1);
});

test("existing identity becomes changed only when its current facts digest changes", () => {
  const input = fixture();
  input.existingEntries = [{ funder_id: "frontier-fellowship", official_url: "https://accelerator.example/frontier", priority: 7, discovery_facts_digest: "b".repeat(64) }];
  const result = buildDailyFunderDiscovery(input);
  assert.equal(result.entries[0].discovery_kind, "existing_change");
  assert.equal(result.entries[0].priority, 7);
  input.existingEntries[0].discovery_facts_digest = result.entries[0].discovery_facts_digest;
  assert.equal(buildDailyFunderDiscovery(input).entries.length, 0);
});

test("a fully assessed fresh source may produce a valid zero-candidate day", () => {
  const input = fixture();
  input.assessment.candidates = [];
  const result = buildDailyFunderDiscovery(input);
  assert.equal(result.entries.length, 0);
  assert.equal(result.run.candidate_count, 0);
  assert.equal(result.run.status, "complete");
});

test("stale, incomplete, fabricated, unsafe, unlinked, duplicate, and hash-drift input fail closed", () => {
  const stale = fixture(); stale.sources[0].fetched_at = "2026-07-30T00:00:00.000Z";
  assert.throws(() => buildDailyFunderDiscovery(stale), /source/i);
  const incomplete = fixture(); incomplete.assessment.assessed_source_ids = [];
  assert.throws(() => buildDailyFunderDiscovery(incomplete), /assessment/i);
  const fabricated = fixture(); fabricated.assessment.candidates[0].evidence_excerpt = "not on the page";
  assert.throws(() => buildDailyFunderDiscovery(fabricated), /evidence/i);
  const unsafe = fixture(); unsafe.assessment.candidates[0].official_url = "http://evil.test/form";
  assert.throws(() => buildDailyFunderDiscovery(unsafe), /URL/i);
  const unlinked = fixture(); unlinked.assessment.candidates[0].official_url = "https://other.example/form";
  assert.throws(() => buildDailyFunderDiscovery(unlinked), /linked/i);
  const duplicate = fixture(); duplicate.assessment.candidates.push({ ...duplicate.assessment.candidates[0] });
  assert.throws(() => buildDailyFunderDiscovery(duplicate), /duplicate/i);
  const drift = fixture(); drift.sources[0].content_sha256 = "0".repeat(64);
  assert.throws(() => buildDailyFunderDiscovery(drift), /hash/i);
});

test("migration and store are tenant-bound append-only exact replay", async () => {
  assert.match(SQL, /ALTER TABLE public\.lm_funder_registry_snapshots/i);
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_funder_discovery_runs/i);
  assert.match(SQL, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(SQL, /REVOKE ALL .* FROM PUBLIC/i);
  assert.match(SQL, /UNIQUE \(tenant_id, tokyo_day\)/i);
  assert.doesNotMatch(SQL, /UPDATE public\./i);
  const discovery = buildDailyFunderDiscovery(fixture());
  const calls = [];
  const saved = await appendDailyFunderDiscovery(discovery, { query: async (sql, params) => {
    calls.push({ sql, params });
    return { rows: [{ id: params[1] }] };
  } });
  assert.equal(saved.entries.length, 1);
  assert.equal(saved.run.inserted, true);
  assert.equal(calls.every(({ sql }) => /ON CONFLICT .* DO NOTHING/i.test(sql)), true);
  await assert.rejects(() => appendDailyFunderDiscovery(discovery, { query: async () => ({ rows: [] }) }), /collision/i);
});

test("daily source manifest runs at 06:30 JST and permits discovery beyond seeds", () => {
  assert.equal(SOURCES.schedule.cron, "30 6 * * *");
  assert.equal(SOURCES.schedule.timezone, "Asia/Tokyo");
  assert.equal(SOURCES.allow_agent_discovered_official_sources, true);
  assert.equal(SOURCES.sources.length, 6);
  assert.equal(SOURCES.sources.every(({ url }) => new URL(url).protocol === "https:"), true);
  assert.equal(new Set(SOURCES.sources.map(({ source_id }) => source_id)).size, 6);
});

test("source fetcher preserves official identity and extracts only HTTPS markdown links", async () => {
  const markdown = "Apply [here](https://official.example/apply#now), ignore [bad](http://evil.test).";
  assert.deepEqual(linkedUrls(markdown), ["https://official.example/apply"]);
  const source = await fetchSource({ source_id: "official", url: "https://official.example/program" }, async (url) => {
    assert.equal(url, "https://r.jina.ai/https://official.example/program");
    return { ok: true, text: async () => markdown };
  });
  assert.equal(source.source_url, "https://official.example/program");
  assert.equal(source.retrieved_via, "jina_reader");
  assert.equal(source.links[0], "https://official.example/apply");
  assert.match(source.content_sha256, /^[0-9a-f]{64}$/);
});

test("Railway fallback renders the validated append-only discovery without secrets or updates", () => {
  const discovery = buildDailyFunderDiscovery(fixture());
  const sql = render(discovery);
  assert.match(sql, /INSERT INTO public\.lm_funder_registry_snapshots/i);
  assert.match(sql, /INSERT INTO public\.lm_funder_discovery_runs/i);
  assert.match(sql, /ON CONFLICT .* DO NOTHING/i);
  assert.doesNotMatch(sql, /UPDATE public\./i);
  assert.match(sql, new RegExp(discovery.run.discovery_run_id));
  const wrapper = fs.readFileSync(path.join(__dirname, "../scripts/record-funder-program-discovery-railway.sh"), "utf8");
  assert.match(wrapper, /mktemp -d/);
  assert.match(wrapper, /railway connect/);
  assert.doesNotMatch(wrapper, /password|DATABASE_URL/i);
});
