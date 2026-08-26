"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { createConnpassApiClient } = require("./connpass-api-client.js");

const FIXTURE_CONNPASS_API_KEY = ["connpass", "test", "key", "0".repeat(16)].join("-");

test("missing API key fails before any connpass network access", async () => {
  let fetches = 0;
  assert.throws(() => createConnpassApiClient({
    apiKey: "",
    fetchImpl: async () => { fetches += 1; },
  }), /connpass API unavailable/i);
  assert.equal(fetches, 0);
});

test("search uses only official v2 GET with a secret header", async () => {
  const calls = [];
  const client = createConnpassApiClient({
    apiKey: FIXTURE_CONNPASS_API_KEY,
    now: () => 2_000,
    sleep: async () => {},
    async fetchImpl(url, options) {
      calls.push([url, options]);
      return {
        ok: true,
        status: 200,
        async json() {
          return { results_returned: 0, results_available: 0, results_start: 1, events: [] };
        },
      };
    },
  });
  const result = await client.searchEvents({
    ymd: ["20260805"],
    keyword_or: ["AI", "startup"],
    count: 100,
    order: 2,
  });
  assert.equal(result.events.length, 0);
  const url = new URL(calls[0][0]);
  assert.equal(url.origin, "https://connpass.com");
  assert.equal(url.pathname, "/api/v2/events/");
  assert.deepEqual(url.searchParams.getAll("ymd"), ["20260805"]);
  assert.deepEqual(url.searchParams.getAll("keyword_or"), ["AI", "startup"]);
  assert.equal(calls[0][1].method, "GET");
  assert.equal(calls[0][1].headers["X-API-Key"], FIXTURE_CONNPASS_API_KEY);
  assert.equal(JSON.stringify(result).includes(FIXTURE_CONNPASS_API_KEY), false);
});

test("unsupported query shapes cannot turn the client into a browser or write transport", async () => {
  const client = createConnpassApiClient({
    apiKey: FIXTURE_CONNPASS_API_KEY,
    fetchImpl: async () => assert.fail("invalid query must fail before fetch"),
  });
  for (const query of [
    { url: "https://group.connpass.com/event/123/" },
    { method: "POST" },
    { count: 101 },
    { ymd: ["2026-08-05"] },
    { start: 0 },
  ]) {
    await assert.rejects(client.searchEvents(query), /connpass API query invalid/i);
  }
});

test("requests are serialized at the stricter five-second interval stated by the application form", async () => {
  const sleeps = [];
  const times = [10_000, 10_100, 11_000];
  const client = createConnpassApiClient({
    apiKey: FIXTURE_CONNPASS_API_KEY,
    now: () => times.shift(),
    sleep: async (ms) => sleeps.push(ms),
    fetchImpl: async () => ({
      ok: true,
      status: 200,
      json: async () => ({ results_returned: 0, results_available: 0, results_start: 1, events: [] }),
    }),
  });
  await client.searchEvents({ keyword: ["AI"] });
  await client.searchEvents({ keyword: ["crypto"] });
  assert.deepEqual(sleeps, [4_900]);
});

test("HTTP errors and malformed payloads fail without reflecting the API key", async () => {
  for (const response of [
    { ok: false, status: 401, json: async () => ({ detail: "bad key" }) },
    { ok: true, status: 200, json: async () => ({ events: "not-array" }) },
  ]) {
    const client = createConnpassApiClient({
      apiKey: FIXTURE_CONNPASS_API_KEY,
      fetchImpl: async () => response,
    });
    await assert.rejects(client.searchEvents({ keyword: ["AI"] }), (error) => {
      assert.equal(error.message, "connpass API unavailable");
      assert.equal(error.message.includes(FIXTURE_CONNPASS_API_KEY), false);
      return true;
    });
  }
});

test("Tokyo inventory uses 28 ymd values and paginates official v2 results", async () => {
  const calls = [];
  const dates = Array.from({ length: 28 }, (_, offset) => (
    new Date(Date.UTC(2026, 7, 7 + offset)).toISOString().slice(0, 10).replaceAll("-", "")
  ));
  const client = createConnpassApiClient({
    apiKey: FIXTURE_CONNPASS_API_KEY,
    now: () => 10_000 + calls.length * 5_000,
    sleep: async () => {},
    async fetchImpl(url) {
      calls.push(new URL(url));
      const start = Number(calls.at(-1).searchParams.get("start"));
      const returned = start === 1 ? 100 : 20;
      return {
        ok: true, status: 200,
        async json() {
          return { results_returned: returned, results_available: 120, results_start: start,
            events: Array.from({ length: returned }, (_, index) => ({ id: start + index })) };
        },
      };
    },
  });

  const events = await client.searchTokyoInventory({ ymd: dates });
  assert.equal(events.length, 120);
  assert.deepEqual(calls.map((url) => url.searchParams.get("prefecture")), ["tokyo", "tokyo"]);
  assert.deepEqual(calls[0].searchParams.getAll("ymd"), dates);
  assert.deepEqual(calls.map((url) => url.searchParams.get("start")), ["1", "101"]);
  assert.deepEqual(calls.map((url) => url.searchParams.get("count")), ["100", "100"]);
});

test("429 fails closed without retrying or exposing the key", async () => {
  let fetches = 0;
  const client = createConnpassApiClient({
    apiKey: FIXTURE_CONNPASS_API_KEY,
    async fetchImpl() { fetches += 1; return { ok: false, status: 429 }; },
  });
  await assert.rejects(client.searchTokyoInventory({ ymd: ["20260807"] }), (error) => {
    assert.equal(error.message, "connpass API unavailable");
    assert.equal(error.message.includes(FIXTURE_CONNPASS_API_KEY), false);
    return true;
  });
  assert.equal(fetches, 1);
});
