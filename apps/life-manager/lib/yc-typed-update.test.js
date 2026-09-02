"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const {
  buildYcTypedUpdatePlan,
  createPreparedFence,
  markEffectAttempted,
  recordOperationReadback,
} = require("./yc-typed-update.js");

const ID = "0b61fe42-e383-490d-b60e-04f1ad7ec5df";
const SHA = "a".repeat(64);
const NOW = "2026-08-02T09:00:00.000Z";

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
function digest(value) { return createHash("sha256").update(stable(value), "utf8").digest("hex"); }

function validInput() {
  const input = {
    verified_at: "2026-08-02T08:59:50.000Z",
    application: {
      id: ID,
      batch: "Fall 2026",
      state: "In review",
      prior_application_submit_count: 1,
    },
    provider_manifest_digest: "b".repeat(64),
    preview: {
      preview_complete: true,
      submit_ready: true,
      blocking_issue_codes: [],
      preview_receipt_digest: "c".repeat(64),
    },
    operations: [
      {
        operation_type: "demo_update",
        disposition: "execute",
        route: `/apps/${ID}/edit/demo`,
        payload: { demo_video: { source_ref: "application-kit://videos/life-manager-yc-demo.mp4", artifact_digest: "d".repeat(64) } },
        observed_at: "2026-08-02T08:59:40.000Z",
        expected_readback_digest: "e".repeat(64),
      },
      {
        operation_type: "progress_update",
        disposition: "execute",
        route: `/apps/${ID}/edit/progress`,
        payload: {
          productLink: "https://github.com/Daisuke134/life-manager",
          productCreds: "No login is required for the public repository and dashboard.",
          howfar: "Current source-backed progress copy.",
          worked: "Current source-backed founder work copy.",
          techstack: "Current source-backed technology copy.",
          people_using: false,
          have_revenue: false,
        },
        observed_at: "2026-08-02T08:59:41.000Z",
        expected_readback_digest: "f".repeat(64),
      },
      {
        operation_type: "team_update",
        disposition: "execute",
        route: `/apps/${ID}/edit/cofounder`,
        payload: { others2: "Current technical-work copy.", cofounder: "Current cofounder copy." },
        observed_at: "2026-08-02T08:59:42.000Z",
        expected_readback_digest: "1".repeat(64),
      },
      {
        operation_type: "founder_profile_update",
        disposition: "execute",
        route: "/bio/721f696b-0566-4a16-bda7-a9c368b1eac1/edit",
        payload: {
          fhack: "Current source-backed answer.",
          fability: "Current source-backed answer.",
          projects: "Current source-backed answer.",
          awards: "None.",
          testScores: "Current source-backed answer.",
          clubs: "None.",
        },
        observed_at: "2026-08-02T08:59:43.000Z",
        expected_readback_digest: "2".repeat(64),
      },
    ],
    effects: {
      form_field_writes: 0,
      option_selections: 0,
      file_attachments: 0,
      update_control_activations: 0,
      application_submissions: 0,
      browser_closes: 0,
    },
  };
  for (const operation of input.operations) operation.expected_readback_digest = digest(operation.payload);
  return input;
}

test("builds four content-addressed typed operations while application submissions stay zero", () => {
  const plan = buildYcTypedUpdatePlan(validInput(), { now: NOW });
  assert.deepEqual(plan.operations.map(({ operation_type }) => operation_type), [
    "demo_update", "progress_update", "team_update", "founder_profile_update",
  ]);
  assert.ok(plan.operations.every(({ operation_id }) => /^[0-9a-f]{64}$/.test(operation_id)));
  assert.equal(new Set(plan.operations.map(({ operation_id }) => operation_id)).size, 4);
  assert.equal(plan.planned_application_submissions, 0);
  assert.equal(plan.effects.application_submissions, 0);
  assert.match(plan.plan_digest, /^[0-9a-f]{64}$/);
  assert.ok(Object.isFrozen(plan));
  assert.ok(Object.isFrozen(plan.operations[0].payload));
});

test("supports source-proven omission for confirmed demo and conditional text operations", () => {
  const input = validInput();
  for (const type of ["team_update", "founder_profile_update"]) {
    const operation = input.operations.find((candidate) => candidate.operation_type === type);
    operation.disposition = "omit_equal";
    operation.payload = {};
    operation.expected_readback_digest = digest(operation.payload);
  }
  input.operations[0].disposition = "omit_equal";
  const plan = buildYcTypedUpdatePlan(input, { now: NOW });
  assert.deepEqual(plan.operations.filter(({ disposition }) => disposition === "omit_equal").map(({ operation_type }) => operation_type), ["demo_update", "team_update", "founder_profile_update"]);
  const bad = validInput();
  bad.operations[1].disposition = "omit_equal";
  bad.operations[1].payload = {};
  bad.operations[1].expected_readback_digest = digest(bad.operations[1].payload);
  assert.throws(() => buildYcTypedUpdatePlan(bad, { now: NOW }), /YC typed update/i);
});

test("fails closed on blocker, stale preview, duplicate type, route drift, payload extras, or any prior mutation", () => {
  const cases = [
    (x) => { x.preview.submit_ready = false; x.preview.blocking_issue_codes = ["demo_missing"]; },
    (x) => { x.verified_at = "2026-08-02T08:50:00.000Z"; },
    (x) => { x.operations[1].operation_type = "demo_update"; },
    (x) => { x.operations[0].route = `/apps/${ID}/edit`; },
    (x) => { x.operations[1].payload.secret = "no"; },
    (x) => { x.effects.form_field_writes = 1; },
    (x) => { x.effects.application_submissions = 1; },
    (x) => { x.application.prior_application_submit_count = 2; },
    (x) => { x.operations[0].expected_readback_digest = "9".repeat(64); },
  ];
  for (const mutate of cases) {
    const input = validInput(); mutate(input);
    assert.throws(() => buildYcTypedUpdatePlan(input, { now: NOW }), /YC typed update/i);
  }
});

test("the fence allows one activation and never retries an ambiguous effect", () => {
  const plan = buildYcTypedUpdatePlan(validInput(), { now: NOW });
  const operation = plan.operations[0];
  const prepared = createPreparedFence(plan, operation.operation_id, { at: "2026-08-02T09:00:01.000Z" });
  assert.equal(prepared.state, "prepared");
  assert.equal(prepared.activation_count, 0);
  const attempted = markEffectAttempted(prepared, { at: "2026-08-02T09:00:02.000Z" });
  assert.equal(attempted.state, "effect_attempted");
  assert.equal(attempted.activation_count, 1);
  assert.throws(() => markEffectAttempted(attempted, { at: "2026-08-02T09:00:03.000Z" }), /YC typed update/i);
  const unknown = recordOperationReadback(attempted, {
    at: "2026-08-02T09:00:04.000Z",
    result: "unknown_effect",
    readback_digest: SHA,
  });
  assert.equal(unknown.state, "unknown_effect");
  assert.throws(() => markEffectAttempted(unknown, { at: "2026-08-02T09:00:05.000Z" }), /YC typed update/i);
  assert.throws(() => recordOperationReadback(unknown, { at: "2026-08-02T09:00:06.000Z", result: "confirmed", readback_digest: SHA }), /YC typed update/i);
});

test("confirmed/not-applied readback is bound to the prepared expected digest", () => {
  const plan = buildYcTypedUpdatePlan(validInput(), { now: NOW });
  const operation = plan.operations[1];
  const attempted = markEffectAttempted(createPreparedFence(plan, operation.operation_id, { at: "2026-08-02T09:00:01.000Z" }), { at: "2026-08-02T09:00:02.000Z" });
  assert.throws(() => recordOperationReadback(attempted, { at: "2026-08-02T09:00:03.000Z", result: "confirmed", readback_digest: SHA }), /YC typed update/i);
  const confirmed = recordOperationReadback(attempted, { at: "2026-08-02T09:00:03.000Z", result: "confirmed", readback_digest: operation.expected_readback_digest });
  assert.equal(confirmed.state, "confirmed");
  assert.equal(confirmed.activation_count, 1);
});
