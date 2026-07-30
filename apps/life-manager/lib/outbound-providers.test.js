// lib/outbound-providers.test.js — provider stubs are honest about being stubs.
//
// Task #1 builds the engine and its gates only. The providers exist so the pipeline has something
// to inject, and every one of them throws NOT_IMPLEMENTED. A stub that returned a plausible fake
// would be indistinguishable from a working provider in the trace, which is the exact class of
// lie this engine is built to make impossible.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const PROVIDER_DIR = path.join(__dirname, "providers");

const EXPECTED = Object.freeze({
  luma: ["discoverEvents", "rsvp", "canonicalEventUrl", "headStatus"],
  gmail: ["findConfirmationEmail", "readMessage"],
  cloakbrowser: ["openPage", "screenshotPng", "submitForm", "close"],
});

for (const [name, functions] of Object.entries(EXPECTED)) {
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
