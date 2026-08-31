"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

test("POST /telegram consumes a typed callback once and cross-tenant/replay callbacks mutate zero", async () => {
  process.env.LM_TELEGRAM_BOT_TOKEN = "fixture-token";
  process.env.LM_TELEGRAM_WEBHOOK_SECRET = "fixture-webhook-secret";
  process.env.SUPABASE_URL = "https://fixture.supabase.co";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "fixture-service-role";
  process.env.LIFE_RUN_LOOPS = "false";

  const originalCreateServer = http.createServer;
  const originalFetch = global.fetch;
  let productionServer;
  http.createServer = (handler) => {
    productionServer = originalCreateServer(handler);
    return productionServer;
  };

  const ask = {
    uid: "u1", event_id: "event-1", reply_token: "reply-token", semantic_key: "calendar_online:hash",
    question_type: "calendar_online", question_context: { seriesId: "series-1" },
    telegram_chat_id: "100", answered_at: null,
  };
  let typedMutations = 0;
  let callbackReceipts = 0;
  let messagesSent = 0;
  global.fetch = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (url.hostname === "api.telegram.org") {
      if (/answerCallbackQuery$/.test(url.pathname)) callbackReceipts++;
      if (/sendMessage$/.test(url.pathname)) messagesSent++;
      return response(200, { ok: true, result: true });
    }
    if (url.pathname === "/rest/v1/lm_users" && method === "GET") {
      const chat = String(url.searchParams.get("telegram_chat_id") || "").replace(/^eq\./, "");
      return response(200, [{ uid: chat === "100" ? "u1" : "u2", telegram_chat_id: chat }]);
    }
    if (url.pathname === "/rest/v1/lm_ask_log" && method === "PATCH") {
      const uid = String(url.searchParams.get("uid") || "").replace(/^eq\./, "");
      const token = String(url.searchParams.get("reply_token") || "").replace(/^eq\./, "");
      const chat = String(url.searchParams.get("telegram_chat_id") || "").replace(/^eq\./, "");
      if (uid !== ask.uid || token !== ask.reply_token || chat !== ask.telegram_chat_id || ask.answered_at) {
        return response(200, []);
      }
      Object.assign(ask, JSON.parse(init.body || "{}"));
      typedMutations++;
      return response(200, [{ ...ask }]);
    }
    throw new Error(`unexpected fetch ${method} ${url}`);
  };

  try {
    const serverPath = require.resolve("../server.js");
    delete require.cache[serverPath];
    require(serverPath);
    assert.ok(productionServer, "the production HTTP server must be captured");
    await new Promise((resolve) => productionServer.listen(0, "127.0.0.1", resolve));
    const origin = `http://127.0.0.1:${productionServer.address().port}`;
    const post = (chatId, actorId, callbackId) => new Promise((resolve, reject) => {
      const body = JSON.stringify({ callback_query: {
        id: callbackId, from: { id: Number(actorId) },
        data: "ask:calendar_online:online:reply-token",
        message: { message_id: 8100, chat: { id: Number(chatId) } },
      } });
      const request = http.request(`${origin}/telegram`, {
        method: "POST",
        headers: {
          "content-type": "application/json", "content-length": Buffer.byteLength(body),
          "x-telegram-bot-api-secret-token": "fixture-webhook-secret",
        },
      }, (res) => {
        res.resume();
        res.on("end", () => resolve(res.statusCode));
      });
      request.on("error", reject);
      request.end(body);
    });

    assert.equal(await post("100", "100", "cb-first"), 200);
    assert.equal(await post("100", "100", "cb-replay"), 200);
    assert.equal(await post("200", "200", "cb-cross"), 200);
    assert.equal(typedMutations, 1);
    assert.equal(callbackReceipts, 3);
    assert.equal(messagesSent, 0);
    assert.equal(ask.answer_value, "online");
    assert.equal(ask.answer_source, "telegram_callback");
    assert.equal(ask.answer_provenance.kind, "telegram_callback");
  } finally {
    http.createServer = originalCreateServer;
    global.fetch = originalFetch;
    if (productionServer && productionServer.listening) {
      await new Promise((resolve) => productionServer.close(resolve));
    }
  }
});

test("POST /telegram opens an exact partial JPY CFO snapshot in the tapped message", { concurrency: false }, async () => {
  process.env.LM_TELEGRAM_BOT_TOKEN = "fixture-token";
  process.env.LM_TELEGRAM_WEBHOOK_SECRET = "fixture-webhook-secret";
  process.env.SUPABASE_URL = "https://fixture.supabase.co";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "fixture-service-role";
  process.env.LIFE_RUN_LOOPS = "false";

  const originalCreateServer = http.createServer;
  const originalFetch = global.fetch;
  let productionServer;
  http.createServer = (handler) => {
    productionServer = originalCreateServer(handler);
    return productionServer;
  };

  const snapshot = {
    schemaVersion: 1, reportingDate: "2026-08-10", revision: 1, state: "partial", currency: "JPY",
    totals: { assetsMinor: 420000, liabilitiesMinor: null, netWorthMinor: null, changeMinor: null },
    sources: [{ sourceId: "moneytree_mufg", label: "MUFG", status: "fresh", asOf: "2026-08-10T06:02:00+09:00", amountMinor: 420000, verificationStatus: "provider_reported" }],
    excluded: [{ label: "負債", reason: "接続範囲が不明" }], repair: null, action: null,
  };
  const calls = [];
  let rejectOwnerLookup = false;
  global.fetch = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    calls.push({ url, method, body: init.body });
    if (url.hostname === "api.telegram.org") return response(200, { ok: true, result: true });
    if (url.pathname === "/rest/v1/lm_users" && method === "GET") {
      if (rejectOwnerLookup) throw new Error("owner provider secret");
      return response(200, [{ uid: "cfo-owner", telegram_chat_id: "100" }]);
    }
    if (url.pathname === "/rest/v1/lm_cfo_daily_snapshots" && method === "GET") {
      return response(200, [{ report_payload: snapshot }]);
    }
    throw new Error(`unexpected fetch ${method} ${url}`);
  };

  const post = (data) => new Promise((resolve, reject) => {
    const body = JSON.stringify({ callback_query: {
      id: data.id || "cfo-callback", from: { id: Number(data.actorId || 100) }, data: data.data,
      message: { message_id: Number(data.messageId || 900), chat: { id: Number(data.chatId || 100) } },
    } });
    const request = http.request(`http://127.0.0.1:${productionServer.address().port}/telegram`, {
      method: "POST", headers: {
        "content-type": "application/json", "content-length": Buffer.byteLength(body),
        "x-telegram-bot-api-secret-token": "fixture-webhook-secret",
      },
    }, (res) => { res.resume(); res.on("end", () => resolve(res.statusCode)); });
    request.on("error", reject); request.end(body);
  });

  try {
    const serverPath = require.resolve("../server.js");
    delete require.cache[serverPath];
    require(serverPath);
    assert.ok(productionServer, "the production HTTP server must be captured");
    await new Promise((resolve) => productionServer.listen(0, "127.0.0.1", resolve));

    assert.equal(await post({ data: "cfo:accounts:20260810:1" }), 200);
    const snapshotGet = calls.find((call) => call.url.pathname === "/rest/v1/lm_cfo_daily_snapshots");
    assert.equal(snapshotGet.method, "GET");
    assert.equal(snapshotGet.url.searchParams.get("uid"), "eq.cfo-owner");
    assert.equal(snapshotGet.url.searchParams.get("reporting_date"), "eq.2026-08-10");
    assert.equal(snapshotGet.url.searchParams.get("revision"), "eq.1");
    assert.equal(snapshotGet.url.searchParams.get("select"), "report_payload");
    assert.equal(snapshotGet.url.searchParams.get("limit"), "1");
    const telegramCalls = calls.filter((call) => call.url.hostname === "api.telegram.org");
    assert.equal(telegramCalls.filter((call) => call.url.pathname.endsWith("/editMessageText")).length, 1);
    assert.equal(telegramCalls.filter((call) => call.url.pathname.endsWith("/answerCallbackQuery")).length, 1);
    assert.equal(telegramCalls.filter((call) => call.url.pathname.endsWith("/sendMessage")).length, 0);
    const edit = telegramCalls.find((call) => call.url.pathname.endsWith("/editMessageText"));
    const editBody = JSON.parse(edit.body);
    assert.equal(editBody.chat_id, "100");
    assert.equal(editBody.message_id, 900);
    assert.match(editBody.text, /MUFG/);
    assert.match(editBody.text, /¥420,000/);

    const assertFailure = async (data, mutate = () => {}) => {
      mutate();
      const beforeFailure = calls.length;
      assert.equal(await post(data), 200);
      const failureCalls = calls.slice(beforeFailure).filter((call) => call.url.hostname === "api.telegram.org");
      assert.equal(failureCalls.filter((call) => call.url.pathname.endsWith("/editMessageText")).length, 0);
      assert.equal(failureCalls.filter((call) => call.url.pathname.endsWith("/sendMessage")).length, 0);
      const failureAnswers = failureCalls.filter((call) => call.url.pathname.endsWith("/answerCallbackQuery"));
      assert.equal(failureAnswers.length, 1);
      assert.equal(JSON.parse(failureAnswers[0].body).text, "読み込めませんでした。もう一度お試しください");
      assert.doesNotMatch(JSON.stringify(failureCalls), /420000|service-role|owner provider secret/);
    };
    await assertFailure({ id: "cfo-bad-actor", actorId: 999, data: "cfo:accounts:20260810:1" });
    await assertFailure({ id: "cfo-bad-owner", data: "cfo:accounts:20260810:1" }, () => { rejectOwnerLookup = true; });
    rejectOwnerLookup = false;
    await assertFailure({ id: "cfo-bad-snapshot", data: "cfo:accounts:20260810:1" }, () => { snapshot.reportingDate = "2026-08-09"; });
    snapshot.reportingDate = "2026-08-10";
    await assertFailure({ id: "cfo-bad-amount", data: "cfo:accounts:20260810:1" }, () => { snapshot.totals.assetsMinor = 1.5; });
    snapshot.totals.assetsMinor = 420000;
    await assertFailure({ id: "cfo-bad-unavailable-evidence", data: "cfo:accounts:20260810:1" }, () => {
      snapshot.sources[0].status = "unavailable"; snapshot.sources[0].amountMinor = null; snapshot.sources[0].verificationStatus = "provider_reported";
    });
    await assertFailure({ id: "cfo-bad-fresh-unknown", data: "cfo:accounts:20260810:1" }, () => {
      snapshot.sources[0].status = "fresh"; snapshot.sources[0].amountMinor = null; snapshot.sources[0].verificationStatus = "unavailable";
    });
  } finally {
    http.createServer = originalCreateServer;
    global.fetch = originalFetch;
    delete require.cache[require.resolve("../server.js")];
    if (productionServer && productionServer.listening) await new Promise((resolve) => productionServer.close(resolve));
  }
});
