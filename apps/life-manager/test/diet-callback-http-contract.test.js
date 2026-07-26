"use strict";
// H2 ORG-diet: the tap must be wired into the REAL webhook, not just the library. This boots the
// actual server.js, posts the callback Telegram would post, and asserts the answer really lands in
// lm_diet_log and the question message really gets edited into its answered state (§10.0-15 ①) —
// with no thank-you message, because the edit IS the response.
const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const { DIET_STRINGS } = require("../lib/i18n.js");

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body, text: async () => JSON.stringify(body) };
}

test("POST /telegram routes diet:answer:* into the diet ledger and edits the question", async () => {
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
  const edits = [];
  const dietRows = [];

  global.fetch = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (url.hostname === "api.telegram.org") {
      if (url.pathname.endsWith("/sendMessage")) sentMessages.push(JSON.parse(init.body || "{}"));
      if (/\/(?:editMessageText|editMessageReplyMarkup)$/.test(url.pathname)) {
        edits.push({ method: url.pathname.split("/").pop(), body: JSON.parse(init.body || "{}") });
      }
      return response(200, { ok: true, result: { message_id: 1 } });
    }
    if (url.pathname === "/rest/v1/lm_users" && method === "GET") {
      const chat = String(url.searchParams.get("telegram_chat_id") || "").replace(/^eq\./, "");
      return response(200, [{ uid: "u1", telegram_chat_id: chat || "100" }]);
    }
    if (url.pathname === "/rest/v1/lm_diet_log") {
      if (method === "GET") {
        const day = String(url.searchParams.get("day") || "").replace(/^eq\./, "");
        const kind = String(url.searchParams.get("kind") || "").replace(/^eq\./, "");
        return response(200, dietRows.filter((r) => (!day || r.day === day) && (!kind || r.kind === kind)));
      }
      const body = JSON.parse(init.body || "{}");
      if (dietRows.some((r) => r.uid === body.uid && r.day === body.day && r.kind === body.kind)) {
        return response(409, { code: "23505", message: "duplicate key value" });
      }
      dietRows.push(body);
      return response(201, {});
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

    const post = (data, callbackId, messageText, fromId = 100) => new Promise((resolve, reject) => {
      const body = JSON.stringify({ callback_query: {
        id: callbackId, from: { id: fromId }, data,
        message: { message_id: 512, chat: { id: 100 }, ...(messageText ? { text: messageText } : {}) },
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

    const copy = DIET_STRINGS.ja.lunchQuestion;

    // 1. The user taps 「バーガー・ファスト」 on the lunch question.
    assert.equal(await post("diet:answer:fast", "cb-fast", copy.text), 200);
    assert.equal(dietRows.length, 1, `the answer must reach lm_diet_log, got ${JSON.stringify(dietRows)}`);
    assert.equal(dietRows[0].uid, "u1");
    assert.equal(dietRows[0].kind, "answer");
    assert.equal(dietRows[0].answer, "fast");
    assert.ok(dietRows[0].answered_at, "the row records when the tap happened");

    // 2. CB-1 ①: the question message itself shows the choice and loses its keyboard.
    assert.equal(edits.length, 1, `the answered question must be edited, got ${JSON.stringify(edits)}`);
    assert.equal(edits[0].method, "editMessageText");
    assert.equal(String(edits[0].body.message_id), "512");
    assert.equal(edits[0].body.text, `${copy.text}\n\n→ ${copy.fastButton}`);
    assert.ok(!("reply_markup" in edits[0].body), "the keyboard must be gone from the answered message");

    // 3. §10.0-15 ①: the edit IS the visible response — a tap must not spawn a thank-you message.
    assert.equal(sentMessages.length, 0, `no follow-up message on a plain tap, got ${JSON.stringify(sentMessages)}`);

    // 4. A second tap is refused by the unique index and answered visibly (§10.0-15 ③).
    assert.equal(await post("diet:answer:men", "cb-again", copy.text), 200);
    assert.equal(dietRows.length, 1, "no duplicate row for the same day");
    assert.equal(sentMessages.length, 1, "the second tap must not be silent");
    assert.equal(sentMessages[sentMessages.length - 1].text,
      copy.alreadyAnswered.replace("{choice}", copy.fastButton));

    // 5. A stranger's tap on this chat's message writes nothing.
    const beforeRows = dietRows.length;
    assert.equal(await post("diet:answer:teishoku", "cb-stranger", copy.text, 999), 200);
    assert.equal(dietRows.length, beforeRows, "a cross-tenant tap must not write");
  } finally {
    console.log = originalLog;
    http.createServer = originalCreateServer;
    global.fetch = originalFetch;
    if (productionServer && productionServer.listening) {
      await new Promise((resolve) => productionServer.close(resolve));
    }
  }
});
