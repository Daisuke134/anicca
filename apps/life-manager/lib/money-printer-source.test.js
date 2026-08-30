"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createMoneyPrinterSource } = require("./money-printer-source.js");

const SUPA = Object.freeze({ supaUrl: "https://supa.example/", supaKey: "service-secret" });
const TENANT = "tenant-a";
const NOW = "2026-08-29T00:00:00.000Z";
const OPPORTUNITY_ID = "a".repeat(64);

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, async json() { return body; } };
}

function rowsFor(url) {
  const parsed = new URL(url);
  if (parsed.pathname.endsWith("/lm_users")) {
    return [{ uid: TENANT, agent_wallet_address: "0x1111111111111111111111111111111111111111" }];
  }
  if (parsed.pathname.endsWith("/lm_agent_earnings")) {
    return [{ entry_key: "earning-1", kind: "financial_external_income", amount_minor: "1200", currency: "JPY", occurred_at: NOW }];
  }
  throw new Error(`unexpected source URL ${url}`);
}

function runtimeSnapshot() {
  return {
    opportunities: [{
      uid: TENANT, opportunity_id: "a".repeat(64), source_url: "https://public.example/opportunity",
      title: "Public opportunity", value_minor: "50000", currency: "JPY", status: "DISCOVERED",
      goal_ref: `intent-entry://${TENANT}/${OPPORTUNITY_ID}`, observed_at: NOW, goal_statement: "must not enter projection input",
    }],
    runtimeJobs: [{ tenant_id: TENANT, job_id: `goal:${OPPORTUNITY_ID}`, status: "queued", created_at: NOW, updated_at: NOW, lease_owner: "must-not-leak" }],
    humanTasks: [{
      uid: TENANT, task_id: "b".repeat(64), job_id: `goal:${OPPORTUNITY_ID}`, reason_code: "identity_assessment", version: 1,
      status: "open", created_at: NOW, updated_at: NOW, answer_ref: "must-not-leak",
      question: "must-not-leak", context_refs: { private_ref: "must-not-leak" },
    }],
    receipts: [{
      tenant_id: TENANT, job_id: `goal:${OPPORTUNITY_ID}`, attempt: 1, outcome: "completed", created_at: NOW,
      receipt: { record_type: "application_receipt", application_external_id: "application-public-1", provider_secret: "private-provider-state" },
    }],
  };
}

test("source reads tenant-scoped live rows and returns only projection-safe fields", async () => {
  const calls = [];
  const source = createMoneyPrinterSource({
    ...SUPA,
    runtimeStore: { readRuntimeSnapshot: async (uid) => { assert.equal(uid, TENANT); return runtimeSnapshot(); } },
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return response(rowsFor(url));
    },
  });
  const input = await source({ uid: TENANT, chatId: "private-chat" });

  assert.equal(input.tenantId, TENANT);
  assert.equal(input.opportunities.length, 1);
  assert.equal(input.opportunities[0].tenant_id, TENANT);
  assert.equal(input.earnings[0].verified, true);
  assert.equal(input.applicationReceipts.length, 1);
  assert.equal(input.applicationReceipts[0].receipt_id, "application-public-1");
  assert.equal(input.applicationReceipts[0].status, "completed");
  assert.equal(input.applicationReceipts[0].observed_at, NOW);
  assert.equal(input.generalReceipts.length, 0);
  assert.deepEqual(input.humanTasks[0], {
    tenant_id: TENANT, task_id: "b".repeat(64), job_id: `goal:${OPPORTUNITY_ID}`, reason_code: "identity_assessment", version: 1,
    status: "open", created_at: NOW, updated_at: NOW,
  });
  assert.doesNotMatch(JSON.stringify(input), /goal_statement|service-secret|answer_ref|lease_owner|private-provider-state/i);
  for (const call of calls) {
    assert.match(call.url, /(?:uid|tenant_id|wallet_address)=eq\./);
    assert.equal(call.init.headers.Authorization, "Bearer service-secret");
    assert.doesNotMatch(call.url, /lm_(?:money_opportunities|runtime_jobs|human_tasks|runtime_job_receipts)/);
  }

  let guestEarningsReads = 0;
  const guestSource = createMoneyPrinterSource({
    ...SUPA,
    runtimeStore: { readRuntimeSnapshot: async () => runtimeSnapshot() },
    fetchImpl: async (url, init) => {
      const parsed = new URL(url);
      if (parsed.pathname.endsWith("/lm_users")) return response([{ uid: TENANT, agent_wallet_address: null }]);
      if (parsed.pathname.endsWith("/lm_agent_earnings")) guestEarningsReads += 1;
      return response(rowsFor(url, init));
    },
  });
  const guestInput = await guestSource({ uid: TENANT });
  assert.deepEqual(guestInput.earnings, []);
  assert.equal(guestEarningsReads, 0);
});

test("source projects kindless failures and reconciliations without leaking raw receipts", async () => {
  const snapshot = {
    ...runtimeSnapshot(),
    receipts: [
      {
        tenant_id: TENANT,
        job_id: "goal:failed",
        attempt: 1,
        outcome: "failed",
        created_at: NOW,
        receipt: { error_code: "CAPABILITY_EXECUTION_FAILED", raw_detail: "private failure" },
      },
      {
        tenant_id: TENANT,
        job_id: "goal:present",
        attempt: 2,
        outcome: "reconciled_present",
        created_at: NOW,
        receipt: { status: "wrong-status", error_code: "PRIVATE_PRESENT_ERROR" },
      },
      {
        tenant_id: TENANT,
        job_id: "goal:absent",
        attempt: 3,
        outcome: "reconciled_absent",
        created_at: NOW,
        receipt: { status: "wrong-status", error_code: "PRIVATE_ABSENT_ERROR" },
      },
    ],
  };
  const source = createMoneyPrinterSource({
    ...SUPA,
    runtimeStore: { readRuntimeSnapshot: async () => snapshot },
    fetchImpl: async (url) => response(rowsFor(url)),
  });
  const input = await source({ uid: TENANT });

  assert.deepEqual(input.generalReceipts, [
    { tenant_id: TENANT, receipt_id: "goal:failed:1", status: "failed", observed_at: NOW },
    { tenant_id: TENANT, receipt_id: "goal:present:2", status: "reconciled_present", observed_at: NOW },
    { tenant_id: TENANT, receipt_id: "goal:absent:3", status: "reconciled_absent", observed_at: NOW },
  ]);
  assert.doesNotMatch(JSON.stringify(input), /CAPABILITY_EXECUTION_FAILED|PRIVATE_PRESENT_ERROR|PRIVATE_ABSENT_ERROR|private failure/);
});

test("source still rejects a kindless completed runtime receipt", async () => {
  const source = createMoneyPrinterSource({
    ...SUPA,
    runtimeStore: {
      readRuntimeSnapshot: async () => ({
        ...runtimeSnapshot(),
        receipts: [{
          tenant_id: TENANT,
          job_id: "goal:completed",
          attempt: 1,
          outcome: "completed",
          created_at: NOW,
          receipt: { application_external_id: "must-not-pass" },
        }],
      }),
    },
    fetchImpl: async (url) => response(rowsFor(url)),
  });
  await assert.rejects(source({ uid: TENANT }), /runtime receipt kind/i);
});

test("source refuses missing rows, malformed responses, and foreign-tenant rows", async () => {
  const source = createMoneyPrinterSource({
    ...SUPA,
    runtimeStore: { readRuntimeSnapshot: async () => ({ ...runtimeSnapshot(), opportunities: [{}] }) },
    fetchImpl: async (url) => {
      return response(rowsFor(url));
    },
  });
  await assert.rejects(source({ uid: TENANT }), /opportun|tenant|unavailable/i);

  const foreign = createMoneyPrinterSource({
    ...SUPA,
    runtimeStore: { readRuntimeSnapshot: async () => ({ ...runtimeSnapshot(), runtimeJobs: [{ ...runtimeSnapshot().runtimeJobs[0], tenant_id: "tenant-b" }] }) },
    fetchImpl: async (url) => {
      return response(rowsFor(url));
    },
  });
  await assert.rejects(foreign({ uid: TENANT }), /tenant/i);
});
