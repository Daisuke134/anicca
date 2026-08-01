"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");
const test = require("node:test");

const { ANSWER_IDS, createApplicationKitProvider, resolveFunderKitFields } = require("./funder-application-kit.js");

function fakeKit() {
  const root = "/fixture/application-kit";
  const files = new Map([
    [path.join(root, "KIT.md"), "# Canonical company facts\nMUIT, not MUFG\n"],
    [path.join(root, "MANIFEST.md"), "deck/deck-en.pdf\ndeck/deck-ja.pdf\nonepager/onepager-en.png\nonepager/onepager-ja.png\nassets/anicca-icon.png\nassets/dais-profile.jpg\n"],
  ]);
  for (const id of ANSWER_IDS) {
    files.set(path.join(root, `answers/${id}.en.md`), id === "q04_traction" ? "MRR {{dashboard:mrr.total_usd}}" : `EN ${id}`);
    files.set(path.join(root, `answers/${id}.ja.md`), `JA ${id}`);
  }
  for (const relative of ["deck/deck-en.pdf", "deck/deck-ja.pdf", "onepager/onepager-en.png", "onepager/onepager-ja.png", "assets/anicca-icon.png", "assets/dais-profile.jpg"]) {
    files.set(path.join(root, relative), Buffer.from(`asset:${relative}`));
  }
  return {
    root,
    readFile(file) {
      if (!files.has(file)) throw Object.assign(new Error("missing"), { code: "ENOENT" });
      return files.get(file);
    },
  };
}

test("snapshot binds KIT, MANIFEST, all 20 answers, and allowlisted assets", () => {
  const fixture = fakeKit();
  const provider = createApplicationKitProvider(fixture);
  const snapshot = provider.snapshot();
  assert.equal(snapshot.answer_count, 20);
  assert.equal(snapshot.asset_count, 6);
  assert.match(snapshot.kit_digest, /^[0-9a-f]{64}$/);
  assert.equal(snapshot.company_facts_ref, "application-kit://KIT.md");
});

test("funder fields resolve only from the kit and inject the same live dashboard snapshot", () => {
  const fixture = fakeKit();
  const provider = createApplicationKitProvider(fixture);
  const result = resolveFunderKitFields({
    provider,
    dashboard: { mrr: { total_usd: 42.5 } },
    fields: [
      { name: "traction", value_source: "kit:answer/q04_traction.en" },
      { name: "team", value_source: "kit:answer/q05_team.ja" },
      { name: "deck", value_source: "kit:asset/deck-en" },
    ],
  });
  assert.equal(result.values.traction, "MRR 42.5");
  assert.equal(result.values.team, "JA q05_team");
  assert.equal(result.values.deck, path.join(fixture.root, "deck/deck-en.pdf"));
  assert.deepEqual(result.sources, {
    traction: "application-kit://answers/q04_traction.en.md",
    team: "application-kit://answers/q05_team.ja.md",
    deck: "application-kit://deck/deck-en.pdf",
  });
  assert.match(result.kit_digest, /^[0-9a-f]{64}$/);
});

test("missing dashboard fact, missing kit file, unknown source, and path tricks fail closed", () => {
  const fixture = fakeKit();
  const provider = createApplicationKitProvider(fixture);
  assert.throws(() => resolveFunderKitFields({
    provider, dashboard: {}, fields: [{ name: "traction", value_source: "kit:answer/q04_traction.en" }],
  }), /dashboard/i);
  assert.throws(() => resolveFunderKitFields({
    provider, dashboard: {}, fields: [{ name: "copy", value_source: "literal:hardcoded duplicate" }],
  }), /source/i);
  assert.throws(() => resolveFunderKitFields({
    provider, dashboard: {}, fields: [{ name: "copy", value_source: "kit:answer/../../KIT.en" }],
  }), /source/i);
  const missing = fakeKit();
  const original = missing.readFile;
  missing.readFile = (file) => file.endsWith("q10_risks.ja.md") ? (() => { throw new Error("missing"); })() : original(file);
  assert.throws(() => createApplicationKitProvider(missing).snapshot(), /incomplete/i);
});
