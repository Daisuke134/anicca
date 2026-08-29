"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createMoneyPrinterRuntimeStore } = require("./money-printer-runtime-store.js");

const TENANT = "tenant-a";
const ID = "a".repeat(64);
const NOW = "2026-08-29T00:00:00.000Z";

function opportunity() {
  return {
    uid: TENANT, opportunity_id: ID, source_url: "https://public.example/opportunity",
    title: "Public opportunity", goal_statement: "Complete it.", value_minor: "50000",
    currency: "JPY", status: "DISCOVERED", goal_ref: `intent-entry://${TENANT}/${ID}`,
    job_id: `goal:${ID}`, observed_at: NOW,
  };
}

test("runtime store uses parameterized RPCs and tenant-bound reads", async () => {
  const calls = [];
  const task = {
    uid: TENANT, task_id: "b".repeat(64), version: 1, question: "Approve?",
    required_format: "approval", reason_code: "model_boundary", resume_ref: `runtime-job://${TENANT}/job-1`,
    status: "open", created_at: NOW, updated_at: NOW,
  };
  const store = createMoneyPrinterRuntimeStore({
    query: async (sql, values) => {
      calls.push({ sql, values });
      if (sql.includes("create_lm_money_opportunity")) return { rows: [opportunity()] };
      if (sql.includes("answer_lm_human_task")) return { rows: [{ ...task, status: "answered", answer_ref: "vault-answer://tenant-a/answer-1" }] };
      if (sql.includes("FROM public.lm_money_opportunities")) return { rows: [opportunity()] };
      if (sql.includes("FROM public.lm_runtime_jobs")) return { rows: [{ tenant_id: TENANT, job_id: `goal:${ID}`, status: "queued", created_at: NOW, updated_at: NOW }] };
      if (sql.includes("FROM public.lm_human_tasks")) return { rows: [task] };
      if (sql.includes("FROM public.lm_runtime_job_receipts")) return { rows: [{ tenant_id: TENANT, job_id: `goal:${ID}`, attempt: 1, outcome: "completed", created_at: NOW, receipt: { record_type: "application_receipt" } }] };
      throw new Error("unexpected query");
    },
  });

  assert.deepEqual(await store.createOpportunity(opportunity()), opportunity());
  assert.deepEqual(await store.readNext({ uid: TENANT }), task);
  assert.equal((await store.answerOnce({ uid: TENANT, taskId: task.task_id, version: 1, answerRef: "vault-answer://tenant-a/answer-1" })).status, "answered");
  const snapshot = await store.readRuntimeSnapshot(TENANT);
  assert.equal(snapshot.opportunities.length, 1);
  assert.equal(snapshot.runtimeJobs.length, 1);
  assert.equal(snapshot.humanTasks.length, 1);
  assert.equal(snapshot.receipts.length, 1);

  assert.match(calls[0].sql, /^\s*SELECT \* FROM public\.create_lm_money_opportunity\(\$1, \$2, \$3, \$4, \$5, \$6, \$7, \$8, \$9\)/i);
  assert.deepEqual(calls[0].values, [TENANT, ID, "https://public.example/opportunity", "Public opportunity", "Complete it.", "50000", "JPY", NOW, `intent-entry://${TENANT}/${ID}`]);
  assert.match(calls[1].sql, /^\s*SELECT uid, task_id, version, question, required_format, reason_code, resume_ref, status, created_at, updated_at\s+FROM public\.lm_human_tasks/i);
  assert.deepEqual(calls[1].values, [TENANT]);
  assert.match(calls[2].sql, /^\s*SELECT \* FROM public\.answer_lm_human_task\(\$1, \$2, \$3, \$4\)/i);
  assert.deepEqual(calls[2].values, [TENANT, task.task_id, 1, "vault-answer://tenant-a/answer-1"]);
  for (const call of calls) assert.ok(Array.isArray(call.values));
});

test("runtime store rejects unavailable query and foreign or ambiguous readback", async () => {
  assert.throws(() => createMoneyPrinterRuntimeStore({}), /runtime store unavailable/);
  const store = createMoneyPrinterRuntimeStore({ query: async () => ({ rows: [{ ...opportunity(), uid: "tenant-b" }, opportunity()] }) });
  await assert.rejects(store.createOpportunity(opportunity()), /readback/);
});
