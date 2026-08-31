"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");


function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}


test("real Telegram webhook persists only scrubbed feedback and sends a non-echoing ack", async () => {
  process.env.LM_TELEGRAM_BOT_TOKEN = "fixture-token";
  process.env.LM_TELEGRAM_WEBHOOK_SECRET = "fixture-webhook-secret";
  process.env.LM_FEEDBACK_PROVENANCE_KEY = "fixture-feedback-provenance";
  process.env.SUPABASE_URL = "https://fixture.supabase.co";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "fixture-service-role";
  process.env.LIFE_RUN_LOOPS = "false";

  const originalCreateServer = http.createServer;
  const originalFetch = global.fetch;
  let productionServer;
  let persisted;
  const sent = [];
  http.createServer = (handler) => {
    productionServer = originalCreateServer(handler);
    return productionServer;
  };
  global.fetch = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (url.hostname === "api.telegram.org" && /sendMessage$/.test(url.pathname)) {
      sent.push(JSON.parse(init.body));
      return response(200, { ok: true, result: { message_id: 9001 } });
    }
    if (url.pathname === "/rest/v1/lm_users" && method === "GET") {
      return response(200, [{ uid: "u1", telegram_chat_id: "100", tg_onboard_stage: "done" }]);
    }
    if (url.pathname === "/rest/v1/lm_feedback_intake" && method === "POST") {
      persisted = JSON.parse(init.body);
      return response(201, [{ id: "feedback-row-1" }]);
    }
    throw new Error(`unexpected fetch ${method} ${url}`);
  };

  try {
    const serverPath = require.resolve("../server.js");
    delete require.cache[serverPath];
    require(serverPath);
    await new Promise((resolve) => productionServer.listen(0, "127.0.0.1", resolve));
    const email = `private${"@"}example.com`;
    const phone = ["+81", "9012345678"].join("");
    const raw = `feedback: Calendar button fails for ${email} ${phone}`;
    const body = JSON.stringify({
      update_id: 7001,
      message: {
        message_id: 8101,
        date: Math.floor(Date.now() / 1000),
        from: { id: 100, first_name: "Fixture" },
        chat: { id: 100, type: "private" },
        text: raw,
      },
    });
    const status = await new Promise((resolve, reject) => {
      const request = http.request(
        `http://127.0.0.1:${productionServer.address().port}/telegram`,
        {
          method: "POST",
          headers: {
            "content-type": "application/json",
            "content-length": Buffer.byteLength(body),
            "x-telegram-bot-api-secret-token": "fixture-webhook-secret",
          },
        },
        (res) => {
          res.resume();
          res.on("end", () => resolve(res.statusCode));
        },
      );
      request.on("error", reject);
      request.end(body);
    });
    assert.equal(status, 200);
    assert.deepEqual(Object.keys(persisted).sort(), ["labels", "source_ref", "summary"]);
    assert.equal(JSON.stringify(persisted).includes(email), false);
    assert.equal(JSON.stringify(persisted).includes(phone), false);
    assert.deepEqual(persisted.labels, ["feedback", "calendar"]);
    assert.match(persisted.source_ref, /^tg:sha256:[a-f0-9]{32}$/);
    assert.equal(sent.length, 1);
    assert.equal(sent[0].text, "Thanks — your privacy-safe feedback was recorded.");
    assert.equal(sent[0].text.includes("Calendar button fails"), false);
  } finally {
    http.createServer = originalCreateServer;
    global.fetch = originalFetch;
    if (productionServer && productionServer.listening) {
      await new Promise((resolve) => productionServer.close(resolve));
    }
  }
});
