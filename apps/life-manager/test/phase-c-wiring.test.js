"use strict";
// PHASE C / PC-1 — WIRING tests (FIND-001/004): prove the recall→no-model and patch→remember invariants in
// the REAL askTick/telegram-reply code paths (not just the helpers). Run: node --test test/phase-c-wiring.test.js
const { test } = require("node:test");
const assert = require("node:assert");
const { recallOrResolve } = require("../lib/ask.js");
const { resolveTelegramReply } = require("../lib/telegram-reply.js");

// REQ-45: a memory hit fills WITHOUT calling the resolution model.
test("recallOrResolve: memory HIT → filled+fromMemory, model NOT called", async () => {
  let resolveCalled = false;
  const res = await recallOrResolve({ summary: "Lunch with Mai", id: "e1" }, {
    uid: "u1", supaUrl: "http://s", supaKey: "k",
    recall: async (uid, phrase) => { assert.strictEqual(phrase, "lunch with mai"); return "Shibuya Hikarie"; },
    resolve: async () => { resolveCalled = true; return { kind: "online" }; },
  });
  assert.deepStrictEqual(res, { kind: "filled", location: "Shibuya Hikarie", fromMemory: true });
  assert.strictEqual(resolveCalled, false, "the model MUST NOT run on a memory hit (REQ-45)");
});

// REQ-45: a memory miss delegates to the agentic resolution (online/filled/ask preserved).
test("recallOrResolve: memory MISS → delegates to agentResolveLocation", async () => {
  const res = await recallOrResolve({ summary: "Zoom sync", id: "e2" }, {
    uid: "u1", supaUrl: "http://s", supaKey: "k",
    recall: async () => null,
    resolve: async () => ({ kind: "online" }),
  });
  assert.deepStrictEqual(res, { kind: "online" });
});

// REQ-46: a Telegram reply that patches a location ALSO remembers it, keyed by the SAME placeKey recall uses.
test("resolveTelegramReply: patch→REMEMBER fires with placeKey(summary)", async () => {
  const remembered = [];
  let patched = null;
  const r = await resolveTelegramReply("chat1", "It's at Shibuya Hikarie", {
    lookupUser: async () => ({ uid: "u9", calendar_provider: "composio_gcal" }),
    calendar: {
      listEventsRaw: async () => [{ id: "ev1", summary: "Lunch with Mai", start: { dateTime: "2026-07-01T12:00:00Z" } }],
      patchEvent: async (uid, args) => { patched = { uid, ...args }; },
    },
    match: async () => ({ eventId: "ev1", location: "Shibuya Hikarie" }),
    remember: async (uid, phrase, addr) => { remembered.push({ uid, phrase, addr }); return true; },
  });
  assert.strictEqual(r.filled, true);
  assert.strictEqual(patched.location, "Shibuya Hikarie");
  assert.deepStrictEqual(remembered, [{ uid: "u9", phrase: "lunch with mai", addr: "Shibuya Hikarie" }],
    "the remember key must equal the recall key so the next same-summary event autofills");
});

// REQ-46: no match → no patch, no remember (don't store a guess).
test("resolveTelegramReply: no match → no remember", async () => {
  let remembered = false;
  const r = await resolveTelegramReply("chat1", "random text", {
    lookupUser: async () => ({ uid: "u9", calendar_provider: "composio_gcal" }),
    calendar: { listEventsRaw: async () => [{ id: "ev1", summary: "X", start: { dateTime: "2026-07-01T12:00:00Z" } }], patchEvent: async () => {} },
    match: async () => null,
    remember: async () => { remembered = true; return true; },
  });
  assert.strictEqual(r.filled, false);
  assert.strictEqual(remembered, false);
});
