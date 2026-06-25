"use strict";
// Contract for the signed Reply-To token. Run: node --test lib/reply-token.test.js
const test = require("node:test");
const assert = require("node:assert");

process.env.LM_REPLY_SECRET = "test_reply_secret_0123456789abcdef";
const { makeReplyToken, verifyReplyToken } = require("./reply-token.js");

test("round-trips uid + eventId", () => {
  const t = makeReplyToken("lm_abc123", "evt_9", 1000);
  const r = verifyReplyToken(t, 1000);
  assert.deepStrictEqual(r, { uid: "lm_abc123", eventId: "evt_9" });
});

test("handles ids with - and _ (google event ids)", () => {
  const t = makeReplyToken("lm_3f-1a_2b", "abc_DEF-123", 1000);
  assert.deepStrictEqual(verifyReplyToken(t, 1000), { uid: "lm_3f-1a_2b", eventId: "abc_DEF-123" });
});

test("rejects a tampered payload", () => {
  const t = makeReplyToken("lm_a", "evt_1", 1000);
  const [payload, sig] = t.split(".");
  const forged = Buffer.from("lm_VICTIM|evt_1|1000").toString("base64url") + "." + sig;
  assert.strictEqual(verifyReplyToken(forged, 1000), null);
});

test("rejects a tampered signature", () => {
  const t = makeReplyToken("lm_a", "evt_1", 1000);
  const bad = t.slice(0, -1) + (t.slice(-1) === "A" ? "B" : "A");
  assert.strictEqual(verifyReplyToken(bad, 1000), null);
});

test("rejects a token forged under a different secret", () => {
  const t = makeReplyToken("lm_a", "evt_1", 1000);
  process.env.LM_REPLY_SECRET = "different_secret";
  delete require.cache[require.resolve("./reply-token.js")];
  const other = require("./reply-token.js");
  assert.strictEqual(other.verifyReplyToken(t, 1000), null);
  // restore
  process.env.LM_REPLY_SECRET = "test_reply_secret_0123456789abcdef";
  delete require.cache[require.resolve("./reply-token.js")];
});

test("rejects an expired token (older than maxAge)", () => {
  const { makeReplyToken: mk, verifyReplyToken: vf } = require("./reply-token.js");
  const t = mk("lm_a", "evt_1", 0);
  assert.strictEqual(vf(t, 31 * 24 * 3600 * 1000), null); // 31 days later > 30d max
  assert.deepStrictEqual(vf(t, 29 * 24 * 3600 * 1000), { uid: "lm_a", eventId: "evt_1" });
});

test("rejects a future-dated token beyond skew", () => {
  const { makeReplyToken: mk, verifyReplyToken: vf } = require("./reply-token.js");
  const t = mk("lm_a", "evt_1", 1_000_000);
  assert.strictEqual(vf(t, 0), null);
});

test("rejects malformed tokens", () => {
  const { verifyReplyToken: vf } = require("./reply-token.js");
  for (const bad of ["", "nope", "a.b.c.d", ".", "abc."]) assert.strictEqual(vf(bad, 1000), null);
});
