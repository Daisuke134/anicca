"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "../../../../..");
const { handlePanelApiRequest } = require(path.join(REPO_ROOT, "apps/life-call/lib/panel-api.js"));

const NOW_MS = Date.parse("2026-07-15T12:00:00.000Z");
const EXPECTED_PERIODS = {
  daily: { start_at: "2026-07-08T12:00:00.000Z", end_at: "2026-07-15T12:00:00.000Z" },
  physical: { start_at: "2026-06-15T12:00:00.000Z", end_at: "2026-07-15T12:00:00.000Z" },
  mental: { start_at: "2026-07-08T12:00:00.000Z", end_at: "2026-07-15T12:00:00.000Z" },
  financial: { start_at: "2026-07-01T00:00:00.000Z", end_at: "2026-07-15T12:00:00.000Z" },
};

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function resultResponse() {
  return {
    status: 0,
    body: "",
    headers: {},
    setHeader(name, value) { this.headers[String(name).toLowerCase()] = value; },
    writeHead(status, headers = {}) { this.status = status; Object.assign(this.headers, headers); },
    end(body) { this.body = body || ""; },
  };
}

function outcome(uid, ref) {
  return {
    public_ref: ref,
    revision_key: ref.replace(/^81/, "82"),
    uid,
    organ: "daily",
    entity_key: "shared-entity",
    outcome_kind: "daily_call",
    outcome_status: "required_succeeded",
    occurred_at: "2026-07-14T09:00:00.000Z",
    resolved_at: null,
    recorded_at: "2026-07-14T09:00:00.000Z",
    amount_minor: null,
    currency: null,
    components: {},
  };
}

async function invoke(method, fetchImpl, url = "/api/panel/scores?uid=tenant-b&organ=mental") {
  const req = { url, method, headers: { cookie: "lm_panel_session=proof-session" } };
  const res = resultResponse();
  await handlePanelApiRequest(req, res, {
    supaUrl: "https://proof.invalid",
    supaKey: "synthetic-proof-key",
    fetchImpl,
    nowMs: NOW_MS,
    sessionScopeImpl: async () => ({ uid: "tenant-a", chatId: "proof-chat" }),
  });
  return { status: res.status, headers: res.headers, body: JSON.parse(res.body) };
}

async function main() {
  const calls = [];
  const fetchImpl = async (input, init = {}) => {
    const url = new URL(input);
    calls.push({ url, init });
    if (url.pathname.endsWith("/lm_panel_preferences")) return response([{ call_time_zone: "UTC" }]);
    if (url.pathname.endsWith("/rpc/lm_panel_score_outcome_snapshot")) {
      return response({
        overflow: false,
        rows_by_organ: {
          daily: [
            outcome("tenant-a", "81000000-0000-4000-8000-000000000001"),
            outcome("tenant-b", "81000000-0000-4000-8000-000000000002"),
          ],
          physical: [],
          mental: [],
          financial: [],
        },
      });
    }
    throw new Error(`unexpected request ${url.pathname}`);
  };

  const getResult = await invoke("GET", fetchImpl);
  assert.equal(getResult.status, 200);
  assert.deepEqual(Object.keys(getResult.body.organs), ["daily", "physical", "mental", "financial"]);
  assert.deepEqual(getResult.body.organs.daily.source_outcome_ids, ["outcome:81000000-0000-4000-8000-000000000001"]);
  assert.equal(getResult.body.organs.daily.denominator, 1);

  const rpcCalls = calls.filter(({ url }) => url.pathname.endsWith("/rpc/lm_panel_score_outcome_snapshot"));
  assert.equal(rpcCalls.length, 1);
  assert.equal(rpcCalls[0].init.method, "POST");
  assert.equal(rpcCalls[0].url.search, "");
  assert.equal(rpcCalls[0].init.headers["content-type"], "application/json");
  const body = JSON.parse(rpcCalls[0].init.body);
  assert.deepEqual(Object.keys(body), ["p_uid", "p_periods"]);
  assert.equal(body.p_uid, "tenant-a");
  assert.deepEqual(body.p_periods, EXPECTED_PERIODS);
  assert.doesNotMatch(JSON.stringify(rpcCalls.map(({ url, init }) => ({ url: url.toString(), body: init.body }))), /tenant-b|uid=eq|organ=eq|occurred_at=gte|occurred_at=lt/);

  for (const method of ["POST", "PUT", "DELETE"]) {
    let effects = 0;
    const denied = await invoke(method, async () => { effects += 1; return response({}); });
    assert.equal(denied.status, 405, method);
    assert.deepEqual(denied.body, { error: "method_not_allowed" }, method);
    assert.equal(effects, 0, `${method}.effects`);
  }

  const overflow = await invoke("GET", async (input) => {
    const url = new URL(input);
    if (url.pathname.endsWith("/lm_panel_preferences")) return response([{ call_time_zone: "UTC" }]);
    if (url.pathname.endsWith("/rpc/lm_panel_score_outcome_snapshot")) return response({ overflow: true, rows_by_organ: {} });
    throw new Error(`unexpected request ${url.pathname}`);
  });
  assert.equal(overflow.status, 503);
  assert.deepEqual(overflow.body, { error: "score_data_unavailable", reason: "source_outcome_limit" });

  console.log("PROP-004 PASS endpoint_cases=5 exact_snapshot_rpc_calls=1 forged_tenant_rows_excluded=1 denied_methods=3 overflow_fail_closed=1 supporting_postgres_required=true");
}

main().catch((error) => {
  console.error(`PROP-004 FAIL ${error.stack || error.message}`);
  process.exitCode = 1;
});
