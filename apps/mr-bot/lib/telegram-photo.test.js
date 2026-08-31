"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { sendPhoto } = require("./telegram.js");

test("sendPhoto uploads real PNG bytes to Telegram without JSON/base64 persistence", async () => {
  const originalFetch = global.fetch;
  let request;
  global.fetch = async (url, options) => {
    request = { url, options };
    return { json: async () => ({ ok: true, result: { message_id: 88 } }) };
  };
  try {
    const response = await sendPhoto(
      "bot-token",
      "42",
      Buffer.from("png-bytes"),
      "Cloud provider receipt",
    );
    assert.equal(response.result.message_id, 88);
    assert.match(request.url, /sendPhoto$/);
    assert.equal(request.options.method, "POST");
    assert.equal(request.options.headers, undefined);
    assert.equal(request.options.body.get("chat_id"), "42");
    assert.equal(request.options.body.get("caption"), "Cloud provider receipt");
    assert.equal(request.options.body.get("photo").type, "image/png");
  } finally {
    global.fetch = originalFetch;
  }
});

test("sendPhoto converts network, timeout, and parse failures to the same delivery-unknown receipt", async () => {
  const originalFetch = global.fetch;
  const originalTimeout = AbortSignal.timeout;
  const timeoutCalls = [];
  const cases = [
    { name: "network", fetch: async (_url, options) => { assert.ok(options.signal instanceof AbortSignal); throw new Error("private network detail"); } },
    { name: "timeout", fetch: async (_url, options) => { assert.ok(options.signal instanceof AbortSignal); throw new Error("private timeout detail"); } },
    { name: "parse", fetch: async (_url, options) => { assert.ok(options.signal instanceof AbortSignal); return { json: async () => { throw new Error("private parser detail"); } }; } },
  ];
  AbortSignal.timeout = (milliseconds) => { timeoutCalls.push(milliseconds); return originalTimeout(milliseconds); };
  try {
    for (const scenario of cases) {
      global.fetch = scenario.fetch;
      const result = await sendPhoto("bot-token", "42", Buffer.from("png-bytes"), "caption");
      assert.deepEqual(result, { ok: false, delivery_unknown: true }, scenario.name);
      assert.equal(Object.hasOwn(result, "error"), false, scenario.name);
    }
    assert.deepEqual(timeoutCalls, [20_000, 20_000, 20_000]);
  } finally {
    global.fetch = originalFetch;
    AbortSignal.timeout = originalTimeout;
  }
});
