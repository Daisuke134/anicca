"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createEventProviderRegistry } = require("./event-provider-registry.js");
const {
  advanceEventProviderCursor,
  createEventProviderCursor,
  createEventProviderCursorStore,
} = require("./event-provider-cursor.js");

const NOW = "2026-08-06T12:00:00.000Z";

test("advances candidate then provider without storing event or identity data", () => {
  const registry = createEventProviderRegistry();
  const initial = createEventProviderCursor({
    registry,
    date: "2026-08-07",
    observedAt: NOW,
  });
  const candidate = advanceEventProviderCursor({
    registry, cursor: initial, transition: "known_no_effect", observedAt: "2026-08-06T12:01:00.000Z",
  });
  const provider = advanceEventProviderCursor({
    registry, cursor: candidate, transition: "provider_exhausted", observedAt: "2026-08-06T12:02:00.000Z",
  });

  assert.equal(candidate.provider, "luma");
  assert.equal(candidate.candidate_index, 1);
  assert.equal(provider.provider, "connpass");
  assert.equal(provider.candidate_index, 0);
  assert.equal(provider.generation, 3);
  assert.deepEqual(Object.keys(provider), [
    "schema_version", "registry_id", "date", "provider", "candidate_index", "generation", "observed_at",
  ]);
  assert.doesNotMatch(JSON.stringify(provider), /event_ref|title|url|email|phone|profile/i);
});

test("unknown effect cannot advance and provider order cannot wrap silently", () => {
  const registry = createEventProviderRegistry();
  const cursor = createEventProviderCursor({ registry, date: "2026-08-07", observedAt: NOW });
  assert.throws(() => advanceEventProviderCursor({
    registry, cursor, transition: "unknown_effect", observedAt: "2026-08-06T12:01:00.000Z",
  }), /event provider cursor invalid/i);

  let last = cursor;
  for (let index = 1; index < registry.provider_order.length; index += 1) {
    last = advanceEventProviderCursor({
      registry, cursor: last, transition: "provider_exhausted", observedAt: `2026-08-06T12:0${index}:00.000Z`,
    });
  }
  assert.equal(last.provider, "eventbrite");
  assert.throws(() => advanceEventProviderCursor({
    registry, cursor: last, transition: "provider_exhausted", observedAt: "2026-08-06T12:07:00.000Z",
  }), /event provider cursor invalid/i);
});

test("persists and reloads only an exact mode-0600 atomic cursor", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "event-provider-cursor-"));
  try {
    const cursorPath = path.join(directory, "provider-cursor.json");
    const registry = createEventProviderRegistry();
    const store = createEventProviderCursorStore({ path: cursorPath, registry });
    const cursor = createEventProviderCursor({ registry, date: "2026-08-07", observedAt: NOW });
    store.write(cursor);

    assert.deepEqual(store.read(), cursor);
    assert.equal(fs.statSync(cursorPath).mode & 0o777, 0o600);
    assert.deepEqual(fs.readdirSync(directory), ["provider-cursor.json"]);
    fs.writeFileSync(cursorPath, JSON.stringify({ ...cursor, provider: "forged" }));
    assert.throws(() => store.read(), /event provider cursor invalid/i);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
