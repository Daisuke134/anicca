"use strict";
// CORE-8f: a discovery answer left no trace. Nothing recorded which gate the user replied to, so an
// announcement for an unlocked-gate rotation could not be audited after the fact. The webhook must name
// the action and the gate it handled, and must stay silent for callbacks it does not own.
const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

test("POST /telegram records which discovery gate the user answered", async () => {
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

  const logged = [];
  console.log = (...args) => { logged.push(args.join(" ")); };

  global.fetch = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (url.hostname === "api.telegram.org") return response(200, { ok: true, result: true });
    if (url.pathname === "/rest/v1/lm_users" && method === "GET") {
      const chat = String(url.searchParams.get("telegram_chat_id") || "").replace(/^eq\./, "");
      return response(200, [{ uid: "u1", telegram_chat_id: chat }]);
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

    assert.equal(await post("discovery:later:payout", "cb-payout"), 200);
    assert.equal(await post("discovery:how:location", "cb-location"), 200);
    // A callback shaped like discovery but naming no real gate must leave no audit line.
    assert.equal(await post("discovery:later:nonsense", "cb-unknown"), 200);

    const audit = logged.filter((line) => line.startsWith("[discovery] callback"));
    assert.equal(audit.length, 2, `expected exactly two audit lines, got ${JSON.stringify(audit)}`);
    assert.match(audit[0], /action=later gate=payout/);
    assert.match(audit[1], /action=how gate=location/);
    // The audit line names the decision, never the person: no chat id, no user id.
    assert.ok(!audit.some((line) => /100|u1/.test(line)), "an audit line must not carry an identifier");
  } finally {
    console.log = originalLog;
    http.createServer = originalCreateServer;
    global.fetch = originalFetch;
    if (productionServer && productionServer.listening) {
      await new Promise((resolve) => productionServer.close(resolve));
    }
  }
});
