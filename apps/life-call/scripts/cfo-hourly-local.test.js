"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), os = require("node:os"), path = require("node:path");
const { SpanKind, SpanStatusCode } = require("@opentelemetry/api");
const { deriveMoneytreeState, composeMoneytreeRead } = require("../lib/cfo-moneytree-state.js");
const { buildCfoDailyReport } = require("../lib/cfo-daily-snapshot.js");
const { buildCfoDailyReportFromRecovery } = require("../lib/cfo-recovery-snapshot.js");
const { renderCfoTelegram } = require("../lib/cfo-telegram.js");
const { runHourlyCfo, main } = require("./cfo-hourly-local.js");
const { captureLocalAgentUsageCollection } = require("../lib/cfo-local-agent-usage-span.js");

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
  return { public_ref: publicRef, reporting_date: DATE, run_id: RUN, revision, report_payload: report };
}
function reordered(value) { if (Array.isArray(value)) return value.map(reordered); if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).reverse().map((key) => [key, reordered(value[key])])); return value; }

function baseOptions(overrides = {}) {
  return {
    env: ENV, uid: UID, chatId: CHAT, now: () => CLOCK, runLocalAgentUsageCollection: async () => undefined, captureLocalAgentUsageCollection: async () => undefined, captureLocalAgentUsageCollection: async () => undefined,
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
  assert.equal(requests.length, 2);
  assert.match(requests[0].url, /\/rest\/v1\/lm_cfo_daily_snapshots\?/);
  assert.match(requests[1].url, /\/rest\/v1\/rpc\/lm_append_cfo_daily_snapshot_revision$/);
  const payload = JSON.parse(requests[1].init.body);
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
  const persisted = { public_ref: REF1, reporting_date: DATE, run_id: RUN, revision: 1, report_payload: reordered(buildCfoDailyReportFromRecovery({ revision: 1, recovery: actionRecovery("provider_outage") }).report) }; let append = 0; let deliver = 0; let deliveredInput;
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
  assert.equal(delivered[0].state, "partial");
  assert.equal(delivered[0].totals.assetsMinor, 321);
  assert.deepEqual(result, { status: "sent", reportingDate: DATE, revision: 1, appended: true, delivered: true, recovered: true });
});

test("provider/config failure has one fixed redacted result", async () => {
  const output = [];
  const result = await main({
    env: { ...ENV, SENTINEL_AMOUNT: "999999", SENTINEL_ACCOUNT: "account-secret" }, uid: UID, chatId: CHAT, now: () => CLOCK, runLocalAgentUsageCollection: async () => undefined, captureLocalAgentUsageCollection: async () => undefined,
    readMoneytreeViaCodex: async () => moneytreeRead(100), latestSnapshot: async () => null,
    resolveCfoDailyRun: async () => ({ public_ref: "30000000-0000-4000-8000-000000000001", reporting_date: DATE, run_id: RUN, time_zone: "Asia/Tokyo", created_at: CLOCK.toISOString() }),
    stdout: (line) => output.push(line),
    appendCfoDailySnapshot: async () => { throw new Error("SENTINEL_AMOUNT SENTINEL_ACCOUNT service-role-fixture"); },
  });
  assert.equal(result.exitCode, 1);
  assert.equal(output.length, 1);
  assert.deepEqual(JSON.parse(output[0]), { status: "failed", reportingDate: DATE, revision: null, appended: false, delivered: false, recovered: false });
  assert.doesNotMatch(output[0], /999999|account-secret|service-role-fixture|SENTINEL/i);
});

test("local usage span rejects an undefined accessor before effects", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "cfo-span-accessor-"));
  try { const accessorEnv = {}; Object.defineProperty(accessorEnv, "LIFE_MANAGER_STATE_HOME", { enumerable: true, get: undefined, set: undefined }); let calls = 0; await assert.rejects(() => captureLocalAgentUsageCollection(() => { calls += 1; }, { env: accessorEnv }), error => error.message === "cfo_local_agent_usage_span_failed:invalid_input"); assert.equal(calls, 0); assert.equal(fs.existsSync(path.join(root, "telemetry")), false); } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test("local usage span writes one content-free line and fixed failures", async t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "cfo-local-agent-span-")), target = path.join(root, "telemetry", "cfo-local-agent-usage-otel-spans.jsonl"), id = "a".repeat(64), source = (sourceId, status, recordId, byteOffset, eventCount, mappingId, coverage) => ({ source_id: sourceId, status, record_id: recordId, byte_offset: byteOffset, event_count: eventCount, mapping_id: mappingId, coverage_exceptions: coverage });
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const input = { env: { LIFE_MANAGER_STATE_HOME: root } }, complete = { status: "complete", collected_at: "2026-08-11T01:02:03.000Z", sources: [source("life_manager_agent_usage", "published", id, 7, 2, "local_agent_usage_v1", []), source("anicca_agent_usage", "published", "b".repeat(64), 9, 3, "local_agent_usage_v1", [])], coverage_exceptions: [] }, partial = { status: "partial", collected_at: complete.collected_at, sources: [complete.sources[0], source("anicca_agent_usage", "unavailable", null, null, null, null, ["source_unreadable"])], coverage_exceptions: ["source_unreadable"] }, read = () => fs.readFileSync(target, "utf8").trimEnd().split("\n").filter(Boolean).map(JSON.parse), logs = { count: 0 }, originals = [console.log, console.error, console.warn];
  [console.log, console.error, console.warn] = [() => { logs.count += 1; }, () => { logs.count += 1; }, () => { logs.count += 1; }];
  try {
    let calls = 0; const returned = await captureLocalAgentUsageCollection(value => { calls += 1; assert.strictEqual(value, input); return complete; }, input); assert.strictEqual(returned, complete); assert.equal(calls, 1);
    let lines = read(); assert.equal(lines.length, 1); assert.deepEqual(lines[0].attributes, {"cfo.operation.name":"local_agent_usage.collect","cfo.usage.collection.status":"complete","cfo.usage.collection.collected_at":complete.collected_at,"cfo.usage.collection.source_count":2,"cfo.usage.collection.coverage_exception_count":0,"cfo.usage.source.life_manager_agent_usage.status":"published","cfo.usage.source.life_manager_agent_usage.record_id":id,"cfo.usage.source.life_manager_agent_usage.byte_offset":7,"cfo.usage.source.life_manager_agent_usage.event_count":2,"cfo.usage.source.life_manager_agent_usage.mapping_id":"local_agent_usage_v1","cfo.usage.source.anicca_agent_usage.status":"published","cfo.usage.source.anicca_agent_usage.record_id":"b".repeat(64),"cfo.usage.source.anicca_agent_usage.byte_offset":9,"cfo.usage.source.anicca_agent_usage.event_count":3,"cfo.usage.source.anicca_agent_usage.mapping_id":"local_agent_usage_v1"}); assert.deepEqual(Object.keys(lines[0]).sort(), ["attributes", "kind", "name", "schema_version", "span_id", "status_code", "trace_id"].sort()); assert.equal(lines[0].kind, SpanKind.INTERNAL); assert.equal(lines[0].status_code, SpanStatusCode.UNSET); assert.match(lines[0].trace_id, /^(?!0{32})[0-9a-f]{32}$/); assert.match(lines[0].span_id, /^(?!0{16})[0-9a-f]{16}$/); assert.equal(lines[0].attributes["cfo.usage.source.life_manager_agent_usage.byte_offset"], 7); assert.equal(lines[0].attributes["cfo.usage.source.anicca_agent_usage.event_count"], 3); assert.equal(lines[0].attributes["cfo.usage.collection.coverage_exception_count"], 0); assert.equal(lines[0].attributes["cfo.usage.collection.coverage_exceptions"], undefined); assert.doesNotMatch(JSON.stringify(lines[0]), /TOKEN_SENTINEL|PROMPT_SENTINEL|SECRET_SENTINEL|HOSTILE|receipt_extra/i); assert.equal(JSON.stringify(lines[0]).includes(root), false);
    const partialReturned = await captureLocalAgentUsageCollection(() => partial, input); assert.strictEqual(partialReturned, partial); lines = read(); assert.equal(lines.length, 2); assert.equal(lines[1].status_code, SpanStatusCode.ERROR); assert.equal(lines[1].attributes["error.type"], "collection_partial"); assert.deepEqual(lines[1].attributes["cfo.usage.collection.coverage_exceptions"], ["source_unreadable"]);
    const thrown = new Error("HOSTILE_THROW_TOKEN"); await assert.rejects(() => captureLocalAgentUsageCollection(() => { throw thrown; }, input), error => error.message === "cfo_local_agent_usage_span_failed:collection"); lines = read(); assert.equal(lines.length, 3); assert.equal(lines[2].status_code, SpanStatusCode.ERROR); assert.equal(lines[2].attributes["error.type"], "collection_failed"); assert.doesNotMatch(JSON.stringify(lines), /HOSTILE_THROW_TOKEN/);
    fs.unlinkSync(target); fs.mkdirSync(target, { recursive: true }); let getterReads = 0; const invalid = { ...complete, extra: "HOSTILE_RECEIPT_EXTRA", sources: complete.sources.slice() }; Object.defineProperty(invalid.sources, "array_extra", { value: "HOSTILE_ARRAY_EXTRA", enumerable: true }); Object.defineProperty(invalid, "getter", { enumerable: true, get: () => { getterReads += 1; throw new Error("HOSTILE_GETTER"); } });
    const exportErrors = []; for (const collect of [() => { throw new Error("HOSTILE_COLLECT"); }, () => invalid]) await assert.rejects(() => captureLocalAgentUsageCollection(collect, input), error => { exportErrors.push(error.message); return /^cfo_local_agent_usage_span_failed:export$/.test(error.message); }); assert.equal(getterReads, 0); assert.equal(fs.statSync(target).isDirectory(), true); assert.equal(logs.count, 0); assert.doesNotMatch(JSON.stringify({ lines, exportErrors, logs }), /HOSTILE|TOKEN|SECRET/i);
  } finally { [console.log, console.error, console.warn] = originals; }
});

test("hourly main isolates usage failures and preserves finance", async () => {
  for (const mode of ["partial", "throw", "reject"]) { const calls = [], output = [], delivered = [], sentinel = new Error(`HOSTILE_${mode}`); let now = 0; const usage = input => { calls.push(["usage", input]); if (mode === "partial") return { status: "partial", usage_secret: "USAGE_SECRET" }; if (mode === "throw") throw sentinel; return Promise.reject(sentinel); }; const options = baseOptions({ env: { ...ENV, LIFE_MANAGER_STATE_HOME: "/tmp/cfo-state", HOSTILE_SECRET: "must-not-pass" }, now: () => { now += 1; return CLOCK; }, runLocalAgentUsageCollection: usage, captureLocalAgentUsageCollection: async (selected, input) => { calls.push(["capture", selected, input]); return selected(input); }, readMoneytreeViaCodex: async () => { calls.push(["moneytree"]); return moneytreeRead(100); }, deliverCfoTelegram: async input => { delivered.push(input); return { status: "sent" }; }, stdout: line => output.push(line) }); const result = await main(options);
    assert.deepEqual(calls.map(([name]) => name), ["capture", "usage", "moneytree"]); assert.strictEqual(calls[0][1], usage); assert.deepEqual(calls[0][2], { env: { LIFE_MANAGER_STATE_HOME: "/tmp/cfo-state" } }); assert.deepEqual(calls[1][1], { env: { LIFE_MANAGER_STATE_HOME: "/tmp/cfo-state" } }); assert.equal(now, 1); assert.deepEqual(result.summary, { status: "sent", reportingDate: DATE, revision: 1, appended: true, delivered: true, recovered: false }); assert.equal(result.exitCode, 0); assert.equal(output.length, 1); assert.deepEqual(JSON.parse(output[0]), result.summary); assert.deepEqual(Object.keys(delivered[0]).sort(), ["chatId", "snapshot", "snapshotPublicRef", "telegramToken", "uid"].sort()); assert.doesNotMatch(JSON.stringify({ result, output, delivered }), /HOSTILE_|USAGE_SECRET/);
  }
});
