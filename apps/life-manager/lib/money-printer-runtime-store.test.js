"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createMoneyPrinterRuntimeStore } = require("./money-printer-runtime-store.js");
const { buildOpportunity } = require("./money-printer-opportunity.js");

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

test("runtime store normalizes a Postgres Date observed_at without changing other fields", async () => {
  const persisted = { ...opportunity(), observed_at: new Date(NOW) };
  const store = createMoneyPrinterRuntimeStore({
    query: async (sql) => {
      if (sql.includes("create_lm_money_opportunity")) return { rows: [persisted] };
      throw new Error("unexpected query");
    },
  });

  assert.deepEqual(await store.createOpportunity(opportunity()), { ...persisted, observed_at: NOW });
});

test("runtime store creates one human task through the atomic pause RPC", async () => {
  const calls = [];
  const task = {
    uid: TENANT, task_id: "b".repeat(64), job_id: `goal:${ID}`, version: 1,
    question: "Complete the assessment.", required_format: { type: "confirmation" },
    reason_code: "identity_assessment", resume_ref: `runtime-job://${TENANT}/goal%3A${ID}`,
    context_refs: { goal_ref: `intent-entry://${TENANT}/${ID}` },
    human_boundary_ref: `human-boundary://sha256/${"c".repeat(64)}`,
    status: "open", created_at: NOW, updated_at: NOW,
  };
  const store = createMoneyPrinterRuntimeStore({ query: async (sql, values) => {
    calls.push({ sql, values });
    return { rows: [task] };
  } });

  assert.deepEqual(await store.createOnce(task), task);
  assert.match(calls[0].sql, /^\s*SELECT \* FROM public\.create_lm_human_task\(\$1, \$2, \$3, \$4, \$5, \$6, \$7, \$8, \$9\)/i);
  assert.deepEqual(calls[0].values, [
    task.uid, task.task_id, task.job_id, task.reason_code, task.question,
    task.required_format, task.resume_ref, task.context_refs, task.human_boundary_ref,
  ]);
});

test("runtime store reads answered references only for the same tenant job", async () => {
  const answered = {
    uid: TENANT, job_id: `goal:${ID}`, reason_code: "identity_assessment",
    answer_ref: `vault-answer://${TENANT}/answer-1`,
    human_boundary_ref: `human-boundary://sha256/${"c".repeat(64)}`,
    version: 1, updated_at: NOW,
  };
  const calls = [];
  const store = createMoneyPrinterRuntimeStore({ query: async (sql, values) => {
    calls.push({ sql, values });
    return { rows: [answered] };
  } });

  assert.deepEqual(await store.readAnsweredForJob({ tenant_id: TENANT, job_id: `goal:${ID}` }), [answered]);
  assert.match(calls[0].sql, /FROM public\.lm_human_tasks[\s\S]*status = 'answered'/i);
  assert.deepEqual(calls[0].values, [TENANT, `goal:${ID}`]);
});

test("runtime store rejects an invalid create opportunity timestamp", async () => {
  const store = createMoneyPrinterRuntimeStore({
    query: async (sql) => {
      if (sql.includes("create_lm_money_opportunity")) {
        return { rows: [{ ...opportunity(), observed_at: new Date("invalid") }] };
      }
      throw new Error("unexpected query");
    },
  });

  await assert.rejects(store.createOpportunity(opportunity()), /observed|time|readback/i);
});

test("runtime store rejects unavailable query and foreign or ambiguous readback", async () => {
  assert.throws(() => createMoneyPrinterRuntimeStore({}), /runtime store unavailable/);
  const store = createMoneyPrinterRuntimeStore({ query: async () => ({ rows: [{ ...opportunity(), uid: "tenant-b" }, opportunity()] }) });
  await assert.rejects(store.createOpportunity(opportunity()), /readback/);
});

test("runtime store reads and idempotently qualifies one exact opportunity", async () => {
  const calls = [];
  const qualified = { ...opportunity(), status: "QUALIFIED" };
  const expected = {
    tenant_id: TENANT,
    opportunity_id: ID,
    goal_ref: `intent-entry://${TENANT}/${ID}`,
  };
  const store = createMoneyPrinterRuntimeStore({
    query: async (sql, values) => {
      calls.push({ sql, values });
      if (sql.includes("WITH updated AS")) return { rows: [qualified] };
      if (sql.includes("FROM public.lm_money_opportunities")) return { rows: [opportunity()] };
      throw new Error("unexpected query");
    },
  });

  assert.deepEqual(await store.readOpportunity(expected), opportunity());
  assert.deepEqual(await store.updateOpportunity(expected, "QUALIFIED"), qualified);
  assert.deepEqual(await store.updateOpportunity(expected, "QUALIFIED"), qualified);

  assert.match(calls[0].sql, /SELECT uid, opportunity_id, source_url, title, goal_statement, value_minor, currency, status, goal_ref, observed_at\s+FROM public\.lm_money_opportunities/i);
  assert.match(calls[0].sql, /WHERE uid = \$1 AND opportunity_id = \$2 AND goal_ref = \$3/i);
  assert.deepEqual(calls[0].values, [TENANT, ID, expected.goal_ref]);
  for (const call of calls.slice(1)) {
    assert.match(call.sql, /UPDATE public\.lm_money_opportunities/i);
    assert.match(call.sql, /status IN \('DISCOVERED', 'QUALIFYING'\)/i);
    assert.match(call.sql, /status = 'QUALIFIED'/i);
    assert.match(call.sql, /NOT EXISTS \(SELECT 1 FROM updated\)/i);
    assert.deepEqual(call.values, [TENANT, ID, expected.goal_ref, "QUALIFIED"]);
  }
});

test("runtime store rejects non-QUALIFIED or non-exact opportunity qualification", async () => {
  const expected = {
    tenant_id: TENANT,
    opportunity_id: ID,
    goal_ref: `intent-entry://${TENANT}/${ID}`,
  };
  const rejectedRows = [
    [],
    [opportunity(), opportunity()],
    [{ ...opportunity(), uid: "tenant-b" }],
    [{ ...opportunity(), opportunity_id: "b".repeat(64) }],
    [{ ...opportunity(), goal_ref: `intent-entry://${TENANT}/${"b".repeat(64)}` }],
  ];
  for (const rows of rejectedRows) {
    const store = createMoneyPrinterRuntimeStore({ query: async () => ({ rows }) });
    await assert.rejects(store.readOpportunity(expected), /readback/);
    await assert.rejects(store.updateOpportunity(expected, "QUALIFIED"), /readback/);
  }
  const store = createMoneyPrinterRuntimeStore({ query: async () => ({ rows: [opportunity()] }) });
  await assert.rejects(store.updateOpportunity(expected, "DISCOVERED"), /status/);
});

test("runtime store reads at most one full opportunity by tenant-scoped canonical source URL", async () => {
  const calls = [];
  const persisted = buildOpportunity({
    tenantId: TENANT, sourceUrl: "https://public.example/opportunity", title: "Public opportunity",
    goalStatement: "Complete it.", valueMinor: "50000", currency: "JPY", observedAt: NOW,
  });
  const store = createMoneyPrinterRuntimeStore({
    query: async (sql, values) => {
      calls.push({ sql, values });
      return { rows: [persisted] };
    },
  });
  assert.deepEqual(await store.readOpportunityBySource({
    tenant_id: TENANT, source_url: "https://public.example/opportunity",
  }), persisted);
  assert.match(calls[0].sql, /SELECT uid, opportunity_id, source_url, title, goal_statement, value_minor, currency, status, goal_ref, observed_at/i);
  assert.match(calls[0].sql, /WHERE uid = \$1 AND source_url = \$2/i);
  assert.deepEqual(calls[0].values, [TENANT, "https://public.example/opportunity"]);

  for (const rows of [[persisted, persisted], [{ ...persisted, uid: "tenant-b" }], [{ ...persisted, status: null }]]) {
    const invalid = createMoneyPrinterRuntimeStore({ query: async () => ({ rows }) });
    await assert.rejects(invalid.readOpportunityBySource({ tenant_id: TENANT, source_url: "https://public.example/opportunity" }), /readback/);
  }
});

test("runtime store source lookup normalizes a Postgres Date and rejects an invalid timestamp", async () => {
  const persisted = buildOpportunity({
    tenantId: TENANT, sourceUrl: "https://public.example/date", title: "Public opportunity",
    goalStatement: "Complete it.", valueMinor: "50000", currency: "JPY", observedAt: NOW,
  });
  const store = createMoneyPrinterRuntimeStore({
    query: async () => ({ rows: [{ ...persisted, observed_at: new Date(NOW) }] }),
  });
  assert.deepEqual(await store.readOpportunityBySource({
    tenant_id: TENANT, source_url: "https://public.example/date",
  }), persisted);
  const invalid = createMoneyPrinterRuntimeStore({
    query: async () => ({ rows: [{ ...persisted, observed_at: new Date("invalid") }] }),
  });
  await assert.rejects(invalid.readOpportunityBySource({
    tenant_id: TENANT, source_url: "https://public.example/date",
  }), /readback|observed|time/i);
});
