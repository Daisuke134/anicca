// C-H1 (HARD-1): atomic claim helpers for ask + travel dedup (race-safe like wake).
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const { claimAsk, unclaimAsk } = require("./ask.js");
const { claimTravel, unclaimTravel } = require("./travel.js");

// Stub global.fetch to return a sequence of HTTP statuses, recording each call.
function stubFetch(statuses) {
  const calls = [];
  const orig = global.fetch;
  let i = 0;
  global.fetch = async (url, opts) => {
    calls.push({ url, method: (opts && opts.method) || "GET", body: (opts && opts.body) || "" });
    const status = statuses[Math.min(i++, statuses.length - 1)];
    return { status, ok: status >= 200 && status < 300, json: async () => [] };
  };
  return { calls, restore: () => { global.fetch = orig; } };
}

test("claimAsk: 201 → claimed (true); 409 → already asked (false); POSTs to lm_ask_log", async () => {
  let s = stubFetch([201]);
  assert.strictEqual(await claimAsk("u1", "e1", "http://s", "k"), true);
  assert.match(s.calls[0].url, /lm_ask_log/);
  assert.strictEqual(s.calls[0].method, "POST");
  assert.ok(s.calls[0].body.includes('"event_id":"e1"'));
  s.restore();
  s = stubFetch([409]);
  assert.strictEqual(await claimAsk("u1", "e1", "http://s", "k"), false, "409 → not claimed");
  s.restore();
});

test("claimAsk: any non-201 (500/network) → false (do NOT proceed to send on an unknown write)", async () => {
  let s = stubFetch([500]);
  assert.strictEqual(await claimAsk("u1", "e1", "http://s", "k"), false);
  s.restore();
});

test("claimAsk: no supa configured → true (best-effort, don't block the ask)", async () => {
  assert.strictEqual(await claimAsk("u1", "e1", "", ""), true);
});

test("claimTravel: 201 → true, 409 → false; POSTs lm_travel_log with the leg", async () => {
  let s = stubFetch([201]);
  assert.strictEqual(await claimTravel("u1", "k1", "go", "http://s", "k"), true);
  assert.match(s.calls[0].url, /lm_travel_log/);
  assert.ok(s.calls[0].body.includes('"leg":"go"'));
  assert.ok(s.calls[0].body.includes('"event_key":"k1"'));
  s.restore();
  s = stubFetch([409]);
  assert.strictEqual(await claimTravel("u1", "k1", "go", "http://s", "k"), false);
  s.restore();
});

test("claimTravel: go and return are SEPARATE legs (so one event gets both blocks, not deduped together)", async () => {
  const s = stubFetch([201, 201]);
  assert.strictEqual(await claimTravel("u1", "k1", "go", "http://s", "k"), true);
  assert.strictEqual(await claimTravel("u1", "k1", "return", "http://s", "k"), true);
  assert.ok(s.calls[0].body.includes('"leg":"go"'));
  assert.ok(s.calls[1].body.includes('"leg":"return"'));
  s.restore();
});

test("claimTravel: no supa → true (in-memory gcal dedup still guards obvious dups)", async () => {
  assert.strictEqual(await claimTravel("u1", "k1", "go", "", ""), true);
});

test("unclaimAsk DELETEs the exact (uid,event_id) row; unclaimTravel DELETEs (uid,event_key,leg)", async () => {
  let s = stubFetch([200]);
  await unclaimAsk("u1", "e1", "http://s", "k");
  assert.strictEqual(s.calls[0].method, "DELETE");
  assert.match(s.calls[0].url, /lm_ask_log\?uid=eq\.u1&event_id=eq\.e1/);
  s.restore();
  s = stubFetch([200]);
  await unclaimTravel("u1", "k1", "return", "http://s", "k");
  assert.strictEqual(s.calls[0].method, "DELETE");
  assert.match(s.calls[0].url, /lm_travel_log\?uid=eq\.u1&event_key=eq\.k1&leg=eq\.return/);
  s.restore();
});

// ── INTEGRATION: fillTravel actually uses the claim ledger (catches FIND-001 evKey collision) ──────
const { fillTravel } = require("./travel.js");
function makeFakeCalendar(eventRows) {
  const created = [];
  return {
    _created: created,
    async listEventsRaw() { return eventRows; },
    async createEvent(_uid, payload) { created.push({ ...payload }); return { successful: true }; },
  };
}
function rawEvId(id, summary, location, startIso, endIso) {
  return { id, summary, location, start: { dateTime: startIso }, end: { dateTime: endIso } };
}
// Simulate lm_travel_log UNIQUE(uid,event_key,leg): a (uid,event_key,leg) POST 201s once then 409s.
function stubClaimLedger() {
  const seen = new Set();
  const orig = global.fetch;
  global.fetch = async (url, opts) => {
    if (/lm_travel_log/.test(url) && opts && opts.method === "POST") {
      const b = JSON.parse(opts.body);
      const key = `${b.uid}|${b.event_key}|${b.leg}`;
      if (seen.has(key)) return { status: 409, ok: false, json: async () => [] };
      seen.add(key);
      return { status: 201, ok: true, json: async () => [] };
    }
    return { status: 200, ok: true, json: async () => [] }; // DELETE / other
  };
  return { seen, restore: () => { global.fetch = orig; } };
}

test("[INTEGRATION][FIND-001] two same-startMs events with DIFFERENT ids BOTH get [Travel] blocks (evKey uses id, not startMs)", async () => {
  const s = stubClaimLedger();
  const start = "2026-06-20T14:00:00+09:00", end = "2026-06-20T15:00:00+09:00";
  const cal = makeFakeCalendar([
    rawEvId("evA", "Dentist", "Shibuya Hikarie, Tokyo", start, end),
    rawEvId("evB", "Investor meet", "Roppongi Hills, Tokyo", start, end),
  ]);
  await fillTravel("uidX", {
    apiKey: "x", mapsKey: "x", home: "Setagaya, Tokyo",
    nowMs: Date.parse("2026-06-20T08:00:00+09:00"),
    calendar: cal, supaUrl: "http://s", supaKey: "k", _directionsMinutes: async () => 30,
  });
  const blocks = cal._created.filter((b) => /\[Travel\]/.test(b.summary || ""));
  // With evKey=id, evA and evB claim distinct keys → BOTH produce blocks. With the FIND-001 bug
  // (evKey=startMs) evB's claims would 409 and its block would be silently dropped.
  const distinctDest = new Set(blocks.map((b) => b.location));
  assert.ok(blocks.length >= 2, `both same-start events got blocks, got ${blocks.length}`);
  assert.ok(distinctDest.size >= 2, `blocks for BOTH venues exist (no evKey collision), got ${[...distinctDest]}`);
  s.restore();
});

test("[INTEGRATION] re-running fillTravel does NOT double-create — 2nd run's claims all 409", async () => {
  const s = stubClaimLedger();
  const start = "2026-06-20T14:00:00+09:00", end = "2026-06-20T15:00:00+09:00";
  const rows = [rawEvId("evZ", "Dentist", "Shibuya Hikarie, Tokyo", start, end)];
  const base = {
    apiKey: "x", mapsKey: "x", home: "Setagaya, Tokyo",
    nowMs: Date.parse("2026-06-20T08:00:00+09:00"), supaUrl: "http://s", supaKey: "k",
    _directionsMinutes: async () => 30,
  };
  const cal1 = makeFakeCalendar(rows);
  await fillTravel("uidY", { ...base, calendar: cal1 });
  assert.ok(cal1._created.length >= 1, "1st run creates block(s)");
  const cal2 = makeFakeCalendar(rows); // same claim ledger (stub seen-set persists)
  await fillTravel("uidY", { ...base, calendar: cal2 });
  const blocks2 = cal2._created.filter((b) => /\[Travel\]/.test(b.summary || ""));
  assert.strictEqual(blocks2.length, 0, "2nd run: claims 409 → no double-create");
  s.restore();
});
