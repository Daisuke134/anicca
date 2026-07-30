// lib/outbound-providers.test.js — a provider is either implemented or it refuses. Never in between.
//
// Task #1 shipped the engine with three refusing stubs, because a stub that returned a plausible
// fake would be indistinguishable from a working provider in the trace ledger — the exact class of
// lie this engine is built to make impossible.
//
// Task #7 implemented `luma`. The rule it now has to satisfy is the mirror image of the stub rule:
// every function the pipeline injects must exist AND must not be a refusal in disguise. gmail and
// cloakbrowser are still stubs and are still required to refuse.
//
// Luma's own behaviour is tested in lib/outbound-luma.test.js against real captured fixtures.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const PROVIDER_DIR = path.join(__dirname, "providers");

const STUBS = Object.freeze({
  gmail: ["findConfirmationEmail", "readMessage"],
  cloakbrowser: ["openPage", "screenshotPng", "submitForm", "close"],
});

// The surface outbound-pass.js injects into the events pack. Extra pure helpers are allowed and
// deliberately not enumerated here; these four are the contract.
const LUMA_PIPELINE_SURFACE = Object.freeze([
  "discoverEvents",
  "rsvp",
  "canonicalEventUrl",
  "headStatus",
]);

for (const [name, functions] of Object.entries(STUBS)) {
  test(`provider ${name} exports every function the pipeline expects`, () => {
    const provider = require(path.join(PROVIDER_DIR, `${name}.js`));
    assert.deepEqual(Object.keys(provider).sort(), [...functions].sort());
  });

  test(`provider ${name} throws NOT_IMPLEMENTED instead of faking a result`, async () => {
    const provider = require(path.join(PROVIDER_DIR, `${name}.js`));
    for (const fn of functions) {
      await assert.rejects(
        async () => provider[fn]({}),
        new RegExp(`^Error: NOT_IMPLEMENTED: ${name}\\.${fn}$`),
        `${name}.${fn} did not refuse`,
      );
    }
  });
}

test("provider luma exposes the whole surface the pipeline injects", () => {
  const provider = require(path.join(PROVIDER_DIR, "luma.js"));
  for (const fn of LUMA_PIPELINE_SURFACE) {
    assert.equal(typeof provider[fn], "function", `luma.${fn} is missing`);
  }
});

test("provider luma is implemented — no NOT_IMPLEMENTED refusal survives anywhere in it", () => {
  const source = fs.readFileSync(path.join(PROVIDER_DIR, "luma.js"), "utf8");
  assert.equal(
    source.includes("NOT_IMPLEMENTED"),
    false,
    "luma still refuses somewhere; a half-implemented provider lies in the trace",
  );
});

test("provider luma decides nothing about success on its own", () => {
  // The verdict belongs to runtime/loop/outbound/evidence.mjs. If the provider ever starts
  // returning ok/verified/registered, the gate has been bypassed.
  const provider = require(path.join(PROVIDER_DIR, "luma.js"));
  const bundle = provider.buildEvidence(
    { canonicalUrl: "https://luma.com/abcdefg", httpEvidence: { status: 201 } },
    { headStatus: 200 },
  );
  assert.deepEqual(Object.keys(bundle).sort(), ["e1", "e2", "e3"]);
  assert.equal(Object.prototype.hasOwnProperty.call(bundle, "ok"), false);
});

test("connpass has no provider at all — decision D1 excludes it from v1", () => {
  assert.equal(
    fs.existsSync(path.join(PROVIDER_DIR, "connpass.js")),
    false,
    "connpass is excluded from v1 (ToS forbids non-API automation; the only session is Dais's personal account)",
  );
  assert.deepEqual(
    fs.readdirSync(PROVIDER_DIR).sort(),
    ["cloakbrowser.js", "gmail.js", "luma.js"],
  );
});
