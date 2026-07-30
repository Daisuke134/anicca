"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildFinancialReportJob,
  enqueueFinancialReportJobs,
  executeFinancialReportJob,
  safeFinancialReportSummary,
  verifyFinancialReportReceipt,
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

// ---------------------------------------------------------------------------
// Cadence-anchored enqueue. The measured defect this replaces: the scheduler
// derived slot identity from POLL time (`Math.floor(Date.now()/pollMs)*pollMs`),
// so every 5-minute poll minted a NEW job_id — 14 distinct queued
// report.financial.telegram jobs accumulated in 30 minutes of the local stack
// (~576/day), none of which could ever execute (they were all off-cadence).
// ---------------------------------------------------------------------------

const TZ = "Asia/Tokyo";
const THU_2000_JST = Date.parse("2026-07-30T11:00:00.000Z");
const THU_1959_JST = Date.parse("2026-07-30T10:59:59.000Z");
const FRI_2000_JST = Date.parse("2026-07-31T11:00:00.000Z");
const SUN_2005_JST = Date.parse("2026-08-02T11:05:00.000Z");

function enqueueRecorder() {
  const seen = new Set();
  const calls = [];
  return {
    calls,
    enqueueJob: async (input) => {
      calls.push(input);
      const created = !seen.has(input.jobId);
      seen.add(input.jobId);
      return { created, job: { ...input, status: "queued" } };
    },
  };
}

async function enqueueAt(nowMs, recorder, extra = {}) {
  return enqueueFinancialReportJobs(["enqueue", "--uid", "tenant-a"], {
    LM_TELEGRAM_TOKEN_REF: "secret://telegram/bot-token",
  }, {
    nowMs,
    timeZone: TZ,
    enqueueJob: recorder.enqueueJob,
    stdout: { write() {} },
    ...extra,
  });
}

test("every poll inside one due window mints exactly one job per report kind", async () => {
  const recorder = enqueueRecorder();
  const first = await enqueueAt(THU_2000_JST, recorder);
  const second = await enqueueAt(THU_2000_JST + 60_000, recorder);
  const third = await enqueueAt(THU_2000_JST + 3 * 3600_000, recorder);

  const daily = first.find((row) => row.report_kind === "daily");
  assert.equal(daily.created, true);
  assert.equal(daily.status, "queued");
  assert.equal(daily.slot, "2026-07-30T11:00:00.000Z");
  for (const later of [second, third]) {
    const row = later.find((entry) => entry.report_kind === "daily");
    assert.equal(row.created, false);
    assert.equal(row.status, "existing");
    assert.equal(row.job_id, daily.job_id);
  }
  // Thursday: the weekly slot is not due, so no weekly job exists at all.
  for (const result of [first, second, third]) {
    const weekly = result.find((row) => row.report_kind === "weekly");
    assert.equal(weekly.status, "not_due");
    assert.equal(weekly.job_id, null);
  }
  assert.equal(new Set(recorder.calls.map((call) => call.jobId)).size, 1);
  assert.equal(recorder.calls.length, 3);
});

test("crossing a period boundary mints exactly one new job", async () => {
  const recorder = enqueueRecorder();
  await enqueueAt(THU_2000_JST, recorder);
  await enqueueAt(THU_2000_JST + 60_000, recorder);
  const nextDay = await enqueueAt(FRI_2000_JST, recorder);

  const daily = nextDay.find((row) => row.report_kind === "daily");
  assert.equal(daily.created, true);
  assert.equal(daily.slot, "2026-07-31T11:00:00.000Z");
  assert.equal(new Set(recorder.calls.map((call) => call.jobId)).size, 2);
});

test("polls before the release window enqueue nothing at all", async () => {
  const recorder = enqueueRecorder();
  const result = await enqueueAt(THU_1959_JST, recorder);
  assert.deepEqual(result.map((row) => row.status), ["not_due", "not_due"]);
  assert.deepEqual(result.map((row) => row.job_id), [null, null]);
  assert.equal(recorder.calls.length, 0);
});

test("a Sunday poll after 20:05 mints exactly one daily and one weekly job", async () => {
  const recorder = enqueueRecorder();
  const result = await enqueueAt(SUN_2005_JST, recorder);
  await enqueueAt(SUN_2005_JST + 120_000, recorder);

  assert.deepEqual(result.map((row) => row.slot), [
    "2026-08-02T11:00:00.000Z",
    "2026-08-02T11:05:00.000Z",
  ]);
  assert.deepEqual(result.map((row) => row.created), [true, true]);
  assert.equal(new Set(recorder.calls.map((call) => call.jobId)).size, 2);
  assert.equal(recorder.calls.length, 4);
});

test("a forced enqueue outside the window anchors to the latest cadence slot", async () => {
  const recorder = enqueueRecorder();
  const first = await enqueueFinancialReportJobs(
    ["enqueue", "--uid", "tenant-a", "--force", "all"],
    { LM_TELEGRAM_TOKEN_REF: "secret://telegram/bot-token" },
    {
      nowMs: THU_1959_JST,
      timeZone: TZ,
      enqueueJob: recorder.enqueueJob,
      stdout: { write() {} },
    },
  );
  assert.deepEqual(first.map((row) => row.slot), [
    "2026-07-29T11:00:00.000Z",
    "2026-07-26T11:05:00.000Z",
  ]);
  assert.deepEqual(first.map((row) => row.created), [true, true]);
  assert.deepEqual(first.map((row) => row.forced), [true, true]);

  // A restart inside the same period re-derives the same forced identity.
  // (Still before 20:00 local, so the latest slots are unchanged.)
  const again = await enqueueFinancialReportJobs(
    ["enqueue", "--uid", "tenant-a", "--force", "all"],
    { LM_TELEGRAM_TOKEN_REF: "secret://telegram/bot-token" },
    {
      nowMs: THU_1959_JST - 60_000,
      timeZone: TZ,
      enqueueJob: recorder.enqueueJob,
      stdout: { write() {} },
    },
  );
  assert.deepEqual(again.map((row) => row.created), [false, false]);
  assert.equal(new Set(recorder.calls.map((call) => call.jobId)).size, 2);
});

// ---------------------------------------------------------------------------
// Shadow hold: the snapshot runs for real, the SEND is held.
// ---------------------------------------------------------------------------

function holdResult(overrides = {}) {
  return {
    status: "shadow_held",
    report_kind: "daily",
    period_key: "2026-08-02",
    slot: "2026-08-02T11:05:00.000Z",
    chat_id_hash: "c".repeat(64),
    snapshot_hash: "d".repeat(64),
    snapshot: { schema_version: 1, kind: "daily" },
    source_freshness: {
      report_cutoff_at: "2026-08-02T11:05:00.000Z",
      earnings_latest_at: "2026-08-02T10:00:00.000Z",
      costs_latest_at: "2026-08-02T10:30:00.000Z",
      balance_observed_at: "2026-08-02T11:05:00.000Z",
    },
    ...overrides,
  };
}

test("shadow mode holds the send, records the hold, and calls no Telegram provider", async () => {
  const calls = [];
  const holds = [];
  const job = buildFinancialReportJob({
    tenantId: "tenant-a",
    kind: "daily",
    nowMs: NOW_MS,
    telegramTokenRef: "secret://telegram/bot-token",
  });
  const { receipt, result } = await executeFinancialReportJob(job, {
    ...reportDeps(calls),
    hold: true,
    appendHold: async (hold) => { holds.push(hold); return "/data/held.jsonl"; },
    runReport: async (request, deps) => {
      calls.push({ kind: "run", hold: request.hold });
      assert.equal(typeof deps.sendTelegram, "function");
      await assert.rejects(
        () => deps.sendTelegram("t", "chat", "body"),
        /shadow/i,
      );
      return holdResult();
    },
    now: () => "2026-08-02T11:05:03.000Z",
  });

  assert.equal(calls.filter((call) => call.kind === "send").length, 0);
  assert.equal(calls.filter((call) => call.kind === "secret").length, 0);
  assert.equal(calls.find((call) => call.kind === "run").hold, true);
  assert.equal(result.status, "shadow_held");
  assert.deepEqual(receipt, {
    schema_version: 1,
    kind: "telegram_financial_report",
    status: "shadow_held",
    report_kind: "daily",
    period_key: "2026-08-02",
    slot: "2026-08-02T11:05:00.000Z",
    chat_id_hash: "c".repeat(64),
    snapshot_hash: "d".repeat(64),
    held_at: "2026-08-02T11:05:03.000Z",
    source_freshness: holdResult().source_freshness,
  });
  assert.equal(verifyFinancialReportReceipt(receipt), true);
  assert.deepEqual(holds, [{
    schema_version: 1,
    kind: "telegram_financial_report_hold",
    status: "shadow_held",
    tenant_id: "tenant-a",
    report_kind: "daily",
    period_key: "2026-08-02",
    slot: "2026-08-02T11:05:00.000Z",
    job_id: job.job_id,
    snapshot_hash: "d".repeat(64),
    chat_id_hash: "c".repeat(64),
    held_at: "2026-08-02T11:05:03.000Z",
  }]);
});

test("shadow mode fails closed without a durable hold sink", async () => {
  const job = buildFinancialReportJob({
    tenantId: "tenant-a",
    kind: "daily",
    nowMs: NOW_MS,
    telegramTokenRef: "secret://telegram/bot-token",
  });
  await assert.rejects(() => executeFinancialReportJob(job, {
    hold: true,
    runReport: async () => holdResult(),
  }), /hold sink/i);
});

test("a shadow-held receipt can never masquerade as a real send", () => {
  const base = {
    schema_version: 1,
    kind: "telegram_financial_report",
    status: "shadow_held",
    report_kind: "daily",
    period_key: "2026-08-02",
    slot: "2026-08-02T11:05:00.000Z",
    chat_id_hash: "c".repeat(64),
    snapshot_hash: "d".repeat(64),
    held_at: "2026-08-02T11:05:03.000Z",
    source_freshness: holdResult().source_freshness,
  };
  assert.equal(verifyFinancialReportReceipt(base), true);
  assert.equal(verifyFinancialReportReceipt({ ...base, message_id: 987 }), false);
  assert.equal(verifyFinancialReportReceipt({ ...base, sent_at: "2026-08-02T11:05:03.000Z" }), false);
  assert.equal(verifyFinancialReportReceipt({ ...base, snapshot_hash: "nope" }), false);
  assert.equal(verifyFinancialReportReceipt({ ...base, slot: "not-an-instant" }), false);
  assert.deepEqual(safeFinancialReportSummary(base), {
    status: "shadow_held",
    report_kind: "daily",
    period_key: "2026-08-02",
    slot: "2026-08-02T11:05:00.000Z",
    snapshot_hash: "d".repeat(64),
    source_freshness: base.source_freshness,
  });
});
