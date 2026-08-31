"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { handlePanelApiRequest } = require("./panel-api.js");

const NOW = Date.parse("2026-07-15T12:00:00.000Z");

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function resultRes() {
  return {
    status: 0, headers: {}, body: "",
    setHeader(name, value) { this.headers[String(name).toLowerCase()] = value; },
    writeHead(status, headers = {}) { this.status = status; Object.assign(this.headers, headers); },
    end(body) { this.body = body || ""; },
  };
}

async function request(fetchImpl, url = "/api/panel/scores?uid=tenant-b") {
  const req = { url, method: "GET", headers: { cookie: "lm_panel_session=safe-session" } };
  const res = resultRes();
  await handlePanelApiRequest(req, res, {
    supaUrl: "https://db.example", supaKey: "service-key", fetchImpl, nowMs: NOW,
    sessionScopeImpl: async () => ({ uid: "tenant-a", chatId: "101" }),
  });
  return { status: res.status, body: JSON.parse(res.body) };
}

function snapshotRows() {
  return {
    overflow: false,
    rows_by_organ: {
      daily: [{
        public_ref: "10000000-0000-4000-8000-000000000001", revision_key: "20000000-0000-4000-8000-000000000001",
        uid: "tenant-a", organ: "daily", entity_key: "event-1", outcome_kind: "daily_call", outcome_status: "required_succeeded",
        occurred_at: "2026-07-14T09:00:00.000Z", resolved_at: null, recorded_at: "2026-07-14T09:00:00.000Z", amount_minor: null, currency: null, components: {},
      }],
      physical: [], mental: [], financial: [],
    },
  };
}

test("score endpoint makes one exact authenticated snapshot RPC and returns all four closed organs", async () => {
  const calls = [];
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(input); calls.push({ url, init });
    if (url.pathname.endsWith("/lm_panel_preferences")) return response([{ call_time_zone: "UTC" }]);
    if (url.pathname.endsWith("/rpc/lm_panel_score_outcome_snapshot")) return response(snapshotRows());
    throw new Error(`unexpected ${url}`);
  };
  const actual = await request(fetchImpl);
  assert.equal(actual.status, 200);
  assert.deepEqual(Object.keys(actual.body.organs), ["daily", "physical", "mental", "financial"]);
  assert.deepEqual({ status: actual.body.organs.daily.status, value: actual.body.organs.daily.value, numerator: actual.body.organs.daily.numerator, denominator: actual.body.organs.daily.denominator }, { status: "measured", value: 100, numerator: 1, denominator: 1 });
  assert.equal(actual.body.organs.mental.status, "insufficient_data");
  const rpcCalls = calls.filter(({ url }) => url.pathname.endsWith("/rpc/lm_panel_score_outcome_snapshot"));
  assert.equal(rpcCalls.length, 1);
  assert.equal(rpcCalls[0].init.method, "POST");
  assert.equal(rpcCalls[0].url.search, "");
  const rpcBody = JSON.parse(rpcCalls[0].init.body);
  assert.equal(rpcBody.p_uid, "tenant-a");
  assert.deepEqual(Object.keys(rpcBody), ["p_uid", "p_periods"]);
  assert.deepEqual(Object.keys(rpcBody.p_periods), ["daily", "physical", "mental", "financial"]);
  for (const period of Object.values(rpcBody.p_periods)) assert.deepEqual(Object.keys(period), ["start_at", "end_at"]);
  assert.doesNotMatch(JSON.stringify(rpcCalls), /tenant-b|uid=eq|organ=eq|occurred_at=gte|occurred_at=lt/);
});

test("score endpoint maps missing outcome storage and overflow to exact fail-closed 503 responses", async () => {
  for (const fixture of [
    { rpc: response({ code: "42P01" }, 404), reason: "source_table_unavailable" },
    { rpc: response({ overflow: true, rows_by_organ: {} }), reason: "source_outcome_limit" },
    { rpc: response({ overflow: false, rows_by_organ: { daily: "not-an-array", physical: [], mental: [], financial: [] } }), reason: "source_table_unavailable" },
  ]) {
    const fetchImpl = async (input) => {
      const url = new URL(input);
      if (url.pathname.endsWith("/lm_panel_preferences")) return response([{ call_time_zone: "UTC" }]);
      if (url.pathname.endsWith("/rpc/lm_panel_score_outcome_snapshot")) return fixture.rpc;
      throw new Error(`unexpected ${url}`);
    };
    const actual = await request(fetchImpl);
    assert.equal(actual.status, 503);
    assert.deepEqual(actual.body, { error: "score_data_unavailable", reason: fixture.reason });
    assert.equal(actual.body.organs, undefined);
  }
});

test("score endpoint is GET-only and executes no mutation/provider path", async () => {
  let called = 0;
  const req = { url: "/api/panel/scores", method: "POST", headers: { cookie: "lm_panel_session=safe" } };
  const res = resultRes();
  await handlePanelApiRequest(req, res, { sessionScopeImpl: async () => ({ uid: "tenant-a", chatId: "101" }), fetchImpl: async () => { called += 1; return response([]); } });
  assert.equal(res.status, 405);
  assert.deepEqual(JSON.parse(res.body), { error: "method_not_allowed" });
  assert.equal(called, 0);
});
