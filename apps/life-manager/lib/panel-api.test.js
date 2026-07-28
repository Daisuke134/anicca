"use strict";

const test = require("node:test");
const assert = require("node:assert");
const crypto = require("node:crypto");
const http = require("node:http");

let handlePanelApiRequest = async (_req, res) => {
  res.writeHead(501, { "content-type": "application/json" });
  res.end(JSON.stringify({ error: "panel API not implemented" }));
};
try {
  ({ handlePanelApiRequest } = require("./panel-api.js"));
} catch (error) {
  if (error.code !== "MODULE_NOT_FOUND") throw error;
}

const NOW = Date.parse("2026-07-21T12:00:00.000Z");
const SESSION = Buffer.alloc(32, 0x88).toString("base64url");
const SESSION_HASH = crypto.createHash("sha256").update(SESSION).digest("hex");

function jsonResponse(rows, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => rows };
}

function makeFixture() {
  const calls = [];
  const calendarUids = [];
  const byUid = {
    u1: {
      user: {
        uid: "u1", call_language: "ja", wake_policy: "travel-only",
        calendar_provider: "composio_gcal", gmail_account_id: null,
        telegram_chat_id: "101", payout_destination: null,
        agent_wallet_address: "0x477EeE969ccfdc0e959F38cE8B83e372FC0262ad",
      },
      location: {
        uid: "u1", latitude: 35.0, longitude: 139.0,
        observed_at: "2026-07-21T11:00:00.000Z", expires_at: "2026-07-21T13:00:00.000Z",
      },
      wakes: [
        { uid: "u1", event_key: "evt-u1|10", called_at: "2026-07-21T08:50:00.000Z", answered_at: "2026-07-21T08:50:10.000Z" },
        { uid: "u1", event_key: "evt-u1|5", called_at: "2026-07-21T08:55:00.000Z", answered_at: null },
      ],
      costs: [
        { uid: "u1", ts: "2026-07-21T08:50:00.000Z", kind: "telnyx_call", quantity: 60, unit: "seconds", est_usd: 0.12 },
        { uid: "u1", ts: "2026-07-21T09:00:00.000Z", kind: "gemini_audio", quantity: 1, unit: "call", est_usd: 0.3 },
      ],
      earnings: [
        {
          entry_key: "pm:loss", kind: "financial_realized_loss", amount_minor: 315,
          currency: "USD", occurred_at: "2026-07-21T10:00:00.000Z",
          tx_hash: null, source: "polymarket", meta: {},
        },
      ],
      receipts: [
        {
          report_kind: "daily", period_key: "2026-07-21", status: "sent",
          snapshot_hash: "a".repeat(64), telegram_message_id: 71,
          period_end: "2026-07-21T11:00:00.000Z",
          snapshot: {
            kind: "daily", period_key: "2026-07-21",
            gross_usd_micros: "0", realized_loss_usd_micros: "0",
            financial_fee_usd_micros: "0", api_cost_usd_micros: "420000",
            operating_net_usd_micros: "-420000", balance_usdc_atomic: "0",
            distributable_usdc_atomic: "0", self_funded_bps: 0,
            stop_reason: "no_external_income", rail_pnl: [],
          },
        },
        {
          report_kind: "weekly", period_key: "2026-W30", status: "sent",
          snapshot_hash: "b".repeat(64), telegram_message_id: 72,
          period_end: "2026-07-20T11:05:00.000Z",
          snapshot: {
            kind: "weekly", period_key: "2026-W30",
            gross_usd_micros: "0", realized_loss_usd_micros: "3150000",
            financial_fee_usd_micros: "0", api_cost_usd_micros: "0",
            operating_net_usd_micros: "-3150000", balance_usdc_atomic: "0",
            distributable_usdc_atomic: "0", self_funded_bps: 0,
            stop_reason: "negative_net",
            rail_pnl: [{ rail: "CAPITAL", net_usd_micros: "-3150000" }],
          },
        },
      ],
    },
    u2: {
      user: { uid: "u2", call_language: "en", calendar_provider: "secret", telegram_chat_id: "202" },
      location: { uid: "u2", expires_at: "2026-07-22T00:00:00.000Z" },
      wakes: [{ uid: "u2", event_key: "secret-u2", called_at: "2026-07-21T09:00:00.000Z", answered_at: "2026-07-21T09:00:01.000Z" }],
      costs: [{ uid: "u2", ts: "2026-07-21T09:00:00.000Z", kind: "secret-u2", quantity: 999, unit: "secret", est_usd: 999 }],
    },
  };

  const fetchImpl = async (input, init = {}) => {
    const url = new URL(input);
    calls.push({ url, init });
    if (url.pathname.endsWith("/rpc/resolve_lm_panel_session")) {
      const body = JSON.parse(init.body);
      return jsonResponse(body.p_session_hash === SESSION_HASH ? [{ uid: "u1", chat_id: "101", rotated: false }] : []);
    }
    if (url.pathname.endsWith("/lm_panel_sessions")) {
      return jsonResponse(url.searchParams.get("session_hash") === `eq.${SESSION_HASH}` ? [{ uid: "u1", chat_id: "101" }] : []);
    }
    if (url.pathname.endsWith("/rpc/lm_panel_score_outcome_snapshot")) {
      const request = JSON.parse(init.body);
      return jsonResponse({ overflow: false, rows_by_organ: {
        daily: request.p_uid === "u1" ? [{
          public_ref: "10000000-0000-4000-8000-000000000001", revision_key: "20000000-0000-4000-8000-000000000001",
          uid: "u1", organ: "daily", entity_key: "evt-u1", outcome_kind: "daily_call", outcome_status: "required_succeeded",
          occurred_at: "2026-07-21T08:50:00.000Z", resolved_at: null, recorded_at: "2026-07-21T08:50:00.000Z", amount_minor: null, currency: null, components: {},
        }] : [], physical: [], mental: [], financial: [],
      } });
    }
    const uid = String(url.searchParams.get("uid") || "").replace(/^eq\./, "");
    const fixture = byUid[uid];
    if (url.pathname.endsWith("/lm_users")) return jsonResponse(fixture ? [fixture.user] : []);
    if (url.pathname.endsWith("/lm_panel_preferences")) return jsonResponse(uid === "u1" ? [{ call_time_zone: "UTC" }] : []);
    if (url.pathname.endsWith("/lm_user_locations")) return jsonResponse(fixture ? [fixture.location] : []);
    if (url.pathname.endsWith("/lm_wake_log")) return jsonResponse(fixture ? fixture.wakes : []);
    if (url.pathname.endsWith("/lm_api_cost")) return jsonResponse(fixture ? fixture.costs : []);
    if (url.pathname.endsWith("/lm_agent_earnings")) {
      const wallet = String(url.searchParams.get("wallet_address") || "").replace(/^eq\./, "");
      return jsonResponse(wallet === byUid.u1.user.agent_wallet_address ? byUid.u1.earnings : []);
    }
    if (url.pathname.endsWith("/lm_financial_report_receipts")) return jsonResponse(fixture ? fixture.receipts : []);
    throw new Error(`unexpected fixture URL ${url}`);
  };
  const calendar = {
    listEventsRaw: async (uid) => {
      calendarUids.push(uid);
      return uid === "u1" ? [{
        id: "evt-u1", summary: "Dentist", location: "Clinic",
        start: { dateTime: "2026-07-21T14:00:00.000Z", timeZone: "UTC" },
        end: { dateTime: "2026-07-21T15:00:00.000Z", timeZone: "UTC" },
      }] : [{ id: "secret-u2", summary: "secret-u2", start: { dateTime: "2026-07-21T14:00:00.000Z" } }];
    },
  };
  return { calls, calendarUids, fetchImpl, calendar, byUid };
}

async function withApiServer(fixture, run) {
  const server = http.createServer((req, res) => {
    Promise.resolve(handlePanelApiRequest(req, res, {
      supaUrl: "https://db.example",
      supaKey: "service-key",
      fetchImpl: fixture.fetchImpl,
      calendar: fixture.calendar,
      nowMs: NOW,
      timeZone: "UTC",
    })).catch((error) => {
      res.writeHead(500, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: error.message }));
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    return await run(`http://127.0.0.1:${server.address().port}`);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

async function getJson(base, endpoint, init = {}) {
  const response = await fetch(`${base}/api/panel/${endpoint}${init.query || ""}`, {
    method: init.method || "GET",
    headers: init.session === false ? {} : { Cookie: `lm_panel_session=${SESSION}` },
  });
  return { response, body: await response.json() };
}

test("LM-33b timeline returns today's interpreted calendar and call telemetry", async () => {
  const fixture = makeFixture();
  await withApiServer(fixture, async (base) => {
    const { response, body } = await getJson(base, "timeline");
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.deepEqual(body, {
      date: "2026-07-21", timezone: "UTC",
      items: [
        { sentence: "14:00開始の予定です。詳細はカレンダーで確認してください。", status: "カレンダーで確認" },
        { sentence: "08:50の電話は応答済みです。", status: "応答済み" },
        { sentence: "08:55の電話は未応答です。", status: "未応答" },
      ],
    });
  });
  assert.deepEqual(fixture.calendarUids, ["u1"]);
});

test("PANEL-8g scores use source outcomes and expose all four closed organs", async () => {
  await withApiServer(makeFixture(), async (base) => {
    const { response, body } = await getJson(base, "scores");
    assert.equal(response.status, 200);
    assert.deepEqual(Object.keys(body.organs), ["daily", "physical", "mental", "financial"]);
    assert.deepEqual({ status: body.organs.daily.status, value: body.organs.daily.value, numerator: body.organs.daily.numerator, denominator: body.organs.daily.denominator }, { status: "measured", value: 100, numerator: 1, denominator: 1 });
    assert.equal(body.organs.physical.status, "insufficient_data");
    assert.equal(body.organs.mental.status, "insufficient_data");
    assert.equal(body.organs.financial.status, "insufficient_data");
  });
});

test("REPORT-1 panel reads the real earnings table and the exact Telegram snapshots", async () => {
  const fixture = makeFixture();
  await withApiServer(fixture, async (base) => {
    const { response, body } = await getJson(base, "ledger");
    assert.equal(response.status, 200);
    assert.deepEqual(body, {
      api_cost: {
        no_data: false,
        total: "USD 0.42",
        items: [
          { label: "API利用料", date: "2026-07-21", amount: "USD 0.12", link: null },
          { label: "API利用料", date: "2026-07-21", amount: "USD 0.30", link: null },
        ],
      },
      financial: {
        no_data: false,
        items: [
          { label: "実現損失", date: "2026-07-21", amount: "USD 3.15", link: null },
        ],
      },
      reports: {
        daily: {
          period_key: "2026-07-21",
          snapshot_hash: "a".repeat(64),
          telegram_message_id: 71,
          gross_usd_micros: "0",
          realized_loss_usd_micros: "0",
          financial_fee_usd_micros: "0",
          api_cost_usd_micros: "420000",
          operating_net_usd_micros: "-420000",
          balance_usdc_atomic: "0",
          distributable_usdc_atomic: "0",
          self_funded_bps: 0,
          stop_reason: "no_external_income",
          rail_pnl: [],
        },
        weekly: {
          period_key: "2026-W30",
          snapshot_hash: "b".repeat(64),
          telegram_message_id: 72,
          gross_usd_micros: "0",
          realized_loss_usd_micros: "3150000",
          financial_fee_usd_micros: "0",
          api_cost_usd_micros: "0",
          operating_net_usd_micros: "-3150000",
          balance_usdc_atomic: "0",
          distributable_usdc_atomic: "0",
          self_funded_bps: 0,
          stop_reason: "negative_net",
          rail_pnl: [{ rail: "CAPITAL", net_usd_micros: "-3150000" }],
        },
      },
    });
  });
  const paths = fixture.calls.map((call) => call.url.pathname);
  assert.equal(paths.includes("/rest/v1/lm_financial_ledger"), false);
  assert.equal(paths.includes("/rest/v1/lm_agent_earnings"), true);
  assert.equal(paths.includes("/rest/v1/lm_financial_report_receipts"), true);
});

test("the authenticated ledger renders exact atomic USDC earnings without float rounding", async () => {
  const fixture = makeFixture();
  fixture.byUid.u1.earnings.unshift({
    entry_key: "taskmarket:award",
    kind: "financial_external_income",
    amount_minor: null,
    amount_atomic: "2312500",
    amount_decimals: 6,
    currency: "USD",
    occurred_at: "2026-07-21T10:30:00.000Z",
    tx_hash: `0x${"c".repeat(64)}`,
    source: "taskmarket_work",
    meta: {},
  });
  await withApiServer(fixture, async (base) => {
    const { response, body } = await getJson(base, "ledger");
    assert.equal(response.status, 200);
    assert.deepEqual(body.financial.items[0], {
      label: "外部収益",
      date: "2026-07-21",
      amount: "USD 2.3125",
      link: null,
    });
  });
  const earningsCall = fixture.calls.find((call) =>
    call.url.pathname.endsWith("/lm_agent_earnings"));
  assert.match(earningsCall.url.searchParams.get("select"), /amount_atomic,amount_decimals/);
});

test("LM-33b gates reuse LM-32 lock decisions and discovery copy", async () => {
  await withApiServer(makeFixture(), async (base) => {
    const { response, body } = await getJson(base, "gates");
    assert.equal(response.status, 200);
    assert.equal(body.gates.length, 2);
    assert.deepEqual(body.gates.map(({ id, unlocked }) => ({ id, unlocked })), [
      { id: "location", unlocked: true },
      { id: "payout", unlocked: false },
    ]);
    for (const gate of body.gates) assert.equal(typeof gate.unlock_method, "string");
  });
});

test("LM-33b settings mirror language, actual call schedule, and connection state", async () => {
  await withApiServer(makeFixture(), async (base) => {
    const { response, body } = await getJson(base, "settings");
    assert.equal(response.status, 200);
    assert.deepEqual(body, {
      call_language: "ja",
      call_schedule: { time_zone: "UTC", minutes_before: [10, 5], wake_policy: "travel-only" },
      connections: { calendar: false, gmail: false, telegram: true },
    });
  });
});

test("LM-33b negative: every endpoint requires a panel session", async () => {
  await withApiServer(makeFixture(), async (base) => {
    for (const endpoint of ["timeline", "scores", "ledger", "gates", "settings"]) {
      const { response, body } = await getJson(base, endpoint, { session: false });
      assert.equal(response.status, 401, endpoint);
      assert.deepEqual(body, { error: "unauthorized" });
    }
  });
});

test("LM-33b negative: a panel cookie outside /api/panel cannot touch session or panel data", async () => {
  const fixture = makeFixture();
  await withApiServer(fixture, async (base) => {
    const response = await fetch(`${base}/health`, {
      headers: { Cookie: `lm_panel_session=${SESSION}` },
    });
    assert.equal(response.status, 404);
    assert.deepEqual(await response.json(), { error: "not_found" });
  });
  assert.equal(fixture.calls.length, 0);
  assert.deepEqual(fixture.calendarUids, []);
});

test("LM-33b negative: API is read-only", async () => {
  const fixture = makeFixture();
  await withApiServer(fixture, async (base) => {
    const { response, body } = await getJson(base, "settings", { method: "POST" });
    assert.equal(response.status, 405);
    assert.deepEqual(body, { error: "method_not_allowed" });
    assert.equal(response.headers.get("allow"), "GET");
  });
  assert.ok(fixture.calls.every(({ url, init }) => !init.method || init.method === "GET" || url.pathname.endsWith("/rpc/resolve_lm_panel_session") || url.pathname.endsWith("/rpc/lm_panel_score_outcome_snapshot")));
});

test("LM-33b negative: request UID is ignored and every data source stays bound to session UID", async () => {
  const fixture = makeFixture();
  await withApiServer(fixture, async (base) => {
    for (const endpoint of ["timeline", "scores", "ledger", "gates", "settings"]) {
      const { response, body } = await getJson(base, endpoint, { query: "?uid=u2" });
      assert.equal(response.status, 200, endpoint);
      assert.doesNotMatch(JSON.stringify(body), /u2|secret/);
    }
  });
  const dataReads = fixture.calls.filter(({ url }) => !url.pathname.endsWith("/lm_panel_sessions") && !url.pathname.includes("/rpc/"));
  assert.ok(dataReads.length > 0);
  for (const { url } of dataReads) {
    if (url.pathname.endsWith("/lm_agent_earnings")) {
      assert.equal(
        url.searchParams.get("wallet_address"),
        `eq.${byUidWallet(fixture)}`,
        url.toString(),
      );
    } else {
      assert.equal(url.searchParams.get("uid"), "eq.u1", url.toString());
    }
  }
  assert.ok(fixture.calendarUids.length > 0);
  assert.ok(fixture.calendarUids.every((uid) => uid === "u1"));
});

function byUidWallet(fixture) {
  const userRead = fixture.calls.find(({ url }) => (
    url.pathname.endsWith("/lm_users")
    && url.searchParams.get("select") === "agent_wallet_address"
  ));
  assert.ok(userRead);
  return "0x477EeE969ccfdc0e959F38cE8B83e372FC0262ad";
}
