"use strict";

const assert = require("node:assert/strict");
const fixture = require("./score-semantics-cases.json");
const { buildScorePeriods, computePanelScores } = require("../lib/panel-score-semantics.js");
const { handlePanelApiRequest } = require("../lib/panel-api.js");
const { renderScoreCards } = require("../lib/panel-ui.js");

function uuid(n, prefix) {
  return `${prefix || "00000000"}-0000-4000-8000-${String(n).padStart(12, "0")}`;
}

function expandRow(row, organ) {
  const at = row.at;
  return {
    public_ref: uuid(row.n, "10000000"),
    revision_key: uuid(row.n, "20000000"),
    uid: row.uid || fixture.tenant,
    organ,
    entity_key: row.entity,
    outcome_kind: row.kind,
    outcome_status: row.status,
    occurred_at: at,
    resolved_at: row.resolved == null ? null : row.resolved,
    recorded_at: row.recorded || at,
    amount_minor: row.amount == null ? null : row.amount,
    currency: row.currency == null ? null : row.currency,
    components: row.components || {},
  };
}

function runCase(testCase) {
  const periods = buildScorePeriods(Date.parse(fixture.defaultNow), fixture.defaultTimeZone);
  for (const variant of [testCase, ...(testCase.variants || []).map((item) => ({ ...item, organ: testCase.organ }))]) {
    const rows = variant.rows.map((row) => expandRow(row, variant.organ));
    const rowsByOrgan = { uid: fixture.tenant, daily: [], physical: [], mental: [], financial: [] };
    rowsByOrgan[variant.organ] = rows;
    const actual = computePanelScores(rowsByOrgan, periods, fixture.defaultTimeZone)[variant.organ];
    const expected = variant.expected;
    for (const key of ["status", "value", "numerator", "denominator"]) {
      assert.deepEqual(actual[key], expected[key], `${variant.id}.${key}`);
    }
    if (expected.reason) assert.equal(actual.reason, expected.reason, `${variant.id}.reason`);
    else assert.ok(actual.reason && !/[{}]/.test(actual.reason), `${variant.id}.reason`);
    assert.equal(actual.source_outcome_ids.length, expected.sourceCount, `${variant.id}.sourceCount`);
    assert.deepEqual(actual.source_outcome_ids, actual.source_outcome_ids.slice().sort(), `${variant.id}.sourceOrder`);
    for (const [key, value] of Object.entries(expected.components || {})) {
      assert.deepEqual(actual.components[key], value, `${variant.id}.components.${key}`);
    }
  }
}

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function resultRes() {
  return {
    status: 0, body: "", headers: {},
    setHeader(name, value) { this.headers[String(name).toLowerCase()] = value; },
    writeHead(status, headers = {}) { this.status = status; Object.assign(this.headers, headers); },
    end(body) { this.body = body || ""; },
  };
}

async function apiFailureCase(testCase, nowMs = Date.parse(fixture.defaultNow)) {
  const req = { url: "/api/panel/scores", method: "GET", headers: { cookie: "lm_panel_session=fixed-eval" } };
  const res = resultRes();
  const fetchImpl = async (input) => {
    const url = new URL(input);
    if (url.pathname.endsWith("/lm_panel_preferences")) return response([{ call_time_zone: fixture.defaultTimeZone }]);
    if (url.pathname.endsWith("/rpc/lm_panel_score_outcome_snapshot")) return response(testCase.rpcBody, testCase.rpcStatus);
    throw new Error(`unexpected fixed-eval request ${url.pathname}`);
  };
  await handlePanelApiRequest(req, res, {
    supaUrl: "https://fixed.invalid", supaKey: "fixed-eval", fetchImpl, nowMs,
    sessionScopeImpl: async () => ({ uid: fixture.tenant, chatId: "fixed-eval" }),
  });
  const body = JSON.parse(res.body);
  assert.equal(res.status, testCase.expectedStatus, `${testCase.id}.status`);
  assert.deepEqual(body, { error: "score_data_unavailable", reason: testCase.expectedReason }, `${testCase.id}.body`);
}

async function runContractCase(testCase) {
  if (testCase.type === "api") return apiFailureCase(testCase);
  if (testCase.type === "period_failure") return apiFailureCase(testCase, Number.NaN);
  if (testCase.type === "ui_rejection") {
    const invalid = { status: "insufficient_data", value: null, numerator: 0, denominator: 0, reason: "No outcomes.", period: { kind: "anything", start_at: "2026-07-08T12:00:00.000Z", end_at: "2026-07-15T12:00:00.000Z" }, source_outcome_ids: ["outcome:------------------------------------"], components: { timezone: "UTC" } };
    assert.throws(() => renderScoreCards({ organs: { daily: invalid, physical: invalid, mental: invalid, financial: invalid } }), /invalid score payload/, testCase.id);
    return;
  }
  if (testCase.type === "snapshot_membership") {
    const periods = buildScorePeriods(Date.parse(fixture.defaultNow), fixture.defaultTimeZone);
    const source = [expandRow({ n: 940, entity: "snapshot-event", kind: "daily_call", status: "required_succeeded", at: "2026-07-14T09:00:00.000Z" }, "daily")];
    const captured = source.slice();
    source.push(expandRow({ n: 941, entity: "snapshot-event", kind: "daily_call", status: "required_failed", at: "2026-07-14T09:00:00.000Z", recorded: "2026-07-14T10:00:00.000Z" }, "daily"));
    const actual = computePanelScores({ uid: fixture.tenant, daily: captured, physical: [], mental: [], financial: [] }, periods, fixture.defaultTimeZone).daily;
    assert.equal(actual.source_outcome_ids.length, testCase.expectedSourceCount, `${testCase.id}.sourceCount`);
    assert.equal(actual.value, testCase.expectedValue, `${testCase.id}.value`);
    return;
  }
  throw new Error(`unknown contract case ${testCase.id}`);
}

async function main() {
  let passed = 0;
  for (const periodCase of fixture.periodCases) {
    const periods = buildScorePeriods(Date.parse(periodCase.now), periodCase.timeZone);
    for (const [organ, [startAt, endAt]] of Object.entries(periodCase.expected)) {
      assert.equal(periods[organ].start_at, startAt, `${periodCase.id}.${organ}.start_at`);
      assert.equal(periods[organ].end_at, endAt, `${periodCase.id}.${organ}.end_at`);
    }
    if (periodCase.effectiveTimeZone) assert.equal(periods.timezone, periodCase.effectiveTimeZone);
    passed += 1;
  }
  for (const testCase of fixture.scoreCases) {
    runCase(testCase);
    passed += 1;
  }
  for (const testCase of fixture.contractCases) {
    await runContractCase(testCase);
    passed += 1;
  }
  const total = fixture.periodCases.length + fixture.scoreCases.length + fixture.contractCases.length;
  console.log(`Score semantics eval: ${passed}/${total} (100.0%) judge=deterministic`);
}

main().catch((error) => {
  console.error(`Score semantics eval failed: ${error.message}`);
  process.exitCode = 1;
});
