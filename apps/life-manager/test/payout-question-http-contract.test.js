"use strict";
// FIN-b (spec row 13b): the payout closed question must be wired into the REAL webhook, not just the
// library. The 12c lesson was that a finished module nobody called changed nothing in production, so
// this test boots the actual server.js, posts the two callbacks Telegram would post, and asserts the
// §9.11 question really leaves over the Bot API and the answer really lands on lm_users.
const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const { FINANCIAL_STRINGS } = require("../lib/i18n.js");

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

test("POST /telegram opens the payout question and stores the tapped answer", async () => {
  process.env.LM_TELEGRAM_BOT_TOKEN = "fixture-token";
  process.env.LM_TELEGRAM_WEBHOOK_SECRET = "fixture-webhook-secret";
  process.env.SUPABASE_URL = "https://fixture.supabase.co";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "fixture-service-role";
  process.env.LIFE_RUN_LOOPS = "false";

  const originalCreateServer = http.createServer;
  const originalFetch = global.fetch;
  const originalLog = console.log;
  let productionServer;
  http.createServer = (handler) => {
    productionServer = originalCreateServer(handler);
    return productionServer;
  };
  console.log = () => {};

  const sentMessages = [];
  const patches = [];
  let storedDestination = null;

  global.fetch = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (url.hostname === "api.telegram.org") {
      if (url.pathname.endsWith("/sendMessage")) sentMessages.push(JSON.parse(init.body || "{}"));
      return response(200, { ok: true, result: { message_id: 1 } });
    }
    if (url.pathname === "/rest/v1/lm_users" && method === "GET") {
      const chat = String(url.searchParams.get("telegram_chat_id") || "").replace(/^eq\./, "");
      const uid = String(url.searchParams.get("uid") || "").replace(/^eq\./, "");
      return response(200, [{ uid: uid || "u1", telegram_chat_id: chat || "100", payout_destination: storedDestination }]);
    }
    if (url.pathname === "/rest/v1/lm_users" && method === "PATCH") {
      patches.push({ url: String(url), body: JSON.parse(init.body || "{}") });
      // Honour the compare-and-set the caller asked for: an already-set column claims no row.
      if (url.searchParams.get("payout_destination") === "is.null" && storedDestination) return response(200, []);
      storedDestination = JSON.parse(init.body || "{}").payout_destination;
      return response(200, [{ uid: "u1", payout_destination: storedDestination }]);
    }
    return response(200, []);
  };

  try {
    const serverPath = require.resolve("../server.js");
    delete require.cache[serverPath];
    require(serverPath);
    assert.ok(productionServer, "the production HTTP server must be captured");
    await new Promise((resolve) => productionServer.listen(0, "127.0.0.1", resolve));
    const origin = `http://127.0.0.1:${productionServer.address().port}`;

    const post = (data, callbackId) => new Promise((resolve, reject) => {
      const body = JSON.stringify({ callback_query: {
        id: callbackId, from: { id: 100 }, data,
        message: { message_id: 246, chat: { id: 100 } },
      } });
      const request = http.request(`${origin}/telegram`, {
        method: "POST",
        headers: {
          "content-type": "application/json", "content-length": Buffer.byteLength(body),
          "x-telegram-bot-api-secret-token": "fixture-webhook-secret",
        },
      }, (res) => { res.resume(); res.on("end", () => resolve(res.statusCode)); });
      request.on("error", reject);
      request.end(body);
    });

    // 1. The register button on the weekly discovery announcement.
    assert.equal(await post("discovery:register:payout", "cb-register"), 200);
    const question = sentMessages.find((m) => m.text === FINANCIAL_STRINGS.ja.payoutQuestion.text);
    assert.ok(question, `the §9.11 question must be sent, got ${JSON.stringify(sentMessages)}`);
    assert.equal(String(question.chat_id), "100");
    assert.equal(question.reply_markup.inline_keyboard.flat().length, 3);

    // 2. The user taps a rail on that question.
    assert.equal(await post("payout:answer:wallet", "cb-wallet"), 200);
    assert.equal(patches.length, 1, `exactly one write, got ${JSON.stringify(patches)}`);
    assert.match(patches[0].url, /uid=eq\.u1/);
    assert.match(patches[0].url, /payout_destination=is\.null/);
    assert.equal(patches[0].body.payout_destination.type, "wallet");
    assert.equal(storedDestination.type, "wallet");

    // 3. The question is never asked a second time once the column carries an answer.
    const beforeReask = sentMessages.length;
    assert.equal(await post("discovery:register:payout", "cb-register-again"), 200);
    assert.equal(sentMessages.length, beforeReask, "an answered payout question must never be re-asked");
  } finally {
    console.log = originalLog;
    http.createServer = originalCreateServer;
    global.fetch = originalFetch;
    if (productionServer && productionServer.listening) {
      await new Promise((resolve) => productionServer.close(resolve));
    }
  }
});
