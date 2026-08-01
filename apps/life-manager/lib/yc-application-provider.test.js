"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  MAIN_FIELDS,
  buildYcApplicationProviderPlan,
  loadYcApplicationProviderManifest,
} = require("./yc-application-provider.js");

const SHA = "a".repeat(64);
const DRAFT = "0b61fe42-e383-490d-b60e-04f1ad7ec5df";

function resolvedValues() {
  const values = {};
  for (const name of MAIN_FIELDS) {
    values[`main.${name}`] = {
      value: `current ${name}`,
      source_ref: name === "describe"
        ? "application-kit://KIT.md#english-one-liner"
        : `application-kit://answers/q01_what.en.md#${name}`,
      source_digest: SHA,
    };
  }
  Object.assign(values, {
    "video.founder_video": {
      source_ref: "application-kit://videos/Anicca_intro_EN.mp4",
      artifact_digest: SHA,
    },
    "demo.demo_video": {
      source_ref: "application-kit://videos/life-manager-current-demo.mp4",
      artifact_digest: "b".repeat(64),
    },
    "progress.usernums": { value: "current users", source_ref: "dashboard-snapshot://current#users", source_digest: SHA },
    "progress.revenuesource": { value: "current recurring sources", source_ref: "dashboard-snapshot://current#revenue-sources", source_digest: SHA },
    "progress.growthrate": { value: "current growth", source_ref: "dashboard-snapshot://current#growth", source_digest: SHA },
    "progress.monthly_revenue": { value: [0, 0, 10, 20, 30, 40], source_ref: "dashboard-snapshot://current#monthly-revenue", source_digest: SHA },
    "progress.people_using_yes": { value: true, source_ref: "dashboard-snapshot://current#users", source_digest: SHA },
    "progress.have_revenue_yes": { value: true, source_ref: "dashboard-snapshot://current#mrr", source_digest: SHA },
  });
  return values;
}

test("canonical successor manifest preserves the complete legacy field/video/progress inventory", () => {
  const manifest = loadYcApplicationProviderManifest();
  assert.equal(manifest.successor_provider, "apply-to-funder");
  assert.equal(manifest.ported_from, "apply-to-yc");
  assert.deepEqual(manifest.pages.map(({ name }) => name), ["main", "video", "demo", "progress"]);
  assert.deepEqual(manifest.pages[0].fields.map(({ name }) => name), MAIN_FIELDS);
  assert.deepEqual(manifest.pages[1].fields.map(({ name }) => name), ["founder_video"]);
  assert.deepEqual(manifest.pages[2].fields.map(({ name }) => name), ["demo_video"]);
  assert.deepEqual(manifest.pages[3].fields.map(({ name }) => name), [
    "usernums", "revenuesource", "growthrate", "monthly_revenue", "people_using_yes", "have_revenue_yes",
  ]);
  const choices = manifest.pages[3].fields.slice(-2);
  assert.deepEqual(choices.map(({ locator }) => locator.question_text), [
    "Are people using your product?", "Do you have revenue?",
  ]);
  assert.ok(choices.every(({ locator }) => locator.strategy === "question_scoped_option" && locator.cardinality === 1));
  assert.ok(JSON.stringify(manifest).includes("native_value_setter"));
  assert.doesNotMatch(JSON.stringify(manifest), /selector_filter|literal:click|9223|Submit application/i);
});

test("builder emits four closed, page-atomic preview operations with exact readback and zero submits", () => {
  const plan = buildYcApplicationProviderPlan({ draftId: DRAFT, resolved: resolvedValues() });
  assert.equal(plan.mode, "preview_only");
  assert.equal(plan.submit_operations, 0);
  assert.equal(plan.logical_field_count, 28);
  assert.deepEqual(plan.operations.map(({ page }) => page), ["main", "video", "demo", "progress"]);
  assert.equal(plan.operations[0].atomic, true);
  assert.equal(plan.operations[0].navigate_count, 1);
  assert.equal(plan.operations[0].save.count, 1);
  assert.deepEqual(plan.operations[0].mutations.map(({ field }) => field), MAIN_FIELDS);
  assert.deepEqual(plan.operations[0].readback.fields, MAIN_FIELDS);
  assert.equal(plan.operations[3].atomic, true);
  assert.equal(plan.operations[3].mutations.find(({ field }) => field === "monthly_revenue").value.length, 6);
  assert.deepEqual(plan.operations[3].mutations.slice(-2).map(({ locator }) => locator.question_text), [
    "Are people using your product?", "Do you have revenue?",
  ]);
  assert.ok(plan.operations.every(({ readback }) => readback.required === true));
  assert.match(plan.manifest_digest, /^[0-9a-f]{64}$/);
  assert.match(plan.plan_digest, /^[0-9a-f]{64}$/);
  assert.ok(Object.isFrozen(plan));
  assert.ok(Object.isFrozen(plan.operations[0].mutations));
});

test("partial, stale, ambiguous, malformed, extra, and submission-bearing inputs fail closed", () => {
  const cases = [];
  const partial = resolvedValues(); delete partial["main.money"]; cases.push(partial);
  const stale = resolvedValues(); stale["main.make"].source_ref = "live:pitch.make"; cases.push(stale);
  const literal = resolvedValues(); literal["progress.people_using_yes"].source_ref = "literal:click"; cases.push(literal);
  const oldFile = resolvedValues(); oldFile["demo.demo_video"].source_ref = "~/Desktop/ycsummer2026.MOV"; cases.push(oldFile);
  const pathTrick = resolvedValues(); pathTrick["demo.demo_video"].source_ref = "application-kit://videos/../../secret.mp4"; cases.push(pathTrick);
  const badDigest = resolvedValues(); badDigest["video.founder_video"].artifact_digest = "not-a-digest"; cases.push(badDigest);
  const wrongMonths = resolvedValues(); wrongMonths["progress.monthly_revenue"].value = [1, 2, 3]; cases.push(wrongMonths);
  const extra = resolvedValues(); extra["submit.application"] = { value: true, source_ref: "provider-surface://submit" }; cases.push(extra);
  const staleKit = resolvedValues(); staleKit["main.make"].source_ref = "application-kit://answers/yc-w26.json#make"; cases.push(staleKit);
  for (const resolved of cases) {
    assert.throws(() => buildYcApplicationProviderPlan({ draftId: DRAFT, resolved }), /YC application provider/i);
  }
  assert.throws(() => buildYcApplicationProviderPlan({ draftId: "summer-legacy", resolved: resolvedValues() }), /YC application provider/i);
});

test("tampered save, readback, question identity, kind, locator, and nested extras fail closed", () => {
  const mutations = [
    (manifest) => { manifest.pages[0].save.text = "Submit"; },
    (manifest) => { manifest.pages[0].readback.strategy = "none"; },
    (manifest) => { manifest.pages[3].fields[4].locator.question_text = "Any question"; },
    (manifest) => { manifest.pages[0].fields[0].kind = "file"; delete manifest.pages[0].fields[0].setter; },
    (manifest) => { manifest.pages[0].fields[0].locator.selector = "input"; },
    (manifest) => { manifest.pages[0].fields[0].unexpected = true; },
  ];
  for (const mutate of mutations) {
    const manifest = structuredClone(loadYcApplicationProviderManifest());
    mutate(manifest);
    assert.throws(() => buildYcApplicationProviderPlan({ draftId: DRAFT, resolved: resolvedValues() }, { manifest }), /YC application provider/i);
  }
});
