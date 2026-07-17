"use strict";
// mail-resend payload + token wiring. Run: node --test lib/mail-resend.test.js
const test = require("node:test");
const assert = require("node:assert");

const { sendAsk, sendLateNotice, resendSend, replyToFor } = require("./mail-resend.js");
const { newReplyToken } = require("./reply-token.js");

// capture the Resend payload without hitting the network
function fakeFetch(captured) {
  return async (_url, opts) => {
    captured.url = _url;
    captured.headers = opts.headers;
    captured.body = JSON.parse(opts.body);
    return { ok: true, status: 200, json: async () => ({ id: "re_test_123" }) };
  };
}

test("replyToFor formats reply+<token>@reply.aniccaai.com, local part <= 64", () => {
  const addr = replyToFor(newReplyToken());
  assert.match(addr, /^reply\+[A-Za-z0-9_-]{16,64}@reply\.aniccaai\.com$/);
  assert.ok(addr.slice(0, addr.indexOf("@")).length <= 64);
});

test("resendSend is fail-closed without a key", async () => {
  const r = await resendSend({ to: "a@b.com", subject: "x", text: "y", resendKey: "" });
  assert.strictEqual(r.sent, false);
});

test("sendAsk posts From hello@, Reply-To reply+<token>@, asks where the event is", async () => {
  const cap = {};
  const token = newReplyToken();
  const r = await sendAsk({ to: "user@example.com", replyToken: token, event: { id: "ev42", summary: "Dentist" }, resendKey: "k", fetchImpl: fakeFetch(cap) });
  assert.strictEqual(r.sent, true);
  assert.match(cap.body.from, /hello@aniccaai\.com/);
  assert.deepStrictEqual(cap.body.to, ["user@example.com"]);
  assert.strictEqual(cap.body.reply_to, `reply+${token}@reply.aniccaai.com`);
  assert.match(cap.body.subject, /Dentist/);
});

test("sendLateNotice replies to the USER's real email (so attendees reach the human)", async () => {
  const cap = {};
  const r = await sendLateNotice({ toAttendees: ["a@x.com", "b@y.com"], userName: "Dais", event: { summary: "Sync" }, etaMinutes: 12, userEmail: "dais@me.com", resendKey: "k", fetchImpl: fakeFetch(cap) });
  assert.strictEqual(r.sent, true);
  assert.deepStrictEqual(cap.body.to, ["a@x.com", "b@y.com"]);
  assert.strictEqual(cap.body.reply_to, "dais@me.com");
  assert.match(cap.body.text, /Dais/);
  assert.match(cap.body.text, /12 minutes/);
});
