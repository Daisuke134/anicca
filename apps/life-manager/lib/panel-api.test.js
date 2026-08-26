"use strict";

const test = require("node:test");
const assert = require("node:assert");
const crypto = require("node:crypto");
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

let handlePanelApiRequest = async (_req, res) => {
  res.writeHead(501, { "content-type": "application/json" });
  res.end(JSON.stringify({ error: "panel API not implemented" }));
};
let handlePanelOAuthCallback = async (_req, res) => {
  res.writeHead(501, { "content-type": "application/json" });
  res.end(JSON.stringify({ error: "panel callback not implemented" }));
};
try {
  ({ handlePanelApiRequest, handlePanelOAuthCallback } = require("./panel-api.js"));
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

function onboardingHarness(initial = {}) {
  const writes = [];
  const syncs = [];
  const wrapperCalls = [];
  const providerReads = [];
  const reads = [];
  const receipts = new Map();
  const state = {
    step: "name", stage: "calendar", name: null, calendarConnected: false,
    homeAddress: null, notificationsEnabled: false, phone: null,
    callEnabled: false, paid: false, paymentLink: null, ...initial,
  };
  const scope = { uid: "tenant-a", chatId: "101", csrf: "csrf-a" };
  const commandStore = {
    async assertCurrentScope(value) { return value.uid === scope.uid && value.chatId === scope.chatId; },
    async readReceipt(value, key) { assert.deepEqual(value, scope); return receipts.get(String(key)) || null; },
    async claimReceipt(value, key, entry) {
      assert.deepEqual(value, scope);
      const normalized = String(key);
      if (receipts.has(normalized)) return false;
      receipts.set(normalized, { requestHash: entry.requestHash, status: entry.status, result: null });
      return true;
    },
    async finishReceipt(value, key, entry) {
      assert.deepEqual(value, scope);
      const receipt = receipts.get(String(key));
      if (!receipt) throw new Error("receipt_missing");
      receipt.status = entry.status;
      receipt.result = entry.result || null;
    },
    async readOnboardingState(value) {
      assert.deepEqual(value, scope);
      reads.push("state");
      return { ...state };
    },
    async syncCalendarStatus(value, status) { assert.deepEqual(value, scope); syncs.push(status); return true; },
    async mutateOnboardingWithCalendar(value, status, action, payload) {
      assert.deepEqual(value, scope);
      wrapperCalls.push({ status, action, payload });
      writes.push({ action, payload });
      return { ...state };
    },
    async mutateOnboarding(value, action, payload) {
      assert.deepEqual(value, scope);
      writes.push({ action, payload });
      return { ...state };
    },
  };
  const opts = {
    panelOrigin: "https://panel.example",
    panelBaseUrl: "https://panel.example",
    sessionScopeImpl: async () => scope,
    commandStore,
    stripePaymentLink: "https://buy.stripe.com/test_life_manager",
    composioKey: "provider-key",
    composioCalendarStatusImpl: async () => { providerReads.push("ACTIVE"); return "ACTIVE"; },
  };
  return { state, scope, writes, syncs, wrapperCalls, providerReads, reads, receipts, opts, commandStore };
}

async function onboardingRequest(harness, { method = "GET", path = "/api/panel/onboarding", body, headers = {} } = {}) {
  const req = new http.IncomingMessage();
  req.method = method;
  req.url = path;
  req.headers = {
    cookie: `__Host-lm_panel_session=${SESSION}`,
    origin: "https://panel.example",
    "content-type": "application/json",
    "x-lm-csrf": "csrf-a",
    "idempotency-key": Object.hasOwn(headers, "idempotency-key") ? headers["idempotency-key"] : `onboarding-${harness._requestNumber = (harness._requestNumber || 0) + 1}`,
    ...headers,
  };
  const chunks = [];
  if (body == null) req.push(null);
  else { req.push(JSON.stringify(body)); req.push(null); }
  const response = await new Promise((resolve, reject) => {
    const out = new (require("node:stream").Writable)({
      write(chunk, _encoding, callback) { chunks.push(Buffer.from(chunk)); callback(); },
    });
    out.writeHead = (status, responseHeaders) => { out.status = status; out.headers = new Map(Object.entries(responseHeaders)); };
    out.end = (chunk) => { if (chunk) chunks.push(Buffer.from(chunk)); resolve(out); };
    Promise.resolve(handlePanelApiRequest(req, out, harness.opts)).catch(reject);
  });
  const raw = Buffer.concat(chunks).toString("utf8");
  return { response, body: raw ? JSON.parse(raw) : null };
}

function onboardingRequestHash(action, payload) {
  return crypto.createHash("sha256").update(JSON.stringify({ action, payload })).digest("hex");
}

test("Task 7A onboarding API follows server-owned fixed progression and ignores client uid", async () => {
  const h = onboardingHarness({ step: "home", stage: "home", calendarConnected: true });
  const first = await onboardingRequest(h, { path: "/api/panel/onboarding?uid=tenant-b" });
  assert.equal(first.response.status, 200);
  assert.equal(first.body.step, "home");
  assert.equal(first.body.paymentLink, undefined);
  assert.equal(h.writes.length, 0);
  const forgedCalendar = await onboardingRequest(h, { method: "POST", body: { action: "calendar.complete", uid: "tenant-b" } });
  assert.equal(forgedCalendar.response.status, 400);
  assert.equal(h.writes.length, 0, "calendar completion is provider-owned, never a client write");

  const actions = [
    ["home.save", { home_address: "東京都渋谷区 1-1-1" }],
    ["notifications.enable", {}],
    ["phone.save", { phone: "+81 (90) 1234-5678", uid: "tenant-b" }],
    ["call.enable", {}],
    ["payment.skip", { paid: true, uid: "tenant-b" }],
  ];
  for (const [action, payload] of actions) {
    h.commandStore.mutateOnboardingWithCalendar = async (scope, status, actualAction, actualPayload) => {
      assert.deepEqual(scope, h.scope);
      assert.equal(status, "ACTIVE");
      h.wrapperCalls.push({ status, action: actualAction, payload: actualPayload });
      h.writes.push({ action: actualAction, payload: actualPayload });
      return { ...h.state, step: action === "payment.skip" ? "dashboard" : action.split(".")[0] };
    };
    const result = await onboardingRequest(h, { method: "POST", body: { action, ...payload } });
    assert.equal(result.response.status, 200, action);
    assert.notEqual(result.body.paid, true, "client action never grants paid");
  }
  assert.equal(h.writes.length, actions.length);
  assert.equal(Object.hasOwn(h.writes[2].payload, "uid"), false, "uid is stripped before the tenant-scoped transition");
  assert.equal(h.writes[2].payload.phone, ["+81", "90", "1234", "5678"].join(""), "phone is normalized before persistence");
});

test("Task 7A rejects an out-of-order onboarding mutation before any write", async () => {
  const h = onboardingHarness({ step: "home", stage: "home" });
  h.commandStore.mutateOnboardingWithCalendar = async () => {
    const error = new Error("onboarding_conflict");
    error.status = 409;
    throw error;
  };
  const result = await onboardingRequest(h, { method: "POST", body: { action: "call.enable" } });
  assert.equal(result.response.status, 409);
  assert.deepEqual(result.body, { error: "onboarding_conflict" });
  assert.equal(h.writes.length, 0);
});

test("Task 7A phone.save converts a Japanese domestic number and preserves explicit international form", async () => {
  const h = onboardingHarness({ step: "phone", stage: "phone", calendarConnected: true });
  const domestic = await onboardingRequest(h, { method: "POST", body: { action: "phone.save", phone: "090-1234-5678" }, headers: { "idempotency-key": "phone-domestic-01" } });
  assert.equal(domestic.response.status, 200);
  assert.equal(h.wrapperCalls.at(-1).payload.phone, ["+81", "90", "1234", "5678"].join(""));

  const international = await onboardingRequest(h, { method: "POST", body: { action: "phone.save", phone: "+44 (20) 7946-0958" }, headers: { "idempotency-key": "phone-intl-0001" } });
  assert.equal(international.response.status, 200);
  assert.equal(h.wrapperCalls.at(-1).payload.phone, "+442079460958");
});

test("Task 7A payment step returns only configured server Stripe link and fails closed when absent", async () => {
  const h = onboardingHarness({ step: "payment", stage: "payment", paymentLink: null });
  const result = await onboardingRequest(h);
  assert.equal(result.response.status, 200);
  assert.equal(result.body.paymentLink, "https://buy.stripe.com/test_life_manager?client_reference_id=tenant-a");
  const missing = onboardingHarness({ step: "payment", stage: "payment" });
  missing.opts.stripePaymentLink = "";
  const unavailable = await onboardingRequest(missing);
  assert.equal(unavailable.response.status, 503);
  assert.deepEqual(unavailable.body, { error: "payment_unavailable" });
});

test("Task 7A paid phone-less tenant resumes at dashboard after required core steps", async () => {
  const h = onboardingHarness({ step: "dashboard", stage: "phone", calendarConnected: true, homeAddress: "home", notificationsEnabled: true, paid: true, phone: null });
  const result = await onboardingRequest(h);
  assert.equal(result.response.status, 200);
  assert.equal(result.body.step, "dashboard");
  assert.equal(result.body.phone, null);
  assert.equal(result.body.callEnabled, false);
});

test("Task 7A refreshes official Calendar truth before every state read or transition", async () => {
  const h = onboardingHarness({ step: "home", stage: "home", calendarConnected: true });
  const get = await onboardingRequest(h);
  assert.equal(get.response.status, 200);
  assert.deepEqual(h.syncs, ["ACTIVE"]);
  h.opts.composioCalendarStatusImpl = async () => "MISSING";
  h.commandStore.mutateOnboardingWithCalendar = async () => { throw new Error("transition must not run when Calendar is missing"); };
  const post = await onboardingRequest(h, { method: "POST", body: { action: "home.save", home_address: "home" } });
  assert.equal(post.response.status, 502);
  assert.deepEqual(h.syncs, ["ACTIVE"], "POST uses the combined transition RPC, not standalone sync");
  assert.deepEqual(h.reads, ["state"]);
});

test("R1A2 valid onboarding POST reads provider then uses exactly one combined sync/transition RPC", async () => {
  const h = onboardingHarness({ step: "home", stage: "home", calendarConnected: true });
  const result = await onboardingRequest(h, { method: "POST", body: { action: "home.save", home_address: "home" } });
  assert.equal(result.response.status, 200);
  assert.deepEqual(h.providerReads, ["ACTIVE"]);
  assert.deepEqual(h.syncs, [], "POST must not call standalone Calendar sync");
  assert.equal(h.wrapperCalls.length, 1);
  assert.deepEqual(h.wrapperCalls[0], { status: "ACTIVE", action: "home.save", payload: { home_address: "home" } });
});

test("R1A2 provider failure prevents both onboarding RPCs", async () => {
  const h = onboardingHarness({ step: "home", stage: "home" });
  h.opts.composioCalendarStatusImpl = async () => { h.providerReads.push("error"); throw new Error("provider_down"); };
  const result = await onboardingRequest(h, { method: "POST", body: { action: "home.save", home_address: "home" } });
  assert.equal(result.response.status, 502);
  assert.deepEqual(h.providerReads, ["error"]);
  assert.deepEqual(h.syncs, []);
  assert.deepEqual(h.wrapperCalls, []);
});

test("Task 7B R1: onboarding POST claims one receipt, replays success, and rejects key reuse", async () => {
  const h = onboardingHarness({ step: "home", stage: "home", calendarConnected: true });
  const key = "onboarding-replay-01";
  const first = await onboardingRequest(h, { method: "POST", body: { action: "home.save", home_address: "home" }, headers: { "idempotency-key": key } });
  assert.equal(first.response.status, 200);
  const before = { provider: h.providerReads.length, wrapper: h.wrapperCalls.length, writes: h.writes.length };
  const replay = await onboardingRequest(h, { method: "POST", body: { action: "home.save", home_address: "home" }, headers: { "idempotency-key": key } });
  assert.equal(replay.response.status, 200);
  assert.deepEqual(replay.body, first.body);
  assert.deepEqual({ provider: h.providerReads.length, wrapper: h.wrapperCalls.length, writes: h.writes.length }, before);
  const conflict = await onboardingRequest(h, { method: "POST", body: { action: "home.save", home_address: "other" }, headers: { "idempotency-key": key } });
  assert.equal(conflict.response.status, 409);
  assert.deepEqual(conflict.body, { error: "idempotency_conflict" });
  assert.deepEqual({ provider: h.providerReads.length, wrapper: h.wrapperCalls.length, writes: h.writes.length }, before);
});

test("Task 7B R1: onboarding POST requires a valid key and never re-transitions pending or failed receipts", async () => {
  const missing = onboardingHarness({ step: "home", stage: "home", calendarConnected: true });
  const noKey = await onboardingRequest(missing, { method: "POST", body: { action: "home.save", home_address: "home" }, headers: { "idempotency-key": "" } });
  assert.equal(noKey.response.status, 400);
  assert.deepEqual(noKey.body, { error: "idempotency_required" });
  assert.equal(missing.providerReads.length, 0);

  const payload = { home_address: "home" };
  const requestHash = onboardingRequestHash("home.save", payload);
  for (const [status, error] of [["pending", "idempotency_in_progress"], ["failed", "idempotency_failed"]]) {
    const h = onboardingHarness({ step: "home", stage: "home", calendarConnected: true });
    h.receipts.set(`onboarding-${status}`, { requestHash, status, result: null });
    const result = await onboardingRequest(h, { method: "POST", body: { action: "home.save", payload }, headers: { "idempotency-key": `onboarding-${status}` } });
    assert.equal(result.response.status, 409, status);
    assert.deepEqual(result.body, { error }, status);
    assert.equal(h.providerReads.length, 0, status);
    assert.equal(h.wrapperCalls.length, 0, status);
  }
});

test("Task 7B R1: failed onboarding transition is durably non-retryable", async () => {
  const h = onboardingHarness({ step: "home", stage: "home", calendarConnected: true });
  h.commandStore.mutateOnboardingWithCalendar = async () => { throw new Error("provider transition failed"); };
  const key = "onboarding-failed-01";
  const first = await onboardingRequest(h, { method: "POST", body: { action: "home.save", home_address: "home" }, headers: { "idempotency-key": key } });
  assert.equal(first.response.status, 502);
  assert.equal(h.receipts.get(key).status, "failed");
  const reads = h.providerReads.length;
  const second = await onboardingRequest(h, { method: "POST", body: { action: "home.save", home_address: "home" }, headers: { "idempotency-key": key } });
  assert.equal(second.response.status, 409);
  assert.deepEqual(second.body, { error: "idempotency_failed" });
  assert.equal(h.providerReads.length, reads);
});

test("Task 7B R1: verified Calendar callback returns onboarding only for incomplete server state", async () => {
  const stateToken = Buffer.alloc(32, 0x71).toString("base64url");
  const run = async (onboarding, expectedLocation, readError = false) => {
    const scope = { uid: "tenant-a", chatId: "101", csrf: "csrf-a" };
    const calls = [];
    const store = {
      async assertCurrentScope(value) { assert.deepEqual(value, scope); return true; },
      async claimOAuthState(value, hash) { calls.push({ type: "claim", value, hash }); return true; },
      async readOnboardingState(value) { calls.push({ type: "onboarding", value }); if (readError) throw new Error("state unavailable"); return onboarding; },
    };
    const response = { status: 0, headers: {}, writeHead(status, headers) { this.status = status; this.headers = headers || {}; }, end() {} };
    await handlePanelOAuthCallback({ method: "GET", url: `/panel/oauth/calendar?state=${stateToken}`, headers: { cookie: "" } }, response, {
      sessionScopeImpl: async () => scope,
      commandStore: store,
      composioCalendarStatusImpl: async () => "ACTIVE",
    });
    assert.equal(response.status, 303);
    assert.equal(response.headers.Location, expectedLocation);
    return calls;
  };
  const incomplete = await run({ step: "home" }, "/panel/onboarding");
  assert.equal(incomplete.filter((call) => call.type === "onboarding").length, 1);
  await run({ step: "dashboard" }, "/panel");
  await run({ step: "done" }, "/panel");
  await run({ step: "home" }, "/panel", true);
});

test("Task 7A rejects malformed JSON arrays, primitives, and payloads before provider/RPC", async () => {
  for (const malformed of [[], "not-an-object", 7, null, { action: "home.save", payload: [] }, { action: "home.save", payload: "home" }, { action: "home.save", extra: "home" }]) {
    const h = onboardingHarness({ step: "home", stage: "home" });
    const result = await onboardingRequest(h, { method: "POST", path: "/api/panel/onboarding/home/save", body: malformed });
    assert.equal(result.response.status, 400, String(malformed));
    assert.equal(h.writes.length, 0);
    assert.deepEqual(h.reads, [], "malformed body must not invoke state RPC");
    assert.deepEqual(h.providerReads, [], "malformed body must not query provider");
    assert.deepEqual(h.syncs, [], "malformed body must not sync provider");
  }
});

test("Task 7A unpaid dashboard remains checkout-reachable without granting paid", async () => {
  const h = onboardingHarness({ step: "dashboard", stage: "done", calendarConnected: true, paid: false });
  const result = await onboardingRequest(h);
  assert.equal(result.response.status, 200);
  assert.equal(result.body.step, "dashboard");
  assert.equal(result.body.paid, false);
  assert.equal(result.body.paymentLink, "https://buy.stripe.com/test_life_manager?client_reference_id=tenant-a");
});

test("Task 7A onboarding migration is additive, tenant-scoped, and lock-atomic", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-27-lm-panel-onboarding-core.sql"), "utf8");
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_panel_onboarding_state/i);
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_panel_onboarding_transition/i);
  assert.match(sql, /SELECT .*FROM public\.lm_users[\s\S]*FOR UPDATE/i);
  assert.match(sql, /telegram_chat_id::text\s*=\s*p_chat_id/i);
  assert.match(sql, /paid\s+IS\s+TRUE/i);
  assert.doesNotMatch(sql, /CREATE TABLE/i);
  const transition = sql.slice(sql.indexOf("CREATE OR REPLACE FUNCTION public.lm_panel_onboarding_transition"));
  assert.doesNotMatch(transition, /SET\s+paid\s*=/i, "client transitions cannot write paid");
  assert.match(transition, /call_enabled\s*=\s*false/i, "phone and notification transitions keep calls off");
  assert.match(sql, /REVOKE ALL ON FUNCTION public\.lm_panel_onboarding_transition/i);
});

test("R1A2 combined onboarding transition wraps Calendar sync and rollback in one RPC", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-27-lm-panel-onboarding-reachability.sql"), "utf8");
  assert.match(sql, /CREATE OR REPLACE FUNCTION public\.lm_panel_onboarding_transition_with_calendar/i);
  assert.match(sql, /sync_lm_panel_calendar_status[\s\S]*lm_panel_onboarding_transition/i);
  assert.match(sql, /LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp/i);
  assert.match(sql, /GRANT EXECUTE ON FUNCTION public\.lm_panel_onboarding_transition_with_calendar/i);
});

test("Task 7A state resumes for another session of the same actor and isolates another actor", async () => {
  const first = onboardingHarness({ step: "phone", stage: "phone", phone: null });
  const resumed = onboardingHarness({ step: "phone", stage: "phone", phone: null });
  assert.deepEqual((await onboardingRequest(first)).body, (await onboardingRequest(resumed)).body);
  const other = onboardingHarness({ step: "dashboard", stage: "dashboard", paid: true });
  other.opts.sessionScopeImpl = async () => ({ uid: "tenant-b", chatId: "202", csrf: "csrf-b" });
  other.opts.commandStore.assertCurrentScope = async () => false;
  const denied = await onboardingRequest(other, { headers: { "x-lm-csrf": "csrf-b" } });
  assert.equal(denied.response.status, 401);
  assert.equal(denied.body.error, "unauthorized");
});
