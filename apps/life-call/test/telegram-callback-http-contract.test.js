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
