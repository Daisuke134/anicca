"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { loadYcSubmittedUpdateProviderManifest } = require("./yc-submitted-update-provider.js");

test("manifest contains only the four freshly observed submitted-application update routes", () => {
  const manifest = loadYcSubmittedUpdateProviderManifest();
  assert.equal(manifest.schema_version, 2);
  assert.equal(manifest.mode, "typed_update");
  assert.equal(manifest.application_submit_operations, 0);
  assert.deepEqual(manifest.operations.map(({ operation_type }) => operation_type), [
    "demo_update", "progress_update", "team_update", "founder_profile_update",
  ]);
  assert.deepEqual(manifest.operations[1].fields.map(({ name }) => name), [
    "productLink", "productCreds", "howfar", "worked", "techstack", "people_using", "have_revenue",
  ]);
  assert.deepEqual(manifest.operations[2].fields.map(({ name }) => name), ["others2", "cofounder"]);
  assert.deepEqual(manifest.operations[3].fields.map(({ name }) => name), ["fhack", "fability", "projects", "awards", "testScores", "clubs"]);
  assert.equal(manifest.operations[0].activation.text, "Save & back");
  assert.equal(manifest.operations[1].activation.text, "Submit update");
  assert.equal(manifest.operations[2].activation.text, "Submit update");
  assert.equal(manifest.operations[3].activation.text, "Save founder profile");
  assert.doesNotMatch(JSON.stringify(manifest), /Save changes|Submit application|\/apps\/\{application_id\}\/edit"/);
});

test("route, control, locator, choice identity, and nested schema drift fail closed", () => {
  const mutations = [
    (x) => { x.operations[0].route_template = "/apps/{application_id}/edit"; },
    (x) => { x.operations[0].activation.text = "Submit application"; },
    (x) => { x.operations[1].fields[0].locator.selector = "input"; },
    (x) => { x.operations[1].fields[5].locator.question_text = "Any question"; },
    (x) => { x.operations[2].activation.count = 2; },
    (x) => { x.operations[3].fields.push({ name: "femail" }); },
    (x) => { x.operations[0].extra = true; },
    (x) => { x.application_submit_operations = 1; },
  ];
  const valid = loadYcSubmittedUpdateProviderManifest();
  for (const mutate of mutations) {
    const manifest = structuredClone(valid); mutate(manifest);
    assert.throws(() => loadYcSubmittedUpdateProviderManifest({ readFile: () => JSON.stringify(manifest) }), /YC submitted update provider/i);
  }
});
