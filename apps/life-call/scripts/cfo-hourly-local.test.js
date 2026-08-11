"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { deriveMoneytreeState, composeMoneytreeRead } = require("../lib/cfo-moneytree-state.js");
const { buildCfoDailyReport } = require("../lib/cfo-daily-snapshot.js");
const { buildCfoDailyReportFromRecovery } = require("../lib/cfo-recovery-snapshot.js");
const { renderCfoTelegram } = require("../lib/cfo-telegram.js");
const { runHourlyCfo, main } = require("./cfo-hourly-local.js");

const CLOCK = new Date("2026-08-10T03:04:05.000Z");
const DATE = "2026-08-10";
const UID = "owner-hourly-fixture";
const CHAT = "123456";
const RUN = "10000000-0000-4000-8000-000000000001";
const REF1 = "20000000-0000-4000-8000-000000000001";
const REF2 = "20000000-0000-4000-8000-000000000002";
const ENV = {
  SUPABASE_URL: "https://fixture.supabase.co",
  SUPABASE_SERVICE_ROLE_KEY: "service-role-fixture",
  LM_UID_SECRET: "fixture-lm-uid-secret-that-is-at-least-32-bytes",
  LM_TELEGRAM_BOT_TOKEN: "telegram-token-fixture",
};
const ANTHROPIC_RECEIPT = Object.freeze({ schema_version: "lm_subscription_receipt_v1", provider: "anthropic", plan: "max_20x", billing_period_start: "2026-08-10", billing_period_end: "2026-09-10", subtotal: "200.00", tax: "20.00", total: "220.00", currency: "USD", paid_date: "2026-08-10", source_hash: `sha256:${"c".repeat(64)}`, evidence_status: "provider_receipt" });
const AI_COST = Object.freeze({ provider: "anthropic", plan: "max_20x", amount: "220.00", currency: "USD", billingPeriodStart: "2026-08-10", billingPeriodEnd: "2026-09-10", evidenceStatus: "provider_receipt", unavailableProviders: ["openai"] });
function anthropicCapture(status = "appended", confirmed = ANTHROPIC_RECEIPT, recordId = confirmed.source_hash) { return { status, record_id: recordId, confirmed }; }
function snapshotWithAi(ref, aiCost = AI_COST) { const row = snapshotRow(ref, 100); row.report_payload = { ...row.report_payload, aiCost }; return row; }

function moneytreeRead(amountMinor, observedAt = CLOCK.toISOString()) {
  const source = {
    schemaVersion: 1, sourceId: "moneytree_mufg", consent: "valid", freshness: "fresh", asOf: observedAt,
    accounts: [{ accountRef: "source_account:fixture", label: "MUFG 普通預金", kind: "deposit", currency: "JPY", balanceMinor: amountMinor, verificationStatus: "provider_reported" }],
    liabilities: [], evidenceRef: "evidence:fixture", partial: true, actionRequired: null,
  };
  const state = deriveMoneytreeState({ signal: "interactive_success", observedAt, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null });
  return composeMoneytreeRead({ source, state });
}

function recoveryRead(amountMinor, status = "fresh") {
  return {
    reportingDate: DATE, observedAt: CLOCK.toISOString(), status, attempts: 1,
    failureKind: null, moneytreeRead: moneytreeRead(amountMinor), repair: null, action: null,
  };
}
function actionRecovery(kind) { return { reportingDate: DATE, observedAt: CLOCK.toISOString(), status: "action_required", attempts: 1, failureKind: kind === "provider_outage" ? kind : "expired", moneytreeRead: null, repair: null, action: { kind, sourceLabel: "Moneytree", retryLabel: kind === "provider_outage" ? "30分後に自動再確認" : "接続後に自動再確認", nextRetryAt: new Date(CLOCK.getTime() + 1800000).toISOString() } }; }

function snapshotRow(publicRef, amountMinor, revision = 1) {
  const report = { ...buildCfoDailyReport({ reportingDate: DATE, moneytreeRead: moneytreeRead(amountMinor) }), revision };
  return { public_ref: publicRef, reporting_date: DATE, run_id: RUN, revision, created_at: CLOCK.toISOString(), report_payload: report };
}
function reordered(value) { if (Array.isArray(value)) return value.map(reordered); if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).reverse().map((key) => [key, reordered(value[key])])); return value; }

function baseOptions(overrides = {}) {
  return {
    env: ENV, uid: UID, chatId: CHAT, now: () => CLOCK, runLocalAgentUsageCollection: async () => undefined,
    readMoneytreeViaCodex: async () => moneytreeRead(100),
    resolveCfoDailyRun: async () => ({ public_ref: "30000000-0000-4000-8000-000000000001", reporting_date: DATE, run_id: RUN, time_zone: "Asia/Tokyo", created_at: CLOCK.toISOString() }),
    latestSnapshot: async () => null,
    appendCfoDailySnapshot: async () => ({ public_ref: REF1, reporting_date: DATE, run_id: RUN, revision: 1, created_at: CLOCK.toISOString() }),
    appendCfoDailySnapshotRevision: async () => ({ public_ref: REF2, reporting_date: DATE, run_id: RUN, revision: 2, supersedes_revision: 1, created_at: CLOCK.toISOString() }),
    deliverCfoTelegram: async () => ({ status: "sent", messageId: 42 }),
    wait: async () => undefined,
    ...overrides,
  };
}

test("fresh first read appends revision 1 and delivers it once", async () => {
  const calls = { append: 0, deliver: 0 };
  const result = await runHourlyCfo(baseOptions({
    appendCfoDailySnapshot: async (input) => { calls.append += 1; assert.equal(input.uid, UID); assert.equal(input.reportingDate, DATE); assert.equal(input.runId, RUN); return { public_ref: REF1, reporting_date: DATE, run_id: RUN, revision: 1, created_at: CLOCK.toISOString() }; },
    deliverCfoTelegram: async (input) => { calls.deliver += 1; assert.equal(input.snapshotPublicRef, REF1); assert.equal(input.snapshot.revision, 1); assert.equal(input.snapshot.totals.assetsMinor, 100); return { status: "sent", messageId: 42 }; },
  }));
  assert.deepEqual(result, { status: "sent", reportingDate: DATE, revision: 1, appended: true, delivered: true, recovered: false });
  assert.deepEqual(calls, { append: 1, deliver: 1 });
});

test("unchanged hourly facts pass through durable delivery and already-sent stays quiet", async () => {
  let append = 0;
  let deliver = 0;
  const result = await runHourlyCfo(baseOptions({
    latestSnapshot: async () => snapshotRow(REF1, 100),
    appendCfoDailySnapshot: async () => { append += 1; return null; },
    deliverCfoTelegram: async () => { deliver += 1; return { status: "already_sent", messageId: null }; },
  }));
  assert.deepEqual(result, { status: "quiet", reportingDate: DATE, revision: 1, appended: false, delivered: false, recovered: false });
  assert.equal(append, 0);
  assert.equal(deliver, 1);
});

test("same facts from a prior owner hour append a new revision and deliver it", async () => {
  const prior = new Date(CLOCK.getTime() - 3600000).toISOString();
  let appended, delivered;
  const result = await runHourlyCfo(baseOptions({
    latestSnapshot: async () => ({ ...snapshotRow(REF1, 100), created_at: prior }),
    appendCfoDailySnapshotRevision: async (input) => { appended = input; return { public_ref: REF2, reporting_date: DATE, run_id: RUN, revision: 2, supersedes_revision: 1, created_at: CLOCK.toISOString() }; },
    deliverCfoTelegram: async (input) => { delivered = input; return { status: "sent", messageId: 45 }; },
  }));
  assert.equal(appended.revision, 2);
  assert.equal(appended.supersedesRevision, 1);
  assert.equal(appended.report.totals.assetsMinor, 100);
  assert.equal(delivered.snapshotPublicRef, REF2);
  assert.equal(delivered.snapshot.revision, 2);
  assert.deepEqual(result, { status: "sent", reportingDate: DATE, revision: 2, appended: true, delivered: true, recovered: false });
});

test("changed facts append N+1 and deliver that exact revision", async () => {
  const calls = { revision: 0, deliver: 0 };
  const requests = [];
  const result = await runHourlyCfo(baseOptions({
    readMoneytreeViaCodex: async () => moneytreeRead(125),
    latestSnapshot: undefined,
    appendCfoDailySnapshotRevision: undefined,
    fetchImpl: async (url, init) => {
      requests.push({ url, init });
      if (init.method === "GET") return { ok: true, status: 200, json: async () => [snapshotRow(REF1, 100)] };
      return { ok: true, status: 200, json: async () => ({ public_ref: REF2, reporting_date: DATE, run_id: RUN, revision: 2, supersedes_revision: 1, created_at: CLOCK.toISOString() }) };
    },
    deliverCfoTelegram: async (input) => { calls.deliver += 1; assert.equal(input.snapshotPublicRef, REF2); assert.equal(input.snapshot.revision, 2); assert.equal(input.snapshot.totals.assetsMinor, 125); return { status: "sent", messageId: 43 }; },
    repair: async () => { calls.revision += 1; return true; },
  }));
  assert.deepEqual(result, { status: "sent", reportingDate: DATE, revision: 2, appended: true, delivered: true, recovered: false });
  assert.deepEqual(calls, { revision: 0, deliver: 1 });
  assert.equal(requests.length, 3);
  assert.match(requests[0].url, /\/rest\/v1\/lm_cfo_daily_snapshots\?/);
  assert.match(requests[2].url, /\/rest\/v1\/rpc\/lm_append_cfo_daily_snapshot_revision$/);
  const payload = JSON.parse(requests[2].init.body);
  assert.deepEqual(Object.keys(payload).sort(), ["p_report_payload", "p_run_id", "p_source_bundle", "p_supersedes_revision", "p_uid", "p_reporting_date", "p_revision"].sort());
  assert.deepEqual({ uid: payload.p_uid, date: payload.p_reporting_date, run: payload.p_run_id, revision: payload.p_revision, supersedes: payload.p_supersedes_revision }, { uid: UID, date: DATE, run: RUN, revision: 2, supersedes: 1 });
  assert.equal(payload.p_report_payload.totals.assetsMinor, 125); assert.equal(payload.p_report_payload.revision, 2); assert.equal(payload.p_source_bundle.source.accounts[0].balanceMinor, 125);
});

test("action-required candidate renders before append and delivers once", async () => {
  for (const kind of ["provider_outage", "reconsent"]) {
    const calls = [], latest = snapshotRow(REF1, 100);
    const result = await runHourlyCfo(baseOptions({ latestSnapshot: async () => latest, recoverMoneytreeRead: async () => actionRecovery(kind), renderCfoTelegram: (input) => { calls.push(["render", input.snapshot]); return renderCfoTelegram(input); }, appendCfoDailySnapshotRevision: async (input) => { calls.push(["append", input]); return { public_ref: REF2, reporting_date: DATE, run_id: RUN, revision: 2, supersedes_revision: 1, created_at: CLOCK.toISOString() }; }, deliverCfoTelegram: async (input) => { calls.push(["deliver", input]); return { status: "sent", messageId: 44 }; } }));
    assert.deepEqual(result, { status: "sent", reportingDate: DATE, revision: 2, appended: true, delivered: true, recovered: false });
    assert.deepEqual(calls.map(([name]) => name), ["render", "render", "append", "deliver"]);
    assert.strictEqual(calls[1][1], calls[2][1].report); assert.strictEqual(calls[3][1].snapshot, calls[2][1].report); assert.equal(calls[3][1].snapshotPublicRef, REF2); assert.equal(calls[3][1].snapshot.action.kind, kind);
  }
});

test("same-facts delivery reuses the exact snapshot/ref and main exits only for sent or quiet", async () => {
  for (const [deliveryStatus, expectedStatus, expectedExit] of [["already_sent", "quiet", 0], ["sent", "sent", 0], ["reconcile", "retry", 1], ["unknown", "failed", 1]]) {
    const persisted = snapshotRow(REF1, 100); let append = 0; let deliveredInput;
    const output = []; const result = await main({ ...baseOptions({ latestSnapshot: async () => persisted, appendCfoDailySnapshot: async () => { append += 1; }, deliverCfoTelegram: async (input) => { deliveredInput = input; return { status: deliveryStatus }; } }), stdout: (line) => output.push(line) });
    assert.equal(result.exitCode, expectedExit); assert.equal(JSON.parse(output[0]).status, expectedStatus); assert.equal(append, 0); assert.equal(deliveredInput.snapshotPublicRef, REF1); assert.strictEqual(deliveredInput.snapshot, persisted.report_payload);
  }
});

test("same-facts JSONB key order stays quiet and deduped", async () => {
  const persisted = { public_ref: REF1, reporting_date: DATE, run_id: RUN, revision: 1, created_at: CLOCK.toISOString(), report_payload: reordered(buildCfoDailyReportFromRecovery({ revision: 1, recovery: actionRecovery("provider_outage") }).report) }; let append = 0; let deliver = 0; let deliveredInput;
  const result = await runHourlyCfo(baseOptions({ recoverMoneytreeRead: async () => actionRecovery("provider_outage"), latestSnapshot: async () => persisted, appendCfoDailySnapshotRevision: async () => { append += 1; return { public_ref: REF2, reporting_date: DATE, run_id: RUN, revision: 2, supersedes_revision: 1, created_at: CLOCK.toISOString() }; }, deliverCfoTelegram: async (input) => { deliver += 1; deliveredInput = input; return { status: "already_sent" }; } }));
  assert.deepEqual(result, { status: "quiet", reportingDate: DATE, revision: 1, appended: false, delivered: false, recovered: false }); assert.equal(append, 0); assert.equal(deliver, 1); assert.equal(deliveredInput.snapshotPublicRef, REF1); assert.strictEqual(deliveredInput.snapshot, persisted.report_payload);
});

test("recovery sends only the recovered report", async () => {
  let reads = 0;
  const delivered = [];
  const result = await runHourlyCfo(baseOptions({
    readMoneytreeViaCodex: async () => { reads += 1; if (reads === 1) throw new Error("cfo_moneytree_codex_read_failed:unavailable"); return moneytreeRead(321); },
    recoverMoneytreeRead: undefined,
    deliverCfoTelegram: async (input) => { delivered.push(input.snapshot); return { status: "sent", messageId: 44 }; },
  }));
  assert.equal(reads, 2);
  assert.equal(delivered.length, 1);
  assert.equal(delivered[0].state, "recovered");
  assert.equal(delivered[0].totals.assetsMinor, 321);
  assert.deepEqual(result, { status: "sent", reportingDate: DATE, revision: 1, appended: true, delivered: true, recovered: true });
});

test("provider/config failure has one fixed redacted result", async () => {
  const output = [];
  const result = await main({
    env: { ...ENV, SENTINEL_AMOUNT: "999999", SENTINEL_ACCOUNT: "account-secret" }, uid: UID, chatId: CHAT, now: () => CLOCK, runLocalAgentUsageCollection: async () => undefined,
    readMoneytreeViaCodex: async () => moneytreeRead(100), latestSnapshot: async () => null,
    resolveCfoDailyRun: async () => ({ public_ref: "30000000-0000-4000-8000-000000000001", reporting_date: DATE, run_id: RUN, time_zone: "Asia/Tokyo", created_at: CLOCK.toISOString() }),
    stdout: (line) => output.push(line),
    appendCfoDailySnapshot: async () => { throw new Error("SENTINEL_AMOUNT SENTINEL_ACCOUNT service-role-fixture"); },
  });
  assert.equal(result.exitCode, 1);
  assert.equal(output.length, 1);
  assert.deepEqual(JSON.parse(output[0]), { status: "failed", reportingDate: DATE, revision: null, appended: false, delivered: false, recovered: false, providerBilling: { status: "unavailable", confirmedCount: 0, unresolvedCount: 0, unavailableCount: 1 } });
  assert.doesNotMatch(output[0], /999999|account-secret|service-role-fixture|SENTINEL/i);
});

test("hourly main isolates usage failures and preserves finance", async () => {
  for (const mode of ["partial", "throw", "reject"]) { const calls = [], output = [], delivered = [], sentinel = new Error(`HOSTILE_${mode}`); let now = 0; const options = baseOptions({ env: { ...ENV, LIFE_MANAGER_STATE_HOME: "/tmp/cfo-state", HOSTILE_SECRET: "must-not-pass" }, now: () => { now += 1; return CLOCK; }, runLocalAgentUsageCollection: input => { calls.push(["usage", input]); if (mode === "partial") return { status: "partial", usage_secret: "USAGE_SECRET" }; if (mode === "throw") throw sentinel; return Promise.reject(sentinel); }, readMoneytreeViaCodex: async () => { calls.push(["moneytree"]); return moneytreeRead(100); }, deliverCfoTelegram: async input => { delivered.push(input); return { status: "sent" }; }, stdout: line => output.push(line) }); const result = await main(options);
    assert.deepEqual(calls.map(([name]) => name), ["usage", "moneytree"]); assert.deepEqual(calls[0][1], { env: { LIFE_MANAGER_STATE_HOME: "/tmp/cfo-state" } }); assert.equal(now, 1); assert.deepEqual(result.summary, { status: "sent", reportingDate: DATE, revision: 1, appended: true, delivered: true, recovered: false }); assert.equal(result.exitCode, 0); assert.equal(output.length, 1); assert.deepEqual(JSON.parse(output[0]), { ...result.summary, providerBilling: result.providerBilling }); assert.deepEqual(Object.keys(delivered[0]).sort(), ["chatId", "snapshot", "snapshotPublicRef", "telegramToken", "uid"].sort()); assert.doesNotMatch(JSON.stringify({ result, output, delivered }), /HOSTILE_|USAGE_SECRET/);
  }
});

test("hourly main publishes exact provider counts after usage and before finance", async () => {
  const calls = [], output = [], capture = [], anthropic = [], confirmed = { schema_version: 1, provider: "google_cloud", billing_period: "202607", scope: { kind: "billing_account", ref: "sha256:" + "a".repeat(64) }, amount: { value: "1100", currency: "JPY" }, source: "provider_invoice_pdf", source_document_ref: "sha256:" + "b".repeat(64), observed_at: CLOCK.toISOString(), evidence_status: "provider_billed" };
  const result = await main({ ...baseOptions({ env: { ...ENV, LIFE_MANAGER_STATE_HOME: "/tmp/cfo-hourly-state", GOG_ACCOUNT: "cfo@example.com" }, now: () => { calls.push("clock"); return CLOCK; }, aiCost: { ...AI_COST, amount: "HOSTILE" }, runLocalAgentUsageCollection: async () => calls.push("usage"), makeGogMail: () => ({ findLatestGoogleCloudInvoice: async () => null }), captureLatestGoogleCloudInvoice: async input => { calls.push("billing"); capture.push(input); return { status: "appended", record_id: "sha256:" + "b".repeat(64), confirmed }; }, captureLatestAnthropicSubscriptionReceipt: async input => { calls.push("anthropic"); anthropic.push(input); return anthropicCapture(); }, readMoneytreeViaCodex: async () => { calls.push("finance"); return moneytreeRead(100); }, appendCfoDailySnapshot: async input => { assert.deepEqual(input.moneytreeRead.source, moneytreeRead(100).source); assert.deepEqual(input.report.aiCost, AI_COST); assert.equal("aiCost" in input.moneytreeRead, false); return { public_ref: REF1, reporting_date: DATE, run_id: RUN, revision: 1, created_at: CLOCK.toISOString() }; }, deliverCfoTelegram: async input => { assert.equal("providerBilling" in input, false); assert.deepEqual(input.snapshot.aiCost, AI_COST); assert.doesNotMatch(JSON.stringify(input), /1100|sha256:|cfo@example/); return { status: "sent" }; } }), stdout: line => output.push(line) });
  assert.deepEqual(calls, ["usage", "clock", "billing", "anthropic", "finance"]); assert.equal(capture.length, 1); assert.deepEqual(Object.keys(capture[0]).sort(), ["mail", "observedAt", "stateRoot"]); assert.equal(capture[0].stateRoot, "/tmp/cfo-hourly-state"); assert.equal(capture[0].observedAt, CLOCK.toISOString()); assert.deepEqual(Object.keys(anthropic[0]).sort(), ["mail", "observedAt", "stateRoot"]); assert.deepEqual(anthropicCapture().confirmed, ANTHROPIC_RECEIPT); assert.equal(anthropicCapture().record_id, ANTHROPIC_RECEIPT.source_hash);
  assert.deepEqual(result.providerBilling, { status: "confirmed_unresolved", confirmedCount: 1, unresolvedCount: 1, unavailableCount: 0 }); assert.equal(Object.isFrozen(result.providerBilling), true); assert.deepEqual(Object.keys(result.providerBilling).sort(), ["confirmedCount", "status", "unavailableCount", "unresolvedCount"]); assert.deepEqual(JSON.parse(output[0]), { ...result.summary, providerBilling: result.providerBilling }); assert.doesNotMatch(output[0], /1100|sha256:|cfo@example/);
});

test("hourly main isolates absent, thrown, and malformed provider billing", async () => {
  const cases = [["absent", {}], ["thrown", { GOG_ACCOUNT: "cfo@example.com", captureLatestGoogleCloudInvoice: async () => { throw new Error("HOSTILE_PROVIDER_SECRET"); } }], ["invalid", { GOG_ACCOUNT: "cfo@example.com", captureLatestGoogleCloudInvoice: async () => ({ status: "appended", record_id: "sha256:" + "a".repeat(64), confirmed: { provider: "google_cloud", billing_period: "202613", scope: { kind: "wrong", ref: "sha256:" + "b".repeat(64) }, amount: { value: "999999", currency: "JPY" }, source: "provider_invoice_pdf", source_document_ref: "sha256:" + "a".repeat(64), observed_at: "HOSTILE_TIMESTAMP", evidence_status: "provider_billed", extra: "HOSTILE_EXTRA" } }) }]];
  for (const [name, extra] of cases) { const output = [], delivered = []; const result = await main({ ...baseOptions({ env: { ...ENV, ...extra }, readMoneytreeViaCodex: async () => moneytreeRead(100), deliverCfoTelegram: async input => { delivered.push(input); return { status: "sent" }; }, stdout: line => output.push(line) }), ...extra }); assert.equal(result.exitCode, 0, name); assert.deepEqual(result.summary, { status: "sent", reportingDate: DATE, revision: 1, appended: true, delivered: true, recovered: false }, name); assert.deepEqual(result.providerBilling, { status: "unavailable", confirmedCount: 0, unresolvedCount: 0, unavailableCount: 1 }, name); assert.deepEqual(JSON.parse(output[0]), { ...result.summary, providerBilling: result.providerBilling }); assert.equal(delivered.length, 1); assert.doesNotMatch(output[0] + JSON.stringify(delivered), /HOSTILE|999999|HOSTILE_ID/); }
});

test("ai cost wins, carries through the first next date, and expires", async () => {
  let appended;
  const changed = await runHourlyCfo(baseOptions({ aiCost: AI_COST, latestSnapshot: async () => snapshotRow(REF1, 100), appendCfoDailySnapshotRevision: async input => { appended = input; return { public_ref: REF2, reporting_date: DATE, run_id: RUN, revision: 2, supersedes_revision: 1, created_at: CLOCK.toISOString() }; } }));
  assert.equal(changed.revision, 2); assert.deepEqual(appended.report.aiCost, AI_COST);
  let carry;
  const next = new Date("2026-08-11T03:04:05.000Z"), prior = snapshotWithAi(REF1);
  const carried = await runHourlyCfo(baseOptions({ now: () => next, aiCost: null, latestSnapshot: async () => null, latestAiCost: async () => prior, resolveCfoDailyRun: async () => ({ reporting_date: "2026-08-11", run_id: RUN }), readMoneytreeViaCodex: async () => moneytreeRead(100, next.toISOString()), appendCfoDailySnapshot: async input => { carry = input; return { public_ref: REF2, reporting_date: "2026-08-11", run_id: RUN, revision: 1, created_at: next.toISOString() }; } }));
  assert.equal(carried.revision, 1); assert.deepEqual(carry.report.aiCost, AI_COST);
  const expired = { ...AI_COST, billingPeriodStart: "2026-07-01", billingPeriodEnd: "2026-08-01" };
  const omitted = await runHourlyCfo(baseOptions({ now: () => next, aiCost: null, latestSnapshot: async () => null, latestAiCost: async () => snapshotWithAi(REF1, expired), resolveCfoDailyRun: async () => ({ reporting_date: "2026-08-11", run_id: RUN }), readMoneytreeViaCodex: async () => moneytreeRead(100, next.toISOString()), appendCfoDailySnapshot: async input => { assert.equal("aiCost" in input.report, false); return { public_ref: REF2, reporting_date: "2026-08-11", run_id: RUN, revision: 1, created_at: next.toISOString() }; } }));
  assert.equal(omitted.revision, 1);
});

test("default initial append preserves exact report/source and rejects hostile capture", async () => {
  const requests = [], delivered = [], output = [];
  const result = await runHourlyCfo(baseOptions({ aiCost: AI_COST, latestSnapshot: undefined, appendCfoDailySnapshot: undefined, fetchImpl: async (url, init) => { requests.push({ url, init }); return init.method === "GET" ? { ok: true, status: 200, json: async () => [] } : { ok: true, status: 200, json: async () => ({ public_ref: REF1, reporting_date: DATE, run_id: RUN, revision: 1, created_at: CLOCK.toISOString(), supersedes_revision: null }) }; }, deliverCfoTelegram: async input => { delivered.push(input); return { status: "sent" }; } }));
  assert.equal(result.revision, 1); const payload = JSON.parse(requests.at(-1).init.body); assert.deepEqual(Object.keys(payload).sort(), ["p_report_payload", "p_reporting_date", "p_run_id", "p_source_bundle", "p_uid"].sort()); assert.deepEqual(payload.p_report_payload.aiCost, AI_COST); assert.equal("aiCost" in payload.p_source_bundle, false); assert.deepEqual(delivered[0].snapshot, payload.p_report_payload);
  for (const bad of [() => { throw new Error("HOSTILE"); }, () => anthropicCapture("failed"), () => anthropicCapture("appended", { ...ANTHROPIC_RECEIPT, total: "221.00" }), () => anthropicCapture("appended", { ...ANTHROPIC_RECEIPT, extra: "HOSTILE" }), () => anthropicCapture("appended", { ...ANTHROPIC_RECEIPT, paid_date: "2026-08-09" }), () => anthropicCapture("appended", ANTHROPIC_RECEIPT, "sha256:" + "d".repeat(64))]) {
    const seen = [], output = []; const result = await main({ ...baseOptions({ env: { ...ENV, GOG_ACCOUNT: "cfo@example.com" }, latestSnapshot: async () => snapshotWithAi(REF1), makeGogMail: () => ({ findLatestGoogleCloudInvoice: async () => null }), captureLatestGoogleCloudInvoice: async () => null, captureLatestAnthropicSubscriptionReceipt: bad, aiCost: { ...AI_COST, amount: "HOSTILE" }, deliverCfoTelegram: async input => { seen.push(input); return { status: "sent" }; }, stdout: line => output.push(line) }) });
    assert.equal(result.exitCode, 0); assert.deepEqual(seen[0].snapshot.aiCost, AI_COST); assert.doesNotMatch(JSON.stringify({ result, output, seen }), /HOSTILE|sha256:|cfo@example/);
  }
});
