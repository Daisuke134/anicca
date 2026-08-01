"use strict";
// spec 2026-08-01-lm-daily-organ-design.md §5.2.1 / §5.2.2 D7 (#2c) — the tap that ends the ladder.
//
// §5.2.1 makes [了解] the primary stop condition, so this is the one path in the feature whose
// failure turns the product into harassment. It is therefore tested through the REAL server.js over
// REAL HTTP with a REAL secret-token header: the fake fetch throws on any host or path it does not
// recognise, which makes "the tap wrote to the right tenant's row" a physical constraint rather than
// an assertion about a mock.
//
// The tenant boundary is the interesting part. callback_data carries only the event start (D7, the
// 64-byte limit), so the uid comes from the CHAT that tapped — never from the payload. Two people
// with a 09:00 meeting therefore tap two different rows, and neither can address the other's.
// Run: node --test test/departure-nudge-http-contract.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

const START_ISO = "2026-08-05T14:00:00+09:00";

test("a [了解] tap stops only the tapper's ladder, visibly, and unknown prefixes stay ignored", async () => {
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

  // Two tenants, each with their own ladder for an event that starts at the same moment.
  const ladders = new Map([
    ["u1", { acked_at: null, ack_reason: null }],
    ["u2", { acked_at: null, ack_reason: null }],
  ]);
  const patched = [];
  let callbackReceipts = 0;
  let edits = 0;
  let messagesSent = 0;

  global.fetch = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (url.hostname === "api.telegram.org") {
      if (/answerCallbackQuery$/.test(url.pathname)) callbackReceipts++;
      // CB-1: the tapped message is edited into its answered state, which is what removes the
      // keyboard. Without it the button stays tappable on a ladder that has already ended.
      if (/editMessageText$/.test(url.pathname)) edits++;
      if (/sendMessage$/.test(url.pathname)) messagesSent++;
      return response(200, { ok: true, result: true });
    }
    if (url.pathname === "/rest/v1/lm_users" && method === "GET") {
      const chat = String(url.searchParams.get("telegram_chat_id") || "").replace(/^eq\./, "");
      return response(200, [{ uid: chat === "100" ? "u1" : "u2", telegram_chat_id: chat, call_language: "ja" }]);
    }
    if (url.pathname === "/rest/v1/lm_departure_nudge" && method === "PATCH") {
      const uid = String(url.searchParams.get("uid") || "").replace(/^eq\./, "");
      const eventKey = String(url.searchParams.get("event_key") || "").replace(/^eq\./, "");
      patched.push({ uid, eventKey, latched: url.searchParams.get("acked_at") === "is.null" });
      const row = ladders.get(uid);
      // The real table's latch: acked_at IS NULL is a filter, so a second tap matches no row.
      if (!row || row.acked_at) return response(200, []);
      Object.assign(row, JSON.parse(init.body || "{}"));
      return response(200, [{ uid, event_key: eventKey, ...row }]);
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

    const post = (chatId, data, callbackId) => new Promise((resolve, reject) => {
      const body = JSON.stringify({ callback_query: {
        id: callbackId, from: { id: Number(chatId) },
        data,
        message: { message_id: 8200, chat: { id: Number(chatId) }, text: "🚨 いま出る時間。08:05" },
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

    assert.equal(await post("100", `depart:ack:${START_ISO}`, "cb-1"), 200);

    // ① the tap landed, on the tapper's row, as a tap
    assert.equal(ladders.get("u1").ack_reason, "tap");
    assert.ok(ladders.get("u1").acked_at, "acked_at is set, which is what every future claim filters on");
    assert.equal(patched.length, 1);
    assert.equal(patched[0].uid, "u1");
    // The key is built from the looked-up uid, NOT from callback_data — that is the tenant boundary.
    assert.equal(patched[0].eventKey, `u1|${START_ISO}`);
    assert.equal(patched[0].latched, true, "the write is a latch, so a second tap cannot rewrite it");

    // ② the user gets a receipt, and ③ the keyboard comes off
    assert.equal(callbackReceipts, 1);
    assert.equal(edits, 1);
    assert.equal(messagesSent, 0, "a stop is not an occasion for another message");

    // ⑤ tenant isolation: the same startIso from another chat touches only that chat's own row
    assert.equal(await post("200", `depart:ack:${START_ISO}`, "cb-2"), 200);
    assert.equal(patched[1].uid, "u2");
    assert.equal(patched[1].eventKey, `u2|${START_ISO}`);
    assert.equal(ladders.get("u2").ack_reason, "tap");

    // and the first tenant's row was not touched a second time
    assert.equal(patched.filter((p) => p.uid === "u1").length, 1);

    // ④ regression: an unknown prefix is still ignored, and writes nothing
    assert.equal(await post("100", "nosuchprefix:ack:whatever", "cb-3"), 200);
    assert.equal(patched.length, 2, "no ledger write for a prefix nobody owns");
  } finally {
    if (productionServer) await new Promise((resolve) => productionServer.close(resolve));
    http.createServer = originalCreateServer;
    global.fetch = originalFetch;
  }
});
