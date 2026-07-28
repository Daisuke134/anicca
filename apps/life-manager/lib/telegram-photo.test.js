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
