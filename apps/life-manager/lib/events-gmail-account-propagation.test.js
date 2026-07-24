"use strict";
// LM-8b propagation: proves a threaded gmailAccountId flows through a REAL getCalendar CONSUMER
// (fetchUpcomingEvents, not index.js directly) all the way to the Unipile HTTP request's account_id
// query param, when LIFE_CAL_TRANSPORT=unipile. Style mirrors lib/transport/calendar-unipile.test.js.
// Run: node --test lib/events-gmail-account-propagation.test.js
const { test } = require("node:test");
const assert = require("node:assert");
const { fetchUpcomingEvents } = require("./events.js");

test("fetchUpcomingEvents threads opts.gmailAccountId to the Unipile account_id query param", async () => {
  const previous = {
    life: process.env.LIFE_TRANSPORT,
    calendar: process.env.LIFE_CAL_TRANSPORT,
    cache: process.env.LM_CAL_CACHE,
    token: process.env.UNIPILE_TOKEN,
    dsn: process.env.UNIPILE_DSN,
  };
  process.env.LIFE_CAL_TRANSPORT = "unipile";
  process.env.LM_CAL_CACHE = "off"; // avoid the process-lifetime cache colliding across test runs
  process.env.UNIPILE_TOKEN = "token-1";
  process.env.UNIPILE_DSN = "api.example:13111";

  const original = global.fetch;
  const calls = [];
  global.fetch = async (url) => {
    calls.push(String(url));
    if (calls.length === 1) {
      return { ok: true, json: async () => ({ data: [{ id: "cal-primary", is_default: true }] }) };
    }
    return { ok: true, json: async () => ({ data: [] }) };
  };

  try {
    await fetchUpcomingEvents("uid-1", {
      nowMs: Date.parse("2026-07-20T00:00:00Z"), horizonH: 6, gmailAccountId: "acct-lm8b-1",
    });
    // one call to resolve the primary calendar + one to list its events — both must carry the
    // per-user Unipile account id threaded all the way from the fetchUpcomingEvents opts.
    assert.equal(calls.length, 2, "resolved the primary calendar then listed its events");
    for (const url of calls) {
      assert.equal(new URL(url).searchParams.get("account_id"), "acct-lm8b-1");
    }
  } finally {
    global.fetch = original;
    if (previous.life == null) delete process.env.LIFE_TRANSPORT; else process.env.LIFE_TRANSPORT = previous.life;
    if (previous.calendar == null) delete process.env.LIFE_CAL_TRANSPORT; else process.env.LIFE_CAL_TRANSPORT = previous.calendar;
    if (previous.cache == null) delete process.env.LM_CAL_CACHE; else process.env.LM_CAL_CACHE = previous.cache;
    if (previous.token == null) delete process.env.UNIPILE_TOKEN; else process.env.UNIPILE_TOKEN = previous.token;
    if (previous.dsn == null) delete process.env.UNIPILE_DSN; else process.env.UNIPILE_DSN = previous.dsn;
  }
});

// Backward compat (invariant #1): LIFE_CAL_TRANSPORT unset (composio default) — gmailAccountId is
// simply ignored (composio only cares about apiKey), so no fetch to Unipile ever happens.
test("backward compat: without LIFE_CAL_TRANSPORT, gmailAccountId is a harmless no-op (composio path)", async () => {
  const previous = { calendar: process.env.LIFE_CAL_TRANSPORT, cache: process.env.LM_CAL_CACHE };
  delete process.env.LIFE_CAL_TRANSPORT;
  process.env.LM_CAL_CACHE = "off";
  const original = global.fetch;
  const calls = [];
  global.fetch = async (url) => { calls.push(String(url)); return { ok: true, json: async () => ({ items: [] }) }; };
  try {
    await fetchUpcomingEvents("uid-1", {
      apiKey: "composio-key", nowMs: Date.parse("2026-07-20T00:00:00Z"), gmailAccountId: "acct-lm8b-1",
    });
    assert.ok(calls.every((url) => !url.includes("unipile") && !new URL(url).searchParams.has("account_id")));
  } finally {
    global.fetch = original;
    if (previous.calendar == null) delete process.env.LIFE_CAL_TRANSPORT; else process.env.LIFE_CAL_TRANSPORT = previous.calendar;
    if (previous.cache == null) delete process.env.LM_CAL_CACHE; else process.env.LM_CAL_CACHE = previous.cache;
  }
});
