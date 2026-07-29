"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildFinancialReportJob,
  executeFinancialReportJob,
} = require("./report-job-adapter.js");
const {
  renderFinancialReport,
  snapshotHash,
} = require("./financial-report-runtime.js");

const NOW_MS = Date.parse("2026-08-02T11:05:00.000Z");
const WALLET = "0x477EeE969ccfdc0e959F38cE8B83e372FC0262ad";

function reportDeps(calls) {
  return {
    secretProvider: {
      async get(tenantId, ref) {
        calls.push({ kind: "secret", tenantId, ref });
        return "telegram-token-value";
      },
    },
    readTenant: async () => ({
      uid: "tenant-a",
      telegram_chat_id: "private-chat-id",
      agent_wallet_address: WALLET,
      notifications_enabled: true,
      call_time_zone: "Asia/Tokyo",
    }),
    readReceipt: async () => null,
    readLedger: async () => [{
      entry_key: "income-1",
      wallet_address: WALLET,
      kind: "financial_external_income",
      amount_minor: 100,
      currency: "USD",
      occurred_at: "2026-08-02T10:00:00.000Z",
      source: "x402_sale",
    }],
    readCosts: async () => [{
      ts: "2026-08-02T10:30:00.000Z",
      kind: "model",
      est_usd: "0.25",
    }],
    readBalance: async () => "42000000",
    claimReceipt: async () => ({ claimed: true }),
    markReceiptSent: async () => true,
    markReceiptFailed: async () => true,
    sendTelegram: async (token, chatId, body) => {
      calls.push({ kind: "send", token, chatId, body });
      return {
        ok: true,
        result: {
          message_id: 987,
          date: Math.floor(NOW_MS / 1000),
        },
      };
    },
  };
}

test("financial report jobs carry only immutable refs and reject raw Telegram secrets", () => {
  const job = buildFinancialReportJob({
    tenantId: "tenant-a",
    kind: "daily",
    nowMs: NOW_MS,
    telegramTokenRef: "secret://telegram/bot-token",
  });

  assert.equal(job.tenant_id, "tenant-a");
  assert.equal(job.loop_id, "financial.report");
  assert.equal(job.capability, "report.financial.telegram");
  assert.equal(job.effect_class, "message");
  assert.match(job.effect_key, /^telegram:financial:[0-9a-f]{64}$/);
  assert.deepEqual(job.input_refs, {
    financial_report_ref: "financial-report://tenant-a/daily/2026-08-02T11%3A05%3A00.000Z",
    telegram_token_ref: "secret://telegram/bot-token",
  });
  assert.doesNotMatch(JSON.stringify(job), /telegram-token-value|private-chat-id/);

  assert.throws(() => buildFinancialReportJob({
    tenantId: "tenant-a",
    kind: "daily",
    nowMs: NOW_MS,
    telegramTokenRef: "123456:raw-secret",
  }), /secret reference/i);
});

test("financial report refs preserve case-sensitive tenant identities", async () => {
  const job = buildFinancialReportJob({
    tenantId: "Tenant-A",
    kind: "daily",
    nowMs: NOW_MS,
    telegramTokenRef: "secret://telegram/bot-token",
  });
  assert.match(job.input_refs.financial_report_ref, /Tenant-A/);
  await assert.doesNotReject(() => executeFinancialReportJob(job, {
    secretProvider: { get: async () => "unused" },
    runReport: async () => ({ status: "skipped", report_kind: "daily" }),
  }));
});

test("adapter preserves the existing report body and snapshot hash and emits a safe effect receipt", async () => {
  const calls = [];
  const job = buildFinancialReportJob({
    tenantId: "tenant-a",
    kind: "daily",
    nowMs: NOW_MS,
    telegramTokenRef: "secret://telegram/bot-token",
  });
  const receipt = await executeFinancialReportJob(job, reportDeps(calls));
  const send = calls.find((call) => call.kind === "send");

  assert.deepEqual(calls[0], {
    kind: "secret",
    tenantId: "tenant-a",
    ref: "secret://telegram/bot-token",
  });
  assert.equal(send.body, renderFinancialReport(receipt.result.snapshot));
  assert.equal(receipt.receipt.snapshot_hash, snapshotHash(receipt.result.snapshot));
  assert.deepEqual({
    chat_id_hash: receipt.receipt.chat_id_hash,
    message_id: receipt.receipt.message_id,
    snapshot_hash: receipt.receipt.snapshot_hash,
    sent_at: receipt.receipt.sent_at,
    source_freshness: receipt.receipt.source_freshness,
  }, {
    chat_id_hash: "954c1bb22e1272793a5e52f5b972719c2b9c3f05d89ef7cde70f127430865132",
    message_id: 987,
    snapshot_hash: receipt.receipt.snapshot_hash,
    sent_at: "2026-08-02T11:05:00.000Z",
    source_freshness: {
      report_cutoff_at: "2026-08-02T11:05:00.000Z",
      earnings_latest_at: "2026-08-02T10:00:00.000Z",
      costs_latest_at: "2026-08-02T10:30:00.000Z",
      balance_observed_at: "2026-08-02T11:05:00.000Z",
    },
  });
  assert.doesNotMatch(JSON.stringify(receipt.receipt), /telegram-token-value|private-chat-id/);
});

test("adapter rejects cross-tenant jobs before resolving a secret or sending", async () => {
  const calls = [];
  const job = buildFinancialReportJob({
    tenantId: "tenant-a",
    kind: "weekly",
    nowMs: NOW_MS,
    telegramTokenRef: "secret://telegram/bot-token",
  });
  const tampered = { ...job, tenant_id: "tenant-b" };

  await assert.rejects(
    executeFinancialReportJob(tampered, reportDeps(calls)),
    /tenant scope mismatch/i,
  );
  assert.deepEqual(calls, []);
});

test("an error after Telegram dispatch is classified as an unknown external effect", async () => {
  const job = buildFinancialReportJob({
    tenantId: "tenant-a",
    kind: "daily",
    nowMs: NOW_MS,
    telegramTokenRef: "secret://telegram/bot-token",
  });
  const deps = reportDeps([]);
  deps.sendTelegram = async () => {
    throw new Error("connection ended after request write");
  };

  await assert.rejects(
    executeFinancialReportJob(job, deps),
    (error) => error.unknownEffect === true,
  );
});

test("a duplicate reconciles the existing real Telegram effect into the runtime receipt", async () => {
  const job = buildFinancialReportJob({
    tenantId: "tenant-a",
    kind: "daily",
    nowMs: NOW_MS,
    telegramTokenRef: "secret://telegram/bot-token",
  });
  const execution = await executeFinancialReportJob(job, {
    secretProvider: { get: async () => "unused-token" },
    runReport: async () => ({
      status: "duplicate",
      report_kind: "daily",
      period_key: "2026-08-02",
      telegram_message_id: 123,
      snapshot_hash: "a".repeat(64),
      chat_id_hash: "b".repeat(64),
      sent_at: "2026-08-02T11:05:01.000Z",
      source_freshness: {
        report_cutoff_at: "2026-08-02T11:05:00.000Z",
        earnings_latest_at: null,
        costs_latest_at: null,
        balance_observed_at: null,
      },
    }),
  });

  assert.deepEqual(execution.receipt, {
    schema_version: 1,
    kind: "telegram_financial_report",
    status: "duplicate",
    report_kind: "daily",
    period_key: "2026-08-02",
    chat_id_hash: "b".repeat(64),
    message_id: 123,
    snapshot_hash: "a".repeat(64),
    sent_at: "2026-08-02T11:05:01.000Z",
    source_freshness: {
      report_cutoff_at: "2026-08-02T11:05:00.000Z",
      earnings_latest_at: null,
      costs_latest_at: null,
      balance_observed_at: null,
    },
  });
});

test("a forced runtime job uses the durable job receipt as its one-shot dedupe boundary", async () => {
  const job = buildFinancialReportJob({
    tenantId: "tenant-a",
    kind: "weekly",
    nowMs: NOW_MS,
    force: true,
    telegramTokenRef: "secret://telegram/bot-token",
  });
  let runtimeDeps;
  const execution = await executeFinancialReportJob(job, {
    secretProvider: { get: async () => "token" },
    runReport: async (_request, receivedDeps) => {
      runtimeDeps = receivedDeps;
      return { status: "skipped", report_kind: "weekly", reason: "fixture" };
    },
  });

  assert.equal((await runtimeDeps.readReceipt()), null);
  assert.deepEqual(await runtimeDeps.claimReceipt(), { claimed: true });
  assert.equal(await runtimeDeps.markReceiptSent(), true);
  assert.equal(await runtimeDeps.markReceiptFailed(), true);
  assert.equal(execution.receipt.status, "skipped");
});
