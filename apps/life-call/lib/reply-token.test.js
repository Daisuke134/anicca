"use strict";
// Reply-To token: short, unguessable, fits the 64-char local-part limit. Run: node --test lib/reply-token.test.js
const test = require("node:test");
const assert = require("node:assert");
const { newReplyToken, isReplyToken } = require("./reply-token.js");

test("newReplyToken is 22 base64url chars (128 bits) and passes isReplyToken", () => {
  const t = newReplyToken();
  assert.strictEqual(t.length, 22);
  assert.match(t, /^[A-Za-z0-9_-]+$/);
  assert.ok(isReplyToken(t));
});

test("reply+<token>@reply.aniccaai.com stays under the 64-char local-part limit", () => {
  const local = "reply+" + newReplyToken();
  assert.ok(local.length <= 64, `local part ${local.length} must be <= 64`);
});

test("tokens are unique across calls", () => {
  const seen = new Set();
  for (let i = 0; i < 1000; i++) seen.add(newReplyToken());
  assert.strictEqual(seen.size, 1000);
});

test("isReplyToken rejects garbage / wrong shape", () => {
  for (const bad of ["", "short", "has space", "a".repeat(65), "bad/char+", null, undefined, 123]) {
    assert.strictEqual(isReplyToken(bad), false);
  }
});
