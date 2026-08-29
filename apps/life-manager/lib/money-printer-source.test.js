"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createMoneyPrinterSource } = require("./money-printer-source.js");

const SUPA = Object.freeze({ supaUrl: "https://supa.example/", supaKey: "service-secret" });
const TENANT = "tenant-a";
const NOW = "2026-08-29T00:00:00.000Z";

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, async json() { return body; } };
}

function rowsFor(url) {
  const parsed = new URL(url);
  if (parsed.pathname.endsWith("/lm_users")) {
    return [{ uid: TENANT, agent_wallet_address: "0x1111111111111111111111111111111111111111" }];
  }
  if (parsed.pathname.endsWith("/lm_money_opportunities")) {
    return [{
      uid: TENANT,
      opportunity_id: "a".repeat(64),
      source_url: "https://public.example/opportunity",
      title: "Public opportunity",
      value_minor: "50000",
      currency: "JPY",
      status: "DISCOVERED",
      goal_ref: `intent-entry://${TENANT}/a${"a".repeat(63)}`,
      observed_at: NOW,
      goal_statement: "must not enter projection input",
    }];
  }
  if (parsed.pathname.endsWith("/lm_runtime_jobs")) {
    return [{ tenant_id: TENANT, job_id: "goal:a", status: "queued", created_at: NOW, updated_at: NOW, lease_owner: "must-not-leak" }];
  }
  if (parsed.pathname.endsWith("/lm_human_tasks")) {
    return [{ uid: TENANT, task_id: "b".repeat(64), status: "open", created_at: NOW, updated_at: NOW, answer_ref: "must-not-leak" }];
  }
  if (parsed.pathname.endsWith("/lm_runtime_job_receipts")) {
    return [{
      tenant_id: TENANT,
      job_id: "goal:a",
      attempt: 1,
      outcome: "completed",
      created_at: NOW,
      receipt: { kind: "application_receipt", application_external_id: "private-provider-state" },
    }];
  }
  if (parsed.pathname.endsWith("/lm_agent_earnings")) {
    return [{ entry_key: "earning-1", kind: "financial_external_income", amount_minor: "1200", currency: "JPY", occurred_at: NOW }];
  }
  throw new Error(`unexpected source URL ${url}`);
}

test("source reads tenant-scoped live rows and returns only projection-safe fields", async () => {
  const calls = [];
  const source = createMoneyPrinterSource({
    ...SUPA,
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
  assert.equal(input.generalReceipts.length, 0);
  assert.doesNotMatch(JSON.stringify(input), /goal_statement|service-secret|answer_ref|lease_owner|private-provider-state/i);
  for (const call of calls) {
    assert.match(call.url, /(?:uid|tenant_id|wallet_address)=eq\./);
    assert.equal(call.init.headers.Authorization, "Bearer service-secret");
  }
});

test("source refuses missing rows, malformed responses, and foreign-tenant rows", async () => {
  const source = createMoneyPrinterSource({
    ...SUPA,
    fetchImpl: async (url) => {
      const rows = rowsFor(url);
      if (new URL(url).pathname.endsWith("/lm_money_opportunities")) return response({});
      return response(rows);
    },
  });
  await assert.rejects(source({ uid: TENANT }), /opportun|exactly|empty|unavailable/i);

  const foreign = createMoneyPrinterSource({
    ...SUPA,
    fetchImpl: async (url) => {
      const rows = rowsFor(url);
      if (new URL(url).pathname.endsWith("/lm_runtime_jobs")) rows[0].tenant_id = "tenant-b";
      return response(rows);
    },
  });
  await assert.rejects(foreign({ uid: TENANT }), /tenant/i);
});
