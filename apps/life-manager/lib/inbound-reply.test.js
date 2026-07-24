"use strict";
// Receive path: recipient parsing (all Resend shapes) + idempotent handleInboundReply + claimAsk token
// persistence. Closes vcsdd FIND-001/002/003/004. Run: node --test lib/inbound-reply.test.js
const test = require("node:test");
const assert = require("node:assert");
const { parseInboundRecipient, handleInboundReply, claimAsk } = require("./ask.js");
const { newReplyToken } = require("./reply-token.js");

const TOK = newReplyToken();
const A = `reply+${TOK}@reply.aniccaai.com`;

// ── parseInboundRecipient: every Resend payload shape (FIND-001) ──
test("parses to as a string", () => {
  assert.deepStrictEqual(parseInboundRecipient({ to: A, text: "at X" }), { token: TOK, text: "at X" });
});
test("parses to as [{address}]", () => {
  assert.strictEqual(parseInboundRecipient({ to: [{ address: A }], text: "y" }).token, TOK);
});
test("parses to as [{email}]", () => {
  assert.strictEqual(parseInboundRecipient({ to: [{ email: A }] }).token, TOK);
});
test("parses to as [string]", () => {
  assert.strictEqual(parseInboundRecipient({ to: [A] }).token, TOK);
});
test("unwraps the Resend {data:{...}} envelope", () => {
  assert.deepStrictEqual(parseInboundRecipient({ type: "inbound", data: { to: A, text: "hi" } }), { token: TOK, text: "hi" });
});
test("falls back to cc / headers.to", () => {
  assert.strictEqual(parseInboundRecipient({ to: "x@y.com", cc: [A] }).token, TOK);
  assert.strictEqual(parseInboundRecipient({ headers: { to: A } }).token, TOK);
});
test("returns token:null for a non-reply recipient", () => {
  assert.strictEqual(parseInboundRecipient({ to: "someone@else.com" }).token, null);
  assert.strictEqual(parseInboundRecipient({}).token, null);
});

// ── handleInboundReply: idempotency + guards (FIND-003/004) ──
function deps(over = {}) {
  const calls = { patch: 0, remember: 0, consumed: 0 };
  const base = {
    supaUrl: "http://s", supaKey: "k", composioKey: "c", geminiKey: "g",
    consume: async () => { calls.consumed++; return { uid: "u1", event_id: "e1" }; },
    listEvents: async () => [{ id: "e1", summary: "Dentist", location: "" }],
    needsLocation: () => true,
    match: async () => ({ location: "Shibuya 1-1" }),
    patch: async () => { calls.patch++; },
    remember: async () => { calls.remember++; },
  };
  return { opts: { ...base, ...over }, calls };
}

test("happy path: consume → match → patch + remember", async () => {
  const { opts, calls } = deps();
  const r = await handleInboundReply(TOK, "it's in Shibuya", opts);
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.location, "Shibuya 1-1");
  assert.strictEqual(calls.patch, 1);
  assert.strictEqual(calls.remember, 1);
});

test("IDEMPOTENT: an already-answered/duplicate token (consume→null) never patches", async () => {
  const { opts, calls } = deps({ consume: async () => null });
  const r = await handleInboundReply(TOK, "dup", opts);
  assert.strictEqual(r.ok, false);
  assert.match(r.reason, /already-answered|unknown/);
  assert.strictEqual(calls.patch, 0);
});

test("NO OVERWRITE: if the event already has a location, don't patch (FIND-004)", async () => {
  const { opts, calls } = deps({ needsLocation: () => false });
  const r = await handleInboundReply(TOK, "somewhere", opts);
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.alreadySet, true);
  assert.strictEqual(calls.patch, 0);
});

test("event vanished after consume → no patch", async () => {
  const { opts, calls } = deps({ listEvents: async () => [] });
  const r = await handleInboundReply(TOK, "x", opts);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(calls.patch, 0);
});

test("reply has no parseable location → no patch", async () => {
  const { opts, calls } = deps({ match: async () => ({ location: null }) });
  const r = await handleInboundReply(TOK, "idk", opts);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(calls.patch, 0);
});

// ── claimAsk persists reply_token (FIND-002) ──
test("claimAsk includes reply_token in the POST body when given", async () => {
  const orig = global.fetch;
  let captured = null;
  global.fetch = async (_url, opts) => { captured = JSON.parse(opts.body); return { status: 201 }; };
  try {
    const ok = await claimAsk("u1", "e1", "http://s", "k", "TOKEN123");
    assert.strictEqual(ok, true);
    assert.strictEqual(captured.reply_token, "TOKEN123");
    assert.strictEqual(captured.event_id, "e1");
  } finally { global.fetch = orig; }
});

test("claimAsk without a token omits reply_token (back-compat)", async () => {
  const orig = global.fetch;
  let captured = null;
  global.fetch = async (_url, opts) => { captured = JSON.parse(opts.body); return { status: 201 }; };
  try {
    await claimAsk("u1", "e1", "http://s", "k");
    assert.ok(!("reply_token" in captured));
  } finally { global.fetch = orig; }
});
