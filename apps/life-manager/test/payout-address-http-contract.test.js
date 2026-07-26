"use strict";
// FIN-d (spec row 13d-a): the typed wallet-address intake must be wired into the REAL webhook.
// The 12c lesson stands: a finished module nobody calls changes nothing in production. This test boots
// the actual server.js and walks the whole user experience over HTTP:
//   tap wallet → (CB-1 edit) → the address question arrives → the user TYPES the address →
//   payout_destination flips to usable (CAS + read-back) → the ✅ confirmation quotes the short form.
// It also pins the routing order: a pending intake claims the typed message BEFORE feedback can
// swallow it, and with no pending intake the feedback path still receives normal messages.
const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const { FINANCIAL_STRINGS } = require("../lib/i18n.js");

const ADDRESS = "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359"; // published EIP-55 vector

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

test("POST /telegram: wallet tap asks for the address, the typed address becomes the usable destination", async () => {
  process.env.LM_TELEGRAM_BOT_TOKEN = "fixture-token";
  process.env.LM_TELEGRAM_WEBHOOK_SECRET = "fixture-webhook-secret";
  process.env.SUPABASE_URL = "https://fixture.supabase.co";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "fixture-service-role";
  process.env.LM_FEEDBACK_PROVENANCE_KEY = "fixture-provenance";
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
  const feedbackInserts = [];
  // The one linked user: chat 100 ↔ uid u1. Chat 999 is a stranger with no row.
  let storedDestination = null;

  global.fetch = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (url.hostname === "api.telegram.org") {
      if (url.pathname.endsWith("/sendMessage")) sentMessages.push(JSON.parse(init.body || "{}"));
      return response(200, { ok: true, result: { message_id: 1 } });
    }
    if (url.pathname === "/rest/v1/lm_feedback_intake" && method === "POST") {
      feedbackInserts.push(JSON.parse(init.body || "{}"));
      return response(201, [{ id: 1 }]);
    }
    if (url.pathname === "/rest/v1/lm_users" && method === "GET") {
      const chat = String(url.searchParams.get("telegram_chat_id") || "").replace(/^eq\./, "");
      if (chat === "999") return response(200, []); // stranger: no linked row
      return response(200, [{ uid: "u1", telegram_chat_id: chat || "100", payout_destination: storedDestination }]);
    }
    if (url.pathname === "/rest/v1/lm_users" && method === "PATCH") {
      patches.push({ url: String(url), body: JSON.parse(init.body || "{}") });
      const body = JSON.parse(init.body || "{}");
      if (!("payout_destination" in body)) return response(200, [{ uid: "u1" }]);
      // Honour every compare-and-set shape the intake uses.
      if (url.searchParams.get("payout_destination") === "is.null") {
        if (storedDestination) return response(200, []);
      } else if (url.searchParams.get("payout_destination->>status")) {
        const expected = String(url.searchParams.get("payout_destination->>status")).replace(/^eq\./, "");
        if (!storedDestination || storedDestination.status !== expected) return response(200, []);
      }
      storedDestination = body.payout_destination;
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

    const post = (update) => new Promise((resolve, reject) => {
      const body = JSON.stringify(update);
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
    const typed = (text, chatId = 100, messageId = 300) => post({
      message: { message_id: messageId, date: 1753500000, chat: { id: chatId }, from: { id: chatId }, text },
    });

    // 1. The user taps the wallet rail → the rail is stored AND the address question arrives.
    assert.equal(await post({ callback_query: {
      id: "cb-wallet", from: { id: 100 }, data: "payout:answer:wallet",
      message: { message_id: 246, chat: { id: 100 }, text: FINANCIAL_STRINGS.ja.payoutQuestion.text },
    } }), 200);
    assert.equal(storedDestination.status, "awaiting_address", "the tap must leave a pending-intake marker");
    assert.equal(storedDestination.type, "wallet");
    const question = sentMessages.find((m) => m.text === FINANCIAL_STRINGS.ja.payoutAddress.ask);
    assert.ok(question, `the address question must be sent, got ${JSON.stringify(sentMessages)}`);
    assert.equal(String(question.chat_id), "100");

    // 2. A stranger's chat typing an address changes nothing.
    const patchesBeforeStranger = patches.length;
    assert.equal(await typed(ADDRESS, 999), 200);
    assert.equal(patches.length, patchesBeforeStranger, "another chat's typed address must write nothing");
    assert.equal(storedDestination.status, "awaiting_address");

    // 3. A malformed address is rejected visibly and stays pending.
    assert.equal(await typed("not-an-address"), 200);
    assert.equal(sentMessages[sentMessages.length - 1].text, FINANCIAL_STRINGS.ja.payoutAddress.rejectedFormat);
    assert.equal(storedDestination.status, "awaiting_address");

    // 4. The real address: CAS to usable + read-back + quoted confirmation.
    assert.equal(await typed(ADDRESS), 200);
    assert.equal(storedDestination.status, "usable");
    assert.equal(storedDestination.address, ADDRESS);
    const confirmation = FINANCIAL_STRINGS.ja.payoutAddress.confirmed.replace("{short}", "0xfB69…d359");
    assert.equal(sentMessages[sentMessages.length - 1].text, confirmation);
    const usablePatch = patches.find((p) => p.body.payout_destination && p.body.payout_destination.status === "usable");
    assert.ok(usablePatch);
    // fetch normalises `->>` to `-%3E%3E` in the URL; both spell the same PostgREST json filter.
    assert.match(usablePatch.url, /payout_destination-(?:>>|%3E%3E)status=eq\.awaiting_address/,
      "the write must be a CAS, never blind");

    // 5. With the destination usable, a normal message flows to feedback — the intake claims nothing.
    const patchesBeforeFeedback = patches.length;
    assert.equal(await typed("feedback: the wake call was 5 minutes late", 100, 301), 200);
    assert.equal(feedbackInserts.length, 1, "feedback intake must still receive normal messages");
    assert.equal(patches.length, patchesBeforeFeedback);
    // And a second pasted address without 「送金先を変更」 does not overwrite the registered one.
    assert.equal(await typed("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed", 100, 302), 200);
    assert.equal(storedDestination.address, ADDRESS, "a usable destination is never silently overwritten");

    // 6. 「送金先を変更」 re-opens the intake and re-asks the same single question.
    assert.equal(await typed("送金先を変更", 100, 303), 200);
    assert.equal(storedDestination.status, "awaiting_address");
    assert.equal(sentMessages[sentMessages.length - 1].text, FINANCIAL_STRINGS.ja.payoutAddress.ask);
    assert.equal(await typed("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed", 100, 304), 200);
    assert.equal(storedDestination.status, "usable");
    assert.equal(storedDestination.address, "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed");
  } finally {
    console.log = originalLog;
    http.createServer = originalCreateServer;
    global.fetch = originalFetch;
    if (productionServer && productionServer.listening) {
      await new Promise((resolve) => productionServer.close(resolve));
    }
  }
});
