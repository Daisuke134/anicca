"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { buildYcTypedUpdatePlan } = require("./yc-typed-update.js");
const { readFence } = require("./yc-typed-update-store.js");
const { executeYcTypedUpdateOperation } = require("./yc-typed-update-executor.js");

const ID = "0b61fe42-e383-490d-b60e-04f1ad7ec5df";
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
function digest(value) { return createHash("sha256").update(stable(value)).digest("hex"); }
function operation(operation_type, route, payload, second) {
  return { operation_type, disposition: "execute", route, payload, observed_at: `2026-08-02T08:59:4${second}.000Z`, expected_readback_digest: digest(payload) };
}
function plan() {
  return buildYcTypedUpdatePlan({
    verified_at: "2026-08-02T08:59:50.000Z",
    application: { id: ID, batch: "Fall 2026", state: "In review", prior_application_submit_count: 1 },
    provider_manifest_digest: "a".repeat(64),
    preview: { preview_complete: true, submit_ready: true, blocking_issue_codes: [], preview_receipt_digest: "b".repeat(64) },
    operations: [
      operation("demo_update", `/apps/${ID}/edit/demo`, { demo_video: { source_ref: "application-kit://videos/life-manager-yc-demo.mp4", artifact_digest: "c".repeat(64) } }, 0),
      operation("progress_update", `/apps/${ID}/edit/progress`, { productLink: "https://github.com/Daisuke134/life-manager", productCreds: "No login required.", howfar: "Current progress.", worked: "Founder work.", techstack: "Current stack.", people_using: true, have_revenue: false }, 1),
      operation("team_update", `/apps/${ID}/edit/cofounder`, { others2: "No non-founder human writes the code.", cofounder: "Sole founder." }, 2),
      operation("founder_profile_update", "/bio/721f696b-0566-4a16-bda7-a9c368b1eac1/edit", { fhack: "A truthful hack.", fability: "A truthful achievement.", projects: "Truthful projects.", awards: "None.", testScores: "Truthful scores.", clubs: "None." }, 3),
    ],
    effects: { form_field_writes: 0, option_selections: 0, file_attachments: 0, update_control_activations: 0, application_submissions: 0, browser_closes: 0 },
  }, { now: "2026-08-02T09:00:00.000Z" });
}
function temporaryFence(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "yc-update-executor-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  return path.join(directory, "fence.json");
}
function clock() {
  const values = ["2026-08-02T09:00:01.000Z", "2026-08-02T09:00:02.000Z", "2026-08-02T09:00:03.000Z"];
  return () => values.shift();
}

test("persists effect_attempted before one adapter activation and confirms exact readback", async (t) => {
  const value = plan();
  const target = value.operations[1];
  const file = temporaryFence(t);
  const calls = [];
  const adapter = {
    async apply(operationValue) {
      calls.push(["apply", operationValue.operation_id, readFence(file).state]);
    },
    async readback(operationValue) {
      calls.push(["readback", operationValue.operation_id]);
      return { result: "confirmed", readback_digest: operationValue.expected_readback_digest };
    },
  };
  const result = await executeYcTypedUpdateOperation({ plan: value, operationId: target.operation_id, fenceFile: file, adapter, now: clock() });
  assert.equal(result.state, "confirmed");
  assert.deepEqual(calls, [["apply", target.operation_id, "effect_attempted"], ["readback", target.operation_id]]);
  assert.equal(readFence(file).activation_count, 1);
  await assert.rejects(() => executeYcTypedUpdateOperation({ plan: value, operationId: target.operation_id, fenceFile: file, adapter, now: clock() }), /already exists/i);
  assert.equal(calls.filter(([name]) => name === "apply").length, 1);
});

test("an ambiguous adapter failure is durably unknown and is never retried", async (t) => {
  const value = plan();
  const target = value.operations[0];
  const file = temporaryFence(t);
  let activations = 0;
  const adapter = {
    async apply() { activations += 1; throw new Error("connection lost after activation"); },
    async readback() { throw new Error("unavailable"); },
  };
  await assert.rejects(() => executeYcTypedUpdateOperation({ plan: value, operationId: target.operation_id, fenceFile: file, adapter, now: clock() }), /effect outcome unknown/i);
  assert.equal(readFence(file).state, "unknown_effect");
  await assert.rejects(() => executeYcTypedUpdateOperation({ plan: value, operationId: target.operation_id, fenceFile: file, adapter, now: clock() }), /already exists/i);
  assert.equal(activations, 1);
});
